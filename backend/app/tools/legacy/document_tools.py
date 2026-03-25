from __future__ import annotations

from typing import Any, Dict


def ok(tool_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": True,
        "tool_name": tool_name,
        "data": data,
        "error": None,
    }


def fail(tool_name: str, message: str, exc: Exception | None = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "tool_name": tool_name,
        "data": None,
        "error": {
            "message": message,
            "type": exc.__class__.__name__ if exc else "ToolError",
        },
    }


class DocumentReadTool:
    name = "document.read"
    description = "Read structured content from a document by file role."
    input_schema = {
        "type": "object",
        "properties": {
            "file_role": {"type": "string"},
        },
        "required": ["file_role"],
    }

    def __init__(self, agent: Any):
        self.agent = agent

    def run(self, **kwargs):
        try:
            file_role = kwargs["file_role"]
            file_item = self.agent.get_file_by_role(file_role)
            parsed = self.agent.document_service.read(file_item.path)

            blocks = [
                {
                    "type": b.type,
                    "index": b.index,
                    "text": b.text,
                    "table_rows": b.table_rows,
                }
                for b in parsed.blocks
            ]

            return ok(
                self.name,
                {
                    "file_role": file_role,
                    "file_path": file_item.path,
                    "file_type": parsed.file_type,
                    "text": parsed.full_text,
                    "paragraphs": parsed.paragraphs,
                    "tables": [t.rows for t in parsed.tables],
                    "blocks": blocks,
                },
            )
        except Exception as e:
            return fail(self.name, f"failed to read document: {str(e)}", e)


class DocumentExtractPlaceholdersTool:
    name = "document.extract_placeholders"
    description = "Extract placeholders like {{name}} from a document template."
    input_schema = {
        "type": "object",
        "properties": {
            "file_role": {"type": "string"},
        },
        "required": ["file_role"],
    }

    def __init__(self, agent: Any):
        self.agent = agent

    def run(self, **kwargs):
        try:
            file_role = kwargs["file_role"]
            file_item = self.agent.get_file_by_role(file_role)
            placeholders = self.agent.document_service.extract_placeholders(file_item.path)

            return ok(
                self.name,
                {
                    "file_role": file_role,
                    "file_path": file_item.path,
                    "placeholders": placeholders,
                },
            )
        except Exception as e:
            return fail(self.name, f"failed to extract placeholders: {str(e)}", e)


class DocumentFillTemplateTool:
    name = "document.fill_template"
    description = "Fill a document template with structured data."
    input_schema = {
        "type": "object",
        "properties": {
            "file_role": {"type": "string"},
            "fill_data": {"type": "object"},
        },
        "required": ["file_role", "fill_data"],
    }

    def __init__(self, agent: Any):
        self.agent = agent

    def run(self, **kwargs):
        try:
            file_role = kwargs["file_role"]
            fill_data = kwargs["fill_data"]
            file_item = self.agent.get_file_by_role(file_role)

            output_path = self.agent.document_service.fill_template(
                template_path=file_item.path,
                data=fill_data,
            )

            return ok(
                self.name,
                {
                    "file_role": file_role,
                    "template_path": file_item.path,
                    "output_path": output_path,
                },
            )
        except Exception as e:
            return fail(self.name, f"failed to fill template: {str(e)}", e)


class DocumentVerifyTool:
    name = "document.verify"
    description = "Verify filled document quality."
    input_schema = {
        "type": "object",
        "properties": {
            "output_path": {"type": "string"},
            "expected_placeholders": {
                "type": "array",
                "items": {"type": "string"},
            },
            "filled_data": {"type": "object"},
        },
        "required": ["output_path", "expected_placeholders", "filled_data"],
    }

    def __init__(self, agent: Any):
        self.agent = agent

    def run(self, **kwargs):
        try:
            result = self.agent.document_service.verify(
                output_path=kwargs["output_path"],
                expected_placeholders=kwargs["expected_placeholders"],
                filled_data=kwargs["filled_data"],
            )
            return ok(self.name, result)
        except Exception as e:
            return fail(self.name, f"failed to verify document: {str(e)}", e)

__all__ = [
    "DocumentReadTool",
    "DocumentExtractPlaceholdersTool",
    "DocumentFillTemplateTool",
    "DocumentVerifyTool",
]
