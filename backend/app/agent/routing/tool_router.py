from __future__ import annotations

from app.agent.routing.capability_resolver import CapabilityResolver


class ToolRouter:
    def __init__(self, resolver: CapabilityResolver):
        self.resolver = resolver

    def route(self, capability: str) -> list[str]:
        return self.resolver.resolve_tools(capability)
