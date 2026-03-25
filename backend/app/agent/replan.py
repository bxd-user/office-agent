from __future__ import annotations

from app.agent.plan_models import ExecutionPlan, PlanStep


class Replanner:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def replan(self, context) -> ExecutionPlan | None:
        if context.replan_count >= context.max_replans:
            return None

        replanned = self.llm_client.replan_task(
            user_prompt=context.user_prompt,
            current_plan=self._serialize_plan(context.plan),
            memory_snapshot=context.memory.snapshot(),
            step_records=[self._serialize_record(r) for r in context.step_records],
        )
        if not replanned:
            return None

        context.replan_count += 1
        return replanned

    def _serialize_plan(self, plan):
        if plan is None:
            return None
        return {
            "goal": plan.goal,
            "task_type": plan.task_type,
            "file_roles": [vars(fr) for fr in plan.file_roles],
            "steps": [vars(s) for s in plan.steps],
            "success_criteria": plan.success_criteria,
            "assumptions": plan.assumptions,
            "requires_output_file": plan.requires_output_file,
        }

    def _serialize_record(self, record):
        return {
            "step_id": record.step_id,
            "tool_calls": record.tool_calls,
            "outputs": record.outputs,
            "success": record.success,
            "error": record.error,
            "verifier_result": record.verifier_result,
        }