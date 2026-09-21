# The learning brain — lineage record

**This file is the single place that names the brain that learns, says what it has actually
achieved, and says where the proof is. Every agent that touches this work reads this file first
and updates it in the same commit as any new result.**

If you are an agent picking this up: do not rename the brain, do not restate a result from prose,
and do not promote a claim that this file marks as not certified. Add a row to the table, point it
at the evidence folder, and leave the old rows alone. Negative results stay. They are the reason
any of the positive ones can be trusted.

**If your job is to audit, verify, or independently test this work rather than extend it, read
`AUDIT_PACK.md`** — it carries the exact commands, the frozen numbers, the file hashes, the traps
that have already fooled people, and eight attempts to break the claim that you are expected to run
and report on.

---

## The brain

| | |
|---|---|
| **Name** | **Helm** |
| **Current shape** | **2.0-experimental — RAN on AWS 2026-09-20, three seeds, source `20208c92`. The grader printed `NO_TRANSFER_TO_NEW_WORLDS`. NOT certified. No claim of upgrade.** See the "Helm 2.0-experimental — ran" section. |
| **Last certified** | **1.0** — and the reason its result was so thin is now known: its loop was broken. Read the mechanism section below before quoting 1.0. |
| **What it is** | The learning part of the CNCM pointer machine. It reads a small structure of parts and "contains" links, and answers questions about which part holds which. |
| **Learned numbers** | **157,919**, in **46** groups |
| **Biggest group** | the word table, `declaration_table`, 1,024 × 64 = **65,536**, which is **41.5%** of the whole brain |
| **Does it grow as it learns?** | **No.** Learning changes the values, never the count. The count moves only when the design is widened on purpose, and that is a version bump. |

### Versioning scheme

| version | meaning |
|---|---|
| **0.x** | being tried out. Nothing officially certified. |
| **1.0** | the first version that passes the official three-run test. |
| **1.1, 1.2** | same shape, trained better. |
| **2.0** | the shape changed, so the number count moved. |

**Proposed extension, 2026-09-21 — owner to ratify before any label below is used as official.**
*The owner-side response of 2026-09-21 keeps this scheme and attaches conditions (rc requires the
unchanged three-seed label AND closed evaluator-integrity/custody gates AND criteria frozen before
the confirmatory run; averaging or best-seed selection may not hide a mandatory-family failure;
disclosure of a regression waives nothing). Recorded verbatim, with the corrected Q0 status
`Q0_DISCOVERY_COMPLETE / Q0_EVALUATOR_BOUNDARY_OPEN`, in
`records/typed_pointer_001/LINEAGE_RATIFICATION_CLARIFICATIONS_20260921.md`. Still marked proposed
until the owner's own word.*
**ACCEPTED BY THE OWNER, 2026-09-21.** The owner's words in chat: "I AGREE WITH THE NAMING SCHEMA". The progression
*experimental -> release candidate -> release* below, with the conditions recorded in
`records/typed_pointer_001/LINEAGE_RATIFICATION_CLARIFICATIONS_20260921.md`, is from this date the official rule for naming
Helm versions. (Recorded by Fable from the chat; not an owner-signed record. The paragraph above is kept as it was written.)
The owner asked for a progression *experimental → release candidate → release* and for it to be
reconciled with the rules above. Reconciled, it reads:

| label | what earns it | what it may claim |
|---|---|---|
| **X.0-experimental** | the shape changed and its `$0` structural gate passed. It may have been run. Whatever the grader printed is recorded verbatim, pass or fail. | **Nothing.** An experimental identity says only "this shape exists and was measured." |
| **X.0-rc** | the frozen grader printed `LEARNS_NEW_WORLDS` on all three seeds, **and** the comparative acceptance tests are recorded with four separate statuses (`engineering`, `representation`, `operation`, `benefit`): held-out cases, meaningful internal interventions, matched comparison arms, and a regression check across **every** task family, not only the gate. | "Passed its own tests." Not yet audited. |
| **X.0** (release) | rc, **plus** an independent audit reproduced it, **plus** release notes that name every family it weakened as plainly as every family it improved. | The version number without qualifier. |

Under this scheme, today: **Helm 1.0** is a release (certified, then independently audited on
2026-09-20 with its interpretation downgraded and its result intact). **Helm 2.0 is
2.0-experimental** — its gate reading is `NO_TRANSFER_TO_NEW_WORLDS`, so it cannot be an rc, however
large its other gains. **Helm 3.0-experimental** is reserved for the CAS-integrated shape and does
not exist yet; nothing of it is built. Old checkpoints are never overwritten; any reuse of one
version's weights in another requires a migration record listing every tensor as carried,
reshaped, absent or fresh — the discipline `rounds_iterate_check.py:_container` already follows.

---

## WHY HELM 1.0's RESULT WAS SO THIN — the mechanism, found 2026-09-20

**Helm 1.0's eight reasoning rounds were one round, repeated eight times.** The loop read the state
into a local named `block` and then never used it. All three per-round aggregates were computed from
`raw` — the frozen input rows — so the round input was a **constant**, and the machine's reach was
**exactly one hop, at 8 rounds or at 800.**

The function's own docstring said `norm(h)`. The code said `norm(raw)`.

```python
for round_index in range(CORE_ROUNDS):
    for position, (start, stop) in enumerate(offsets):
        block = hidden[start:stop, :]        # assigned, NEVER READ
        raw   = blocks[position][2]          # the frozen rows
        inputs.append(  _rms_unit(torch, raw))
        parents.append( _rms_unit(torch, adjacency.matmul(raw)))
        children.append(_rms_unit(torch, adjacency.transpose(0,1).matmul(raw)))
```

**This explains everything the independent audit measured.**

| what the audit found | why, mechanically |
|---|---|
| a rule that learns nothing scores **11 of 18**, and Helm scored 12/12/11 | the one-hop adjacency rule **is the architecture's ceiling**. Helm did not "only learn a trivial rule" — a trivial rule is the **only thing it could compute**. |
| `analogy` **0 of 5** before and after, all seeds | analogy needs a containment pattern compared **across** worlds. Impossible at one hop. |
| `context`, `definition`, `parts`, `edge_account` at **1.00 on both training and held** | all four are one-hop questions. Saturated, with zero headroom to show learning. |
| `reach` 0.94 train / 0.88–0.96 held | DIRECT is one hop and learnable; **VIA needs two** and was out of reach. |
| `correspondence` **0.09 on its own training data** | every head ended `Linear(64→2)` and every source was scored against the same query vector, so **every source got the identical ranking** — a one-to-one mapping was not merely unlearned but **unrepresentable**. |
| the ten-node panel at 7/59, 9/59, 6/59 | bigger graphs put more of the question outside one hop. |

**So the correct description of Helm 1.0 is not "it learned a shallow rule".** It is: **the label is
real, and what it measured was the ceiling of a broken loop.** The study asked a one-hop machine a
question needing more than one hop, and the one-hop machine answered exactly as far as it could.

**Do not use Helm 1.0's numbers to argue anything about Helm's capacity.** They measure a defect.

---

## Helm 2.0-experimental — RAN 2026-09-20. The grader printed `NO_TRANSFER_TO_NEW_WORLDS`. NOT certified.

**Recorded 2026-09-21 by the session that did the independent audit and built F1/F2/F3/F4.** The
three runs below were launched and collected by a *different* session working on this same branch
on 2026-09-20 (commits `df20eb46` … `3da10d84`); their receipts reached the tree after that
session's last commit and were swept into this session's `c8d5c430` and `27fd5698` by `git add -A`.
This section is the record those receipts were owed. The certified Helm 1.0 evidence was **not**
touched: it lives byte-identical under `receipt_helm1_certified_2026091{7,8,9}/` and
`admission_helm1_certified/` (renamed by `df20eb46`, zero content changes; `verify_evidence_hashes.py`
→ 297 files, `EVIDENCE_HASH_CHECK:PASS`; `gate_reading.json` sha256 still `475379d2f9d47387…`).

**The runs.** Jobs `cas-meta2-tpntr-20260920210258-20208c92-m-{20260917,20260918,20260919}`, source
frozen at `20208c92` — which is F1/F2/F4 **plus** that session's repair of a first-update NaN in
`_rms_unit` (`9e9ba62a`: clamp the mean square before the sqrt; forward bitwise unchanged) and an
ablation-coverage fix. All three: `COMPLETE_TYPED_POINTER_ARM`, no failed checks, full 10-pass
`REGISTERED` schedule, 1,470 updates, 174,303 numbers in 48 groups. Evidence hash check on all three:
297 files, `PASS`. Reading: `admission_001/gate_reading.json`, sha256 `52877c1670132c70…`.

```
LABEL : NO_TRANSFER_TO_NEW_WORLDS
integrity: pass, failures []
G_LEARN_population: FAIL  (per seed: 20260917 False, 20260918 True, 20260919 False)
```

Two seeds each **broke one** frozen question (gained 11 / lost 1, gained 7 / lost 1), and the gate
requires zero broken on every seed. Both broken questions are `reach`, and both are in
`RANK_LAST_SOLVED_QUESTION_IDS` — the "point at the alphabetically last node" floor. Helm 2.0
stopped exploiting that shortcut and paid for it on the gate.

### Every number, beside Helm 1.0 (certified) on the same questions

| | seed 20260917 | seed 20260918 | seed 20260919 |
|---|---|---|---|
| the frozen 18, before → after | 2 → **12** | 0 → **12** | 4 → **10** |
| gained / broken | 11 / **1** | 12 / 0 | 7 / **1** |
| above the zero-learning floor (11) | 2 | 2 | 2 |
| *Helm 1.0 frozen 18 / above floor* | *12 / 2* | *12 / 2* | *11 / 2* |
| never-shown worlds, per answer (127) | **103** (1.0: 84) | **105** (1.0: 88) | **99** (1.0: 81) |
| the whole course (564) | **495** (1.0: 392) | **495** (1.0: 422) | **490** (1.0: 407) |
| memory check (96) | **78** (1.0: 93) | 93 (1.0: 93) | **82** (1.0: 87) |

**By kind, on the 127 never-shown-world answers, 1.0 → 2.0:**

| kind | 20260917 | 20260918 | 20260919 |
|---|---|---|---|
| `correspondence` (20) | 0 → **20** | 0 → **20** | 0 → **20** |
| `analogy` (17) | 0 → 0 | 0 → 0 | 0 → 0 |
| `reach` (26) | 25 → **23** | 25 → 25 | 23 → **20** |
| `parts` (9) | 9 → **7** | 9 → 9 | 6 → 6 |
| `role_set` (6) | 1 → 4 | 5 → **2** | 3 → 4 |
| `context` / `definition` / `edge_account` | 17/17, 15/15, 17/17 — unchanged | same | same |

**The gain that the certified instrument cannot see.** `correspondence` went from **0 of 20 to 20 of
20 on never-shown worlds, on all three seeds.** That is F2b, the matching head. The audit had classed
that kind *inexpressible* and all five of its questions were removed from the frozen 18 — so the gate
is structurally blind to it. Mechanism-free baselines registered against the same 20 questions,
exact match against the checker's admissible answers: **unique in/out-degree + declared-whole
signature match 4 / 20; positional match 0 / 20; always `NO_MATCH` 0 / 20.** Helm 2.0 beat the
cheapest rule by sixteen. **Open:** a full isomorphism matcher with lexical tie-breaks has not been
registered; 4/20 is the cheapest baseline, not the strongest.

**What did not move and what got worse.** `analogy` is 0 of 17 on every seed, exactly as
predicted — it needs relational features, not a bigger loop. `reach` fell on two seeds, `parts` on
one, and **retention fell on two seeds** (93 → 78, 87 → 82). Training loss went far lower than 1.0
(0.4629 → 0.0745 on seed 20260918, against 1.0's 0.1598). F4's clipping was live — 187 of 1,470
updates clipped, largest pre-clip norm 24.566 — and F4's schedule was **dormant**
(`CONSTANT_AS_HELM_1_0`; `planned_main_updates` still not wired).

### Four statuses, as the implementation directive requires

| status | reading |
|---|---|
| `engineering_status` | **PASS** — three clean runs, hashes intact, source frozen, gate check passes. |
| `representation_status` | **PARTIAL** — one previously inexpressible kind is now expressed and transfers; one (analogy) is untouched. |
| `operation_status` | **NOT APPLICABLE** — no CAS operation modules exist in this lineage; that is 3.0. |
| `benefit_status` | **MIXED, NOT AN UPGRADE ON THE CERTIFIED INSTRUMENT.** Large gains on per-answer measures and on correspondence; the frozen gate failed; retention and reach regressed on two seeds. |

### The best seed, and what is preserved

**Best Helm 2.0-experimental seed: 20260918** — 12/18, 105/127, 495/564, 93/96 — the only seed
that held retention. Archived at `D:\tksCAS-archive\helm_2_0_experimental_20208c92\receipt_20260918`
with `final.pt` sha256 `a6e72caac1fccbd994433a46684846f5a3de48683dcc6b5def5946b85ef20658`, all
hashes confirmed against the repository copy. **Best certified seed remains Helm 1.0's 20260918**
(12/18, 88/127, 422/564, 93/96), archived at
`D:\tksCAS-archive\helm_1_0_certified\receipt_helm1_certified_20260918` with `final.pt` sha256
`a63b2428f77b0151…`, confirmed against the `c95dc6ac` bytes. Neither will be overwritten. Any 3.0
reuse of either needs a migration record.

**MAY be claimed:** Helm 2.0-experimental, on the same frozen questions and the same never-shown
worlds as the certified 1.0 runs, answered `correspondence` perfectly where 1.0 answered none and a
structural rule answers four; it answered 19, 17 and 18 more of the 127 never-shown-world questions;
and it answered 103, 73 and 83 more of the whole course.

**MAY NOT be claimed:** that Helm 2.0 is an upgrade over 1.0 — the frozen grader refused it, it is
level with 1.0 above the zero-learning floor, and it lost retention on two seeds; that the loop
repair alone explains any of this — the run also carries the NaN repair and the matching head, and no
ablation separates them; that anything here is certified.

---

## Helm 2.0 — built 2026-09-20, NOT trained, NOT certified

**No claim is made here. There is no result.** This section exists so the next agent knows what shape
exists and what has and has not been shown.

**Branch:** `research/helm-2.0-iterating-rounds`, commit `7f3a656f`, based on `6580add4`.
**Cost: `$0`.** No GPU, no run, no reservation, no ledger entry, no claim promoted.

The shape changed, so the version moved to 2.0 by the scheme above.

| | Helm 1.0 | Helm 2.0 |
|---|---|---|
| learned numbers | 157,919 | **174,303** (+16,384, +10.4%) |
| tensor groups | 46 | **48** |
| reach | **1 hop, always** | **up to 8 hops** |
| round input | 3 frozen feature rows (54 wide) | **3 state vectors (192 wide)** |

**What changed, in plain terms:**

- **F1 — the loop now reads its own state.** New `state_encode` `Linear(64,64)`; `BLOCK_INPUT_WIDTH`
  54 → 192. This is the repair for the mechanism above.
- **F2a — the reach head is shown the pair it judges.** It used to decide "is this part inside that
  whole" without being shown either node. Input 132 → 260. `reach` carries 6 of the 18 gate questions.
- **F2b — correspondence can express a one-to-one mapping.** A bilinear pair score plus log-domain
  Sinkhorn steps, so different sources can prefer different targets.
- **F4 — gradient clipping at norm 1.0**, plus an opt-in warm-up/cosine schedule that is **off by
  default**, so the arithmetic is bitwise unchanged unless a caller asks for it. Both are recorded in
  every update row, so the guards are auditable rather than trusted.

**Verified on CPU at `$0`, by me, not by the agent that wrote it:**

```
python records/typed_pointer_001/rounds_iterate_check.py    ->  ROUNDS_ITERATE_PASS, exit 0
python -m pytest tests/test_typed_pointer_study.py -q       ->  22 passed, exit 0
```

Six checks, all real: no assigned-and-never-read name in `_rounds`; the round input is three state
vectors (`192 == 3 * 64`); **the round input differs across rounds and the difference grows steadily**
(`0.014739282429218292`, `0.02969013899564743`, `0.04484092444181442`, `0.06017898768186569`,
`0.07569090276956558`, `0.0913623794913292`, `0.10717859119176865`); **a change two hops away now
reaches the node** (`0.0018496513366699219` where 1.0 gave exactly `0.000e+00`), with the node's
one-hop neighbourhood asserted bitwise identical **and** the graph asserted really changed, so it
cannot pass vacuously; the reach head is 260 wide; and different sources now prefer different targets
with Sinkhorn columns summing to 1 (`1.1920928955078125e-07`).

**This says the machine is now CAPABLE of more than one hop. It does not say it is better.** What it
does with that capability is a question for a run and a grader, and neither has happened.

**Known trap, reported rather than hidden.** A Helm 1.0 checkpoint does **not** load strictly into
Helm 2.0: three tensors are absent (`match_key.weight`, `reach_option_head.0.weight`,
`state_encode.weight`) and one changed shape (`reach_option_head.0.weight`). The check prints all four
by name. Any continuation from a 1.0 checkpoint must drop and report them, **never silently coerce**.
The practice-checkpoint phase-A restore path has **not** been exercised and may need the same treatment.

### Still open, and this is the one that gates everything

**F3 — build a ruler a curve can be drawn on.** Eighteen yes/no questions cannot show a learning curve,
and six of the eighteen are questions a one-hop machine cannot reach. Until there is a difficulty
ladder by world size and hop distance, plus a continuous score beside exact-match, **no scaling run can
show anything.** Build it **beside** the frozen 18, **never replacing it**.

Then F5 — scale. `CORE_ROUNDS` 8 → 12 → 16 first, which costs **zero new parameters** because the
round is shared.

---

## Helm 1.0 — CERTIFIED on 2026-09-20, **INTERPRETATION DOWNGRADED on 2026-09-20**

> ## READ THIS BEFORE QUOTING ANY NUMBER BELOW
>
> **A rule that learns nothing scores 11 of 18 on the same questions.** The grader's own certificate
> says so, in its `oracle_ceilings` block:
>
> ```
> oracle_or_rank_solvable_in_the_label_population: 11     (of the 18 the label is keyed on)
> oracle_solvable_in_the_label_population: 7              (one-hop read: edge_account 5 + parts 2)
> applied_as_removals: false
> floor_note: "a zero-learning rule already answers these questions of the label's own population;
>              they are REPORTED and NOT subtracted, so the label must be read beside them"
> ```
>
> **Helm scored 12, 12, 11. Correct answers it produced that the no-learning rule does NOT produce:
> 2, 2, 2.** Run the gate's OWN bar (improved ≥ 7, broken 0) against that rule rather than against
> the untrained machine, and **all three seeds fail**: p = 0.50, 0.50, 0.69.
>
> **And `analogy` — the only one of the four kinds no trivial rule can touch — scores 0 of 5 before
> training and 0 of 5 after, in all three seeds.** All 33 gains sit on the 13 questions that have
> exactly one acceptable answer; **zero** gains on the 5 questions with more than one.
>
> **So the honest headline is `+2 over a program that reads the links off the page`, at even odds —
> not `0–2 → 11–12 of 18` at 1-in-1024.** Both are true. The second is measured against a starting
> point that cannot read the page; the first is measured against a starting point that can. The
> second is not wrong. It is just not the number that answers "did it learn to read structure".
>
> **What this does not do:** it does not withdraw the label. `LEARNS_NEW_WORLDS` is what the frozen
> grader prints, and it stands as a mechanical fact. **What it withdraws is my interpretation of it.**
> Helm 1.0 learned to apply a one-hop structural rule to structures it had never seen. It did **not**
> demonstrate the broader structural comparison the study was built to test. The certified label
> cannot tell those two apart, and I did not put the floor in this file when I first wrote it.
>
> Found by an independent audit on 2026-09-20:
> `records/typed_pointer_001/AUDIT_REPORT_20260920_INDEPENDENT.md`.

**The grader printed the label. This is the first version that earned it.**

```
LABEL : LEARNS_NEW_WORLDS
integrity: pass, failures []
```

The label was printed by `records/typed_pointer_001/evaluate_gates.py`, run over
`records/typed_pointer_001/admission_001/study.json` by `execute_study.py` as the last step of the
study itself. **No hand was on it.** Certifying reading:
`records/typed_pointer_001/admission_001/gate_reading.json`, 202862 bytes, sha256
`475379d2f9d47387a821c79e03a239f9a1f1277a0bbb25b298417557f9b058a9`.

### The three runs

Three seeds, three separate machines, run one after another on AWS. Every one of them finished
completely: launcher status `AWS_CANDIDATE_FINISHED`, `completed_deliverable: true`,
`cleanup.complete: true`, worker status `COMPLETE_TYPED_POINTER_ARM`, **no failed checks**, and the
save-and-reload step verified `true`.

| | seed 20260917 | seed 20260918 | seed 20260919 |
|---|---|---|---|
| the frozen 18, before | **2 of 18** | **0 of 18** | **0 of 18** |
| the frozen 18, after | **12 of 18** | **12 of 18** | **11 of 18** |
| gained | **10** | **12** | **11** |
| broken (must be 0) | **0** | **0** | **0** |
| the bar (7) | cleared | cleared | cleared |
| odds this is luck | **1/1024** | **1/4096** | **1/2048** |
| kinds improved (need 2) | **3** | **3** | **3** |
| worlds improved (need 2) | **5** | **5** | **5** |
| never-shown worlds, per answer (127) | 9 → **84** | 2 → **88** | 5 → **81** |
| taught worlds, per answer (358) | 16 → 258 | 10 → 284 | 13 → 275 |
| the whole course (564) | 30 → **392** | 17 → **422** | 20 → **407** |
| memory check (96) | 93 → 93 | 93 → 93 | 87 → 87 |
| the run's own clock | 7791.257429470999 s | 7834.867562267 s | 7792.573039091 s |

**All three seeds passed the primary test.** Nine of nine gate comparisons that the label depends on
came back `pass`.

### Every gate the grader reported

| gate | result |
|---|---|
| `integrity` | **pass** — `failures: []` |
| **`G_LEARN_population`** — the label's own test | **pass, all 3 seeds** |
| `G_LEARN_all_kinds` | pass, all 3 seeds |
| `TRAINED_start_to_final` | pass, all 3 seeds |
| `TRAINED_first_to_final` | pass, all 3 seeds |
| `G_LEARN_DIRECT_READ` | pass, all 3 seeds |
| `MORE_PRACTICE_population` | **fail, all 3 seeds** |
| `G_LEARN_TEXT` | **fail, all 3 seeds** |
| `kind_g_learn` (8 kinds) | **fail, all 3 seeds** |

### The three that did not pass, and why they are not failures of the claim

These are REPORTED comparisons, not the label. Say all three plainly whenever this result is quoted,
because a reader will notice them.

- **`MORE_PRACTICE_population` — failed.** It asks whether the machine got better *after its first
  pass*, i.e. whether extra practice beyond the first pass bought anything on the frozen 18. It did
  not: most of the gain lands in pass 1. So the honest reading of Helm 1.0 is **"it learned from the
  teaching it was given"**, not "it kept improving the longer it trained". This matches the earlier
  finding that the training loss flattened from pass 6.
- **`G_LEARN_TEXT` — failed.** That is the `role_set` tier, 6 questions, where **0 were gained and 0
  lost**. Nothing got worse; nothing got better. It is a null result on a tier the label does not use.
- **`kind_g_learn` — all eight failed.** These compare each question kind on its own, and the small
  kinds have only 5 or 6 questions. With a bar of 7 improved, a 5-question kind **cannot pass by
  construction** — the arithmetic makes it impossible regardless of the machine. These entries are
  informational. One of them is worth reading anyway: `edge_account`, `parts` and `reach` are where
  the real gains are, and those are exactly the three the primary test names as improved.

### A weakness in this test, found on 2026-09-20 — read this before quoting the result

**The five "never-shown worlds" are new parts and new names arranged in wiring that teaching had already
shown. All five. This was measured, not suspected.**

Throw away the part names and look only at the wiring — which part points at which — treating any
renaming of the same pattern as the same pattern. Then:

- Teaching used **19 worlds but only 6 distinct wiring patterns**. Five of the 19 share one pattern,
  five share another, and the rest repeat three more.
- The five test worlds use **4 distinct patterns**, and **all 4 of those are among the 6 patterns
  teaching already contained**.
- So **5 of the 5 test worlds** are a pattern Helm had already practised, redecorated with new part
  names.
- Part names are genuinely new: 68 distinct names in teaching, 20 in the test worlds, and only
  **two** appear in both — `Chuck` and `Gear`.

**What this does and does not change.**

It does **not** change the certified label. The grader is frozen, the question set was fixed before
the result was seen, and the worlds really were never read during training. `LEARNS_NEW_WORLDS` was
printed by that grader and stands.

It **does** narrow what the words mean. The honest description of Helm 1.0 is:

> new parts, new names, **already-seen wiring**.

Not "new worlds" in the sense a reader would assume. Helm did not have to work out a new kind of
structure. It had to apply a structure it had already seen to parts it had not, and get the direction
right. That is still real work — the before-behaviour was listing every possible pair and even naming
a part as containing itself — but the test is easier than the phrase "worlds it had never seen"
suggests, and anyone quoting this result must say so.

**The fix for Helm 1.1** is a harder test set: held-out wiring patterns that appear **nowhere** in
teaching, and larger worlds with more parts. Six patterns is a thin basis for a transfer claim, and
the current test cannot detect whether Helm can generalise to a shape it has never seen.

### What may be claimed, and what may not

**MAY be claimed:** Helm 1.0, measured by the frozen grader over three independent runs whose
question set was fixed before any result was seen, learned to read which part contains which in
**machines it had never been shown**, going from 0–2 of 18 to 11–12 of 18, gaining 10, 12 and 11
questions while breaking none, across 3 question kinds and all 5 held-out worlds. Retention held.
**Say it as: new parts, mostly new names, already-seen wiring** — the section above this one
measures why the last three words are required, and two of the 20 part names in the test worlds
(`Chuck` and `Gear`) had in fact been taught. **And say the floor beside it: a rule that learns
nothing scores 11 of 18 on the same questions.**

**MAY NOT be claimed:** that it works on anything beyond small structures of parts and containment
links; that the transfer is to a novel *domain* (the five held-out worlds are the same kind of thing
as 11 of the taught ones — machines); that the transfer is to **novel wiring**, which was the original
wording here and is **measured false** — all 5 held-out worlds reuse a pattern teaching already
contained, out of only 6 patterns teaching ever had; that it would handle a shape it has never seen,
which this test cannot tell you; that extra practice beyond the first pass helps; that the whole CNCM
machine exists.

**Also not claimed, and worth stating because it is easy to slide past:** this is a result on a
**fixed, stored** test set, not on new work arriving later. By the standard set out in
`CAS_RPA_Replay_Policy_Lab_Development_Directive_v1.md` section 12, that makes it a *screening*
result. "Fresh benefit" — does it help on genuinely new work under matched conditions — has **not**
been demonstrated for Helm and would need a different experiment.

**Certified is not the same as independently audited.** The grader is frozen and the runs are real,
but the same session built the machine and read the result. `AUDIT_PACK.md` names the checks and the
falsification attempts an outside agent should run.

---

## Helm 0.1 — the record (uncertified, kept as history)

**Measured on 2026-09-20**, job `cas-meta2-tpntr-20260920033528-1af25973-m-20260917`, seed
`20260917`.

### What it was taught

A world is a small set of parts with "contains" links between them. Teaching used **19 worlds**:

- **11 machines** — four parts, three links each, e.g. a Loom, Shuttle, Thread and Bearing wired
  together.
- **8 grammar patterns** — e.g. "a list pattern": **List, Item, Determiner, Marker**, where List
  contains Marker, Item contains Marker, and List contains Determiner.

**8 kinds of question** were asked, **564 questions** in all: `context` 70, `correspondence` 88,
`reach` 107, `definition` 70, `role_set` 36, `parts` 53, `analogy` 70, `edge_account` 70.
358 questions were used for practice, **127 were held back**, 79 were set aside and never counted.

Training: **10 passes**, **1470** weight updates, about 526 seconds per pass.

### What it was tested on

**5 worlds it was never shown.** All five are machines in a workshop. The link count varies — one of
them has four links, the rest have three.

| machine | its parts | what contains what |
|---|---|---|
| a weaving machine | Bearing, Loom, Shuttle, Thread | Loom→Thread, Shuttle→Thread, Loom→Bearing |
| a turning machine | Bolt, Chuck, Lathe, Tool | Lathe→Chuck, Lathe→Tool, Tool→Bolt |
| a transmission assembly | Gear, Gearbox, Manifold, Shaft | Gearbox→Shaft, Shaft→Gear, Gear→Manifold |
| a stopping assembly | Brake, Disc, Pad, Pinion | Brake→Pad, Brake→Disc, Disc→Pinion |
| a lifting machine | Bracket, Cable, Crane, Hook | Crane→Hook, Crane→Cable, Cable→Bracket, Hook→Bracket |

**Honest scope of the claim.** These five are the *same kind* of thing as some of the worlds it was
taught — machines — so this is transfer to **new individuals with new part names and new wiring**,
not to a wholly new kind of thing. That is real transfer. A machine that had memorised would fail
it. It is not a claim about novel domains.

### How well it did

The graders fixed **18 questions in advance**, all about the five never-shown worlds. This is the
score that counts, because it was chosen before the result was known.

| measure | before | after |
|---|---|---|
| **the frozen 18** | **2 of 18** | **12 of 18** |
| used to be wrong, now right | — | **10** |
| used to be right, now wrong | — | **0** |
| the bar it had to clear | — | **7** |
| odds this is luck | — | **1 in 1024** |

Everything else measured, for the record:

| measure | before | after |
|---|---|---|
| held-out worlds, per answer (127) | 9 right | **84 right** |
| taught worlds, per answer (358) | 16 right | 258 right |
| the whole course (564) | 30 right | **392 right** |
| all 45 eligible held-back questions | — | 26 gained, **0 lost** |
| taught questions (189) | — | 124 gained, **1 lost** |
| held worlds, retention check (96) | 93 | 93 |

### What it said before and after — the clearest evidence

Four of the ten gained questions, in the machine's own words:

| the machine | before | after | correct |
|---|---|---|---|
| a turning machine, every link | 7 links incl. `Tool contains Tool`, `Bolt contains Lathe` | `Lathe→Chuck`, `Lathe→Tool`, `Tool→Bolt` | same |
| a weaving machine, every link | all **12** possible pairs incl. `Thread contains Thread` | `Loom→Bearing`, `Loom→Thread`, `Shuttle→Thread` | same |
| a weaving machine, what the Loom holds | **nothing** — empty answer | Bearing and Thread | Bearing and Thread |
| a transmission assembly, what the Gearbox holds | Manifold | Shaft | Shaft |

Before, it was guessing: listing every pair, naming a part as containing itself, or answering
nothing. After, it read the actual structure of a machine it had never seen.

### The official verdict

**NOT CERTIFIED** — this is **Helm 0.1's** verdict, kept as history. Helm 1.0, above, is certified. The
paragraphs that follow explain why this particular run can never be certified, and that reason is a
lesson worth keeping.

The run itself succeeded completely — status `COMPLETE_TYPED_POINTER_ARM`, no failed checks, the
save-and-reload step verified `true`, 99 of 99 required files produced. But the frozen grader
**did not certify it and cannot**, for two hard reasons:

1. The certificate is written by the launching program, not by the machine doing the training. That
   program was killed by an interrupted tool call before it wrote the certificate. The grader reads
   `completed_deliverable` and `cleanup.complete` out of that file.
2. The ledger refuses to run the same job twice (`JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY`), so that
   job can never be run again.

There is no collect-only path, and writing the certificate by hand is forbidden — that is exactly
the forgery the whole design exists to prevent.

**So the correct way to describe Helm 0.1 is: the learning is real and measured with the graders'
own test code, and it is not an official pass.** Never write that Helm 0.1 "passed".

### Where the proof lives

| what | where |
|---|---|
| the machine's own records, 612 files, 143 MB | `records/typed_pointer_001/receipt_20260917_orphaned_1af25973/s3_worker_records/` |
| the launcher's records from that attempt | `records/typed_pointer_001/receipt_20260917_orphaned_1af25973/` |
| the grader | `records/typed_pointer_001/evaluate_gates.py` |
| the frozen question set, 18 questions | `cas_meta2/typed_teaching/pointer_contract.py`, `relational_population` |
| the three runs meant to earn the certificate | `records/typed_pointer_001/receipt_2026091{7,8,9}/` |

---

## Generations

Add a row. Never edit an old one.

| version | date | numbers | taught on | tested on | the frozen 18 | official verdict | evidence |
|---|---|---|---|---|---|---|---|
| **Helm 2.0-experimental** | 2026-09-20 (ran), recorded 2026-09-21 | **174,303** | 19 worlds (same course as 1.0), source `20208c92` | the same 5 never-shown machines | 2/18→**12/18**, 0/18→**12/18**, 4/18→**10/18**; gained 11, 12, 7; **broke 1, 0, 1** | **`NO_TRANSFER_TO_NEW_WORLDS` — NOT CERTIFIED. Not an upgrade on the gate.** Correspondence 0→20/20 on never-shown worlds (structural baseline 4/20); held-back 127: 103, 105, 99; whole course 495, 495, 490; retention **78**, 93, **82**. Best seed 20260918. | `receipt_2026091{7,8,9}/` + `admission_001/gate_reading.json` (`52877c16…`); `verify_evidence_hashes.py` PASS |
| **Helm 2.0** | 2026-09-20 | **174,303** | not trained | not tested | **no result** | **NOT TRAINED, NOT CERTIFIED, NO CLAIM.** Built and CPU-verified at `$0`; the loop now iterates and reaches 8 hops. | branch `research/helm-2.0-iterating-rounds`, commit `7f3a656f`; `rounds_iterate_check.py` |
| **Helm 1.0** | 2026-09-20 | 157,919 | 19 worlds (11 machines, 8 grammar patterns) | 5 never-shown machines, all reusing taught wiring | 2/18→**12/18**, 0/18→**12/18**, 0/18→**11/18**; gained 10, 12, 11; lost 0. **A no-learning rule scores 11/18 on the same set; Helm's margin over it is 2, 2, 2 at p = 0.50, 0.50, 0.69. `analogy` 0/5 in every seed.** | **`LEARNS_NEW_WORLDS` — CERTIFIED, all 3 seeds. Interpretation DOWNGRADED 2026-09-20. Cause now known: the loop was broken; one hop was the ceiling.** | `receipt_2026091{7,8,9}/` + `admission_001/gate_reading.json` + `AUDIT_REPORT_20260920_INDEPENDENT.md` |
| **Helm 0.1** | 2026-09-20 | 157,919 | 19 worlds (11 machines, 8 grammar patterns) | 5 never-shown machines | 2/18 → **12/18**, gained 10, lost 0 | **NOT CERTIFIED** | `receipt_20260917_orphaned_1af25973/` |

---

## Rules for whoever comes next

1. **A result is only a result if a grader printed it.** The grader here is
   `records/typed_pointer_001/evaluate_gates.py`, run over a study file. Run it and quote what it
   printed.
2. **Never call an uncertified run a pass**, however good its numbers look. Say "measured, not
   certified" and give both numbers.
3. **Never write or edit a certificate, a lifecycle record, a reservation, or — added
   2026-09-20 — `course_p00_scoring.json` or `course_p10_scoring.json`.** Those last two are the
   files that actually decide the label, and **as of Helm 1.0 the grader does not check them
   against the sha256 the run itself recorded in `artifact_manifest.json`.** An independent audit
   proved this by hand-editing seed 19's file: `LEARNS_NEW_WORLDS` still came out, with
   `integrity: pass, failures: []`. The real files were verified intact afterwards (297 of 297
   matched), so nothing is forged — but the guarantee is weaker than this file used to imply.
   **Verify with `records/typed_pointer_001/verify_evidence_hashes.py`, and fix the grader in the
   next version rather than editing the frozen one.**
4. **Read the certificate's `oracle_ceilings` and `contract` blocks, not just its headline.** They
   say what a rule that learns nothing already solves. Helm 1.0's file said `11 of 18` and this
   file did not repeat it, which is the mistake this rule exists to stop.
5. **Never change the 18-question set or the pass mark** to make a result land. They were fixed
   before the result was known; that is the only reason they mean anything.
6. **Do not delete a failed run's folder.** Run 7's failure and the two killed attempts are what
   prove the fixes were real.
7. **Update this file in the same commit as the result**, and point the new row at the folder.
8. **A certified label is not an interpretation.** The grader tells you what it printed. It does not
   tell you what was learned. Compare against a rule that learns nothing before saying a machine
   learned anything.
9. **Never edit source while a run is in flight.** `typed_pointer_worker.py:1516`,
   `_final_source_verification`, re-reads the **live working tree** at the **very end** of a run and
   refuses if it no longer matches the frozen rows. An edit made mid-run does not fail fast — it fails
   at the finish line, after all the compute is spent, and the run is discarded. Do not touch anything
   under `cncm/`, `research/`, or the four `records/typed_*_001` pin sets. Root-level files
   (`AGENTS.md`, this file, `AUDIT_PACK.md`, `CHANGELOG.md`) and `records/typed_pointer_001/` are not
   in the inventory and are safe. **This has already cost the project two runs** — a study driver
   killed between jobs by an interrupted tool call, and a dry run killed by a concurrent edit to
   `pointer_learner.py`.
