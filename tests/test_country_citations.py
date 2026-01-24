from datetime import datetime, timezone

from madd.core.schemas import Citation, CountryFacts, CountryProfile, EconomicData, TreatyDraft
from madd.core.scenario import Scenario
from madd.core.state import create_initial_state
from madd.agents import country as country_agent


class FakeLLM:
    def __init__(self, *args, **kwargs):
        self.schema = None

    def with_structured_output(self, schema, method=None):
        self.schema = schema
        return self

    def invoke(self, messages):
        return self.schema(
            public_statement="We support UNCLOS-based navigation rules.",
            clause_votes={},
            citation_ids_to_reference=[],
        )


def test_generate_turn_enforces_citations(monkeypatch):
    cite1 = Citation(
        id="cite_a",
        title="UNCLOS",
        url="https://un.org/los",
        snippet="Law of the Sea framework.",
        retrieved_at=datetime.now(timezone.utc),
        topic="maritime_law",
    )
    facts = CountryFacts(
        name="TestLand",
        scenario_citations=[cite1],
        economy=EconomicData(),
    )
    profile = CountryProfile(facts=facts)

    scenario = Scenario(
        name="Test",
        description="Test",
        countries=["TestLand", "OtherLand"],
        max_rounds=1,
    )
    state = create_initial_state(scenario)
    state["round"] = 1
    state["profiles"] = {"TestLand": profile}
    state["treaty"] = TreatyDraft()

    monkeypatch.setattr(country_agent, "ChatOpenAI", FakeLLM)

    msg = country_agent.generate_turn(state, "TestLand")

    assert msg.references_used
    assert msg.references_used[0] == "cite_a"
