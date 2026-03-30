from __future__ import annotations

from enum import Enum


def _normalize_key(value: str) -> str:
    text = (value or "").strip().lower()
    text = text.replace("-", "_")
    text = text.replace(" ", "_")
    return text


class ActionType(str, Enum):
    READ_DOCUMENT = "READ_DOCUMENT"
    EXTRACT_STRUCTURED_DATA = "EXTRACT_STRUCTURED_DATA"
    LOCATE_TARGETS = "LOCATE_TARGETS"
    FILL_FIELDS = "FILL_FIELDS"
    UPDATE_TABLE = "UPDATE_TABLE"
    SUMMARIZE_CONTENT = "SUMMARIZE_CONTENT"
    COMPARE_DOCUMENTS = "COMPARE_DOCUMENTS"
    VALIDATE_OUTPUT = "VALIDATE_OUTPUT"
    CREATE_OUTPUT = "CREATE_OUTPUT"
    BUILD_FIELD_MAPPING = "BUILD_FIELD_MAPPING"
    SCAN_TEMPLATE_FIELDS = "SCAN_TEMPLATE_FIELDS"

    @property
    def canonical_name(self) -> str:
        return self.name.lower()

    @classmethod
    def aliases(cls) -> dict[str, "ActionType"]:
        alias_map: dict[str, ActionType] = {}

        # 先注册官方枚举名和值
        for item in cls:
            alias_map[_normalize_key(item.name)] = item
            alias_map[_normalize_key(item.value)] = item

        # 再注册历史/漂移命名
        alias_map.update(
            {
                "read": cls.READ_DOCUMENT,
                "read_doc": cls.READ_DOCUMENT,
                "document_read": cls.READ_DOCUMENT,
                "extract": cls.EXTRACT_STRUCTURED_DATA,
                "extract_fields": cls.EXTRACT_STRUCTURED_DATA,
                "extract_content": cls.EXTRACT_STRUCTURED_DATA,
                "locate": cls.LOCATE_TARGETS,
                "locate_target": cls.LOCATE_TARGETS,
                "fill": cls.FILL_FIELDS,
                "fill_field": cls.FILL_FIELDS,
                "update": cls.UPDATE_TABLE,
                "summarize": cls.SUMMARIZE_CONTENT,
                "summary": cls.SUMMARIZE_CONTENT,
                "compare": cls.COMPARE_DOCUMENTS,
                "compare_document": cls.COMPARE_DOCUMENTS,
                "validate": cls.VALIDATE_OUTPUT,
                "validate_document": cls.VALIDATE_OUTPUT,
                "write": cls.CREATE_OUTPUT,
                "write_document": cls.CREATE_OUTPUT,
                "scan_template": cls.SCAN_TEMPLATE_FIELDS,
                "scan_template_field": cls.SCAN_TEMPLATE_FIELDS,
                "build_mapping": cls.BUILD_FIELD_MAPPING,
            }
        )
        return alias_map

    @classmethod
    def from_any(cls, value: str | "ActionType" | None) -> "ActionType" | None:
        if isinstance(value, cls):
            return value
        if value is None:
            return None
        key = _normalize_key(str(value))
        return cls.aliases().get(key)

    @classmethod
    def normalize(cls, value: str | "ActionType" | None) -> str | None:
        item = cls.from_any(value)
        return item.canonical_name if item else None