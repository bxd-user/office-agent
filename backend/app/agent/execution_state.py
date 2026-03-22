from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StepRecord:
    step_id: str
    action: str
    status: str = "pending"
    output: Any = None
    error: Optional[str] = None


@dataclass
class ExecutionState:
    current_step_id: Optional[str] = None
    step_records: List[StepRecord] = field(default_factory=list)

    # 多文件文本
    source_file_texts: Dict[str, str] = field(default_factory=dict)
    reference_file_texts: Dict[str, str] = field(default_factory=dict)
    combined_source_text: str = ""

    # 中间结果
    structured_data: Dict[str, Any] = field(default_factory=dict)

    # 模板驱动结果
    template_placeholders: List[str] = field(default_factory=list)
    final_fill_data: Dict[str, Any] = field(default_factory=dict)
    missing_fields: List[str] = field(default_factory=list)

    # 生成结果
    summary_text: str = ""
    output_file_path: Optional[str] = None
    verify_passed: Optional[bool] = None

    # review / repair
    repair_attempts: int = 0
    last_review_report: Dict[str, Any] = field(default_factory=dict)
    repaired_fill_data: Dict[str, Any] = field(default_factory=dict)
    unreplaced_placeholders: List[str] = field(default_factory=list)

    def add_step_record(self, step_id: str, action: str) -> StepRecord:
        record = StepRecord(step_id=step_id, action=action, status="running")
        self.step_records.append(record)
        self.current_step_id = step_id
        return record