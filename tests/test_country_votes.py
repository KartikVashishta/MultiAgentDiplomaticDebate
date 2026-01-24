from datetime import datetime, timezone

from madd.agents import country as country_agent
from madd.core.schemas import Clause, ClauseStatus, Citation, CountryFacts, CountryProfile, TreatyDraft
from madd.core.scenario import Scenario
from madd.core.state import create_initial_state


class FakeLLM:
    def __init__(self, *args, **kwargs):
        self.schema = None

    def with_structured_output(self, schema, method=None):
        self.schema = schema
        return self

    def invoke(self, messages):
        return self.schema(
            public_statement="We support maritime safety.",
            clause_votes={},
            citation_ids_to_reference=["cite_a"],
        )


def test_missing_votes_default_to_abstain(monkeypatch):
    cite = Citation(
        id="cite_a",
        title="UNCLOS",
        url="https://un.org/los",
        snippet="Law of the Sea framework.",
        retrieved_at=datetime.now(timezone.utc),
    )
    profile = CountryProfile(facts=CountryFacts(name="A", scenario_citations=[cite]))
    scenario = Scenario(
        name="Test",
        description="Test",
        countries=["A", "B"],
        max_rounds=2,
    )
    state = create_initial_state(scenario)
    state["round"] = 2
    state["profiles"] = {"A": profile}
    treaty = TreatyDraft()
    treaty.clauses = [
        Clause(
            id="C1",
            text="Prior clause",
            proposed_by="B",
            proposed_round=1,
            status=ClauseStatus.PROPOSED,
            supporters=["B"],
        )
    ]
    state["treaty"] = treaty

    monkeypatch.setattr(country_agent, "ChatOpenAI", FakeLLM)

    msg = country_agent.generate_turn(state, "A")

    assert msg.clause_votes.get("C1") == "abstain"
