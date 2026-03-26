from __future__ import annotations

from app.agent.execution_context import ExecutionContext
from app.agent.routing.action_handler_registry import ActionHandlerRegistry
from app.agent.schemas.action import ActionObservation, ActionPlan, ActionStep


class ExecutorV2:
    def __init__(self, file_resolver) -> None:
        self.file_resolver = file_resolver
        self.handler_registry = ActionHandlerRegistry()
        self.context = ExecutionContext()
        self.trace: list[dict] = []

    def execute_step(self, step: ActionStep) -> ActionObservation:
        self._check_dependencies(step)
        handler = self.handler_registry.get_handler(step.action_type)
        observation = handler.handle(step, self.file_resolver, self.context)
        self.context.add_observation(observation)

        self.trace.append(
            {
                "step": step.model_dump(),
                "observation": observation.model_dump(),
            }
        )
        return observation

    def execute_plan(self, plan: ActionPlan) -> list[ActionObservation]:
        observations: list[ActionObservation] = []

        for step in plan.steps:
            observation = self.execute_step(step)
            observations.append(observation)

            if not observation.success and not step.allow_retry:
                break

        return observations

    def _check_dependencies(self, step: ActionStep) -> None:
        for dep in step.depends_on:
            obs = self.context.get_observation(dep)
            if obs is None:
                raise ValueError(f"Dependency not executed yet: {dep}")
            if not obs.success:
                raise ValueError(f"Dependency failed: {dep}")

    def export_context(self) -> dict:
        return self.context.export_debug_dict()

    def export_trace(self) -> list[dict]:
        return self.trace