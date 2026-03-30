from __future__ import annotations

import os

from app.agent.execution_context import ExecutionContext
from app.agent.schemas.action import ActionObservation, ActionStep
from app.document.service import DocumentService


class WriteOutputHandler:
    def __init__(self) -> None:
        self.document_service = DocumentService()

    def handle(self, step: ActionStep, file_resolver, context: ExecutionContext) -> ActionObservation:
        call_params = dict(step.params or {})
        file_info = self._resolve_source_file(step, file_resolver, context, call_params)
        if file_info is None:
            return ActionObservation(
                step_id=step.id,
                success=False,
                message="WRITE requires target_file_id or input_file_ids",
            )

        result = self.document_service.write(
            file_path=file_info["path"],
            filename=file_info.get("filename"),
            **call_params,
        )

        produced_file_ids: list[str] = []
        if result.output_path:
            produced_file_ids.append(result.output_path)

        return ActionObservation(
            step_id=step.id,
            success=result.success,
            message=result.message,
            data=result.data | {"output_path": result.output_path},
            produced_file_ids=produced_file_ids,
            raw=result.raw,
        )

    @staticmethod
    def _resolve_source_file(step: ActionStep, file_resolver, context: ExecutionContext, call_params: dict) -> dict | None:
        artifact_ref = call_params.pop("source_from_artifact", None)
        if artifact_ref:
            artifact = context.get_artifact(str(artifact_ref))
            if artifact is not None and isinstance(artifact.value, str) and artifact.value:
                return {"path": artifact.value, "filename": os.path.basename(artifact.value)}

        has_explicit_write_payload = any(
            bool(call_params.get(key))
            for key in ("append_text", "replacements", "field_values")
        )
        if not has_explicit_write_payload:
            refs = context.state.intermediate_refs if hasattr(context.state, "intermediate_refs") else {}
            output_paths = refs.get("output_file_paths", []) if isinstance(refs, dict) else []
            if isinstance(output_paths, list) and output_paths:
                latest = output_paths[-1]
                if isinstance(latest, str) and latest:
                    return {"path": latest, "filename": os.path.basename(latest)}

        file_id = step.target_file_id or (step.input_file_ids[0] if step.input_file_ids else None)
        if not file_id:
            return None
        return file_resolver(file_id)
