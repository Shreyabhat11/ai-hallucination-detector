import asyncio
import logging
import json

from app.llm.verifier import verify_prompt_async
from app.utils.prompt_safety import VERIFICATION_SYSTEM_INSTRUCTION, wrap_untrusted
from app.utils.web_search import search_web_async
from app.vector_db.simple_store import store

logger = logging.getLogger(__name__)

VERDICTS = (
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "CONTRADICTED",
    "UNCERTAIN",
    "NO_RELEVANT_EVIDENCE",
    "INSUFFICIENT_EVIDENCE",
)

_VERDICT_SCORE = {
    "SUPPORTED": 1.0,
    "PARTIALLY_SUPPORTED": 0.6,
    "UNCERTAIN": 0.5,
    "CONTRADICTED": 0.0,
    "NO_RELEVANT_EVIDENCE": 0.5,
    "INSUFFICIENT_EVIDENCE": 0.5,
}

def _parse_verdict(raw: str) -> str:
    upper = (raw or "").upper()

    for label in VERDICTS:
        if label in upper:
            return label

    return "UNCERTAIN"

def _parse_verification_response(raw: str) -> tuple[str, list[int]]:
    try:
        data = json.loads(raw)

        verdict = _parse_verdict(data.get("verdict", ""))
        candidates = data.get("relevant_candidates", [])

        if not isinstance(candidates, list):
            candidates = []

        valid_candidates = [
            int(index)
            for index in candidates
            if isinstance(index, int) and index >= 1
        ]

        return verdict, valid_candidates

    except (json.JSONDecodeError, TypeError, ValueError):
        # Preserve compatibility with the old plain-label verifier response.
        return _parse_verdict(raw), None
    
async def _verify_one_claim(
    claim: str,
    semaphore: asyncio.Semaphore,
    use_web_search: bool,
) -> dict:
    async with semaphore:

        async def kb_lookup():
            try:
                return await asyncio.to_thread(store.query, claim, 3)
            except Exception as e:
                logger.warning("KB lookup failed for claim %r: %s", claim, e)
                return []

        async def web_lookup():
            if not use_web_search:
                return []
            try:
                return await search_web_async(claim)
            except Exception as e:
                logger.warning("Web search failed for claim %r: %s", claim, e)
                return []

        kb_docs, web_results = await asyncio.gather(
            kb_lookup(),
            web_lookup(),
        )

        # No retrieval results at all.
        if not kb_docs and not web_results:
            return {
                "claim": claim,
                "verdict": "INSUFFICIENT_EVIDENCE",
                "score": _VERDICT_SCORE["INSUFFICIENT_EVIDENCE"],
                "evidence": None,
                "sources": [],
            }

        # Keep local KB and web results clearly separated.
        candidates = []
        sources = []

        for similarity, doc in kb_docs:
            candidates.append(
                {
                    "content": doc,
                    "source": "LOCAL KNOWLEDGE BASE",
                    "title": None,
                    "url": None,
                }
            )

        for r in web_results:
            title = r.get("title", "")
            url = r.get("url", "")
            body = r.get("body", "")

            if not body:
                continue

            candidate_index = len(candidates) + 1

            candidates.append(
                {
                    "content": body,
                    "source": "WEB SOURCE",
                    "title": title,
                    "url": url,
                }
            )

            sources.append(
                {
                    "title": title,
                    "url": url,
                }
            )
        evidence_parts = []

        for index, candidate in enumerate(candidates, start=1):
            if candidate["source"] == "LOCAL KNOWLEDGE BASE":
                evidence_parts.append(
                    f"""[CANDIDATE {index}]
        LOCAL KNOWLEDGE BASE
        Content: {candidate["content"]}"""
                )
            else:
                evidence_parts.append(
                    f"""[CANDIDATE {index}]
        WEB SOURCE
        Title: {candidate["title"]}
        URL: {candidate["url"]}
        Content: {candidate["content"]}"""
                )

        evidence_text = "\n\n".join(evidence_parts).strip()
                

        if not evidence_text:
            return {
                "claim": claim,
                "verdict": "INSUFFICIENT_EVIDENCE",
                "score": _VERDICT_SCORE["INSUFFICIENT_EVIDENCE"],
                "evidence": None,
                "sources": [],
            }

        prompt = f"""
Claim:
{wrap_untrusted(claim)}

Candidate evidence:

{wrap_untrusted(evidence_text)}

Assess the candidate evidence carefully.

Determine whether at least one candidate actually addresses the claim.

Use exactly one label:

SUPPORTED
- At least one candidate directly supports the claim.

PARTIALLY_SUPPORTED
- Relevant evidence supports only part of the claim or leaves an important
  part unverified.

CONTRADICTED
- Relevant evidence directly conflicts with the claim.

UNCERTAIN
- Relevant evidence addresses the claim, but it is insufficient or ambiguous
  to determine whether the claim is true.

NO_RELEVANT_EVIDENCE
- Candidate material exists, but none of it actually addresses the claim.
- Do not treat merely similar words or unrelated facts as relevant evidence.

Important:
- Do not infer support from the topic alone.
- Do not treat unrelated local knowledge-base documents as evidence.
- Evaluate the actual content of each candidate.
Return valid JSON only, using exactly this structure:

{{
  "verdict": "SUPPORTED",
  "relevant_candidates": [1]
}}

Rules:
- "verdict" must be exactly one of:
  SUPPORTED
  PARTIALLY_SUPPORTED
  CONTRADICTED
  UNCERTAIN
  NO_RELEVANT_EVIDENCE
- "relevant_candidates" must contain the 1-based candidate numbers
  that actually address the claim.
- Include only candidates that are relevant to the claim.
- If no candidate is relevant, return an empty list.
- Return JSON only. No markdown or explanation.
"""

        try:
            raw_verdict = await verify_prompt_async(
                prompt,
                system_instruction=VERIFICATION_SYSTEM_INSTRUCTION,
            )
        except Exception as e:
            logger.warning("Verifier call failed for claim %r: %s", claim, e)
            raw_verdict = "UNCERTAIN"

        verdict, relevant_candidates = _parse_verification_response(raw_verdict)

        if relevant_candidates is None:
            relevant_candidates = list(range(1, len(candidates) + 1))
            
        if verdict == "NO_RELEVANT_EVIDENCE" or not relevant_candidates:
            return {
                "claim": claim,
                "verdict": verdict,
                "score": _VERDICT_SCORE[verdict],
                "evidence": None,
                "sources": [],
            }

        selected_candidates = [
            candidates[index - 1]
            for index in relevant_candidates
            if 1 <= index <= len(candidates)
        ]

        if not selected_candidates:
            return {
                "claim": claim,
                "verdict": "NO_RELEVANT_EVIDENCE",
                "score": _VERDICT_SCORE["NO_RELEVANT_EVIDENCE"],
                "evidence": None,
                "sources": [],
            }

        selected_evidence = "\n\n".join(
            candidate["content"]
            for candidate in selected_candidates
        )

        selected_sources = [
            {
                "title": candidate["title"],
                "url": candidate["url"],
            }
            for candidate in selected_candidates
            if candidate["url"]
        ]

        return {
            "claim": claim,
            "verdict": verdict,
            "score": _VERDICT_SCORE[verdict],
            "evidence": selected_evidence[:800],
            "sources": selected_sources,
        }

async def fact_check_claims(
    claims: list[str],
    max_concurrent: int = 5,
    use_web_search: bool = True,
) -> tuple[list[dict], float]:
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
