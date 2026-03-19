from __future__ import annotations

from typing import Dict

from agents.base import BaseAgent
from core.messages import AgentResult
from core.task_context import TaskContext

from tools.word_tools import (
    FillWordTemplateInput,
    FillWordTemplateTool,
)


class ExecutorAgent(BaseAgent):
    """负责根据 field_mapping 和 Excel 数据填充 Word 模板。

    当前版本：
    1. 默认只使用 Excel 第一条记录
    2. 生成 replacements
    3. 调 FillWordTemplateTool 输出新的 docx
    """

    name = "executor"

    def __init__(self, output_dir: str = "./storage/outputs") -> None:
        super().__init__()
        self.output_dir = output_dir
        self.fill_word_tool = FillWordTemplateTool()

    def _run(self, ctx: TaskContext) -> AgentResult:
        if not ctx.word_path:
            return self.fail(ctx, "word_path is missing in TaskContext")

        if not ctx.field_mapping:
            return self.fail(ctx, "field_mapping is empty, run mapper first")

        record = ctx.get_first_excel_record()
        if not record:
            return self.fail(ctx, "excel record is empty, run inspector first")

        ctx.log(f"[executor] first excel record: {record}")
        ctx.log(f"[executor] field mapping: {ctx.field_mapping}")

        replacements = self._build_replacements(
            field_mapping=ctx.field_mapping,
            record=record,
        )

        ctx.replacements = replacements
        ctx.log(f"[executor] replacements built: {replacements}")

        tool_ctx = self.build_tool_context(ctx)

        fill_result = self.fill_word_tool.execute_safe(
            FillWordTemplateInput(
                template_path=ctx.word_path,
                replacements=replacements,
                output_dir=self.output_dir,
                output_tag="filled",
            ),
            tool_ctx,
        )

        if not fill_result.success:
            return self.fail(
                ctx,
                error=fill_result.error or "failed to fill word template",
                message=fill_result.message,
            )

        result_data = fill_result.data if isinstance(fill_result.data, dict) else {}
        output_path = result_data.get("output_path")
        if not output_path:
            return self.fail(ctx, "fill_word_template returned no output_path")

        ctx.output_path = output_path
        ctx.add_output_file(
            path=output_path,
            file_type="word",
            role="filled_document",
            name="filled_output.docx",
            metadata={
                "source_template": ctx.word_path,
            },
        )

        ctx.shared["executor_summary"] = {
            "output_path": output_path,
            "replacement_count": len(replacements),
            "unfilled_placeholders": result_data.get("unfilled_placeholders", []),
        }

        self.merge_tool_logs(ctx, tool_ctx)

        ctx.log(f"[executor] output generated: {output_path}")

        return AgentResult.ok(
            message="Executor finished successfully",
            data={
                "output_path": output_path,
                "replacement_count": len(replacements),
                "unfilled_placeholders": result_data.get(
                    "unfilled_placeholders", []
                ),
                "passed": result_data.get("passed", False),
            },
        )

    def _build_replacements(
        self,
        field_mapping: Dict[str, str],
        record: Dict[str, object],
    ) -> Dict[str, str]:
        """根据映射关系，把 Excel record 转成 Word 替换字典。

        field_mapping 格式：
        {
            "姓名": "学生姓名",
            "班级": "班级名称"
        }

        输出 replacements：
        {
            "姓名": "张三",
            "班级": "一班"
        }
        """
        replacements: Dict[str, str] = {}

        for placeholder, excel_header in field_mapping.items():
            value = record.get(excel_header, "")
            replacements[placeholder] = "" if value is None else str(value)

        return replacements