from datetime import datetime, timezone

from madd.core.scenario import Scenario, AgendaItem
from madd.core.scenario_router import build_router_plan, DEFAULT_INSTITUTION_NAME, RouterPlan
from madd.agents import researcher as researcher_agent
from madd.agents import country as country_agent
from madd.core.schemas import Citation, CountryFacts, CountryProfile, TreatyDraft
from madd.core.state import create_initial_state


def _score_for(plan, archetype: str) -> float:
    for item in plan.archetypes:
        if item.archetype == archetype:
            return item.score
    return 0.0


def test_router_detects_archetypes_greenland():
    scenario = Scenario(
        name="Greenland Security and Critical Minerals",
        description=(
            "Strategic location and critical-minerals potential with defense access "
            "and safeguards for environment and Indigenous communities."
        ),
        countries=["Denmark", "United States"],
        max_rounds=3,
        agenda=[
            AgendaItem(
                topic="Defense access and updated basing arrangements",
                description="Review defense framework and de-escalation protocols",
                priority=1,
            ),
            AgendaItem(
                topic="Critical minerals investment and supply-chain guarantees",
                description="Licensing, financing, local value creation, and offtake",
                priority=2,
            ),
            AgendaItem(
                topic="Environmental, Indigenous, and community safeguards",
                description="ESIA standards and consultation mechanisms",
                priority=3,
            ),
        ],
    )
    plan = build_router_plan(scenario)

    assert _score_for(plan, "SECURITY_DEFENSE") > 0.4
    assert _score_for(plan, "RESOURCES_MINERALS") > 0.4
    assert _score_for(plan, "ENVIRONMENT_CLIMATE") > 0.4
    assert _score_for(plan, "HUMAN_RIGHTS_COMMUNITY") > 0.4


def test_router_institution_detection():
    scenario = Scenario(
        name="Test",
        description="Negotiations will be overseen by MMSAC for reporting.",
        countries=["A", "B"],
        max_rounds=1,
    )
    plan = build_router_plan(scenario)
    assert plan.institution_name == "MMSAC"


def test_router_defaults_to_joc():
    scenario = Scenario(
        name="Test",
        description="No named institution provided.",
        countries=["A", "B"],
        max_rounds=1,
    )
    plan = build_router_plan(scenario)
    assert plan.institution_name == DEFAULT_INSTITUTION_NAME


class FakeResearchLLM:
    def __init__(self, *args, **kwargs):
        self.schema = None

    def with_structured_output(self, schema, method=None):
        self.schema = schema
        return self

    def invoke(self, messages):
        return self.schema(name="TestLand")


def test_research_uses_router_topics(monkeypatch):
    captured = {}

    def fake_search(country_name, topic_key, query_hint=None, allowed_domains=None, scenario_context=None):
        captured["topic_key"] = topic_key
        captured["allowed_domains"] = allowed_domains
        return "", []

    plan = RouterPlan(
        research_topics={"law": "treaty law"},
        topic_domains={"law": ["un.org"]},
    )

    monkeypatch.setattr(researcher_agent, "search_country_info", fake_search)
    monkeypatch.setattr(researcher_agent, "ChatOpenAI", FakeResearchLLM)

    researcher_agent.generate_profile(
        "TestLand",
        "Test scenario",
        scenario_name="Test",
        router_plan=plan,
    )

    assert captured["topic_key"] == "law"
    assert captured["allowed_domains"] == ["un.org"]


class PromptCaptureLLM:
    last_instance = None

    def __init__(self, *args, **kwargs):
        self.schema = None
        self.system_prompt = ""
        PromptCaptureLLM.last_instance = self

    def with_structured_output(self, schema, method=None):
        self.schema = schema
        return self

    def invoke(self, messages):
        if not self.system_prompt:
            for msg in messages:
                if hasattr(msg, "content") and "Scenario Router Patch" in msg.content:
                    self.system_prompt = msg.content
                    break
        fields = getattr(self.schema, "model_fields", {}) if self.schema else {}
        if "public_statement" in fields:
            return self.schema(
                public_statement="We propose a joint framework.",
                clause_votes={},
                citation_ids_to_reference=["cite_a"],
            )
        return self.schema(citation_ids_to_reference=["cite_a"])


def test_country_prompt_includes_patch(monkeypatch):
    cite = Citation(
        id="cite_a",
        title="Test",
        url="https://example.com",
        snippet="Snippet",
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
    state["router_plan"] = RouterPlan(turn_prompt_patch="PATCH_TEST")

    monkeypatch.setattr(country_agent, "ChatOpenAI", PromptCaptureLLM)

    country_agent.generate_turn(state, "A")

    captured = PromptCaptureLLM.last_instance.system_prompt
    assert "PATCH_TEST" in captured
