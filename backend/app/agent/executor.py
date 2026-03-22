# app/agent/executor.py
from __future__ import annotations

from typing import Any, Dict, List

from app.agent.execution_state import ExecutionState
from app.agent.planner import ExecutionPlan, ToolCallStep
from app.tools.registry import ToolRegistry


class StepExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, plan: ExecutionPlan, initial_state: Dict[str, Any]) -> ExecutionState:
        state = ExecutionState()
        state.values = dict(initial_state)
        state.step_results = []

        for step in plan.steps:
            result = self._execute_step(step, state)
            record = {
                "step_id": step.step_id,
                "tool_name": step.tool_name,
                "output_key": step.output_key or step.step_id,
                "result": result,
            }
            state.step_results.append(record)

        return state

    def _execute_step(self, step: ToolCallStep, state: ExecutionState) -> Any:
        tool = self.registry.get(step.tool_name)
        resolved_args = self._resolve_value(step.args, state)
        result = tool.run(**resolved_args)

        output_key = step.output_key or step.step_id
        state.set_value(output_key, result)
        return result

    def _resolve_value(self, value: Any, state: ExecutionState) -> Any:
        if isinstance(value, dict):
            return {k: self._resolve_value(v, state) for k, v in value.items()}

        if isinstance(value, list):
            return [self._resolve_value(v, state) for v in value]

        if isinstance(value, str) and value.startswith("$"):
            return self._resolve_reference(value[1:], state)

        return value

    def _resolve_reference(self, ref: str, state: ExecutionState) -> Any:
        """
        支持两种引用：
        1. $source_text
        2. $source_text.text
        """
        if "." not in ref:
            return state.get_value(ref)

        root, *rest = ref.split(".")
        current = state.get_value(root)

        for part in rest:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                raise ValueError(f"Cannot resolve nested reference: ${ref}")

        return current