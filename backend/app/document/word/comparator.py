"""
Word Document Comparator module.
"""
from __future__ import annotations

import difflib

from docx import Document


class WordComparator:
    """
    对比两个 Word 文档，返回段落级别的差异。

    结果包含：
    - added   : 仅在右侧文档出现的段落
    - removed : 仅在左侧文档出现的段落
    - changed : 行号位置发生变化的段落对
    - summary : 统计数字
    """

    def compare(
        self,
        left_file_path: str,
        right_file_path: str,
        include_tables: bool = True,
        **kwargs,
    ) -> dict:
        left_doc = Document(left_file_path)
        right_doc = Document(right_file_path)

        left_paras = self._extract_text_blocks(left_doc, include_tables)
        right_paras = self._extract_text_blocks(right_doc, include_tables)

        diff = self._diff(left_paras, right_paras)

        return {
            "left_file": left_file_path,
            "right_file": right_file_path,
            "added": diff["added"],
            "removed": diff["removed"],
            "changed": diff["changed"],
            "unchanged_count": diff["unchanged_count"],
            "summary": {
                "added_count": len(diff["added"]),
                "removed_count": len(diff["removed"]),
                "changed_count": len(diff["changed"]),
                "unchanged_count": diff["unchanged_count"],
                "left_total": len(left_paras),
                "right_total": len(right_paras),
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_text_blocks(self, doc, include_tables: bool) -> list[str]:
        blocks: list[str] = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                blocks.append(text)

        if include_tables:
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells)
                    if row_text.strip(" |"):
                        blocks.append(f"[TABLE] {row_text}")

        return blocks

    def _diff(self, left: list[str], right: list[str]) -> dict:
        matcher = difflib.SequenceMatcher(None, left, right, autojunk=False)

        added: list[dict] = []
        removed: list[dict] = []
        changed: list[dict] = []
        unchanged_count = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                unchanged_count += i2 - i1
            elif tag == "insert":
                for j in range(j1, j2):
                    added.append({"right_index": j, "text": right[j]})
            elif tag == "delete":
                for i in range(i1, i2):
                    removed.append({"left_index": i, "text": left[i]})
            elif tag == "replace":
                left_chunk = left[i1:i2]
                right_chunk = right[j1:j2]
                # 逐行配对，多余的归入 added/removed
                for k in range(max(len(left_chunk), len(right_chunk))):
                    l_text = left_chunk[k] if k < len(left_chunk) else None
                    r_text = right_chunk[k] if k < len(right_chunk) else None
                    if l_text and r_text:
                        changed.append({
                            "left_index": i1 + k,
                            "right_index": j1 + k,
                            "left_text": l_text,
                            "right_text": r_text,
                            "similarity": round(
                                difflib.SequenceMatcher(None, l_text, r_text).ratio(), 2
                            ),
                        })
                    elif l_text:
                        removed.append({"left_index": i1 + k, "text": l_text})
                    elif r_text:
                        added.append({"right_index": j1 + k, "text": r_text})

        return {
            "added": added,
            "removed": removed,
            "changed": changed,
            "unchanged_count": unchanged_count,
        }
