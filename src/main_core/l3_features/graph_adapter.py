"""Read-only graph-engine adapter for L3 feature enrichment."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from main_core.common.errors import MainCoreError
from main_core.common.schemas.feature_bundle import FeatureSignalBundle
from main_core.common.types import CycleId, EntityId


class GraphSnapshotError(MainCoreError):
    """Raised when a graph snapshot cannot be consumed safely."""


@dataclass(frozen=True, slots=True)
class GraphImpactRecord:
    """One graph impact row from the read-only graph snapshot surface."""

    cycle_id: CycleId
    entity_id: EntityId
    features: Mapping[str, Any]
    snapshot_id: str


@dataclass(frozen=True, slots=True)
class GraphRegimeContext:
    """Graph regime context read from the graph snapshot surface."""

    cycle_id: CycleId
    snapshot_id: str
    regime_context: Mapping[str, Any]


@runtime_checkable
class GraphEnginePort(Protocol):
    """Read-only graph-engine boundary used by main-core."""

    def read_graph_impact_snapshot(
        self,
        cycle_id: CycleId,
    ) -> Sequence[GraphImpactRecord]:
        """Return per-entity graph impact rows for the requested cycle."""

    def read_graph_regime_context(
        self,
        cycle_id: CycleId,
    ) -> GraphRegimeContext | None:
        """Return graph regime context for the requested cycle, when available."""


def load_graph_features(
    cycle_id: CycleId,
    entity_id: EntityId,
    port: GraphEnginePort | None,
) -> dict[str, Any]:
    """Load graph impact features for one entity from a read-only graph port."""

    if port is None:
        return {}

    records = list(port.read_graph_impact_snapshot(cycle_id))
    matching_records: list[GraphImpactRecord] = []
    for record in records:
        if str(record.cycle_id) != str(cycle_id):
            raise GraphSnapshotError(
                "graph impact snapshot contains records from a different cycle"
            )
        if str(record.entity_id) == str(entity_id):
            matching_records.append(record)

    if not matching_records:
        return {}
    if len(matching_records) > 1:
        raise GraphSnapshotError(
            "graph impact snapshot contains duplicate records for entity"
        )

    record = matching_records[0]
    return {
        "snapshot_id": record.snapshot_id,
        "features": _to_plain_json_like(record.features),
    }


def merge_graph_features(
    bundle: FeatureSignalBundle,
    graph_features: Mapping[str, Any],
) -> FeatureSignalBundle:
    """Return a new feature bundle with graph features merged in."""

    return bundle.model_copy(
        update={"graph_features": _to_plain_json_like(graph_features)}
    )


def _to_plain_json_like(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _to_plain_json_like(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_to_plain_json_like(item) for item in value]
    return value


__all__ = [
    "GraphEnginePort",
    "GraphImpactRecord",
    "GraphRegimeContext",
    "GraphSnapshotError",
    "load_graph_features",
    "merge_graph_features",
]
