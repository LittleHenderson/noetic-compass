# Faculties v2 — wondering, pondering, imagination, self-notice, the restart fallback, and the Unity Eye

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\faculties_v2\`, as the merged
copy of `..\faculties\`. This is the RB-I faculties layer from `helm_rb_i_faculties_design_v1`
(written 2026-10-15, marked **DESIGN ONLY. NOT BUILT**), now built, tested, and carrying two
mechanisms that already existed in this project and were not wired in until now:

  * **RB-C4's RESTART_FALLBACK** (seeded alternative fit starts), in `restart.py`, called by
    `pondering`;
  * **the Unity Eye** (the F1 watcher), in `eye/`, pointed at this project's real builds.

The original `..\faculties\` is untouched and still passes: `TOTAL 37 cases: 37 passed, 0 failed`.
Standard library only. No torch, no numpy, no network, no cloud, no spend.

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

The 37 original cases all still pass, and the merge added cases for the two mechanisms; the run
prints one line per case and the totals last. The ones that carry the original claim:

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
4. **The restart fallback is in, and the fitter it restarts is still not.** `pondering` runs
   RB-C4's fallback when no refit is passed, but this build has no LSR fitter and no recipe
   book: a route here is a named canonical form plus the cells it claims, supplied by the
   caller, so the fallback re-starts a route choice and not a recipe fit.
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


## What this merge added: the restart fallback (`restart.py`)

RB-C4 measured one thing and kept it: when a fit leaves real training rows unexplained, retry the
fit from **seeded alternative starting points** and keep whichever start explains the most rows
(`rb_c4/fitg.py` lines 150-179; `rb_c4/RESULTS.md` line 43: fired **8,828** times, an alternative
start kept **7,823** times; line 52: "The randomness win is a FIT-START win, not a proposal win.").
The normal verifier and RPM gate still decide acceptance. Randomness changes where fitting starts;
it never chooses the answer.

This build ports that mechanism rather than inventing one. Start 0 is the consistency-checked
start and makes no draw; the fallback fires only when start 0 leaves rows unexplained; it then
tries the seeded starts 1 to 8; it keeps the fewest unexplained rows, ties to the lower start; and
every start is recorded with its **seed**, the **start** it tried, the **rows it explained** and
whether it was **kept**. `pondering` calls it when the caller supplies no refit, and every
candidate it produces goes into the held buffer as `HELD`.

What differs from the source is in the UNDECIDED IN SOURCES list below: RB-C4 scores a start by
exact yields and breaks ties by an exact residual sum; this build has no `y`, so a row is
explained or it is not, and ties go to the lower start index. RB-C4's routes are recipes; here a
route is a named canonical form plus the cells it claims, because this build has no recipe book.

**A restart cannot accept anything.** `RestartResult` has no verdict, no admission and no accepted
flag. `accepted_forms()` is the only reader that hands forms back as accepted, it demands a sealed
`ADMITTED` verdict per form, and it refuses with `RESTART_RESULT_NOT_VERIFIED` otherwise. The case
`test_a_restart_cannot_accept_a_result_the_verifier_refused` proves the wall four ways, including a
start that explains 6 of 6 rows whose forms the verifier refuses and which therefore stay `HELD`.

## What this merge added: the Unity Eye (`eye/`)

Form **MINI-VERSION**, ACCEPTED_BY_OWNER (`OWNER_RULING_UNITY_EYE_20261015.md`): one recipe over
the measured health signals, the Limiting Reagent readout naming the component most short of
unity, gate words G1-G4, and an eta / epsilon receipt on every reading. 0 learned parameters. It
sits **outside** what it watches and it is **report-only**: it proposes, and every change would go
through normal verification and receipts.

The recipe, per watched package: five ingredients, requirement a_i = 1 for each
(`UNITY_EYE.md:93`), Y_T = min_i(x_i / a_i), the Limiting Reagent at the minimum.

| ingredient | count rule | where the number comes from |
| --- | --- | --- |
| `tests_passing` | cases passed / cases run | the package's own suite result |
| `suite_complete` | cases run / cases registered | the `@case` functions counted in the suite file |
| `mechanism_proofs` | mechanisms required of the package and proved by a named passing test / mechanisms required | the suite's own PASS lines |
| `design_coverage` | parts of its own design the package carries / parts the design names | `faculties_v2`: its `FACULTIES` tuple over the nine faculties `FACULTIES.md` 2.1-2.9 names. `language_v2`: the coverage-ledger cells COVERED over the 200 probed |
| `read_only` | the tap's digest held across the reading | the tap, never the package |

**The eye cannot write.** Every read is a tap: the folder is hashed before and after, and a
reading taken across a write is refused (`WATCHED_VALUE_MOVED`). The case
`test_the_eye_cannot_alter_any_watched_value` re-hashes every watched folder outside the eye
before and after a full read, a report and a re-check, and requires equality.

**The eye never gates.** It has no method that returns a yes or no, no part of the brain imports
it, and `test_removing_the_eye_changes_no_decision_anywhere` runs the drive loop with the eye
reading between every tick and without the eye at all, then compares every `TurnRecord`, the
buffer digest, the Bias version and digest, and the satisfactions.

## The eye's actual output, on this project's builds

Printed from `eye/recorded_suite_results.json`, which holds the exact command and the exact tail of
each suite as it ran. The eye reads that record; it does not run a suite itself, because it lives
inside one of them. A case re-counts the `@case` functions in each suite and fails if a recorded
count disagrees, so a stale record cannot flatter a package.

```
weakest package: faculties_v2 (Y_T 4/9). Limiting reagent: design_coverage -- 4 of 9 faculties carried: wondering, pondering, imagination, self_notice. Gate: no gate word; one limiting reagent, everything present.
  OM_faculties_v2: Y_T 4/9, limiting reagent design_coverage
  OM_language_v2: every ingredient met its requirement (Y_T 1); nothing is short
  REPORTED faculties_v2: design_coverage (4 of 9 faculties carried: wondering, pondering, imagination, self_notice) -- would do: nothing: building a missing part is outside a report-only watcher; must never: claiming the part exists, or building it silently
  NONE language_v2: none (every ingredient met its requirement (Y_T 1/1)) -- would do: nothing; must never: inventing work where nothing is short
```

In words: the weakest of the two packages is named, with the ingredient that limits it, the
number behind that ingredient, and the gate word. It is a reading, not a verdict: nothing in this
build reads it, and nothing acts on it.

## The UNDECIDED IN SOURCES lines

Every point the two source mechanisms do not settle **for this host** is marked in the code with
`# UNDECIDED IN SOURCES: <question>` and listed here word for word, with the reading this build
took. A case reads the markers out of the code and fails if one is missing here, or if this list
carries one the code does not.

- UNDECIDED IN SOURCES: which exact numbers the fallback uses, when fitg.py freezes 8 seeded starts and a 20-iteration fixed-point cap -- fitg.py:52 and :171 give both numbers for rb_c4's own grammar fit and no source says whether another host must use the same two, so this build uses 8 and 20 exactly as rb_c4 froze them and records them as constants rather than scaling them.
- UNDECIDED IN SOURCES: how a start is scored when the host has no yields, when fitg.py keeps the fewest unexplained rows and breaks ties by the exact residual sum -- fitg.py:167 compares `res` only, and `res` comes from yields that this build does not have, so this build counts unexplained rows and breaks ties by the lower start index alone, which is the second half of fitg.py's own rule with the first half absent.
- UNDECIDED IN SOURCES: whether the fallback may fire a second time within one fit call, when fitg.py fires once per call (`fallback and k == 0 and not fired`) -- fitg.py:169 sets `fired = True` before the starts are appended and never resets it, so this build fires at most once per call and records `fallback_fired` as a yes or no.
- UNDECIDED IN SOURCES: where a restart's candidate routes come from, when rb_c4's routes are recipes held by the grammar and this build has no grammar and no recipe book -- FACULTIES.md section 2.3 says pondering re-fits each group "with the RB-C4 restart fallback" and never says where the alternatives come from, so this build takes the routes from the caller, or from the Bias's own admitted facts when a fact names the cells it covers, and refuses with RESTART_NEEDS_A_START when nothing is named.
- UNDECIDED IN SOURCES: what the eye's digest must cover, when UNITY_EYE.md says "`D(brain)` before = after, digest-checked" and never says what D hashes -- so this build hashes every watched file's path and bytes, excludes the eye's own folder by name, and prints the exclusion in the reading.
- UNDECIDED IN SOURCES: whether a tap may read a file's text at all, when the design's tap is described as reading a station out loud and this build's stations are source files -- so this build reads text for the suffixes it lists and hashes everything else, and it never writes either.
- UNDECIDED IN SOURCES: what each ingredient's requirement a_i is, when UNITY_EYE.md section 2.1 sets every a_i = 1 as PROPOSED and Q24 leaves the numbers to the owner -- so this build uses exactly 1 for every ingredient and lets a caller pass another requirement, and never learns one from an invented gold.
- UNDECIDED IN SOURCES: whether the eye's readout must be reported per stage of 16 ticks, when UNITY_EYE.md section 2.1 says "per stage (16 ticks, DRIVE_LOOP.md:128)" and this project's packages have no ticks at all -- so this build reads once per call, names the call a stage, and records the stage id in the log instead of inventing a tick count.
- UNDECIDED IN SOURCES: which packages the eye watches, when the owning instruction says to point it at "the real builds in this project" and names no list -- so this build watches the two merged packages, `faculties_v2` and `language_v2`, and says so in the reading rather than deciding for every folder on the disk.
- UNDECIDED IN SOURCES: which signals stand in for the design's nine brain signals, when UNITY_EYE.md section 2.1 names receipts, lacunae, stations, drive balance, drive entropy, continuity, the memory check, the UNDETERMINED rate and the language skin, and these builds have no stations, no drive loop and no dialogues -- so this build measures test results, suite completeness, mechanism proofs, design coverage and read-only integrity, and records each count rule beside its number.
- UNDECIDED IN SOURCES: whether the eye may run a watched package's suite itself, when UNITY_EYE.md gives it a cadence of cheap signals and this build's eye lives inside one of the suites it would run -- so this build reads a recorded result instead, and a test re-counts the suite's cases to catch a stale record.
- UNDECIDED IN SOURCES: whether comparing a faculty-roster yield to a coverage-ledger yield is a like-for-like comparison, when the Limiting Reagent logic assumes one recipe's ingredients and these are two different count rules -- so this build puts each package's rule in the reading and compares the two yields anyway, which is what "the weakest package" means here and is not a claim that the two packages are otherwise alike.
- UNDECIDED IN SOURCES: what counts as the case count a package declares, when the faculties README says "37 cases, all passing" and the language README says "30 runnable cases" -- so this build parses the first "<n> cases" phrase out of the README and reports it, and never uses it to score anything.
- UNDECIDED IN SOURCES: whether the eye may make a FIX proposal at all here, when the owner's acting ruling approves acting only inside test U1 on the laptop and this build is not U1 -- so this build marks every proposal REPORT_ONLY, performs none, and records the kind (FIX, HELP, REPORTED) as a word for what a later acting build would do.
- UNDECIDED IN SOURCES: how a tie between two packages is reported, when the gate word G3 names both and this instruction asks the output to name one weakest package -- so this build names both in `tied_with`, breaks the tie for the headline by the package's name in sorted order, and prints the G3 word beside the answer.
- UNDECIDED IN SOURCES: whether the eye's log may be written to disk, when UNITY_EYE.md says its only write is its own append-only log and the log's durability is never specified -- so this build keeps the log in memory, returns it to the caller, and writes nothing anywhere.
- UNDECIDED IN SOURCES: what the eye should do when its own package is the weakest, when nothing in the sources says a watcher may or may not report on the build it lives in -- so this build reports it, because suppressing it would be the eye preferring a flattering reading to a measured one.

## What is in this folder

| file | what it is |
| --- | --- |
| `guard.py` | the two evidence types, the one verifier, the faculty-return check, the single door to the Bias |
| `held.py` | the held buffer and its four states, with every move recorded |
| `faculties.py` | wondering, pondering, imagination, self-notice |
| `drive_loop.py` | when each faculty gets a turn |
| `restart.py` | RB-C4's RESTART_FALLBACK, ported: seeded starts, every seed recorded, `accepted_forms` refuses without a sealed verdict |
| `eye/` | the Unity Eye (F1 watcher): `tap.py` (read-only digest check), `recipe.py` (Y_T, Limiting Reagent, gate, receipt), `signals.py` (the five measured ingredients), `eye.py` (the watcher), `recorded_suite_results.json` (its input) |
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
