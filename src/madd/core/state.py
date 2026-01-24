import operator
from typing import Annotated, TypedDict

from madd.core.schemas import (
    AuditFinding,
    CountryProfile,
    DebateMessage,
    RoundScorecard,
    TreatyDraft,
)
from madd.core.scenario import Scenario
from madd.core.scenario_router import RouterPlan


def _merge_profiles(existing: dict, new: dict) -> dict:
    merged = dict(existing)
    merged.update(new)
    return merged


class DebateState(TypedDict):
    scenario: Scenario
    round: int
    profiles: Annotated[dict[str, CountryProfile], _merge_profiles]
    treaty: TreatyDraft
    messages: Annotated[list[DebateMessage], operator.add]
    scorecards: Annotated[list[RoundScorecard], operator.add]
    audit: Annotated[list[AuditFinding], operator.add]
    max_rounds: int
    clause_counter: int
    router_plan: RouterPlan | None
    treaty_text: str | None


def create_initial_state(scenario: Scenario) -> DebateState:
    return DebateState(
        scenario=scenario,
        round=0,
        profiles={},
        treaty=TreatyDraft(),
        messages=[],
        scorecards=[],
        audit=[],
        max_rounds=scenario.max_rounds,
        clause_counter=0,
        router_plan=None,
        treaty_text=None,
    )
