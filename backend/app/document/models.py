from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


BlockType = Literal["paragraph", "table"]


@dataclass
class ParsedTable:
    rows: List[List[str]]


@dataclass
class DocumentBlock:
    type: BlockType
    index: int
    text: str = ""
    table_rows: List[List[str]] = field(default_factory=list)


@dataclass
class ParsedDocument:
    file_name: str
    file_path: str
    file_type: str
    paragraphs: List[str]
    tables: List[ParsedTable]
    blocks: List[DocumentBlock]
    full_text: str


@dataclass
class VerificationResult:
    verify_passed: bool
    unreplaced_placeholders: List[str]
    empty_fields: List[str]
    warnings: List[str] = field(default_factory=list)
    needs_repair: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verify_passed": self.verify_passed,
            "unreplaced_placeholders": self.unreplaced_placeholders,
            "empty_fields": self.empty_fields,
            "warnings": self.warnings,
            "needs_repair": self.needs_repair,
        }