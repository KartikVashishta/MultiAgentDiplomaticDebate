from typing import cast

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from madd.core.config import get_settings
from madd.core.schemas import AuditFinding, AuditSeverity
from madd.core.state import DebateState


class FindingOutput(BaseModel):
    severity: str = "info"
    category: str = ""
    description: str = ""
    country: str = ""
    evidence: list[str] = []


class VerifierLLMOutput(BaseModel):
    findings: list[FindingOutput] = []


def verify_claims(state: DebateState) -> list[AuditFinding]:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.verify_model,
        temperature=0.0,
        api_key=settings.openai_api_key,
        max_retries=settings.max_retries,
    )
    
    current_round = state["round"]
    all_messages = state.get("messages", [])
    messages = [m for m in all_messages if m.round_number == current_round]
    
    if not messages:
        return []
    
    findings: list[AuditFinding] = []
    
    for m in messages:
        profile = state["profiles"].get(m.country)
        if not profile:
            continue
        
        valid_citation_ids = {c.id for c in profile.all_citations()}
        refs_used = m.references_used
        
        if not valid_citation_ids:
            findings.append(AuditFinding(
                severity=AuditSeverity.WARNING,
                category="missing_citations",
                description=f"{m.country} has no citations in profile; verification is limited",
                country=m.country,
                round_number=current_round,
                evidence=[],
            ))
        
        if not refs_used:
            findings.append(AuditFinding(
                severity=AuditSeverity.WARNING,
                category="unsupported_claim",
                description=f"{m.country} made statements without any citation references",
                country=m.country,
                round_number=current_round,
                evidence=[
                    f"Statement snippet: \"{m.public_statement[:150]}...\"",
                    "references_used: []",
                ],
            ))
        else:
            unknown_ids = [cid for cid in refs_used if cid not in valid_citation_ids]
            if unknown_ids:
                findings.append(AuditFinding(
                    severity=AuditSeverity.WARNING,
                    category="unsupported_claim",
                    description=f"{m.country} referenced unknown citation IDs",
                    country=m.country,
                    round_number=current_round,
                    evidence=[
                        f"Unknown IDs: {unknown_ids}",
                        f"Valid IDs: {list(valid_citation_ids)[:5]}",
                        f"Statement snippet: \"{m.public_statement[:100]}...\"",
                    ],
                ))
    
    structured_llm = llm.with_structured_output(VerifierLLMOutput, method="function_calling")
    
    system_prompt = """You are a fact-checking verifier.
Detect:
1. Contradictions between statements and country profile facts
2. Inconsistencies with prior statements
3. Factual errors

Return findings with:
- severity: info/warning/error
- category: contradiction/inconsistency/factual_error
- description: what the issue is
- country: which country
- evidence: list of specific quotes showing the issue"""

    context = ""
    for m in messages:
        profile = state["profiles"].get(m.country)
        facts = ""
        if profile:
            facts = f"GDP: {profile.facts.economy.gdp_usd_billions}B, Leaders: {profile.facts.current_leaders}"
        prior_statements = [
            p for p in all_messages
            if p.country == m.country and p.round_number < current_round
        ]
        prior_text = "\n".join(
            f"Round {p.round_number}: {p.public_statement[:250]}"
            for p in prior_statements[-2:]
        )
        context += (
            f"\n{m.country} (Facts: {facts}):\n"
            f"Prior statements:\n{prior_text or 'None'}\n"
            f"Current statement:\n{m.public_statement[:400]}\n"
        )

    user_prompt = f"""Round {current_round} statements:
{context}

Check for contradictions and inconsistencies only (unsupported claims already checked)."""

    try:
        result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        output = cast(VerifierLLMOutput, result)
        
        severity_map = {"info": AuditSeverity.INFO, "warning": AuditSeverity.WARNING, "error": AuditSeverity.ERROR}
        for f in output.findings:
            findings.append(AuditFinding(
                severity=severity_map.get(f.severity.lower(), AuditSeverity.INFO),
                category=f.category or "general",
                description=f.description,
                country=f.country or None,
                round_number=current_round,
                evidence=f.evidence,
            ))
    except Exception as e:
        print(f"    Verifier LLM error: {e}")
        findings.append(AuditFinding(
            severity=AuditSeverity.ERROR,
            category="verifier_failed",
            description=f"Verifier structured output failed: {e}",
            round_number=current_round,
            evidence=[],
        ))
    
    return findings
