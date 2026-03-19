from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, Response

from app.api import router as api_router


app = FastAPI(title="Office Agent Demo", version="0.1.0")
app.include_router(api_router)

APP_DIR = Path(__file__).resolve().parent
INDEX_PATH = APP_DIR / "index.html"


@app.get("/", response_class=HTMLResponse, response_model=None)
async def index() -> Response:
    if INDEX_PATH.exists():
        return FileResponse(INDEX_PATH)
    return HTMLResponse("<h1>Office Agent Demo</h1><p>index.html not found.</p>")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
