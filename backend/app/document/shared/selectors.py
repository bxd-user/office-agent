from __future__ import annotations

from app.document.adapters.excel_adapter import ExcelAdapter
from app.document.adapters.word_adapter import WordAdapter
from app.document.shared.base import BaseSelector


class WordSelector(BaseSelector):
    def select(self, file_path: str) -> WordAdapter:
        if not file_path.lower().endswith((".doc", ".docx")):
            raise ValueError("WordSelector only supports .doc/.docx files")
        return WordAdapter()


class ExcelSelector(BaseSelector):
    def select(self, file_path: str) -> ExcelAdapter:
        if not file_path.lower().endswith((".xls", ".xlsx", ".xlsm", ".csv", ".tsv")):
            raise ValueError("ExcelSelector only supports excel-like files")
        return ExcelAdapter()


def get_selector(file_path: str) -> BaseSelector:
    lower = file_path.lower()
    if lower.endswith((".doc", ".docx")):
        return WordSelector()
    if lower.endswith((".xls", ".xlsx", ".xlsm", ".csv", ".tsv")):
        return ExcelSelector()
    raise ValueError(f"No selector for file type: {file_path}")
