import re

def citation_score(answer: str):
    citations = re.findall(r'\[\d+\]|\(.*?\d{4}.*?\)', answer)

    if not citations:
        return 0.5   # neutral

    # naive: assume citations suspicious
    return 0.3
