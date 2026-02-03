CONFIDENT_WORDS = ["always", "never", "definitely", "guaranteed"]

def confidence_score(text: str):
    lower = text.lower()
    count = sum(w in lower for w in CONFIDENT_WORDS)

    if count > 3:
        return 0.3
    return 1.0
