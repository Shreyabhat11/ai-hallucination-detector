import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.detector.pipeline import run_detection
from app.llm.generator import generate_answer_async
from app.schemas.response_schema import Query
from app.vector_db.load_kb import load_default_kb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_default_kb()

app = FastAPI(title="AI Hallucination Detector", version="0.2.0")

# TODO(security phase): this is wide open (allow_origins=["*"]) to keep the
# separately-hosted Streamlit frontend working without extra config during
# this refactor. Tighten to the actual Streamlit Cloud origin before that
# phase is considered done.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.post("/ask")
async def ask(q: Query):
    request_start = time.perf_counter()

    gen_start = time.perf_counter()
    answer = await generate_answer_async(q.prompt)
    generation_ms = (time.perf_counter() - gen_start) * 1000

    report = await run_detection(q.prompt, answer, mode=q.mode)

    # fold generation timing + true end-to-end total into the pipeline's
    # latency dict rather than measuring generation separately in two places
    report["latency"]["generation_ms"] = round(generation_ms, 1)
    report["latency"]["total_ms"] = round((time.perf_counter() - request_start) * 1000, 1)

    return {"answer": answer, **report}


@app.get("/health")
def health():
    from app.vector_db.simple_store import store
    from app.utils.embeddings import cache_stats as embedding_cache_stats
    from app.utils.web_search import cache_stats as web_cache_stats

    return {
        "status": "ok",
        "kb_documents": len(store.docs),
        "embedding_cache": embedding_cache_stats(),
        "web_search_cache": web_cache_stats(),
    }
