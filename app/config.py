import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

PRIMARY_MODEL = "gemini-2.5-flash"   # fast + cheap
VERIFIER_MODEL = "gemini-3.1-flash-lite"

# --- Security / robustness settings -----------------------------------
# All overridable via env vars so the deployment's config doesn't require
# a code change.

# Comma-separated list of allowed origins for CORS. Defaults to the Vite
# dev server's origin -- deliberately NOT a wildcard. Set this to the
# actual deployed frontend URL (e.g. "https://your-frontend.vercel.app")
# via the ALLOWED_ORIGINS env var in the Render deployment's settings.
# Multiple origins: comma-separated, e.g.
#   ALLOWED_ORIGINS=http://localhost:5173,https://your-frontend.vercel.app
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5174,https://localhost:5173,https://frontend-coral-one-6cme2r1fvt.vercel.app/").split(",") if o.strip()
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
