from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Observation:
    source: str
    content: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None
