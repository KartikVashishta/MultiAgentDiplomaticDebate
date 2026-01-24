import logging

from langgraph.graph import StateGraph, END

from madd.core.state import DebateState
from madd.core.schemas import Clause, ClauseStatus, TreatyDraft
from madd.stores.profile_store import ensure_profile
from madd.agents.country import generate_turn
from madd.agents.judge import evaluate_round
from madd.agents.verifier import verify_claims

logger = logging.getLogger(__name__)


def build_graph() -> StateGraph:
    graph = StateGraph(DebateState)
    
    graph.add_node("ensure_profiles", _ensure_profiles)
    graph.add_node("opening_statements", _opening_statements)
    graph.add_node("negotiate_round", _negotiate_round)
    graph.add_node("compile_treaty", _compile_treaty)
    graph.add_node("verify", _verify)
    graph.add_node("judge", _judge)
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
            "finalize": "finalize_report",
        }
    )
    graph.add_edge("negotiate_round", "compile_treaty")
    graph.add_edge("finalize_report", END)
    
    return graph.compile()


def _ensure_profiles(state: DebateState) -> dict:
    scenario = state["scenario"]
    profiles = {}
    
    logger.info(f"Loading/generating profiles for {len(scenario.countries)} countries")
    
    for country in scenario.countries:
        logger.info(f"  - {country}...")
        profiles[country] = ensure_profile(country, scenario.description)
    
    return {"profiles": profiles}


def _opening_statements(state: DebateState) -> dict:
    scenario = state["scenario"]
    logger.info("Round 1: Opening statements")
    
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
    
    return {"messages": new_messages, "round": 1, "treaty": temp_state["treaty"]}


def _negotiate_round(state: DebateState) -> dict:
    scenario = state["scenario"]
    current_round = state["round"] + 1
    logger.info(f"Round {current_round}: Negotiation")
    
    new_messages = []
    temp_state = dict(state)
    temp_state["round"] = current_round
    
    for country in scenario.countries:
        logger.info(f"  - {country} speaking...")
        temp_state["messages"] = list(state.get("messages", [])) + new_messages
        msg = generate_turn(temp_state, country)
        msg.round_number = current_round
        new_messages.append(msg)
    
    return {"messages": new_messages, "round": current_round}


def _compile_treaty(state: DebateState) -> dict:
    logger.info("Compiling treaty clauses")
    
    current_round = state["round"]
    messages = state.get("messages", [])
    treaty = state.get("treaty") or TreatyDraft()
    countries = state["scenario"].countries
    
    round_messages = [m for m in messages if m.round_number == current_round]
    
    for msg in round_messages:
        for proposed in msg.proposed_clauses:
            clause_id = f"C{len(treaty.clauses) + 1}"
            treaty.clauses.append(Clause(
                id=clause_id,
                text=proposed.text,
                proposed_by=msg.country,
                status=ClauseStatus.PROPOSED,
                proposed_round=current_round,
                supporters=[msg.country],
                objectors=[],
            ))
    
    votable_clauses = [
        c for c in treaty.clauses
        if c.status == ClauseStatus.PROPOSED and c.proposed_round < current_round
    ]
    
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
                clause.status = ClauseStatus.AMENDED
            else:
                clause.status = ClauseStatus.REJECTED
            clause.resolved_round = current_round
            logger.info(f"  Clause {clause.id} {clause.status.value.upper()} ({oppose_count}/{total})")
    
    updated_treaty = TreatyDraft(
        title=treaty.title or f"Treaty on {state['scenario'].name}",
        preamble=treaty.preamble,
        clauses=treaty.clauses,
    )
    
    return {"treaty": updated_treaty}


def _verify(state: DebateState) -> dict:
    logger.info("Verifying claims")
    try:
        findings = verify_claims(state)
        return {"audit": findings}
    except Exception as e:
        logger.warning(f"Verification error: {e}")
        return {"audit": []}


def _judge(state: DebateState) -> dict:
    current_round = state["round"]
    logger.info(f"Judging round {current_round}")
    try:
        scorecard = evaluate_round(state)
        return {"scorecards": [scorecard]}
    except Exception as e:
        logger.warning(f"Judge error: {e}")
        from madd.core.schemas import RoundScorecard
        return {"scorecards": [RoundScorecard(round_number=current_round)]}


def _finalize_report(state: DebateState) -> dict:
    logger.info(f"Debate complete after {state['round']} rounds")
    treaty = state.get("treaty")
    if treaty:
        logger.info(f"  Accepted: {len(treaty.accepted_clauses)}, Pending: {len(treaty.pending_clauses)}")
    return {}


def _should_continue(state: DebateState) -> str:
    current_round = state.get("round", 1)
    max_rounds = state.get("max_rounds", 3)
    
    if current_round >= max_rounds:
        return "finalize"
    return "continue"
