from __future__ import annotations

from app.agent.execution_context import ExecutionContext
from app.agent.llm_mapping_builder import LLMMappingBuilder
from app.agent.schemas.action import ActionObservation, ActionStep


class BuildFieldMappingHandler:
    def __init__(self) -> None:
        self.mapping_builder = LLMMappingBuilder()

    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        source_step_id = step.params.get("source_step_id")
        if not source_step_id:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message="BUILD_FIELD_MAPPING requires params.source_step_id",
            )

        source_obs = context.get_observation(source_step_id)
        if source_obs is None or not source_obs.success:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message=f"Source step not found or failed: {source_step_id}",
            )

        target_schema = step.params.get("target_schema", {})
        target_schema_artifact = step.params.get("target_schema_from_artifact")
        if target_schema_artifact:
            target_schema = context.require_artifact(target_schema_artifact).value

        user_request = step.params.get("user_request", "")

        try:
            field_values = self.mapping_builder.build_field_values(
                source_data=source_obs.data,
                target_schema=target_schema,
                user_request=user_request,
            )
        except Exception as e:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message=f"LLM mapping failed: {e}",
            )

        artifact_name = step.params.get("artifact_name", f"{step.id}.field_mapping")
        context.add_artifact(
            name=artifact_name,
            artifact_type="field_mapping",
            value=field_values,
            source_step_id=step.id,
        )

        return ActionObservation(
            step_id=step.id,
            success=True,
            message="Field mapping built by LLM successfully",
            data={
                "artifact_name": artifact_name,
                "field_values": field_values,
            },
        )