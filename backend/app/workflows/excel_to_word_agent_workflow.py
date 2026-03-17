from app.tools.excel_tool import ExcelTool
from app.tools.word_tool import WordTool
from app.core.agent import OfficeAgent


class ExcelToWordAgentWorkflow:
    def __init__(self):
        self.excel_tool = ExcelTool()
        self.word_tool = WordTool()
        self.agent = OfficeAgent()

    def run(self, instruction: str, excel_path: str, word_path: str, output_path: str) -> dict:
        logs = []

        logs.append("步骤1：读取 Excel 第一条数据")
        excel_data = self.excel_tool.read_first_row_as_dict(excel_path)
        excel_fields = list(excel_data.keys())
        logs.append(f"Excel 字段: {excel_fields}")

        logs.append("步骤2：读取 Word 表单支持字段")
        word_fields = self.word_tool.get_supported_form_fields()
        logs.append(f"Word 字段: {word_fields}")

        logs.append("步骤3：调用 LLM 生成字段映射")
        agent_result = self.agent.plan_excel_to_word(
            instruction=instruction,
            excel_fields=excel_fields,
            word_fields=word_fields,
        )

        mapping = agent_result.get("mapping", {})
        missing_fields = agent_result.get("missing_fields", [])
        confidence = agent_result.get("confidence", "unknown")

        logs.append(f"LLM mapping: {mapping}")
        logs.append(f"missing_fields: {missing_fields}")
        logs.append(f"confidence: {confidence}")

        logs.append("步骤4：构建写入 context")
        context = {}
        for word_field, excel_field in mapping.items():
            context[word_field] = excel_data.get(excel_field, "")
        logs.append(f"context: {context}")

        logs.append("步骤5：写入 Word")
        self.word_tool.fill_review_form(word_path, context, output_path)
        logs.append(f"输出文件: {output_path}")

        return {
            "logs": logs,
            "mapping": mapping,
            "missing_fields": missing_fields,
            "confidence": confidence,
            "output_path": output_path,
            "context": context,
        }