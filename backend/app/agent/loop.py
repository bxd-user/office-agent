from __future__ import annotations

from typing import Any, Dict, List

from app.agent.messages import tool_result_message
from app.mcp.client import LocalMCPClient


class ToolCallingLoop:
    def __init__(self, llm_client, mcp_client: LocalMCPClient, max_steps: int = 8):
        self.llm_client = llm_client
        self.mcp_client = mcp_client
        self.max_steps = max_steps

    def run(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]):
        trace = []

        for _ in range(self.max_steps):
            llm_response = self.llm_client.chat(messages=messages, tools=tools)

            if llm_response.get("final_answer"):
                return llm_response["final_answer"], trace

            tool_calls = llm_response.get("tool_calls", [])
            if not tool_calls:
                return llm_response.get("content", ""), trace

            for call in tool_calls:
                result = self.mcp_client.call_tool(
                    tool_name=call["name"],
                    arguments=call.get("arguments", {}),
                )
                trace.append({
                    "tool_call": call,
                    "tool_result": {
                        "success": result.success,
                        "content": result.content,
                        "error": result.error,
                    },
                })

                messages.append({
                    "role": "assistant",
                    "tool_call": call,
                })
                messages.append(tool_result_message(call["name"], {
                    "success": result.success,
                    "content": result.content,
                    "error": result.error,
                }))

        return "工具调用达到最大步数，任务未完成。", trace