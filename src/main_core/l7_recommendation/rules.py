"""Shared deterministic L7 recommendation rules."""

from __future__ import annotations

from main_core.common.schemas import ActionType

BUY_SCORE_THRESHOLD = 0.65
REDUCE_SCORE_THRESHOLD = 0.35

_RATING_BY_ACTION: dict[str, str] = {
    "buy": "A",
    "hold": "B",
    "reduce": "C",
}


def action_for_score(score: float) -> ActionType:
    """Map a validated alpha score into the deterministic action bucket."""

    if score >= BUY_SCORE_THRESHOLD:
        return "buy"
    if score <= REDUCE_SCORE_THRESHOLD:
        return "reduce"
    return "hold"


def rating_for_action(action_type: ActionType | str) -> str:
    """Map a non-inconclusive recommendation action to its formal rating."""

    return _RATING_BY_ACTION[str(action_type)]


__all__ = [
    "BUY_SCORE_THRESHOLD",
    "REDUCE_SCORE_THRESHOLD",
    "action_for_score",
    "rating_for_action",
]
