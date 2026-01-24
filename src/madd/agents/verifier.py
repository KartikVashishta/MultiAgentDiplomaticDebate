from typing import cast
import hashlib
import re

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


FACTUAL_KEYWORDS = [
    "unclos",
    "eez",
    "exclusive economic zone",
    "territorial sea",
    "contiguous zone",
    "high seas",
    "transit passage",
    "innocent passage",
    "arbitration",
    "itlos",
    "icj",
    "pca",
    "code of conduct",
    "asean",
    "mmsac",
    "mmacc",
]

LEADER_TITLES = [
    "president",
    "prime minister",
    "king",
    "queen",
    "chancellor",
    "emperor",
]


def _requires_citation(text: str) -> bool:
    lowered = text.lower()
    if re.search(r"\d", lowered):
        return True
    return any(keyword in lowered for keyword in FACTUAL_KEYWORDS)


def _mentions_named_leader(text: str) -> bool:
    lowered = text.lower()
    for title in LEADER_TITLES:
        if title in lowered:
            return True
    return False


def _format_facts(profile) -> str:
    parts = []
    gdp = profile.facts.economy.gdp_usd_billions
    if gdp is None:
        parts.append("GDP: Unknown")
    else:
        parts.append(f"GDP: {gdp}B")
    leaders = profile.facts.current_leaders
    if leaders:
        parts.append(f"Leaders: {leaders}")
    return ", ".join(parts)


def _dedupe_findings(findings: list[AuditFinding]) -> list[AuditFinding]:
    seen = set()
    unique: list[AuditFinding] = []
    for f in findings:
        evidence = [e.strip().lower() for e in (f.evidence or [])]
        key = "|".join([
            f.country or "",
            str(f.round_number or ""),
            f.category or "",
            f.description or "",
            "|".join(sorted(evidence)),
        ])
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
        if digest in seen:
            continue
        seen.add(digest)
        unique.append(f)
    return unique


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
            if not valid_citation_ids:
                findings.append(AuditFinding(
                    severity=AuditSeverity.WARNING,
                    category="profile_missing_citations",
                    description=f"{m.country} has no profile citations; verification is limited",
                    country=m.country,
                    round_number=current_round,
                    evidence=[],
                ))
            elif _requires_citation(m.public_statement):
                findings.append(AuditFinding(
                    severity=AuditSeverity.WARNING,
                    category="unsupported_claim",
                    description=f"{m.country} made factual/legal statements without citations",
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
    message_map = {m.country: m for m in messages}
    for m in messages:
        profile = state["profiles"].get(m.country)
        facts = ""
        if profile:
            facts = _format_facts(profile)
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
            msg = message_map.get(f.country or "")
            if "leader" in (f.description or "").lower() and msg and not _mentions_named_leader(msg.public_statement):
                continue
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
    
    return _dedupe_findings(findings)
