from __future__ import annotations

from typing import Any

from app.agent.schemas.action import ActionPlan, ActionStep
from app.domain.document_types import DocumentType, detect_document_type


ALLOWED_ACTIONS = {
    "read",
    "extract",
    "locate",
    "fill",
    "compare",
    "validate",
    "write",
    "summarize",
}


class Planner:
    """
    能力层 Planner：
    - 综合 user prompt + 文件列表 + 文件类型/数量 + 历史上下文
    - 输出统一 action 命名的结构化步骤
    - 仅规划到 capability 层，不下沉到实现文件
    """

    def build_plan(
        self,
        user_request: str,
        files: list[dict[str, Any]],
        capabilities: dict[str, Any] | None = None,
        history_context: dict[str, Any] | None = None,
    ) -> ActionPlan:
        capabilities = capabilities or {}
        resolved_history_context: dict[str, Any] = history_context or capabilities.get("history_context") or {}

        file_facts = self._analyze_files(files)
        task_type = self._infer_task_type(
            user_request=user_request,
            file_facts=file_facts,
            history_context=resolved_history_context,
        )

        if task_type == "single_document_summary":
            steps = self._plan_single_document_summary(files=files)
        elif task_type == "excel_to_word_fill":
            steps = self._plan_excel_to_word_fill(files=files)
        elif task_type == "multi_document_compare":
            steps = self._plan_multi_document_compare(files=files)
        elif task_type == "template_scan_locate_fill":
            steps = self._plan_template_scan_locate_fill(files=files)
        else:
            steps = self._plan_extract_structured_fields(files=files)

        self._validate_actions(steps)
        return ActionPlan(
            steps=steps,
            metadata={
                "planner": "capability_planner_v1",
                "task_type": task_type,
                "inputs": {
                    "file_count": len(files),
                    "file_types": file_facts["types"],
                    "has_history_context": bool(resolved_history_context),
                },
            },
        )

    def _analyze_files(self, files: list[dict[str, Any]]) -> dict[str, Any]:
        types: dict[str, int] = {}
        typed_files: list[dict[str, Any]] = []

        for file_info in files:
            filename = str(file_info.get("filename") or "")
            doc_type = detect_document_type(filename=filename)
            types[doc_type.value] = types.get(doc_type.value, 0) + 1
            typed_files.append({
                "file_id": file_info.get("file_id"),
                "filename": filename,
                "doc_type": doc_type.value,
            })

        return {
            "types": types,
            "typed_files": typed_files,
            "count": len(files),
        }

    def _infer_task_type(
        self,
        user_request: str,
        file_facts: dict[str, Any],
        history_context: dict[str, Any],
    ) -> str:
        text = user_request.lower()
        types = file_facts["types"]
        file_count = file_facts["count"]

        history_hint = str(history_context.get("last_task_type") or "").lower()

        has_excel = types.get(DocumentType.EXCEL.value, 0) > 0
        has_word = types.get(DocumentType.WORD.value, 0) > 0

        if "compare" in text or "对比" in text or "比较" in text:
            return "multi_document_compare"

        if has_excel and has_word and (
            "填" in text
            or "fill" in text
            or "映射" in text
            or "template" in text
            or history_hint == "excel_to_word_fill"
        ):
            return "excel_to_word_fill"

        if (
            "template" in text
            or "模板" in text
            or "扫描" in text
            or "locate" in text
            or "定位" in text
        ) and (has_word or has_excel):
            return "template_scan_locate_fill"

        if file_count == 1 and ("总结" in text or "summary" in text or "summarize" in text):
            return "single_document_summary"

        if file_count >= 2 and history_hint == "multi_document_compare":
            return "multi_document_compare"

        return "extract_structured_fields"

    def _plan_single_document_summary(self, files: list[dict[str, Any]]) -> list[ActionStep]:
        if not files:
            return []

        file_id = files[0]["file_id"]
        return [
            ActionStep(
                id="step_read",
                action_type="read",
                input_file_ids=[file_id],
                params={"need_validation": False},
                expected_output={"kind": "document_content"},
                depends_on=[],
                allow_retry=True,
            ),
            ActionStep(
                id="step_summarize",
                action_type="summarize",
                input_file_ids=[file_id],
                params={"source": "step_read", "need_validation": False},
                expected_output={"kind": "summary_text"},
                depends_on=["step_read"],
                allow_retry=True,
            ),
        ]

    def _plan_excel_to_word_fill(self, files: list[dict[str, Any]]) -> list[ActionStep]:
        excel = self._first_file_by_type(files, DocumentType.EXCEL)
        word = self._first_file_by_type(files, DocumentType.WORD)
        if not excel or not word:
            return self._plan_extract_structured_fields(files)

        return [
            ActionStep(
                id="step_read_excel",
                action_type="read",
                input_file_ids=[excel["file_id"]],
                params={"need_validation": False},
                expected_output={"kind": "excel_preview"},
                depends_on=[],
                allow_retry=True,
            ),
            ActionStep(
                id="step_extract_fields",
                action_type="extract",
                input_file_ids=[excel["file_id"]],
                params={"need_validation": False},
                expected_output={"kind": "structured_fields"},
                depends_on=["step_read_excel"],
                allow_retry=True,
            ),
            ActionStep(
                id="step_read_template",
                action_type="read",
                input_file_ids=[word["file_id"]],
                params={"need_validation": False},
                expected_output={"kind": "template_content"},
                depends_on=[],
                allow_retry=True,
            ),
            ActionStep(
                id="step_locate_targets",
                action_type="locate",
                input_file_ids=[word["file_id"]],
                params={"need_validation": False, "placeholder": "*"},
                expected_output={"kind": "fill_targets"},
                depends_on=["step_read_template"],
                allow_retry=True,
            ),
            ActionStep(
                id="step_fill",
                action_type="fill",
                target_file_id=word["file_id"],
                params={
                    "source_fields_from": "step_extract_fields",
                    "targets_from": "step_locate_targets",
                    "need_validation": True,
                },
                expected_output={"kind": "filled_document"},
                depends_on=["step_extract_fields", "step_locate_targets"],
                allow_retry=True,
            ),
            ActionStep(
                id="step_validate",
                action_type="validate",
                target_file_id=word["file_id"],
                params={"source": "step_fill", "need_validation": True},
                expected_output={"kind": "validation_report"},
                depends_on=["step_fill"],
                allow_retry=True,
            ),
            ActionStep(
                id="step_write",
                action_type="write",
                target_file_id=word["file_id"],
                params={"source": "step_fill", "need_validation": False},
                expected_output={"kind": "output_file"},
                depends_on=["step_validate"],
                allow_retry=True,
            ),
        ]

    def _plan_multi_document_compare(self, files: list[dict[str, Any]]) -> list[ActionStep]:
        if len(files) < 2:
            return self._plan_extract_structured_fields(files)

        left = files[0]
        right = files[1]
        return [
            ActionStep(
                id="step_read_left",
                action_type="read",
                input_file_ids=[left["file_id"]],
                params={"need_validation": False},
                expected_output={"kind": "left_content"},
                depends_on=[],
                allow_retry=True,
            ),
            ActionStep(
                id="step_read_right",
                action_type="read",
                input_file_ids=[right["file_id"]],
                params={"need_validation": False},
                expected_output={"kind": "right_content"},
                depends_on=[],
                allow_retry=True,
            ),
            ActionStep(
                id="step_compare",
                action_type="compare",
                input_file_ids=[left["file_id"], right["file_id"]],
                params={"need_validation": True},
                expected_output={"kind": "comparison_result"},
                depends_on=["step_read_left", "step_read_right"],
                allow_retry=True,
            ),
            ActionStep(
                id="step_summarize_compare",
                action_type="summarize",
                input_file_ids=[left["file_id"], right["file_id"]],
                params={"source": "step_compare", "need_validation": False},
                expected_output={"kind": "comparison_summary"},
                depends_on=["step_compare"],
                allow_retry=True,
            ),
        ]

    def _plan_template_scan_locate_fill(self, files: list[dict[str, Any]]) -> list[ActionStep]:
        if not files:
            return []

        target = self._first_file_by_type(files, DocumentType.WORD) or files[0]
        target_id = target["file_id"]
        return [
            ActionStep(
                id="step_read_template",
                action_type="read",
                input_file_ids=[target_id],
                params={"need_validation": False},
                expected_output={"kind": "template_content"},
                depends_on=[],
                allow_retry=True,
            ),
            ActionStep(
                id="step_extract_template_fields",
                action_type="extract",
                input_file_ids=[target_id],
                params={"mode": "template_fields", "need_validation": False},
                expected_output={"kind": "template_fields"},
                depends_on=["step_read_template"],
                allow_retry=True,
            ),
            ActionStep(
                id="step_locate_targets",
                action_type="locate",
                input_file_ids=[target_id],
                params={"source": "step_extract_template_fields", "need_validation": False},
                expected_output={"kind": "fill_targets"},
                depends_on=["step_extract_template_fields"],
                allow_retry=True,
            ),
            ActionStep(
                id="step_fill",
                action_type="fill",
                target_file_id=target_id,
                params={"source": "step_locate_targets", "need_validation": True},
                expected_output={"kind": "filled_document"},
                depends_on=["step_locate_targets"],
                allow_retry=True,
            ),
            ActionStep(
                id="step_validate",
                action_type="validate",
                target_file_id=target_id,
                params={"source": "step_fill", "need_validation": True},
                expected_output={"kind": "validation_report"},
                depends_on=["step_fill"],
                allow_retry=True,
            ),
            ActionStep(
                id="step_write",
                action_type="write",
                target_file_id=target_id,
                params={"source": "step_fill", "need_validation": False},
                expected_output={"kind": "output_file"},
                depends_on=["step_validate"],
                allow_retry=True,
            ),
        ]

    def _plan_extract_structured_fields(self, files: list[dict[str, Any]]) -> list[ActionStep]:
        if not files:
            return []

        first = files[0]
        file_id = first["file_id"]
        return [
            ActionStep(
                id="step_read",
                action_type="read",
                input_file_ids=[file_id],
                params={"need_validation": False},
                expected_output={"kind": "document_content"},
                depends_on=[],
                allow_retry=True,
            ),
            ActionStep(
                id="step_extract",
                action_type="extract",
                input_file_ids=[file_id],
                params={"need_validation": False},
                expected_output={"kind": "structured_fields"},
                depends_on=["step_read"],
                allow_retry=True,
            ),
            ActionStep(
                id="step_validate",
                action_type="validate",
                input_file_ids=[file_id],
                params={"source": "step_extract", "need_validation": True},
                expected_output={"kind": "validation_report"},
                depends_on=["step_extract"],
                allow_retry=True,
            ),
        ]

    @staticmethod
    def _first_file_by_type(files: list[dict[str, Any]], doc_type: DocumentType) -> dict[str, Any] | None:
        for file_info in files:
            filename = str(file_info.get("filename") or "")
            if detect_document_type(filename=filename) == doc_type:
                return file_info
        return None

    @staticmethod
    def _validate_actions(steps: list[ActionStep]) -> None:
        invalid = [step.action_type for step in steps if step.action_type not in ALLOWED_ACTIONS]
        if invalid:
            raise ValueError(f"Planner generated unsupported actions: {invalid}")


# 向后兼容旧名称
PlannerV2Compatible = Planner
