from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class WorkflowStep:
    """工作流中的单个步骤定义。"""

    name: str
    enabled: bool = True


DEFAULT_WORKFLOW: List[WorkflowStep] = [
    WorkflowStep(name="inspector"),
    WorkflowStep(name="mapper"),
    WorkflowStep(name="executor"),
    WorkflowStep(name="validator"),
]