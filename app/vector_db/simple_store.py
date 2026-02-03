from app.utils.embeddings import embed
from app.utils.similarity import cosine

class SimpleVectorStore:
    def __init__(self):
        self.docs = []
        self.vectors = []

    def add_documents(self, docs):
        self.docs.extend(docs)
        self.vectors.extend(embed(docs))

    def query(self, text, k=3):
        query_vec = embed([text])[0]

        sims = [
            (cosine(query_vec, v), d)
            for v, d in zip(self.vectors, self.docs)
        ]

        sims.sort(reverse=True)
        return [d for _, d in sims[:k]]


# global instance
store = SimpleVectorStore()
