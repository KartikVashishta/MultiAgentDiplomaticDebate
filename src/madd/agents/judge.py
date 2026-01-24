from typing import cast
from datetime import datetime, timezone

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from madd.core.config import get_settings
from madd.core.schemas import RoundScorecard, CountryScore
from madd.core.state import DebateState


class JudgeLLMOutput(BaseModel):
    scores: list[dict] = []
    rankings: list[str] = []
    summary: str = ""


def evaluate_round(state: DebateState) -> RoundScorecard:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.judge_model,
        temperature=settings.judge_temperature,
        api_key=settings.openai_api_key,
        max_retries=settings.max_retries,
    )
    
    structured_llm = llm.with_structured_output(JudgeLLMOutput)
    current_round = state["round"]
    messages = [m for m in state.get("messages", []) if m.round_number == current_round]
    
    if not messages:
        return RoundScorecard(round_number=current_round)
    
    system_prompt = """You are an impartial diplomatic judge.
Score each country 0-10 based on:
1. Diplomatic effectiveness
2. Negotiation willingness
3. Communication clarity

Return:
- scores: list of {country, score, reasoning}
- rankings: ordered list of country names
- summary: brief round analysis"""

    messages_text = "\n".join(
        f"{m.country}: {m.public_statement[:500]}"
        for m in messages
    )
    
    user_prompt = f"""Round {current_round}:

{messages_text}

Evaluate and score."""

    try:
        result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        output = cast(JudgeLLMOutput, result)
    except Exception as e:
        print(f"    Judge error: {e}")
        return RoundScorecard(round_number=current_round)
    
    scores = []
    for s in output.scores:
        if isinstance(s, dict) and "country" in s:
            scores.append(CountryScore(
                country=s["country"],
                score=float(s.get("score", 5)),
                reasoning=s.get("reasoning", ""),
            ))
    
    treaty = state.get("treaty")
    
    return RoundScorecard(
        round_number=current_round,
        scores=scores,
        rankings=output.rankings,
        summary=output.summary,
        clauses_proposed=len(treaty.clauses) if treaty else 0,
        clauses_accepted=len(treaty.accepted_clauses) if treaty else 0,
        clauses_rejected=len([c for c in (treaty.clauses if treaty else []) if c.status.value == "rejected"]),
    )
