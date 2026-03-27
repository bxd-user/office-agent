from __future__ import annotations

from app.agent.execution_context import ExecutionContext
from app.agent.schemas.action import ActionObservation, ActionStep
from app.document.service import DocumentService


class LocateTargetsHandler:
    """
    在文档中定位内容。

    params 支持（至少传一个）：
    - keyword       : str  — 关键字搜索
    - placeholder   : str  — 占位符名称（不含括号）
    - table_header  : list — 表头列表
    - case_sensitive: bool — 关键字是否区分大小写（默认 False）
    - sheet_name    : str  — Excel 专用
    - headers       : list — Excel 表头模式
    - text          : str  — Excel 精确文本
    """

    def __init__(self) -> None:
        self.document_service = DocumentService()

    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        if not step.input_file_ids:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message="LOCATE_TARGETS requires at least one input file",
            )

        file_id = step.input_file_ids[0]
        file_info = file_resolver(file_id)

        result = self.document_service.locate(
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
def handle_locate_targets(payload: dict) -> dict:
    return {"action": "locate_targets", "payload": payload}
