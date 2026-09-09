# Graph-first ^6 — ln(3) diagnostic AWS attempt 005: FINISHED — the encoder's embed lookup is the measured root cause

Status: **AWS_GRAPH_TRAINING_LN3_DIAGNOSTIC_FINISHED.** The full zero-update
measurement ran on both framing arms: per-record scores, option geometry,
individual tag vectors before pooling, OLD vs CORRECTED representation
comparison, graph-edit response, module outputs, and the alternative-target
gradient test. `optimizer_steps_taken: 0`, checkpoint unchanged, cleanup
complete with zero leftovers.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-ln3-diagnostic-20260909175351-5f425cf9` |
| request sha256 | `99fcd61d4325352ea07a8d1ee91db057229320b205dd45998ab406f3253891a5` |
| authority sha256 | `30ebff2e9ea8d4b99c30adee8697e1edd3e30040b62b5d29871cefb81b0632b5` |
| owner record sha256 | `b177a8fdf3a967f5b620d66aefb07a6f73d660dad826fd24d7a2223a60728f06` |
| collected result sha256 | `c6822f24cd3683a0620f127f3fea53243ed1b7f2b711e42e32e411b06a7dbf01` |
| instance | `i-0447492011c6fa2cc` (CONFIRMED_TERMINATED) |
| elapsed | 551.98 s |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-ln3-diagnostic-20260909175351-5f425cf9/`

Ledger 38 → 39 (`$202.00 → $206.00` reserved, `$198.00 → $194.00`
unreserved).

## The measured answer: the embed lookup returns ONE vector for every token

Both arms measure identically. The earliest stage is decisive:

1. **Individual tag vectors, before pooling:** 10 distinct tag tokens — the
   framing units AND different part names (`[WORD:6964656132]` = "idea2",
   `[WORD:6964656136]` = "idea6", …) — ALL have norm `0.9902205467224121`,
   identical to 11 significant digits, and all 45 pairwise cosines measure
   `0.9999999675104585`. These are the SAME vector, not merely parallel:
   the frozen encoder's `embed()` used `projection[index.get(token_id, 0)]`
   where `index` maps token STRINGS to positions while `token_id` is an
   INTEGER — every token silently fell back to row 0.
2. **Consequences, all consistent with the measurement:**
   - different part names are numerically indistinguishable before pooling;
   - option vectors differ only by multiplicity (sum) — attempt 011's loss
     movement was "different amounts of text", exactly the owner's
     hypothesis, now measured as fact;
   - FIND_SHARED_PART (2-token options) sums to identical vectors — exactly
     ln 3;
   - correction 002's removal changes score MAGNITUDES only: spread_old mean
     `0.1548` vs spread_new mean `0.0774`, 20/30 and 18/30 records changed,
     but argmax changed on **0/30** records — decisions untouched;
   - graph edits change nothing that survives encoding: output difference
     norms ≤ `1.5e-4` (float noise), decision changes 0/6;
   - the module output is essentially constant across records (norms ≈
     `0.38816`, pairwise cosines ≈ 1.0) — explained UPSTREAM by the
     constant inputs, so the saturation hypothesis remains open but
     unnecessary for these observations;
   - gradients are substantial (max norm `1.786`) and losses differ per
     target (`1.05`–`1.19`) — but they grade a count representation of one
     shared vector, not content.

## The fix (one line, test-locked, NOT yet re-measured)

`real_framework.build_encoder.embed` now indexes the projection row by the
token id directly — ids ARE vocabulary positions — with a bounds guard
(`0 <= token_id < len(projection)` else row 0). Source-locked test added;
105 graph tests pass. With this fix, distinct tokens receive distinct frozen
rows (~orthogonal), and the whole content-vs-count question becomes real and
re-measurable.

## What this does and does not say

- It DOES answer the owner's question with a measurement: the specialist was
  NOT receiving distinguishable ideas — at the earliest stage, the encoder's
  embed lookup.
- It does NOT claim the module can learn whole-part reasoning: nothing about
  the module's capacity has been measured with distinct inputs yet.
- The training pilot stays pending; no saturation change; no allowance
  change; no learning claim. A re-run of this SAME diagnostic with the fixed
  encoder needs a new owner authorization and one new `$4.00` reservation.
