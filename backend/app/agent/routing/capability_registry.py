from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.capability_types import CapabilityType
from app.domain.document_types import DocumentType


class ProviderProtocol(Protocol):
    document_type: DocumentType

    def supports(self, capability: CapabilityType) -> bool:
        ...


@dataclass
class RegisteredProvider:
    document_type: DocumentType
    provider: ProviderProtocol


class CapabilityRegistry:
    def __init__(self) -> None:
        self._providers: dict[DocumentType, ProviderProtocol] = {}

    def register_provider(self, provider: ProviderProtocol) -> None:
        self._providers[provider.document_type] = provider

    def get_provider(self, document_type: DocumentType) -> ProviderProtocol | None:
        return self._providers.get(document_type)

    def require_provider(self, document_type: DocumentType) -> ProviderProtocol:
        provider = self.get_provider(document_type)
        if provider is None:
            raise ValueError(f"No provider registered for document type: {document_type}")
        return provider

    def supports(self, document_type: DocumentType, capability: CapabilityType) -> bool:
        provider = self.get_provider(document_type)
        if provider is None:
            return False
        return provider.supports(capability)

    def list_supported_document_types(self) -> list[DocumentType]:
        return list(self._providers.keys())

    def list_supported_capabilities(self, document_type: DocumentType) -> list[str]:
        provider = self.get_provider(document_type)
        if provider is None:
            return []
        return [cap.value for cap in CapabilityType if provider.supports(cap)]

    def export_for_prompt(self) -> dict:
        result: dict[str, list[str]] = {}
        for doc_type in self.list_supported_document_types():
            result[doc_type.value] = self.list_supported_capabilities(doc_type)
        return result


_global_registry: CapabilityRegistry | None = None


def get_capability_registry() -> CapabilityRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = CapabilityRegistry()
    return _global_registry