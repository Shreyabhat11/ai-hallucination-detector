"""Citation verification.

The previous version treated ANY citation-shaped text as suspicious just for
existing. This version actually tries to say something about each citation:

- A URL citation is checked for reachability (HEAD request). Reachable does
  NOT mean "supports the claim" -- we only know the source exists and
  responds. Calling that SUPPORTED (not "verified correct") is a deliberate
  choice to avoid overclaiming what a reachability check can tell you.
- A bare numbered ([1]) or author-year ("(Smith, 2020)") citation with no
  URL can't be resolved to an actual source from plain text alone. Rather
  than guess, this is honestly labeled NO_SOURCE.

Verdicts: SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, NO_SOURCE.
"""

from __future__ import annotations

import asyncio
import logging
import re

import httpx

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://[^\s\)\]]+")
_NUMBERED_RE = re.compile(r"\[\d+\]")
_AUTHOR_YEAR_RE = re.compile(r"\([^()]*\b(19|20)\d{2}\b[^()]*\)")

_VERDICT_SCORE = {
    "SUPPORTED": 1.0,
    "PARTIALLY_SUPPORTED": 0.6,
    "UNSUPPORTED": 0.2,
    "NO_SOURCE": 0.4,
}

DEFAULT_TIMEOUT_S = 5.0


def extract_citations(text: str) -> list[dict]:
    citations: list[dict] = []
    url_spans = []

    for m in _URL_RE.finditer(text):
        citations.append({"type": "url", "text": m.group(0)})
        url_spans.append(m.group(0))

    for m in _NUMBERED_RE.finditer(text):
        citations.append({"type": "numbered", "text": m.group(0)})

    for m in _AUTHOR_YEAR_RE.finditer(text):
        span_text = m.group(0)
        if any(span_text in u for u in url_spans):
            continue
        citations.append({"type": "author_year", "text": span_text})

    return citations


async def _check_url(client: httpx.AsyncClient, url: str) -> str:
    """2xx/3xx -> reachable, treated as SUPPORTED (source exists and
    responds; this is NOT a claim that it supports the text's assertion,
    just that the citation resolves to something real).
    4xx -> the resource doesn't exist at that URL, fairly confidently
    UNSUPPORTED.
    5xx -> the server had an error; that's inconclusive (could be a bad
    citation, could just be a flaky server right now), so it's scored as
    PARTIALLY_SUPPORTED rather than confidently wrong.
    """
    try:
        resp = await client.head(url)
        if resp.status_code < 400:
            return "SUPPORTED"
        if resp.status_code < 500:
            return "UNSUPPORTED"
        return "PARTIALLY_SUPPORTED"
    except Exception as e:
        logger.warning("Citation URL check failed for %s: %s", url, e)
        return "UNSUPPORTED"


async def citation_score_async(
    answer: str, timeout: float = DEFAULT_TIMEOUT_S
) -> tuple[float, list[dict]]:
    """Returns (aggregate score, per-citation reports). No citations found
    is neutral (0.5), not suspicious -- most correct answers cite nothing.
    """
    citations = extract_citations(answer)
    if not citations:
        return 0.5, []

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        async def _report(c: dict) -> dict:
            if c["type"] == "url":
                verdict = await _check_url(client, c["text"])
            else:
                verdict = "NO_SOURCE"
            return {**c, "verdict": verdict}

        reports = await asyncio.gather(*[_report(c) for c in citations])

    avg = sum(_VERDICT_SCORE[r["verdict"]] for r in reports) / len(reports)
    return avg, list(reports)
