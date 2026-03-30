from __future__ import annotations

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
    SUPPORTED_CAPABILITIES = {
        CapabilityType.READ,
        CapabilityType.EXTRACT,
        CapabilityType.LOCATE,
        CapabilityType.FILL,
        CapabilityType.VALIDATE,
        CapabilityType.WRITE,
        CapabilityType.COMPARE,
        CapabilityType.SCAN_TEMPLATE,
    }

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
        if self.analyzer or self.template_scanner:
            supported.add(CapabilityType.EXTRACT)
        if self.locator:
            supported.add(CapabilityType.LOCATE)
        if self.filler:
            supported.add(CapabilityType.FILL)
        if self.validator:
            supported.add(CapabilityType.VALIDATE)
        if self.writer:
            supported.add(CapabilityType.WRITE)
        if self.comparator:
            supported.add(CapabilityType.COMPARE)
        if self.template_scanner:
            supported.add(CapabilityType.SCAN_TEMPLATE)
        return supported

    def scan_template(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.template_scanner:
            return self._unsupported("scan_template")

        try:
            result = self.template_scanner.scan(file_path)
            return ProviderResult.ok(
                message="Word template scanned successfully",
                data=result,
                capability=CapabilityType.SCAN_TEMPLATE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to scan word template: {e}",
                error_code="WORD_SCAN_TEMPLATE_FAILED",
                capability=CapabilityType.SCAN_TEMPLATE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def read(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.parser:
            return self._unsupported("read")

        try:
            text = self.parser.read_text(file_path=file_path)
            tables = self.parser.read_tables(file_path=file_path)
            structure = self.parser.extract_structure(file_path=file_path)

            return ProviderResult.ok(
                message="Word document read successfully",
                data={
                    "text": text,
                    "tables": tables,
                    "structure": structure,
                },
                capability=CapabilityType.READ.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to read word document: {e}",
                error_code="WORD_READ_FAILED",
                capability=CapabilityType.READ.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def extract(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.analyzer and not self.template_scanner:
            return self._unsupported("extract")

        try:
            analyzed = self.analyzer.find_placeholders(file_path=file_path) if self.analyzer else {}
            scanned = self.template_scanner.scan(file_path=file_path) if self.template_scanner else {}
            return ProviderResult.ok(
                message="Word document extracted successfully",
                data={
                    "analyzed": analyzed,
                    "template_fields": scanned,
                },
                capability=CapabilityType.EXTRACT.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to extract word document: {e}",
                error_code="WORD_EXTRACT_FAILED",
                capability=CapabilityType.EXTRACT.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def locate(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.locator:
            return self._unsupported("locate")

        try:
            result = self.locator.locate(file_path=file_path, **kwargs)
            return ProviderResult.ok(
                message="Targets located successfully",
                data={"locations": result},
                capability=CapabilityType.LOCATE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to locate targets: {e}",
                error_code="WORD_LOCATE_FAILED",
                capability=CapabilityType.LOCATE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def fill(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.filler:
            return self._unsupported("fill")

        try:
            mapping = kwargs.get("mapping") or kwargs.get("field_values") or {}
            output_path = kwargs.get("output_path") or self._default_output_path(file_path)
            content = str(kwargs.get("content") or "").strip()

            if isinstance(mapping, dict) and mapping:
                result = self.filler.write_kv_pairs_to_template(
                    file_path=file_path,
                    mapping=mapping,
                    output_path=output_path,
                    skip_empty_values=bool(kwargs.get("skip_empty_values", True)),
                    overwrite_strategy=str(kwargs.get("overwrite_strategy", "replace")),
                    preserve_format=bool(kwargs.get("preserve_format", True)),
                    table_cell_values=kwargs.get("table_cell_values"),
                )
            elif content and self.writer:
                # Fallback for "append content at end" tasks without placeholders.
                result = self.writer.append_text(
                    file_path=file_path,
                    append_text=content,
                    output_path=output_path,
                    avoid_overwrite=False,
                )
                result.setdefault("replace_count", 0)
                result.setdefault("paragraph_replace_count", 0)
                result.setdefault("table_replace_count", 0)
                result.setdefault("direct_cell_write_count", 0)
                result.setdefault("used_mapping_keys", [])
                result.setdefault("skipped_keys", [])
                result.setdefault("overwrite_strategy", str(kwargs.get("overwrite_strategy", "replace")))
                result.setdefault("preserve_format", bool(kwargs.get("preserve_format", True)))
                result["appended"] = bool(content)
            else:
                result = self.filler.write_kv_pairs_to_template(
                    file_path=file_path,
                    mapping={},
                    output_path=output_path,
                    skip_empty_values=bool(kwargs.get("skip_empty_values", True)),
                    overwrite_strategy=str(kwargs.get("overwrite_strategy", "replace")),
                    preserve_format=bool(kwargs.get("preserve_format", True)),
                    table_cell_values=kwargs.get("table_cell_values"),
                )

            field_values = kwargs.get("field_values") or kwargs.get("mapping") or {}
            return ProviderResult.ok(
                message="Word document filled successfully",
                data={
                    "field_values_count": len(field_values) if isinstance(field_values, dict) else 0,
                    "fill_result": result,
                },
                output_path=str(result.get("output_path") or output_path),
                capability=CapabilityType.FILL.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to fill word document: {e}",
                error_code="WORD_FILL_FAILED",
                capability=CapabilityType.FILL.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def compare(self, left_file_path: str, right_file_path: str, **kwargs) -> ProviderResult:
        if not self.comparator:
            return self._unsupported("compare")

        try:
            result = self.comparator.compare(
                left_file_path=left_file_path,
                right_file_path=right_file_path,
                **kwargs,
            )
            return ProviderResult.ok(
                message="Word documents compared successfully",
                data={"comparison": result},
                capability=CapabilityType.COMPARE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to compare word documents: {e}",
                error_code="WORD_COMPARE_FAILED",
                capability=CapabilityType.COMPARE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def validate(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.validator:
            return self._unsupported("validate")

        try:
            result = self.validator.validate_replacements(
                file_path=file_path,
                source_template_path=kwargs.get("source_template_path"),
                expected_fields=kwargs.get("expected_fields"),
                filled_values=kwargs.get("filled_values") or kwargs.get("field_values"),
                fill_targets=kwargs.get("fill_targets"),
            )
            return ProviderResult.ok(
                message="Word document validated successfully",
                data={"validation": result},
                capability=CapabilityType.VALIDATE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to validate word document: {e}",
                error_code="WORD_VALIDATE_FAILED",
                capability=CapabilityType.VALIDATE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

    def write(self, file_path: str, **kwargs) -> ProviderResult:
        if not self.writer:
            return self._unsupported("write")

        try:
            output_path = kwargs.get("output_path") or self._default_output_path(file_path, suffix="_written")
            replacements = kwargs.get("replacements") or kwargs.get("field_values") or {}
            append_text = kwargs.get("append_text")

            if append_text:
                result = self.writer.append_text(
                    file_path=file_path,
                    append_text=str(append_text),
                    output_path=output_path,
                )
            else:
                result = self.writer.replace_text(
                    file_path=file_path,
                    replacements={str(k): str(v) for k, v in dict(replacements).items()},
                    output_path=output_path,
                )

            return ProviderResult.ok(
                message="Word document written successfully",
                data={"write_result": result},
                output_path=output_path,
                capability=CapabilityType.WRITE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
                raw={"provider": "word"},
            )
        except Exception as e:
            return ProviderResult.fail(
                message=f"Failed to write word document: {e}",
                error_code="WORD_WRITE_FAILED",
                capability=CapabilityType.WRITE.value,
                provider=self.provider_name,
                document_type=self.document_type.value,
            )

