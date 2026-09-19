# Independent re-derivation of rule R10, and a second no-learning policy it exposes

> Written 2026-09-19 by the orchestrating agent, HEAD `6cb0b348`. Read-only, $0, no torch. Re-derived from the leaks
> lens's own published caches (`lk_cache_packets.pkl`, `lk_cache_admissible.json`) rather than trusted, because R10
> drove a decision reversal.

**Script:** `verify_r10.py` in this directory.

## Verdict: R10 is confirmed exactly

Rule **R10** is *"the reach answer names the alphabetically-last node"* (node rank == highest), reading only the rank
flag and no adjacency. The lens reported it solves **4 of the 9** eligible held `reach` questions
(`lk2_single_flag_out.txt` lines 89-94). Re-derived: **4 of 9. AGREES.**

The nine eligible held `reach` questions, re-derived, with the highest-rank node of each focus world (`n3` in all nine)
and the admissible answers:

| question | records | admissible answer | R10 solves? |
|---|---|---|---|
| `…2f4fd46f` | 4 | `VIA n3` | **yes** |
| `…82157005` | 1 | `VIA n3` | **yes** |
| `…ed95f217` | 4 | `VIA n3` | **yes** |
| `…ac8b5d82` | 1 | `VIA n3` | **yes** |
| `…5c3f9e94` | 1 | `VIA n1` | no |
| `…8ff70695` | 4 | `VIA n1` | no |
| `…af68e2c7` | 4 | `VIA n1` | no |
| `…27bd014c` | 1 | `VIA n1` | no |
| `…da4b16f7` | 1 | `ABSENT` | no |

## The part the lens's table does not show: a constant answer also scores 4 of 9

Read the `admissible answer` column again. Every one of the nine answers is `VIA n3`, `VIA n1` or `ABSENT` — there is
no other value. Four questions want `n3`, four want `n1`, one wants `ABSENT`.

So **"always answer `VIA n1`" — a constant, reading nothing at all, not even the rank — also solves 4 of the 9**, on
the *complementary* set of questions to R10. Two different no-learning policies each score 4 of 9:

| policy | reads | solves | which questions |
|---|---|---|---|
| R10, rank == highest | the rank flag | 4 / 9 | the four `VIA n3` |
| constant `VIA n1` | **nothing** | 4 / 9 | the four `VIA n1` |
| R10 ∪ constant | — | **8 / 9** | all but the single `ABSENT` |

The reach answers in this course are strongly skewed toward two symbols. That is a property of the corpus, and the
project's own standing rule is that *a win is uninterpretable until it beats the cheapest method without the
mechanism*. A skewed prior is the cheapest method there is.

## Why this matters, and what it does not yet settle

- If the removal list registers **both** policies, the honest `reach` population collapses to **1 question** — the
  single `ABSENT`. With `analogy` 5 and `correspondence` 5, the whole relational tier would be **11**, against a floor
  of `b = 7` at `p ≤ 0.01`, in all three seeds, across ≥ 2 kinds and ≥ 2 worlds.
- It does **not** automatically follow that all eight must be removed. The gate is a **paired** test on discordant
  questions: a question the untrained machine already answers correctly at pass 0 cannot contribute a gain, so a
  prior the untrained machine happens to hold is partly absorbed by the design. What is *not* absorbed is the case
  this removal logic exists for — a machine that **learns** the trivial policy during training and gains those
  questions that way. That gain is real as arithmetic and empty as evidence.
- This is therefore a question for the **required-removals table**, which is exactly what lens A is building, and it
  must be decided on the paired-test arithmetic with `p0`'s actual answers in hand — not by me now, and not by
  guessing which of the two policies a trained machine would pick.

## Consequences recorded

1. `REVIEW_SYNTHESIS.md` §6 and §7 gain this second policy; the population table there is a floor, not a forecast.
2. The `reach` tier may be as small as 1 honest question, which would make it useless as a gate component and would
   leave the label resting on `analogy` and `correspondence` alone.
3. Any protocol that freezes a `reach` population without stating which no-learning policies were registered, and
   what each scores, is not audit-ready. The protocol must print this table.

**Claim state:** MEASURED, $0, re-derived from the lens's own caches. The R10 figure is confirmed; the constant-policy
figure is new here and is arithmetic on the same measured answers.
