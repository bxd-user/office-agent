from __future__ import annotations

from app.agent.execution_context import ExecutionContext
from app.agent.schemas.action import ActionObservation, ActionStep
from app.document.service import DocumentService


class ValidateOutputHandler:
    """
    验证文档输出内容是否满足要求。

    params 支持：
    Word:
    - （无额外参数，自动检测残留占位符）

    Excel:
    - required_cells : list[str] — 必填单元格列表，如 ["B2", "C3"]
    - sheet_name     : str       — 指定 sheet（默认第一个）
    """

    def __init__(self) -> None:
        self.document_service = DocumentService()

    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        file_id = step.target_file_id or (step.input_file_ids[0] if step.input_file_ids else None)
        if not file_id:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message="VALIDATE_OUTPUT requires target_file_id or input_file_ids",
            )

        file_info = file_resolver(file_id)

        result = self.document_service.validate(
            file_path=file_info["path"],
            filename=file_info.get("filename"),
            **step.params,
        )

        return ActionObservation(
            step_id=step.id,
            success=result.success,
            message=result.message,
            data=result.data,
            raw=result.raw,
        )


# 保留旧的函数签名，避免旧调用点报错
def handle_validate_output(payload: dict) -> dict:
    return {"action": "validate_output", "payload": payload}
