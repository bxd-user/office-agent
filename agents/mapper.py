from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple

from agents.base import BaseAgent
from core.messages import AgentResult
from core.task_context import TaskContext


class MapperAgent(BaseAgent):
    """负责把 Word placeholders 映射到 Excel headers。

    输出写入：
    - ctx.field_mapping: {placeholder: excel_header}
    """

    name = "mapper"

    def __init__(self, llm_client=None) -> None:
        super().__init__()
        self.llm_client = llm_client

    def _run(self, ctx: TaskContext) -> AgentResult:
        excel_headers = self._normalize_names(ctx.get_excel_headers())
        word_placeholders = self._normalize_names(ctx.get_word_placeholders())

        if not excel_headers:
            return self.fail(ctx, "excel headers are empty, run inspector first")

        if not word_placeholders:
            return self.fail(ctx, "word placeholders are empty, run inspector first")

        ctx.log(f"[mapper] excel headers: {excel_headers}")
        ctx.log(f"[mapper] word placeholders: {word_placeholders}")

        # 1. 先做规则直连
        direct_mapping, unmapped_placeholders = self._build_direct_mapping(
            excel_headers=excel_headers,
            word_placeholders=word_placeholders,
        )

        ctx.log(f"[mapper] direct mapping count: {len(direct_mapping)}")
        if unmapped_placeholders:
            ctx.log(f"[mapper] unmapped placeholders after direct match: {unmapped_placeholders}")

        final_mapping = dict(direct_mapping)
        unmapped_before_llm = len(unmapped_placeholders)
        llm_used = False

        # 2. 如果还有未映射项，再走 LLM
        if unmapped_placeholders:
            llm_mapping = self._build_llm_mapping(
                ctx=ctx,
                excel_headers=excel_headers,
                unmapped_placeholders=unmapped_placeholders,
            )
            llm_used = bool(llm_mapping)

            # 只合并合法映射
            for placeholder, header in llm_mapping.items():
                if placeholder in unmapped_placeholders and header in excel_headers:
                    final_mapping[placeholder] = header

        # 3. 最终检查
        missing = [p for p in word_placeholders if p not in final_mapping]

        ctx.field_mapping = final_mapping
        ctx.shared["mapper_summary"] = {
            "mapping_count": len(final_mapping),
            "missing_placeholders": missing,
            "llm_configured": self.llm_client is not None,
            "llm_used": llm_used,
            "unmapped_before_llm": unmapped_before_llm,
        }

        ctx.log(f"[mapper] final mapping: {final_mapping}")
        if missing:
            ctx.log(f"[mapper] still missing placeholders: {missing}")

        return AgentResult.ok(
            message="Mapper finished successfully",
            data={
                "field_mapping": final_mapping,
                "mapping_count": len(final_mapping),
                "mapper_summary": ctx.shared["mapper_summary"],
                "missing_placeholders": missing,
            },
        )

    def _normalize_names(self, names: List[str]) -> List[str]:
        normalized: List[str] = []
        seen: set[str] = set()
        for name in names:
            text = str(name).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    def _build_direct_mapping(
        self,
        excel_headers: List[str],
        word_placeholders: List[str],
    ) -> Tuple[Dict[str, str], List[str]]:
        """同名优先的简单规则映射。"""
        excel_header_set = set(excel_headers)
        mapping: Dict[str, str] = {}
        unmapped: List[str] = []

        for placeholder in word_placeholders:
            if placeholder in excel_header_set:
                mapping[placeholder] = placeholder
            else:
                unmapped.append(placeholder)

        return mapping, unmapped

    def _build_llm_mapping(
        self,
        ctx: TaskContext,
        excel_headers: List[str],
        unmapped_placeholders: List[str],
    ) -> Dict[str, str]:
        """调用 LLM 做剩余映射。

        要求返回格式：
        {
          "姓名": "student_name",
          "班级": "class_name"
        }
        """
        if self.llm_client is None:
            ctx.log("[mapper] llm_client is not configured, skip llm mapping")
            return {}

        prompt = self._build_mapping_prompt(
            instruction=ctx.instruction,
            excel_headers=excel_headers,
            placeholders=unmapped_placeholders,
        )

        ctx.log("[mapper] calling llm for semantic mapping")

        try:
            response_text = self.llm_client.chat(
                system_prompt=self._system_prompt(),
                user_prompt=prompt,
            )
        except Exception as exc:  # noqa: BLE001
            ctx.log(f"[mapper] llm call failed: {exc}")
            return {}

        ctx.log(f"[mapper] llm raw response: {response_text}")

        parsed = self._parse_mapping_response(response_text)
        ctx.log(f"[mapper] llm parsed mapping: {parsed}")
        return parsed

    def _system_prompt(self) -> str:
        return (
            "你是一个 Office 文档字段映射助手。\n"
            "你的任务是把 Word 模板中的占位符，映射到 Excel 表头。\n"
            "请只返回 JSON 对象，不要输出解释，不要输出 markdown 代码块。\n"
            "JSON 格式示例：\n"
            "{\"姓名\": \"姓名\", \"班级\": \"班级\"}"
        )

    def _build_mapping_prompt(
        self,
        instruction: str,
        excel_headers: List[str],
        placeholders: List[str],
    ) -> str:
        return (
            f"用户任务：{instruction}\n\n"
            f"Excel 表头列表：{excel_headers}\n"
            f"Word 占位符列表：{placeholders}\n\n"
            "请为每个 Word 占位符，从 Excel 表头中选择最匹配的一项。\n"
            "要求：\n"
            "1. 只允许使用 Excel 表头列表中已有的字段名作为值\n"
            "2. 如果实在找不到合适项，就不要输出该字段\n"
            "3. 只输出 JSON 对象，不要输出解释\n"
        )

    def _parse_mapping_response(self, text: str) -> Dict[str, str]:
        """尽量从模型返回中提取 JSON。"""
        cleaned = text.strip()

        # 去掉可能的 markdown 代码块
        cleaned = self._strip_markdown_fence(cleaned)

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return {
                    str(k).strip(): str(v).strip()
                    for k, v in data.items()
                    if str(k).strip() and str(v).strip()
                }
        except Exception:
            pass

        # 尝试截取最外层 {...}
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and start < end:
            maybe_json = cleaned[start:end + 1]
            try:
                data = json.loads(maybe_json)
                if isinstance(data, dict):
                    return {
                        str(k).strip(): str(v).strip()
                        for k, v in data.items()
                        if str(k).strip() and str(v).strip()
                    }
            except Exception:
                pass

        return {}

    def _strip_markdown_fence(self, text: str) -> str:
        fenced = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fenced:
            return fenced.group(1).strip()
        return text