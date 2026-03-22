import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from app.api.schemas import AgentResponse, ResultData
from app.service import TaskService, infer_roles_from_filenames

router = APIRouter()
service = TaskService()


@router.post("/agent/run-workflow", response_model=AgentResponse)
async def run_workflow(
    files: List[UploadFile] = File(...),
    roles_json: Optional[str] = Form(None),
    prompt: str = Form(...),
):
    if roles_json:
        try:
            roles = json.loads(roles_json)
        except Exception:
            return AgentResponse(
                success=False,
                message="roles_json 不是合法 JSON",
                result=ResultData(),
                logs=["api: roles_json 解析失败"],
                error="invalid roles_json",
            )
    else:
        roles = infer_roles_from_filenames(files)

    if not isinstance(roles, list) or not all(isinstance(x, str) for x in roles):
        return AgentResponse(
            success=False,
            message="roles_json 必须是字符串数组",
            result=ResultData(
                answer="",
                file_name="workflow",
                text_length=0,
                structured_data=None,
                output_file_path=None,
                download_url=None,
            ),
            logs=["api: roles_json 类型不正确"],
            error="roles_json must be list[str]",
        )

    result = service.run_workflow_task(
        files=files,
        roles=roles,
        user_prompt=prompt,
    )

    download_url = None
    if result.output_file_path:
        output_name = Path(result.output_file_path).name
        download_url = f"/files/{output_name}"

    return AgentResponse(
        success=result.success,
        message=result.message,
        result=ResultData(
            answer=result.answer,
            file_name="workflow",
            text_length=len(result.answer or ""),
            structured_data=result.structured_data,
            output_file_path=result.output_file_path,
            download_url=download_url,
        ),
        logs=result.logs,
        error=result.error,
    )


@router.get("/files/{filename}")
async def download_file(filename: str):
    file_path = Path("storage/outputs") / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
