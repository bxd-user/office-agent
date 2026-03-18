from __future__ import annotations

from app.workflows.engine.state import WorkflowState
from app.workflows.engine.steps import WorkflowStep


class StepScheduler:
    def should_run(self, step: WorkflowStep, state: WorkflowState) -> bool:
        condition = (step.condition or "").strip()
        if not condition:
            return True

        if condition.startswith("has:"):
            key = condition.split(":", 1)[1].strip()
            return state.has(key)

        if condition.startswith("missing:"):
            key = condition.split(":", 1)[1].strip()
            return not state.has(key)

        return True
