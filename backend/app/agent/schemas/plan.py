from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.schemas.action import ActionStep


class FileRole(BaseModel):
    file_id: str
    filename: str
    role: str = "unknown"
    reason: str = ""


class PlanStep(BaseModel):
    step_id: str
    title: str
    objective: str
    suggested_tools: list[str] = Field(default_factory=list)
    inputs: dict = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list)
    status: str = "pending"
    notes: str = ""


class StepExecutionRecord(BaseModel):
    step_id: str
    tool_calls: list[dict] = Field(default_factory=list)
    outputs: dict = Field(default_factory=dict)
    success: bool = False
    error: str | None = None
    verifier_result: dict | None = None


class ExecutionPlan(BaseModel):
    goal: str = ""
    task_type: str = "unknown"
    file_roles: list[FileRole] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    requires_output_file: bool = False


class PlannerOutput(BaseModel):
    steps: list[ActionStep] = Field(default_factory=list)