from __future__ import annotations

from app.agent.routing.capability_registry import get_capability_registry
from app.document.providers.excel_provider import ExcelProvider
from app.document.providers.word_provider import WordProvider


def bootstrap_document_providers() -> None:
    registry = get_capability_registry()
    registry.register_provider(WordProvider())
    registry.register_provider(ExcelProvider())