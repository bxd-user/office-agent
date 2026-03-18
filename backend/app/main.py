import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.utils import ensure_dir
from app.services.file_service import FileService
from app.workflows.autonomous_agent_workflow import AutonomousAgentWorkflow

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uploads")
OUTPUT_DIR = os.path.join(STORAGE_DIR, "outputs")

ensure_dir(UPLOAD_DIR)
ensure_dir(OUTPUT_DIR)

app = FastAPI(title="Office Agent V2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

file_service = FileService(UPLOAD_DIR)
autonomous_workflow = AutonomousAgentWorkflow()

SUPPORTED_TASK_TYPES = {
    "agent_autonomous": "根据提示词自主规划并调用工具执行任务",
}

TASK_HANDLERS = {
    "agent_autonomous": "_handle_agent_autonomous",
}


@app.get("/")
def root():
    return {"message": "Office Agent backend is running"}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/tasks/types")
def get_task_types():
    return {
        "success": True,
        "task_types": SUPPORTED_TASK_TYPES,
    }


@app.post("/api/tasks/execute")
async def execute_task(
    task_type: str = Form("agent_autonomous"),
    instruction: str = Form(""),
    params_json: str = Form("{}"),
    files: list[UploadFile] | None = File(default=None),
    excel_file: UploadFile | None = File(default=None),
    word_file: UploadFile | None = File(default=None),
):
    params = _parse_params_json(params_json)
    effective_task_type = _resolve_task_type(task_type, params)

    uploaded_files = _collect_uploaded_files(
        files=files or [],
        excel_file=excel_file,
        word_file=word_file,
    )
    saved_files = await _save_uploaded_files(uploaded_files)

    handler_name = TASK_HANDLERS.get(effective_task_type)
    if not handler_name:
        raise HTTPException(status_code=400, detail=f"不支持的 task_type: {effective_task_type}")

    handler = globals().get(handler_name)
    if not handler:
        raise HTTPException(status_code=500, detail=f"任务处理器未注册: {handler_name}")

    task_result = await handler(
        instruction=instruction,
        saved_files=saved_files,
        params=params,
    )
    return _build_task_response(task_type=effective_task_type, task_result=task_result)


@app.post("/api/tasks/run")
async def run_task(
    instruction: str = Form(...),
    excel_file: UploadFile = File(...),
    word_file: UploadFile = File(...),
):
    saved_files = await _save_uploaded_files([excel_file, word_file])
    task_result = await _handle_agent_autonomous(
        instruction=instruction,
        saved_files=saved_files,
        params={},
    )
    return _build_task_response(task_type="agent_autonomous", task_result=task_result)


@app.get("/api/files/download/{filename}")
def download_file(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


def _parse_params_json(params_json: str) -> dict:
    if not params_json or not params_json.strip():
        return {}

    try:
        payload = json.loads(params_json)
        if isinstance(payload, dict):
            return payload
        raise ValueError("params_json 必须是 JSON 对象")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"params_json 无效: {exc}") from exc


async def _run_autonomous_task(
    instruction: str,
    saved_files: list[dict],
    params: dict,
):
    if not saved_files:
        raise HTTPException(status_code=400, detail="agent_autonomous 任务至少需要上传 1 个文件")

    result = autonomous_workflow.run(
        instruction=instruction,
        input_files=saved_files,
        output_dir=OUTPUT_DIR,
        params=params,
    )
    result["message"] = "执行完成"
    return result


async def _handle_agent_autonomous(
    instruction: str,
    saved_files: list[dict],
    params: dict,
):
    return await _run_autonomous_task(
        instruction=instruction,
        saved_files=saved_files,
        params=params,
    )


def _resolve_task_type(task_type: str, params: dict) -> str:
    explicit = str(task_type or "").strip()
    if explicit == "excel_to_word":
        return "agent_autonomous"
    if explicit:
        return explicit
    fallback = str(params.get("task_type") or "").strip()
    if fallback == "excel_to_word":
        return "agent_autonomous"
    return fallback or "agent_autonomous"


def _collect_uploaded_files(
    files: list[UploadFile],
    excel_file: UploadFile | None,
    word_file: UploadFile | None,
) -> list[UploadFile]:
    merged: list[UploadFile] = [f for f in files if f and f.filename]
    if excel_file is not None:
        merged.append(excel_file)
    if word_file is not None:
        merged.append(word_file)

    unique_files: list[UploadFile] = []
    seen = set()
    for file in merged:
        key = id(file)
        if key in seen:
            continue
        seen.add(key)
        unique_files.append(file)

    return unique_files


async def _save_uploaded_files(files: list[UploadFile]) -> list[dict]:
    saved_files: list[dict] = []
    for file in files:
        saved_path = await file_service.save_upload(file)
        saved_files.append(
            {
                "filename": file.filename or os.path.basename(saved_path),
                "path": saved_path,
            }
        )
    return saved_files


def _build_task_response(task_type: str, task_result: dict) -> dict:
    output_file = task_result.get("output_file")
    output_path = task_result.get("output_path")
    if not output_file and isinstance(output_path, str) and output_path.strip():
        output_file = os.path.basename(output_path)

    download_url = f"/api/files/download/{output_file}" if output_file else None

    return {
        "success": True,
        "task_type": task_type,
        "message": task_result.get("message", "执行完成"),
        "output_file": output_file,
        "download_url": download_url,
        "logs": task_result.get("logs", []),
        "plan": task_result.get("plan", {}),
        "read_summaries": task_result.get("read_summaries", []),
        "execution_observation": task_result.get("execution_observation", []),
        "mapping": task_result.get("mapping", {}),
        "missing_fields": task_result.get("missing_fields", []),
        "confidence": task_result.get("confidence", "unknown"),
        "context": task_result.get("context", {}),
        "word_field_slots": task_result.get("word_field_slots", []),
    }


