from __future__ import annotations

from app.agent.action_handlers.build_field_mapping import BuildFieldMappingHandler
from app.agent.action_handlers.compare_documents import CompareDocumentsHandler
from app.agent.action_handlers.extract_structured_data import ExtractStructuredDataHandler
from app.agent.action_handlers.fill_fields import FillFieldsHandler
from app.agent.action_handlers.locate_targets import LocateTargetsHandler
from app.agent.action_handlers.read_document import ReadDocumentHandler
from app.agent.action_handlers.scan_template_fields import ScanTemplateFieldsHandler
from app.agent.action_handlers.summarize_content import SummarizeContentHandler
from app.agent.action_handlers.update_table import UpdateTableHandler
from app.agent.action_handlers.validate_output import ValidateOutputHandler
from app.agent.action_handlers.write_output import WriteOutputHandler
from app.domain.action_types import ActionType


class ActionHandlerRegistry:
    def __init__(self) -> None:
        read_handler = ReadDocumentHandler()
        extract_handler = ExtractStructuredDataHandler()
        locate_handler = LocateTargetsHandler()
        fill_handler = FillFieldsHandler()
        update_table_handler = UpdateTableHandler()
        summarize_handler = SummarizeContentHandler()
        compare_handler = CompareDocumentsHandler()
        validate_handler = ValidateOutputHandler()
        write_handler = WriteOutputHandler()
        build_mapping_handler = BuildFieldMappingHandler()
        scan_template_handler = ScanTemplateFieldsHandler()

        self._handlers = {
            ActionType.READ_DOCUMENT.value: read_handler,
            ActionType.EXTRACT_STRUCTURED_DATA.value: extract_handler,
            ActionType.LOCATE_TARGETS.value: locate_handler,
            ActionType.FILL_FIELDS.value: fill_handler,
            ActionType.UPDATE_TABLE.value: update_table_handler,
            ActionType.SUMMARIZE_CONTENT.value: summarize_handler,
            ActionType.COMPARE_DOCUMENTS.value: compare_handler,
            ActionType.VALIDATE_OUTPUT.value: validate_handler,
            ActionType.CREATE_OUTPUT.value: write_handler,
            ActionType.BUILD_FIELD_MAPPING.value: build_mapping_handler,
            ActionType.SCAN_TEMPLATE_FIELDS.value: scan_template_handler,

            "read": read_handler,
            "extract": extract_handler,
            "locate": locate_handler,
            "fill": fill_handler,
            "write": write_handler,
            "summarize": summarize_handler,
            "compare": compare_handler,
            "validate": validate_handler,
        }

    def get_handler(self, action_type: str):
        handler = self._handlers.get(action_type)
        if handler is None:
            raise ValueError(f"No handler registered for action_type={action_type}")
        return handler