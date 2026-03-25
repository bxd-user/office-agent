from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.agent.memory import WorkingMemory
from app.agent.plan_models import ExecutionPlan, StepExecutionRecord


@dataclass
class ExecutionContext:
    task_id: str
    user_prompt: str
    files: List[Dict[str, Any]]

    plan: Optional[ExecutionPlan] = None
    memory: WorkingMemory = field(default_factory=WorkingMemory)
    step_records: List[StepExecutionRecord] = field(default_factory=list)

    max_retries_per_step: int = 2
    replan_count: int = 0
    max_replans: int = 1

    def add_step_record(self, record: StepExecutionRecord) -> None:
        self.step_records.append(record)

    def get_step_record(self, step_id: str) -> Optional[StepExecutionRecord]:
        for r in self.step_records:
            if r.step_id == step_id:
                return r
        return None