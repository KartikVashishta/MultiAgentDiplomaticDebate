from datetime import datetime, timezone

from madd.core.graph import build_graph, _compile_treaty
from madd.core.schemas import (
    Citation,
    CountryProfile,
    CountryFacts,
    DebateMessage,
    ProposedClause,
    RoundScorecard,
    TreatyDraft,
)
from madd.core.scenario import Scenario
from madd.core.state import create_initial_state


def _make_profile(country: str) -> CountryProfile:
    cite = Citation(
        id=f"cite_{country.lower()}",
        title="UNCLOS",
        url="https://un.org/los",
        snippet="Law of the Sea framework.",
    )
    facts = CountryFacts(name=country, scenario_citations=[cite])
    return CountryProfile(facts=facts)


def test_graph_runs_all_rounds(monkeypatch):
    scenario = Scenario(
        name="Test",
        description="Test scenario",
        countries=["A", "B", "C"],
        max_rounds=3,
    )
    state = create_initial_state(scenario)

    def fake_ensure_profile(country, scenario_description, scenario_name=None, scenario_key=None):
        return _make_profile(country)

    def fake_generate_turn(state, country):
        profile = state["profiles"][country]
        cite_id = profile.all_citations()[0].id
        proposed = []
        if state["round"] == 1:
            proposed = [ProposedClause(text=f"Clause from {country}")]
        return DebateMessage(
            round_number=state["round"],
            country=country,
            public_statement=f"{country} statement",
            proposed_clauses=proposed,
            clause_votes={},
            references_used=[cite_id],
            timestamp=datetime.now(timezone.utc),
        )

    def fake_evaluate_round(state):
        return RoundScorecard(round_number=state["round"])

    def fake_verify_claims(state):
        return []

    monkeypatch.setattr("madd.core.graph.ensure_profile", fake_ensure_profile)
    monkeypatch.setattr("madd.core.graph.generate_turn", fake_generate_turn)
    monkeypatch.setattr("madd.core.graph.evaluate_round", fake_evaluate_round)
    monkeypatch.setattr("madd.core.graph.verify_claims", fake_verify_claims)

    graph = build_graph()
    final_state = graph.invoke(state)

    assert final_state["round"] == 3
    assert len(final_state["messages"]) == 9
    assert len(final_state["scorecards"]) == 3


def test_clause_counter_increments():
    scenario = Scenario(
        name="Test",
        description="Test scenario",
        countries=["A", "B"],
        max_rounds=1,
    )
    state = create_initial_state(scenario)
    state["round"] = 1
    state["treaty"] = TreatyDraft()
    state["clause_counter"] = 2
    state["messages"] = [
        DebateMessage(
            round_number=1,
            country="A",
            public_statement="Statement",
            proposed_clauses=[ProposedClause(text="New clause")],
            references_used=[],
        )
    ]

    updates = _compile_treaty(state)
    updated_treaty = updates["treaty"]

    assert updates["clause_counter"] == 3
    assert updated_treaty.clauses[-1].id == "C3"
