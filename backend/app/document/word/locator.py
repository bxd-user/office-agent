"""
Word Document Locator module.
"""
from __future__ import annotations

import re

from docx import Document


_PLACEHOLDER_PATTERNS = [
    r"\{\{(.*?)\}\}",
    r"【(.*?)】",
    r"<<(.*?)>>",
]


class WordLocator:
    """
    在 Word 文档中定位内容，支持：
    - 关键字搜索（段落 + 表格单元格）
    - 占位符定位
    - 表头行定位
    """

    def locate(
        self,
        file_path: str,
        keyword: str | None = None,
        placeholder: str | None = None,
        table_header: list[str] | None = None,
        case_sensitive: bool = False,
        **kwargs,
    ) -> dict:
        doc = Document(file_path)
        results: list[dict] = []

        if keyword is not None:
            results = self._locate_keyword(doc, keyword, case_sensitive)
        elif placeholder is not None:
            results = self._locate_placeholder(doc, placeholder)
        elif table_header is not None:
            results = self._locate_table_header(doc, table_header)
        else:
            # 默认：扫描所有占位符
            results = self._locate_all_placeholders(doc)

        return {"matches": results, "count": len(results)}

    # ------------------------------------------------------------------
    # Locate strategies
    # ------------------------------------------------------------------

    def _locate_keyword(self, doc, keyword: str, case_sensitive: bool) -> list[dict]:
        matches: list[dict] = []

        def text_matches(text: str) -> bool:
            if case_sensitive:
                return keyword in text
            return keyword.lower() in text.lower()

        for i, p in enumerate(doc.paragraphs):
            if text_matches(p.text):
                matches.append({
                    "type": "paragraph",
                    "index": i,
                    "text": p.text,
                    "style": getattr(p.style, "name", None),
                })

        for ti, table in enumerate(doc.tables):
            for ri, row in enumerate(table.rows):
                for ci, cell in enumerate(row.cells):
                    if text_matches(cell.text):
                        matches.append({
                            "type": "table_cell",
                            "table_index": ti,
                            "row_index": ri,
                            "col_index": ci,
                            "text": cell.text,
                        })

        return matches

    def _locate_placeholder(self, doc, placeholder: str) -> list[dict]:
        """精确查找某个占位符名称（不含括号）出现的位置。"""
        matches: list[dict] = []
        targets = [
            f"{{{{{placeholder}}}}}",
            f"【{placeholder}】",
            f"<<{placeholder}>>",
        ]

        for i, p in enumerate(doc.paragraphs):
            for t in targets:
                if t in p.text:
                    matches.append({
                        "type": "paragraph",
                        "index": i,
                        "text": p.text,
                        "matched_token": t,
                    })
                    break

        for ti, table in enumerate(doc.tables):
            for ri, row in enumerate(table.rows):
                for ci, cell in enumerate(row.cells):
                    for t in targets:
                        if t in cell.text:
                            matches.append({
                                "type": "table_cell",
                                "table_index": ti,
                                "row_index": ri,
                                "col_index": ci,
                                "text": cell.text,
                                "matched_token": t,
                            })
                            break

        return matches

    def _locate_table_header(self, doc, headers: list[str]) -> list[dict]:
        """找到包含指定表头的表格及其行号。"""
        matches: list[dict] = []
        normalized = [h.strip() for h in headers]

        for ti, table in enumerate(doc.tables):
            for ri, row in enumerate(table.rows):
                row_texts = [cell.text.strip() for cell in row.cells]
                found = [h for h in normalized if h in row_texts]
                if found:
                    matches.append({
                        "type": "table_header_row",
                        "table_index": ti,
                        "row_index": ri,
                        "row_texts": row_texts,
                        "matched_headers": found,
                        "match_score": len(found),
                    })

        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches

    def _locate_all_placeholders(self, doc) -> list[dict]:
        """扫描文档内所有占位符并返回位置。"""
        matches: list[dict] = []

        def scan(text: str, location: dict):
            for pat in _PLACEHOLDER_PATTERNS:
                for m in re.finditer(pat, text):
                    matches.append({
                        "placeholder": m.group(0),
                        "key": m.group(1).strip(),
                        **location,
                    })

        for i, p in enumerate(doc.paragraphs):
            scan(p.text, {"type": "paragraph", "index": i})

        for ti, table in enumerate(doc.tables):
            for ri, row in enumerate(table.rows):
                for ci, cell in enumerate(row.cells):
                    scan(cell.text, {
                        "type": "table_cell",
                        "table_index": ti,
                        "row_index": ri,
                        "col_index": ci,
                    })

        return matches
