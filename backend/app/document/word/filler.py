from __future__ import annotations

import os
from docx import Document


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
            for key, value in mapping.items():
                token = f"{{{{{key}}}}}"
                if token in p.text:
                    for run in p.runs:
                        before = run.text
                        run.text = run.text.replace(token, str(value))
                        if before != run.text:
                            replace_count += 1

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for key, value in mapping.items():
                        token = f"{{{{{key}}}}}"
                        if token in cell.text:
                            before = cell.text
                            cell.text = cell.text.replace(token, str(value))
                            if before != cell.text:
                                replace_count += 1

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)

        return {
            "output_path": output_path,
            "replace_count": replace_count,
            "used_mapping_keys": list(mapping.keys()),
        }