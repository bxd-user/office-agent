from __future__ import annotations

import os
from typing import Any, Dict, List


class FileStore:
    def __init__(self, upload_dir: str, output_dir: str):
        self.upload_dir = upload_dir
        self.output_dir = output_dir

    def list_task_files(self, task_id: str) -> List[Dict[str, Any]]:
        task_dir = os.path.join(self.upload_dir, task_id)
        if not os.path.exists(task_dir):
            return []

        items = []
        for name in os.listdir(task_dir):
            path = os.path.join(task_dir, name)
            if os.path.isfile(path):
                items.append({
                    "file_id": name,
                    "filename": name,
                    "path": path,
                })
        return items

    def get_file_info(self, task_id: str, file_id: str) -> Dict[str, Any]:
        path = os.path.join(self.upload_dir, task_id, file_id)
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        return {
            "file_id": file_id,
            "filename": os.path.basename(path),
            "path": path,
            "size": os.path.getsize(path),
        }

    def make_output_path(self, task_id: str, filename: str) -> str:
        output_task_dir = os.path.join(self.output_dir, task_id)
        os.makedirs(output_task_dir, exist_ok=True)
        return os.path.join(output_task_dir, filename)