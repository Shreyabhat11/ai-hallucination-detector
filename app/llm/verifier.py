import google.generativeai as genai
from app.config import GEMINI_API_KEY, VERIFIER_MODEL

genai.configure(api_key=GEMINI_API_KEY)

verifier_model = genai.GenerativeModel(VERIFIER_MODEL)


def verify_prompt(prompt: str) -> str:
    try:
        res = verifier_model.generate_content(prompt)
        return res.text
    except Exception:
        return "UNCERTAIN"
