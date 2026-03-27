from __future__ import annotations

import os
import re
from difflib import unified_diff
from pathlib import Path
from typing import Any

from app.domain.capability_types import CapabilityType
from app.domain.document_types import DocumentType
from app.document.providers.base import BaseDocumentProvider, ProviderResult


class TextProvider(BaseDocumentProvider):

    document_type = DocumentType.TEXT

    _PLACEHOLDER_PATTERNS = [
        re.compile(r"\{\{\s*([^{}\n]+?)\s*\}\}"),
        re.compile(r"<<\s*([^<>\n]+?)\s*>>"),
        re.compile(r"【\s*([^【】\n]+?)\s*】"),
    ]

    def supported_capabilities(self) -> set[CapabilityType]:
        return {
            CapabilityType.READ,
            CapabilityType.EXTRACT,
            CapabilityType.LOCATE,
            CapabilityType.FILL,
            CapabilityType.COMPARE,
            CapabilityType.VALIDATE,
            CapabilityType.WRITE,
            CapabilityType.SCAN_TEMPLATE,
        }

    def read(self, file_path: str, **kwargs) -> ProviderResult:
        try:
            text = self._read_text(file_path)
            lines = text.splitlines()
            return ProviderResult(
                success=True,
                message="Text document read successfully",
                data={
                    "text": text,
                    "line_count": len(lines),
                    "char_count": len(text),
                    "preview": "\n".join(lines[:20]),
                },
                raw={"provider": "text"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to read text document: {e}")

    def extract(self, file_path: str, **kwargs) -> ProviderResult:
        try:
            text = self._read_text(file_path)
            lines = text.splitlines()
            paragraphs = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]

            headings: list[dict[str, Any]] = []
            if Path(file_path).suffix.lower() == ".md":
                for idx, line in enumerate(lines):
                    stripped = line.lstrip()
                    if stripped.startswith("#"):
                        level = len(stripped) - len(stripped.lstrip("#"))
                        headings.append(
                            {
                                "line_index": idx,
                                "level": level,
                                "title": stripped[level:].strip(),
                            }
                        )

            fields, occurrences = self._scan_fields(text)
            return ProviderResult(
                success=True,
                message="Text structured data extracted successfully",
                data={
                    "paragraphs": paragraphs,
                    "headings": headings,
                    "fields": fields,
                    "field_occurrences": occurrences,
                },
                raw={"provider": "text"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to extract text data: {e}")

    def locate(self, file_path: str, **kwargs) -> ProviderResult:
        keyword = kwargs.get("keyword")
        if not keyword:
            return ProviderResult(success=False, message="'keyword' is required for text locate")

        try:
            text = self._read_text(file_path)
            lines = text.splitlines()
            case_sensitive = bool(kwargs.get("case_sensitive", False))
            use_regex = bool(kwargs.get("regex", False))
            max_results = int(kwargs.get("max_results", 200))

            results: list[dict[str, Any]] = []
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(str(keyword), flags)
                for line_idx, line in enumerate(lines):
                    for match in pattern.finditer(line):
                        results.append(
                            {
                                "line_index": line_idx,
                                "column_start": match.start(),
                                "column_end": match.end(),
                                "line_text": line,
                                "matched": match.group(0),
                            }
                        )
                        if len(results) >= max_results:
                            break
                    if len(results) >= max_results:
                        break
            else:
                needle = str(keyword) if case_sensitive else str(keyword).lower()
                for line_idx, line in enumerate(lines):
                    line_cmp = line if case_sensitive else line.lower()
                    start = line_cmp.find(needle)
                    while start != -1:
                        end = start + len(needle)
                        results.append(
                            {
                                "line_index": line_idx,
                                "column_start": start,
                                "column_end": end,
                                "line_text": line,
                                "matched": line[start:end],
                            }
                        )
                        if len(results) >= max_results:
                            break
                        start = line_cmp.find(needle, end)
                    if len(results) >= max_results:
                        break

            return ProviderResult(
                success=True,
                message="Text locate completed",
                data={
                    "keyword": keyword,
                    "case_sensitive": case_sensitive,
                    "regex": use_regex,
                    "matches": results,
                },
                raw={"provider": "text"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to locate in text: {e}")

    def fill(self, file_path: str, **kwargs) -> ProviderResult:
        try:
            field_values: dict[str, Any] = kwargs.get("field_values", {})
            text = self._read_text(file_path)
            replaced_text, replace_count = self._replace_fields(text, field_values)

            output_path = kwargs.get("output_path") or self._default_output_path(file_path, suffix="_filled")
            self._write_text(output_path, replaced_text)

            return ProviderResult(
                success=True,
                message="Text document filled successfully",
                data={
                    "field_values_count": len(field_values),
                    "replace_count": replace_count,
                },
                output_path=output_path,
                raw={"provider": "text"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to fill text document: {e}")

    def compare(self, left_file_path: str, right_file_path: str, **kwargs) -> ProviderResult:
        try:
            left_text = self._read_text(left_file_path)
            right_text = self._read_text(right_file_path)

            if left_text == right_text:
                return ProviderResult(
                    success=True,
                    message="Text documents are identical",
                    data={"identical": True, "diff": []},
                    raw={"provider": "text"},
                )

            left_lines = left_text.splitlines()
            right_lines = right_text.splitlines()
            diff = list(
                unified_diff(
                    left_lines,
                    right_lines,
                    fromfile=os.path.basename(left_file_path),
                    tofile=os.path.basename(right_file_path),
                    lineterm="",
                )
            )
            return ProviderResult(
                success=True,
                message="Text documents compared successfully",
                data={"identical": False, "diff": diff[:1000]},
                raw={"provider": "text"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to compare text documents: {e}")

    def validate(self, file_path: str, **kwargs) -> ProviderResult:
        try:
            text = self._read_text(file_path)
            required_keywords: list[str] = kwargs.get("required_keywords", [])
            missing_keywords = [key for key in required_keywords if key not in text]

            must_not_be_empty = bool(kwargs.get("must_not_be_empty", True))
            valid = (not must_not_be_empty or bool(text.strip())) and not missing_keywords

            return ProviderResult(
                success=True,
                message="Text validation completed",
                data={
                    "valid": valid,
                    "empty": len(text.strip()) == 0,
                    "required_keywords": required_keywords,
                    "missing_keywords": missing_keywords,
                },
                raw={"provider": "text"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to validate text document: {e}")

    def write(self, file_path: str, **kwargs) -> ProviderResult:
        try:
            text = kwargs.get("text")
            if text is None:
                text = kwargs.get("content")
            if text is None:
                return ProviderResult(success=False, message="'text' or 'content' is required for text write")

            output_path = kwargs.get("output_path") or self._default_output_path(file_path, suffix="_written")
            self._write_text(output_path, str(text))

            return ProviderResult(
                success=True,
                message="Text document written successfully",
                data={"char_count": len(str(text))},
                output_path=output_path,
                raw={"provider": "text"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to write text document: {e}")

    def scan_template(self, file_path: str, **kwargs) -> ProviderResult:
        try:
            text = self._read_text(file_path)
            fields, occurrences = self._scan_fields(text)
            return ProviderResult(
                success=True,
                message="Text template scanned successfully",
                data={
                    "fields": fields,
                    "field_count": len(fields),
                    "occurrences": occurrences,
                },
                raw={"provider": "text"},
            )
        except Exception as e:
            return ProviderResult(success=False, message=f"Failed to scan text template: {e}")

    @staticmethod
    def _read_text(file_path: str) -> str:
        encodings = ["utf-8", "utf-8-sig", "gb18030", "gbk"]
        last_error: Exception | None = None
        for encoding in encodings:
            try:
                return Path(file_path).read_text(encoding=encoding)
            except Exception as e:
                last_error = e
        raise RuntimeError(f"Unsupported text encoding: {last_error}")

    @staticmethod
    def _write_text(file_path: str, text: str) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    @classmethod
    def _scan_fields(cls, text: str) -> tuple[list[str], list[dict[str, Any]]]:
        fields: set[str] = set()
        occurrences: list[dict[str, Any]] = []

        for pattern in cls._PLACEHOLDER_PATTERNS:
            for match in pattern.finditer(text):
                field = match.group(1).strip()
                fields.add(field)
                occurrences.append(
                    {
                        "field": field,
                        "start": match.start(),
                        "end": match.end(),
                        "matched": match.group(0),
                    }
                )

        return sorted(fields), occurrences

    @classmethod
    def _replace_fields(cls, text: str, field_values: dict[str, Any]) -> tuple[str, int]:
        replaced = text
        replace_count = 0
        for key, value in field_values.items():
            value_str = str(value)
            variants = [f"{{{{{key}}}}}", f"{{{key}}}", f"<<{key}>>", f"【{key}】"]
            for token in variants:
                count = replaced.count(token)
                if count:
                    replaced = replaced.replace(token, value_str)
                    replace_count += count
        return replaced, replace_count

    @staticmethod
    def _default_output_path(file_path: str, suffix: str) -> str:
        base, ext = os.path.splitext(file_path)
        return f"{base}{suffix}{ext}"
