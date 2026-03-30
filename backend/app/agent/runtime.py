from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.agent.executor import Executor
from app.agent.finalizer import Finalizer
from app.agent.memory import WorkingMemory
from app.agent.planner_v2 import PlannerV2
from app.agent.replan import Replanner
from app.agent.session import AgentSession
from app.agent.verifier import Verifier
from app.core.config import settings
from app.core.logger import get_logger, log_event
from app.document.bootstrap import bootstrap_document_providers


class AgentRuntime:
    def __init__(
        self,
        file_resolver,
        max_replans: int | None = None,
        max_step_retries: int | None = None,
    ) -> None:
        bootstrap_document_providers()
        self.file_resolver = file_resolver
        self.max_replans = max(0, int(settings.AGENT_MAX_REPLANS if max_replans is None else max_replans))
        self.max_step_retries = max(
            0,
            int(settings.AGENT_MAX_STEP_RETRIES if max_step_retries is None else max_step_retries),
        )

        self.planner = PlannerV2()
        self.replanner = Replanner()
        self.verifier = Verifier()
        self.finalizer = Finalizer()
        self.logger = get_logger("app.agent.runtime")

    def run(
        self,
        user_request: str,
        files: list[dict[str, Any]],
        capabilities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_capabilities = capabilities or {}
        session = self._create_session(user_request=user_request, files=files)
        memory = self._init_memory(session=session)

        log_event(
            self.logger,
            "runtime.start",
            task_id=session.task_id,
            user_prompt=user_request,
            file_count=len(files),
            max_replans=self.max_replans,
            max_step_retries=self.max_step_retries,
        )

        plan = self.planner.build_plan(
            user_request=user_request,
            files=files,
            capabilities=resolved_capabilities,
        )

        log_event(
            self.logger,
            "runtime.plan.ready",
            task_id=session.task_id,
            step_count=len(plan.steps),
            steps=[step.action_type for step in plan.steps],
        )

        attempt = 0
        replan_count = 0
        last_observations: list[dict[str, Any]] = []
        last_context: dict[str, Any] = {}
        last_trace: list[dict[str, Any]] = []
        last_summary: dict[str, Any] = {
            "success": False,
            "summary": "执行未完成",
            "issues": ["runtime_not_executed"],
        }

        while True:
            executor = Executor(
                file_resolver=self.file_resolver,
                max_step_retries=self.max_step_retries,
            )
            observations = executor.execute_plan(plan)

            last_observations = [obs.model_dump() for obs in observations]
            last_context = executor.export_context()
            last_trace = executor.export_trace_dict()
            last_summary = self.verifier.summarize(
                observations=last_observations,
                context=last_context,
            )

            log_event(
                self.logger,
                "runtime.iteration.summary",
                task_id=session.task_id,
                attempt=attempt,
                replan_count=replan_count,
                success=last_summary.get("success", False),
                issues=last_summary.get("issues", []),
            )

            self._sync_memory(memory=memory, context=last_context, observations=last_observations)

            if self._is_verified(last_observations, last_summary):
                log_event(
                    self.logger,
                    "runtime.completed",
                    task_id=session.task_id,
                    success=True,
                    replan_count=replan_count,
                )
                return self.finalizer.finalize_run(
                    success=True,
                    session=session,
                    memory=memory,
                    plan=plan,
                    observations=last_observations,
                    context=last_context,
                    trace=last_trace,
                    summary=last_summary,
                    replan_count=replan_count,
                )

            can_replan = attempt < self.max_replans and self._should_replan(last_observations, last_context)
            if not can_replan:
                log_event(
                    self.logger,
                    "runtime.completed",
                    task_id=session.task_id,
                    success=False,
                    replan_count=replan_count,
                    reason="cannot_replan",
                    issues=last_summary.get("issues", []),
                )
                return self.finalizer.finalize_run(
                    success=False,
                    session=session,
                    memory=memory,
                    plan=plan,
                    observations=last_observations,
                    context=last_context,
                    trace=last_trace,
                    summary=last_summary,
                    replan_count=replan_count,
                )

            new_plan = self.replanner.rebuild_plan(
                user_request=user_request,
                files=files,
                old_plan=plan,
                execution_trace=last_trace,
            )
            if not new_plan.steps:
                log_event(
                    self.logger,
                    "runtime.completed",
                    task_id=session.task_id,
                    success=False,
                    replan_count=replan_count,
                    reason="replan_empty_steps",
                )
                return self.finalizer.finalize_run(
                    success=False,
                    session=session,
                    memory=memory,
                    plan=plan,
                    observations=last_observations,
                    context=last_context,
                    trace=last_trace,
                    summary={
                        "success": False,
                        "summary": "重规划未生成可执行步骤",
                        "issues": ["replan_empty_steps"],
                    },
                    replan_count=replan_count,
                )

            plan = new_plan
            attempt += 1
            replan_count += 1
            log_event(
                self.logger,
                "runtime.replanned",
                task_id=session.task_id,
                attempt=attempt,
                replan_count=replan_count,
                new_step_count=len(plan.steps),
            )

    @staticmethod
    def _create_session(user_request: str, files: list[dict[str, Any]]) -> AgentSession:
        return AgentSession(
            task_id=str(uuid4()),
            user_prompt=user_request,
            files=files,
        )

    @staticmethod
    def _init_memory(session: AgentSession) -> WorkingMemory:
        memory = WorkingMemory()
        memory.file_manifest = list(session.files)
        for file_info in session.files:
            file_id = str(file_info.get("file_id") or "")
            if file_id:
                memory.remember_file_role(file_id, "unknown")
        return memory

    @staticmethod
    def _is_verified(observations: list[dict[str, Any]], summary: dict[str, Any]) -> bool:
        has_failed_step = any(not obs.get("success", False) for obs in observations)
        summary_success = bool(summary.get("success", False)) if isinstance(summary, dict) else False
        return (not has_failed_step) and summary_success

    @staticmethod
    def _should_replan(observations: list[dict[str, Any]], context: dict[str, Any]) -> bool:
        state = context.get("state", {}) if isinstance(context, dict) else {}
        refs = state.get("intermediate_refs", {}) if isinstance(state, dict) else {}

        if refs.get("replan_required") is True:
            return True

        failed = [obs for obs in observations if not obs.get("success", False)]
        if not failed:
            return False

        failure_reasons = {str(obs.get("failure_reason") or "").lower() for obs in failed}
        if "non_recoverable" in failure_reasons:
            return False
        if "replannable" in failure_reasons:
            return True

        return False

    @staticmethod
    def _sync_memory(
        memory: WorkingMemory,
        context: dict[str, Any],
        observations: list[dict[str, Any]],
    ) -> None:
        state = context.get("state", {}) if isinstance(context, dict) else {}
        refs = state.get("intermediate_refs", {}) if isinstance(state, dict) else {}

        read_documents = refs.get("read_documents", {})
        if isinstance(read_documents, dict):
            for key, value in read_documents.items():
                if isinstance(value, dict):
                    text_candidate = value.get("text") or value.get("content")
                    if isinstance(text_candidate, str) and text_candidate:
                        memory.remember_text(key, text_candidate)
                    memory.remember_structure(key, value)

        extracted = refs.get("extracted_fields", {})
        if isinstance(extracted, dict):
            for key, value in extracted.items():
                if isinstance(value, dict):
                    memory.remember_fields(key, value)

        output_paths = refs.get("output_file_paths", [])
        if isinstance(output_paths, list):
            for path in output_paths:
                if isinstance(path, str) and path:
                    memory.add_output_file({"path": path})

        for obs in observations:
            step_id = str(obs.get("step_id") or "")
            if not step_id:
                continue
            if obs.get("success", False):
                memory.mark_completed(step_id)
            else:
                memory.mark_failed(step_id)