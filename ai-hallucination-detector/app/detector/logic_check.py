from app.llm.verifier import verify_prompt, verify_prompt_async
from app.utils.prompt_safety import VERIFICATION_SYSTEM_INSTRUCTION, wrap_untrusted

_PROMPT_TEMPLATE = """
Does the following text contain internal contradictions?
Return only: YES or NO

{answer}
"""


def logic_score(answer: str) -> float:
    prompt = _PROMPT_TEMPLATE.format(answer=wrap_untrusted(answer))
    res = verify_prompt(prompt, system_instruction=VERIFICATION_SYSTEM_INSTRUCTION)
    return 0.3 if "YES" in res.upper() else 1.0


async def logic_score_async(answer: str) -> float:
    prompt = _PROMPT_TEMPLATE.format(answer=wrap_untrusted(answer))
    res = await verify_prompt_async(prompt, system_instruction=VERIFICATION_SYSTEM_INSTRUCTION)
    return 0.3 if "YES" in res.upper() else 1.0
