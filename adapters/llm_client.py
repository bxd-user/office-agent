from __future__ import annotations

from typing import Any, Optional

import requests

from app.config import settings


class LLMClient:
    """统一 LLM 调用客户端（DeepSeek/OpenAI 兼容接口）。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
        debug: bool = False,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = (base_url or settings.deepseek_base_url).rstrip("/")
        self.model = model or settings.model_name
        self.timeout = timeout
        self.debug = debug
        self.session = session or requests.Session()

        if not self.api_key:
            raise ValueError("DeepSeek API key is not configured")

        if not self.base_url:
            raise ValueError("DeepSeek base URL is not configured")

        if not self.model:
            raise ValueError("LLM model is not configured")

    def _chat_completions_url(self) -> str:
        # 兼容 base_url 已含 /v1 或不含 /v1 两种配置
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/chat/completions"

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """最小 chat 接口，返回纯文本 content。"""

        url = self._chat_completions_url()

        if not system_prompt.strip():
            raise ValueError("system_prompt is required")
        if not user_prompt.strip():
            raise ValueError("user_prompt is required")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        if self.debug:
            print("\n[LLM REQUEST]")
            print("model:", self.model)
            print("system:", system_prompt[:200])
            print("user:", user_prompt[:200])

        try:
            response = self.session.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout:
            raise RuntimeError("LLM request timeout")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM request error: {e}") from e

        if response.status_code != 200:
            raise RuntimeError(
                f"LLM request failed: {response.status_code}\n{response.text}"
            )

        data: dict[str, Any] = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Invalid LLM response: {data}") from e

        if self.debug:
            print("\n[LLM RESPONSE]")
            print(content[:500])

        return str(content)


def create_default_llm_client(debug: bool = False) -> Optional[LLMClient]:
    """按当前 settings 创建默认 LLM 客户端。未配置时返回 None。"""
    if not settings.deepseek_api_key or not settings.deepseek_base_url or not settings.model_name:
        return None
    return LLMClient(debug=debug)