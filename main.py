import asyncio
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import (
    ALLOWED_ORIGINS,
    MAX_REQUEST_BODY_BYTES,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
)
from app.detector.pipeline import run_detection
from app.llm.generator import generate_answer_async
from app.schemas.response_schema import Query
from app.utils.rate_limit import SlidingWindowRateLimiter
from app.vector_db.load_kb import load_default_kb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_default_kb()

app = FastAPI(title="AI Hallucination Detector", version="0.3.0")

# CORS: restricted to ALLOWED_ORIGINS (see app/config.py), not a wildcard.
# Set ALLOWED_ORIGINS in the deployment environment to the real deployed
# frontend URL (e.g. Vercel/Netlify).
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_rate_limiter = SlidingWindowRateLimiter(
    max_requests=RATE_LIMIT_REQUESTS, window_seconds=RATE_LIMIT_WINDOW_SECONDS
)


def _client_key(request: Request) -> str:
    # Render sits behind a proxy; prefer the forwarded client IP when present.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def request_guards(request: Request, call_next):
    """Applies, in order: request-size limit, rate limiting, and an overall
    request timeout. Kept as one middleware so the ordering (cheapest check
    first) is explicit and easy to audit.
    """
    # 1. Reject oversized bodies before they're read into memory.
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"error": "request body too large"},
                )
        except ValueError:
            pass  # malformed header; let normal parsing surface the problem

    # 2. Rate limit per client, only on the actual analysis endpoint --
    # health checks and docs shouldn't count against the budget.
    if request.url.path == "/ask":
        client_key = _client_key(request)
        allowed, retry_after = _rate_limiter.check(client_key)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "rate limit exceeded, please slow down"},
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

    # 3. Overall timeout so a hang anywhere (including something not
    # covered by the per-call timeouts deeper in the pipeline) can't hold a
    # worker forever.
    try:
        return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.warning("Request to %s timed out after %.0fs", request.url.path, REQUEST_TIMEOUT_SECONDS)
        return JSONResponse(status_code=504, content={"error": "request timed out"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Full detail goes to the server log only -- never back to the client.
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": "internal server error"})


@app.post("/ask")
async def ask(q: Query):
    request_start = time.perf_counter()

    gen_start = time.perf_counter()
    answer = await generate_answer_async(q.prompt)
    generation_ms = (time.perf_counter() - gen_start) * 1000

    report = await run_detection(q.prompt, answer, mode=q.mode)

    report["latency"]["generation_ms"] = round(generation_ms, 1)
    report["latency"]["total_ms"] = round((time.perf_counter() - request_start) * 1000, 1)

    return {"answer": answer, **report}


@app.get("/health")
def health():
    from app.utils.embeddings import cache_stats as embedding_cache_stats
    from app.utils.web_search import cache_stats as web_cache_stats
    from app.vector_db.simple_store import store

    return {
        "status": "ok",
        "kb_documents": len(store.docs),
        "embedding_cache": embedding_cache_stats(),
        "web_search_cache": web_cache_stats(),
    }
