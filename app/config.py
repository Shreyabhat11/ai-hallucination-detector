import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

PRIMARY_MODEL = "gemini-2.5-flash"   # fast + cheap
VERIFIER_MODEL = "gemini-2.5-flash"