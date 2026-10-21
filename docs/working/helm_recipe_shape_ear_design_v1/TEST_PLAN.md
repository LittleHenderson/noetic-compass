# Recipe-shape proposer ear — TEST PLAN (v1, 2026-10-20 PDT). Frozen before any package. Nothing run.

## 0. Order of work (each step needs the step before; steps 1-2 cost 0 USD and need no owner word)

1. **Census, laptop, counts only.** Run wide reader v5 over every ingredient line of the X-REAL recipe frames. Count
   lines READ cleanly, lines refused by code (`UNREAD_CLAUSE`, `AMOUNT_RELATIVE`, split failure, unit mismatch), per
   source. Floor for the gap stratum: **at least 4 x 64 = 256 refused lines in recipes with an ANSWER key** (the USE-1
   floor rule). Below the floor: STOP, `NOT_EXERCISED`, report; no package.
2. **Build + laptop tests** (shape schema, filler, pointer refusal, read-back, agreement rule with fake proposers).
3. **Sealed package + preregistration + custodian exam** (never seen by the builder) + **owner sign line with the zip
   sha256 and a cap**. Only then a GPU run.

## 1. Arms

| Arm | What | Why |
|---|---|---|
| A0 | wide reader v5 alone (asks on every gap line) | today's HELM |
| **A4E** | reader first + three-copy shape ear under the agreement rule, read-back, yes | the arm under test |
| A2E | reader first + copy-closest: the 3 training lines with the highest word overlap, each shape re-pointed to this line's spans, agreement rule | **mechanism-free baseline**: no learning, same rule |
| A4-s1..s3 | each copy alone, no vote | the "without the rule" control |
| C2E | three untrained copies under the rule | lock + checker + vote with no learning |
| REPLAY | A4E re-run on the same inputs | determinism |

## 2. Exams (custodian, builder blind; keys never reach the GPU host)

- **G-REAL (primary):** 128 real recipes from the gap stratum (every recipe has at least one line reader v5 refuses),
  keys by RB-W1T's frozen rules (fully learned / RIGHT / WRONG / UNDETERMINED), drawn from the census frame excluding
  every spent exam by id and text. Scored on the laptop by the RB-W1T scorer (`unexplained_ask`, lessons learned / wrong).
- **G-CONV:** 64 multi-turn dialogues from the wave-6 conversation generator with gap lines planted (RIGHT / WRONG / asks).
- **NO-HARM:** the six spent wave language exams and wave 6's X6v3 language files OFF, OFF-removed, ON: byte-identical
  records required.
- **Leakage:** any exam line whose text equals, contains or shares an 8-word run with a training line is excluded
  (CTT's rule). Census and overlap counts published; no text.

## 3. Hard gates (any one false = `FAILURE`)

| Gate | Rule |
|---|---|
| H-NUMBER | 0 digits and 0 name tokens in any ear output; every pointer resolves to a span of the sentence |
| H-WRONG-LESSON | 0 wrong lessons admitted in A4E (the brain's receipt may not be fooled by a wrong shape) |
| H-WRONG | WRONG answers in A4E = 0 (RB-W1T's K3) |
| H-CWFW | confident well-formed wrong shapes offered: A4E <= 2 per 128 recipes and <= A2E's |
| H-USED | 0 shapes used without a yes; every offered shape read back with every amount, unit and name quoted |
| H-NOHARM | OFF = OFF-removed = ON on every language exam |
| H-SEP | static separation: the ear imports only stdlib, torch and its own package; the brain never imports the ear |
| H-WRITE | audit-clean ear processes (A-CTT-2 rule) |
| H-VOTE / H-CUSTODY / H-NOFOREIGN | instrument rows as in CTT-2R |

## 4. Marks

| Mark | Rule |
|---|---|
| M-G1 | G-REAL fully learned: A4E - A0 >= 16 of 128 |
| M-G2 | A4E - A2E >= 8 (beat the no-learning rival) |
| M-G3 | A4E - C2E >= 16 |
| M-G4 | G-CONV RIGHT: A4E >= A0 + 4, WRONG 0 |
| R (reported) | reader-wrong count on the exam; agreement histogram; shapes refused by the filler |

## 5. Status words (frozen order; the reader stops at the first rule that fires)

1. instrument problem or any part `NOT_EXERCISED` -> `INSTRUMENT_ERROR`, `INCONCLUSIVE`;
2. any harm gate false -> `FAILURE`, `EAR_SHAPE_HARMED`;
3. all gates true, all marks held -> `PASS`, `EAR_SHAPE_EARNED_KEEP`;
4. all gates true, a mark missed -> `PASS`, `EAR_SHAPE_NO_GAIN`.
Spec-sheet words: `ENGINEERED-NOT-VALIDATED` unless word 3; `VACUOUS` for any `NOT_EXERCISED` part.

## 6. Honest predictions (written before any data)

- The census is the first risk: the gap stratum may be below 256 in recipes with an ANSWER key (the K4 line was 1 in
  128). `INCONCLUSIVE` by the floor: about 0.35.
- If exercised: `EAR_SHAPE_NO_GAIN` about 0.35 (A2E close behind; agreement silent), `EAR_SHAPE_HARMED` about 0.15
  (a shape that passes the filler but mislabels RAN_OUT, caught only by the receipt), `EAR_SHAPE_EARNED_KEEP` about 0.15.

## 7. Cost (for the later sign request; nothing is spent by this packet)

Three copies + twin + controls on one g5.xlarge: about 1.0-1.5 USD; scoring run about 0.3 USD. Proposed cap 2.00 USD,
one attempt + one plumbing retry. Laptop steps 0 USD.
