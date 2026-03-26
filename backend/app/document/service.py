from __future__ import annotations

from app.agent.routing.capability_registry import get_capability_registry
from app.domain.document_types import detect_document_type


class DocumentService:
    def __init__(self) -> None:
        self.registry = get_capability_registry()

    def read(self, file_path: str, filename: str | None = None, **kwargs):
        doc_type = detect_document_type(filename=filename or file_path)
        provider = self.registry.require_provider(doc_type)
        return provider.read(file_path=file_path, **kwargs)

    def extract(self, file_path: str, filename: str | None = None, **kwargs):
        doc_type = detect_document_type(filename=filename or file_path)
        provider = self.registry.require_provider(doc_type)
        return provider.extract(file_path=file_path, **kwargs)

    def locate(self, file_path: str, filename: str | None = None, **kwargs):
        doc_type = detect_document_type(filename=filename or file_path)
        provider = self.registry.require_provider(doc_type)
        return provider.locate(file_path=file_path, **kwargs)

    def fill(self, file_path: str, filename: str | None = None, **kwargs):
        doc_type = detect_document_type(filename=filename or file_path)
        provider = self.registry.require_provider(doc_type)
        return provider.fill(file_path=file_path, **kwargs)

    def update_table(self, file_path: str, filename: str | None = None, **kwargs):
        doc_type = detect_document_type(filename=filename or file_path)
        provider = self.registry.require_provider(doc_type)
        return provider.update_table(file_path=file_path, **kwargs)

    def validate(self, file_path: str, filename: str | None = None, **kwargs):
        doc_type = detect_document_type(filename=filename or file_path)
        provider = self.registry.require_provider(doc_type)
        return provider.validate(file_path=file_path, **kwargs)

    def scan_template(self, file_path: str, filename: str | None = None, **kwargs):
        doc_type = detect_document_type(filename=filename or file_path)
        provider = self.registry.require_provider(doc_type)
        return provider.scan_template(file_path=file_path, **kwargs)