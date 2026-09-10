# GRAPH6_CURRICULUM_002 — attempt 004 RESULT

**Registered outcome (deterministic rule, no prose judgement):
`VARIED_CURRICULUM_NOT_ESTABLISHED` — 0 of 3 seeds showed a curriculum advantage,
0 of 3 reached the absolute level.**

The varied relationship lessons did **not** beat repeating the existing lessons at
equal budget, and neither condition rose above chance on the untouched panel. The
run finished, was collected, and its checkpoint files are retained.

## Execution, collection and cleanup (reported separately)

| Stage | Outcome |
| --- | --- |
| execution | `FINISHED` |
| collection | `VERIFIED` — result sha256 `848db69bdb0eaefa4f702a4dd4361f779fbc9fbc13c7ca5609de071a8cbcd4d0`, **18/18 checkpoint files** collected (4,740,750 bytes), none missing |
| cleanup | `COMPLETE` — instance `i-06d963e0b19f80dbc` `CONFIRMED_TERMINATED`, bucket deleted after verified collection |
| `completed_deliverable` | **true** |

Job `cas-meta2-graph6curr-20260910133000-aecb5d07`, elapsed 571.3 s, reservation
`$7.00` created once, zero retries; ledger revision 50 → 51 (`$270.00` reserved /
`$130.00` unreserved).

## The pre-registered comparison (untouched panel, 90 cases, 256 updates)

| Seed | Control | Varied | Varied − Control | 95 % CI (family-clustered) | McNemar p | Advantage? | Level ≥ 0.50? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 20260913 | 26/90 (28.89 %) | 30/90 (33.33 %) | +4/90 = +4.44 % | −8.89 % … +17.78 % | 0.6440 | no | no |
| 20260914 | 22/90 (24.44 %) | 26/90 (28.89 %) | +4/90 = +4.44 % | −8.89 % … +17.78 % | 0.6358 | no | no |
| 20260915 | 26/90 (28.89 %) | 26/90 (28.89 %) | 0/90 = 0.00 % | −14.44 % … +14.44 % | 1.0000 | no | no |
| **pooled** | **74/270 (27.41 %)** | **82/270 (30.37 %)** | **+8/270 = +2.96 %** | — | — | 0/3 seeds | 0/3 seeds |

Chance for the three-option interface is **33.33 %**: both conditions sat at or
below chance on the new arrangements.

## Repetition effect (secondary, reported, never gating)

| Curriculum | 64 → 256 updates, per seed | Mean |
| --- | --- | --- |
| control | +1, −5, −9 cases of 90 | **−4.3/90 = −4.8 %** |
| varied | +2, −4, −1 cases of 90 | **−1.0/90 = −1.1 %** |

More repetition did not improve either curriculum; the control's fresh accuracy
drifted slightly downward.

## What each curriculum actually learned (the informative part)

| Learner | Practice (frozen 30 familiar records) | Own curriculum (30 lesson records) | Fresh (90 new arrangements) |
| --- | --- | --- | --- |
| control 20260913 | 9 → 23 → **23/30** | 9 → 23 → 23/30 | 19 → 25 → 26/90 |
| control 20260914 | 4 → 22 → **23/30** | 4 → 22 → 23/30 | 24 → 27 → 22/90 |
| control 20260915 | 9 → 23 → **23/30** | 9 → 23 → 23/30 | 26 → 35 → 26/90 |
| varied 20260913 | 9 → 8 → **12/30** | 12 → 23 → **27/30** | 19 → 28 → 30/90 |
| varied 20260914 | 4 → 13 → **14/30** | 13 → 24 → **27/30** | 24 → 30 → 26/90 |
| varied 20260915 | 9 → 12 → **14/30** | 9 → 24 → **27/30** | 26 → 27 → 26/90 |

* Both conditions learned *something*: control reached 23/30 on the frozen
  familiar records (all three seeds), varied reached **27/30 on its own lessons**
  (all three seeds).
* The varied learner was **worse on the frozen familiar records** (12, 14, 14 of
  30) than the control (23, 23, 23 of 30) — the variation-rich lessons did not
  preserve the original worksheet's performance.
* Neither transferred to **unseen arrangements**: 22–30 of 90 in both conditions.
* Varied training losses fell much lower (final ≈ 0.22–0.23) than control
  (≈ 0.43–0.59), consistent with fitting its own easier-to-fit worksheet.

## Controls (all held)

| Control | Observed |
| --- | --- |
| encoder identity shared by all six learners | true — `116f3677d343db7cd9becbb0b293c4419d5f455b9e1044e33dbd6738ed1468cb` |
| paired initial weights matched within each seed | true — `9c34c98f…`, `61b0f180…`, `da4f55f7…` each appear for both conditions |
| initial checkpoints distinct across seeds | true |
| every learner reported | true — 6/6, 256 updates each = **1,536** total |
| checkpoints written, reloaded, verified in-job | true — **2/2 verifications per learner**, all `verified: true` |
| exposure matched between conditions | true — 256 deliveries each, 30 distinct records, 85/86/85 per operation, 8–9 deliveries per record; tokens 84,770 (control) vs 106,771 (varied) |
| answers sealed before predictions | true (with the recorded limitation: this proves the prediction pass saw no answer field, not the event ordering) |

## GAP against the registered execution gates (reported, not hidden)

The registered gate *"only the operation:^6 parameter group may change; the
containment report must name any forbidden change"* was **not measured in this
run**. The segmented trainer path used here does not call `trainer.launch`, so no
parameter snapshot / containment report was recorded. What is known: the learner's
optimizer is constructed over the decompose module's parameters only, and the
encoder projection is frozen (`requires_grad_(False)`), so no other parameter was
reachable by the optimizer — but that is an argument from the code, not the
registered digest-level evidence. **The result is reported with that gap stated.**

## What this supports, and what it does not

Supported (measured, delivered, checksummed):
* On an untouched panel of 30 arrangements that appear in no teaching template and
  no curriculum family, **neither curriculum exceeded chance** at 256 updates.
* **The owner's hypothesis was not supported at this budget**: varied practice did
  not separate the relationship from the surface — it did not beat repetition
  (+2.96 % pooled, 0/3 seeds with a positive interval) and it degraded
  performance on the original familiar records (12–14/30 versus 23/30).
* **More repetition is not the answer either**: control fresh accuracy did not
  improve from 64 to 256 updates (−4.8 % mean).
* The varied curriculum's own-worksheet learning was strong and consistent
  (27/30 in all three seeds), so the lesson design is learnable — it just does not
  transfer.

Not supported:
* No transfer claim, no curriculum-superiority claim, no composition or
  specialist claim. The earlier run-005 `7/12` remains a single-seed result on a
  previously examined 12-case panel.

## Retained artifacts

* `receipt_cas-meta2-graph6curr-20260910133000-aecb5d07/curriculum_result.json` —
  the full result (per-learner practice, own-curriculum and fresh measurements,
  learning curves, decisions, verdict).
* `receipt_cas-meta2-graph6curr-20260910133000-aecb5d07/checkpoints/` — **18 real
  checkpoint files** (initial, 64, 256 for each of six learners), each containing
  the model state, optimizer state, encoder projection, tokenizer vocabulary and
  configuration: `control_seed20260913_step000/064/256.pt` … `varied_seed20260915_step256.pt`.
