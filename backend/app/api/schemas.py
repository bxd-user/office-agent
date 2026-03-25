from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class AgentResponse(BaseModel):
    success: bool
    answer: str
    output_files: List[Dict[str, Any]] = []
    tool_trace: List[Dict[str, Any]] = []
    error: Optional[str] = None