# CAS Harness MTC — 28 Foundations vs GoEmotions-28 — Preregistration & Run Spec

**Date:** 2026-06-15
**Status:** DRAFT PREREG — must be frozen + WORM-anchored *before* any GPU activation capture (Gate 3).
**Model under test:** GPT-NeoX-20B (real open weights, 44 layers).
**Supersedes failure modes of:** MTC v1 (text-leak null), MTC v2 / dual-labeled F28 pilot (meaning-stripped null — **quarantined**, prereg amendment A1.1, must not be cited as a result).

---

## 0. What this run does and does NOT decide

- **Tests:** whether GPT-NeoX-20B's hidden states encode CAS's 28-Foundation partition (a) at all (linear decodability) and (b) **more cleanly than an established 28-class human-meaning taxonomy** (GoEmotions), under leakage control.
- **Does NOT test:** whether CAS is true, useful, or human-meaningful. CAS meaning stayed 100% human-recoverable on Condition-3; this is a per-model, per-fixture, linear-probe question only.
- **Honest prior (preregistered so it can't be reinterpreted later):** given Condition-3 (CAS-F28 recovered at ~chance), the **most likely outcome is BLOCKED_CAS_NOT_RECOVERABLE or FAIL.** A loss means "not linearly decodable from this model/fixture," NOT "CAS is false."

---

## 1. Label spaces

- **CAS — 28 Foundations** = 7 Drives × 4 Registers (per the MTC build plan; the MTC infra uses Registers, not Domains).
  - Drives: F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection, F5 Agency, F6 Structure, F7 Purpose.
  - Registers: T Transcendent, A Analytical, f Affective, E Embodied.
  - Label form: `FjR` (e.g. `F1T`, `F4f`, `F6A`). 28 classes. Chance = 3.571%.
- **Rival — GoEmotions-28** (single published taxonomy, Demszky et al., ACL 2020) = 27 emotions + Neutral:
  admiration, amusement, anger, annoyance, approval, caring, confusion, curiosity, desire, disappointment, disapproval, disgust, embarrassment, excitement, fear, gratitude, grief, joy, love, nervousness, optimism, pride, realization, relief, remorse, sadness, surprise, **neutral**. 28 classes. Chance = 3.571%.
- **Controls (mandatory):**
  - `scrambled_cas_f28` — CAS labels permuted (balance + split preserved). Must floor near chance (~3.57%). If scrambled ≥ real CAS → no signal.
  - `lexical_kmeans28` — TF-IDF k-means, k=28, on prompt wording. Surface ceiling.

---

## 2. Fixture (dual-labeled, leakage-controlled) — the hard part, $0, local

Each row = ordinary-world scenario, labeled with **both** a CAS Foundation (`FjR`) **and** a GoEmotion, **assigned before capture**.

- **Joint balance:** both 28-class marginals balanced across a frozen train/test split.
- **Size:** pilot 28×25 = 700 rows; confirmatory 28×100 = 2,800 rows. (Condition-3 had ~18/class — too thin; preregister ≥25/class pilot, ≥100/class confirmatory.)
- **Authoring rules (avoid BOTH prior failure modes):**
  1. Ordinary concrete prose. No CAS/TKS source vocabulary. No GoEmotion answer-word used as a class badge.
  2. Strip literal answer-key words for **both** label sets, then a bag-of-words classifier must NOT recover the labels (that was the v1 100%-text failure).
  3. But the meaning must remain so a blind reader CAN recover the labels (over-stripping was the v2 quarantined failure). Target the middle.
  4. Cue/marker systems balanced across classes (no surface marker = class badge).
- **Row schema** (matches existing MTC fixture format):
  ```json
  {"id":"...","prompt":"...",
   "expected_cas_axes":{"drive":"F1..F7","register":"T|A|f|E","foundation":"FjR"},
   "control_emotion":{"goemotion":"<one of 28>"},
   "metadata":{"split":"train|test","fixture_family":"mtc_f28_goemotions_v1",
               "authoring_rule":"concrete ordinary scenario; answer-words stripped both label sets"}}
  ```

---

## 3. Gates — run IN ORDER, do not skip. Corrected thresholds.

| # | Gate | Where | Threshold | Fail verdict |
|---|---|---|---|---|
| 1 | **Surface-text baseline** | LOCAL $0 | TF-IDF/logreg ≤ **60%** on BOTH label sets (after answer-word stripping) | `BLOCKED_TEXT_BASELINE_TOO_HIGH` → rewrite |
| 2 | **Meaning-preservation** | LOCAL/API ~$0 | blind reader recovers labels at **~50%+**, clearly above the surface baseline (single intelligent rater + independent human spot-check) | meaning-stripped → rewrite |
| 3 | **Activation capture** | **POD (GPU)** | GPT-NeoX-20B forward over fixture → per-layer last-token npz | — |
| 4 | **CAS recoverability floor** | LOCAL $0 | CAS-F28 hidden readout beats its OWN text baseline by **≥ 20pp** | `BLOCKED_CAS_NOT_RECOVERABLE` → STOP. **Not a CAS loss.** |
| 5 | **Comparative specificity** | LOCAL $0 | see §4 — only run if Gate 4 clears | PASS / GREY / FAIL |

> Corrected from the draft catalog (errors my own adversarial check caught): MP gate is **~50% single-reader recovery**, not "75% inter-rater"; the prior F28 "scrambled beat CAS" number is from the **quarantined** pilot and is **not** cited here.

---

## 4. Comparative specificity (Gate 5) — same pipeline, blind

- Same activations, same frozen split+seed, same probe for every label set: `StandardScaler → LogisticRegression(C=0.1, class_weight="balanced", solver="lbfgs")`, best layer selected independently per label set, grader blind to which label set is CAS.
- **Primary metric:** macro-F1 **hidden-minus-text** (the model's internal-state lift over a text-only classifier). CAS must exceed GoEmotions-28 by the preregistered margin under **Holm** multiple-comparison correction, and sit above the scrambled-null floor.
- **Structural test (this is where the notation — Drive × Register — is actually tested, not flat labels):** flat lacunarity + **nested** lacunarity (Drive-within-Foundation, Register-within-Foundation).
  - PASS if CAS lacunarity ≥ **3.0×** cleaner than the best rival; GREY 1.5×–3.0×; FAIL ≤1.5×. Win ≥ **2 of 3** nested scores.
- **Null calibration:** scrambled-CAS must floor near chance; lexical-kmeans bounds generic lexical structure.

## 5. Decision rule (preregistered)

- **PASS specificity:** Gate 4 cleared AND CAS beats GoEmotions on hidden-minus-text macro-F1 (Holm) AND lacunarity ≥3× AND ≥2/3 nested.
- **GREY:** mixed (e.g. wins F1 but lacunarity 1.5–3×).
- **FAIL:** GoEmotions ≥ CAS on hidden-minus-text, or CAS clears floor but loses the structural test.
- **BLOCKED_CAS_NOT_RECOVERABLE:** CAS misses the +20pp floor → uninterpretable; neither win nor loss; do not spend interpreting.
- Verdict honesty: any ACCEPT requires WORM; default `FLAG_FOR_HUMAN_REVIEW`.

## 6. Evidence packet (per run)

fixture hash · assignment-artifact hash · source-manifest hash · both text-baseline diagnostics · MP-gate evidence (rater recovery + human spot-check) · per-layer hidden readout (best layer, acc, macro-F1) · lift-over-text · flat+nested lacunarity · permutation null (≥100 shuffles) · split hash · activation hash · explicit PASS/GREY/FAIL/BLOCKED verdict under this frozen rule.

## 7. Run order & cost

| Step | Where | Cost | Blocker |
|---|---|---|---|
| Fixture build + Gate 1 + Gate 2 | LOCAL | $0 | none — start now |
| Freeze + WORM-anchor prereg + fixture | LOCAL | $0 | gates 1–2 pass |
| Gate 3 capture | **POD** | GPU | pod up + SSH creds (was timing out: `194.68.245.165`) |
| Gates 4–5 scoring | LOCAL | $0 | npz from step 3 |

## 8. Artifacts to build next (local, $0)

1. `mtc_f28_goemotions_generator` — dual-labeled, joint-balanced, answer-word-stripped scenario generator.
2. `surface_text_gate` — TF-IDF/logreg baseline per label set (Gate 1).
3. `meaning_preservation_harness` — blind-rater recovery (Gate 2).
4. Reuse the existing MTC scoring runner for Gates 4–5 (probe + lacunarity + nulls + Holm).
