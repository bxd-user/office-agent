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
        if not self.llm.enabled:
            return self._fallback_summary(observations)

        payload = {
            "observations": observations,
            "context": context,
        }
        try:
            result = self.llm.chat_json(
                system_prompt=VALIDATION_SUMMARY_PROMPT,
                user_prompt=json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                temperature=0.0,
            )
            return result
        except LLMClientError:
            return self._fallback_summary(observations)

    @staticmethod
    def _fallback_summary(observations: list[dict[str, Any]]) -> dict[str, Any]:
        failed = [o for o in observations if not o.get("success", False)]
        if failed:
            return {
                "success": False,
                "summary": "部分步骤执行失败。",
                "issues": [f.get("message", "unknown failure") for f in failed],
            }
        return {
            "success": True,
            "summary": "任务执行完成。",
            "issues": [],
        }