from __future__ import annotations

from abc import ABC, abstractmethod

from core.messages import AgentResult
from core.task_context import TaskContext
from tools.base import ToolContext


class BaseAgent(ABC):
    """所有 Agent 的统一基类。

    设计原则：
    1. Agent 负责业务步骤，不直接承担 runtime 编排
    2. Agent 通过读写 TaskContext 协作
    3. Agent 统一返回 AgentResult
    """

    name: str = ""

    def __init__(self) -> None:
        if not self.name:
            self.name = self.__class__.__name__.lower()

    def before_run(self, ctx: TaskContext) -> None:
        """执行前钩子。"""
        ctx.set_step(self.name)
        ctx.set_status("running")
        ctx.log(f"[agent:{self.name}] start")

    def after_run(self, ctx: TaskContext, result: AgentResult) -> None:
        """执行后钩子。"""
        if result.success:
            ctx.set_status("succeeded")
            ctx.log(f"[agent:{self.name}] success: {result.message}")
        else:
            if not ctx.error:
                ctx.set_error(result.error or result.message or f"{self.name} failed")
            ctx.log(
                f"[agent:{self.name}] failed: {result.error or result.message}"
            )

    def fail(self, ctx: TaskContext, error: str, message: str = "") -> AgentResult:
        """统一失败返回。"""
        if not ctx.error:
            ctx.set_error(error)
        ctx.log(f"[agent:{self.name}] error: {error}")
        return AgentResult.fail(error=error, message=message or error)

    def build_tool_context(
        self,
        ctx: TaskContext,
        working_dir: str = ".",
        temp_dir: str = "./storage/temp",
    ) -> ToolContext:
        """构建统一 ToolContext。"""
        return ToolContext(
            task_id=ctx.task_id,
            working_dir=working_dir,
            temp_dir=temp_dir,
            metadata={
                "instruction": ctx.instruction,
                "agent": self.name,
            },
        )

    def merge_tool_logs(self, ctx: TaskContext, tool_ctx: ToolContext) -> None:
        """把工具日志回收进任务上下文。"""
        if tool_ctx.logs:
            ctx.logs.extend(tool_ctx.logs)

    def run(self, ctx: TaskContext) -> AgentResult:
        """统一执行入口。"""
        self.before_run(ctx)
        try:
            result = self._run(ctx)
        except Exception as exc:  # noqa: BLE001
            result = self.fail(
                ctx,
                error=f"Unexpected error in agent {self.name}: {exc}",
                message=f"{self.name} failed unexpectedly",
            )
        self.after_run(ctx, result)
        return result

    @abstractmethod
    def _run(self, ctx: TaskContext) -> AgentResult:
        """子类实现具体业务逻辑。"""
        raise NotImplementedError