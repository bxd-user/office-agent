from app.core.llm_client import DeepSeekClient


class OfficeAgent:
    def __init__(self):
        self.llm = DeepSeekClient()

    def plan_excel_to_word(
        self,
        instruction: str,
        excel_fields: list[str],
        word_fields: list[str],
    ) -> dict:
        return self.llm.build_field_mapping(
            instruction=instruction,
            excel_fields=excel_fields,
            word_fields=word_fields,
        )