from __future__ import annotations

from enum import Enum


class CapabilityType(str, Enum):
    READ = "read"
    EXTRACT = "extract"
    LOCATE = "locate"
    FILL = "fill"
    UPDATE_TABLE = "update_table"
    SUMMARIZE = "summarize"
    COMPARE = "compare"
    VALIDATE = "validate"
    WRITE = "write"
    SCAN_TEMPLATE = "scan_template"