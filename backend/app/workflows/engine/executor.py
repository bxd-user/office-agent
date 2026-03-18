from __future__ import annotations

from dataclasses import asdict
import os
from typing import Any

from app.tools.tool_registry import ToolRegistry
from app.workflows.engine.state import WorkflowState
from app.workflows.engine.steps import WorkflowPlan, WorkflowStep
from app.workflows.engine.scheduler import StepScheduler


class WorkflowExecutor:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.scheduler = StepScheduler()

    def execute(self, plan: WorkflowPlan, state: WorkflowState) -> dict[str, Any]:
        state.log(f"执行目标: {plan.goal}")
        state.set("plan", {"goal": plan.goal, "steps": [asdict(step) for step in plan.steps]})

        for index, step in enumerate(plan.steps, start=1):
            if not self.scheduler.should_run(step, state):
                state.log(f"跳过步骤{index}: {step.name} (condition={step.condition})")
                continue

            try:
                self._run_step(index, step, state)
            except Exception as exc:
                state.log(f"步骤{index}失败: {step.name} error={exc}")
                if step.on_fail == "break":
                    break

        return {
            "plan": state.get("plan", {}),
            "logs": state.logs,
            "data": state.data,
        }

    def _run_step(self, index: int, step: WorkflowStep, state: WorkflowState) -> None:
        tool = self.registry.get_tool(step.tool)
        if tool is None:
            raise ValueError(f"未找到工具: {step.tool}")

        normalized_action = str(step.action or "").strip().lower()
        instruction = self._build_instruction(step, state)
        state.log(f"步骤{index}: {step.name} -> {instruction}")

        result = tool.execute_llm_instruction(instruction)
        state.set(f"step_result::{step.name}", result)

        if normalized_action.startswith("read"):
            summary = self._build_read_summary(step=step, instruction=instruction, result=result)
            if summary:
                existing = state.get("read_summaries", [])
                if not isinstance(existing, list):
                    existing = []
                existing.append(summary)
                state.set("read_summaries", existing)
                state.log(f"读取摘要: {summary}")

        self._merge_result(step, result, state)

    def _build_instruction(self, step: WorkflowStep, state: WorkflowState) -> dict[str, Any]:
        instruction: dict[str, Any] = {
            "action": step.action,
        }

        args = dict(step.args)
        source_path = args.get("source_path")
        if not source_path:
            source_path = self._resolve_source_path(step.tool, state)
            if source_path:
                args["path"] = args.get("path") or source_path
                args["source_path"] = source_path

        output_path = args.get("output_path")
        if not output_path and step.action in {"write", "fill_context"}:
            output_name = str(args.get("output_name") or state.params.get("output_name") or "result.docx")
            output_path = state.output_dir + "/" + output_name
            args["output_path"] = output_path

        if step.action == "fill_context":
            if "template_path" not in args and source_path:
                args["template_path"] = source_path
            if "context" not in args:
                args["context"] = state.get("context", {})

        if step.action == "write" and "data" not in args:
            if step.tool == "excel":
                args["data"] = state.get("excel_payload", {})
            if step.tool == "word":
                args["data"] = state.get("word_payload", {})

        instruction.update(args)
        return instruction

    def _resolve_source_path(self, tool_name: str, state: WorkflowState) -> str | None:
        for item in state.input_files:
            path = item.get("path")
            if not path:
                continue
            tool = self.registry.get_tool_for_path(path)
            if tool and tool.TOOL_NAME == tool_name:
                return path
        return None

    def _merge_result(self, step: WorkflowStep, result: dict[str, Any], state: WorkflowState) -> None:
        action = str(step.action or "").strip().lower()

        if action == "read":
            payload = result.get("data", {})
            if step.tool == "excel":
                state.set("excel_payload", payload)
            elif step.tool == "word":
                state.set("word_payload", payload)
                if isinstance(payload, dict):
                    state.set("word_field_slots", payload.get("field_slots", []))

        if action == "extract_fields":
            fields = result.get("fields", [])
            if step.tool == "excel":
                state.set("excel_fields", fields)
            elif step.tool == "word":
                state.set("word_fields", fields)
                state.set("word_field_slots", result.get("field_slots", []))

        if action in {"write", "fill_context"}:
            output_path = result.get("output_path")
            if output_path:
                state.set("output_path", output_path)

    def _build_read_summary(self, step: WorkflowStep, instruction: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        data = result.get("data", {}) if isinstance(result.get("data"), dict) else {}
        row_data = result.get("row", {}) if isinstance(result.get("row"), dict) else {}
        source_path = str(instruction.get("path") or instruction.get("source_path") or "")

        summary: dict[str, Any] = {
            "tool": step.tool,
            "action": step.action,
            "source_path": source_path,
            "source_file": os.path.basename(source_path) if source_path else None,
        }

        if step.tool == "excel":
            if row_data:
                summary.update(
                    {
                        "read_mode": "first_row",
                        "field_count": len(row_data),
                        "row_preview": dict(list(row_data.items())[:20]),
                    }
                )
                return summary

            sheets = data.get("sheets", []) if isinstance(data.get("sheets", []), list) else []
            first_sheet = sheets[0] if sheets and isinstance(sheets[0], dict) else {}
            rows = first_sheet.get("rows", []) if isinstance(first_sheet.get("rows", []), list) else []
            header = rows[0] if rows and isinstance(rows[0], list) else []
            sample_rows = rows[1:3] if len(rows) > 1 else []

            summary.update(
                {
                    "file_type": data.get("file_type"),
                    "sheet_count": len(sheets),
                    "sheet_names": [str(item.get("name") or "") for item in sheets[:5] if isinstance(item, dict)],
                    "header": header,
                    "sample_rows": sample_rows,
                }
            )
            return summary

        if step.tool == "word":
            if row_data:
                summary.update(
                    {
                        "read_mode": "row",
                        "row_preview": dict(list(row_data.items())[:20]),
                    }
                )
                return summary

            fields = data.get("fields", []) if isinstance(data.get("fields", []), list) else []
            stats = data.get("stats", {}) if isinstance(data.get("stats", {}), dict) else {}
            summary.update(
                {
                    "file_type": data.get("file_type"),
                    "field_count": len(fields),
                    "fields_preview": fields[:20],
                    "stats": stats,
                }
            )
            return summary

        summary.update(
            {
                "file_type": data.get("file_type"),
                "top_level_keys": list(data.keys())[:20],
            }
        )
        return summary
