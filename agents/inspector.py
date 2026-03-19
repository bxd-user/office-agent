from __future__ import annotations

from typing import Any

from core.messages import AgentResult
from core.task_context import TaskContext
from agents.base import BaseAgent

from tools.excel_tools import (
    ReadExcelRecordsInput,
    ReadExcelRecordsTool,
)
from tools.word_tools import (
    ExtractWordPlaceholdersInput,
    ExtractWordPlaceholdersTool,
    InspectWordStructureInput,
    InspectWordStructureTool,
)


class InspectorAgent(BaseAgent):
    """负责读取输入文件并写入 TaskContext。

    当前职责：
    1. 读取 Excel records
    2. 检查 Word 结构
    3. 提取 Word placeholders
    4. 将结果写入 ctx
    """

    name = "inspector"

    def __init__(self) -> None:
        super().__init__()
        self.excel_tool = ReadExcelRecordsTool()
        self.word_structure_tool = InspectWordStructureTool()
        self.word_placeholder_tool = ExtractWordPlaceholdersTool()

    @staticmethod
    def _to_dict_data(data: Any) -> dict[str, Any]:
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _to_str_list_data(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]

    def _run(self, ctx: TaskContext) -> AgentResult:
        if not ctx.excel_path:
            return self.fail(ctx, "excel_path is missing in TaskContext")

        if not ctx.word_path:
            return self.fail(ctx, "word_path is missing in TaskContext")

        tool_ctx = self.build_tool_context(ctx)

        ctx.log("[inspector] start reading excel")
        excel_result = self.excel_tool.execute_safe(
            ReadExcelRecordsInput(
                file_path=ctx.excel_path,
            ),
            tool_ctx,
        )

        if not excel_result.success:
            return self.fail(
                ctx,
                error=excel_result.error or "failed to read excel",
                message=excel_result.message,
            )

        excel_data = self._to_dict_data(excel_result.data)
        ctx.excel_data = excel_data
        ctx.log(
            f"[inspector] excel loaded: "
            f"{excel_data.get('record_count', 0)} records"
        )

        ctx.log("[inspector] start inspecting word structure")
        word_structure_result = self.word_structure_tool.execute_safe(
            InspectWordStructureInput(
                file_path=ctx.word_path,
                include_blocks=False,
            ),
            tool_ctx,
        )

        if not word_structure_result.success:
            return self.fail(
                ctx,
                error=word_structure_result.error or "failed to inspect word",
                message=word_structure_result.message,
            )

        word_structure = self._to_dict_data(word_structure_result.data)
        ctx.word_structure = word_structure
        ctx.log(
            f"[inspector] word inspected: "
            f"{word_structure.get('paragraph_count', 0)} paragraphs, "
            f"{word_structure.get('table_count', 0)} tables"
        )

        ctx.log("[inspector] start extracting word placeholders")
        placeholder_result = self.word_placeholder_tool.execute_safe(
            ExtractWordPlaceholdersInput(
                file_path=ctx.word_path,
            ),
            tool_ctx,
        )

        if not placeholder_result.success:
            return self.fail(
                ctx,
                error=placeholder_result.error or "failed to extract placeholders",
                message=placeholder_result.message,
            )

        placeholder_data = self._to_dict_data(placeholder_result.data)
        placeholders = self._to_str_list_data(placeholder_data.get("placeholders", []))
        ctx.word_placeholders = placeholders
        ctx.log(
            f"[inspector] placeholders extracted: {len(placeholders)}"
        )

        # 把 tool 日志写回 ctx，便于统一排查
        self.merge_tool_logs(ctx, tool_ctx)

        # 可选：记录中间产物摘要
        ctx.shared["inspector_summary"] = {
            "excel_headers": ctx.get_excel_headers(),
            "excel_record_count": len(ctx.get_excel_records()),
            "word_placeholders": ctx.get_word_placeholders(),
        }

        return AgentResult.ok(
            message="Inspector finished successfully",
            data={
                "excel_headers": ctx.get_excel_headers(),
                "excel_record_count": len(ctx.get_excel_records()),
                "word_placeholders": ctx.get_word_placeholders(),
                "word_table_count": (
                    ctx.word_structure.get("table_count", 0)
                    if ctx.word_structure
                    else 0
                ),
            },
        )