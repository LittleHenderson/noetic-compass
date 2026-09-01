# CJT-DEV-P1 — Static Dual-Stream Neural Coupling Development Pilot

**Status:** COMPLETE. S7-P (hard partition) construction FAILED and is preserved
as a negative result; the owner amendment **CJT-DEV-P1-S7Δ** replaced it with a
SOFT WordNet semantic simplex control (`S7_DELTA_WN1`), which passes all
construction-integrity gates. The four-arm pilot (S0 / S3 / S6 / **S7-Δ**) **ran
on a real AWS GPU** (Qwen2.5-0.5B on a Tesla T4, us-west-2, $0.133). Development
verdict: **`NO_DEV_SIGNAL`** — the CAS profile gave no advantage over the plain,
uniform, or WordNet-soft controls (all four arms ~0.21 val accuracy, within
0.002). See `CLOUD_EXECUTION_RECEIPT.json` and `results_p1/`.

**Branch:** `research/cjt-dev-gpu-pilot-v1` (from anchor `3182e0623`).
**Classification:** development-only, **non-claim-bearing** (owner directive
CJT-DEV-P1). This directory is deliberately SEPARATE from the frozen Gate 1B
package `../cjt_gate1a_static_neural_v1/` so the claim-bearing tree is untouched.

## What the pilot is

Train four small heads over frozen `Qwen2.5-0.5B-Instruct` activations and ask,
in development terms only, whether the CAS-coupled head (S3) learns the approved
construction-gold task better than a plain head (S0), a matched-capacity head
(S6), and an **independent** semantic-taxonomy head (S7-P).

The four arms:
- **S0** plain head (no attention, no profiles)
- **S3** CAS-coupled head (attention over Ideas + the 4-class CAS profile per Idea)
- **S6** same module as S3, but every Idea gets the uniform profile (capacity control)
- **S7-P** same module as S3, but Ideas get a **WordNet-derived** 4-class profile
  that must be an INDEPENDENT carving of the 16 head verbs, not the CAS carving

## The blocker: S7-P cannot be built without manufacturing it

`build_s7_pilot.py` constructs S7-P from a frozen WordNet 3.0 snapshot
(`wordnet.zip` SHA-256 `cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59`,
10,775,600 bytes, Princeton WordNet 3.0 License). The result is
`S7_PILOT_BUILD_RECEIPT.json`.

The gate requires a 4×4-balanced, WordNet-only, CAS-blind partition of the 16
verbs with **Cramér's V(S7, CAS) ≤ 0.35**, not equal to and not a permutation of
the CAS partition.

**It fails.** The 16 registered verbs' CAS classes are semantic operation-types
(attract / avert / decompose / trigger), and WordNet organizes verbs
semantically, so every principled CAS-blind WordNet *semantic* partition
correlates with CAS above the threshold:

| construction (pre-declared / diagnostic) | Cramér's V | semantic? | passes ≤0.35? |
|---|---|---|---|
| **verb primary-sense lexname** (repo's frozen `construction_law`, PRIMARY) | **0.3536** | yes | **no** (fails by 0.0036) |
| sense-1 hypernym lexname (FALLBACK) | 0.6124 | yes | no |
| primary lexname (round-robin) | 0.408 | yes | no |
| polysemy count | 0.408 | no | no |
| lemma count (round-robin) | 0.354 | no | no |
| **synset offset (round-robin)** | **0.289** | **no** | yes — **EXCLUDED** |

The only construction that passes is a **shuffle by arbitrary WordNet synset
catalog numbers** — not a semantic taxonomy. Selecting it *because* it passes the
CAS-orthogonality test is exactly the "manufacture a convenient control" the
directive forbids. So the honest verdict is `S7_PILOT_CONSTRUCTION_FAILED`, and
the pilot stops before any GPU use.

This confirms the taxonomy manifest's own `circularity_disclosure`: the dataset's
answer function is defined over the CAS classes, so no genuinely task-relevant
non-CAS control can exist on this 16-verb vocabulary.

## The owner's resolution: a SOFT simplex control (S7-Δ-WN1)

The owner ruled (amendment **CJT-DEV-P1-S7Δ**) that the real defect was the
hard-partition assumption — that a meaning belongs to exactly one box. Overlapping
meaning is *information*, not contamination. So the hard S7-P is **replaced** (the
FAILED verdict above is **preserved, not rewritten**) by a soft control:

`build_s7_delta.py` gives each registered verb sense a 4-component profile in the
simplex Δ³ (`simplex_semantics = SEMANTIC_COMPOSITION` — not a probability):
1. one **sense-in-context** synset per verb, frozen by clause meaning (documented;
   CAS never consulted);
2. TF-IDF WordNet features (lexname, gloss words, hypernym lemmas, verb frames)
   over the **complete** ~13.7k verb-sense inventory — four factors learned from a
   real population, not from 16 points;
3. a deterministic 4-factor **NMF** (nndsvda init) → per-sense factor loadings;
4. **gentle global factor-scale equalization** → ~equal component mass *without
   forcing any word to a corner* (an aggressive Sinkhorn was rejected because it
   fabricated pure-corner profiles — e.g. flipped `summoned` from a genuine 58/42
   mix to 100/0).

The Cramér's-V ≤ 0.35 rule does **not** govern this soft control. Soft
CAS-alignment is **reported** after the table is frozen, never optimized against.
Construction-integrity gates (finite / nonnegative / rows sum to 1; rank 4; fixed
per sense; no CAS/Qwen input; ≠ S3; no permutation = S3; same 4-dim interface and
capacity) all pass. Result: mean per-verb entropy ≈ 0.58 (genuinely soft), balanced
component mass ≈ [2.98, 4.79, 3.54, 4.69]. See `S7_DELTA_BUILD_RECEIPT.json`.

## Files
- `build_s7_pilot.py` — deterministic, WordNet-only hard S7-P construction + gates.
- `S7_PILOT_BUILD_RECEIPT.json` — the frozen **negative** result (verdict, full
  landscape, per-verb WordNet features, pinned snapshot). Kept, not deleted.
- `build_s7_delta.py` — the soft S7-Δ construction (NMF simplex + integrity gates
  + soft-alignment reporting).
- `S7_DELTA_WN1.json` — the frozen 16×4 soft profile table (the control the pilot
  actually uses for its S7-Δ arm).
- `S7_DELTA_BUILD_RECEIPT.json` — sense assignments, integrity gates, per-verb
  dominance/entropy, soft CAS-alignment reporting, provenance.
- `run_pilot.py` — the pilot harness (reuses the frozen Gate 1B blocks; extracts
  Qwen activations once, trains the four heads, writes all dev outputs).
- `CLOUD_EXECUTION_RECEIPT.json` — the authoritative cloud run receipt (instance,
  GPU, cost, digests, termination proof, both stage verdicts).
- `results_p0/`, `results_p1/` — the run outputs (raw results, arm comparison,
  learning-curve CSV, receipt, summary; P1 also has the trimmed execution log).

## Pilot execution — cloud GPU (2026-08-31)

Owner directive: **"no local, use cloud aws or runpod."** Run on **one
self-terminating AWS `g4dn.xlarge`** (Tesla T4 16GB, us-west-2, torch 2.5.1+cu121),
booted → installed → downloaded Qwen → P0 smoke → P1 → uploaded results →
**self-terminated in 15.1 min for ~$0.133** (triple-guarded termination; far under
the $30 / 2-hour owner ceiling). `is_real_model: true`. No protected split touched;
no claim promoted.

- **P0 smoke:** `P0_SMOKE_OK` — all four arms trained, candidate tensors present,
  losses finite, no CPU fallback, parameter counts matched.
- **P1 pilot** (4 arms × seeds 11/23/47 × 1000 updates, L\*=24):

| arm | mean val acc | std | val loss | params |
|---|---|---|---|---|
| S0 plain | 0.2117 | 0.0056 | 2.018 | 942,574 |
| S3 CAS (one-hot) | 0.2123 | 0.0005 | 2.013 | 951,744 |
| S6 uniform | 0.2140 | 0.0037 | 2.009 | 951,744 |
| S7-Δ WordNet soft | 0.2113 | 0.0012 | 2.015 | 951,744 |

- **S3 − S0 = +0.0007, S3 − S6 = −0.0017, S3 − S7-Δ = +0.0010** — none clears the
  +0.02 signal threshold. Verdict **`NO_DEV_SIGNAL`**. S3 ties S6, so the profile
  *content* is not load-bearing in this configuration.
- Surface references: B0 class-blind floor (val) **0.668**, B1 surface ceiling
  (val) **1.000**. **All four neural arms (~0.21) fall far below the floor.** The
  comparison is fair (every arm shares the readout handicap), but the low absolute
  ceiling makes this a **weak / underpowered test** — a small profile benefit could
  be masked near the readout floor. A stronger-readout follow-up is an **owner**
  research-design decision, not taken here (per the stop law).

No claim-status vocabulary is used; the only labels are the development triage
statuses. Prohibited terms (`CAS-specific`, `EMPIRICALLY_SUPPORTED`, `GATE1B_PASS`,
`CJT_TRANSFORMER_VALIDATED`) are not used.

## Δ.1 round (owner ruling CJT-DEV-P1-S7Δ.1, 2026-08-31) — statistical correction + five-arm rebuild, STOPPED at a failed control gate

The owner's exact permutation analysis (independently re-verified in-session by
full enumeration of all 63,063,000 balanced partitions — all five null
probabilities matched exactly) established that the old **V ≤ 0.35 gate was
miscalibrated for n=16**: it admitted only ~10% of genuinely random balanced
partitions, and 0.35 sits in an empty gap of the attainable-V lattice
(0.288675 → 0.353553). The "missed by 0.0036" framing is **retired**
(`STATISTICAL_CORRECTION_S7.json`); the `S7_PILOT_CONSTRUCTION_FAILED` verdict
is preserved with a narrowed interpretation (the *protocol* failed its gate; it
did **not** establish that no honest semantic control can exist).

**S7-H registered** (`build_s7_h.py` → `S7_H_WN1.json`): the honest
primary-lexname hard partition (V=0.353553, exact-null p=0.90 — fully compatible
with independence) is rehabilitated as a valid hard control. Its own
permutation-invariant agreement is A\* = 7/16, comfortably inside the 9/16
anti-copy bound. `profile_semantics=EXCLUSIVE_LEXICAL_CATEGORY`,
`authority=RESOURCE_DERIVED_CONTROL`.

**S7-Δ v2 FAILED its frozen anti-copy gates** (`build_s7_delta_v2.py` →
`S7_DELTA_V2_BUILD_RECEIPT.json`, verdict `S7_DELTA_V2_CONSTRUCTION_FAILED`).
Rebuilt under all Δ.1 laws — background fit **excluding** the 16 target senses,
factor-stability gate (median mean-row JS = 0.0000: perfectly stable),
background-frozen anti-uniform gates (all four pass), raw+balanced profiles
preserved. But the permutation-invariant near-copy diagnostics fail:

- **A_hard\* = 11/16** (> the 9/16 structural bound; shuffle-null p95 = 10, p = 0.0109)
- **A_soft\* = 0.5239** (> shuffle-null p95 = 0.4532, p = 0.0016)
- Robust to the null: the owner-literal entropy-matched row-value-permutation
  null (`diag_s7_delta_v2_nulls.py`) gives A_hard\* p = 0.00688, A_soft\* p = 0.00121.

Plain reading: after optimally renaming factors, 11 of 16 verbs' dominant
WordNet factor coincides with their CAS class — the honest soft semantic
representation of this vocabulary is significantly CAS-aligned beyond the
ruling's near-copy boundary. This is the same structural circumstance as the
S7-P episode, now visible at the soft level: the 16 verbs were *chosen* to
instantiate the 4 CAS operations, so a faithful semantic representation echoes
that grouping (the hard partition survives the same standard only because hard
categorization discards most of the alignment information — correction 1
catching exactly the loophole it was designed for; the v1 table has the same
0.52 soft alignment). This shows the vocabulary's semantic coherence; it is NOT
evidence of CAS specificity.

**Consequence (blocker law class A, scientific-comparison integrity):** the
five-arm pilot ordered by the ruling requires S7-Δ to pass its
construction-integrity checks first ("GPU PILOT: PROCEED AFTER THESE BOUNDED
CONTROL-INTEGRITY CHECKS"). It did not. No GPU was launched in this round ($0).
Whether to (a) run four arms (S0/S3/S6/S7-H) without S7-Δ, (b) recalibrate the
near-copy gate to test copy *magnitude* rather than alignment *significance*
(the current gate rejects any detectable semantic alignment, which sits in
tension with the ruling's own "correlation should be reported, not treated as
contamination"), or (c) close the S7-Δ line, is an **owner decision**.

## Δ.2 / P1.2 round (owner rulings "association is not copying" + "correct the power analysis") — V3 ADMITTED, readout diagnostics ordered

The owner chose **option (b), modified**: magnitude gates replace the
significance veto ("The v2 soft control failed an association-significance
gate. It did not demonstrate that the WordNet control copied CAS."). Both
prior FAILED verdicts stay preserved under their own gates. Executed:

- **16-sense audit** (`audit_s7_senses.py` → `S7_SENSE_AUDIT.json`):
  `AUDIT_PASS_NO_SENSE_CORRECTIONS` — 11 CORRECT, 4 DEFENSIBLE,
  1 BEST_AVAILABLE, 0 ERROR. Particle-verb alternatives recorded
  (back_away = retreat.v.04, commitment-retreat register; break_down ∈
  decompose.v.01, near-synonymous). Sense-policy disclosure: S7-H uses
  primary-of-surface-lemma senses, S7-Δ uses construction-context senses —
  their contrast is NOT a pure hard-vs-soft ablation.
- **Structural independence** (`wordnet_profile_builder.py`): the builder
  holds NO CAS mapping (alphabetical verbs, anonymous columns WN-F0..F3, no
  cas_class_order field); WordNet 3.0 pin FAIL-CLOSED; deterministic
  recomputation reproduces the frozen v2 profiles (max drift 4.86e-09) →
  `S7_DELTA_WN1_V3.json` reuses them byte-for-byte. Stability reported
  per-fit (median mean-row JS 0.000014; fits 1.2e-05…0.0406 — "passed
  strongly", not "perfect"). Centered affine rank 3. Factor report emitted
  (`S7_DELTA_FACTOR_REPORT.json`), components stay anonymous.
- **Comparator** (`compare_s7_to_cas.py`, runs only after sealing):
  **`S7_DELTA_V3_ADMITTED`** — A_soft\* = 0.523915 < 0.75
  (D_copy = 0.476085 > 0.25), A_hard\* = 11/16 < 14/16, ≠ S3 under all 24
  permutations. The Monte Carlo nulls are renamed
  `CONDITIONAL_BALANCED_PERMUTATION_MONTE_CARLO` and are **descriptive only**
  (p_hard = 0.01088 ± 0.00023, p_soft = 0.00162 ± 0.00009): WordNet's factors
  align with CAS more than shuffled labels — expected for two semantic
  descriptions of verbs selected to instantiate the CAS operations.
- **Corrected chance baselines** (`CANDIDATE_UNIFORM_BASELINES.json`): the
  task selects from a variable candidate set (val: 4–18, mean 9.067), so
  chance is candidate-uniform — val uniform accuracy **0.12284**, uniform CE
  **2.15307** (never 0.25 / ln 4). The ran pilot's ~0.21 / 2.01 is therefore
  **`ABOVE_UNIFORM_LOW_COMPETENCE_READOUT`** — above uniform, far below the
  surface references. Structural fact: train (families A,B) and val (family
  C) share **zero** clause head verbs — validation demands total cross-family
  surface transfer.
- **Next per the ruling:** `run_diagnostics.py` (CJT-DEV-P1.1) runs
  Diagnostics A–G (memorization, in-distribution holdout vs cross-family
  transfer, gold-clause oracle, contextual-candidate oracle, profile
  sensitivity, attention inspection) on a cloud GPU; then the readout is
  repaired (profile-aware routing: the profile enters Idea *selection*, not
  just the post-attention dashboard) and the five-arm pilot
  (S0/S3/S6/S7-H/S7-Δ-V3) relaunches. Arm type tags: S3
  `EXACT_OPERATION_IDENTITY`/`CONSTRUCTION_GOLD`; S6
  `UNIFORM_CONTROL`/`EXPERIMENTAL_CONTROL`; S7-H
  `EXCLUSIVE_LEXICAL_CATEGORY`/`RESOURCE_DERIVED_CONTROL`; S7-Δ
  `WORDNET_LEXICAL_FACTOR_COMPOSITION`/`RESOURCE_DERIVED_CONTROL`.

## P1.1 diagnostics + P1.2 five-arm relaunch — RAN (2026-08-31); verdict `NO_DEV_SIGNAL` again, at a much higher readout level

**Diagnostics** (`results_diag/`, T4, 562.8s, ~$0.154): machinery healthy
(128-example memorization → 1.000); v1 attention collapsed and dead (entropy
0.0, gold-clause top-1 23.7%, `w_q` grad ~1e-17); profile channel provably
inert (true=uniform=permuted=zeroed); gold-clause oracle +0.036; contextual
candidates +0.031; in-distribution holdout 0.278 (S3) vs cross-family 0.210 —
binding-readout generalization is the primary bottleneck. Full causal analysis
in `results_diag/DIAGNOSTIC_FINDINGS.md`.

**Five-arm relaunch** (`run_pilot_v2.py` → `results_v2_p1/`, T4, 19.8 min,
~$0.173): RoutedHead (profile-aware routing, λ learned from 0) + contextual
candidates for all arms; P0 `P0_SMOKE_OK`; P1 selected layer 18. The repairs
lifted **every** arm from ~0.21 to 0.37–0.40 — and the arms remain
statistically indistinguishable:

| arm | mean val acc | std | by-seed range | λ by seed |
|---|---|---|---|---|
| S0 plain | 0.3737 | 0.0033 | .370–.378 | — |
| S3 CAS | 0.3943 | 0.0160 | .378–.416 | −0.010 / **0.055** / **0.051** |
| S6 uniform | **0.3990** | 0.0291 | .360–.430 | ~0.000 |
| S7-H hard WN | 0.3810 | 0.0198 | .366–.409 | ≤|0.008| |
| S7-Δ soft WN | 0.3753 | 0.0230 | .349–.405 | ≤0.017 |

S3−S0 = +0.0207, S3−S6 = **−0.0047**, S3−S7-H = +0.0133, S3−S7-Δ = +0.0190 →
**`NO_DEV_SIGNAL`** (all seed ranges overlap; S6 nominally highest). All arms
~3× candidate-uniform (0.123) and far below B0 = 0.668.

**λ-initialization finding (recorded, not relaunched):** λ was initialized at
exactly 0, and the routing-query gradient is proportional to λ — so `W_r`
received zero gradient until λ escaped 0, a chicken-and-egg lock. Routing never
substantively engaged; the accuracy jump came from the candidate-grounding
repair, which is profile-independent. S3 was the only arm whose λ escaped zero
(2/3 seeds) — directionally consistent with the CAS profile carrying some
routing signal, but the accuracy effect is inside seed noise and licenses
nothing. Per the stop law, no post-hoc redesign was run; a λ>0 initialization
is the documented fix for a future owner-authorized iteration. See
`CLOUD_EXECUTION_RECEIPT_P12.json`.

## P1.2b — the λ-fix rerun (owner P1.1-closure directive): routing finally engaged; verdict still `NO_DEV_SIGNAL`; first mechanistic arm separation

Single repair (λ init 1.0) + the directive's **executable P0 gates** +
adversarial pre-launch review (which proved S6's routing gradient is
mathematically zero by design — uniform profiles are a softmax-invariant
shift — and exempted it from the routing-gradient gate). One self-terminating
T4, 20.5 min, ~$0.18 (`CLOUD_EXECUTION_RECEIPT_P12B.json`; cumulative project
GPU ≈ $0.64).

- **PRIMARY (frozen candidates): `PILOT_PIPELINE_FAILURE` at P0 — a real
  catch, not noise.** S3's `w_r` grad at step 50 was 1.3e-14 (early softmax
  saturation at L\*=24 still starves routing in frozen mode); the boot script
  skipped P1-frozen exactly per protocol.
- **SECONDARY (contextual): P0 passed ALL gates** (S3 routing grads real:
  7.9 → 2.2 → 0.08; profile-swap moves logits, mean|Δlogit| 0.52). P1
  (5 arms × 3 seeds × 1000 updates, L\*=18):

| arm | val acc | std | gold-clause hit | true→permuted→uniform→zeroed acc | λ |
|---|---|---|---|---|---|
| S0 | 0.3737 | 0.0033 | 0.365 | — | — |
| **S3** | **0.3780** | 0.0222 | **0.472** | **.378 → .365 → .355 → .356** | ~0.99 |
| S6 | 0.3630 | 0.0062 | 0.423 | .363 → .363 → .363 → .361 (exact invariance, Δlogit 0.0000) | ~1.00 |
| S7-H | 0.3590 | 0.0265 | 0.346 | .359 → .362 → .361 → .359 | ~0.92 |
| S7-Δ | 0.3617 | 0.0131 | 0.248 | .362 → .365 → .367 → .365 | ~0.94 |

S3−S0 = +0.004, S3−S6 = +0.015, S3−S7-H = +0.019, S3−S7-Δ = +0.016 →
**`NO_DEV_SIGNAL`** (nothing clears +0.02; seed ranges overlap).

**What is genuinely new:** (1) the routing branch provably trained for the
first time; (2) **S3's exact operation profile routes attention to the gold
clause better than every control** (47.2% vs 24.8–42.3%); (3) **S3 is the
only arm whose accuracy declines when its profiles are shuffled or
replaced** — the owner's condition-6 content-dependence test fires for S3
alone (S6 exactly invariant, verifying the math in vivo; S7-H/S7-Δ get no
benefit from their true profiles); (4) **the binding ceiling is confirmed**:
an +11pp routing advantage converts to only +0.4pp accuracy — matching
Diagnostic D. The deterministic status is `NO_DEV_SIGNAL`; the mechanistic
pattern matches the owner's `READOUT_STILL_UNDERPOWERED` description
(recorded as an observation, not the emitted status). Train-subset ~0.78 vs
val ~0.37 shows the cross-family generalization gap on top.
