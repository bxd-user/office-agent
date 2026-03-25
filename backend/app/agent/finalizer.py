from __future__ import annotations

from typing import Any, Dict


class Finalizer:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def build_final_answer(self, context) -> str:
        answer = self.llm_client.finalize_response(
            user_prompt=context.user_prompt,
            plan=self._serialize_plan(context.plan),
            memory_snapshot=context.memory.snapshot(),
            step_records=[self._serialize_record(r) for r in context.step_records],
        )
        if answer:
            return answer

        if context.memory.output_files:
            return "任务已完成，并已生成输出文件。"
        return "任务已执行完成。"

    def _serialize_plan(self, plan):
        if plan is None:
            return None
        return {
            "goal": plan.goal,
            "task_type": plan.task_type,
            "file_roles": [vars(fr) for fr in plan.file_roles],
            "steps": [vars(s) for s in plan.steps],
            "success_criteria": plan.success_criteria,
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