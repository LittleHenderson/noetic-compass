# PRACTICE_STUDY_RESULT — the neurons learn what they practise, and none of it reaches worlds they never practised

**Label, printed by `evaluate_gates.py` (the claim status is this label, not prose): `NO_TRANSFER_TO_NEW_WORLDS`.**
Flags: `trained_questions_rise_from_start: true`, `trained_questions_rise_with_more_practice: true`,
`more_practice_helps_new_worlds: false`. Integrity I0–I4: **PASS** (including I3, the same random start as
the matched study, in all three seeds).

Study: `docs/CNCM_TYPED_PRACTICE_STUDY_v0.1.md`, frozen at `c4f7c321` (package `daeb6497`,
`study.json` sha256 `0a329f32db44920773638d8b62cb1641b55ae592e41bc5a1d4bb7f274f37a3b6`). Gate reading:
`admission_001/gate_reading.json`. Receipts: `receipt_20260917/`, `receipt_20260918/`, `receipt_20260919/`
(also archived at `D:\tksCAS-archive\cncm_typed_practice_001_20260918`, 1,795 files, 0 mismatches).
Run log: `execute_study_log.txt`.

## What was asked

After ten passes of practice on 358 course records, do the neurons answer questions about **five worlds they
never practised on** — worlds with no look-alike anywhere in the bank, and never mentioned by any trained
record? Owner's words: *"IT MUST BE LEARNING LEARNING AT THE NEURON LEVEL."*

## What happened — per seed 20260917 / 20260918 / 20260919

**Questions** (a question counts as right only if every one of its records is right):

| | before training | after pass 1 | after pass 10 |
|---|---|---|---|
| **practised questions** (of 189) | 13 / 18 / 17 | 57 / 57 / 56 | **84 / 85 / 86** |
| **held-back gate questions** (of 45) | 2 / 3 / 3 | 4 / 4 / 2 | **5 / 3 / 2** |
| held-back shortcut questions (of 5; `reach` → `DIRECT`) | 0 / 2 / 1 | 1 / 1 / 2 | 5 / 5 / 5 |

**The gate tests** (per seed; b = wrong→right, c = right→wrong; pass needs b > c, exact p ≤ 0.01, gains in
≥ 2 kinds and ≥ 2 worlds):

| test | 20260917 | 20260918 | 20260919 | gate |
|---|---|---|---|---|
| `G_LEARN_p0_to_p10` (held, eligible 45) | b 5, c 2, p 0.227 | b 3, c 3, p 0.656 | b 2, c 3, p 0.812 | **FAIL** |
| `MORE_PRACTICE_p1_to_p10` (held, eligible 45) | b 5, c 4, p 0.5 | b 3, c 4, p 0.773 | b 1, c 1, p 0.75 | **FAIL** |
| `TRAINED_p0_to_p10` (practised, 189) | b 77, c 6, p 4.22e-17 | b 72, c 5, p 1.4e-16 | b 73, c 4, p 9.46e-18 | PASS |
| `TRAINED_p1_to_p10` (practised, 189) | b 35, c 8, p 2.1e-05 | b 35, c 7, p 7.55e-06 | b 35, c 5, p 6.91e-07 | PASS |

**Held-back by kind at pass 10:** `context`, `correspondence`, `definition` and `edge_account` are **0 in
every seed**. What moves is `reach` (5–8 questions, most of it the input-blind `DIRECT` shortcut), one
`analogy` question, and `parts`/`role_set` flickering between 0 and 2.

**Records** (reported, not gated): held back 5 / 7 / 7 → 23 / 21 / 15 of 127; practised 30 / 25 / 28 →
190 / 192 / 195 of 358. The held-back record rise is almost all the shortcut questions (5 questions, many
records each).

**Development panel** (59 new ten-node questions, cursors 0, 147, 294, 588, 882, 1,176, 1,470):
`[4, 3, 3, 4, 4, 4, 4]` / `[17, 3, 3, 4, 4, 4, 3]` / `[0, 3, 3, 5, 3, 3, 2]`. In seed 20260918 the
**untrained** start scored 17 of 59 and one pass of training took it to 3.

**Retention** (96 old-skill questions, before → after the interference interval): 56 → 50, 55 → 50, 55 → 53.

**Training loss per pass** (mean raw batch loss, seed 20260917): 1.2880, 0.8254, 0.7058, 0.6303, 0.5677,
0.5173, 0.4783, 0.4447, 0.4170, 0.3982 — still falling at pass 10 in all three seeds.

**Cost:** 18,171 s of instance time over three jobs (6,064 / 6,082 / 6,025 s), about **$12.72** at the
observed $2.52/hour; $45.00 reserved (no automatic refund). Worker time 5,466 / 5,476 / 5,451 s.

## What it means, in plain words

- **The neurons do learn.** Ten passes lift practised questions from about 16 to about 85 of 189, in every
  seed, with the loss still falling. That is real change in the 16,384 trainable weights.
- **What they learn does not carry over to worlds they never practised.** On the 45 held-back questions
  that no cheap constant answers, the machine is where it started (2–3 right before training, 2–5 after).
  Four question kinds stay at zero on held-back worlds in every seed.
- **The one thing that does carry over is an input-blind habit:** answer `reach` questions with `DIRECT`.
  It is right on 5 held-back questions for a reason that has nothing to do with reading the world — which is
  exactly why the gate set those questions aside before the run.
- **So, in this machine, practice produces memorisation of practised worlds, not a reading skill.** This is
  the owner's "only memorise" outcome, measured cleanly for the first time: the held-back worlds shared no
  shape, no mention and no answer with training.

## Claim status

- **REAL (negative, this configuration):** ten passes of practice raise accuracy on practised questions
  (84–86 of 189) and do **not** raise accuracy on questions about five never-practised, twin-free course
  worlds (`G_LEARN_p0_to_p10` FAIL in 3 of 3 seeds). Artifacts above.
- **REAL:** the learned gain on held-back worlds is confined to an input-blind prior (`reach` → `DIRECT`).
- **NOT LICENSED:** that this architecture family cannot learn to transfer; that more passes would not
  help (the loss was still falling); anything about other learning rates, the other teaching order, other
  plastic components, or the protected final study. Only this machine — frozen encoder, frozen `[90, 64]`
  readout, one 16,384-weight `^6` block, AdamW `lr 3e-3`, this course — was tested.
- **OPEN:** whether the trained block keeps what the encoder hands it (the 96.3758% linear-availability
  question). The initial, pass-1 and final checkpoints are in the receipts for that measurement.
