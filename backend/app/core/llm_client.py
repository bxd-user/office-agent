import json
import os

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
        excel_preview: dict | None = None,
      word_field_slots: list[dict] | None = None,
    ) -> dict:
        system_prompt = """
你是一个 Office 表单字段映射助手。

任务：
1. 用户想把 Excel 里的数据填写到 Word 表单。
2. 你会收到：
   - 用户指令
   - Excel 字段列表
   - Excel 内容预览（可能包含 sheet 名和样例数据）
   - Word 字段列表
  - Word 字段列表
  - Word 字段槽位信息（可能包含来源位置和置信度）
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
- 如果 Excel 预览里能看到字段语义（例如样例值），优先利用它提高匹配准确性。
- 若 Word 字段列表与字段槽位冲突，优先参考高置信度槽位。
"""

        user_prompt = f"""
用户指令：
{instruction}

Excel 字段列表：
{excel_fields}

Word 字段列表：
{word_fields}

Word 字段槽位：
{word_field_slots or []}

Excel 内容预览：
{excel_preview or {}}
"""

        return self._chat_json(system_prompt=system_prompt, user_prompt=user_prompt)

    def analyze_excel_structure(self, instruction: str, excel_preview: dict) -> dict:
        system_prompt = """
你是 Excel 结构分析助手，需要先判断表格结构，再交给程序读取。

目标：根据 Excel 预览内容，识别每个 sheet 的表头行和数据起始行。
必须只输出 JSON，格式：

{
  "primary_sheet": "人员信息",
  "sheets": [
    {
      "name": "人员信息",
      "header_row_index": 0,
      "data_start_row_index": 1,
      "confidence": "high",
      "reason": "第1行是字段名，第2行开始是数据"
    }
  ]
}

规则：
- 行号从 0 开始。
- header_row_index 和 data_start_row_index 必须是非负整数。
- 若不确定，优先给出最可能结构，不要返回空。
"""

        user_prompt = f"""
用户指令：
{instruction}

Excel 预览：
{excel_preview}
"""

        return self._chat_json(system_prompt=system_prompt, user_prompt=user_prompt)

    def plan_tool_calls(
        self,
        instruction: str,
        file_inventory: list[dict],
        available_tools: list[dict],
    ) -> dict:
        system_prompt = """
你是任务编排助手，需要根据用户指令规划工具调用步骤。

你只能使用提供的工具名，输出严格 JSON：
{
  "goal": "任务目标",
  "steps": [
    {
      "tool": "tool_name",
      "action": "read|write|extract_fields|fill_context",
      "args": {"k": "v"},
      "condition": "可选，has:key 或 missing:key",
      "on_fail": "continue|break",
      "reason": "为什么调用"
    }
  ]
}

规则：
- steps 至少 1 步，最多 8 步。
- tool 必须来自 available_tools.name。
- action 必须为 read/write/extract_fields/fill_context 之一。
- args 必须是对象。
- 如果用户要求从 Excel 到 Word 的处理，建议包含：
  1) excel.read
  2) word.read
  3) word.fill_context
"""

        user_prompt = f"""
用户指令：
{instruction}

文件清单：
{file_inventory}

可用工具：
{available_tools}
"""

        return self._chat_json(system_prompt=system_prompt, user_prompt=user_prompt)

    def _chat_json(self, system_prompt: str, user_prompt: str) -> dict:
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
        if content is None:
          raise ValueError("LLM 返回为空，无法解析 JSON")
        return json.loads(content)
