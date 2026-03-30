from __future__ import annotations

from typing import Any

from app.document.capabilities._common import (
    capability_error,
    ensure_dict_payload,
    finalize_capability_response,
    get_document_service,
)


def execute_compare(payload: dict[str, Any]) -> dict[str, Any]:
    request = ensure_dict_payload(payload)
    filename = request.get("filename")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}

    file_paths = request.get("file_paths")
    left_file_path = request.get("left_file_path")
    right_file_path = request.get("right_file_path")

    normalized_paths: list[str] = []
    if isinstance(file_paths, list):
        normalized_paths.extend([p for p in file_paths if isinstance(p, str) and p])
    if isinstance(left_file_path, str) and left_file_path:
        normalized_paths.insert(0, left_file_path)
    if isinstance(right_file_path, str) and right_file_path:
        normalized_paths.append(right_file_path)

    if len(normalized_paths) < 2:
        return capability_error(
            "compare",
            "compare capability requires two file paths",
            request=request,
        )

    result = get_document_service().compare_documents(
        left_file_path=normalized_paths[0],
        right_file_path=normalized_paths[1],
        filename=filename,
        **params,
    )
    return finalize_capability_response(capability="compare", result=result, request=request)


def compare_document(
    file_a: str | dict[str, Any],
    file_b: str | None = None,
    filename: str | None = None,
    **kwargs,
):
    if isinstance(file_a, dict):
        return execute_compare(file_a)
    payload = {
        "left_file_path": file_a,
        "right_file_path": file_b,
        "filename": filename,
        "params": kwargs,
    }
    return execute_compare(payload)
