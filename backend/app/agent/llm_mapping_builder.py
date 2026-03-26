from __future__ import annotations

import json
from typing import Any

from app.agent.prompts import MAPPING_SYSTEM_PROMPT
from app.core.llm_client import LLMClient, LLMClientError


class LLMMappingBuilder:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()

    def build_field_values(
        self,
        source_data: dict[str, Any],
        target_schema: dict[str, Any] | None = None,
        user_request: str | None = None,
    ) -> dict[str, Any]:
        if not self.llm.enabled:
            return self._fallback_field_values(source_data, target_schema)

        payload = {
            "user_request": user_request or "",
            "source_data": source_data,
            "target_schema": target_schema or {},
            "required_output": {
                "field_values": {}
            },
        }
        try:
            result = self.llm.chat_json(
                system_prompt=MAPPING_SYSTEM_PROMPT,
                user_prompt=json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                temperature=0.0,
            )
        except LLMClientError:
            return self._fallback_field_values(source_data, target_schema)

        field_values = result.get("field_values", {})
        if not isinstance(field_values, dict):
            raise ValueError(f"Invalid field_values returned by LLM: {result}")
        return field_values

    @staticmethod
    def _fallback_field_values(
        source_data: dict[str, Any],
        target_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        schema = target_schema or {}
        placeholders = schema.get("placeholders", []) if isinstance(schema, dict) else []
        if not placeholders:
            return source_data if isinstance(source_data, dict) else {"value": source_data}

        flattened: dict[str, Any] = {}
        if isinstance(source_data, dict):
            flattened.update(source_data)

        mapping: dict[str, Any] = {}
        for key in placeholders:
            if key in flattened:
                mapping[key] = flattened[key]
                continue
            key_lower = str(key).lower()
            for source_key, source_value in flattened.items():
                if key_lower in str(source_key).lower() or str(source_key).lower() in key_lower:
                    mapping[key] = source_value
                    break
            if key not in mapping:
                mapping[key] = ""
        return mapping