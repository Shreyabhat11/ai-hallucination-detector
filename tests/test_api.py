from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import main


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
