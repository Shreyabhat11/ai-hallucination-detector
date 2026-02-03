from app.llm.verifier import verify_prompt

def logic_score(answer: str):
    prompt = f"""
    Does the following text contain contradictions?
    Return only: YES or NO

    {answer}
    """
    res = verify_prompt(prompt)

    if "YES" in res:
        return 0.3
    return 1.0
