from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI


class LLMClient:
    def __init__(self) -> None:
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        self.api_key = os.getenv("LLM_API_KEY", "").strip()
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").strip()

        self.client: Optional[OpenAI] = None
        self.enabled = False

        if not self.api_key:
            print("[LLM] disabled: missing LLM_API_KEY")
            return

        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            self.enabled = True
            print(f"[LLM] initialized: model={self.model}, base_url={self.base_url}")
        except Exception as e:
            print(f"[LLM] init failed: {e}")
            self.client = None
            self.enabled = False

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0) -> str:
        if not self.enabled or self.client is None:
            condensed = " ".join((user_prompt or "").split())
            if len(condensed) > 200:
                condensed = condensed[:200] + "..."
            return f"自动摘要（本地回退）：{condensed}" if condensed else "自动摘要（本地回退）：无可用内容"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content or ""
            return content.strip()
        except Exception as e:
            print(f"[LLM] generate failed: {e}")
            condensed = " ".join((user_prompt or "").split())
            if len(condensed) > 200:
                condensed = condensed[:200] + "..."
            return f"自动摘要（本地回退）：{condensed}" if condensed else "自动摘要（本地回退）：无可用内容"

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0,
    ) -> Dict[str, Any]:
        raw = self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        return self._parse_json_object(raw)

    def generate_tool_plan(
        self,
        user_prompt: str,
        files: List[Dict[str, Any]],
        available_tools: List[Dict[str, Any]],
    ) -> str:
        if not self.enabled or self.client is None:
            return self._fallback_tool_plan(user_prompt, files, available_tools)

        system_prompt = self._build_tool_planner_system_prompt()
        planner_user_prompt = self._build_tool_planner_user_prompt(
            user_prompt=user_prompt,
            files=files,
            available_tools=available_tools,
        )

        raw = self.generate(
            system_prompt=system_prompt,
            user_prompt=planner_user_prompt,
            temperature=0,
        )

        parsed = self._parse_json_object(raw)
        if self._is_valid_plan(parsed, available_tools):
            return json.dumps(parsed, ensure_ascii=False)

        print("[LLM] planner returned invalid plan, using fallback plan")
        return self._fallback_tool_plan(user_prompt, files, available_tools)

    def _build_tool_planner_system_prompt(self) -> str:
        return """
You are a planning agent for an office document workflow system.

Your task:
1. Understand the user's goal.
2. Inspect the provided file list and available tools.
3. Produce a valid execution plan in JSON only.
4. Each step must choose exactly one tool from available_tools.
5. args must be concrete JSON values or state references like "$source_text.text".
6. Prefer minimal plans, but include all required steps.

Hard rules:
- Output JSON only. No markdown. No explanation.
- Do not invent tools.
- Use file roles from the input when helpful.
- For summarization tasks, usually read the source file first, then call llm.summarize.
- For extraction tasks, usually read the source file first, then call llm.extract_fields.
- For template filling tasks, usually:
  1) read source text
  2) extract template placeholders
  3) call llm.extract_for_template
  4) fill template
  5) verify the output if verify tool exists

Output schema:
{
  "goal": "string",
  "steps": [
    {
      "step_id": "s1",
      "tool_name": "tool.name",
      "args": {},
      "reason": "string",
      "depends_on": [],
      "output_key": "string"
    }
  ]
}
""".strip()

    def _build_tool_planner_user_prompt(
        self,
        user_prompt: str,
        files: List[Dict[str, Any]],
        available_tools: List[Dict[str, Any]],
    ) -> str:
        payload = {
            "user_request": user_prompt,
            "files": files,
            "available_tools": available_tools,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def summarize(self, text: str, user_prompt: str) -> str:
        prompt = f"""用户需求：
{user_prompt}

文档内容：
{text}

请输出简洁、自然、结构清晰的中文摘要。
"""
        raw = self.generate(
            system_prompt="你是一个办公文档总结助手，输出自然、准确、简洁的中文总结。",
            user_prompt=prompt,
            temperature=0.2,
        )
        return (raw or "").strip()

    def extract_fields(self, text: str, fields: List[str], user_prompt: str) -> Dict[str, Any]:
        field_text = ", ".join(fields) if fields else "请提取文档中的关键信息"

        prompt = f"""请从下面文档中提取字段，并且只输出 JSON 对象。

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
            system_prompt=f"你是一个信息抽取助手。用户需求：{user_prompt}",
            user_prompt=prompt,
            temperature=0,
        )
        if not raw:
            return {}
        return self._parse_json_object(raw)

    def extract_for_template(
        self,
        source_text: str,
        placeholders: List[str],
        user_prompt: str,
    ) -> Dict[str, Any]:
        prompt = f"""你需要根据用户需求和源文档内容，为模板占位符直接生成最终填充值。

用户需求：
{user_prompt}

模板占位符：
{json.dumps(placeholders, ensure_ascii=False, indent=2)}

源文档内容：
{source_text}

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

        normalized_filled: Dict[str, Any] = {}
        for ph in placeholders:
            normalized_filled[ph] = filled_data.get(ph, "")

        normalized_missing: List[str] = []
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

    def repair_fill_data(
        self,
        user_prompt: str,
        source_text: str,
        placeholders: List[str],
        current_fill_data: Dict[str, Any],
        missing_fields: List[str],
        unreplaced_placeholders: List[str],
    ) -> Dict[str, Any]:
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

        normalized_filled: Dict[str, Any] = {}
        for ph in placeholders:
            if ph in filled_data:
                normalized_filled[ph] = filled_data[ph]
            elif current_fill_data and ph in current_fill_data:
                normalized_filled[ph] = current_fill_data[ph]
            else:
                normalized_filled[ph] = ""

        normalized_missing: List[str] = []
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

    def _fallback_tool_plan(
        self,
        user_prompt: str,
        files: List[Dict[str, Any]],
        available_tools: List[Dict[str, Any]],
    ) -> str:
        tool_names = {tool.get("name") for tool in available_tools}
        roles = {f.get("role") for f in files}
        lowered = (user_prompt or "").lower()

        # summarize
        if "word.read_text" in tool_names and "llm.summarize" in tool_names:
            if any(k in user_prompt for k in ["总结", "摘要", "概括"]) or "summary" in lowered:
                role = "source" if "source" in roles else (next(iter(roles)) if roles else "source")
                return json.dumps(
                    {
                        "goal": "读取并总结文档",
                        "steps": [
                            {
                                "step_id": "s1",
                                "tool_name": "word.read_text",
                                "args": {"file_role": role},
                                "reason": "读取文档文本",
                                "depends_on": [],
                                "output_key": "source_text",
                            },
                            {
                                "step_id": "s2",
                                "tool_name": "llm.summarize",
                                "args": {
                                    "text": "$source_text.text",
                                    "user_prompt": user_prompt,
                                },
                                "reason": "总结文档内容",
                                "depends_on": ["s1"],
                                "output_key": "summary_result",
                            },
                        ],
                    },
                    ensure_ascii=False,
                )

        # template fill
        if {
            "word.read_text",
            "word.extract_placeholders",
            "llm.extract_for_template",
            "word.fill_template",
        }.issubset(tool_names):
            if any(k in user_prompt for k in ["填写", "填入", "填充", "生成到模板"]):
                source_role = "source" if "source" in roles else "source"
                template_role = "template" if "template" in roles else "template"
                steps = [
                    {
                        "step_id": "s1",
                        "tool_name": "word.read_text",
                        "args": {"file_role": source_role},
                        "reason": "读取源材料",
                        "depends_on": [],
                        "output_key": "source_text",
                    },
                    {
                        "step_id": "s2",
                        "tool_name": "word.extract_placeholders",
                        "args": {"file_role": template_role},
                        "reason": "提取模板占位符",
                        "depends_on": [],
                        "output_key": "template_meta",
                    },
                    {
                        "step_id": "s3",
                        "tool_name": "llm.extract_for_template",
                        "args": {
                            "source_text": "$source_text.text",
                            "placeholders": "$template_meta.placeholders",
                            "user_prompt": user_prompt,
                        },
                        "reason": "生成模板填充值",
                        "depends_on": ["s1", "s2"],
                        "output_key": "fill_result",
                    },
                    {
                        "step_id": "s4",
                        "tool_name": "word.fill_template",
                        "args": {
                            "file_role": template_role,
                            "fill_data": "$fill_result.filled_data",
                        },
                        "reason": "将内容写入模板",
                        "depends_on": ["s3"],
                        "output_key": "filled_doc",
                    },
                ]
                if "doc.verify" in tool_names:
                    steps.append(
                        {
                            "step_id": "s5",
                            "tool_name": "doc.verify",
                            "args": {
                                "output_path": "$filled_doc.output_path",
                                "expected_placeholders": "$template_meta.placeholders",
                                "filled_data": "$fill_result.filled_data",
                            },
                            "reason": "校验模板填充结果",
                            "depends_on": ["s4"],
                            "output_key": "verify_result",
                        }
                    )

                return json.dumps(
                    {
                        "goal": "根据源文档填写模板",
                        "steps": steps,
                    },
                    ensure_ascii=False,
                )

        return json.dumps({"goal": "无可用步骤", "steps": []}, ensure_ascii=False)

    def _is_valid_plan(self, data: Dict[str, Any], available_tools: List[Dict[str, Any]]) -> bool:
        if not isinstance(data, dict):
            return False
        if not isinstance(data.get("goal"), str):
            return False
        steps = data.get("steps")
        if not isinstance(steps, list) or not steps:
            return False

        tool_names = {tool.get("name") for tool in available_tools}
        seen_ids = set()

        for step in steps:
            if not isinstance(step, dict):
                return False
            step_id = step.get("step_id")
            tool_name = step.get("tool_name")
            args = step.get("args")
            depends_on = step.get("depends_on", [])
            output_key = step.get("output_key")

            if not isinstance(step_id, str) or not step_id:
                return False
            if step_id in seen_ids:
                return False
            seen_ids.add(step_id)

            if not isinstance(tool_name, str) or tool_name not in tool_names:
                return False
            if not isinstance(args, dict):
                return False
            if not isinstance(depends_on, list):
                return False
            if output_key is not None and not isinstance(output_key, str):
                return False

        return True

    def _parse_json_object(self, text: str) -> Dict[str, Any]:
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
    
    def decide_next_step(
        self,
        user_prompt: str,
        files: List[Dict[str, Any]],
        available_tools: List[Dict[str, Any]],
        state: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        system_prompt = """
    You are an office workflow agent.

    At each turn, decide exactly one next action.

    Output JSON only.

    If more work is needed, output:
    {
    "type": "tool_call",
    "tool_name": "tool.name",
    "args": {},
    "reason": "string",
    "output_key": "string"
    }

    If the task is complete, output:
    {
    "type": "final",
    "final_answer": "string"
    }
    """.strip()

        user_data = {
            "user_request": user_prompt,
            "files": files,
            "available_tools": available_tools,
            "state": state,
            "history": history,
        }

        raw = self.generate(
            system_prompt=system_prompt,
            user_prompt=json.dumps(user_data, ensure_ascii=False, indent=2),
            temperature=0,
        )
        return self._parse_json_object(raw)
    
    def _is_valid_react_decision(
        self,
        data: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
    ) -> bool:
        if not isinstance(data, dict):
            return False

        decision_type = data.get("type")
        if decision_type == "final":
            return isinstance(data.get("final_answer"), str)

        if decision_type != "tool_call":
            return False

        tool_names = {tool.get("name") for tool in available_tools}
        tool_name = data.get("tool_name")
        args = data.get("args", {})
        output_key = data.get("output_key")

        if not isinstance(tool_name, str) or tool_name not in tool_names:
            return False
        if not isinstance(args, dict):
            return False
        if output_key is not None and not isinstance(output_key, str):
            return False

        return True

    def _fallback_next_step(
        self,
        user_prompt: str,
        files: List[Dict[str, Any]],
        available_tools: List[Dict[str, Any]],
        state: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        tool_names = {tool.get("name") for tool in available_tools}
        lowered = (user_prompt or "").lower()

        # 已有总结 -> 直接结束
        summary = state.get("summary")
        if isinstance(summary, dict) and isinstance(summary.get("summary"), str):
            return {
                "type": "final",
                "final_answer": summary["summary"],
            }

        # 已有填充文档 -> 直接结束
        filled_doc = state.get("filled_doc")
        if isinstance(filled_doc, dict) and isinstance(filled_doc.get("output_path"), str):
            return {
                "type": "final",
                "final_answer": f"已完成，输出文件: {filled_doc['output_path']}",
            }

        # 总结任务
        if any(k in user_prompt for k in ["总结", "摘要", "概括"]) or "summary" in lowered:
            if "source_text" not in state and "word.read_text" in tool_names:
                return {
                    "type": "tool_call",
                    "tool_name": "word.read_text",
                    "args": {"file_role": "source"},
                    "reason": "先读取源文档文本",
                    "output_key": "source_text",
                }

            if "source_text" in state and "llm.summarize" in tool_names and "summary" not in state:
                return {
                    "type": "tool_call",
                    "tool_name": "llm.summarize",
                    "args": {
                        "text": "$source_text.text",
                        "user_prompt": user_prompt,
                    },
                    "reason": "根据源文档生成摘要",
                    "output_key": "summary",
                }

        # 模板填写任务
        if any(k in user_prompt for k in ["填写", "填入", "填充", "生成到模板"]):
            if "source_text" not in state and "word.read_text" in tool_names:
                return {
                    "type": "tool_call",
                    "tool_name": "word.read_text",
                    "args": {"file_role": "source"},
                    "reason": "先读取源材料",
                    "output_key": "source_text",
                }

            if "template_meta" not in state and "word.extract_placeholders" in tool_names:
                return {
                    "type": "tool_call",
                    "tool_name": "word.extract_placeholders",
                    "args": {"file_role": "template"},
                    "reason": "读取模板占位符",
                    "output_key": "template_meta",
                }

            if (
                "source_text" in state
                and "template_meta" in state
                and "fill_result" not in state
                and "llm.extract_for_template" in tool_names
            ):
                return {
                    "type": "tool_call",
                    "tool_name": "llm.extract_for_template",
                    "args": {
                        "source_text": "$source_text.text",
                        "placeholders": "$template_meta.placeholders",
                        "user_prompt": user_prompt,
                    },
                    "reason": "根据源材料生成模板填充值",
                    "output_key": "fill_result",
                }

            if "fill_result" in state and "filled_doc" not in state and "word.fill_template" in tool_names:
                return {
                    "type": "tool_call",
                    "tool_name": "word.fill_template",
                    "args": {
                        "file_role": "template",
                        "fill_data": "$fill_result.filled_data",
                    },
                    "reason": "将填充值写入模板",
                    "output_key": "filled_doc",
                }

            if (
                "filled_doc" in state
                and "verify_result" not in state
                and "doc.verify" in tool_names
                and "template_meta" in state
                and "fill_result" in state
            ):
                return {
                    "type": "tool_call",
                    "tool_name": "doc.verify",
                    "args": {
                        "output_path": "$filled_doc.output_path",
                        "expected_placeholders": "$template_meta.placeholders",
                        "filled_data": "$fill_result.filled_data",
                    },
                    "reason": "校验模板填充结果",
                    "output_key": "verify_result",
                }

        # 默认结束
        return {
            "type": "final",
            "final_answer": "任务执行完成",
        }