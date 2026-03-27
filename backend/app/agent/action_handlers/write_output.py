from __future__ import annotations

from app.agent.execution_context import ExecutionContext
from app.agent.schemas.action import ActionObservation, ActionStep
from app.document.service import DocumentService


class WriteOutputHandler:
    def __init__(self) -> None:
        self.document_service = DocumentService()

    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        file_id = step.target_file_id or (step.input_file_ids[0] if step.input_file_ids else None)
        if not file_id:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message="WRITE requires target_file_id or input_file_ids",
            )

        file_info = file_resolver(file_id)
        result = self.document_service.write(
            file_path=file_info["path"],
            filename=file_info.get("filename"),
            **step.params,
        )

        produced_file_ids: list[str] = []
        if result.output_path:
            produced_file_ids.append(result.output_path)

        return ActionObservation(
            step_id=step.id,
            success=result.success,
            message=result.message,
            data=result.data | {"output_path": result.output_path},
            produced_file_ids=produced_file_ids,
            raw=result.raw,
        )
