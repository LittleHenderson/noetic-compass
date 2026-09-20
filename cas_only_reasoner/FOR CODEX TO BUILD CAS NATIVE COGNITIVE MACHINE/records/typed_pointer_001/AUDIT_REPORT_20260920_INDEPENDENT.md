# Independent audit of Helm 1.0 — report

**Auditor:** a session that did not build this. **Date:** 2026-09-20.
**Target:** `BRAIN_LINEAGE.md`, Helm 0.1 and Helm 1.0, label `LEARNS_NEW_WORLDS`.
**Instructions followed:** `AUDIT_PACK.md` sections 6 and 7.
**Cost:** `$0`. Everything ran on this Windows machine, on the processor, no cloud, no GPU.
**Nothing in the repository was changed by this audit.** The working tree is clean. All damage
tests were done on copies under a scratch folder.

---

## The short version

The reproduction work all passes. Every number in `BRAIN_LINEAGE.md` is exactly right. I
recomputed them myself from the raw `correct` flags without running the grader, and I got the
same numbers to the digit.

**The guessability test did not break the claim.** Always giving the commonest answer scores
**0 of 45**. That attack fails completely.

**Two other things did break, and they are serious.**

1. **A rule that learns nothing already scores 11 of 18.** The machine scores 12, 12 and 11.
   Run the gate's own pass test against that rule instead of against the untrained machine and
   **all three seeds fail**, with odds of 1 in 2, 1 in 2 and worse than even. This number is
   printed by the grader itself, and the contract says out loud that it must be read beside the
   label. `BRAIN_LINEAGE.md` does not say it. A reader of the lineage file alone would not know.

2. **The certificate is not tied to the evidence.** I edited one scoring file by hand so that
   every question the machine really got right was marked wrong, and every question it really
   got wrong was marked right. The grader printed `LEARNS_NEW_WORLDS`, `integrity: pass,
   failures: []`. The edited file no longer matches the sha256 the run recorded for it in its
   own `artifact_manifest.json`, and nothing checks.

Neither finding says this run was faked. I checked: the real files on disk are the genuine
ones, they are in git, and the numbers are honest. Finding 1 is about **how the result should
be described**. Finding 2 is about **how strong the guarantee is**.

---

## Part A — reproducing the work (`AUDIT_PACK.md` section 6)

### Hashes first

Every file hash in `AUDIT_PACK.md` section 5 recomputed and matched, byte count and sha256:

| file | bytes | sha256 | |
|---|---|---|---|
| `records/typed_pointer_001/evaluate_gates.py` | 133618 | `d3e0ea97…cdc90d` | ✅ match |
| `records/typed_pointer_001/admission_001/study.json` | 5940 | `241c110f…d23fde` | ✅ match |
| `docs/CNCM_TYPED_POINTER_STUDY_v0.1.md` | 98536 | `81afe89e…c7f08f` | ✅ match |
| `records/typed_pointer_001/holdout_audit.py` | 19708 | `1ea46779…3c2c53b` | ✅ match |
| `records/typed_pointer_001/preflight_dry_run.py` | 49080 | `b6cd4116…42b888` | ✅ match |
| `cncm/typed_pointer_worker.py` | 123625 | `0d801b67…e24bd1` | ✅ match |
| `research/.../aws/typed_pointer_launch.py` | 62866 | `9dfdc22a…7e8fec` | ✅ match |
| `records/typed_pointer_001/admission_001/gate_reading.json` | 202862 | `475379d2…b058a9` | ✅ match |

The committed bytes at `c95dc6ac` for the grader, the lineage file and the reading match the
bytes on disk. Working tree clean.

### Check 1 — is the grader sound? ✅ **REPRODUCED**

```
python records/typed_pointer_001/evaluate_gates.py --self-test
```
Exit `0`. Last line: `SELFTEST_PASS 50 checks (evaluate() driven 2 times by this suite)`.
Printed source sha256 `d3e0ea979835fa548ae4fe4081280839b5b629296f24735a70e90e8880cdc90d`,
133618 bytes, 1929 lines. Exactly the expected revision, not a stale copy.

### Check 2 — was the held-out split derived honestly? ✅ **REPRODUCED**

```
python records/typed_pointer_001/holdout_audit.py
```
Exit `0`. `"status": "HOLDOUT_AUDIT_PASS"`, `"failures": []`. All nine `schedule_agreements`
`true`, including `presentations_per_pass_is_not_the_source_value: true`. Held digest
`668e6ce7…`, excluded digest `b82108e1…`, both matching the frozen values and the contract.
Counts re-derived here: held 127, trained 358, excluded 79 — sum 564.

### Check 3 — unit tests ✅ **REPRODUCED**

```
python -m pytest tests/test_typed_pointer_study.py -q
```
`22 passed in 168.64s`. Exit `0`.

### Check 4 — end-to-end dry run 🔧 **STILL RUNNING AT TIME OF WRITING**

```
python records/typed_pointer_001/preflight_dry_run.py <fresh dir>
```
Note for the next auditor: the directory must **not exist**. If you create it first the script
stops with `FileExistsError`. `AUDIT_PACK.md` check 4 says "empty scratch dir", which reads as
"make one first". It should say "a path that does not exist yet".

The run is progressing normally through the real phase order — preflight, packet preparation,
input checks, `course_p00` predictions, main training at 1470 updates. No errors. It is slow on
a processor because it does the full schedule. Result to follow.

### Check 5 — the reading. ✅ **REPRODUCED, BYTE FOR BYTE**

```
python records/typed_pointer_001/evaluate_gates.py records/typed_pointer_001/admission_001/study.json
```
Exit `0`. The file it wrote is **identical to the committed one**: 202862 bytes, sha256
`475379d2f9d47387a821c79e03a239f9a1f1277a0bbb25b298417557f9b058a9`.

```
label   : LEARNS_NEW_WORLDS
integrity: pass, failures []
```

Nine gates, exactly as the lineage file states:

| gate | result |
|---|---|
| `integrity` | pass |
| `G_LEARN_population` (the label's own test) | pass |
| `G_LEARN_all_kinds` | pass |
| `TRAINED_start_to_final` | pass |
| `TRAINED_first_to_final` | pass |
| `G_LEARN_DIRECT_READ` | pass |
| `MORE_PRACTICE_population` | **fail** |
| `G_LEARN_TEXT` | **fail** |
| `kind_g_learn`, all 8 kinds | **fail** |

The three failures are reported in `BRAIN_LINEAGE.md` accurately, with accurate reasons.

### Every headline number recomputed by hand ✅

Straight from the `correct` flags in `course_p00_scoring.json` and `course_p10_scoring.json`,
without running the grader at all (`AUDIT_PACK.md` section 7 item 8):

| | seed 20260917 | seed 20260918 | seed 20260919 |
|---|---|---|---|
| whole course, 564 | 30 → 392 | 17 → 422 | 20 → 407 |
| never-shown worlds, 127 | 9 → 84 | 2 → 88 | 5 → 81 |
| taught worlds, 358 | 16 → 258 | 10 → 284 | 13 → 275 |
| memory check, 96 | 93 → 93 | 93 → 93 | 87 → 87 |
| the frozen 18 | 2 → 12 | 0 → 12 | 0 → 11 |
| gained / broken | 10 / 0 | 12 / 0 | 11 / 0 |

**No disagreement anywhere.** Every figure in the lineage table is exact.

### The machine's size ✅

Loaded `initial.pt` and counted: `model_state` holds **46** tensors, **157,919** numbers.
`declaration_table` is `(1024, 64)` = **65,536** = **41.50%**. All three claims exact.

### Lifecycle and the known traps ✅

For all three seeds: `result.status = AWS_CANDIDATE_FINISHED`, `completed_deliverable = true`,
`cleanup.complete = true`, `worker.status = COMPLETE_TYPED_POINTER_ARM`, `claim_bearing = true`.
Run clocks 7791.257429470999 s, 7834.867562267 s, 7792.573039091 s — exact.

- Trap 1 (folder named smoke): the three receipts are not smoke folders and their own records
  say `claim_bearing: true`. Consistent.
- Trap 2 (a reduced-schedule flag that never arrived): `schedule_plan.mode = REGISTERED`,
  `reduced_schedule_requested = false`, `reduced_schedule: null`, all three seeds. Clean.
- Money: `15.00` reserved per job, `remaining_unreserved_usd` `4289.00` → `4274.00` → `4259.00`.
  Each machine recorded `CONFIRMED_TERMINATED` (`i-01d640263557da32b`, `i-04453c9ffff520c91`,
  `i-0981ea8cd07ef8746`). **This is the run's own record, not an independent check of AWS.** I
  did not query AWS. ⬜ Not independently confirmed.

---

## Part B — the eight attempts to break it (`AUDIT_PACK.md` section 7)

### 1. Could guessing explain it? ✅ **ATTACK FAILED — the claim survives**

This was named the most important test, so I ran it two ways.

**The commonest-answer rule.** The project already ships this exact baseline as
`constant_policy` in `pre_design/measurements/leaks_review/lk6_gate_population.py`: "the best
single trained alias-form CONSTANT answer per kind". Its measured score is **0 of 45** eligible
held questions. Always giving the commonest answer gets **nothing**. Also measured and
recorded there: "point at the alphabetically first node" scores 0, "point at the query's
argument node" scores 0.

**So: no, guessing cannot explain 12 of 18. That attack fails outright.**

### 🟥 But a *different* mechanism-free rule scores 11 of 18 — and that one is not in the lineage file

The grader prints this itself, in `oracle_ceilings`:

```
oracle_or_rank_solvable_in_the_label_population : 11
```

Two rules, neither of which learns anything:

- **the one-hop adjacency read** — for `parts`, the children of the named whole; for
  `edge_account`, copy the focus world's links; for `reach`, DIRECT if the part is a child.
  Solves **7** of the 18.
- **"always point at the alphabetically last node"** — reads no links at all.
  Solves **5** of the 18. One question overlaps, so the two together solve **11**.

The machine scores 12, 12, 11.

I checked which questions it actually gets right:

| | seed 20260917 | seed 20260918 | seed 20260919 |
|---|---|---|---|
| correct, 18 | 12 | 12 | 11 |
| of those, inside the zero-learning 11 | 10 | 10 | 9 |
| of those, **outside** it | **2** | **2** | **2** |
| zero-learning questions it got **wrong** | 1 | 1 | 2 |

Per kind, at pass 10, all three seeds:

| kind | in the 18 | s17 | s18 | s19 |
|---|---|---|---|---|
| `edge_account` | 5 | 5 | 5 | 5 |
| `parts` | 2 | 2 | 2 | 1 |
| `reach` | 6 | 5 | 5 | 5 |
| `analogy` | 5 | **0** | **0** | **0** |

`analogy` is the one kind in the population that no zero-learning rule touches. The machine
scores **zero out of five on it, in every seed**. The five `correspondence` questions were
removed from the population before the run because the head cannot express a bijection.

Now apply the gate's own pass rule — improved at least 7, broken 0, one-sided p at most 1/128 —
but with the zero-learning rule as the thing being beaten, instead of the untrained machine:

| | machine | rule | machine-only | rule-only | one-sided p | gate verdict |
|---|---|---|---|---|---|---|
| seed 20260917 | 12/18 | 11/18 | **2** | 1 | **0.5000** | **FAIL** |
| seed 20260918 | 12/18 | 11/18 | **2** | 1 | **0.5000** | **FAIL** |
| seed 20260919 | 11/18 | 11/18 | **2** | 2 | **0.6875** | **FAIL** |

**Plain words.** The machine went from far worse than a trivial program to about level with a
trivial program, and two questions better. The "1 in 1024" odds are odds against the untrained
machine, which scores 0 to 2 — worse than the trivial program. They are not odds against a
program that reads the links off the page.

**This is not new information to the project.** The contract says it in full
(`pointer_contract.py`, `zero_learning_floor`), the grader prints it, and the project's stated
position is that "applying the checker's own rule to the input IS the skill under test"
(protocol section 4.4, confirmed by the owner), so it is reported and never subtracted. That is
a defensible position. **What is not defensible is that `BRAIN_LINEAGE.md` does not carry the
number.** The lineage file is the file every agent reads first and the one a claim gets quoted
from. It says "going from 0–2 of 18 to 11–12 of 18" with no mention that 11 of 18 is what a
program with no learned weights already scores.

### 2. Are the gained questions the guessable ones? 🟥 **YES — completely concentrated**

Each question records how many answers are admissible. Of the 18:

- **13** have exactly one admissible answer.
- **5** have more than one (three with 6, two with 9). Those five are the `analogy` questions.

**Every single gain, in every seed, is on a one-answer question.** 10 of 10, 12 of 12, 11 of 11.
Gains on multi-answer questions: **zero, in all three seeds.**

### 3. Did the held-out worlds leak into training? ✅ **ATTACK FAILED — no leak**

I scanned every `pass_01..10_batches.jsonl` and `pass_*_updates.jsonl` and the interference
logs, for all three seeds, for all 127 held-back record ids.

- Held record ids in the training batch logs: **0**.
- Held record ids in the weight-update logs: **0**.
- Excluded record ids in the update logs: **0**.
- Distinct trained ids actually updated: **358 of 358**, all three seeds.

One thing to note and dismiss: a held **world** id appears 4 times in seed 20260917's and
seed 20260918's pass-1 logs. I traced every occurrence to its exact place in the JSON. All four
are at `predictions[]/answer/value/kind_ref` — **the machine's own wrong guess**, not input and
not a training target. It means the answer menu for that slot spans every world in the bank.
Not a leak of any held world's structure.

### 4. Could it have memorised? 🟨 **MOSTLY FAILED — but "new wiring" is not accurate**

- **World overlap: zero.** None of the 5 held worlds appears in any trained record, as focus or
  as support.
- **Part names:** 18 of the 20 held part names never appear in training. **Two do**: `Chuck` (a
  turning machine) and `Gear` (a transmission assembly) are both used in taught worlds.
  `BRAIN_LINEAGE.md` says "parts and names it had never seen". That is right for 18 of 20, not
  20 of 20.
- **Wiring: 🟥 not new.** I computed each held world's link pattern ignoring the names — the
  bare shape. **All five held shapes also occur among the taught worlds**, 2, 1, 3, 1 and 4
  times respectively. The lineage file's phrase "new individuals, new names, new wiring" is
  wrong on the last word. The wiring is a pattern it was trained on. What is new is the
  identity and the labels.

So memorising the *names* would not work — that part holds. But the machine did not have to
generalise to an unseen shape either.

### 5. Is it reproducible, or one lucky run? ✅ **ATTACK FAILED — reproducible**

Each run recorded the starting-point identity **for all three seeds**, not just its own. All
three runs recorded the **same** map:

```
20260917 -> 82d2037ca88593233f1176913b91f54d419ebacd23f5abc4e12bd71795feb794
20260918 -> 35081019e8b56f0c0c14aa8168262c23dab4c662c385ddcf26edc794a179b706
20260919 -> 91279389cfc22df46415dd56a26b1285fb3ef1ecd59e3aaccef553564528c12e
```

Every run reports `double_build_equal: true` and `seeds_pairwise_different: true`, and each
seed's identity equals the practice study's recorded start. The starting point is a pure
function of the seed and three separate machines agreed. **Not luck.**

### 6. Does the grader read its data? 🟥 **ATTACK SUCCEEDED — the certificate is not tied to the evidence**

The grader does read its data. It also accepts data that has been edited by hand.

**Test 6a — can an edit destroy a pass?** I copied seed 20260919's receipt, and in the *before*
file marked all 18 frozen questions already correct. The grader printed:

```
label : NO_TRANSFER_TO_NEW_WORLDS
integrity: {'failures': [], 'pass': True}
G_LEARN_population: pass=False, per_seed {20260917: True, 20260918: True, 20260919: False}
```

Good: the label follows the data and names the seed.

**Test 6b — can an edit manufacture a pass? 🟥 Yes.** I put the *before* file back and edited
the *after* file instead, so that:

- all **11** questions the machine really got right were marked **wrong**, and
- all **7** questions it really got **wrong** were marked **right**.

Every remaining "gain" was therefore a question the machine actually failed. The grader printed:

```
label : LEARNS_NEW_WORLDS
integrity: {'failures': [], 'pass': True}
G_LEARN_population: pass=True, per_seed {20260917: True, 20260918: True, 20260919: True}
seed 19 improved kinds: ['analogy', 'parts', 'reach']   worlds: 5
```

It certified a fabrication, and it reported gains on `analogy` — the kind the machine has never
once got right.

**Why nothing caught it.** The run's own `artifact_manifest.json` **does** record a sha256 for
`course_p00_scoring.json` (`51df0a74…`, 593642 bytes). My edited file hashes to `3a6409a9…`,
650832 bytes. The two do not match. The grader never compares them. Its only sha256 check on
run evidence is the practice start checkpoint pin (`evaluate_gates.py:646`, the `I3` check).
The `public_seal` inside each scoring file seals the *predictions* file, not the scoring file
itself, so it stays valid while the scores are rewritten.

**What this does and does not mean.** It does **not** mean this run was forged. I verified the
real files: they are the ones in git at `c95dc6ac`, and every number recomputes correctly from
them. What it means is that the guarantee is weaker than the design intends.
`BRAIN_LINEAGE.md` rule 3 says "never write or edit a certificate, a lifecycle record, or a
reservation by hand" — but the two files that actually decide the label are not on that list
and are not protected by any check.

### 7. Do the gate's own guards fire? ✅ **ATTACK FAILED — guards verified**

Recomputed from the scoring files, independently of the summary:

| | improved (bar 7) | broken (bar 0) | kinds (need 2) | worlds (need 2) |
|---|---|---|---|---|
| seed 20260917 | 10 | 0 | 3 — `edge_account`, `parts`, `reach` | 5 |
| seed 20260918 | 12 | 0 | 3 — same | 5 |
| seed 20260919 | 11 | 0 | 3 — same | 5 |

Every count matches the grader. The frozen population digest
`4b1e3c1f0b8f8be339e281410dc830fac1834432e8d816d67dce58906e90036d` matches, and the make-up is
`analogy 5, correspondence 0, edge_account 5, parts 2, reach 6` = 18, exactly as frozen.

### 8. Recompute the 18 from the raw flags ✅ **ATTACK FAILED — no disagreement**

Done above. 2→12, 0→12, 0→11. Identical to the grader and to the lineage file.

---

## Part C — one extra thing I measured

### The learning curve says "snapped", not "learned gradually"

`MORE_PRACTICE_population` failing is reported honestly in the lineage file. Here is what it
looks like on the frozen 18, all three seeds:

| | p00 | p01 | p02 | p04 | p06 | p08 | p10 |
|---|---|---|---|---|---|---|---|
| seed 20260917 | 2 | 11 | 11 | 12 | 12 | 12 | 12 |
| seed 20260918 | 0 | 12 | 12 | 12 | 12 | 12 | 12 |
| seed 20260919 | 0 | 11 | 12 | 11 | 11 | 11 | 11 |

And the count **above the zero-learning floor**, same columns: `1,2,2,2,2,2,2` / `0,2,2,2,2,2,2`
/ `0,2,2,2,2,2,2`.

One pass takes it from below trivial to the trivial rule's level plus two, and then nine more
passes move nothing. That shape is what you would expect from a machine latching onto a copy
rule, not from a machine building up a structural reading.

### A small completeness note on the teaching set

`BRAIN_LINEAGE.md` says teaching used 19 worlds — 11 machines and 8 grammar patterns. That is
exactly right as **focus** worlds, and I confirmed it. But three more worlds appear as
**supports** inside trained records: a packed kit (99 times), a cooking procedure (216 times),
a caption pattern (once). The machine read 22 worlds during training. None of them is a held
world, so this is not a leak — just a number the lineage file does not mention.

---

## Verdicts, in the required form

| section 7 test | did it break the claim? |
|---|---|
| 1. commonest-answer guessing | ✅ **No.** 0 of 45. Attack failed cleanly. |
| 1b. zero-learning rules (extra, not in the pack) | 🟥 **Yes.** 11 of 18 without learning; gate fails at p = 0.50 / 0.50 / 0.69 against it. |
| 2. gains concentrated on giveaway questions | 🟥 **Yes.** 33 of 33 gains are one-answer questions; 0 of 15 multi-answer gains. |
| 3. held worlds leaked into training | ✅ No. Zero held ids anywhere in training. |
| 4. memorising | 🟨 Mostly no — but "new wiring" is wrong, and 2 of 20 part names were seen. |
| 5. one lucky run | ✅ No. Three machines reproduced all three seed identities. |
| 6. grader reads its data | 🟥 **Yes, badly.** A hand edit manufactured a `LEARNS_NEW_WORLDS` pass with `integrity: pass`. |
| 7. gate guards | ✅ No. All guards verified independently. |
| 8. recompute the 18 | ✅ No. Exact agreement. |

| section 6 check | outcome |
|---|---|
| 1 grader self-test | ✅ REPRODUCED |
| 2 hold-out audit | ✅ REPRODUCED |
| 3 unit tests | ✅ REPRODUCED |
| 4 preflight dry run | 🔧 running at time of writing |
| 5 the reading | ✅ REPRODUCED, byte-identical |

**What I did not change.** Per `AUDIT_PACK.md` section 10, I did not touch the verdict row in
`BRAIN_LINEAGE.md`. Nothing in the repository was modified. The verdict is the owner's to move.

---

## For the owner — decisions only you can make

1. **Add the zero-learning number to `BRAIN_LINEAGE.md`.** The grader prints "11 of 18 is
   reachable without learning" and the lineage file does not repeat it. Anyone quoting the
   lineage file quotes "0–2 → 11–12 of 18" with no floor beside it. My suggestion: put
   "a rule with no learned weights scores 11 of 18 on this same set" in the Helm 1.0 block and
   in the "MAY NOT be claimed" list. **Your call, not mine.**

2. **Decide whether the honest headline is "+2 over a trivial program".** Against the untrained
   machine the result is 10–12 gained at 1-in-1024. Against a program that reads the links off
   the page it is +2, at even odds, and the gate's own rule refuses it. Both are true. Which one
   leads is a claim decision.

3. **Fix the forgery path, or write it down as a known limit.** The label is a function of two
   editable JSON files per seed, and the grader does not check them against the sha256 the run
   itself recorded in `artifact_manifest.json`. A one-line digest check in `evaluate_gates.py`
   closes it. Until then, `BRAIN_LINEAGE.md` rule 3 should list the scoring files alongside
   certificates and lifecycle records.

4. **Correct "new wiring" in `BRAIN_LINEAGE.md`.** All five held worlds have a link pattern the
   machine was trained on. "New individuals, new names" is right. "New wiring" is not.

5. **Correct "parts and names it had never seen".** `Chuck` and `Gear` were both seen.

6. **Fix `AUDIT_PACK.md` check 4's wording** — the scratch directory must not exist, or the
   script stops.

7. **Independent AWS confirmation is still open.** I confirmed the money and the shutdowns from
   the run's own records only. Nobody has queried AWS from outside.
