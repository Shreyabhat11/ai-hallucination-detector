from app.detector.claims import extract_claims
from app.detector.fact_check import fact_score
from app.detector.logic_check import logic_score
from app.detector.citation_check import citation_score
from app.detector.confidence import confidence_score
from app.detector.cross_model import cross_model_score
from app.detector.scoring import compute_final_score


def run_detection(prompt, answer):

    claims = extract_claims(answer)

    scores = {
        "fact": fact_score(claims),
        "logic": logic_score(answer),
        "citation": citation_score(answer),
        "confidence": confidence_score(answer),
        "cross": cross_model_score(prompt)
    }

    risk = compute_final_score(scores)

    return {
        "risk_score": risk,
        "module_scores": scores,
        "claims": claims
    }
