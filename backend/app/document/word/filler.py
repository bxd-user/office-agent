from __future__ import annotations

import os
import re

from docx import Document
from docx.oxml.ns import qn


_PLACEHOLDER_TRIGGERS = ("{{", "【", "<<")


class WordFiller:
    def write_kv_pairs_to_template(
        self,
        file_path: str,
        mapping: dict[str, str],
        output_path: str,
    ):
        doc = Document(file_path)
        replace_count = 0

        for p in doc.paragraphs:
            replace_count += self._replace_in_paragraph(p, mapping)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        replace_count += self._replace_in_paragraph(para, mapping)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)

        return {
            "output_path": output_path,
            "replace_count": replace_count,
            "used_mapping_keys": list(mapping.keys()),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _replace_in_paragraph(self, paragraph, mapping: dict[str, str]) -> int:
        """
        替换段落中的占位符，正确处理跨 run 情况。

        策略：若段落文本含有占位符触发字符，先将所有 run 合并到首 run
        （保留首 run 的字体/样式），执行替换后返回替换次数。
        """
        full_text = paragraph.text
        if not any(trigger in full_text for trigger in _PLACEHOLDER_TRIGGERS):
            return 0

        # 归一化：将跨 run 分散的文本合并到第一个 run
        self._normalize_runs(paragraph)

        count = 0
        for run in paragraph.runs:
            original = run.text
            new_text = original
            for key, value in mapping.items():
                token = f"{{{{{key}}}}}"
                new_text = new_text.replace(token, str(value))
            if new_text != original:
                run.text = new_text
                count += 1
        return count

    @staticmethod
    def _normalize_runs(paragraph) -> None:
        """
        将段落所有 run 的文本合并到首 run，消除跨 run 的占位符分裂问题。
        只在段落含有占位符触发符时调用，避免不必要的格式损失。
        """
        runs = paragraph.runs
        if len(runs) <= 1:
            return

        full_text = "".join(r.text for r in runs)
        runs[0].text = full_text
        for run in runs[1:]:
            run.text = ""
