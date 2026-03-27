from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecutionState(BaseModel):
    current_step_id: str = ""
    status: str = "idle"
    intermediate_artifacts: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    retry_count: dict[str, int] = Field(default_factory=dict)

    def set_current_step(self, step_id: str) -> None:
        self.current_step_id = step_id
        self.status = "running"

    def add_artifact(self, name: str, value: Any) -> None:
        self.intermediate_artifacts[name] = value

    def get_artifact(self, name: str) -> Any:
        return self.intermediate_artifacts.get(name)

    def mark_failed(self, message: str) -> None:
        self.error = message
        self.status = "failed"

    def mark_completed(self) -> None:
        self.status = "completed"

    def increment_retry(self, step_id: str) -> int:
        self.retry_count[step_id] = self.retry_count.get(step_id, 0) + 1
        return self.retry_count[step_id]
