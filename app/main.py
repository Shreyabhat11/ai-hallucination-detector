from fastapi import FastAPI
from app.schemas.response_schema import Query
from app.llm.generator import generate_answer
from app.detector.pipeline import run_detection
from app.vector_db.load_kb import load_default_kb

load_default_kb()

app = FastAPI()

@app.post("/ask")
def ask(q: Query):
    answer = generate_answer(q.prompt)
    report = run_detection(q.prompt, answer)

    return {
        "answer": answer,
        **report
    }
