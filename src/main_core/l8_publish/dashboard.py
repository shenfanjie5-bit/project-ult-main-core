"""Formal dashboard snapshot builders for L8 publication."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from main_core.common.errors import ManifestPublishError
from main_core.common.schemas import DashboardSnapshot, PublishBundle
from main_core.common.types import CycleId
from main_core.l8_publish.bundle_entries import (
    FormalObjectEntry,
    parse_bundle_formal_object_entry,
)
from main_core.l8_publish.refs import (
    ALPHA_RESULT_SNAPSHOT_KEY,
    OFFICIAL_ALPHA_POOL_KEY,
    RECOMMENDATION_SNAPSHOT_KEY,
    WORLD_STATE_SNAPSHOT_KEY,
)

DASHBOARD_SNAPSHOT_KEY = "dashboard_snapshot"

_ACTION_TYPES = ("buy", "hold", "reduce", "inconclusive")


@dataclass(frozen=True)
class _RequiredFormalObjects:
    world_state: FormalObjectEntry
    pool: FormalObjectEntry
    alpha_results: FormalObjectEntry
    recommendations: FormalObjectEntry


def build_dashboard_snapshot(
    cycle_id: CycleId,
    bundle: PublishBundle,
) -> DashboardSnapshot:
    """Build the formal dashboard snapshot from same-cycle published refs."""

    requested_cycle_id = CycleId(str(cycle_id))
    objects = _extract_required_formal_objects(requested_cycle_id, bundle)
    summary_cards = _build_summary_cards(objects)

    return DashboardSnapshot(
        cycle_id=requested_cycle_id,
        world_state_ref=objects.world_state.ref,
        pool_ref=objects.pool.ref,
        recommendation_ref=objects.recommendations.ref,
        summary_cards=summary_cards,
    )


def _extract_required_formal_objects(
    cycle_id: CycleId,
    bundle: PublishBundle,
) -> _RequiredFormalObjects:
    return _RequiredFormalObjects(
        world_state=parse_bundle_formal_object_entry(
            bundle,
            WORLD_STATE_SNAPSHOT_KEY,
            cycle_id,
            payload_shape="mapping",
        ),
        pool=parse_bundle_formal_object_entry(
            bundle,
            OFFICIAL_ALPHA_POOL_KEY,
            cycle_id,
            payload_shape="mapping",
        ),
        alpha_results=parse_bundle_formal_object_entry(
            bundle,
            ALPHA_RESULT_SNAPSHOT_KEY,
            cycle_id,
            payload_shape="list",
        ),
        recommendations=parse_bundle_formal_object_entry(
            bundle,
            RECOMMENDATION_SNAPSHOT_KEY,
            cycle_id,
            payload_shape="list",
        ),
    )


def _build_summary_cards(objects: _RequiredFormalObjects) -> dict[str, Any]:
    world_state = _as_mapping(objects.world_state.payload)
    pool = _as_mapping(objects.pool.payload)
    alpha_results = _as_payload_list(objects.alpha_results.payload)
    recommendations = _as_payload_list(objects.recommendations.payload)

    by_action = dict.fromkeys(_ACTION_TYPES, 0)
    override_entity_ids: list[str] = []
    inconclusive_recommendation_entity_ids: list[str] = []
    for recommendation in recommendations:
        action_type = str(recommendation.get("action_type", ""))
        by_action[action_type] = by_action.get(action_type, 0) + 1
        if recommendation.get("override_applied") is True:
            override_entity_ids.append(str(recommendation.get("entity_id", "")))
        if action_type == "inconclusive":
            inconclusive_recommendation_entity_ids.append(
                str(recommendation.get("entity_id", ""))
            )

    alpha_inconclusive_entity_ids = [
        str(alpha_result.get("entity_id", ""))
        for alpha_result in alpha_results
        if alpha_result.get("status") == "inconclusive"
    ]
    selected_entities = _string_list(pool.get("selected_entities", []))
    added_entities = _string_list(pool.get("added_entities", []))
    removed_entities = _string_list(pool.get("removed_entities", []))
    freeze_reason_map = pool.get("freeze_reason_map", {})
    frozen_count = len(freeze_reason_map) if isinstance(freeze_reason_map, Mapping) else 0
    override_applied_count = len(override_entity_ids)

    return {
        "regime": {
            "baseline_regime": world_state.get("baseline_regime"),
            "llm_delta": world_state.get("llm_delta"),
            "final_regime": world_state.get("final_regime"),
            "llm_rationale": world_state.get("llm_rationale"),
            "actual_model_used": world_state.get("actual_model_used"),
            "actual_provider": world_state.get("actual_provider"),
        },
        "pool": {
            "selected_count": len(selected_entities),
            "capacity": pool.get("official_alpha_pool_capacity"),
            "added_count": len(added_entities),
            "removed_count": len(removed_entities),
            "observation_pool_size": pool.get("observation_pool_size"),
            "frozen_count": frozen_count,
        },
        "recommendations": {
            "total_count": len(recommendations),
            "by_action": by_action,
            "override_applied_count": override_applied_count,
        },
        "inconclusive": {
            "alpha_count": len(alpha_inconclusive_entity_ids),
            "recommendation_count": by_action.get("inconclusive", 0),
            "alpha_entity_ids": alpha_inconclusive_entity_ids,
            "recommendation_entity_ids": inconclusive_recommendation_entity_ids,
        },
        "overrides": {
            "override_applied_count": override_applied_count,
            "entity_ids": override_entity_ids,
        },
    }


def _as_mapping(
    payload: Mapping[str, Any] | tuple[Mapping[str, Any], ...],
) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ManifestPublishError("expected single formal object payload")
    return payload


def _as_payload_list(
    payload: Mapping[str, Any] | tuple[Mapping[str, Any], ...],
) -> tuple[Mapping[str, Any], ...]:
    if isinstance(payload, Mapping):
        raise ManifestPublishError("expected formal object payload list")
    return payload


def _string_list(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [str(item) for item in value]


__all__ = ["DASHBOARD_SNAPSHOT_KEY", "build_dashboard_snapshot"]
