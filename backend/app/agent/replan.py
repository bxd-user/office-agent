from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.agent.prompts import REPLAN_SYSTEM_PROMPT
from app.agent.schemas.action import ActionPlan
from app.agent.schemas.plan import PlannerOutput
from app.core.llm_client import LLMClient, LLMClientError


class Replanner:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()

    def rebuild_plan(
        self,
        user_request: str,
        files: list[dict[str, Any]],
        old_plan: ActionPlan,
        execution_trace: list[dict[str, Any]],
    ) -> ActionPlan:
        if not self.llm.enabled:
            return old_plan

        payload = {
            "user_request": user_request,
            "files": files,
            "old_plan": old_plan.model_dump(),
            "execution_trace": execution_trace,
            "required_output": {
                "steps": []
            },
        }

        try:
            result = self.llm.chat_json(
                system_prompt=REPLAN_SYSTEM_PROMPT,
                user_prompt=json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                temperature=0.1,
            )
        except LLMClientError:
            return old_plan

        try:
            parsed = PlannerOutput.model_validate(result)
        except ValidationError as e:
            return old_plan

        return ActionPlan(
            steps=parsed.steps,
            metadata={
                "planner": "replanner_llm",
                "raw_output": result,
            },
        )