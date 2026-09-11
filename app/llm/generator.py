from google import genai

from app.config import GEMINI_API_KEY, PRIMARY_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_answer(prompt: str) -> str:
    try:
        response = client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"LLM Error: {str(e)}"