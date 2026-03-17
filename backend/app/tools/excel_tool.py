from openpyxl import load_workbook


class ExcelTool:
    def read_first_row_as_dict(self, path: str) -> dict:
        wb = load_workbook(path, data_only=True)
        ws = wb.active

        headers = [cell.value for cell in ws[1]]
        values = [cell.value for cell in ws[2]]

        result = {}
        for h, v in zip(headers, values):
            if h is None:
                continue
            key = str(h).strip()
            result[key] = "" if v is None else str(v).strip()

        return result