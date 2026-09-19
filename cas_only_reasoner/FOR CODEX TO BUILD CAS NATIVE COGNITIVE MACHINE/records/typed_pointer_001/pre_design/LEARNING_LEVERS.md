# Getting the neurons to learn: what the receipts say

> Written 2026-09-19 at the owner's instruction — *"REMEMBER OUR MAIN GOAL IS GETTING THOSE NEURONS TO LEARN"* — which
> reframed this session's priority. All numbers are read from the practice study's own receipts
> (`records/typed_practice_001/receipt_<seed>/checkpoints/worker_report.json`) and from the registered contracts.
> $0, no torch, no AWS.

## 1. The machine was stopped while it was still learning

Mean raw batch loss per pass, seed 20260917:

```
pass  1  1.2879780873
pass  2  0.8253738100
pass  3  0.7057827289
pass  4  0.6303408602
pass  5  0.5676977850
pass  6  0.5173196002
pass  7  0.4782794501
pass  8  0.4447320951
pass  9  0.4170011747
pass 10  0.3981766156     ← still falling, every single pass
```

Ten passes was a **protocol choice, not convergence**, and the run used **5,465.811116 s of a 12,300 s deadline —
44.4 % of its budget — and stopped anyway.**

`MEASURED.` The last-batch loss fell from 0.3141852419 to 0.0720160812 over the same period.

## 2. A registered ceiling currently makes longer training impossible

| Quantity | Value | Source |
|---|---|---|
| `LEARNER_MAX_UPDATES_CEILING` | **2048** | `practice_contract.py:61` |
| the bound actually enforced | `main_updates + 16 <= 2048` | `practice_contract.py:171`, `PRACTICE_UPDATE_BOUND` |
| updates per pass | 147 | schedule |
| **maximum passes under the ceiling** | **13** (1,911 + 16 = 1,927) | arithmetic |
| 14 passes | 2,074 > 2,048 → **refused** | arithmetic |

`pointer_contract.py:66` currently inherits that ceiling unchanged:
`LEARNER_MAX_UPDATES_CEILING = practice.LEARNER_MAX_UPDATES_CEILING`.

**So the pointer study cannot train longer than 13 passes without a new registered ceiling.** This is a one-line
change — the pointer study is a new candidate and is entitled to its own registered limit — but it is a change that has
to be made deliberately and recorded, because the ceiling is part of the admission contract.

*(Note: `learner.py:94` carries a `max_updates <= 176` check, but that binds `TypedCourseLearner` (the matched study),
not the practice arm. The practice checkpoints record `max_updates: 1486`, well above 176, so the practice learner
overrides it. A `PointerCourseLearner` sets its own limits the same way.)*

## 3. Projecting how much training is left to gain

Successive drops in mean loss: −0.4626042773, −0.1195910811, −0.0754418687, −0.0626430752, −0.0503781848,
−0.0390401501, −0.0335473550, −0.0277309204, −0.0188245591. The drops decay at a mean ratio of about **0.77**.

Continuing that decay, the remaining reduction sums to roughly **−0.063**, so the loss would asymptote near **0.335**.

| passes | projected mean loss | share of the remaining reduction captured |
|---|---|---|
| 13 (the ceiling today) | ≈ 0.356 | ≈ 67 % |
| 20 | ≈ 0.340 | ≈ 93 % |
| beyond 25 | → 0.335 asymptote | — |

`ESTIMATE, not a measurement` — this is the OLD machine's decay curve extrapolated, and the pointer machine will have
its own. It is offered only to size the lever: **the difference between 10 passes and ~20 is roughly 93 % of the
training improvement that was still on the table versus 0 %.**

## 4. The neurons DID move on held-back data — the gate just cannot see it

This is the finding that matters most for the main goal. Per the practice receipts, correct answers out of 127
held-back records (records the machine never practised on) versus the question-level gate:

| seed | trained records | **held-back records** | held-back gate **questions** |
|---|---|---|---|
| 20260917 | 30 → 190 of 358 | **5 → 23 of 127** | 2 → 5 of 45 |
| 20260918 | 25 → 192 of 358 | **7 → 21 of 127** | 3 → 3 of 45 |
| 20260919 | 28 → 195 of 358 | **7 → 15 of 127** | 3 → 2 of 45 |

**Held-back record accuracy roughly tripled to quintupled (+18, +14, +8 records) while the question-level gate moved by
+3, 0 and −1.** The machine was learning something about worlds it had never practised on even through the broken
input, and the gate's unit of measurement could not see it.

`MEASURED.` The mechanism is arithmetic: a *question* is correct only when **all** of its records are correct, and
eligible questions carry 1, 3, 4 or 5 records (`records per eligible question: {1: 15, 3: 14, 4: 15, 5: 1}`). Requiring
every record of a 4- or 5-record question turns a real, visible per-record gain into an invisible per-question one.

## 5. What this implies for the goal, and what it does not

**Two changes, and neither weakens the gate:**

1. **Train to convergence, not to ten passes.** Raise the registered ceiling so the pointer study may run to roughly
   20 passes, sized from the smoke job's measured per-update cost, within the deadline and the owner's envelope. The
   old run left 55 % of its time budget unused while the loss was still falling; that is the cheapest available
   improvement to the neurons.
2. **Report held-back accuracy per RECORD as well as per question.** The per-question gate stays exactly as strict as
   the owner confirmed. The per-record figure is a second, reported number — never a label — and it is the number that
   shows whether the neurons moved. On the old input it showed a 3–5× improvement that the gate reported as nothing.

**What this does not do:** it does not make the relational tier easier, does not change the label, does not touch the
removals, and does not excuse a thin gate. Section 4 is a reason to *look* harder at learning, not a reason to grade
more leniently.

**And the honest caveat:** more training was not what the old machine lacked for *transfer* — the practice study showed
held-back questions flat-to-down across ten passes. The diagnosis was an input defect, and the pointer input is the
fix for that. Training length and input quality are separate levers and both are needed; neither substitutes for the
other.
