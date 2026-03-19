from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from agents.mapper import MapperAgent


class MapperAgentTests(unittest.TestCase):
	def test_normalize_names_deduplicates_and_trims(self) -> None:
		agent = MapperAgent()
		names = [" 姓名 ", "", "姓名", "班级", "班级 "]
		self.assertEqual(agent._normalize_names(names), ["姓名", "班级"])

	def test_parse_mapping_response_supports_fenced_json(self) -> None:
		agent = MapperAgent()
		text = """```json
{\"姓名\": \"student_name\", \"班级\": \"class_name\"}
```"""

		parsed = agent._parse_mapping_response(text)
		self.assertEqual(
			parsed,
			{"姓名": "student_name", "班级": "class_name"},
		)


if __name__ == "__main__":
	unittest.main()
