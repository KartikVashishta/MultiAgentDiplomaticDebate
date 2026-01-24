from typing import cast

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from madd.core.config import get_settings
from madd.core.schemas import RoundScorecard, DebateMessage, CountryProfile
from madd.core.state import DebateState


def evaluate_round(state: DebateState) -> RoundScorecard:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0.0,
        api_key=settings.openai_api_key
    )
    
    structured_llm = llm.with_structured_output(RoundScorecard)
    current_round = state["round"]
    messages = [m for m in state["messages"] if m.round_number == current_round]
    
    if not messages:
        return RoundScorecard(round_number=current_round)
    
    system_prompt = """You are an impartial Diplomatic Judge.
Your role is to score each country's performance based on:
1. Effectiveness in advancing their national interests.
2. Willingness to negotiate and find common ground.
3. Clarity and professionalism of communication.

You must provide a numeric score (0-10) and detailed reasoning for each country.
"""

    messages_text = "\n".join(
        f"{m.country}: {m.public_statement} (Intent: {m.private_intent})"
        for m in messages
    )
    user_prompt = f"""Round: {current_round}

Debate Log:
{messages_text}

Evaluate this round and generate a scorecard.
Calculate treaty progress metrics based on proposed/accepted clauses."""

    response = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    return cast(RoundScorecard, response)
