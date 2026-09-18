# The architecture has exactly one composition mechanism, and it is hard-coded for one kind

**Record:** `records/encoder_capacity_001/`
**Script:** the attribution check in this record's commit (JSON only)
**Source read:** `cas_meta2/typed_teaching/slots.py`, `score_decisions`, lines 283–296
**Spend:** $0.00. Pure standard library. No torch, no device, no target opened.
**Corrects:** one clause of `ARGMAX_CHECK_RESULT.md`'s attribution.

---

## The mechanism, in full

```python
def score_decisions(packet, scores):
    """Deterministic scalar reference decoder, with no numeric package or teacher. ..."""
    plan = compile_slots(packet)
    _check_scores(plan, scores)
    if plan["kind"] != "correspondence":
        return _decision(plan, {slot["slot_id"]: max(slot["symbols"], key=lambda symbol: scores[slot["slot_id"]][symbol])
                                for slot in plan["slots"]})
    winner = max(_candidate_scores(plan, scores), key=lambda row: row["log_probability"])
    return _decision(plan, {}, winner["candidate_id"])
```

**Two branches, and nothing else.**

- **Every kind except `correspondence`** is decided by `max(slot["symbols"], key=score)` — a **plain
  independent per-slot argmax**.
- **`correspondence`** is decided by a **joint MAP over candidate bijections**: `_candidate_scores`
  computes, for each candidate, `log P(NO_MATCH) + log P(MAPPING) + Σ_pairs log P(pair score)`,
  normalised hierarchically, and takes the winner. `selected` is returned **empty** — the whole
  decision is a single `correspondence_candidate_id`.

**The architecture's only composition mechanism is three lines of a branch, and it is applied to
exactly one of the eight question kinds.**

## The attribution, now exact

Round 25 found 422 non-argmax `selected` values per run-file and attributed them to *"forced slots
and the joint correspondence candidate"*. **The joint candidate is right and "forced slots" is
wrong.** Measured, by kind, for `receipt_20260919_m`'s final predictions:

| kind | slots | mismatches | missing from `selected` | rate |
|---|---:|---:|---:|---:|
| **`correspondence`** | **422** | **422** | **422** | **100.00%** |
| `analogy` | 70 | 0 | 0 | 0.00% |
| `context` | 337 | 0 | 0 | 0.00% |
| `definition` | 210 | 0 | 0 | 0.00% |
| `edge_account` | 1,029 | 0 | 0 | 0.00% |
| `parts` | 207 | 0 | 0 | 0.00% |
| `reach` | 107 | 0 | 0 | 0.00% |
| `role_set` | 216 | 0 | 0 | 0.00% |

**Every mismatch is a `correspondence` slot, every one is *missing from* `selected`, and no other
kind contributes a single one.** The 422 figure is identical in all six runs and both prediction
files because the plan is identical — 88 correspondence questions × 5 slots, less the questions whose
candidate list has one entry.

**No forced slot is involved.** A forced slot has one symbol, so its argmax *is* that symbol and it
matches. That part of round 25's inference is withdrawn.

## Why this is the sharpest statement of the architectural gap so far

Put the branch beside the measured scores:

| | how the contract decides it | after teaching |
|---|---|---:|
| **`correspondence`** | **joint MAP over candidate bijections** | **93.18%** |
| `reach` | plain per-slot `max` | 75.70% |
| `parts` | plain per-slot `max` | 22.64% |
| `analogy` | plain per-slot `max` | 15.71% |
| `role_set` | plain per-slot `max` | 8.33% |
| `context` | plain per-slot `max` | **0.00%** |
| `definition` | plain per-slot `max` | **0.00%** |
| `edge_account` | plain per-slot `max` | **0.00%** |

And these figures hold in **all six runs** (`ALL_RUNS_RESULT.md`).

**The one kind the contract composes jointly is the one kind that works.** This is not an inference
from a correlation: it is a three-line branch in the code, and the kind on the composed side of it
scores 93.18% while the kinds on the independent side include all three that have never once been
answered in 1,260 attempts.

## What this does to Fix B

**Fix B is no longer an invention. It is the generalisation of a mechanism the contract already has,
already applies, and has already proven.**

The joint branch does exactly what `records/composition_layer_001/STATUS.md` proposes, in miniature:

1. form a **joint score over the whole answer** rather than a per-slot one — there, a hierarchical
   product of pair log-probabilities and mode priors;
2. take **one winner** for the entity the answer is about — there, a candidate bijection;
3. **assemble the rest from that winner** rather than deciding each part independently — there,
   `selected` is returned empty and the answer is built from the candidate id.

**And it answers the boundary question more sharply than OS-026 currently states it.** The question
is not *"should composition be added?"* — composition is already in the contract. The question is:

> **Should the joint decision that already exists for `correspondence` be extended to the kinds whose
> answers are readings of one entity?**

That is a much more answerable question, it is a question about an existing mechanism rather than a
proposed one, and it is still an authority decision. **OS-026 is restated in those terms.**

## What is NOT established here

- **Nothing was executed beyond reading recorded JSON and the source.** No forward pass, no device.
- **`correspondence`'s 93.18% is not shown to be *caused* by the joint branch.** The branch and the
  score are both facts; the causal link is an inference from the fact that it is the only kind on
  that side of the branch. No ablation was run and none is proposed here.
- **The other kinds' failures are not shown to be caused by the per-slot `max` either.** The
  decision-shape decomposition, the identification measurements and the composition analysis are the
  evidence for that, and they are separate from this reading.
- **`_candidate_scores`'s normalisation was read but not verified numerically.** What is quoted is
  the code's own structure.
- **One run's predictions** were tabulated by kind; the 422-per-file figure was verified identical
  across all six in `ARGMAX_CHECK_RESULT.md`.
- **No GPU work was launched.**
