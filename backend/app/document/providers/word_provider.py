from __future__ import annotations

from typing import Any

from app.domain.capability_types import CapabilityType
from app.domain.document_types import DocumentType
from app.document.providers.base import BaseDocumentProvider, ProviderResult

try:
    from app.document.word.parser import WordParser
except Exception:
    WordParser = None

try:
    from app.document.word.analyzer import WordAnalyzer
except Exception:
    WordAnalyzer = None

try:
    from app.document.word.locator import WordLocator
except Exception:
    WordLocator = None

try:
    from app.document.word.filler import WordFiller
except Exception:
    WordFiller = None

try:
    from app.document.word.validator import WordValidator
except Exception:
    WordValidator = None

try:
    from app.document.word.writer import WordWriter
except Exception:
    WordWriter = None

try:
    from app.document.word.comparator import WordComparator
except Exception:
    WordComparator = None

try:
    from app.document.word.template_scanner import WordTemplateScanner
except Exception:
    WordTemplateScanner = None


class WordProvider(BaseDocumentProvider):
    document_type = DocumentType.WORD

    def __init__(self) -> None:
        self.parser = WordParser() if WordParser else None
        self.analyzer = WordAnalyzer() if WordAnalyzer else None
        self.locator = WordLocator() if WordLocator else None
        self.filler = WordFiller() if WordFiller else None
        self.validator = WordValidator() if WordValidator else None
        self.writer = WordWriter() if WordWriter else None
        self.comparator = WordComparator() if WordComparator else None
        self.template_scanner = WordTemplateScanner() if WordTemplateScanner else None

    def supported_capabilities(self) -> set[CapabilityType]:
        supported: set[CapabilityType] = set()

        if self.parser:
            supported.add(CapabilityType.READ)
            supported.add(CapabilityType.EXTRACT)

        if self.locator:
            supported.add(CapabilityType.LOCATE)

        if self.filler:
            supported.add(CapabilityType.FILL)

        if self.comparator:
            supported.add(CapabilityType.COMPARE)

        if self.validator:
            supported.add(CapabilityType.VALIDATE)

        if self.writer:
            supported.add(CapabilityType.WRITE)

        if self.template_scanner:
            supported.add(CapabilityType.SCAN_TEMPLATE)

        return supported

    def scan_template(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.template_scanner:
            return ProviderResult(success=False, message="Word template scanner is not available")

        try:
            result = self.template_scanner.scan(file_path)
            return ProviderResult(
                success=True,
                message="Word template scanned successfully",
                data=result,
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to scan word template: {e}")

    def read(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.parser:
            return ProviderResult(success=False, message="Word parser is not available")

        try:
            parsed = self._safe_call(
                obj=self.parser,
                candidate_methods=["read_text", "extract_structure", "read_tables", "parse", "read", "load"],
                file_path=file_path,
            )

            return ProviderResult(
                success=True,
                message="Word document read successfully",
                data={"document": parsed},
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to read word document: {e}")

    def extract(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.parser:
            return ProviderResult(success=False, message="Word parser is not available")

        try:
            if hasattr(self.parser, "extract_structure"):
                parsed = self.parser.extract_structure(file_path=file_path)
            elif hasattr(self.parser, "read_text"):
                parsed = {
                    "text": self.parser.read_text(file_path=file_path),
                    "tables": self.parser.read_tables(file_path=file_path) if hasattr(self.parser, "read_tables") else [],
                }
            else:
                parsed = self._safe_call(
                    obj=self.parser,
                    candidate_methods=["extract_structure", "read_text", "read_tables", "parse", "read", "load"],
                    file_path=file_path,
                )

            analyzed = None
            if self.analyzer:
                analyzed = self._safe_call(
                    obj=self.analyzer,
                    candidate_methods=["find_placeholders", "analyze", "extract", "run"],
                    file_path=file_path,
                )

            return ProviderResult(
                success=True,
                message="Word document extracted successfully",
                data={
                    "parsed": parsed,
                    "structured_data": analyzed if analyzed is not None else parsed,
                },
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to extract word document: {e}")

    def locate(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.locator:
            return ProviderResult(success=False, message="Word locator is not available")

        try:
            result = self._safe_call(
                obj=self.locator,
                candidate_methods=["locate", "find", "run"],
                file_path=file_path,
                **kwargs,
            )
            return ProviderResult(
                success=True,
                message="Targets located successfully",
                data={"locations": result},
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to locate targets: {e}")

    def fill(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.filler:
            return ProviderResult(success=False, message="Word filler is not available")

        try:
            call_kwargs = dict(kwargs)
            call_kwargs.setdefault("file_path", file_path)
            if "field_values" in call_kwargs and "mapping" not in call_kwargs:
                call_kwargs["mapping"] = call_kwargs["field_values"]

            result = self._safe_call(
                obj=self.filler,
                candidate_methods=["fill", "apply", "run", "write_kv_pairs_to_template"],
                **call_kwargs,
            )

            output_path = kwargs.get("output_path")
            if isinstance(result, dict) and not output_path:
                output_path = result.get("output_path")
            if isinstance(result, str) and not output_path:
                output_path = result

            field_values = kwargs.get("field_values") or kwargs.get("mapping") or {}
            return ProviderResult(
                success=True,
                message="Word document filled successfully",
                data={
                    "field_values_count": len(field_values) if isinstance(field_values, dict) else 0,
                    "fill_result": result,
                },
                output_path=output_path,
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to fill word document: {e}")

    def compare(self, left_file_path: str, right_file_path: str, **kwargs) -> ProviderResult:
        if not self.comparator:
            return ProviderResult(success=False, message="Word comparator is not available")

        try:
            result = self._safe_call(
                obj=self.comparator,
                candidate_methods=["compare", "run"],
                left_file_path=left_file_path,
                right_file_path=right_file_path,
                **kwargs,
            )
            return ProviderResult(
                success=True,
                message="Word documents compared successfully",
                data={"comparison": result},
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to compare word documents: {e}")

    def validate(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.validator:
            return ProviderResult(success=False, message="Word validator is not available")

        try:
            result = self._safe_call(
                obj=self.validator,
                candidate_methods=["validate", "run"],
                file_path=file_path,
                **kwargs,
            )
            return ProviderResult(
                success=True,
                message="Word document validated successfully",
                data={"validation": result},
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to validate word document: {e}")

    def write(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.writer:
            return ProviderResult(success=False, message="Word writer is not available")

        try:
            result = self._safe_call(
                obj=self.writer,
                candidate_methods=["write", "save", "run", "replace_text", "append_text"],
                file_path=file_path,
                **kwargs,
            )

            output_path = kwargs.get("output_path")
            if isinstance(result, dict) and not output_path:
                output_path = result.get("output_path")
            if isinstance(result, str) and not output_path:
                output_path = result

            return ProviderResult(
                success=True,
                message="Word document written successfully",
                data={"write_result": result},
                output_path=output_path,
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to write word document: {e}")

    @staticmethod
    def _safe_call(obj: Any, candidate_methods: list[str], **kwargs) -> Any:
        for method_name in candidate_methods:
            method = getattr(obj, method_name, None)
            if callable(method):
                return method(**kwargs)
        raise AttributeError(
            f"{obj.__class__.__name__} does not have any callable methods in {candidate_methods}"
        )
