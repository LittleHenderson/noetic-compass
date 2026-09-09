# Graph-first ^6 — representation follow-up 001 — AWS attempt 011: FINISHED (flat-ln3 regime broken for 2 of 3 ops; sealed accuracy still at chance)

Status: **AWS_GRAPH_TRAINING_FINISHED.** Same bounded pilot as attempt 010
(64 optimizer steps / 600 s per framing condition; totals 128 / 1200 s), with
exactly ONE variable changed: option-slot aggregation in the frozen readout
went from mean-pooling (measured collapse) to sum-pooling. Containment HELD
(only `left.weight`, `merge.weight`, `right.weight` changed; zero forbidden);
sealed predictions recorded before answers; cleanup with zero leftovers.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909095712-4ca46fce` |
| request sha256 | `5adc103b06557897a149adea398f830e7dd5fdc59cca93770fb9caf44bab62bd` |
| authority sha256 | `38446d88b60f3ab92ad484306ba2e2cc291e8337788ff405de37f06c78269a34` |
| owner record sha256 | `b7df9c1614a57a28d848c7ccc14022048dbaba96f7098fa4a58a35c3bbb0dd7a` |
| collected result sha256 | `e4a0d61d09f0b44fc1e8530a468a47f2ce1ce5e91cb723c094a0d052b31f4e41` |
| instance | `i-03a1c87d7bcc3c078` (CONFIRMED_TERMINATED) |
| elapsed | 538.71 s |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-teaching-graph-20260909095712-4ca46fce/`

Ledger 35 → 36 (`$190.00 → $194.00` reserved, `$210.00 → $206.00`
unreserved).

## Measured (per-op before/after losses, both arms, 64 updates each)

| Op | cas before | cas after | generic before | generic after |
|---|---|---|---|---|
| LIST_PARTS | `1.1162622809410094` | `1.0805925846099853` (−0.0357) | `1.0805925726890564` | `1.0833292126655578` (+0.0027) |
| FIND_SHARED_PART | `1.0986123085021973` | `1.0986123085021973` (0) | `1.0986123085021973` | `1.0986123085021973` (0) |
| REACHED_VIA | `1.0885493397712707` | `1.1301095008850097` (+0.0416) | `1.1301094532012939` | `1.1143203616142272` (−0.0158) |

Sealed evaluation: cas `2/7` validation + `1/5` test = **3/12**; generic
identical counts (the fixed worker runs both arms sequentially on one shared
module). Attempt 010's chance reference was ≈ 4/12; 3/12 is chance-level.

## Reading against the preregistration

- **A (first half): CONFIRMED for 2 of 3 ops.** Before-losses are no longer
  uniformly exactly ln 3 for LIST_PARTS and REACHED_VIA, and both move under
  the same 64-step allowance — the sum-pooled readout now gives the module
  distinct options for those ops. The measured input-stage collapse from the
  ln(3) diagnostic is removed where it mattered for those two lessons.
- **A (second half): NOT confirmed.** Sealed accuracy did not move above
  chance (3/12). The bounded pilot did not convert the usable readout into
  generalizable decisions.
- **Residual: FIND_SHARED_PART sits EXACTLY at float32 ln 3 before and after
  training in both arms.** Its three options still produce identical scores —
  the collapse persists for that op specifically (single-token part options
  against the fixed readout). Unresolved at the measurement level.
- **No learning or capability claim follows.** This is a measured step: the
  frozen uniform regime was representation-caused for two ops and is now
  gone; the remaining flatness/at-chance result points to (a) the
  FIND_SHARED_PART residual, (b) the small 64-step allowance (the owner's
  repeated-teaching point), and/or (c) the module's operating point — each a
  separate, separately authorizable step.

Frozen negatives `0/72`, accepted models, sealed splits, and the attempt-010
record are untouched.

## Owner-directed reinterpretation (2026-09-09) — the record above is narrowed, not retracted

The owner reviewed the report and ruled the following; each point was
re-checked against code and the recorded bytes:

1. **The two conditions are sequential training phases, NOT a matched framing
   comparison.** The worker builds ONE module and runs both arms on it:
   cas trains 64 updates, then generic continues on the same module. The
   checkpoints demonstrate no reset (cas `01157267…`, generic `cc93fe47…`),
   and generic's before-losses nearly equal cas's after-losses
   (LIST_PARTS `1.0805925727` vs `1.0805925846`). The per-arm loss table
   above is therefore one trajectory in two stages; it cannot separate the
   generic framing's effect from cas's prior training. A future framing
   comparison must use two candidate copies from the same initial weights
   with separate optimizer state (prepared; see
   `REPRESENTATION_CORRECTION_002.md`).
2. **Nonuniform or moving losses do NOT establish content recovery.** The
   inspection (`tools/graph_training_representation_inspection.py`, evidence
   `representation_inspection_001/`) measured that LIST_PARTS options ALWAYS
   differ in encoded length (median spread 10 tokens; content tokens unique
   to an option: median 0.5), and sum = token-count × mean. The observed
   movement is therefore consistent with a token-count signal — "different
   amounts of text" — not demonstrated "different contents."
3. **FIND_SHARED_PART is content-only and still flat.** Its three options are
   each 2 tokens (`[OBS]` + one tag token), equal length, sum == mean, so its
   exact ln 3 before and after is NOT a representation artifact. Its next
   measurement is the module's output geometry (norm + pairwise cosines,
   prepared in the diagnostic) — the saturation reading stays an UNMEASURED
   HYPOTHESIS; `initial_saturation=100.0` is NOT being changed.
4. **Sealed evaluation is a repeat diagnostic on previously examined splits**
   (3/12 vs attempt 010's ≈ 4/12), not fresh evidence; the small counts
   establish no exact underlying chance level.

The computations above stand as recorded; only their interpretation is
narrowed.

