from typing import cast

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from madd.core.config import get_settings
from madd.core.schemas import DebateMessage, CountryProfile, TreatyDraft
from madd.core.state import DebateState


def generate_turn(state: DebateState, country_name: str) -> DebateMessage:
    """Generate a diplomatic turn for a specific country.
    
    Args:
        state: Current debate state.
        country_name: Name of the country taking the turn.
        
    Returns:
        Structured DebateMessage with public statement and clauses.
    """
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=settings.temperature,
        api_key=settings.openai_api_key
    )
    
    # Get context from state
    profile: CountryProfile = state["profiles"][country_name]
    treaty: TreatyDraft = state["treaty"]
    messages = state["messages"]
    current_round = state["round"]
    scenario = state["scenario"]
    
    # Configure structured output
    structured_llm = llm.with_structured_output(DebateMessage)
    
    system_prompt = f"""You are the Diplomatic Representative of {country_name}.
Your goal is to negotiate a treaty that serves your national interests.

Scenario: {scenario.name}
{scenario.description}

Your Profile Facts:
{profile.facts.model_dump_json()}

Your Strategy:
{profile.strategy.model_dump_json()}

Current Treaty Draft:
{treaty.model_dump_json()}

Instructions:
1. Analyze recent messages from other countries.
2. Advance your strategic goals through `public_statement`.
3. Propose concrete clauses using `proposed_clauses`.
4. Vote on existing clauses using `clause_votes` (support/oppose/amend).
5. Outline `private_intent` to explain your move to the system (hidden from others).
"""

    # Format history
    history_text = "\n".join(
        f"Round {m.round_number} - {m.country}: {m.public_statement}"
        for m in messages
        if m.round_number >= current_round - 1 # Only recent context to save tokens
    )
    
    user_prompt = f"""Current Round: {current_round}
    
Recent History:
{history_text or "No messages yet. You are speaking first."}

Generate your official turn output."""

    response = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    return cast(DebateMessage, response)
