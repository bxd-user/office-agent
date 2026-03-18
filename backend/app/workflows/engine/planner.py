from __future__ import annotations

from app.core.agent import OfficeAgent
from app.tools.tool_registry import ToolRegistry
from app.workflows.engine.steps import WorkflowPlan


class WorkflowPlanner:
    def __init__(self, agent: OfficeAgent, registry: ToolRegistry):
        self.agent = agent
        self.registry = registry

    def plan(self, instruction: str, file_inventory: list[dict]) -> WorkflowPlan:
        available_tools = []
        for item in self.registry.list_tools():
            available_tools.append(
                {
                    "name": item["name"],
                    "extensions": item.get("extensions", []),
                    "actions": ["read", "write", "extract_fields", "fill_context"],
                }
            )

        payload = self.agent.plan_tool_calls(
            instruction=instruction,
            file_inventory=file_inventory,
            available_tools=available_tools,
        )

        plan = WorkflowPlan.from_llm_payload(payload, default_goal="根据提示词执行文件处理")
        if not plan.steps:
            plan = self._fallback_plan(file_inventory)
        return plan

    def _fallback_plan(self, file_inventory: list[dict]) -> WorkflowPlan:
        has_excel = any(str(item.get("type")) == "excel" for item in file_inventory)
        has_word = any(str(item.get("type")) == "word" for item in file_inventory)

        payload = {
            "goal": "默认回退执行",
            "steps": [],
        }

        if has_excel:
            payload["steps"].append({"tool": "excel", "action": "read", "args": {}})
        if has_word:
            payload["steps"].append({"tool": "word", "action": "read", "args": {}})

        return WorkflowPlan.from_llm_payload(payload, default_goal="默认回退执行")
