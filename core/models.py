"""Pydantic models for the KYC/AML Entity Intelligence pipeline."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    INDIVIDUAL = "individual"
    COMPANY = "company"


class RiskRating(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendedAction(str, Enum):
    APPROVE = "APPROVE"
    ENHANCED_DUE_DILIGENCE = "ENHANCED_DUE_DILIGENCE"
    ESCALATE = "ESCALATE"
    REJECT = "REJECT"


class SanctionsHit(BaseModel):
    list_name: str          # OFAC_SDN / UN_CONSOLIDATED / HMT / EU
    match_type: str         # EXACT / FUZZY / ALIAS
    match_score: float      # 0-1
    entry_type: str         # individual / entity / vessel / aircraft
    entry_details: str
    listed_date: Optional[str] = None
    program: Optional[str] = None  # e.g. RUSSIA, IRAN, DPRK


class PEPRecord(BaseModel):
    is_pep: bool
    pep_type: Optional[str] = None         # DIRECT / ASSOCIATE / FAMILY
    role: Optional[str] = None
    country: Optional[str] = None
    pep_tier: Optional[int] = None         # 1=head of state, 2=senior official, 3=local/minor
    active: Optional[bool] = None
    risk_level: Optional[str] = None       # HIGH / MEDIUM / LOW


class AdverseMediaHit(BaseModel):
    source: str
    headline: str
    date: str
    category: str    # financial_crime / corruption / sanctions_breach / fraud / other
    summary: str
    url: Optional[str] = None


class CompanyRegistryData(BaseModel):
    registered_name: str
    registration_number: Optional[str] = None
    jurisdiction: str
    incorporation_date: Optional[str] = None
    status: str          # active / dissolved / struck_off
    directors: list[str] = []
    beneficial_owners: list[str] = []      # PSC / UBO data
    ownership_transparency: str            # HIGH / MEDIUM / LOW / OPAQUE
    registered_address: Optional[str] = None


class GeographicRisk(BaseModel):
    country: str
    fatf_status: str     # BLACKLIST / GREYLIST / CLEAN
    corruption_perception_index: Optional[int] = None  # 0-100, higher = less corrupt
    risk_level: str      # HIGH / MEDIUM / LOW
    notes: str = ""


class EnrichedEntity(BaseModel):
    case_id: str
    entity_name: str
    entity_type: EntityType
    sanctions_hits: list[SanctionsHit] = []
    pep_record: Optional[PEPRecord] = None
    adverse_media: list[AdverseMediaHit] = []
    company_registry: Optional[CompanyRegistryData] = None
    geographic_risks: list[GeographicRisk] = []
    enrichment_notes: str = ""


class KYCDecision(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    risk_rating: RiskRating
    recommended_action: RecommendedAction
    confidence: float = Field(ge=0, le=1)
    reasoning: list[str]        # numbered reasoning chain
    key_red_flags: list[str]
    mitigating_factors: list[str]
    requires_hitl: bool
    hitl_reason: Optional[str] = None
    edd_requirements: list[str] = []   # specific EDD steps if EDD recommended


class KYCCase(BaseModel):
    case_id: str
    entity_name: str
    entity_type: EntityType
    stated_purpose: str
    country: str
    enriched: Optional[EnrichedEntity] = None
    decision: Optional[KYCDecision] = None
    audit_entry_id: Optional[int] = None
    hitl_item_id: Optional[int] = None


class AuditEntry(BaseModel):
    entry_id: int
    case_id: str
    entity_name: str
    timestamp_utc: str
    ai_decision: str
    ai_risk_score: int
    ai_confidence: float
    requires_hitl: bool
    analyst_id: Optional[str] = None
    analyst_decision: Optional[str] = None
    analyst_notes: Optional[str] = None
    final_outcome: Optional[str] = None
    reviewed_utc: Optional[str] = None
