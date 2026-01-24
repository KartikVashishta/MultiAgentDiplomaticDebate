from typing import cast, Optional
from datetime import datetime, timezone

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from madd.core.config import get_settings
from madd.core.schemas import DebateMessage, CountryProfile, TreatyDraft, ProposedClause
from madd.core.state import DebateState


class ProposedClauseOut(BaseModel):
    text: str
    rationale: str = ""


class TurnLLMOutput(BaseModel):
    public_statement: str
    private_intent: Optional[str] = None
    proposed_clauses: list[ProposedClauseOut] = Field(default_factory=list)
    clause_votes: dict[str, str] = Field(default_factory=dict)
    acceptance_conditions: list[str] = Field(default_factory=list)
    red_lines: list[str] = Field(default_factory=list)
    citation_ids_to_reference: list[str] = Field(default_factory=list)


def generate_turn(state: DebateState, country_name: str) -> DebateMessage:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.turn_model,
        temperature=settings.turn_temperature,
        api_key=settings.openai_api_key,
        max_retries=settings.max_retries,
    )
    
    profile: CountryProfile = state["profiles"][country_name]
    treaty: TreatyDraft = state.get("treaty") or TreatyDraft()
    messages = state.get("messages", [])
    current_round = state["round"]
    scenario = state["scenario"]
    
    structured_llm = llm.with_structured_output(TurnLLMOutput, method="function_calling")
    
    pending_clauses = [
        f"- {c.id}: {c.text} (by {c.proposed_by})"
        for c in treaty.clauses
        if c.status.value == "proposed"
    ]
    
    recent_messages = [m for m in messages if m.round_number >= max(1, current_round - 1)]
    history = "\n".join(
        f"{m.country}: {m.public_statement[:300]}..."
        for m in recent_messages[-6:]
    )
    
    all_citations = profile.all_citations()
    valid_ids = {c.id for c in all_citations}
    citation_refs = "\n".join(
        f"- {c.id}: {c.title} ({c.snippet[:80]}...)"
        for c in all_citations[:10]
    )
    
    system_prompt = f"""You are the Diplomatic Representative of {country_name}.
Scenario: {scenario.name}
{scenario.description}

Your key interests: {', '.join(profile.strategy.core_policy_goals[:3])}
Your allies: {', '.join(profile.strategy.key_allies[:3])}
Your red lines: {', '.join(profile.strategy.red_lines[:3])}

Available citations you MUST reference (use exact IDs):
{citation_refs}

Respond with:
- public_statement: Your official diplomatic statement
- private_intent: Your hidden strategy
- proposed_clauses: List of clauses (each with "text" and "rationale")
- clause_votes: Vote on pending clauses by ID ("support", "oppose", or "amend")
- citation_ids_to_reference: List of citation IDs (e.g. "cite_abc123") that support your statement"""

    pending_str = "\n".join(pending_clauses) if pending_clauses else "None"
    
    user_prompt = f"""Round {current_round}

Pending Clauses:
{pending_str}

Recent History:
{history if history else "No prior statements."}

Generate your turn. You MUST include at least one citation_ids_to_reference from the available citations."""

    try:
        result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        output = cast(TurnLLMOutput, result)
    except Exception as e:
        print(f"    Error generating turn: {e}")
        output = TurnLLMOutput(
            public_statement=f"{country_name} reserves its position.",
        )
    
    proposed = [
        ProposedClause(text=p.text, rationale=p.rationale)
        for p in (output.proposed_clauses or [])
        if p and p.text
    ]
    
    references = [cid for cid in output.citation_ids_to_reference if cid in valid_ids]
    if not references and all_citations:
        references = [all_citations[0].id]
    
    return DebateMessage(
        round_number=current_round,
        country=country_name,
        public_statement=output.public_statement,
        proposed_clauses=proposed,
        clause_votes=output.clause_votes,
        private_intent=output.private_intent,
        acceptance_conditions=output.acceptance_conditions,
        red_lines=output.red_lines,
        references_used=references,
        timestamp=datetime.now(timezone.utc),
    )
