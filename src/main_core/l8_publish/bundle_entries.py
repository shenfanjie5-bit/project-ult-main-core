"""Shared helpers for ordered L8 formal object bundle entries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from main_core.common.errors import ManifestPublishError
from main_core.common.schemas import FormalObjectBase, PublishBundle
from main_core.common.types import CycleId
from main_core.l8_publish.publish_port import FormalObjectValue
from main_core.l8_publish.refs import CANONICAL_FORMAL_OBJECT_KEYS

PayloadShape = Literal["mapping", "list"]
MIN_CANONICAL_REF_PARTS = 2
_MISSING = object()


@dataclass(frozen=True)
class FormalObjectEntry:
    """Validated entry from a PublishBundle.formal_objects mapping."""

    ref: str
    payload: Mapping[str, Any] | tuple[Mapping[str, Any], ...]
    count: int


def ordered_formal_object_keys(formal_objects: Mapping[str, object]) -> tuple[str, ...]:
    """Return canonical L4-L7 keys first, followed by derived keys in insertion order."""

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


def build_bundle_formal_object_entry(
    value: FormalObjectValue,
    ref: str,
) -> dict[str, Any]:
    """Build the canonical PublishBundle.formal_objects entry for one object key."""

    payload = _bundle_payload(value)
    return {
        "ref": ref,
        "payload": payload,
        "count": len(payload) if isinstance(payload, list) else 1,
    }


def parse_bundle_formal_object_entry(
    bundle: PublishBundle,
    object_key: str,
    cycle_id: CycleId,
    *,
    payload_shape: PayloadShape,
) -> FormalObjectEntry:
    """Validate and parse one committed formal object entry from a publish bundle."""

    if bundle.cycle_id != cycle_id:
        raise ManifestPublishError("publish bundle cycle_id must match requested cycle_id")

    entry = _entry_mapping(bundle, object_key)
    ref = _entry_ref(entry, object_key)
    validate_formal_object_ref_cycle(object_key, ref, cycle_id)

    if payload_shape == "mapping":
        return _mapping_entry(entry, object_key, ref, cycle_id)
    return _list_entry(entry, object_key, ref, cycle_id)


def validate_formal_object_ref_cycle(
    object_key: str,
    ref: str,
    cycle_id: CycleId,
) -> None:
    """Require the canonical object ref shape to include the exact requested cycle."""

    parts = ref.split("/")
    if (
        len(parts) < MIN_CANONICAL_REF_PARTS
        or parts[0] != object_key
        or parts[1] != str(cycle_id)
    ):
        raise ManifestPublishError(f"{object_key}.ref must point to requested cycle_id")


def _bundle_payload(value: FormalObjectValue) -> dict[str, Any] | list[dict[str, Any]]:
    if isinstance(value, FormalObjectBase):
        return value.model_dump(mode="json")
    return [
        item.model_dump(mode="json")
        for item in value
    ]


def _mapping_entry(
    entry: Mapping[str, Any],
    object_key: str,
    ref: str,
    cycle_id: CycleId,
) -> FormalObjectEntry:
    payload = entry.get("payload", _MISSING)
    if not isinstance(payload, Mapping):
        raise ManifestPublishError(f"{object_key}.payload must be a mapping")

    count = _entry_count(entry, object_key)
    if count != 1:
        raise ManifestPublishError(f"{object_key}.count must be 1")
    _ensure_payload_cycle(object_key, payload, cycle_id)
    return FormalObjectEntry(ref=ref, payload=dict(payload), count=count)


def _list_entry(
    entry: Mapping[str, Any],
    object_key: str,
    ref: str,
    cycle_id: CycleId,
) -> FormalObjectEntry:
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


def _entry_mapping(bundle: PublishBundle, object_key: str) -> Mapping[str, Any]:
    try:
        entry = bundle.formal_objects[object_key]
    except KeyError as exc:
        raise ManifestPublishError(f"missing formal object entry {object_key}") from exc
    if not isinstance(entry, Mapping):
        raise ManifestPublishError(f"{object_key} formal object entry must be a mapping")
    return entry


def _entry_ref(entry: Mapping[str, Any], object_key: str) -> str:
    if "refs" in entry:
        refs = entry["refs"]
        if (
            isinstance(refs, Sequence)
            and not isinstance(refs, (str, bytes))
            and all(isinstance(ref, str) for ref in refs)
        ):
            if len(refs) == 1:
                return refs[0]
            raise ManifestPublishError(f"{object_key} must expose exactly one formal ref")
        raise ManifestPublishError(f"{object_key}.refs must be a sequence of strings")

    ref = entry.get("ref")
    if not isinstance(ref, str) or not ref:
        raise ManifestPublishError(f"{object_key}.ref must be a non-empty string")
    return ref


def _entry_count(entry: Mapping[str, Any], object_key: str) -> int:
    count = entry.get("count", _MISSING)
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ManifestPublishError(f"{object_key}.count must be a non-negative integer")
    return count


def _ensure_payload_cycle(
    object_key: str,
    payload: Mapping[str, Any],
    cycle_id: CycleId,
) -> None:
    if payload.get("cycle_id") != str(cycle_id):
        raise ManifestPublishError(f"{object_key}.payload cycle_id must match")


__all__ = [
    "FormalObjectEntry",
    "build_bundle_formal_object_entry",
    "ordered_formal_object_keys",
    "parse_bundle_formal_object_entry",
    "validate_formal_object_ref_cycle",
]
