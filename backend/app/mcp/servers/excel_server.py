from __future__ import annotations

from typing import List

from app.document.adapters.excel_adapter import ExcelAdapter
from app.mcp.servers.base import BaseMCPServer
from app.mcp.types import ServerInfo, ToolCall, ToolResult, ToolSchema


class ExcelServer(BaseMCPServer):
    def __init__(self, excel_adapter: ExcelAdapter):
        super().__init__(ServerInfo(name="excel_server", description="Excel document operations"))
        self.excel_adapter = excel_adapter

    def list_tools(self) -> List[ToolSchema]:
        return [
            ToolSchema(
                name="excel.read_preview",
                description="Read sheet names and preview rows from an excel file.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"},
                        "max_rows": {"type": "integer"},
                        "max_cols": {"type": "integer"},
                    },
                    "required": ["file_path"],
                },
            )
        ]

    def call_tool(self, call: ToolCall) -> ToolResult:
        try:
            args = call.arguments

            if call.name == "excel.read_preview":
                file_path = args["file_path"]
                sheet_name = args.get("sheet_name")
                max_rows = int(args.get("max_rows", 30))
                max_cols = int(args.get("max_cols", 20))

                workbook = self.excel_adapter.load(file_path)
                sheets = self.excel_adapter.list_sheets(workbook)
                worksheet = self.excel_adapter.get_sheet(workbook, sheet_name)
                used = self.excel_adapter.read_used_range(worksheet)

                clipped = []
                for row in used[:max_rows]:
                    clipped.append(row[:max_cols])

                return ToolResult(
                    call_id=call.id,
                    tool_name=call.name,
                    success=True,
                    content={
                        "sheet_names": sheets,
                        "active_sheet": worksheet.title,
                        "preview": clipped,
                    },
                )

            return ToolResult(
                call_id=call.id,
                tool_name=call.name,
                success=False,
                content=None,
                error=f"Unsupported tool: {call.name}",
            )

        except Exception as e:
            return ToolResult(
                call_id=call.id,
                tool_name=call.name,
                success=False,
                content=None,
                error=str(e),
            )
