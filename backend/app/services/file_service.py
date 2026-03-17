import os
from fastapi import UploadFile
from app.utils import ensure_dir, unique_filename


class FileService:
    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir
        ensure_dir(upload_dir)

    async def save_upload(self, file: UploadFile) -> str:
        filename = unique_filename(file.filename or "upload.bin")
        path = os.path.join(self.upload_dir, filename)

        content = await file.read()
        with open(path, "wb") as f:
            f.write(content)

        return path