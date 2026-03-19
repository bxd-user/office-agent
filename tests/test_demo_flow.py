from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from agents.base import BaseAgent
from core.messages import AgentResult
from core.task_context import TaskContext


class _SuccessAgent(BaseAgent):
	name = "success_agent"

	def _run(self, ctx: TaskContext) -> AgentResult:
		ctx.log("running success")
		return AgentResult.ok(message="ok")


class _FailAgent(BaseAgent):
	name = "fail_agent"

	def _run(self, ctx: TaskContext) -> AgentResult:
		return self.fail(ctx, "boom")


class DemoFlowTests(unittest.TestCase):
	def test_base_agent_success_updates_context_status(self) -> None:
		ctx = TaskContext(task_id="t1", instruction="demo")
		result = _SuccessAgent().run(ctx)

		self.assertTrue(result.success)
		self.assertEqual(ctx.current_step, "success_agent")
		self.assertEqual(ctx.status, "succeeded")
		self.assertIsNone(ctx.error)

	def test_base_agent_failure_updates_context_error(self) -> None:
		ctx = TaskContext(task_id="t2", instruction="demo")
		result = _FailAgent().run(ctx)

		self.assertFalse(result.success)
		self.assertEqual(ctx.status, "failed")
		self.assertEqual(ctx.error, "boom")


if __name__ == "__main__":
	unittest.main()
