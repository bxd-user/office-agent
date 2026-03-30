from __future__ import annotations

from typing import Any

from app.document.capabilities._common import (
    capability_error,
    ensure_dict_payload,
    finalize_capability_response,
    get_document_service,
)


def execute_extract(payload: dict[str, Any]) -> dict[str, Any]:
    request = ensure_dict_payload(payload)
    file_path = request.get("file_path")
    filename = request.get("filename")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}

    if not isinstance(file_path, str) or not file_path:
        return capability_error("extract", "extract capability requires file_path", request=request)

    result = get_document_service().extract_fields(file_path=file_path, filename=filename, **params)
    return finalize_capability_response(capability="extract", result=result, request=request)


def extract_content(file_path: str | dict[str, Any], filename: str | None = None, **kwargs):
    if isinstance(file_path, dict):
        return execute_extract(file_path)
    payload = {
        "file_path": file_path,
        "filename": filename,
        "params": kwargs,
    }
    return execute_extract(payload)
