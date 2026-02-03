from app.vector_db.simple_store import store
from app.utils.web_search import search_web
from app.llm.verifier import verify_prompt


def verify_with_evidence(claim, evidence):
    prompt = f"""
    Claim: {claim}
    Evidence: {evidence}

    Is the claim supported?
    Answer strictly: YES or NO or UNCERTAIN
    """

    res = verify_prompt(prompt)

    if "YES" in res:
        return 1.0
    if "UNCERTAIN" in res:
        return 0.5
    return 0.0


def fact_score(claims):
    scores = []

    for claim in claims:

        # local search
        kb_docs = store.query(claim, k=3)

        # web search
        web_docs = search_web(claim)

        evidence = "\n".join(kb_docs) + "\n" + web_docs

        score = verify_with_evidence(claim, evidence)
        scores.append(score)

    return sum(scores) / len(scores) if scores else 1.0
