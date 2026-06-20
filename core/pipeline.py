"""KYC/AML pipeline orchestration — enrichment → risk assessment → audit logging."""

from .models import EntityType, KYCCase
from .audit_trail import AuditTrail
from ..agents import enrichment_agent, risk_assessment_agent

audit = AuditTrail()


def process_entity(
    case_id: str,
    entity_name: str,
    entity_type: str,
    country: str,
    stated_purpose: str,
    additional_context: dict | None = None,
) -> KYCCase:
    """Run full KYC pipeline for an entity. Returns complete KYCCase."""
    etype = EntityType(entity_type)

    print(f"\n{'='*60}")
    print(f"KYC SCREENING: {entity_name} ({entity_type.upper()})")
    print(f"{'='*60}")

    print("[1/3] Entity enrichment (sanctions · PEP · adverse media · registry)...")
    enriched = enrichment_agent.run(
        case_id=case_id,
        entity_name=entity_name,
        entity_type=etype,
        country=country,
        additional_context=additional_context,
    )
    print(f"      Sanctions hits: {len(enriched.sanctions_hits)}")
    print(f"      PEP: {'Yes — ' + enriched.pep_record.role if enriched.pep_record and enriched.pep_record.is_pep else 'No'}")
    print(f"      Adverse media: {len(enriched.adverse_media)} item(s)")

    print("[2/3] Risk assessment...")
    decision = risk_assessment_agent.run(enriched)
    print(f"      Decision: {decision.recommended_action.value}")
    print(f"      Risk: {decision.risk_rating.value} ({decision.risk_score}/100)")
    print(f"      Confidence: {decision.confidence:.0%}")
    print(f"      HITL required: {decision.requires_hitl}")

    print("[3/3] Logging to audit trail...")
    entry_id = audit.log_ai_decision(
        case_id=case_id,
        entity_name=entity_name,
        entity_type=entity_type,
        decision=decision,
        enriched=enriched,
    )
    print(f"      Audit entry: #{entry_id}")

    outcome_icon = {
        "APPROVE": "✓",
        "ENHANCED_DUE_DILIGENCE": "⚠",
        "ESCALATE": "🔺",
        "REJECT": "✗",
    }.get(decision.recommended_action.value, "?")
    print(f"\n{outcome_icon}  {decision.recommended_action.value} — {decision.risk_rating.value} risk ({decision.risk_score}/100)")
    if decision.key_red_flags:
        for flag in decision.key_red_flags[:2]:
            print(f"   Red flag: {flag}")

    return KYCCase(
        case_id=case_id,
        entity_name=entity_name,
        entity_type=etype,
        stated_purpose=stated_purpose,
        country=country,
        enriched=enriched,
        decision=decision,
        audit_entry_id=entry_id,
    )
