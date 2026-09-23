# Why Helm, and why Helm did not pass: team review, 2026-09-22

**What this is.** The owner asked for a team of agents to answer two questions. **Why Helm?**
**Why did Helm not pass?** This folder holds their committed findings, the final judge's rulings,
and every script and output they made.

**What this is not.** It is advice to the owner. It changes no claim status anywhere. No
certificate, grader, frozen record or old row was edited. The three GPU runs made during the review
are diagnostics. Their numbers are labelled `DIAGNOSTIC_NOT_CLAIM_BEARING`, which means they may
not be used as evidence for or against a capability claim.

Claim states used below:

- `MEASURED`: a team member ran a program during this review and saw the number (the team output
  spells this `MEASURED_BY_ME`).
- `READ`: quoted from an existing file, with its path and line.
- `INFERRED`: reasoning from measured or read facts.
- `OPEN`: not settled.

---

## How the review ran

- **Workflow run `wf_b5716bf0-378`**: 31 agents, 0 errors, 1,228 tool calls, 8,076,980 ms.
- **Round 1, solo research.** Seven researchers worked alone, blind to each other:
  - R1 origin;
  - R2 design;
  - R3 Helm 1.0/2.0 gate;
  - R4 Q4 code;
  - R5 Q4 data and outputs;
  - R6 cross-version pattern;
  - R7 contrarian.
- **Round 2, meeting.** Each researcher read all seven reports and agreed, disputed or revised. A
  dispute needed a fresh check of the files first. A chair merged the result.
- **Further research, 2 rounds.** Round 1 ran 4 read-only tasks and 2 GPU tasks. Round 2 ran
  2 read-only tasks and 1 GPU task. Before any task ran, the chair wrote down which outcome would
  mean what.
- **Committed.** A scribe committed 32 findings, D1 to D32, and listed 15 open questions.
- **Skeptics.** Three skeptics each tried to break the findings from one angle:
  - REPRODUCE re-ran the evidence;
  - ALTERNATIVE looked for other explanations;
  - DISCIPLINE checked that no claim said more than its evidence.
- **Final judge.** Ruled on every finding. Result: **15 UPHELD, 17 UPHELD_IN_PART, 0 NOT_UPHELD,
  0 OPEN.**
- **Nothing in any repository changed during the review.** Afterwards the orchestrator (the Claude
  session that ran the team) checked `q4-live`, `helm3-lab`, `vision-next` and
  `codex-cas-reconcile`. All four were clean and still at their earlier commits. The main checkout's
  modified files all predate the review.

### The orchestrator's own re-checks

- **Which Helm 2.0 run failed.** READ from `records/typed_pointer_001/admission_001/gate_reading.json`:
  - run 20260917 passed, 11 gained, 1 lost;
  - run 20260918 passed, 12 gained, 0 lost;
  - run 20260919 failed, 7 gained, 1 lost.

  `BRAIN_LINEAGE.md:231` prints run 20260917 as `False`. `BRAIN_LINEAGE.md:234-235` says the gate
  "requires zero broken on every seed". Both statements are wrong.
- **The trust tool's pass rule.** READ, `records/typed_pointer_001/trusted_rescore.py:437`: at least
  7 gained, 0 lost, and no luck-probability test. Its agreement check (`:462-470`) compares only the
  counts and the label, never each run's pass result.
- **The Q4 plan.** READ, `records/q4_authorized_20260922/plan.json`: 29 fields, and none is an
  accuracy target.
- **The name.** READ, commit `994950b5` (2026-09-19 23:52:57 -0700): "The owner chose the name."
- **The GPU scripts.** All six GPU scripts refuse to run without the GPU (`GPU_REQUIRED`). The RT2
  and RT7 re-runs first reproduced the original run exactly before doing anything new.

---

## Answer 1: Why Helm?

**What it is.** READ. Helm is the name of the learning part of the CNCM pointer machine. CNCM means
CAS Native Cognitive Machine. "The learning part" is the neural network whose numbers change during
training. The versions stand as follows:

- Helm 1.0 is the last certified release.
- Helm 2.0 is an experiment.
- Helm 3.0 is only planned. It has not been built.

**Why it was built.** READ.
- The machine before Helm learned the questions it practised. Its scores rose from 13, 18 and 17 to
  84, 85 and 86 out of 189.
- On five worlds it had never practised, it stayed flat. Those scores went from 2, 3 and 3 to 5, 3
  and 2 out of 45. (A "world" is a small made-up machine with named parts and links.)
- A check that cost nothing found the cause. Every input blended all 64 worlds into one 64-number
  vector. So a new world could not be read.

Sources: `records/typed_practice_001/PRACTICE_STUDY_RESULT.md:26-27` and
`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:16-24`.

**The fix.** READ.
- On 2026-09-19 the owner chose "pointer answers plus the checkpoint check". A pointer answer means
  "this part, here", inside the world being read, so the same skill works in any world.
- Agents then said pointing alone would not work. The input also had to change, so that the machine
  reads one world as a small graph. The owner replied "Accept both, carry on."
  (`docs/CNCM_TYPED_POINTER_STUDY_v0.1.md:52-55`).

**What it is for.** READ. The goal is learning inside the trained numbers, in the owner's words
"IT MUST BE LEARNING LEARNING AT THE NEURON LEVEL". The end goal is a working CASFORMER/CNCM. Gains
that come from hand-written rules never count as machine progress
(`HANDOFF_20260919_CNCM_POINTER_MACHINE.md:93-96`).

**Why it looks the way it does.**
- READ: The inputs carry no words, only the graph.
- READ: The pass test counts only questions about how parts connect. The reason is that a program
  which just copied one input flag had passed the older test.
- READ: The written plan warned before the run that the test was weak. Even at a true 50%
  improvement, the chance that all three runs would pass was at most 0.6839.
- READ: Only 6 different shapes exist among the 64 worlds
  (`docs/CNCM_TYPED_POINTER_STUDY_v0.1.md:165-172`, `:273-276`).
- INFERRED: So "new worlds" meant new names on shapes the machine had already practised.

**The name.** READ, then OPEN. "Helm" first appears in commit `994950b5`. The record says only "The
owner chose the name." No reason for the word is written anywhere the team searched. **Only the
owner can say.**

**Today's Q4 model is not Helm.** MEASURED. It is a separate lab model, a 70,818-number GRU (a simple
step-by-step neural network). It imports no pointer-machine code. It shares no task, data or
weights with Helm.

---

## Answer 2: Why did Helm not pass?

### Helm 1.0: it did pass, but the pass shows less than it seems

- **It passed the grader.** MEASURED. On the 18 fixed questions, it gained 10, 12 and 11 over its
  untrained start, with 0 losses.
- **The yardstick was its own random start.** READ. The grader compares each run with its own
  untrained start, not with a rule that learns nothing. It prints the no-learning score beside the
  result but does not subtract it. That was a written design choice.
- **It barely beat a no-learning rule.** MEASURED.
  - A rule that learns nothing already gets 11 of 18. Helm 1.0 ended at 12, 12 and 11.
  - Rules written down before the runs answer 16 of 18.
  - The only 2 questions Helm got right outside the no-learning rule were the same two, `7a391350`
    and `a3e70de9`, in every run.
- **The analogy part gives one fixed answer.** MEASURED. It gave the same world for all 70 analogy
  records. So it could never win an analogy question.
- **The learning stopped early.** MEASURED. Almost all of the gain came in the first of ten training
  passes.
- **A bug existed, but its effect is unproven.** READ: a wiring bug made the 8 reasoning rounds act
  as one. INFERRED: no measurement shows that this bug set the limit.

### Helm 2.0-experimental: one run of three fell short

- **One run failed, not two.** MEASURED.

  | Run | Gained | Lost | Chance of luck | Result |
  |---|---|---|---|---|
  | 20260917 | 11 | 1 | 13/4096 | passed |
  | 20260918 | 12 | 0 | 1/4096 | passed |
  | 20260919 | 7 | 1 | 9/256 = 0.03515625 | failed (above the 1/100 bar) |

- **The failure turned on one question at the very end.** MEASURED. The failing run's untrained
  start already had 4 of 18 right. It lost question `36988555` only at its last checkpoint. It
  passes at every earlier checkpoint.
- **A pass would not have shown 2.0 better than 1.0.** MEASURED.
  - On the 18, it is the same in two runs and one worse in the third.
  - On held-back questions without correspondence, it is lower in every run: 83 vs 84, 85 vs 88,
    79 vs 81.
  - Retention fell in 2 of 3 runs.
- **Its one clear gain is matched by a simple rule.** MEASURED. Correspondence (matching parts
  one-to-one between two worlds) went from 0 to 20 of 20. A rule that reads no links scores the
  same.
- **The repaired loop mostly stayed shut.** MEASURED. The loop ended nearly shut in 2 of 3 runs.
  The one run where it opened answers course reach questions exactly like two Helm 1.0 runs.
- **The learning curve did not keep climbing.** MEASURED. That was 2.0's purpose. Every run was flat
  after the first pass.

### Today's Q4 smoke: an engineering test with no pass mark, and it rebuilt nothing

- **There was no pass mark.** READ. No accuracy target was set before the run. The directive says a
  smoke run of this kind cannot support a capability claim.
- **The result.** MEASURED. 0 of 16 trees rebuilt, with the same tree `(^7^E + ^7^C)` for all 16.
  The training loss was still falling at the end. It was still worse than simple counters that
  ignore the input.
- **Only a true reader of the input could score.** MEASURED: all 256 development trees have shapes
  never seen in training. INFERRED: so a method that does not really read the input scores 0.
- **Where the budget came from.** READ. The 128-update limit came from the directive's smoke-test
  template (`q4_smoke_job.py:61`).
- **No code bug was found at the level tested.** MEASURED. The team checked these parts:
  - the hand-off from encoder to decoder;
  - teacher-forcing alignment (feeding the correct previous token during training);
  - the grammar mask and token codec, which replay all 2,304 visible rows;
  - the checkpoint, which reloads and reproduces all 16 predictions.
- **GPU diagnostics.** MEASURED, `DIAGNOSTIC_NOT_CLAIM_BEARING`:
  - **RT1 (forward only).** The 64-number hand-off is nearly the same for every input. The relative
    spread is 0.03772133314348652 on the 16 dev inputs. The lowest cosine over 272 inputs is
    0.9911303112245342. 55 of 64 units sit near their limit.
  - **RT7 (8 rows, 2,000 updates).** The same code memorised all 8 training rows exactly. On the 16
    dev inputs it then gave copies of memorised training trees: 0 of 16.
  - **RT2 (256 rows, 2,000 updates).** 0 exact anywhere: 0 of 256 training-type rows, 0 of 256 dev.
    Its loss on the training-type rows (1.043102) did fall below the input-blind counters (1.255115
    and 1.159039). So it began to use the input, but it got no leaf sequence right.
- **OPEN.** The remaining cause is not known. It could be too little training (RT2 gave each row
  about 7.8 showings), a 64-number hand-off that is too small, or the way the hand-off carries the
  input.

### The common root (INFERRED from measured parts)

1. **The yardstick was weak.** Each run was compared with its own random start, not with a rule that
   learns nothing. A climb up to the no-learning level could count as a pass.
2. **Simple fixed programs could already answer the tests.** The project's own programs answer every
   planned lab task (Q0 to Q6) exactly from what the model sees: 9362 of 9362 visible Q3 records.
   The "new" worlds reuse practised shapes.
3. **Parts were built but never fed or never read.** Examples:
   - the unused loop variable in 1.0;
   - the learning-rate slow-down that was never wired in;
   - an analogy part that never sees the world it is asked about;
   - a checking tool that never compares each run's pass.

   The tests checked the wiring, not the effect.
4. **The pass test was known to be weak before the runs.**
5. **The process lost evidence and copied rules wrongly.** A killed run left Helm 0.1 impossible to
   certify. A reworded "zero losses" rule spread through several records.

MEASURED: in all six Helm runs, almost all learning happened in the first pass.

---

## All 32 committed findings and the judge's rulings

Full statements, evidence and the judge's reasons are in `team_output.json` under `dossier` and
`judgment`.

| ID | Topic | Judge | State | Finding, in one line |
|---|---|---|---|---|
| D1 | Why Helm | UPHELD_IN_PART | READ | Helm exists because the machine before it could not read never-practised worlds: practised 13/18/17 to 84/85/86 of 189, held-back 2/3/3 to 5/3/2 of 45. |
| D2 | Why Helm | UPHELD | READ | Purpose: learning inside the trained numbers ("AT THE NEURON LEVEL"), toward a working CASFORMER/CNCM. Rule-layer gains never count. |
| D3 | Why Helm | UPHELD_IN_PART | OPEN | The name first appears in `994950b5` (2026-09-19 23:52:57 -0700). Only "The owner chose the name" is recorded. No reason is written down. |
| D4 | Why Helm | UPHELD_IN_PART | READ | Design: pointer answers, a graph input with no words, a pass test on connection questions. The plan warned beforehand that the test was weak. The 0.0216 / 0.2450 / 0.6839 figures are upper bounds. |
| D5 | Why Helm | UPHELD | READ | Today's Q4 model is not Helm. It is a separate 70,818-number GRU that imports no pointer-machine code. |
| D6 | 1.0 | UPHELD_IN_PART | MEASURED | The grader compares with the untrained start. 1.0 passed (10/0, 12/0, 11/0) but ended only +1, +1, 0 above the registered no-learning floor of 11 of 18. |
| D7 | 1.0 | UPHELD | MEASURED | Rules written before the runs answer 16 of 18. Every Helm run is below that. The only 2 answers outside the floor are the same pair in all six runs. |
| D8 | 1.0 | UPHELD | READ | The analogy part gives one fixed world for all 70 analogy records in every final model. "0.42 train / 0.00 held" was a constant, not memorisation. |
| D9 | 1.0 | UPHELD_IN_PART | INFERRED | The 1.0 loop bug (`block` assigned, never read) was real. No measurement shows it set the limit. |
| D10 | 2.0 | UPHELD | MEASURED | 2.0 failed on one run (20260919: 7/1, p 9/256), not two. The lineage file names the wrong run and the wrong rule. |
| D11 | 2.0 | UPHELD | MEASURED | The failing run started with 4 of 18 right and lost `36988555` only at the last checkpoint. It passes at every earlier one. |
| D12 | 2.0 | UPHELD | MEASURED | A pass would not have shown 2.0 better than 1.0: the same or worse on the 18, lower on held-back (without correspondence), retention down in 2 of 3. |
| D13 | 2.0 | UPHELD | MEASURED | The repaired loop starts shut in every run and ended nearly shut in 2 of 3 Helm 2.0 runs. |
| D14 | 2.0 | UPHELD_IN_PART | INFERRED | Nothing in the saved answers shows the open loop being used. This does not prove the loop is unused. |
| D15 | Pattern | UPHELD | MEASURED | Helm mostly picks the common neighbour as the VIA part (135/165). The mixed cases are 18 "diamond" records whose gold answer depends on a tie-break Helm cannot see. |
| D16 | 2.0 | UPHELD_IN_PART | INFERRED | Untrained starts show no built-in pull toward the rank-last part (0 of 6 runs reach 2x chance). |
| D17 | 1.0 | UPHELD | INFERRED | The ten-node panel test had no power: all 59 questions are outside the trained input range. The cause of those misses is OPEN. |
| D18 | Pattern | UPHELD | INFERRED | The wrong "zero broken" rule entered by paraphrase (`AUDIT_PACK.md:60`) and was copied into later records, including `CHANGELOG.md:1196`. |
| D19 | Pattern | UPHELD_IN_PART | MEASURED | `trusted_rescore.py` uses a stricter rule than the grader: 15 gained/lost cells where the grader passes and the tool fails, 0 the other way. A future real pass could be voided. |
| D20 | Pattern | UPHELD_IN_PART | MEASURED | Several record statements do not match the receipts. See "Records that disagree with the receipts" below. |
| D21 | Q4 | UPHELD | MEASURED | Q4's 0/16 is a measured negative result, not a failed gate. No accuracy target was set. |
| D22 | Q4 | UPHELD_IN_PART | MEASURED | At the end of the smoke, the loss was still falling and still worse than input-blind counters. |
| D23 | Q4 | UPHELD_IN_PART | MEASURED | The repeated tree `(^7^E + ^7^C)` is the input-blind default shape. Exactly why the leaves are ^7, E and C is OPEN. |
| D24 | Q4 | UPHELD | MEASURED | The dev check cannot separate causes: dev tree shapes never occur in training (train 16, dev 9, shared 0). |
| D25 | Q4 | UPHELD_IN_PART | READ | The 128-update budget came from the smoke template, not from the designed experiment. |
| D26 | Q4 | UPHELD_IN_PART | MEASURED | No code defect found at the level tested (hand-off, alignment, mask and codec on 2,304/2,304 rows, reload 16/16). |
| D27 | Q4 | UPHELD | MEASURED (diagnostic) | The saved model's 64-number hand-off is nearly identical for every input. |
| D28 | Q4 | UPHELD_IN_PART | MEASURED (diagnostic) | 2,000 updates on 256 rows: still 0 exact anywhere. |
| D29 | Q4 | UPHELD_IN_PART | MEASURED (diagnostic) | The same code memorises 8 rows exactly, so the learning path works at small scale. |
| D30 | Pattern | UPHELD_IN_PART | MEASURED | The project's own programs already answer every planned lab task (Q0-Q6) exactly from the visible input. |
| D31 | Pattern | UPHELD_IN_PART | INFERRED | Common root: weak yardsticks, tests that fixed programs already answer, parts built but unfed, a pass test known to be weak, process losses. |
| D32 | Why Helm | UPHELD | READ | Helm 0.1 was the first claim-bearing job (2 to 12 of 18). It was never certified because its driver was killed. |

### Records that disagree with the receipts (from D20; corrections not yet made)

These lines are **flagged, not corrected**. Correcting them is an owner decision. The fix is a dated
note; old rows are never rewritten. Every line number in this report refers to the files at commit
`4eb98682`. This review adds a section at the top of `BRAIN_LINEAGE.md` and of `CHANGELOG.md`, so
their current line numbers are later.

- `BRAIN_LINEAGE.md:231` and `:234-235`: the wrong failing run, and the wrong "zero broken" rule.
- `BRAIN_LINEAGE.md:392`: another copy of the "zero broken" rule.
- `BRAIN_LINEAGE.md:195`, `:198`, `:200`: "the one-hop rule is the architecture's ceiling", "VIA
  needs two", "ten-node worlds need long chains". These are stated as measured causes. They are
  inferences.
- `BRAIN_LINEAGE.md:395` and `AUDIT_REPORT_20260920_INDEPENDENT.md:227`: "analogy is the one kind
  no zero-learning rule touches". The pre-run LB18 rule contradicts this.
- `BRAIN_LINEAGE.md:669`: the Helm 1.0 evidence pointer names Helm 2.0 folders.
- `AUDIT_PACK.md:60`, `AUDIT_REPORT_20260920_INDEPENDENT.md:231`, `CHANGELOG.md:1196`: the "zero
  broken" wording.
- `records/typed_pointer_001/ladder/build_ladder.py:159-164`: the "mirrors the frozen rule" comment.

---

## The GPU diagnostics: what ran and on what authority

Three short diagnostic runs used the local RTX 4070 laptop GPU.

- **RT1**: forward passes only, on the saved Q4 checkpoint.
- **RT2**: an in-memory re-run of 2,000 updates on 256 training rows. It took 28.855429800009006 s.
- **RT7**: an in-memory re-run of 2,000 updates on 8 training rows.

The limits were the same for all three:
- Each script refuses to run without the GPU, with no CPU fallback.
- The saved checkpoint was read only.
- No sealed or eval-split file was opened.
- Nothing was written into any model or repository folder.
- The outputs are in `evidence/RT1`, `evidence/RT2` and `evidence/RT7`.
- Each run's outcome rules were written and hashed before it ran (`PREREG_RT*.txt`).

**Authority.** The orchestrator set these limits. It acted under two things:
- the owner's standing authorization of 2026-09-22, which the owner pasted into this conversation
  (`docs/OWNER_RUN_AUTHORIZATION_20260922.md`);
- the owner's own request that the team "disperse to further research".

The judge noted that no run record named its authority. This section is that record. It is an agent
record, not an owner-signed one.

---

## Judge's recommendations (advice; most need the owner's decision)

1. **Add effect tests.** Check that each planned mechanism actually changes a number. Also check
   that the Q4 output changes when the input changes. Cost: $0 and minutes of local GPU. No owner
   decision needed.
2. **Add dated correction notes** for the records listed above. Never rewrite old rows. About one
   hour, $0. *Owner decision.*
3. **Sign one per-run pass rule.** Then align `trusted_rescore.py` with the frozen grader, so it
   cannot void a genuine pass. $0, a small code and test change. *Owner decision.*
4. **Name the no-learning floor** that Helm results are read against: 11, 16 or 18 of 18. Report
   future results net of it, beside the frozen label. The certified 1.0 label is not re-graded.
   *Owner decision.*
5. **Fix the test bank before any new Helm training spend.** Use held-out worlds with genuinely new
   shapes, real multi-step and "no path" questions, and the strongest no-learning baseline for every
   question kind. Do a power check before launch. *Owner decision.*
6. **If the loop question matters:** first run forward-only checks on the Helm 2.0 weights with the
   loop forced shut. Only then consider a pre-registered three-run Helm 2.x study on AWS with the
   learning-rate schedule (F4) actually wired in. INFERRED cost: about $18 cash plus the $15.00
   per-job reservation. *Owner decision.*
7. **If Q4 continues:** write the outcome rules first. Then run longer on the same 256 rows (about
   32,000 updates, about 8 minutes on the local GPU for development), with a held-out check on
   shapes seen in training. Note: a 20-line parser already rebuilds 16/16. So success would only
   show that the learned hand-off keeps the structure. *Owner decision.*
8. **Confirm the authority for agent-run GPU diagnostics** in a signed or otherwise executable
   record. Also confirm whether it replaces the rule that phase approvals must be owner-signed.
   *Owner decision.*
9. **Note a partly carried-out decision.** The owner's 2026-09-19 choice was "Stratify AND train
   longer". Training stayed at 10 passes after an agent wrote "Ten passes is enough"
   (`CHANGELOG.md:1569-1572`). INFERRED: longer training would probably not have changed the gate.
10. **Ask the owner why the name "Helm" was chosen**, and record the answer in `BRAIN_LINEAGE.md`.

## Still open (15)

The full list with reasons is `team_output.json` → `dossier.unresolved`. The main items:

- Why the word "Helm" was chosen. Only the owner knows.
- For Q4: too little training, or a limit of the 64-number hand-off? And can this design learn a
  general leaf-copy skill?
- Which no-learning floor governs. Which per-run pass rule governs. Owner or custodian decisions.
- For Helm, questions the current question bank never tests apart:
  - Does it pick its 2-hop VIA part by the common-neighbour rule or by a one-sided cue?
  - Does its correspondence part read the declared order, or the structure?
  - Did the unwired learning-rate schedule cause the last-checkpoint flip?
- What gate a future integrated Helm 3.0 will be judged by. When a task that the project's own
  programs cannot compute enters the plan.

## Dissent recorded by the judge (not adopted)

The full list is in `team_output.json` → `judgment.dissent_recorded`. Three examples:
- "The loop was held shut by design, so the repair was never exercised." Kept as a live alternative,
  not adopted as the explanation.
- "The authoritative floor is 16 of 18." Not adopted, because choosing the floor is the owner's
  call.
- "The unwired F4 schedule caused the flip." Not adopted. It stays OPEN.

## Files in this folder

- `README.md`: this report.
- `team_output.json`: the complete team output, in one file. It holds the 7 solo reports, 7 meeting
  responses, 3 chair states, 9 follow-up results, the committed dossier, 3 skeptic reviews and the
  judgment.
- `evidence/<AGENT>/`: every script and output the agents wrote. Findings cite these as
  `SCRATCH/<AGENT>/<file>`, which here means `evidence/<AGENT>/<file>`.
- `EVIDENCE_MANIFEST.json`: the byte size and sha256 of all 284 files.
  - 282 are committed here.
  - Two derived outputs over 2 MiB, `RT3/out_structure.txt` and `RT5/rt5_inputs.json`, are only in
    the archive.
  - A full copy of everything is at `D:/tksCAS-archive/helm_why_review_20260922`.
- `.gitattributes`: keeps the evidence bytes exact, so the recorded hashes stay valid after checkout.
