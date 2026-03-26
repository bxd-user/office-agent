from __future__ import annotations

from enum import Enum


class DocumentType(str, Enum):
    WORD = "word"
    EXCEL = "excel"
    PPT = "ppt"
    PDF = "pdf"
    TEXT = "text"
    UNKNOWN = "unknown"


EXTENSION_TO_DOCUMENT_TYPE: dict[str, DocumentType] = {
    ".doc": DocumentType.WORD,
    ".docx": DocumentType.WORD,
    ".xls": DocumentType.EXCEL,
    ".xlsx": DocumentType.EXCEL,
    ".xlsm": DocumentType.EXCEL,
    ".ppt": DocumentType.PPT,
    ".pptx": DocumentType.PPT,
    ".pdf": DocumentType.PDF,
    ".txt": DocumentType.TEXT,
    ".md": DocumentType.TEXT,
}


def detect_document_type(filename: str | None = None, ext: str | None = None) -> DocumentType:
    """
    根据文件名或扩展名推断文档类型。
    """
    candidate = (ext or "").strip().lower()
    if not candidate and filename:
        dot = filename.rfind(".")
        if dot != -1:
            candidate = filename[dot:].lower()

    return EXTENSION_TO_DOCUMENT_TYPE.get(candidate, DocumentType.UNKNOWN)