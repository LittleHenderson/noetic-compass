# Independent audit pack — Helm and the pointer study

**Written for an agent who did not build this and has no stake in the answer.**
Everything here is command-ready. Run it, break it, and report what you actually got.

Companion file: `BRAIN_LINEAGE.md` (the brain's name, version, and record).

---

## 1. What you are auditing, at its exact strength

**The claim under test:** the machine reads a small structure of parts and "contains" links, and
answers questions about a structure **it has never seen**, better than it could before training.

**What a pass means:** the grader program `records/typed_pointer_001/evaluate_gates.py`, run over
the study file, prints the label. Nothing else is a pass. Not a good-looking score, not this
document, not a number in a changelog.

**What has already been measured, and by whom:** the numbers in `BRAIN_LINEAGE.md` for Helm 0.1 were
produced by the same session that built the machine, using the graders' own test functions. That is
**not** an independent verification. It is exactly the thing you are here to check.

---

## 2. The machine in thirty seconds

- A **world** is a handful of named parts plus directed "contains" links. Example: `Lathe contains
  Chuck`, `Lathe contains Tool`, `Tool contains Bolt`.
- A **question** asks something about one world: list every link, list what a part directly holds,
  is another part reachable and through what, what kind of thing is this, which known pattern does it
  match. Eight kinds exist.
- The machine is given a world and a question, and must return the answer.
- **Teaching** uses 19 worlds. **Testing** uses 5 worlds that were never in teaching.
- The brain holds **157,919** learned numbers in 46 groups. It does not get bigger by learning.

---

## 3. Environment

| need | why |
|---|---|
| Linux + CUDA GPU | the learner refuses to run without CUDA (`TYPED_LEARNER_CUDA_REQUIRED`), and the shared gate refuses off Linux. Training runs on AWS (`g7.2xlarge`, `us-west-2`), about `2.5200000000`/hour. |
| **Windows, no GPU** | is fine for everything in section 6 except the AWS re-run. The grader, the audit driver, and the test suite are all CPU and cost `$0`. |
| Python + `torch` 2.11.0 | `torch` is only needed for the parameter count and the learner's own CPU round trip. |
| `boto3` | only for reading S3 and EC2. |

---

## 4. The frozen things — check these did not move

If any of these changed, **the study is void** and you should stop and say so. These were fixed
before any result was seen. That is the only reason a result can mean anything.

| constant | frozen value |
|---|---|
| held-back question set size | **18** |
| its digest | `4b1e3c1f0b8f8be339e281410dc830fac1834432e8d816d67dce58906e90036d` |
| its make-up by kind | `{'parts': 2, 'edge_account': 5, 'reach': 6, 'correspondence': 0, 'analogy': 5}` |
| eligible relational questions before removals | **29** |
| pass mark | **7** improved, **0** broken |
| world held back | 5 worlds, never taught |
| seeds | `20260917`, `20260918`, `20260919` |
| passes | `10` |
| question counts | 564 total, 358 practised, 127 held back, 79 set aside |
| the three tiers | `DIRECT_READ` = definition, context. `RELATIONAL` = parts, edge_account, reach, correspondence, analogy. `TEXT` = role_set. |
| reservation per job | `15.00` |

**The label is keyed on the RELATIONAL tier only.** That is deliberate: those are the questions you
cannot answer by reading one word off the page. A gain on the easy kinds must not be able to produce
the label.

---

## 5. The files, with hashes at the time of writing

| file | bytes | sha256 (first 16) | what it is |
|---|---|---|---|
| `records/typed_pointer_001/evaluate_gates.py` | 133618 | `d3e0ea979835fa54` | **the grader.** Reads a study file, prints a label. |
| `records/typed_pointer_001/admission_001/study.json` | 5940 | `241c110f933c0cb4` | the three jobs, their seeds, their receipts, the owner's signed choices |
| `docs/CNCM_TYPED_POINTER_STUDY_v0.1.md` | 98536 | `81afe89eb2ffa8f0` | the protocol frozen before the run |
| `records/typed_pointer_001/holdout_audit.py` | 19708 | `1ea4677901544828` | re-derives the held-back split from the frozen rules, independently of the contract |
| `records/typed_pointer_001/preflight_dry_run.py` | 49080 | `b6cd411613b430c9` | drives the whole worker with a non-neural stand-in. `$0`, no GPU. |
| `cncm/typed_pointer_worker.py` | 123625 | `0d801b675d837ebd` | the program that runs inside the cloud machine |
| `research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py` | 62866 | `9dfdc22a4bb88437` | the program that reserves money, starts the machine, collects the evidence |
| `.../cas_meta2/typed_teaching/pointer_learner.py` | 134832 | `e0fe6dc8b523bc65` | the brain |
| `.../cas_meta2/typed_teaching/pointer_contract.py` | 70733 | `70be7ae7b7b3dbef` | the frozen question set, schedule, and split |

**Recompute every hash yourself.** `git show <commit>:<path>` gives the committed bytes with line
endings untouched, which is what the package uses.

The full sha256 of the grader, which the grader prints in its own output:
`d3e0ea979835fa548ae4fe4081280839b5b629296f24735a70e90e8880cdc90d`.
**Match it.** Readings have been taken against stale copies before — 45 and 47 checks, 112596 and
116356 bytes — while the real one is 133618 bytes. The grader prints its own byte count and hash
precisely so you can settle that from the output alone.

---

## 6. The checks, in order

Work on Windows/CPU. All of these are `$0`.

### Check 1 — is the grader itself sound?

```
python records/typed_pointer_001/evaluate_gates.py --self-test
```

- **Proves:** the grader's own 50 checks pass, and that the suite actually drives `evaluate()` (it
  reports how many times). An earlier version of this suite never called `evaluate()` at all, so a
  broken call site could not be seen by any test. That is why the count is asserted.
- **Pass looks like:** `SELFTEST_PASS 50 checks (evaluate() driven 2 times by this suite)` and the
  sha256 above. Takes about 90 seconds.
- **Fail looks like:** `SELFTEST_FAIL`, or a different sha, or a check count other than 50.

### Check 2 — was the held-out split derived honestly?

```
python records/typed_pointer_001/holdout_audit.py
```

No arguments. Prints JSON and exits `0` when it passes.
- **Proves:** the split is re-derived from the frozen RULES, not read back from the contract's own
  constants. If the contract's numbers were fudged, the two derivations would disagree.
- **Pass looks like:** exit `0`, and every one of the nine `schedule_agreements` is `true`. Note
  `presentations_per_pass_is_not_the_source_value` must be `true` — the stratified schedule changed
  presentations per pass while leaving updates per pass alone, and those two must never be asserted
  equal.

### Check 3 — do the unit tests pass?

```
python -m pytest tests/test_typed_pointer_study.py -q
```

- **Pass looks like:** `22 passed`.

### Check 4 — the end-to-end dry run, no GPU

```
python records/typed_pointer_001/preflight_dry_run.py <empty scratch dir>
```

- **Proves:** the whole pipeline runs with a deliberately dumb stand-in brain, so a pass cannot come
  from the real brain being clever and a failure cannot come from the plumbing.
- **Pass looks like:** `PREFLIGHT_PASS`, exit `0`.

### Check 5 — **the reading. This is the one that matters.**

```
python records/typed_pointer_001/evaluate_gates.py records/typed_pointer_001/admission_001/study.json
```

- **Proves:** whatever the grader says about the three real runs. It writes the full reading to
  `admission_001/gate_reading.json`.
- **A reading is always printed.** An unexpected error comes back as a `VOID` reading, never a bare
  traceback, so an empty or crashing run is itself a printed result.
- **Read these fields, in this order:** `label`, then `gates`, then `failures`. The `failures` list
  is the reason for a refusal and uses codes like `I1:<seed>`, `I2:<seed>`, `I3:<seed>`, `I4:<seed>`,
  `POPULATION:...`, `SCORING:...`.
- **The label is only earned when all three seeds pass.** One seed passing is not the label.

---

## 7. Independent tests to run — including attempts to break it

The checks above reproduce my work. These try to falsify it. **Run them and report honestly,
including when they fail to break anything.**

1. **Could guessing explain it?** Take the held-back questions and compute the commonest single
   answer across all of them. Then compute what a machine that always gave that answer would score on
   the frozen 18. If that alone reaches 12 of 18, the result is not evidence of reading structure.
   This is the single most important test on this list.

2. **Are the gained questions guessable ones?** Each question records how many answers are
   admissible. Find every question with only one admissible answer, and check whether the ten gains
   are concentrated there. If they are, the machine may be exploiting a giveaway rather than reading.

3. **Did the held-out worlds leak into training?**
   `records/typed_pointer_001/protocol_material.json` records the held-back record ids. Cross-check
   them against every training log (`pass_*_batches.jsonl`) and assert **no** held-back id appears.
   The grader does this as its `I2` check; verify it independently and do not take the grader's word.

4. **Could it have memorised?** Check that the five held-out worlds share no part names with the
   taught worlds, and that their link arrangements are not duplicates of taught ones. Memorising part
   names would then be impossible, so any gain must come from reading the structure.

5. **Is the result reproducible, or was it one lucky run?** The run records an
   `initial_model_identity`. Rebuild the brain for the same seed and confirm you get the same
   identity. If the starting point is a pure function of the seed, the run is not luck.

6. **Does the grader actually read the data?** Substitute a deliberately damaged scoring file — one
   where you flip some `correct` flags, or truncate the file — and confirm the grader refuses or
   changes its answer. A grader that prints the same thing regardless of its input is worthless.

7. **Do the gate's own guards fire?** The grader requires at least **2 different kinds** of question
   and at least **2 different worlds** to have improved. Verify the counts independently from the
   scoring files rather than trusting the summary.

8. **Fetch the raw evidence yourself.** The machine's answers are its own files. Read
   `course_p00_scoring.json` and `course_p10_scoring.json` from each receipt and recompute the
   18-question score yourself, from the `correct` flags, without running the grader at all. If your
   number and the grader's number disagree, that is a finding.

---

## 8. Traps that have already fooled people — including me

Read these before you conclude anything. Each one cost real money or produced a false impression.

1. **A folder named `receipt_smoke_*` held a full-length run.** The name said smoke; the runner's own
   records said `claim_bearing: true`, `schedule_plan_mode: REGISTERED`, ten passes. **Read the run's
   own records, never the folder name.**

2. **A `--reduced-schedule` flag that never reached the machine.** The launch program believed it was
   running a cheap 1-pass rehearsal while the machine ran the full 10-pass plan, and then graded the
   result against the wrong contract. Look at `schedule_plan.json`: `reduced_schedule_requested` and
   `mode` are the truth.

3. **A certificate that cannot be reconstructed.** The file the grader reads to certify a run is
   written by the *launching* program, not by the machine that trained. If the launcher dies, that
   run can never be certified, even if its training succeeded completely. See the "NOT CERTIFIED"
   row in `BRAIN_LINEAGE.md`. **Never accept a hand-written certificate.**

4. **Loss going down is not learning.** Learning is measured on held-back questions, not on training
   loss. In one run the loss flattened from pass 6 while the held-back score kept climbing.

5. **A run that finishes is not a run that passes.** A run can report complete success and still be
   refused by the grader. Both facts are true at once and must be reported together.

6. **Failure codes that look like arithmetic but are not.** `I1:<seed>:REQUIRED_ARTIFACTS:99!=99`
   reads like a contradiction. It comes from comparing two lists **in order** — same contents,
   different order. Do not chase it as a data problem without checking the ordering.

---

## 9. What is explicitly NOT claimed

- Not a claim that the machine is generally intelligent, or that it works on anything other than
  small structures of parts and containment links.
- Not a claim about novel *domains*. The five held-out worlds are the same kind of thing as 11 of the
  taught worlds: machines. The transfer is to **new individuals, new names, new wiring**.
- Not a claim about the whole CNCM machine. This is one component reading one kind of structure.
- Not a claim that any past run passed unless the grader printed the label for that run.

---

## 10. How to report

For each check, give: the exact command, the exit code, and the raw line that decides it. Then state
one of:

- **REPRODUCED** — you got the same thing.
- **CONTRADICTED** — you got something different, with the raw output.
- **COULD NOT RUN** — with the blocker.

Then, separately, say whether any of the eight falsification attempts in section 7 succeeded. A
falsification attempt that **fails** is a result worth recording: it is evidence the claim survives
contact. An attempt that **succeeds** is the most valuable thing you can send back.

**Do not upgrade or downgrade a claim on your own.** Report what you measured and leave
`BRAIN_LINEAGE.md`'s verdict row for the owner to change.
