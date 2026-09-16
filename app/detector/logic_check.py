from app.llm.verifier import verify_prompt, verify_prompt_async

_PROMPT_TEMPLATE = """
Does the following text contain internal contradictions?
Return only: YES or NO

{answer}
"""


def logic_score(answer: str) -> float:
    res = verify_prompt(_PROMPT_TEMPLATE.format(answer=answer))
    return 0.3 if "YES" in res.upper() else 1.0


async def logic_score_async(answer: str) -> float:
    res = await verify_prompt_async(_PROMPT_TEMPLATE.format(answer=answer))
    return 0.3 if "YES" in res.upper() else 1.0
