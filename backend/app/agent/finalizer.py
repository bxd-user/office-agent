from __future__ import annotations

from typing import Any, Dict


class Finalizer:
    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def finalize_run(
        self,
        *,
        success: bool,
        session,
        memory,
        plan,
        observations: list[dict[str, Any]],
        context: dict[str, Any],
        trace: list[dict[str, Any]],
        summary: dict[str, Any],
        replan_count: int,
    ) -> dict[str, Any]:
        memory_snapshot = memory.snapshot() if hasattr(memory, "snapshot") else {}
        lifecycle = {
            "stage_flow": ["input", "plan", "execute", "verify", "replan_if_needed", "output"],
            "replan_count": replan_count,
        }

        text_result = self._build_text_result(success=success, summary=summary)
        file_result = self._build_file_result(memory_snapshot=memory_snapshot, context=context)
        structured_result = self._build_structured_result(
            success=success,
            summary=summary,
            plan=plan,
            observations=observations,
            context=context,
        )
        logs = self._build_logs(trace=trace, observations=observations, lifecycle=lifecycle)

        return {
            "success": success,
            "session": {
                "task_id": getattr(session, "task_id", ""),
                "user_prompt": getattr(session, "user_prompt", ""),
            },
            "plan": plan.model_dump() if hasattr(plan, "model_dump") else self._serialize_plan(plan),
            "observations": observations,
            "context": context,
            "trace": trace,
            "summary": summary,
            "memory": memory_snapshot,
            "lifecycle": lifecycle,

            "text_result": text_result,
            "file_result": file_result,
            "structured_result": structured_result,
            "logs": logs,
            "final_output": {
                "text": text_result,
                "files": file_result,
                "structured": structured_result,
                "logs": logs,
            },
        }

    def build_final_answer(self, context) -> str:
        if self.llm_client and hasattr(self.llm_client, "finalize_response"):
            answer = self.llm_client.finalize_response(
                user_prompt=context.user_prompt,
                plan=self._serialize_plan(context.plan),
                memory_snapshot=context.memory.snapshot(),
                step_records=[self._serialize_record(r) for r in context.step_records],
            )
            if answer:
                return answer

        if context.memory.output_files:
            return "任务已完成，并已生成输出文件。"
        return "任务已执行完成。"

    def _serialize_plan(self, plan):
        if plan is None:
            return None
        return {
            "goal": plan.goal,
            "task_type": plan.task_type,
            "file_roles": [vars(fr) for fr in plan.file_roles],
            "steps": [vars(s) for s in plan.steps],
            "success_criteria": plan.success_criteria,
        }

    def _serialize_record(self, record):
        return {
            "step_id": record.step_id,
            "tool_calls": record.tool_calls,
            "outputs": record.outputs,
            "success": record.success,
            "error": record.error,
            "verifier_result": record.verifier_result,
        }

    @staticmethod
    def _build_text_result(success: bool, summary: dict[str, Any]) -> str:
        summary_text = str(summary.get("summary") or "").strip() if isinstance(summary, dict) else ""
        if summary_text:
            return summary_text
        return "任务执行完成。" if success else "任务执行失败。"

    @staticmethod
    def _build_file_result(memory_snapshot: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        seen_paths: set[str] = set()

        output_files = memory_snapshot.get("output_files", []) if isinstance(memory_snapshot, dict) else []
        if isinstance(output_files, list):
            for item in output_files:
                if isinstance(item, dict):
                    path = str(item.get("path") or "")
                    if path and path not in seen_paths:
                        files.append(item)
                        seen_paths.add(path)

        state = context.get("state", {}) if isinstance(context, dict) else {}
        refs = state.get("intermediate_refs", {}) if isinstance(state, dict) else {}
        output_paths = refs.get("output_file_paths", []) if isinstance(refs, dict) else []
        if isinstance(output_paths, list):
            for path in output_paths:
                if isinstance(path, str) and path and path not in seen_paths:
                    files.append({"path": path})
                    seen_paths.add(path)

        return files

    @staticmethod
    def _build_structured_result(
        success: bool,
        summary: dict[str, Any],
        plan,
        observations: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        checks = summary.get("checks", {}) if isinstance(summary, dict) else {}
        return {
            "success": success,
            "checks": checks,
            "issues": summary.get("issues", []) if isinstance(summary, dict) else [],
            "goal": getattr(plan, "goal", ""),
            "step_count": len(getattr(plan, "steps", []) or []),
            "observation_count": len(observations),
            "context_state": (context.get("state", {}) if isinstance(context, dict) else {}),
        }

    @staticmethod
    def _build_logs(
        trace: list[dict[str, Any]],
        observations: list[dict[str, Any]],
        lifecycle: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "trace": trace,
            "observation_logs": observations,
            "lifecycle": lifecycle,
        }