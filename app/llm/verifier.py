import asyncio
import logging

from google import genai

from app.config import GEMINI_API_KEY, VERIFIER_MODEL

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)

DEFAULT_TIMEOUT_S = 15.0


def verify_prompt(prompt: str) -> str:
    try:
        response = client.models.generate_content(model=VERIFIER_MODEL, contents=prompt)
        return response.text or ""
    except Exception as e:
        logger.warning("verify_prompt failed: %s", e)
        return "UNCERTAIN"


async def verify_prompt_async(prompt: str, timeout: float = DEFAULT_TIMEOUT_S) -> str:
    try:
        return await asyncio.wait_for(asyncio.to_thread(verify_prompt, prompt), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("verify_prompt_async timed out after %.1fs", timeout)
        return "UNCERTAIN"
