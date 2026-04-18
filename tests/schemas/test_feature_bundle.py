"""Tests for the L3 feature signal bundle schema."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

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


def _append_late_mutation(value: Any) -> None:
    value.append("late mutation")


def _set_late_mutation(value: Any) -> None:
    value["late"] = "mutation"


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
    [0.0, -0.1],
)
def test_feature_signal_bundle_rejects_non_positive_or_non_finite_multiplier(
    multiplier: float,
) -> None:
    payload = _bundle_payload()
    payload["feature_weight_multiplier"] = {"momentum": multiplier}

    with pytest.raises(ValidationError, match="finite and > 0"):
        FeatureSignalBundle(**payload)


@pytest.mark.parametrize("multiplier", [float("nan"), float("inf")])
def test_feature_signal_bundle_rejects_non_finite_multiplier(
    multiplier: float,
) -> None:
    payload = _bundle_payload()
    payload["feature_weight_multiplier"] = {"momentum": multiplier}

    with pytest.raises(ValidationError):
        FeatureSignalBundle(**payload)


@pytest.mark.parametrize("feature_value", [float("nan"), float("inf")])
def test_feature_signal_bundle_rejects_non_finite_feature_values(
    feature_value: float,
) -> None:
    payload = _bundle_payload()
    payload["feature_values"] = {"momentum": feature_value}

    with pytest.raises(ValidationError):
        FeatureSignalBundle(**payload)


def test_feature_signal_bundle_deep_freezes_nested_payload_containers() -> None:
    payload = _bundle_payload()
    payload["signal_values"] = {"history": ["initial"]}
    payload["graph_features"] = {"node": {"centrality": 0.5}}
    bundle = FeatureSignalBundle(**payload)
    before_json = bundle.to_json()

    with pytest.raises(AttributeError):
        bundle.signal_values["history"].append("late mutation")
    with pytest.raises(TypeError):
        bundle.graph_features["node"]["centrality"] = 0.9

    assert bundle.to_json() == before_json


@pytest.mark.parametrize(
    ("instance", "field_name", "mutate"),
    [
        (
            FeatureSignalBundle(**_bundle_payload()),
            "feature_values",
            _set_late_mutation,
        ),
        (
            WorldStateSnapshot(
                cycle_id="cycle_001",
                baseline_regime="neutral",
                llm_delta=0,
                final_regime="neutral",
                llm_rationale="baseline unchanged",
                actual_model_used="reasoner-stub",
                actual_provider="local",
                fallback_path=["baseline"],
            ),
            "fallback_path",
            _append_late_mutation,
        ),
        (
            OfficialAlphaPool(
                cycle_id="cycle_001",
                observation_pool_size=1,
                official_alpha_pool_capacity=1,
                selected_entities=["ENT_001"],
                added_entities=[],
                removed_entities=[],
                freeze_reason_map={},
            ),
            "selected_entities",
            _append_late_mutation,
        ),
        (
            AlphaResultSnapshot(
                cycle_id="cycle_001",
                entity_id="ENT_001",
                analyzer_type="single_prompt_v1",
                score=0.72,
                confidence=0.81,
                rationale="quality and momentum are aligned",
                similar_cases=[{"entity_id": "ENT_009", "score": 0.69}],
                status="ok",
            ),
            "similar_cases",
            _append_late_mutation,
        ),
        (
            RecommendationSnapshot(
                cycle_id="cycle_001",
                entity_id="ENT_001",
                action_type="buy",
                rating="A",
                confidence=0.77,
                triggered_by="system",
                override_applied=False,
                constraints_applied={"regime": "risk_on"},
            ),
            "constraints_applied",
            _set_late_mutation,
        ),
        (
            DashboardSnapshot(
                cycle_id="cycle_001",
                world_state_ref="world_state_snapshot/cycle_001",
                pool_ref="official_alpha_pool/cycle_001",
                recommendation_ref="recommendation_snapshot/cycle_001",
                summary_cards={"top_action": "buy"},
            ),
            "summary_cards",
            _set_late_mutation,
        ),
        (
            FormalReport(
                cycle_id="cycle_001",
                report_type="daily",
                recommendation_ref="recommendation_snapshot/cycle_001",
                narrative_sections={"overview": "Market risk appetite improved."},
                appendix_refs={"audit": "audit/cycle_001"},
            ),
            "narrative_sections",
            _set_late_mutation,
        ),
        (
            PublishBundle(
                cycle_id="cycle_001",
                formal_objects={
                    "world_state_snapshot": {
                        "ref": "world_state_snapshot/cycle_001/ref",
                        "payload": {"cycle_id": "cycle_001"},
                        "count": 1,
                    },
                },
                manifest_candidate={
                    "snapshot_id": "snap_001",
                    "object_refs": {
                        "world_state_snapshot": "world_state_snapshot/cycle_001/ref",
                    },
                },
                audit_payload={"actor": "system"},
                retrospective_seed={"window": "1d"},
            ),
            "formal_objects",
            _set_late_mutation,
        ),
    ],
)
def test_schema_container_fields_are_immutable_after_validation(
    instance: FormalObjectBase,
    field_name: str,
    mutate: Callable[[Any], None],
) -> None:
    before_json = instance.to_json()

    with pytest.raises((AttributeError, TypeError)):
        mutate(getattr(instance, field_name))

    assert instance.to_json() == before_json


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
        assert model.model_config["allow_inf_nan"] is False
