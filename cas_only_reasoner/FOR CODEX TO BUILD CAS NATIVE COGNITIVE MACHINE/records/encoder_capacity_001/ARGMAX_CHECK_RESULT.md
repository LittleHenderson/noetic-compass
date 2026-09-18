# Self-check: `selected` is the argmax of `scores` on every slot this record measures

**Record:** `records/encoder_capacity_001/`
**Script:** `check_selected_is_argmax.py` (output `selected_argmax_check.txt`)
**Spend:** $0.00. Pure standard library, JSON only. No torch, no device, no target opened.

---

## Why this check was overdue

Three rounds are built on reading `decisions.selected` out of the workers' prediction files and
treating it as **the readout's argmax**:

- `READOUT_COLLAPSE_RESULT.md` measured the concentration that way;
- `ALL_RUNS_CONCENTRATION_RESULT.md` extended it to all six runs;
- `measure_target_prior.py` eliminated two explanations of it on the same basis.

`_forward` writes `scores` as the raw logits and derives `decisions` through
`slots.score_decisions(packet, scores)`. The declared decision contract says *"argmax over each
slot's declared symbol order; first wins exact ties"* — **a claim about code, and this record was
treating it as a fact.** It had been spot checked once, on one slot, early on. Nothing had checked it
across the runs.

## The result

**All six runs, both prediction files, every slot — 31,176 slots:**

| receipt | file | slots | match | mismatch | **world-typed slots** | **wt match** |
|---|---|---:|---:|---:|---:|---:|
| all twelve file-runs, identical | | 2,598 | 2,176 | 422 | **210** | **210** |
| **TOTAL** | | **31,176** | 26,112 | 5,064 | **2,520** | **2,520** |

> **On the world-typed slots — the ones every concentration measurement uses — the recorded
> `selected` is the argmax of the recorded `scores` in 2,520 of 2,520 cases.**
>
> Every concentration figure in this record is measuring exactly what it claims.

**Zero ties** across all 31,176 slots, so the first-wins tie-break question does not arise.

## Where the 5,064 other mismatches are

| alphabet size | slots | mismatches | rate |
|---:|---:|---:|---:|
| 2 | 21,684 | 1,056 | **4.87%** |
| 3 | 828 | 648 | **78.26%** |
| 4 | 4,020 | 3,360 | **83.58%** |
| 5 | 336 | 0 | 0.00% |
| 6 | 948 | 0 | 0.00% |
| **64** | **2,520** | **0** | **0.00%** |
| 65 | 840 | 0 | 0.00% |

**The mismatches are confined to alphabet sizes 2, 3 and 4, and they are near-total at 3 and 4.**
Sizes 5, 6, 64 and 65 have none at all.

> **CORRECTED — see `COMPOSITION_BRANCH_RESULT.md`.** This record attributed the mismatches to
> *"forced slots and the **joint** correspondence candidate".* **The joint candidate is right; the
> forced slots are wrong.** Measured by kind, **every one of the 422 mismatches is a `correspondence`
> slot and every one is *missing from* `selected`** — no other kind contributes a single one, and a
> forced slot has one symbol whose argmax is itself, so it matches. The cause is
> `score_decisions` returning `selected = {}` for `correspondence` and putting the whole decision in
> `correspondence_candidate_id`.

Those are the slots the decision contract does **not** resolve by independent per-slot argmax —
forced slots and the **joint** correspondence candidate. `score_decisions` assigns the correspondence
mapping rows from a single joint candidate decision rather than row by row, so the per-row argmax is
simply not the rule there.

**The counts are identical in every run and every file** — 2,598 / 2,176 / 422 twelve times over —
because the **slot plan is identical across runs**. The mismatch pattern is a property of the plan,
not of any model. That is itself a small confirmation that the plan is deterministic and shared.

## What this adds beyond the check passing

**It locates the one place the architecture already composes, and it is the one kind that works.**

The decision-shape decomposition found that `correspondence` scores **93.18%** while every kind whose
answer is spread over independent per-slot decisions scores near zero. The decision contract explains
why: **correspondence is the one kind decided jointly rather than per-slot** — the same 422-slots-per-run
signature the table above exposes.

So this check does not merely confirm a measurement. It shows, in the workers' own recorded decisions,
that the machine's one successful composition case is implemented by a joint decision over a candidate
list, and that the other kinds receive no such treatment. **That is the decision-shape finding's
mechanism, visible in the contract's own behaviour.**

## What is NOT established here

- **Nothing was scored.** This compares two recorded fields against each other.
- **The rule that produces the mismatching `selected` values was not read.** They are attributed to
  forced slots and the joint correspondence candidate on the strength of the decision contract's
  description and the alphabet-size pattern. The code path in `score_decisions` was not traced for
  this record.
- **No claim that the non-argmax rule is right or wrong.** It is the declared contract's behaviour.
- **Only `decisions.selected` and `scores` were compared.** The assembled answers, the candidate ids
  and the correspondence decisions were not.
- **One study, six runs, one course.** The plan-identical property is specific to these runs.
- **No GPU work was launched.**
