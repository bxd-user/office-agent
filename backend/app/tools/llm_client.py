import os
from openai import OpenAI


class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.base_url = os.getenv("LLM_BASE_URL", "")
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")

        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        else:
            self.client = None

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        统一调用接口
        """

        # ===== 没配置 → fallback =====
        if not self.client:
            return self._mock_response(system_prompt, user_prompt)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            if not response.choices:
                return "LLM返回为空"

            message = response.choices[0].message

            if not message or not message.content:
                return "LLM返回内容为空"

            return message.content

        except Exception as e:
            return f"LLM调用失败: {str(e)}"

    def _mock_response(self, system_prompt: str, user_prompt: str) -> str:
        return (
            "【模拟LLM输出】\n\n"
            "请配置 LLM_API_KEY 使用真实模型\n\n"
            f"输入片段:\n{user_prompt[:200]}"
        )