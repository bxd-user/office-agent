from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class WorkingMemory:
    file_manifest: List[Dict[str, Any]] = field(default_factory=list)
    file_roles: Dict[str, str] = field(default_factory=dict)

    document_texts: Dict[str, str] = field(default_factory=dict)
    document_structures: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    table_views: Dict[str, Any] = field(default_factory=dict)

    extracted_fields: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    candidate_mappings: List[Dict[str, Any]] = field(default_factory=list)

    output_files: List[Dict[str, Any]] = field(default_factory=list)
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def remember_file_role(self, file_id: str, role: str) -> None:
        self.file_roles[file_id] = role

    def remember_text(self, file_id: str, text: str) -> None:
        self.document_texts[file_id] = text

    def remember_structure(self, file_id: str, structure: Dict[str, Any]) -> None:
        self.document_structures[file_id] = structure

    def remember_fields(self, file_id: str, fields: Dict[str, Any]) -> None:
        self.extracted_fields[file_id] = fields

    def add_output_file(self, output: Dict[str, Any]) -> None:
        self.output_files.append(output)

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)

    def add_note(self, note: str) -> None:
        self.notes.append(note)

    def mark_completed(self, step_id: str) -> None:
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)

    def mark_failed(self, step_id: str) -> None:
        if step_id not in self.failed_steps:
            self.failed_steps.append(step_id)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "file_manifest": self.file_manifest,
            "file_roles": self.file_roles,
            "document_texts": self.document_texts,
            "document_texts_keys": list(self.document_texts.keys()),
            "document_structures_keys": list(self.document_structures.keys()),
            "table_views_keys": list(self.table_views.keys()),
            "extracted_fields": self.extracted_fields,
            "candidate_mappings": self.candidate_mappings,
            "output_files": self.output_files,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "warnings": self.warnings,
            "notes": self.notes,
        }