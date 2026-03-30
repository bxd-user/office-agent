from __future__ import annotations

from typing import Any

from app.document.capabilities._common import (
    capability_error,
    ensure_dict_payload,
    finalize_capability_response,
    get_document_service,
)


def execute_write(payload: dict[str, Any]) -> dict[str, Any]:
    request = ensure_dict_payload(payload)
    file_path = request.get("file_path")
    filename = request.get("filename")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}

    if not isinstance(file_path, str) or not file_path:
        return capability_error("write", "write capability requires file_path", request=request)

    result = get_document_service().write_document(file_path=file_path, filename=filename, **params)
    return finalize_capability_response(capability="write", result=result, request=request)


def write_document(
    file_path: str | dict[str, Any],
    replacements: dict[str, str] | None = None,
    output_path: str | None = None,
    filename: str | None = None,
    **kwargs,
):
    if isinstance(file_path, dict):
        return execute_write(file_path)
    params = dict(kwargs)
    if replacements is not None:
        params.setdefault("replacements", replacements)
    if output_path is not None:
        params.setdefault("output_path", output_path)
    payload = {
        "file_path": file_path,
        "filename": filename,
        "params": params,
    }
    return execute_write(payload)
