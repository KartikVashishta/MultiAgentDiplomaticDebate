from datetime import datetime, timezone
from typing import cast, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from madd.core.config import get_settings
from madd.core.schemas import (
    CountryProfile,
    CountryFacts,
    CountryStrategy,
    EconomicData,
    Citation,
)
from madd.tools.web_search import search_country_info


class ProfileLLMOutput(BaseModel):
    name: str
    region: Optional[str] = None
    population: Optional[int] = None
    government_type: Optional[str] = None
    current_leaders: list[str] = []
    gdp_usd_billions: Optional[float] = None
    gdp_year: Optional[int] = None
    gdp_growth_pct: Optional[float] = None
    major_industries: list[str] = []
    trade_partners: list[str] = []
    colonial_history: Optional[str] = None
    major_conflicts: list[str] = []
    treaties: list[str] = []
    international_memberships: list[str] = []
    core_policy_goals: list[str] = []
    alliance_patterns: list[str] = []
    negotiation_style: Optional[str] = None
    negotiation_tactics: list[str] = []
    security_concerns: list[str] = []
    economic_interests: list[str] = []
    key_allies: list[str] = []
    key_rivals: list[str] = []
    red_lines: list[str] = []
    negotiation_priorities: list[str] = []


RESEARCH_TOPICS = {
    "economy": "GDP economy trade industries",
    "leaders": "government president prime minister leaders",
    "alliances": "foreign policy alliances treaties international relations",
    "history": "military conflicts history wars",
}


def generate_profile(country_name: str, scenario_description: str) -> CountryProfile:
    settings = get_settings()
    
    topic_citations: dict[str, list[Citation]] = {}
    research_context = ""
    
    for topic_key, topic_query in RESEARCH_TOPICS.items():
        try:
            text, cites = search_country_info(country_name, topic_query)
            research_context += f"\n{topic_key.upper()}:\n{text}\n"
            topic_citations[topic_key] = cites
        except Exception as e:
            print(f"  Research failed for {topic_key}: {e}")
            topic_citations[topic_key] = []
    
    llm = ChatOpenAI(
        model=settings.research_model,
        temperature=settings.research_temperature,
        api_key=settings.openai_api_key,
        max_retries=settings.max_retries,
    )
    
    structured_llm = llm.with_structured_output(ProfileLLMOutput)
    
    system_prompt = """You are an expert diplomatic researcher.
Generate a country profile based on the research data provided.
Only include information supported by the research context.
If data is not available, leave fields empty/null."""

    user_prompt = f"""Country: {country_name}
Scenario: {scenario_description}

Research Data:
{research_context[:8000]}

Generate the profile fields."""

    try:
        result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        output = cast(ProfileLLMOutput, result)
    except Exception as e:
        print(f"  Profile generation failed: {e}")
        output = ProfileLLMOutput(name=country_name)
    
    now = datetime.now(timezone.utc)
    
    facts = CountryFacts(
        name=output.name,
        region=output.region,
        population=output.population,
        government_type=output.government_type,
        current_leaders=output.current_leaders,
        economy=EconomicData(
            gdp_usd_billions=output.gdp_usd_billions,
            gdp_year=output.gdp_year,
            gdp_growth_pct=output.gdp_growth_pct,
            major_industries=output.major_industries,
            trade_partners=output.trade_partners,
            citations=topic_citations.get("economy", []),
        ),
        colonial_history=output.colonial_history,
        major_conflicts=output.major_conflicts,
        treaties=output.treaties,
        international_memberships=output.international_memberships,
        citations=topic_citations.get("alliances", []),
        leaders_citations=topic_citations.get("leaders", []),
        history_citations=topic_citations.get("history", []),
    )
    
    strategy = CountryStrategy(
        core_policy_goals=output.core_policy_goals,
        alliance_patterns=output.alliance_patterns,
        negotiation_style=output.negotiation_style,
        negotiation_tactics=output.negotiation_tactics,
        security_concerns=output.security_concerns,
        economic_interests=output.economic_interests,
        key_allies=output.key_allies,
        key_rivals=output.key_rivals,
        red_lines=output.red_lines,
        negotiation_priorities=output.negotiation_priorities,
    )
    
    return CountryProfile(
        facts=facts,
        strategy=strategy,
        created_at=now,
        updated_at=now,
    )
