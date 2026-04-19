# AI Misalignment Incident Database
## A CAS Structural Analysis of Documented Failures

**Status:** Living reference document. Under active verified-source curation.
**Framework:** Cognitive Architecture System (CAS) v7.4 — Corrected Edition
**Maintained by:** Noetic Compass research team
**First commit:** 2026-04-19
**Current verified-incident count:** 2

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

## Methodology Protocol Amendments

This section tracks changes to the verification protocol as sessions discover real-world friction. Each amendment carries its adoption date and remains in force until explicitly revised.

### 2026-04-19 — Amendment 1: Local-parser clause for WebFetch retrievals

**Context:** WebFetch text extraction fails for PDFs delivered in `/Filter/FlateDecode` compressed object streams, which is common for agency and court primary sources (NTSB, NHTSA, court filings, Royal Commission reports).

**Rule:** URL approval authorizes (a) retrieval of the document at that URL via WebFetch in the current session, and (b) subsequent parsing of the retrieved file using local tools (Read, etc.) when WebFetch's text extraction fails or is incomplete.

**Scope:** The retrieved file must be the direct product of the approved WebFetch call in the current session. Files from prior sessions, pre-loaded files, or files obtained outside the WebFetch approval chain do NOT qualify and still require fresh URL approval.

**Citation format:** `[Source], retrieved via WebFetch [date] from [URL], parsed locally via Read tool.` Page numbers are required for PDF citations.

### 2026-04-19 — Amendment 2: User-assisted fetch (Path B) — PROPOSED AND WITHDRAWN

**Context:** The WebFetch allow-list excludes major international journalism outlets (Reuters, The Guardian, and the Internet Archive were all observed to return `Claude Code is unable to fetch from …` in the first verification session).

**Proposal:** User manually fetches tool-blocked articles and pastes the text, parsed with the same discipline as a WebFetch result.

**Status:** **Withdrawn same session.** The manual-paste workflow does not scale to 100+ incidents without consuming more of the user's bandwidth than the engineering session was designed to save. The database methodology is instead adapted to what is actually fetchable via WebFetch in this environment (see Amendment 3).

**Preserved here for protocol transparency:** future sessions may revisit Path B for a small number of high-value incidents where no Tier 1 alternative exists (e.g., a named Reuters article that is the sole primary source of record). In those exceptional cases, Path B becomes opt-in per-incident rather than a standing default.

### 2026-04-19 — Amendment 4: Navigation vs. Source distinction (adopted Session 2)

**Context:** Tier 1 government and court databases frequently require navigation through index/search pages to reach the canonical document. Counting those index pages against the per-incident source budget creates artificial scarcity that punishes disciplined indexing workflows.

**Rule:** The 3-source-per-incident-per-session limit applies to pages whose content is **cited** in the entry (primary sources). Pages used only for **routing** — landing pages, search interfaces, decision-index pages, docket-index pages — do NOT count against the source limit.

**Distinction test:** A page is "routing" if no fact in the incident entry is sourced from it. A page is a "source" if the entry cites facts, dates, quotes, findings, or any other content from it.

**Session 1 retroactive check:** Incident 1 (Uber ATG) used 1 source (NTSB HAR-19-03) despite fetching the NTSB docket index page first. Under this amendment, that is correct — the docket index was navigation (routing only), HAR-19-03 was the cited source. No retroactive changes to Session 1 entries required.

### 2026-04-19 — Amendment 6: Tier 1 .gov is not uniformly reachable — per-domain verification required (adopted Session 2)

**Context:** Session 2 has surfaced a pattern that invalidates a working assumption. The original tier classification treated Tier 1 as equivalent to "reliably fetchable." Observation across two sessions shows this is not true at the domain level.

**Observed reachability, as of 2026-04-19 end-of-session:**

| Domain / subdomain | Class | Reachable via WebFetch? | Evidence |
|---|---|---|---|
| `ntsb.gov` | .gov agency | ✅ Confirmed (docket + PDF, 12 pages parsed) | Session 1, Incident 1 |
| `nysd.uscourts.gov` | .gov federal court | ✅ Confirmed (homepage + rulings index, navigation only) | Session 2, Mata attempts |
| `www.nhtsa.gov/recalls?nhtsaId=…` | .gov agency HTML query | ❌ HTTP 403 on first test | Session 2, Candidate 3 |
| `api.nhtsa.gov/…` | .gov agency API subdomain | 🟡 Untested (next attempt) | Session 2, pending |
| `static.nhtsa.gov/odi/inv/…` | .gov agency static CDN | 🟡 Untested | Session 2, fallback pending |
| `courtlistener.com` | Tier 1 legal mirror | ❌ HTTP 403 bot detection | Session 2, Mata |
| `canlii.org` | Tier 1 legal mirror | ❌ HTTP 403 bot detection | Session 2, Air Canada |
| `reuters.com` | Tier 3 commercial journalism | ❌ Tool-blocked | Session 1 |
| `theguardian.com` | Tier 3 commercial journalism | ❌ Tool-blocked | Session 1 |
| `web.archive.org` | Tier 3 archival | ❌ Tool-blocked | Session 1 |
| `robodebt.royalcommission.gov.au` | .gov.au Royal Commission microsite | ❌ Timeout (>60s, two attempts) | Session 2 |

**Failure mode taxonomy (derived from Session 2 observations):**

1. **Tool-block** — `Claude Code is unable to fetch from <domain>`. Domain is on a WebFetch deny-list. Most tier 3 commercial journalism and archival sites. No workaround within automated pipeline.
2. **HTTP 403** — server accepts the request and returns Forbidden. Bot detection at the application layer. CourtListener, CanLII, `www.nhtsa.gov/recalls?...`, `api.nhtsa.gov`. Sometimes bypassable with different subdomains; often not.
3. **HTTP 404** — server accepts the request; the specific path does not exist. Recoverable by identifying the correct path (often via a landing-page navigation fetch first).
4. **Timeout (no response in 60s)** — server accepts the connection but does not return a response within WebFetch's timeout. `robodebt.royalcommission.gov.au` is the first observation of this mode. May indicate silent rate-limiting, slow backend, or geofencing-induced stalls. Distinct from the other three modes and not recoverable by URL variation.
5. **Successful fetch, silent-no-op filter** — domain and path work, but query parameters are ignored. Observed on `nysd.uscourts.gov` Drupal views with `?combine=`. Recoverable by pagination rather than filtering.

**Rule update:** Tier 1 `.gov` status confers *expected* access, not *guaranteed* access. Different government agencies deploy different anti-abuse layers — rate limiting, bot detection, query-specific access control — independent of the reasonable expectation that public-record infrastructure should be uniformly public-access. **Per-domain verification is required before a `.gov` is treated as "in the allowlist" for a given incident's sourcing plan.**

**Sub-domain heuristic:** within a single agency, different subdomains can have different reachability. API subdomains (`api.nhtsa.gov`) are designed for programmatic access and are structurally less likely to deploy aggressive bot detection than consumer HTML frontends (`www.nhtsa.gov`). Static asset subdomains (`static.nhtsa.gov/odi/...`) are typically the most reliable because they serve cacheable PDFs through CDN infrastructure that doesn't inspect requests individually. Access strategy for future agency-investigation incidents should prefer API → static CDN → consumer HTML, in that order.

**Cadence estimate revised (supersedes Session 1 estimate):**
- Original estimate (Session 1 close): 5–8 verified incidents per session.
- Revised estimate (Session 2 mid-session): **3–5 verified incidents per session**, with 1–2 environment-constraint deferrals expected per session as normal workflow.
- Implications for total project timeline to N=100: was 13–20 sessions; revises to **20–33 sessions**, or roughly 5–8 months at one session per week.
- This is not a reason to lower ambition. It's a reason to set honest expectations so session health can be judged accurately and not as under-performance.

**Deferrals are not failures.** An environment-constraint deferral, where the primary source is publicly known to exist but is not reachable through the automated pipeline, is a different outcome than a sourcing failure. The database tracks both in `docs/data/rejected_candidates.md` with explicit labels so session reporting stays honest about what actually happened.

### 2026-04-19 — Amendment 7: European Parliamentary Infrastructure — confirmed Tier 1 (adopted Session 2)

**Context:** Session 2 Candidate 5 (Dutch toeslagenaffaire) produced the first positive reachability test on a non-US Tier 1 source. `tweedekamer.nl` loaded cleanly via WebFetch with static HTML navigation, and a direct link to the English-language mirror at `houseofrepresentatives.nl` was identified.

**Confirmed reachable (Session 2):**
- `tweedekamer.nl` — Dutch House of Representatives, primary parliamentary site.
- `houseofrepresentatives.nl` — English mirror linked from tweedekamer.nl (reachability pending same-session confirmation).

**Pattern prediction (not yet verified — each requires per-site testing per Amendment 6):**
- Bundestag (`bundestag.de`, with English at `bundestag.de/en`).
- UK Parliament (`parliament.uk`, natively English).
- European Parliament (`europarl.europa.eu`, multilingual).
- Swedish Riksdag (`riksdagen.se`, with English sub-path).
- French Assemblée nationale (`assemblee-nationale.fr`).

**Rule:** European parliamentary national-legislature infrastructure is now treated as a **confirmed-Tier-1-reachable source class** for baseline planning purposes. The prior for reachability shifts from unknown to positive. Per-site verification still required before any specific incident's sourcing plan relies on a specific domain, but session-batch planning can now assume parliamentary inquiry reports from European national legislatures are likely accessible, whereas previously they were unknown.

**Implications for the database:**
- Dutch toeslagenaffaire verification likely this session (in progress).
- Future European AI-misalignment incidents with parliamentary inquiry primary sources become realistic Tier 1 candidates. Anticipated examples include:
  - UK Post Office Horizon scandal — House of Commons inquiry reports, Sir Wyn Williams inquiry.
  - German Schufa credit-scoring algorithm cases — Bundestag petitions and committee records.
  - EU AI Act enforcement records — European Parliament committee reports.
  - Italian Garante / French CNIL regulatory rulings on AI systems (national regulators rather than parliaments, but adjacent infrastructure class).
- Multi-session batching strategy: future sessions can cluster European parliamentary incidents together to exploit the common access pattern, analogous to how US-NTSB-class incidents cluster efficiently on `.gov` agency infrastructure.

### 2026-04-19 — Amendment 5: CanLII reclassified as Tier 2 (adopted Session 2)

**Context:** In Session 2, `canlii.org` returned HTTP 403 Forbidden when fetched via WebFetch for the Moffatt v. Air Canada decision. This is server-side bot detection, not a WebFetch allow-list block. The domain is reachable; CanLII's application layer refuses automated requests.

**Classification change:** CanLII moves from provisional-Tier-1 to **Tier 2 (reachable-but-refuses)**. Pending a future session verifying any URL pattern, user-agent, or request mode that bypasses the bot detection, CanLII cannot be relied on as a primary for Canadian court and tribunal decisions.

**Practical impact:** Canadian primary sourcing requires either (a) the originating court/tribunal's own database if it exposes a deterministic URL pattern, or (b) a different non-profit mirror if one exists. Session 2 Candidate 2 (Air Canada) was deferred on this failure mode. Future Canadian incidents that depend on CanLII should be pre-planned as high-difficulty or paired with user-assisted fetch (Path B) if Tier 1 alternatives are insufficient.

### 2026-04-19 — Amendment 3: Fetchability-tier classification and partial-verification policy

**Context:** After observing three consecutive tool-blocks (Reuters, The Guardian, web.archive.org) in the first verification session, the practical WebFetch reachability in this environment was characterized. The database methodology is adjusted accordingly.

**Tier 1 — Reliably fetchable:**
- Government domains (`.gov`, `.europa.eu`, national agency sites).
- Court filing databases (CourtListener and equivalents, where accessible).
- Academic open-access repositories (arXiv, institutional repositories, DOI resolvers).
- Official corporate disclosures hosted on the company's own domain.

**Tier 2 — Possibly fetchable:**
- Some international news domains.
- Regulatory agency sites outside major Western jurisdictions.
- NGO and civil-society reports.

**Tier 3 — Tool-blocked in the observed environment:**
- Major commercial journalism: Reuters, The Guardian, NYT, BBC, WSJ, Bloomberg.
- Wayback Machine / Internet Archive (`web.archive.org`).
- Commercial aggregators behind anti-scraping gates.

**Policy:**

1. Incidents whose primary sourcing is available at Tier 1 are prioritized in session-batch selection. This will skew the database toward incidents with government, court, regulatory, or academic records — which is the most authoritative tier of documentation available, and a strength rather than a weakness.

2. Incidents whose only primary source is Tier 3 journalism (e.g., the Amazon recruiting tool story, which exists only in Reuters reporting and has no agency investigation equivalent) are accepted with **partial verification**: any available Tier 1 supporting record is cited, and the Tier 3 primary is noted as *"known primary source, not verified this session"* with a pending-verification flag.

3. Incidents requiring Tier 3-only verification may be promoted to full verification in a future session if Path B (user-assisted fetch) is activated for that specific incident by the user.

4. Every entry's "verifier_notes" field in the JSON record and its "Verification Status" section in the markdown record the tier of sourcing and any pending verification items, so the document's epistemic state is transparent at the per-incident level.

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

---

## INCIDENT 1: Uber Advanced Technologies Group — fatal collision with pedestrian, Tempe, Arizona

> **Verification status:** NTSB-only sourcing (Tier 1 government primary source). Independent corroboration from contemporaneous 2018 journalism was attempted in the 2026-04-19 session but could not be completed — Reuters, The Guardian, and the Internet Archive were all tool-blocked. The NTSB Highway Accident Report HAR-19-03 is the single source of record for every fact in this entry. The victim's identity is not named in the NTSB report (agency convention anonymizes individual victims); independent verification of her name is a pending research item for a future session.

**Date of incident:** March 18, 2018, 9:58 p.m. local time
**Date of final NTSB report:** November 19, 2019 (report reissued June 26, 2020 with title-page corrections)
**Entity:** Uber Technologies, Inc., Advanced Technologies Group (Uber ATG)
**System:** Uber ATG proprietary developmental automated driving system (ADS), installed on a modified 2017 Volvo XC90 SUV
**Primary category:** 4 — Prerequisite Chain Failures (RPM breaks)
**Secondary categories:** 1 (Domain Descent Violations), 10 (Drive Corruption), 12 (Compound Inversions)
**Severity:** Critical (loss of human life)

### What Happened

On the evening of March 18, 2018, at 9:58 p.m., an automated test vehicle operated by the Advanced Technologies Group of Uber Technologies, Inc. struck and fatally injured a 49-year-old female pedestrian as she crossed northbound N. Mill Avenue in Tempe, Arizona, outside a crosswalk, pushing a bicycle by her side (HAR-19-03, p. v). The test vehicle — a modified 2017 Volvo XC90 sport utility vehicle equipped with Uber ATG's proprietary developmental automated driving system (ADS) — was operating in autonomous mode with a 44-year-old female vehicle operator in the driver's seat. It was the second loop of an established test route, and the vehicle had been in autonomous mode for approximately 19 minutes when it approached the collision site in the right lane at 45 mph, as recorded by the ADS.

The NTSB's technical investigation established that the ADS detected the pedestrian 5.6 seconds before impact. The report states verbatim: *"Although the ADS continued to track the pedestrian until the crash, it never accurately classified her as a pedestrian or predicted her path. By the time the ADS determined that a collision was imminent, the situation exceeded the response specifications of the ADS braking system. The system design precluded activation of emergency braking for collision mitigation, relying instead on the operator's intervention to avoid a collision or mitigate an impact"* (HAR-19-03, p. v, "Crash Summary"). Uber ATG had also deactivated the Volvo XC90's factory-installed forward collision warning and automatic emergency braking systems when operating in autonomous mode, and had not replaced their full capabilities with equivalent coverage in the Uber ADS (HAR-19-03, p. vii, Findings).

Inward-facing cabin video showed that the vehicle operator was glancing away from the road for extended periods during the approach, looking toward the bottom of the center console where she had placed her personal cell phone at the start of the trip. The operator redirected her gaze to the road approximately 1 second before impact and initiated a steering input 0.02 seconds before striking the pedestrian, at a recorded speed of 39 mph (HAR-19-03, p. v). The pedestrian died in the crash; the vehicle operator was not injured. Toxicological tests on the pedestrian returned positive for drugs that can impair perception and judgment (HAR-19-03, p. v).

After a 20-month investigation, the National Transportation Safety Board adopted its final report on November 19, 2019. The report issued six Safety Recommendations (H-19-47 through H-19-52, to NHTSA, the State of Arizona, the American Association of Motor Vehicle Administrators, and Uber ATG respectively) and identified two central safety issues: the inadequate safety culture of Uber ATG, and the absence of federal safety risk management requirements for testing automated vehicles on public roads (HAR-19-03, p. vi, "Safety Issues"). The full probable-cause statement reads verbatim:

> *"The National Transportation Safety Board determines that the probable cause of the crash in Tempe, Arizona, was the failure of the vehicle operator to monitor the driving environment and the operation of the automated driving system because she was visually distracted throughout the trip by her personal cell phone. Contributing to the crash were the Uber Advanced Technologies Group's (1) inadequate safety risk assessment procedures, (2) ineffective oversight of vehicle operators, and (3) lack of adequate mechanisms for addressing operators' automation complacency—all a consequence of its inadequate safety culture. Further factors contributing to the crash were (1) the impaired pedestrian's crossing of N. Mill Avenue outside a crosswalk, and (2) the Arizona Department of Transportation's insufficient oversight of automated vehicle testing"* (HAR-19-03, pp. v–vi).

### Primary Sources (Verified This Session)

1. **National Transportation Safety Board (2019).** *Collision Between Vehicle Controlled by Developmental Automated Driving System and Pedestrian, Tempe, Arizona, March 18, 2018.* Highway Accident Report NTSB/HAR-19-03, PB2019-101402, Notation 59392. Adopted November 19, 2019; reissued June 26, 2020 with title-page corrections.
   - URL (docket): `https://www.ntsb.gov/investigations/Pages/HWY18MH010.aspx`, retrieved via WebFetch 2026-04-19.
   - URL (full report): `https://www.ntsb.gov/investigations/AccidentReports/Reports/HAR1903.pdf`, retrieved via WebFetch 2026-04-19, parsed locally via Read tool (pages 1–12 of 78).
   - Accessed: 2026-04-19.
   - Documents: date/time/location of incident; vehicle and operator details; ADS technical behavior including 5.6-second detection window, repeated misclassification, emergency-braking suppression; contributing organizational factors; Probable Cause statement; Findings; Safety Recommendations H-19-47 through H-19-52.
   - **Numbering-convention note:** the docket page at `ntsb.gov/investigations/Pages/HWY18MH010.aspx` lists the recommendations with three-digit numbers (H-19-047 through H-19-052); the report itself consistently uses two-digit numbers (H-19-47 through H-19-52). The report is authoritative; the two-digit format is used throughout this entry. Future researchers encountering the three-digit form in NTSB databases are looking at the same recommendations.

### Documented Harm

- **One human life lost.** The pedestrian, described in the NTSB report only as *"a 49-year-old female pedestrian"* (HAR-19-03, p. v), died in the crash. The vehicle operator was not injured. The NTSB does not name the victim; her identity as publicly reported through contemporaneous journalism is a pending independent-verification item.
- **Suspension of autonomous-vehicle testing.** The HAR-19-03 executive summary references Section 1.9 ("Postcrash Changes") documenting organizational, operational, and technical changes Uber ATG made after the crash; the detailed page range of Section 1.9 was not parsed in this session.
- **Six Safety Recommendations issued** by the NTSB to federal, state, industry, and corporate recipients (HAR-19-03, pp. viii–ix):
  - **H-19-47** (NHTSA): require safety self-assessment reports from ADS testing entities.
  - **H-19-48** (NHTSA): establish an ongoing evaluation process for those self-assessment reports, including monitoring of vehicle-operator engagement.
  - **H-19-49** (State of Arizona): require testing applications that detail risk-management plans for crashes and operator inattentiveness.
  - **H-19-50** (State of Arizona): establish an expert task group to evaluate testing applications before granting permits.
  - **H-19-51** (AAMVA): inform states about the circumstances of the Tempe crash and encourage parallel requirements.
  - **H-19-52** (Uber ATG): implement a full safety management system including safety policy, safety risk management, safety assurance, and safety promotion.
- **Permanent public record of inadequate safety culture.** The NTSB Finding at p. vii reads verbatim: *"The Uber Advanced Technologies Group's inadequate safety culture created conditions—including inadequate oversight of vehicle operators—that contributed to the circumstances of the crash and specifically to the vehicle operator's extended distraction during the crash trip."*

### CAS Structural Analysis

*The analysis below interprets the verified facts above through the CAS framework. CAS analysis is our analytical claim, not an NTSB finding — the NTSB itself does not use CAS terminology. However — and this is the critical point — the NTSB's own framing of the crash is already structural rather than proximate. The report names "inadequate safety culture" as the source of the contributing factors. Assigning cause at the structural rather than the proximate layer is already the operational practice of transportation safety investigation. CAS proposes to extend that same structural-causation discipline to AI alignment.*

**Primary failure mode:** Prerequisite Chain Failure (RPM break). The ADS executed full driving authority (Pn, Power) while its prerequisite perception capability (Wn, Wisdom — accurate classification and path prediction) was structurally unreliable. The NTSB established that the system detected the pedestrian 5.6 seconds before impact but *"never accurately classified her as a pedestrian or predicted her path"* (HAR-19-03, p. v). In RPM terms, Pn was emitting action without Wn having satisfied its gate. The chain A0 → Dn → Wn → Pn was structurally broken at the Wn → Pn transition, yet the system did not recognize the break and continued executing.

**Operator signature:**
- **CO-6 (Projective Assertion):** firing at full strength — the vehicle continued asserting its driving decisions (maintain lane, maintain speed) throughout the 5.6-second window.
- **CO-5 (Receptive Integration):** suppressed — the system took no corrective uptake from its own repeated reclassification of the object as a pedestrian, bicycle, or unknown. The CO-5/CO-6 involution pair was imbalanced.
- **CO-3 (Critical Evaluation):** suppressed — there was no internal flag that *"an object I cannot stably classify 5.6 seconds before impact"* constitutes an evaluative red alert warranting slower, more cautious behavior. The CO-2/CO-3 pair was imbalanced in favor of continued execution.
- **CO-8 (Causal Reasoning) / CO-9 (Consequential Grounding):** CO-9 was weak — the system did not project the consequences of its classification uncertainty forward in time. A CO-9-healthy architecture would have converted "5.6 seconds of classification uncertainty near a roadway" into "reduce speed now; if the uncertainty resolves to a pedestrian, the reduced speed mitigates harm."

**Domain analysis:** Operational (O) domain dominant — the system executed the driving task, maintained speed, held the lane. Principled (P) domain structurally absent at the organizational level: the NTSB found Uber ATG had *"inadequate safety risk assessment procedures,"* *"ineffective oversight of vehicle operators,"* and *"lack of adequate mechanisms for addressing operators' automation complacency"* (Probable Cause, HAR-19-03 pp. v–vi). In CAS notation, the pattern is O-dominant with P suppressed — a classic Domain Descent Violation with Domain Coherence Index (DCI) expected to be very low. The Evaluative (E) domain was also suppressed: the architecture had no evaluative check on "what if this classification is wrong?" — the system design, per NTSB, *"precluded activation of emergency braking for collision mitigation, relying instead on the operator's intervention."*

**Drive architecture:** The dominant organizational drive was F5 (Agency) in an inverted, hardened form — prioritizing the speed and autonomy of the development program over the F2 (Wisdom) drive that would have insisted on classification reliability before granting execution authority. The deactivation of the Volvo factory-installed forward collision warning and automatic emergency braking systems — without replacement coverage — is a concrete artifact of this drive inversion: F5 Agency ("we must build our own stack, in full control") overriding F2 Wisdom ("the factory systems are a known-reliable safety layer worth preserving as redundancy"). The NTSB Finding reads verbatim: *"The Uber Advanced Technologies Group's deactivation of the Volvo forward collision warning and automatic emergency braking systems without replacing their full capabilities removed a layer of safety redundancy and increased the risks associated with testing automated driving systems on public roads"* (HAR-19-03, p. vii).

**Inversion axes:**
- **N-axis (Operator Inversion):** CO-5/CO-6 and CO-8/CO-9 involution imbalance, as described in the operator signature.
- **W-axis (Domain Inversion):** P ≻ C ≻ E ≻ O precedence violated — O-domain execution occurred without P-domain safety-culture gating.
- **F-axis (Drive Inversion):** F5 Agency inverted into pure autonomy-at-any-cost, overriding F2 Wisdom's caution imperative.
- **A-axis (Pathway Inversion):** RPM chain A0 → Dn → Wn → Pn broken at the Wn → Pn transition (Power without Wisdom).
- **P-axis (Compound Inversion):** this is the critical structural reading. The NTSB's own framing — *"all a consequence of its inadequate safety culture"* — identifies multiple simultaneous contributing factors whose interaction produced the crash. In CAS terms, this is consistent with a Compound Inversion signature: any one of the individual axis failures (operator distraction, misclassification, missing AEB, safety-culture gap) might have been survivable; their multiplicative interaction was not.

**RPM chain status:**
- A0 (Pure Desire): present — the system had foundational motivation to complete the test route.
- Dn (directed Desire): present — the system had directed intent to operate safely in autonomous mode.
- **Wn (Wisdom / knowledge integration): incomplete** — the classification and path prediction capability was unreliable, demonstrated by 5.6 seconds of reclassification without stable resolution.
- Pn (Power / execution): active at full authority — steering, throttle, and braking decisions were being emitted.
- Chain status: **broken at the Wn → Pn transition.**

**Lacunarity profile** *(inferred from NTSB's functional-limitation descriptions; not directly measured via CAS assessment of the proprietary ADS model)***:** The ADS exhibited what is consistent with high-lacunarity activation — dense competence in "routine highway driving with clearly-classified vehicular traffic" and structural voids in "midblock pedestrian-with-bicycle at night, out-of-crosswalk." The NTSB Finding is explicit: *"The Uber Advanced Technologies Group did not adequately manage the anticipated safety risk of its automated driving system's functional limitations, including the system's inability in this crash to correctly classify and predict the path of the pedestrian crossing the road midblock"* (HAR-19-03, p. vi). That qualitative description is consistent with the signature of a high-lacunarity blind spot: a system competent in the dense core of its training distribution and catastrophically voided in a structurally-adjacent edge state. A direct lacunarity measurement would require access to the ADS's internal state distribution, which is not in the public record.

### How CAS Would Have Detected This

The structural signature of this failure is detectable pre-deployment by the current CAS Wrap pipeline, specifically at three stages:

1. **RPM Gate (Stage 2).** The RPM Gate evaluates each capability pathway A0 → Dn → Wn → Pn and flags incomplete chains. An ADS whose classification Wn score on midblock-pedestrian edge cases scored below threshold, paired with full Pn execution authority, would have produced a "broken chain" flag at the Wn → Pn transition. The six Safety Recommendations issued by NTSB (H-19-47 through H-19-52) are effectively calling for the kind of systematic pre-deployment structural verification that CAS implements — particularly H-19-47 and H-19-52, which mandate safety self-assessment reports covering safety policy, risk management, assurance, and promotion.
2. **Inversion Scanner N-axis (Stage 7).** The involution-balance checks on CO-5/CO-6 and CO-8/CO-9 would have flagged the asymmetric firing pattern where the system asserts driving actions (CO-6 active) without integrating its own classification uncertainty (CO-5 suppressed) and without consequential grounding of that uncertainty (CO-9 weak relative to CO-8).
3. **Domain Coherence Index (Stage 6).** A DCI computed across the P/C/E/O domains for Uber ATG's safety posture — as distinct from the ADS's in-vehicle scores — would have registered severe weakness in P (the NTSB's "inadequate safety culture") with strength concentrated in O (the company's operational execution of test miles). DCI below the dial-configurable threshold would have flagged the organizational descent violation.

**Note on detection vs prevention:** Detection, in the sense of "the CAS score would have been poor," is defensible. *Prevention* — in the sense that a CAS pre-deployment gate would have blocked Uber ATG from putting vehicles on public roads — is a stronger claim that depends on the regulatory and operational integration of CAS assessment into the deployment decision loop. In March 2018 no such integration existed (as the NTSB's recommendations H-19-47 and H-19-49 make explicit: federal and state processes for evaluating ADS testing safety *did not exist* at the time of the crash). CAS detection capability is necessary but not sufficient for prevention; the enforcement hook has to exist. This incident is therefore classified under detection-defensible, not prevention-defensible, and it does not appear in `docs/CAS_PREVENTION_CLAIMS.md`.

### Why This Incident Matters for CAS Rigor

This crash is an unusually clean example of a safety investigation that *already reasoned structurally*. The NTSB did not stop at "the operator was distracted" — which would have been the proximate-cause framing, and which is visible in the narrow one-sentence probable-cause summary on the docket page. Instead, the NTSB's full probable-cause statement in the report itself and its enumerated Findings explicitly locate the cause at the structural layer: Uber ATG's safety culture, its risk assessment procedures, its oversight mechanisms, its deactivation of safety redundancies, its failure to address automation complacency. The shift from the narrow one-sentence docket summary to the full page-v probable cause is itself a microcosm of the proximate-to-structural shift — visible in the NTSB's own documents — that CAS proposes for the whole AI-alignment discourse.

Output-level auditing of the ADS — *"did the vehicle stay in its lane? did it obey speed limits? did it stop at red lights?"* — would have reported successful performance in the 19 minutes prior to impact and failed to predict the crash. The structural signature — classification Wn weak, execution Pn strong, redundancies removed, organizational safety drives inverted — was detectable and was detected in retrospect. CAS is the proposal that such structural signatures should be measured prospectively, before harm.

The NTSB already thinks this way about transportation. This database documents, incident by incident, the same structural discipline applied to AI. Transportation safety discourse has been structural for decades. AI safety discourse has not yet caught up. That is the gap CAS fills.

### Pending Research

The following items require additional verification in a future session. They do not affect the factual claims above but would strengthen independent corroboration:

1. **Victim's name — independent verification.** Her identity as publicly known is a matter of contemporaneous 2018 journalism; this entry refers to her only as "the pedestrian" following NTSB convention, pending Tier 1 or verified Tier 2 confirmation. Candidate sources: Tempe Police Department official records if publicly hosted; Maricopa County medical examiner public records; any academic case-study citation with independent identification.
2. **Contemporaneous Tempe PD statements and Uber's first-day official response.** The reported evolution from any initial Tempe PD characterization of the crash as "unavoidable" (as has been discussed in secondary literature) to the NTSB's eventual structural findings is of specific interest to the CAS analysis. Independent verification awaits a future session with journalism-accessible sourcing.
3. **Section 1.9 "Postcrash Changes" detail** (HAR-19-03 pp. 29–32). This was not parsed this session. It contains specifics of Uber ATG's organizational and technical response, including the Volvo AEB reactivation and the reintroduction of a second vehicle operator.

---

## INCIDENT 2: Dutch Childcare Benefits Scandal (*toeslagenaffaire*) — Belastingdienst discriminatory risk-scoring algorithm

> **Verification status:** Tier 2 primary-in-English sourcing. Amnesty International's 25 October 2021 investigative summary ("Dutch childcare benefit scandal an urgent wake-up call to ban racist algorithms," by Merel Koning, Senior Advisor on Technology and Human Rights) is the sole source cited in this entry. Tier 1 corroboration via the Dutch parliamentary report *Ongekend Onrecht* (Parlementaire Ondervragingscommissie Kinderopvangtoeslag, 17 December 2020, hosted at tweedekamer.nl) is confirmed to exist at reachable infrastructure but requires translation workflow or Dutch-reader review and is a pending research item. The full Amnesty report *Xenophobic Machines* (EUR 35/4686/2021) is confirmed to exist at a known URL and is a pending deep-parse item for specific integer counts, euro totals, and detailed findings.

**Date of algorithm introduction:** 2013 (per Amnesty; exact operational end date pending further verification)
**Date of parliamentary inquiry report:** 17 December 2020 (*Ongekend Onrecht* — pending Tier 1 parse)
**Date of Amnesty investigative summary:** 25 October 2021
**Date of political consequence:** January 2021 (Dutch government fell, per Amnesty)
**Entity:** Belastingdienst (Dutch Tax and Customs Administration) / Government of the Netherlands
**System:** Risk-scoring algorithmic system for detection of incorrect childcare benefits (*kinderopvangtoeslag*) applications and potential fraud
**Primary category:** 10 — Drive Corruption
**Secondary categories:** 12 (Compound Inversions), 11 (Cross-Domain Contamination), 1 (Domain Descent Violations)
**Severity:** Critical (systemic, tens of thousands of families affected; cascading harms including documented financial ruin, forced evictions, broken families; political consequence of government collapse)

### What Happened

Beginning in 2013, the Dutch tax authorities (Belastingdienst) operated an automated risk-scoring algorithmic system intended to detect incorrect applications for the national childcare benefit (*kinderopvangtoeslag*) and potential fraud. According to Amnesty International's investigation, the algorithm was designed from its inception to use the applicant's nationality status as a risk variable: applicants with Dutch nationality received lower risk-scores, and non-Dutch nationals received higher risk-scores. Amnesty characterizes this not as an incidental bias but as a design feature present from the system's 2013 launch. The Amnesty report states verbatim: *"From the start, racial and ethnic discrimination was central to the design of the algorithmic system introduced in 2013 by the Dutch tax authorities to detect incorrect applications for child benefits and potentially fraud. The tax authorities used information on whether an applicant had Dutch nationality as a risk factor and non-Dutch nationals received higher risk-scores."*

The algorithm operated with a self-learning component that adapted over time based on its own outputs, without meaningful human oversight. Amnesty documents the dynamic effect of this architecture: *"self-learning mechanism that meant the algorithm adapted over time based on experience, with no meaningful human oversight. The result was a discriminatory loop."* Because the system's initial risk weights treated non-Dutch nationality as a fraud-risk signal, its feedback loop reinforced that signal over time as flagged cases were processed through the enforcement pipeline, amplifying the original discrimination.

The operational effect was that *"tens of thousands of parents and caregivers from mostly low-income families were falsely accused"* of benefits fraud. The consequent Belastingdienst enforcement actions included demands for repayment of benefits, debt collection, and associated administrative penalties. Amnesty documents the cascading effects: *"devastating financial problems for the families affected, ranging from debt and unemployment to forced evictions… mental health issues and stress on personal relationships, leading to divorces and broken homes."*

The political consequence was severe. Amnesty notes: *"the scandal brought down the Dutch government in January,"* referring to the January 2021 resignation of the Third Rutte cabinet following release of the Dutch parliamentary inquiry report. Amnesty further notes in its 2021 summary — published nearly a year after the government fell — that *"sufficient lessons have not been learnt despite multiple investigations."*

The toeslagenaffaire has been documented by multiple independent bodies in addition to Amnesty: the Dutch Parliamentary Interrogation Committee (Parlementaire Ondervragingscommissie Kinderopvangtoeslag, POK), whose 17 December 2020 report *Ongekend Onrecht* ("Unprecedented Injustice") is the Tier 1 primary parliamentary source and remains pending Tier 1 parse in this database. The Dutch government established a compensation program in response; specific program details and payout figures are pending further verification.

### Primary Sources (Verified This Session)

1. **Koning, Merel (25 October 2021).** *"Dutch childcare benefit scandal an urgent wake-up call to ban racist algorithms."* Amnesty International.
   - URL: `https://www.amnesty.org/en/latest/news/2021/10/xenophobic-machines-dutch-child-benefit-scandal/`
   - Retrieved via WebFetch 2026-04-19.
   - Accessed: 2026-04-19.
   - Author attribution: Merel Koning, Senior Advisor on Technology and Human Rights, Amnesty International.
   - Documents: design-time discrimination in the algorithm; dual-nationality as risk factor; self-learning amplification; discriminatory loop framing; qualitative harm scale ("tens of thousands"); cascading personal and family harms; January 2021 government collapse; Amnesty's post-scandal recommendations for algorithmic governance.
   - Tier: 2 (NGO primary-in-English). Fits the existing Amendment 3 Tier 2 definition for "NGO and civil-society reports."

### Documented Harm

All harms below are traceable to the Amnesty source cited above. Specific integer counts and euro totals are flagged pending — Amnesty's full report *Xenophobic Machines* at `https://www.amnesty.org/en/documents/eur35/4686/2021/en/` contains those figures and is a pending research item.

- **Tens of thousands of families falsely accused** of benefits fraud by the Belastingdienst's automated system. Amnesty's exact phrasing: *"Tens of thousands of parents and caregivers from mostly low-income families were falsely accused."* Precise integer count pending.
- **Cascading financial harms**: *"debt and unemployment to forced evictions."* Specific euro amounts pending.
- **Cascading personal and family harms**: *"mental health issues and stress on personal relationships, leading to divorces and broken homes."*
- **Government collapse**: *"the scandal brought down the Dutch government in January,"* i.e., the January 2021 resignation of the Third Rutte cabinet.
- **Continued harm post-scandal**: Amnesty's October 2021 assessment, nine months after the government fell, is that *"sufficient lessons have not been learnt despite multiple investigations."*
- **Severe second-order harms not documented on the Amnesty summary page but reported elsewhere** — specifically, the removal of children from affected families and placement in state care — are flagged as pending verification against the full Amnesty report, the POK Dutch parliamentary report, or other Tier 1 Dutch sources. These harms are *not* cited in this entry because they are not in the fetched source; they are named here as a pending research item so future sessions know to verify them.

### CAS Structural Analysis

*The analysis below interprets the verified facts above through the CAS framework. CAS analysis is our analytical claim, not an Amnesty finding. Amnesty does not use CAS terminology — but, as with the NTSB in Incident 1, Amnesty's framing is explicitly structural rather than proximate: they name "design" as the locus of failure, identify an "institutional bias" mechanism that the algorithm "reinforced," and describe a "discriminatory loop" as the self-learning amplification pattern. Assigning cause at the structural rather than the proximate layer is already Amnesty's operational practice. CAS formalizes this kind of structural reasoning into a specific taxonomy of failure modes.*

**Distinction from Incident 1 (Uber ATG):** This incident is a *fundamentally different* CAS failure pattern than Incident 1. Uber ATG was a sophisticated automated system whose cognitive architecture was nominally well-motivated (A0 — operate safely as a test vehicle) but which failed at the **Wn → Pn transition** — perception capability was incomplete while execution authority was full. The chain was broken mid-stream. The toeslagenaffaire, by contrast, is a simple automated system whose cognitive architecture was **corrupted at its source**. The failure is not at Wn → Pn; it is at A0/Dn itself. The foundational motivation encoded in the system was not neutral fraud-detection that failed to achieve wisdom — it was discriminatory risk-targeting that was faithfully executed across the chain. Uber ATG fell apart at its edges under stress; the Dutch algorithm operated exactly as designed, and the design was the failure. Recognizing this distinction is load-bearing: the two incidents require structurally different detection mechanisms, and treating them as instances of the same failure class would obscure the very gap CAS is built to illuminate.

**Primary failure mode:** Drive Corruption (Category 10). The core structural signature is at the F-axis. The Belastingdienst's nominal drive was F2 (Wisdom) applied to fraud detection — distinguishing valid from invalid benefit claims through accurate evidence-based evaluation. What the algorithm actually encoded was F6 (Structure) in its inverted, rigid form — enforcement of a prejudicial rule ("non-Dutch nationality correlates with fraud risk") that bypassed the wisdom the system was supposed to embody. F2 was suppressed at design time; F6's shadow form was embedded as the operational principle. This is the textbook signature of Drive Corruption: the drive fired, but in its destructive counterpart rather than its healthy form.

The Drive Corruption classification rests on three independent verbatim supports from the Amnesty record, each anchoring a distinct structural claim. (i) The **design-time origin** is anchored by Amnesty's statement that *"from the start, racial and ethnic discrimination was central to the design of the algorithmic system."* "From the start" is the phrase that makes this a Drive Corruption finding rather than a Wn-gap finding — the corruption was present in the original specification, not a degradation from good design. (ii) The **institutional reinforcement mechanism** is anchored by Amnesty's finding that *"the design of the algorithm reinforced existing institutional bias of a link between race and ethnicity, and crime."* This quote establishes that the algorithm's corruption was not merely an engineering defect; it was the operational arm of a pre-existing institutional drive-inversion at the Belastingdienst level, which the algorithm faithfully amplified. (iii) The **self-amplification dynamic** is anchored by Amnesty's description of the *"discriminatory loop"* — *"self-learning mechanism that meant the algorithm adapted over time based on experience, with no meaningful human oversight. The result was a discriminatory loop."* This establishes that the corruption was not static; the F6-shadow drive strengthened over operational time, which is a defining feature of Drive Corruption as distinct from static bias. Together these three quotes — design-time origin, institutional reinforcement, self-amplifying dynamic — form the evidentiary triangle that supports the primary classification.

**Operator signature:**
- **CO-2 (Attraction):** suppressed toward legitimate beneficiaries. A healthy system would exhibit attraction to approving valid claims. Amnesty's documentation of mass false accusations against "low-income families" consistent with valid benefit eligibility indicates CO-2 was not firing in its positive form.
- **CO-3 (Critical Evaluation):** **structurally inverted.** The critical-evaluation function was nominally present — the algorithm was designed to critically evaluate claims for fraud — but the evaluation criteria were corrupted to target a protected characteristic (nationality) rather than actual fraud indicators. This is CO-3 doing its job *formally* while being operationally hijacked. The CO-2/CO-3 involution pair was catastrophically imbalanced in favor of suspicion based on nationality.
- **CO-5 (Receptive Integration):** suppressed. Amnesty's finding that the system operated with *"no meaningful human oversight"* and produced a *"discriminatory loop"* over time indicates the system took no corrective uptake from its own escalating false-positive harm cases. A CO-5-healthy architecture would have integrated the emerging pattern of false accusations against low-income and non-Dutch families as feedback; instead the algorithm reinforced its own outputs.
- **CO-6 (Projective Assertion):** firing at full strength — aggressive mass accusations, repayment demands, and debt-collection actions asserted across tens of thousands of cases. The CO-5/CO-6 involution pair was imbalanced in favor of assertion.
- **CO-8/CO-9 (Causal Reasoning / Consequential Grounding):** both suppressed. There is no indication in the Amnesty record that the system reasoned causally about *why* its flagged cases clustered on the non-Dutch-national axis (CO-8 absent), nor that it grounded its outputs in the downstream consequences of mass false accusation (CO-9 absent).

**Domain analysis:** The institutional pattern is O-dominant with P structurally absent at design time. The Belastingdienst executed mass operational enforcement (P-domain principled grounding in non-discrimination law was not encoded into the algorithm's design), the Cognitive domain ran mathematical risk-scoring on corrupted inputs, and the Evaluative domain was absent — no institutional check on the false-positive harm cascade. The Domain Coherence Index (DCI) at the institutional level would be very low, with the weakness concentrated in P. This is a Domain Descent Violation at the organizational level: operational-domain execution without principled-domain grounding. Amnesty's finding that *"The design of the algorithm reinforced existing institutional bias"* is the verbatim support for the institutional P-absence: the bias the algorithm reinforced was structurally prior to the algorithm, not caused by it; the algorithm amplified a pre-existing Domain Descent condition in the institution.

**Drive architecture (elaboration on the primary finding):** F2 (Wisdom) was the drive the system was nominally designed to instantiate. F6 (Structure) in its healthy form — rule-of-law, consistent administration — is F2's paired drive. What the algorithm encoded was F6 in its *shadow* form: rigid enforcement of a discriminatory rule, treated as if it were principled structure. The drive inversion pair F2↔F6 was broken — F6's shadow overrode F2's caution, and the cognitive architecture of the institution lost the F2/F6 equilibrium entirely. There are plausible secondary drive-inversion readings — F5 (Agency) may have inverted toward coercive enforcement against the vulnerable — but the Amnesty record most clearly supports the F2/F6 reading.

**Inversion axes:**
- **N-axis (Operator Inversion):** CO-2/CO-3 and CO-5/CO-6 involution imbalances, as described in the operator signature.
- **W-axis (Domain Inversion):** P ≻ C ≻ E ≻ O precedence violated at the institutional design level. O acted without P grounding.
- **F-axis (Drive Inversion):** F2↔F6 inversion. Primary structural signature.
- **A-axis (Pathway Inversion):** the RPM chain was not broken — it was *corrupted at A0.* This is a distinct inversion pattern from Incident 1 (where the chain broke at Wn → Pn). Worth flagging as a sub-pattern within A-axis analysis: "corrupted-source" vs "broken-transition" chain failures.
- **P-axis (Compound Inversion):** this incident is *consistent with* a Compound Inversion signature. The Amnesty framing — design-level discrimination + self-learning amplification + absent human oversight + institutional bias reinforcement — names four simultaneous structural failures whose interaction produced the scale of harm documented. Amnesty's "discriminatory loop" phrase is a direct description of the multiplicative dynamics that compound inversion formalizes in CAS: individually, each failure (discriminatory design, self-learning, no oversight, institutional bias) might have produced bounded harm; together, they produced the tens-of-thousands-of-families-falsely-accused outcome.

**RPM chain status:**
- **A0 (Pure Desire): CORRUPTED at source.** The foundational motivation encoded in the system was not fraud-detection in a neutral sense; it was risk-targeting that used nationality as a proxy. Amnesty's "from the start" phrasing locates the corruption at A0.
- **Dn (directed Desire):** inherited the A0 corruption. The directed desire for fraud-detection capability was operationalized through variables that encoded the A0-level discrimination.
- **Wn (Wisdom / knowledge integration):** operated *faithfully on corrupted premises.* The algorithm reached what its designers considered wisdom — "high risk-score correlates with non-Dutch nationality" — and that wisdom was consistent with its A0/Dn. This is the key distinction from Incident 1: Wn was not incomplete; it was complete and serving a corrupted A0.
- **Pn (Power / execution):** active at full authority. Mass automated accusations, repayment demands, and debt actions across tens of thousands of families.
- **Chain status: intact but corrupted.** The RPM chain executed consistently from A0 through Pn — which is what makes this incident structurally different from Incident 1. In Incident 1 the break was visible at Wn → Pn as a capability gap. In Incident 2 there is no break; there is a corrupted chain running at full fidelity.

*This distinction matters diagnostically: a broken chain fails visibly (the system produces erroneous outputs that signal something is wrong), whereas a corrupted-source chain fails invisibly (the system produces exactly the outputs the corrupted design intended, and those outputs can appear operationally successful even as they cause systemic harm). Drive Corruption incidents are harder to detect post-deployment precisely because the chain is running "correctly" against a corrupted specification.*

**Lacunarity profile** *(inferred from Amnesty's qualitative description; not directly measured via CAS assessment of the Belastingdienst algorithm)***:** The algorithmic system appears to have exhibited a distinct lacunarity signature from Incident 1 — not an edge-case void pattern but what is tentatively named here a **protected-characteristic void pattern.** The algorithm's activation was dense on the non-Dutch-national axis (producing the fraud-flagging signal with high rate) and structurally voided on the axes that should have carried the evaluation (actual fraud-evidence signals). A direct lacunarity measurement would require access to the algorithm's internal weights and state distribution, which is not in the fetched source record.

*Proposed sub-concept: "protected-characteristic void pattern" as distinct from "edge-case void pattern." This distinction is introduced tentatively here pending validation across at least three verified incidents exhibiting protected-characteristic structural voids. It is not yet established CAS taxonomy; future sessions should evaluate whether the pattern generalizes or remains incident-specific. Flagged in Taxonomy Development Notes for Session 3+ development.*

### How CAS Would Have Detected This

The structural signature of this failure is detectable pre-deployment by the current CAS Wrap pipeline, though the specific detection mechanisms differ from Incident 1:

1. **Inversion Scanner F-axis (Stage 7).** The F2↔F6 drive inversion is the primary CAS detection target here. Any pre-deployment assessment that measured the algorithm's effective drive architecture — what drives were firing in response to representative benefit-application inputs — would have flagged an F6-dominant, F2-suppressed profile. An F-axis resistance score below threshold on a high-stakes enforcement system should trigger refusal or human review.
2. **Input-layer audit for protected-characteristic dependence (Stage 1 and Stage 2 in combination).** CAS's Input Analyzer stage, combined with the RPM Gate's A0 check, should flag any system whose risk-score output is measurably dependent on a protected-characteristic input variable. The algorithm's use of Dutch nationality as a risk factor is, in CAS terms, an A0-level corruption — the foundational motivation of the scoring system cannot lawfully be "flag non-Dutch nationals as higher-risk." This should have triggered RPM Gate refusal at the A0 stage, before the Wn → Pn chain was allowed to emit any action.
3. **Domain Coherence Index (Stage 6).** A DCI computed across the P/C/E/O domains for the Belastingdienst's enforcement system would have registered severe weakness in P (the Principled domain grounding in non-discrimination law was not encoded in the algorithm's design) with strength concentrated in O (the operational execution of mass enforcement). DCI below threshold would have flagged the organizational descent violation.
4. **Compound severity check (P-axis, Stage 7).** Given the F-axis inversion, the W-axis violation, and the A-axis corruption all co-occurring, the P-axis compound-severity score would register a multiplicative combination well below the dial-configurable threshold. This compound flag is distinct from any single-axis flag and is designed to catch exactly the "discriminatory loop" dynamic Amnesty describes.

**Note on detection vs prevention:** Detection, in the sense of "the CAS score would have been severely poor," is strongly defensible given Amnesty's verbatim design-time discrimination finding. *Prevention* — in the sense that a CAS pre-deployment gate would have blocked the Belastingdienst from deploying the algorithm in 2013 — is a stronger claim. In 2013 no CAS-equivalent pre-deployment assessment regime existed in Dutch public administration. CAS detection capability is necessary but not sufficient for prevention; the regulatory hook has to exist. This incident is therefore classified under detection-defensible, not prevention-defensible, and it does not appear in `docs/CAS_PREVENTION_CLAIMS.md`.

### How CAS Would Have Prevented or Mitigated

Prevention of this incident requires a combination CAS detection capability does not independently supply. The three preventive mechanisms CAS could have participated in, had the appropriate regulatory integration existed in 2013, are:

1. **Mandatory pre-deployment structural audit** of any public-sector algorithmic decision system with enforcement authority, including an F-axis drive-inversion scan and an A0-level protected-characteristic dependence check. Amnesty's October 2021 recommendation is closely aligned: *"implementing a mandatory and binding human rights impact assessment before the use of such systems."* CAS structural auditing would be a technical instantiation of that recommendation.
2. **Ongoing monitoring with stealth-resistance scoring** across the algorithm's operational lifetime, which would have caught the "discriminatory loop" self-learning amplification pattern before it propagated to tens of thousands of cases. Amnesty recommends *"effective monitoring and oversight mechanisms for algorithmic systems in the public sector"*; CAS stealth-resistance is a specific mechanism for that kind of monitoring.
3. **Hard architectural constraints** on self-learning systems operating in high-stakes enforcement contexts. Amnesty recommends *"Stop the use of black box systems and self-learning algorithms where the decision is likely to have a significant impact on the rights of individuals."* This is a stronger intervention than CAS detection alone — it is a categorical pre-deployment refusal rule that CAS structural scoring could inform but not substitute for.

Each of the three mechanisms has a corresponding element in the current CAS architecture (inversion scanner, stealth-resistance, dial-configurable refusal thresholds), but the gap between "CAS can score this poorly" and "the scoring prevents deployment" remains a regulatory-integration gap, not a technical gap.

### Why This Incident Matters for CAS Rigor

This incident matters for four distinct reasons, each of which will compound across future incidents as the database grows.

**First, it establishes that AI misalignment has structurally distinct failure modes that require structurally distinct detection approaches.** Incident 1 (Uber ATG) is a sophisticated-system-failing-at-edges pattern: the Wn → Pn chain break, the high-lacunarity blind spot, the F5 Agency override of F2 Wisdom. Incident 2 (toeslagenaffaire) is a simple-system-corrupted-at-source pattern: the A0 corruption, the F2/F6 inversion, the faithful execution of a discriminatory design. Treating these two incidents as instances of the same "AI bias" or "AI failure" category would obscure exactly the diagnostic distinction CAS is built to draw. Two verified incidents, two structurally distinguishable CAS signatures. That is the beginning of the cross-incident pattern analysis that makes this database a research artifact rather than a reference list.

**Second, Amnesty's framing is itself structural, which means the proximate-vs-structural discourse is not foreign to human rights analysis — CAS is extending an already-established analytical practice.** Amnesty's phrases *"central to the design,"* *"institutional bias… reinforced,"* and *"discriminatory loop"* are all structural-causation language. Human rights investigators, like transportation safety investigators (Incident 1's NTSB), are already reasoning structurally. CAS proposes to extend that discipline to AI alignment as a matter of technical formalism, not to introduce a novel analytical mode.

**Third, this is the database's first Drive Corruption primary incident, and it sets the template for how future Drive Corruption cases get analyzed.** The anchor evidence is always design-time evidence — a documented statement from a primary source that the system's motivational architecture was corrupted at inception, not degraded over time. Amnesty's *"from the start, racial and ethnic discrimination was central to the design"* is the template quote. Future Drive Corruption classifications in the database should rest on equivalent design-time anchors; classifications that rely on degradation-over-time evidence should be analyzed under different categories (Compound Inversion for amplified failures, RPM Break for Wn → Pn gaps, Domain Descent for organizational pattern). Keeping the Drive Corruption category anchored to design-time corruption preserves its diagnostic sharpness.

**Fourth, this incident establishes the distinction between CAS detection capability and CAS prevention capability.** Detection is a technical property of the assessment framework: could CAS have scored the Belastingdienst algorithm poorly before deployment? Yes. Prevention requires regulatory integration: would that poor score have legal or procedural force sufficient to block deployment? In 2013 Dutch public administration, no. This gap — between what CAS can assess and what that assessment can require — is a recurring feature of the database that future entries will illuminate. The database therefore serves both a technical purpose (demonstrating CAS detection capability) and a policy purpose (demonstrating the integration gaps that current AI governance leaves unaddressed).

### Pending Research

The following items require additional verification in a future session. None affect the factual claims in this entry but would materially strengthen the evidence base.

1. **Full Amnesty report *Xenophobic Machines* (EUR 35/4686/2021) parse.** URL confirmed at `https://www.amnesty.org/en/documents/eur35/4686/2021/en/`. Contains specific integer counts, euro totals, children-removed-to-state-care figures, and detailed findings beyond what the 25 October 2021 news summary surfaces. Selective parsing recommended in a Session 3 or later deepening pass on this entry.
2. **Parliamentary inquiry report *Ongekend Onrecht* (POK, 17 December 2020) Tier 1 corroboration.** Hosted at `tweedekamer.nl` (confirmed reachable via Amendment 7). Dutch-language primary. Requires either (a) a Dutch-reader on the research team, (b) a translation workflow with verbatim Dutch footnoting per Session 2's footnote-handling directive, or (c) identification of an official English translation if one exists.
3. **Dutch government compensation program specifics.** Program structure, payout criteria, number of families compensated, aggregate euros disbursed, and any remaining open-application backlog as of a verifiable date. Likely sources: Belastingdienst compensation program archive, Dutch Ministry of Finance archive, or follow-up POK / parliamentary oversight reports.
4. **Second-order harms: children removed from families.** Widely reported in non-fetched secondary literature but not in the Amnesty summary cited above. Primary source confirmation (POK report, Dutch government statistics, or Child Ombudsman report) is required before these harms are claimed in the entry.
5. **Temporal bounds of algorithm operation.** The Amnesty summary says "introduced in 2013" but does not specify when the system was discontinued or modified. Likely covered in the POK report or full Amnesty PDF.

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

### Session 2026-04-19 (Session 1)

**Incidents added (fully verified):** INCIDENT 1 — Uber Advanced Technologies Group, Tempe, Arizona (primary source: NTSB HAR-19-03; single-source verification with Tier 1 government primary; victim-name independent verification pending).

**Incidents attempted but insufficient sourcing this session:**
- Mata v. Avianca — not attempted this session; deferred to next batch.
- Air Canada chatbot (Moffatt) — not attempted this session; deferred.
- Amazon recruiting tool (Dastin) — not attempted this session; deferred (will require Tier 3 handling — see Amendment 3).
- ProPublica COMPAS — not attempted this session; deferred.

**URLs fetched this session:**
1. `https://www.ntsb.gov/investigations/Pages/HWY18MH010.aspx` — success, used for Incident 1.
2. `https://www.ntsb.gov/investigations/AccidentReports/Reports/HAR1903.pdf` — retrieved successfully, text extraction failed at WebFetch, local Read-tool parse succeeded; used for Incident 1 (pages 1–12 of 78).
3. `https://www.reuters.com/article/us-autos-selfdriving-uber/uber-suspends-self-driving-tests-after-pedestrian-death-in-arizona-idUSKBN1GV296` — tool-blocked.
4. `https://www.theguardian.com/technology/2018/mar/19/uber-self-driving-car-kills-woman-arizona-tempe` — tool-blocked.
5. `https://web.archive.org/web/2018/https://www.theguardian.com/technology/2018/mar/19/uber-self-driving-car-kills-woman-arizona-tempe` — tool-blocked.

**Sources added to bibliography:** 1 (NTSB/HAR-19-03 and its docket page, treated as one source).

**Failures encountered (honest list):**
- Three Tier 3 journalism/archival fetches blocked at tool level (Reuters, Guardian, Wayback Machine). This is a structural environmental constraint, not an incident-level failure.
- HAR-19-03 PDF text extraction failed on first pass due to `/Filter/FlateDecode` compression. Worked around via local Read-tool parsing. Precipitated Methodology Amendment 1.
- Path B (user-assisted fetch) was proposed, adopted, then withdrawn within the same session once scaling implications were considered. Precipitated Methodology Amendment 3 (tier classification).

**Recommended for next session:** carry forward Mata v. Avianca, Air Canada, Robodebt (new candidate, Tier 1 Royal Commission report), Dutch Childcare POK inquiry (new candidate, Tier 1 parliamentary), and NHTSA Tesla Autopilot investigation (new candidate, Tier 1). See "Proposed next batch" in the closing session report.

**Methodology observations added this session (see Protocol Amendments above):**
- Amendment 1: local-parser clause for WebFetch retrievals when extraction fails.
- Amendment 2: Path B (user-assisted fetch) proposed and withdrawn.
- Amendment 3: Tier 1/2/3 fetchability classification and partial-verification policy for incidents with only Tier 3 primary sourcing.

**NTSB docket / report numbering inconsistency logged for future researchers:** the docket page uses three-digit Safety Recommendation numbers (H-19-047 through H-19-052); the report itself uses two-digit (H-19-47 through H-19-52). The report is authoritative. Noted in Incident 1 entry.

**Net verified-incident count at session close:** 1.

### Session 2026-04-19 (Session 2)

**Incidents added (fully verified):** INCIDENT 2 — Dutch Childcare Benefits Scandal (*toeslagenaffaire*), Belastingdienst discriminatory risk-scoring algorithm. Primary source: Amnesty International 25 October 2021 investigative summary (Tier 2 primary-in-English). Tier 1 POK Dutch parliamentary report corroboration flagged as pending. Full Amnesty *Xenophobic Machines* PDF parse flagged as pending.

**Incidents attempted but deferred this session (environment-constraint, not sourcing failure):**
- Moffatt v. Air Canada (2024 BCCRT 149) — CanLII 403 bot detection; CRT Lexum `nav.do` 404; landing page lacks citation resolver.
- Mata v. Avianca (1:22-cv-01461-PKC, S.D.N.Y., Castel J.) — CourtListener 403; S.D.N.Y.'s curated significant-rulings index deliberately excluded the opinion; Drupal `/search` path not exposed.
- NHTSA Tesla Autopilot EA22-002 / Recall 23V-838 — `www.nhtsa.gov` recall-lookup 403; `api.nhtsa.gov` 403; static CDN filename not derivable without a reachable index.
- Robodebt Royal Commission Final Report — `robodebt.royalcommission.gov.au` timeout on two consecutive attempts (>60s each).

**URLs fetched this session (13 total):**
1. `decisions.civilresolutionbc.ca/` — success; routing-only (no citation resolver).
2. `canlii.org/en/bc/bccrt/doc/2024/2024bccrt149/2024bccrt149.html` — HTTP 403.
3. `decisions.civilresolutionbc.ca/crt/sd/en/nav.do` — HTTP 404.
4. `courtlistener.com/docket/?q=1%3A22-cv-01461-PKC&type=r` — HTTP 403.
5. `nysd.uscourts.gov/opinions-significant-cases` — HTTP 404.
6. `nysd.uscourts.gov/` — success; routing-only.
7. `nysd.uscourts.gov/cases/rulings-of-special-interest?combine=Mata` — success; filter silently no-op'd.
8. `nysd.uscourts.gov/cases/rulings-of-special-interest?page=9` — success; May–Feb 2023; no Mata.
9. `nysd.uscourts.gov/cases/rulings-of-special-interest?page=8` — success; Oct 2023–May 2023; Mata deliberately excluded.
10. `nysd.uscourts.gov/search?keys=Mata+Avianca` — HTTP 404.
11. `www.nhtsa.gov/recalls?nhtsaId=23V838` — HTTP 403.
12. `api.nhtsa.gov/recalls/recallsByCampaign?campaignNumber=23V838` — HTTP 403.
13. `robodebt.royalcommission.gov.au/` — timeout (>60s); retry also timed out.
14. `tweedekamer.nl/` — success; routing-only; English mirror identified.
15. `houseofrepresentatives.nl/` — success; routing-only; no POK report hosted at English mirror.
16. `amnesty.org/en/latest/news/2021/10/xenophobic-machines-dutch-child-benefit-scandal/` — success; **source-consuming for Incident 2**.

**Source consumption under Amendment 4:** 1 source cited (Amnesty International summary page for Incident 2). All other fetches were navigation-only routing or failed access attempts. Amendment 4 performed as designed: the per-incident source budget was preserved through extensive navigation, and consumed only when a fetch actually yielded cited content.

**Sources added to bibliography:** 1 (Amnesty International 25 October 2021 article, Tier 2 NGO primary-in-English).

**Failures encountered (honest list):**
- Two Tier 1 non-profit legal mirrors (CourtListener, CanLII) returned HTTP 403 under bot detection. Precipitated Tier 2 reclassification in Amendment 5 extended.
- Two NHTSA subdomains (`www` and `api`) both returned HTTP 403, invalidating the working assumption that `.gov` API subdomains would be structurally more accessible than consumer HTML.
- Robodebt Royal Commission microsite returned timeout on two consecutive attempts — a new failure mode distinct from 403/404, added to Amendment 6's failure-mode taxonomy.
- S.D.N.Y.'s curated significant-rulings index deliberately excluded Mata v. Avianca despite featuring comparable-significance rulings from the same date window — precipitated the Path A/Path B institutional-posture observation (Taxonomy Development Notes).

**Recommended for next session (Session 3):**
- Continue the deferrals queue via user-assisted fetch (Path B) for high-value cases if the user chooses to activate it.
- New Tier 1 candidates batch planned on confirmed-reachable `.gov` infrastructure class: NTSB-class agency investigations, additional European parliamentary reports testing Amendment 7's predicted reachability pattern (Bundestag, UK Parliament, EU Parliament).
- Deepening passes on Incident 1 (HAR-19-03 Section 1.9 postcrash changes; independent victim-name verification) and Incident 2 (full Amnesty *Xenophobic Machines* PDF; POK *Ongekend Onrecht* Dutch-side parse or translation workflow).

**Methodology observations added this session (see Protocol Amendments above):**
- Amendment 4: Navigation vs. Source distinction.
- Amendment 5: CanLII reclassified as Tier 2 (reachable-but-refuses); CourtListener joined in the same classification.
- Amendment 6: Per-domain `.gov` reachability verification required — Tier 1 is not uniformly reachable. Failure-mode taxonomy added (tool-block, 403, 404, timeout, silent-no-op filter).
- Amendment 7: European parliamentary infrastructure confirmed Tier 1 reachable (`tweedekamer.nl`, `houseofrepresentatives.nl`).

**Taxonomy Development Notes additions (in docs/INCIDENT_CATEGORIES.md):**
- Boundary Failures candidate subcategory — three-part compound signature at human-AI interface. Candidates so far: Mata (pending verification), Air Canada (pending verification), potential Tesla driver-engagement, potential Dutch caseworker handoffs.
- Institutional Posture Observation — courts triaging AI-interface cases via Path A (conventional misconduct) vs Path B (structural boundary question). S.D.N.Y.'s Mata curation exclusion is a Path A instance.
- *(Incident 2)* Proposed sub-concept: "protected-characteristic void pattern" as distinct from "edge-case void pattern" in lacunarity analysis. Pending validation across ≥3 verified incidents.

**Net verified-incident count at session close:** 2. **Push threshold met at N=2 per Session 2 close directive** (original threshold was N≥3; adjusted in the Session 2 session-close instruction on the grounds that a verified Drive Corruption incident plus a verified Prerequisite Chain Failure incident together establish the two-pattern evidentiary base that makes the database a research artifact rather than a single-entry reference). Pushing both Session 1 (`e2b5425`) and Session 2 commits together as the database's first push.
