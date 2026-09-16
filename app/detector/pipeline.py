import asyncio
import time

from app.detector.citation_check import citation_score
from app.detector.claims import extract_claims
from app.detector.confidence import confidence_score
from app.detector.cross_model import cross_model_score_async
from app.detector.fact_check import fact_check_claims
from app.detector.logic_check import logic_score_async
from app.detector.scoring import compute_final_score
from app.utils.timing import Timer

# Mode configuration. This is what "Quick / Standard / Deep" actually does,
# and it's intentionally explicit here rather than scattered across modules
# so the behavior is easy to audit and document.
MODE_CONFIG = {
    "quick": {
        "max_concurrent_claims": 8,
        "use_web_search": False,   # KB-only fact checking, no network search
        "run_logic_check": False,  # skip the extra LLM call
        "run_cross_model": False,  # skip the two extra LLM calls
    },
    "standard": {
        "max_concurrent_claims": 5,
        "use_web_search": True,
        "run_logic_check": True,
        "run_cross_model": True,
    },
    "deep": {
        "max_concurrent_claims": 3,  # lower concurrency, be gentler on rate limits
        "use_web_search": True,
        "run_logic_check": True,
        "run_cross_model": True,
    },
}


async def run_detection(prompt: str, answer: str, mode: str = "standard") -> dict:
    cfg = MODE_CONFIG.get(mode, MODE_CONFIG["standard"])
    timer = Timer()
    wall_start = time.perf_counter()

    with timer.measure("claim_extraction_ms"):
        claims = await asyncio.to_thread(extract_claims, answer)

    # Cheap, deterministic, no I/O -- no need to parallelize these with the
    # LLM/network-bound work below.
    with timer.measure("citation_ms"):
        citation = citation_score(answer)
    with timer.measure("confidence_ms"):
        confidence = confidence_score(answer)

    async def run_fact_check():
        with timer.measure("evidence_and_verification_ms"):
            # NOTE: evidence gathering and verification happen together,
            # per claim, inside fact_check_claims (parallelized across
            # claims). They're not split into separate evidence_ms /
            # verification_ms buckets because that would mean serializing
            # what is currently a single concurrent unit of work per claim
            # -- measuring them separately isn't worth giving up the
            # parallelism for.
            return await fact_check_claims(
                claims,
                max_concurrent=cfg["max_concurrent_claims"],
                use_web_search=cfg["use_web_search"],
            )

    async def run_logic():
        if not cfg["run_logic_check"]:
            return 1.0
        with timer.measure("logic_ms"):
            return await logic_score_async(answer)

    async def run_cross_model():
        if not cfg["run_cross_model"]:
            return 1.0
        with timer.measure("cross_model_ms"):
            return await cross_model_score_async(prompt)

    # These three run concurrently -- fact-checking, logic-checking, and
    # cross-model self-consistency are all independent of each other given
    # the answer text.
    (claim_reports, fact), logic, cross = await asyncio.gather(
        run_fact_check(), run_logic(), run_cross_model()
    )

    scores = {
        "fact": fact,
        "logic": logic,
        "citation": citation,
        "confidence": confidence,
        "cross": cross,
    }

    with timer.measure("scoring_ms"):
        risk = compute_final_score(scores)

    total_ms = (time.perf_counter() - wall_start) * 1000

    return {
        "risk_score": risk,
        "module_scores": scores,
        "claims": claim_reports,
        "mode": mode,
        "latency": {
            "total_ms": round(total_ms, 1),
            **timer.as_dict(),
        },
    }
