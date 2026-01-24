import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from madd.core.schemas import (
    Citation, CountryProfile, CountryFacts, CountryStrategy, EconomicData,
    Clause, ClauseStatus, TreatyDraft, DebateMessage, ProposedClause,
)
from madd.core.scenario import Scenario, load_scenario, AgendaItem
from madd.core.state import create_initial_state


def test_citation_schema():
    c = Citation(title="Test", url="https://example.com", snippet="snippet")
    assert c.title == "Test"
    assert c.retrieved_at is not None


def test_country_profile_all_citations():
    facts = CountryFacts(
        name="Test",
        economy=EconomicData(citations=[Citation(title="GDP", url="https://a.com", snippet="x")]),
        citations=[Citation(title="Treaty", url="https://b.com", snippet="y")],
        leaders_citations=[Citation(title="Leader", url="https://c.com", snippet="z")],
    )
    profile = CountryProfile(facts=facts)
    all_cites = profile.all_citations()
    assert len(all_cites) == 3


def test_scenario_load(tmp_path):
    yaml_content = """
name: "Test Scenario"
description: "A test"
countries:
  - USA
  - China
max_rounds: 2
"""
    scenario_file = tmp_path / "test.yaml"
    scenario_file.write_text(yaml_content)
    
    scenario = load_scenario(scenario_file)
    assert scenario.name == "Test Scenario"
    assert len(scenario.countries) == 2
    assert scenario.max_rounds == 2


def test_initial_state():
    scenario = Scenario(
        name="Test",
        description="Desc",
        countries=["A", "B"],
        max_rounds=3,
    )
    state = create_initial_state(scenario)
    assert state["round"] == 0
    assert state["max_rounds"] == 3
    assert state["profiles"] == {}


def test_treaty_compilation():
    treaty = TreatyDraft()
    
    c1 = Clause(id="C1", text="Clause 1", proposed_by="A", proposed_round=1)
    c1.supporters = ["A", "B"]
    c1.status = ClauseStatus.ACCEPTED
    
    c2 = Clause(id="C2", text="Clause 2", proposed_by="B", proposed_round=1)
    c2.objectors = ["A"]
    c2.status = ClauseStatus.REJECTED
    
    treaty.clauses = [c1, c2]
    
    assert len(treaty.accepted_clauses) == 1
    assert treaty.accepted_clauses[0].id == "C1"
    assert len(treaty.pending_clauses) == 0


def test_debate_message_references():
    msg = DebateMessage(
        round_number=1,
        country="Test",
        public_statement="Statement",
        references_used=["https://example.com/source1"],
    )
    assert len(msg.references_used) == 1
