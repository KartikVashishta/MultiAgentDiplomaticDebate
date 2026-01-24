from datetime import datetime, timezone

from madd.agents import country as country_agent
from madd.core.schemas import Citation, CountryFacts, CountryProfile, TreatyDraft
from madd.core.scenario import Scenario
from madd.core.state import create_initial_state


class FakeLLM:
    def __init__(self, *args, **kwargs):
        self.schema = None

    def with_structured_output(self, schema, method=None):
        self.schema = schema
        return self

    def invoke(self, messages):
        payload = dict(
            public_statement="We support cooperative frameworks for resource development and safety",
            clause_votes={},
            citation_ids_to_reference=["cite_a"],
        )
        if self.schema is None:
            return type("StructuredOutput", (), payload)
        return self.schema(**payload)


def test_truncation_flag_set(monkeypatch):
    cite = Citation(
        id="cite_a",
        title="UNCLOS",
        url="https://un.org/los",
        snippet="Law of the Sea framework.",
        topic="Test",
        retrieved_at=datetime.now(timezone.utc),
    )
    profile = CountryProfile(facts=CountryFacts(name="A", scenario_citations=[cite]))
    scenario = Scenario(
        name="Test",
        description="Test",
        countries=["A", "B"],
        max_rounds=1,
    )
    state = create_initial_state(scenario)
    state["round"] = 1
    state["profiles"] = {"A": profile}
    state["treaty"] = TreatyDraft()

    monkeypatch.setattr(country_agent, "ChatOpenAI", FakeLLM)

    msg = country_agent.generate_turn(state, "A")

    assert msg.is_truncated is True
    assert msg.truncation_note
