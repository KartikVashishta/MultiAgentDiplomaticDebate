from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from madd.core.schemas import (
    AuditFinding,
    CountryProfile,
    DebateMessage,
    RoundScorecard,
    TreatyDraft,
)
from madd.core.scenario import Scenario


class DebateState(TypedDict):
    scenario: Scenario
    round: int
    profiles: dict[str, CountryProfile]
    treaty: TreatyDraft
    messages: Annotated[list[DebateMessage], add_messages]
    scorecards: list[RoundScorecard]
    audit: list[AuditFinding]
    max_rounds: int


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
    )
