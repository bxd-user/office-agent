from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FileRole:
    file_id: str
    filename: str
    role: str  # template / data_source / reference / unknown
    reason: str = ""


@dataclass
class PlanStep:
    step_id: str
    title: str
    objective: str
    suggested_tools: List[str] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_outputs: List[str] = field(default_factory=list)
    status: str = "pending"  # pending / running / completed / failed / skipped
    notes: str = ""


@dataclass
class ExecutionPlan:
    goal: str
    task_type: str
    file_roles: List[FileRole] = field(default_factory=list)
    steps: List[PlanStep] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    requires_output_file: bool = False


@dataclass
class StepExecutionRecord:
    step_id: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    error: Optional[str] = None
    verifier_result: Optional[Dict[str, Any]] = None