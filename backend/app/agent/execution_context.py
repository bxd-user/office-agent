from __future__ import annotations

from typing import Any

from app.agent.schemas.action import ActionObservation, ExecutionArtifact, ExecutionState


class ExecutionContext:
    def __init__(self) -> None:
        self.state = ExecutionState()

    def add_observation(self, observation: ActionObservation) -> None:
        self.state.add_observation(observation)

    def get_observation(self, step_id: str) -> ActionObservation | None:
        return self.state.get_observation(step_id)

    def add_artifact(self, name: str, artifact_type: str, value: Any, source_step_id: str | None = None) -> None:
        artifact = ExecutionArtifact(
            name=name,
            type=artifact_type,
            value=value,
            source_step_id=source_step_id,
        )
        self.state.add_artifact(artifact)

    def get_artifact(self, name: str) -> ExecutionArtifact | None:
        return self.state.get_artifact(name)

    def require_artifact(self, name: str) -> ExecutionArtifact:
        artifact = self.get_artifact(name)
        if artifact is None:
            raise ValueError(f"Artifact not found: {name}")
        return artifact

    def export_debug_dict(self) -> dict[str, Any]:
        return {
            "state": {
                "current_step_id": self.state.current_step_id,
                "status": self.state.status,
                "error": self.state.error,
                "retry_count": dict(self.state.retry_count),
                "intermediate_refs": dict(self.state.intermediate_refs),
            },
            "observations": {k: v.model_dump() for k, v in self.state.observations.items()},
            "artifacts": {k: v.model_dump() for k, v in self.state.artifacts.items()},
        }