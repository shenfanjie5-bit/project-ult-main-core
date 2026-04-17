"""L3 package: feature and signal bundle assembly."""

from main_core.l3_features.builder import build_feature_signal_bundle
from main_core.l3_features.errors import InvalidMultiplierError, L3FeatureError
from main_core.l3_features.multiplier_store import InMemoryMultiplierStore, MultiplierStore
from main_core.l3_features.weight_api import (
    apply_weight_multiplier,
    get_feature_weight_multiplier,
)

__all__ = [
    "InMemoryMultiplierStore",
    "InvalidMultiplierError",
    "L3FeatureError",
    "MultiplierStore",
    "apply_weight_multiplier",
    "build_feature_signal_bundle",
    "get_feature_weight_multiplier",
]
