# app/tools/registry.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol


class ToolProtocol(Protocol):
    name: str
    description: str
    input_schema: Dict[str, Any]

    def run(self, **kwargs) -> Any:
        ...


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolProtocol] = {}

    def register(self, tool: ToolProtocol) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolProtocol:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        return tool

    def has(self, name: str) -> bool:
        return name in self._tools

    def describe_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def list_names(self) -> List[str]:
        return list(self._tools.keys())