from __future__ import annotations

from typing import Any, Dict, List

from app.agent.plan_models import ExecutionPlan, FileRole, PlanStep


class PlannerV2:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def build_plan(self, user_prompt: str, files: List[Dict[str, Any]]) -> ExecutionPlan:
        """
        第一版先做“半结构化规划”：
        1. 让 LLM 识别任务类型
        2. 识别文件角色
        3. 输出步骤
        如果 LLM 未实现，可先 fallback 到规则骨架
        """
        plan_data = self.llm_client.plan_task(
            user_prompt=user_prompt,
            files=files,
        )

        if not plan_data:
            return self._fallback_plan(user_prompt, files)

        file_roles = [
            FileRole(
                file_id=item["file_id"],
                filename=item["filename"],
                role=item.get("role", "unknown"),
                reason=item.get("reason", ""),
            )
            for item in plan_data.get("file_roles", [])
        ]

        steps = [
            PlanStep(
                step_id=step["step_id"],
                title=step["title"],
                objective=step["objective"],
                suggested_tools=step.get("suggested_tools", []),
                inputs=step.get("inputs", {}),
                expected_outputs=step.get("expected_outputs", []),
            )
            for step in plan_data.get("steps", [])
        ]

        return ExecutionPlan(
            goal=plan_data.get("goal", user_prompt),
            task_type=plan_data.get("task_type", "unknown"),
            file_roles=file_roles,
            steps=steps,
            success_criteria=plan_data.get("success_criteria", []),
            assumptions=plan_data.get("assumptions", []),
            requires_output_file=plan_data.get("requires_output_file", False),
        )

    def _fallback_plan(self, user_prompt: str, files: List[Dict[str, Any]]) -> ExecutionPlan:
        file_roles = []
        for f in files:
            role = "unknown"
            if "模板" in f["filename"] or "空表" in f["filename"] or "template" in f["filename"].lower():
                role = "template"
            else:
                role = "data_source"
            file_roles.append(
                FileRole(
                    file_id=f["file_id"],
                    filename=f["filename"],
                    role=role,
                    reason="fallback heuristic",
                )
            )

        steps = [
            PlanStep(
                step_id="step_1",
                title="Inspect files",
                objective="Read file content and structure",
                suggested_tools=["word.read_text", "word.extract_structure"],
                expected_outputs=["document content", "document structure"],
            ),
            PlanStep(
                step_id="step_2",
                title="Extract useful information",
                objective="Extract fields, summaries, or mappings required by the task",
                suggested_tools=["understanding.extract_fields", "understanding.summarize"],
                expected_outputs=["extracted fields or summary"],
            ),
            PlanStep(
                step_id="step_3",
                title="Produce final result",
                objective="Generate final answer or write output file if needed",
                suggested_tools=["word.replace_text"],
                expected_outputs=["final answer or output file"],
            ),
        ]

        return ExecutionPlan(
            goal=user_prompt,
            task_type="generic_word_task",
            file_roles=file_roles,
            steps=steps,
            success_criteria=["Task should be completed with sufficient evidence from files"],
            assumptions=[],
            requires_output_file=("填" in user_prompt or "生成" in user_prompt or "输出文件" in user_prompt),
        )