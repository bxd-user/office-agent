from app.document.adapters.word_adapter import WordAdapter
from app.document.selectors.base import BaseSelector


class WordSelector(BaseSelector):
    def select(self, file_path: str) -> WordAdapter:
        if not file_path.lower().endswith(".docx"):
            raise ValueError("WordSelector only supports .docx files")
        return WordAdapter()
