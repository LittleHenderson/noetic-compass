# RESULT — Track A independent-bank pilot: REJECTED at G1 (surface separability)

**Date:** 2026-08-17
**Verdict:** `REJECT — bank fails one or more gates; do not use` (per `INDEPENDENT_BANK_SPECIFICATION.md` §4, reject-not-repair).
**Cost:** authoring stage only (640 items, 4 API authors). The R6 labelling stage was **not run** — the G1 early-kill stopped before that spend.

## What was run

- **Authors (all confirmed blind, see `blindness_summary.json` + `bp_gemini.json`):** Gemini-2.5-flash, DeepSeek-V4-Pro, Qwen3.8-max, GLM-4.6.
- **Generation:** per-world (documented deviation from the frozen all-40-in-one template, to fix truncation). `pilot_author.py --items-per-cell 4`.
- **Result:** 640 unique scenarios, **exactly 16/cell across all 40 cells**, 160 per author. `pilot_raw.jsonl`.
- **Gate:** `acceptance_gate.py` on the author labels. Report: `pilot_raw_gate_report.json`.

## Gate results

| Gate | Result | Numbers |
|---|---|---|
| **G1 surface separability** | **FAIL** | char-ngram TF-IDF **0.4781**, word-unigram **0.4172** (bar ≤ 0.10, chance 0.025); length 0.0328 PASS |
| G2 vocabulary overlap | PASS | TKS 0.0217, CAS 0.0282, asymmetry 1.30, ceiling PASS |
| G3 inter-rater | FAIL* | 0.0 — *artifact:* gate mis-fires on pre-labelling data (author_id present + all rows unique); labelling never ran |
| G4 admissibility | PASS | 640 total / 640 unique / 0 dup / 40 labels |
| G5 coverage | PASS | 40/40 cells, 16–16 items/cell |

## Interpretation (honest)

- **The decisive failure is G1.** A bag-of-words classifier predicts the concept ~42–48% of the time (chance 2.5%). The scenarios are trivially surface-separable: "spiritual" items say *sacred / contemplation / interconnectedness*; "physical" items say *calloused / tangible / physical*; "mental" items say *assumptions / systematically / critically*. The concept is carried in the surface vocabulary.
- **This reproduces the historical deadlock** (bag-of-words 0.4851) that killed instruments v1–v5b. The AI-mediated independent bank was the proposed *escape* from that deadlock. **It does not escape it.**
- **What blind authorship DID solve:** G2. Overlap with both definition sets is ~0.02 and symmetric — the scenarios do not parrot TKS or compact-CAS wording. So blindness removed **definition-leakage**, but not **scenario surface-separability**, because the 40 concepts carry topical vocabulary that even blind authors emit. (The colloquial prompts themselves use realm words — "physical", "spiritual" — which authors echo.)
- **G3's 0.0 is not a real inter-rater failure.** Labelling was never run; the number is an artifact of the gate's G3 logic on single-rater rows.

## Options (each needs fresh owner sign-off; none is a repair of this bank)

- **A. Accept + record the negative result** (disciplined default). Track A, naive colloquial construction, does not break the surface deadlock.
- **B. Surface-controlled redesign** (new pre-registration): strip realm/concept vocabulary from prompts, forbid concept-typical words, matched minimal pairs — attempt to push G1 down. High effort, uncertain, risks artificiality.
- **C. Redesign the experiment** (new pre-registration): difference-in-differences that tolerates surface-separability (does TKS beat the surface floor by MORE than CAS?) instead of requiring G1 ≤ 0.10. Different design and threshold — must be pre-registered, not a silent change.

## Scope of this result

Applies to the **Gate 2 semantic** route via an independent bank. Does **not** affect Gate 1 (already confirmed on real Pythia) or the novel-capability confirmation track (RunPod). The blindness validation of the 4 authors stands and is reusable.
