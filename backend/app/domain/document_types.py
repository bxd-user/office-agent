from __future__ import annotations

from enum import Enum


def _normalize_key(value: str) -> str:
    text = (value or "").strip().lower()
    text = text.replace("-", "_")
    text = text.replace(" ", "_")
    return text


class DocumentType(str, Enum):
    WORD = "word"
    EXCEL = "excel"
    PPT = "ppt"
    PDF = "pdf"
    TEXT = "text"
    UNKNOWN = "unknown"

    @classmethod
    def aliases(cls) -> dict[str, "DocumentType"]:
        alias_map: dict[str, DocumentType] = {}

        for item in cls:
            alias_map[_normalize_key(item.name)] = item
            alias_map[_normalize_key(item.value)] = item

        alias_map.update(
            {
                "doc": cls.WORD,
                "docx": cls.WORD,
                ".doc": cls.WORD,
                ".docx": cls.WORD,
                "word_document": cls.WORD,
                "xls": cls.EXCEL,
                "xlsx": cls.EXCEL,
                "xlsm": cls.EXCEL,
                ".xls": cls.EXCEL,
                ".xlsx": cls.EXCEL,
                ".xlsm": cls.EXCEL,
                "spreadsheet": cls.EXCEL,
                "ppt": cls.PPT,
                "pptx": cls.PPT,
                ".ppt": cls.PPT,
                ".pptx": cls.PPT,
                "presentation": cls.PPT,
                "markdown": cls.TEXT,
                "md": cls.TEXT,
                ".md": cls.TEXT,
                "plain_text": cls.TEXT,
                "txt": cls.TEXT,
                ".txt": cls.TEXT,
                "portable_document": cls.PDF,
                ".pdf": cls.PDF,
            }
        )
        return alias_map

    @classmethod
    def from_any(cls, value: str | "DocumentType" | None) -> "DocumentType":
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.UNKNOWN
        key = _normalize_key(str(value))
        return cls.aliases().get(key, cls.UNKNOWN)

    @classmethod
    def normalize(cls, value: str | "DocumentType" | None) -> str:
        return cls.from_any(value).value


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

    if candidate:
        by_alias = DocumentType.from_any(candidate)
        if by_alias != DocumentType.UNKNOWN:
            return by_alias

    return EXTENSION_TO_DOCUMENT_TYPE.get(candidate, DocumentType.UNKNOWN)