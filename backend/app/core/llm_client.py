import os
import json
from typing import Any

from openai import OpenAI

class LLMClient:
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0) -> str:
        try:
            api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.deepseek.com/v1"
            model = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "deepseek-chat"

            client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt or ""},
                    {"role": "user", "content": user_prompt or ""},
                ],
                temperature=temperature,
            )

            content = response.choices[0].message.content

            if content is None:
                return ""

            return str(content)

        except Exception as e:
            raise RuntimeError(f"LLM generate failed: {str(e)}")

    def map_fields_to_placeholders(
        self,
        extracted_data: dict,
        placeholders: list[str],
        user_prompt: str,
    ) -> dict:
        prompt = f"""你需要把提取出的字段映射到模板占位符。

    用户需求：
    {user_prompt}

    提取结果：
    {json.dumps(extracted_data, ensure_ascii=False, indent=2)}

    模板占位符：
    {json.dumps(placeholders, ensure_ascii=False, indent=2)}

    要求：
    1. 只输出 JSON 对象
    2. key 必须来自模板占位符
    3. value 必须来自提取结果，或为空字符串
    4. 不要输出解释
    """
        raw = self.generate(
            system_prompt="你是一个字段映射助手，负责把提取结果准确映射到模板占位符。",
            user_prompt=prompt,
            temperature=0,
        )

        if not raw:
            return {}

        return self._parse_json_object(raw)

    def summarize(self, text: str, system_prompt: str, user_prompt: str) -> str:
        prompt = f"""用户需求：
{user_prompt}

文档内容：
{text}

请输出简洁中文摘要。
"""
        raw = self.generate(
            system_prompt=system_prompt,
            user_prompt=prompt,
            temperature=0.2,
        )
        return (raw or "").strip()

    def extract_fields(self, text: str, fields: list[str], system_prompt: str) -> dict:
        field_text = ", ".join(fields) if fields else "请提取文档中的关键信息"

        prompt = f"""请从下面文档中提取字段，并只输出 JSON 对象。

字段列表：
{field_text}

文档内容：
{text}

输出要求：
1. 只输出 JSON
2. key 必须来自字段列表
3. 找不到就填空字符串
"""
        raw = self.generate(
            system_prompt=system_prompt,
            user_prompt=prompt,
            temperature=0,
        )

        if not raw:
            return {}

        return self._parse_json_object(raw)

    def extract_for_template(
        self,
        text: str,
        placeholders: list[str],
        user_prompt: str,
    ) -> dict:
        prompt = f"""你需要根据用户需求和源文档内容，为模板占位符直接生成最终填充值。

    用户需求：
    {user_prompt}

    模板占位符：
    {json.dumps(placeholders, ensure_ascii=False, indent=2)}

    源文档内容：
    {text}

    输出要求：
    1. 只输出 JSON
    2. JSON 格式必须为：
    {{
    "filled_data": {{
        "占位符1": "值1",
        "占位符2": "值2"
    }},
    "missing_fields": ["未找到的占位符1", "未找到的占位符2"]
    }}
    3. filled_data 的 key 必须来自模板占位符
    4. 找不到就不要乱编，可以放进 missing_fields，filled_data 对应值可填空字符串
    5. 不要输出解释
    """
        raw = self.generate(
            system_prompt="你是一个办公文档填充助手，负责根据材料内容直接为模板占位符生成最终填充值。",
            user_prompt=prompt,
            temperature=0,
        )

        if not raw:
            return {"filled_data": {}, "missing_fields": placeholders}

        data = self._parse_json_object(raw)
        if not isinstance(data, dict):
            return {"filled_data": {}, "missing_fields": placeholders}

        filled_data = data.get("filled_data")
        missing_fields = data.get("missing_fields")

        if not isinstance(filled_data, dict):
            filled_data = {}

        if not isinstance(missing_fields, list):
            missing_fields = []

        # 强约束：只保留合法占位符
        normalized_filled = {}
        for ph in placeholders:
            if ph in filled_data:
                normalized_filled[ph] = filled_data[ph]
            else:
                normalized_filled[ph] = ""

        # 自动补 missing_fields
        normalized_missing = []
        seen = set()
        for ph in placeholders:
            if not normalized_filled.get(ph):
                if ph not in seen:
                    seen.add(ph)
                    normalized_missing.append(ph)

        for ph in missing_fields:
            if ph in placeholders and ph not in seen:
                seen.add(ph)
                normalized_missing.append(ph)

        return {
            "filled_data": normalized_filled,
            "missing_fields": normalized_missing,
        }

    def _parse_json_object(self, text: str) -> dict:
        import json
        import re

        if not text:
            return {}

        text = text.strip()

        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()

        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            pass

        start = text.find("{")
        if start == -1:
            return {}

        depth = 0
        in_string = False
        escape = False

        for i in range(start, len(text)):
            ch = text[i]

            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        data = json.loads(candidate)
                        return data if isinstance(data, dict) else {}
                    except Exception:
                        return {}

        return {}
    
    def repair_fill_data(
        self,
        user_prompt: str,
        source_text: str,
        placeholders: list[str],
        current_fill_data: dict,
        missing_fields: list[str],
        unreplaced_placeholders: list[str],
    ) -> dict:
        prompt = f"""你需要修复一份模板填充数据。

用户需求：
{user_prompt}

模板占位符：
{json.dumps(placeholders, ensure_ascii=False, indent=2)}

源文档内容：
{source_text}

当前填充数据：
{json.dumps(current_fill_data, ensure_ascii=False, indent=2)}

当前缺失字段：
{json.dumps(missing_fields, ensure_ascii=False, indent=2)}

当前未替换占位符：
{json.dumps(unreplaced_placeholders, ensure_ascii=False, indent=2)}

输出要求：
1. 只输出 JSON
2. JSON 格式必须为：
{{
  "filled_data": {{
    "占位符1": "值1",
    "占位符2": "值2"
  }},
  "missing_fields": ["仍然无法确定的字段1", "仍然无法确定的字段2"]
}}
3. filled_data 的 key 必须来自模板占位符
4. 能从材料中确定就补全，不能确定就保持空字符串
5. 不要输出解释
"""
        raw = self.generate(
            system_prompt="你是一个办公文档修复助手，负责根据已有结果和缺失项修复模板填充数据。",
            user_prompt=prompt,
            temperature=0,
        )

        if not raw:
            return {
                "filled_data": current_fill_data or {},
                "missing_fields": missing_fields or [],
            }

        data = self._parse_json_object(raw)
        if not isinstance(data, dict):
            return {
                "filled_data": current_fill_data or {},
                "missing_fields": missing_fields or [],
            }

        filled_data = data.get("filled_data")
        returned_missing = data.get("missing_fields")

        if not isinstance(filled_data, dict):
            filled_data = current_fill_data or {}

        if not isinstance(returned_missing, list):
            returned_missing = missing_fields or []

        normalized_filled = {}
        for ph in placeholders:
            if ph in filled_data:
                normalized_filled[ph] = filled_data[ph]
            elif current_fill_data and ph in current_fill_data:
                normalized_filled[ph] = current_fill_data[ph]
            else:
                normalized_filled[ph] = ""

        normalized_missing = []
        seen = set()

        for ph in placeholders:
            value = normalized_filled.get(ph, "")
            if value is None or str(value).strip() == "":
                if ph not in seen:
                    seen.add(ph)
                    normalized_missing.append(ph)

        for ph in returned_missing:
            if ph in placeholders and ph not in seen:
                seen.add(ph)
                normalized_missing.append(ph)

        return {
            "filled_data": normalized_filled,
            "missing_fields": normalized_missing,
        }