from __future__ import annotations

from typing import Any

from app.document.capabilities._common import (
    capability_error,
    ensure_dict_payload,
    finalize_capability_response,
    get_document_service,
)


def execute_locate(payload: dict[str, Any]) -> dict[str, Any]:
    request = ensure_dict_payload(payload)
    file_path = request.get("file_path")
    filename = request.get("filename")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}

    if not isinstance(file_path, str) or not file_path:
        return capability_error("locate", "locate capability requires file_path", request=request)

    result = get_document_service().locate_targets(file_path=file_path, filename=filename, **params)
    return finalize_capability_response(capability="locate", result=result, request=request)


def locate_targets(
    file_path: str | dict[str, Any],
    keyword: str | None = None,
    filename: str | None = None,
    **kwargs,
):
    if isinstance(file_path, dict):
        return execute_locate(file_path)
    params = dict(kwargs)
    if keyword is not None:
        params.setdefault("keyword", keyword)
    payload = {
        "file_path": file_path,
        "filename": filename,
        "params": params,
    }
    return execute_locate(payload)
