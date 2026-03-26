from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    user_request: str
    files: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: dict[str, Any] = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    success: bool
    answer: str = ""
    result: dict[str, Any]