from __future__ import annotations
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    context: dict = Field(default_factory=dict)
    conversation_id: str | None = None
    history: list[dict] = Field(default_factory=list)
