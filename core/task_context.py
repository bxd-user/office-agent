from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class TaskFile:
    """任务输入/输出文件描述。"""

    path: str
    file_type: str
    role: str = ""
    name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskArtifact:
    """任务执行过程中产生的中间产物或最终产物。"""

    name: str
    path: Optional[str] = None
    type: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskContext:
    """整个任务执行过程的共享上下文。

    设计原则：
    1. 所有 agent 共用同一个 ctx
    2. agent 通过读写 ctx 协作
    3. ctx 只保存状态，不放复杂业务逻辑
    """

    # =========================
    # 任务基础信息
    # =========================
    task_id: str
    instruction: str

    # =========================
    # 文件信息
    # =========================
    excel_path: Optional[str] = None
    word_path: Optional[str] = None
    output_path: Optional[str] = None

    input_files: List[TaskFile] = field(default_factory=list)
    output_files: List[TaskFile] = field(default_factory=list)

    # =========================
    # 执行阶段结果
    # =========================
    plan: Optional[List[Dict[str, Any]]] = None

    excel_data: Optional[Dict[str, Any]] = None
    word_structure: Optional[Dict[str, Any]] = None
    word_placeholders: Optional[List[str]] = None

    field_mapping: Optional[Dict[str, str]] = None
    replacements: Optional[Dict[str, str]] = None

    validation_result: Optional[Dict[str, Any]] = None

    # =========================
    # 运行状态
    # =========================
    current_step: str = ""
    status: str = "pending"
    error: Optional[str] = None

    # =========================
    # 日志 / 中间产物 / 扩展数据
    # =========================
    logs: List[str] = field(default_factory=list)
    artifacts: List[TaskArtifact] = field(default_factory=list)
    shared: Dict[str, Any] = field(default_factory=dict)

    # =========================
    # 基础方法
    # =========================
    def log(self, message: str) -> None:
        self.logs.append(message)

    def set_step(self, step_name: str) -> None:
        self.current_step = step_name
        self.log(f"[step] {step_name}")

    def set_status(self, status: str) -> None:
        self.status = status
        self.log(f"[status] {status}")

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = "failed"
        self.log(f"[error] {error}")

    def add_input_file(
        self,
        path: str,
        file_type: str,
        role: str = "",
        name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.input_files.append(
            TaskFile(
                path=path,
                file_type=file_type,
                role=role,
                name=name,
                metadata=metadata or {},
            )
        )

    def add_output_file(
        self,
        path: str,
        file_type: str,
        role: str = "",
        name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.output_files.append(
            TaskFile(
                path=path,
                file_type=file_type,
                role=role,
                name=name,
                metadata=metadata or {},
            )
        )

    def add_artifact(
        self,
        name: str,
        path: Optional[str] = None,
        type: str = "",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.artifacts.append(
            TaskArtifact(
                name=name,
                path=path,
                type=type,
                description=description,
                metadata=metadata or {},
            )
        )

    @staticmethod
    def _as_dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        return value if isinstance(value, list) else []

    def get_excel_headers(self) -> List[str]:
        data = self._as_dict(self.excel_data)
        headers = self._as_list(data.get("headers", []))
        return [str(item) for item in headers]

    def get_excel_records(self) -> List[Dict[str, Any]]:
        data = self._as_dict(self.excel_data)
        records = self._as_list(data.get("records", []))
        return [record for record in records if isinstance(record, dict)]

    def get_first_excel_record(self) -> Dict[str, Any]:
        records = self.get_excel_records()
        return records[0] if records else {}

    def get_word_placeholders(self) -> List[str]:
        direct = self._as_list(self.word_placeholders)
        if direct:
            return [str(item) for item in direct]

        structure = self._as_dict(self.word_structure)
        placeholders = self._as_list(structure.get("placeholders", []))
        return [str(item) for item in placeholders]

    def build_summary(self) -> Dict[str, Any]:
        """返回一个适合调试/接口返回的摘要。"""
        return {
            "task_id": self.task_id,
            "instruction": self.instruction,
            "status": self.status,
            "current_step": self.current_step,
            "excel_path": self.excel_path,
            "word_path": self.word_path,
            "output_path": self.output_path,
            "excel_headers": self.get_excel_headers(),
            "word_placeholders": self.get_word_placeholders(),
            "field_mapping": self.field_mapping,
            "validation_result": self.validation_result,
            "error": self.error,
            "artifact_count": len(self.artifacts),
            "log_count": len(self.logs),
        }