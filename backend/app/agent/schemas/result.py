from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRunResult(BaseModel):
    text_result: str = ""
    structured_result: dict[str, Any] = Field(default_factory=dict)
    generated_files: list[dict[str, Any]] = Field(default_factory=list)
    execution_logs: list[dict[str, Any]] = Field(default_factory=list)
    validation_status: dict[str, Any] = Field(default_factory=dict)

    success: bool = True
    summary: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_legacy(cls, payload: dict[str, Any]) -> "AgentRunResult":
        return cls(
            text_result=payload.get("answer", ""),
            generated_files=payload.get("output_files", []),
            execution_logs=payload.get("tool_trace", []),
            raw=payload.get("raw", {}),
            success=bool(payload.get("success", True)),
        )


__all__ = ["AgentRunResult"]
