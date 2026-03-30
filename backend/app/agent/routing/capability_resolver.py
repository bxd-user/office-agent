from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agent.routing.capability_registry import get_capability_registry
from app.agent.schemas.action import ActionStep
from app.domain.capability_types import CapabilityType
from app.domain.document_types import DocumentType, detect_document_type


@dataclass
class ResolvedStepRoute:
    step_id: str
    capability: str
    service_method: str | None
    requires_structured_input: bool
    cross_file_capability: bool
    multi_document_mode: bool
    primary_document_type: str
    provider_document_types: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "capability": self.capability,
            "service_method": self.service_method,
            "requires_structured_input": self.requires_structured_input,
            "cross_file_capability": self.cross_file_capability,
            "multi_document_mode": self.multi_document_mode,
            "primary_document_type": self.primary_document_type,
            "provider_document_types": self.provider_document_types,
        }


class CapabilityResolver:
    _CAPABILITY_ALIAS = {
        "read_document": "read",
        "extract_structured_data": "extract",
        "locate_targets": "locate",
        "fill_fields": "fill",
        "compare_documents": "compare",
        "validate_output": "validate",
        "create_output": "write",
        "scan_template_fields": "scan_template",
        "update_table": "update_table",
    }

    _SERVICE_METHOD_BY_CAPABILITY = {
        "read": "read",
        "extract": "extract",
        "locate": "locate",
        "fill": "fill",
        "update_table": "update_table",
        "compare": "compare",
        "validate": "validate",
        "write": "write",
        "scan_template": "scan_template",
    }

    def __init__(self) -> None:
        self.registry = get_capability_registry()

    def resolve_provider(self, document_type: DocumentType, capability: CapabilityType):
        provider = self.registry.require_provider(document_type)
        if not provider.supports(capability):
            raise ValueError(
                f"Provider for {document_type.value} does not support capability {capability.value}"
            )
        return provider

    def resolve_step_route(
        self,
        step: ActionStep,
        file_resolver,
        context: Any | None = None,
    ) -> ResolvedStepRoute:
        capability_name = self._normalize_capability_name(step)
        service_method = self._SERVICE_METHOD_BY_CAPABILITY.get(capability_name)
        requires_structured_input = self.registry.capability_requires_structured_input(capability_name)
        cross_file_capability = self.registry.capability_can_cross_file(capability_name)

        file_ids: list[str] = []
        if step.target_file_id:
            file_ids.append(step.target_file_id)
        file_ids.extend(step.input_file_ids)

        resolved_types: list[DocumentType] = []
        for file_id in file_ids:
            if not file_id:
                continue
            file_info = file_resolver(file_id)
            filename = file_info.get("filename") or file_info.get("path")
            doc_type = detect_document_type(filename=filename)
            if doc_type == DocumentType.UNKNOWN:
                continue
            resolved_types.append(doc_type)

        unique_types: list[DocumentType] = []
        for doc_type in resolved_types:
            if doc_type not in unique_types:
                unique_types.append(doc_type)

        multi_document_mode = len(step.input_file_ids) > 1 or capability_name == "compare"
        if not multi_document_mode and cross_file_capability and len(unique_types) > 1:
            multi_document_mode = True

        capability_enum = self._to_capability_enum(capability_name)
        # Auxiliary capabilities (for example summarize) are handled by local action handlers
        # and should not be blocked by provider capability checks.
        if capability_enum is not None and service_method is not None:
            for doc_type in unique_types:
                self.resolve_provider(doc_type, capability_enum)

        primary_document_type = unique_types[0].value if unique_types else "unknown"
        return ResolvedStepRoute(
            step_id=step.id,
            capability=capability_name,
            service_method=service_method,
            requires_structured_input=requires_structured_input,
            cross_file_capability=cross_file_capability,
            multi_document_mode=multi_document_mode,
            primary_document_type=primary_document_type,
            provider_document_types=[doc.value for doc in unique_types],
        )

    def _normalize_capability_name(self, step: ActionStep) -> str:
        raw = (step.capability or step.action_type or "").strip()
        normalized = CapabilityType.normalize(raw)
        if normalized:
            return normalized

        lowered = raw.lower()
        return self._CAPABILITY_ALIAS.get(lowered, lowered)

    @staticmethod
    def _to_capability_enum(capability_name: str) -> CapabilityType | None:
        try:
            return CapabilityType(capability_name)
        except Exception:
            return None
