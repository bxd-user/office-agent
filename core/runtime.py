from __future__ import annotations

from typing import Dict

from agents.base import BaseAgent
from core.messages import AgentExecutionRecord, TaskResult
from core.task_context import TaskContext
from core.workflow import DEFAULT_WORKFLOW


class AgentRuntime:
    """按固定 workflow 顺序执行各个 agent。"""

    def __init__(self, agents: Dict[str, BaseAgent]) -> None:
        self.agents = agents

    def run(self, ctx: TaskContext) -> TaskResult:
        ctx.set_status("running")

        execution_records: list[AgentExecutionRecord] = []

        for step in DEFAULT_WORKFLOW:
            if not step.enabled:
                ctx.log(f"[runtime] skip disabled step: {step.name}")
                continue

            agent = self.agents.get(step.name)
            if agent is None:
                ctx.set_error(f"Agent not found for step: {step.name}")
                return TaskResult.fail(
                    task_id=ctx.task_id,
                    error=ctx.error or "agent missing",
                    message=f"Missing agent: {step.name}",
                    data={
                        "summary": ctx.build_summary(),
                        "execution_records": [
                            {
                                "agent_name": r.agent_name,
                                "success": r.success,
                                "message": r.message,
                                "error": r.error,
                                "data": r.data,
                            }
                            for r in execution_records
                        ],
                    },
                    logs=ctx.logs.copy(),
                )

            ctx.log(f"[runtime] run step: {step.name}")
            result = agent.run(ctx)

            execution_records.append(
                AgentExecutionRecord(
                    agent_name=step.name,
                    success=result.success,
                    message=result.message,
                    error=result.error,
                    data=result.data,
                )
            )

            if not result.success:
                ctx.set_error(result.error or result.message or f"{step.name} failed")
                return TaskResult.fail(
                    task_id=ctx.task_id,
                    error=ctx.error or "task failed",
                    message=f"Workflow failed at step: {step.name}",
                    data={
                        "failed_step": step.name,
                        "agent_result": {
                            "success": result.success,
                            "message": result.message,
                            "error": result.error,
                            "data": result.data,
                        },
                        "summary": ctx.build_summary(),
                        "execution_records": [
                            {
                                "agent_name": r.agent_name,
                                "success": r.success,
                                "message": r.message,
                                "error": r.error,
                                "data": r.data,
                            }
                            for r in execution_records
                        ],
                    },
                    logs=ctx.logs.copy(),
                )

        ctx.set_status("completed")
        ctx.log("[runtime] workflow completed")

        return TaskResult.ok(
            task_id=ctx.task_id,
            message="Task completed successfully",
            output_path=ctx.output_path,
            data={
                "summary": ctx.build_summary(),
                "execution_records": [
                    {
                        "agent_name": r.agent_name,
                        "success": r.success,
                        "message": r.message,
                        "error": r.error,
                        "data": r.data,
                    }
                    for r in execution_records
                ],
            },
            logs=ctx.logs.copy(),
        )