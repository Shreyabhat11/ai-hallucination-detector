import google.generativeai as genai
from app.config import GEMINI_API_KEY, PRIMARY_MODEL

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(PRIMARY_MODEL)


def generate_answer(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"LLM Error: {str(e)}"
