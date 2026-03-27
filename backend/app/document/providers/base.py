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


class StubDocumentProvider(BaseDocumentProvider):
    """
    格式存根基类：格式已被识别但功能尚未实现时使用。
    返回结构化的"未支持"响应，而不是抛出异常，实现优雅降级。

    实现新格式时，将对应 Provider 的父类从 StubDocumentProvider
    改为 BaseDocumentProvider，并逐步实现各 capability 方法即可。
    """

    def supported_capabilities(self) -> set[CapabilityType]:
        return set()

    def _unsupported(self, operation: str) -> ProviderResult:
        fmt = self.document_type.value.upper()
        return ProviderResult(
            success=False,
            message=f"{fmt} 格式暂不支持 [{operation}] 操作，敬请期待。",
        )

    def read(self, file_path: str, **kwargs) -> ProviderResult:
        return self._unsupported("read")

    def extract(self, file_path: str, **kwargs) -> ProviderResult:
        return self._unsupported("extract")

    def locate(self, file_path: str, **kwargs) -> ProviderResult:
        return self._unsupported("locate")

    def fill(self, file_path: str, **kwargs) -> ProviderResult:
        return self._unsupported("fill")

    def update_table(self, file_path: str, **kwargs) -> ProviderResult:
        return self._unsupported("update_table")

    def compare(self, left_file_path: str, right_file_path: str, **kwargs) -> ProviderResult:
        return self._unsupported("compare")

    def validate(self, file_path: str, **kwargs) -> ProviderResult:
        return self._unsupported("validate")

    def write(self, file_path: str, **kwargs) -> ProviderResult:
        return self._unsupported("write")

    def scan_template(self, file_path: str, **kwargs) -> ProviderResult:
        return self._unsupported("scan_template")