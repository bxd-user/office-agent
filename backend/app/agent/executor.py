from __future__ import annotations

from typing import Any

from app.agent.execution_context import ExecutionContext
from app.agent.routing.action_handler_registry import ActionHandlerRegistry
from app.agent.routing.capability_resolver import CapabilityResolver
from app.agent.schemas.action import ActionObservation, ActionPlan, ActionStep
from app.agent.schemas.plan import StepExecutionRecord


FAILURE_RETRYABLE = "retryable"
FAILURE_REPLANNABLE = "replannable"
FAILURE_NON_RECOVERABLE = "non_recoverable"


class Executor:
    def __init__(self, file_resolver, max_step_retries: int = 1) -> None:
        self.file_resolver = file_resolver
        self.max_step_retries = max(0, max_step_retries)
        self.handler_registry = ActionHandlerRegistry()
        self.capability_resolver = CapabilityResolver()
        self.context = ExecutionContext()
        self.trace: list[StepExecutionRecord] = []

    def execute_plan(self, plan: ActionPlan) -> list[ActionObservation]:
        observations: list[ActionObservation] = []

        for step in plan.steps:
            attempt = 0
            while True:
                observation = self.execute_step(step)
                observations.append(observation)

                if observation.success:
                    break

                failure_reason = observation.failure_reason or self._classify_failure(step, observation.message)
                can_retry = (
                    failure_reason == FAILURE_RETRYABLE
                    and step.allow_retry
                    and attempt < self.max_step_retries
                )
                if can_retry:
                    attempt += 1
                    self.context.state.increment_retry(step.id)
                    continue

                if failure_reason == FAILURE_REPLANNABLE:
                    self.context.state.add_intermediate_ref("replan_required", True)
                    self.context.state.add_intermediate_ref("replan_reason", observation.message)

                return observations

        return observations

    def execute_step(self, step: ActionStep) -> ActionObservation:
        try:
            self._check_dependencies(step)
            self.context.state.set_current_step(step.id)
            route = self.capability_resolver.resolve_step_route(
                step=step,
                file_resolver=self.file_resolver,
                context=self.context,
            )
            self._write_back_route(route.to_dict())

            handler = self.handler_registry.get_handler(step.action_type)
            observation = handler.handle(step, self.file_resolver, self.context)
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            observation = ActionObservation(
                step_id=step.id,
                success=False,
                message=message,
                failure_reason=self._classify_failure(step, message),
            )

        if not observation.success and not observation.failure_reason:
            observation.failure_reason = self._classify_failure(step, observation.message)

        self.context.add_observation(observation)
        self._write_back_observation(step, observation)

        self.trace.append(
            StepExecutionRecord(
                step_id=step.id,
                tool_calls=[],
                outputs={
                    "step": step.model_dump(),
                    "observation": observation.model_dump(),
                },
                success=observation.success,
                error=observation.message if not observation.success else None,
                verifier_result=observation.validation_result or None,
            )
        )

        if observation.success:
            self.context.state.mark_completed()
        else:
            self.context.state.mark_failed(observation.message)

        return observation

    def export_context(self) -> dict[str, Any]:
        return self.context.export_debug_dict()

    def export_trace(self) -> list[StepExecutionRecord]:
        return self.trace

    def export_trace_dict(self) -> list[dict[str, Any]]:
        return [item.model_dump() for item in self.trace]

    def _check_dependencies(self, step: ActionStep) -> None:
        for dep in step.depends_on:
            obs = self.context.get_observation(dep)
            if obs is None:
                raise ValueError(f"Dependency not executed yet: {dep}")
            if not obs.success:
                raise ValueError(f"Dependency failed: {dep}")

    def _write_back_route(self, route: dict[str, Any]) -> None:
        refs = self.context.state.intermediate_refs
        refs.setdefault("step_routing", {})
        step_id = str(route.get("step_id") or "")
        if step_id:
            refs["step_routing"][step_id] = route

    def _classify_failure(self, step: ActionStep, message: str) -> str:
        text = (message or "").lower()

        retry_keywords = [
            "timeout",
            "timed out",
            "tempor",
            "rate limit",
            "429",
            "connection",
            "network",
            "unavailable",
            "busy",
            "try again",
        ]
        if any(keyword in text for keyword in retry_keywords):
            return FAILURE_RETRYABLE

        replanning_keywords = [
            "no handler registered",
            "unsupported",
            "dependency",
            "provider",
            "capability",
            "not support",
            "not executed yet",
        ]
        if any(keyword in text for keyword in replanning_keywords):
            return FAILURE_REPLANNABLE

        if step.allow_retry:
            return FAILURE_RETRYABLE
        return FAILURE_NON_RECOVERABLE

    def _write_back_observation(self, step: ActionStep, observation: ActionObservation) -> None:
        refs = self.context.state.intermediate_refs
        refs.setdefault("read_documents", {})
        refs.setdefault("extracted_fields", {})
        refs.setdefault("generated_mappings", {})
        refs.setdefault("filled_documents", {})
        refs.setdefault("output_file_paths", [])

        action = (step.action_type or "").strip().lower()
        if action in {"read", "read_document"} and observation.success:
            refs["read_documents"][step.id] = observation.read_result or observation.data

        if action in {"extract", "extract_structured_data"} and observation.success:
            refs["extracted_fields"][step.id] = observation.extracted_fields or observation.data

        if action in {"build_field_mapping"} and observation.success:
            refs["generated_mappings"][step.id] = observation.data

        if action in {"fill", "fill_fields"} and observation.success:
            refs["filled_documents"][step.id] = observation.data

        if action in {"write", "create_output", "fill", "fill_fields"} and observation.success:
            output_paths = refs["output_file_paths"]
            for output in observation.produced_file_ids:
                if output not in output_paths:
                    output_paths.append(output)

            output_path = observation.data.get("output_path") if isinstance(observation.data, dict) else None
            if isinstance(output_path, str) and output_path and output_path not in output_paths:
                output_paths.append(output_path)
