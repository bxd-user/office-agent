from __future__ import annotations

import re
from docx import Document


class WordAnalyzer:
    PLACEHOLDER_PATTERNS = [
        r"\{\{(.*?)\}\}",
        r"【(.*?)】",
        r"<<(.*?)>>",
    ]

    def find_placeholders(self, file_path: str):
        doc = Document(file_path)
        matches = []

        def scan_text(text: str, location: dict):
            for pattern in self.PLACEHOLDER_PATTERNS:
                for m in re.finditer(pattern, text):
                    matches.append({
                        "placeholder": m.group(0),
                        "key": m.group(1).strip(),
                        "location": location,
                    })

        for i, p in enumerate(doc.paragraphs):
            scan_text(p.text, {"type": "paragraph", "index": i})

        for ti, table in enumerate(doc.tables):
            for ri, row in enumerate(table.rows):
                for ci, cell in enumerate(row.cells):
                    scan_text(cell.text, {
                        "type": "table_cell",
                        "table_index": ti,
                        "row_index": ri,
                        "col_index": ci,
                    })

        return {
            "placeholders": matches,
            "count": len(matches),
        }

    def find_paragraphs_by_keyword(self, file_path: str, keyword: str):
        doc = Document(file_path)
        items = []
        for i, p in enumerate(doc.paragraphs):
            if keyword in p.text:
                items.append({
                    "index": i,
                    "text": p.text,
                    "style": getattr(p.style, "name", None),
                })
        return {"matches": items, "count": len(items)}

    def find_table_by_header(self, file_path: str, headers: list[str]):
        doc = Document(file_path)
        candidates = []

        for ti, table in enumerate(doc.tables):
            rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
            header_row = rows[0] if rows else []
            score = sum(1 for h in headers if h in header_row)

            if score > 0:
                candidates.append({
                    "table_index": ti,
                    "header_row": header_row,
                    "match_score": score,
                    "rows": rows,
                })

        candidates.sort(key=lambda x: x["match_score"], reverse=True)
        return {
            "candidates": candidates,
            "best_match": candidates[0] if candidates else None,
        }