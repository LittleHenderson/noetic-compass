# Source Grounding Notes — CAS Reasoning Runtime (load-bearing design claims)

**Date:** 2026-08-28
**Status:** verification-only grounding document; creates no new source content and modifies no existing file.

## Methodology

- **Source 1 — CAS PCBA Engineer book.** Read the Markdown chapter sources `book/CAS_PCBA_Engineer/Chapter_*.md` and `Appendix_*.md` (preferred over the build-artifact PDF). "Book page" is given where the `.md` text carries an explicit page marker; otherwise location is cited as **chapter + section heading** (the `.md` sources carry no per-line page numbers).
- **Source 2 — CAS-Ohm 1.0 v0.2 research paper.** The exact `.tex` source exists at `docs/whitepapers/tex/RESEARCH_PAPER_CAS_OHM_1_0_v0.2.tex` (read in full; the PDF is a build artifact). No `.md` source exists for this paper. Locations are cited by **§section**.
- **Source 3 — CAS-Ohm Quantification Guide.** The canonical path `docs/reference/pdf/CAS_Ohm_Quantification_Guide.pdf` **does not exist in the current working tree**. It was recovered as three byte-identical copies (2,610,388 bytes) and read from `project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/03_RESEARCH_AND_ARCHITECTURE_DOCS/SUPPLIED_SOURCE_INPUTS/CAS_Ohm_Quantification_Guide-2.pdf` (18 pages), extracted with Python 3.14 + pypdf 6.10.2. **No `.md`/`.tex` source exists for the Guide.** Locations are cited by **page number**.
- **TKS confirmation only (for claim M).** `docs/reference/tks_28_foundations_translation_key.md`, `pdf_review/TKS_FULL_Cognitive_Framework.md`, `_tmp_TKS_FULL_Cognitive_Framework.txt`, `_tmp_TKS_FORMAL_MATHEMATICAL_MANUAL_v6_1_COMPLETE.txt`, `_tmp_TKS_v7_4_FULL_CORRECTED.txt`. These are used ONLY to confirm foundation names and the A0/A22 discrepancy; the three main sources take precedence.

**Status legend:** CONFIRMED (verbatim support found), PARTIAL (some but not all sub-claims found), NOT FOUND (no support; not invented).

---

## A. CJT primitive: Cause | Bias => Effect, with gain, cutoff, saturation, and operating regions

**Status:** CONFIRMED (one refinement: the source defines **four** operating regions, not three — the claim's parenthetical omits **breakdown**).

- "The component that captures all of this is the **Cognitive Junction Transistor (CJT)** — the central part of the entire book and the building block of every circuit you will design from here on. Its written form is: `CJT< cause | bias => effect > [β=2.4]`" — **Chapter 3, "Introducing the CJT".**
- "Every transistor lives in one of four **operating regions**… - **Cutoff.** … - **Active.** … - **Saturation.** … - **Breakdown.**" — **Chapter 3, "The four operating regions".**
- "Hold those four words — cutoff, active, saturation, breakdown — in your hand. We are about to find all four in a thought." — **Chapter 3, "The four operating regions".**
- "Gain has three regimes worth naming now… **β < 1 — attenuation.** … **β = 1 — unity gain.** … **β > 1 — amplification.**" — **Chapter 3, "Gain (β)".**

The Quantification Guide states the same four regions explicitly: "The source-defined CJT regions are **cutoff, active, saturation, and breakdown**." — **Quantification Guide, p. 11.**

---

## B. The 7 CAS Drive rails and inversion pairs

**Status:** CONFIRMED.

- "| `F1` | **Unity** | … | `F2` | **Wisdom** | … | `F3` | **Vitality** | … | `F4` | **Connection** | … | `F5` | **Agency** | … | `F6` | **Structure** | … | `F7` | **Purpose** |" — **Chapter 2, "The 7 Drives — Why Cognition Moves".**
- "Like the Noetics, the Drives have inversion pairs — opposing motivational poles: **F1 Unity ↔ F7 Purpose**, **F2 Wisdom ↔ F6 Structure**, **F3 Vitality ↔ F5 Agency**. **F4 Connection** is self-dual." — **Chapter 2, "The 7 Drives".**

---

## C. ^8 Above/Cause (associative triggering) vs deduction (compound ^6 Male + ^9 Below/Effect)

**Status:** CONFIRMED.

- "**`^8` Above/Cause is associative triggering, not deductive reasoning.** It's "that reminds me," "one thing leads to another" — an Idea surfacing another Idea by association. It is *not* "therefore, X follows logically." Step-by-step deduction is a compound of `^6` Male (decomposition) and `^9` Below/Effect (landing on the conclusion), not `^8`." — **Chapter 2, Bench Note under "The 10 Noetics".**
- Reinforced at the CJT terminals: "`^8` is *associative triggering*, "that reminds me," "one thing leads to another." It is the arriving stimulus, not a chain of deductive reasoning." — **Chapter 3, "Collector, Base, Emitter → Cause, Bias, Effect".**
- "`^8` is triggering, not reasoning… deductive analysis is a compound of `^6` Male and `^9` Below/Effect." — **Chapter 4, Bench Note under "Component 1".**

---

## D. Amplifier chapter: unity gain (β=1) as the honest evaluation stage

**Status:** CONFIRMED.

- "2. **Evaluation** — assess the amplified understanding against the system's principles and risk model. This stage wants *unity gain* (β=1) or close to it: it shouldn't inflate or deflate the signal, it should weigh it faithfully. A risk evaluator that amplifies its own judgment is a system that cries wolf; one that attenuates it is a system that misses real danger." — **Chapter 11, "Multi-Stage Amplifiers".**
- "At β=1 it neither inflates nor deflates the signal. The risk it finds comes out at the same magnitude it went in. That is deliberate: an evaluation stage with gain > 1 is a system that exaggerates risk; with gain < 1, one that downplays it. Unity is honesty." — **Chapter 11, "The Worked Build".**

---

## E. Schmitt trigger: two thresholds, hysteresis, no flip-flopping, routed through a CJT for a reasoned verdict

**Status:** CONFIRMED.

- "A **Schmitt trigger** fixes this with **hysteresis**: it uses *two* thresholds instead of one. The input must rise above a high threshold to switch ON, and then fall all the way below a *lower* threshold to switch back OFF. The gap between the two thresholds is a buffer zone where the output simply doesn't change." — **Chapter 10, "Schmitt Trigger — Hysteresis Comparator".**
- "In CAS, a Schmitt trigger prevents a system from **rapidly oscillating between two opposed states**… Without hysteresis, a stimulus sitting right on the boundary between `^2` attraction and `^3` aversion makes the system flip-flop…" — **Chapter 10, "Schmitt Trigger — Hysteresis Comparator".**
- "The Schmitt trigger (`stabilize`) then refuses to flip-flop… The CJT (`resolve`) takes the now-stable input and the conflict flag and produces a single reasoned verdict, `^9^E_{F2}|A`." — **Chapter 10, "Worked Build: A Schmitt Trigger That Stops the Flip-Flop".**

---

## F. RPM loop (Prime Desire → target Foundation → D→W→P scan → sub-desire → act → re-measure → return to parent)

**Status:** CONFIRMED (located in the Quantification Guide, p. 15).

- "RPM scans the D/W/P triad and recursively turns the first insufficient prerequisite into a sub-desire." — **Quantification Guide, p. 15 ("RPM TREE").**
- "1. **Define** — Name the Prime Desire and target Foundation. 2. **Scan** — Assess D, W, P with card phase, decimal score, and trend. 3. **Recurse** — The first insufficient state becomes the next goal. 4. **Act and ascend** — Execute a Noetic action, re-measure, then return to the parent goal." — **Quantification Guide, p. 15.**
- "SOURCE — TKS Formal Manual v6.1, RPM Sections 7.1–7.7." — **Quantification Guide, p. 15.**

---

## G. CMB: 40-cell bank (10 Noetics × 4 Domains), leakage, refresh, lacunae detection, structural query

**Status:** CONFIRMED.

- "the cognitive state space has a natural array size: exactly **40 Cognitive States**, being **10 Noetics × 4 Domains** (P0–P9, C0–C9, E0–E9, O0–O9)." — **Chapter 21, "The Capacitor Bank".**
- "**Structural query is Fisher-Rao nearest-neighbor.** Any query you can express as a cognitive shape… becomes a search." — **Chapter 21, "Key Takeaways".**
- "That is a **false recall** (misattribution), and it is structurally different from **lacunarity** (the memory was never stored — an empty cell, which the CMB reports directly) and from **inversion** (the memory returns as its shadow form)." — **Chapter 21, "Failure Modes".**

---

## H. CDAB: shared bias, matched gains, common-mode rejection, amplifying meaningful divergence

**Status:** CONFIRMED.

- "**Matched CJTs, shared bias.** That phrase is the whole foundation of the board." — **Chapter 20, "CMRR" section intro.**
- "The figure of merit for any differential amplifier is its **CMRR** — the **Common-Mode Rejection Ratio**. It answers one question: *how much better is this amplifier at amplifying the difference than at amplifying the shared part?*" — **Chapter 20, "CMRR".**
- "The **CDAB (CCB-3)** is the reference board for **precise comparison**: it amplifies the *difference* between two ideas, beliefs, or AI outputs and **rejects the assumptions they share** (the common mode)." — **Chapter 20, "Key Takeaways".**
- "The art is to set differential gain so a *real, meaningful* divergence between the two ideas is surfaced strongly enough to drive a decision, without inflating a trivial difference into a false dichotomy." — **Chapter 20, "Differential gain".**

---

## I. P→C→E→O domain descent; diodes enforcing direction; power sequencing (Operational last); the Analytical→Embodied joins warning

**Status:** CONFIRMED (all four sub-claims found).

- "**Domain Descent** is the normal causal flow: **P → C → E → O**. A commitment causes reasoning, which causes a judgment, which causes an action." — **Chapter 2, "The 4 Domains".**
- "The whole Domain Descent chain is therefore not one diode but a **chain of diodes**, each enforcing one seam… Three valves in series, all pointing the same way. Current — cognitive flow — can run all the way down P→C→E→O. It cannot run back up." — **Chapter 8, "The PN Junction in Cognition".**
- "Cognitive circuits have a mandatory startup order, and it is the Domain precedence order you learned in Chapter 2: **P → C → E → O**. Principled powers first, then Cognitive, then Evaluative, and Operational powers *last*." — **Chapter 14, "Power Sequencing".**
- "**The Operational domain — the domain of concrete action and output — must not come up before the Principled domain is stable.** … In safety terms it has a name — **"no action without principle"**…" — **Chapter 14, "Power Sequencing".**
- "// Bench Note — the DAC CJT must be the ONLY join between the |A rail and the |E rail, // so every crossing from analytical-discrete to embodied-continuous passes one // validated converter; multiple uncontrolled |A->|E joins would let analytical // conclusions leak into action without conversion, defeating the rail separation." — **Appendix E, Exercise 15.4 answer.**
- "**Mixed-signal grounding:** keep the analog Registers (`|f`, `|E`) and the digital Register (`|A`) on separate rails, joined at exactly one designed point — the converter. Direct bleed in either direction is a grounding fault." — **Chapter 15, "Key Takeaways".**

---

## J. CPMB: the Drive rails it manages and sequencing

**Status:** CONFIRMED.

- "the **seven Drives are seven rails**, with **F3 Vitality (+12 V)** the master supply and **F7 Purpose (+12 V)** its companion high rail powering the Principled domain." — **Chapter 22, "Key Takeaways".**
- "The **power sequencer** enforces **P→C→E→O** and holds **O low until P, C, and E all report power-good** — the "no action without principle" invariant, the core safety property of the board." — **Chapter 22, "Key Takeaways".**

---

## K. CSB: RC low-pass feedback so a single spike cannot rewrite the constitution

**Status:** CONFIRMED.

- "runs it through an **RC low-pass filter** with a time constant of **τ = 5 minutes** (Chapter 12), and uses the smoothed trend to adjust the bias — the `system_constitution`." — **Chapter 18, "The Feedback Loop".**
- "The RC filter is essential… Without it, a single unusual prompt could yank the constitution around, and an attacker could rewrite the board's principles by flooding it with crafted inputs. The low-pass filter (τ=5 min) washes out fast transients… The constitution is updated by the slow, accumulated pattern of what the board has been seeing, never by a single spike." — **Chapter 18, "The Feedback Loop".**

---

## L. CCDL grammar: state-literal coordinate slots, no sub-foundation slot, scope analysis ("17 of 39 no formal semantics")

**Status:** CONFIRMED.

**State-literal slots (four, no fifth "sub-foundation" slot):**
- "| Axis | Question it answers | Notation slot | … **Noetic** … `^0`–`^9` … **Domain** … `P C E O` … **Drive** … `_{F1}`–`_{F7}` … **Register** … `|T |A |f |E` |" — **Chapter 2, "The Four Axes".**
- Grammar: "`^Noetic ^Domain _{Drive} |Register`" — **Chapter 2, "Putting It Together".**
- "A state literal is a first-class lexical token in CCDL… Its grammar is the canonical CAS state grammar from Appendix A and Chapter 2." — **Appendix C, "Overview".**

**Scope analysis (the exact numbers are 11 / 11 / 17 of 39):**
- "**2. The stateful and temporal family has syntax and no formalized semantics.** `charge`, `discharge`, `refresh`, `scan`, `sequence`, `hold`, `on`, `force_state`, `enter` and `interrupt` all describe something happening *over time*… CCDL as this book defines it is a **declarative netlist language**. It has no execution model, no clock, and no state-transition semantics." — **Appendix C, "Scope of This Grammar".**
- "Of the thirty-nine rows, **eleven leaders have full semantics, eleven are partial, and seventeen have none** — and that last block is not a random scatter. It is almost exactly the stateful and temporal family named in limit 2 above, plus the Chapter 23 verification sub-language." — **Appendix C, "Construct Coverage Matrix".**
- Matrix rows with "Semantics formalized = **No**" include `hold`, `force_state`, `charge`, `discharge`, `decode`, `refresh`, `scan`, `interrupt`, `sequence`, `gate`, `monitor`, `on`, `enter`. — **Appendix C, "Construct Coverage Matrix".**

---

## M. The 7 Foundations / 28 Sub-Foundations / 22 acquisitions (A0 vs A22)

**Status:** PARTIAL. The three authoritative sources reference the **RPM/acquisition chain** and **D/W/P**, but **none of them states the "7 Foundations × 4 Worlds = 28 sub-foundations" or "22 acquisitions" ontology.** The full foundation names and sub-foundation notation exist only in the TKS manual / translation key.

**What the three main sources actually say:**
- "The **RPM** chain — Recovery / Prerequisite Mechanism — is how the system satisfies prerequisites: **A0 → Dₙ → Wₙ → Pₙ → Outcome**, each stage requiring the one before it." — **Book, Chapter 8, "Diodes and RPM".**
- "The letters: **D** is Desire, the motivational prerequisite; **W** is Wisdom, the know-how prerequisite; **P** is Power, the capability prerequisite." — **Book, Chapter 8, "Diodes and RPM".**
- "Prime Desire → target Foundation / goal → Scan D → W → P …" and "SOURCE — TKS Formal Manual v6.1, §6.5 … §7." — **Quantification Guide, pp. 15, 9.**
- **CAS-Ohm v0.2 paper:** no mention of Foundations, sub-foundations, or acquisitions (NOT FOUND there).

**TKS confirmation only (not a main source):**
- Foundation names (position 1–7): "F1 Unity/Association, F2 Wisdom, F3 Life, F4 Companionship, F5 Power, F6 Material/Wealth, F7 Lust/Continuation" — **`_tmp_TKS_v7_4_FULL_CORRECTED.txt` (7-Foundation table, lines ~1644–1662; also ~2248–2254).**
- 28 sub-foundations = 7 Foundations × 4 Worlds, with the World axis "a = Spiritual, b = Mental, c = Emotional, d = Physical"; "F3d denotes Physical Life" — **`_tmp_TKS_v7_4_FULL_CORRECTED.txt` (line ~2261).**
- Acquisitions "Dₘ, Wₘ, Pₘ — Desire, Wisdom, Power for Foundation m" and "ℱₘ — Foundation — Life domain (m ∈ {1,...,7})" — **`pdf_review/TKS_FULL_Cognitive_Framework.md`, Appendix B Symbol Reference.**
- **A0 vs A22:** the root/initial acquisition is written **"A0"** in the book (Chapter 8) and in `_tmp_TKS_v7_4_FULL_CORRECTED.txt`; the v6.1 manual instead uses **"A1"** ("A1: Divine Mind (First Cause Awareness)") and sub-acquisition labels like "A21b". The label **"A22"** appears **nowhere** in any checked source. The number "22" is the **count** (A0 + D1–D7 + W1–W7 + P1–P7 = 22), not an index label. The three main sources do not state "22 acquisitions" at all.

---

## N. CAS-Ohm 1.0 v0.2 paper restrictions

**Status:** CONFIRMED (all quoted from `docs/whitepapers/tex/RESEARCH_PAPER_CAS_OHM_1_0_v0.2.tex`).

- "It is *not* physical Ohm's law, an electrical implementation, a measure of attention, or a causal law." — **Abstract.**
- "This paper establishes no live execution, scientific conclusion, physical measurement, causal effect, safety or clinical conclusion, product capability, license, canon admission, or disclosure." — **§1 (Scope).**
- "series, parallel, and gain-product operations exist only as *unauthenticated structural research calculations*, each capability-gated." — **§Structural network operations.**
- "A residual can rank follow-up probes. It cannot, by sign alone, identify a hidden policy, bypass, opposition, cause, or safety failure: causal interpretation requires an explicit causal model and identifiable interventions." — **§Residuals are non-identifying.**
- "There is no admitted live calibration, held-out estimate, drift-threshold validation, or inter-rater reliability result. … History-dependent dynamics remain open." — **§Limitations.**
- "Whether the model predicts anything is exactly the question that program leaves to controlled, independently audited experiments—and nothing in this paper preempts their answer." — **§Conclusion.**

---

## O. Quantification Guide: cascade (p.13), nested-CJT test points (p.14), Measure→Diagnose→Tune→Re-test loop (p.17)

**Status:** CONFIRMED.

- "A three-stage understanding → evaluation → response cascade. Each stage can have a local Drive, constraint, attention reading, bias, and gain." — **Quantification Guide, p. 13 ("CASCADES").**
- "Recursive measurement rule: compute the parent equivalent for overview, but never discard the child readings. A healthy parent total can hide one overloaded branch and one starved branch that cancel numerically." — **Quantification Guide, p. 14 ("RECURSION").**
- "1. **Measure** V, R, I, effect. 2. **Diagnose** ASOM + residual. 3. **Tune** RPM / bias repair. 4. **Re-test** new operating point." — **Quantification Guide, p. 17 ("CLOSED LOOP").**

---

## P. COB (iteration/rhythm role) and debugging (last-good/first-bad walk-down)

**Status:** CONFIRMED.

- "Where the CSB is a *firewall* — it gates and blocks — the COB is a *clock and a tuner*. Its job is to model rhythmic and habitual cognition: to represent a habit loop as a real oscillating circuit, to diagnose when that loop has locked into a compulsive cycle, and to drive a slow, controlled shift of the cycle to a healthier rate." — **Chapter 19, intro.**
- "The **master clock** is **`^7` Rhythm** — *"the rate and pattern a Mind is exposed to an Idea, entraining/conditioning it."*" — **Chapter 19, "Stage 1".**
- "She picks up a probe… walking the signal forward one stage at a time — until she touches a point where the reading is wrong… between the last good reading and the first bad one." — **Chapter 24, intro.**
- "It has a name on the electronics bench: the **oscilloscope walk-down** — probe the stages in order, find where the signal first deviates from what it should be, and the fault is right there." — **Chapter 24, intro.**
- "**The walk-down is the core technique.** Probe TP1 → TP2 → TP3 → TP4 in signal order; stop at the *first* test point where measured disagrees with expected." — **Chapter 24, "Key Takeaways".**

---

## Q. Evidence packet / CAS trace as the structural story of a decision

**Status:** CONFIRMED — it is **Chapter 25 (Production Deployment)**, "The Evidence Packet" section.

- "| `cas_trace` | The CAS state at each stage: `expanded_prompt`, `attraction`, `aversion`, `risk_signal`, the three cascade nodes, `safety_decision`. | The structural story of *how* the decision formed, stage by stage. |" — **Chapter 25, "The Evidence Packet".**
- "The whole book has one thesis you can say in seven words: **show your work, or don't ship it.**" — **Chapter 25, intro.**
- "The chain runs unbroken from a user's prompt, through the CAS trace, to the exact signed board that produced the decision — show-your-work, all the way down." — **Chapter 25, "The Circuit Registry".**

---

## GAPS — design elements the three authoritative sources do NOT cover

Stated plainly, for the proposed CAS Reasoning Runtime:

1. **No native sub-foundation (e.g. "5b") slot in CCDL.** The state literal has exactly four coordinate slots — Noetic, Domain, Drive, Register — and no fifth slot for a TKS sub-foundation. The TKS sub-foundation notation (F2b, "2c = Emotional Wisdom", "6d = Material Resources") exists only in the TKS manual, never in the book/CCDL.
2. **No runtime / scheduler semantics.** CCDL is a declarative netlist language with "no execution model, no clock, and no state-transition semantics" (Appendix C). The 17 no-semantics leaders — `hold`, `force_state`, `charge`, `discharge`, `decode`, `refresh`, `scan`, `interrupt`, `sequence`, `gate`, `monitor`, `on`, `enter`, plus the Chapter 23 test sub-language — have syntax but no checkable meaning.
3. **No full 28-foundation ontology in these docs.** The three authoritative sources do not state "7 Foundations", "28 sub-foundations", or "22 acquisitions". Only the RPM chain `A0 → D → W → P → Outcome` and the D/W/P letters appear (Book Ch. 8; QG pp. 9/15). Foundation names/sub-foundations live only in the TKS manual and translation key.
4. **"A22" label not found.** The root acquisition is "A0" (Book Ch. 8; TKS v7.4); v6.1 uses "A1". "A22" appears nowhere; "22" is a count, not an index. Any "A22" in the runtime design is unsourced.
5. **No live calibration or measured telemetry.** The CAS-Ohm paper: "There is no admitted live calibration…"; the book's repeated honesty notes ("design choices, not measured results") confirm nothing is an empirical run.
6. **No causal or safety authority.** CAS-Ohm v0.2: residuals "cannot, by sign alone, identify" a cause; eligibility for authenticated Evidence Packets is "always false in this candidate."
7. **CJT region count.** The runtime claim's three-region list (active/cutoff/saturation) omits the fourth, **breakdown** (Book Ch. 3; QG p. 11), where the output flips to its involution Noetic pair.
8. **Foundations/acquisitions are only ever the RPM chain in the main sources** — there is no main-source statement of the 7/28/22 ontology to bind a runtime data model to.

---

*End of grounding notes. Quotes are verbatim from the listed sources; "NOT FOUND" is reported rather than inferred where a source is silent.*
