from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.routes import router


def create_app():
    app = FastAPI(title="Office Agent")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )

        body_schema = openapi_schema.get("components", {}).get("schemas", {}).get(
            "Body_run_workflow_agent_run_workflow_post"
        )
        if body_schema:
            files_schema = body_schema.get("properties", {}).get("files")
            if files_schema and isinstance(files_schema.get("items"), dict):
                items = files_schema["items"]
                if items.get("type") == "string" and items.get("contentMediaType"):
                    items.pop("contentMediaType", None)
                    items["format"] = "binary"

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    return app


app = create_app()