"""Request models for the HTTP API."""
from typing import Literal

from pydantic import BaseModel


class RunBody(BaseModel):
    id: str
    code: str | None = None       # edited source (only honoured when PREP_ALLOW_EDIT=1)


class AiBody(BaseModel):
    id: str
    mode: Literal["explain", "quiz", "break", "java", "predict", "ask"] = "explain"
    output: str = ""
    question: str = ""
    code: str | None = None
