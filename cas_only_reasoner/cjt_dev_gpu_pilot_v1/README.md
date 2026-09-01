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
