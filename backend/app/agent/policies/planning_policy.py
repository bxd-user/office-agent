from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlanningPolicy:
    max_steps: int = 10
    allow_fallback_plan: bool = True
