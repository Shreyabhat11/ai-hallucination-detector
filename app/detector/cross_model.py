from app.llm.generator import generate_answer

def cross_model_score(prompt):
    a1 = generate_answer(prompt)
    a2 = generate_answer(prompt)

    if a1 == a2:
        return 1.0
    return 0.6
