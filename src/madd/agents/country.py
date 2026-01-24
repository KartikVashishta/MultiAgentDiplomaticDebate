from typing import cast, Optional, Any
from datetime import datetime, timezone

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from madd.core.config import get_settings
from madd.core.schemas import DebateMessage, CountryProfile, TreatyDraft, ProposedClause
from madd.core.treaty_utils import get_votable_clauses, format_clause_lines
from madd.core.state import DebateState
from madd.core.scenario_router import build_router_plan, DEFAULT_INSTITUTION_NAME, RouterPlan


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


class CitationSelectionOutput(BaseModel):
    citation_ids_to_reference: list[str] = Field(default_factory=list)


class PropositionalRewriteOutput(BaseModel):
    public_statement: str


class AmendmentOutput(BaseModel):
    proposed_clauses: list[ProposedClauseOut] = Field(default_factory=list)


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
    router_plan: RouterPlan = state.get("router_plan") or build_router_plan(scenario)
    
    structured_llm = llm.with_structured_output(TurnLLMOutput, method="function_calling")
    
    votable_clauses = get_votable_clauses(treaty, current_round)
    pending_clauses = format_clause_lines(votable_clauses)
    
    history_entries = [
        f"Round {m.round_number} - {m.country}: {m.public_statement[:300]}..."
        for m in messages
    ]
    history = "\n".join(history_entries)
    
    all_citations = profile.all_citations()
    valid_ids = {c.id for c in all_citations if c.id}
    scenario_citations = profile.facts.scenario_citations
    preferred_citations = scenario_citations or all_citations
    citation_refs = _format_citation_groups(profile, preferred_citations)
    institution_name = router_plan.institution_name or DEFAULT_INSTITUTION_NAME
    agenda_text = _format_agenda_text(scenario)
    voice_guidance = _build_voice_guidance(profile, router_plan)
    
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
    
    system_prompt = f"""You are the Diplomatic Representative of {country_name} in a formal negotiation.

Scenario: {scenario.name}
Scenario description:
{scenario.description}

Agenda (ordered by priority; you MUST address these in order):
{agenda_text}

Country profile (facts you may rely on):
{facts_summary_text}

Negotiation style guidance:
- Follow your profile’s negotiation_style if provided.
- Do NOT mirror the other side’s phrasing. Use your own national voice and priorities.
- Avoid generic filler; be specific, mechanism-oriented, and responsive to the agenda.
- Profile style: {profile.strategy.negotiation_style or "Not specified"}
- Scenario voice: {voice_guidance}

Institution naming:
- Use the oversight body name exactly as provided in the scenario if present.
- If none is provided, refer to “Joint Oversight Commission (JOC)” consistently.
- Institution name for this scenario: {institution_name}

Scenario Router Patch:
{router_plan.turn_prompt_patch}

EVIDENCE & CITATION DISCIPLINE (highest priority):
- You may ONLY include factual or legal assertions if you can support them with the available citations by ID.
- If you cannot support a factual/legal assertion with available citations, rewrite as:
  (a) proposal (“we propose…”),
  (b) request for oversight study (“we request JOC produce… within X days”),
  (c) conditional (“subject to verification…”, “pending review…”).
- Never pad citations. Only select citation IDs that genuinely match what you said.
- If you mention treaties, borders, legal status, casualty figures, dates, statistics, specific incidents, or binding obligations, include at least 2 relevant citations.

DIPLOMATIC REALISM (required each turn):
- Include all three:
  1) One ASK,
  2) One OFFER/CONCESSION,
  3) One CONDITIONAL TRADEOFF.
- Address agenda priorities explicitly in order (P1 → P2 → P3 ...).

TREATY-QUALITY CLAUSE DRAFTING:
- Propose 0–3 clauses max per turn.
- Each clause must be implementable: scope, authority, timelines, compliance/enforcement, exceptions.
- Avoid duplicates. If changing an existing clause, set supersedes="C#".
- If you vote "amend" on any clause, you MUST also propose a replacement clause that supersedes it.

VOTING:
- For every votable clause ID provided, output exactly one vote:
  "support" | "oppose" | "amend" | "abstain".
- Do not vote on non-votable IDs.

AVAILABLE CITATIONS (use exact IDs only):
{citation_refs or "None"}

Return a structured response with:
- public_statement (180–260 words, 2–4 short paragraphs, end punctuation)
- private_intent
- proposed_clauses (text, rationale, supersedes optional)
- clause_votes
- citation_ids_to_reference

Do NOT include citation IDs inside the public_statement text.
"""

    pending_str = "\n".join(pending_clauses) if pending_clauses else "None"
    
    user_prompt = f"""Round {current_round}

Votable Clauses:
{pending_str}

Treaty So Far:
{treaty_summary if treaty_summary else "None"}

Recent History:
{history if history else "No prior statements."}

Generate your turn. For every votable clause ID listed, include exactly one vote. If you vote "amend", include a replacement clause with supersedes="C#". If no votable clauses are listed, return an empty clause_votes object."""

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
    citation_fallback_used = False
    if not references:
        references = _select_citations_second_pass(
            llm,
            output.public_statement,
            citation_refs,
            valid_ids,
        )
    if not references:
        rewritten = _rewrite_to_propositional(
            llm,
            output.public_statement,
            scenario.name,
            agenda_text,
            institution_name,
        )
        if rewritten:
            output.public_statement = rewritten
        else:
            citation_fallback_used = True

    clause_votes = _normalize_clause_votes(output.clause_votes)
    votable_ids = {c.id for c in votable_clauses}
    clause_votes = _enforce_vote_policy(
        clause_votes,
        votable_ids,
        strict=settings.strict_votes,
    )

    proposed = _ensure_amendment_replacements(
        llm,
        proposed,
        clause_votes,
        votable_clauses,
        scenario.name,
        agenda_text,
        institution_name,
    )
    
    is_truncated, trunc_note = _detect_truncation(output.public_statement)
    if citation_fallback_used:
        is_truncated = True
        trunc_note = "Citation fallback used"
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
        is_truncated=is_truncated,
        truncation_note=trunc_note,
        timestamp=datetime.now(timezone.utc),
    )


def _format_agenda_text(scenario) -> str:
    items = sorted(scenario.agenda, key=lambda a: a.priority)
    if not items:
        return "No agenda provided."
    lines = []
    for item in items:
        desc = f" - {item.description}" if item.description else ""
        lines.append(f"P{item.priority}: {item.topic}{desc}")
    return "\n".join(lines)


def _build_voice_guidance(profile: CountryProfile, router_plan: RouterPlan) -> str:
    guidance = []
    archetypes = {a.archetype for a in (router_plan.archetypes or []) if a.score >= 0.4}
    if "SECURITY_DEFENSE" in archetypes:
        guidance.append("Emphasize operational realism and legal sovereignty constraints.")
    if "TRADE_SANCTIONS_FINANCE" in archetypes or "RESOURCES_MINERALS" in archetypes:
        guidance.append("Emphasize economic framing, licensing, and compliance mechanisms.")
    if "ENVIRONMENT_CLIMATE" in archetypes or "HUMAN_RIGHTS_COMMUNITY" in archetypes:
        guidance.append("Emphasize safeguards, consent thresholds, and monitoring.")
    if profile.strategy.negotiation_style:
        guidance.append(f"Leverage style: {profile.strategy.negotiation_style}.")
    return " ".join(guidance) or "Balance legal, economic, and humanitarian considerations."


def _select_citations_second_pass(
    llm: ChatOpenAI,
    public_statement: str,
    citation_refs: str,
    valid_ids: set[str],
) -> list[str]:
    if not public_statement or not valid_ids:
        return []
    selection_llm = llm.with_structured_output(CitationSelectionOutput, method="function_calling")
    system_prompt = """Select citation IDs that directly support the statement.
Use ONLY the provided citation IDs. If none apply, return an empty list.
Do not invent citations or rewrite the statement."""
    user_prompt = f"""Statement:
{public_statement}

Available citations:
{citation_refs or "None"}

Return citation_ids_to_reference only."""
    try:
        result = selection_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        output = cast(CitationSelectionOutput, result)
    except Exception:
        return []
    return _normalize_references(output.citation_ids_to_reference, valid_ids)


def _rewrite_to_propositional(
    llm: ChatOpenAI,
    public_statement: str,
    scenario_name: str,
    agenda_text: str,
    institution_name: str,
) -> str:
    if not public_statement:
        return ""
    rewrite_llm = llm.with_structured_output(PropositionalRewriteOutput, method="function_calling")
    system_prompt = """Rewrite the statement to avoid factual or legal assertions that require citations.
Keep it propositional and mechanism-oriented.
Retain the structure: 180–260 words, 2–4 short paragraphs, end punctuation.
Include one ASK, one OFFER/CONCESSION, and one CONDITIONAL TRADEOFF.
Address agenda priorities in order."""
    user_prompt = f"""Scenario: {scenario_name}
Agenda:
{agenda_text}
Institution name: {institution_name}

Original statement:
{public_statement}

Rewrite now."""
    try:
        result = rewrite_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        output = cast(PropositionalRewriteOutput, result)
    except Exception:
        return ""
    return (output.public_statement or "").strip()


def _ensure_amendment_replacements(
    llm: ChatOpenAI,
    proposed: list[ProposedClause],
    clause_votes: dict[str, str],
    votable_clauses: list,
    scenario_name: str,
    agenda_text: str,
    institution_name: str,
) -> list[ProposedClause]:
    amend_ids = {cid for cid, vote in clause_votes.items() if vote == "amend"}
    if not amend_ids:
        return proposed
    existing_supersedes = {p.supersedes for p in proposed if p.supersedes}
    missing = amend_ids - existing_supersedes
    if not missing:
        return proposed

    clause_map = {c.id: c.text for c in votable_clauses if c.id in missing}
    replacement_llm = llm.with_structured_output(AmendmentOutput, method="function_calling")
    system_prompt = """Draft replacement clauses for amendments.
Each replacement must set supersedes to the clause ID being amended.
Ensure each clause is implementable: scope, authority, timelines, compliance, exceptions."""
    clause_text = "\n".join(f"{cid}: {text}" for cid, text in clause_map.items())
    user_prompt = f"""Scenario: {scenario_name}
Agenda:
{agenda_text}
Institution name: {institution_name}

Clauses to replace:
{clause_text or "None"}

Provide replacement proposed_clauses."""
    try:
        result = replacement_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        output = cast(AmendmentOutput, result)
        replacements = [
            ProposedClause(text=p.text, rationale=p.rationale, supersedes=p.supersedes)
            for p in (output.proposed_clauses or [])
            if p and p.text and p.supersedes in missing
        ]
    except Exception:
        replacements = []

    if replacements:
        return proposed + replacements

    fallback = []
    for cid in missing:
        fallback.append(
            ProposedClause(
                text=(
                    f"Replace {cid} with a jointly drafted clause under {institution_name} "
                    "within 30 days, specifying scope, approvals, timelines, compliance, "
                    "exceptions, and reporting."
                ),
                rationale="Ensures an explicit replacement clause is proposed.",
                supersedes=cid,
            )
        )
    return proposed + fallback


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


def _detect_truncation(text: str) -> tuple[bool, str | None]:
    if not text:
        return False, None
    lowered = text.lower()
    if "truncated" in lowered:
        return True, "Statement contains truncation marker"
    if text and text[-1].isalnum() and not text.strip().endswith((".", "!", "?", "\"", "'")):
        return True, "Statement appears cut off mid-sentence"
    return False, None


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
