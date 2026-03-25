from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI


class LLMClient:
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._remote_enabled = bool(api_key and base_url)
        self._client = OpenAI(api_key=api_key, base_url=base_url) if self._remote_enabled else None

    def _chat_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Optional[str]:
        if not self._remote_enabled or self._client is None:
            return None

        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            content = resp.choices[0].message.content if resp.choices else ""
            if isinstance(content, str):
                content = content.strip()
            return content or None
        except Exception:
            return None

    def _chat_json(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        if not self._remote_enabled or self._client is None:
            return None

        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content if resp.choices else ""
            if not content:
                return None
            return json.loads(content)
        except Exception:
            return None

    def plan_task(self, user_prompt: str, files: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        lowered = (user_prompt or "").lower()
        is_summary = ("总结" in user_prompt) or ("摘要" in user_prompt) or ("summary" in lowered)

        file_roles = [
            {
                "file_id": f.get("file_id", f.get("filename", "")),
                "filename": f.get("filename", ""),
                "role": "data_source",
                "reason": "default fallback",
            }
            for f in files
        ]

        if is_summary:
            steps = [
                {
                    "step_id": "step_1",
                    "title": "Read document text",
                    "objective": "Read uploaded document text",
                    "suggested_tools": ["word.read_text"],
                    "inputs": {},
                    "expected_outputs": ["document text"],
                },
                {
                    "step_id": "step_2",
                    "title": "Summarize content",
                    "objective": "Generate concise summary",
                    "suggested_tools": ["understanding.summarize"],
                    "inputs": {},
                    "expected_outputs": ["summary"],
                },
            ]
            return {
                "goal": user_prompt,
                "task_type": "summarization",
                "file_roles": file_roles,
                "steps": steps,
                "success_criteria": ["Return a clear summary based on file content"],
                "assumptions": [],
                "requires_output_file": False,
            }

        return None

    def decide_step_actions(
        self,
        user_prompt: str,
        plan_goal: str,
        current_step: Dict[str, Any],
        memory_snapshot: Dict[str, Any],
        files: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        suggested_tools = current_step.get("suggested_tools", [])
        files = files or []
        first_file = files[0] if files else {}
        file_path = first_file.get("path", "")
        file_id = first_file.get("file_id", first_file.get("filename", ""))

        if "word.read_text" in suggested_tools and file_path:
            return {
                "tool_calls": [
                    {
                        "name": "word.read_text",
                        "arguments": {
                            "file_path": file_path,
                            "file_id": file_id,
                        },
                    }
                ]
            }

        if "understanding.summarize" in suggested_tools:
            texts = (memory_snapshot or {}).get("document_texts", {})
            text = ""
            if texts:
                first_key = next(iter(texts.keys()))
                text = texts.get(first_key, "")

            if not text and file_path:
                return {
                    "tool_calls": [
                        {
                            "name": "word.read_text",
                            "arguments": {
                                "file_path": file_path,
                                "file_id": file_id,
                            },
                        }
                    ]
                }

            return {
                "tool_calls": [
                    {
                        "name": "understanding.summarize",
                        "arguments": {
                            "text": text,
                            "instruction": user_prompt,
                            "file_id": file_id,
                        },
                    }
                ]
            }

        return {"tool_calls": []}

    def verify_step(
        self,
        user_prompt: str,
        plan_goal: str,
        current_step: Dict[str, Any],
        step_record: Dict[str, Any],
        memory_snapshot: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return {
            "passed": bool(step_record.get("tool_calls")),
            "reason": "fallback verifier",
            "missing": [],
        }

    def critique_step_failure(
        self,
        user_prompt: str,
        step: Dict[str, Any],
        verifier_result: Dict[str, Any],
        memory_snapshot: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return {
            "action": "retry",
            "reason": "fallback critic",
        }

    def replan_task(
        self,
        user_prompt: str,
        current_plan: Dict[str, Any],
        memory_snapshot: Dict[str, Any],
        step_records: List[Dict[str, Any]],
    ):
        return None

    def finalize_response(
        self,
        user_prompt: str,
        plan: Dict[str, Any],
        memory_snapshot: Dict[str, Any],
        step_records: List[Dict[str, Any]],
    ) -> Optional[str]:
        for record in reversed(step_records or []):
            for call in record.get("tool_calls", []):
                result = call.get("result", {})
                content = result.get("content") if isinstance(result, dict) else None
                if call.get("tool_name") == "understanding.summarize" and isinstance(content, dict):
                    summary = content.get("summary")
                    if summary:
                        return summary

        output_files = (memory_snapshot or {}).get("output_files", [])
        if output_files:
            return "任务已完成，并已生成输出文件。"
        return "任务已执行完成。"

    def summarize_text(self, text: str, instruction: str = "") -> str:
        remote_summary = self._chat_text(
            system_prompt=(
                "你是一个专业文档总结助手。请基于输入文本生成简洁、准确、结构清晰的中文总结。"
                "不要编造事实；长度控制在150~260字。"
            ),
            user_prompt=f"指令：{instruction or '总结文档'}\n\n文档内容：\n{text}",
            temperature=0.2,
        )
        if remote_summary:
            return remote_summary

        clean = re.sub(r"\s+", " ", text or "").strip()
        if not clean:
            return "文档内容为空，无法总结。"

        max_len = 220
        if len(clean) <= max_len:
            return f"文档总结：{clean}"
        return f"文档总结：{clean[:max_len]}..."

    def extract_fields(self, content: Any, instruction: str) -> Dict[str, Any]:
        remote_data = self._chat_json(
            system_prompt=(
                "你是信息抽取助手。请严格输出JSON对象，不要输出额外文本。"
                "当字段不确定时可以省略，不要编造。"
            ),
            user_prompt=f"抽取要求：{instruction}\n\n内容：\n{json.dumps(content, ensure_ascii=False)}",
        )
        if isinstance(remote_data, dict):
            return remote_data

        if isinstance(content, dict):
            return content

        if isinstance(content, list):
            return {"items": content[:20]}

        text = str(content)
        pairs = {}
        for line in text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()
                if k:
                    pairs[k] = v

        if pairs:
            return pairs

        return {"text": text[:500]}

    def match_source_to_template(
        self,
        template_placeholders: List[str],
        source_content: Any,
        instruction: str = "",
    ) -> Dict[str, Any]:
        remote_mapping = self._chat_json(
            system_prompt=(
                "你是模板映射助手。请根据源内容为模板占位符生成映射，"
                "严格输出JSON对象：key为占位符名，value为填充值。"
                "找不到就不要输出该key。"
            ),
            user_prompt=(
                f"占位符：{json.dumps(template_placeholders, ensure_ascii=False)}\n"
                f"额外指令：{instruction}\n"
                f"源内容：{json.dumps(source_content, ensure_ascii=False)}"
            ),
        )
        if isinstance(remote_mapping, dict):
            return remote_mapping

        extracted = self.extract_fields(source_content, instruction)
        mapping: Dict[str, Any] = {}
        for key in template_placeholders:
            if key in extracted:
                mapping[key] = extracted[key]
            elif isinstance(extracted, dict):
                for ek, ev in extracted.items():
                    if key.lower() in str(ek).lower():
                        mapping[key] = ev
                        break
        return mapping