from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDataTool(ABC):
    TOOL_NAME = "base"
    SUPPORTED_EXTENSIONS: set[str] = set()

    def supports_path(self, path: str) -> bool:
        return self.get_extension(path) in self.SUPPORTED_EXTENSIONS

    def get_extension(self, path: str) -> str:
        if "." not in path:
            return ""
        return "." + path.rsplit(".", 1)[-1].lower()

    @abstractmethod
    def read_for_llm(self, path: str, **kwargs) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def write_from_llm(self, source_path: str, data: dict[str, Any], output_path: str, **kwargs) -> str:
        raise NotImplementedError

    @abstractmethod
    def execute_llm_instruction(self, instruction: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
