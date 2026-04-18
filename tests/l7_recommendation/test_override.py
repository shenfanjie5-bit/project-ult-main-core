"""Tests for L7 human override handling."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from main_core.common.errors import MainCoreError
from main_core.common.schemas import (
    AlphaResultSnapshot,
    OfficialAlphaPool,
    OverrideRecord,
    RecommendationSnapshot,
    WorldStateSnapshot,
)
from main_core.l7_recommendation import (
    InMemoryOverrideStore,
    apply_override,
    find_override,
    generate_recommendations,
    rating_for_action,
    submit_override,
)


def _override_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "cycle_id": "cycle_l7",
        "entity_id": "ENT_A",
        "submitted_by": "analyst",
        "action_type": "buy",
        "rationale": "human override",
        "submitted_at": datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    }
    payload.update(updates)
    return payload


def _candidate(**updates: object) -> RecommendationSnapshot:
    payload: dict[str, object] = {
        "cycle_id": "cycle_l7",
        "entity_id": "ENT_A",
        "action_type": "hold",
        "rating": "B",
        "confidence": 0.6,
        "triggered_by": "system",
        "override_applied": False,
        "constraints_applied": {"existing": "kept"},
    }
    payload.update(updates)
    return RecommendationSnapshot(**payload)


def test_submit_override_accepts_mapping_and_stores_validated_record() -> None:
    store = InMemoryOverrideStore()

    override = submit_override(_override_payload(), store=store)

    assert isinstance(override, OverrideRecord)
    assert override.action_type == "buy"
    assert store.records == (override,)
    with pytest.raises(ValidationError):
        OverrideRecord.model_validate({**override.model_dump(), "action_type": "sell"})


def test_submit_override_accepts_existing_record() -> None:
    store = InMemoryOverrideStore()
    override = OverrideRecord(**_override_payload(action_type="reduce"))

    stored_override = submit_override(override, store=store)

    assert stored_override == override
    assert stored_override is not override
    assert store.records == (stored_override,)


def test_find_override_returns_matching_cycle_entity_record() -> None:
    first = OverrideRecord(**_override_payload(entity_id="ENT_B", action_type="reduce"))
    second = OverrideRecord(**_override_payload())

    assert find_override([first, second], "cycle_l7", "ENT_A") == second
    assert find_override([first, second], "cycle_l7", "ENT_Z") is None


def test_find_override_uses_latest_duplicate_submission() -> None:
    older = OverrideRecord(**_override_payload(action_type="buy"))
    newer = OverrideRecord(**_override_payload(action_type="reduce"))

    assert find_override([older, newer], "cycle_l7", "ENT_A") == newer


def test_apply_override_sets_human_audit_fields_and_keeps_constraints() -> None:
    override = OverrideRecord(**_override_payload(action_type="reduce"))

    result = apply_override(_candidate(), override)

    assert result.action_type == "reduce"
    assert result.rating == "C"
    assert result.triggered_by == "human_decision"
    assert result.override_applied is True
    assert result.constraints_applied == {"existing": "kept"}


def test_rating_for_action_is_shared_l7_rule() -> None:
    assert rating_for_action("buy") == "A"
    assert rating_for_action("hold") == "B"
    assert rating_for_action("reduce") == "C"


def test_apply_override_rejects_non_matching_override() -> None:
    override = OverrideRecord(**_override_payload(entity_id="ENT_B"))

    with pytest.raises(MainCoreError, match="entity_id"):
        apply_override(_candidate(), override)


def test_submit_override_honors_falsey_custom_store_end_to_end() -> None:
    class FalseyOverrideStore(InMemoryOverrideStore):
        def __len__(self) -> int:
            return 0

    store = FalseyOverrideStore()
    submit_override(_override_payload(action_type="reduce"), store=store)
    pool = OfficialAlphaPool(
        cycle_id="cycle_l7",
        observation_pool_size=1,
        official_alpha_pool_capacity=1,
        selected_entities=["ENT_A"],
        added_entities=["ENT_A"],
        removed_entities=[],
        freeze_reason_map={},
    )
    analysis = AlphaResultSnapshot(
        cycle_id="cycle_l7",
        entity_id="ENT_A",
        analyzer_type="single_prompt_v1",
        score=0.8,
        confidence=0.7,
        rationale="fixture alpha",
        similar_cases=[],
        status="ok",
    )
    world_state = WorldStateSnapshot(
        cycle_id="cycle_l7",
        baseline_regime="neutral",
        llm_delta=0,
        final_regime="neutral",
        llm_rationale="fixture",
        actual_model_used="fixture",
        actual_provider="local",
        fallback_path=[],
    )

    [recommendation] = generate_recommendations(
        pool,
        [analysis],
        world_state,
        override_store=store,
    )

    assert recommendation.action_type == "reduce"
    assert recommendation.override_applied is True
