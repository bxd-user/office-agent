import os

from app.core.agent import OfficeAgent
from app.tools.tool_registry import build_default_registry
from app.workflows.engine.executor import WorkflowExecutor
from app.workflows.engine.planner import WorkflowPlanner
from app.workflows.engine.state import WorkflowState
from app.workflows.engine.steps import WorkflowPlan


class AutonomousAgentWorkflow:
    EXCEL_EXTS = {".xlsx", ".xlsm", ".xltx", ".xltm", ".csv", ".tsv"}
    WORD_EXTS = {".docx", ".docm", ".dotx", ".dotm"}

    def __init__(self):
        self.agent = OfficeAgent()
        self.registry = build_default_registry()
        self.planner = WorkflowPlanner(agent=self.agent, registry=self.registry)
        self.executor = WorkflowExecutor(registry=self.registry)

    def run(
        self,
        instruction: str,
        input_files: list[dict],
        output_dir: str,
        params: dict | None = None,
    ) -> dict:
        state = WorkflowState(
            instruction=instruction,
            input_files=input_files,
            output_dir=output_dir,
            params=params or {},
        )

        inventory = self._build_file_inventory(input_files)
        state.log(f"文件清单: {inventory}")
        state.log(f"可用工具: {self.registry.list_tools()}")

        self._prepare_excel_to_word_state(state, inventory)

        plan = self.planner.plan(instruction=instruction, file_inventory=inventory)
        self._normalize_plan(plan, inventory, state)

        execution_result = self.executor.execute(plan=plan, state=state)
        self._postprocess_state(state)

        output_path = state.get("output_path")
        output_file = os.path.basename(output_path) if output_path else None
        execution_observation = self._build_execution_observation(state)

        return {
            "logs": execution_result.get("logs", []),
            "plan": execution_result.get("plan", {}),
            "mapping": state.get("mapping", {}),
            "missing_fields": state.get("missing_fields", []),
            "confidence": state.get("confidence", "unknown"),
            "context": state.get("context", {}),
            "word_field_slots": state.get("word_field_slots", []),
            "read_summaries": state.get("read_summaries", []),
            "execution_observation": execution_observation,
            "output_path": output_path,
            "output_file": output_file,
            "download_file_name": output_file,
        }

    def _build_file_inventory(self, input_files: list[dict]) -> list[dict]:
        inventory = []
        for item in input_files:
            path = item.get("path")
            if not path:
                continue
            name = item.get("filename") or os.path.basename(path)
            ext = os.path.splitext(name)[1].lower()
            file_type = "unknown"
            if ext in self.EXCEL_EXTS:
                file_type = "excel"
            elif ext in self.WORD_EXTS:
                file_type = "word"
            inventory.append({"filename": name, "path": path, "ext": ext, "type": file_type})
        return inventory

    def _normalize_plan(self, plan: WorkflowPlan, inventory: list[dict], state: WorkflowState) -> None:
        has_excel = any(item.get("type") == "excel" for item in inventory)
        has_word = any(item.get("type") == "word" for item in inventory)
        force_excel_to_word = str(state.params.get("workflow_mode") or "").strip() == "excel_to_word"

        has_excel_read = any(step.tool == "excel" and step.action == "read" for step in plan.steps)
        has_word_read = any(step.tool == "word" and step.action == "read" for step in plan.steps)
        has_word_fill = any(step.tool == "word" and step.action == "fill_context" for step in plan.steps)

        if has_excel and not has_excel_read:
            plan.steps.insert(0, self._mk_step(tool="excel", action="read", reason="自动补齐 Excel 读取"))

        if has_word and not has_word_read:
            plan.steps.append(self._mk_step(tool="word", action="read", reason="自动补齐 Word 读取"))

        if (has_excel and has_word) and not has_word_fill:
            plan.steps.append(self._mk_step(tool="word", action="fill_context", reason="自动补齐 Word 写入"))

        if force_excel_to_word and has_excel and has_word:
            ordered_steps = []

            excel_read_step = next(
                (step for step in plan.steps if step.tool == "excel" and step.action == "read"),
                self._mk_step(tool="excel", action="read", reason="excel_to_word 强制读取 Excel"),
            )
            word_read_step = next(
                (step for step in plan.steps if step.tool == "word" and step.action == "read"),
                self._mk_step(tool="word", action="read", reason="excel_to_word 强制读取 Word"),
            )
            word_fill_step = next(
                (step for step in plan.steps if step.tool == "word" and step.action == "fill_context"),
                self._mk_step(tool="word", action="fill_context", reason="excel_to_word 强制填充 Word"),
            )

            ordered_steps.extend([excel_read_step, word_read_step, word_fill_step])

            seen = {(step.tool, step.action, step.name) for step in ordered_steps}
            for step in plan.steps:
                key = (step.tool, step.action, step.name)
                if key in seen:
                    continue
                ordered_steps.append(step)

            plan.steps = ordered_steps

        if len(plan.steps) > 12:
            plan.steps = plan.steps[:12]

    def _mk_step(self, tool: str, action: str, reason: str):
        from app.workflows.engine.steps import WorkflowStep

        return WorkflowStep(
            name=f"auto_{tool}_{action}",
            tool=tool,
            action=action,
            args={},
            condition=None,
            on_fail="continue",
        )

    def _prepare_excel_to_word_state(self, state: WorkflowState, inventory: list[dict]) -> None:
        has_excel = any(item.get("type") == "excel" for item in inventory)
        has_word = any(item.get("type") == "word" for item in inventory)

        if not (has_excel and has_word):
            return

        if not state.has("excel_payload"):
            excel_path = self._pick_path_by_type(inventory, "excel")
            if excel_path:
                excel_tool = self.registry.get_tool("excel")
                if excel_tool is not None:
                    excel_result = excel_tool.execute_llm_instruction({"action": "read", "path": excel_path})
                    state.set("excel_payload", excel_result.get("data", {}))
                    state.log("预处理：已读取 Excel 结构化数据")

        if not state.has("word_payload"):
            word_path = self._pick_path_by_type(inventory, "word")
            if word_path:
                word_tool = self.registry.get_tool("word")
                if word_tool is not None:
                    word_result = word_tool.execute_llm_instruction({"action": "read", "path": word_path})
                    word_payload = word_result.get("data", {})
                    state.set("word_payload", word_payload)
                    if isinstance(word_payload, dict):
                        state.set("word_field_slots", word_payload.get("field_slots", []))
                    state.log("预处理：已读取 Word 结构化数据")

        if state.has("excel_payload") and state.has("word_payload"):
            self._postprocess_state(state)

    def _pick_path_by_type(self, inventory: list[dict], file_type: str) -> str | None:
        for item in inventory:
            if item.get("type") != file_type:
                continue
            path = item.get("path")
            if path:
                return path
        return None

    def _postprocess_state(self, state: WorkflowState) -> None:
        excel_payload = state.get("excel_payload", {})
        word_payload = state.get("word_payload", {})

        if not state.has("excel_fields"):
            fields = self._extract_excel_fields(excel_payload)
            state.set("excel_fields", fields)

        if not state.has("word_fields"):
            state.set("word_fields", self._extract_word_fields(word_payload))

        if not state.has("word_field_slots"):
            if isinstance(word_payload, dict):
                state.set("word_field_slots", word_payload.get("field_slots", []))

        if not state.has("mapping"):
            self._build_mapping_with_agent(state)

        if not state.has("context"):
            self._build_context(state)

    def _extract_excel_fields(self, excel_payload: dict) -> list[str]:
        sheets = excel_payload.get("sheets", []) if isinstance(excel_payload, dict) else []
        fields = []
        seen = set()
        for sheet in sheets:
            rows = sheet.get("rows", []) if isinstance(sheet, dict) else []
            if not rows:
                continue
            header = rows[0] if isinstance(rows[0], list) else []
            for item in header:
                name = str(item or "").strip()
                normalized = "".join(name.split()).lower()
                if not name or normalized in seen:
                    continue
                seen.add(normalized)
                fields.append(name)
        return fields

    def _extract_word_fields(self, word_payload: dict) -> list[str]:
        if not isinstance(word_payload, dict):
            return []

        slots = word_payload.get("field_slots", [])
        fields = []
        seen = set()

        if isinstance(slots, list):
            sorted_slots = sorted(
                [slot for slot in slots if isinstance(slot, dict)],
                key=lambda item: float(item.get("confidence", 0.0)),
                reverse=True,
            )
            for slot in sorted_slots:
                field_name = str(slot.get("field_name") or "").strip()
                normalized = "".join(field_name.split()).lower()
                if not field_name or normalized in seen:
                    continue
                seen.add(normalized)
                fields.append(field_name)

        if fields:
            return fields

        raw_fields = word_payload.get("fields", [])
        return [str(item).strip() for item in raw_fields if str(item).strip()]

    def _build_mapping_with_agent(self, state: WorkflowState) -> None:
        excel_fields = state.get("excel_fields", [])
        word_fields = state.get("word_fields", [])
        if not excel_fields or not word_fields:
            state.set("mapping", {})
            state.set("missing_fields", [])
            state.set("confidence", "unknown")
            return

        excel_preview = self._build_excel_preview(state.get("excel_payload", {}))
        word_field_slots = state.get("word_field_slots", [])

        result = self.agent.plan_excel_to_word(
            instruction=state.instruction,
            excel_fields=excel_fields,
            word_fields=word_fields,
            excel_preview=excel_preview,
            word_field_slots=word_field_slots,
        )

        state.set("mapping", result.get("mapping", {}))
        state.set("missing_fields", result.get("missing_fields", []))
        state.set("confidence", result.get("confidence", "unknown"))
        state.log(f"自动生成映射: {state.get('mapping', {})}")

    def _build_excel_preview(self, excel_payload: dict) -> dict:
        sheets = excel_payload.get("sheets", []) if isinstance(excel_payload, dict) else []
        preview_sheets = []
        for sheet in sheets[:3]:
            rows = sheet.get("rows", []) if isinstance(sheet, dict) else []
            preview_sheets.append(
                {
                    "name": sheet.get("name", "Sheet"),
                    "header": rows[0] if rows else [],
                    "sample_rows": rows[1:4] if len(rows) > 1 else [],
                }
            )
        return {"sheets": preview_sheets}

    def _build_context(self, state: WorkflowState) -> None:
        mapping = state.get("mapping", {})
        excel_payload = state.get("excel_payload", {})
        first_row = self._extract_first_row(excel_payload)

        context = {}
        for word_field, excel_field in mapping.items():
            context[word_field] = first_row.get(excel_field, "")

        state.set("context", context)

    def _extract_first_row(self, excel_payload: dict) -> dict:
        sheets = excel_payload.get("sheets", []) if isinstance(excel_payload, dict) else []
        for sheet in sheets:
            rows = sheet.get("rows", []) if isinstance(sheet, dict) else []
            if len(rows) < 2:
                continue
            header = rows[0] if isinstance(rows[0], list) else []
            for row in rows[1:]:
                if not isinstance(row, list):
                    continue
                if not any(str(cell or "").strip() for cell in row):
                    continue
                return {
                    str(header[idx] or "").strip(): "" if idx >= len(row) or row[idx] is None else str(row[idx])
                    for idx in range(len(header))
                    if str(header[idx] or "").strip()
                }
        return {}

    def _build_execution_observation(self, state: WorkflowState) -> list[str]:
        lines: list[str] = []
        summaries = state.get("read_summaries", [])

        if isinstance(summaries, list) and summaries:
            for item in summaries:
                if not isinstance(item, dict):
                    continue
                tool = str(item.get("tool") or "")
                source_file = str(item.get("source_file") or "未知文件")

                if tool == "excel":
                    sheet_count = int(item.get("sheet_count") or 0)
                    header = item.get("header", []) if isinstance(item.get("header", []), list) else []
                    sample_rows = item.get("sample_rows", []) if isinstance(item.get("sample_rows", []), list) else []
                    header_preview = "、".join(str(x) for x in header[:8] if str(x).strip()) or "无"
                    lines.append(f"已读取 Excel 文件《{source_file}》，识别到 {sheet_count} 个工作表。")
                    lines.append(f"首个表头字段：{header_preview}。")
                    if sample_rows:
                        lines.append(f"首个工作表样例数据行数：{len(sample_rows)}。")
                    continue

                if tool == "word":
                    field_count = int(item.get("field_count") or 0)
                    fields_preview = item.get("fields_preview", []) if isinstance(item.get("fields_preview", []), list) else []
                    field_preview_text = "、".join(str(x) for x in fields_preview[:8] if str(x).strip()) or "无"
                    lines.append(f"已读取 Word 文件《{source_file}》，识别到 {field_count} 个字段槽位。")
                    lines.append(f"字段示例：{field_preview_text}。")
                    continue

                lines.append(f"已读取文件《{source_file}》。")

        if not lines:
            lines.append("本次执行没有提取到可展示的读取摘要。")

        output_path = state.get("output_path")
        if output_path:
            lines.append(f"本次执行已生成输出文件：{os.path.basename(output_path)}。")
        else:
            lines.append("本次执行以读取/分析为主，未生成新文件。")

        return lines
