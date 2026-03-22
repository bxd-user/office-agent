# app/agent/planner.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError


class ToolCallStep(BaseModel):
    step_id: str
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    depends_on: List[str] = Field(default_factory=list)
    output_key: Optional[str] = None


class ExecutionPlan(BaseModel):
    goal: str
    steps: List[ToolCallStep] = Field(default_factory=list)


class PlannerContext(BaseModel):
    user_prompt: str
    files: List[Dict[str, Any]] = Field(default_factory=list)
    available_tools: List[Dict[str, Any]] = Field(default_factory=list)


class WorkflowPlanner:
    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    def create_plan(self, context: PlannerContext) -> ExecutionPlan:
        raw = self.llm.generate_tool_plan(
            user_prompt=context.user_prompt,
            files=context.files,
            available_tools=context.available_tools,
        )
        plan = self._parse_plan(raw)
        self._validate_plan(plan, context.available_tools)
        return plan

    def _parse_plan(self, raw: str) -> ExecutionPlan:
        try:
            data = json.loads(raw)
            return ExecutionPlan.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Invalid tool plan from LLM: {e}") from e

    def _validate_plan(
        self,
        plan: ExecutionPlan,
        available_tools: List[Dict[str, Any]],
    ) -> None:
        tool_names = {tool["name"] for tool in available_tools}

        if not plan.steps:
            raise ValueError("Plan contains no steps")

        seen_ids = set()
        for step in plan.steps:
            if step.step_id in seen_ids:
                raise ValueError(f"Duplicate step_id: {step.step_id}")
            seen_ids.add(step.step_id)

            if step.tool_name not in tool_names:
                raise ValueError(f"Unknown tool in plan: {step.tool_name}")

            for dep in step.depends_on:
                if dep not in seen_ids and dep not in {s.step_id for s in plan.steps}:
                    raise ValueError(f"Unknown depends_on step: {dep}")