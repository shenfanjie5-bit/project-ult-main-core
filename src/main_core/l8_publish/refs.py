"""Canonical formal object keys and ref readers for L8 publish bundles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from main_core.common.errors import ManifestPublishError
from main_core.common.schemas import PublishBundle
from main_core.common.types import CycleId

WORLD_STATE_SNAPSHOT_KEY = "world_state_snapshot"
OFFICIAL_ALPHA_POOL_KEY = "official_alpha_pool"
ALPHA_RESULT_SNAPSHOT_KEY = "alpha_result_snapshot"
RECOMMENDATION_SNAPSHOT_KEY = "recommendation_snapshot"

CANONICAL_FORMAL_OBJECT_KEYS: tuple[str, ...] = (
    WORLD_STATE_SNAPSHOT_KEY,
    OFFICIAL_ALPHA_POOL_KEY,
    ALPHA_RESULT_SNAPSHOT_KEY,
    RECOMMENDATION_SNAPSHOT_KEY,
)

_MISSING = object()


@dataclass(frozen=True)
class FormalObjectEntry:
    """Validated PublishBundle entry for one committed formal object key."""

    ref: str
    payload: Mapping[str, Any] | tuple[Mapping[str, Any], ...]
    count: int


def formal_object_ref(bundle: PublishBundle, object_key: str) -> str:
    """Return the single canonical ref for a formal object entry."""

    refs = formal_object_refs(bundle, object_key)
    if len(refs) != 1:
        raise ManifestPublishError(f"{object_key} must expose exactly one formal ref")
    return refs[0]


def formal_object_refs(bundle: PublishBundle, object_key: str) -> tuple[str, ...]:
    """Return formal refs from a bundle entry using the canonical ref shape."""

    entry = _formal_object_entry(bundle, object_key)
    return _entry_refs(object_key, entry)


def mapping_formal_object_entry(
    bundle: PublishBundle,
    object_key: str,
    cycle_id: CycleId,
) -> FormalObjectEntry:
    """Parse and validate a single-payload formal object bundle entry."""

    entry = _formal_object_entry(bundle, object_key)
    ref = formal_object_ref(bundle, object_key)
    _ensure_ref_points_to_cycle(f"{object_key}.ref", ref, cycle_id)
    payload = entry.get("payload", _MISSING)
    if not isinstance(payload, Mapping):
        raise ManifestPublishError(f"{object_key}.payload must be a mapping")

    count = _entry_count(entry, object_key)
    if count != 1:
        raise ManifestPublishError(f"{object_key}.count must be 1")
    _ensure_payload_cycle(object_key, payload, cycle_id)
    return FormalObjectEntry(ref=ref, payload=dict(payload), count=count)


def list_formal_object_entry(
    bundle: PublishBundle,
    object_key: str,
    cycle_id: CycleId,
) -> FormalObjectEntry:
    """Parse and validate a list-payload formal object bundle entry."""

    entry = _formal_object_entry(bundle, object_key)
    ref = formal_object_ref(bundle, object_key)
    _ensure_ref_points_to_cycle(f"{object_key}.ref", ref, cycle_id)
    payload = entry.get("payload", _MISSING)
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
        raise ManifestPublishError(f"{object_key}.payload must be a list")

    payload_items: list[Mapping[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, Mapping):
            raise ManifestPublishError(
                f"{object_key}.payload[{index}] must be a mapping"
            )
        _ensure_payload_cycle(object_key, item, cycle_id)
        payload_items.append(dict(item))

    count = _entry_count(entry, object_key)
    if count != len(payload_items):
        raise ManifestPublishError(f"{object_key}.count must match payload length")
    return FormalObjectEntry(ref=ref, payload=tuple(payload_items), count=count)


def ordered_formal_object_keys(formal_objects: Mapping[str, Any]) -> tuple[str, ...]:
    """Return canonical L8 formal object keys followed by derived keys."""

    canonical_keys = [
        object_key
        for object_key in CANONICAL_FORMAL_OBJECT_KEYS
        if object_key in formal_objects
    ]
    derived_keys = [
        object_key
        for object_key in formal_objects
        if object_key not in CANONICAL_FORMAL_OBJECT_KEYS
    ]
    return (*canonical_keys, *derived_keys)


def _entry_refs(object_key: str, entry: Mapping[str, Any]) -> tuple[str, ...]:
    if "refs" in entry:
        refs = entry["refs"]
        if (
            isinstance(refs, Sequence)
            and not isinstance(refs, (str, bytes))
            and all(isinstance(ref, str) and ref for ref in refs)
        ):
            return tuple(refs)
        raise ManifestPublishError(f"{object_key}.refs must be a sequence of strings")

    ref = entry.get("ref")
    if not isinstance(ref, str) or not ref:
        raise ManifestPublishError(f"{object_key}.ref must be a non-empty string")
    return (ref,)


def _formal_object_entry(
    bundle: PublishBundle,
    object_key: str,
) -> Mapping[str, Any]:
    try:
        entry = bundle.formal_objects[object_key]
    except KeyError as exc:
        raise ManifestPublishError(f"missing formal object entry {object_key}") from exc

    if not isinstance(entry, Mapping):
        raise ManifestPublishError(f"{object_key} formal object entry must be a mapping")
    return entry


def _entry_count(entry: Mapping[str, Any], object_key: str) -> int:
    count = entry.get("count", _MISSING)
    if (
        not isinstance(count, int)
        or isinstance(count, bool)
        or count < 0
    ):
        raise ManifestPublishError(f"{object_key}.count must be a non-negative integer")
    return count


def _ensure_payload_cycle(
    object_key: str,
    payload: Mapping[str, Any],
    cycle_id: CycleId,
) -> None:
    if payload.get("cycle_id") != str(cycle_id):
        raise ManifestPublishError(f"{object_key}.payload cycle_id must match")


def _ensure_ref_points_to_cycle(
    ref_name: str,
    ref: str,
    cycle_id: CycleId,
) -> None:
    if str(cycle_id) not in ref.split("/"):
        raise ManifestPublishError(f"{ref_name} must point to requested cycle_id")


__all__ = [
    "ALPHA_RESULT_SNAPSHOT_KEY",
    "CANONICAL_FORMAL_OBJECT_KEYS",
    "FormalObjectEntry",
    "OFFICIAL_ALPHA_POOL_KEY",
    "RECOMMENDATION_SNAPSHOT_KEY",
    "WORLD_STATE_SNAPSHOT_KEY",
    "formal_object_ref",
    "formal_object_refs",
    "list_formal_object_entry",
    "mapping_formal_object_entry",
    "ordered_formal_object_keys",
]
