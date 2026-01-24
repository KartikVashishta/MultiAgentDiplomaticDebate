from typing import cast

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from pydantic import BaseModel
from madd.core.config import get_settings
from madd.core.schemas import AuditFinding, AuditSeverity, DebateMessage
from madd.core.state import DebateState


class AuditReport(BaseModel):
    findings: list[AuditFinding]


def verify_claims(state: DebateState) -> list[AuditFinding]:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0.0,
        api_key=settings.openai_api_key
    )

    class AuditResult(AuditReport):
        findings: list[AuditFinding]
        
    structured_llm = llm.with_structured_output(AuditResult)
    
    current_round = state["round"]
    messages = [m for m in state["messages"] if m.round_number == current_round]
    
    if not messages:
        return []

    system_prompt = """You are a Fact-Checking Verifier bot.
Your goal is to detect:
1. Direct contradictions between a country's statement and their profile facts.
2. Claims that are unsupported by citations or clearly hallucinated.
3. Inconsistencies with previous statements from the same country.

Be strict but fair. Only report significant issues."""

    context_text = ""
    for m in messages:
        profile = state["profiles"].get(m.country)
        profile_facts = profile.facts.model_dump_json() if profile else "No profile"
        
        context_text += f"""
---
Country: {m.country}
Statement: {m.public_statement}
Profile Facts: {profile_facts}
---
"""

    user_prompt = f"""Audit the following statements from Round {current_round}:
{context_text}

Return a list of findings."""

    response = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    return response.findings if response else []
