# Faculties — wondering, pondering, imagination, self-notice, over a held buffer

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\faculties\`.
This is the RB-I faculties layer from `helm_rb_i_faculties_design_v1` (written 2026-10-15, marked
**DESIGN ONLY. NOT BUILT**), now built and tested. Standard library only. No torch, no numpy,
no network, no cloud, no spend.

## The claim ceiling

Verbatim, and it is the whole ceiling:

```
MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
```

## The guardrail is the spine of this build

The design states one rule, in its own words (FACULTIES.md section 1, from the panel's verdict):

> randomness may only propose; the verifier, the receipts and the RPM Gate always decide.

and (FACULTIES.md section 2.4, Rule P):

> imagination may propose candidates, but imagined data may never verify a candidate or change
> what the brain believes.

Everything in this package is arranged so that sentence cannot be broken through the front
door. Not "checked and refused". The shapes make it unreachable. Four walls:

1. **Imagined evidence is a different type from real evidence, and not a smaller version of it.**
   `guard.RealEvidence` and `guard.ImaginedEvidence` are siblings. Neither inherits from the
   other, so `isinstance(imagined, RealEvidence)` is `False` and no `isinstance` test anywhere
   can be talked into reading one as the other. The verifier takes `RealEvidence`, so an
   imagined world's rows have **no route into a verification call at all** — not blocked by a
   flag, blocked by the type of the argument. `guard.verify` refuses the imagined type with
   `IMAGINED_EVIDENCE_CANNOT_VERIFY` **before it looks at the checker**; the test instruments
   the checker and proves it was never called. And the imagined type does not have the
   `canonical_forms` reader the default checker reads, so even a copy of `guard.py` with every
   type check deleted cannot get imagined data through that checker — which the test shows by
   building exactly that broken copy and watching it fail at the reader.
2. **Real evidence refuses an `INTERNAL` row.** Every row is tagged `REAL` or `INTERNAL`.
   `RealEvidence` refuses an `INTERNAL` row with the design's own code,
   `REFUSE:INTERNAL_WITNESS`, so a daydream's rows cannot be laundered into real evidence by
   building a `RealEvidence` around them. And `ImaginedEvidence` refuses a `REAL` row, so it
   cannot carry a real witness even by accident.
3. **A verdict cannot be made by hand.** `guard.verify` mints the only verdicts. `Verdict`'s
   constructor demands a sealed token that exists only as a private name inside `guard.py`, and
   `is_verdict` re-checks the seal, so an object built with `object.__new__` is not a verdict.
   The held buffer accepts nothing else to move a candidate out of `HELD`.
4. **One door to the Bias, and faculties are not it.** A faculty is handed
   `guard.BiasReading`, which has no `write` method to refuse (there is no method). The copied
   `Bias` itself refuses any writer named `FACULTY:<name>`. `guard.check_faculty_return` refuses
   a return value carrying a Bias write, a verdict, an admission, or evidence. And
   `guard.believe` — the only function in the package that calls `Bias.write` — refuses
   anything but an `ADMITTED` verdict minted on real evidence.

The test file proves each wall separately, and also proves the walls are not vacuous: an
admission on **real** evidence does reach the Bias, both through `guard.believe` and through
the drive loop's own write step.

A test that cannot fail proves nothing, so there is one more case. It builds a copy of
`guard.py` in memory with the two type checks deliberately broken. That broken copy does hand
an imagined world to a checker — the exact event the wall exists to prevent — and with a
permissive checker it admits the candidate. The default checker still refuses it, because the
imagined type has no `canonical_forms` to read. And the check used in the real test reports the
broken copy as broken, so the guardrail's own test is known to be able to fail.

## What the tests prove

37 cases, all passing, printed one line each. The ones that carry the claim:

| case | what it settles |
| --- | --- |
| `test_a_faculty_writes_held_and_nothing_else` | all four faculties write `HELD` and no other state |
| `test_a_direct_admitted_write_is_refused` | a candidate claiming `ADMITTED`, `REFUSED` or `EXPIRED` is refused at the door |
| `test_no_faculty_can_write_the_bias` | three walls: the reading has no `write`, the Bias refuses `FACULTY:<name>`, the belief door refuses a faculty |
| `test_imagined_evidence_cannot_be_passed_to_the_verifier_at_all` | sibling types, the refusal code, and a checker proven never to run |
| `test_the_guardrail_test_can_fail` | the check above catches a deliberately broken copy of `guard.py` |
| `test_a_daydream_stays_a_daydream_until_real_evidence_verifies_it` | `DAYDREAM` until a real verdict, then `INSIGHT` |
| `test_a_daydream_that_is_never_verified_never_changes_what_the_brain_believes` | twelve ticks of daydreams and imagined evidence leave the Bias at version 0 with an unchanged digest |
| `test_pondering_refuses_a_tick_with_input_queued` and `test_the_drive_loop_never_runs_pondering_on_a_tick_with_input` | pondering runs only when idle, in the faculty and in the loop |
| `test_self_notice_records_one_receipt_per_nesting_level` | one receipt per level, and the labels spell `^8->^9 . ^6 . ^0` |
| `test_the_held_buffer_never_loses_a_refused_or_expired_candidate` | every candidate stays, in all four states, with its history |
| `test_the_drive_loop_is_deterministic_for_the_same_inputs` | identical records, buffer and Bias for the same inputs, for all four arms; and a different seed does change the order |

## The faculties, one line each

| faculty | one line | design label |
| --- | --- | --- |
| `wondering` | Surfaces a related candidate into the **held** buffer. It is not accepted as true. | `^8->^9` |
| `pondering` | During idle time, breaks down unexplained **real** data by binding cell and tries fitting it again; every refit lands `HELD`. | `^6` |
| `imagination` | Builds and simulates hypothetical worlds and files each recipe as a **daydream** (`DAYDREAM`) until real evidence verifies it. | `^0` |
| `self_notice` | Runs one faculty inside another and records a receipt at each level. | (nesting operator; no Noetic label claimed) |

Each returns a `FacultyReport` that has already passed `guard.check_faculty_return`. Each takes
a Bias and immediately narrows it to a `BiasReading`. None of them can write anything but
`HELD`, and none of them can write the Bias.

**Contemplation is not a faculty** in the design, so it is not one here. The design's nearest
concepts are pondering (FACULTIES.md 2.3) and self-notice (FACULTIES.md 2.5), and inventing a
sixth faculty would invent a claim. A test fails if a fifth faculty name appears.

The design labels (`^8->^9`, `^6`, `^0`) are recorded as text. They score nothing and they are
not compiled `Φ<...>` words: CAS_MAPPING.md section 4 lists that spelling as an open builder
check, so no record here contains a `Φ` word.

## The held buffer

One store, four states, and nothing is ever deleted:

| state | what it means | who can set it |
| --- | --- | --- |
| `HELD` | a faculty put it here; there is no evidence about it yet | the faculty door `put()`, and nothing else |
| `ADMITTED` | a real verdict admitted it | the verifier door `settle()`, with a sealed verdict |
| `REFUSED` | a real verdict refused it, with a code | the verifier door `settle()` |
| `EXPIRED` | the age cap or the capacity cap reached it | the consolidator door `expire()`, and expiry can produce nothing else |

A candidate that was refused or expired **stays in the buffer** with its whole history.
`entries()` returns every candidate ever put in, in order. Every move records who moved it
(`FACULTY`, `VERIFIER`, `CONSOLIDATOR`), that writer's name, its `phi` when it has one, a reason
word and the verdict's code.

Two labels ride on a candidate. `DAYDREAM` is written by imagination and by nothing else.
`INSIGHT` is written only by the buffer, only on an admission, and only for a candidate that
came in as a daydream — FACULTIES.md 2.4: "an insight = an imagined recipe later admitted on
real rows". Nothing else in this build is called an insight, and no faculty may label anything
`INSIGHT` (the proposal constructor refuses it).

## The drive loop: when each faculty gets a turn

The tick runs the design's order (ARCHITECTURE.md section 1 steps 0-8): INPUT, SENSE, MEASURE,
MASK, ARBITRATE, ACT, VERIFY, WRITE, LOG. Then the consolidator's expiry step when the caller
names a cap.

- **Masks.** A drive with no available action is masked and the record says
  `DRIVE_DEPRIORITIZED:<drive>` with the reason. It is never given invented work.
- **Guards then arm.** Masked → pair cap (dial = 10·pull, more than 4 apart restricts the tick
  to the higher-pull member) → max neglect (24 ticks) → dwell (2 ticks) → the arm.
- **Four arms, deterministic for the same inputs:** `GREEDY`, `ROUND_ROBIN`, `FIXED_PRIORITY` (`F7, F6, F2, F5,
  F4, F1, F3`), and `PULL_SAMPLING` — the owner's "oscillating random", a seeded integer draw
  over the exact pulls, whose seed counts as one of the inputs. That draw is the only random
  step in the package, it can only pick which drive acts, and the seed is recorded. It cannot
  write a candidate, a verdict, a belief or a gain.
- **Idle triggers pondering.** Idle means no new input queued on this tick. Pondering is F7's
  idle-time action, so on a tick with input F7 is masked and pondering is unreachable — the loop
  cannot ponder while busy, and the record shows `PONDERING_RUNS_ONLY_WHEN_IDLE`.
- **Every turn is recorded.** A `TurnRecord` per tick: the tick, the idle flag, the arm, the
  masked drives, the guards that fired, the focus drive, the faculty, what it wrote, what was
  verified, what reached the Bias, what expired, the draws made, the gains and the
  satisfactions. A tick where every drive is masked is recorded too
  (`NO_UNMASKED_DRIVE`).
- **Determinism.** Satisfactions are exact `Fraction`s, the order is a fixed tuple, and the
  digests of the records, the buffer and the Bias match on a second identical run. The test also
  proves the determinism is not by accident: a different seed reorders the seeded arm.

## What this build does not contain

Each line is a whole piece of the design that is **not here**. This list is the honest ceiling.

1. **No fitter, no writer, no recipe book.** F7's "fit on the current Ω" is absent, so
   pondering's measured gain is 0 and the tick says `GAIN_NOT_MEASURABLE_WITHOUT_A_FITTER`.
2. **No faculty for F1, F2, F3, F4 or F6.** Curiosity, asking, integration, consolidation as a
   faculty turn, and verify-as-a-drive-action are not built. Those drives are masked every tick
   with `NO_FACULTY_IN_THIS_BUILD`, which is exactly what the design says to do with a drive
   that has no available action.
3. **No grammar, no shape algebra, no simulated world.** `imagination` takes a world builder and
   writes what it returns. It does not generate worlds.
4. **No restart fallback.** `pondering` takes a refit callable. RB-C4's fallback (the one slot
   with a measured keep) is not copied in.
5. **No Fisher-Rao anything.** No restlessness, no distance to the barycentre, no FIXATION or
   THRASH flags, no `GEODESIC-STEP` arm, and no stage (16-tick) F/E checks. DRIVE_LOOP.md
   section 6 asks for all of it; none of it is here.
6. **No Lacunarity Machine, no stored residual store, no question ledger, no path log.** The
   loop's SENSE step is the idle flag and nothing else.
7. **No readout.** Test plan H5 requires that the readout reads the buffer 0 times. There is no
   readout in this build to read it.
8. **No run, no world, no family, no model.** No faculty has run inside HELM. Every case in the
   suite is a mechanism check on inputs the suite supplies.

## How to run it

```
cd C:\Users\wakil\Documents\Codex\2026-10-16\faculties
python -B test_all.py
```

One line per case, then a total. Exit code 0 when every case passes, 1 when any fails. No
pytest, no files written, no network.

## The undecided lines

Every point the design does not settle is marked in the code with
`# UNDECIDED IN DESIGN: <question>` and is listed below word for word, with the reading this
build took. A test reads the markers out of the code and fails if one is missing here, or if
this list carries one that the code does not. The two lists cannot drift apart.

- UNDECIDED IN DESIGN: whether the support mark for admitting a faculty's candidate is the LSR-T4 8-new-rows mark -- DEFINITION.md section 2 U-c names "the 8-new-rows support mark of LSR-T4" for VERIFY and RB-I never states whether a candidate born in the held buffer must clear the same number, so this build applies 8 and lets a caller override it.
- UNDECIDED IN DESIGN: how many candidates the buffer may hold and whether the cap counts only HELD or every state -- ARCHITECTURE.md section 3 gives "64 HELD; oldest-first expiry, logged" as PROPOSED and FACULTIES.md never states a capacity, so this build defaults to no cap, counts HELD only when a cap is named, and refuses nothing that it cannot log.
- UNDECIDED IN DESIGN: what the age cap is, in ticks or in entries -- FACULTIES.md section 2.2 lists "EXPIRED (age cap, logged, never silently dropped)" and gives no number and no unit, so this build requires the caller to name it and refuses with HELD_CAP_NOT_NAMED rather than pick one.
- UNDECIDED IN DESIGN: whether an expired or refused candidate may be revised and re-proposed as itself -- FACULTIES.md gives the four states and no route back out of REFUSED or EXPIRED, so this build keeps the old record for ever and every re-proposal enters as a new candidate with a new id.
- UNDECIDED IN DESIGN: whether a daydream keeps its DAYDREAM label after a refusal -- FACULTIES.md section 2.4 defines a daydream as a world or recipe "never confirmed by real rows", and a refused candidate was never confirmed, so this build leaves the label DAYDREAM on refusal and changes it to INSIGHT only on admission.
- UNDECIDED IN DESIGN: whether the faculty checks "idle" itself or the drive loop guarantees it -- FACULTIES.md section 2.3 says the pass "runs only when no new input is queued" and does not say who decides that, so this build requires the Unexplained record to say it is idle and refuses PONDERING_RUNS_ONLY_WHEN_IDLE when it says otherwise, while the drive loop separately never calls pondering on a tick with queued input.
- UNDECIDED IN DESIGN: how the residual rows are ordered within and between binding cells -- FACULTIES.md section 2.3 says pondering "decomposes the residual rows by which cell binds them" and gives no tie order, so this build sorts groups by cell name and rows by row id, which makes the pass byte-reproducible.
- UNDECIDED IN DESIGN: how many grammar draws imagination takes per F5 tick -- FACULTIES.md section 2.4 gives "K seeded grammar draws per F5 tick (K PROPOSED 8, as LSR-T7/RB-C4)", a PROPOSED number the owner has not accepted, so this build draws nothing itself and takes whatever worlds the caller's builder returns, recording K as given.
- UNDECIDED IN DESIGN: whether an imagined world may be built out of rows another imagined world produced -- FACULTIES.md section 2.4 says a world is built from the book and does not say whether a daydream may be a premise, so this build refuses a world whose rows are not tagged INTERNAL and does not look at where INTERNAL rows came from, which leaves the question open rather than answering it.
- UNDECIDED IN DESIGN: what a per-level receipt must contain -- Chapter 27's Theorem 27.3 states that epsilon(n) after eta(n) equals the identity at every depth independently and FACULTIES.md section 2.5 says "every level carries its own receipt" without saying what it records, so this build records the faculty, the candidates it wrote, the forms it said it wrote, and the re-read result of an actual read-back of the buffer.
- UNDECIDED IN DESIGN: what a failed inner level does to the candidates it already wrote -- FACULTIES.md section 2.5 says "a failed receipt at level n invalidates every parent" and does not say whether the already-written candidates are withdrawn, marked or left, so this build leaves them in the buffer (nothing here deletes a candidate) and refuses to record any parent level.
- UNDECIDED IN DESIGN: whether the exact Phi word may be written into a record -- CAS_MAPPING.md section 4 lists "the exact Phi<...> spelling must be compiled in the site compiler (464fd4ad) before any Phi word is written into a record" as an open builder check, so this build records each faculty's design label (for example ^8->^9) and never a compiled Phi word.
- UNDECIDED IN DESIGN: whether "idle" is read per tick or per stage -- FACULTIES.md 2.3 and DRIVE_LOOP.md 2 say the pass runs when "no new input is queued" and give no window, so this build reads it per tick: a tick with an empty input queue is idle, and the next tick with input is not.
- UNDECIDED IN DESIGN: which drive owns pondering and whether wondering is a turn of its own -- ARCHITECTURE.md section 2 puts "imagine + wonder" under F5 and "fit on current Omega; else ponder" under F7, and never says whether wondering is a separate turn or a step nested inside the F5 turn, so this build nests wondering inside the F5 turn with one level receipt per level and gives pondering the F7 turn.
- UNDECIDED IN DESIGN: what gain a faculty earns when the measured outcome needs a fitter this build does not contain -- DRIVE_LOOP.md section 2 defines F7's gain as unexplained rows before minus after and FACULTIES.md leaves the fit outside the faculty, so with no fitter this build records gain 0 and writes GAIN_NOT_MEASURABLE_WITHOUT_A_FITTER on the tick rather than invent a number.
- UNDECIDED IN DESIGN: which HELD candidates the tick's VERIFY step checks -- ARCHITECTURE.md section 1 step 6 says VERIFY runs every tick and does not say whether it checks every HELD candidate or only the ones an arm names, so this build checks every HELD candidate in the buffer against the evidence supplied for that tick.
- UNDECIDED IN DESIGN: the values of the drive loop's PROPOSED constants -- DRIVE_LOOP.md section 1 and OPEN_QUESTIONS.md mark gamma = 2, delta = 1/32, s_lo = 1/64, s_hi = 63/64, D_min = 2, max neglect 24 ticks, the pair cap 4, stage 16 ticks and K = 8 as PROPOSED for the owner to accept or change, so this build uses exactly those numbers and freezes them as constants rather than pretending they were decided.

## What is in this folder

| file | what it is |
| --- | --- |
| `guard.py` | the two evidence types, the one verifier, the faculty-return check, the single door to the Bias |
| `held.py` | the held buffer and its four states, with every move recorded |
| `faculties.py` | wondering, pondering, imagination, self-notice |
| `drive_loop.py` | when each faculty gets a turn |
| `test_all.py` | the whole suite, plain Python, no pytest |
| `bias.py` | **copied** byte for byte from `the_loop` — the Bias a faculty may read and may not write |
| `README.md` | this file |
| `PROVENANCE.md` | where the copy came from, its sha256, and what was read but not copied |

## One sentence, again

It shows four programmed faculties proposing into a buffer that only a real verdict can move,
one verifier that cannot be reached with imagined data, and a scheduler that gives them turns —
and it cannot claim that anything wondered, pondered, imagined or noticed anything, because
nothing here thinks and no faculty has run inside HELM.

```
MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
```
