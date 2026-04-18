"""L8 runtime publish bundle schema."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import model_validator

from main_core.common.schemas.base import FormalObjectBase
from main_core.common.types import CycleId


class PublishBundle(FormalObjectBase):
    """Runtime Phase 3 publish bundle described in §9.3."""

    cycle_id: CycleId
    formal_objects: dict[str, Any]
    manifest_candidate: dict[str, Any]
    audit_payload: dict[str, Any]
    retrospective_seed: dict[str, Any]

    @model_validator(mode="after")
    def validate_cycle_refs(self) -> PublishBundle:
        """Reject stale formal object and manifest object refs inside the bundle."""

        cycle_id = str(self.cycle_id)
        _ensure_optional_payload_cycle("manifest_candidate", self.manifest_candidate, cycle_id)

        formal_refs_by_key = _formal_refs_by_key(self.formal_objects, cycle_id)
        _validate_manifest_object_refs(
            self.manifest_candidate.get("object_refs"),
            formal_refs_by_key,
            cycle_id,
        )
        _validate_committed_object_refs(
            self.manifest_candidate.get("committed_objects"),
            cycle_id,
        )
        return self


def _formal_refs_by_key(
    formal_objects: Mapping[str, Any],
    cycle_id: str,
) -> dict[str, tuple[str, ...]]:
    formal_refs_by_key: dict[str, tuple[str, ...]] = {}
    for object_key, entry in formal_objects.items():
        if not isinstance(entry, Mapping):
            continue

        key = str(object_key)
        refs = _entry_refs(key, entry)
        if refs:
            formal_refs_by_key[key] = refs
        for ref in refs:
            _ensure_ref_has_cycle_segment(f"{key}.ref", ref, cycle_id)

        _ensure_payload_cycles(key, entry.get("payload"), cycle_id)
    return formal_refs_by_key


def _validate_manifest_object_refs(
    object_refs: Any,
    formal_refs_by_key: Mapping[str, tuple[str, ...]],
    cycle_id: str,
) -> None:
    if object_refs is None:
        return
    if not isinstance(object_refs, Mapping):
        raise ValueError("manifest_candidate.object_refs must be a mapping")
    for object_key, ref in object_refs.items():
        if not isinstance(ref, str) or not ref:
            raise ValueError("manifest object_ref values must be non-empty strings")
        key = str(object_key)
        _ensure_ref_has_cycle_segment(
            f"manifest_candidate.object_refs.{key}",
            ref,
            cycle_id,
        )
        matching_refs = formal_refs_by_key.get(key)
        if matching_refs is not None and ref not in matching_refs:
            raise ValueError(
                "manifest object_ref must match the formal_objects entry ref"
            )


def _validate_committed_object_refs(committed_objects: Any, cycle_id: str) -> None:
    if committed_objects is None:
        return
    if not isinstance(committed_objects, Sequence) or isinstance(
        committed_objects,
        (str, bytes),
    ):
        raise ValueError("manifest_candidate.committed_objects must be a list")
    for index, committed_object in enumerate(committed_objects):
        _validate_committed_object_ref(index, committed_object, cycle_id)


def _validate_committed_object_ref(
    index: int,
    committed_object: Any,
    cycle_id: str,
) -> None:
    if not isinstance(committed_object, Mapping):
        raise ValueError(
            f"manifest_candidate.committed_objects[{index}] must be a mapping"
        )
    ref = committed_object.get("ref")
    if ref is None:
        return
    if not isinstance(ref, str) or not ref:
        raise ValueError("committed object ref must be a non-empty string")
    _ensure_ref_has_cycle_segment(
        f"manifest_candidate.committed_objects[{index}].ref",
        ref,
        cycle_id,
    )


def _entry_refs(object_key: str, entry: Mapping[str, Any]) -> tuple[str, ...]:
    if "refs" in entry:
        refs = entry["refs"]
        if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes)):
            raise ValueError(f"{object_key}.refs must be a sequence of strings")
        if not all(isinstance(ref, str) and ref for ref in refs):
            raise ValueError(f"{object_key}.refs must contain non-empty strings")
        return tuple(refs)

    ref = entry.get("ref")
    if ref is None:
        return ()
    if not isinstance(ref, str) or not ref:
        raise ValueError(f"{object_key}.ref must be a non-empty string")
    return (ref,)


def _ensure_optional_payload_cycle(
    payload_name: str,
    payload: Mapping[str, Any],
    cycle_id: str,
) -> None:
    payload_cycle_id = payload.get("cycle_id")
    if payload_cycle_id is not None and payload_cycle_id != cycle_id:
        raise ValueError(f"{payload_name}.cycle_id must match bundle.cycle_id")


def _ensure_payload_cycles(object_key: str, payload: Any, cycle_id: str) -> None:
    if isinstance(payload, Mapping):
        _ensure_optional_payload_cycle(f"{object_key}.payload", payload, cycle_id)
        return

    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
        return
    for index, item in enumerate(payload):
        if isinstance(item, Mapping):
            _ensure_optional_payload_cycle(
                f"{object_key}.payload[{index}]",
                item,
                cycle_id,
            )


def _ensure_ref_has_cycle_segment(ref_name: str, ref: str, cycle_id: str) -> None:
    if cycle_id not in ref.split("/"):
        raise ValueError(f"{ref_name} must point to bundle.cycle_id")


__all__ = ["PublishBundle"]
