from pydantic import BaseModel
from typing import List, Optional, Union, Dict

class BasicInfo(BaseModel):
    name: str
    region: Optional[str] = None
    population: Optional[int] = None

class Government(BaseModel):
    government_type: Optional[str] = None
    current_leadership: Optional[List[str]] = None
    political_ideologies: Optional[List[str]] = None

class HistoricalContext(BaseModel):
    colonial_history: Optional[str] = None
    major_conflicts: Optional[List[str]] = None
    evolution_of_foreign_policy: Optional[str] = None

class ForeignPolicy(BaseModel):
    core_goals: Optional[List[str]] = None
    alliance_patterns: Optional[List[str]] = None
    global_issue_positions: Optional[List[str]] = None
    treaties_and_agreements: Optional[List[str]] = None

class EconomicProfile(BaseModel):
    gdp: Optional[float] = None
    gdp_unit: Optional[str] = None
    gdp_year: Optional[str] = None
    major_industries: Optional[List[str]] = None
    trade_relations: Optional[List[str]] = None
    development_goals: Optional[List[str]] = None

class CulturalSocietal(BaseModel):
    cultural_values: Optional[List[str]] = None
    public_opinion: Optional[str] = None
    communication_style: Optional[str] = None

class DiplomaticBehavior(BaseModel):
    style: Optional[str] = None
    negotiation_tactics: Optional[List[str]] = None
    decision_making_process: Optional[str] = None
    short_term_objectives: Optional[List[str]] = None
    long_term_vision: Optional[List[str]] = None

class StrategicInterests(BaseModel):
    security_concerns: Optional[List[str]] = None
    economic_interests: Optional[List[str]] = None
    cultural_ideological_promotion: Optional[List[str]] = None

class RelationshipsAndAlliances(BaseModel):
    past_alliances: Optional[List[str]] = None
    rivalries_conflicts: Optional[List[str]] = None
    diplomatic_reputation: Optional[str] = None

class MemorySeeds(BaseModel):
    previous_resolutions: Optional[List[str]] = None
    memorable_events: Optional[List[str]] = None
    alliances_and_deals: Optional[List[str]] = None

class CountryProfile(BaseModel):

    basic_info: BasicInfo
    government: Government
    historical_context: HistoricalContext
    foreign_policy: ForeignPolicy
    economic_profile: EconomicProfile
    cultural_societal: CulturalSocietal
    diplomatic_behavior: DiplomaticBehavior
    strategic_interests: StrategicInterests
    relationships_alliances: RelationshipsAndAlliances
    memory_seeds: MemorySeeds