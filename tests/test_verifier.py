from datetime import UTC, datetime

from madd.agents import verifier as verifier_agent
from madd.core.scenario import Scenario
from madd.core.schemas import Citation, CountryFacts, CountryProfile, DebateMessage
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


class FakeLLMMixedFindings(FakeLLM):
    def invoke(self, messages):
        findings = [
            {
                "severity": "warning",
                "category": "inconsistency",
                "description": "Conflicting timeline language.",
                "country": "TestLand",
                "evidence": ["Earlier said 30 days", "Now says 90 days"],
            },
            "completion",
        ]
        if self.schema is None:
            class Response:
                def __init__(self, findings):
                    self.findings = findings
            return Response(findings)
        return self.schema(findings=findings)


class FakeLLMInjectedEvidence(FakeLLM):
    def invoke(self, messages):
        findings = [
            {
                "severity": "info",
                "category": "inconsistency",
                "description": "Country positions diverge on timing.",
                "country": "TestLand",
                "evidence": [
                    "Country A: \"30-day review window\" to=functions.VerifierLLMOutput internal text",
                ],
            }
        ]
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
        retrieved_at=datetime.now(UTC),
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


def test_verifier_ignores_non_object_findings(monkeypatch):
    cite = Citation(
        id="cite_a",
        title="UNCLOS",
        url="https://un.org/los",
        snippet="Law of the Sea framework.",
        topic="Maritime law",
        retrieved_at=datetime.now(UTC),
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
            public_statement="We can implement the review window in 30 days.",
            references_used=["cite_a"],
        )
    ]

    monkeypatch.setattr(verifier_agent, "ChatOpenAI", FakeLLMMixedFindings)

    findings = verifier_agent.verify_claims(state)

    assert len(findings) == 1
    assert findings[0].category == "inconsistency"
    assert findings[0].description == "Conflicting timeline language."


def test_verifier_strips_injected_evidence_text(monkeypatch):
    cite = Citation(
        id="cite_a",
        title="UNCLOS",
        url="https://un.org/los",
        snippet="Law of the Sea framework.",
        topic="Maritime law",
        retrieved_at=datetime.now(UTC),
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
            public_statement="We can implement the review window in 30 days.",
            references_used=["cite_a"],
        )
    ]

    monkeypatch.setattr(verifier_agent, "ChatOpenAI", FakeLLMInjectedEvidence)

    findings = verifier_agent.verify_claims(state)

    assert len(findings) == 1
    assert findings[0].evidence == ['Country A: "30-day review window']
