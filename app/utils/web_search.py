from duckduckgo_search import DDGS


def search_web(query: str, k: int = 3):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=k):
            results.append(r["body"])
    return "\n".join(results)