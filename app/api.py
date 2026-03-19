from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from agents.executor import ExecutorAgent
from agents.inspector import InspectorAgent
from agents.mapper import MapperAgent
from agents.validator import ValidatorAgent
from adapters.llm_client import create_default_llm_client
from app.config import settings
from core.task_context import TaskContext


router = APIRouter(prefix="/api", tags=["demo"])


def _save_upload(upload: UploadFile, output_dir: str) -> str:
	suffix = Path(upload.filename or "").suffix
	safe_suffix = suffix if suffix else ""
	filename = f"{uuid4().hex}{safe_suffix}"
	output_path = Path(output_dir) / filename

	with output_path.open("wb") as f:
		content = upload.file.read()
		f.write(content)

	return str(output_path)


@router.post("/run")
async def run_demo(
	excel_file: UploadFile = File(...),
	word_file: UploadFile = File(...),
	prompt: str = Form(...),
) -> dict:
	if not prompt.strip():
		raise HTTPException(status_code=400, detail="prompt is required")

	excel_path = _save_upload(excel_file, settings.upload_dir)
	word_path = _save_upload(word_file, settings.upload_dir)

	task_ctx = TaskContext(
		task_id=uuid4().hex[:12],
		instruction=prompt.strip(),
		excel_path=excel_path,
		word_path=word_path,
	)

	task_ctx.add_input_file(path=excel_path, file_type="excel", role="input_excel")
	task_ctx.add_input_file(path=word_path, file_type="word", role="input_word")

	inspector = InspectorAgent()
	llm_client = create_default_llm_client()
	mapper = MapperAgent(llm_client=llm_client)
	executor = ExecutorAgent(output_dir=settings.output_dir)
	validator = ValidatorAgent()

	for agent in (inspector, mapper, executor, validator):
		result = agent.run(task_ctx)
		if not result.success:
			return {
				"success": False,
				"message": result.message or "处理失败",
				"error": result.error,
				"data": {
					"task_id": task_ctx.task_id,
					"current_step": task_ctx.current_step,
					"status": task_ctx.status,
					"excel_file": excel_file.filename,
					"word_file": word_file.filename,
					"excel_saved_path": excel_path,
					"word_saved_path": word_path,
					"prompt": prompt.strip(),
					"logs": task_ctx.logs[-30:],
				},
			}

	output_path = task_ctx.output_path or ""
	output_name = Path(output_path).name if output_path else ""
	output_url = f"/api/outputs/{output_name}" if output_name else ""

	return {
		"success": True,
		"message": "处理成功",
		"data": {
			"task_id": task_ctx.task_id,
			"excel_file": excel_file.filename,
			"word_file": word_file.filename,
			"excel_saved_path": excel_path,
			"word_saved_path": word_path,
			"prompt": prompt.strip(),
			"output_path": output_path,
			"output_file": output_name,
			"output_file_url": output_url,
			"llm_enabled": llm_client is not None,
			"mapper_summary": task_ctx.shared.get("mapper_summary", {}),
			"validation": task_ctx.validation_result or {},
			"summary": task_ctx.build_summary(),
		},
	}


@router.get("/outputs/{file_name}")
async def download_output(file_name: str):
	output_root = Path(settings.output_dir).resolve()
	target = (output_root / file_name).resolve()

	if output_root not in target.parents and target != output_root:
		raise HTTPException(status_code=400, detail="invalid file path")

	if not target.exists() or not target.is_file():
		raise HTTPException(status_code=404, detail="output file not found")

	return FileResponse(path=target, filename=target.name)
