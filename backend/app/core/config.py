from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "office-agent"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "deepseek-chat"
    UPLOAD_DIR: str = "storage/uploads"
    OUTPUT_DIR: str = "storage/outputs"

    class Config:
        env_file = ".env"


settings = Settings()