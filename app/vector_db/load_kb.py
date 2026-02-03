from app.vector_db.simple_store import store

def load_default_kb():
    docs = [
        "The Eiffel Tower is 330 meters tall.",
        "The Eiffel Tower was completed in 1889.",
        "Python was created by Guido van Rossum.",
        "FastAPI is a Python web framework."
    ]

    store.add_documents(docs)
    print("Default knowledge base loaded with sample documents.")