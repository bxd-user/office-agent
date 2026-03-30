from __future__ import annotations

from typing import Any

from app.document.capabilities._common import (
    capability_error,
    ensure_dict_payload,
    finalize_capability_response,
    get_document_service,
)


def execute_read(payload: dict[str, Any]) -> dict[str, Any]:
    request = ensure_dict_payload(payload)
    file_path = request.get("file_path")
    filename = request.get("filename")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}

    if not isinstance(file_path, str) or not file_path:
        return capability_error("read", "read capability requires file_path", request=request)

    result = get_document_service().read_document(file_path=file_path, filename=filename, **params)
    return finalize_capability_response(capability="read", result=result, request=request)


def read_document(file_path: str | dict[str, Any], filename: str | None = None, **kwargs):
    if isinstance(file_path, dict):
        return execute_read(file_path)
    payload = {
        "file_path": file_path,
        "filename": filename,
        "params": kwargs,
    }
    return execute_read(payload)
