from __future__ import annotations

from app.agent.execution_context import ExecutionContext
from app.agent.schemas.action import ActionObservation, ActionStep
from app.document.service import DocumentService


class ScanTemplateFieldsHandler:
    def __init__(self) -> None:
        self.document_service = DocumentService()

    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        if not step.target_file_id:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message="SCAN_TEMPLATE_FIELDS requires target_file_id",
            )

        target_info = file_resolver(step.target_file_id)

        result = self.document_service.scan_template(
            file_path=target_info["path"],
            filename=target_info.get("filename"),
        )

        if result.success:
            artifact_name = step.params.get("output_artifact_name", f"{step.id}.template_schema")
            context.add_artifact(
                name=artifact_name,
                artifact_type="template_schema",
                value=result.data,
                source_step_id=step.id,
            )

        return ActionObservation(
            step_id=step.id,
            success=result.success,
            message=result.message,
            data=result.data,
            raw=result.raw,
        )