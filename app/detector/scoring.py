def compute_final_score(scores: dict):

    final = (
        0.35 * scores["fact"] +
        0.20 * scores["logic"] +
        0.15 * scores["citation"] +
        0.15 * scores["confidence"] +
        0.15 * scores["cross"]
    )

    risk = int((1 - final) * 100)

    return risk
