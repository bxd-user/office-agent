from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agent.routing.capability_resolver import CapabilityResolver
from app.agent.schemas.action import ActionStep


@dataclass
class ToolRoute:
    route_type: str
    capability: str
    service_method: str | None
    reason: str
    route_data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_type": self.route_type,
            "capability": self.capability,
            "service_method": self.service_method,
            "reason": self.reason,
            "route_data": self.route_data,
        }


class ToolRouter:
    """
    轻量分流层：
    - document-native capability：由 document service/provider 主链处理
    - auxiliary/external tool：辅助能力或外部工具链处理
    """

    AUXILIARY_CAPABILITIES = {
        "mapper",
        "build_field_mapping",
        "summarize",
    }

    def __init__(self, resolver: CapabilityResolver | None = None):
        self.resolver = resolver
        if self.resolver is None:
            self.resolver = CapabilityResolver()

    def route_step(
        self,
        step: ActionStep,
        file_resolver,
        context: Any | None = None,
    ) -> ToolRoute:
        route = self.resolver.resolve_step_route(
            step=step,
            file_resolver=file_resolver,
            context=context,
        )

        capability = route.capability
        if self._is_document_native(capability=capability, service_method=route.service_method):
            return ToolRoute(
                route_type="document-native",
                capability=capability,
                service_method=route.service_method,
                reason="capability can be handled by document service/provider",
                route_data=route.to_dict(),
            )

        return ToolRoute(
            route_type="auxiliary",
            capability=capability,
            service_method=route.service_method,
            reason="capability requires auxiliary/external tool handling",
            route_data=route.to_dict(),
        )

    def route(self, capability: str) -> list[str]:
        """
        兼容旧签名：返回推荐分流类型。
        """
        normalized = str(capability or "").strip().lower()
        if self._is_document_native(capability=normalized, service_method=normalized):
            return ["document-native"]
        return ["auxiliary"]

    def _is_document_native(self, capability: str, service_method: str | None) -> bool:
        if capability in self.AUXILIARY_CAPABILITIES:
            return False
        return bool(service_method)
