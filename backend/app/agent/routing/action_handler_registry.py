from __future__ import annotations

from app.agent.action_handlers.build_field_mapping import BuildFieldMappingHandler
from app.agent.action_handlers.extract_structured_data import ExtractStructuredDataHandler
from app.agent.action_handlers.fill_fields import FillFieldsHandler
from app.agent.action_handlers.read_document import ReadDocumentHandler
from app.agent.action_handlers.scan_template_fields import ScanTemplateFieldsHandler
from app.agent.action_handlers.update_table import UpdateTableHandler
from app.domain.action_types import ActionType


class ActionHandlerRegistry:
    def __init__(self) -> None:
        self._handlers = {
            ActionType.READ_DOCUMENT.value: ReadDocumentHandler(),
            ActionType.EXTRACT_STRUCTURED_DATA.value: ExtractStructuredDataHandler(),
            ActionType.FILL_FIELDS.value: FillFieldsHandler(),
            ActionType.UPDATE_TABLE.value: UpdateTableHandler(),
            ActionType.BUILD_FIELD_MAPPING.value: BuildFieldMappingHandler(),
            ActionType.SCAN_TEMPLATE_FIELDS.value: ScanTemplateFieldsHandler(),
        }

    def get_handler(self, action_type: str):
        handler = self._handlers.get(action_type)
        if handler is None:
            raise ValueError(f"No handler registered for action_type={action_type}")
        return handler