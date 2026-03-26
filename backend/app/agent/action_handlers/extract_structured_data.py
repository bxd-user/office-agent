from __future__ import annotations

from app.agent.execution_context import ExecutionContext
from app.agent.schemas.action import ActionObservation, ActionStep
from app.document.service import DocumentService


class ExtractStructuredDataHandler:
    def __init__(self) -> None:
        self.document_service = DocumentService()

    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        if not step.input_file_ids:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message="EXTRACT_STRUCTURED_DATA requires at least one input file",
            )

        file_id = step.input_file_ids[0]
        file_info = file_resolver(file_id)

        call_params = dict(step.params)
        artifact_name = call_params.pop("output_artifact_name", None)

        result = self.document_service.extract(
            file_path=file_info["path"],
            filename=file_info.get("filename"),
            **call_params,
        )

        obs = ActionObservation(
            step_id=step.id,
            success=result.success,
            message=result.message,
            data=result.data,
            raw=result.raw,
        )

        if result.success and artifact_name:
            context.add_artifact(
                name=artifact_name,
                artifact_type="structured_data",
                value=result.data,
                source_step_id=step.id,
            )

        return obs