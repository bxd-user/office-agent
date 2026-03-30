from __future__ import annotations

from app.agent.execution_context import ExecutionContext
from app.agent.schemas.action import ActionObservation, ActionStep


class SummarizeContentHandler:
    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        source_step_id = str(step.params.get("source") or step.params.get("source_step_id") or "").strip()
        source_obs = context.get_observation(source_step_id) if source_step_id else None
        resolved_source_step_id = source_step_id
        if source_obs is None:
            resolved_source_step_id, source_obs = self._resolve_fallback_source(context)

        source_data = self._extract_source_data(source_obs)
        candidate_text = self._pick_text(source_data)
        summary = self._summarize_text(candidate_text)

        return ActionObservation(
            step_id=step.id,
            success=True,
            message="Summary generated",
            data={
                "summary": summary,
                "source_step_id": resolved_source_step_id or None,
            },
        )

    @staticmethod
    def _resolve_fallback_source(context: ExecutionContext) -> tuple[str, ActionObservation | None]:
        # Prefer latest successful read/extract observation with text-like payload.
        observations = list(context.state.observations.items())
        for step_id, obs in reversed(observations):
            if not obs.success:
                continue
            if SummarizeContentHandler._pick_text(SummarizeContentHandler._extract_source_data(obs)):
                return str(step_id), obs
        return "", None

    @staticmethod
    def _extract_source_data(obs: ActionObservation | None) -> dict:
        if obs is None:
            return {}
        if isinstance(obs.data, dict) and obs.data:
            return obs.data
        if isinstance(obs.read_result, dict) and obs.read_result:
            return obs.read_result
        if isinstance(obs.extracted_fields, dict) and obs.extracted_fields:
            return obs.extracted_fields
        return {}

    @staticmethod
    def _pick_text(data: dict) -> str:
        for key in ("text", "content", "markdown", "summary"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return str(data) if data else ""

    @staticmethod
    def _summarize_text(text: str, max_len: int = 300) -> str:
        if not text:
            return ""
        normalized = " ".join(text.split())
        return normalized[:max_len]


def handle_summarize_content(payload: dict) -> dict:
    return {"action": "summarize_content", "payload": payload}
