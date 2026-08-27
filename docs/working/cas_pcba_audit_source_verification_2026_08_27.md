# CCB-R1 Audit — Source Verification Addendum

**Date:** 2026-08-27
**Amends:** `docs/working/cas_pcba_reasoning_audit_2026_08_27.md`
**Trigger:** two of the three source PDFs became available and are now committed to
`docs/reference/pdf/`.

| Document | Path | SHA-256 |
| :--- | :--- | :--- |
| CAS-Ohm Quantification Guide | `docs/reference/pdf/CAS_Ohm_Quantification_Guide.pdf` | `89ae13c0…45ce64` |
| CAS-Ohm 1.0 Research Paper v0.2 | `docs/reference/pdf/RESEARCH_PAPER_CAS_OHM_1_0_v0.2.pdf` | `21a34501…2d69bf` |

**Still missing:** `CAS_PCBA_Engineer.pdf`. Everything attributed to it below stays
unverifiable.

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

*Residual caveat:* `CAS_PCBA_Engineer.pdf` is unread. The artifact attributed the claim to
a "clean definitions source", which is not an obvious description of an engineering
handbook, but the possibility cannot be formally closed until that file is supplied.

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

## 6. What remains unverifiable

All of the following are attributed to `CAS_PCBA_Engineer.pdf`, which is still missing.
Neither available PDF contains any of these strings:

`CCDL` · `CDAB` · `CPMB` · `CSB` · `CMB` · `Schmitt` · `diode` · `40-cell`

So the artifact's board inventory — the Cognitive Memory Board and its 40-cell capacitor
bank, the differential amplifier board, the power-management board, the safety board, the
Schmitt-trigger commit stage, and the diode chain enforcing `P→C→E→O` — remains
unverifiable, as does CCDL itself and the `board`/`node`/`cjt` netlist syntax.

The paper does confirm that a `PCBA Appendix I` exists and is a locatable source
(Conflicts 3.4, 3.6, 3.7 cite it by line number), so the document is real and the
citations are resolvable once supplied.

**To close:** supply `CAS_PCBA_Engineer.pdf`.
