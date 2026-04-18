"""L7 package — recommendation work; see §14 of main-core.project-doc.md."""

from main_core.l7_recommendation.constraints import DefaultConstraintProvider
from main_core.l7_recommendation.override import (
    InMemoryOverrideStore,
    OverrideStore,
    apply_override,
    find_override,
    submit_override,
)
from main_core.l7_recommendation.rules import action_for_score, rating_for_action
from main_core.l7_recommendation.service import generate_recommendations

__all__ = [
    "DefaultConstraintProvider",
    "InMemoryOverrideStore",
    "OverrideStore",
    "apply_override",
    "action_for_score",
    "find_override",
    "generate_recommendations",
    "rating_for_action",
    "submit_override",
]
