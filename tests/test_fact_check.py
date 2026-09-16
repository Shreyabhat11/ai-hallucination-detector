from unittest.mock import AsyncMock, patch

import pytest

from app.detector.fact_check import fact_check_claims


@pytest.mark.asyncio
async def test_no_claims_returns_default_score():
    results, score = await fact_check_claims([])
    assert results == []
    assert score == 1.0


@pytest.mark.asyncio
@patch("app.detector.fact_check.store")
@patch("app.detector.fact_check.search_web_async", new_callable=AsyncMock)
@patch("app.detector.fact_check.verify_prompt_async", new_callable=AsyncMock)
async def test_no_evidence_gives_insufficient_evidence_verdict(
    mock_verify, mock_search, mock_store
):
    mock_store.query.return_value = []
    mock_search.return_value = []

    results, score = await fact_check_claims(["Some unverifiable claim"], use_web_search=True)

    assert len(results) == 1
    assert results[0]["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert results[0]["evidence"] is None
    # verifier should never be called when there's no evidence to give it
    mock_verify.assert_not_called()


@pytest.mark.asyncio
@patch("app.detector.fact_check.store")
@patch("app.detector.fact_check.search_web_async", new_callable=AsyncMock)
@patch("app.detector.fact_check.verify_prompt_async", new_callable=AsyncMock)
async def test_supported_verdict_scores_full_marks(mock_verify, mock_search, mock_store):
    mock_store.query.return_value = ["The Eiffel Tower was completed in 1889."]
    mock_search.return_value = []
    mock_verify.return_value = "SUPPORTED"

    results, score = await fact_check_claims(["The Eiffel Tower was completed in 1889."])

    assert results[0]["verdict"] == "SUPPORTED"
    assert results[0]["score"] == 1.0
    assert score == 1.0


@pytest.mark.asyncio
@patch("app.detector.fact_check.store")
@patch("app.detector.fact_check.search_web_async", new_callable=AsyncMock)
@patch("app.detector.fact_check.verify_prompt_async", new_callable=AsyncMock)
async def test_contradicted_verdict_scores_zero(mock_verify, mock_search, mock_store):
    mock_store.query.return_value = ["The Eiffel Tower is 500 meters tall."]
    mock_search.return_value = []
    mock_verify.return_value = "CONTRADICTED"

    results, score = await fact_check_claims(["The Eiffel Tower is 50 meters tall."])

    assert results[0]["verdict"] == "CONTRADICTED"
    assert results[0]["score"] == 0.0


@pytest.mark.asyncio
@patch("app.detector.fact_check.store")
@patch("app.detector.fact_check.search_web_async", new_callable=AsyncMock)
@patch("app.detector.fact_check.verify_prompt_async", new_callable=AsyncMock)
async def test_one_failing_claim_does_not_crash_the_others(mock_verify, mock_search, mock_store):
    mock_store.query.side_effect = [
        RuntimeError("KB is on fire"),  # claim 1: KB lookup blows up
        ["Python was created by Guido van Rossum."],  # claim 2: fine
    ]
    mock_search.return_value = []
    mock_verify.return_value = "SUPPORTED"

    results, score = await fact_check_claims(
        ["claim that breaks", "Python was created by Guido van Rossum."]
    )

    assert len(results) == 2
    # claim 1's KB failure degrades to "no evidence", not a crash
    assert results[0]["verdict"] == "INSUFFICIENT_EVIDENCE"
    # claim 2 still gets fully processed
    assert results[1]["verdict"] == "SUPPORTED"


@pytest.mark.asyncio
@patch("app.detector.fact_check.store")
@patch("app.detector.fact_check.search_web_async", new_callable=AsyncMock)
async def test_web_search_skipped_when_disabled(mock_search, mock_store):
    mock_store.query.return_value = ["some KB doc"]
    with patch(
        "app.detector.fact_check.verify_prompt_async", new_callable=AsyncMock
    ) as mock_verify:
        mock_verify.return_value = "SUPPORTED"
        await fact_check_claims(["a claim"], use_web_search=False)

    mock_search.assert_not_called()


@pytest.mark.asyncio
@patch("app.detector.fact_check.store")
@patch("app.detector.fact_check.search_web_async", new_callable=AsyncMock)
@patch("app.detector.fact_check.verify_prompt_async", new_callable=AsyncMock)
async def test_web_sources_are_populated_with_title_and_url(mock_verify, mock_search, mock_store):
    mock_store.query.return_value = []
    mock_search.return_value = [
        {"title": "Eiffel Tower - Wikipedia", "url": "https://en.wikipedia.org/wiki/Eiffel_Tower", "body": "Completed in 1889."}
    ]
    mock_verify.return_value = "SUPPORTED"

    results, _ = await fact_check_claims(["The Eiffel Tower was completed in 1889."])

    assert results[0]["sources"] == [
        {"title": "Eiffel Tower - Wikipedia", "url": "https://en.wikipedia.org/wiki/Eiffel_Tower"}
    ]
    assert "Completed in 1889." in results[0]["evidence"]
