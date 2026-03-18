from __future__ import annotations

from typing import Any

from app.tools.base_tool import BaseDataTool
from app.tools.excel_tool import ExcelTool
from app.tools.word_tool import WordTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseDataTool] = {}

    def register(self, tool: BaseDataTool) -> None:
        self._tools[tool.TOOL_NAME] = tool

    def get_tool(self, name: str) -> BaseDataTool | None:
        return self._tools.get(name)

    def get_tool_for_path(self, path: str) -> BaseDataTool | None:
        for tool in self._tools.values():
            if tool.supports_path(path):
                return tool
        return None

    def list_tools(self) -> list[dict[str, Any]]:
        result = []
        for tool in self._tools.values():
            result.append(
                {
                    "name": tool.TOOL_NAME,
                    "extensions": sorted(list(tool.SUPPORTED_EXTENSIONS)),
                }
            )
        return result


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ExcelTool())
    registry.register(WordTool())
    return registry
