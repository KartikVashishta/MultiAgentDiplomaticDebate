from typing import cast

from langgraph.graph import StateGraph, END

from madd.core.state import DebateState
from madd.agents import (
    generate_profile,
    generate_turn,
    evaluate_round,
    verify_claims,
)


def build_graph() -> StateGraph:

    graph = StateGraph(DebateState)
    
    graph.add_node("ensure_profiles", _ensure_profiles)
    graph.add_node("opening_statements", _opening_statements)
    graph.add_node("negotiate_round", _negotiate_round)
    graph.add_node("compile_treaty", _compile_treaty)
    graph.add_node("verify", _verify)
    graph.add_node("judge", _judge)
    graph.add_node("finalize_report", _finalize_report)
    
    # Define edges
    graph.set_entry_point("ensure_profiles")
    graph.add_edge("ensure_profiles", "opening_statements")
    graph.add_edge("opening_statements", "negotiate_round")
    graph.add_edge("negotiate_round", "compile_treaty")
    graph.add_edge("compile_treaty", "verify")
    graph.add_edge("verify", "judge")
    
    # Conditional edge: continue or finalize
    graph.add_conditional_edges(
        "judge",
        _should_continue,
        {
            "continue": "negotiate_round",
            "finalize": "finalize_report",
        }
    )
    graph.add_edge("finalize_report", END)
    
    return graph.compile()


# =============================================================================
# Node Implementations
# =============================================================================

def _ensure_profiles(state: DebateState) -> dict:

    scenario = state["scenario"]
    profiles = dict(state["profiles"]) # Copy
    
    print(f"--- Node: Ensure Profiles ---")
    
    for country in scenario.countries:
        if country not in profiles:
            print(f"Generating profile for: {country}")
            profiles[country] = generate_profile(country, scenario.description)
            
    return {"profiles": profiles}


def _opening_statements(state: DebateState) -> dict:
    """Collect opening statements from all countries."""
    scenario = state["scenario"]
    messages = []
    
    print(f"--- Node: Opening Statements (Round 1) ---")
    
    for country in scenario.countries:
        # For opening statements, we can set round=1 context
        # Ideally, we update the state round before this loop, 
        # but since 'opening_statements' implies start, we force it.
        # However, the node return value updates the state.
        
        # We need to pass a temp state with round=1 to the agent?
        # Or just let the agent see round=0 and know it's opening?
        # Let's verify: State has 'round'. We should probably increment round to 1 here?
        pass 

    # Better approach: Iterate countries, generate turns.
    # Since this is "opening", it's effectively Round 1.
    
    new_messages = []
    for country in scenario.countries:
        print(f"{country} is speaking...")
        # We need to temporarily mock round=1 for the agent if it's currently 0
        context_state = state.copy()
        context_state["round"] = 1 
        
        msg = generate_turn(context_state, country)
        new_messages.append(msg)
        
    return {"messages": new_messages, "round": 1}


def _negotiate_round(state: DebateState) -> dict:
    """Run a negotiation round with all countries."""
    scenario = state["scenario"]
    current_round = state["round"] + 1 # Increment for this new round
    
    print(f"--- Node: Negotiate Round {current_round} ---")
    
    new_messages = []
    # In a real debate, order might shuffle or be sequential.
    # Currently simple iteration.
    for country in scenario.countries:
        print(f"{country} is speaking...")
        
        # Update context to reflect this new round
        context_state = state.copy()
        context_state["round"] = current_round
        
        # Also need to append previous messages from THIS round to context?
        # Our state["messages"] only gets updated at the END of the node execution in LangGraph (usually).
        # To allow agents to react to each other WITHIN the round, we might need a sub-loop 
        # or append to context_state["messages"].
        
        # For MVP: Simultaneous turns (agents don't see each other's messages in the SAME round until next node).
        # Or we append locally:
        context_state["messages"] = list(state["messages"]) + new_messages
        
        msg = generate_turn(context_state, country)
        new_messages.append(msg)
        
    return {"messages": new_messages, "round": current_round}


def _compile_treaty(state: DebateState) -> dict:

    # MVP: Just copy existing treaty for now. 
    # Real logic: Parse 'clause_votes' from messages and update clause statuses.
    print(f"--- Node: Compile Treaty ---")
    
    # TODO: Implement complex clause voting logic.
    # For now, pass through.
    return {}


def _verify(state: DebateState) -> dict:

    print(f"--- Node: Verify ---")
    audit_findings = verify_claims(state)
    return {"audit": audit_findings}


def _judge(state: DebateState) -> dict:
    print(f"--- Node: Judge ---")
    scorecard = evaluate_round(state)
    return {"scorecards": [scorecard]}


def _finalize_report(state: DebateState) -> dict:
    print(f"--- Node: Finalize Report ---")
    # MVP: Just print done
    print("Debate concluded.")
    return {}


def _should_continue(state: DebateState) -> str:
    """Determine if debate should continue or finalize."""
    current_round = state.get("round", 1)
    max_rounds = state.get("max_rounds", 3)
    
    if current_round >= max_rounds:
        return "finalize"
    return "continue"
