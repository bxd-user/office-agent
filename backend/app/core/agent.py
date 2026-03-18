from app.core.llm_client import DeepSeekClient


class OfficeAgent:
    def __init__(self):
        self.llm = DeepSeekClient()

    def plan_excel_to_word(
        self,
        instruction: str,
        excel_fields: list[str],
        word_fields: list[str],
        excel_preview: dict | None = None,
        word_field_slots: list[dict] | None = None,
    ) -> dict:
        return self.llm.build_field_mapping(
            instruction=instruction,
            excel_fields=excel_fields,
            word_fields=word_fields,
            excel_preview=excel_preview or {},
            word_field_slots=word_field_slots or [],
        )

    def analyze_excel_structure(self, instruction: str, excel_preview: dict) -> dict:
        return self.llm.analyze_excel_structure(
            instruction=instruction,
            excel_preview=excel_preview,
        )

    def plan_tool_calls(self, instruction: str, file_inventory: list[dict], available_tools: list[dict]) -> dict:
        return self.llm.plan_tool_calls(
            instruction=instruction,
            file_inventory=file_inventory,
            available_tools=available_tools,
        )