from unittest.mock import patch

from app.detector.claims import extract_claims


def test_empty_answer_returns_no_claims():
    assert extract_claims("") == []
    assert extract_claims("   ") == []


def test_llm_error_answer_returns_no_claims():
    assert extract_claims("LLM Error: generation timed out") == []


@patch("app.detector.claims.verify_prompt")
def test_strips_numbering_and_bullets(mock_verify):
    mock_verify.return_value = (
        "1. The Eiffel Tower was completed in 1889.\n"
        "- It is 330 meters tall.\n"
        "* Paris is the capital of France.\n"
    )
    claims = extract_claims("some multi-fact answer")
    assert claims == [
        "The Eiffel Tower was completed in 1889.",
        "It is 330 meters tall.",
        "Paris is the capital of France.",
    ]


@patch("app.detector.claims.verify_prompt")
def test_blank_verifier_response_returns_no_claims(mock_verify):
    mock_verify.return_value = ""
    assert extract_claims("some answer") == []
