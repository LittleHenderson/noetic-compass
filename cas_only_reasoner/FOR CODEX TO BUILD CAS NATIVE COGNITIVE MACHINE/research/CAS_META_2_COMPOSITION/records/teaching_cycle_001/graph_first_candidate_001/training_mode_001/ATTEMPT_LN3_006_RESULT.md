# Graph-first ^6 — ln(3) diagnostic AWS attempt 006: FINISHED — the repair is measured working; relationships do not survive mean-pooling

Status: **AWS_GRAPH_TRAINING_LN3_DIAGNOSTIC_FINISHED.** The lookup-repaired,
zero-update diagnostic ran on both framing arms. `optimizer_steps_taken: 0`,
checkpoint unchanged, cleanup complete with zero leftovers.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-ln3-diagnostic-20260909183759-cce57ffb` |
| request sha256 | `23b796f25b6c3fabf73dd723ea8802b59831d1be5701d218681d5978b7696568` |
| authority sha256 | `3b005b39204838c56ac862baefb52ffe7743d96b7ad17fb75dc2e2fb90e16693` |
| owner record sha256 | `8f8d2bc5f16c009090601156f596e0047206d62eb9e8991a9206c60a9ca6031f` |
| collected result sha256 | `6c7469e8997981310507e73b1c2fd1d5aea82314c20f188ceb036672de28a5de` |
| instance | `i-0639a763baef9220d` (CONFIRMED_TERMINATED) |
| elapsed | 572.78 s |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-ln3-diagnostic-20260909183759-cce57ffb/`

Ledger 39 → 40 (`$206.00 → $210.00` reserved, `$194.00 → $190.00`
unreserved).

## Measured, per arm (cas / generic, 30 records each)

| Quantity | cas | generic |
|---|---|---|
| tag norms (10 distinct tags) | 0.889–1.073 (VARY) | same |
| tag pairwise cosines (45 pairs) | mean 0.024, median 0.033, range −0.307…0.264 | same |
| option pair cosines (content-only) | mean 0.124, median 0.035, min −0.117 | same |
| problem→option cosines | mean 0.098, max 0.655 | mean 0.096, max 0.573 |
| records with zero score spread | **0/30** (was 10/30 before the repair) | 0/30 |
| correction changes decisions (old→new argmax) | **5/30** (was 0/30) | 4/30 |
| graph edits (3 records × 3 kinds) | 9; output difference median ≈ 1.5e-3, max 7.4e-3 | 9; median ≈ 2.3e-3, max 1.1e-2 |
| module output norms across records | 0.119–0.125 (VARY; was constant 0.38816) | 0.115–0.121 |
| module output pairwise cosines | mean 0.9986, min 0.9969 | mean 0.9970, min 0.9936 |
| per-target losses | differ per target (1.073–1.116) | differ (1.071–1.116) |
| max gradient norm | 0.378 | 0.366 |
| argmax vs chance | 5/30 vs 10/30 (untrained; not demanded) | 6/30 |

## The lookup repair, measured working

Different part names now reach DIFFERENT numbers before pooling (tag
cosines near zero with real spread; norms vary) — the identical-vector
collapse is gone at the earliest stage. Downstream: options are distinct
directions, scores are never exactly tied, the content-only correction now
CHANGES DECISIONS (≈1/6 of records), graph changes move the module output by
~10–50× the previous float-noise floor, and corrective gradients are
substantial and target-dependent. The distinctions and corrective signals
now SURVIVE the pipeline — the owner's measurement criterion, satisfied.

## The same-token rewiring contrast: relationships do NOT survive mean-pooling

All three rewire rows preserved the problem token multiset exactly
(`problem_token_count_before == after`, `multiset_equal: true`), and the
module output moved by only `5.4e-5` (one row exactly `0.0`) — pure float
summation noise. The retarget and node edits (vocabulary changed) moved the
output ~30–200× more. Measured boundary: the problem representation is a
**bag of words** — WHICH part belongs to WHICH idea is invisible to the
module input beyond the token multiset. Vocabulary is preserved;
relationship structure is not.

## What this does and does not say

- It DOES say the pipeline now carries content distinctions and corrective
  signals end to end, and it MEASURES the next boundary: the problem side
  discards relationship structure under mean-pooling.
- It does NOT say the module can learn whole-part reasoning — it has never
  been trained on distinct inputs. The training pilot stays pending; any
  problem-side representation change (e.g., relationship-aware pooling) is a
  separate, separately authorizable step; saturation stays a hypothesis;
  no learning claim follows.
