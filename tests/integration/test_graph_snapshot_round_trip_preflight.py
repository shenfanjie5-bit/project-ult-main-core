"""M3.2 — Graph snapshot ref round-trip preflight.

Bounded preflight that closes the M3.2 gate criterion ("P2 consumes an
actual produced graph snapshot ref in a bounded run, not a fixture-only
fake"). Wires the **real** graph-engine snapshot writer + reader and a
small adapter port through main-core's L3 / L4 consumers; proves the
cycle_id plus GraphSnapshot-derived node/edge payload round-trip
end-to-end.

Scope boundaries deliberately observed:

* No live PG, no live Neo4j, no Dagster job execution. The test uses
  ``tmp_path`` for the artifact root and ``InMemoryStaticReasonerPort``
  semantics for L4. M3.3 (production same-cycle proof) remains the
  full-stack proof that this preflight stops short of.
* No production ``GraphEnginePort`` impl (none exists yet); the test
  introduces an ``_ArtifactBackedGraphEnginePort`` that internally
  reads the artifact via ``ArtifactCanonicalReader`` and converts the
  contracts-shape GraphSnapshot-derived cold-reload plan into the main-core
  ``GraphImpactRecord`` / ``GraphRegimeContext`` shapes the L3 / L4
  adapters expect. The adapter is local to this test.
* The writer stores the companion ``GraphImpactSnapshot`` in the
  formal artifact, but the public ``ArtifactCanonicalReader`` path used
  here exposes only the GraphSnapshot-derived cold-reload plan. Formal
  GraphImpactSnapshot consumption remains future production-adapter
  work.
* graph-engine is imported as a sibling repo. main-core's `.venv` does
  not pre-install ``graph_engine``; the test prepends the sibling
  source path lazily so the import works from the standard
  ``.venv/bin/python -m pytest`` invocation.

Per main-core/CLAUDE.md the integration test consumes graph-engine's
**public** writer + reader entry points only (``FormalArtifactSnapshotWriter``
and ``ArtifactCanonicalReader``); no graph-engine internal symbols
are touched.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from main_core.common.protocols import GraphImpactRecord, GraphRegimeContext
from main_core.common.types import CycleId, EntityId
from main_core.l1_l2_basis import EntityMasterRow, MarketBar
from main_core.l3_features import build_feature_signal_bundles
from main_core.l4_world_state import StaticWorldStateReasonerPort, derive_world_state
from main_core.l4_world_state.reasoner_port import WorldStateDeltaDecision

# ---------------------------------------------------------------------------
# Lazy graph-engine import: main-core's .venv does not install
# ``graph_engine``; prepend the sibling repo's source path on first call.
# Defined after the main_core imports because main_core does not depend
# on graph_engine — only the graph-engine reads (writer/reader + the
# artifact-backed adapter below) need the path nudge.
# ---------------------------------------------------------------------------


def _ensure_graph_engine_on_path() -> None:
    """Resolve the sibling ``graph-engine`` repo and append its root to
    ``sys.path``. The preflight is a **gate** — missing graph-engine
    must hard-fail rather than silently skip, so that a CI lane that
    forgets to check out the sibling repo cannot pass the M3.2
    preflight by accident (codex review-fold-1 P2: skip-as-pass would
    weaken the gate). Set ``ULT_M3_2_ALLOW_SKIP_MISSING_GRAPH_ENGINE=1``
    to opt out for purely-local development checkouts that intentionally
    omit the sibling."""

    here = Path(__file__).resolve()
    workspace = here.parents[3]  # .../project-ult
    graph_engine_root = workspace / "graph-engine"
    if not graph_engine_root.is_dir():
        import os

        if os.environ.get("ULT_M3_2_ALLOW_SKIP_MISSING_GRAPH_ENGINE") == "1":
            pytest.skip(
                f"graph-engine sibling repo not found at {graph_engine_root}; "
                "skipping cross-module preflight (env opt-out enabled)"
            )
        raise RuntimeError(
            f"graph-engine sibling repo not found at {graph_engine_root}; "
            "the M3.2 preflight requires graph-engine on disk. Either "
            "check out graph-engine alongside main-core in the workspace "
            "or set ULT_M3_2_ALLOW_SKIP_MISSING_GRAPH_ENGINE=1 to opt out."
        )
    if str(graph_engine_root) not in sys.path:
        # Append rather than insert(0) so the sibling repo cannot
        # shadow stdlib / installed packages with conflicting names.
        # (review-fold-1 P2: code-reviewer D1.)
        sys.path.append(str(graph_engine_root))

# ---------------------------------------------------------------------------
# Fakes for non-graph dependencies (data-platform, world-state policy).
# Minimal — keep the test focused on the graph-snapshot round-trip.
# ---------------------------------------------------------------------------


@dataclass
class _FakeDataPlatformPort:
    market_bars: Sequence[object] = field(default_factory=tuple)
    entity_master: Sequence[object] = field(default_factory=tuple)

    def read_market_bars(self, cycle_id: CycleId | str) -> Sequence[object]:
        return self.market_bars

    def read_calendar(self, cycle_id: CycleId | str) -> Sequence[object]:
        return ()

    def read_entity_master(self, cycle_id: CycleId | str) -> Sequence[object]:
        return self.entity_master


@dataclass
class _SimpleWorldStatePolicy:
    seen_inputs: list[Any] = field(default_factory=list)

    def baseline(self, inputs: Any) -> str:
        self.seen_inputs.append(inputs)
        return "neutral"

    def bound_delta(self, raw_delta: int) -> int:
        if raw_delta < 0:
            return -1
        if raw_delta > 0:
            return 1
        return 0

    def compose(self, baseline: str, delta: int) -> str:
        regimes = ("risk_off", "neutral", "risk_on")
        new_index = regimes.index(baseline) + delta
        # Clamp to a valid index so the policy is safe to reuse with
        # a non-zero delta on a regime at either edge of the spectrum.
        # (review-fold-1 minor: python-reviewer.)
        new_index = max(0, min(len(regimes) - 1, new_index))
        return regimes[new_index]


# ---------------------------------------------------------------------------
# Test-only adapter: wraps graph-engine's ArtifactCanonicalReader to
# satisfy main-core's GraphEnginePort protocol. This mirrors what a
# future production adapter would do — read records from a persisted
# artifact and reshape them into the main-core protocol.
# ---------------------------------------------------------------------------


@dataclass
class _ArtifactBackedGraphEnginePort:
    """Test-only ``GraphEnginePort`` impl reading from a graph-engine
    snapshot artifact written by ``FormalArtifactSnapshotWriter``.

    **Scope:** test fixture only. The adapter's
    ``read_graph_impact_snapshot`` projects main-core protocol records
    from ``plan.node_records`` only; it deliberately does **not**
    consume the formal ``GraphImpactSnapshot`` payload or project from
    ``plan.edge_records``. A production adapter would need to extend
    this to consume formal impact snapshots once a public reader path
    exists and to surface edge-derived impact (e.g. SUPPLY_CHAIN
    contagion). Treat this class as a fixture for round-trip semantics,
    **not** a production-adapter starting point.

    **`snapshot_ref` constraint:** the round-trip preflight tests pass
    an absolute filesystem path produced by
    ``FormalArtifactSnapshotWriter.last_artifact_ref``. Passing an
    ``artifact://...`` URI would require ``artifact_root`` be set; the
    current preflight does not exercise that path and the adapter does
    not assert the constraint at construction time. (review-fold-1
    P1: documented rather than rejected because the test caller never
    deviates from the absolute-path convention.)

    Reading via ``ArtifactCanonicalReader.read_cold_reload_plan`` is
    done once on construction; subsequent reads on the port are O(1)
    over the cached plan.
    """

    snapshot_ref: str
    artifact_root: Path | None = None
    impact_calls: list[CycleId] = field(default_factory=list)
    regime_calls: list[CycleId] = field(default_factory=list)
    # Internal post-init state. Declared with ``field(init=False)`` so
    # the dataclass contract acknowledges them — ``replace()``,
    # ``__repr__``, and ``__eq__`` skip these explicitly. Types are
    # ``Any`` because the concrete graph-engine types are imported
    # lazily and cannot be statically referenced at class-definition
    # time. (review-fold-1 P1: python-reviewer.)
    _cached_plan: Any = field(init=False, repr=False, default=None)
    _cached_snapshot: Any = field(init=False, repr=False, default=None)
    _cached_node_records: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        _ensure_graph_engine_on_path()
        from graph_engine.reload import ArtifactCanonicalReader

        reader = ArtifactCanonicalReader(self.artifact_root)
        plan = reader.read_cold_reload_plan(self.snapshot_ref)
        self._cached_plan = plan
        # ``expected_snapshot`` is a GraphMetricsSnapshot (live-metric
        # shape: cycle_id / snapshot_id / counts / checksum). The
        # detailed ``node_records`` / ``edge_records`` come from the
        # plan, not the metrics snapshot.
        self._cached_snapshot = plan.expected_snapshot
        self._cached_node_records = plan.node_records

    def read_graph_impact_snapshot(
        self, cycle_id: CycleId
    ) -> Sequence[GraphImpactRecord]:
        self.impact_calls.append(cycle_id)
        # Project the cold-reload plan's node records into one
        # main-core protocol ``GraphImpactRecord`` per node carrying a
        # canonical entity id. **Test-only projection — production
        # adapters MUST consume formal impact snapshots and also surface
        # edge-derived impact** (this fixture intentionally skips both).
        #
        # The ``round_trip_marker`` and ``node_id_in_payload`` fields
        # are read from the node's payload properties (decoded from
        # ``properties_json`` by the cold-reload reader), NOT
        # synthesized by this adapter. That makes their presence in
        # the L3 feature bundle a witness that the artifact's payload
        # round-tripped through the reader (codex review-fold-1 P2).
        snapshot = self._cached_snapshot
        records: list[GraphImpactRecord] = []
        for node_record in self._cached_node_records:
            entity_id_value = getattr(node_record, "canonical_entity_id", None)
            if not entity_id_value:
                continue
            payload_properties = getattr(node_record, "properties", {}) or {}
            records.append(
                GraphImpactRecord(
                    cycle_id=CycleId(snapshot.cycle_id),
                    entity_id=EntityId(str(entity_id_value)),
                    snapshot_id=snapshot.snapshot_id,
                    features={
                        "node_label": node_record.label,
                        # Read from payload (proves the round-trip)
                        # rather than hardcoded by the adapter.
                        "round_trip_marker": payload_properties.get(
                            "round_trip_marker"
                        ),
                        "node_id_in_payload": payload_properties.get(
                            "node_id_in_payload"
                        ),
                    },
                )
            )
        return tuple(records)

    def read_graph_regime_context(
        self, cycle_id: CycleId
    ) -> GraphRegimeContext | None:
        self.regime_calls.append(cycle_id)
        snapshot = self._cached_snapshot
        # Aggregate the marker witnesses from the node records so the
        # L4 regime context also surfaces a payload-round-trip proof.
        markers: set[str] = set()
        for node_record in self._cached_node_records:
            payload_properties = getattr(node_record, "properties", {}) or {}
            marker = payload_properties.get("round_trip_marker")
            if isinstance(marker, str):
                markers.add(marker)
        return GraphRegimeContext(
            cycle_id=CycleId(snapshot.cycle_id),
            snapshot_id=snapshot.snapshot_id,
            regime_context={
                "node_count": snapshot.node_count,
                "edge_count": snapshot.edge_count,
                # Sorted list so the assertion is deterministic.
                "round_trip_markers_from_payload": sorted(markers),
            },
        )


# ---------------------------------------------------------------------------
# Snapshot fixture builder: constructs a contracts-conformant
# GraphSnapshot plus companion GraphImpactSnapshot small enough to verify by hand.
# ---------------------------------------------------------------------------


def _build_graph_snapshot_pair(cycle_id: str) -> tuple[Any, Any]:
    """Build a ``(GraphSnapshot, GraphImpactSnapshot)`` pair conforming
    to the contracts schemas. Returns the contracts-domain Pydantic
    models that ``FormalArtifactSnapshotWriter`` accepts. The M3.2
    consumer path below reads the GraphSnapshot-derived cold-reload
    plan; it does not consume the formal impact snapshot."""

    _ensure_graph_engine_on_path()
    from contracts.core.types import Direction
    from contracts.schemas import (
        GraphImpactSnapshot,
        GraphSnapshot,
    )
    from contracts.schemas.graph import (
        EntityReference,
        GraphEdge,
        GraphNode,
    )

    created_at = datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)
    entity_a = EntityReference(
        entity_type="security",
        entity_id="ENT_001",
        canonical_id_rule_version="v1",
    )
    entity_b = EntityReference(
        entity_type="security",
        entity_id="ENT_002",
        canonical_id_rule_version="v1",
    )

    # graph-engine's ArtifactCanonicalReader requires "live-metric-shaped"
    # node + edge properties — see
    # graph_engine/reload/service.py::_validate_live_metric_node_properties.
    # Required keys: node_id, label, properties_json, created_at,
    # updated_at; canonical_entity_id when ``entity`` is set.
    iso_now = "2026-04-30T12:00:00+00:00"

    def _node_props(node_id: str, label: str, entity_id: str) -> dict[str, Any]:
        # ``round_trip_marker`` lives **inside** ``properties_json`` so
        # it round-trips through the reader's ``_canonical_properties``
        # decoding pass. The artifact-backed port reads this marker
        # back from the cold-reload plan rather than synthesizing it,
        # making it a true payload-round-trip witness
        # (codex review-fold-1 P2: marker must come from the artifact,
        # not from the adapter itself).
        return {
            "node_id": node_id,
            "label": label,
            "canonical_entity_id": entity_id,
            "properties_json": json.dumps(
                {
                    "round_trip_marker": "from-artifact-payload",
                    "node_id_in_payload": node_id,
                },
                sort_keys=True,
            ),
            "created_at": iso_now,
            "updated_at": iso_now,
        }

    def _edge_props(edge_id: str, src: str, tgt: str, rel: str) -> dict[str, Any]:
        # ``properties_json`` is the live-metric source-of-truth that the
        # cold-reload reader decodes back into the GraphEdgeRecord's
        # ``properties`` dict. Evidence refs must live inside that JSON
        # blob (NOT alongside ``properties_json`` as a sibling key) so
        # the reader's ``_canonical_properties`` returns them.
        return {
            "edge_id": edge_id,
            "source_node_id": src,
            "target_node_id": tgt,
            "relationship_type": rel,
            "properties_json": json.dumps(
                {"evidence_refs": ["evidence://test/round-trip-001"]},
                sort_keys=True,
            ),
            "weight": 1.0,
            "created_at": iso_now,
            "updated_at": iso_now,
        }

    nodes = [
        GraphNode(
            node_id="NODE_001",
            labels=["Entity"],
            properties=_node_props("NODE_001", "Entity", "ENT_001"),
            entity=entity_a,
        ),
        GraphNode(
            node_id="NODE_002",
            labels=["Entity"],
            properties=_node_props("NODE_002", "Entity", "ENT_002"),
            entity=entity_b,
        ),
    ]
    edges = [
        GraphEdge(
            edge_id="EDGE_001",
            source_node="NODE_001",
            target_node="NODE_002",
            relation_type="SUPPLY_CHAIN",
            properties=_edge_props(
                "EDGE_001", "NODE_001", "NODE_002", "SUPPLY_CHAIN"
            ),
            evidence_refs=["evidence://test/001"],
        ),
    ]

    graph_snapshot = GraphSnapshot(
        graph_snapshot_id=f"graph-snapshot-{cycle_id}-7-abc",
        cycle_id=cycle_id,
        version="v1",
        created_at=created_at,
        node_count=len(nodes),
        edge_count=len(edges),
        nodes=nodes,
        edges=edges,
    )
    impact_snapshot = GraphImpactSnapshot(
        impact_snapshot_id=f"impact-snapshot-{cycle_id}-7-abc",
        cycle_id=cycle_id,
        version="v1",
        created_at=created_at,
        target_entities=[entity_a],
        affected_entities=[entity_a],
        affected_sectors=[],
        direction=Direction.BULLISH,
        impact_score=0.81,
        evidence_refs=["evidence://test/impact-001"],
    )
    return graph_snapshot, impact_snapshot


# ---------------------------------------------------------------------------
# The preflight tests
# ---------------------------------------------------------------------------


def test_graph_snapshot_artifact_round_trips_via_writer_and_reader(
    tmp_path: Path,
) -> None:
    """Phase 1 of the preflight: graph-engine's
    ``FormalArtifactSnapshotWriter`` writes a real ``GraphSnapshot`` +
    companion ``GraphImpactSnapshot`` pair to disk; ``ArtifactCanonicalReader``
    reads back a ``ColdReloadPlan`` whose ``expected_snapshot`` matches
    the original GraphSnapshot identity fields. This is the boundary
    contract M3.2 hinges on: the GraphSnapshot write/read shapes agree.
    The public reader does not expose formal GraphImpactSnapshot
    consumption."""

    _ensure_graph_engine_on_path()
    from graph_engine.reload import ArtifactCanonicalReader
    from graph_engine.snapshots import FormalArtifactSnapshotWriter

    cycle_id = "cycle-m3-2-preflight"
    graph_snapshot, impact_snapshot = _build_graph_snapshot_pair(cycle_id)

    writer = FormalArtifactSnapshotWriter(tmp_path)
    writer.write_snapshots(graph_snapshot, impact_snapshot)
    artifact_ref = writer.last_artifact_ref
    assert artifact_ref is not None
    assert Path(artifact_ref).is_file(), (
        f"writer did not produce a file at {artifact_ref}"
    )

    reader = ArtifactCanonicalReader()
    plan = reader.read_cold_reload_plan(artifact_ref)

    assert plan.cycle_id == cycle_id
    expected = plan.expected_snapshot  # GraphMetricsSnapshot
    assert expected.snapshot_id == graph_snapshot.graph_snapshot_id
    assert expected.node_count == graph_snapshot.node_count
    assert expected.edge_count == graph_snapshot.edge_count
    # Cold-reload plan also exposes the per-record lists derived from
    # the live-metric properties_json — verify the counts match.
    assert len(plan.node_records) == graph_snapshot.node_count
    assert len(plan.edge_records) == graph_snapshot.edge_count


def test_main_core_l3_consumes_artifact_backed_graph_snapshot_node_payload(
    tmp_path: Path,
) -> None:
    """Phase 2 of the preflight: the artifact-backed
    ``GraphEnginePort`` adapter projects main-core protocol records
    from the round-tripped GraphSnapshot node payload; main-core's
    ``build_feature_signal_bundles`` (L3) consumes them and stamps the
    snapshot's identifier into the feature bundle. This proves the L3
    consumer reads from a real produced GraphSnapshot, not a hard-coded
    fixture. It does not prove formal GraphImpactSnapshot consumption."""

    _ensure_graph_engine_on_path()
    from graph_engine.snapshots import FormalArtifactSnapshotWriter

    cycle_id = CycleId("cycle-m3-2-preflight")
    graph_snapshot, impact_snapshot = _build_graph_snapshot_pair(str(cycle_id))

    writer = FormalArtifactSnapshotWriter(tmp_path)
    writer.write_snapshots(graph_snapshot, impact_snapshot)
    artifact_ref = writer.last_artifact_ref
    assert artifact_ref is not None

    entity = EntityMasterRow(
        entity_id=EntityId("ENT_001"),
        ticker="AAA",
        name="Alpha A",
        exchange="NASDAQ",
    )
    data_port = _FakeDataPlatformPort(
        entity_master=(entity,),
        market_bars=(
            MarketBar(
                cycle_id=cycle_id,
                entity_id=entity.entity_id,
                as_of_date=date(2026, 4, 30),
                close_price=100.0,
                volume=1000.0,
                return_1d=0.01,
            ),
        ),
    )

    graph_port = _ArtifactBackedGraphEnginePort(snapshot_ref=artifact_ref)
    bundles = build_feature_signal_bundles(
        cycle_id,
        data_port=data_port,
        graph_engine_port=graph_port,
    )

    assert len(bundles) == 1
    bundle = bundles[0]
    # The bundle's graph_features MUST carry the produced snapshot's
    # graph_snapshot_id — proving L3 consumed the **real** ref, not a
    # synthetic value the test conjured outside the snapshot lifecycle.
    assert bundle.graph_features["snapshot_id"] == graph_snapshot.graph_snapshot_id
    # The marker comes from the snapshot's payload (embedded in
    # properties_json by the fixture builder, decoded by the reader,
    # surfaced by the adapter). Reading "from-artifact-payload" here
    # proves the **payload** round-tripped through writer→reader, not
    # just the IDs/counts (codex review-fold-1 P2).
    bundle_features = bundle.graph_features["features"]
    assert bundle_features["round_trip_marker"] == "from-artifact-payload"
    # The per-node id-in-payload field came through the payload too.
    assert bundle_features["node_id_in_payload"] == "NODE_001"
    # L3 called the protocol impact path exactly once with the requested cycle id.
    assert graph_port.impact_calls == [cycle_id]


def test_main_core_l4_consumes_artifact_backed_graph_regime_context(
    tmp_path: Path,
) -> None:
    """Phase 3 of the preflight: the artifact-backed adapter also
    serves the ``read_graph_regime_context`` path; main-core's
    ``derive_world_state`` (L4) consumes it and stamps the snapshot's
    identifier + node/edge counts into the world-state inputs. Proves
    the L4 consumer also reads from the real produced GraphSnapshot.
    It does not prove formal GraphImpactSnapshot consumption."""

    _ensure_graph_engine_on_path()
    from graph_engine.snapshots import FormalArtifactSnapshotWriter

    cycle_id = CycleId("cycle-m3-2-preflight")
    graph_snapshot, impact_snapshot = _build_graph_snapshot_pair(str(cycle_id))

    writer = FormalArtifactSnapshotWriter(tmp_path)
    writer.write_snapshots(graph_snapshot, impact_snapshot)
    artifact_ref = writer.last_artifact_ref
    assert artifact_ref is not None

    entity = EntityMasterRow(
        entity_id=EntityId("ENT_001"),
        ticker="AAA",
        name="Alpha A",
        exchange="NASDAQ",
    )
    data_port = _FakeDataPlatformPort(
        entity_master=(entity,),
        market_bars=(
            MarketBar(
                cycle_id=cycle_id,
                entity_id=entity.entity_id,
                as_of_date=date(2026, 4, 30),
                close_price=100.0,
                volume=1000.0,
                return_1d=0.01,
            ),
        ),
    )
    graph_port = _ArtifactBackedGraphEnginePort(snapshot_ref=artifact_ref)
    bundles = build_feature_signal_bundles(
        cycle_id,
        data_port=data_port,
        graph_engine_port=graph_port,
    )
    assert len(bundles) == 1

    policy = _SimpleWorldStatePolicy()
    world_state = derive_world_state(
        bundles[0],
        policy=policy,
        reasoner_port=StaticWorldStateReasonerPort(
            WorldStateDeltaDecision(
                raw_delta=0,
                rationale="static preflight delta",
                actual_model_used="static",
                actual_provider="local",
                fallback_path=[],
            )
        ),
        graph_engine_port=graph_port,
    )

    assert world_state.cycle_id == cycle_id
    # The L4 inputs the policy saw MUST carry the snapshot's
    # graph_snapshot_id and counts — proving L4 consumed the real ref.
    assert len(policy.seen_inputs) == 1
    graph_impact = policy.seen_inputs[0].graph_impact
    assert graph_impact["snapshot_id"] == graph_snapshot.graph_snapshot_id
    regime_context = graph_impact["regime_context"]
    assert regime_context["node_count"] == graph_snapshot.node_count
    assert regime_context["edge_count"] == graph_snapshot.edge_count
    # The markers are aggregated by the adapter from each node's
    # payload (decoded via the reader's properties_json round-trip);
    # both nodes embed the same marker so the deduped list has one
    # entry — proving payload values flow end-to-end (codex
    # review-fold-1 P2).
    assert regime_context["round_trip_markers_from_payload"] == [
        "from-artifact-payload",
    ]
    # L4 called the regime path exactly once with the requested cycle id.
    assert graph_port.regime_calls == [cycle_id]


def test_round_trip_preserves_cycle_id_with_long_alphanumeric_ref(
    tmp_path: Path,
) -> None:
    """Belt-and-braces: the round-trip preserves ``cycle_id`` for a
    long alphanumeric ref that mirrors the production cycle-id
    convention (``cycle-<task>-<date>T<time>Z`` with hyphens replacing
    colons in the timestamp). Catches a regression where the writer or
    reader silently coerces / truncates the cycle_id when the value
    has more visual structure than the simpler ``cycle-current``
    examples used by the other three tests.

    The hyphen-as-time-separator is intentional: ``CycleId`` rejects
    the literal-colon ``T12:00Z`` form (per the validator constraint)
    and the production filesystem convention also uses hyphens to
    avoid path-separator clashes on case-insensitive filesystems."""

    _ensure_graph_engine_on_path()
    from graph_engine.reload import ArtifactCanonicalReader
    from graph_engine.snapshots import FormalArtifactSnapshotWriter

    cycle_id = "cycle-m3-2-2026-04-30T12-00Z"
    graph_snapshot, impact_snapshot = _build_graph_snapshot_pair(cycle_id)

    writer = FormalArtifactSnapshotWriter(tmp_path)
    writer.write_snapshots(graph_snapshot, impact_snapshot)
    artifact_ref = writer.last_artifact_ref
    assert artifact_ref is not None

    reader = ArtifactCanonicalReader()
    plan = reader.read_cold_reload_plan(artifact_ref)
    assert plan.cycle_id == cycle_id
    assert plan.expected_snapshot.cycle_id == cycle_id
