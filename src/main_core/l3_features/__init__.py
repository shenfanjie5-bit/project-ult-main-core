"""L3 package: feature and signal bundle assembly."""

from main_core.l3_features.builder import build_feature_signal_bundle, build_feature_signal_bundles
from main_core.l3_features.errors import InvalidMultiplierError, L3FeatureError
from main_core.l3_features.graph_adapter import (
    GraphEnginePort,
    GraphImpactRecord,
    GraphRegimeContext,
    GraphSnapshotError,
    load_graph_features,
    merge_graph_features,
)
from main_core.l3_features.multiplier_store import InMemoryMultiplierStore, MultiplierStore
from main_core.l3_features.weight_api import (
    apply_weight_multiplier,
    get_feature_weight_multiplier,
)

__all__ = [
    "GraphEnginePort",
    "GraphImpactRecord",
    "GraphRegimeContext",
    "GraphSnapshotError",
    "InMemoryMultiplierStore",
    "InvalidMultiplierError",
    "L3FeatureError",
    "MultiplierStore",
    "apply_weight_multiplier",
    "build_feature_signal_bundle",
    "build_feature_signal_bundles",
    "get_feature_weight_multiplier",
    "load_graph_features",
    "merge_graph_features",
]
