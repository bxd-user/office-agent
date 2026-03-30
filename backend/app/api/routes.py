from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile

from app.agent.runtime import AgentRuntime
from app.api.schemas import AgentRunRequest, AgentRunResponse
from app.core.config import settings
from app.domain.task_config import infer_task_type
from app.domain.output_schema import normalize_agent_output_dict


router = APIRouter()


def _normalize_output_mode(value: str | None) -> str:
    mode = (value or "full").strip().lower()
    if mode not in {"full", "summary", "minimal"}:
        return "full"
    return mode


def _resolve_task_type(user_request: str, task_type: str | None, infer_enabled: bool) -> str:
    candidate = (task_type or "auto").strip().lower()
    if candidate and candidate != "auto":
        return candidate
    if infer_enabled:
        return infer_task_type(user_request)
    return "auto"


def _build_capabilities(
    base_capabilities: dict[str, Any],
    *,
    user_request: str,
    files: list[dict[str, Any]],
    output_mode: str,
    task_type: str,
    infer_task_type_enabled: bool,
    include_execution_logs: bool,
) -> dict[str, Any]:
    merged = dict(base_capabilities or {})
    merged["api_options"] = {
        "output_mode": output_mode,
        "task_type": task_type,
        "infer_task_type": infer_task_type_enabled,
        "include_execution_logs": include_execution_logs,
        "file_count": len(files),
        "input_mode": "single_file" if len(files) == 1 else ("multi_file" if len(files) > 1 else "no_file"),
    }
    merged["task_type"] = task_type
    merged["input_mode"] = merged["api_options"]["input_mode"]
    merged["requested_output_mode"] = output_mode
    return merged


def _apply_output_preferences(
    normalized_result: dict[str, Any],
    *,
    output_mode: str,
    include_execution_logs: bool,
) -> dict[str, Any]:
    result = deepcopy(normalized_result)
    payload = result.get("payload") if isinstance(result.get("payload"), dict) else {}

    if not include_execution_logs:
        final_output = payload.get("final_output") if isinstance(payload.get("final_output"), dict) else {}
        final_output["logs"] = {}
        payload["final_output"] = final_output
        payload["trace"] = []
        payload["observations"] = []

    if output_mode == "summary":
        payload["trace"] = []
        payload["observations"] = []
        payload["memory"] = {}
        payload["context"] = {}
    elif output_mode == "minimal":
        keep = {
            "success": payload.get("success", False),
            "session": payload.get("session", {}),
            "summary": payload.get("summary", {}),
            "execution": payload.get("execution", {}),
            "final_output": payload.get("final_output", {}),
            "task": payload.get("task", None),
        }
        payload = keep

    payload["api"] = {
        "output_mode": output_mode,
        "include_execution_logs": include_execution_logs,
    }
    result["payload"] = payload
    return result


def extract_answer(result: dict) -> str:
    final_output = result.get("payload", {}).get("final_output", {}) if isinstance(result, dict) else {}
    if isinstance(final_output, dict):
        text = final_output.get("text", "")
        if isinstance(text, str) and text.strip():
            return text

    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    if isinstance(summary, dict):
        text = summary.get("summary", "")
        if isinstance(text, str):
            return text
    return ""


def extract_response_fields(result: dict) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    final_output = payload.get("final_output", {}) if isinstance(payload, dict) else {}

    text = ""
    if isinstance(final_output, dict):
        text = str(final_output.get("text") or "")
    if not text:
        text = extract_answer(result)

    files = final_output.get("files", []) if isinstance(final_output, dict) else []
    if not isinstance(files, list):
        files = []

    structured = final_output.get("structured", {}) if isinstance(final_output, dict) else {}
    if not isinstance(structured, dict):
        structured = {}

    trace = payload.get("trace", []) if isinstance(payload, dict) else []
    if not isinstance(trace, list):
        trace = []

    return text, files, structured, trace


def build_file_resolver(files: list[dict]):
    file_map = {f["file_id"]: f for f in files}

    def resolve(file_id: str) -> dict:
        if file_id not in file_map:
            raise ValueError(f"Unknown file_id: {file_id}")
        return file_map[file_id]

    return resolve


def normalize_file_items(files: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(files or [], start=1):
        if isinstance(item, dict):
            data = dict(item)
        elif hasattr(item, "model_dump"):
            data = item.model_dump()
        elif hasattr(item, "dict"):
            data = item.dict()
        else:
            continue

        file_id = data.get("file_id") or data.get("filename") or f"file_{idx}"
        filename = data.get("filename") or str(file_id)
        path = data.get("path") or ""
        normalized.append(
            {
                "file_id": str(file_id),
                "filename": str(filename),
                "path": str(path),
                **{k: v for k, v in data.items() if k not in {"file_id", "filename", "path"}},
            }
        )
    return normalized


@router.post("/agent/run", response_model=AgentRunResponse)
async def run_agent(
    prompt: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    capabilities: str = Form(default="{}"),
    output_mode: str = Form(default="full"),
    task_type: str = Form(default="auto"),
    infer_task_type: bool = Form(default=True),
    include_execution_logs: bool = Form(default=True),
) -> AgentRunResponse:
    try:
        task_id = str(uuid.uuid4())
        upload_dir = os.path.join(settings.UPLOAD_DIR, task_id)
        os.makedirs(upload_dir, exist_ok=True)

        file_infos: list[dict] = []
        for idx, file in enumerate(files, start=1):
            filename = file.filename or f"upload_{idx}"
            save_path = os.path.join(upload_dir, filename)
            with open(save_path, "wb") as out:
                out.write(await file.read())

            file_infos.append(
                {
                    "file_id": filename,
                    "filename": filename,
                    "path": save_path,
                }
            )

        try:
            capabilities_dict = json.loads(capabilities) if capabilities else {}
            if not isinstance(capabilities_dict, dict):
                capabilities_dict = {}
        except Exception:
            capabilities_dict = {}

        resolved_output_mode = _normalize_output_mode(output_mode)
        resolved_task_type = _resolve_task_type(
            user_request=prompt,
            task_type=task_type,
            infer_enabled=bool(infer_task_type),
        )

        merged_capabilities = _build_capabilities(
            base_capabilities=capabilities_dict,
            user_request=prompt,
            files=file_infos,
            output_mode=resolved_output_mode,
            task_type=resolved_task_type,
            infer_task_type_enabled=bool(infer_task_type),
            include_execution_logs=bool(include_execution_logs),
        )

        file_resolver = build_file_resolver(file_infos)
        runtime = AgentRuntime(file_resolver=file_resolver)

        result = runtime.run(
            user_request=prompt,
            files=file_infos,
            capabilities=merged_capabilities,
        )
        normalized = normalize_agent_output_dict(result)
        normalized = _apply_output_preferences(
            normalized,
            output_mode=resolved_output_mode,
            include_execution_logs=bool(include_execution_logs),
        )
        payload = normalized.get("payload", {}) if isinstance(normalized, dict) else {}
        result_text, result_files, structured_data, execution_trace = extract_response_fields(normalized)
        return AgentRunResponse(
            success=bool(payload.get("success", False)),
            result_text=result_text,
            result_files=result_files,
            structured_data=structured_data,
            execution_trace=execution_trace,
            answer=extract_answer(normalized),
            result=normalized,
        )
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "summary": {"success": False, "summary": "运行失败", "issues": [str(e)]},
        }
        normalized = normalize_agent_output_dict(error_result)
        normalized = _apply_output_preferences(
            normalized,
            output_mode=_normalize_output_mode(output_mode),
            include_execution_logs=bool(include_execution_logs),
        )
        payload = normalized.get("payload", {}) if isinstance(normalized, dict) else {}
        result_text, result_files, structured_data, execution_trace = extract_response_fields(normalized)
        return AgentRunResponse(
            success=bool(payload.get("success", False)),
            result_text=result_text,
            result_files=result_files,
            structured_data=structured_data,
            execution_trace=execution_trace,
            answer=extract_answer(normalized),
            result=normalized,
        )


@router.post("/agent/run_json", response_model=AgentRunResponse)
def run_agent_json(payload: AgentRunRequest) -> AgentRunResponse:
    normalized_files = normalize_file_items(list(payload.files))
    file_resolver = build_file_resolver(normalized_files)
    runtime = AgentRuntime(file_resolver=file_resolver)

    resolved_output_mode = _normalize_output_mode(payload.output_mode)
    resolved_task_type = _resolve_task_type(
        user_request=payload.user_request,
        task_type=payload.task_type,
        infer_enabled=bool(payload.infer_task_type),
    )
    merged_capabilities = _build_capabilities(
        base_capabilities=payload.capabilities,
        user_request=payload.user_request,
        files=normalized_files,
        output_mode=resolved_output_mode,
        task_type=resolved_task_type,
        infer_task_type_enabled=bool(payload.infer_task_type),
        include_execution_logs=bool(payload.include_execution_logs),
    )

    result = runtime.run(
        user_request=payload.user_request,
        files=normalized_files,
        capabilities=merged_capabilities,
    )
    normalized = normalize_agent_output_dict(result)
    normalized = _apply_output_preferences(
        normalized,
        output_mode=resolved_output_mode,
        include_execution_logs=bool(payload.include_execution_logs),
    )
    payload = normalized.get("payload", {}) if isinstance(normalized, dict) else {}
    result_text, result_files, structured_data, execution_trace = extract_response_fields(normalized)
    return AgentRunResponse(
        success=bool(payload.get("success", False)),
        result_text=result_text,
        result_files=result_files,
        structured_data=structured_data,
        execution_trace=execution_trace,
        answer=extract_answer(normalized),
        result=normalized,
    )