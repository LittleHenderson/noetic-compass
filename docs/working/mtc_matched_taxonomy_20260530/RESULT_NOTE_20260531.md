# MTC Matched-Taxonomy Control — dual_labeled 40E — Result Note (2026-05-31)

## Plain-English bottom line

This run did **not** establish CAS specificity. It returned **FALSIFY**.

It also does **not** falsify CAS globally. It falsifies the dual_labeled
marker-balanced fixture as a specificity instrument: on this fixture,
GPT-NeoX-20B hidden states do not recover the CAS 40-Element distinction above
chance, so there is no signal for the matched-taxonomy comparison to interpret.

## What was run

- Runner: `live-trace-worker/scripts/run_matched_taxonomy_control.py` (prereg
  `cas_harness_matched_taxonomy_control_prereg_20260530.md`, schema
  `cas_harness_matched_taxonomy_control.v1`).
- Activations: `gpt_neox_20b_mtc_dual_labeled_40e_pilot_20260530_layers_0_43.npz`
  (1000 × 44 × 6144), already on pod from the 2026-05-30 capture.
- Manifest: `mtc_dual_labeled_40e_pilot_assignments_20260530.json` — one coherent
  matched control `NC40_TOPIC_FRAME_V1` (topic_40 × frame_40, 40 classes).
- Probe: `StandardScaler + LogisticRegression(C=0.1, class_weight='balanced',
  lbfgs)`, all 44 layers, each taxonomy gets its own best layer.
- Split: seed 20260530, 800/200, stratified (dual_labeled has no
  counterfactual-pair grouping → `group_key=null`).
- Report SHA256: `55a24e50e4108980493ce3a1f0f2fe81b6ab2ade3d5d4441711648141d0690ac`

## Numbers (chance = 2.5% for 40 classes)

| Taxonomy | role | best layer | hidden acc | hidden macro-F1 | text acc |
|---|---|---:|---:|---:|---:|
| `cas_40e` | CAS | 20 | **5.5%** | 5.3% | 1.5% |
| `NC40_TOPIC_FRAME_V1` | coherent matched | 0 | 1.5% | 0.07% | 0.0% |
| `scrambled_cas_seed_20260530` | scrambled null | 11 | **5.0%** | 4.9% | 3.0% |

## Why this is FALSIFY (not specificity)

Two preregistered gates govern the verdict:

- **Gate 1 — CAS hidden readout lift over text: FAILED.** CAS hidden = 5.5%,
  CAS text = 1.5%, lift = **+4.0pp**. Required ≥ **+20pp**. CAS is barely above
  the 2.5% chance floor.
- **Gate 2 — CAS beats coherent matched control: technically "passed"
  (+4.0pp acc / +5.2pp macro-F1 over NC40), but this is not meaningful.** Both
  CAS (5.5%) and the matched control (1.5%) are at or below the noise floor.
  Beating noise with slightly-less-noise is not specificity.

**The decisive observation is the scrambled control.** Randomly-permuted CAS
labels recover **5.0%** — statistically indistinguishable from real CAS at
**5.5%**. When you can "recover" shuffled labels about as well as true labels,
the probe is fitting noise in the 6144-dim space, not reading a CAS signal. The
runner flags this: `scrambled_cas_near_chance_no_clean_structure = failed`.

## Reconciliation note: the "32%" text baseline

The capture runbook / pilot gate doc cited a **32%** CAS text baseline for the
dual_labeled 40E fixture. The authoritative runner's text lane on the same npz
reports **1.5%**. The 32% figure does not reproduce here and should not be
relied on. The most likely explanation: the marker-balanced prompts rotate the
N/D cue-card *definitions* per row, so the literal selected marker token (e.g.
"N0") does not map to a fixed element — a bag-of-words classifier keyed on the
visible markers cannot recover the element, consistent with ~1.5%. Flag the 32%
gate diagnostic for re-derivation; do not cite it.

## F28 axis — also FALSIFY (even cleaner null)

Same runner, `gpt_neox_20b_mtc_dual_labeled_f28_pilot_20260530_layers_0_43.npz`
(700 × 44 × 6144), manifest control `NC28_TOPIC_FUNCTION_NESTED_V1`. Chance for
28 classes = 3.57%.

| Taxonomy | role | hidden acc | text acc |
|---|---|---:|---:|
| `cas_f28` | CAS | **3.57%** (= chance) | 0.0% |
| `NC28_TOPIC_FUNCTION_NESTED_V1` | coherent matched | 5.0% | 0.0% |
| `scrambled_cas_seed_20260530` | scrambled null | **6.43%** | 4.29% |

CAS F28 recovers at **exactly the 3.57% chance floor**, and the **scrambled
null (6.43%) recovers *higher* than real CAS** — the definitive no-signal
signature. Gate 1 fails (+3.57pp vs required +20pp). This is a clean fixture
null, consistent with the 40E result and the prior pilot (F28 0.0% recovery).

## What this means for the spec sheet / claims

- "ESTABLISH CAS-SPECIFICITY" **cannot be marked done.** The data we can run on
  (dual_labeled marker-balanced capture) is a fixture null. The original v1
  95.625% fixture's specificity remains **untested** — those activations were
  lost with the prior pod and cannot be re-probed.
- This is fully consistent with `cas_harness_mtc_20b_pilot_results_20260530.md`:
  marker-balanced fixtures over-correct — they remove surface leakage so
  aggressively that the model has no reason to internally represent the CAS
  distinction, so the probe recovers nothing.
- Honest external wording: "The leakage-controlled marker-balanced dual_labeled
  fixture did not make CAS recoverable from 20B hidden states (5.5% vs 2.5%
  chance; scrambled labels recover 5.0%). This is a fixture-design null.
  Matched-taxonomy specificity remains open and requires a fixture where CAS
  labels are genuinely grounded in scenario meaning without being visible text
  shortcuts."

## Next move (unchanged from pilot doc)

Build the MTC v2.5 meaning-preserving fixture: plain-English, non-leaky prompts
whose scenario meaning genuinely requires the target CAS distinction (not
marker cue-cards, not source-vocabulary anchors). Gate locally on BOTH the
Surface Gate (text baseline ≤ near-chance) AND a Meaning-Preservation Gate
(human raters recover labels) before spending any GPU on capture.
