from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Citation(BaseModel):
    id: str = Field(default="", description="Unique citation ID")
    title: str = Field(..., description="Title of the source")
    url: str = Field(..., description="URL of the source")
    snippet: str = Field(default="", description="Relevant excerpt")
    retrieved_at: datetime = Field(default_factory=_utc_now)
    quote: Optional[str] = None
    topic: Optional[str] = Field(None, description="Topic this citation supports")


class EconomicData(BaseModel):
    gdp_usd_billions: Optional[float] = None
    gdp_year: Optional[int] = None
    gdp_growth_pct: Optional[float] = None
    major_industries: list[str] = Field(default_factory=list)
    trade_partners: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class CountryFacts(BaseModel):
    name: str
    region: Optional[str] = None
    population: Optional[int] = None
    government_type: Optional[str] = None
    current_leaders: list[str] = Field(default_factory=list)
    economy: EconomicData = Field(default_factory=EconomicData)
    colonial_history: Optional[str] = None
    major_conflicts: list[str] = Field(default_factory=list)
    treaties: list[str] = Field(default_factory=list)
    international_memberships: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    leaders_citations: list[Citation] = Field(default_factory=list)
    history_citations: list[Citation] = Field(default_factory=list)


class CountryStrategy(BaseModel):
    core_policy_goals: list[str] = Field(default_factory=list)
    alliance_patterns: list[str] = Field(default_factory=list)
    negotiation_style: Optional[str] = None
    negotiation_tactics: list[str] = Field(default_factory=list)
    decision_making_process: Optional[str] = None
    security_concerns: list[str] = Field(default_factory=list)
    economic_interests: list[str] = Field(default_factory=list)
    key_allies: list[str] = Field(default_factory=list)
    key_rivals: list[str] = Field(default_factory=list)
    red_lines: list[str] = Field(default_factory=list)
    negotiation_priorities: list[str] = Field(default_factory=list)


class CountryProfile(BaseModel):
    facts: CountryFacts
    strategy: CountryStrategy = Field(default_factory=CountryStrategy)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    version: int = Field(default=1)
    
    def all_citations(self) -> list[Citation]:
        cites = list(self.facts.citations)
        cites.extend(self.facts.economy.citations)
        cites.extend(self.facts.leaders_citations)
        cites.extend(self.facts.history_citations)
        return cites


class ClauseStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AMENDED = "amended"
    WITHDRAWN = "withdrawn"


class Clause(BaseModel):
    id: str
    text: str
    proposed_by: str
    status: ClauseStatus = Field(default=ClauseStatus.PROPOSED)
    supporters: list[str] = Field(default_factory=list)
    objectors: list[str] = Field(default_factory=list)
    amendments: list[str] = Field(default_factory=list)
    proposed_round: int
    resolved_round: Optional[int] = None


class TreatyDraft(BaseModel):
    title: Optional[str] = None
    preamble: Optional[str] = None
    clauses: list[Clause] = Field(default_factory=list)
    
    @property
    def accepted_clauses(self) -> list[Clause]:
        return [c for c in self.clauses if c.status == ClauseStatus.ACCEPTED]
    
    @property
    def pending_clauses(self) -> list[Clause]:
        return [c for c in self.clauses if c.status == ClauseStatus.PROPOSED]


class CountryScore(BaseModel):
    country: str
    score: float = Field(..., ge=0, le=10)
    reasoning: str = ""
    diplomatic_effectiveness: Optional[float] = None
    strategic_alignment: Optional[float] = None
    treaty_contribution: Optional[float] = None


class RoundScorecard(BaseModel):
    round_number: int
    scores: list[CountryScore] = Field(default_factory=list)
    rankings: list[str] = Field(default_factory=list)
    summary: str = ""
    clauses_proposed: int = 0
    clauses_accepted: int = 0
    clauses_rejected: int = 0


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AuditFinding(BaseModel):
    severity: AuditSeverity
    category: str
    description: str
    country: Optional[str] = None
    round_number: Optional[int] = None
    evidence: list[str] = Field(default_factory=list)


class ProposedClause(BaseModel):
    text: str
    rationale: str = ""


class DebateMessage(BaseModel):
    round_number: int
    country: str
    public_statement: str
    proposed_clauses: list[ProposedClause] = Field(default_factory=list)
    clause_votes: dict[str, str] = Field(default_factory=dict)
    private_intent: Optional[str] = None
    acceptance_conditions: list[str] = Field(default_factory=list)
    red_lines: list[str] = Field(default_factory=list)
    references_used: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=_utc_now)
