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


class LLMExtractForTemplateTool:
    name = "llm.extract_for_template"
    description = "Use LLM to generate fill data for template placeholders from source text."
    input_schema = {
        "type": "object",
        "properties": {
            "source_text": {"type": "string"},
            "placeholders": {
                "type": "array",
                "items": {"type": "string"},
            },
            "user_prompt": {"type": "string"},
        },
        "required": ["source_text", "placeholders", "user_prompt"],
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    def run(self, **kwargs) -> Dict[str, Any]:
        try:
            result = self.agent.llm.extract_for_template(
                source_text=kwargs["source_text"],
                placeholders=kwargs["placeholders"],
                user_prompt=kwargs["user_prompt"],
            )
            filled_data = result.get("filled_data", {})
            missing_fields = result.get("missing_fields", [])
            return ok(
                self.name,
                {
                    "filled_data": filled_data,
                    "missing_fields": missing_fields,
                },
            ) | {
                "fill_data": filled_data,
                "filled_data": filled_data,
                "missing_fields": missing_fields,
            }
        except Exception as e:
            return fail(self.name, f"failed to extract fill data: {str(e)}", e)


class LLMSummarizeTool:
    name = "llm.summarize"
    description = "Use LLM to summarize text."
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "user_prompt": {"type": "string"},
        },
        "required": ["text", "user_prompt"],
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    def run(self, **kwargs) -> Dict[str, Any]:
        try:
            summary = self.agent.llm.summarize(
                text=kwargs["text"],
                user_prompt=kwargs["user_prompt"],
            )
            return ok(self.name, {"summary": summary}) | {"summary": summary}
        except Exception as e:
            return fail(self.name, f"failed to summarize: {str(e)}", e)


class LLMExtractFieldsTool:
    name = "llm.extract_fields"
    description = "Use LLM to extract requested fields from text."
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "fields": {
                "type": "array",
                "items": {"type": "string"},
            },
            "user_prompt": {"type": "string"},
        },
        "required": ["text", "fields", "user_prompt"],
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    def run(self, **kwargs) -> Dict[str, Any]:
        try:
            extracted = self.agent.llm.extract_fields(
                text=kwargs["text"],
                fields=kwargs["fields"],
                user_prompt=kwargs["user_prompt"],
            )
            return ok(self.name, {"fields": extracted}) | {"fields": extracted}
        except Exception as e:
            return fail(self.name, f"failed to extract fields: {str(e)}", e)

__all__ = [
    "LLMExtractForTemplateTool",
    "LLMSummarizeTool",
    "LLMExtractFieldsTool",
]
