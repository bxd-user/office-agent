from __future__ import annotations

from typing import Any

from app.agent.execution_state import ExecutionState
from app.domain.models import TaskContext, TaskResult
from app.tools.word.verifier import DocxVerifier

class StepExecutor:
    def __init__(self):
        self.verifier = DocxVerifier()

    def run(
        self,
        agent: Any,
        context: TaskContext,
        plan: Any,
        logs: list[str],
    ) -> TaskResult:
        state = ExecutionState()
        logs.append("executor: 开始按计划执行")

        try:
            for step in plan.steps:
                logs.append(f"executor: 开始步骤 {step.step_id} -> {step.action}")
                record = state.add_step_record(step.step_id, step.action)

                try:
                    output = self._execute_step(
                        agent=agent,
                        context=context,
                        step=step,
                        state=state,
                        logs=logs,
                    )
                    record.status = "success"
                    record.output = output
                    logs.append(f"executor: 步骤成功 -> {step.step_id}")
                except Exception as e:
                    record.status = "failed"
                    record.error = str(e)
                    logs.append(f"executor: 步骤失败 -> {step.step_id}: {str(e)}")
                    return TaskResult(
                        success=False,
                        message=f"步骤执行失败: {step.action}",
                        answer=state.summary_text or "",
                        structured_data=state.structured_data or None,
                        output_file_path=state.output_file_path,
                        logs=logs,
                        error=str(e),
                    )

            logs.append("executor: 全部步骤执行完成")

            final_answer = state.summary_text or ""

            if plan.task_type == "extract_fields" and state.structured_data:
                final_answer = str(state.structured_data)

            if plan.task_type == "extract_and_fill" and state.output_file_path:
                if state.missing_fields:
                    final_answer = f"文档已生成，但仍有缺失字段: {', '.join(state.missing_fields)}"
                else:
                    final_answer = "文档已生成"

            return TaskResult(
                success=True,
                message="执行完成",
                answer=final_answer,
                structured_data=state.final_fill_data or state.structured_data or None,
                output_file_path=state.output_file_path,
                logs=logs,
                error=None,
            )

        except Exception as e:
            logs.append(f"executor error: {str(e)}")
            return TaskResult(
                success=False,
                message="执行失败",
                answer="",
                structured_data=state.structured_data or None,
                output_file_path=state.output_file_path,
                logs=logs,
                error=str(e),
            )

    def _execute_step(
        self,
        agent: Any,
        context: TaskContext,
        step: Any,
        state: ExecutionState,
        logs: list[str],
    ) -> Any:
        action = step.action

        if action == "analyze_template":
            return self._handle_analyze_template(agent, context, step, state, logs)

        if action == "read_document":
            return self._handle_read_document(context, step, state, logs)

        if action == "extract_fields":
            return self._handle_extract_fields(agent, context, step, state, logs)

        if action == "extract_for_template":
            return self._handle_extract_for_template(agent, context, step, state, logs)

        if action == "summarize_document":
            return self._handle_summarize_document(agent, context, step, state, logs)

        if action == "fill_template":
            return self._handle_fill_template(agent, context, step, state, logs)

        if action == "verify_document":
            return self._handle_verify_document(agent, context, step, state, logs)

        if action == "save_document":
            return self._handle_save_document(agent, context, step, state, logs)

        raise ValueError(f"未知 action: {action}")

    def _handle_read_document(self, context, step, state, logs):
        source_files = [f for f in context.files if f.role == "source"]
        reference_files = [f for f in context.files if f.role == "reference"]

        if not source_files:
            raise ValueError("没有 source 文件可读取")

        source_file_texts = {}
        for f in source_files:
            source_file_texts[f.file_name] = f.full_text or ""

        reference_file_texts = {}
        for f in reference_files:
            reference_file_texts[f.file_name] = f.full_text or ""

        state.source_file_texts = source_file_texts
        state.reference_file_texts = reference_file_texts

        combined_source_text = "\n\n".join(
            f"===== SOURCE FILE: {file_name} =====\n{text}"
            for file_name, text in source_file_texts.items()
        )

        if reference_file_texts:
            combined_reference_text = "\n\n".join(
                f"===== REFERENCE FILE: {file_name} =====\n{text}"
                for file_name, text in reference_file_texts.items()
            )
            combined_source_text = combined_source_text + "\n\n" + combined_reference_text

        state.combined_source_text = combined_source_text
        logs.append(
            f"executor/read_document: 已读取 source={len(source_files)} 个, reference={len(reference_files)} 个"
        )
        return combined_source_text

    def _handle_extract_fields(self, agent, context, step, state, logs):
        if not state.combined_source_text:
            raise ValueError("extract_fields 前缺少 combined_source_text")

        requested_fields = agent._extract_requested_fields(context.user_prompt)
        if not requested_fields:
            requested_fields = agent._extract_template_placeholders(context)

        extracted = agent.llm.extract_fields(
            text=state.combined_source_text,
            fields=requested_fields,
            system_prompt=agent.EXTRACT_SYSTEM_PROMPT,
        )

        state.structured_data = extracted or {}
        logs.append(
            f"executor/extract_fields: 提取字段完成 -> {list(state.structured_data.keys())}"
        )
        return state.structured_data

    def _handle_summarize_document(self, agent, context, step, state, logs):
        if not state.combined_source_text:
            raise ValueError("summarize_document 前缺少 combined_source_text")

        summary = agent.llm.summarize(
            text=state.combined_source_text,
            system_prompt=agent.SUMMARIZE_SYSTEM_PROMPT,
            user_prompt=context.user_prompt,
        )

        state.summary_text = summary or ""
        logs.append("executor/summarize_document: 摘要生成完成")
        return state.summary_text

    def _handle_fill_template(self, agent, context, step, state, logs):
        data_to_fill = state.final_fill_data or state.structured_data
        if not data_to_fill:
            raise ValueError("fill_template 前缺少可填充数据")

        template_file = next((f for f in context.files if f.role == "template"), None)
        if not template_file:
            raise ValueError("没有 template 文件")

        output_path = agent.writer.fill_template(
            template_path=template_file.file_path,
            data=data_to_fill,
        )
        state.output_file_path = output_path
        logs.append(f"executor/fill_template: 模板填充完成 -> {output_path}")
        return output_path

    def _handle_verify_document(self, agent, context, step, state, logs):
        if not state.output_file_path:
            raise ValueError("verify_document 前缺少 output_file_path")

        expected_placeholders = state.template_placeholders or []
        filled_data = state.final_fill_data or state.structured_data or {}

        review_report = self.verifier.verify_filled_document(
            output_path=state.output_file_path,
            expected_placeholders=expected_placeholders,
            filled_data=filled_data,
        )

        state.verify_passed = review_report["verify_passed"]
        state.unreplaced_placeholders = review_report.get("unreplaced_placeholders", [])
        state.last_review_report = review_report

        # empty_fields 也并入 missing_fields
        empty_fields = review_report.get("empty_fields", [])
        if isinstance(empty_fields, list):
            state.missing_fields = self._merge_unique_lists(state.missing_fields, empty_fields)

        logs.append(f"executor/verify_document: review -> {review_report}")
        return review_report

    def _handle_save_document(self, agent, context, step, state, logs):
        if not state.output_file_path:
            raise ValueError("save_document 前缺少 output_file_path")

        logs.append(f"executor/save_document: 输出文件已保存 -> {state.output_file_path}")
        return state.output_file_path

    def _map_fields_to_template(self, data, context, agent):
        if not data:
            return {}

        placeholders = agent._extract_template_placeholders(context)
        if not placeholders:
            return data

        mapped = agent.llm.map_fields_to_placeholders(
            extracted_data=data,
            placeholders=placeholders,
            user_prompt=context.user_prompt,
        )

        if mapped:
            return mapped

        # fallback：保留你原来的规则匹配
        fallback_mapped = {}

        for ph in placeholders:
            if ph in data:
                fallback_mapped[ph] = data[ph]

        for key, value in data.items():
            for ph in placeholders:
                if ph in fallback_mapped:
                    continue
                if key in ph or ph in key:
                    fallback_mapped[ph] = value

        for ph in placeholders:
            if ph not in fallback_mapped:
                fallback_mapped[ph] = ""

        return fallback_mapped
    
    def _handle_analyze_template(self, agent, context, step, state, logs):
        placeholders = agent._extract_template_placeholders(context)
        state.template_placeholders = placeholders or []
        logs.append(f"executor/analyze_template: 占位符 -> {state.template_placeholders}")
        return state.template_placeholders
    
    def _handle_extract_for_template(self, agent, context, step, state, logs):
        if not state.combined_source_text:
            raise ValueError("extract_for_template 前缺少 combined_source_text")

        if not state.template_placeholders:
            raise ValueError("extract_for_template 前缺少 template_placeholders")

        result = agent.llm.extract_for_template(
            text=state.combined_source_text,
            placeholders=state.template_placeholders,
            user_prompt=context.user_prompt,
        )

        # 兼容两种返回：
        # 1. 直接 dict: {"姓名": "张三"}
        # 2. 包装 dict: {"filled_data": {...}, "missing_fields": [...]}
        if isinstance(result, dict) and "filled_data" in result:
            state.final_fill_data = result.get("filled_data") or {}
            missing_fields = result.get("missing_fields")
            state.missing_fields = missing_fields if isinstance(missing_fields, list) else []
        else:
            state.final_fill_data = result or {}
            state.missing_fields = [
                ph for ph in state.template_placeholders
                if not state.final_fill_data.get(ph)
            ]

        logs.append(
            f"executor/extract_for_template: 生成填充值完成 -> {list(state.final_fill_data.keys())}"
        )
        logs.append(
            f"executor/extract_for_template: 缺失字段 -> {state.missing_fields}"
        )
        return state.final_fill_data
    
    def _needs_repair(self, state: ExecutionState) -> bool:
        if state.verify_passed is True:
            return False

        if state.unreplaced_placeholders:
            return True

        if state.missing_fields:
            return True

        report = state.last_review_report or {}
        return bool(report.get("needs_repair"))
    
    def _attempt_repair(self, agent, context, state, logs):
        if state.repair_attempts >= 1:
            logs.append("executor/repair: 已达到最大修复次数")
            return False

        logs.append("executor/repair: 开始自动修复")
        state.repair_attempts += 1

        result = agent.llm.repair_fill_data(
            user_prompt=context.user_prompt,
            source_text=state.combined_source_text,
            placeholders=state.template_placeholders,
            current_fill_data=state.final_fill_data or state.structured_data,
            missing_fields=state.missing_fields,
            unreplaced_placeholders=state.unreplaced_placeholders,
        )

        if not isinstance(result, dict):
            logs.append("executor/repair: repair_fill_data 返回格式非法")
            return False

        repaired_fill_data = result.get("filled_data") or {}
        repaired_missing_fields = result.get("missing_fields") or []

        if not isinstance(repaired_fill_data, dict):
            repaired_fill_data = {}

        if not isinstance(repaired_missing_fields, list):
            repaired_missing_fields = []

        state.repaired_fill_data = repaired_fill_data
        state.final_fill_data = repaired_fill_data
        state.missing_fields = repaired_missing_fields

        logs.append(
            f"executor/repair: 修复完成 -> {list(state.final_fill_data.keys())}"
        )
        logs.append(
            f"executor/repair: 修复后缺失字段 -> {state.missing_fields}"
        )
        return True
    
    def _rerun_fill_and_verify(self, agent, context, state, logs):
        logs.append("executor/repair: 开始二次填充与校验")

        template_file = next((f for f in context.files if f.role == "template"), None)
        if not template_file:
            raise ValueError("repair 阶段没有 template 文件")

        output_path = agent.writer.fill_template(
            template_path=template_file.file_path,
            data=state.final_fill_data,
        )
        state.output_file_path = output_path
        logs.append(f"executor/repair: 二次填充完成 -> {output_path}")

        review_report = self.verifier.verify_filled_document(
            output_path=state.output_file_path,
            expected_placeholders=state.template_placeholders,
            filled_data=state.final_fill_data,
        )

        state.verify_passed = review_report["verify_passed"]
        state.unreplaced_placeholders = review_report.get("unreplaced_placeholders", [])
        state.last_review_report = review_report

        empty_fields = review_report.get("empty_fields", [])
        if isinstance(empty_fields, list):
            state.missing_fields = self._merge_unique_lists(state.missing_fields, empty_fields)

        logs.append(f"executor/repair: 二次校验结果 -> {review_report}")

    def _merge_unique_lists(self, a, b):
        result = []
        seen = set()

        for item in (a or []) + (b or []):
            if item not in seen:
                seen.add(item)
                result.append(item)

        return result