from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv_file(dotenv_path: Path) -> None:
    if not dotenv_path.exists() or not dotenv_path.is_file():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(slots=True)
class Settings:
    deepseek_api_key: str = ""
    deepseek_base_url: str = ""
    model_name: str = ""
    upload_dir: str = "./storage/uploads"
    output_dir: str = "./storage/outputs"
    temp_dir: str = "./storage/temp"

    @classmethod
    def from_env(cls) -> "Settings":
        project_root = Path(__file__).resolve().parents[1]
        load_dotenv_file(project_root / ".env")

        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY", ""),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL") or os.getenv("LLM_BASE_URL", ""),
            model_name=os.getenv("MODEL_NAME") or os.getenv("LLM_MODEL", ""),
            upload_dir=os.getenv("UPLOAD_DIR", "./storage/uploads"),
            output_dir=os.getenv("OUTPUT_DIR", "./storage/outputs"),
            temp_dir=os.getenv("TEMP_DIR", "./storage/temp"),
        )

    def ensure_dirs(self) -> None:
        for raw_path in (self.upload_dir, self.output_dir, self.temp_dir):
            Path(raw_path).mkdir(parents=True, exist_ok=True)


settings = Settings.from_env()
settings.ensure_dirs()