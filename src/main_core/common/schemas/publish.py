"""L8 runtime publish bundle schema."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self

from pydantic import Field, model_validator

from main_core.common.schemas.base import FormalObjectBase
from main_core.common.types import CycleId


class ManifestReference(FormalObjectBase):
    """Typed manifest anchor embedded in a publish bundle candidate."""

    cycle_id: CycleId
    manifest_ref: str
    object_refs: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_manifest_anchor(self) -> Self:
        """Require the manifest anchor and referenced formal object refs to be present."""

        if not self.manifest_ref.strip():
            raise ValueError("manifest_ref must be non-empty")
        if not self.object_refs:
            raise ValueError("object_refs must not be empty")
        return self


class PublishBundle(FormalObjectBase):
    """Runtime Phase 3 publish bundle described in §9.3."""

    cycle_id: CycleId
    formal_objects: dict[str, Any]
    manifest_candidate: dict[str, Any]
    audit_payload: dict[str, Any]
    retrospective_seed: dict[str, Any]

    @model_validator(mode="after")
    def validate_cycle_and_manifest_consistency(self) -> Self:
        """Validate same-cycle anchors when a manifest candidate is present."""

        _ensure_optional_cycle("manifest_candidate", self.manifest_candidate, self.cycle_id)
        _ensure_optional_cycle("audit_payload", self.audit_payload, self.cycle_id)
        _ensure_optional_cycle(
            "retrospective_seed",
            self.retrospective_seed,
            self.cycle_id,
        )

        manifest_ref = self.manifest_candidate.get("manifest_ref")
        object_refs = self.manifest_candidate.get("object_refs")
        if manifest_ref is None and object_refs is None:
            return self
        if object_refs is not None and self.manifest_candidate.get("cycle_id") is None:
            raise ValueError(
                "manifest_candidate.cycle_id must be set when object_refs is present"
            )
        if manifest_ref is not None and self.manifest_candidate.get("cycle_id") is None:
            raise ValueError(
                "manifest_candidate.cycle_id must be set when manifest_ref is present"
            )
        if object_refs is None:
            raise ValueError(
                "manifest_candidate.object_refs must be set when manifest_ref is present"
            )
        if not isinstance(object_refs, Mapping):
            raise ValueError("manifest_candidate.object_refs must be a mapping")
        manifest_ref = ManifestReference.model_validate(
            {
                "cycle_id": self.manifest_candidate.get("cycle_id"),
                "manifest_ref": self.manifest_candidate.get("manifest_ref"),
                "object_refs": dict(object_refs),
            }
        )
        for object_key, expected_ref in manifest_ref.object_refs.items():
            entry = self.formal_objects.get(object_key)
            if not isinstance(entry, Mapping):
                raise ValueError(
                    f"manifest_candidate.object_refs contains missing {object_key}"
                )
            actual_ref = entry.get("ref")
            if actual_ref != expected_ref:
                raise ValueError(f"{object_key}.ref must match manifest_candidate")
        return self


def _ensure_optional_cycle(
    payload_name: str,
    payload: Mapping[str, Any],
    cycle_id: CycleId,
) -> None:
    payload_cycle_id = payload.get("cycle_id")
    if payload_cycle_id is not None and payload_cycle_id != str(cycle_id):
        raise ValueError(f"{payload_name}.cycle_id must match")


__all__ = ["ManifestReference", "PublishBundle"]
