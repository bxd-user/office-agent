from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from app.agent.prompts import REPLAN_SYSTEM_PROMPT
from app.agent.schemas.action import ActionPlan, ActionStep
from app.agent.schemas.plan import PlannerOutput
from app.core.llm_client import LLMClient, LLMClientError


class Replanner:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()

    def rebuild_plan(
        self,
        user_request: str,
        files: list[dict[str, Any]],
        old_plan: ActionPlan,
        execution_trace: list[dict[str, Any]],
    ) -> ActionPlan:
        ruled = self._rule_based_replan(old_plan=old_plan, execution_trace=execution_trace)
        if ruled is not None:
            return ruled

        if not self.llm.enabled:
            return old_plan

        payload = {
            "user_request": user_request,
            "files": files,
            "old_plan": old_plan.model_dump(),
            "execution_trace": execution_trace,
            "required_output": {
                "steps": []
            },
        }

        try:
            result = self.llm.chat_json(
                system_prompt=REPLAN_SYSTEM_PROMPT,
                user_prompt=json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                temperature=0.1,
            )
        except LLMClientError:
            return old_plan

        try:
            parsed = PlannerOutput.model_validate(result)
        except ValidationError:
            return old_plan

        if not parsed.steps:
            return old_plan

        return ActionPlan(
            steps=parsed.steps,
            metadata={
                "planner": "replanner_llm",
                "raw_output": result,
            },
        )

    def _rule_based_replan(self, old_plan: ActionPlan, execution_trace: list[dict[str, Any]]) -> ActionPlan | None:
        failed = self._last_failed(execution_trace)
        if failed is None:
            return None

        failed_step_id = str(failed.get("step_id") or "")
        if not failed_step_id:
            return None

        step_index = self._find_step_index(old_plan.steps, failed_step_id)
        if step_index < 0:
            return None

        failed_step = old_plan.steps[step_index]
        action = self._normalize_action(failed_step.action_type)

        if action == "extract":
            patched = self._patch_extract(old_plan, step_index)
            return self._build_plan_from(old_plan, patched, "rule_extract_degraded")

        if action == "locate":
            patched = self._patch_locate(old_plan, step_index)
            return self._build_plan_from(old_plan, patched, "rule_locate_full_text")

        if action == "fill":
            patched = self._patch_fill(old_plan, step_index)
            return self._build_plan_from(old_plan, patched, "rule_fill_field_by_field")

        return None

    @staticmethod
    def _last_failed(execution_trace: list[dict[str, Any]]) -> dict[str, Any] | None:
        for item in reversed(execution_trace):
            if not item.get("success", False):
                return item
        return None

    @staticmethod
    def _find_step_index(steps: list[ActionStep], step_id: str) -> int:
        for idx, step in enumerate(steps):
            if step.id == step_id:
                return idx
        return -1

    @staticmethod
    def _normalize_action(action_type: str) -> str:
        raw = (action_type or "").strip().lower()
        alias = {
            "extract_structured_data": "extract",
            "locate_targets": "locate",
            "fill_fields": "fill",
            "read_document": "read",
        }
        return alias.get(raw, raw)

    def _patch_extract(self, old_plan: ActionPlan, failed_index: int) -> list[ActionStep]:
        steps = [step.model_copy(deep=True) for step in old_plan.steps]
        failed = steps[failed_index]

        has_read_before = any(self._normalize_action(s.action_type) == "read" for s in steps[:failed_index])
        if not has_read_before:
            read_step_id = f"{failed.id}_pre_read"
            read_step = ActionStep(
                id=read_step_id,
                action_type="read",
                input_file_ids=list(failed.input_file_ids),
                target_file_id=failed.target_file_id,
                params={"need_validation": False},
                expected_output={"kind": "document_content"},
                depends_on=list(failed.depends_on),
                allow_retry=True,
            )
            steps.insert(failed_index, read_step)
            failed.depends_on = [read_step_id]

        params = deepcopy(failed.params)
        params["mode"] = "coarse"
        params.setdefault("need_validation", False)
        failed.params = params
        return steps

    def _patch_locate(self, old_plan: ActionPlan, failed_index: int) -> list[ActionStep]:
        steps = [step.model_copy(deep=True) for step in old_plan.steps]
        failed = steps[failed_index]

        params = deepcopy(failed.params)
        params["fallback_mode"] = "full_text_search"
        params["full_text_search"] = True
        params["case_sensitive"] = False
        failed.params = params
        return steps

    def _patch_fill(self, old_plan: ActionPlan, failed_index: int) -> list[ActionStep]:
        steps = [step.model_copy(deep=True) for step in old_plan.steps]
        failed = steps[failed_index]
        params = deepcopy(failed.params)

        field_values = params.get("field_values")
        if not isinstance(field_values, dict) or len(field_values) <= 1:
            params["incremental"] = True
            failed.params = params
            return steps

        new_steps: list[ActionStep] = []
        previous_depends = list(failed.depends_on)
        for idx, (key, value) in enumerate(field_values.items(), start=1):
            step_id = f"{failed.id}_item_{idx}"
            item_params = deepcopy(params)
            item_params["field_values"] = {key: value}

            item_step = ActionStep(
                id=step_id,
                action_type=failed.action_type,
                capability=failed.capability,
                input_file_ids=list(failed.input_file_ids),
                target_file_id=failed.target_file_id,
                target_documents=list(failed.target_documents),
                params=item_params,
                expected_output=failed.expected_output,
                depends_on=list(previous_depends),
                allow_retry=True,
            )
            new_steps.append(item_step)
            previous_depends = [step_id]

        return steps[:failed_index] + new_steps + steps[failed_index + 1 :]

    @staticmethod
    def _build_plan_from(old_plan: ActionPlan, steps: list[ActionStep], reason: str) -> ActionPlan:
        metadata = dict(old_plan.metadata)
        metadata["planner"] = "replanner_rule"
        metadata["rule_reason"] = reason
        return ActionPlan(
            goal=old_plan.goal,
            allow_degraded_execution=old_plan.allow_degraded_execution,
            requires_validation=old_plan.requires_validation,
            input_declarations=old_plan.input_declarations,
            output_declarations=old_plan.output_declarations,
            steps=steps,
            metadata=metadata,
        )