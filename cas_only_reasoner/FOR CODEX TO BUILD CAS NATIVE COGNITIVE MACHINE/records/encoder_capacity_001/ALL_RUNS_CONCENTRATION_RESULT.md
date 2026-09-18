# The concentration is six for six, every run converges on `W36`, and two explanations are dead

**Record:** `records/encoder_capacity_001/`
**Scripts:** `measure_all_runs_concentration.py` (output `all_runs_concentration.txt`),
`measure_target_prior.py` (output `target_prior.txt`)
**Spend:** $0.00. `torch` used only to deserialise the six runs' checkpoints. No device, no target
opened, no run launched.

---

## 1. The recorded concentration holds in all six runs

Read from each run's own `initial_predictions.json` and `final_predictions.json` — **the workers'
records, with nothing reconstructed**, so `RECONSTRUCTION_GAP.md` does not touch this table:

| receipt | arm | seed | cursor 0 | cursor 160 |
|---|---|---:|---|---|
| `receipt_20260917_a` | ALT | 17 | 27 distinct, W61 17.6%, 4.203 bits | **11 distinct, `W36` 60.0%, 2.184 bits** |
| `receipt_20260917_m` | MIX | 17 | 27 distinct, W61 17.6%, 4.203 bits | **11 distinct, `W36` 54.8%, 2.312 bits** |
| `receipt_20260918_a` | ALT | 18 | 18 distinct, W46 37.6%, 2.989 bits | **11 distinct, `W36` 49.0%, 2.540 bits** |
| `receipt_20260918_m` | MIX | 18 | 18 distinct, W46 37.6%, 2.989 bits | **10 distinct, `W36` 48.6%, 2.528 bits** |
| `receipt_20260919_a` | ALT | 19 | 26 distinct, W49 15.2%, 4.164 bits | **9 distinct, `W36` 47.6%, 2.354 bits** |
| `receipt_20260919_m` | MIX | 19 | 26 distinct, W49 15.2%, 4.164 bits | **9 distinct, `W36` 44.3%, 2.516 bits** |

*(uniform over 64 aliases would be 64 distinct, 1.6% commonest, 6.000 bits)*

**Two things the table gives for free, and both are consistency checks the data passes exactly:**

- **Within a seed, the two arms have byte-identical cursor-0 distributions.** 17_a and 17_m both give
  27 distinct / W61 / 17.6% / 4.203; 18_a and 18_m both give 18 / W46 / 37.6% / 2.989; 19_a and 19_m
  both give 26 / W49 / 15.2% / 4.164. The arm condition changes curriculum *order*, not initial
  weights, and the measurement shows exactly that.
- **Across seeds the cursor-0 distributions differ** — 27, 18 and 26 distinct aliases, with W61, W46
  and W49 as the commonest. The three initialisations really are different.

**And then all six converge on the same alias.** Three independent initialisations, two curriculum
orders, **one destination: `W36`**, at 44.3% to 60.0% of every world-typed reference slot.

## 2. The task-free concentration holds in all six runs too

210 pseudo-random unit vectors — inputs carrying no task information — through each run's
`initial.pt` and `final.pt`. The block, the recurrence and the frozen readout are exact for the saved
weights, so no encoder is involved:

| receipt | seed | cursor 0, depth 8 | cursor 160, depth 8 |
|---|---:|---|---|
| `…17_a` | 17 | 53 distinct, W24 5.7%, 5.454 bits | 27 distinct, W40 21.4%, 3.642 bits |
| `…17_m` | 17 | 53 distinct, W24 5.7%, 5.454 bits | 28 distinct, W47 20.0%, 3.721 bits |
| `…18_a` | 18 | 56 distinct, W56 4.8%, 5.584 bits | 31 distinct, W47 27.6%, 3.427 bits |
| `…18_m` | 18 | 56 distinct, W56 4.8%, 5.584 bits | 32 distinct, W40 27.6%, 3.520 bits |
| `…19_a` | 19 | 57 distinct, W36 4.8%, 5.535 bits | 28 distinct, W40 26.2%, 3.715 bits |
| `…19_m` | 19 | 57 distinct, W36 4.8%, 5.535 bits | 27 distinct, W40 25.2%, 3.752 bits |

**Training narrows the readout in every run** — from 53–57 distinct aliases to 27–32, and from
5.4–5.6 bits to 3.4–3.8 — on inputs it has never seen. The training effect `CONCENTRATION_SOURCE_RESULT.md`
found on one run is general.

**But the task-free commonest alias is `W40` or `W47`, not `W36`.** So the concentration and the
*particular destination* `W36` are two different facts, and the second is specific to the real inputs.

## 3. Two explanations of `W36`, both dead

The obvious explanation is that the training objective rewards raising the target symbol's rank, so a
block that outputs the **marginal prior** instead of reading its input scores well on average — and
would converge on the commonest target alias.

**Measured, from the run's own `schedule.batches` and the public course:**

| | presentations | distinct aliases | entropy | commonest |
|---|---:|---:|---:|---|
| every presentation across the 160 main batches | 1,152 | **24** | 4.547 bits | **W15** at 5.8% |
| the 564 distinct training packets | 564 | 24 | 4.574 bits | W35 at 4.6% |
| the registry the model is scored on | 564 | 24 | 4.574 bits | W35 at 4.6% |

> ## `W36` IS NOT A TRAINING TARGET AT ALL.
>
> It does not appear among the 24 distinct target aliases, in any batch, at any weight.

**The second candidate** is that `W36`'s readout row is simply what a *constant* output favours.
Measured:

| constant direction | argmax |
|---|---|
| all-ones | **W20** |
| mean of all 64 alias rows | **W37** |
| mean of the training target rows, unweighted | **W27** |
| mean of the training target rows, presentation-weighted | **W27** |

**None is `W36`.** Against the mean of all rows `W36` ranks **56th of 64**; against the mean of the
target rows it ranks **22nd of 64**.

**So the alias every run converges on is neither a target nor a plausible constant.** The
convergence is real, robust across six runs, and **unexplained**.

## What this changes

- **The concentration is no longer a one-run finding.** It holds in six of six, and so does the
  training effect behind it.
- **`W36` is a sharper object than "a collapse".** An alias the machine was never taught, never
  rewarded for, and which no constant direction favours, is the destination of three independent
  initialisations under two curricula. That is a stronger and stranger fact than the one it replaces.
- **The prior hypothesis is dead and the constant-direction hypothesis is dead**, both by direct
  measurement rather than argument.
- `records/MACHINE_STATE_001/STATUS.md` is updated.

## What is NOT established here

- **The convergence on `W36` still has no explanation.** Two candidates were eliminated; nothing
  replaced them. This record narrows the question and does not answer it.
- **Nothing was scored.** Concentration is a distributional fact; no error rate follows, and the
  targets are sealed. **A concentrated readout is not automatically a wrong one.**
- **The task-free measurements are exact for the block but say nothing about the course.** They
  isolate the parameters; they are not a claim about the task.
- **The training-target frequency is for `receipt_20260919_m`'s schedule.** The other five runs run
  the same 564 packets in different orders, so the 24-alias target set is the same, but the
  presentation weights were not recomputed per run.
- **The six runs are three seeds by two arms of one study**, not six independent studies.
- **No GPU work was launched.**
