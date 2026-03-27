from __future__ import annotations

from app.agent.execution_context import ExecutionContext
from app.agent.schemas.action import ActionObservation, ActionStep
from app.document.service import DocumentService


class CompareDocumentsHandler:
    """
    对比两个文档，返回差异信息。

    step.input_file_ids[0] = 左侧（原始）文档
    step.input_file_ids[1] = 右侧（修改后）文档

    params 支持：
    - include_tables : bool — 是否纳入表格行对比（默认 True，Word 专用）
    """

    def __init__(self) -> None:
        self.document_service = DocumentService()

    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        if len(step.input_file_ids) < 2:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message="COMPARE_DOCUMENTS requires exactly two input files (left, right)",
            )

        left_info = file_resolver(step.input_file_ids[0])
        right_info = file_resolver(step.input_file_ids[1])

        result = self.document_service.compare(
            left_file_path=left_info["path"],
            right_file_path=right_info["path"],
            filename=left_info.get("filename"),
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
def handle_compare_documents(payload: dict) -> dict:
    return {"action": "compare_documents", "payload": payload}
