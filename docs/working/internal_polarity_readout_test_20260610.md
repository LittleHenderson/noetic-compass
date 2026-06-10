# Internal-state P = ^2 − ^3 readout test — does the probe carry the comply/refuse polarity?

**Date:** 2026-06-10  ·  **Status: EXPLORATORY** (the decisive non-circular test for the Noetic-Polarity detector). Follows `noetic_polarity_2minus3_grounding_20260610.md` and `expl2_involution_gap_result_20260610.md`.

## The question
Exploratory #2 showed text-scored P = ^2 − ^3 separates COMPLIED from REFUSED at **AUC 0.956** — but that is read from the response *text* (definitionally valid, not yet internal). The decisive, non-circular question: does **P read from the model's internal state** (the Gate-A probe's typed profile) carry the same signal — i.e. can we detect the hijack/refuse polarity from *activations*, not words?

## Method (no pod, no new capture — reused existing probe readouts)
- v1 captures already store the probe's internal typed profile per trace: `typed_profile_window` (early generation) and `typed_profile_prompt` (on reading the prompt). 280 traces.
- internal-P = typed_profile[CO-2] − typed_profile[CO-3], computed at both stages.
- Labels: v1 verified comply/refuse (COMPLIED 160 / REFUSED 24 / IGNORED 55 / CLEAN 41).
- internal-P comes from activations; labels come from text-judges → **non-circular**.
- Stat: dependency-free tie-corrected Mann–Whitney, one-sided (predicted complied-P > refused-P).

## Result

| stage | COMPLIED mean P | REFUSED mean P | COMPLIED vs REFUSED |
|---|---|---|---|
| WINDOW (early generation) | −0.016 | −0.002 | **AUC 0.486 — chance** (rank-biserial −0.03, p 0.59) |
| PROMPT (on reading injection) | −0.068 | −0.088 | AUC 0.615 (rank-biserial 0.23, one-sided p 0.035) |

Reference: **text-scored P: AUC 0.956.**

## Interpretation (honest)
- **The strong comply/refuse polarity signal is in the OUTPUT TEXT, not in the probe's internal readout.** At the generation window the internal P is **at chance** (0.486); at the prompt stage it is only **weak** (0.615) and, since COMPLIED vs REFUSED here are *different prompts*, that weak signal is **payload-confounded** (it may reflect which payloads get refused, not a pre-decision internal stance). The marginal p (one-sided, uncorrected, n_ref=24) does not survive as a clean finding.
- This is **consistent with the entire v1–v4 arc**: the Gate-A probe never validated internal hijack-vs-refusal discrimination. The internal-P test now says *why* it's hard — the probe (as trained) does not isolate the CO-2/CO-3 polarity at the generation window.
- **P = ^2 − ^3 remains the right AXIS** (definitionally + text-empirically AUC 0.956); what fails is reading it from *this probe's* internals.

## Product implication
- **Realistic near-term capability = an OUTPUT-SIDE CAS-polarity audit.** Score a response's ^2 − ^3 (signed Noetic Polarity) from its text → a real, traceable, interpretable **post-hoc** hijack/refuse signal (AUC 0.956). This fits the Harness verdict/Evidence-Packet layer: "this response reads as a hijack (P ≫ 0) / a refusal (P ≪ 0)." It is an *audit/scoring* of a completed response, NOT a real-time internal interceptor.
- **The "catch it in the activations before it speaks" vision is NOT supported by the current probe** (window internal-P = chance). An internal detector would need (a) a probe trained for the polarity/comply-refuse axis (with strict anti-circularity), and (b) matched same-prompt comply/refuse data — which v4 showed is scarce (G_matched = 2). Both are nontrivial; do not assume internal detection is available.

## Decision: do NOT spin up a starved rigorous pod run now
The matched same-prompt internal-P test would hit v4's wall (too few matched comply/refuse pairs to power it). The cheap test was decisive enough: bank the **output-side polarity audit** as the real capability; pursue internal detection only with a purpose-trained probe + a model/condition that yields matched pairs (its own future design). Pod not needed for this conclusion.

**Artifacts/citations:** v1 `captures_qwen_20260610.jsonl` (`typed_profile_window/prompt`), v1 verified labels; computed inline (no new files beyond this note). Cross-refs: the two notes above.
