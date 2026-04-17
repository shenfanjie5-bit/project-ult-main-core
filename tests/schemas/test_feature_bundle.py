"""Tests for FeatureSignalBundle."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from main_core.common.schemas import FeatureSignalBundle, FormalObjectBase


def _feature_bundle() -> FeatureSignalBundle:
    return FeatureSignalBundle(
        cycle_id="cycle-20260417",
        entity_id="ENT_001",
        feature_values={"momentum": 1.5},
        signal_values={"breakout": True},
        graph_features={"centrality": 0.7},
        feature_weight_multiplier={"momentum": 1.2},
        generated_at=datetime(2026, 4, 17, tzinfo=UTC),
    )


def test_feature_bundle_happy_path_and_round_trip() -> None:
    bundle = _feature_bundle()

    assert isinstance(bundle, FormalObjectBase)
    assert FeatureSignalBundle.from_json(bundle.to_json()) == bundle


def test_feature_bundle_rejects_missing_required_field() -> None:
    payload = _feature_bundle().model_dump()
    payload.pop("feature_values")

    with pytest.raises(ValidationError):
        FeatureSignalBundle(**payload)


@pytest.mark.parametrize("multiplier", [0.0, -0.1, float("nan")])
def test_feature_bundle_rejects_non_positive_or_non_finite_multiplier(
    multiplier: float,
) -> None:
    payload = _feature_bundle().model_dump()
    payload["feature_weight_multiplier"] = {"momentum": multiplier}

    with pytest.raises(ValidationError):
        FeatureSignalBundle(**payload)
