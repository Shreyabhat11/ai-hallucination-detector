import re

from app.llm.verifier import verify_prompt
from app.utils.prompt_safety import VERIFICATION_SYSTEM_INSTRUCTION, wrap_untrusted

_LIST_MARKER_RE = re.compile(r"^(\d+[\.\)]\s*|[-*•]\s*)")


def _strip_list_marker(line: str) -> str:
    return _LIST_MARKER_RE.sub("", line).strip()


def extract_claims(answer: str) -> list[str]:
    if not answer or not answer.strip():
        return []

    if answer.startswith("LLM Error"):
        # generation itself failed; there's nothing factual to extract from
        # an error string.
        return []

    prompt = f"""
    Break the following text into independent factual claims.
    Return each claim on its own line with no numbering, bullets, or extra
    commentary.

    Text:
    {wrap_untrusted(answer)}
    """
    result = verify_prompt(prompt, system_instruction=VERIFICATION_SYSTEM_INSTRUCTION)
    if not result or not result.strip():
        return []

    lines = [line.strip() for line in result.split("\n") if line.strip()]
    claims = [_strip_list_marker(line) for line in lines]
    return [c for c in claims if c]
