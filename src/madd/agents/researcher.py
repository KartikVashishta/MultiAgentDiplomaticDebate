from typing import cast

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from madd.core.config import get_settings
from madd.core.schemas import CountryProfile


def generate_profile(country_name: str, scenario_description: str) -> CountryProfile:

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0.3, 
        api_key=settings.openai_api_key
    )
    
    structured_llm = llm.with_structured_output(CountryProfile)
    
    system_prompt = """You are an expert diplomatic researcher and intelligence analyst.
Your goal is to generate a comprehensive, factually accurate profile for a country in a diplomatic simulation.
You must provide real-world data with verifiable citations where appropriate.

The profile must be strictly structured according to the schema.
- 'facts' should contain verifiable data (GDP, population, history).
- 'strategy' should contain analysis of their likely position in the given scenario.
- 'citations' must include plausible sources (title, url, snippet) for key facts.
"""

    user_prompt = f"""Research Target: {country_name}
Scenario Context: {scenario_description}

Generate a detailed CountryProfile.
Ensure economic data is normalized (Billions USD).
Include real colonial history and major conflicts.
Derive strategic interests relevant to the scenario."""

    response = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    return cast(CountryProfile, response)
