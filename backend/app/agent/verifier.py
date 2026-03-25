from __future__ import annotations

from typing import Any, Dict

from app.agent.plan_models import PlanStep, StepExecutionRecord


class Verifier:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def verify_step(self, context, step: PlanStep, record: StepExecutionRecord) -> Dict[str, Any]:
        if not record.success:
            return {
                "passed": False,
                "reason": record.error or "Step execution failed",
                "missing": [],
            }

        verification = self.llm_client.verify_step(
            user_prompt=context.user_prompt,
            plan_goal=context.plan.goal if context.plan else "",
            current_step={
                "step_id": step.step_id,
                "title": step.title,
                "objective": step.objective,
                "expected_outputs": step.expected_outputs,
            },
            step_record={
                "tool_calls": record.tool_calls,
                "outputs": record.outputs,
            },
            memory_snapshot=context.memory.snapshot(),
        )

        if not verification:
            return {
                "passed": True,
                "reason": "No verifier response; default pass",
                "missing": [],
            }

        return verification