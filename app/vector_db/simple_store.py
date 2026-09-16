from app.utils.embeddings import embed
from app.utils.similarity import cosine


class SimpleVectorStore:
    def __init__(self):
        self.docs: list[str] = []
        self.vectors: list[list[float]] = []

    def add_documents(self, docs: list[str]) -> None:
        self.docs.extend(docs)
        self.vectors.extend(embed(docs))

    def query(self, text: str, k: int = 3) -> list[str]:
        if not self.docs:
            return []

        query_vec = embed([text])[0]
        if not query_vec:
            # embedding failed; degrade to "no local evidence" rather than
            # raising and taking down the whole claim check.
            return []

        sims = [(cosine(query_vec, v), d) for v, d in zip(self.vectors, self.docs)]
        sims.sort(key=lambda pair: pair[0], reverse=True)
        return [d for _, d in sims[:k]]


# global instance
store = SimpleVectorStore()
