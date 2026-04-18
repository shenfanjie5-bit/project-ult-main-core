"""L8 runtime publish bundle schema."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import Field, model_validator

from main_core.common.json_like import to_plain_json_like
from main_core.common.schemas.base import FormalObjectBase
from main_core.common.types import CycleId


class ManifestReference(FormalObjectBase):
    """Typed manifest anchor embedded in final publish bundles."""

    cycle_id: CycleId
    object_refs: dict[str, str]
    manifest_ref: str
    committed_objects: list[dict[str, Any]] = Field(default_factory=list)
    manifest_version: str | None = None
    table_snapshots: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_manifest_reference(self) -> ManifestReference:
        """Require non-empty manifest and object refs."""

        if not self.manifest_ref.strip():
            raise ValueError("manifest_ref must be non-empty")
        if not self.object_refs:
            raise ValueError("object_refs must be non-empty when manifest_ref is present")
        blank_object_keys = [
            object_key
            for object_key, object_ref in self.object_refs.items()
            if not object_key.strip() or not object_ref.strip()
        ]
        if blank_object_keys:
            raise ValueError("object_refs keys and values must be non-empty")
        return self


class PublishBundle(FormalObjectBase):
    """Runtime Phase 3 publish bundle described in §9.3."""

    cycle_id: CycleId
    formal_objects: dict[str, Any]
    manifest_candidate: dict[str, Any]
    audit_payload: dict[str, Any]
    retrospective_seed: dict[str, Any]

    @model_validator(mode="after")
    def validate_final_manifest_anchor(self) -> PublishBundle:
        """Require final bundles to anchor each formal object in the manifest."""

        if "manifest_ref" not in self.manifest_candidate:
            return self

        manifest = ManifestReference.model_validate(
            to_plain_json_like(self.manifest_candidate)
        )
        if manifest.cycle_id != self.cycle_id:
            raise ValueError("manifest_candidate.cycle_id must match bundle cycle_id")
        object_refs = dict(manifest.object_refs)
        formal_object_keys = set(self.formal_objects)
        manifest_object_keys = set(object_refs)
        if manifest_object_keys != formal_object_keys:
            raise ValueError(
                "manifest_candidate.object_refs must exactly match formal_objects"
            )

        for object_key, entry in self.formal_objects.items():
            if not isinstance(entry, Mapping):
                raise ValueError(f"{object_key} formal object entry must be a mapping")
            entry_ref = entry.get("ref")
            if not isinstance(entry_ref, str) or not entry_ref.strip():
                raise ValueError(f"{object_key}.ref must be a non-empty string")
            if entry_ref != object_refs[object_key]:
                raise ValueError(f"{object_key}.ref must match manifest object_refs")

        return self

__all__ = ["ManifestReference", "PublishBundle"]
