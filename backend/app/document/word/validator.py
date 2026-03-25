from __future__ import annotations

from docx import Document


class WordValidator:
    def validate_replacements(self, file_path: str):
        doc = Document(file_path)
        remaining = []

        for i, p in enumerate(doc.paragraphs):
            if "{{" in p.text and "}}" in p.text:
                remaining.append({
                    "type": "paragraph",
                    "index": i,
                    "text": p.text,
                })

        for ti, table in enumerate(doc.tables):
            for ri, row in enumerate(table.rows):
                for ci, cell in enumerate(row.cells):
                    if "{{" in cell.text and "}}" in cell.text:
                        remaining.append({
                            "type": "table_cell",
                            "table_index": ti,
                            "row_index": ri,
                            "col_index": ci,
                            "text": cell.text,
                        })

        return {
            "passed": len(remaining) == 0,
            "remaining_placeholders": remaining,
            "count": len(remaining),
        }