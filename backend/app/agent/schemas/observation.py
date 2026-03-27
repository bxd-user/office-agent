from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Observation(BaseModel):
    step_id: str = ""
    source: str = ""
    success: bool = True
    message: str = ""

    read_result: dict[str, Any] = Field(default_factory=dict)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    validation_result: dict[str, Any] = Field(default_factory=dict)

    content: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = None
    error: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
