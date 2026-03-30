from __future__ import annotations

from typing import Any

from app.domain.capability_types import CapabilityType
from app.domain.document_types import DocumentType
from app.document.excel.analyzer import ExcelAnalyzer
from app.document.excel.locator import ExcelLocator
from app.document.excel.mapper import ExcelMapper
from app.document.excel.reader import ExcelReader
from app.document.excel.writer import ExcelWriter
from app.document.providers.base import BaseDocumentProvider, ProviderResult


class ExcelProvider(BaseDocumentProvider):
    document_type = DocumentType.EXCEL
    SUPPORTED_CAPABILITIES = {
        CapabilityType.READ,
        CapabilityType.EXTRACT,
        CapabilityType.LOCATE,
        CapabilityType.FILL,
        CapabilityType.UPDATE_TABLE,
        CapabilityType.VALIDATE,
        CapabilityType.WRITE,
        CapabilityType.COMPARE,
    }

    def __init__(self) -> None:
        self.reader = ExcelReader()
        self.analyzer = ExcelAnalyzer()
        self.locator = ExcelLocator()
        self.mapper = ExcelMapper()
        self.writer = ExcelWriter()

    def supported_capabilities(self) -> set[CapabilityType]:
        return set(self.SUPPORTED_CAPABILITIES)

    def read(self, file_path: str, **kwargs) -> ProviderResult:
        try:
            workbook = self.reader.adapter.load(file_path)
            sheets = self.reader.adapter.list_sheets(workbook)

            preview: dict[str, Any] = {}
            for sheet_name in sheets[:3]:
                ws = self.reader.adapter.get_sheet(workbook, sheet_name)
                preview[sheet_name] = self.reader.adapter.read_range(ws, "A1:E10")

            return ProviderResult.ok(
                message="Excel document read successfully",
                data={
                    "sheet_names": sheets,
                    "preview": preview,
                },
                capability=CapabilityType.READ.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "excel"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to read excel document: {e}",
                error_code="EXCEL_READ_FAILED",
                capability=CapabilityType.READ.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def extract(self, file_path: str, **kwargs) -> ProviderResult:
        """
        支持三种模式：
        1. 指定 sheet + range
        2. 指定 headers 自动抽表
        3. 默认返回 sheet 预览
        """
        try:
            workbook = self.reader.adapter.load(file_path)
            sheet_name = kwargs.get("sheet_name")
            cell_range = kwargs.get("cell_range")
            headers = kwargs.get("headers")
            target_fields = kwargs.get("target_fields")

            ws = self.reader.adapter.get_sheet(workbook, sheet_name)

            if sheet_name is None:
                sheet_name = ws.title

            if headers:
                records = self.analyzer.extract_table_by_header(
                    file_path=file_path,
                    headers=headers,
                    sheet_name=sheet_name,
                )
                mapped_records = self.mapper.map_rows(records, target_fields) if target_fields else records
                return ProviderResult.ok(
                    message="Excel structured data extracted by headers",
                    data={
                        "sheet_name": sheet_name,
                        "mode": "header_table",
                        "headers": headers,
                        "records": mapped_records,
                    },
                    capability=CapabilityType.EXTRACT.value,
                    provider=self.provider_name,
                    document_type=self.document_type.value,
                    raw={"provider": "excel"},
                )

            if cell_range:
                values = self.reader.adapter.read_range(ws, cell_range)
                return ProviderResult.ok(
                    message="Excel range extracted successfully",
                    data={
                        "sheet_name": sheet_name,
                        "mode": "range",
                        "range": cell_range,
                        "values": values,
                    },
                    capability=CapabilityType.EXTRACT.value,
                    provider=self.provider_name,
                    document_type=self.document_type.value,
                    raw={"provider": "excel"},
                )

            used = self.reader.read_used_range(file_path=file_path, sheet_name=sheet_name)
            return ProviderResult.ok(
                message="Excel used range extracted successfully",
                data={
                    "sheet_name": sheet_name,
                    "mode": "used_range",
                    "values": used[:50],
                },
                capability=CapabilityType.EXTRACT.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "excel"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to extract excel data: {e}",
                error_code="EXCEL_EXTRACT_FAILED",
                capability=CapabilityType.EXTRACT.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def locate(self, file_path: str, **kwargs) -> ProviderResult:
        """
        支持：
        - headers: 查表头行
        - text: 查找某个值出现的位置
        """
        try:
            workbook = self.reader.adapter.load(file_path)
            sheet_name = kwargs.get("sheet_name")
            headers = kwargs.get("headers")
            text = kwargs.get("text")

            ws = self.reader.adapter.get_sheet(workbook, sheet_name)
            if sheet_name is None:
                sheet_name = ws.title

            if headers:
                row_idx = self.locator.find_header_row(
                    file_path=file_path,
                    headers=headers,
                    sheet_name=sheet_name,
                )
                return ProviderResult.ok(
                    message="Excel headers located",
                    data={
                        "sheet_name": sheet_name,
                        "headers": headers,
                        "header_row": row_idx,
                    },
                    capability=CapabilityType.LOCATE.value,
                    provider=self.provider_name,
                    document_type=self.document_type.value,
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
                return ProviderResult.ok(
                    message="Excel text located",
                    data={
                        "sheet_name": sheet_name,
                        "text": text,
                        "partial_match": partial,
                        "case_sensitive": case_sensitive,
                        "matches": matches,
                    },
                    capability=CapabilityType.LOCATE.value,
                    provider=self.provider_name,
                    document_type=self.document_type.value,
                    raw={"provider": "excel"},
                )

            return ProviderResult.fail(
                message="No locate parameters provided for excel document",
                error_code="EXCEL_LOCATE_PARAMS_MISSING",
                capability=CapabilityType.LOCATE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to locate in excel: {e}",
                error_code="EXCEL_LOCATE_FAILED",
                capability=CapabilityType.LOCATE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def map_transform(self, rows: list[dict[str, Any]], target_fields: list[str]) -> ProviderResult:
        try:
            mapped = self.mapper.map_rows(rows=rows, target_fields=target_fields)
            return ProviderResult.ok(
                message="Excel rows mapped successfully",
                data={"mapped_rows": mapped, "target_fields": target_fields},
                capability="mapper",
                provider=self.provider_name,
                document_type=self.document_type.value,
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to map excel rows: {e}",
                error_code="EXCEL_MAP_FAILED",
                capability="mapper",
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def fill(self, file_path: str, **kwargs) -> ProviderResult:
        """
        支持：
        - cell_values: {"B2": "张三", "C2": 100}
        - rows_payload: {"sheet_name": "...", "start_row": 2, "start_col": 1, "rows": [[...], [...]]}
        """
        # fill 兼容能力：内部转到 write 路径
        return self.write(file_path=file_path, **kwargs)

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
            return self.write(file_path=file_path, **kwargs)

        try:
            workbook = self.reader.adapter.load(file_path)
            output_path = kwargs.get("output_path") or self._default_output_path(file_path)
            sheet_name = kwargs.get("sheet_name")
            ws = self.reader.adapter.get_sheet(workbook, sheet_name)

            written = self.reader.adapter.append_rows_by_header(ws, headers, rows)
            if written == 0:
                return ProviderResult.fail(
                    message=f"Headers not found in sheet '{ws.title}': {headers}",
                    error_code="EXCEL_HEADERS_NOT_FOUND",
                    capability=CapabilityType.UPDATE_TABLE.value,
                    provider=self.provider_name,
                    document_type=self.document_type.value,
                )

            saved = self.reader.adapter.save(workbook, output_path)
            return ProviderResult.ok(
                message=f"Appended {written} row(s) to table in '{ws.title}'",
                data={
                    "sheet_name": ws.title,
                    "headers": headers,
                    "rows_appended": written,
                },
                output_path=saved,
                capability=CapabilityType.UPDATE_TABLE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "excel"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to update table: {e}",
                error_code="EXCEL_UPDATE_TABLE_FAILED",
                capability=CapabilityType.UPDATE_TABLE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def validate(self, file_path: str, **kwargs) -> ProviderResult:
        try:
            workbook = self.reader.adapter.load(file_path)
            sheet_name = kwargs.get("sheet_name")
            required_cells: list[str] = kwargs.get("required_cells", [])
            ws = self.reader.adapter.get_sheet(workbook, sheet_name)

            missing: list[str] = []
            for cell_ref in required_cells:
                if ws[cell_ref].value in (None, ""):
                    missing.append(cell_ref)

            return ProviderResult.ok(
                message="Excel validation completed",
                data={
                    "sheet_name": ws.title,
                    "required_cells": required_cells,
                    "missing_cells": missing,
                    "valid": len(missing) == 0,
                },
                capability=CapabilityType.VALIDATE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "excel"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to validate excel document: {e}",
                error_code="EXCEL_VALIDATE_FAILED",
                capability=CapabilityType.VALIDATE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def write(self, file_path: str, **kwargs) -> ProviderResult:
        try:
            output_path = kwargs.get("output_path") or self._default_output_path(file_path)
            sheet_name = kwargs.get("sheet_name")

            rows_payload = kwargs.get("rows_payload")
            cell_values: dict[str, Any] = kwargs.get("cell_values", {})

            workbook = self.reader.adapter.load(file_path)
            ws = self.reader.adapter.get_sheet(workbook, sheet_name)

            if cell_values:
                # 写单元格场景
                for cell_ref, value in cell_values.items():
                    self.reader.adapter.write_cell(ws, cell_ref, value)
                saved = self.reader.adapter.save(workbook, output_path)
                return ProviderResult.ok(
                    message="Excel cells written successfully",
                    data={"sheet_name": ws.title, "cell_values_count": len(cell_values)},
                    output_path=saved,
                    capability=CapabilityType.WRITE.value,
                    provider=self.provider_name,
                    document_type=self.document_type.value,
                    raw={"provider": "excel"},
                )

            if rows_payload:
                start_row = int(rows_payload["start_row"])
                start_col = int(rows_payload["start_col"])
                rows = rows_payload["rows"]
                saved = self.writer.write_rows(
                    file_path=file_path,
                    start_row=start_row,
                    start_col=start_col,
                    rows=rows,
                    output_path=output_path,
                    sheet_name=sheet_name,
                )
                return ProviderResult.ok(
                    message="Excel rows written successfully",
                    data={"sheet_name": sheet_name or ws.title, "rows_written": len(rows)},
                    output_path=saved,
                    capability=CapabilityType.WRITE.value,
                    provider=self.provider_name,
                    document_type=self.document_type.value,
                    raw={"provider": "excel"},
                )

            saved = self.reader.adapter.save(workbook, output_path)
            return ProviderResult.ok(
                message="Excel document written successfully",
                data={"sheet_name": ws.title, "rows_written": 0, "cell_values_count": 0},
                output_path=saved,
                capability=CapabilityType.WRITE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "excel"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to write excel document: {e}",
                error_code="EXCEL_WRITE_FAILED",
                capability=CapabilityType.WRITE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def compare(self, left_file_path: str, right_file_path: str, **kwargs) -> ProviderResult:
        try:
            left_wb = self.reader.adapter.load(left_file_path)
            right_wb = self.reader.adapter.load(right_file_path)

            left_sheets = self.reader.adapter.list_sheets(left_wb)
            right_sheets = self.reader.adapter.list_sheets(right_wb)
            common_sheets = sorted(set(left_sheets) & set(right_sheets))

            differences: list[dict[str, Any]] = []
            for sheet in common_sheets:
                left_ws = self.reader.adapter.get_sheet(left_wb, sheet)
                right_ws = self.reader.adapter.get_sheet(right_wb, sheet)
                left_values = self.reader.adapter.read_used_range(left_ws)
                right_values = self.reader.adapter.read_used_range(right_ws)
                if left_values != right_values:
                    differences.append(
                        {
                            "sheet_name": sheet,
                            "left_rows": len(left_values),
                            "right_rows": len(right_values),
                        }
                    )

            result = {
                "left_file": left_file_path,
                "right_file": right_file_path,
                "left_sheets": left_sheets,
                "right_sheets": right_sheets,
                "common_sheets": common_sheets,
                "differences": differences,
                "identical": len(differences) == 0 and left_sheets == right_sheets,
            }
            return ProviderResult.ok(
                message="Excel documents compared successfully",
                data=result,
                capability=CapabilityType.COMPARE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "excel"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to compare excel documents: {e}",
                error_code="EXCEL_COMPARE_FAILED",
                capability=CapabilityType.COMPARE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

