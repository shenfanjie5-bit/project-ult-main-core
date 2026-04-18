"""Tests for the L3 feature signal bundle schema."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
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
from main_core.l8_publish import CommittedFormalObject, ManifestWriteResult


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
    [0.0, -0.1, float("inf")],
)
def test_feature_signal_bundle_rejects_non_positive_or_non_finite_multiplier(
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


@pytest.mark.parametrize(
    "bad_number",
    [float("nan"), float("inf"), Decimal("NaN"), Decimal("Infinity")],
)
@pytest.mark.parametrize(
    ("factory", "field_name"),
    [
        (
            lambda bad_number: FeatureSignalBundle(
                **{**_bundle_payload(), "signal_values": {"nested": bad_number}}
            ),
            "signal_values",
        ),
        (
            lambda bad_number: FeatureSignalBundle(
                **{**_bundle_payload(), "graph_features": {"nested": bad_number}}
            ),
            "graph_features",
        ),
        (
            lambda bad_number: AlphaResultSnapshot(
                cycle_id="cycle_001",
                entity_id="ENT_001",
                analyzer_type="multi_agent_v1",
                score=0.72,
                confidence=0.81,
                rationale="quality and momentum are aligned",
                similar_cases=[],
                status="ok",
                diagnostics={"role": {"score": bad_number}},
            ),
            "diagnostics",
        ),
        (
            lambda bad_number: PublishBundle(
                cycle_id="cycle_001",
                formal_objects={"world_state": {"ref": "world_state_snapshot/cycle_001"}},
                manifest_candidate={"snapshot_id": "snap_001"},
                audit_payload={"quality": {"score": bad_number}},
                retrospective_seed={"window": "1d"},
            ),
            "audit_payload",
        ),
        (
            lambda bad_number: PublishBundle(
                cycle_id="cycle_001",
                formal_objects={"world_state": {"ref": "world_state_snapshot/cycle_001"}},
                manifest_candidate={"snapshot_id": "snap_001"},
                audit_payload={"actor": "system"},
                retrospective_seed={"quality": {"score": bad_number}},
            ),
            "retrospective_seed",
        ),
    ],
)
def test_schema_any_payloads_reject_non_finite_numbers(
    factory: Callable[[Any], FormalObjectBase],
    field_name: str,
    bad_number: Any,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        factory(bad_number)


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
                formal_objects={"world_state": {"ref": "world_state_snapshot/cycle_001"}},
                manifest_candidate={"snapshot_id": "snap_001"},
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


def test_schema_contract_builds_one_valid_cycle_across_formal_objects() -> None:
    cycle_id = "cycle_contract"
    feature_bundle = FeatureSignalBundle(
        cycle_id=cycle_id,
        entity_id="ENT_001",
        feature_values={"momentum": 0.42},
        signal_values={},
        graph_features={},
        feature_weight_multiplier={"momentum": 1.0},
    )
    world_state = WorldStateSnapshot(
        cycle_id=cycle_id,
        baseline_regime="neutral",
        llm_delta=0,
        final_regime="neutral",
        llm_rationale="contract fixture",
        actual_model_used="static",
        actual_provider="local",
        fallback_path=[],
    )
    pool = OfficialAlphaPool(
        cycle_id=cycle_id,
        observation_pool_size=1,
        official_alpha_pool_capacity=1,
        selected_entities=["ENT_001"],
        added_entities=["ENT_001"],
        removed_entities=[],
        freeze_reason_map={},
    )
    alpha = AlphaResultSnapshot(
        cycle_id=cycle_id,
        entity_id="ENT_001",
        analyzer_type="single_prompt_v1",
        score=0.72,
        confidence=0.81,
        rationale="quality and momentum are aligned",
        similar_cases=[],
        status="ok",
    )
    recommendation = RecommendationSnapshot(
        cycle_id=cycle_id,
        entity_id="ENT_001",
        action_type="buy",
        rating="A",
        confidence=0.81,
        triggered_by="system",
        override_applied=False,
        constraints_applied={},
    )
    committed = (
        CommittedFormalObject(
            object_key="world_state_snapshot",
            ref=f"world_state_snapshot/{cycle_id}/ref",
            snapshot_id="world-snapshot",
            payload_hash="world-hash",
            row_count=1,
        ),
        CommittedFormalObject(
            object_key="official_alpha_pool",
            ref=f"official_alpha_pool/{cycle_id}/ref",
            snapshot_id="pool-snapshot",
            payload_hash="pool-hash",
            row_count=1,
        ),
        CommittedFormalObject(
            object_key="alpha_result_snapshot",
            ref=f"alpha_result_snapshot/{cycle_id}/ref",
            snapshot_id="alpha-snapshot",
            payload_hash="alpha-hash",
            row_count=1,
        ),
        CommittedFormalObject(
            object_key="recommendation_snapshot",
            ref=f"recommendation_snapshot/{cycle_id}/ref",
            snapshot_id="recommendation-snapshot",
            payload_hash="recommendation-hash",
            row_count=1,
        ),
    )
    manifest = ManifestWriteResult(
        manifest_ref="pg://cycle_publish_manifest/42",
        manifest_version="v1",
        table_snapshots={
            committed_object.object_key: committed_object.snapshot_id
            for committed_object in committed
        },
    )

    bundle = PublishBundle(
        cycle_id=cycle_id,
        formal_objects={
            "world_state_snapshot": {
                "ref": committed[0].ref,
                "payload": world_state.model_dump(mode="json"),
                "count": 1,
            },
            "official_alpha_pool": {
                "ref": committed[1].ref,
                "payload": pool.model_dump(mode="json"),
                "count": 1,
            },
            "alpha_result_snapshot": {
                "ref": committed[2].ref,
                "payload": [alpha.model_dump(mode="json")],
                "count": 1,
            },
            "recommendation_snapshot": {
                "ref": committed[3].ref,
                "payload": [recommendation.model_dump(mode="json")],
                "count": 1,
            },
        },
        manifest_candidate={
            "cycle_id": cycle_id,
            "manifest_ref": manifest.manifest_ref,
            "object_refs": {
                committed_object.object_key: committed_object.ref
                for committed_object in committed
            },
        },
        audit_payload={"cycle_id": cycle_id},
        retrospective_seed={"cycle_id": cycle_id},
    )

    assert feature_bundle.cycle_id == bundle.cycle_id
    assert bundle.manifest_candidate["manifest_ref"] == "pg://cycle_publish_manifest/42"
