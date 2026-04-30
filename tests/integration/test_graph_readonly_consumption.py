"""Integration coverage for read-only graph consumption across L3 and L4."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

import pytest

from main_core.common.contexts import WorldStateInputs
from main_core.common.protocols import (
    GraphImpactRecord,
    GraphRegimeContext,
    GraphSnapshotError,
)
from main_core.common.schemas import WorldStateSnapshot
from main_core.common.types import CycleId, EntityId, Regime
from main_core.l1_l2_basis import EntityMasterRow, MarketBar
from main_core.l3_features import build_feature_signal_bundles
from main_core.l4_world_state import StaticWorldStateReasonerPort, derive_world_state
from main_core.l4_world_state.reasoner_port import WorldStateDeltaDecision


@dataclass
class FakeDataPlatformPort:
    market_bars: Sequence[object] = field(default_factory=tuple)
    entity_master: Sequence[object] = field(default_factory=tuple)

    def read_market_bars(self, cycle_id: CycleId | str) -> Sequence[object]:
        return self.market_bars

    def read_calendar(self, cycle_id: CycleId | str) -> Sequence[object]:
        return ()

    def read_entity_master(self, cycle_id: CycleId | str) -> Sequence[object]:
        return self.entity_master


@dataclass
class FakeGraphEnginePort:
    previous_world_state: WorldStateSnapshot
    graph_only_entity_id: EntityId = EntityId("ENT_Z")
    impact_calls: list[CycleId] = field(default_factory=list)
    regime_calls: list[CycleId] = field(default_factory=list)

    def read_graph_impact_snapshot(
        self,
        cycle_id: CycleId,
    ) -> Sequence[GraphImpactRecord]:
        self.impact_calls.append(cycle_id)
        return (
            GraphImpactRecord(
                cycle_id=cycle_id,
                entity_id=EntityId("ENT_001"),
                snapshot_id=f"graph-impact-{cycle_id}",
                features={
                    "previous_cycle_id": str(self.previous_world_state.cycle_id),
                    "previous_final_regime": self.previous_world_state.final_regime,
                    "impact_score": 0.81,
                },
            ),
            GraphImpactRecord(
                cycle_id=cycle_id,
                entity_id=self.graph_only_entity_id,
                snapshot_id=f"graph-impact-extra-{cycle_id}",
                features={"impact_score": 0.99},
            ),
        )

    def read_graph_regime_context(
        self,
        cycle_id: CycleId,
    ) -> GraphRegimeContext | None:
        self.regime_calls.append(cycle_id)
        return GraphRegimeContext(
            cycle_id=cycle_id,
            snapshot_id=f"graph-snapshot-{cycle_id}",
            regime_context={
                "previous_cycle_id": str(self.previous_world_state.cycle_id),
                "previous_final_regime": self.previous_world_state.final_regime,
                "previous_llm_delta": self.previous_world_state.llm_delta,
            },
        )


@dataclass
class CapturingWorldStatePolicy:
    seen_inputs: list[WorldStateInputs] = field(default_factory=list)

    def baseline(self, inputs: WorldStateInputs) -> Regime:
        self.seen_inputs.append(inputs)
        return "neutral"

    def bound_delta(self, raw_delta: int) -> int:
        if raw_delta < 0:
            return -1
        if raw_delta > 0:
            return 1
        return 0

    def compose(self, baseline: Regime, delta: int) -> Regime:
        regimes: tuple[Regime, ...] = ("risk_off", "neutral", "risk_on")
        return regimes[regimes.index(baseline) + delta]


def test_previous_world_state_feeds_readonly_graph_context_into_l3_and_l4() -> None:
    previous_cycle_id = CycleId("cycle-previous")
    current_cycle_id = CycleId("cycle-current")
    previous_world_state = WorldStateSnapshot(
        cycle_id=previous_cycle_id,
        baseline_regime="neutral",
        llm_delta=1,
        final_regime="risk_on",
        llm_rationale="previous cycle risk appetite improved",
        actual_model_used="static",
        actual_provider="local",
        fallback_path=[],
    )
    entity = EntityMasterRow(
        entity_id=EntityId("ENT_001"),
        ticker="AAA",
        name="Alpha A",
        exchange="NASDAQ",
    )
    data_port = FakeDataPlatformPort(
        entity_master=(entity,),
        market_bars=(
            MarketBar(
                cycle_id=current_cycle_id,
                entity_id=entity.entity_id,
                as_of_date=date(2026, 4, 17),
                close_price=100.0,
                volume=1000.0,
                return_1d=0.01,
            ),
        ),
    )
    graph_port = FakeGraphEnginePort(previous_world_state=previous_world_state)

    bundles = build_feature_signal_bundles(
        current_cycle_id,
        data_port=data_port,
        graph_engine_port=graph_port,
    )

    assert [bundle.entity_id for bundle in bundles] == ["ENT_001"]
    assert bundles[0].graph_features == {
        "snapshot_id": "graph-impact-cycle-current",
        "features": {
            "previous_cycle_id": "cycle-previous",
            "previous_final_regime": "risk_on",
            "impact_score": 0.81,
        },
    }

    policy = CapturingWorldStatePolicy()
    world_state = derive_world_state(
        bundles[0],
        policy=policy,
        reasoner_port=StaticWorldStateReasonerPort(
            WorldStateDeltaDecision(
                raw_delta=0,
                rationale="static integration delta",
                actual_model_used="static",
                actual_provider="local",
                fallback_path=[],
            )
        ),
        graph_engine_port=graph_port,
    )

    assert world_state.cycle_id == current_cycle_id
    assert world_state.final_regime == "neutral"
    assert policy.seen_inputs[0].graph_impact == {
        "snapshot_id": "graph-snapshot-cycle-current",
        "regime_context": {
            "previous_cycle_id": "cycle-previous",
            "previous_final_regime": "risk_on",
            "previous_llm_delta": 1,
        },
    }
    assert graph_port.impact_calls == [current_cycle_id]
    assert graph_port.regime_calls == [current_cycle_id]


# ---------------------------------------------------------------------------
# M3.1 — cross-cycle rejection branch
#
# Per C4 audit (2026-04-28): the per-layer unit tests in
# tests/l3_features/test_graph_adapter.py and
# tests/l4_world_state/test_graph_adapter.py already pin the
# ``GraphSnapshotError`` raise on a single-call cycle mismatch. What the
# integration suite was missing is end-to-end coverage that the
# fail-closed rejection survives the higher-level
# ``build_feature_signal_bundles`` (L3) and ``derive_world_state`` (L4)
# call paths — i.e. that the production daily-cycle path will halt at
# the first cycle-id mismatch instead of silently consuming the
# drifted graph artifact.
# ---------------------------------------------------------------------------


@dataclass
class FakeDriftedGraphEnginePort:
    """Returns graph artifacts whose ``cycle_id`` deliberately differs from
    the requested ``cycle_id``. Models the failure mode where the graph
    snapshot writer somehow committed a snapshot under a stale cycle id
    (e.g. a botched freeze) and L3/L4 try to read the current cycle's
    snapshot but receive the stale one."""

    drift_cycle_id: CycleId
    impact_calls: list[CycleId] = field(default_factory=list)
    regime_calls: list[CycleId] = field(default_factory=list)
    drift_impact: bool = True
    drift_regime: bool = True

    def read_graph_impact_snapshot(
        self,
        cycle_id: CycleId,
    ) -> Sequence[GraphImpactRecord]:
        self.impact_calls.append(cycle_id)
        # If drift_impact is True, return records tagged with
        # drift_cycle_id (NOT the requested cycle_id) — this is the
        # fail-closed trigger.
        snapshot_cycle = self.drift_cycle_id if self.drift_impact else cycle_id
        return (
            GraphImpactRecord(
                cycle_id=snapshot_cycle,
                entity_id=EntityId("ENT_001"),
                snapshot_id=f"graph-impact-{snapshot_cycle}",
                features={"impact_score": 0.42},
            ),
        )

    def read_graph_regime_context(
        self,
        cycle_id: CycleId,
    ) -> GraphRegimeContext | None:
        self.regime_calls.append(cycle_id)
        snapshot_cycle = self.drift_cycle_id if self.drift_regime else cycle_id
        return GraphRegimeContext(
            cycle_id=snapshot_cycle,
            snapshot_id=f"graph-snapshot-{snapshot_cycle}",
            regime_context={"sample": "value"},
        )


def _entity_with_market_bar(
    cycle_id: CycleId,
) -> tuple[EntityMasterRow, FakeDataPlatformPort]:
    """Construct the minimal data-platform fixture needed for L3 and L4
    in the cross-cycle rejection tests."""

    entity = EntityMasterRow(
        entity_id=EntityId("ENT_001"),
        ticker="AAA",
        name="Alpha A",
        exchange="NASDAQ",
    )
    data_port = FakeDataPlatformPort(
        entity_master=(entity,),
        market_bars=(
            MarketBar(
                cycle_id=cycle_id,
                entity_id=entity.entity_id,
                as_of_date=date(2026, 4, 17),
                close_price=100.0,
                volume=1000.0,
                return_1d=0.01,
            ),
        ),
    )
    return entity, data_port


def test_l3_build_feature_bundles_fails_closed_on_cross_cycle_graph_impact() -> None:
    """End-to-end L3 rejection: when graph_engine_port returns impact
    records tagged with a cycle id that differs from the requested
    cycle id, ``build_feature_signal_bundles`` MUST raise
    ``GraphSnapshotError`` rather than silently consume the drift.
    The check is the production guarantee that L3 cannot ingest a
    stale-cycle graph snapshot into the current cycle's feature bundle."""

    current_cycle_id = CycleId("cycle-current")
    drift_cycle_id = CycleId("cycle-stale-from-yesterday")
    _entity, data_port = _entity_with_market_bar(current_cycle_id)
    drift_port = FakeDriftedGraphEnginePort(drift_cycle_id=drift_cycle_id)

    with pytest.raises(GraphSnapshotError, match="different cycle"):
        build_feature_signal_bundles(
            current_cycle_id,
            data_port=data_port,
            graph_engine_port=drift_port,
        )

    # The impact path must have been called exactly once before the
    # rejection — the failure is in the FIRST graph read, not after a
    # silent retry or downstream re-attempt.
    assert drift_port.impact_calls == [current_cycle_id]
    # The regime path must NOT have been consulted; failure halts L3
    # before L4 wiring can be reached. Pinned so a regression that
    # swallows the L3 exception and proceeds to L4 is caught here.
    assert drift_port.regime_calls == []


def test_l4_derive_world_state_fails_closed_on_cross_cycle_graph_regime() -> None:
    """End-to-end L4 rejection: when graph_engine_port returns a regime
    context tagged with a cycle id different from the requested cycle
    id, ``derive_world_state`` MUST raise ``GraphSnapshotError``.

    Set up: drift only the regime context, not the impact snapshot, so
    L3 succeeds and L4 is the layer that surfaces the rejection. This
    pins that the cross-cycle guard exists at L4 even when L3's path
    happened to consume a same-cycle artifact (e.g. graph_impact and
    graph_snapshot are written by separate writers and could disagree
    on cycle id in a partial-failure scenario)."""

    current_cycle_id = CycleId("cycle-current")
    drift_cycle_id = CycleId("cycle-stale-from-yesterday")
    _entity, data_port = _entity_with_market_bar(current_cycle_id)
    drift_port = FakeDriftedGraphEnginePort(
        drift_cycle_id=drift_cycle_id,
        drift_impact=False,  # L3 sees same-cycle records
        drift_regime=True,   # L4 sees stale-cycle context
    )

    bundles = build_feature_signal_bundles(
        current_cycle_id,
        data_port=data_port,
        graph_engine_port=drift_port,
    )
    # L3 succeeded because drift_impact=False — pin the success state
    # so a regression that breaks L3 before L4 is reached is caught.
    assert len(bundles) == 1
    assert drift_port.impact_calls == [current_cycle_id]

    policy = CapturingWorldStatePolicy()
    with pytest.raises(GraphSnapshotError, match="different cycle"):
        derive_world_state(
            bundles[0],
            policy=policy,
            reasoner_port=StaticWorldStateReasonerPort(
                WorldStateDeltaDecision(
                    raw_delta=0,
                    rationale="static integration delta",
                    actual_model_used="static",
                    actual_provider="local",
                    fallback_path=[],
                )
            ),
            graph_engine_port=drift_port,
        )

    # The regime read happened (the rejection is on its return value).
    assert drift_port.regime_calls == [current_cycle_id]
    # The policy MUST NOT have been consulted: rejection happens before
    # any downstream world-state computation. Pinned so a regression
    # that catches GraphSnapshotError and falls back to a default
    # regime is caught here.
    assert policy.seen_inputs == []


def test_cross_cycle_rejection_halts_before_world_state_is_emitted() -> None:
    """Belt-and-braces end-to-end: a cycle whose L3 graph artifact is
    drifted MUST NOT produce a ``WorldStateSnapshot`` for the current
    cycle. The rejection halts the chain at the first encounter."""

    current_cycle_id = CycleId("cycle-current")
    drift_cycle_id = CycleId("cycle-from-last-month")
    _entity, data_port = _entity_with_market_bar(current_cycle_id)
    drift_port = FakeDriftedGraphEnginePort(
        drift_cycle_id=drift_cycle_id,
        drift_impact=True,
        drift_regime=True,
    )

    # First failure: L3 should raise.
    with pytest.raises(GraphSnapshotError):
        build_feature_signal_bundles(
            current_cycle_id,
            data_port=data_port,
            graph_engine_port=drift_port,
        )

    # No world-state snapshot should ever be emitted from this drift
    # scenario; the chain halts at L3. Pinning by checking that the L4
    # graph regime read was never even attempted (because L3 raised
    # before the L4 wiring was reached).
    assert drift_port.regime_calls == []
