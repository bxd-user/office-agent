from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from tools.base import (
    BaseInspectTool,
    BaseValidateTool,
    Capability,
    FileType,
    ToolContext,
    ToolInput,
    ToolResult,
    ToolValidationError,
)
from tools.common_tools import ensure_excel_file


# =========================
# 输入模型
# =========================

@dataclass(slots=True)
class ExcelFileInput(ToolInput):
    """最基础的 Excel 文件输入。"""

    file_path: str

    def validate_basic(self) -> None:
        if not self.file_path:
            raise ToolValidationError("file_path is required")


@dataclass(slots=True)
class ExcelSheetInput(ExcelFileInput):
    """带 sheet 选择的 Excel 输入。

    sheet_name 和 sheet_index 二选一，默认都不传时使用 active sheet。
    """

    sheet_name: Optional[str] = None
    sheet_index: Optional[int] = None


@dataclass(slots=True)
class ReadExcelRecordsInput(ExcelSheetInput):
    """读取 Excel 为 records 的输入。

    假设第一行是表头。
    """

    header_row: int = 1
    start_row: Optional[int] = None
    max_rows: Optional[int] = None
    drop_empty_rows: bool = True
    trim_strings: bool = True


@dataclass(slots=True)
class GetExcelHeadersInput(ExcelSheetInput):
    """只读取表头。"""

    header_row: int = 1
    trim_strings: bool = True


@dataclass(slots=True)
class InspectExcelStructureInput(ExcelSheetInput):
    """读取工作簿/工作表结构信息。"""

    sample_rows: int = 5


@dataclass(slots=True)
class ValidateExcelHeadersInput(ExcelSheetInput):
    """校验 Excel 表头。"""

    expected_headers: List[str] = field(default_factory=list)
    header_row: int = 1
    allow_extra_headers: bool = True
    trim_strings: bool = True


_SUPPORTED_EXTENSIONS = (".xlsx", ".xlsm")


def _validate_excel_file_path(file_path: str) -> None:
    ensure_excel_file(file_path)


# =========================
# 工具类
# =========================

class GetExcelHeadersTool(BaseInspectTool):
    name = "get_excel_headers"
    description = "Read headers from an Excel sheet"
    supported_file_types = (FileType.EXCEL,)
    capabilities = (Capability.READ, Capability.INSPECT, Capability.EXTRACT)
    supported_extensions = _SUPPORTED_EXTENSIONS

    @property
    def input_model(self):
        return GetExcelHeadersInput

    def validate_input(self, params: ToolInput) -> None:
        super().validate_input(params)
        assert isinstance(params, GetExcelHeadersInput)

        params.validate_basic()
        _validate_excel_file_path(params.file_path)

        if params.header_row < 1:
            raise ToolValidationError("header_row must be >= 1")

    def execute(self, params: GetExcelHeadersInput, ctx: ToolContext) -> ToolResult:
        self.ensure_path_supported(params.file_path)
        ctx.log(f"[{self.name}] reading headers from {params.file_path}")

        from adapters.excel_adapter import get_headers, get_worksheet

        sheet = get_worksheet(
            params.file_path,
            sheet_name=params.sheet_name,
            sheet_index=params.sheet_index,
        )
        headers = get_headers(
            file_path=params.file_path,
            header_row=params.header_row,
            sheet_name=sheet.title,
            trim_strings=params.trim_strings,
        )

        data = {
            "file_path": params.file_path,
            "sheet_name": sheet.title,
            "header_row": params.header_row,
            "headers": headers,
        }
        return ToolResult.ok(data=data, message="Excel headers read successfully")


class ReadExcelRecordsTool(BaseInspectTool):
    name = "read_excel_records"
    description = "Read Excel rows as a list of records using the header row"
    supported_file_types = (FileType.EXCEL,)
    capabilities = (Capability.READ, Capability.INSPECT, Capability.EXTRACT)
    supported_extensions = _SUPPORTED_EXTENSIONS

    @property
    def input_model(self):
        return ReadExcelRecordsInput

    def validate_input(self, params: ToolInput) -> None:
        super().validate_input(params)
        assert isinstance(params, ReadExcelRecordsInput)

        params.validate_basic()
        _validate_excel_file_path(params.file_path)

        if params.header_row < 1:
            raise ToolValidationError("header_row must be >= 1")
        if params.start_row is not None and params.start_row < 1:
            raise ToolValidationError("start_row must be >= 1")
        if params.max_rows is not None and params.max_rows < 1:
            raise ToolValidationError("max_rows must be >= 1")

    def execute(self, params: ReadExcelRecordsInput, ctx: ToolContext) -> ToolResult:
        self.ensure_path_supported(params.file_path)
        ctx.log(f"[{self.name}] reading records from {params.file_path}")

        from adapters.excel_adapter import get_headers, get_worksheet, read_sheet_as_records

        sheet = get_worksheet(
            params.file_path,
            sheet_name=params.sheet_name,
            sheet_index=params.sheet_index,
        )

        headers = get_headers(
            file_path=params.file_path,
            header_row=params.header_row,
            sheet_name=sheet.title,
            trim_strings=params.trim_strings,
        )
        records = read_sheet_as_records(
            file_path=params.file_path,
            sheet_name=sheet.title,
            header_row=params.header_row,
            start_row=params.start_row,
            max_rows=params.max_rows,
            drop_empty_rows=params.drop_empty_rows,
            trim_strings=params.trim_strings,
        )

        data = {
            "file_path": params.file_path,
            "sheet_name": sheet.title,
            "header_row": params.header_row,
            "headers": headers,
            "record_count": len(records),
            "records": records,
        }
        return ToolResult.ok(data=data, message="Excel records read successfully")


class InspectExcelStructureTool(BaseInspectTool):
    name = "inspect_excel_structure"
    description = "Inspect workbook and sheet structure information"
    supported_file_types = (FileType.EXCEL,)
    capabilities = (Capability.READ, Capability.INSPECT, Capability.EXTRACT)
    supported_extensions = _SUPPORTED_EXTENSIONS

    @property
    def input_model(self):
        return InspectExcelStructureInput

    def validate_input(self, params: ToolInput) -> None:
        super().validate_input(params)
        assert isinstance(params, InspectExcelStructureInput)

        params.validate_basic()
        _validate_excel_file_path(params.file_path)

        if params.sample_rows < 1:
            raise ToolValidationError("sample_rows must be >= 1")

    def execute(self, params: InspectExcelStructureInput, ctx: ToolContext) -> ToolResult:
        self.ensure_path_supported(params.file_path)
        ctx.log(f"[{self.name}] inspecting workbook {params.file_path}")

        from adapters.excel_adapter import inspect_workbook, inspect_worksheet

        workbook_info = inspect_workbook(params.file_path)
        sheet_info = inspect_worksheet(
            file_path=params.file_path,
            sheet_name=params.sheet_name,
            sheet_index=params.sheet_index,
            header_row=1,
            sample_rows=params.sample_rows,
        )

        data = {
            "file_path": params.file_path,
            "workbook": {
                "sheet_names": workbook_info["sheet_names"],
                "sheet_count": workbook_info["sheet_count"],
                "active_sheet": workbook_info["active_sheet"],
            },
            "sheet": {
                "title": sheet_info["sheet_name"],
                "max_row": sheet_info["max_row"],
                "max_column": sheet_info["max_column"],
                "headers": sheet_info["headers"],
                "sample_records": sheet_info["sample_records"],
            },
        }
        return ToolResult.ok(data=data, message="Excel structure inspected successfully")


class ValidateExcelHeadersTool(BaseValidateTool):
    name = "validate_excel_headers"
    description = "Validate whether expected headers exist in the Excel sheet"
    supported_file_types = (FileType.EXCEL,)
    capabilities = (Capability.READ, Capability.VALIDATE, Capability.INSPECT)
    supported_extensions = _SUPPORTED_EXTENSIONS

    @property
    def input_model(self):
        return ValidateExcelHeadersInput

    def validate_input(self, params: ToolInput) -> None:
        super().validate_input(params)
        assert isinstance(params, ValidateExcelHeadersInput)

        params.validate_basic()
        _validate_excel_file_path(params.file_path)

        if params.header_row < 1:
            raise ToolValidationError("header_row must be >= 1")
        if not params.expected_headers:
            raise ToolValidationError("expected_headers is required")

    def execute(self, params: ValidateExcelHeadersInput, ctx: ToolContext) -> ToolResult:
        self.ensure_path_supported(params.file_path)
        ctx.log(f"[{self.name}] validating headers in {params.file_path}")

        from adapters.excel_adapter import get_headers, get_worksheet

        sheet = get_worksheet(
            params.file_path,
            sheet_name=params.sheet_name,
            sheet_index=params.sheet_index,
        )
        actual_headers = get_headers(
            file_path=params.file_path,
            header_row=params.header_row,
            sheet_name=sheet.title,
            trim_strings=params.trim_strings,
        )

        actual_set = set(actual_headers)
        expected_set = set(params.expected_headers)

        missing_headers = [h for h in params.expected_headers if h not in actual_set]
        extra_headers = [h for h in actual_headers if h not in expected_set]

        passed = len(missing_headers) == 0 and (
            params.allow_extra_headers or len(extra_headers) == 0
        )

        data = {
            "file_path": params.file_path,
            "sheet_name": sheet.title,
            "header_row": params.header_row,
            "expected_headers": params.expected_headers,
            "actual_headers": actual_headers,
            "missing_headers": missing_headers,
            "extra_headers": extra_headers,
            "passed": passed,
        }

        if passed:
            return ToolResult.ok(data=data, message="Excel headers validation passed")

        return ToolResult.fail(
            error="Excel headers validation failed",
            message="Excel headers do not match expected headers",
            data=data,
        )