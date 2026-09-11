from google import genai

from app.config import GEMINI_API_KEY, VERIFIER_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)


def verify_prompt(prompt: str) -> str:
    try:
        response = client.models.generate_content(
            model=VERIFIER_MODEL,
            contents=prompt
        )
        return response.text
    except Exception:
        return "UNCERTAIN"