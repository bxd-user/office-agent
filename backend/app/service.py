import shutil
from pathlib import Path

from fastapi import UploadFile

from app.agent import WorkflowAgent
from app.models import InputFile, TaskContext, TaskResult
from app.tools.docx_reader import DocxReader


UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class TaskService:
    def __init__(self):
        self.reader = DocxReader()
        self.agent = WorkflowAgent()

    def run_workflow_task(
        self,
        files: list[UploadFile],
        roles: list[str],
        user_prompt: str,
    ) -> TaskResult:
        logs = ["service: 开始处理统一工作流请求"]

        try:
            if len(files) != len(roles):
                return TaskResult(
                    success=False,
                    message="文件数量与角色数量不一致",
                    answer="",
                    logs=logs,
                    error="files/roles length mismatch",
                )

            parsed_files: list[InputFile] = []

            for idx, (file, role) in enumerate(zip(files, roles), start=1):
                filename = file.filename or f"file_{idx}.docx"
                file_path = UPLOAD_DIR / f"{idx}_{role}_{filename}"

                with file_path.open("wb") as f:
                    shutil.copyfileobj(file.file, f)

                logs.append(f"service: 文件已保存 -> {file_path}")

                parsed_doc = self.reader.read(str(file_path))
                logs.append(f"service: docx 解析完成 -> {parsed_doc.file_name} ({role})")

                parsed_files.append(
                    InputFile(
                        role=role,
                        file_name=parsed_doc.file_name,
                        file_path=parsed_doc.file_path,
                        paragraphs=parsed_doc.paragraphs,
                        tables=parsed_doc.tables,
                        full_text=parsed_doc.full_text,
                    )
                )

            source_files = [f for f in parsed_files if f.role == "source"]
            combined_text = "\n\n".join(
                f"===== {f.file_name} =====\n{f.full_text}" for f in source_files
            )

            first_file_name = parsed_files[0].file_name if parsed_files else ""
            first_file_path = parsed_files[0].file_path if parsed_files else ""

            context = TaskContext(
                user_prompt=user_prompt,
                logs=logs,
                files=parsed_files,
                file_name=first_file_name,
                file_path=first_file_path,
                full_text=combined_text,
                paragraphs=[],
                tables=[],
            )

            result = self.agent.run(context)
            result.logs.append("service: 统一工作流任务处理结束")
            return result

        except Exception as e:
            logs.append(f"service error: {str(e)}")
            return TaskResult(
                success=False,
                message="服务执行失败",
                answer="",
                logs=logs,
                error=str(e),
            )