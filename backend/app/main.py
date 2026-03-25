from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="Office Agent MCP")

app.include_router(router, prefix="/api")