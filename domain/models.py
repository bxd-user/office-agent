from dataclasses import dataclass, field

@dataclass
class TaskFile:
    path: str
    file_type: str

@dataclass
class FieldMapping:
    placeholder: str
    column_name: str

@dataclass
class ValidationResult:
    passed: bool
    unfilled_placeholders: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)