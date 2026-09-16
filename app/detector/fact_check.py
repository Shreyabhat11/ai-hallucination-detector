import asyncio
import logging

from app.llm.verifier import verify_prompt_async
from app.utils.web_search import search_web_async
from app.vector_db.simple_store import store

logger = logging.getLogger(__name__)

VERDICTS = ("SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED", "UNCERTAIN")

_VERDICT_SCORE = {
    "SUPPORTED": 1.0,
    "PARTIALLY_SUPPORTED": 0.6,
    "UNCERTAIN": 0.5,
    "CONTRADICTED": 0.0,
    # not a real verdict from the verifier -- assigned when no evidence at
    # all was found, so we don't conflate "unproven" with "false".
    "INSUFFICIENT_EVIDENCE": 0.5,
}


def _parse_verdict(raw: str) -> str:
    upper = (raw or "").upper()
    for label in VERDICTS:
        if label in upper:
            return label
    return "UNCERTAIN"


async def _verify_one_claim(claim: str, semaphore: asyncio.Semaphore, use_web_search: bool) -> dict:
    async with semaphore:
        # KB search and web search are independent of each other, run them
        # concurrently. Each is individually exception-isolated so one
        # failing source degrades to "no evidence from that source" rather
        # than failing the claim.
        async def kb_lookup():
            try:
                return await asyncio.to_thread(store.query, claim, 3)
            except Exception as e:
                logger.warning("KB lookup failed for claim %r: %s", claim, e)
                return []

        async def web_lookup():
            if not use_web_search:
                return ""
            try:
                return await search_web_async(claim)
            except Exception as e:
                logger.warning("Web search failed for claim %r: %s", claim, e)
                return ""

        kb_docs, web_evidence = await asyncio.gather(kb_lookup(), web_lookup())

        evidence_parts = list(kb_docs)
        if web_evidence:
            evidence_parts.append(web_evidence)
        evidence_text = "\n".join(p for p in evidence_parts if p).strip()

        if not evidence_text:
            return {
                "claim": claim,
                "verdict": "INSUFFICIENT_EVIDENCE",
                "score": _VERDICT_SCORE["INSUFFICIENT_EVIDENCE"],
                "evidence": None,
                "sources": [],
            }

        prompt = f"""
        Claim: {claim}
        Evidence: {evidence_text}

        Classify the relationship between the evidence and the claim as
        exactly one label: SUPPORTED, PARTIALLY_SUPPORTED, CONTRADICTED, or
        UNCERTAIN. Respond with only the label, nothing else.
        """
        try:
            raw_verdict = await verify_prompt_async(prompt)
        except Exception as e:
            logger.warning("Verifier call failed for claim %r: %s", claim, e)
            raw_verdict = "UNCERTAIN"

        verdict = _parse_verdict(raw_verdict)

        return {
            "claim": claim,
            "verdict": verdict,
            "score": _VERDICT_SCORE[verdict],
            "evidence": evidence_text[:800],
            "sources": [],  # populated once citation/source metadata is wired in
        }


async def fact_check_claims(
    claims: list[str],
    max_concurrent: int = 5,
    use_web_search: bool = True,
) -> tuple[list[dict], float]:
    """Verifies all claims concurrently (bounded by max_concurrent) and
    returns (per-claim results, aggregate fact score). A single claim
    raising is not supposed to happen (verify_one_claim catches internally)
    but asyncio.gather still runs with return_exceptions=True as a final
    safety net so one unexpected bug can't 500 the whole request.
    """
    if not claims:
        return [], 1.0

    semaphore = asyncio.Semaphore(max_concurrent)
    raw_results = await asyncio.gather(
        *[_verify_one_claim(c, semaphore, use_web_search) for c in claims],
        return_exceptions=True,
    )

    results = []
    for claim, r in zip(claims, raw_results):
        if isinstance(r, Exception):
            logger.error("Unexpected error verifying claim %r: %s", claim, r)
            results.append(
                {
                    "claim": claim,
                    "verdict": "UNCERTAIN",
                    "score": _VERDICT_SCORE["UNCERTAIN"],
                    "evidence": None,
                    "sources": [],
                    "error": str(r),
                }
            )
        else:
            results.append(r)

    avg_score = sum(r["score"] for r in results) / len(results)
    return results, avg_score
