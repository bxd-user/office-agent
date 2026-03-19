from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from core.task_context import TaskContext


class TaskContextGetterTests(unittest.TestCase):
	def test_excel_getters_handle_malformed_data(self) -> None:
		ctx = TaskContext(task_id="t3", instruction="demo")
		ctx.excel_data = {
			"headers": ["姓名", 123, None],
			"records": [{"姓名": "张三"}, "bad", 1],
		}

		self.assertEqual(ctx.get_excel_headers(), ["姓名", "123", "None"])
		self.assertEqual(ctx.get_excel_records(), [{"姓名": "张三"}])
		self.assertEqual(ctx.get_first_excel_record(), {"姓名": "张三"})

	def test_word_placeholder_getter_prefers_direct_value(self) -> None:
		ctx = TaskContext(task_id="t4", instruction="demo")
		ctx.word_structure = {"placeholders": ["结构占位符"]}
		ctx.word_placeholders = ["直接占位符", 100]

		self.assertEqual(ctx.get_word_placeholders(), ["直接占位符", "100"])


if __name__ == "__main__":
	unittest.main()
