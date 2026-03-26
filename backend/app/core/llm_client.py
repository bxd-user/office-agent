from __future__ import annotations

import json
import os
from typing import Any

import requests

from app.core.config import settings


class LLMClientError(Exception):
    pass


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 120,
    ) -> None:
        self.api_key = api_key or os.getenv("LLM_API_KEY", "") or settings.LLM_API_KEY
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "") or settings.LLM_BASE_URL).rstrip("/")
        self.model = model or os.getenv("LLM_MODEL", "") or settings.LLM_MODEL
        self.timeout = timeout
        self.enabled = bool(self.api_key and self.base_url and self.model)

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        if not self.enabled:
            raise LLMClientError("LLM is not configured")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        if response_format:
            payload["response_format"] = response_format

        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        if resp.status_code >= 400:
            raise LLMClientError(f"LLM request failed: {resp.status_code} {resp.text}")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise LLMClientError(f"Invalid LLM response format: {e}") from e

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        raw = self.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(raw)
        except Exception as e:
            raise LLMClientError(f"Failed to parse LLM JSON response: {e}\nRaw:\n{raw}") from e