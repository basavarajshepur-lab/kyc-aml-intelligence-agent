"""CLI runner for KYC/AML Intelligence Agent."""

import argparse
import json
from pathlib import Path
from dotenv import load_dotenv
from core.pipeline import process_entity, audit

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="KYC/AML Intelligence Agent")
    parser.add_argument("--file", help="JSON file of entities to screen")
    parser.add_argument("--id", help="Screen a single entity by case_id from the sample file")
    parser.add_argument("--batch", action="store_true", help="Process all entities in the file")
    parser.add_argument("--sample", action="store_true", help="Use data/sample_entities.json")
    args = parser.parse_args()

    source_file = "data/sample_entities.json" if args.sample else args.file
    if not source_file:
        parser.error("Provide --file or use --sample")

    entities = json.loads(Path(source_file).read_text())

    if args.id:
        entities = [e for e in entities if e["case_id"] == args.id]
        if not entities:
            print(f"Case ID '{args.id}' not found.")
            return

    if not args.batch and not args.id:
        print("Specify --batch to process all or --id CASE_ID for one.")
        return

    results = []
    for entity in entities:
        case = process_entity(
            case_id=entity["case_id"],
            entity_name=entity["entity_name"],
            entity_type=entity["entity_type"],
            country=entity["country"],
            stated_purpose=entity["stated_purpose"],
            additional_context=entity.get("additional_context"),
        )
        results.append({
            "case_id": case.case_id,
            "entity": case.entity_name,
            "decision": case.decision.recommended_action.value,
            "risk_rating": case.decision.risk_rating.value,
            "risk_score": case.decision.risk_score,
            "confidence": case.decision.confidence,
            "requires_hitl": case.decision.requires_hitl,
            "audit_entry_id": case.audit_entry_id,
        })

    print(f"\n{'='*60}")
    print(f"BATCH RESULTS ({len(results)} cases)")
    print(f"{'='*60}")
    for r in results:
        icon = {"APPROVE": "✓", "ENHANCED_DUE_DILIGENCE": "⚠", "ESCALATE": "🔺", "REJECT": "✗"}.get(r["decision"], "?")
        hitl = " [HITL]" if r["requires_hitl"] else ""
        print(f"  {icon} {r['case_id']:12} {r['entity']:35} {r['decision']:25} {r['risk_rating']:8} {r['risk_score']:3}/100{hitl}")

    stats = audit.get_stats()
    print(f"\nAudit: {stats['total']} total | {stats['approved']} approved | {stats['edd']} EDD | {stats['escalated']} escalated | {stats['rejected']} rejected | {stats['hitl_required']} HITL")


if __name__ == "__main__":
    main()
