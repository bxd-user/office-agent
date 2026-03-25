from __future__ import annotations

from copy import deepcopy
import os
from docx import Document
from docx.text.paragraph import Paragraph
from docx.text.run import Run


class WordWriter:
    def _find_reference_paragraph_and_run(self, doc: Document) -> tuple[Paragraph | None, Run | None]:
        for paragraph in reversed(doc.paragraphs):
            if not paragraph.text or not paragraph.text.strip():
                continue
            for run in reversed(paragraph.runs):
                if run.text and run.text.strip():
                    return paragraph, run
            return paragraph, None

        for table in reversed(doc.tables):
            for row in reversed(table.rows):
                for cell in reversed(row.cells):
                    for paragraph in reversed(cell.paragraphs):
                        if not paragraph.text or not paragraph.text.strip():
                            continue
                        for run in reversed(paragraph.runs):
                            if run.text and run.text.strip():
                                return paragraph, run
                        return paragraph, None

        return None, None

    def _copy_run_style(self, src: Run, dst: Run) -> None:
        dst.bold = src.bold
        dst.italic = src.italic
        dst.underline = src.underline
        dst.style = src.style

        dst.font.name = src.font.name
        dst.font.size = src.font.size
        dst.font.bold = src.font.bold
        dst.font.italic = src.font.italic
        dst.font.underline = src.font.underline
        dst.font.highlight_color = src.font.highlight_color
        dst.font.strike = src.font.strike
        dst.font.subscript = src.font.subscript
        dst.font.superscript = src.font.superscript

        if src.font.color is not None:
            dst.font.color.rgb = src.font.color.rgb

        src_rpr = src._element.rPr
        if src_rpr is not None:
            dst._element.rPr = deepcopy(src_rpr)

    def replace_text(self, file_path: str, replacements: dict[str, str], output_path: str):
        doc = Document(file_path)

        for p in doc.paragraphs:
            for old, new in replacements.items():
                if old in p.text:
                    for run in p.runs:
                        run.text = run.text.replace(old, new)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for old, new in replacements.items():
                        if old in cell.text:
                            cell.text = cell.text.replace(old, new)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)

        return {
            "output_path": output_path,
            "replacements_count": len(replacements),
        }

    def append_text(self, file_path: str, append_text: str, output_path: str):
        doc = Document(file_path)

        text = (append_text or "").strip()
        if text:
            reference_paragraph, reference_run = self._find_reference_paragraph_and_run(doc)
            doc.add_paragraph("")
            new_paragraph = doc.add_paragraph()
            if reference_paragraph is not None:
                new_paragraph.style = reference_paragraph.style

            new_run = new_paragraph.add_run(text)
            if reference_run is not None:
                self._copy_run_style(reference_run, new_run)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)

        return {
            "output_path": output_path,
            "appended": bool(text),
        }


DocxWriter = WordWriter