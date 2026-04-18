"""Pure-market L1-L8 integration coverage for the minimal P2 path."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from main_core.common.contexts import AlphaAnalysisContext
from main_core.common.errors import MainCoreError
from main_core.common.schemas import OfficialAlphaPool
from main_core.l1_l2_basis import EntityMasterRow, MarketBar
from main_core.l3_features import build_feature_signal_bundles
from main_core.l4_world_state import StaticWorldStateReasonerPort, derive_world_state
from main_core.l4_world_state.reasoner_port import WorldStateDeltaDecision
from main_core.l5_universe import select_official_alpha_pool
from main_core.l6_alpha import (
    AlphaReasonerResponse,
    SinglePromptAnalyzer,
    StaticAlphaReasonerPort,
    analyze_stock,
)
from main_core.l7_recommendation import (
    InMemoryOverrideStore,
    generate_recommendations,
    submit_override,
)
from main_core.l8_publish import prepare_publish_bundle
from tests.l3_features.conftest import FakeDataPlatformPort
from tests.l8_publish import FakeFormalObjectSource, RecordingPublishPort


def test_pure_market_closed_loop_handles_override_constraint_and_inconclusive() -> None:
    cycle_id = "cycle_market_closed_loop"
    bundles = build_feature_signal_bundles(cycle_id, data_port=_market_port(cycle_id))
    world_state = derive_world_state(
        bundles[0],
        reasoner_port=StaticWorldStateReasonerPort(
            WorldStateDeltaDecision(
                raw_delta=-1,
                rationale="risk appetite faded",
                actual_model_used="static",
                actual_provider="local",
                fallback_path=[],
            ),
        ),
    )

    with pytest.raises(MainCoreError, match="frozen entities must be present"):
        select_official_alpha_pool(
            world_state,
            bundles,
            previous_pool=OfficialAlphaPool(
                cycle_id=cycle_id,
                observation_pool_size=1,
                official_alpha_pool_capacity=1,
                selected_entities=["ENT_STALE"],
                added_entities=[],
                removed_entities=[],
                freeze_reason_map={"ENT_STALE": "stale freeze"},
            ),
            capacity=2,
        )

    pool = select_official_alpha_pool(world_state, bundles, capacity=2)
    bundle_by_entity = {str(bundle.entity_id): bundle for bundle in bundles}
    alpha_results = [
        analyze_stock(
            entity_id,
            AlphaAnalysisContext(
                cycle_id=cycle_id,
                entity_id=entity_id,
                feature_bundle=bundle_by_entity[entity_id],
                world_state=world_state,
                similar_cases=[],
            ),
            analyzer=SinglePromptAnalyzer(
                StaticAlphaReasonerPort(_alpha_response(entity_id))
            ),
        )
        for entity_id in pool.selected_entities
    ]
    override_store = InMemoryOverrideStore()
    submit_override(
        {
            "cycle_id": cycle_id,
            "entity_id": "ENT_A",
            "submitted_by": "analyst",
            "action_type": "buy",
            "rationale": "manual conviction review",
            "submitted_at": datetime(2026, 4, 17, 9, 30, tzinfo=UTC),
        },
        store=override_store,
    )

    recommendations = generate_recommendations(
        pool,
        alpha_results,
        world_state,
        override_store=override_store,
    )
    recommendation_by_entity = {
        str(recommendation.entity_id): recommendation
        for recommendation in recommendations
    }

    assert recommendation_by_entity["ENT_A"].action_type == "hold"
    assert recommendation_by_entity["ENT_A"].triggered_by == "human_decision"
    assert recommendation_by_entity["ENT_A"].override_applied is True
    assert (
        recommendation_by_entity["ENT_A"].constraints_applied["regime_gate"]
        == "risk_off_buy_to_hold"
    )
    assert recommendation_by_entity["ENT_B"].action_type == "inconclusive"

    publish_bundle = prepare_publish_bundle(
        cycle_id,
        source=FakeFormalObjectSource(
            loaded_world_state=world_state,
            loaded_pool=pool,
            loaded_alpha_results=alpha_results,
            loaded_recommendations=recommendations,
        ),
        publish_port=RecordingPublishPort(),
    )

    assert publish_bundle.manifest_candidate["manifest_ref"] == f"manifest/{cycle_id}"
    assert publish_bundle.audit_payload["recommendation_inconclusive_count"] == 1


def _market_port(cycle_id: str) -> FakeDataPlatformPort:
    return FakeDataPlatformPort(
        entity_master=(
            EntityMasterRow(
                entity_id="ENT_A",
                ticker="AAA",
                name="Alpha A",
                exchange="NASDAQ",
            ),
            EntityMasterRow(
                entity_id="ENT_B",
                ticker="BBB",
                name="Beta B",
                exchange="NYSE",
            ),
        ),
        market_bars=(
            MarketBar(
                cycle_id=cycle_id,
                entity_id="ENT_A",
                as_of_date=date(2026, 4, 17),
                close_price=100.0,
                volume=1000.0,
                return_1d=0.03,
            ),
            MarketBar(
                cycle_id=cycle_id,
                entity_id="ENT_B",
                as_of_date=date(2026, 4, 17),
                close_price=80.0,
                volume=800.0,
                return_1d=0.01,
            ),
        ),
    )


def _alpha_response(entity_id: str) -> AlphaReasonerResponse:
    if entity_id == "ENT_B":
        return AlphaReasonerResponse(
            score=None,
            confidence=0.0,
            rationale="provider timeout",
            similar_cases=[],
            task_failed=True,
            failure_reason="task-level timeout",
        )
    return AlphaReasonerResponse(
        score=0.8,
        confidence=0.7,
        rationale="strong current-cycle market signal",
        similar_cases=[],
    )
