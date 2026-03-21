from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ParsedTable:
    rows: List[List[str]] = field(default_factory=list)


@dataclass
class ParsedDocument:
    file_name: str
    file_path: str
    paragraphs: List[str] = field(default_factory=list)
    tables: List[ParsedTable] = field(default_factory=list)
    full_text: str = ""


@dataclass
class InputFile:
    role: str  # source / template / reference
    file_name: str
    file_path: str
    paragraphs: List[str] = field(default_factory=list)
    tables: List[ParsedTable] = field(default_factory=list)
    full_text: str = ""


@dataclass
class TaskContext:
    user_prompt: str
    logs: List[str] = field(default_factory=list)

    files: List[InputFile] = field(default_factory=list)

    # 兼容旧逻辑
    file_name: str = ""
    file_path: str = ""
    full_text: str = ""
    paragraphs: List[str] = field(default_factory=list)
    tables: List[ParsedTable] = field(default_factory=list)

    template_file_name: Optional[str] = None
    template_file_path: Optional[str] = None


@dataclass
class TaskResult:
    success: bool
    message: str
    answer: str = ""
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    output_file_path: Optional[str] = None