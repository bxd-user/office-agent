from __future__ import annotations

from typing import Any

from app.document.capabilities._common import (
    capability_error,
    ensure_dict_payload,
    finalize_capability_response,
    get_document_service,
)


def execute_fill(payload: dict[str, Any]) -> dict[str, Any]:
    request = ensure_dict_payload(payload)
    file_path = request.get("file_path") or request.get("template_path")
    filename = request.get("filename")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}

    if not isinstance(file_path, str) or not file_path:
        return capability_error("fill", "fill capability requires file_path/template_path", request=request)

    result = get_document_service().fill_document(file_path=file_path, filename=filename, **params)
    return finalize_capability_response(capability="fill", result=result, request=request)


def fill_document(
    template_path: str | dict[str, Any],
    mapping: dict[str, str] | None = None,
    output_path: str | None = None,
    filename: str | None = None,
    **kwargs,
):
    if isinstance(template_path, dict):
        return execute_fill(template_path)
    params = dict(kwargs)
    if mapping is not None:
        params.setdefault("mapping", mapping)
    if output_path is not None:
        params.setdefault("output_path", output_path)
    payload = {
        "template_path": template_path,
        "filename": filename,
        "params": params,
    }
    return execute_fill(payload)
