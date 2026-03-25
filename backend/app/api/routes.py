from __future__ import annotations

import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form

from app.agent.runtime import AgentRuntime
from app.agent.session import AgentSession
from app.api.schemas import AgentResponse
from app.core.config import settings
from app.core.file_store import FileStore
from app.core.llm_client import LLMClient
from app.document.word.adapter import WordAdapter
from app.mcp.client import LocalMCPClient
from app.mcp.registry import MCPServerRegistry
from app.mcp.servers.file_server import FileServer
from app.mcp.servers.word_server import WordServer
from app.mcp.servers.understanding_server import UnderstandingServer

router = APIRouter()


def build_runtime() -> AgentRuntime:
    file_store = FileStore(
        upload_dir=settings.UPLOAD_DIR,
        output_dir=settings.OUTPUT_DIR,
    )
    llm_client = LLMClient(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )
    word_adapter = WordAdapter()

    registry = MCPServerRegistry()
    registry.register_server(FileServer(file_store=file_store))
    registry.register_server(WordServer(word_adapter=word_adapter))
    registry.register_server(UnderstandingServer(llm_client=llm_client))

    mcp_client = LocalMCPClient(registry=registry)
    return AgentRuntime(llm_client=llm_client, mcp_client=mcp_client)


@router.post("/agent/run", response_model=AgentResponse)
async def run_agent(
    prompt: str = Form(...),
    files: list[UploadFile] = File(default=[]),
):
    try:
        task_id = str(uuid.uuid4())
        upload_dir = os.path.join(settings.UPLOAD_DIR, task_id)
        os.makedirs(upload_dir, exist_ok=True)

        file_infos = []
        for idx, f in enumerate(files, start=1):
            filename = f.filename or f"upload_{idx}"
            save_path = os.path.join(upload_dir, filename)
            with open(save_path, "wb") as out:
                out.write(await f.read())

            file_infos.append({
                "file_id": filename,
                "filename": filename,
                "path": save_path,
            })

        runtime = build_runtime()
        session = AgentSession(
            task_id=task_id,
            user_prompt=prompt,
            files=file_infos,
        )
        result = runtime.run(session)

        return AgentResponse(
            success=True,
            answer=result.answer,
            output_files=result.output_files,
            tool_trace=result.tool_trace,
        )
    except Exception as e:
        detail = str(e).strip()
        if not detail:
            detail = repr(e)
        return AgentResponse(
            success=False,
            answer="",
            error=detail,
        )