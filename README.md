# KYC/AML Intelligence Agent

**Multi-agent entity screening** — screens individuals and companies against sanctions lists, PEP databases, adverse media, and corporate registries. Produces AI risk scoring with a full reasoning chain. Routes high-risk cases to a HITL review queue. Logs every decision in an append-only audit trail.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Status](https://img.shields.io/badge/Status-Production--Ready%20Demo-brightgreen) ![Claude](https://img.shields.io/badge/Powered%20by-Claude%20AI-orange)

---

## The Problem

KYC onboarding at a tier-1 bank costs £30–50M per year. Corporate client onboarding takes 30–120 days. 80% of the work is manual data aggregation — an analyst checking 6–8 systems for each entity: OFAC, UN sanctions, HMT, EU sanctions, PEP databases, adverse media, Companies House, and FATF country risk.

The judgment call — is this entity a material risk? — takes 5 minutes. The data collection takes 45.

Worldcheck aggregates this data into a single screening API used by 40,000+ financial institutions. KYC operations at major banks run thousands of entity checks daily. The enrichment is a solved data problem. The risk assessment still requires human judgment — but it doesn't require humans to do the data work first.

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

## Background

Built by [Basavaraj Shepur](https://linkedin.com/in/basavarajshepur) — Senior AI Product Manager with 19 years in financial services. This system implements KYC enrichment patterns (multi-list screening, fuzzy matching, PEP tiers) and responsible AI controls (confidence thresholds, HITL gates, audit chains) drawn from production financial services deployments.

---

## License

MIT
