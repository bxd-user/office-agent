from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.domain.capability_types import CapabilityType
from app.domain.document_types import DocumentType


class ProviderResult(BaseModel):
    success: bool = True
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    output_path: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class BaseDocumentProvider(ABC):
    document_type: DocumentType = DocumentType.UNKNOWN

    def supports(self, capability: CapabilityType) -> bool:
        return capability in self.supported_capabilities()

    @abstractmethod
    def supported_capabilities(self) -> set[CapabilityType]:
        raise NotImplementedError

    def read(self, file_path: str, **kwargs) -> ProviderResult:
        raise NotImplementedError

    def extract(self, file_path: str, **kwargs) -> ProviderResult:
        raise NotImplementedError

    def locate(self, file_path: str, **kwargs) -> ProviderResult:
        raise NotImplementedError

    def fill(self, file_path: str, **kwargs) -> ProviderResult:
        raise NotImplementedError

    def update_table(self, file_path: str, **kwargs) -> ProviderResult:
        raise NotImplementedError

    def compare(self, left_file_path: str, right_file_path: str, **kwargs) -> ProviderResult:
        raise NotImplementedError

    def validate(self, file_path: str, **kwargs) -> ProviderResult:
        raise NotImplementedError

    def write(self, file_path: str, **kwargs) -> ProviderResult:
        raise NotImplementedError

    def scan_template(self, file_path: str, **kwargs) -> ProviderResult:
        raise NotImplementedError