from __future__ import annotations

import os
import uuid
from typing import List

from app.document.word.adapter import WordAdapter
from app.mcp.servers.base import BaseMCPServer
from app.mcp.types import ServerInfo, ToolCall, ToolResult, ToolSchema

class WordServer(BaseMCPServer):
    def __init__(self, word_adapter: WordAdapter):
        super().__init__(ServerInfo(name="word_server", description="Word document operations"))
        self.word_adapter = word_adapter

    def list_tools(self) -> List[ToolSchema]:
        return [
            ToolSchema(
                name="word.read_text",
                description="Read all plain text paragraphs from a docx file.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"}
                    },
                    "required": ["file_path"]
                },
            ),
            ToolSchema(
                name="word.read_tables",
                description="Read all tables from a docx file and return structured rows.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"}
                    },
                    "required": ["file_path"]
                },
            ),
            ToolSchema(
                name="word.extract_structure",
                description="Extract paragraphs, headings, and tables from a docx file.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"}
                    },
                    "required": ["file_path"]
                },
            ),
            ToolSchema(
                name="word.replace_text",
                description="Replace placeholder text in a docx file and save as a new file.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "replacements": {
                            "type": "object",
                            "additionalProperties": {"type": "string"}
                        },
                        "output_path": {"type": "string"}
                    },
                    "required": ["file_path", "replacements", "output_path"]
                },
            ),
            ToolSchema(
                name="word.append_text",
                description="Append text to the end of a docx file and save as a new file.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "append_text": {"type": "string"},
                        "output_path": {"type": "string"}
                    },
                    "required": ["file_path", "append_text"]
                },
            ),
        ]

    def call_tool(self, call: ToolCall) -> ToolResult:
        try:
            args = call.arguments

            if call.name == "word.read_text":
                content = self.word_adapter.read_text(args["file_path"])
                return ToolResult(
                    call_id=call.id,
                    tool_name=call.name,
                    success=True,
                    content={"text": content},
                )

            if call.name == "word.read_tables":
                tables = self.word_adapter.read_tables(args["file_path"])
                return ToolResult(
                    call_id=call.id,
                    tool_name=call.name,
                    success=True,
                    content={"tables": tables},
                )

            if call.name == "word.extract_structure":
                structure = self.word_adapter.extract_structure(args["file_path"])
                return ToolResult(
                    call_id=call.id,
                    tool_name=call.name,
                    success=True,
                    content=structure,
                )

            if call.name == "word.replace_text":
                result = self.word_adapter.replace_text(
                    file_path=args["file_path"],
                    replacements=args["replacements"],
                    output_path=args["output_path"],
                )
                return ToolResult(
                    call_id=call.id,
                    tool_name=call.name,
                    success=True,
                    content=result,
                )

            if call.name == "word.append_text":
                output_path = args.get("output_path")
                if not output_path:
                    src = args["file_path"]
                    base_name = os.path.basename(src)
                    output_path = os.path.join(
                        "storage",
                        "outputs",
                        f"{uuid.uuid4().hex}_appended_{base_name}",
                    )

                result = self.word_adapter.append_text(
                    file_path=args["file_path"],
                    append_text=args["append_text"],
                    output_path=output_path,
                )
                return ToolResult(
                    call_id=call.id,
                    tool_name=call.name,
                    success=True,
                    content=result,
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
        