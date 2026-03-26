from __future__ import annotations

from typing import Any

from app.agent.loop import AgentLoop
from app.document.bootstrap import bootstrap_document_providers


class AgentRuntime:
    def __init__(self, file_resolver) -> None:
        bootstrap_document_providers()
        self.loop = AgentLoop(file_resolver=file_resolver)

    def run(
        self,
        user_request: str,
        files: list[dict[str, Any]],
        capabilities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.loop.run(
            user_request=user_request,
            files=files,
            capabilities=capabilities or {},
        )