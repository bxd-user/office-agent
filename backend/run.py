import uvicorn

if __name__ == "__main__":
    try:
        import fastapi  # noqa: F401
    except Exception:
        raise SystemExit(
            "当前 Python 环境缺少 fastapi。请先激活 agent 环境后重试：\n"
            "  conda activate agent\n"
            "  python run.py"
        )

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)