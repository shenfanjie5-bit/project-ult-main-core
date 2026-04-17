"""Tests for L8 formal object commits and manifest semantics."""

from __future__ import annotations

import pytest

from main_core.common.errors import ManifestPublishError
from main_core.l8_publish import prepare_publish_bundle
from main_core.l8_publish.manifest import (
    build_manifest_candidate,
    commit_formal_objects,
    write_manifest_after_commits,
)
from main_core.l8_publish.refs import (
    ALPHA_RESULT_SNAPSHOT_KEY,
    OFFICIAL_ALPHA_POOL_KEY,
    RECOMMENDATION_SNAPSHOT_KEY,
    WORLD_STATE_SNAPSHOT_KEY,
)
from tests.l8_publish import (
    FakeFormalObjectSource,
    RecordingPublishPort,
    alpha_result,
    pool,
    recommendation,
    world_state,
)


def test_commit_formal_objects_uses_stable_publish_order() -> None:
    formal_objects = {
        RECOMMENDATION_SNAPSHOT_KEY: (recommendation("ENT_A"),),
        ALPHA_RESULT_SNAPSHOT_KEY: (alpha_result("ENT_A"),),
        WORLD_STATE_SNAPSHOT_KEY: world_state(),
        OFFICIAL_ALPHA_POOL_KEY: pool(("ENT_A",)),
    }
    publish_port = RecordingPublishPort()

    committed_objects = commit_formal_objects(
        "cycle_l8",
        formal_objects,
        publish_port,
    )
    manifest = write_manifest_after_commits(
        "cycle_l8",
        committed_objects,
        publish_port,
    )

    assert [call[1] for call in publish_port.commit_calls] == [
        WORLD_STATE_SNAPSHOT_KEY,
        OFFICIAL_ALPHA_POOL_KEY,
        ALPHA_RESULT_SNAPSHOT_KEY,
        RECOMMENDATION_SNAPSHOT_KEY,
    ]
    assert publish_port.manifest_calls == [("cycle_l8", committed_objects)]
    assert manifest.manifest_ref == "manifest/cycle_l8"


def test_build_manifest_candidate_includes_commit_and_manifest_refs() -> None:
    publish_port = RecordingPublishPort()
    committed_objects = commit_formal_objects(
        "cycle_l8",
        {WORLD_STATE_SNAPSHOT_KEY: world_state()},
        publish_port,
    )
    manifest = write_manifest_after_commits("cycle_l8", committed_objects, publish_port)

    candidate = build_manifest_candidate("cycle_l8", committed_objects, manifest)

    assert candidate["object_refs"] == {
        WORLD_STATE_SNAPSHOT_KEY: "world_state_snapshot/cycle_l8/ref",
    }
    assert candidate["manifest_ref"] == "manifest/cycle_l8"
    assert candidate["table_snapshots"] == {
        WORLD_STATE_SNAPSHOT_KEY: "world_state_snapshot-snapshot",
    }


def test_prepare_publish_bundle_does_not_write_manifest_after_commit_failure() -> None:
    publish_port = RecordingPublishPort(fail_on_object_key=ALPHA_RESULT_SNAPSHOT_KEY)

    with pytest.raises(ManifestPublishError, match="failed to commit"):
        prepare_publish_bundle(
            "cycle_l8",
            source=FakeFormalObjectSource(),
            publish_port=publish_port,
        )

    assert [call[1] for call in publish_port.commit_calls] == [
        WORLD_STATE_SNAPSHOT_KEY,
        OFFICIAL_ALPHA_POOL_KEY,
        ALPHA_RESULT_SNAPSHOT_KEY,
    ]
    assert publish_port.manifest_calls == []


def test_prepare_publish_bundle_raises_when_manifest_write_fails() -> None:
    publish_port = RecordingPublishPort(fail_manifest=True)

    with pytest.raises(ManifestPublishError, match="manifest"):
        prepare_publish_bundle(
            "cycle_l8",
            source=FakeFormalObjectSource(),
            publish_port=publish_port,
        )

    assert [call[1] for call in publish_port.commit_calls] == [
        WORLD_STATE_SNAPSHOT_KEY,
        OFFICIAL_ALPHA_POOL_KEY,
        ALPHA_RESULT_SNAPSHOT_KEY,
        RECOMMENDATION_SNAPSHOT_KEY,
    ]
    assert len(publish_port.manifest_calls) == 1
