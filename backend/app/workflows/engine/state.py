from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowState:
    instruction: str
    input_files: list[dict]
    output_dir: str
    params: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        self.logs.append(message)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def has(self, key: str) -> bool:
        return key in self.data
