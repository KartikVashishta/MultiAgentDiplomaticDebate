from madd.core.graph import _compile_treaty
from madd.core.schemas import Clause, ClauseStatus, DebateMessage, ProposedClause, TreatyDraft
from madd.core.scenario import Scenario
from madd.core.state import create_initial_state


def test_amended_clause_stays_proposed():
    scenario = Scenario(
        name="Test",
        description="Test",
        countries=["A", "B", "C"],
        max_rounds=3,
    )
    state = create_initial_state(scenario)
    state["round"] = 2
    treaty = TreatyDraft()
    treaty.clauses = [
        Clause(
            id="C1",
            text="Original clause",
            proposed_by="A",
            proposed_round=1,
            status=ClauseStatus.PROPOSED,
            supporters=["A"],
        )
    ]
    state["treaty"] = treaty
    state["messages"] = [
        DebateMessage(
            round_number=2,
            country="B",
            public_statement="Statement",
            proposed_clauses=[],
            clause_votes={"C1": "amend"},
            references_used=[],
        ),
        DebateMessage(
            round_number=2,
            country="C",
            public_statement="Statement",
            proposed_clauses=[],
            clause_votes={"C1": "amend"},
            references_used=[],
        ),
    ]

    updates = _compile_treaty(state)
    updated = updates["treaty"].clauses[0]

    assert updated.status == ClauseStatus.PROPOSED
    assert updated.resolved_round is None
    assert updated.amendments
