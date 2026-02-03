from app.llm.verifier import verify_prompt

def extract_claims(answer: str):
    prompt = f"""
    Break the following text into independent factual claims.
    Return each claim on a new line.

    Text:
    {answer}
    """
    result = verify_prompt(prompt)
    claims = [c.strip() for c in result.split("\n") if c.strip()]
    return claims
