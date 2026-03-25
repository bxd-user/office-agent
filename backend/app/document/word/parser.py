from __future__ import annotations

import re
from docx import Document

from app.document.word.models import ParagraphBlock, TableBlock, DocumentStructure


PLACEHOLDER_PATTERN = re.compile(r"\{\{(.*?)\}\}")


def extract_placeholders(text: str) -> list[str]:
    if not text:
        return []
    return [x.strip() for x in PLACEHOLDER_PATTERN.findall(text) if x.strip()]


class WordParser:
    def read_text(self, file_path: str) -> str:
        doc = Document(file_path)
        parts = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                parts.append(text)
        return "\n".join(parts)

    def read_tables(self, file_path: str):
        doc = Document(file_path)
        all_tables = []

        for i, table in enumerate(doc.tables):
            rows = []
            for row in table.rows:
                rows.append([cell.text for cell in row.cells])
            all_tables.append({
                "table_index": i,
                "rows": rows,
            })
        return all_tables

    def extract_structure(self, file_path: str):
        doc = Document(file_path)

        paragraphs = []
        for i, p in enumerate(doc.paragraphs):
            paragraphs.append({
                "index": i,
                "text": p.text,
                "style": getattr(p.style, "name", None),
            })

        tables = []
        for i, table in enumerate(doc.tables):
            rows = []
            for row in table.rows:
                rows.append([cell.text for cell in row.cells])

            tables.append({
                "table_index": i,
                "rows": rows,
            })

        return {
            "paragraphs": paragraphs,
            "tables": tables,
        }