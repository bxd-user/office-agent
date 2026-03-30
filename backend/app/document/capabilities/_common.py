from __future__ import annotations

from typing import Any

from app.document.providers.base import ProviderResult
from app.document.service import DocumentService


def get_document_service() -> DocumentService:
    return DocumentService()


def ensure_dict_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def provider_result_to_dict(result: ProviderResult) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "dict"):
        return result.dict()
    return {
        "success": bool(getattr(result, "success", False)),
        "message": str(getattr(result, "message", "")),
        "error_code": getattr(result, "error_code", None),
        "capability": getattr(result, "capability", None),
        "provider": getattr(result, "provider", None),
        "document_type": getattr(result, "document_type", None),
        "data": dict(getattr(result, "data", {}) or {}),
        "output_path": getattr(result, "output_path", None),
        "raw": dict(getattr(result, "raw", {}) or {}),
    }


def capability_error(capability: str, message: str, request: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "error_code": "CAPABILITY_INPUT_INVALID",
        "capability": capability,
        "provider": None,
        "document_type": None,
        "data": {
            "_capability": {
                "name": capability,
                "request": dict(request or {}),
            }
        },
        "output_path": None,
        "raw": {"layer": "capability"},
    }


def finalize_capability_response(
    *,
    capability: str,
    result: ProviderResult,
    request: dict[str, Any],
) -> dict[str, Any]:
    payload = provider_result_to_dict(result)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    data["_capability"] = {
        "name": capability,
        "request": request,
    }
    payload["data"] = data

    raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else {}
    raw["layer"] = "capability"
    payload["raw"] = raw

    payload["capability"] = payload.get("capability") or capability
    return payload
