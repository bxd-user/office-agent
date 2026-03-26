from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.agent.prompts import PLANNER_SYSTEM_PROMPT
from app.agent.routing.capability_registry import get_capability_registry
from app.agent.schemas.action import ActionPlan
from app.agent.schemas.plan import PlannerOutput
from app.core.llm_client import LLMClient, LLMClientError


class PlannerV2:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()
        self.registry = get_capability_registry()

    def build_plan(
        self,
        user_request: str,
        files: list[dict[str, Any]],
        capabilities: dict[str, Any] | None = None,
    ) -> ActionPlan:
        capabilities = capabilities or {}
        allow_fallback = bool(capabilities.get("allow_fallback", False))

        if not self.llm.enabled:
            if allow_fallback:
                return self._fallback_plan(user_request=user_request, files=files)
            raise LLMClientError("LLM is not configured. Please set LLM_API_KEY / LLM_BASE_URL / LLM_MODEL")

        merged_capabilities = {
            "provider_capabilities": self.registry.export_for_prompt(),
            "extra_capabilities": capabilities or {},
        }

        user_prompt = self._build_user_prompt(
            user_request=user_request,
            files=files,
            capabilities=merged_capabilities,
        )

        try:
            result = self.llm.chat_json(
                system_prompt=PLANNER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1,
            )
        except LLMClientError:
            if allow_fallback:
                return self._fallback_plan(user_request=user_request, files=files)
            raise

        try:
            parsed = PlannerOutput.model_validate(result)
        except ValidationError as e:
            if allow_fallback:
                return self._fallback_plan(user_request=user_request, files=files)
            raise ValueError(
                f"Planner output validation failed: {e}; raw={json.dumps(result, ensure_ascii=False, default=str)}"
            ) from e

        return ActionPlan(
            steps=parsed.steps,
            metadata={
                "planner": "llm",
                "raw_output": result,
            },
        )

    def _build_user_prompt(
        self,
        user_request: str,
        files: list[dict[str, Any]],
        capabilities: dict[str, Any],
    ) -> str:
        return json.dumps(
            {
                "user_request": user_request,
                "available_files": files,
                "capabilities": capabilities,
                "planning_hints": {
                    "excel_to_word": [
                        "SCAN_TEMPLATE_FIELDS",
                        "EXTRACT_STRUCTURED_DATA",
                        "BUILD_FIELD_MAPPING",
                        "FILL_FIELDS",
                    ],
                    "excel_to_excel_table": [
                        "EXTRACT_STRUCTURED_DATA",
                        "UPDATE_TABLE",
                    ],
                },
                "output_format": {
                    "steps": [
                        {
                            "id": "string",
                            "action_type": "string",
                            "input_file_ids": ["string"],
                            "target_file_id": "string|null",
                            "params": {},
                            "expected_output": {},
                            "depends_on": ["string"],
                            "allow_retry": True,
                        }
                    ]
                },
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    def _fallback_plan(self, user_request: str, files: list[dict[str, Any]]) -> ActionPlan:
        if not files:
            return ActionPlan(
                steps=[],
                metadata={"planner": "fallback", "reason": "no_files"},
            )

        excel_files = [f for f in files if str(f.get("filename", "")).lower().endswith((".xlsx", ".xls", ".xlsm", ".csv", ".tsv"))]
        word_files = [f for f in files if str(f.get("filename", "")).lower().endswith((".docx", ".doc"))]

        steps: list[dict[str, Any]] = []

        if excel_files and word_files:
            source = excel_files[0]
            target = word_files[0]
            schema_artifact = f"schema_{uuid4().hex[:8]}"
            data_artifact = f"data_{uuid4().hex[:8]}"
            mapping_artifact = f"mapping_{uuid4().hex[:8]}"

            steps = [
                {
                    "id": "step_scan_template",
                    "action_type": "SCAN_TEMPLATE_FIELDS",
                    "input_file_ids": [],
                    "target_file_id": target["file_id"],
                    "params": {"output_artifact_name": schema_artifact},
                    "expected_output": {},
                    "depends_on": [],
                    "allow_retry": True,
                },
                {
                    "id": "step_extract_source",
                    "action_type": "EXTRACT_STRUCTURED_DATA",
                    "input_file_ids": [source["file_id"]],
                    "target_file_id": None,
                    "params": {"output_artifact_name": data_artifact},
                    "expected_output": {},
                    "depends_on": [],
                    "allow_retry": True,
                },
                {
                    "id": "step_build_mapping",
                    "action_type": "BUILD_FIELD_MAPPING",
                    "input_file_ids": [],
                    "target_file_id": None,
                    "params": {
                        "source_step_id": "step_extract_source",
                        "target_schema_from_artifact": schema_artifact,
                        "artifact_name": mapping_artifact,
                        "user_request": user_request,
                    },
                    "expected_output": {},
                    "depends_on": ["step_scan_template", "step_extract_source"],
                    "allow_retry": True,
                },
                {
                    "id": "step_fill_template",
                    "action_type": "FILL_FIELDS",
                    "input_file_ids": [],
                    "target_file_id": target["file_id"],
                    "params": {
                        "field_values_from_artifact": mapping_artifact,
                    },
                    "expected_output": {},
                    "depends_on": ["step_build_mapping"],
                    "allow_retry": True,
                },
            ]
        else:
            first = files[0]
            steps = [
                {
                    "id": "step_extract",
                    "action_type": "EXTRACT_STRUCTURED_DATA",
                    "input_file_ids": [first["file_id"]],
                    "target_file_id": None,
                    "params": {"output_artifact_name": "extract_result"},
                    "expected_output": {},
                    "depends_on": [],
                    "allow_retry": True,
                }
            ]

        return ActionPlan(
            steps=PlannerOutput.model_validate({"steps": steps}).steps,
            metadata={"planner": "fallback", "reason": "llm_unavailable_or_invalid"},
        )