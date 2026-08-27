# CCB-R1 Audit — Source Verification Addendum

**Date:** 2026-08-27
**Amends:** `docs/working/cas_pcba_reasoning_audit_2026_08_27.md`
**Trigger:** two of the three source PDFs became available and are now committed to
`docs/reference/pdf/`.

| Document | Path | SHA-256 |
| :--- | :--- | :--- |
| CAS-Ohm Quantification Guide | `docs/reference/pdf/CAS_Ohm_Quantification_Guide.pdf` | `89ae13c0…45ce64` |
| CAS-Ohm 1.0 Research Paper v0.2 | `docs/reference/pdf/RESEARCH_PAPER_CAS_OHM_1_0_v0.2.pdf` | `21a34501…2d69bf` |
| CAS PCBA Engineer (supplied as .docx) | `docs/reference/pdf/CAS_PCBA_Engineer.docx` | `018b5c5d…30ed3` |

**All three sources are now in the repository.** Nothing in the CCB-R1 audit remains
unverifiable for want of a source. See §7.

---

## 1. The `A22` finding is upgraded: UNVERIFIABLE → CONTRADICTED

The audited artifact claimed:

> *"one TKS source names the root Pure Desire `A0`, while the clean definitions source uses `A22` for the global Meta-Desire"*

and made resolving it the first item of its Gate 1.

The token `A22` occurs **exactly once** across both newly available documents, and it is
not a symbol. It is a substring of a SHA-256 digest in the research paper's Gate 4 receipt:

```
2E81A685961286D944894A22EB93345B97211B4433B6C71EAF628D84CD8EB1EF
                 ^^^^^^
```

Tally across every source now readable:

| Source | `A22` as a symbol |
| :--- | :--- |
| TKS Formal Manual v6.1 | 0 |
| TKS v7.4 Full Corrected | 0 |
| TKS Full Cognitive Framework | 0 |
| TKS v7.4 Referee Defensible | 0 |
| CAS-Ohm Quantification Guide | 0 |
| CAS-Ohm Research Paper v0.2 | 0 (one hex-substring false positive) |

Neither CAS-Ohm document mentions `A0`, "Pure Desire", or "Meta-Desire" at all. The only
definition anywhere remains TKS Definition 2.14: `A = {A0} ∪ {Dm} ∪ {Wm} ∪ {Pm}`,
`|A| = 22`, `A0: Pure Desire (root intentional vector)`.

**Conclusion.** No source available to this project supports the claimed `A0`/`A22`
conflict. The most probable origin is a misreading of the cardinality `|A| = 22` as a
symbol name. `A0` is canonical; the Gate 1 item should be struck, not resolved.

**Residual caveat now closed.** `CAS_PCBA_Engineer` has since been supplied (1.1 M
characters of extracted text). `A22` occurs **zero** times in it. `A0` occurs four times,
always as the canonical root of the prerequisite chain — e.g. *"A0 → Dₙ → Wₙ → Pₙ →
Outcome, each stage requiring the one before it."* The handbook even notes its own gap
here: *"Chapter 8 introduces the RPM chain as A0 → Dₙ → Wₙ → Pₙ → Outcome and never says
what the letters stand for."*

Final tally of `A22`-as-a-symbol across **all seven** readable sources: **zero.** The
finding is closed. `A0` is canonical and the Gate 1 item is struck.

---

## 2. Three citations previously unverifiable are now CONFIRMED — two nearly verbatim

The audit could not check the artifact's page-anchored citations. All three hold.

**Page 13 — the cascade.** The artifact described *"Understanding → Evaluation → Response,
with the effect of one CJT becoming the cause of the next … each stage has local Drive,
constraint, attention, bias, and gain. Gains may multiply, but the local flow must be
probed separately at every stage."*

Guide p. 13 reads: *"A three-stage understanding → evaluation → response cascade. Each
stage can have a local Drive, constraint, attention reading, bias, and gain."*;
*"Effect state from each stage becomes the next stage's cause."*;
`β_total = β₁ × β₂ × β₃`; *"Probe each stage whose failure would otherwise be silent."*
**Accurate, close to verbatim.**

**Page 14 — the nested-CJT rule.** This was flagged in the audit as *"the least hedged and
least corroborated of the three"* and the sole warrant for the artifact's Law 5. It is in
fact the best corroborated. Guide p. 14: *"compute the parent equivalent for overview, but
never discard the child readings. A healthy parent total can hide one overloaded branch
and one starved branch that cancel numerically."* The artifact's Law 5 restates this
almost word for word. **Confirmed.**

**Page 15 — the RPM tree.** Guide p. 15: *"Prime Desire / target Foundation"*,
*"Scan D → W → P"*, *"First block: Wisdom"*, *"Formulate a sub-desire"*,
*"Recurse → act → re-measure → ascend"*, *"Execute a Noetic action, re-measure, then return
to the parent goal."* The artifact's §9 worked example (`D7` strong, `W7` partial,
`P7` partial, first block `W7`) follows the source's own pattern. **Confirmed.**

**The paper's disclaimers.** Verbatim from the abstract: *"It is not physical Ohm's law, an
electrical implementation, a measure of attention, or a causal law."* All four, exactly as
the artifact reported. Also confirmed: the circular same-sample identity is *"rejected as
circular"*; network operations are *"capability-gated"*; residuals are *"non-identifying"*.
**Confirmed.**

---

## 3. A methodological correction: string-absence is not claim-absence

Searching both PDFs for `"unity gain"` and `"unity-gain"` returns **zero hits**, which on a
naive reading would mark the artifact's central safety claim unsupported.

It is supported. Guide p. 13 expresses it numerically: the three-stage cascade runs
`β₁=2.0` (Understanding), **`β₂=1.0` (Evaluation)**, `β₃=1.5` (Response). The evaluation
stage is the unity-gain stage in the source's own worked example.

This is worth recording as a rule for the remaining verification work: a claim can be
faithfully sourced to a diagram that never uses the claim's vocabulary. Term-frequency
sweeps are a triage tool, not a verdict.

---

## 4. New finding: an eight-conflict source registry already exists, and the artifact never cites it

The research paper reproduces a **machine-readable source audit** —
`CAS_OHM_SOURCE_CONFLICT_EVIDENCE_v0.1.json` — registering eight conflicts across the
Quantification Guide, the operationalization addendum, and PCBA Appendix I, *"each with
source locators, the conflicting facts, and its binding candidate rule"*, and states that
*"none is silently harmonized."*

Preserved Conflicts 3.1–3.8: scale/saturation; full-scale profile; the dimensional bridge;
**gain definition**; ASOM axis overload; **network rules**; residual identification;
Q4 boundaries.

Two of these sit directly under the artifact's design:

- **Conflict 3.6 (Network rules; validation-status conflict)** is located at *Guide pp. 13–…*
  — the exact pages the artifact builds its CJT cascade on. The paper's resolution is that
  series, parallel, and gain-product operations exist only as capability-gated structural
  operations. The artifact reported that restriction correctly, but did not flag that its
  own architectural foundation rests on a formally preserved conflict.
- **Conflict 3.4 (Gain definition; distinct mathematical profiles)** is located in PCBA.
  The `β` semantics the artifact's truth firewall depends on are themselves an open
  conflict in the source corpus.

**Consequence for Gate 1.** The artifact's "Freeze the ontology" gate lists conflicts to
resolve as though none had been catalogued. A curated, locator-bearing, machine-readable
registry already exists. Gate 1 should begin by loading
`CAS_OHM_SOURCE_CONFLICT_EVIDENCE_v0.1.json` and closing its eight entries — not by
enumerating conflicts from scratch. This is the same "reinvents what already ships" pattern
the original audit found in §12, appearing on the source-document side.

---

## 5. Provenance flag: the Quantification Guide is built on the manual we just archived

Both `SOURCE` attributions in the guide cite **TKS Formal Manual v6.1**:

- p. 11 (D/W/P face-card states): *"TKS Formal Manual v6.1, Section 6.5."*
- p. 15 (RPM tree): *"TKS Formal Manual v6.1, RPM Sections 7.1–7.7."*

That is the manual archived to `docs/archive/superseded/` under Clarification 11's C3, for
carrying inverted `^5`/`^6`, `^2`/`^3` denoting Above/Below, and pre-v7.4 Foundation labels.

This does **not** invalidate the guide's RPM content — RPM sections 7.1–7.7 are not
obviously touched by the Noetic-numbering inversion. But it means the CAS-Ohm layer
inherits a v6.1 foundation, and any future reconciliation of the guide against v7.4 must
check RPM and the D/W/P face-card states specifically. Recorded so the archive decision
does not silently orphan the documents that depend on the archived manual.

---

## 6. Section 6 superseded — the board inventory is CONFIRMED

*The original §6 listed the board inventory as unverifiable. `CAS_PCBA_Engineer` has since
been supplied and every term is present, most of them heavily.*

| Term | Occurrences | Status |
| :--- | ---: | :--- |
| `CCDL` | 196 | ✅ real language |
| `diode` | 185 | ✅ |
| `CSB` (Cognitive Safety Board) | 165 | ✅ |
| `CPMB` (Power Management Board) | 72 | ✅ |
| `COB` (Oscillator Board) | 48 | ✅ |
| `CDAB` (Differential Amplifier Board) | 46 | ✅ |
| `Schmitt` | 45 | ✅ |
| `CMB` (Cognitive Memory Board) | 33 | ✅ |
| `unity gain` / `unity-gain` | 16 | ✅ |
| `40-cell` | 4 | ✅ |
| `Appendix I` | 13 | ✅ |
| `board` / `probe` / `feedback` | 552 / 250 / 346 | ✅ netlist vocabulary |

**The artifact's source fidelity to the handbook is vindicated.** Specific confirmations:

- **Unity gain, verbatim:** *"β = 1 — unity gain"*, and the load-bearing gloss
  *"A unity-gain follower carries the principle across the domain boundary without
  amplifying or inverting it — it preserves the content and changes only…"* The artifact's
  truth-firewall reading is faithful to the source.
- **The 40-cell CMB is real and typed:** *"The Capacitor Bank: A 40-Cell Memory Array"*,
  with cells declared in CCDL as `Capacitor< ^2^E_{F4}|f, C=120, leakage=… >` and
  `Capacitor< ^3^P_{F7}|f, C=200, … >`.
  **This closes audit finding #5 in the source's favour, not the artifact's:** the CMB's
  40 cells *are* addressed by CAS state literals carrying Domain and Register, so the
  memory board already maps onto the 40 Cognitive States. The artifact used the CMB
  without ever making that mapping explicit — the connection to Δ39° it was faulted for
  omitting is present in its own source.
- **Correction 2 is engaged by the handbook, not by the artifact:** *"(section-retraction)
  — Prerequisite satisfaction structured as a one-directional chain (A0 → Dₙ → Wₙ → Pₙ →
  Outcome)"*, and *"The Domain Descent diode chain (P→C→E→O) and the RPM prerequisite chain
  are both expressions of the same fact."* The audit faulted the artifact for never
  engaging section-retraction; the source engages it directly.
- **The declared-gap claim is verbatim:** *"The stateful and temporal family has syntax and
  no formalized semantics."* This is the gap the test program's Stage 1 proposes to
  formalize, confirmed in the source's own words.

## 7. Nothing remains unverifiable

All three sources are in the repository. Every claim the original audit marked
unverifiable has now been checked.

**Net effect on the audit's verdict: unchanged, but the balance shifts.** The artifact's
*source fidelity* is materially better than the audit could establish — three page
citations confirmed near-verbatim, the board inventory real, unity gain real, the declared
semantics gap real, and its restraint on `|A| = 22` correct. Exactly one claim is
fabricated (`A22`), and it was load-bearing only for a Gate 1 item that should be struck.

The audit's *substantive* findings are untouched, because they never depended on the
missing sources: the §11 netlist still runs `E → C` against its own diode chain, still
wires `goal_bias` into inference, still leaves `action` an orphan; §12 still proposes a
grammar extension for objects the compiler already ships; and the Foundation-to-Drive
adapter still hand-rolls v7.6 recipe semantics. Those were all verified against this
repository, not against the PDFs.

Two findings now resolve *against* the artifact more sharply than before, because its own
source contains what it omitted: the CMB's 40 cells are already CAS-state-typed
(so the Δ39° mapping existed), and the handbook engages section-retraction explicitly
(so Correction 2 was available to it).
