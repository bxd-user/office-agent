from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class OutputSchema:
    schema_name: str
    fields: Dict[str, Any] = field(default_factory=dict)
