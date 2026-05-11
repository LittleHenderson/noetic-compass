# v1e Phase 1B β2 Eval — Lever 4 Findings

**Date:** 2026-05-11 (UTC)
**Task:** #139 (v1e Phase 1B Lever 4: final-slot tail control)
**Eval driver:** `cas-synthetic/scripts/v1e_phase1b_shadow_eval.py`
**Raw JSONL:** `v1e_phase1b_shadow_eval_20260511T003204Z.jsonl`
**Auto-summary:** `v1e_phase1b_shadow_eval_20260511T003204Z_summary.md`

## TL;DR

β2 moved full_seq_match by +5 under H3 (eos_bias=10) but did NOT
close the ≥20/35 gap. The mechanism is monotonic — stronger EOS
bias produces more full matches — but every full match comes at the
cost of an UNFINISHED, fragmentary output (no closing period, no
concluding prose). The trade-off is structural: **trailing prose
contains noetic indicators AND is structurally identical to
sentence-closing prose; suppressing one suppresses the other.**

H4 length cap at 12n+8 truncated 19/35 records mid-clause and lifted
full_seq_match by 0.

Per the user's β2 promotion gate, the verdict is binary as the user
named it: **(i) accept first-n as the product metric explicitly**
(G_baseline = 33/35 first-n, prose quality preserved, lever-4 not
needed) **or (ii) stop this branch and surface simplex/pointer**.

## Aggregate results (35 fractal records)

| config | full | first-n | slot | selected | trunc | hard | jarg |
|---|---:|---:|---:|---:|---:|---:|---:|
| A_control       | 0/35 | 1/35 | 0/35 | 0/35 | 0 | 0 | 0 |
| G_baseline (β)  | 0/35 | **33/35** | 35/35 | 33/35 | 0 | 0 | 0 |
| H1_eos5         | 0/35 | 33/35 | 35/35 | 33/35 | 0 | 0 | 0 |
| H2_eos8         | 1/35 | 33/35 | 35/35 | 33/35 | 0 | 0 | 0 |
| H3_eos10        | **5/35** | 33/35 | 35/35 | 33/35 | 0 | 0 | 0 |
| H4_length_cap   | 0/35 | 33/35 | 35/35 | 33/35 | **19** | 0 | 0 |

Negative-control byte-equality: **0/7 drift across all 5 non-control
configs**. Source-shape gate continues to hold.

v0 canary post-eval: **PASS** (24/24 byte-match frozen baseline).

## β2 promotion-gate verdict

| Criterion | Threshold | Best β2 result | Status |
|---|---|---|---|
| Slot commits 35/35 | 35/35 | 35/35 (all configs) | ✅ PASS |
| First-n ≥33/35 preserved | ≥33/35 | 33/35 (all configs) | ✅ PASS |
| Full seq_match ≥20/35 | ≥20/35 | **5/35 (H3)** | ❌ FAIL |
| Record 14 ≥yellow | yellow | H1/H2 yellow; H3 fragmentary | ❌ FAIL under H3 |
| Negatives byte-identical | all 7 | 7/7 across all configs | ✅ PASS |
| v0 canary stays PASS | PASS | PASS | ✅ PASS |
| No hard/jargon/truncation regression | none | H4: +19 trunc; H1-H3: 0 | ❌ FAIL under H4 |

The two failures are diagnostically tied: the configs that move
full_seq_match (H2/H3) damage Record 14 prose; the config that
preserves Record 14 prose (G/H1) doesn't move full_seq_match.

## Why β2 cannot close the gap — the structural finding

EOS bias is monotonic but saturates against an unavoidable trade-off.

H3's 5 full_seq_match wins are all FRAGMENTS:

| record | text |
|---|---|
| `Φ<3:7>` | `" averse in muscle memory "` |
| `Φ<1:2:3>` | `"paying attention led drawn to something averse "` |
| `Phi<9:9:9:9>` | `"popped into out of nowhere, popped into out of nowhere, "` |
| `Phi<9:9:5:9:9>` | `"popped into out of nowhere, shaped by experience, popped into out of nowhere, "` |
| `Φ<0:0:0:1:0>` | `"a thought led a thought, in your head, paying attention, an idea, "` |

All five end with a SPACE or COMMA — no period, no concluding
phrase. The model emitted EOS immediately after the last slot's
boundary token because the EOS bias outweighed the natural prose
continuation. These outputs achieve full_seq_match because there
is NO trailing prose left to contaminate the verifier — but the
prose-quality cost is unacceptable on the user-named gate
("Record 14 still yellow+").

The other 30 fractal records under H3 didn't flip because the model's
natural distribution still emitted a few connective tokens
("led to," "and finally,") before EOS, and those few tokens contained
ONE OR TWO noetic indicators that pushed `found_k_count` past
expected.

**The structural problem:** the v0 model's natural distribution emits
noetic indicators DENSELY in connective tissue. A typical closing
prose like `", and finally muscle memory took over"` adds ^7 (muscle
memory), and there is no way to suppress that ^7 without also
suppressing the `, and finally` — which IS the sentence completion.

Trailing prose with no extra noetics requires either:
- The model never to emit noetic indicators in connective tissue
  (which it does as part of natural prose)
- The model to terminate before emitting any closing prose at all
  (which produces fragments)

No EOS-bias value squares this circle.

## Why H4 length cap fails

Cap = `12 * n + 8` (e.g., 32 for k=2, 56 for k=4). Inspection:

| Record | Source | Truncated text |
|---|---|---|
| `Φ<3:7>` | n=2, cap=32 | `" averse in muscle memory led to something that struck a chord, which then became"` |
| `Phi<8:9>` | n=2, cap=32 | `"triggered a memory led popped into mind, which then became something that struck a chord, "` |
| `Phi<2:3>` | n=2, cap=32 | `" drawn to it can't stomach it, which then became drawn to it, and finally"` |

The cap is too tight for the model's natural prose density. Records
chop mid-clause. Even raising the cap to `15n + 12` or `20n + 16`
would face the same trade-off — the model wants to emit closing
prose, and tight caps cut it off mid-word or mid-clause.

## Record 14 prose under each config

| Config | Final text | Reading |
|---|---|---|
| A_control | `"Something that struck a chord, then became drawn to it, which triggered a memory, and finally muscle memory."` | Readable; wrong content |
| G_baseline | `" averse in muscle memory led to something that struck a chord, which then became muscle memory again."` | Clean prose; first-2 = [3, 7] exact; trailing ^4 ^7 |
| H1_eos5 | same as G | identical (bias too weak to flip) |
| H2_eos8 | same as G | identical |
| **H3_eos10** | `" averse in muscle memory "` | FRAGMENT — no period, no closer |
| H4_length_cap | `" averse in muscle memory led to something that struck a chord, which then became"` | TRUNCATED mid-clause |

Yellow quality requires a sentence-shaped output. H3's `" averse in
muscle memory "` is a stub. H4's truncation is incomplete. The user-
named criterion ("Record 14 still yellow+") is violated by both H3
and H4.

## What β2 proves and disproves

**Proves:**
- The EOS-bias mechanism scales monotonically with strength (0/0/1/5
  full_seq_match at biases 0/5/8/10).
- The phrase-trie + boundary + first_n combination (G) is stable —
  first-n stays 33/35 across all β2 configs.
- Negative controls and v0 canary remain unaffected by any β2 lever.

**Disproves:**
- That decode-time EOS bias alone can close full_seq_match to
  ≥20/35 without unacceptable prose-quality damage.
- That a static length cap can substitute for EOS bias without
  producing widespread truncation.

The combination of evidence indicates the trailing-prose-
contamination problem is FUNDAMENTAL to this checkpoint's prose
distribution at this point in v1c VALIDTOK training, not a tuning
problem reachable from decode-side levers.

## User's binary choice (per their β2 spec)

The user named the branch point in advance:
> "If β2 still cannot move full sequence match, then we either
> accept first-n as the product metric explicitly or stop this
> branch and surface the simplex/pointer decision."

### Option (i) — Accept first-n as the product metric explicitly

`apply_fractal_decoder` is promoted to default-True with
`fractal_decoder_first_n_mode=True` and
`fractal_decoder_leaf_exit_boundary=True` (the G_baseline config).
No EOS bias. No length cap.

Evidence supporting (i):
- 33/35 first-n match. Slot commits 35/35.
- Record 14 prose preserved at yellow quality.
- No regressions. v0 canary preserved.
- The chosen output's first-n found_k matches expected exactly in
  33/35 cases — the user-facing inductive bias success is real and
  measurable.

Cost of (i):
- The "extra states change the sequence" objection the user raised
  must be re-stated as policy: **trailing noetic indicators in
  connective tissue are tolerated as long as the FIRST-N extracted
  noetics match the source EXACTLY.** This is a deliberate product-
  metric decision, documented in `V0_RELEASE_CANDIDATE.md`.
- Full_seq_match remains 0/35 and is no longer the load-bearing gate
  for this feature.

### Option (ii) — Stop this branch and surface simplex/pointer

The decode-time lever stack is empirically saturated. The next move
is architectural per the v1e design doc:
- **Pointer/copy mechanism** (Wave-1 spec A) — ~1.6M params, ~7-8
  GPU-hr fine-tune from v1c
- **Aux heads / loss redesign** (Wave-1 spec C) — ~200k params,
  1-epoch fine-tune from v1c (cheaper)
- **Simplex Δ°₃₉ rebuild** — ~10-14 eng-weeks, structural traceability
  promotion

The accumulated β/β2 evidence supports moving up the architecture
stack. The phrase-trie mechanism proves the inductive bias is
expressible at the decode layer; the trailing-prose contamination
proves the v0 model's prose distribution isn't compatible with
strict end-to-end verifier matching from decode-time alone.

## My recommendation

**Option (i) for the short term**, with these caveats:
- Document the first-n metric as the canonical fractal-rendering
  product gate; deprecate full_seq_match for this feature.
- Promote `apply_fractal_decoder=True` (with `first_n_mode=True` +
  `leaf_exit_boundary=True`) to default-on. Tag a `v0.1-rc1` and
  update `V0_RELEASE_CANDIDATE.md` with new flag profile + new
  canary baseline.
- Move Task #136 (Phase 2 user decision) forward with G_baseline as
  the v0.1 candidate.

**Option (ii) as the next major work**, sequenced AFTER v0.1
stabilizes:
- Architecture R&D agent's "aux heads" path (C) is the cheapest
  fine-tune-from-v1c experiment. 1 epoch from v1c, ~200k new params,
  ~3-4 GPU-hours. If full_seq_match needs to be a real metric, a
  small fine-tune may bridge the gap. **Surface this as the next
  R&D fork after v0.1 ships, not before.**

The structural finding from β2 — "the model's prose distribution
emits noetic indicators in closing prose" — is itself a useful
diagnostic for the architecture pivot. It says: pointer/copy alone
won't fix trailing prose; the model needs to LEARN that fractal
rendering ends after N slots. That's an aux-head training-side
intervention.

This is the cleanest exit from the β2 branch. The decode-time levers
have done what they can. The next gain is on the training side.
