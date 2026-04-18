"""Shared L8 publish-bundle parsing utilities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from main_core.common.errors import ManifestPublishError
from main_core.common.schemas import PublishBundle
from main_core.common.types import CycleId
from main_core.l8_publish.publish_port import FormalObjectValue
from main_core.l8_publish.refs import CANONICAL_FORMAL_OBJECT_KEYS, formal_object_ref

MIN_CANONICAL_REF_PARTS = 3


@dataclass(frozen=True)
class FormalObjectEntry:
    """Typed publish-bundle entry after ref, payload, and count validation."""

    ref: str
    payload: Mapping[str, Any] | tuple[Mapping[str, Any], ...]
    count: int


def ordered_formal_object_keys(
    formal_objects: Mapping[str, FormalObjectValue],
) -> tuple[str, ...]:
    """Return canonical formal object keys before derived object keys."""

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


def parse_publish_bundle_entry(
    bundle: PublishBundle,
    object_key: str,
    cycle_id: CycleId,
    *,
    payload_shape: Literal["mapping", "list"],
) -> FormalObjectEntry:
    """Validate and parse one typed formal object entry from a publish bundle."""

    entry = _entry_mapping(bundle, object_key)
    ref = formal_object_ref(bundle, object_key)
    ensure_formal_object_ref_matches_cycle(object_key, ref, cycle_id)
    payload = entry.get("payload", _MISSING)
    if payload_shape == "mapping":
        if not isinstance(payload, Mapping):
            raise ManifestPublishError(f"{object_key}.payload must be a mapping")
        count = _entry_count(entry, object_key)
        if count != 1:
            raise ManifestPublishError(f"{object_key}.count must be 1")
        _ensure_payload_cycle(object_key, payload, cycle_id)
        return FormalObjectEntry(ref=ref, payload=dict(payload), count=count)

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


def ensure_formal_object_ref_matches_cycle(
    object_key: str,
    ref: str,
    cycle_id: CycleId,
) -> None:
    """Validate the canonical object_key/cycle_id/ref shape exactly."""

    parts = ref.split("/")
    if (
        len(parts) < MIN_CANONICAL_REF_PARTS
        or parts[0] != object_key
        or parts[1] != str(cycle_id)
    ):
        raise ManifestPublishError(f"{object_key}.ref must point to requested cycle_id")


_MISSING = object()


def _entry_mapping(bundle: PublishBundle, object_key: str) -> Mapping[str, Any]:
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


__all__ = [
    "FormalObjectEntry",
    "ensure_formal_object_ref_matches_cycle",
    "ordered_formal_object_keys",
    "parse_publish_bundle_entry",
]
