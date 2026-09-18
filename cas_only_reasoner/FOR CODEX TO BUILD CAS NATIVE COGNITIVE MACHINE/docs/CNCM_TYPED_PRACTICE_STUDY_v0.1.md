# CNCM typed practice study v0.1 — does more practice teach the neurons, on worlds they never practised?

**Status:** FROZEN BEFORE THE FIRST RUN. Its sha256 is pinned into the study admission.
**Owner approval, 2026-09-18.** Asked *"Which AWS experiment should I build and launch first? Your
choice will be recorded as the signed approval for it."*, the owner selected **"Practice test
(Recommended)"**, whose stated terms were: *"Same machine, same random start, 10x more practice (1,600
updates instead of 160). One in five practice questions is held back and never trained on, so we see
whether the neurons LEARN (score rises on held-back questions) or only memorise. Plus the 59
new-question panel and the old-skills panel. 3 seeds, one after another, ~3 hours and ~$7.50 each;
reserve up to $45."* The same words are recorded verbatim in every job's `owner.json`.

**Owner ruling in force (2026-09-18):** *"IT MUST BE LEARNING LEARNING AT THE NEURON LEVEL."* Only what
training changes in the plastic weights counts. No rule layer, fitted readout or hand-computed weight
enters this study.

## 0. What changed from the first draft, and why (before anything was frozen or run)

A first draft held back one question in five by `query_id`. An adversarial pre-flight review
(`records/typed_practice_001/PREFLIGHT_REVIEW.md`) showed that "never trained on" was then false in
substance, and that the gate could print a learning result on memorisation:

- **rule twins:** 16 held records had a trained twin posing the same question about the same world under
  another rule; 12 shared the answer;
- **answers in worked supports:** 26 of the 51 held questions sat, with their correct answers, as worked
  supports inside 132 trained records, every pass;
- **a same-world answer prior** alone got 14 of 28 held `reach` records right;
- **the wrong unit:** records of one question move together and the three seeds are near-copies, so a
  record-level pooled test could pass on a single question.

It also found two run-killers in the build (a growing log file meeting the create-only evidence publisher,
and a wait loop that ended a healthy job on one network error). A **second** review of a world-level redesign
then found three more channels: a held world with an identical-shape **trained twin** (its answers transfer
by node position), trained **analogy answers naming held worlds** (a reverse lookup), and worked supports
reaching held worlds through their **arguments and answers**. All are fixed below. Holding back whole
**twin-free worlds**, and excluding every record that mentions one, keeps the owner's terms — about one
question in five, never trained on — and makes them true.

## 1. What is held fixed

The machine is the matched study's, unchanged: frozen encoder (seed `20260916`), frozen `[90, 64]`
readout, the one plastic `^6` block (16,384 weights), AdamW `lr 3e-3`, `wd 0.01`, the registered loss,
recurrence and decoder. The random start is the matched study's, per model seed (`20260917`,
`20260918`, `20260919`). Teaching order: `MIXED_SAME_ITEMS`.

`cas_meta2/typed_teaching/practice_learner.py` subclasses the registered learner and changes **only**
two ceilings — updates `176 → 2048`, wall seconds `3600 → 14400` — and records itself in the run
identity. The registered learner file is not modified.

## 2. What changes

- **Five whole worlds held back, by four frozen rules** (`records/typed_practice_001/holdout_audit.py`
  derives them; a test re-derives them with the answer checker): (1) only course worlds with **no shape
  twin anywhere in the 64-world bank** are eligible — 12 of 24; (2) a world's exposure is every other-world
  record that **mentions it anywhere** (query, arguments, cue, instruction, worked supports) **or whose
  correct answers name it**; (3) the five eligible worlds with the smallest exposure, ties by world id;
  (4) every exposure record is excluded from training. Result: `world-22704554…`, `world-28f61f2d…`,
  `world-4090ec49…`, `world-6e1fcbda…`, `world-98c6352d…` — **127 records, 50 questions, all eight kinds**
  (analogy 17, context 17, correspondence 20, definition 15, edge_account 17, parts 9, reach 26, role_set 6
  records).
- **79 records excluded** from training (73 mention a held world in their text; 6 only through their
  correct analogy answers); neither trained nor gated. **358 records trained**, all eight kinds.
- No trained record mentions a held world anywhere in its text, and none has a correct answer that names
  one — checked in `practice_contract.split` and in the tests. The worker never reads a correct answer
  before training: the split is frozen as constants in the contract.
- **Ten passes** over the 358 trained records: **147 updates per pass, 1,470 main updates**, then 16
  interference updates (trained records only) and 2 validation replays = **1,488**. Every trained question
  gets ten times its single-pass practice; the total is below 1,600 only because 36% of records are held or
  excluded.
- **Measured** before training and after passes 1, 2, 4, 6, 8, 10 on the held-back records and the
  59-question development panel; the full course at passes 0, 1 and 10; retention before and after
  interference, split into held-world and trained-world records.

## 3. Money and time

One `g7.2xlarge` at the observed $2.52/hour, jobs one after another (8-vCPU quota: one at a time).
Estimated worker time ~1.5 h per job (3.43 s per update, measured on the matched runs). Envelope per job:
worker deadline 12,300 s < numeric child 12,600 s < outer bound 13,500 s < guest watchdog 14,100 s <
launcher wait 14,400 s. Reservation **$15.00 per job** (4 h × $2.52 + $1.48 = $11.56, rounded up),
**$45.00 for three**, the owner's cap. No automatic retries; the study stops on the first failed job.
Note: the inherited lifecycle's receipts record its generic `$7.00 / 7,200 s` scope in
`reservation_scope` and `permit.resource_plan`; the authoritative figures are the ledger entry's
`reserved_usd` (15.00) and `plan.runtime_seconds_max` (14,400).

## 4. Frozen predictions (predictions, not gates)

- **P1 — practised questions rise.** Trained questions improve from pass 0 to pass 10. *Confidence: high.*
- **P2 — held-back worlds.** **No confident prediction.** The in-course failures are shared across worlds
  and the development panel (new, larger worlds) has always scored `0/59`; either outcome is informative.
- **P3 — development panel** stays at or near `0/59`. *Confidence: moderate-high.*
- **P4 — retention** falls across the interference interval, as in all six matched runs.

## 5. Hard gates — read by `records/typed_practice_001/evaluate_gates.py`, not by prose

**Unit: a question** (`query_id`), correct at a checkpoint only if **every** one of its records is correct.

**Integrity — any failure makes the study `VOID`:**

| gate | condition |
|---|---|
| **I0** | the study has exactly the three seeds |
| **I1** | every job `completed_deliverable`, cleanup complete, worker status `COMPLETE_TYPED_PRACTICE_ARM`, every expected artifact present, every scoring file readable |
| **I2** | held and excluded ids equal the frozen split; every record in every main and interference batch log is a trained record; 1,470 + 16 logged updates |
| **I3** | same random start: each job's initial `model_state_identity` equals the matched study's initial checkpoint for the same seed (`receipt_<seed>_m`) |
| **I4** | per job 1,470 main, 16 interference and 2 replay updates; reloads and replays exact |

**Mechanism-free shortcut, registered before the run.** For each kind, the most common trained answer
written in the learner's own output symbols — worlds as their global `W` aliases, nodes as their per-world
`N` aliases — ties by text. It is the best single answer the machine could give while ignoring the input.
It answers **5** of the 50 held questions (all `reach` → `DIRECT`). The gate uses the other **45**
("eligible") questions, which cover all eight kinds and all five held worlds (8–10 each). Answering a
`definition` question with the focus world's own references is the task's rule, not a shortcut.

**Primary — `G_LEARN_p0_to_p10`, the answer to the owner's question.** In **each seed separately**, over
the 45 eligible held questions: `b` = wrong before training, right after pass 10; `c` = the reverse.
The seed passes iff `b > c`, the one-sided exact binomial `P(X ≥ b | n = b + c, p = 1/2) ≤ 0.01`, and the
improved questions span **at least two kinds and at least two held worlds**. **The gate passes only if all
three seeds pass.** (With `c = 0` a seed needs at least 7 improved questions.)

**Secondary, same test, reported as flags:** `MORE_PRACTICE_p1_to_p10` (eligible held questions, pass 1
to pass 10); `TRAINED_p0_to_p10` and `TRAINED_p1_to_p10` (trained questions).

**Reported, not gated:** record-level counts; every checkpoint's held counts; the 5 shortcut questions;
per-kind and per-world tables; development; retention by side; per-pass training loss.

## 6. The outcome label — one deterministic reading

| label | when |
|---|---|
| `VOID` | any of I0–I4 fails |
| `LEARNS_NEW_WORLDS` | `G_LEARN_p0_to_p10` passes |
| `NO_TRANSFER_TO_NEW_WORLDS` | it fails |

Flags accompany the label: `more_practice_helps_new_worlds`, `trained_questions_rise_from_start`,
`trained_questions_rise_with_more_practice`. Claim status follows the label and nothing else.
`LEARNS_NEW_WORLDS` would make **REAL**: *after training on other worlds, the neurons answer correctly
questions about five course worlds they never practised on, beyond a registered shortcut, in each of three
seeds.* It would **not** license claims about the development panel, the protected final study, the CAS
architecture, or worlds of other sizes. A failed gate is a **FAILURE**, never "PASS with caveats".
Negative results are kept.

## 7. Limits this design does not remove

- **Same-size, same-bank worlds.** Held worlds have the sizes and question kinds of trained ones and no
  exact twin, but they share partial structure with trained worlds (star centres, chain positions); a
  layout-level habit learned on one world can be right on another. That is a kind of generalisation, and it
  is not "reading a new world from scratch". Every input also carries the whole 64-world bank, so the
  held worlds' declarations are visible in every training input; what is withheld is practice on questions
  about them.
- **Questions about one world move together.** The gate requires gains in two worlds and two kinds, but it
  does not model world-level clustering; a world-resampled check is a later analysis.
- **Three seeds are replications, not independent samples of questions.**
- **Whether the neurons keep what the encoder gives them** (the 96.3758% linear-availability question) is
  not measured here; the initial, pass-1 and final checkpoints are saved for a later measurement.
- Anything about the other teaching order, other learning rates, or architecture changes.
