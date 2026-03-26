from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ExecutionState:
    current_step_id: str = ""
    retries: Dict[str, int] = field(default_factory=dict)
