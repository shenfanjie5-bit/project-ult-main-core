"""Tests for DashboardSnapshot, FormalReport, and OverrideRecord."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from main_core.common.schemas import (
    DashboardSnapshot,
    FormalObjectBase,
    FormalReport,
    OverrideRecord,
)


def _dashboard() -> DashboardSnapshot:
    return DashboardSnapshot(
        cycle_id="cycle-20260417",
        world_state_ref="world-state/cycle-20260417",
        pool_ref="pool/cycle-20260417",
        recommendation_ref="recommendation/cycle-20260417",
        summary_cards={"top_actions": ["ENT_001"]},
    )


def _report() -> FormalReport:
    return FormalReport(
        cycle_id="cycle-20260417",
        report_type="daily",
        recommendation_ref="recommendation/cycle-20260417",
        narrative_sections={"overview": "Risk appetite improved."},
        appendix_refs={"audit": "audit/cycle-20260417"},
    )


def _override() -> OverrideRecord:
    return OverrideRecord(
        cycle_id="cycle-20260417",
        entity_id="ENT_001",
        submitted_by="analyst@example.com",
        action_type="hold",
        rationale="Human review reduced conviction.",
        submitted_at=datetime(2026, 4, 17, tzinfo=UTC),
    )


def test_dashboard_happy_path_and_round_trip() -> None:
    dashboard = _dashboard()

    assert isinstance(dashboard, FormalObjectBase)
    assert DashboardSnapshot.from_json(dashboard.to_json()) == dashboard


def test_dashboard_rejects_missing_required_field() -> None:
    payload = _dashboard().model_dump()
    payload.pop("summary_cards")

    with pytest.raises(ValidationError):
        DashboardSnapshot(**payload)


def test_dashboard_rejects_extra_field() -> None:
    payload = _dashboard().model_dump()
    payload["unexpected"] = "forbidden"

    with pytest.raises(ValidationError):
        DashboardSnapshot(**payload)


def test_formal_report_happy_path_and_round_trip() -> None:
    report = _report()

    assert isinstance(report, FormalObjectBase)
    assert FormalReport.from_json(report.to_json()) == report


def test_formal_report_rejects_missing_required_field() -> None:
    payload = _report().model_dump()
    payload.pop("narrative_sections")

    with pytest.raises(ValidationError):
        FormalReport(**payload)


def test_formal_report_rejects_wrong_json_field_type() -> None:
    payload = _report().model_dump()
    payload["appendix_refs"] = []

    with pytest.raises(ValidationError):
        FormalReport(**payload)


def test_override_record_happy_path_and_round_trip() -> None:
    override = _override()

    assert isinstance(override, FormalObjectBase)
    assert OverrideRecord.from_json(override.to_json()) == override


def test_override_record_rejects_missing_required_field() -> None:
    payload = _override().model_dump()
    payload.pop("submitted_by")

    with pytest.raises(ValidationError):
        OverrideRecord(**payload)


def test_override_record_rejects_unknown_action_type() -> None:
    payload = _override().model_dump()
    payload["action_type"] = "sell"

    with pytest.raises(ValidationError):
        OverrideRecord(**payload)
