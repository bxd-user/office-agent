from __future__ import annotations

from agents.base import BaseAgent
from core.messages import AgentResult
from core.task_context import TaskContext

from tools.word_tools import (
    ValidateWordPlaceholdersInput,
    ValidateWordPlaceholdersTool,
)


class ValidatorAgent(BaseAgent):
    """负责校验生成后的 Word 文档。

    当前版本只做：
    1. 检查输出文件是否存在
    2. 检查是否还有未替换占位符
    """

    name = "validator"

    def __init__(self) -> None:
        super().__init__()
        self.validate_word_tool = ValidateWordPlaceholdersTool()

    def _run(self, ctx: TaskContext) -> AgentResult:
        if not ctx.output_path:
            return self.fail(ctx, "output_path is empty, run executor first")

        tool_ctx = self.build_tool_context(ctx)

        ctx.log(f"[validator] validating output file: {ctx.output_path}")

        validate_result = self.validate_word_tool.execute_safe(
            ValidateWordPlaceholdersInput(
                file_path=ctx.output_path,
                expected_empty=True,
            ),
            tool_ctx,
        )

        self.merge_tool_logs(ctx, tool_ctx)

        result_data = validate_result.data if isinstance(validate_result.data, dict) else {}

        if validate_result.success:
            ctx.validation_result = result_data
            ctx.shared["validator_summary"] = {
                "passed": True,
                "unfilled_count": result_data.get("unfilled_count", 0),
            }
            ctx.log("[validator] validation passed")

            return AgentResult.ok(
                message="Validator finished successfully",
                data={
                    "validation_result": result_data,
                    "passed": True,
                },
            )

        # fail 分支：仍然保存校验结果，方便调试
        ctx.validation_result = result_data
        ctx.shared["validator_summary"] = {
            "passed": False,
            "unfilled_count": result_data.get("unfilled_count", 0),
        }

        ctx.log(
            f"[validator] validation failed: "
            f"{validate_result.error or validate_result.message}"
        )

        return AgentResult.fail(
            error=validate_result.error or "validation failed",
            message=validate_result.message or "Validator failed",
            data={
                "validation_result": result_data,
                "passed": False,
            },
        )