"""Manifest-backed formal object commit helpers for L8 publication."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from main_core.common.errors import ManifestPublishError
from main_core.common.schemas import FormalObjectBase
from main_core.common.types import CycleId
from main_core.l8_publish.publish_port import (
    CommittedFormalObject,
    DataPlatformPublishPort,
    FormalObjectValue,
    ManifestWriteResult,
)
from main_core.l8_publish.refs import CANONICAL_FORMAL_OBJECT_KEYS


def commit_formal_objects(
    cycle_id: CycleId,
    formal_objects: Mapping[str, FormalObjectValue],
    publish_port: DataPlatformPublishPort,
) -> tuple[CommittedFormalObject, ...]:
    """Commit formal object classes in stable order before manifest publication."""

    committed_objects: list[CommittedFormalObject] = []
    for object_key in _ordered_object_keys(formal_objects):
        payload = _commit_payload(formal_objects[object_key])
        try:
            committed_object = publish_port.commit_formal_object(
                cycle_id=cycle_id,
                object_key=object_key,
                payload=payload,
            )
        except ManifestPublishError:
            raise
        except Exception as exc:
            raise ManifestPublishError(
                f"failed to commit formal object {object_key}",
            ) from exc

        if committed_object.object_key != object_key:
            raise ManifestPublishError(
                f"commit result object_key mismatch for {object_key}",
            )
        committed_objects.append(committed_object)

    return tuple(committed_objects)


def write_manifest_after_commits(
    cycle_id: CycleId,
    committed_objects: Sequence[CommittedFormalObject],
    publish_port: DataPlatformPublishPort,
) -> ManifestWriteResult:
    """Write the cycle manifest only after all formal object commits succeed."""

    try:
        return publish_port.write_cycle_manifest(
            cycle_id=cycle_id,
            committed_objects=tuple(committed_objects),
        )
    except ManifestPublishError:
        raise
    except Exception as exc:
        raise ManifestPublishError("failed to write cycle publish manifest") from exc


def build_manifest_candidate(
    cycle_id: CycleId,
    committed_objects: Sequence[CommittedFormalObject],
    manifest: ManifestWriteResult | None = None,
) -> dict[str, Any]:
    """Build the manifest candidate embedded in the returned publish bundle."""

    candidate: dict[str, Any] = {
        "cycle_id": str(cycle_id),
        "object_refs": {
            committed.object_key: committed.ref
            for committed in committed_objects
        },
        "committed_objects": [
            {
                "object_key": committed.object_key,
                "ref": committed.ref,
                "snapshot_id": committed.snapshot_id,
                "payload_hash": committed.payload_hash,
                "row_count": committed.row_count,
            }
            for committed in committed_objects
        ],
    }
    if manifest is not None:
        candidate.update(
            {
                "manifest_ref": manifest.manifest_ref,
                "manifest_version": manifest.manifest_version,
                "table_snapshots": dict(manifest.table_snapshots),
            }
        )
    return candidate


def _ordered_object_keys(formal_objects: Mapping[str, FormalObjectValue]) -> tuple[str, ...]:
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


def _commit_payload(value: FormalObjectValue) -> Mapping[str, Any]:
    if isinstance(value, FormalObjectBase):
        return value.model_dump(mode="json")

    payload_items = [
        item.model_dump(mode="json")
        for item in value
    ]
    return {"items": payload_items, "count": len(payload_items)}


__all__ = [
    "build_manifest_candidate",
    "commit_formal_objects",
    "write_manifest_after_commits",
]
