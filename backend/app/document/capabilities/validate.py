from __future__ import annotations

from typing import Any

from app.document.capabilities._common import (
    capability_error,
    ensure_dict_payload,
    finalize_capability_response,
    get_document_service,
)


def execute_validate(payload: dict[str, Any]) -> dict[str, Any]:
    request = ensure_dict_payload(payload)
    file_path = request.get("file_path")
    filename = request.get("filename")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}

    if not isinstance(file_path, str) or not file_path:
        return capability_error("validate", "validate capability requires file_path", request=request)

    result = get_document_service().validate_document(file_path=file_path, filename=filename, **params)
    return finalize_capability_response(capability="validate", result=result, request=request)


def validate_document(file_path: str | dict[str, Any], filename: str | None = None, **kwargs):
    if isinstance(file_path, dict):
        return execute_validate(file_path)
    payload = {
        "file_path": file_path,
        "filename": filename,
        "params": kwargs,
    }
    return execute_validate(payload)
