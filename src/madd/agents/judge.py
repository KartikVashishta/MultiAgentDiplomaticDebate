import logging
from typing import cast

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from madd.core.config import get_settings
from madd.core.schemas import CountryScore, RoundScorecard
from madd.core.state import DebateState

logger = logging.getLogger(__name__)


class ScoreOut(BaseModel):
    country: str
    score: float = Field(default=5, ge=0, le=10)
    reasoning: str = ""
    diplomatic_effectiveness: float = Field(default=0.0, ge=0, le=10)
    negotiation_willingness: float = Field(default=0.0, ge=0, le=10)
    communication_clarity: float = Field(default=0.0, ge=0, le=10)
    treaty_contribution: float = Field(default=0.0, ge=0, le=10)


class JudgeLLMOutput(BaseModel):
    scores: list[ScoreOut] = Field(default_factory=list)
    rankings: list[str] = Field(default_factory=list)
    summary: str = ""


def evaluate_round(state: DebateState) -> RoundScorecard:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.judge_model,
        temperature=settings.judge_temperature,
        api_key=settings.openai_api_key,
        max_retries=settings.max_retries,
    )
    
    structured_llm = llm.with_structured_output(JudgeLLMOutput, method="function_calling")
    current_round = state["round"]
    messages = [m for m in state.get("messages", []) if m.round_number == current_round]
    
    if not messages:
        return RoundScorecard(round_number=current_round)
    
    system_prompt = """You are an impartial diplomatic judge.
Score each country 0-10 based on:
1. Diplomatic effectiveness
2. Negotiation willingness
3. Communication clarity
4. Treaty contribution (quality/quantity of concrete, constructive proposals)

Return:
- scores: list of {country, score, reasoning, diplomatic_effectiveness, negotiation_willingness, communication_clarity, treaty_contribution}
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
        logger.warning(f"Judge error: {e}")
        return RoundScorecard(round_number=current_round)
    
    message_map = {m.country: m for m in messages}
    scores = []
    for s in (output.scores or []):
        if not s or not s.country:
            continue
        msg = message_map.get(s.country)
        is_truncated = bool(msg and msg.is_truncated)
        trunc_note = msg.truncation_note if msg and msg.is_truncated else None
        scores.append(CountryScore(
            country=s.country,
            score=float(s.score),
            reasoning=s.reasoning,
            diplomatic_effectiveness=float(s.diplomatic_effectiveness or s.score),
            negotiation_willingness=float(s.negotiation_willingness or s.score),
            communication_clarity=float(s.communication_clarity or s.score),
            treaty_contribution=float(s.treaty_contribution or 0.0),
            statement_truncated=is_truncated,
            truncation_note=trunc_note,
        ))
    
    treaty = state.get("treaty")
    clauses = treaty.clauses if treaty else []
    clauses_this_round = [c for c in clauses if c.proposed_round == current_round]
    resolved_this_round = [c for c in clauses if c.resolved_round == current_round]
    accepted_cumulative = len([c for c in clauses if c.status.value == "accepted"])
    rejected_cumulative = len([c for c in clauses if c.status.value == "rejected"])
    pending_cumulative = len([c for c in clauses if c.status.value == "proposed"])
    total_unique = len(clauses)
    accepted_this_round = len([c for c in resolved_this_round if c.status.value == "accepted"])
    rejected_this_round = len([c for c in resolved_this_round if c.status.value in ("rejected", "amended")])
    
    summary_truncated = _detect_truncation(output.summary)
    return RoundScorecard(
        round_number=current_round,
        scores=scores,
        rankings=output.rankings,
        summary=output.summary,
        summary_truncated=summary_truncated,
        clauses_proposed=len(clauses_this_round),
        clauses_accepted=accepted_this_round,
        clauses_rejected=rejected_this_round,
        clauses_proposed_this_round=len(clauses_this_round),
        clauses_accepted_this_round=accepted_this_round,
        clauses_rejected_this_round=rejected_this_round,
        clauses_accepted_cumulative=accepted_cumulative,
        clauses_rejected_cumulative=rejected_cumulative,
        clauses_pending_cumulative=pending_cumulative,
        clauses_total_unique_cumulative=total_unique,
    )


def _detect_truncation(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if "truncated" in lowered:
        return True
    return text[-1].isalnum() and not text.strip().endswith((".", "!", "?", "\"", "'"))
