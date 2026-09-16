from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_PROMPT_CHARS = 4000


class Query(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_CHARS)
    mode: Literal["quick", "standard", "deep"] = "standard"

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("prompt must not be blank")
        return stripped
