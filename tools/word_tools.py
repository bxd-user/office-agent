from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from tools.base import (
    BaseInspectTool,
    BaseTransformTool,
    BaseValidateTool,
    Capability,
    FileType,
    ToolContext,
    ToolInput,
    ToolResult,
    ToolValidationError,
)
from tools.common_tools import (
    build_output_path,
    get_file_name,
)


# =========================
# 输入模型
# =========================

@dataclass(slots=True)
class WordFileInput(ToolInput):
    file_path: str

    def validate_basic(self) -> None:
        if not self.file_path:
            raise ToolValidationError("file_path is required")


@dataclass(slots=True)
class InspectWordStructureInput(WordFileInput):
    """检查 Word 结构。"""
    include_blocks: bool = False


@dataclass(slots=True)
class ExtractWordPlaceholdersInput(WordFileInput):
    """提取 Word 占位符。"""
    pass


@dataclass(slots=True)
class FillWordTemplateInput(ToolInput):
    """填充 Word 模板。"""
    template_path: str
    replacements: Dict[str, Any] = field(default_factory=dict)
    output_path: Optional[str] = None
    output_dir: Optional[str] = None
    output_tag: str = "filled"

    def validate_basic(self) -> None:
        if not self.template_path:
            raise ToolValidationError("template_path is required")
        if not isinstance(self.replacements, dict):
            raise ToolValidationError("replacements must be a dict")


@dataclass(slots=True)
class ValidateWordPlaceholdersInput(WordFileInput):
    """校验 Word 中是否还有未填占位符。"""
    expected_empty: bool = True


# =========================
# 公共校验
# =========================

_SUPPORTED_EXTENSIONS = (".docx",)


def _validate_word_file_path(file_path: str) -> None:
    from adapters.docx_adapter import ensure_docx_file

    ensure_docx_file(file_path)


# =========================
# 工具类
# =========================

class InspectWordStructureTool(BaseInspectTool):
    name = "inspect_word_structure"
    description = "Inspect Word document structure, including paragraphs, tables, and placeholders"
    supported_file_types = (FileType.WORD,)
    capabilities = (Capability.READ, Capability.INSPECT, Capability.EXTRACT)
    supported_extensions = _SUPPORTED_EXTENSIONS

    @property
    def input_model(self):
        return InspectWordStructureInput

    def validate_input(self, params: ToolInput) -> None:
        super().validate_input(params)
        assert isinstance(params, InspectWordStructureInput)

        params.validate_basic()
        _validate_word_file_path(params.file_path)

    def execute(self, params: InspectWordStructureInput, ctx: ToolContext) -> ToolResult:
        self.ensure_path_supported(params.file_path)
        ctx.log(f"[{self.name}] inspecting word document: {params.file_path}")

        from adapters.docx_adapter import inspect_document, get_document_blocks

        inspection = inspect_document(params.file_path)

        if params.include_blocks:
            inspection["blocks"] = get_document_blocks(params.file_path)

        return ToolResult.ok(
            data=inspection,
            message="Word document inspected successfully",
        )


class ExtractWordPlaceholdersTool(BaseInspectTool):
    name = "extract_word_placeholders"
    description = "Extract placeholders from a Word document"
    supported_file_types = (FileType.WORD,)
    capabilities = (Capability.READ, Capability.INSPECT, Capability.EXTRACT)
    supported_extensions = _SUPPORTED_EXTENSIONS

    @property
    def input_model(self):
        return ExtractWordPlaceholdersInput

    def validate_input(self, params: ToolInput) -> None:
        super().validate_input(params)
        assert isinstance(params, ExtractWordPlaceholdersInput)

        params.validate_basic()
        _validate_word_file_path(params.file_path)

    def execute(self, params: ExtractWordPlaceholdersInput, ctx: ToolContext) -> ToolResult:
        self.ensure_path_supported(params.file_path)
        ctx.log(f"[{self.name}] extracting placeholders from: {params.file_path}")

        from adapters.docx_adapter import extract_placeholders

        placeholders = extract_placeholders(params.file_path)

        data = {
            "file_path": params.file_path,
            "file_name": get_file_name(params.file_path),
            "placeholder_count": len(placeholders),
            "placeholders": placeholders,
        }

        return ToolResult.ok(
            data=data,
            message="Word placeholders extracted successfully",
        )


class FillWordTemplateTool(BaseTransformTool):
    name = "fill_word_template"
    description = "Fill placeholders in a Word template and save a new document"
    supported_file_types = (FileType.WORD,)
    capabilities = (Capability.FILL_TEMPLATE, Capability.WRITE, Capability.REPLACE)
    supported_extensions = _SUPPORTED_EXTENSIONS

    @property
    def input_model(self):
        return FillWordTemplateInput

    def validate_input(self, params: ToolInput) -> None:
        super().validate_input(params)
        assert isinstance(params, FillWordTemplateInput)

        params.validate_basic()
        _validate_word_file_path(params.template_path)

        if params.output_path is None and params.output_dir is None:
            raise ToolValidationError(
                "Either output_path or output_dir must be provided"
            )

    def execute(self, params: FillWordTemplateInput, ctx: ToolContext) -> ToolResult:
        self.ensure_path_supported(params.template_path)
        ctx.log(f"[{self.name}] filling template: {params.template_path}")

        from adapters.docx_adapter import (
            replace_placeholders_in_doc,
            find_unfilled_placeholders,
        )

        if params.output_path:
            output_path = params.output_path
        else:
            assert params.output_dir is not None
            output_path = build_output_path(
                output_dir=params.output_dir,
                original_name=get_file_name(params.template_path),
                tag=params.output_tag,
                new_extension=".docx",
            )

        final_path = replace_placeholders_in_doc(
            file_path=params.template_path,
            replacements=params.replacements,
            output_path=output_path,
        )

        unfilled = find_unfilled_placeholders(final_path)

        data = {
            "template_path": params.template_path,
            "output_path": final_path,
            "replacement_count": len(params.replacements),
            "unfilled_placeholders": unfilled,
            "passed": len(unfilled) == 0,
        }

        return ToolResult.ok(
            data=data,
            message="Word template filled successfully",
        )


class ValidateWordPlaceholdersTool(BaseValidateTool):
    name = "validate_word_placeholders"
    description = "Validate whether a Word document still contains unfilled placeholders"
    supported_file_types = (FileType.WORD,)
    capabilities = (Capability.READ, Capability.VALIDATE, Capability.INSPECT)
    supported_extensions = _SUPPORTED_EXTENSIONS

    @property
    def input_model(self):
        return ValidateWordPlaceholdersInput

    def validate_input(self, params: ToolInput) -> None:
        super().validate_input(params)
        assert isinstance(params, ValidateWordPlaceholdersInput)

        params.validate_basic()
        _validate_word_file_path(params.file_path)

    def execute(self, params: ValidateWordPlaceholdersInput, ctx: ToolContext) -> ToolResult:
        self.ensure_path_supported(params.file_path)
        ctx.log(f"[{self.name}] validating placeholders in: {params.file_path}")

        from adapters.docx_adapter import find_unfilled_placeholders

        unfilled = find_unfilled_placeholders(params.file_path)
        passed = len(unfilled) == 0

        data = {
            "file_path": params.file_path,
            "unfilled_placeholders": unfilled,
            "unfilled_count": len(unfilled),
            "passed": passed,
        }

        if passed:
            return ToolResult.ok(
                data=data,
                message="Word placeholders validation passed",
            )

        return ToolResult.fail(
            error="Word placeholders validation failed",
            message="Unfilled placeholders still exist in the document",
            data=data,
        )