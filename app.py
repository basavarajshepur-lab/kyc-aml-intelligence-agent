"""
KYC/AML Intelligence Agent — Streamlit HITL interface

Tabs:
  1. Screen Entity   — manual input + run assessment
  2. Sample Cases    — pre-loaded entities covering all risk scenarios
  3. HITL Review     — analyst decision queue
  4. Audit Trail     — full decision log
  5. PM Guide        — docs/pm-guide-ai-in-kyc.md
"""

import json
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from core.models import EntityType, RecommendedAction, RiskRating
from core.pipeline import process_entity, audit

load_dotenv()

st.set_page_config(page_title="KYC/AML Intelligence Agent", page_icon="🔍", layout="wide")
st.title("KYC/AML Intelligence Agent")
st.markdown(
    "**Multi-agent entity screening** — Sanctions · PEP · Adverse Media · "
    "Corporate Registry · Geographic Risk · AI Risk Scoring · HITL Review · Audit Trail"
)
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Screen Entity", "Sample Cases", "HITL Review Queue", "Audit Trail", "PM Guide"]
)

ACTION_COLOUR = {
    "APPROVE": "green",
    "ENHANCED_DUE_DILIGENCE": "orange",
    "ESCALATE": "red",
    "REJECT": "red",
}
RATING_ICON = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "CRITICAL": "🔴"}

# ── Tab 1: Screen Entity ──────────────────────────────────────────────────────
with tab1:
    st.header("Screen an Entity")

    col1, col2 = st.columns(2)
    with col1:
        entity_name = st.text_input("Entity name", placeholder="e.g. Viktor Petrov")
        entity_type = st.selectbox("Entity type", ["individual", "company"])
        country = st.text_input("Country (ISO code or name)", placeholder="e.g. GB, RU, NG")
    with col2:
        case_id = st.text_input("Case ID", value="KYC_MANUAL_001")
        stated_purpose = st.text_area(
            "Stated purpose of relationship",
            placeholder="Business account for...",
            height=120,
        )

    if st.button("Run KYC Screening", type="primary"):
        if not entity_name or not country:
            st.error("Entity name and country are required.")
        else:
            with st.spinner("Running enrichment + risk assessment..."):
                try:
                    case = process_entity(
                        case_id=case_id,
                        entity_name=entity_name,
                        entity_type=entity_type,
                        country=country,
                        stated_purpose=stated_purpose,
                    )
                    st.session_state.last_case = case
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.info("Ensure ANTHROPIC_API_KEY is set in .env")

    if "last_case" in st.session_state:
        case = st.session_state.last_case
        dec = case.decision
        enr = case.enriched

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Decision", dec.recommended_action.value)
        c2.metric("Risk Rating", f"{RATING_ICON.get(dec.risk_rating.value, '')} {dec.risk_rating.value}")
        c3.metric("Risk Score", f"{dec.risk_score}/100")
        c4.metric("Confidence", f"{dec.confidence:.0%}")

        if dec.requires_hitl:
            st.warning(f"⚠ HITL required — {dec.hitl_reason}")
        else:
            colour = ACTION_COLOUR.get(dec.recommended_action.value, "gray")
            st.success(f"Auto-decision: **{dec.recommended_action.value}**")

        col1, col2 = st.columns(2)
        with col1:
            with st.expander("Enrichment Results", expanded=True):
                st.markdown(f"**Sanctions hits:** {len(enr.sanctions_hits)}")
                for h in enr.sanctions_hits:
                    st.error(f"⛔ {h.list_name} — {h.match_type} match ({h.match_score:.0%}): {h.entry_details[:100]}")
                pep = enr.pep_record
                if pep and pep.is_pep:
                    st.warning(f"👤 PEP — {pep.role} | Tier {pep.pep_tier} | Risk: {pep.risk_level}")
                else:
                    st.success("No PEP record")
                if enr.adverse_media:
                    for hit in enr.adverse_media:
                        st.warning(f"📰 {hit.category.upper()}: {hit.headline}")
                else:
                    st.success("No adverse media")
                if enr.company_registry:
                    reg = enr.company_registry
                    st.info(f"🏢 {reg.registered_name} | {reg.jurisdiction} | Transparency: {reg.ownership_transparency}")
                for gr in enr.geographic_risks:
                    icon = "🔴" if gr.risk_level == "HIGH" else "🟡" if gr.risk_level == "MEDIUM" else "🟢"
                    st.info(f"{icon} {gr.country} — {gr.fatf_status} | {gr.risk_level} risk")

        with col2:
            with st.expander("AI Reasoning", expanded=True):
                if dec.key_red_flags:
                    st.markdown("**Red flags:**")
                    for f in dec.key_red_flags:
                        st.markdown(f"- 🚩 {f}")
                if dec.mitigating_factors:
                    st.markdown("**Mitigating factors:**")
                    for f in dec.mitigating_factors:
                        st.markdown(f"- ✓ {f}")
                st.markdown("**Reasoning chain:**")
                for i, r in enumerate(dec.reasoning, 1):
                    st.markdown(f"{i}. {r}")
                if dec.edd_requirements:
                    st.markdown("**EDD requirements:**")
                    for r in dec.edd_requirements:
                        st.markdown(f"- {r}")

        st.caption(f"Audit entry #{case.audit_entry_id} logged")

# ── Tab 2: Sample Cases ───────────────────────────────────────────────────────
with tab2:
    st.header("Sample KYC Cases")
    st.markdown(
        "10 pre-built entities covering the full risk spectrum: "
        "clean individuals, sanctions hits, PEPs, BVI shells, adverse media, name collisions, and legitimate SMEs."
    )

    with open("data/sample_entities.json") as f:
        samples = json.load(f)

    for sample in samples:
        with st.expander(
            f"**{sample['case_id']}** — {sample['entity_name']} ({sample['entity_type'].upper()}) | {sample['expected_outcome'].split('—')[0].strip()}"
        ):
            st.markdown(f"**Country:** {sample['country']}")
            st.markdown(f"**Stated purpose:** {sample['stated_purpose']}")
            st.markdown(f"**Expected outcome:** `{sample['expected_outcome']}`")
            if st.button("Run Screening", key=f"sample_{sample['case_id']}"):
                with st.spinner(f"Screening {sample['entity_name']}..."):
                    try:
                        case = process_entity(
                            case_id=sample["case_id"],
                            entity_name=sample["entity_name"],
                            entity_type=sample["entity_type"],
                            country=sample["country"],
                            stated_purpose=sample["stated_purpose"],
                            additional_context=sample.get("additional_context"),
                        )
                        st.session_state.last_case = case
                        dec = case.decision
                        st.metric("Decision", dec.recommended_action.value)
                        st.metric("Risk", f"{dec.risk_rating.value} ({dec.risk_score}/100)")
                        if dec.requires_hitl:
                            st.warning(f"HITL required — {dec.hitl_reason}")
                        if dec.key_red_flags:
                            for f in dec.key_red_flags:
                                st.error(f"🚩 {f}")
                    except Exception as e:
                        st.error(f"Error: {e}")

# ── Tab 3: HITL Review Queue ──────────────────────────────────────────────────
with tab3:
    st.header("HITL Review Queue")
    st.caption("Cases requiring analyst review before any decision is actioned.")

    pending = audit.get_pending_hitl()
    stats = audit.get_stats()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pending Review", len(pending))
    c2.metric("Total Cases", stats["total"])
    c3.metric("HITL Required", stats["hitl_required"])
    c4.metric("Reviewed", stats["reviewed"])

    if not pending:
        st.info("No cases pending review. Run some sample entities first.")
    else:
        for item in pending:
            red_flags = json.loads(item.get("red_flags", "[]"))
            reasoning = json.loads(item.get("reasoning", "[]"))
            with st.expander(
                f"#{item['entry_id']} — {item['entity_name']} | AI: {item['ai_decision']} | Score: {item['ai_risk_score']}/100",
                expanded=True,
            ):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Entity:** {item['entity_name']} ({item['entity_type']})")
                    st.markdown(f"**AI Decision:** `{item['ai_decision']}` | Risk: {item['ai_risk_score']}/100 | Confidence: {item['ai_confidence']:.0%}")
                    st.markdown(f"**HITL reason:** {item.get('hitl_reason', 'N/A')}")
                    if red_flags:
                        st.markdown("**Red flags:**")
                        for f in red_flags:
                            st.markdown(f"- 🚩 {f}")
                    if reasoning:
                        with st.expander("Full reasoning"):
                            for i, r in enumerate(reasoning, 1):
                                st.markdown(f"{i}. {r}")

                with col2:
                    analyst_id = st.text_input("Analyst ID", value="analyst_1", key=f"aid_{item['entry_id']}")
                    decision = st.selectbox(
                        "Your decision",
                        ["APPROVE", "ENHANCED_DUE_DILIGENCE", "ESCALATE", "REJECT"],
                        key=f"dec_{item['entry_id']}",
                    )
                    notes = st.text_area("Notes", key=f"notes_{item['entry_id']}", height=80)
                    if st.button("Submit", key=f"sub_{item['entry_id']}"):
                        if not notes.strip() and decision in ("REJECT", "ESCALATE"):
                            st.error("Notes required for REJECT/ESCALATE.")
                        else:
                            audit.log_analyst_review(
                                entry_id=item["entry_id"],
                                analyst_id=analyst_id,
                                analyst_decision=decision,
                                analyst_notes=notes,
                                final_outcome=decision,
                            )
                            st.success(f"Review logged — {decision}")
                            st.rerun()

# ── Tab 4: Audit Trail ────────────────────────────────────────────────────────
with tab4:
    st.header("Audit Trail")
    st.caption("Append-only log of all AI decisions and analyst reviews. Exportable for regulatory submission.")

    stats = audit.get_stats()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", stats["total"])
    c2.metric("Approved", stats["approved"])
    c3.metric("EDD", stats["edd"])
    c4.metric("Escalated", stats["escalated"])
    c5.metric("Rejected", stats["rejected"])

    recent = audit.get_recent(50)
    if not recent:
        st.info("No cases logged yet.")
    else:
        import pandas as pd
        rows = [
            {
                "ID": r["entry_id"],
                "Entity": r["entity_name"],
                "Type": r["entity_type"],
                "AI Decision": r["ai_decision"],
                "Score": r["ai_risk_score"],
                "Confidence": f"{r['ai_confidence']:.0%}",
                "HITL": "Yes" if r["requires_hitl"] else "No",
                "Analyst Decision": r.get("analyst_decision") or "—",
                "Reviewed By": r.get("analyst_id") or "—",
                "Timestamp": r["timestamp_utc"][:16],
            }
            for r in recent
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if st.button("Export CSV"):
            import csv, io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            st.download_button("Download", output.getvalue(), "kyc_audit_export.csv", "text/csv")

# ── Tab 5: PM Guide ───────────────────────────────────────────────────────────
with tab5:
    guide_path = Path("docs/pm-guide-ai-in-kyc.md")
    if guide_path.exists():
        st.markdown(guide_path.read_text())
    else:
        st.info("Guide not found — check docs/pm-guide-ai-in-kyc.md")
