from pydantic import BaseModel

class Query(BaseModel):
    prompt: str

class Response(BaseModel):
    answer: str
    risk_score: int
    module_scores: dict
