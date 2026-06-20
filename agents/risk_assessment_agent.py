"""
Risk Assessment Agent — produces structured KYC risk decision from enriched entity data.

Takes the enrichment output and reasons to a structured decision:
  risk_score (0-100), risk_rating (LOW/MEDIUM/HIGH/CRITICAL),
  recommended_action (APPROVE/EDD/ESCALATE/REJECT), confidence,
  numbered reasoning chain, red flags, and mitigating factors.

Design decisions:
  - Low temperature (0.1): KYC risk decisions must be consistent. Same entity
    profile → same risk rating. Inconsistency is an audit risk.
  - Structured output via tool use: every field is machine-parseable,
    not free text. Downstream systems (audit trail, HITL queue, case management)
    consume structured data, not prose.
  - Conservative HITL policy: HIGH/CRITICAL risk and any REJECT decision
    always route to human review. Cost of a missed sanctions hit or rejected
    legitimate customer both require human accountability.

Regulatory basis:
  FATF Recommendation 10 (CDD), FCA SYSC 6.3, JMLSG Guidance Part I Chapter 5.
"""

from anthropic import Anthropic
from ..core.models import EnrichedEntity, KYCDecision, RiskRating, RecommendedAction

client = Anthropic()

SYSTEM_PROMPT = """You are a senior KYC compliance analyst at a tier-1 bank with 15 years of experience.

You receive enriched entity data and must produce a structured risk assessment covering:
- Risk score (0-100): reflects cumulative risk across all signals
- Risk rating: LOW (<30) / MEDIUM (30-59) / HIGH (60-84) / CRITICAL (85-100)
- Recommended action: APPROVE / ENHANCED_DUE_DILIGENCE / ESCALATE / REJECT
- Confidence in your assessment (0-1)
- Numbered reasoning chain — each step references specific evidence
- Key red flags — specific, not generic
- Mitigating factors — what reduces risk, if anything

Action guidance:
- APPROVE: Low/medium risk, no material concerns
- ENHANCED_DUE_DILIGENCE: Elevated risk requiring additional information before decision (PEP, complex ownership, geographic risk)
- ESCALATE: High-risk factors requiring MLRO/senior compliance review (sanctions-adjacent, adverse media, opacity)
- REJECT: Direct sanctions match (EXACT), confirmed prohibited entity, or overwhelming adverse evidence

HITL policy: REJECT always requires human review. ESCALATE always requires human review.
HIGH/CRITICAL risk rating always requires human review.
Confidence below 0.80 always requires human review (uncertain assessments must not auto-approve)."""

DECISION_TOOL = {
    "name": "record_kyc_decision",
    "description": "Record structured KYC risk assessment decision",
    "input_schema": {
        "type": "object",
        "properties": {
            "risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "risk_rating": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
            "recommended_action": {
                "type": "string",
                "enum": ["APPROVE", "ENHANCED_DUE_DILIGENCE", "ESCALATE", "REJECT"],
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Numbered reasoning steps, each referencing specific evidence",
            },
            "key_red_flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific red flags identified from enrichment data",
            },
            "mitigating_factors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Factors that reduce risk or explain concerning signals",
            },
            "edd_requirements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific EDD steps required (if recommended_action is ENHANCED_DUE_DILIGENCE)",
            },
        },
        "required": [
            "risk_score", "risk_rating", "recommended_action", "confidence",
            "reasoning", "key_red_flags", "mitigating_factors",
        ],
    },
}


def _determine_hitl(decision: KYCDecision) -> tuple[bool, str | None]:
    """Apply HITL routing policy."""
    if decision.recommended_action == RecommendedAction.REJECT:
        return True, "REJECT decision always requires human review — regulatory and legal accountability"
    if decision.recommended_action == RecommendedAction.ESCALATE:
        return True, "ESCALATE decision requires MLRO or senior compliance review"
    if decision.risk_rating in (RiskRating.HIGH, RiskRating.CRITICAL):
        return True, f"{decision.risk_rating.value} risk rating requires human review before any action"
    if decision.confidence < 0.80:
        return True, f"Confidence {decision.confidence:.0%} below 0.80 threshold — uncertain assessment requires human review"
    return False, None


def run(enriched: EnrichedEntity) -> KYCDecision:
    """Produce structured KYC risk decision from enriched entity data."""
    import json

    enrichment_summary = f"""
Entity: {enriched.entity_name} ({enriched.entity_type.value})

SANCTIONS SCREENING:
{f"HITS FOUND ({len(enriched.sanctions_hits)}):" if enriched.sanctions_hits else "No sanctions matches."}
{json.dumps([h.model_dump() for h in enriched.sanctions_hits], indent=2) if enriched.sanctions_hits else ""}

PEP STATUS:
{json.dumps(enriched.pep_record.model_dump() if enriched.pep_record else {"is_pep": False}, indent=2)}

ADVERSE MEDIA:
{f"HITS FOUND ({len(enriched.adverse_media)}):" if enriched.adverse_media else "No adverse media."}
{json.dumps([h.model_dump() for h in enriched.adverse_media], indent=2) if enriched.adverse_media else ""}

COMPANY REGISTRY:
{json.dumps(enriched.company_registry.model_dump(), indent=2) if enriched.company_registry else "N/A (individual)"}

GEOGRAPHIC RISK:
{json.dumps([g.model_dump() for g in enriched.geographic_risks], indent=2) if enriched.geographic_risks else "Not assessed."}

ENRICHMENT NOTES:
{enriched.enrichment_notes or "None."}"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        temperature=0.1,
        system=SYSTEM_PROMPT,
        tools=[DECISION_TOOL],
        tool_choice={"type": "any"},
        messages=[{
            "role": "user",
            "content": f"Assess the KYC risk for this entity and record your structured decision:\n{enrichment_summary}",
        }],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_kyc_decision":
            d = block.input
            rating = RiskRating(d["risk_rating"])
            action = RecommendedAction(d["recommended_action"])

            decision = KYCDecision(
                risk_score=d["risk_score"],
                risk_rating=rating,
                recommended_action=action,
                confidence=d["confidence"],
                reasoning=d["reasoning"],
                key_red_flags=d["key_red_flags"],
                mitigating_factors=d["mitigating_factors"],
                edd_requirements=d.get("edd_requirements", []),
                requires_hitl=False,
            )
            requires_hitl, hitl_reason = _determine_hitl(decision)
            decision.requires_hitl = requires_hitl
            decision.hitl_reason = hitl_reason
            return decision

    # Fallback — conservative default
    return KYCDecision(
        risk_score=80, risk_rating=RiskRating.HIGH,
        recommended_action=RecommendedAction.ESCALATE,
        confidence=0.3,
        reasoning=["Risk assessment could not be completed — conservative escalation applied"],
        key_red_flags=["Assessment failure"],
        mitigating_factors=[],
        requires_hitl=True,
        hitl_reason="Assessment failure — manual review required",
    )
