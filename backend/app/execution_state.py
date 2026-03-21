from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ExecutionState:
    task_type: str
    collected_text: str = ""
    structured_data: Optional[Dict[str, Any]] = None
    answer: str = ""
    output_file_path: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)