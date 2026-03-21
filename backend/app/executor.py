import json
from pathlib import Path
from uuid import uuid4

from app.execution_state import ExecutionState
from app.models import TaskContext, TaskResult
from app.utils.docx_verify import count_unreplaced_placeholders
from app.utils.json_utils import extract_json_object


class StepExecutor:
    def run(self, agent, context: TaskContext, task_type: str, steps: list[str], logs: list[str]) -> TaskResult:
        state = ExecutionState(task_type=task_type)

        try:
            for step in steps:
                logs.append(f"executor: 开始步骤 -> {step}")

                if step == "collect_source_text":
                    self._step_collect_source_text(context, state, logs)

                elif step == "extract_fields":
                    self._step_extract(agent, context, state, logs)

                elif step == "write_docx":
                    self._step_write_docx(agent, context, state, logs)

                elif step == "summarize_document":
                    self._step_summarize_document(agent, context, state, logs)

                elif step == "summarize_result":
                    self._step_summarize_result(agent, context, state, logs)

                else:
                    return TaskResult(
                        success=False,
                        message="执行失败",
                        answer="",
                        logs=logs,
                        error=f"unknown step: {step}",
                    )

                logs.append(f"executor: 完成步骤 -> {step}")

            return TaskResult(
                success=True,
                message="执行成功" if task_type != "fill" else "填充成功",
                answer=state.answer,
                logs=logs,
                error=None,
                structured_data=state.structured_data,
                output_file_path=state.output_file_path,
            )

        except Exception as e:
            logs.append(f"executor error: {str(e)}")
            return TaskResult(
                success=False,
                message="执行失败",
                answer=state.answer,
                logs=logs,
                error=str(e),
                structured_data=state.structured_data,
                output_file_path=state.output_file_path,
            )

    def _step_collect_source_text(self, context: TaskContext, state: ExecutionState, logs: list[str]) -> None:
        source_files = [f for f in context.files if f.role == "source"]

        if not source_files:
            source_files = context.files

        parts = []
        for idx, file in enumerate(source_files, start=1):
            parts.append(f"===== 文件 {idx}: {file.file_name} =====\n{file.full_text}")

        state.collected_text = "\n\n".join(parts)
        logs.append(f"executor: 已收集 source 文件数量 -> {len(source_files)}")

    def _step_extract(self, agent, context: TaskContext, state: ExecutionState, logs: list[str]) -> None:
        text = state.collected_text or context.full_text

        fields = agent._extract_requested_fields(context.user_prompt)
        logs.append(f"executor: prompt 识别字段 -> {fields}")

        template_fields = agent._extract_template_placeholders(context)
        if template_fields:
            logs.append(f"executor: 模板占位符字段 -> {template_fields}")

        if not fields:
            fields = template_fields

        if not fields:
            fields = ["姓名", "年龄", "专业"]
            logs.append("executor: 未识别到字段且模板无占位符，使用默认字段")
        else:
            logs.append(f"executor: 最终目标字段 -> {fields}")

        empty_json_example = {field: "" for field in fields}

        user_prompt = (
            "请从下面内容中提取指定字段，并严格返回 JSON。\n\n"
            f"目标字段：{fields}\n\n"
            "要求：\n"
            "1. 只输出 JSON 对象\n"
            "2. key 必须与目标字段完全一致\n"
            "3. 找不到的字段值置为空字符串\n"
            "4. 不要添加额外说明\n\n"
            f"输出示例：\n{json.dumps(empty_json_example, ensure_ascii=False)}\n\n"
            f"文档内容：\n{text}"
        )

        raw_answer = agent.llm.generate(
            system_prompt=agent.EXTRACT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        structured_data = extract_json_object(raw_answer)
        state.structured_data = structured_data
        state.meta["target_fields"] = fields

        if structured_data is not None:
            state.answer = json.dumps(structured_data, ensure_ascii=False, indent=2)
            logs.append("executor: JSON 解析成功")
        else:
            state.answer = raw_answer
            logs.append("executor: JSON 解析失败")

    def _step_write_docx(self, agent, context: TaskContext, state: ExecutionState, logs: list[str]) -> None:
        if not state.structured_data:
            raise ValueError("write_docx 前没有可用的 structured_data")

        template_file = self._get_template_file(context)
        if not template_file:
            raise ValueError("未找到 template 文件，无法执行 write_docx")

        output_dir = Path("storage/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file_path = output_dir / f"{uuid4().hex}_filled_{template_file.file_name}"

        saved_file = agent.writer.replace_placeholders(
            template_path=template_file.file_path,
            output_path=str(output_file_path),
            data={k: str(v) for k, v in state.structured_data.items()},
        )

        remaining = count_unreplaced_placeholders(saved_file)
        logs.append(f"executor: 文档已生成 -> {saved_file}")
        logs.append(f"executor: 未替换占位符数量 -> {remaining}")

        state.output_file_path = saved_file
        state.meta["remaining_placeholders"] = remaining
        state.answer = f"已生成填充后的 Word 文档，剩余未替换占位符数量：{remaining}"

    def _step_summarize_document(self, agent, context: TaskContext, state: ExecutionState, logs: list[str]) -> None:
        text = state.collected_text or context.full_text

        user_prompt = (
            f"用户需求：{context.user_prompt}\n\n"
            f"文档内容：\n{text}"
        )

        answer = agent.llm.generate(
            system_prompt=agent.SUMMARIZE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        state.answer = answer

    def _step_summarize_result(self, agent, context: TaskContext, state: ExecutionState, logs: list[str]) -> None:
        user_prompt = (
            "请对本次文档工作流执行结果做简要总结。\n\n"
            f"用户需求：{context.user_prompt}\n\n"
            f"提取到的结构化数据：{state.structured_data or {}}\n\n"
            f"输出文件路径：{state.output_file_path or '未生成'}\n\n"
            f"剩余未替换占位符数量：{state.meta.get('remaining_placeholders', '未知')}\n\n"
            "请输出：\n"
            "1. 本次完成了什么\n"
            "2. 提取到了哪些关键字段\n"
            "3. 是否还有未替换占位符\n"
        )

        answer = agent.llm.generate(
            system_prompt=agent.SUMMARIZE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        state.answer = answer

    def _get_template_file(self, context: TaskContext):
        for file in context.files:
            if file.role == "template":
                return file
        return None