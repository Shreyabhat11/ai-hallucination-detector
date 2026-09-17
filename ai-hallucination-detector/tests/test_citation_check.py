from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.detector.citation_check import citation_score_async, extract_citations


def test_extract_citations_finds_urls_numbered_and_author_year():
    text = (
        "The tower was built in 1889 [1]. See https://example.com/source "
        "for details (Smith, 2020)."
    )
    citations = extract_citations(text)
    types = {c["type"] for c in citations}
    assert "url" in types
    assert "numbered" in types
    assert "author_year" in types


def test_no_citations_found():
    assert extract_citations("The sky is blue.") == []


@pytest.mark.asyncio
async def test_no_citations_is_neutral_not_suspicious():
    score, reports = await citation_score_async("The sky is blue with no sources.")
    assert score == 0.5
    assert reports == []


@pytest.mark.asyncio
async def test_bare_numbered_citation_is_no_source():
    score, reports = await citation_score_async("This is true [1].")
    assert reports[0]["verdict"] == "NO_SOURCE"
    assert reports[0]["type"] == "numbered"


@pytest.mark.asyncio
async def test_reachable_url_is_supported():
    fake_response = MagicMock(status_code=200)

    with patch("httpx.AsyncClient.head", new=AsyncMock(return_value=fake_response)):
        score, reports = await citation_score_async("See https://example.com/real-source for proof.")

    assert reports[0]["type"] == "url"
    assert reports[0]["verdict"] == "SUPPORTED"
    assert score == 1.0


@pytest.mark.asyncio
async def test_unreachable_url_is_unsupported():
    with patch("httpx.AsyncClient.head", new=AsyncMock(side_effect=Exception("connection refused"))):
        score, reports = await citation_score_async("See https://this-domain-does-not-resolve.invalid/x for proof.")

    assert reports[0]["verdict"] == "UNSUPPORTED"
    assert score == 0.2


@pytest.mark.asyncio
async def test_not_found_url_is_unsupported():
    fake_response = MagicMock(status_code=404)

    with patch("httpx.AsyncClient.head", new=AsyncMock(return_value=fake_response)):
        score, reports = await citation_score_async("See https://example.com/missing for proof.")

    assert reports[0]["verdict"] == "UNSUPPORTED"


@pytest.mark.asyncio
async def test_server_error_url_is_partially_supported():
    fake_response = MagicMock(status_code=503)

    with patch("httpx.AsyncClient.head", new=AsyncMock(return_value=fake_response)):
        score, reports = await citation_score_async("See https://example.com/flaky for proof.")

    assert reports[0]["verdict"] == "PARTIALLY_SUPPORTED"
