"""Pure-market L1-L8 style closed-loop coverage."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

import pytest

from main_core.common.contexts import AlphaAnalysisContext
from main_core.common.errors import MainCoreError
from main_core.common.schemas import OfficialAlphaPool
from main_core.common.types import CycleId, EntityId
from main_core.l1_l2_basis import EntityMasterRow, MarketBar
from main_core.l3_features import build_feature_signal_bundles
from main_core.l4_world_state import StaticWorldStateReasonerPort, derive_world_state
from main_core.l4_world_state.reasoner_port import WorldStateDeltaDecision
from main_core.l5_universe import select_official_alpha_pool
from main_core.l6_alpha import AlphaReasonerResponse, SinglePromptAnalyzer, analyze_stock
from main_core.l7_recommendation import (
    InMemoryOverrideStore,
    generate_recommendations,
    submit_override,
)


@dataclass
class MarketOnlyDataPort:
    entity_master: Sequence[EntityMasterRow]
    market_bars: Sequence[MarketBar]
    entity_master_calls: list[CycleId | str] = field(default_factory=list)
    market_bar_calls: list[CycleId | str] = field(default_factory=list)

    def read_entity_master(self, cycle_id: CycleId | str) -> Sequence[EntityMasterRow]:
        self.entity_master_calls.append(cycle_id)
        return self.entity_master

    def read_market_bars(self, cycle_id: CycleId | str) -> Sequence[MarketBar]:
        self.market_bar_calls.append(cycle_id)
        return self.market_bars

    def read_calendar(self, cycle_id: CycleId | str) -> Sequence[object]:
        return ()


class PerEntityReasonerPort:
    def __init__(self, responses: dict[str, AlphaReasonerResponse]) -> None:
        self.responses = responses

    def analyze_alpha(
        self,
        entity_id: EntityId,
        context: AlphaAnalysisContext,
    ) -> AlphaReasonerResponse:
        return self.responses[str(entity_id)]


def test_pure_market_closed_loop_with_override_constraint_and_inconclusive() -> None:
    cycle_id = CycleId("cycle_pure_market")
    data_port = MarketOnlyDataPort(
        entity_master=(
            _entity("ENT_A", "AAA"),
            _entity("ENT_B", "BBB"),
        ),
        market_bars=(
            _bar(cycle_id, "ENT_A", close_price=100.0, volume=1000.0, return_1d=0.04),
            _bar(cycle_id, "ENT_B", close_price=80.0, volume=900.0, return_1d=0.02),
        ),
    )
    bundles = build_feature_signal_bundles(cycle_id, data_port=data_port)
    world_state = derive_world_state(
        bundles[0],
        reasoner_port=StaticWorldStateReasonerPort(
            WorldStateDeltaDecision(
                raw_delta=-1,
                rationale="risk appetite deteriorated",
                actual_model_used="static",
                actual_provider="local",
                fallback_path=[],
            )
        ),
    )
    pool = select_official_alpha_pool(world_state, bundles, capacity=2)
    reasoner = PerEntityReasonerPort(
        {
            "ENT_A": AlphaReasonerResponse(
                score=0.8,
                confidence=0.7,
                rationale="strong but gated by regime",
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
    analyses = [
        analyze_stock(
            entity_id,
            _context(cycle_id, entity_id, bundles, world_state),
            analyzer=SinglePromptAnalyzer(reasoner),
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
            "rationale": "manual conviction",
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

    assert [analysis.status for analysis in analyses] == ["ok", "inconclusive"]
    assert recommendations[0].entity_id == "ENT_A"
    assert recommendations[0].action_type == "hold"
    assert recommendations[0].triggered_by == "human_decision"
    assert recommendations[0].override_applied is True
    assert recommendations[0].constraints_applied["regime_gate"] == (
        "risk_off_buy_to_hold"
    )
    assert recommendations[1].action_type == "inconclusive"
    assert recommendations[1].confidence is None
    assert data_port.entity_master_calls == [cycle_id]
    assert data_port.market_bar_calls == [cycle_id]


def test_pure_market_closed_loop_rejects_stale_freeze_before_recommendation() -> None:
    cycle_id = CycleId("cycle_pure_market")
    bundles = build_feature_signal_bundles(
        cycle_id,
        data_port=MarketOnlyDataPort(
            entity_master=(_entity("ENT_A", "AAA"),),
            market_bars=(_bar(cycle_id, "ENT_A"),),
        ),
    )
    world_state = derive_world_state(bundles[0])
    previous_pool = OfficialAlphaPool(
        cycle_id=cycle_id,
        observation_pool_size=1,
        official_alpha_pool_capacity=1,
        selected_entities=["ENT_STALE"],
        added_entities=[],
        removed_entities=[],
        freeze_reason_map={"ENT_STALE": "prior freeze"},
    )

    with pytest.raises(MainCoreError, match="frozen entities must be present"):
        select_official_alpha_pool(
            world_state,
            bundles,
            previous_pool=previous_pool,
            capacity=1,
        )


def _entity(entity_id: str, ticker: str) -> EntityMasterRow:
    return EntityMasterRow(
        entity_id=EntityId(entity_id),
        ticker=ticker,
        name=f"{ticker} Inc.",
        exchange="NASDAQ",
    )


def _bar(
    cycle_id: CycleId,
    entity_id: str,
    *,
    close_price: float = 100.0,
    volume: float = 1000.0,
    return_1d: float | None = 0.02,
) -> MarketBar:
    return MarketBar(
        cycle_id=cycle_id,
        entity_id=EntityId(entity_id),
        as_of_date=date(2026, 4, 17),
        close_price=close_price,
        volume=volume,
        return_1d=return_1d,
    )


def _context(
    cycle_id: CycleId,
    entity_id: EntityId,
    bundles: Sequence[object],
    world_state: object,
) -> AlphaAnalysisContext:
    bundle_by_entity = {
        str(bundle.entity_id): bundle
        for bundle in bundles
    }
    return AlphaAnalysisContext(
        cycle_id=cycle_id,
        entity_id=entity_id,
        feature_bundle=bundle_by_entity[str(entity_id)],
        world_state=world_state,
        similar_cases=[],
    )
