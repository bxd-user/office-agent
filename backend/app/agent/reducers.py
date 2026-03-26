from __future__ import annotations

from typing import Any, Dict

from app.agent.memory import WorkingMemory


class ToolResultReducer:
    def reduce(self, memory: WorkingMemory, tool_name: str, tool_args: Dict[str, Any], tool_result: Dict[str, Any]) -> None:
        if not tool_result.get("success"):
            memory.add_warning(f"Tool failed: {tool_name} - {tool_result.get('error', '')}")
            return

        content = tool_result.get("content")
        if content is None:
            return

        file_id = tool_args.get("file_id") or tool_args.get("file_path") or ""

        if tool_name == "word.read_text":
            text = content.get("text", "")
            if file_id:
                memory.remember_text(file_id, text)

        elif tool_name == "word.extract_structure":
            if file_id:
                memory.remember_structure(file_id, content)

        elif tool_name == "word.read_tables":
            if file_id:
                memory.table_views[file_id] = content.get("tables", [])

        elif tool_name == "excel.read_preview":
            if file_id:
                memory.table_views[file_id] = content

        elif tool_name == "understanding.extract_fields":
            if file_id:
                memory.remember_fields(file_id, content)
            else:
                memory.notes.append(f"Extracted fields without explicit file_id: {content}")

        elif tool_name in ("word.replace_text", "word.write_kv_pairs_to_template", "word.fill_table_cells"):
            output_path = content.get("output_path")
            if output_path:
                memory.add_output_file(content)

        elif tool_name == "understanding.match_source_to_template":
            memory.candidate_mappings.append(content)