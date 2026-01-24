from typing import cast, Optional, Any
from datetime import datetime, timezone

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from madd.core.config import get_settings
from madd.core.schemas import DebateMessage, CountryProfile, TreatyDraft, ProposedClause
from madd.core.treaty_utils import get_votable_clauses, format_clause_lines
from madd.core.state import DebateState


class ProposedClauseOut(BaseModel):
    text: str
    rationale: str = ""
    supersedes: Optional[str] = None


class ClauseVoteOut(BaseModel):
    clause_id: str | None = None
    vote: str | None = None


class TurnLLMOutput(BaseModel):
    public_statement: str
    private_intent: Optional[str] = None
    proposed_clauses: list[ProposedClauseOut] = Field(default_factory=list)
    clause_votes: dict[str, str] | list[Any] = Field(default_factory=dict)
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
    
    votable_clauses = get_votable_clauses(treaty, current_round)
    pending_clauses = format_clause_lines(votable_clauses)
    
    history_entries = [
        f"Round {m.round_number} - {m.country}: {m.public_statement[:300]}..."
        for m in messages
    ]
    history = "\n".join(history_entries)
    
    all_citations = profile.all_citations()
    if not all_citations:
        raise ValueError(f"Profile for {country_name} has no citations")
    valid_ids = {c.id for c in all_citations if c.id}
    scenario_citations = profile.facts.scenario_citations
    preferred_citations = scenario_citations or all_citations
    citation_refs = _format_citation_groups(profile, preferred_citations)
    
    facts_summary = [
        f"Region: {profile.facts.region or 'Unknown'}",
        f"Government: {profile.facts.government_type or 'Unknown'}",
        f"Leaders: {', '.join(profile.facts.current_leaders[:3]) or 'Unknown'}",
        f"GDP (USD billions): {profile.facts.economy.gdp_usd_billions or 'Unknown'}",
        f"Major industries: {', '.join(profile.facts.economy.major_industries[:5]) or 'Unknown'}",
    ]
    facts_summary_text = "\n".join(facts_summary)
    
    treaty_summary = "\n".join(
        f"- {c.id} [{c.status.value}] {c.text} (by {c.proposed_by})"
        for c in treaty.clauses
    )
    
    system_prompt = f"""You are the Diplomatic Representative of {country_name}.
Scenario: {scenario.name}
{scenario.description}

Your key interests: {', '.join(profile.strategy.core_policy_goals[:3])}
Your allies: {', '.join(profile.strategy.key_allies[:3])}
Your red lines: {', '.join(profile.strategy.red_lines[:3])}
Use the institution name "MMSAC" consistently.
Facts:
{facts_summary_text}

Available citations (use exact IDs only if they support your statement; prefer Scenario/Law sources for legal claims):
{citation_refs}

Respond with:
- public_statement: Your official diplomatic statement
- private_intent: Your hidden strategy
- proposed_clauses: List of clauses (each with "text" and "rationale")
- clause_votes: Vote on votable clauses by ID ("support", "oppose", or "amend")
- citation_ids_to_reference: List of citation IDs (e.g. "cite_abc123") that directly support your statement. If you cite UNCLOS, EEZs, dispute settlement, or legal obligations, include at least 2 citations. If you omit citations, your response will be rejected."""

    pending_str = "\n".join(pending_clauses) if pending_clauses else "None"
    
    user_prompt = f"""Round {current_round}

Votable Clauses:
{pending_str}

Treaty So Far:
{treaty_summary if treaty_summary else "None"}

Recent History:
{history if history else "No prior statements."}

Generate your turn. For every votable clause ID listed, include exactly one vote. If no votable clauses are listed, return an empty clause_votes object."""

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
        ProposedClause(text=p.text, rationale=p.rationale, supersedes=p.supersedes)
        for p in (output.proposed_clauses or [])
        if p and p.text
    ]
    
    references = _normalize_references(output.citation_ids_to_reference, valid_ids)
    if not references:
        references = [c.id for c in preferred_citations if c.id][:2]
    if not references:
        raise ValueError(f"No valid citations available for {country_name}")
    
    clause_votes = _normalize_clause_votes(output.clause_votes)
    votable_ids = {c.id for c in votable_clauses}
    clause_votes = _enforce_vote_policy(
        clause_votes,
        votable_ids,
        strict=settings.strict_votes,
    )
    
    return DebateMessage(
        round_number=current_round,
        country=country_name,
        public_statement=output.public_statement,
        proposed_clauses=proposed,
        clause_votes=clause_votes,
        private_intent=output.private_intent,
        acceptance_conditions=output.acceptance_conditions,
        red_lines=output.red_lines,
        references_used=references,
        timestamp=datetime.now(timezone.utc),
    )


def _normalize_clause_votes(raw_votes: dict[str, str] | list[Any]) -> dict[str, str]:
    if isinstance(raw_votes, dict):
        return {str(k): str(v).strip().lower() for k, v in raw_votes.items() if k and v}
    if not isinstance(raw_votes, list):
        return {}
    
    votes: dict[str, str] = {}
    for item in raw_votes or []:
        if isinstance(item, ClauseVoteOut):
            clause_id = item.clause_id
            vote = item.vote
        elif isinstance(item, dict):
            clause_id = item.get("clause_id") or item.get("clause") or item.get("id") or item.get("clauseId")
            vote = item.get("vote")
        else:
            clause_id = None
            vote = None
        if clause_id and vote:
            votes[str(clause_id)] = str(vote).strip().lower()
    return votes


def _normalize_references(raw_ids: list[Any] | None, valid_ids: set[str]) -> list[str]:
    if not raw_ids:
        return []
    seen: set[str] = set()
    refs: list[str] = []
    for item in raw_ids:
        if not isinstance(item, str):
            continue
        cid = _normalize_citation_id(item)
        if cid and cid in valid_ids and cid not in seen:
            seen.add(cid)
            refs.append(cid)
    return refs


def _normalize_citation_id(raw_id: str) -> str:
    cid = raw_id.strip()
    if cid.startswith("[") and cid.endswith("]"):
        cid = cid[1:-1]
    cid = cid.strip().strip(",.;")
    return cid


def _enforce_vote_policy(
    clause_votes: dict[str, str],
    votable_ids: set[str],
    strict: bool,
) -> dict[str, str]:
    if not votable_ids:
        return {}
    votes: dict[str, str] = {}
    extras = set(clause_votes) - votable_ids
    if extras and strict:
        raise ValueError(f"Votes include non-votable clause IDs: {sorted(extras)}")
    for cid, vote in clause_votes.items():
        if cid not in votable_ids:
            continue
        if vote not in {"support", "oppose", "amend", "abstain"}:
            if strict:
                raise ValueError(f"Invalid vote '{vote}' for {cid}")
            vote = "abstain"
        votes[cid] = vote
    missing = votable_ids - set(votes)
    if missing:
        if strict:
            raise ValueError(f"Missing votes for clauses: {sorted(missing)}")
        for cid in missing:
            votes[cid] = "abstain"
    return votes


def _format_citation_groups(profile: CountryProfile, fallback: list) -> str:
    groups = [
        ("Scenario/Law", profile.facts.scenario_citations),
        ("Leaders", profile.facts.leaders_citations),
        ("Economy", profile.facts.economy.citations),
        ("History", profile.facts.history_citations),
        ("Other", profile.facts.citations),
    ]
    lines: list[str] = []
    for label, citations in groups:
        if not citations:
            continue
        lines.append(f"{label}:")
        for c in citations[:4]:
            lines.append(f"- {c.id}: {c.title} ({c.snippet[:80]}...)")
    if not lines:
        for c in fallback[:8]:
            lines.append(f"- {c.id}: {c.title} ({c.snippet[:80]}...)")
    return "\n".join(lines)
