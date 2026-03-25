from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional

from app.agent.critic import Critic
from app.agent.execution_context import ExecutionContext
from app.agent.executor_v2 import ExecutorV2
from app.agent.finalizer import Finalizer
from app.agent.planner_v2 import PlannerV2
from app.agent.replan import Replanner
from app.agent.verifier import Verifier


@dataclass
class AgentResult:
    answer: str
    output_files: List[Dict[str, str]] = field(default_factory=list)
    tool_trace: List[Dict[str, Any]] = field(default_factory=list)


class AgentRuntime:
    """Agent runtime with plan/execute/verify/replan loop."""

    def __init__(self, llm_client, mcp_client):
        self.llm_client = llm_client
        self.mcp_client = mcp_client

        self.planner = PlannerV2(llm_client)
        self.executor = ExecutorV2(llm_client, mcp_client)
        self.verifier = Verifier(llm_client)
        self.critic = Critic(llm_client)
        self.replanner = Replanner(llm_client)
        self.finalizer = Finalizer(llm_client)

    def run(self, session_or_task_id, user_prompt: Optional[str] = None, files: Optional[list] = None) -> AgentResult:
        # Support both AgentSession object and direct parameters
        if hasattr(session_or_task_id, 'task_id'):
            # It's an AgentSession object
            session = session_or_task_id
            task_id = session.task_id
            user_prompt = session.user_prompt
            files = session.files
        else:
            # It's task_id string
            task_id = session_or_task_id

        context = ExecutionContext(
            task_id=task_id,
            user_prompt=user_prompt or "",
            files=files or [],
        )
        context.memory.file_manifest = files or []

        plan = self.planner.build_plan(user_prompt=context.user_prompt, files=context.files)
        context.plan = plan

        for fr in plan.file_roles:
            context.memory.remember_file_role(fr.file_id, fr.role)

        step_index = 0
        while step_index < len(context.plan.steps):
            step = context.plan.steps[step_index]

            retries = 0
            while retries <= context.max_retries_per_step:
                record = self.executor.execute_step(context, step)
                verifier_result = self.verifier.verify_step(context, step, record)
                record.verifier_result = verifier_result
                context.add_step_record(record)

                if verifier_result.get("passed", False):
                    break

                critique = self.critic.analyze_failure(context, step, record, verifier_result)
                action = critique.get("action", "retry")

                if action == "retry" and retries < context.max_retries_per_step:
                    retries += 1
                    context.memory.add_note(
                        f"Retrying step {step.step_id}: {critique.get('reason', '')}"
                    )
                    continue

                if action == "replan":
                    new_plan = self.replanner.replan(context)
                    if new_plan is not None:
                        context.plan = new_plan
                        step_index = -1
                        break

                step.status = "failed"
                context.memory.mark_failed(step.step_id)
                break

            step_index += 1

        answer = self.finalizer.build_final_answer(context)

        step_records = [
            {
                "step_id": r.step_id,
                "tool_calls": r.tool_calls,
                "outputs": r.outputs,
                "success": r.success,
                "error": r.error,
                "verifier_result": r.verifier_result,
            }
            for r in context.step_records
        ]

        return AgentResult(
            answer=answer,
            output_files=context.memory.output_files,
            tool_trace=step_records,
        )