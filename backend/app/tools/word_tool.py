from docx import Document


class WordTool:
    FORM_FIELDS = [
        "团支部",
        "团员编号",
        "姓名",
        "性别",
        "出生年月",
        "民族",
        "籍贯",
        "入团时间",
        "工作职务",
        "申请入党时间",
        "被推荐人优缺点",
        "团支部意见",
    ]

    SPECIAL_RULES = {
        "团支部": "right",
        "团员编号": "right",
        "姓名": "right",
        "性别": "right",
        "出生年月": "right",
        "民族": "right",
        "籍贯": "right",
        "入团时间": "right",
        "工作职务": "right",
        "申请入党时间": "right",
        "被推荐人优缺点": "below",
        "团支部意见": "below",
    }

    def get_supported_form_fields(self) -> list[str]:
        return self.FORM_FIELDS

    def fill_review_form(self, template_path: str, context: dict, output_path: str) -> str:
        doc = Document(template_path)

        for table in doc.tables:
            self._fill_table(table, context)

        doc.save(output_path)
        return output_path

    def _normalize(self, text: str) -> str:
        if text is None:
            return ""
        return "".join(str(text).split())

    def _set_cell_text(self, cell, value: str) -> None:
        cell.text = "" if value is None else str(value)

    def _fill_table(self, table, context: dict) -> None:
        rows = table.rows
        row_count = len(rows)

        for i, row in enumerate(rows):
            cells = row.cells
            col_count = len(cells)

            for j, cell in enumerate(cells):
                current = self._normalize(cell.text)

                for field_name, field_value in context.items():
                    normalized_field = self._normalize(field_name)

                    if not normalized_field:
                        continue

                    if normalized_field in current:
                        rule = self.SPECIAL_RULES.get(field_name, "right")

                        if rule == "right":
                            if j + 1 < col_count:
                                target_cell = row.cells[j + 1]
                                self._set_cell_text(target_cell, field_value)
                                break

                        if rule == "below":
                            if i + 1 < row_count:
                                target_cell = rows[i + 1].cells[j]
                                self._set_cell_text(target_cell, field_value)
                                break