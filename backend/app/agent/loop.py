from __future__ import annotations

from typing import Any

from app.agent.executor_v2 import ExecutorV2
from app.agent.planner_v2 import PlannerV2
from app.agent.replan import Replanner
from app.agent.verifier import Verifier


class AgentLoop:
    def __init__(
        self,
        file_resolver,
        max_replans: int = 2,
    ) -> None:
        self.file_resolver = file_resolver
        self.max_replans = max_replans

        self.planner = PlannerV2()
        self.replanner = Replanner()
        self.verifier = Verifier()

    def run(
        self,
        user_request: str,
        files: list[dict[str, Any]],
        capabilities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        plan = self.planner.build_plan(
            user_request=user_request,
            files=files,
            capabilities=capabilities or {},
        )

        attempt = 0
        last_observations = []
        last_context = {}
        last_trace = []

        while attempt <= self.max_replans:
            executor = ExecutorV2(file_resolver=self.file_resolver)
            observations = executor.execute_plan(plan)

            last_observations = [obs.model_dump() for obs in observations]
            last_context = executor.export_context()
            last_trace = executor.export_trace()

            failed = next((obs for obs in observations if not obs.success), None)
            if failed is None:
                summary = self.verifier.summarize(
                    observations=last_observations,
                    context=last_context,
                )
                return {
                    "success": True,
                    "plan": plan.model_dump(),
                    "observations": last_observations,
                    "context": last_context,
                    "trace": last_trace,
                    "summary": summary,
                }

            if attempt >= self.max_replans:
                summary = self.verifier.summarize(
                    observations=last_observations,
                    context=last_context,
                )
                return {
                    "success": False,
                    "plan": plan.model_dump(),
                    "observations": last_observations,
                    "context": last_context,
                    "trace": last_trace,
                    "summary": summary,
                }

            plan = self.replanner.rebuild_plan(
                user_request=user_request,
                files=files,
                old_plan=plan,
                execution_trace=last_trace,
            )
            attempt += 1

        return {
            "success": False,
            "plan": plan.model_dump(),
            "observations": last_observations,
            "context": last_context,
            "trace": last_trace,
            "summary": {
                "success": False,
                "summary": "Unexpected loop termination",
                "issues": ["agent_loop_terminated_unexpectedly"],
            },
        }