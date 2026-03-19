from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =========================
# Agent 执行结果
# =========================

@dataclass(slots=True)
class AgentResult:
    """单个 Agent 执行结果。

    统一所有 agent 的返回结构。
    """

    success: bool
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @classmethod
    def ok(
        cls,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> "AgentResult":
        return cls(
            success=True,
            message=message,
            data=data or {},
            error=None,
        )

    @classmethod
    def fail(
        cls,
        error: str,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> "AgentResult":
        return cls(
            success=False,
            message=message,
            data=data or {},
            error=error,
        )


# =========================
# Runtime 执行结果（整体任务）
# =========================

@dataclass(slots=True)
class TaskResult:
    """整个任务执行的最终结果。"""

    success: bool
    message: str = ""
    task_id: str = ""
    output_path: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)

    @classmethod
    def ok(
        cls,
        task_id: str,
        message: str = "Task completed successfully",
        output_path: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        logs: Optional[List[str]] = None,
    ) -> "TaskResult":
        return cls(
            success=True,
            message=message,
            task_id=task_id,
            output_path=output_path,
            data=data or {},
            logs=logs or [],
        )

    @classmethod
    def fail(
        cls,
        task_id: str,
        error: str,
        message: str = "Task failed",
        data: Optional[Dict[str, Any]] = None,
        logs: Optional[List[str]] = None,
    ) -> "TaskResult":
        return cls(
            success=False,
            message=message,
            task_id=task_id,
            data=data or {},
            error=error,
            logs=logs or [],
        )


# =========================
# Agent 执行记录（可选，用于调试/追踪）
# =========================

@dataclass(slots=True)
class AgentExecutionRecord:
    """记录每个 agent 的执行过程（可选但很有用）。"""

    agent_name: str
    success: bool
    message: str = ""
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


# =========================
# LLM 相关消息（为 MapperAgent 预留）
# =========================

@dataclass(slots=True)
class LLMMessage:
    """通用 LLM 消息结构（简单版）。"""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(slots=True)
class LLMRequest:
    """发送给 LLM 的请求。"""

    messages: List[LLMMessage]
    temperature: float = 0.0
    max_tokens: Optional[int] = None


@dataclass(slots=True)
class LLMResponse:
    """LLM 返回结果。"""

    content: str
    raw: Optional[Any] = None