from datetime import datetime, timezone
from types import SimpleNamespace

from madd.agents import judge as judge_agent
from madd.core.schemas import Clause, ClauseStatus, DebateMessage, TreatyDraft
from madd.core.scenario import Scenario
from madd.core.state import create_initial_state


class FakeLLM:
    def __init__(self, *args, **kwargs):
        self.schema = SimpleNamespace

    def with_structured_output(self, schema, method=None):
        self.schema = schema
        return self

    def invoke(self, messages):
        return self.schema(
            scores=[
                judge_agent.ScoreOut(
                    country="A",
                    score=7.0,
                    reasoning="Reasoning",
                    diplomatic_effectiveness=7.0,
                    negotiation_willingness=7.0,
                    communication_clarity=7.0,
                    treaty_contribution=5.0,
                )
            ],
            rankings=["A"],
            summary="Summary",
        )


def test_clause_accounting_fields(monkeypatch):
    scenario = Scenario(
        name="Test",
        description="Test",
        countries=["A", "B"],
        max_rounds=2,
    )
    state = create_initial_state(scenario)
    state["round"] = 2
    state["messages"] = [
        DebateMessage(
            round_number=2,
            country="A",
            public_statement="Statement.",
            references_used=[],
            timestamp=datetime.now(timezone.utc),
        )
    ]
    treaty = TreatyDraft()
    treaty.clauses = [
        Clause(id="C1", text="Clause 1", proposed_by="A", proposed_round=1, status=ClauseStatus.ACCEPTED, resolved_round=2),
        Clause(id="C2", text="Clause 2", proposed_by="B", proposed_round=2, status=ClauseStatus.PROPOSED),
    ]
    state["treaty"] = treaty

    monkeypatch.setattr(judge_agent, "ChatOpenAI", FakeLLM)

    scorecard = judge_agent.evaluate_round(state)

    assert scorecard.clauses_proposed_this_round == 1
    assert scorecard.clauses_accepted_this_round == 1
    assert scorecard.clauses_accepted_cumulative == 1
    assert scorecard.clauses_pending_cumulative == 1
    assert scorecard.clauses_total_unique_cumulative == 2
    assert scorecard.scores[0].diplomatic_effectiveness == 7.0
