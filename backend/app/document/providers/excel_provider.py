from __future__ import annotations

import os
from typing import Any

from app.domain.capability_types import CapabilityType
from app.domain.document_types import DocumentType
from app.document.adapters.excel_adapter import ExcelAdapter
from app.document.providers.base import BaseDocumentProvider, ProviderResult


class ExcelProvider(BaseDocumentProvider):
    document_type = DocumentType.EXCEL

    def __init__(self) -> None:
        self.adapter = ExcelAdapter()

    def supported_capabilities(self) -> set[CapabilityType]:
        return {
            CapabilityType.READ,
            CapabilityType.EXTRACT,
            CapabilityType.LOCATE,
            CapabilityType.FILL,
            CapabilityType.UPDATE_TABLE,
            CapabilityType.VALIDATE,
            CapabilityType.WRITE,
        }

    def read(self, file_path: str, **kwargs) -> ProviderResult:
        try:
            workbook = self.adapter.load(file_path)
            sheets = self.adapter.list_sheets(workbook)

            preview: dict[str, Any] = {}
            for sheet_name in sheets[:3]:
                ws = self.adapter.get_sheet(workbook, sheet_name)
                preview[sheet_name] = self.adapter.read_range(ws, "A1:E10")

            return ProviderResult(
                success=True,
                message="Excel document read successfully",
                data={
                    "sheet_names": sheets,
                    "preview": preview,
                },
                raw={"provider": "excel"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to read excel document: {e}")

    def extract(self, file_path: str, **kwargs) -> ProviderResult:
        """
        支持三种模式：
        1. 指定 sheet + range
        2. 指定 headers 自动抽表
        3. 默认返回 sheet 预览
        """
        try:
            workbook = self.adapter.load(file_path)
            sheet_name = kwargs.get("sheet_name")
            cell_range = kwargs.get("cell_range")
            headers = kwargs.get("headers")

            ws = self.adapter.get_sheet(workbook, sheet_name)

            if sheet_name is None:
                sheet_name = ws.title

            if headers:
                records = self.adapter.extract_table_by_header(ws, headers)
                return ProviderResult(
                    success=True,
                    message="Excel structured data extracted by headers",
                    data={
                        "sheet_name": sheet_name,
                        "mode": "header_table",
                        "headers": headers,
                        "records": records,
                    },
                    raw={"provider": "excel"},
                )

            if cell_range:
                values = self.adapter.read_range(ws, cell_range)
                return ProviderResult(
                    success=True,
                    message="Excel range extracted successfully",
                    data={
                        "sheet_name": sheet_name,
                        "mode": "range",
                        "range": cell_range,
                        "values": values,
                    },
                    raw={"provider": "excel"},
                )

            used = self.adapter.read_used_range(ws)
            return ProviderResult(
                success=True,
                message="Excel used range extracted successfully",
                data={
                    "sheet_name": sheet_name,
                    "mode": "used_range",
                    "values": used[:50],
                },
                raw={"provider": "excel"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to extract excel data: {e}")

    def locate(self, file_path: str, **kwargs) -> ProviderResult:
        """
        支持：
        - headers: 查表头行
        - text: 查找某个值出现的位置
        """
        try:
            workbook = self.adapter.load(file_path)
            sheet_name = kwargs.get("sheet_name")
            headers = kwargs.get("headers")
            text = kwargs.get("text")

            ws = self.adapter.get_sheet(workbook, sheet_name)
            if sheet_name is None:
                sheet_name = ws.title

            if headers:
                row_idx = self.adapter.find_header_row(ws, headers)
                return ProviderResult(
                    success=True,
                    message="Excel headers located",
                    data={
                        "sheet_name": sheet_name,
                        "headers": headers,
                        "header_row": row_idx,
                    },
                    raw={"provider": "excel"},
                )

            if text is not None:
                matches: list[dict[str, Any]] = []
                target = str(text).strip()
                partial = bool(kwargs.get("partial_match", False))
                case_sensitive = bool(kwargs.get("case_sensitive", False))

                cmp_target = target if case_sensitive else target.lower()

                for row in ws.iter_rows():
                    for cell in row:
                        cell_str = "" if cell.value is None else str(cell.value).strip()
                        cmp_cell = cell_str if case_sensitive else cell_str.lower()
                        hit = (cmp_target in cmp_cell) if partial else (cmp_target == cmp_cell)
                        if hit:
                            matches.append(
                                {
                                    "coordinate": cell.coordinate,
                                    "row": cell.row,
                                    "column": cell.column,
                                    "value": cell.value,
                                }
                            )
                return ProviderResult(
                    success=True,
                    message="Excel text located",
                    data={
                        "sheet_name": sheet_name,
                        "text": text,
                        "partial_match": partial,
                        "case_sensitive": case_sensitive,
                        "matches": matches,
                    },
                    raw={"provider": "excel"},
                )

            return ProviderResult(
                success=False,
                message="No locate parameters provided for excel document",
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to locate in excel: {e}")

    def fill(self, file_path: str, **kwargs) -> ProviderResult:
        """
        支持：
        - cell_values: {"B2": "张三", "C2": 100}
        - rows_payload: {"sheet_name": "...", "start_row": 2, "start_col": 1, "rows": [[...], [...]]}
        """
        try:
            workbook = self.adapter.load(file_path)
            output_path = kwargs.get("output_path") or self._default_output_path(file_path)

            sheet_name = kwargs.get("sheet_name")
            ws = self.adapter.get_sheet(workbook, sheet_name)

            cell_values: dict[str, Any] = kwargs.get("cell_values", {})
            for cell_ref, value in cell_values.items():
                self.adapter.write_cell(ws, cell_ref, value)

            rows_payload = kwargs.get("rows_payload")
            if rows_payload:
                start_row = int(rows_payload["start_row"])
                start_col = int(rows_payload["start_col"])
                rows = rows_payload["rows"]
                self.adapter.write_rows(ws, start_row, start_col, rows)

            saved = self.adapter.save(workbook, output_path)

            return ProviderResult(
                success=True,
                message="Excel document filled successfully",
                data={
                    "sheet_name": ws.title,
                    "cell_values_count": len(cell_values),
                    "rows_written": 0 if not rows_payload else len(rows_payload["rows"]),
                },
                output_path=saved,
                raw={"provider": "excel"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to fill excel document: {e}")

    def update_table(self, file_path: str, **kwargs) -> ProviderResult:
        """
        按表头追加行，支持两种模式：
        - append_by_header: 传入 headers + rows(list[dict])，自动定位表尾追加
        - 其余参数：退化为 fill()

        params:
        - headers    : list[str]       — 表头列表（用于定位表格）
        - rows       : list[dict]      — 每行数据，key 为表头名
        - sheet_name : str             — 可选，指定 sheet
        - output_path: str             — 输出路径
        """
        headers: list[str] | None = kwargs.get("headers")
        rows: list[dict] | None = kwargs.get("rows")

        if not headers or not rows:
            # 无表头模式：退化为 fill
            return self.fill(file_path=file_path, **kwargs)

        try:
            workbook = self.adapter.load(file_path)
            output_path = kwargs.get("output_path") or self._default_output_path(file_path)
            sheet_name = kwargs.get("sheet_name")
            ws = self.adapter.get_sheet(workbook, sheet_name)

            written = self.adapter.append_rows_by_header(ws, headers, rows)
            if written == 0:
                return ProviderResult(
                    success=False,
                    message=f"Headers not found in sheet '{ws.title}': {headers}",
                )

            saved = self.adapter.save(workbook, output_path)
            return ProviderResult(
                success=True,
                message=f"Appended {written} row(s) to table in '{ws.title}'",
                data={
                    "sheet_name": ws.title,
                    "headers": headers,
                    "rows_appended": written,
                },
                output_path=saved,
                raw={"provider": "excel"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to update table: {e}")

    def validate(self, file_path: str, **kwargs) -> ProviderResult:
        try:
            workbook = self.adapter.load(file_path)
            sheet_name = kwargs.get("sheet_name")
            required_cells: list[str] = kwargs.get("required_cells", [])
            ws = self.adapter.get_sheet(workbook, sheet_name)

            missing: list[str] = []
            for cell_ref in required_cells:
                if ws[cell_ref].value in (None, ""):
                    missing.append(cell_ref)

            return ProviderResult(
                success=True,
                message="Excel validation completed",
                data={
                    "sheet_name": ws.title,
                    "required_cells": required_cells,
                    "missing_cells": missing,
                    "valid": len(missing) == 0,
                },
                raw={"provider": "excel"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to validate excel document: {e}")

    def write(self, file_path: str, **kwargs) -> ProviderResult:
        """
        暂时等价于 fill / save，保留能力接口。
        """
        return self.fill(file_path=file_path, **kwargs)

    @staticmethod
    def _default_output_path(file_path: str) -> str:
        base, ext = os.path.splitext(file_path)
        return f"{base}_filled{ext}"