# KYC/AML Intelligence Agent

**Multi-agent entity screening** — screens individuals and companies against sanctions lists, PEP databases, adverse media, and corporate registries. Produces AI risk scoring with a full reasoning chain. Routes high-risk cases to a HITL review queue. Logs every decision in an append-only audit trail.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Status](https://img.shields.io/badge/Status-Production--Ready%20Demo-brightgreen) ![Claude](https://img.shields.io/badge/Powered%20by-Claude%20AI-orange)

---

## Executive Summary

KYC compliance is one of the most expensive, slowest, and most error-prone processes in financial services — not because the risk judgment is hard, but because the data gathering before it is manual, fragmented, and exhausting.

A compliance analyst screening a single customer today must manually check 6–8 separate systems: OFAC, UN, HM Treasury, EU sanctions lists, PEP databases, adverse media sources, corporate registries, and FATF country risk ratings. That research — largely copy-paste and tab-switching — takes 45 minutes. The actual risk judgment takes 5. At a tier-1 bank, this costs **£30–50 million per year** and stretches corporate client onboarding to **30–120 days**.

### The Pain Points This Tool Solves

**1. The manual research trap.** Analysts spend 80% of their time aggregating data, not assessing risk. This tool automates all of it — sanctions screening, PEP checks, adverse media, company registry lookups, and country risk — in under 60 seconds per entity.

**2. Analyst fatigue and decision inconsistency.** Reviewing hundreds of cases a day degrades decision quality and creates regulatory audit risk. This tool produces the same risk rating for the same entity profile every time, regardless of case volume.

**3. The false positive flood.** Automated name-screening tools generate 60–70% false positive rates. Analysts drown in alerts for innocent matches. This tool provides confidence scores and specific reasoning, enabling faster, better-informed clearance decisions.

**4. Audit gaps.** Manual processes leave inconsistent documentation. This tool creates an append-only audit trail — every decision recorded with a numbered reasoning chain, before any analyst sees it — that meets POCA 2002 and FCA SYSC 6.3 requirements.

### Business Value in Financial Services

| Metric | Impact |
|--------|--------|
| Screening time per entity | 45 minutes → under 60 seconds |
| Analyst capacity | 5–10× more cases with same headcount |
| KYC operations cost reduction | 30–40% at tier-1 bank scale (£10–20M+/year) |
| Audit trail quality | Full reasoning chain, immutable, regulator-ready |
| False positive clearance | Faster with AI-provided disambiguation context |
| Regulatory risk | Reduced through consistent, documented decisions |

The tool does not replace compliance analysts. It eliminates the data gathering so analysts focus exclusively on judgment — the 20% of KYC work that actually requires a human.

---

## The Problem

KYC onboarding at a tier-1 bank costs £30–50M per year. Corporate client onboarding takes 30–120 days. 80% of the work is manual data aggregation  an analyst checking 6–8 systems for each entity: OFAC, UN sanctions, HMT, EU sanctions, PEP databases, adverse media, Companies House, and FATF country risk.

The judgment call  is this entity a material risk?  takes 5 minutes. The data collection takes 45.

Worldcheck aggregates this data into a single screening API used by 40,000+ financial institutions. KYC operations at major banks run thousands of entity checks daily. The enrichment is a solved data problem. The risk assessment still requires human judgment but it doesn't require humans to do the data work first.

---

## What It Does

A two-agent pipeline that screens an entity and produces a documented risk decision in under 60 seconds:

```
                   ┌──────────────────────────────────────────────────┐
                   │          KYC/AML INTELLIGENCE PIPELINE           │
                   └──────────────────────────────────────────────────┘

   Entity Input              Agent 1                      Agent 2
  (name, type,           Enrichment Agent            Risk Assessment Agent
   country, purpose)

  ┌───────────┐    ──►   ┌──────────────────┐   ──►  ┌──────────────────────┐
  │ Name      │          │ Tool use loop:   │         │ Risk score 0-100     │
  │ Type      │          │ • Sanctions scan │         │ LOW/MEDIUM/HIGH/CRIT │
  │ Country   │          │   (OFAC/UN/HMT)  │         │ APPROVE/EDD/ESCALATE │
  │ Purpose   │          │ • PEP check      │         │   /REJECT            │
  └───────────┘          │ • Adverse media  │         │ Confidence score     │
                         │ • Company reg.   │         │ Reasoning chain      │
                         │ • Country risk   │         │ Key red flags        │
                         └──────────────────┘         │ Mitigating factors   │
                                                       └──────────────────────┘
                                                                │
                                          ┌─────────────────────┤
                                          │                     │
                                   [LOW risk,            [HIGH/CRITICAL/
                                    high conf]            REJECT/ESCALATE/
                                          │               low confidence]
                                          ▼                     ▼
                                    Auto-decision          HITL Review Queue
                                    Audit logged          Analyst reviews
                                                          Audit logged
```

---

## Features

- **Enrichment Agent** — agentic tool-use loop that decides which sources to query based on entity type and what it finds: sanctions lists (OFAC/UN/HMT/EU), PEP databases (tiered 1–3), adverse media, company registry (Companies House / international), geographic risk (FATF/CPI)
- **Risk Assessment Agent** — structured decision at low temperature: risk score, rating, recommended action, confidence, numbered reasoning chain, red flags, mitigating factors, EDD requirements
- **HITL routing** — HIGH/CRITICAL risk, REJECT decisions, ESCALATE decisions, and confidence below 0.80 all route to human review. Conservative by design: asymmetric cost of sanctions false negatives
- **Audit trail** — append-only SQLite log: AI decision logged before analyst sees it (prevents post-hoc rationalisation), analyst review logged against same entry
- **Streamlit UI** — 5 tabs: screen entity, sample cases, HITL review queue, audit trail, PM guide
- **10 sample entities** — covering clean individuals, direct sanctions hits, PEP tier 2, low-risk PEP, BVI shell companies, FCA-investigated firms, common name collisions, sanctions-adjacent companies, legitimate high-risk jurisdiction businesses, and clean SMEs
- **PM Guide** — `docs/pm-guide-ai-in-kyc.md`: where AI adds value in KYC, where humans must stay in the loop, HITL design principles, production deployment checklist

---

## Quick Start

```bash
git clone https://github.com/basavarajshepur-lab/kyc-aml-intelligence-agent
cd kyc-aml-intelligence-agent
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY
streamlit run app.py
```

**CLI — screen a single entity:**
```bash
python run_kyc.py --sample --id KYC_002
```

**CLI — batch process all sample entities:**
```bash
python run_kyc.py --sample --batch
```

---

## Sample Output

```
KYC SCREENING: Viktor Petrov (INDIVIDUAL)
[1/3] Entity enrichment (sanctions · PEP · adverse media · registry)...
      Sanctions hits: 1
      PEP: No
      Adverse media: 0 item(s)
[2/3] Risk assessment...
      Decision: REJECT
      Risk: CRITICAL (94/100)
      Confidence: 97%
      HITL required: True
[3/3] Logging to audit trail...
      Audit entry: #2

✗  REJECT — CRITICAL risk (94/100)
   Red flag: EXACT match on OFAC SDN List under RUSSIA program — EO 14024 designation
   Red flag: Russian national from FATF-suspended jurisdiction (CRITICAL geographic risk)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KYC SCREENING: Margaret Collins (INDIVIDUAL)
[1/3] Entity enrichment...
      Sanctions hits: 0
      PEP: Yes — Elected Local Councillor, Surrey County Council (2015-2022)
      Adverse media: 0 item(s)
[2/3] Risk assessment...
      Decision: APPROVE
      Risk: LOW (12/100)
      Confidence: 91%
      HITL required: False

✓  APPROVE — LOW risk (12/100)
```

---

## The 10 Sample Entities

| Case | Entity | Type | Expected Decision |
|---|---|---|---|
| KYC_001 | James Thornton | Individual | APPROVE — clean UK solicitor |
| KYC_002 | Viktor Petrov | Individual | REJECT — direct OFAC SDN match |
| KYC_003 | Ahmed Al-Rashidi | Individual | EDD — PEP tier 2, Nigeria |
| KYC_004 | Margaret Collins | Individual | APPROVE — low-risk retired PEP |
| KYC_005 | Sunrise Holdings Ltd | Company | ESCALATE — BVI, opaque ownership, fuzzy sanctions match |
| KYC_006 | FastTrack Finance Ltd | Company | ESCALATE — FCA investigation, serial director |
| KYC_007 | Wei Zhang | Individual | APPROVE after HITL — name collision, needs disambiguation |
| KYC_008 | Atlas Trading International | Company | REJECT/ESCALATE — HMT sanctions match, adverse media |
| KYC_009 | Caspian Energy Partners | Company | EDD — legitimate but Caspian region risk |
| KYC_010 | Sarah Bennett | Individual | APPROVE — clean NHS nurse |

---

## HITL Design — The Decisions That Matter

**Conservative routing threshold:** Confidence below 0.80 triggers human review — lower than the 0.85 threshold used in transaction monitoring. KYC decisions are more consequential: a missed sanctions hit carries regulatory fines and reputational damage; an incorrect rejection creates ombudsman exposure.

**AI decision logged first:** The AI recommendation is recorded in the audit trail before the analyst sees it. This is not a UI choice — it's an audit integrity requirement. If the analyst sees the recommendation first, their "independent" review is influenced. Logging first creates an honest record of what the AI decided and what the analyst chose to do about it.

**Override always available:** No AI decision is final without human review in HITL cases. The analyst can agree with the AI or override to any other decision. Override requires a documented note.

---

## Production Deployment

This is a production-ready **demo**. For deployment at a regulated institution:

1. Replace mock enrichment tools with licensed feeds: Worldcheck (LSEG), ComplyAdvantage, Dow Jones Risk & Compliance
2. Integrate Companies House API (free, UK Gov), OpenCorporates for international registries
3. Add biometric / document verification for name collision disambiguation (Onfido, Jumio)
4. Connect to case management system (Appian, Pegasystems) for EDD workflow
5. GDPR / data residency compliance for PII processed by AI
6. FCA SYSC 6.3 notification for material change to screening process
7. Audit trail retention aligned to POCA 2002 (minimum 5 years, recommend 7)
8. False positive rate benchmarking against historical manual screening before go-live

See `docs/pm-guide-ai-in-kyc.md` for the full "where AI adds value vs. where humans must stay" framework.

---

## Competitive Advantages

### 1. Purpose-Built for Financial Services Compliance
Most AI tools are general-purpose. This tool is built specifically for KYC/AML workflows, with the regulatory framework baked in — PEP tiers, FATF risk ratings, HITL thresholds aligned to FCA guidance. A generic AI assistant cannot replicate this domain-specific design.

### 2. Reasoning Chain — Not a Black Box
Every risk score comes with a numbered explanation of *why*. This is not just useful for analysts — it is a regulatory requirement. Regulators expect to see how decisions were made, not just what they were. Tools that produce a score without explanation fail this requirement.

### 3. Structured Output — Machine-Readable, Not Prose
The risk assessment produces typed, structured data — not a paragraph of text. This makes it directly connectable to downstream systems: case management platforms (Appian, Pegasystems), reporting tools, and regulatory submission systems. You pipe structured data, you do not copy AI prose.

### 4. Conservative by Design
The tool errs on the side of human review. Confidence below 80% triggers analyst review — not auto-approval. This is the right risk posture for a compliance tool. Regulatory penalties for a missed sanctions hit are orders of magnitude more severe than the cost of routing one extra case to a human reviewer.

### 5. Audit Integrity Built In
The append-only audit trail with AI decision logged *before* the analyst sees it is not a feature added as an afterthought — it is a core design principle. This prevents post-hoc rationalisation, a known failure mode where analysts unconsciously align their "independent" review with what the AI already told them.

### 6. Production-Ready Architecture
Built on the same patterns used in production at LSEG — where the Worldcheck screening platform serves 40,000+ financial institutions globally. The enrichment agent design mirrors the VEDaaS entity verification pipeline. This is not an academic prototype.

### 7. Transparent Human-AI Division of Labour
The tool is explicit about what AI does and what humans must do. AI handles the research. Humans handle judgment on consequential decisions. This clarity is what regulators expect — and what too many AI compliance tools obscure.

---

## Future Growth Opportunities

### Near-Term: Connect to Live Data Feeds
The current version uses realistic mock data. Connecting to licensed commercial feeds unlocks full production value:
- **Worldcheck (LSEG)** — gold-standard sanctions, PEP, and adverse media feed used by 40,000+ institutions
- **ComplyAdvantage** — real-time adverse media and sanctions monitoring
- **Companies House API** (free, UK Government) — live UK corporate registry
- **OpenCorporates** — international company data across 140+ jurisdictions
- **Dow Jones Risk & Compliance** — additional PEP and adverse media coverage

### Near-Term: Ongoing Monitoring
KYC is not a one-time check. The tool architecture supports building an ongoing monitoring layer that re-screens existing customers when trigger events occur — a new sanctions designation, a PEP becoming active, a regulatory action — without requiring manual re-initiation.

### Medium-Term: EDD Workflow Automation
For customers requiring Enhanced Due Diligence, the tool can draft EDD questionnaires, structure source-of-wealth analysis, and surface specific documentation requirements — reducing EDD completion time from days to hours.

### Medium-Term: SAR Drafting Support
When a case warrants a Suspicious Activity Report, the AI has already assembled the evidence and can draft the SAR narrative. The MLRO reviews and submits. SAR drafting time drops from hours to minutes.

### Medium-Term: Cross-Institution Pattern Detection
Individual institutions see only their own customer data. A sanctions evasion network may span multiple institutions, staying below each one's detection threshold. With appropriate privacy-preserving architecture, the tool could contribute to and benefit from cross-institution pattern detection.

### Longer-Term: Biometric Integration for Name Disambiguation
The hardest KYC problem is name disambiguation — distinguishing your "Wei Zhang" from the sanctioned one. Integrating document verification providers (Onfido, Jumio, iProov) would allow biometric confirmation that resolves name collisions programmatically.

### Longer-Term: Regulatory Reporting Automation
The structured audit trail makes periodic regulatory returns automatable. The data is already typed and queryable — connecting it to regulatory reporting templates eliminates manual data extraction for submissions.

### Longer-Term: Multi-Jurisdictional Expansion
The tool is currently calibrated for UK/EU frameworks (FCA, JMLSG, HMT). The same architecture applies to US (FinCEN, OFAC), Singapore (MAS), UAE (CBUAE), and other major financial centres — each requiring jurisdiction-specific sanctions lists, PEP definitions, and reporting requirements.

---

## Background

Built by [Basavaraj Shepur](https://linkedin.com/in/basavarajshepur) — Senior AI Product Manager with 19 years in financial services. This system implements KYC enrichment patterns (multi-list screening, fuzzy matching, PEP tiers) and responsible AI controls (confidence thresholds, HITL gates, audit chains) drawn from production financial services deployments.

---

## License

MIT
