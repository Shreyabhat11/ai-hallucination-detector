import asyncio
import logging

from ddgs import DDGS

from app.utils.cache import TTLCache

logger = logging.getLogger(__name__)

# Web results change over time, so a shorter TTL than embeddings.
_cache = TTLCache(maxsize=512, ttl=600.0)

DEFAULT_TIMEOUT_S = 8.0


def search_web(query: str, k: int = 3) -> list[dict]:
    """Returns up to k results as [{"title": ..., "url": ..., "body": ...}].
    An empty list means "no results / search failed" -- callers must treat
    that as "no evidence found", never as "claim is false".
    """
    cached = _cache.get(query)
    if cached is not None:
        return cached

    results: list[dict] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=k):
                body = r.get("body", "")
                if not body:
                    continue
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "body": body,
                    }
                )
    except Exception as e:
        logger.warning("search_web failed for %r: %s", query, e)
        return []

    _cache.set(query, results)
    return results


async def search_web_async(query: str, k: int = 3, timeout: float = DEFAULT_TIMEOUT_S) -> list[dict]:
    try:
        return await asyncio.wait_for(asyncio.to_thread(search_web, query, k), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("search_web_async timed out after %.1fs for %r", timeout, query)
        return []


def cache_stats() -> dict:
    return _cache.stats()
