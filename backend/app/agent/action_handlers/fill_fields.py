from __future__ import annotations

from copy import deepcopy

from app.agent.execution_context import ExecutionContext
from app.agent.schemas.action import ActionObservation, ActionStep
from app.document.service import DocumentService


class FillFieldsHandler:
    def __init__(self) -> None:
        self.document_service = DocumentService()

    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        if not step.target_file_id:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message="FILL_FIELDS requires target_file_id",
            )

        target_info = file_resolver(step.target_file_id)
        resolved_params = self._resolve_params(step.params, context)

        result = self.document_service.fill(
            file_path=target_info["path"],
            filename=target_info.get("filename"),
            **resolved_params,
        )

        produced_file_ids: list[str] = []
        if result.output_path:
            produced_file_ids.append(result.output_path)

            artifact_name = resolved_params.get("output_artifact_name", f"{step.id}.output_file")
            context.add_artifact(
                name=artifact_name,
                artifact_type="file_path",
                value=result.output_path,
                source_step_id=step.id,
            )

        return ActionObservation(
            step_id=step.id,
            success=result.success,
            message=result.message,
            data=result.data | {"output_path": result.output_path},
            produced_file_ids=produced_file_ids,
            raw=result.raw,
        )

    def _resolve_params(self, params: dict, context: ExecutionContext) -> dict:
        resolved = deepcopy(params)

        artifact_ref = resolved.pop("field_values_from_artifact", None)
        if artifact_ref:
            artifact = context.require_artifact(artifact_ref)
            resolved["field_values"] = artifact.value

        cell_values_ref = resolved.pop("cell_values_from_artifact", None)
        if cell_values_ref:
            artifact = context.require_artifact(cell_values_ref)
            resolved["cell_values"] = artifact.value

        return resolved