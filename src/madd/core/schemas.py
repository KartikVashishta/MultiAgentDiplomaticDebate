"""Pydantic schemas for MADD.

Includes all core data models with citation support for defensibility.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# Citation & Source Tracking
# =============================================================================

class Citation(BaseModel):
    """A citation for a piece of information."""
    
    title: str = Field(..., description="Title of the source")
    url: str = Field(..., description="URL of the source")
    snippet: str = Field(..., description="Relevant excerpt from the source")
    retrieved_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this source was retrieved"
    )
    quote: Optional[str] = Field(
        None,
        description="Direct quote if applicable"
    )


# =============================================================================
# Country Profile (Facts + Strategy separation)
# =============================================================================

class EconomicData(BaseModel):
    """Normalized economic data structure."""
    
    gdp_usd_billions: Optional[float] = Field(None, description="GDP in billions USD")
    gdp_year: Optional[int] = Field(None, description="Year of GDP measurement")
    gdp_growth_pct: Optional[float] = Field(None, description="GDP growth percentage")
    major_industries: list[str] = Field(default_factory=list)
    trade_partners: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class CountryFacts(BaseModel):
    """Factual information about a country with citations."""
    
    name: str
    region: Optional[str] = None
    population: Optional[int] = None
    government_type: Optional[str] = None
    current_leaders: list[str] = Field(default_factory=list)
    
    # Economic data (normalized)
    economy: EconomicData = Field(default_factory=EconomicData)
    
    # Historical context
    colonial_history: Optional[str] = None
    major_conflicts: list[str] = Field(default_factory=list)
    
    # Treaties and memberships
    treaties: list[str] = Field(default_factory=list)
    international_memberships: list[str] = Field(default_factory=list)
    
    # All citations for factual claims
    citations: list[Citation] = Field(default_factory=list)


class CountryStrategy(BaseModel):
    """Strategic and policy information (less verifiable, more interpretive)."""
    
    # Foreign policy
    core_policy_goals: list[str] = Field(default_factory=list)
    alliance_patterns: list[str] = Field(default_factory=list)
    
    # Diplomatic behavior
    negotiation_style: Optional[str] = None
    negotiation_tactics: list[str] = Field(default_factory=list)
    decision_making_process: Optional[str] = None
    
    # Strategic interests
    security_concerns: list[str] = Field(default_factory=list)
    economic_interests: list[str] = Field(default_factory=list)
    
    # Relationships
    key_allies: list[str] = Field(default_factory=list)
    key_rivals: list[str] = Field(default_factory=list)
    
    # Red lines and priorities
    red_lines: list[str] = Field(default_factory=list)
    negotiation_priorities: list[str] = Field(default_factory=list)


class CountryProfile(BaseModel):
    """Complete country profile combining facts and strategy."""
    
    facts: CountryFacts
    strategy: CountryStrategy = Field(default_factory=CountryStrategy)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)


# =============================================================================
# Treaty & Clauses
# =============================================================================

class ClauseStatus(str, Enum):
    """Status of a treaty clause."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AMENDED = "amended"
    WITHDRAWN = "withdrawn"


class Clause(BaseModel):
    """A single clause in a treaty draft."""
    
    id: str = Field(..., description="Unique clause identifier")
    text: str = Field(..., description="Clause content")
    proposed_by: str = Field(..., description="Country that proposed this clause")
    status: ClauseStatus = Field(default=ClauseStatus.PROPOSED)
    
    # Voting/support tracking
    supporters: list[str] = Field(default_factory=list)
    objectors: list[str] = Field(default_factory=list)
    
    # Amendment history
    amendments: list[str] = Field(
        default_factory=list,
        description="List of amendment descriptions"
    )
    
    # Round tracking
    proposed_round: int = Field(..., description="Round when proposed")
    resolved_round: Optional[int] = Field(None, description="Round when resolved")


class TreatyDraft(BaseModel):
    """Current state of the treaty being negotiated."""
    
    title: Optional[str] = None
    preamble: Optional[str] = None
    clauses: list[Clause] = Field(default_factory=list)
    
    @property
    def accepted_clauses(self) -> list[Clause]:
        """Get all accepted clauses."""
        return [c for c in self.clauses if c.status == ClauseStatus.ACCEPTED]
    
    @property
    def pending_clauses(self) -> list[Clause]:
        """Get all pending/proposed clauses."""
        return [c for c in self.clauses if c.status == ClauseStatus.PROPOSED]


# =============================================================================
# Scoring & Audit
# =============================================================================

class CountryScore(BaseModel):
    """Score for a single country in a round."""
    
    country: str
    score: float = Field(..., ge=0, le=10)
    reasoning: str
    
    # Detailed metrics
    diplomatic_effectiveness: Optional[float] = Field(None, ge=0, le=10)
    strategic_alignment: Optional[float] = Field(None, ge=0, le=10)
    treaty_contribution: Optional[float] = Field(None, ge=0, le=10)


class RoundScorecard(BaseModel):
    """Scorecard for a debate round."""
    
    round_number: int
    scores: list[CountryScore] = Field(default_factory=list)
    rankings: list[str] = Field(default_factory=list)
    summary: str = ""
    
    # Treaty progress metrics
    clauses_proposed: int = 0
    clauses_accepted: int = 0
    clauses_rejected: int = 0


class AuditSeverity(str, Enum):
    """Severity of an audit finding."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AuditFinding(BaseModel):
    """A finding from the verifier agent."""
    
    severity: AuditSeverity
    category: str = Field(..., description="e.g., 'contradiction', 'unsupported_claim'")
    description: str
    country: Optional[str] = None
    round_number: Optional[int] = None
    evidence: list[str] = Field(default_factory=list)


# =============================================================================
# Debate Messages (Structured Turn Output)
# =============================================================================

class ProposedClause(BaseModel):
    """A clause proposed during a turn."""
    
    text: str
    rationale: str


class DebateMessage(BaseModel):
    """Structured output from a country's turn."""
    
    round_number: int
    country: str
    
    # Public output
    public_statement: str
    proposed_clauses: list[ProposedClause] = Field(default_factory=list)
    
    # Positions on existing clauses
    clause_votes: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of clause_id -> 'support'|'oppose'|'amend'"
    )
    
    # Private intent (for analysis, not shown to other agents)
    private_intent: Optional[str] = None
    acceptance_conditions: list[str] = Field(default_factory=list)
    red_lines: list[str] = Field(default_factory=list)
    
    # Citation references
    references_used: list[str] = Field(
        default_factory=list,
        description="Citation IDs referenced in this statement"
    )
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
