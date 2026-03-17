import os
import uuid


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def unique_filename(filename: str) -> str:
    ext = os.path.splitext(filename)[1]
    return f"{uuid.uuid4().hex}{ext}"