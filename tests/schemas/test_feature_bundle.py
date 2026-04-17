"""Tests for the L3 feature signal bundle schema."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from main_core.common.schemas import (
    AlphaResultSnapshot,
    DashboardSnapshot,
    FeatureSignalBundle,
    FormalObjectBase,
    FormalReport,
    OfficialAlphaPool,
    OverrideRecord,
    PublishBundle,
    RecommendationSnapshot,
    WorldStateSnapshot,
)


def _bundle_payload() -> dict[str, object]:
    return {
        "cycle_id": "cycle_001",
        "entity_id": "ENT_001",
        "feature_values": {"momentum": 0.42},
        "signal_values": {"direction": "positive"},
        "graph_features": {"centrality": 0.5},
        "feature_weight_multiplier": {"momentum": 1.2},
        "generated_at": datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    }


def test_feature_signal_bundle_happy_path_round_trips_json() -> None:
    bundle = FeatureSignalBundle(**_bundle_payload())

    assert FeatureSignalBundle.from_json(bundle.to_json()) == bundle


def test_feature_signal_bundle_missing_field_fails() -> None:
    payload = _bundle_payload()
    payload.pop("entity_id")

    with pytest.raises(ValidationError):
        FeatureSignalBundle(**payload)


@pytest.mark.parametrize(
    "multiplier",
    [0.0, -0.1, float("inf")],
)
def test_feature_signal_bundle_rejects_non_positive_or_non_finite_multiplier(
    multiplier: float,
) -> None:
    payload = _bundle_payload()
    payload["feature_weight_multiplier"] = {"momentum": multiplier}

    with pytest.raises(ValidationError, match="finite and > 0"):
        FeatureSignalBundle(**payload)


def test_all_schema_models_inherit_frozen_forbid_strict_base() -> None:
    models = (
        FeatureSignalBundle,
        WorldStateSnapshot,
        OfficialAlphaPool,
        AlphaResultSnapshot,
        RecommendationSnapshot,
        DashboardSnapshot,
        FormalReport,
        PublishBundle,
        OverrideRecord,
    )

    for model in models:
        assert issubclass(model, FormalObjectBase)
        assert model.model_config["frozen"] is True
        assert model.model_config["extra"] == "forbid"
        assert model.model_config["strict"] is True
