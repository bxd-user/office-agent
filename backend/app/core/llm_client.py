import os
import json
from openai import OpenAI


class DeepSeekClient:
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("未设置 DEEPSEEK_API_KEY")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

    def build_field_mapping(
        self,
        instruction: str,
        excel_fields: list[str],
        word_fields: list[str],
    ) -> dict:
        system_prompt = """
你是一个 Office 表单字段映射助手。

任务：
1. 用户想把 Excel 里的数据填写到 Word 表单。
2. 你会收到：
   - 用户指令
   - Excel 字段列表
   - Word 字段列表
3. 你的目标是给出 Word 字段 -> Excel 字段 的映射。
4. 只输出 JSON，不要输出任何解释。
5. 格式必须严格为：

{
  "mapping": {
    "Word字段1": "Excel字段A",
    "Word字段2": "Excel字段B"
  },
  "missing_fields": ["在Excel中找不到来源的Word字段"],
  "confidence": "high"
}

规则：
- 只在你有较高把握时才建立映射。
- 不确定就放到 missing_fields。
- 不要编造 Excel 字段名。
- mapping 的 key 必须来自 Word 字段列表。
- mapping 的 value 必须来自 Excel 字段列表。
"""

        user_prompt = f"""
用户指令：
{instruction}

Excel 字段列表：
{excel_fields}

Word 字段列表：
{word_fields}
"""

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content
        return json.loads(content)