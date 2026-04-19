# Regulatory Mapping

Maps CAS detection and prevention capabilities to specific requirements in major AI regulatory instruments. Mappings are claim-by-claim, not holistic — each CAS feature is paired with the specific regulatory clause it addresses, with no claim of comprehensive coverage.

**Status:** Scaffold. Detailed mapping is populated as verified-incident evidence accumulates that supports specific claims.

---

## Instruments in Scope

- **EU AI Act** (Regulation (EU) 2024/1689) — high-risk AI systems (Annex III), general-purpose AI model obligations.
- **NIST AI Risk Management Framework** (AI RMF 1.0) — Govern, Map, Measure, Manage functions.
- **ISO/IEC 42001:2023** — AI management systems.
- **UK AI Safety Institute** evaluation methodology.
- **Colorado AI Act** (SB24-205) and emerging US state instruments.
- **OECD AI Principles** and the UNESCO Recommendation on the Ethics of AI.

---

## Mapping Approach

For each instrument, we identify clauses that require some form of:
- Risk identification or classification
- Bias and fairness assessment
- Transparency and explainability
- Human oversight
- Robustness and adversarial testing
- Incident reporting and post-market monitoring
- Conformity assessment

Then, per clause, we state:
1. **Requirement** — what the clause asks for, with citation to the specific article/section.
2. **CAS capability** — which CAS module addresses this (if any).
3. **Coverage level** — full / partial / indirect / none. No rounding up.
4. **Evidence** — which verified incidents in the main database demonstrate this capability applied to real failures.

A "partial" coverage claim is not weaker-than-full in the sense that matters; it is more honest. Regulators do not reward overclaiming.

---

## EU AI Act

*(Mapping populated after verified incidents accumulate that illustrate EU-AI-Act-relevant failures.)*

### Article 9 — Risk Management System (high-risk AI)
- Requirement: identification, analysis, and evaluation of risks that may emerge.
- CAS capability: *pending mapping.*

### Article 10 — Data and Data Governance
- Requirement: training/validation/test data must meet specified quality criteria.
- CAS capability: CAS operates post-training; coverage here is **none**. Documented explicitly.

### Article 13 — Transparency and Provision of Information
- Requirement: system must be designed to enable users to interpret output.
- CAS capability: *pending mapping.*

### Article 14 — Human Oversight
- Requirement: design must enable effective human oversight.
- CAS capability: *pending mapping.*

### Article 15 — Accuracy, Robustness, Cybersecurity
- Requirement: systems must achieve appropriate level of accuracy and robustness.
- CAS capability: *pending mapping.*

---

## NIST AI RMF 1.0

*(Mapping populated when ≥10 verified incidents support each function.)*

### Govern — *pending.*
### Map — *pending.*
### Measure — *pending.*
### Manage — *pending.*

---

## ISO/IEC 42001

*(Pending.)*

---

## UK AI Safety Institute Evaluation Methodology

*(Pending.)*

---

## US State Instruments

### Colorado AI Act (SB24-205)
*Pending.*

### Other state instruments
*Pending.*

---

## Honest Limitations

Regulations are drafted around questions CAS does not claim to answer:
- Training-data provenance and copyright.
- IP ownership of generated output.
- Emissions and compute-cost reporting.
- Cross-border data flow compliance.

For those questions, CAS integrates with, but does not replace, conventional compliance tooling.
