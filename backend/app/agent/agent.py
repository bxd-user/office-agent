# app/agent/agent.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agent.execution_state import ExecutionState
from app.agent.executor import StepExecutor
from app.agent.planner import WorkflowPlanner, PlannerContext
from app.tools.basic_tools import (
    LLMExtractFieldsTool,
    LLMExtractForTemplateTool,
    LLMSummarizeTool,
    VerifyDocumentTool,
    WordExtractPlaceholdersTool,
    WordFillTemplateTool,
    WordReadTextTool,
)
from app.tools.registry import ToolRegistry


@dataclass
class AgentFile:
    file_id: str
    filename: str
    path: str
    file_type: str
    extension: str
    role: Optional[str] = None


class WorkflowAgent:
    def __init__(
        self,
        llm: Any = None,
        reader: Any = None,
        writer: Any = None,
        verifier: Any = None,
    ) -> None:
        self.llm = llm
        self.reader = reader
        self.writer = writer
        self.verifier = verifier

        self.planner = WorkflowPlanner(llm_client=self.llm) if self.llm else None
        self.registry = ToolRegistry()
        self.executor = StepExecutor(registry=self.registry)

        self.files: List[AgentFile] = []

        if self.llm and self.reader and self.writer and self.verifier:
            self._register_tools()

    def _register_tools(self) -> None:
        self.registry.register(WordReadTextTool(self))
        self.registry.register(WordExtractPlaceholdersTool(self))
        self.registry.register(LLMExtractForTemplateTool(self))
        self.registry.register(LLMSummarizeTool(self))
        self.registry.register(LLMExtractFieldsTool(self))
        self.registry.register(WordFillTemplateTool(self))
        self.registry.register(VerifyDocumentTool(self))

    # =========================
    # 标准 planner -> executor 模式
    # =========================
    def run(self, user_prompt: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.planner is None:
            raise RuntimeError("WorkflowAgent 未完成初始化：缺少 planner")
        if self.executor is None:
            raise RuntimeError("WorkflowAgent 未完成初始化：缺少 executor")

        self.files = [self._build_agent_file(i, item) for i, item in enumerate(files)]
        self._infer_roles()

        planner_context = PlannerContext(
            user_prompt=user_prompt,
            files=[self._file_to_prompt_dict(f) for f in self.files],
            available_tools=self.registry.describe_tools(),
        )

        plan = self.planner.create_plan(planner_context)

        initial_state = {
            "user_prompt": user_prompt,
            "files": [self._file_to_prompt_dict(f) for f in self.files],
        }

        state = self.executor.execute(plan=plan, initial_state=initial_state)
        final_answer = self._build_final_answer(state.values, state.step_results)

        return {
            "mode": "plan_execute",
            "plan": plan.model_dump(),
            "state": state.values,
            "step_results": state.step_results,
            "final_answer": final_answer,
        }

    # =========================
    # ReAct 模式：LLM 每次决定一步
    # =========================
    def run_react(self, user_prompt: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.llm is None:
            raise RuntimeError("WorkflowAgent 未完成初始化：缺少 llm")
        if self.executor is None:
            raise RuntimeError("WorkflowAgent 未完成初始化：缺少 executor")

        self.files = [self._build_agent_file(i, item) for i, item in enumerate(files)]
        self._infer_roles()

        state: Dict[str, Any] = {
            "user_prompt": user_prompt,
            "files": [self._file_to_prompt_dict(f) for f in self.files],
        }
        history: List[Dict[str, Any]] = []
        available_tools = self.registry.describe_tools()

        max_steps = 10

        for idx in range(max_steps):
            summarized_state = self._summarize_state_for_llm(state)
            summarized_history = self._summarize_history_for_llm(history, limit=5)

            decision = self.llm.decide_next_step(
                user_prompt=user_prompt,
                files=state["files"],
                available_tools=available_tools,
                state=summarized_state,
                history=summarized_history,
            )

            if not isinstance(decision, dict):
                return {
                    "mode": "react",
                    "final_answer": "LLM 决策结果不是合法对象",
                    "state": state,
                    "history": history,
                }

            decision_type = decision.get("type")

            if decision_type == "final":
                final_answer = decision.get("final_answer") or self._build_final_answer(state, history)
                return {
                    "mode": "react",
                    "final_answer": final_answer,
                    "state": state,
                    "history": history,
                }

            if decision_type != "tool_call":
                history.append(
                    {
                        "step": idx + 1,
                        "type": "invalid_decision",
                        "decision": decision,
                    }
                )
                return {
                    "mode": "react",
                    "final_answer": "决策格式错误",
                    "state": state,
                    "history": history,
                }

            tool_name = decision.get("tool_name")
            args = decision.get("args", {})
            output_key = decision.get("output_key") or f"step_{idx + 1}"
            reason = decision.get("reason", "")

            if not isinstance(tool_name, str) or not tool_name.strip():
                error_result = {"error": f"工具名无效: {tool_name}"}
                state[output_key] = error_result
                history.append(
                    {
                        "step": idx + 1,
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "args": args,
                        "resolved_args": None,
                        "output_key": output_key,
                        "result": error_result,
                        "reason": reason,
                    }
                )
                continue

            try:
                tool = self.registry.get(tool_name)
            except Exception as e:
                error_result = {"error": f"未知工具: {tool_name}, detail={str(e)}"}
                state[output_key] = error_result
                history.append(
                    {
                        "step": idx + 1,
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "args": args,
                        "resolved_args": None,
                        "output_key": output_key,
                        "result": error_result,
                        "reason": reason,
                    }
                )
                continue

            try:
                resolve_state = ExecutionState(values=state)
                resolved_args = self.executor._resolve_value(args, resolve_state)
            except Exception as e:
                error_result = {"error": f"参数解析失败: {str(e)}"}
                state[output_key] = error_result
                history.append(
                    {
                        "step": idx + 1,
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "args": args,
                        "resolved_args": None,
                        "output_key": output_key,
                        "result": error_result,
                        "reason": reason,
                    }
                )
                continue

            try:
                result = tool.run(**resolved_args)
            except Exception as e:
                result = {"error": f"工具执行失败: {str(e)}"}

            state[output_key] = result
            history.append(
                {
                    "step": idx + 1,
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "args": args,
                    "resolved_args": resolved_args,
                    "output_key": output_key,
                    "result": result,
                    "reason": reason,
                }
            )

        return {
            "mode": "react",
            "final_answer": self._build_final_answer(state, history) or "达到最大步数，任务中止",
            "state": state,
            "history": history,
        }

    # =========================
    # 基础文件与角色
    # =========================
    def _build_agent_file(self, idx: int, item: Dict[str, Any]) -> AgentFile:
        path = item["path"]
        filename = item.get("filename") or Path(path).name
        extension = Path(path).suffix.lower()

        if extension == ".docx":
            file_type = "word"
        elif extension in {".xlsx", ".xls"}:
            file_type = "excel"
        else:
            file_type = "unknown"

        return AgentFile(
            file_id=str(idx),
            filename=filename,
            path=path,
            file_type=file_type,
            extension=extension,
            role=item.get("role"),
        )

    def _infer_roles(self) -> None:
        if len(self.files) == 1:
            if self.files[0].role is None:
                self.files[0].role = "source"
            return

        for f in self.files:
            if f.role:
                continue

            lower_name = f.filename.lower()
            if "模板" in f.filename or "空表" in f.filename or "template" in lower_name:
                f.role = "template"
            else:
                f.role = "source"

    def get_file_by_role(self, role: str) -> AgentFile:
        for f in self.files:
            if f.role == role:
                return f
        raise ValueError(f"No file found for role: {role}")

    def _file_to_prompt_dict(self, f: AgentFile) -> Dict[str, Any]:
        return {
            "file_id": f.file_id,
            "filename": f.filename,
            "path": f.path,
            "file_type": f.file_type,
            "extension": f.extension,
            "role": f.role,
        }

    # =========================
    # 文档辅助能力
    # =========================
    def extract_template_placeholders(self, path: str) -> List[str]:
        """
        修正为适配你当前 reader.py 的 read(path) -> ParsedDocument
        """
        parsed = self.reader.read(path)
        text = parsed.full_text or ""

        found = re.findall(r"\{\{(.*?)\}\}", text)
        cleaned: List[str] = []
        seen = set()

        for item in found:
            value = item.strip()
            if value and value not in seen:
                cleaned.append(value)
                seen.add(value)

        return cleaned

    # =========================
    # 给 LLM 的上下文压缩
    # =========================
    def _summarize_state_for_llm(self, state: Dict[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}

        for k, v in state.items():
            if k in {"user_prompt", "files"}:
                summary[k] = v
                continue

            summary[k] = self._compact_value(v)

        return summary

    def _summarize_history_for_llm(self, history: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        compacted: List[Dict[str, Any]] = []

        for item in history[-limit:]:
            compacted.append(
                {
                    "step": item.get("step"),
                    "type": item.get("type"),
                    "tool_name": item.get("tool_name"),
                    "output_key": item.get("output_key"),
                    "reason": item.get("reason"),
                    "result": self._compact_value(item.get("result")),
                }
            )

        return compacted

    def _compact_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            compact: Dict[str, Any] = {}

            if "error" in value:
                compact["error"] = value["error"]

            if "summary" in value and isinstance(value["summary"], str):
                compact["summary"] = value["summary"][:800]

            if "text" in value and isinstance(value["text"], str):
                compact["text_preview"] = value["text"][:800]
                compact["text_length"] = len(value["text"])

            if "placeholders" in value and isinstance(value["placeholders"], list):
                compact["placeholders"] = value["placeholders"][:50]

            if "filled_data" in value and isinstance(value["filled_data"], dict):
                compact["filled_data"] = {
                    k: (str(v)[:120] if v is not None else "")
                    for k, v in list(value["filled_data"].items())[:30]
                }

            if "missing_fields" in value and isinstance(value["missing_fields"], list):
                compact["missing_fields"] = value["missing_fields"][:50]

            if "output_path" in value:
                compact["output_path"] = value["output_path"]

            if "file_path" in value:
                compact["file_path"] = value["file_path"]

            # 如果上面一个字段都没命中，递归压缩前几个键
            if not compact:
                for idx, (k, v) in enumerate(value.items()):
                    if idx >= 8:
                        compact["__truncated__"] = True
                        break
                    compact[k] = self._compact_value(v)

            return compact

        if isinstance(value, list):
            compact_list = [self._compact_value(v) for v in value[:8]]
            if len(value) > 8:
                compact_list.append({"__truncated__": True, "size": len(value)})
            return compact_list

        if isinstance(value, str):
            return value[:300]

        return value

    # =========================
    # 最终答案组装
    # =========================
    def _build_final_answer(self, state: Dict[str, Any], records: List[Dict[str, Any]]) -> str:
        # 1. 常见摘要输出
        for key in ["summary", "summary_result"]:
            value = state.get(key)
            if isinstance(value, dict):
                summary = value.get("summary")
                if isinstance(summary, str) and summary.strip():
                    return summary.strip()

        # 2. 模板填充输出
        for key in ["filled_doc", "filled_doc_result", "output_file"]:
            value = state.get(key)
            if isinstance(value, dict):
                output_path = value.get("output_path")
                if isinstance(output_path, str) and output_path.strip():
                    return f"已完成，输出文件: {output_path}"

        # 3. 从记录倒序兜底
        for record in reversed(records):
            result = record.get("result")
            if isinstance(result, dict):
                summary = result.get("summary")
                if isinstance(summary, str) and summary.strip():
                    return summary.strip()

                output_path = result.get("output_path")
                if isinstance(output_path, str) and output_path.strip():
                    return f"已完成，输出文件: {output_path}"

        return "任务执行完成"