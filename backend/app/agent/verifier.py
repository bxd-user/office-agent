from __future__ import annotations

import json
from typing import Any

from app.agent.prompts import VALIDATION_SUMMARY_PROMPT
from app.core.llm_client import LLMClient, LLMClientError


class Verifier:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()

    def summarize(
        self,
        observations: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        deterministic = self._deterministic_summary(observations=observations, context=context)

        if not self.llm.enabled:
            return deterministic

        payload = {
            "observations": observations,
            "context": context,
            "deterministic": deterministic,
        }
        try:
            result = self.llm.chat_json(
                system_prompt=VALIDATION_SUMMARY_PROMPT,
                user_prompt=json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                temperature=0.0,
            )
            if isinstance(result, dict):
                merged = dict(deterministic)
                merged["llm_summary"] = result
                return merged
            return deterministic
        except LLMClientError:
            return deterministic

    @staticmethod
    def _deterministic_summary(observations: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
        refs = Verifier._extract_refs(context)

        failed_steps = [o for o in observations if not o.get("success", False)]
        missing_fields = Verifier._collect_missing_fields(refs.get("extracted_fields", {}))
        template_gaps = Verifier._collect_template_gaps(observations)
        output_files = Verifier._collect_output_files(observations, refs)
        empty_summaries = Verifier._collect_empty_summaries(observations)

        checks = {
            "execution_success": {
                "passed": len(failed_steps) == 0,
                "failed_steps": [o.get("step_id") for o in failed_steps],
            },
            "fields_completeness": {
                "passed": len(missing_fields) == 0,
                "missing_fields": missing_fields,
            },
            "template_filled": {
                "passed": len(template_gaps) == 0,
                "unfilled": template_gaps,
            },
            "output_generated": {
                "passed": len(output_files) > 0,
                "files": output_files,
            },
            "summary_non_empty": {
                "passed": len(empty_summaries) == 0,
                "empty_summary_steps": empty_summaries,
            },
        }

        issues: list[str] = []
        for failed in failed_steps:
            issues.append(str(failed.get("message") or f"步骤失败: {failed.get('step_id') or 'unknown'}"))
        if missing_fields:
            issues.append("存在缺失字段，抽取结果不完整")
        if template_gaps:
            issues.append("模板仍有未填充字段")
        if not output_files:
            issues.append("未生成输出文件")
        if empty_summaries:
            issues.append("摘要结果为空")

        success = all(bool(check.get("passed", False)) for check in checks.values())
        summary_text = "任务执行完成且通过校验。" if success else "任务执行完成但校验未通过。"

        return {
            "success": success,
            "summary": summary_text,
            "issues": issues,
            "checks": checks,
        }

    @staticmethod
    def _extract_refs(context: dict[str, Any]) -> dict[str, Any]:
        state = context.get("state", {}) if isinstance(context, dict) else {}
        refs = state.get("intermediate_refs", {}) if isinstance(state, dict) else {}
        return refs if isinstance(refs, dict) else {}

    @staticmethod
    def _collect_missing_fields(extracted_fields: Any) -> list[str]:
        if not isinstance(extracted_fields, dict):
            return []

        missing: list[str] = []

        def walk(prefix: str, value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    child_prefix = f"{prefix}.{key}" if prefix else str(key)
                    walk(child_prefix, child)
                return
            if isinstance(value, list):
                for idx, child in enumerate(value):
                    child_prefix = f"{prefix}[{idx}]"
                    walk(child_prefix, child)
                return
            if value is None:
                missing.append(prefix)
                return
            if isinstance(value, str) and not value.strip():
                missing.append(prefix)

        for step_id, payload in extracted_fields.items():
            walk(str(step_id), payload)
        return missing

    @staticmethod
    def _collect_template_gaps(observations: list[dict[str, Any]]) -> list[str]:
        gaps: list[str] = []
        for obs in observations:
            data = obs.get("data", {})
            if not isinstance(data, dict):
                continue

            candidates = [
                data.get("remaining_placeholders"),
                data.get("unfilled_fields"),
                data.get("placeholders_left"),
            ]
            for item in candidates:
                if isinstance(item, list) and item:
                    gaps.extend([str(v) for v in item])
                elif isinstance(item, int) and item > 0:
                    gaps.append(f"count:{item}")
        return gaps

    @staticmethod
    def _collect_output_files(observations: list[dict[str, Any]], refs: dict[str, Any]) -> list[str]:
        output_paths: list[str] = []

        from_refs = refs.get("output_file_paths", []) if isinstance(refs, dict) else []
        if isinstance(from_refs, list):
            for path in from_refs:
                if isinstance(path, str) and path and path not in output_paths:
                    output_paths.append(path)

        for obs in observations:
            produced = obs.get("produced_file_ids", [])
            if isinstance(produced, list):
                for path in produced:
                    if isinstance(path, str) and path and path not in output_paths:
                        output_paths.append(path)

            data = obs.get("data", {})
            if isinstance(data, dict):
                output_path = data.get("output_path")
                if isinstance(output_path, str) and output_path and output_path not in output_paths:
                    output_paths.append(output_path)

        return output_paths

    @staticmethod
    def _collect_empty_summaries(observations: list[dict[str, Any]]) -> list[str]:
        empty_steps: list[str] = []
        for obs in observations:
            data = obs.get("data", {})
            if not isinstance(data, dict):
                continue
            if "summary" not in data:
                continue

            summary = data.get("summary")
            if not isinstance(summary, str) or not summary.strip():
                empty_steps.append(str(obs.get("step_id") or "unknown"))
        return empty_steps