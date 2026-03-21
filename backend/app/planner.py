from dataclasses import dataclass, field
from typing import List

from app.tools.llm_client import LLMClient
from app.utils.json_utils import extract_json_object


@dataclass
class Plan:
    task_type: str
    steps: List[str] = field(default_factory=list)


class WorkflowPlanner:
    def __init__(self):
        self.llm = LLMClient()

    def create_plan(self, user_prompt: str, file_roles: list[str]) -> Plan:
        system_prompt = (
            "你是一个 Office 文档工作流规划助手。\n"
            "请根据用户需求和文件角色，生成任务类型和执行步骤。\n"
            "任务类型只能是：summarize、extract、fill。\n"
            "步骤只能从以下集合中选择："
            "collect_source_text, extract_fields, write_docx, summarize_document, summarize_result。\n"
            "只输出 JSON，不要解释。"
        )

        planner_prompt = (
            "请输出如下格式：\n"
            '{"task_type":"fill","steps":["collect_source_text","extract_fields","write_docx"]}\n\n'
            f"文件角色：{file_roles}\n"
            f"用户需求：{user_prompt}"
        )

        raw_answer = self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=planner_prompt,
        )

        data = extract_json_object(raw_answer)
        if not data:
            return self._fallback_plan(user_prompt, file_roles)

        task_type = data.get("task_type", "")
        steps = data.get("steps", [])

        if task_type not in {"summarize", "extract", "fill"}:
            return self._fallback_plan(user_prompt, file_roles)

        if not isinstance(steps, list):
            return self._fallback_plan(user_prompt, file_roles)

        steps = self._normalize_plan(task_type, steps, user_prompt, file_roles)
        return Plan(task_type=task_type, steps=steps)

    def _normalize_plan(
        self,
        task_type: str,
        steps: list[str],
        user_prompt: str,
        file_roles: list[str],
    ) -> list[str]:
        normalized = [step for step in steps if isinstance(step, str)]

        if task_type in {"extract", "fill", "summarize"}:
            if "collect_source_text" not in normalized:
                normalized.insert(0, "collect_source_text")

        if task_type == "extract":
            if "extract_fields" not in normalized:
                normalized.append("extract_fields")
            normalized = self._dedupe(normalized)

        elif task_type == "fill":
            if "extract_fields" not in normalized:
                normalized.append("extract_fields")
            if "write_docx" not in normalized:
                normalized.append("write_docx")

            if any(k in user_prompt for k in ["总结", "概括", "归纳"]):
                if "summarize_result" not in normalized:
                    normalized.append("summarize_result")

            normalized = self._reorder_fill_steps(normalized)
            normalized = self._dedupe(normalized)

        elif task_type == "summarize":
            if "summarize_document" not in normalized:
                normalized.append("summarize_document")
            normalized = self._dedupe(normalized)

        return normalized

    def _fallback_plan(self, user_prompt: str, file_roles: list[str]) -> Plan:
        prompt = user_prompt.strip()

        if any(keyword in prompt for keyword in ["填写", "填入", "填表"]):
            steps = ["collect_source_text", "extract_fields", "write_docx"]
            if any(k in prompt for k in ["总结", "概括", "归纳"]):
                steps.append("summarize_result")
            return Plan(task_type="fill", steps=steps)

        if any(keyword in prompt for keyword in ["提取", "抽取", "找出", "识别"]):
            return Plan(task_type="extract", steps=["collect_source_text", "extract_fields"])

        return Plan(task_type="summarize", steps=["collect_source_text", "summarize_document"])

    def _reorder_fill_steps(self, steps: list[str]) -> list[str]:
        ordered = []
        for step in ["collect_source_text", "extract_fields", "write_docx", "summarize_result"]:
            if step in steps:
                ordered.append(step)

        for step in steps:
            if step not in ordered:
                ordered.append(step)

        return ordered

    def _dedupe(self, items: list[str]) -> list[str]:
        result = []
        seen = set()
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result