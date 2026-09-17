import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

PRIMARY_MODEL = "gemini-2.5-flash"   # fast + cheap
VERIFIER_MODEL = "gemini-2.5-flash"

# --- Security / robustness settings -----------------------------------
# All overridable via env vars so Render/Streamlit Cloud config doesn't
# require a code change.

# Comma-separated list of allowed origins for CORS. Defaults to localhost
# only -- deliberately NOT a wildcard. Set this to the actual Streamlit
# Cloud URL (e.g. "https://your-app.streamlit.app") in the deployment's
# environment variables.
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",") if o.strip()
]

# Sliding-window rate limit: N requests per WINDOW_SECONDS per client IP.
# In-process only (see app/utils/rate_limit.py) -- resets on restart, not
# shared across multiple workers/instances. Acceptable for a single-instance
# portfolio deployment; would need a shared store (e.g. Redis) to be correct
# behind multiple workers, which is intentionally not introduced here.
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
RATE_LIMIT_WINDOW_SECONDS = float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

# Reject request bodies larger than this before they're parsed.
MAX_REQUEST_BODY_BYTES = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(50 * 1024)))  # 50 KB

# Hard ceiling on total request processing time (generation + full
# pipeline). Prevents a pathological Deep-mode request (or an upstream
# hang not caught by the per-call timeouts) from holding a worker forever.
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))
