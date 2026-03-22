# app/tools/basic_tools.py
from __future__ import annotations

from typing import Any, Dict, List


class WordReadTextTool:
    name = "word.read_text"
    description = "Read text content from a word document by file role."
    input_schema = {
        "type": "object",
        "properties": {
            "file_role": {"type": "string"}
        },
        "required": ["file_role"],
    }

    def __init__(self, agent):
        self.agent = agent

    def run(self, **kwargs):
        file_role = kwargs["file_role"]
        file_item = self.agent.get_file_by_role(file_role)
        parsed = self.agent.reader.read(file_item.path)

        return {
            "file_role": file_role,
            "file_path": file_item.path,
            "text": parsed.full_text,
            "paragraphs": parsed.paragraphs,
            "tables": [t.rows for t in parsed.tables],
        }


class WordExtractPlaceholdersTool:
    name = "word.extract_placeholders"
    description = "Extract placeholders like {{name}} from a word template."
    input_schema = {
        "type": "object",
        "properties": {
            "file_role": {"type": "string", "description": "template"}
        },
        "required": ["file_role"],
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    def run(self, **kwargs) -> Dict[str, Any]:
        file_role = kwargs["file_role"]
        file_item = self.agent.get_file_by_role(file_role)
        placeholders = self.agent.extract_template_placeholders(file_item.path)
        return {
            "file_role": file_role,
            "file_path": file_item.path,
            "placeholders": placeholders,
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
        source_text = kwargs["source_text"]
        placeholders = kwargs["placeholders"]
        user_prompt = kwargs["user_prompt"]

        fill_data = self.agent.llm.extract_for_template(
            source_text=source_text,
            placeholders=placeholders,
            user_prompt=user_prompt,
        )
        return {"fill_data": fill_data}


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
        text = kwargs["text"]
        user_prompt = kwargs["user_prompt"]
        summary = self.agent.llm.summarize(text=text, user_prompt=user_prompt)
        return {"summary": summary}


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
        text = kwargs["text"]
        fields = kwargs["fields"]
        user_prompt = kwargs["user_prompt"]
        extracted = self.agent.llm.extract_fields(
            text=text,
            fields=fields,
            user_prompt=user_prompt,
        )
        return {"fields": extracted}


class WordFillTemplateTool:
    name = "word.fill_template"
    description = "Fill a word template with structured fill data."
    input_schema = {
        "type": "object",
        "properties": {
            "file_role": {"type": "string"},
            "fill_data": {"type": "object"},
        },
        "required": ["file_role", "fill_data"],
    }

    def __init__(self, agent):
        self.agent = agent

    def run(self, **kwargs):
        file_role = kwargs["file_role"]
        fill_data = kwargs["fill_data"]
        file_item = self.agent.get_file_by_role(file_role)

        output_path = self.agent.writer.fill_template(
            template_path=file_item.path,
            data=fill_data,
        )
        return {"output_path": output_path}


class VerifyDocumentTool:
    name = "doc.verify"
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

    def __init__(self, agent):
        self.agent = agent

    def run(self, **kwargs):
        return self.agent.verifier.verify_filled_document(
            output_path=kwargs["output_path"],
            expected_placeholders=kwargs["expected_placeholders"],
            filled_data=kwargs["filled_data"],
        )