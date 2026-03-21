from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResultData(BaseModel):
    answer: str = ""
    file_name: str = ""
    text_length: int = 0
    structured_data: Optional[Dict[str, Any]] = None
    output_file_path: Optional[str] = None
    download_url: Optional[str] = None


class AgentResponse(BaseModel):
    success: bool = True
    message: str = "ok"
    result: ResultData = Field(default_factory=ResultData)
    logs: List[str] = Field(default_factory=list)
    error: Optional[str] = None