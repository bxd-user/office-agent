from __future__ import annotations

from app.agent.execution_context import ExecutionContext
from app.agent.schemas.action import ActionObservation, ActionStep
from app.document.service import DocumentService


class ReadDocumentHandler:
    def __init__(self) -> None:
        self.document_service = DocumentService()

    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        if not step.input_file_ids:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message="READ_DOCUMENT requires at least one input file",
            )

        file_id = step.input_file_ids[0]
        file_info = file_resolver(file_id)
        result = self.document_service.read(
            file_path=file_info["path"],
            filename=file_info.get("filename"),
        )

        obs = ActionObservation(
            step_id=step.id,
            success=result.success,
            message=result.message,
            data=result.data,
            raw=result.raw,
        )

        return obs