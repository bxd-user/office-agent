from __future__ import annotations

from typing import Any, Dict


class Critic:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def analyze_failure(self, context, step, record, verifier_result: Dict[str, Any]) -> Dict[str, Any]:
        critique = self.llm_client.critique_step_failure(
            user_prompt=context.user_prompt,
            step={
                "step_id": step.step_id,
                "title": step.title,
                "objective": step.objective,
            },
            verifier_result=verifier_result,
            memory_snapshot=context.memory.snapshot(),
        )

        if not critique:
            return {
                "action": "retry",
                "reason": "Fallback retry policy",
            }
        return critique