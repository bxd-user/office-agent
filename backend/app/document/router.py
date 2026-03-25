from pathlib import Path

from app.document.exceptions import UnsupportedDocumentTypeError
from app.document.word.adapter import WordAdapter


class DocumentRouter:
    def __init__(self) -> None:
        adapter = WordAdapter()
        self.readers = {
            ".docx": adapter,
        }
        self.writers = {
            ".docx": adapter,
        }
        self.verifiers = {
            ".docx": adapter,
        }
        self.inspectors = {
            ".docx": adapter,
        }

    def _ext(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        if ext not in self.readers:
            raise UnsupportedDocumentTypeError(f"Unsupported document type: {ext}")
        return ext

    def get_reader(self, file_path: str):
        return self.readers[self._ext(file_path)]

    def get_writer(self, file_path: str):
        return self.writers[self._ext(file_path)]

    def get_verifier(self, file_path: str):
        return self.verifiers[self._ext(file_path)]

    def get_inspector(self, file_path: str):
        return self.inspectors[self._ext(file_path)]