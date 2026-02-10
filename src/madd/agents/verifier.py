import hashlib
import re
from typing import Any, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, ValidationError

from madd.core.config import get_settings
from madd.core.schemas import AuditFinding, AuditSeverity
from madd.core.state import DebateState


class FindingOutput(BaseModel):
    severity: str = "info"
    category: str = ""
    description: str = ""
    country: str = ""
    evidence: list[str] = Field(default_factory=list)


class VerifierLLMOutput(BaseModel):
    findings: list[FindingOutput | dict[str, Any] | str] = Field(default_factory=list)


BASE_FACTUAL_KEYWORDS = [
    "treaty",
    "agreement",
    "framework",
    "unclos",
    "eez",
    "exclusive economic zone",
    "territorial sea",
    "arbitration",
    "itlos",
    "icj",
    "pca",
    "sovereignty",
    "sanctions",
    "export control",
    "fdi",
    "basing",
    "defense",
    "eia",
    "esia",
    "fpic",
]

LEADER_TITLES = [
    "president",
    "prime minister",
    "king",
    "queen",
    "chancellor",
    "emperor",
]

SUSPICIOUS_MARKERS = [
    "</analysis",
    "to=functions",
    "end_function_call",
    "tool call is done",
    "not_user_visible_exception",
]


def _requires_citation(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    if re.search(r"\d", lowered):
        return True
    return any(keyword in lowered for keyword in keywords)


def _mentions_named_leader(text: str) -> bool:
    lowered = text.lower()
    return any(title in lowered for title in LEADER_TITLES)


def _coerce_finding_output(
    finding: FindingOutput | dict[str, Any] | str,
) -> FindingOutput | None:
    if isinstance(finding, FindingOutput):
        return finding
    if isinstance(finding, dict):
        try:
            return FindingOutput.model_validate(finding)
        except ValidationError:
            return None
    return None


def _sanitize_generated_text(text: str, *, max_chars: int) -> str:
    cleaned = text.replace("\u3011", " ").replace("\u3010", " ")
    lowered = cleaned.lower()
    cutoff = len(cleaned)
    for marker in SUSPICIOUS_MARKERS:
        idx = lowered.find(marker)
        if idx != -1:
            cutoff = min(cutoff, idx)
    cleaned = cleaned[:cutoff]
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" \t\r\n\"'")
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "..."
    return cleaned


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
    router_plan = state.get("router_plan")
    extra_keywords = router_plan.verifier_keywords if router_plan else []
    keywords = BASE_FACTUAL_KEYWORDS + [k.lower() for k in extra_keywords]
    
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
            elif _requires_citation(m.public_statement, keywords):
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
    
    contradiction_focus = _build_contradiction_focus(router_plan)
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
- evidence: list of specific quotes showing the issue
""" + (f"\nPrioritize contradiction checks: {contradiction_focus}" if contradiction_focus else "")

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
        
        severity_map = {
            "info": AuditSeverity.INFO,
            "warning": AuditSeverity.WARNING,
            "error": AuditSeverity.ERROR,
        }
        for raw_finding in output.findings:
            finding = _coerce_finding_output(raw_finding)
            if not finding:
                continue
            description = _sanitize_generated_text(finding.description or "", max_chars=500)
            country = _sanitize_generated_text(finding.country or "", max_chars=80)
            category = _sanitize_generated_text(finding.category or "general", max_chars=60) or "general"
            severity_key = _sanitize_generated_text(finding.severity or "", max_chars=20).lower()
            evidence = [
                cleaned
                for cleaned in (
                    _sanitize_generated_text(item, max_chars=280)
                    for item in (finding.evidence or [])
                    if isinstance(item, str)
                )
                if cleaned
            ]
            if not description:
                continue
            msg = message_map.get(country or "")
            if (
                "leader" in description.lower()
                and msg
                and not _mentions_named_leader(msg.public_statement)
            ):
                continue
            findings.append(AuditFinding(
                severity=severity_map.get(severity_key, AuditSeverity.INFO),
                category=category,
                description=description,
                country=country or None,
                round_number=current_round,
                evidence=evidence,
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


def _build_contradiction_focus(router_plan) -> str:
    if not router_plan:
        return ""
    archetypes = {a.archetype for a in (router_plan.archetypes or []) if a.score >= 0.4}
    focus = []
    if "SECURITY_DEFENSE" in archetypes:
        focus.append("approval vs notification, basing duration, force access conditions")
    if "RESOURCES_MINERALS" in archetypes:
        focus.append("licensing vs free access, audit rights vs confidentiality")
    if "HUMAN_RIGHTS_COMMUNITY" in archetypes:
        focus.append("consent vs consultation thresholds, grievance access")
    if "TRADE_SANCTIONS_FINANCE" in archetypes:
        focus.append("export control licensing vs unrestricted transfer")
    if "ENVIRONMENT_CLIMATE" in archetypes:
        focus.append("no-go zones vs development access, remediation obligations")
    return "; ".join(focus)
