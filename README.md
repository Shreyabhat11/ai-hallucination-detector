# AI Hallucination Detector

Fact-checks AI-generated answers at the claim level: it takes a question,
generates an answer with Gemini, breaks that answer into individual factual
claims, checks each one against evidence (a small local knowledge base and
live web search), and reports a risk score with an explainable breakdown of
what was checked and why.

## Architecture

```
React/Vite frontend  --(HTTPS, JSON)-->  FastAPI backend  -->  Gemini
     (frontend/)                            (this repo)        + web search (DDGS)
                                                  |
                                         claim extraction
                                         fact verification (parallel, per claim)
                                         logic / citation / confidence checks
                                         self-consistency check
                                                  |
                                            risk scoring
```

- **Backend**: FastAPI, deployed on Render. Single endpoint (`POST /ask`)
  takes a prompt, generates an answer via Gemini, and runs it through a
  parallelized verification pipeline. See "How it works" below.
- **Frontend**: React + TypeScript + Vite + Tailwind, in `frontend/`. A
  standalone dashboard that calls the backend's API — it has no server-side
  logic of its own. Deployed separately (e.g. Vercel/Netlify).
- **Legacy**: `streamlit_app.py` is the original UI, superseded by the
  React frontend. Kept for reference; not part of the current deployment
  and not installed by `requirements.txt` (see "Legacy Streamlit UI" below).

## How it works

1. **Generate** — the submitted prompt goes to Gemini, which produces an answer.
2. **Extract claims** — the answer is broken into individual factual statements.
3. **Verify** — each claim is checked concurrently (bounded parallelism) against:
   - a small local knowledge base (embedding similarity)
   - live web search results
   - an LLM verifier call, given that evidence
   Each claim gets one of: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONTRADICTED`,
   `UNCERTAIN`, or `INSUFFICIENT_EVIDENCE` (used when no evidence was found
   at all — distinct from a claim being judged false).
4. **Other signals**, run concurrently with claim verification:
   - **Logic check** — does the answer contradict itself?
   - **Citation check** — for URL citations, is the source actually
     reachable? (Reachable ≠ proves the claim — just that it exists and
     responds.) Bare `[1]`/`(Author, Year)` references with no URL are
     honestly labeled `NO_SOURCE` rather than guessed at.
   - **Confidence language** — a density-normalized heuristic comparing
     certainty language ("always", "definitely") against hedging language
     ("might", "possibly"), not a simple keyword count.
   - **Self-consistency** — asks the same model the same prompt twice and
     compares outputs. This is explicitly *not* genuine cross-model
     verification (it's one model checked against itself), and the code
     and API are honest about that rather than overselling it.
5. **Score** — the signals above combine into a 0-100 risk score using
   heuristic weights (see `app/detector/scoring.py`) — not a statistically
   calibrated probability. Labeled as such throughout.

### Analysis modes

| Mode | Web search | Logic check | Self-consistency check | Claim concurrency |
|---|---|---|---|---|
| Quick | No (KB only) | Skipped | Skipped | 8 |
| Standard | Yes | Yes | Yes | 5 |
| Deep | Yes | Yes | Yes | 3 (gentler on rate limits) |

## Setup

### Backend

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` in the project root:

```
GEMINI_API_KEY=your_api_key_here
```

Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey).

Run it:

```bash
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API docs.

Relevant backend env vars (all optional, see `app/config.py` for defaults):

| Variable | Purpose | Default |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API key | — (required) |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowlist | `http://localhost:5173` |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | Per-IP rate limit on `/ask` | 20 requests / 60s |
| `MAX_REQUEST_BODY_BYTES` | Reject larger request bodies | 50 KB |
| `REQUEST_TIMEOUT_SECONDS` | Hard ceiling on total request processing | 60s |

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# edit .env: set VITE_API_URL to your backend's URL
npm run dev
```

Opens on `http://localhost:5173`. Full details (env vars, build, deploy) in
`frontend/README.md`.

**Important**: the backend's `ALLOWED_ORIGINS` must include whatever origin
the frontend is actually running on, or the browser will block the request
via CORS. The defaults above match each other for local dev
(`localhost:5173`), but a deployed frontend URL must be added explicitly.

### Running both together locally

```bash
# terminal 1
uvicorn main:app --reload
# terminal 2
cd frontend && npm run dev
```

## API

**`POST /ask`**

```json
// request
{ "prompt": "When was the Eiffel Tower built?", "mode": "standard" }
```

```json
// response (200) -- shape simplified, see app/schemas/response_schema.py
// and app/detector/pipeline.py for the exact fields
{
  "answer": "...",
  "risk_score": 12,
  "module_scores": { "fact": 0.9, "logic": 1.0, "citation": 0.5, "confidence": 0.8, "cross": 1.0 },
  "claims": [{ "claim": "...", "verdict": "SUPPORTED", "score": 1.0, "evidence": "...", "sources": [...] }],
  "citations": [{ "type": "url", "text": "...", "verdict": "SUPPORTED" }],
  "mode": "standard",
  "latency": { "total_ms": 4200, "generation_ms": 600, "claim_extraction_ms": 400, "..." : "..." }
}
```

`logic_ms` / `cross_model_ms` are **absent** (not zero) in Quick mode, since
those stages are skipped entirely.

Errors: `422` (invalid input), `413` (body too large), `429` (rate
limited, with `Retry-After` header), `500` (generic — no stack traces are
ever returned to the client), `504` (request timed out).

**`GET /health`** → `{"status": "ok", "kb_documents": N, "embedding_cache": {...}, "web_search_cache": {...}}`

## Testing

```bash
# backend
pip install -r requirements.txt   # includes pytest, pytest-asyncio, httpx
pytest -v

# frontend
cd frontend
npm run build   # type-check + production build
npm run lint    # oxlint
npm run test    # vitest
```

Backend tests mock all LLM/web-search calls (no live network needed).
Frontend tests cover the API client's error normalization and display
logic with a mocked `fetch` (no live backend needed).

## Legacy Streamlit UI

`streamlit_app.py` predates the React frontend and is not part of the
current deployment. It's kept only for reference. To run it, install its
dependency separately (it's intentionally not in `requirements.txt`
anymore, since the backend itself never imports `streamlit`):

```bash
pip install streamlit
streamlit run streamlit_app.py
```

## Limitations

- **Risk scores are heuristic, not calibrated.** No evaluation dataset or
  precision/recall/F1 numbers exist yet for this project. Treat the risk
  score as a relative signal for comparing answers, not a validated
  probability.
- **"Self-consistency" is not cross-model verification.** It checks one
  model against itself twice, not against an independent model.
- **Prompt-injection defenses are a mitigation, not a guarantee** (see
  `app/utils/prompt_safety.py`). There is no complete client-side defense
  against prompt injection with current LLMs.
- **Rate limiting and caching are in-process only** — correct for a
  single-instance deployment, not correct across multiple workers/instances
  without a shared store (deliberately not added, to keep this deployable
  cheaply).
- Citation checking verifies that a URL is *reachable*, not that it
  actually supports the claim it's attached to.

## Tech stack

Backend: Python, FastAPI, Gemini (`google-genai`), DDGS web search, NumPy
(cosine similarity), an in-process TTL cache, pytest.
Frontend: React, TypeScript, Vite, Tailwind CSS, vitest.

## Future improvements

- Real evaluation dataset + precision/recall/F1/calibration
- User-provided knowledge base (upload PDF/TXT/DOCX for claim retrieval)
- Batch evaluation (CSV of multiple answers → metrics dashboard)
- CI (GitHub Actions running both test suites on push)
