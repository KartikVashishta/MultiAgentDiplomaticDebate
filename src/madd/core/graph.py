import logging
import re

from langgraph.graph import StateGraph, END

from madd.core.state import DebateState
from madd.core.schemas import AuditFinding, AuditSeverity, Clause, ClauseStatus, TreatyDraft
from madd.stores.profile_store import ensure_profile, make_scenario_key
from madd.core.scenario_router import build_router_plan, DEFAULT_INSTITUTION_NAME
from madd.core.treaty_utils import get_votable_clauses
from madd.agents.country import generate_turn
from madd.agents.judge import evaluate_round
from madd.agents.verifier import verify_claims
from madd.agents.treaty_refiner import refine_treaty

logger = logging.getLogger(__name__)

def _log_state(event: str, state: DebateState) -> None:
    round_number = state.get("round", 0)
    max_rounds = state.get("max_rounds", 0)
    messages = state.get("messages", [])
    profiles = state.get("profiles", {})
    citation_counts = {
        name: len(profile.all_citations())
        for name, profile in profiles.items()
    }
    logger.info(
        "%s round=%s max_rounds=%s messages=%s citations=%s",
        event,
        round_number,
        max_rounds,
        len(messages),
        citation_counts,
    )


def build_graph() -> StateGraph:
    graph = StateGraph(DebateState)
    
    graph.add_node("ensure_profiles", _ensure_profiles)
    graph.add_node("opening_statements", _opening_statements)
    graph.add_node("negotiate_round", _negotiate_round)
    graph.add_node("compile_treaty", _compile_treaty)
    graph.add_node("verify", _verify)
    graph.add_node("judge", _judge)
    graph.add_node("refine_treaty", _refine_treaty)
    graph.add_node("finalize_report", _finalize_report)
    
    graph.set_entry_point("ensure_profiles")
    graph.add_edge("ensure_profiles", "opening_statements")
    graph.add_edge("opening_statements", "compile_treaty")
    graph.add_edge("compile_treaty", "verify")
    graph.add_edge("verify", "judge")
    
    graph.add_conditional_edges(
        "judge",
        _should_continue,
        {
            "continue": "negotiate_round",
            "finalize": "refine_treaty",
        }
    )
    graph.add_edge("negotiate_round", "compile_treaty")
    graph.add_edge("refine_treaty", "finalize_report")
    graph.add_edge("finalize_report", END)
    
    return graph.compile()


def _ensure_profiles(state: DebateState) -> dict:
    scenario = state["scenario"]
    profiles = {}
    router_plan = build_router_plan(scenario)
    
    logger.info(f"Loading/generating profiles for {len(scenario.countries)} countries")
    _log_state("ensure_profiles.start", state)
    scenario_key = make_scenario_key(scenario.name, scenario.description)
    
    for country in scenario.countries:
        logger.info(f"  - {country}...")
        profiles[country] = ensure_profile(
            country,
            scenario.description,
            scenario_name=scenario.name,
            scenario_key=scenario_key,
            router_plan=router_plan,
        )
    
    updated = dict(state)
    updated["profiles"] = profiles
    updated["router_plan"] = router_plan
    _log_state("ensure_profiles.end", updated)
    return {"profiles": profiles, "router_plan": router_plan}


def _opening_statements(state: DebateState) -> dict:
    scenario = state["scenario"]
    logger.info("Round 1: Opening statements")
    _log_state("opening_statements.start", state)
    
    new_messages = []
    temp_state = dict(state)
    temp_state["round"] = 1
    temp_state["treaty"] = TreatyDraft(title=f"Treaty on {scenario.name}")
    
    for country in scenario.countries:
        logger.info(f"  - {country} speaking...")
        temp_state["messages"] = list(state.get("messages", [])) + new_messages
        msg = generate_turn(temp_state, country)
        msg.round_number = 1
        new_messages.append(msg)
    
    updated = dict(state)
    updated["messages"] = list(state.get("messages", [])) + new_messages
    updated["round"] = 1
    updated["treaty"] = temp_state["treaty"]
    _log_state("opening_statements.end", updated)
    return {"messages": new_messages, "round": 1, "treaty": temp_state["treaty"]}


def _negotiate_round(state: DebateState) -> dict:
    scenario = state["scenario"]
    current_round = state["round"] + 1
    logger.info(f"Round {current_round}: Negotiation")
    _log_state("negotiate_round.start", state)
    
    new_messages = []
    temp_state = dict(state)
    temp_state["round"] = current_round
    
    for country in scenario.countries:
        logger.info(f"  - {country} speaking...")
        temp_state["messages"] = list(state.get("messages", [])) + new_messages
        msg = generate_turn(temp_state, country)
        msg.round_number = current_round
        new_messages.append(msg)
    
    updated = dict(state)
    updated["messages"] = list(state.get("messages", [])) + new_messages
    updated["round"] = current_round
    _log_state("negotiate_round.end", updated)
    return {"messages": new_messages, "round": current_round}


def _compile_treaty(state: DebateState) -> dict:
    logger.info("Compiling treaty clauses")
    _log_state("compile_treaty.start", state)
    
    current_round = state["round"]
    messages = state.get("messages", [])
    treaty = state.get("treaty") or TreatyDraft()
    countries = state["scenario"].countries
    clause_counter = state.get("clause_counter", len(treaty.clauses))
    
    round_messages = [m for m in messages if m.round_number == current_round]
    
    for msg in round_messages:
        for proposed in msg.proposed_clauses:
            clause_counter += 1
            clause_id = f"C{clause_counter}"
            institution_name = _get_institution_name(state)
            clause_text = _normalize_institution_name(proposed.text, institution_name)
            new_clause = Clause(
                id=clause_id,
                text=clause_text,
                proposed_by=msg.country,
                status=ClauseStatus.PROPOSED,
                proposed_round=current_round,
                supporters=[msg.country],
                objectors=[],
                supersedes=proposed.supersedes,
            )
            treaty.clauses.append(new_clause)
            if proposed.supersedes:
                for existing in treaty.clauses:
                    if existing.id == proposed.supersedes:
                        existing.amendments.append(f"{clause_id} supersedes {existing.id}")
    
    votable_clauses = get_votable_clauses(treaty, current_round)
    
    for clause in votable_clauses:
        for msg in round_messages:
            if msg.country == clause.proposed_by:
                continue
            
            vote = msg.clause_votes.get(clause.id, "")
            
            if vote == "support":
                if msg.country not in clause.supporters:
                    clause.supporters.append(msg.country)
                if msg.country in clause.objectors:
                    clause.objectors.remove(msg.country)
            elif vote == "oppose":
                if msg.country not in clause.objectors:
                    clause.objectors.append(msg.country)
                if msg.country in clause.supporters:
                    clause.supporters.remove(msg.country)
            elif vote == "amend":
                if msg.country not in clause.objectors:
                    clause.objectors.append(msg.country)
                amendment_text = f"[Round {current_round}] {msg.country} proposed amendment"
                if amendment_text not in clause.amendments:
                    clause.amendments.append(amendment_text)
            elif vote == "abstain":
                if msg.country in clause.supporters:
                    clause.supporters.remove(msg.country)
                if msg.country in clause.objectors:
                    clause.objectors.remove(msg.country)
    
    for clause in votable_clauses:
        support_count = len(clause.supporters)
        oppose_count = len(clause.objectors)
        total = len(countries)
        
        if support_count > total / 2:
            clause.status = ClauseStatus.ACCEPTED
            clause.resolved_round = current_round
            logger.info(f"  Clause {clause.id} ACCEPTED ({support_count}/{total})")
        elif oppose_count > total / 2:
            if clause.amendments:
                clause.status = ClauseStatus.PROPOSED
                clause.resolved_round = None
                logger.info(f"  Clause {clause.id} remains PROPOSED (amendments pending)")
            else:
                clause.status = ClauseStatus.REJECTED
                clause.resolved_round = current_round
                logger.info(f"  Clause {clause.id} {clause.status.value.upper()} ({oppose_count}/{total})")
    
    updated_treaty = TreatyDraft(
        title=treaty.title or f"Treaty on {state['scenario'].name}",
        preamble=treaty.preamble,
        clauses=treaty.clauses,
    )
    updated = dict(state)
    updated["treaty"] = updated_treaty
    updated["clause_counter"] = clause_counter
    _log_state("compile_treaty.end", updated)
    return {"treaty": updated_treaty, "clause_counter": clause_counter}


def _normalize_institution_name(text: str, institution_name: str | None) -> str:
    if not text:
        return text
    name = institution_name or DEFAULT_INSTITUTION_NAME
    pattern = r"\b(joc|joint oversight commission|mmacc|mmsac|asean maritime coordination centre)\b"
    return re.sub(pattern, name, text, flags=re.IGNORECASE)


def _get_institution_name(state: DebateState) -> str:
    router_plan = state.get("router_plan")
    if router_plan and router_plan.institution_name:
        return router_plan.institution_name
    return DEFAULT_INSTITUTION_NAME


def _verify(state: DebateState) -> dict:
    logger.info("Verifying claims")
    _log_state("verify.start", state)
    try:
        findings = verify_claims(state)
        updated = dict(state)
        updated["audit"] = state.get("audit", []) + findings
        _log_state("verify.end", updated)
        return {"audit": findings}
    except Exception as e:
        logger.warning(f"Verification error: {e}")
        findings = [AuditFinding(
            severity=AuditSeverity.ERROR,
            category="verifier_failed",
            description=f"Verifier crashed: {e}",
            round_number=state.get("round", 0),
            evidence=[],
        )]
        updated = dict(state)
        updated["audit"] = state.get("audit", []) + findings
        _log_state("verify.end", updated)
        return {"audit": findings}


def _judge(state: DebateState) -> dict:
    current_round = state["round"]
    logger.info(f"Judging round {current_round}")
    _log_state("judge.start", state)
    try:
        scorecard = evaluate_round(state)
        updated = dict(state)
        updated["scorecards"] = state.get("scorecards", []) + [scorecard]
        _log_state("judge.end", updated)
        return {"scorecards": [scorecard]}
    except Exception as e:
        logger.warning(f"Judge error: {e}")
        from madd.core.schemas import RoundScorecard
        scorecard = RoundScorecard(round_number=current_round)
        updated = dict(state)
        updated["scorecards"] = state.get("scorecards", []) + [scorecard]
        _log_state("judge.end", updated)
        return {"scorecards": [scorecard]}


def _refine_treaty(state: DebateState) -> dict:
    logger.info("Refining treaty into publication-ready draft")
    _log_state("refine_treaty.start", state)
    treaty_text = refine_treaty(state)
    updated = dict(state)
    updated["treaty_text"] = treaty_text
    _log_state("refine_treaty.end", updated)
    return {"treaty_text": treaty_text}


def _finalize_report(state: DebateState) -> dict:
    logger.info(f"Debate complete after {state['round']} rounds")
    treaty = state.get("treaty")
    if treaty:
        logger.info(f"  Accepted: {len(treaty.accepted_clauses)}, Pending: {len(treaty.pending_clauses)}")
    _log_state("finalize_report.end", state)
    return {}


def _should_continue(state: DebateState) -> str:
    current_round = state.get("round", 1)
    max_rounds = state.get("max_rounds", 3)
    
    decision = "finalize" if current_round >= max_rounds else "continue"
    logger.info(
        "should_continue round=%s max_rounds=%s decision=%s",
        current_round,
        max_rounds,
        decision,
    )
    return decision
