"""Tests for PublishBundle and schema exports."""

from __future__ import annotations

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


def _publish_bundle() -> PublishBundle:
    return PublishBundle(
        cycle_id="cycle-20260417",
        formal_objects={"world_state": {"ref": "world-state/cycle-20260417"}},
        manifest_candidate={"formal_table_snapshots": {"world_state": "snapshot-1"}},
        audit_payload={"actor": "system"},
        retrospective_seed={"cycle_id": "cycle-20260417"},
    )


def test_publish_bundle_happy_path_and_round_trip() -> None:
    bundle = _publish_bundle()

    assert isinstance(bundle, FormalObjectBase)
    assert PublishBundle.from_json(bundle.to_json()) == bundle


def test_publish_bundle_rejects_missing_required_field() -> None:
    payload = _publish_bundle().model_dump()
    payload.pop("manifest_candidate")

    with pytest.raises(ValidationError):
        PublishBundle(**payload)


def test_publish_bundle_rejects_wrong_payload_type() -> None:
    payload = _publish_bundle().model_dump()
    payload["formal_objects"] = []

    with pytest.raises(ValidationError):
        PublishBundle(**payload)


def test_schema_package_reexports_expected_models() -> None:
    exported_models = (
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

    assert all(issubclass(model, FormalObjectBase) for model in exported_models)
    assert all(model.model_config["extra"] == "forbid" for model in exported_models)
    assert all(model.model_config["frozen"] is True for model in exported_models)
    assert all(model.model_config["strict"] is True for model in exported_models)
