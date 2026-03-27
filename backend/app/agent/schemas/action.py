from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DocumentRef(BaseModel):
    file_id: str
    filename: str | None = None
    role: str = "input"


class ActionStep(BaseModel):
    id: str = Field(..., description="步骤唯一 ID")
    action_type: str = Field(..., description="动作类型")
    capability: str | None = Field(default=None, description="能力标识，默认与 action_type 对齐")

    input_file_ids: list[str] = Field(default_factory=list, description="输入文件 ID 列表")
    target_file_id: str | None = Field(default=None, description="目标文件 ID")
    target_documents: list[DocumentRef] = Field(default_factory=list, description="目标文档引用")

    params: dict[str, Any] = Field(default_factory=dict, description="动作参数")
    expected_output: dict[str, Any] | None = Field(default=None, description="期望输出")

    depends_on: list[str] = Field(default_factory=list, description="依赖的前置步骤")
    allow_retry: bool = Field(default=True, description="失败后是否允许重试")


class ActionObservation(BaseModel):
    step_id: str
    success: bool
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    read_result: dict[str, Any] = Field(default_factory=dict)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    validation_result: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = None
    produced_file_ids: list[str] = Field(default_factory=list)
    error_code: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ExecutionArtifact(BaseModel):
    name: str
    type: str
    value: Any
    source_step_id: str | None = None


class ActionPlan(BaseModel):
    goal: str = ""
    allow_degraded_execution: bool = False
    requires_validation: bool = False
    input_declarations: dict[str, Any] = Field(default_factory=dict)
    output_declarations: dict[str, Any] = Field(default_factory=dict)
    steps: list[ActionStep] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionState(BaseModel):
    current_step_id: str = ""
    status: str = "idle"
    error: str | None = None
    retry_count: dict[str, int] = Field(default_factory=dict)
    intermediate_refs: dict[str, Any] = Field(default_factory=dict)
    observations: dict[str, ActionObservation] = Field(default_factory=dict)
    artifacts: dict[str, ExecutionArtifact] = Field(default_factory=dict)

    def add_observation(self, obs: ActionObservation) -> None:
        self.observations[obs.step_id] = obs

    def get_observation(self, step_id: str) -> ActionObservation | None:
        return self.observations.get(step_id)

    def set_current_step(self, step_id: str) -> None:
        self.current_step_id = step_id
        self.status = "running"

    def mark_failed(self, error: str) -> None:
        self.error = error
        self.status = "failed"

    def mark_completed(self) -> None:
        self.status = "completed"

    def increment_retry(self, step_id: str) -> int:
        self.retry_count[step_id] = self.retry_count.get(step_id, 0) + 1
        return self.retry_count[step_id]

    def add_intermediate_ref(self, name: str, value: Any) -> None:
        self.intermediate_refs[name] = value

    def add_artifact(self, artifact: ExecutionArtifact) -> None:
        self.artifacts[artifact.name] = artifact

    def get_artifact(self, name: str) -> ExecutionArtifact | None:
        return self.artifacts.get(name)