from datetime import datetime, timezone

from madd.agents import verifier as verifier_agent
from madd.core.schemas import Citation, CountryFacts, CountryProfile, DebateMessage
from madd.core.scenario import Scenario
from madd.core.state import create_initial_state


class FakeLLM:
    def __init__(self, *args, **kwargs):
        self.schema = None

    def with_structured_output(self, schema, method=None):
        self.schema = schema
        return self

    def invoke(self, messages):
        findings = [verifier_agent.FindingOutput(
            severity="warning",
            category="inconsistency",
            description="Profile leaders empty but negotiator speaks.",
            country="TestLand",
            evidence=["Leaders: []", "The delegation states..."],
        )]
        if self.schema is None:
            class Response:
                def __init__(self, findings):
                    self.findings = findings
            return Response(findings)
        return self.schema(findings=findings)


def test_verifier_dedupes_and_ignores_leader_false_positive(monkeypatch):
    cite = Citation(
        id="cite_a",
        title="UNCLOS",
        url="https://un.org/los",
        snippet="Law of the Sea framework.",
        topic="Maritime law",
        retrieved_at=datetime.now(timezone.utc),
    )
    profile = CountryProfile(facts=CountryFacts(name="TestLand", scenario_citations=[cite]))
    scenario = Scenario(
        name="Test",
        description="Test",
        countries=["TestLand", "OtherLand"],
        max_rounds=1,
    )
    state = create_initial_state(scenario)
    state["round"] = 1
    state["profiles"] = {"TestLand": profile}
    state["messages"] = [
        DebateMessage(
            round_number=1,
            country="TestLand",
            public_statement="The delegation states its position.",
            references_used=["cite_a"],
        )
    ]

    monkeypatch.setattr(verifier_agent, "ChatOpenAI", FakeLLM)

    findings = verifier_agent.verify_claims(state)

    assert findings == []


def test_gdp_formatting_unknown():
    profile = CountryProfile(facts=CountryFacts(name="TestLand"))
    facts = verifier_agent._format_facts(profile)
    assert "NoneB" not in facts
    assert "GDP: Unknown" in facts
