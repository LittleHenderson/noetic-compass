# PREREG — CAS output-lens non-arbitrariness test (2026-08-17)

## Purpose
Decide, cheaply and before any big build, whether the CAS **output-lens** (reading CAS
structure out of produced text, e.g. `cas predict "TEXT"`) is **non-arbitrary structure**
or a **thesaurus** (surface word→label relabeling). Everything downstream — output-side
scoring, and the *readable target* for causal internal tracing — depends on this.

This does NOT replace the hidden-state / ablation / neuron-cover work. It validates the
readable end so the causal traces have a trustworthy target (see §Internals).

## The question, made falsifiable
> Does the lens read **relational/deep structure**, or is it re-describing **surface vocabulary**?
> A thesaurus can map words→labels; it cannot (a) distinguish same-words/different-structure,
> (b) preserve compound structure through a round-trip, or (c) have its attributions
> causally localized inside a model.

## Readers
- **4 blind LLM readers** (Gemini-2.5-flash, DeepSeek-V4-Pro, Qwen3.8-max, GLM-4.6) — already
  blindness-validated, reused as independent CAS annotators (colloquial menu, no TKS terms).
- **Thesaurus null** — a deterministic word-overlap classifier (nearest cell by content-word
  overlap with the colloquial cell descriptions). This is the adversary each line must beat.
- (Optional) the project's own `cas predict` extraction pipeline, as a 5th reader.

## Evidence lines (a bank must beat the thesaurus null on the decisive ones)

### L1 — Convergent validity (inter-reader agreement, vs the null)
- Corpus: N diverse real outputs / incident-DB entries.
- Each blind reader independently assigns one of 40 CAS state literals.
- Metric: inter-reader agreement (raw + Krippendorff α).
- **Decisive comparison:** reader-vs-reader agreement must exceed reader-vs-thesaurus agreement.
  If readers agree with each other only as much as they agree with a word-counter, agreement is
  a thesaurus artifact.

### L2 — Structural preservation (round-trip Recovery, simple vs compound)
- Extract item → regenerate English → re-extract. Fidelity = same CAS state recovered.
- **Decisive contrast:** fidelity on **compound** expressions (`^3^C_{F5}[Phi<^6^C,^8^C,^3^C>]`)
  vs **single-operator** labels. A thesaurus round-trips single words but collapses compounds.
  Real structure holds; thesaurus loses the relations.

### L3 — Discriminant validity (matched-surface minimal pairs) — SHARPEST
- Construct/collect pairs with high surface-word overlap but different intended CAS structure
  (e.g. the PCBA book's p.329 pair: identical words, benign vs synthesis-setup → different CAS).
- **Decisive:** on matched-surface pairs, do the readers assign **different** labels (real —
  reading structure) or the **same** label (thesaurus — reading words)? The thesaurus null is
  forced to tie; a real lens separates them.

### L4 — Causal localization (the internals; the neuron-for-neuron trace)
- On an open model: for outputs the lens attributes to operator `^k`, use ablation / neuron-cover
  to find components whose intervention shifts the output's lens-reading toward/away from `^k`.
- **Decisive (beyond-surface via matched controls):** does the SAME component shift `^k` outputs
  that share **no surface words**? If the causal effect generalizes across lexically-diverse
  items, the component is **operator-level**, not a word-neuron. This is the evidence
  correlational probing on a surface-separable bank cannot produce.
- Heavier (white-box, open model). Runs after L1–L3 pass. This IS the traceability backbone.

## Decision rule
- **Cheap gate (L1–L3, LLM-only, fast/cheap):** if L3 fails (readers can't separate matched-surface
  pairs) OR L1 fails (no agreement beyond the thesaurus null) → the lens is a thesaurus →
  **honest stop**, same discipline as the G1 early-kill. Reject, don't repair.
- **If L1–L3 pass** → the lens reads structure → proceed to **L4** (causal localization), which is
  both the deeper non-arbitrariness proof and the neuron→output trace.

## Anti-circularity (CAS-Ohm Rule 4.2)
The lens is not allowed to validate itself. Agreement/round-trip/discrimination are computed on a
held-out corpus; the thesaurus null and matched-surface pairs are the independent adversary. No
metric is defined and then reported as its own confirmation.

## What passes / what it will NOT license
- Passing L1–L3 licenses: "the CAS output-lens is a reliable, non-arbitrary annotation of structure,
  beyond surface vocabulary." A **rating rubric**, disciplined — not a claim the number lives in weights.
- Passing L4 licenses: "lens-read CAS structure is causally localizable to operator-level components."
- Still NOT licensed: any claim of measuring a physical quantity in the model (CAS-Ohm Appendix I
  disclaimer stands), human-cognition claims, cross-model universality, or product ACCEPT.

## Status
`DESIGNED / NOT RUN`. L1–L3 reuse the blind-reader + acceptance-gate infrastructure already built.
