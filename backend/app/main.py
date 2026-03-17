import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.utils import ensure_dir, unique_filename
from app.services.file_service import FileService
from app.workflows.excel_to_word_agent_workflow import ExcelToWordAgentWorkflow

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
workflow = ExcelToWordAgentWorkflow()


@app.get("/")
def root():
    return {"message": "Office Agent backend is running"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/tasks/run")
async def run_task(
    instruction: str = Form(...),
    excel_file: UploadFile = File(...),
    word_file: UploadFile = File(...),
):
    excel_path = await file_service.save_upload(excel_file)
    word_path = await file_service.save_upload(word_file)

    output_filename = unique_filename("result.docx")
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    result = workflow.run(
        instruction=instruction,
        excel_path=excel_path,
        word_path=word_path,
        output_path=output_path,
    )

    return {
        "success": True,
        "message": "生成成功",
        "output_file": output_filename,
        "download_url": f"/api/files/download/{output_filename}",
        "logs": result["logs"],
        "mapping": result["mapping"],
        "missing_fields": result["missing_fields"],
        "confidence": result["confidence"],
        "context": result["context"],
    }


@app.get("/api/files/download/{filename}")
def download_file(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )