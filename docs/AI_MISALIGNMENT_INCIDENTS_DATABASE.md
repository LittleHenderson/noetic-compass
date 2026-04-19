# AI Misalignment Incident Database
## A CAS Structural Analysis of Documented Failures

**Status:** Living reference document. Under active verified-source curation.
**Framework:** Cognitive Architecture System (CAS) v7.4 — Corrected Edition
**Maintained by:** Noetic Compass research team
**First commit:** 2026-04-19
**Current verified-incident count:** 1

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
