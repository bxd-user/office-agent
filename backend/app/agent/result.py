from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentRunResult:
    answer: str
    tool_trace: List[Dict[str, Any]] = field(default_factory=list)
    output_files: List[Dict[str, Any]] = field(default_factory=list)
    raw: Optional[Dict[str, Any]] = None