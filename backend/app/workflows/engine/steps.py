from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowStep:
    name: str
    tool: str
    action: str
    args: dict[str, Any] = field(default_factory=dict)
    condition: str | None = None
    on_fail: str = "continue"  # continue | break


@dataclass
class WorkflowPlan:
    goal: str
    steps: list[WorkflowStep]

    @staticmethod
    def from_llm_payload(payload: dict[str, Any], default_goal: str = "执行任务") -> "WorkflowPlan":
        goal = str(payload.get("goal") or default_goal)
        raw_steps = payload.get("steps", []) if isinstance(payload.get("steps", []), list) else []
        steps: list[WorkflowStep] = []

        for idx, item in enumerate(raw_steps, start=1):
            if not isinstance(item, dict):
                continue

            tool = str(item.get("tool") or "").strip()
            action = str(item.get("action") or "").strip()
            args = item.get("args", {}) if isinstance(item.get("args", {}), dict) else {}
            condition = item.get("condition") if isinstance(item.get("condition"), str) else None
            on_fail = str(item.get("on_fail") or "continue").strip().lower()
            if on_fail not in {"continue", "break"}:
                on_fail = "continue"

            if not tool:
                continue

            if not action:
                action = "read"

            steps.append(
                WorkflowStep(
                    name=f"step_{idx}_{tool}_{action}",
                    tool=tool,
                    action=action,
                    args=args,
                    condition=condition,
                    on_fail=on_fail,
                )
            )

        return WorkflowPlan(goal=goal, steps=steps)
