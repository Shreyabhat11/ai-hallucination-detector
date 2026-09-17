from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    # main._rate_limiter is a module-level singleton so its state persists
    # across tests unless reset -- avoid cross-test flakiness.
    main._rate_limiter._hits.clear()
    yield
    main._rate_limiter._hits.clear()


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "kb_documents" in body


def test_empty_prompt_rejected(client):
    resp = client.post("/ask", json={"prompt": ""})
    assert resp.status_code == 422


def test_whitespace_only_prompt_rejected(client):
    resp = client.post("/ask", json={"prompt": "   "})
    assert resp.status_code == 422


def test_oversized_prompt_rejected(client):
    resp = client.post("/ask", json={"prompt": "x" * 5000})
    assert resp.status_code == 422


def test_invalid_mode_rejected(client):
    resp = client.post("/ask", json={"prompt": "hello", "mode": "ultra"})
    assert resp.status_code == 422


@patch("main.run_detection", new_callable=AsyncMock)
@patch("main.generate_answer_async", new_callable=AsyncMock)
def test_ask_happy_path(mock_generate, mock_run_detection, client):
    mock_generate.return_value = "The Eiffel Tower was completed in 1889."
    mock_run_detection.return_value = {
        "risk_score": 10,
        "module_scores": {"fact": 1.0, "logic": 1.0, "citation": 0.5, "confidence": 1.0, "cross": 1.0},
        "claims": [{"claim": "The Eiffel Tower was completed in 1889.", "verdict": "SUPPORTED", "score": 1.0}],
        "mode": "standard",
        "latency": {"claim_extraction_ms": 1.0},
    }

    resp = client.post("/ask", json={"prompt": "When was the Eiffel Tower built?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "The Eiffel Tower was completed in 1889."
    assert body["risk_score"] == 10
    assert "generation_ms" in body["latency"]
    assert "total_ms" in body["latency"]


@patch("main.run_detection", new_callable=AsyncMock)
@patch("main.generate_answer_async", new_callable=AsyncMock)
def test_ask_defaults_to_standard_mode(mock_generate, mock_run_detection, client):
    mock_generate.return_value = "answer"
    mock_run_detection.return_value = {
        "risk_score": 0,
        "module_scores": {},
        "claims": [],
        "mode": "standard",
        "latency": {},
    }

    client.post("/ask", json={"prompt": "hello"})

    _, kwargs = mock_run_detection.call_args
    # mode passed positionally in main.py -- check via call_args directly
    called_args = mock_run_detection.call_args.args
    called_kwargs = mock_run_detection.call_args.kwargs
    assert called_kwargs.get("mode", called_args[-1] if called_args else None) == "standard"


def test_oversized_body_rejected_before_parsing(client):
    huge_prompt = "x" * (60 * 1024)  # bigger than the 50 KB MAX_REQUEST_BODY_BYTES default
    resp = client.post("/ask", json={"prompt": huge_prompt})
    assert resp.status_code == 413


def test_rate_limit_blocks_after_threshold(client):
    # Tighten the limiter just for this test so it doesn't need 20+ requests.
    original_max = main._rate_limiter.max_requests
    main._rate_limiter.max_requests = 2
    try:
        with patch("main.run_detection", new_callable=AsyncMock) as mock_run_detection, patch(
            "main.generate_answer_async", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = "answer"
            mock_run_detection.return_value = {
                "risk_score": 0,
                "module_scores": {},
                "claims": [],
                "mode": "standard",
                "latency": {},
            }

            r1 = client.post("/ask", json={"prompt": "one"})
            r2 = client.post("/ask", json={"prompt": "two"})
            r3 = client.post("/ask", json={"prompt": "three"})

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
        assert "Retry-After" in r3.headers
    finally:
        main._rate_limiter.max_requests = original_max


def test_health_endpoint_not_rate_limited(client):
    # Tighten the limiter, but /health should be exempt.
    original_max = main._rate_limiter.max_requests
    main._rate_limiter.max_requests = 1
    try:
        for _ in range(5):
            resp = client.get("/health")
            assert resp.status_code == 200
    finally:
        main._rate_limiter.max_requests = original_max


def test_unhandled_exception_returns_safe_generic_message():
    # raise_server_exceptions=False: by default TestClient re-raises
    # exceptions instead of returning the response, specifically so bugs
    # don't hide silently in tests. Here we're deliberately testing that
    # the registered handler converts it to a safe response, so we need
    # the client to actually hand back that response instead of re-raising.
    client = TestClient(main.app, raise_server_exceptions=False)
    with patch("main.generate_answer_async", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = RuntimeError("some internal secret detail")
        resp = client.post("/ask", json={"prompt": "hello"})

    assert resp.status_code == 500
    body = resp.json()
    assert body == {"error": "internal server error"}
    # the actual exception message must never reach the client
    assert "some internal secret detail" not in resp.text


def test_cors_headers_reflect_allowed_origin(client):
    allowed_origin = main.ALLOWED_ORIGINS[0]
    resp = client.get("/health", headers={"Origin": allowed_origin})
    assert resp.headers.get("access-control-allow-origin") == allowed_origin


def test_cors_rejects_disallowed_origin(client):
    resp = client.get(
        "/health",
        headers={"Origin": "https://not-an-allowed-origin.example.com"},
    )
    # CORSMiddleware simply omits the allow-origin header for a disallowed
    # origin rather than blocking the request server-side (browsers enforce
    # the block); this asserts that we didn't reflect the disallowed origin.
    assert resp.headers.get("access-control-allow-origin") != "https://not-an-allowed-origin.example.com"
