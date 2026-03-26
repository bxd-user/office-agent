from __future__ import annotations

import json
import os
import uuid

from fastapi import APIRouter, File, Form, UploadFile

from app.agent.runtime import AgentRuntime
from app.api.schemas import AgentRunRequest, AgentRunResponse
from app.core.config import settings


router = APIRouter()


def extract_answer(result: dict) -> str:
    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    if isinstance(summary, dict):
        text = summary.get("summary", "")
        if isinstance(text, str):
            return text
    return ""


def build_file_resolver(files: list[dict]):
    file_map = {f["file_id"]: f for f in files}

    def resolve(file_id: str) -> dict:
        if file_id not in file_map:
            raise ValueError(f"Unknown file_id: {file_id}")
        return file_map[file_id]

    return resolve


@router.post("/agent/run", response_model=AgentRunResponse)
async def run_agent(
    prompt: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    capabilities: str = Form(default="{}"),
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

        file_resolver = build_file_resolver(file_infos)
        runtime = AgentRuntime(file_resolver=file_resolver)

        result = runtime.run(
            user_request=prompt,
            files=file_infos,
            capabilities=capabilities_dict,
        )
        return AgentRunResponse(
            success=result["success"],
            answer=extract_answer(result),
            result=result,
        )
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "summary": {"success": False, "summary": "运行失败", "issues": [str(e)]},
        }
        return AgentRunResponse(
            success=False,
            answer=extract_answer(error_result),
            result=error_result,
        )


@router.post("/agent/run_json", response_model=AgentRunResponse)
def run_agent_json(payload: AgentRunRequest) -> AgentRunResponse:
    file_resolver = build_file_resolver(payload.files)
    runtime = AgentRuntime(file_resolver=file_resolver)

    result = runtime.run(
        user_request=payload.user_request,
        files=payload.files,
        capabilities=payload.capabilities,
    )
    return AgentRunResponse(
        success=result["success"],
        answer=extract_answer(result),
        result=result,
    )