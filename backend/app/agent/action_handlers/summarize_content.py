from __future__ import annotations

from app.agent.execution_context import ExecutionContext
from app.agent.schemas.action import ActionObservation, ActionStep


class SummarizeContentHandler:
    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        source_step_id = str(step.params.get("source") or "").strip()
        source_obs = context.get_observation(source_step_id) if source_step_id else None

        source_data = source_obs.data if source_obs else {}
        candidate_text = self._pick_text(source_data)
        summary = self._summarize_text(candidate_text)

        return ActionObservation(
            step_id=step.id,
            success=True,
            message="Summary generated",
            data={
                "summary": summary,
                "source_step_id": source_step_id or None,
            },
        )

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
