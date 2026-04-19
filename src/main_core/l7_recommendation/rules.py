"""Shared L7 recommendation business rules."""

from __future__ import annotations

from datetime import datetime

from main_core.common.schemas import ActionType, OverrideRecord

_ACTION_RATINGS: dict[ActionType, str | None] = {
    "buy": "A",
    "hold": "B",
    "reduce": "C",
    "inconclusive": None,
}


def rating_for_action(action_type: ActionType) -> str | None:
    """Return the formal rating implied by an L7 action."""

    return _ACTION_RATINGS[action_type]


def override_recency_key(
    override: OverrideRecord,
    insertion_index: int,
) -> tuple[datetime, int]:
    """Order duplicate overrides by submitted time, then insertion order."""

    return (override.submitted_at, insertion_index)


__all__ = ["override_recency_key", "rating_for_action"]
