from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ActionStep(BaseModel):
    id: str = Field(..., description="步骤唯一 ID")
    action_type: str = Field(..., description="动作类型")

    input_file_ids: list[str] = Field(default_factory=list, description="输入文件 ID 列表")
    target_file_id: str | None = Field(default=None, description="目标文件 ID")

    params: dict[str, Any] = Field(default_factory=dict, description="动作参数")
    expected_output: dict[str, Any] | None = Field(default=None, description="期望输出")

    depends_on: list[str] = Field(default_factory=list, description="依赖的前置步骤")
    allow_retry: bool = Field(default=True, description="失败后是否允许重试")


class ActionObservation(BaseModel):
    step_id: str
    success: bool
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    produced_file_ids: list[str] = Field(default_factory=list)
    error_code: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ExecutionArtifact(BaseModel):
    name: str
    type: str
    value: Any
    source_step_id: str | None = None


class ActionPlan(BaseModel):
    steps: list[ActionStep] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionState(BaseModel):
    observations: dict[str, ActionObservation] = Field(default_factory=dict)
    artifacts: dict[str, ExecutionArtifact] = Field(default_factory=dict)

    def add_observation(self, obs: ActionObservation) -> None:
        self.observations[obs.step_id] = obs

    def get_observation(self, step_id: str) -> ActionObservation | None:
        return self.observations.get(step_id)

    def add_artifact(self, artifact: ExecutionArtifact) -> None:
        self.artifacts[artifact.name] = artifact

    def get_artifact(self, name: str) -> ExecutionArtifact | None:
        return self.artifacts.get(name)