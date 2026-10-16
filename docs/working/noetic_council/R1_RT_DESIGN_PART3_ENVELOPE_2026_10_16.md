# R1-RT — design, part three: the run envelope

**Added:** 2026-10-16 PDT by the council's R1-RT turn. **Status:** DESIGN, PART THREE. The envelope
only: machine, window, cost, and what would make it cost more. It starts nothing, allocates nothing,
and spends nothing. Every figure below is derived from a measured unit or a named list price.

**This document does not authorise a run.** R1-RT's gate is *"W1's reading and the owner's word"*
and only half of it is met. Nothing here may be launched until the owner gives the other half.

---

## 1. What has to run, in measured units

Wave 1's own reading carries the wall-clock time of all 79 units it ran
(`R1_W1_READING.json` → `reported_only.R_COST.units_seconds`). They split cleanly by side:

| group | units | min | max | total |
|---|---|---|---|---|
| `TTB_*` transformer on Task B | 40 | 1,685.43 s | 2,482.01 s | **81,169.97 s** |
| `TGB_*` transformer on Gate B | 4 | 295.10 s | 1,572.40 s | **3,740.47 s** |
| `RTB_*` recipe on Task B | 11 | **0.37 s** | 127.12 s | **413.87 s** |
| `RGB_*` recipe on Gate B | 23 | **0.22 s** | 12.94 s | **25.55 s** |
| `RCCE_*` the CCE skin | 1 | 6.23 s | 6.23 s | **6.23 s** |

**The recipe side totals 445.65 seconds for 35 units. The transformer side totals 84,910.44 seconds
for 44 units — 190.5317 times as much, for four fewer units.**

R1-RT needs **only the recipe side**. It does not teach a transformer, does not re-run GB3, and does
not re-score wave 1's exam. On wave 1's own measured unit times, the work R1-RT must do is
**445.65 seconds**, and the units it actually needs — panel replays and a restart — are among the
cheapest: the fastest three are **0.22 s** each, and wave 1's own restart-replay unit
`RTB_A1_RESTART` is **0.37 s**.

## 2. The machine and the window

| item | value | where it comes from |
|---|---|---|
| machine | one **`m6i.xlarge`**, us-west-2 | the same instance type job R1-X0 ran on, from that job's own control record; and the runtime is CPU-only: the package sets `CUDA_VISIBLE_DEVICES=""` itself |
| list price | **`0.192` USD per host hour** | **read** from `aws-claude-r1x0-c33-control.json` → `hourly_usd`, the rate this account actually booked for an `m6i.xlarge` in `us-west-2`. Its own `components_usd` shows `compute_30min: 0.096`, which is `0.192` × ½ — the arithmetic checks itself |
| window | **60 minutes**, hard cut-off at 45 minutes with 15 minutes reserved for finalisation | the platform rule this project already uses: a finalisation reserve at the end, and the workload cut off before it |
| restart is cheap on the brain's side | **0.37 s** measured | `RTB_A1_RESTART` in wave 1 |

**Cost at list for the window as booked: 60 minutes × `0.192` = `0.192` USD.**
That is the number on the ledger if the machine runs its full hour. If it finishes in the measured
446 seconds instead, the real charge is about **`0.023768` USD** — because AWS bills the seconds
used, not the window booked.

**A rate correction, kept because the first draft got it wrong.** This document's first version used
`0.2089047012` USD per host hour and attributed it to jobs c21 and c23. **That figure is not the
booked rate for this account's `m6i.xlarge`.** The rate is **`0.192`**, read directly from the
R1-X0 control record, and the numbers above are re-derived from it.

## 3. The cap, and why it is larger than the estimate

| | amount |
|---|---|
| list estimate for the full booked window | **`0.192` USD** |
| list estimate for the measured work alone | about **`0.023768` USD** |
| **proposed cap** | **`2.00` USD**, one attempt, no retry |

The cap is roughly **ten and a half times** the booked-window estimate (`2.00 ÷ 0.192 = 10.4166666667`),
and that gap is deliberate. Three things could make this run cost more than its arithmetic says, and
none of them is visible until the run starts:

1. **The runtime has never been started with a non-neural brain.** It imports torch, builds a
   22,856-line module graph, and opens a SQLite store. The store's own start-up cost is
   **unmeasured** — no unit in wave 1 timed it, because wave 1 never opened it.
2. **The bridge does not exist yet.** Its cost is not in any unit time. The shim is small, but the
   `nn.Module` registration path inside a torch process has never carried a foreign brain.
3. **A wrong turn costs the window.** If the store's restart path turns out to be minutes rather than
   seconds, the run hits its cut-off and the machine bills for the window, not for the work.

**A cap is not an expectation.** The expectation is pennies. The cap is what the owner's ceiling has
to hold if the unexpected happens once.

## 4. What the envelope explicitly does not include

- **No transformer work.** No GB3 re-run, no teaching tick, no re-scoring of wave 1's exam. Those are
  the 84,910 seconds R1-RT does not pay for.
- **No new exam sealing.** Wave 1's fresh exam is already sealed, verified and backed up, and R1-RT
  scores on exposed worlds only — so it needs no custodian job and no new seal.
- **No backup job.** The run's own deliverable is small (wave 1's whole deliverable was 4,771,573
  bytes) and goes to the existing archive with the same three confirmations.
- **No second attempt.** One attempt per sealed package. A failure is a recorded failure, and a
  retest needs a new owner line.

## 5. What would make this envelope wrong

Stated so that a later reader can check the prediction rather than trust it:

| if this is true | the envelope must change |
|---|---|
| the store's start-up or restart path costs minutes, not seconds | the window stands, the machine may need to be larger, and the cap should rise — but the *measured* work is still 446 s, so the fix is the cut-off, not the budget |
| the runtime refuses to start without a neural checkpoint loaded | the design changes, not the envelope: shape 2 would need the checkpoint path stubbed, which is a package edit |
| the recipe brain's answer is wrong on the runtime's task | the run still completes and still reports; a wrong answer is a `FAILURE`, and failure is cheap |
| an interface defect passes all identity marks | `RT_NON_VACUOUS` catches it, and the reading is `INSTRUMENT_ERROR`, which is the honest outcome and still costs the same pennies |

## 6. The one-line summary for the owner

**One `m6i.xlarge`, 60-minute window, cap 2.00 USD, one attempt, expectation about 2.38 cents.**

And nothing starts until he chooses the shape.

## 7. Every figure in this document, with its source

| figure | value | source |
|---|---|---|
| recipe-side unit total | `445.65` s over 35 units | `R1_W1_READING.json` → `reported_only.R_COST.units_seconds` |
| transformer-side unit total | `84,910.44` s over 44 units | same field |
| their ratio | `190.5317` | computed here |
| `RTB_A1_RESTART` | `0.37` s | same field |
| fastest units | `0.22` s (three-way tie) | same field |
| `m6i.xlarge` hourly rate | `0.192` USD | `aws-claude-r1x0-c33-control.json` → `hourly_usd` |
| the rate's own cross-check | `compute_30min: 0.096` = `0.192` × ½ | same file → `components_usd` |
| booked-window cost | `0.192` USD | `0.192` × 1 hour |
| measured-work cost | `0.023768` USD | `445.65 ÷ 3600 × 0.192` |
| cap ÷ booked window | `10.4166666667` | computed here |
| wave 1's deliverable size | `4,771,573` bytes | `DOWNLOADED_pointer-saturation-deliverable.zip` |
| wave 1's machines and job | `m6i.8xlarge`, `us-west-2`, job `helm-claude-r1-w1-20261016-c34-g` | spec sheet §7.47 |
