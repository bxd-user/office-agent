from __future__ import annotations

from app.document.shared.selectors import get_selector


class LegacyDocumentCompatibility:
    @staticmethod
    def select_adapter(file_path: str):
        selector = get_selector(file_path)
        return selector.select(file_path)
