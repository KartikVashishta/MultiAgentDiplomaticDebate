import pytest
from pathlib import Path

from madd.core.schemas import (
    Citation, CountryProfile, CountryFacts, CountryStrategy, EconomicData,
    DebateMessage,
)
from madd.core.scenario import Scenario
from madd.core.state import create_initial_state
from madd.stores.run_store import save_transcript, build_citation_index


def test_transcript_contains_citation_ids(tmp_path):
    cite1 = Citation(
        id="cite_abc1234567",
        title="World Bank GDP Report",
        url="https://worldbank.org/gdp",
        snippet="GDP data for testing",
    )
    cite2 = Citation(
        id="cite_def9876543",
        title="Government Leaders",
        url="https://gov.example/leaders",
        snippet="Leaders info",
    )
    
    facts = CountryFacts(
        name="TestLand",
        economy=EconomicData(citations=[cite1]),
        leaders_citations=[cite2],
    )
    profile = CountryProfile(facts=facts)
    
    scenario = Scenario(
        name="Test Scenario",
        description="Testing",
        countries=["TestLand", "OtherLand"],
        max_rounds=1,
    )
    
    state = create_initial_state(scenario)
    state["profiles"] = {"TestLand": profile}
    state["round"] = 1
    
    msg = DebateMessage(
        round_number=1,
        country="TestLand",
        public_statement="We propose cooperation based on official data.",
        references_used=["cite_abc1234567"],
    )
    state["messages"] = [msg]
    
    transcript_path = save_transcript(state, tmp_path)
    content = transcript_path.read_text()
    
    assert "cite_abc1234567" in content
    assert "[cite_abc1234567]" in content
    assert "Sources:" in content
    assert "## References" in content
    assert "World Bank GDP Report" in content
    assert "https://worldbank.org/gdp" in content


def test_transcript_marks_unknown_ids(tmp_path):
    facts = CountryFacts(name="TestLand")
    profile = CountryProfile(facts=facts)
    
    scenario = Scenario(
        name="Test",
        description="Test",
        countries=["TestLand", "OtherLand"],
        max_rounds=1,
    )
    
    state = create_initial_state(scenario)
    state["profiles"] = {"TestLand": profile}
    state["round"] = 1
    
    msg = DebateMessage(
        round_number=1,
        country="TestLand",
        public_statement="Statement",
        references_used=["unknown_citation_id"],
    )
    state["messages"] = [msg]
    
    transcript_path = save_transcript(state, tmp_path)
    content = transcript_path.read_text()
    
    assert "[unknown_citation_id?]" in content


def test_build_citation_index():
    cite = Citation(id="cite_test123", title="Test", url="https://t.com", snippet="s")
    facts = CountryFacts(name="X", citations=[cite])
    profile = CountryProfile(facts=facts)
    
    scenario = Scenario(name="T", description="D", countries=["X", "Y"], max_rounds=1)
    state = create_initial_state(scenario)
    state["profiles"] = {"X": profile}
    
    index = build_citation_index(state)
    
    assert "cite_test123" in index
    assert index["cite_test123"].title == "Test"
