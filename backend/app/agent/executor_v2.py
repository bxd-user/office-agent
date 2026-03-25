from __future__ import annotations

from typing import Any, Dict, List

from app.agent.plan_models import PlanStep, StepExecutionRecord
from app.agent.reducers import ToolResultReducer
from app.mcp.client import LocalMCPClient


class ExecutorV2:
    def __init__(self, llm_client, mcp_client: LocalMCPClient):
        self.llm_client = llm_client
        self.mcp_client = mcp_client
        self.reducer = ToolResultReducer()

    def execute_step(self, context, step: PlanStep) -> StepExecutionRecord:
        step.status = "running"
        record = StepExecutionRecord(step_id=step.step_id)

        decision = self.llm_client.decide_step_actions(
            user_prompt=context.user_prompt,
            plan_goal=context.plan.goal if context.plan else "",
            current_step={
                "step_id": step.step_id,
                "title": step.title,
                "objective": step.objective,
                "suggested_tools": step.suggested_tools,
                "inputs": step.inputs,
                "expected_outputs": step.expected_outputs,
            },
            memory_snapshot=context.memory.snapshot(),
            files=context.files,
        )

        tool_calls = decision.get("tool_calls", [])
        if not tool_calls:
            record.success = False
            record.error = "No tool calls produced for step"
            step.status = "failed"
            context.memory.mark_failed(step.step_id)
            return record

        for call in tool_calls:
            tool_name = call["name"]
            arguments = call.get("arguments", {})

            result = self.mcp_client.call_tool(tool_name=tool_name, arguments=arguments)
            tool_result_dict = {
                "success": result.success,
                "content": result.content,
                "error": result.error,
            }

            record.tool_calls.append({
                "tool_name": tool_name,
                "arguments": arguments,
                "result": tool_result_dict,
            })

            self.reducer.reduce(
                memory=context.memory,
                tool_name=tool_name,
                tool_args=arguments,
                tool_result=tool_result_dict,
            )

        record.outputs = {
            "memory_snapshot_after_step": context.memory.snapshot()
        }
        record.success = True
        step.status = "completed"
        context.memory.mark_completed(step.step_id)
        return record