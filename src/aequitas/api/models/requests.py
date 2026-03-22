from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    context: dict = Field(default_factory=dict)
    conversation_id: str | None = None
    history: list[HistoryMessage] = Field(default_factory=list)
