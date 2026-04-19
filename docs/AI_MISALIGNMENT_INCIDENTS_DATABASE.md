# AI Misalignment Incident Database
## A CAS Structural Analysis of Documented Failures

**Status:** Living reference document. Under active verified-source curation.
**Framework:** Cognitive Architecture System (CAS) v7.4 — Corrected Edition
**Maintained by:** Noetic Compass research team
**First commit:** 2026-04-19
**Current verified-incident count:** 0 (scaffold only)

---

## Prologue — Why This Document Exists

Most AI "failure" catalogs treat failure as an output problem: the model said something false, refused something it should have helped with, said yes when it should have said no, leaked data it should have protected, produced content that discriminated against a class of users. These failures are real, and output-level benchmarks — truthfulness, refusal consistency, bias audits, safety classifier pass rates — have done real work documenting them.

But output-level cataloging misses what produced the output. An AI system that fabricates a legal citation and an AI system that hallucinates a medical dosage can, from the outside, look like "two instances of hallucination." Inside the system, they can be structurally very different failures — one a failure of critical evaluation (CO-3) under confident projective assertion (CO-6), the other a failure of domain descent where operational fluency (O) runs without principled (P) grounding. Treating them as the same kind of error means fixing one does nothing for the other.

This database is organized around the hypothesis that AI misalignment events have *structural signatures*, and that those signatures are more diagnostic than the surface-level behavior. The Cognitive Architecture System (CAS) provides a formal taxonomy for those signatures: 10 cognitive operators, 4 processing domains under a strict precedence (P ≻ C ≻ E ≻ O), 7 core drives with three involution pairs, 22 capability pathways organized into the Recursive Prerequisite Model (A0 → Dn → Wn → Pn), and 7 inversion axes that detect the specific ways those structures can fail. The database documents real, primary-source-verified AI failures and then, *separately and visibly*, interprets each one through this taxonomy.

The epistemic distinction between the two layers is load-bearing. The documented facts of an incident — what happened, who was harmed, what the investigating body concluded — come from primary sources that we cite verbatim. The CAS interpretation of those facts is our analytical claim, and it is labeled as such. A reader who rejects CAS as a framework can still use this database as a verified incident catalog. A reader who accepts CAS can use it as a diagnostic map of where structural monitoring would have raised flags that output-level monitoring did not.

**What this database is not.** It is not a marketing document. It is not a list of reasons to buy the Noetic Compass platform. It is not an exhaustive enumeration of every AI failure in the public record — such a catalog would be both impossible and untrustworthy, because the rate of unreported incidents exceeds the rate of reported ones. It is not a proof that CAS would have prevented every case; prevention is a stronger claim than detection, and we mark the two separately.

**What this database is.** A growing, primary-source-anchored set of AI failures each read through the CAS structural lens, intended to support the Noetic Compass peer-review paper, the book's appendices, and regulator/stakeholder briefings where specific rigorous examples are more useful than aggregate statistics.

---

## Methodology

### Inclusion criteria

An incident is included if and only if all of the following are true:

1. **Primary-source documentation exists.** This means at least one of: (a) a court filing with a docket number; (b) a government or regulatory report with a public document ID; (c) a peer-reviewed academic paper with a DOI; (d) an official incident disclosure from the operating entity; (e) reporting from an established news organization (Reuters, AP, NYT, WSJ, BBC, Bloomberg, MIT Technology Review, ProPublica, STAT) that names sources and is datelined.
2. **Two independent sources minimum.** "Independent" means not downstream of the same originating report. Two news outlets both republishing a single press release do not count as two independent sources.
3. **Sources fetched and read in the current verification session.** Every source cited in an incident entry must have been accessed via `WebFetch` during the session that added or updated the entry. Citations from model memory are prohibited.
4. **Direct attribution.** Every factual claim in the "What Happened" and "Documented Harm" sections must be traceable to a specific fetched source. Claims that cannot be traced are removed, not softened.

### Exclusion criteria

An incident is excluded if any of the following:

- Primary sourcing cannot be located after reasonable effort.
- Only rumor, social media posts, or unnamed leaks are available.
- The incident is genuinely disputed by the originating entity *and* no authoritative adjudication exists.
- Verification in a session produces fewer than two independent sources after three fetch attempts.

Excluded candidates are logged in `docs/data/rejected_candidates.md` with the reason, so future sessions can revisit if new sources emerge.

### Epistemic layers

Each incident entry has two clearly separated layers:

- **Verified facts.** Incident date, disclosure date, entity, system, harms, legal/regulatory findings — drawn only from fetched primary sources with direct citations.
- **CAS analysis.** Structural interpretation of the verified facts using the CAS framework. Labeled as analysis, not fact. Uses hedged language where interpretation is uncertain ("the documented behavior is consistent with..." rather than "X occurred").

### Citation format

```
[N] Author(s). "Title." Publication, date.
    URL: https://exact-url-fetched
    Accessed: YYYY-MM-DD
    Documents: <specific facts this source supports>
```

### Quotation rules

Direct quotes use quotation marks and must appear verbatim in the fetched source. If a quote is paraphrased or reconstructed, it does not get quotation marks. A quote that cannot be traced word-for-word to a fetched source is removed.

### Dates

If a source gives only a month, the entry gives only the month. If a source gives only a year, the entry gives only the year. Approximating a specific date when the source does not provide one is prohibited — it is a credibility wound disguised as precision.

---

## CAS Failure-Class Taxonomy

Each incident is assigned a **primary** failure class. Many incidents exhibit features of more than one class; secondary classes are listed in the `secondary_categories` field of the JSON record but the primary class is the one whose structural signature most closely matches the verified facts.

See `docs/INCIDENT_CATEGORIES.md` for the full taxonomy with framework citations. The twelve classes:

1. **Domain Descent Violations** — P ≻ C ≻ E ≻ O precedence broken; Operational output without Principled grounding.
2. **Operator Inversions** — involution pair imbalance (CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9).
3. **Stealth Inversions** — harmful output wrapped in surface safety language; stealth-resistance axis failure.
4. **Prerequisite Chain Failures** — RPM break; Power emitted without Wisdom, or Desire without A0 grounding.
5. **Cognitive Fractal Amplification** — recursive reasoning without convergence to a fixed point.
6. **High-Lacunarity Blind Spots** — strong activation in one operator/domain, catastrophic void in a structurally adjacent one.
7. **Adversarial Susceptibility** — architecture flips under crafted prompts (jailbreaks, prompt injection).
8. **Sycophancy and Self-Grading Failures** — optimization for apparent approval over truth; self-scoring bias.
9. **Hallucination and Confabulation** — CO-6 projective assertion without CO-3 critical evaluation.
10. **Drive Corruption** — motivational architecture (F1–F7) subverted or inverted.
11. **Cross-Domain Contamination** — Principled constraints bypassed via Operational framing or vice versa.
12. **Compound Inversions (P-axis failures)** — multiple simultaneous structural failures with non-linear severity amplification.

---

## Verified Incidents

*This section is populated through verified-source research sessions. Each entry carries its verification date and the URLs fetched during that session. Entries are numbered in the order verified, not by incident severity or date.*

<!-- INCIDENTS_INSERT_POINT — do not remove -->

*(No verified incidents yet — scaffold phase.)*

---

## Summary Sections

The following analytical sections are populated after a sufficient number of verified incidents exist to support them. They are deliberately left as stubs until the evidence base can carry the claims.

### A. Statistical Overview

*Populated when N ≥ 25 verified incidents.*
Will include: incidents by category, by year, by sector, by severity; primary failure modes ranked by frequency.

### B. Gap Analysis — CAS vs Existing Frameworks

*Populated when N ≥ 30 verified incidents.*
Will compare coverage of the verified incident set under OWASP AI Top 10, NIST AI RMF, the EU AI Act, TAB, and ETHICS — showing which structural failures none of those frameworks flag that CAS does flag. Claims will be backed by incident-level mapping, not narrative assertion.

### C. The Prevention vs Detection Case

*Populated when N ≥ 30 verified incidents.*
Separates incidents where CAS would **detect** the structural signature pre-deployment from incidents where CAS would only **flag at runtime**. Prevention is the stronger claim and will not be overstated.

### D. The Economic Case

*Populated when N ≥ 40 verified incidents with documented settlement / fine / harm figures.*
Cumulative documented cost of verified incidents with dollar/harm figures traceable to primary sources. Aggregates only — no extrapolation to "total cost of AI misalignment."

### E. Regulatory Alignment

*Populated when N ≥ 20 verified incidents covering regulatory actions.*
Maps CAS detection capabilities to specific requirements in the EU AI Act (High-Risk AI Systems, Annex III), NIST AI RMF functions (Govern/Map/Measure/Manage), ISO/IEC 42001, UK AISI evaluation methodology, Colorado AI Act, and equivalent regulatory instruments. Mappings are claim-by-claim, not holistic.

---

## Supporting Files

- `docs/INCIDENT_CATEGORIES.md` — detailed taxonomy of the 12 CAS failure classes.
- `docs/CAS_PREVENTION_CLAIMS.md` — conservative subset: incidents where CAS prevention (not just detection) is defensible.
- `docs/CITATION_INDEX.md` — master bibliography across the database.
- `docs/REGULATORY_MAPPING.md` — CAS capabilities mapped to regulatory instruments.
- `docs/data/incidents.json` — machine-readable incident records.
- `docs/data/incident_analytics.json` — summary statistics, regenerated as new incidents are added.
- `docs/data/rejected_candidates.md` — incidents investigated and excluded, with reason.

## Session Log

Verified-source research sessions are logged at the bottom of this file under `## Session Log`. Each session entry records: date, incidents added (with IDs), incidents investigated but rejected for insufficient sourcing, URLs fetched, and any conflicts encountered between sources.

<!-- SESSION_LOG_INSERT_POINT — do not remove -->

*(No sessions yet.)*
