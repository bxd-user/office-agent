from __future__ import annotations

import re
from typing import Any

from docx import Document


class WordTemplateScanner:
    PATTERNS = [
        re.compile(r"\{\{\s*([^\{\}\n]+?)\s*\}\}"),
        re.compile(r"\{\s*([^\{\}\n]+?)\s*\}"),
        re.compile(r"<<\s*([^<>\n]+?)\s*>>"),
        re.compile(r"【\s*([^【】\n]+?)\s*】"),
    ]

    def scan(self, file_path: str) -> dict[str, Any]:
        doc = Document(file_path)

        hits: list[dict[str, Any]] = []
        seen: set[str] = set()

        for idx, para in enumerate(doc.paragraphs):
            text = para.text or ""
            for field in self._extract_fields(text):
                if field not in seen:
                    seen.add(field)
                hits.append(
                    {
                        "container": "paragraph",
                        "index": idx,
                        "field": field,
                        "text": text,
                    }
                )

        for t_idx, table in enumerate(doc.tables):
            for r_idx, row in enumerate(table.rows):
                for c_idx, cell in enumerate(row.cells):
                    text = cell.text or ""
                    for field in self._extract_fields(text):
                        if field not in seen:
                            seen.add(field)
                        hits.append(
                            {
                                "container": "table_cell",
                                "table_index": t_idx,
                                "row_index": r_idx,
                                "col_index": c_idx,
                                "field": field,
                                "text": text,
                            }
                        )

        fields = sorted(seen)
        return {
            "fields": fields,
            "field_count": len(fields),
            "occurrences": hits,
        }

    def _extract_fields(self, text: str) -> list[str]:
        results: list[str] = []
        for pattern in self.PATTERNS:
            for match in pattern.findall(text):
                value = str(match).strip()
                if value:
                    results.append(value)
        return results