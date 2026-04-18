"""Shared L7 recommendation rules."""

from __future__ import annotations

from main_core.common.schemas import ActionType

ACTION_RATING_MAP: dict[str, str] = {
    "buy": "A",
    "hold": "B",
    "reduce": "C",
}


def rating_for_action(action_type: ActionType | str) -> str:
    """Map a conclusive recommendation action to its formal rating."""

    return ACTION_RATING_MAP[str(action_type)]


__all__ = ["ACTION_RATING_MAP", "rating_for_action"]
