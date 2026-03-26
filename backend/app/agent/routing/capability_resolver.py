from __future__ import annotations

from app.agent.routing.capability_registry import get_capability_registry
from app.domain.capability_types import CapabilityType
from app.domain.document_types import DocumentType


class CapabilityResolver:
    def __init__(self) -> None:
        self.registry = get_capability_registry()

    def resolve_provider(self, document_type: DocumentType, capability: CapabilityType):
        provider = self.registry.require_provider(document_type)
        if not provider.supports(capability):
            raise ValueError(
                f"Provider for {document_type.value} does not support capability {capability.value}"
            )
        return provider