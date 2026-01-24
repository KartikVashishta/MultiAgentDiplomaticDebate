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
        fields = getattr(self.schema, "model_fields", {}) if self.schema else {}
        if "public_statement" in fields:
            return self.schema(
                public_statement="We support UNCLOS-based navigation rules.",
                clause_votes={},
                citation_ids_to_reference=[],
            )
        return self.schema(citation_ids_to_reference=["cite_a"])


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


class RewriteLLM:
    def __init__(self, *args, **kwargs):
        self.schema = None
        self.calls = 0

    def with_structured_output(self, schema, method=None):
        self.schema = schema
        return self

    def invoke(self, messages):
        self.calls += 1
        fields = getattr(self.schema, "model_fields", {}) if self.schema else {}
        if "public_statement" in fields and "citation_ids_to_reference" in fields:
            return self.schema(
                public_statement="We request a joint study and propose mechanisms.",
                clause_votes={},
                citation_ids_to_reference=[],
            )
        if "citation_ids_to_reference" in fields:
            return self.schema(citation_ids_to_reference=[])
        return self.schema(public_statement="We propose a study and conditional cooperation.")


def test_second_pass_rewrite_when_no_citations(monkeypatch):
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

    monkeypatch.setattr(country_agent, "ChatOpenAI", RewriteLLM)

    msg = country_agent.generate_turn(state, "TestLand")

    assert "propose" in msg.public_statement.lower()
    assert msg.references_used == []
