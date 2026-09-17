"""Combines module-level signals (0.0-1.0 each, higher = better/safer) into
a single risk score (0-100, higher = riskier).

IMPORTANT: DEFAULT_WEIGHTS below are HEURISTIC, chosen by intuitive
priority (fact-checking matters most, logic/citation/confidence/cross
roughly equal), NOT statistically validated against a labeled dataset.
Until an evaluation dataset exists and these are calibrated against it
(see the planned evaluation framework), treat the risk score as a
relative signal for comparing answers, not a calibrated probability of
"this answer is wrong."
"""

DEFAULT_WEIGHTS = {
    "fact": 0.35,
    "logic": 0.20,
    "citation": 0.15,
    "confidence": 0.15,
    "cross": 0.15,
}


def compute_final_score(scores: dict, weights: dict | None = None) -> int:
    weights = weights or DEFAULT_WEIGHTS

    missing = set(weights) - set(scores)
    if missing:
        raise ValueError(f"scores missing required keys: {missing}")

    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 1e-6:
        raise ValueError(f"scoring weights must sum to 1.0, got {weight_sum}")

    final = sum(weights[k] * scores[k] for k in weights)
    risk = int(round((1 - final) * 100))
    return max(0, min(100, risk))
