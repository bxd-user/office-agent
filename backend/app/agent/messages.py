from __future__ import annotations

from typing import Any, Dict, List


def build_system_message(tool_schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "role": "system",
        "content": (
            "你是一个Office Agent。"
            "你可以通过工具读取和处理Word文档。"
            "当需要了解文件内容时，优先使用工具，不要臆测文件内容。"
            "如果用户的任务需要多步完成，请自行规划并按需调用工具。"
        ),
    }


def build_user_message(user_prompt: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "role": "user",
        "content": {
            "prompt": user_prompt,
            "files": files,
        },
    }


def tool_result_message(tool_name: str, result: Any) -> Dict[str, Any]:
    return {
        "role": "tool",
        "name": tool_name,
        "content": result,
    }