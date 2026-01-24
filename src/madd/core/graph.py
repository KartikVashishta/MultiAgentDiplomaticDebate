from typing import cast
import uuid

from langgraph.graph import StateGraph, END

from madd.core.state import DebateState
from madd.core.schemas import (
    Clause, ClauseStatus, TreatyDraft, DebateMessage, ProposedClause
)
from madd.stores.profile_store import ensure_profile
from madd.agents.country import generate_turn
from madd.agents.judge import evaluate_round
from madd.agents.verifier import verify_claims


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
    
    print(f"[ensure_profiles] Loading/generating profiles for {len(scenario.countries)} countries")
    
    for country in scenario.countries:
        print(f"  - {country}...")
        profiles[country] = ensure_profile(country, scenario.description)
    
    return {"profiles": profiles}


def _opening_statements(state: DebateState) -> dict:
    scenario = state["scenario"]
    print(f"[opening_statements] Round 1")
    
    new_messages = []
    temp_state = dict(state)
    temp_state["round"] = 1
    
    for country in scenario.countries:
        print(f"  - {country} speaking...")
        msg = generate_turn(temp_state, country)
        msg.round_number = 1
        new_messages.append(msg)
        temp_state["messages"] = list(state.get("messages", [])) + new_messages
    
    return {"messages": new_messages, "round": 1}


def _negotiate_round(state: DebateState) -> dict:
    scenario = state["scenario"]
    current_round = state["round"] + 1
    print(f"[negotiate_round] Round {current_round}")
    
    new_messages = []
    temp_state = dict(state)
    temp_state["round"] = current_round
    
    for country in scenario.countries:
        print(f"  - {country} speaking...")
        temp_state["messages"] = list(state.get("messages", [])) + new_messages
        msg = generate_turn(temp_state, country)
        msg.round_number = current_round
        new_messages.append(msg)
    
    return {"messages": new_messages, "round": current_round}


def _compile_treaty(state: DebateState) -> dict:
    print(f"[compile_treaty] Processing clauses")
    
    current_round = state["round"]
    messages = state.get("messages", [])
    treaty = state.get("treaty") or TreatyDraft()
    countries = state["scenario"].countries
    existing_clause_ids = {c.id for c in treaty.clauses}
    
    round_messages = [m for m in messages if m.round_number == current_round]
    
    new_clauses = []
    for msg in round_messages:
        for proposed in msg.proposed_clauses:
            clause_id = f"C{len(treaty.clauses) + len(new_clauses) + 1}"
            new_clauses.append(Clause(
                id=clause_id,
                text=proposed.text,
                proposed_by=msg.country,
                status=ClauseStatus.PROPOSED,
                proposed_round=current_round,
                supporters=[msg.country],
                objectors=[],
            ))
    
    all_clauses = list(treaty.clauses) + new_clauses
    
    for clause in all_clauses:
        if clause.status != ClauseStatus.PROPOSED:
            continue
        
        for msg in round_messages:
            if msg.country == clause.proposed_by:
                continue
            
            vote = msg.clause_votes.get(clause.id, "")
            if vote == "support" and msg.country not in clause.supporters:
                clause.supporters.append(msg.country)
            elif vote == "oppose" and msg.country not in clause.objectors:
                clause.objectors.append(msg.country)
    
    for clause in all_clauses:
        if clause.status != ClauseStatus.PROPOSED:
            continue
        
        support_count = len(clause.supporters)
        oppose_count = len(clause.objectors)
        total = len(countries)
        
        if support_count > total / 2:
            clause.status = ClauseStatus.ACCEPTED
            clause.resolved_round = current_round
        elif oppose_count > total / 2:
            clause.status = ClauseStatus.REJECTED
            clause.resolved_round = current_round
    
    updated_treaty = TreatyDraft(
        title=treaty.title or f"Treaty on {state['scenario'].name}",
        preamble=treaty.preamble,
        clauses=all_clauses,
    )
    
    return {"treaty": updated_treaty}


def _verify(state: DebateState) -> dict:
    print(f"[verify] Checking claims")
    try:
        findings = verify_claims(state)
        return {"audit": findings}
    except Exception as e:
        print(f"  Verification error: {e}")
        return {"audit": []}


def _judge(state: DebateState) -> dict:
    print(f"[judge] Evaluating round {state['round']}")
    try:
        scorecard = evaluate_round(state)
        return {"scorecards": [scorecard]}
    except Exception as e:
        print(f"  Judge error: {e}")
        from madd.core.schemas import RoundScorecard
        return {"scorecards": [RoundScorecard(round_number=state["round"])]}


def _finalize_report(state: DebateState) -> dict:
    print(f"[finalize_report] Debate complete after {state['round']} rounds")
    return {}


def _should_continue(state: DebateState) -> str:
    current_round = state.get("round", 1)
    max_rounds = state.get("max_rounds", 3)
    
    if current_round >= max_rounds:
        return "finalize"
    return "continue"
