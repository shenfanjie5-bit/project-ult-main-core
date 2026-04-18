"""Cross-layer pure-market L3-L7 closed-loop coverage."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from main_core.common.contexts import AlphaAnalysisContext
from main_core.common.errors import MainCoreError
from main_core.common.schemas import FeatureSignalBundle, OfficialAlphaPool
from main_core.l4_world_state import derive_world_state
from main_core.l5_universe import select_official_alpha_pool
from main_core.l6_alpha import AlphaReasonerResponse, SinglePromptAnalyzer
from main_core.l7_recommendation import (
    InMemoryOverrideStore,
    generate_recommendations,
    submit_override,
)


class MappingReasonerPort:
    def __init__(self, responses: dict[str, AlphaReasonerResponse]) -> None:
        self.responses = responses

    def analyze_alpha(
        self,
        entity_id: str,
        context: AlphaAnalysisContext,
    ) -> AlphaReasonerResponse:
        return self.responses[str(entity_id)]


def test_pure_market_closed_loop_with_override_constraint_and_inconclusive() -> None:
    cycle_id = "cycle_market_closed_loop"
    bundles = [
        _bundle(cycle_id, "ENT_A", 3.0),
        _bundle(cycle_id, "ENT_B", 2.0),
    ]
    world_state = derive_world_state(bundles[0])
    pool = select_official_alpha_pool(world_state, bundles, capacity=2)
    bundle_by_entity = {str(bundle.entity_id): bundle for bundle in bundles}
    reasoner_port = MappingReasonerPort(
        {
            "ENT_A": AlphaReasonerResponse(
                score=0.8,
                confidence=0.9,
                rationale="strong current-cycle alpha",
                similar_cases=[],
            ),
            "ENT_B": AlphaReasonerResponse(
                score=None,
                confidence=0.0,
                rationale="provider timeout",
                similar_cases=[],
                task_failed=True,
                failure_reason="task-level timeout",
            ),
        }
    )
    analyzer = SinglePromptAnalyzer(reasoner_port)
    analyses = [
        analyzer.analyze(
            entity_id,
            AlphaAnalysisContext(
                cycle_id=cycle_id,
                entity_id=entity_id,
                feature_bundle=bundle_by_entity[str(entity_id)],
                world_state=world_state,
                similar_cases=[],
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
            "rationale": "manual conviction check",
            "submitted_at": datetime(2026, 4, 17, 9, 30, tzinfo=UTC),
        },
        store=override_store,
    )

    recommendations = generate_recommendations(
        pool,
        analyses,
        world_state,
        override_store=override_store,
    )

    by_entity = {
        str(recommendation.entity_id): recommendation
        for recommendation in recommendations
    }
    assert by_entity["ENT_A"].action_type == "hold"
    assert by_entity["ENT_A"].triggered_by == "human_decision"
    assert by_entity["ENT_A"].override_applied is True
    assert by_entity["ENT_A"].constraints_applied["regime_gate"] == "risk_off_buy_to_hold"
    assert by_entity["ENT_B"].action_type == "inconclusive"
    assert by_entity["ENT_B"].confidence is None


def test_pure_market_closed_loop_rejects_stale_previous_freeze() -> None:
    cycle_id = "cycle_market_closed_loop"
    previous_pool = OfficialAlphaPool(
        cycle_id=cycle_id,
        observation_pool_size=1,
        official_alpha_pool_capacity=2,
        selected_entities=["ENT_STALE"],
        added_entities=[],
        removed_entities=[],
        freeze_reason_map={"ENT_STALE": "stale freeze"},
    )
    world_state = derive_world_state(_bundle(cycle_id, "ENT_A", 3.0))

    with pytest.raises(MainCoreError, match="frozen entities must be present"):
        select_official_alpha_pool(
            world_state,
            [_bundle(cycle_id, "ENT_A", 3.0)],
            previous_pool=previous_pool,
            capacity=2,
        )


def _bundle(cycle_id: str, entity_id: str, momentum: float) -> FeatureSignalBundle:
    return FeatureSignalBundle(
        cycle_id=cycle_id,
        entity_id=entity_id,
        feature_values={"momentum": momentum},
        signal_values={"baseline_regime": "risk_off"},
        graph_features={},
        feature_weight_multiplier={"momentum": 1.0},
    )
