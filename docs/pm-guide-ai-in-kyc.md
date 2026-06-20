# PM Guide: AI in KYC — Where It Adds Value and Where Humans Must Stay

*By Basavaraj Shepur — drawing on LSEG Worldcheck/VEDaaS integration and JPMorgan KYC work*

---

## The KYC Problem in Numbers

KYC (Know Your Customer) is one of the most labour-intensive processes in financial services:

- **£30–50M per year** — typical tier-1 bank annual KYC operations cost
- **30–120 days** — average onboarding time for corporate clients (KPMG 2023)
- **80% manual** — share of KYC review work still done by human analysts
- **60–70% false positive rate** — typical rate on automated name screening (similar problem to AML alerts)

The core process hasn't changed in 20 years:
1. Customer submits name and identifiers
2. Compliance team manually checks sanctions lists (OFAC, UN, HMT, EU)
3. Checks PEP databases
4. Searches adverse media
5. Verifies company registry details
6. Makes a risk-based decision
7. Logs the rationale

Steps 1–6 are largely pattern matching and data aggregation. Step 7 is human judgment.

---

## Where AI Adds Value in KYC

### 1. Enrichment — the mechanical research

The biggest time cost in KYC is aggregating data from multiple sources. An analyst screening a single entity manually checks 4–8 systems:
- OFAC SDN List
- UN Consolidated List
- HM Treasury Asset Freeze
- EU Consolidated Sanctions List
- One or more PEP databases
- News/media databases (Factiva, LexisNexis)
- Companies House / international registries
- FATF country risk assessments

An AI agent with tool use can run all of these in parallel and return structured enrichment data in under 30 seconds. Not a summarisation of a document — a structured data call per source with parsed, typed results.

**The Worldcheck pattern:** At LSEG, Worldcheck aggregated sanctions, PEP, and adverse media data into a single screening API. VEDaaS added entity verification. The pattern in this system follows the same design — each enrichment tool represents a data source, and the agent decides which tools to call based on entity type and what it finds.

### 2. Risk scoring — structured reasoning at low temperature

Once enrichment is complete, the AI can reason over the combined signals and produce a structured risk score. The key design choices:

- **Low temperature (0.1):** Same entity data → same risk rating. Inconsistency in KYC decisions is a regulatory audit risk.
- **Structured output via tool use:** Every field is typed and machine-parseable. The risk score, rating, recommended action, confidence, reasoning chain, and red flags are all structured data, not prose.
- **Conservative defaults:** When uncertain (confidence < 0.80), the system escalates rather than auto-approving. The cost of a false negative on sanctions screening is regulatory fines and reputational damage. The cost of a false positive is onboarding delay — asymmetric risk.

### 3. Risk-ranked queue — triage, not replacement

AI doesn't replace the analyst. It changes what the analyst spends time on.

Without AI: analyst reviews every case sequentially, same time regardless of risk.

With AI: analyst reviews HIGH/CRITICAL cases, REJECT decisions, and cases with ambiguous signals. LOW-risk cases with high confidence can auto-approve. The AI has done the research; the analyst reviews the conclusion.

---

## Where Humans Must Stay In the Loop

### 1. REJECT decisions — always

Rejecting a customer has legal and reputational consequences. Under UK law, if a rejection is based on a false sanctions match, the bank can face a complaint to the Financial Ombudsman. In some jurisdictions, incorrect rejection of a sanctioned entity can itself constitute a crime (tipping off).

Human review before any rejection is non-negotiable.

### 2. PEP onboarding — always enhanced due diligence

FATF Recommendation 12 and FCA SYSC 6.3.9 require enhanced due diligence for PEP relationships. This means:
- Senior management approval before onboarding
- Source of wealth verification
- Enhanced ongoing monitoring

The AI can identify PEP status and draft the EDD requirements. The senior management approval is a human control that cannot be automated.

### 3. Fuzzy name matches — human disambiguation

"Wei Zhang" is one of the most common names in the world. A fuzzy match on a sanctions list for "Wei Zhang" could refer to any of millions of individuals. The AI can flag the match and present the evidence; only a human can make the determination that this specific Wei Zhang is or is not the sanctioned individual.

This is the fundamental limit of entity resolution with name-only data. Biometrics, document verification, and in-person checks are the real solutions — AI can present the ambiguity clearly, not resolve it.

### 4. Adverse media — materiality assessment

A company that appeared in an adverse media article from 2015 about an industry-wide mis-selling scandal is different from a company under active FCA investigation. Both generate adverse media hits. Only a human can assess materiality in context.

The AI can summarise the media hit and categorise it (financial_crime / fraud / corruption / sanctions_breach). The analyst makes the call on whether it is material to the relationship.

---

## The HITL Design Principle

This system routes to human review when:

| Condition | Why |
|---|---|
| REJECT decision | Legal and regulatory accountability |
| ESCALATE decision | Requires MLRO or senior compliance sign-off |
| HIGH / CRITICAL risk rating | Risk level warrants human judgment |
| Confidence < 0.80 | Uncertain AI assessments must not auto-approve |

The routing is conservative by design. In KYC, the cost asymmetry favours false positives (onboarding delays) over false negatives (sanctions violations, reputational damage).

**The key audit principle:** The AI decision is logged before the analyst sees it. This creates an immutable record of what the AI recommended and prevents post-hoc rationalisation. The analyst is reviewing the AI, not being guided by it.

---

## What This Replaces vs What It Doesn't

| KYC Activity | AI Role | Human Role |
|---|---|---|
| Sanctions screening | Automated tool call, structured result | Review fuzzy matches, clear false positives |
| PEP check | Automated tool call, tiered result | EDD process, senior management approval |
| Adverse media | Automated aggregation, categorisation | Materiality assessment |
| Corporate registry | Automated lookup, UBO extraction | Interpretation of complex structures |
| Risk decision | Scoring, recommendation, reasoning chain | Final decision on HIGH/CRITICAL cases |
| SAR / MLRO referral | Drafts escalation note | MLRO reviews, makes filing decision |
| Ongoing monitoring | Can flag trigger events | Periodic review |

The 80% manual share of KYC work that is data aggregation and pattern matching becomes AI-driven. The 20% that requires judgment — materiality assessment, PEP EDD approval, sanction false positive disambiguation — stays with humans.

---

## Production Deployment Checklist

Before deploying AI KYC at a regulated institution:

- [ ] Legal review of AI use in customer screening decisions
- [ ] MLRO sign-off on HITL thresholds and escalation policy
- [ ] Replace mock enrichment tools with licensed data feeds (Worldcheck, ComplyAdvantage, Companies House API)
- [ ] Data residency compliance — customer PII processed by AI must meet GDPR/local requirements
- [ ] False positive rate benchmarking before production (compare AI vs. manual screening on historical cases)
- [ ] Analyst training on AI-assisted workflow and override process
- [ ] Audit trail retention aligned to POCA 2002 / local AML legislation
- [ ] FCA/PRA notification if material change to screening process (SYSC 6.3)
- [ ] Biometric / document verification integration for disambiguation of name collisions
