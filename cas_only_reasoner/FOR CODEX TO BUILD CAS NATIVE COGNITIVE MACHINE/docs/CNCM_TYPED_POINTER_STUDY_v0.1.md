# CNCM typed pointer study v0.1 — does a machine that points at the question's own parts learn, on worlds it never read?

**Status:** FROZEN BEFORE THE FIRST RUN, EXCEPT FOR ONE VALUE. Its sha256 is pinned into the study admission
(`admission_001/study.json`, field `protocol_sha256`). The one value left open is `PASSES` (§6). Nothing has been
run, no gate has been claimed, and `$0.00` has been spent on this study.

**Branch `codex/cncm-vision-next`.** The CNCM root is the `FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE`
directory under `_worktrees/vision-next/cas_only_reasoner/`. Every relative path below is relative to that root.

**On the two commits named in this document.** This protocol was drafted against HEAD `026e6473`, and every
statement it makes about the repository is a statement about that commit or about a named file read at that commit.
While it was being written, HEAD advanced to **`e3ee21c1`** — subject *"Exclude the rank feature, and record the
owner's AWS-first order"* — which landed two changes this document describes as pending or contested: the rank
feature flag in the contract, and the rule for where the smoke list runs. §11.2, §11.3 and §12 record both states
and which one governs. No number, threshold, gate or claim rule in this document changes between the two commits.

**Owner approval for this study, 2026-09-19, verbatim from chat:**

> "do option 1, pointer answers plus the checkpoint check BUT EXAMINE THIS TO SEE IF AND HOW IT OR ANYTHING IN HERE
> CAN HELP:      "C:\Users\wakil\Downloads\CAS-RPA × TypeSafe AI × CAS PCBA_ JEV Integration Deep Dive.pdf""

**Option 1 as it was offered to the owner, verbatim, and what was approved:**

> "Pointer answers + checkpoint check (my recommendation). Today the machine answers by choosing from a fixed list
> of 90 labels, like "node 3" or "world 46". A pointer version answers by pointing at a part of the question's own
> input: "this node here." That pointing skill is the same for any world, including new ones. It's the standard fix
> for "works on things it has seen, fails on new ones." Whether it actually works here is what the run would test.
> I'd build and dry-run it for $0 first. The paid run would be about the same size as this one (about $13, with $45
> reserved). The checkpoint check from option 3 runs on the same machine at no extra cost."

The two errors inside that offer were corrected before this protocol was written, and the owner accepted both:
the checkpoint check is **not** at no extra cost, and pointer answers alone cannot work because the INPUT must
change too. Both are recorded verbatim in §1.

## 0. Header block

### 0.1 Standing owner ruling in force

Owner ruling 2026-09-18, recorded at `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:93-96`: rule-layer gains never
count as machine progress. A gain in a rule, a schedule, a checker or a score is not the machine learning. Only a
change in the trained weights that moves the answers counts.

Standing owner goal, verbatim excerpt, same lines: "IT MUST BE LEARNING LEARNING AT THE NEURON LEVEL THE
ARCHITECTURE SHOULD BE SERVING THIS PURPOSE ... CONTINUE ON WITH AI AGENTS RESEARCH AND DEVELOPMENT UNTIL THE
ULTIMATE VISION OF THIS PROJECT IS FULLY FULFILLED MEANING WE HAVE A WORKING CASFORMER LLM/CNCM".

### 0.2 The owner decisions of 2026-09-19, verbatim

Five decisions were taken on 2026-09-19. Each was offered as a labelled option; the owner selected one label. The
selected labels are recorded verbatim and are copied into every job's `owner.json`, one record per job.

1. **The two corrections — accepted.** Owner answer verbatim: *"Accept both, carry on."* The two corrections are:
   (a) the in-job checkpoint check costs about $0.38–$0.63 per job, not "no extra cost"; (b) pointer answers alone
   cannot work, because the **INPUT** must change too — one world is read as a small directed graph instead of a
   blend of all 64 worlds.
2. **The short AWS smoke job for the end-to-end worker test S10 — approved.** Owner selected the option labelled
   verbatim *"Approve the smoke job (Recommended)"*. Cost model and shrunken schedule:
   `records/typed_pointer_001/pre_design/AWS_SMOKE_S10_PLAN.md`. The measured non-worker overhead is 598.2 s of boot,
   package install and delivery, costing $0.42 on its own.

   > **AMENDED 2026-09-19, before the smoke ran.** This item said *"Well under $1"* and *"the approved $1 leaves the
   > smoke a worker clock of at most about 830 s."* **Both are wrong, and the corrected figures are recorded here
   > rather than left standing, because this document is the governance record of what the owner approved and what
   > it buys.** Two independent corrections:
   >
   > 1. **The smoke needs TWO course evaluations, not one.** A reload-enabled plan must carry an evaluation at pass
   >    `0` **and** at pass `passes` — enforced at `cncm/typed_pointer_worker.py:190`
   >    (`POINTER_PLAN_RELOAD_EVALUATIONS`). The one-evaluation schedule would have been **refused outright**. The
   >    first course pass is also the cold one (`300.51911266499997` s cold against `173.78626021600007` s warm in
   >    the practice receipts), so the corrected worker clock is about **771 s**, not 470 s, and the corrected
   >    instance time is about **1,369 s ≈ $0.96 at $2.52/hour** — 96 % of the approved $1 with no margin. The S1–S9
   >    checks that ride in the same job cross it. The plan's own kill rule would have fired mid-run, because the
   >    one-evaluation estimate was low by **64 %**.
   > 2. **The smoke's reservation cannot be small.** `typed_pointer_launch.py:311,314` hard-requires the caller's
   >    amount and then reserves the study's own `RESERVATION_USD` (`15.00`); `reservation_plan_for()` pins
   >    `runtime_seconds_max` to `INSTANCE_SECONDS_MAX` (14400), and `budget.validate_plan` requires
   >    `reserved_usd >= bound`, making the minimum reservable about **$11.56** — so a $1 reservation is refused with
   >    `RESERVATION_BELOW_DECLARED_COST_BOUND`. `budget.py` exposes only `reserve_budget`: there is **no release,
   >    refund or settle function**, and the ledger carries `no_automatic_refund: true`.
   >
   > **The owner has since given standing pre-approval for all future jobs**, and the smoke proceeds at the
   > launcher's `$15.00` reservation with a cash cost of about `$1`. The $15.00 is a **cap commitment, not a
   > charge** — no money leaves the account — but it is not returned either, so it is recorded as a real commitment
   > rather than described as "small". Ledger, read from the CANONICAL `meta1` path, NOT the CNCM snapshot:
   > cap `5000.00`, reserved `546.00`, unreserved `4454.00`, revision 87. See §11 for why that distinction bites.
3. **The gate change — confirmed.** Owner answer verbatim: *"Yes — require the relational kinds."*
   `LEARNS_NEW_WORLDS` requires gains on the RELATIONAL kinds. The all-kinds result is reported alongside as a flag,
   never as the label.
4. **On purpose — the owner selected the option labelled "Run it as the transfer test, label honestly
   (Recommended)".** The study runs as the transfer test it was built to be, and the label is printed honestly: a
   tier or a kind whose answer is already in the input is reported as such and never carries a learning claim. The
   reconciled evidence behind the choice is `REVIEW_SYNTHESIS.md` §10.4, whose closing line is: *"This is the
   substance of what the owner decided on 2026-09-19: run it as the transfer test and label honestly."*
5. **On training — the owner selected the option labelled "Stratify AND train longer (Recommended)".** The schedule
   is stratified, so every kind appears in every update, and the study trains for more passes than the practice
   study's ten. The numbers behind both halves are in §5.

### 0.3 What changed from the design draft, and why (before anything was frozen or run)

This protocol is the successor and the freeze of `records/typed_pointer_001/pre_design/DESIGN_DRAFT_v0.2.md`
(1,341 lines at HEAD `d5e1dc1b`). It is assembly, not design: every decision here is already recorded in a source,
and each is cited. Four changes of form are worth naming.

- **The gate population is 18, not the 23 the leaks lens froze.** The leaks lens's own removal table gives 23 after
  six shortcut-rule removals (`measurements/leaks_review/lk6_gate_population_out.txt:43-44`). A seventh class was
  then applied: the five `correspondence` questions are removed because the drafted head **cannot express** a
  bijection at all. The union is 11 removals and a population of 18. The two figures are not a disagreement; they
  are two removal stages, and `REVIEW_SYNTHESIS.md` §12.2 records that distinction in a table. See §4.2 and §4.3.
- **The ORACLE one-hop rules are ceilings, not removals.** `REVIEW_SYNTHESIS.md` §10.1.1 settles the tension
  between the two lenses: applying the checker's own rule to the input **is the skill under test**, so those rules
  are the numbers to beat and are reported beside the label. See §4.4.
- **`PASSES` is deliberately not pinned here.** It is set from the smoke job's measured per-update cost. It is the
  only value this protocol leaves open, and §6 says exactly when it is filled in.
- **The rank feature is excluded.** The decision is exclude; at HEAD `026e6473` the contract file still said the
  opposite, and a concurrent edit has since landed the flag as `False`. Both states, and the residual uncertainty,
  are recorded in §12. See §4.3 and §5.3.

---

## 1. Purpose and claim boundary

### 1.1 What the study is

The pointer study asks one question: **does a machine that reads one focus world as a small directed graph, and
answers by pointing at a part of the question's own input, learn an answer skill that transfers to worlds it never
read?**

It is the same question the practice study asked, on a machine whose relation to its input is different. The
practice machine read one 64-number blend of all 64 worlds plus a scrambled code of the answer slot's name, so a
world it never practised was unreadable **by construction**. The pointer machine reads a graph and points at nodes.

The registered purposes of the study, exactly:

- contract `purpose`: `DOES_THE_POINTER_MACHINE_LEARN_RELATIONAL_ANSWERS_ON_WORLDS_IT_NEVER_READ`
  (`pointer_contract.py:655`);
- contract `input_unit`: `ONE_FOCUS_WORLD_READ_AS_A_DIRECTED_GRAPH` (`:666`);
- contract `answer_form`: `POINTER_INTO_THE_QUESTION_INPUT` (`:667`).

### 1.2 What the study is not licensed to claim

The contract's registered boundary, verbatim (`pointer_contract.py:647-651`):

> "Typed pointer reading of ONE focus world as a small directed graph, on one teaching order. The held-back
> questions are about five course worlds the machine never read (same world sizes and question kinds as training);
> the development panel is out-of-distribution ten-node parts/reach. The primary label is keyed on the RELATIONAL
> tier, so gains on the DIRECT_READ kinds alone cannot produce it. No protected final-study, general CAS
> architecture, or full-machine claim."

`NOT LICENSED`, unchanged from `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:364`: any claim about the pointer
machine, about CASformer attention, or about the architecture family — until a run produces a printed label.

Two consequences that must be stated out loud, because a reader will otherwise take them for granted:

- **A `LEARNS_NEW_WORLDS` label would not license a claim about the CAS architecture.** It would license exactly
  one sentence: after training on other worlds, the neurons answer correctly questions about five course worlds
  they never read, beyond the registered baselines, in all three seeds, on the RELATIONAL population of §4.
- **A `NO_TRANSFER_TO_NEW_WORLDS` label is a FAILURE and is never "PASS with caveats."** Negative results are kept.

### 1.3 What the study can never show, and why it is stated here rather than discovered later

The `correspondence` head as drafted cannot express a bijection (LB12, LB13, LB15). The word `analogy` is solved by
a same-shape-and-different-domain rule at zero learning (LB18). Both facts were measured before this protocol was
written, and both are handled in §4 and §7 rather than papered over.

**The gate's power is disclosed, not hidden.** At the frozen improvable population of 18, the probability that all
three seeds clear is **0.0216** if the machine genuinely improves 30 % of them, **0.2450** at 40 %, and **0.6839**
at 50 % (`GATE_FEASIBILITY.md` §5; `DESIGN_DRAFT_v0.2.md` §6.6). Every figure is an **upper bound**: it assumes no
losses, ignores the ≥ 2 kinds and ≥ 2 worlds rules, treats clustered questions as independent, and assumes uniform
improvement. So this study can return `NO_TRANSFER_TO_NEW_WORLDS` from a machine that learned something, and the
protocol says so before the run rather than after it. The three options the feasibility document sets out — run it
with `NO_TRANSFER` expected, enlarge the honest population, or pre-declare a weaker all-seeds rule — were put to the
owner, and the owner chose the first: *"Run it as the transfer test, label honestly (Recommended)"* (§0.2 item 4).

---

## 2. What is held fixed

The course, the hold-out, the split, the split's digests, the seeds, the encoder, the teaching condition, the
evaluation points and the development panel are the practice study's, **reused BY IMPORT and never re-derived**, so
the two studies stay comparable question for question.

| element | value | source |
|---|---|---|
| held records | 127 | hand-off §4; `INTERFACE_SPEC_PIPELINE.md:1497` |
| held questions | 50 | `INTERFACE_SPEC_PIPELINE.md:1445` |
| held worlds | 5, twin-free | hand-off §4; `practice_contract.HELD_WORLDS` |
| excluded records | 79 | `INTERFACE_SPEC_PIPELINE.md:1498` |
| trained records | 358 | hand-off §4 |
| updates per pass | 147 | `REVIEW_SYNTHESIS.md` §4.7 |
| interference | 16 batches | `INTERFACE_SPEC_PIPELINE.md:104` |
| replays | 2 | `INTERFACE_SPEC_PIPELINE.md:109` |
| checkpoints | 0, 1, 2, 4, 6, 8, 10 | `typed_practice_worker.py:43` |
| full-course checkpoints | 0, 1, 10 | `typed_practice_worker.py:44` |
| model seeds | 20260917, 20260918, 20260919 | `matched_contract.py:22` |
| condition | `MIXED_SAME_ITEMS` | `INTERFACE_SPEC_SHARED.md:1159` |
| source seed | 101 | `matched_contract.py:23` |
| encoder seed | 20260916 | `matched_contract.py:23` |
| evaluation depth | 8 for every evaluation | `INTERFACE_SPEC_PIPELINE.md:248` |
| development panel | 59 packets, ten-node worlds | `matched_contract.py:203` |

The reader is not read: the worker never reads a correct answer before training. The split is frozen as constants
in the contract, and the practice contract's custody rule (`practice_contract.py:11-12`) governs this study too.
Test P14 asserts the ordering.

**Reused unchanged by import** (`pointer_contract.py:156-162`, `:320-325`): `split`, `held_worlds`,
`held_back_questions`, `practice_schedule`, `interference_batches`, `retention_packets`, `development_packets`,
`load_material`, `public_packets`, `material_inputs`, `KINDS`, `CONDITION`, `MODEL_SEEDS`, `SOURCE_SEED`,
`ENCODER_SEED`, `PASS_CHECKPOINTS`, `FULL_COURSE_CHECKPOINTS`, `INTERFERENCE_UPDATES`, `INTERFERENCE_BATCH`,
`REPLAY_UPDATES`, `MAX_CORE_CALLS`, `WORKER_DEADLINE_SECONDS`, `MAX_WALL_SECONDS`, `RESERVATION_USD`,
`INSTANCE_SECONDS_MAX`.

### 2.1 The three digests that must remain identical

Registering them here is not bookkeeping. If any one of them moves, the hold-out is no longer the practice
study's, and no statement in this protocol about "worlds it never read" holds.

| what | digest | source |
|---|---|---|
| held record ids | `668e6ce73c426d1fcf8f2391e1a08d90c045ffb37fba95fc64e2658f5369ab1d` | `INTERFACE_SPEC_POINTER.md:55` |
| excluded record ids | `b82108e14554a9fe746a7cfcb1e2cb181a99a3019dc39a3596805f10934c2621` | `INTERFACE_SPEC_POINTER.md:56` |
| source training schedule | `1772c0a53933aa92ea7dfb6b2ce53dcd1089cb3634b089427caba3369977d275` | `pointer_contract.py:314`, `source_schedule_digest` |

Test P1 pins all three. The third is the **source** schedule digest (the base MIXED course the stratified pass is
built from), recorded as `stats["source_schedule_digest"]`; it is not the same number as either batches digest in
§5.1 and must not be confused with them.

### 2.2 What changes

Three things, and only three:

1. **The input reading.** One focus world is read as a small directed graph. The question is expressed by pointing
   at that graph's nodes. The answer is a pointer into the input rather than a label drawn from a fixed bank.
2. **The machine.** A new class `PointerCourseLearner` in a new file. Its `self.module` is ONE container holding
   every learned weight, the registered `^6` block included. The registered `^6` block itself is unchanged.
3. **The pass count and the pass composition.** The owner's fifth decision. See §5.

The registered learner file `learner.py` is **not modified**. Nothing under `cncm/` or `cas_meta2/` that already
existed is edited. `CAS_RRK_v0.1` is never written to.

---

## 3. Tiers, and what each may carry

Three tiers, fixed before the run (`pointer_contract.py:328-333`):

| tier | kinds | what it may carry |
|---|---|---|
| **DIRECT_READ** | `definition`, `context` | **reported only.** Never carries a learning claim. |
| **RELATIONAL** | `parts`, `edge_account`, `reach`, `correspondence`, `analogy` | the primary label is keyed here. |
| **TEXT** | `role_set` | **reported only.** Never carries a learning claim. |

**DIRECT_READ is reported only, and the reason is measured.** `definition` and `context` are the answer's own
fields fed back as input flags: a zero-learning flag copy gets **5/5** and **5/5** of their eligible held
questions, and **15/15** and **17/17** of their held records (LK2; LB2). A pure flag copier scores `b = 10`,
`c = 0`, `p = 0.0009765625` on the 10 eligible DIRECT_READ questions over 5 worlds, which clears the unchanged
practice gate and prints `LEARNS_NEW_WORLDS`. That is finding FP1, and it is why the label is keyed on RELATIONAL
and why test P12 requires that a flag-copy-only outcome receives **no** label.

**TEXT is reported only, and the reason is measured.** `role_set`'s `focal_excerpt` **is** the answer: a published
clause-prefix rule with zero learned weights reproduces **6/6** held-back and **30/30** trained `role_set` records,
and a position-free token-bag reading reproduces it identically. There are 36 distinct token-bag signatures and
**0** of them carry more than one distinct answer (LK1; `REVIEW_SYNTHESIS.md` §3). So `role_set` is registered as
`ANSWER_IN_INPUT`, it is run and reported, and its gains may never contribute to the label.

**Within RELATIONAL, one kind is a declared false negative and one is reported separately.**

- **`correspondence` is run, scored and published as a declared false negative.** The drafted head has no input
  depending on the target world's edge set, so every permutation in the source world's automorphism group gets an
  identical score and the tie rule picks the first syntactic bijection — correct in **0 of 20** held records, and
  in **81 of 88** records no additive per-node score can prefer a correct answer (LB12, LB13, LB15). It is
  excluded from the **label**, not from the study: the head scores it, its predictions are sealed, and the result
  is published as a declared false negative with the architectural reason attached.
- **`analogy` is reported separately, never as the sole basis of a label.** A same-shape-and-different-domain rule
  solves **17 of 17** held analogy records at zero learning (LB18), because only **6** non-isomorphic structures
  exist in the 64-world bank (class sizes 12, 12, 12, 12, 8, 8) and every held world has **7, 6, 11, 6, 11**
  same-shape trained twins (LB3, LB4). LK3 additionally measures that `analogy`'s admissible set is 6 or 9 worlds,
  so a guess is about 13–15 % per record. `analogy` stays in the population and its own numbers are printed beside
  the label.

---

## 4. The gate

### 4.1 The owner-confirmed primary label

Three labels only, and **the gate program's printed label IS the claim status**:

| label | when |
|---|---|
| `VOID` | any of I0–I4 of §7 fails |
| `LEARNS_NEW_WORLDS` | the RELATIONAL test passes in all three seeds |
| `NO_TRANSFER_TO_NEW_WORLDS` | it does not |

The all-kinds result is reported as a **flag**, never as the label. The exact arithmetic is unchanged from the
practice study and is re-derived by test P12:

- the test is `binomial_upper_tail(b, n) = Fraction(sum(comb(n, k) for k in range(b, n + 1)), 2 ** n)` — exact
  rational arithmetic, never floating point (`INTERFACE_SPEC_PIPELINE.md:1319-1329`);
- `n = b + c`, the number of discordant questions; ties are excluded from both;
- `ALPHA = Fraction(1, 100)`, `MIN_IMPROVED_KINDS = 2`, `MIN_IMPROVED_WORLDS = 2` (`INTERFACE_SPEC_PIPELINE.md:1313-1317`);
- **the minimum passing `b` at `c = 0` and `p ≤ 0.01` is 7**, because `2**-7 = 1/128 = 0.0078125 ≤ 0.01`, while
  **`2**-6 = 1/64 = 0.0156250` fails** (`INTERFACE_SPEC_PIPELINE.md:1361-1364`; `pointer_contract.py:335-336`);
- a question counts as correct ONLY if **every** one of its records is correct — `question_outcomes` requires
  `all(record_correct[r] for r in records)` (`INTERFACE_SPEC_PIPELINE.md:1366-1368`);
- each seed is tested on its own and `all(...)` requires all three (`INTERFACE_SPEC_PIPELINE.md:1385-1387`).

**The rule, in one sentence.** `LEARNS_NEW_WORLDS` is printed only if, **in each of the three seeds separately**,
over the frozen population of §4.3: `b > c`, the one-sided exact binomial `P(X ≥ b | n = b + c, p = 1/2) ≤ 0.01`,
and the improved questions span **at least two kinds and at least two held worlds**.

**Losses are expensive and are stated before the run.** With no regressions (`c = 0`) the smallest passing `b` is
7. At `c = 1` it is **10**, at `c = 2` it is **12**, and at `c = 3` it is **14** (`GATE_FEASIBILITY.md` §2). One
previously-correct question lost costs three extra gains.

### 4.2 The frozen removal table

The counting rule is the gate's own: a question is removed when **every** record of it is answered correctly by a
registered no-learning rule, so the unit of evidence is the question. Source:
`measurements/leaks_review/lk6_gate_population_out.txt`.

| removal | takes | ids printed at |
|---|---|---|
| 1. registered input-blind shortcut (already applied before the gate) | **0** | `:61` |
| 2a. FP2 `parts(declared_whole) = participants − declared_whole` | **3** (`parts` 3) | `:62` |
| 2b. `reach` flag rule (DIRECT if whole == declared_whole and part is a participant) | **0** | `:63` |
| 2c. edge flag rule (edges = declared_whole → participants − whole) | **0** | `:64` |
| 3. DG3 node-order-dependent questions (the private answer is not invariant under renaming the focus world's node refs) | **2** (`reach` 2) | `:65` |
| 4a. rank-0 pointing (alphabetically first node) | **0** | `:66` |
| 4b. rank-last pointing (needs the rank feature; the feature is excluded) | **5** (`parts` 1, `reach` 4) | `:67` |
| 4c. PRESENT for every node / every edge slot; ABSENT for reach; NO_MATCH for the rest | **1** (`reach` 1) | `:68` |
| 4d. argument-node pointing | **0** | `:69` |
| 4e. best single trained alias-form constant answer per kind | **0** | `:70` |

**The six shortcut-rule removals, with their exact `typed-query-…` ids, read from the run's own output.**

`parts` 3, the FP2 rule (`lk6_gate_population_out.txt:62`):

- `typed-query-4a0342c26f982758689611569bebd798f324a52a3b8ee25cb5f016b394e17509`
- `typed-query-6d9f6280ddb8dc463bfb557617353b7857fba6cfda057403516a79d8a5ec1249`
- `typed-query-a14f184d8f6cc4f3b80a87998515fe3c707c2dfb4f92a2358f1233fc43fba1d9`

`reach` 2, node-order dependence (`:65`):

- `typed-query-5850f9113bccb701f9bc1cd326758889b77cd0cb3f0a443181b9e1105c3f9e94`
- `typed-query-85a38565803471f8fe7867631871a54f1f5ba7d4be1ae01d8516d9b5af68e2c7`

`reach` 1, the PRESENT-for-all policy (`:68`):

- `typed-query-dde56958ee3398739016ce6152278d821a1691cb5875c191e9a42077da4b16f7`

The rank-last row's **5** ids are printed at `:67` but are **not** counted as removals, because that rule needs the
rank feature and the rank feature is excluded (§4.3). They are kept in the contract as a registered baseline so the
removal list stays reproducible. If the rank feature were adopted instead, the union would be **11 of these ids**
and the population would still be **18** (`lk6_gate_population_out.txt:49-55`), with a different composition.

Two arithmetic readings that are easy to mis-take, and both are stated so no later reader collapses them:

- The **"11 ids printed across the rules"** in `lk6_gate_population_out.txt:60-71` and in `REVIEW_SYNTHESIS.md` §10.1
  is the number of ids the run **printed**, not the number removed without the rank feature. The removals without
  the rank feature are **6**: FP2 `parts` 3 + node-order dependence 2 + PRESENT-for-all 1.
- `DESIGN_DRAFT_v0.2.md` §6.2 records a CONFLICT that the design draft's earlier line said "29 − 3 − 2 = 24", short
  by the PRESENT-for-every-node removal. The correct figure at that stage was **23, not 24**. This protocol uses
  neither 24 nor 23 as its population; see §4.3.

### 4.3 The frozen gate population: 18, and the seventh removal class

The five `correspondence` questions are removed from the label's population. This is a **different class of removal
from all six above**, and it must be described as such: the six are **shortcut rules** — cheap rules a machine could
copy from the input, whose removal stops a shortcut being counted as learning. The `correspondence` removal is an
**architectural inexpressibility**: the drafted head cannot represent the answer at all, so the questions can never
contribute a gain and they are dead weight in the denominator. It is a statement about the head design, not about
the machine's skill, and it is charged to the architecture rather than to the learning.

| | value |
|---|---|
| eligible held questions (all kinds) | 45 |
| RELATIONAL tier before removals | 29 |
| removals, shortcut-rule class | **6** — FP2 `parts` 3, node-order dependence 2, PRESENT-for-every-node 1 |
| removals, architectural-inexpressibility class | **5** — the `correspondence` questions |
| **total removals** | **11** |
| **gate population** | **18** — `analogy` 5, `edge_account` 5, `parts` 2, `reach` 6 |
| minimum passing `b` at `c = 0`, `p ≤ 0.01` | **7** (`2**-7 = 0.0078125`; `2**-6 = 0.0156250` fails) |
| **required share of the population to improve** | **7/18 = 0.3889** |
| feasibility, all three seeds | **0.0216** at 30 %, **0.2450** at 40 %, **0.6839** at 50 % |
| single-seed figures at N = 18 | **0.2783** at 30 %, 0.4509 at 35 %, **0.6257** at 40 %, 0.8811 at 50 % |
| **frozen population digest** | **`4b1e3c1f0b8f8be339e281410dc830fac1834432e8d816d67dce58906e90036d`** |

> **ADDED 2026-09-19, after this document was first drafted.** The population digest was not available when the
> protocol was written, because it could only be computed once the removal lists were filled in the contract. It is
> now pinned and **asserted**, not merely described: `pointer_contract.REMOVALS` carries the 11 ids,
> `pointer_contract.VERIFIED_POPULATION = 18`, `VERIFIED_POPULATION_BY_KIND` and `VERIFIED_POPULATION_DIGEST`, and
> both `tests/test_typed_pointer_study.py` (20 passed) and the independent 32-check verifier hold them. The list was
> re-derived by `pre_design/freeze_removals.py`, which reads the ids out of `lk6_gate_population_out.txt` rather than
> retyping them, and which reproduces this digest.
>
> Note that `by_kind` covers **all five** RELATIONAL kinds, so `correspondence` appears with a count of **0** rather
> than being absent.

Sources: `REVIEW_SYNTHESIS.md` §11.1 and §12.1; `GATE_FEASIBILITY.md` §5; `DESIGN_DRAFT_v0.2.md` §6.6.

**Why removing five questions does not weaken the gate.** A question the drafted head cannot answer can never
contribute a gain, so it enters neither `b` nor `c`. With `correspondence` in, the machine must still produce 7
gains from the same 18 answerable questions; with it out, exactly the same. The required share of what the machine
can actually move is **7/18 = 0.3889** either way. What the removal buys is honesty of reporting.

**The STRICT variant is reported, never the label's population.** Also removing the 11 oracle one-hop questions
gives **16**, share **7/16 = 0.4375** (`lk6_gate_population_out.txt:47`). LK17 records that its arithmetic is a
false-negative trap, because it removes exactly the questions that test the skill and leaves only the kinds this
corpus cannot test. It is printed as a sensitivity analysis.

**The contract must be set to match this population before the freeze.** `pointer_contract.py` currently carries
`REMOVALS = {"flag_rule": {}, "rank_rule": {}}` as an empty, typed placeholder and refuses to be read as a finished
population while it is empty (`RELATIONAL_POPULATION_UNRECONCILED`, `pointer_contract.py:473-478`, `:559-597`). The
frozen per-question `query_id` lists of §4.2 go into `REMOVALS["flag_rule"]` and `REMOVALS["rank_rule"]`, and the
five `correspondence` removals are registered as their own class. `RELATIONAL_POPULATION` in
`INTERFACE_SPEC_POINTER.md:46` is marked `OPEN:` and stays open until that edit lands. **Still unset at HEAD
`e3ee21c1`: both `REMOVALS["flag_rule"]` and `REMOVALS["rank_rule"]` are the empty placeholder. AMENDED 2026-09-19 (R1-11): that is HISTORY ONLY. `pointer_contract.py` at HEAD `7d237b93` has `REMOVAL_RULES = ("flag_rule", "order_rule", "present_rule", "inexpressible")` with `REMOVALS` populated with those four classes — there is no `rank_rule`, which survives only in the historical `VERIFIED_KNOWN_REMOVALS = {"flag_rule": {"parts": 3}, "rank_rule": {"reach": 2}}` — and `VERIFIED_POPULATION = 18`. `RELATIONAL_POPULATION` at `INTERFACE_SPEC_POINTER.md:46` is therefore marked SUPERSEDED rather than `OPEN:`. **The present-tense sentences above are superseded; `pointer_contract.py` governs.**

**RECONCILED 2026-09-19 (R1-15) — the per-world spread is NOT in conflict.** The two sources agree exactly; the apparent disagreement was a **sorted-order misread**. `INTERFACE_SPEC_POINTER.md:46` lists the
RELATIONAL per-held-world figures as `world-98c6352d` 6, `world-28f61f2d` 5, `world-6e1fcbda` 6, `world-22704554` 5, `world-4090ec49` 7, summing to 29; the leaks run's own output gives
`{'world-22704554': 5, 'world-28f61f2d': 5, 'world-4090ec49': 7, 'world-6e1fcbda': 6, 'world-98c6352d': 6}` (`lk6_gate_population_out.txt:14`). **Those are the same five counts.** The leaks line is
`dict(sorted(Counter(...).items()))`, so it prints in world-id order; the spec's own cited source, `pipeline_review/r4_reach_lexical.py:58`, prints `dict(Counter(...))` **unsorted**, so it prints
in the order the worlds are first encountered in `eligible` — which is why the spec's list reads 98c6352d, 28f61f2d, 6e1fcbda, 22704554, 4090ec49 and not alphabetically. Read the spec's five
entries as world-to-count pairs rather than by position, and the two sources agree on every world. Re-derived from the frozen material for this amendment, by import
(`evaluate_gates.eligible_questions` in `records/typed_practice_001`, and `pointer_contract.relational_population`), the eligible RELATIONAL per-held-world mapping is exactly
`world-98c6352d` 6, `world-28f61f2d` 5, `world-6e1fcbda` 6, `world-22704554` 5, `world-4090ec49` 7, total **29** — identical to `lk6_gate_population_out.txt:14` and to
`pointer_contract.VERIFIED_RELATIONAL_BY_WORLD`, which pins the same five counts against the full 64-hex world ids. **The spec's per-world figures are therefore confirmed and MAY be quoted; they are not
undetermined, and no per-world claim is withheld.** `DESIGN_DRAFT_v0.2.md` §6.2's related `UNCERTAIN` is answered as well: they are RELATIONAL-only, and the separate ALL-KIND per-world counts over the same five worlds are 8 / 9 / 10 / 9 / 9, summing to 45. The removal list of §4.2 is applied per-question by `query_id`, so the gate population of 18 was never affected.

### 4.4 The ORACLE RULES ceiling — reported, NOT removed

This is the decision that settles the tension between the two review lenses, and it is stated in the leaks run's own
words (`lk6_gate_population_out.txt:35-39`):

> **ORACLE RULES (reported, NOT removed by default: applying the checker's own rule to the input IS the skill under
> test; these are the ceiling baselines the label must be compared against)**
> `parts` = children of the whole argument (one adjacency hop) → removes 5 eligible
> `edge_account` = the full adjacency of the focus world (one-hop copy) → removes 5 eligible
> `reach` = DIRECT iff part is a child, else ABSENT (one adjacency hop) → removes 1 eligible

So the one-hop adjacency rules are **reported, not removed**: `parts` **5/5**, `edge_account` **5/5** and `reach`
**1/9** of their eligible held questions (LK9). The reason is that applying the checker's own rule to the input
**is the skill under test**. A machine that learns to read a world's structure and answer about it has learned the
thing the study asks about, so the one-hop rule is the number to beat and the number to report beside the label —
not a reason to delete the questions. The leaks lens measured those one-hop rules as leaks and wanted the questions
out; this run keeps them **in** and makes the rule a **ceiling** instead (`REVIEW_SYNTHESIS.md` §10.1.1).

**The ceiling must be reported beside the label, every time.** A `LEARNS_NEW_WORLDS` label that is not printed
alongside its three oracle ceilings is not a reportable result.

### 4.5 What is reported beside the label

Reported, never gated:

- the three oracle one-hop ceilings of §4.4, on the same population the label uses;
- every mechanism-free baseline of §8, including the ones that measure zero;
- the all-kinds result as a flag (`G_LEARN`), never the label;
- the TEXT tier (`role_set`) and the DIRECT_READ tier (`definition`, `context`);
- `correspondence`, with its declared-false-negative status and its architectural reason;
- `analogy`, separately;
- the STRICT variant's arithmetic of §4.3;
- the development panel: 59 questions (53 `reach` + 6 `parts`) over ten-node worlds, all 53 `reach` questions using
  `first_direct_constituent_lexical_v1`, a rule the course NEVER teaches. Reported as "unpractised rule"; never
  gated on;
- the checkpoint check's probe results, with a status field; never a gate input;
- per-kind and per-world tables; record-level counts; every checkpoint's held counts; per-pass training loss;
- **per gained question, its record count and its admissible-answer count** (LK11: 15 of the 45 eligible questions
  are decided by a single record);
- the **held-back per-RECORD** accuracy as a second reported number, never a label (LEARNING_LEVERS.md §5). On the
  practice machine the held-back record figures moved 5 → 23, 7 → 21, 7 → 15 of 127 while the question gate moved
  +3, 0 and −1; the per-question gate stays exactly as strict as the owner confirmed, and the per-record figure is
  what shows whether the neurons moved.

### 4.6 The six VACUOUS permutation claims (LK13)

Six permutation claims cannot fail and must be listed as **VACUOUS** and printed next to the label, so no reader
mistakes a passing invariance test for evidence:

1. world-level relabelling invariance;
2. node-head equivariance;
3. "the assembled answer is unchanged when node refs are shuffled";
4. the checkpoint probe's accuracy as a transfer measure;
5. I3 as written in an earlier draft, which would compare the job to itself;
6. the `RELATIONAL_TRANSFER` flag as printed.

**VACUOUS, never evidence:** any control that relabels or shuffles a quantity the machine is meant to read
(hand-off §2; `PDF_ASSESSMENT.md:22`). Because the rank feature is excluded (§5.3), the machine reads no order-like
channel at all, so the vacuity law of design v0.1 **stands** and is not withdrawn (LK14).

**REQUIRED, engineering only, never evidence:** that a node influences the answer **only** through its declared
features — its raw flags, and nothing else — and never through its position in the packet, its position in the
file, or any part of its ref. Five permutation tests follow from the measured facts (LK15): E1 no-alias-channel,
E2 wiring, E3 symbol-row alignment, E4 rank, E5 answer-side precondition. E4 does not apply once rank is excluded.
They are added to the pre-launch test list and **none of them counts as evidence of learning**.

---

## 5. The training configuration

Three things are frozen here: how long the study trains, how a pass is composed, and how the recurrence and its
normalisation are set up. The owner's fifth decision is *"Stratify AND train longer (Recommended)"* (§0.2 item 5),
and both halves have measured numbers behind them.

### 5.1 The schedule is stratified — every kind in every update

As-is, at 147 updates per pass, each kind is **ABSENT** from a large share of updates (`REVIEW_SYNTHESIS.md` §4.7,
measured by `lb11_economics.py`):

| kind | updates where ABSENT (of 147) | present |
|---|---|---|
| `role_set` | **115** | 32 |
| `analogy` | **112** | 35 |
| `context` | **107** | 40 |
| `definition` | **105** | 42 |
| `edge_account` | **95** | 52 |
| `correspondence` | **67** | 80 |
| `parts` | **63** | 84 |
| `reach` | **40** | 107 |

So a `role_set` head receives a gradient in **32 of 147** updates and an `analogy` head in **35**. That is the
mechanism behind the learnability lens's "the rarest head sees 320 of 1,470" (LB11).

| branch | updates/pass | presentations/pass | every kind every update? | vs as-is |
|---|---|---|---|---|
| **A as-is** | 147 | 818 | no | — |
| **B stratified — ADOPTED** | **147** | **1176** | **yes** | **+43.8 %** |
| C widened (the lens's literal reading) | 470 | 3760 | yes | +359.7 % |

**B is the adopted branch.** It fixes coverage completely for a **+43.8 %** presentation increase at the SAME
update count. C multiplies presentations by 4.6× and its ten passes would need **4,716** updates, which is above
the raised ceiling of **3544**, so C is refused as stated. The extra presentations cost instance time only; the
update count, and therefore the learned parameter trajectory's length, is unchanged at 147 per pass.

- `STRATIFIED = True` is a module constant (`pointer_contract.py:135`) and `pointer_schedule` defaults to it.
- The stratified whole-schedule `batches_digest` is
  **`1c67edd74bf670a1b2b17af63209bc33bc2a92bc3a796e2d66f285d10c7b5304`** (`pointer_contract.py:153`).
- The unstratified `batches_digest` remains
  **`daf95831dd6f054f0395e9a868c513650982bd1912247adc698ca067433bc857`** and stays available as
  `stratified=False` for fidelity checks (`pointer_contract.py:255-261`); with `passes == 10` it reproduces the
  practice study's own schedule byte for byte, at `updates_per_pass` 147 and `presentations_per_pass` 818.
- A different pass count gives a different whole-schedule digest, because the pass number is inside every
  occurrence and presentation id. That is expected and is recorded here. The **single-pass** digest
  `80ae7121ff75f687e9c6c88593e2ed7d3f6024173d3577243ed05049c8859056` is pass-count independent and is what the
  contract re-checks on every call (`pointer_contract.py:154`).
- `practice_schedule` itself is still imported unchanged. The practice schedule is untouched.

### 5.2 The `^6` initialisation and the normalisation placement

These two were measured by the learnability lens, and the measurement decided both (LB9, LB13;
`REVIEW_SYNTHESIS.md` §5.6).

**RMS normalisation is placed at the INPUTS of each round, not after the update.** Spectral norm of
`d(Σ final node states) / d(initial node states)` after 8 shared rounds:

| placement | 3 nodes | 4 nodes | 10 nodes |
|---|---|---|---|
| after the update | 18.59 → **135.1** | 21.93 → **127.0** | 22.04 → **140.2** |
| **before the update (inputs) — ADOPTED** | 2.202 → **8.240** | 4.463 → **13.84** | 4.980 → **14.83** |
| none | 2.217 → 6.790 | 4.492 → 10.63 | 4.965 → 11.19 |

The after-update placement drives the 8-round Jacobian to **127–140**, which is an exploding gradient. The input
placement gives **8.2–14.8**. The input placement is pinned.

**The `^6` initialisation is pinned to the torch-default scheme**, the one the lens measured as moderate:
**7.65–13.42 %** of pre-activations with `|z| > 2`, against **48.02–91.83 %** with the output norm and
**75.30–98.03 %** with He-normal and no norm. Leaving it unspecified is a silent false-negative generator: with
He-normal the block is effectively constant and its gradient near zero, and nothing in the run would say why.

**The worker must assert the measured pass-0 saturation fraction.** The assertion is on the combination actually
built, not on an inherited number.

`UNCERTAIN:` the saturation fraction for **torch-default with the INPUT placement** is not among the figures the
lens printed — it printed torch-default with the *output* placement (7.65–13.42 %). The worker's pass-0 assertion
must therefore measure the combination actually built rather than assume that number carries over
(`REVIEW_SYNTHESIS.md` §5.6, decisions item 4). This protocol does not guess the value.

**`K` is pinned at 8 and the learner is forbidden to condition on `depth`.** Training batches used depths 1 / 2 / 4
/ 8 (for 380 / 370 / 340 / 380 of the 1,470 updates) while **every** evaluation uses depth 8
(`INTERFACE_SPEC_PIPELINE.md:248`). A learner that read the batch's `depth` field could gain from p0 to p10 by
extrapolating depth rather than by learning, and that gain would be indistinguishable in the label. LK18 states the
instruction plainly. So `K = 8` is a fixed constant of the pointer learner, `depth` is recorded only as a schedule
coordinate and is never an input to any head, and both facts are pinned in the learner profile. `loss_plan` checks
only `depth ∈ (1,2,4,8)`, so this is a study decision rather than a schema constraint.

**`K = 8` is recorded as an unconverged phase, not as a compute knob.** The per-round update magnitude for a
4-node world at torch-default with output normalisation runs 0.279, 0.288, 0.309, 0.325, 0.333, 0.338, 0.341,
**0.343** — still growing toward its fixed point. The states have not settled after 8 rounds, so a depth ablation
over K = 1, 2, 4, 8 selects **different functions**, not merely more compute. That is registered as a property of
the study (`REVIEW_SYNTHESIS.md` §5.6 decision 3).

**RMS-normalising every round is also the DG7 fix.** Without it, a residual recurrence feeding dot-product
pointers can push `|score|` past `1e6` (`slots.py:248`) or break the 2e-5 tensor/Python loss agreement
(`learner.py:261`). Smoke S8 proves it.

### 5.3 What the input carries, and what it never carries

Read from the public packet ONLY:

- **the worlds**: the focus world read as a graph, the correspondence target world, and every world a world-choice
  slot lists. Each world is a set of nodes plus directed `contains` edges.
- **per node, its own raw flags only**: `is_declared_whole`; `is_participant` with rank 1..3; `is_whole_argument`;
  `is_part_argument`. **`is_primary_label` and its rank are REMOVED**, because `primary_labels == participants` in
  **64 of 64** worlds (LK5), and the flag kept is the one the checker's own `context` answer is derived from.
- **per world**: its domain-text token ids, plus the flags `is_focus` and `is_target`.
- **the query**: `kind` as an 8-way learned id; `rule` as a learned id (DG2: swapping the reach rule changes 11
  answers); the argument node ids where present.
- **for `role_set` only**: the focal excerpt as a frozen bag of token ids, position-free.

**The node rank feature is EXCLUDED.** This is the final decision, recorded in `REVIEW_SYNTHESIS.md` §10.2. The
leaks lens measured the rule *"node rank == the alphabetically last ref"* — reading **only** the rank flag and **no
adjacency** — as solving **5 of the 45** eligible held questions by itself (`parts` 1 of 5 and `reach` 4 of 9), the
largest single-flag score of any kind outside the DIRECT_READ pair (LK7). The learnability lens reached the same
fork from the hidden-ref-order side: rule-1 `reach` depends on the hidden alphabetical order of node references
for **5 held, 11 trained and 2 excluded** reach records (LB1). Adopting rank would have taken the population from
**23 to 18** and raised the required improvement share from **7/23 = 0.3043** to **7/18 = 0.3889**, and it would
have **withdrawn this document's own vacuity paragraph**, because rank *is* the node alias: at **244 of 244** refs
every node ref's position in the sorted list equals its own stored index. So the feature is out, the order-dependent
questions are removed instead (§4.2), and the rank-last pointing rule stays registered as a no-learning baseline
so the removal list is reproducible.

**Node LABEL words are DROPPED from the input.** Four independent measurements agree:

1. no answer rule can use them: `checker.py:97` says so in terms — *"node labels, root choice and archetypes do not
   vote"* — and that is the only mention of a label anywhere in the checker;
2. they are a memorisation channel for held worlds: all **20 of 20** held-world node labels occur somewhere in
   trained record text — 7,160 (label, trained record) occurrences — and the reader would embed a held-world label
   **30,420** times across the schedule (LB10);
3. they carry no signal for the kinds that matter: the paired worlds of a `correspondence` question share **no**
   node label (0 of 20 held, 0 of 54 trained, 0 of 14 excluded), and **123 of 123** correct `analogy` candidates
   have zero label overlap with the focus world (LB14);
4. cost is not the argument, but it agrees: uncached, the full run needs 284,900 label encodes at a measured
   0.0219 s per call = **6,225 s** of a 12,300 s deadline; a 230-entry cache costs 5.0 s.

**What is NEVER read**: `supports`, `cue`, `instruction`, and any answer or target. **No order-like channel is read
at all** — not the registered node rank, not a node's position in the packet, not its position in the file, not any
part of its ref. Test S9 is the engineering check for exactly that, and it is never evidence of learning.

**The directed `contains` adjacency is given ONLY to message passing.** It never reaches a readout head. This is
what makes the answer depend on relations among input elements rather than on one copied flag.

**The reader is pure, deterministic and digestible**: `label_cache(root)`, `read_packet(packet)`,
`input_digest(reading)`, `slot_readings(reading, slots)`. The label cache is built ONCE — 230 distinct labels, 244
nodes — and its digest is pinned (RK3).

### 5.4 The network, in brief

The full API surface is fixed in `pre_design/INTERFACE_SPEC_POINTER.md` §§1-6 and is not restated here. Fixed
facts:

- `PointerCourseLearner`, a NEW class. `self.module` is ONE container holding every learned weight, the registered
  `^6` block included. `scope_parameters` is NEVER called on it, because `graph_teaching/trainer.py:86-87` would
  freeze every non-`^6` weight. The class owns its own `__init__`, `predict`, `stage_batch`, `train_sealed_batch`,
  `export_checkpoint`, `restore_checkpoint` and `profile`. It borrows `TypedCourseLearner._tensor_loss` by CALLING
  it, so the joint correspondence loss is unchanged.
- The `^6` block comes from `cncm.typed_matched_worker._framework(torch, device, seed)`, built FIRST, on the same
  model seed. The registered contract id is `cas.cjt.operation.^6.decompose/0.2`.
- The update rule is `h ← h + ^6(W_self h + W_down Σ parents + W_up Σ children)`, with `^6` the registered
  `_DecomposeTransform` used unchanged as the update function.
- Dense adjacency matrix multiplies and one-hot matrix multiplies instead of embedding lookups, under
  `torch.use_deterministic_algorithms(True)`. The probes use a closed-form ridge solve. This is the RK7 resolution;
  smoke S1 proves it.
- Gradient discipline: `train_sealed_batch` requires finiteness only on parameters where `p.grad is not None`,
  requires at least one non-None gradient overall, records that AdamW with `zero_grad(set_to_none=True)` applies
  neither an update nor a weight-decay term to a `None`-gradient parameter, and logs per update which parameters
  received gradients (RK1).
- Output: the same `{slot_id: {symbol: logit}}` shape the old learner produced, one logit for EVERY declared symbol
  in `slot["symbols"]` order, and exactly `loss_plan.validate_prediction`'s 12-field set (DG6).

The head set itself is `OPEN:` in `INTERFACE_SPEC_POINTER.md:110-115` and is fixed by whichever builder lands
first against the lens's expressivity table; the per-head changes the lens requires are LB6, LB7, LB12, LB16 and
LB17. **The head set is not a gate parameter and not a claim parameter**: whatever it is, the gate of §4 and the
label rule are unchanged.

### 5.5 The CAS reading, and its claim state

The world encoder is `^6` Male — "An Idea impregnated with another Idea, the Ideas an Idea is composed of" —
applied along the `contains` composition graph, with decomposition carried by the registered `^6` operation. **No
new CAS primitive is claimed.** The block itself is byte-identical to the practice study's registered block; only
what surrounds it is new. The CAS reading is an interpretation of the architecture, **not a measured property**,
and no independent CAS-semantics review of the container has been done.

---

## 6. The pass count — the one value left open

**`PASSES` is the only value this protocol leaves open at drafting time.** It is set from the AWS smoke job's
**measured per-update cost**, never guessed, and it is filled in **before the freeze of the study admission and
before the first paid launch** — that is, between the smoke job's result landing and
`prepare_study.py` writing `admission_001/study.json`.

**The rule.** Set `PASSES` from the smoke's measured seconds per update and per evaluation, so that the projected
full job fits the worker deadline with margin, subject to:

- `MAX_PASSES_PERMITTED = 24` (`pointer_contract.py:112`);
- `LEARNER_MAX_UPDATES_CEILING = MAX_PASSES_PERMITTED * 147 + 16 = 3544` (`pointer_contract.py:113`), which permits
  24 passes and refuses 25. The contract enforces it as `main_updates + INTERFERENCE_UPDATES <= ceiling` and fails
  closed with `POINTER_UPDATE_BOUND` otherwise (`pointer_contract.py:316-318`).
- `pointer_schedule` itself refuses a pass count outside `1 <= count <= MAX_PASSES_PERMITTED` with
  `POINTER_PASSES_BOUND` (`pointer_contract.py:274-275`).

**The same measurement must re-check `MAX_CORE_CALLS`.** `MAX_CORE_CALLS` is currently inherited unchanged from
the practice contract (`pointer_contract.py:114`). The pointer machine calls the registered `^6` block once per
node per round — about 4 nodes × 8 rounds = 32 calls per world read — against the old machine's 8, so the core-call
budget may bind before the update budget does. Both are recorded in `DESIGN` and must be reconciled before the
study is frozen.

**Why the pass count exists at all, with the evidence.** The practice run's mean raw batch loss fell monotonically
at every one of its ten passes, from **1.2879780873** at pass 1 to **0.3981766156** at pass 10, and last-batch loss
fell from 0.3141852419 to 0.0720160812 over the same period. It used **5,465.811116 s of a 12,300 s deadline —
44.4 % of its budget — and stopped anyway** (`LEARNING_LEVERS.md` §1, read from
`records/typed_practice_001/receipt_<seed>/checkpoints/worker_report.json`, seed 20260917). Ten passes was a
protocol choice, not convergence. The registered practice ceiling `LEARNER_MAX_UPDATES_CEILING = 2048`
(`practice_contract.py:61`), enforced as `main_updates + 16 <= 2048`, capped any study at **13 passes**
(1,911 + 16 = 1,927); 14 passes would need 2,074 and would be refused (`LEARNING_LEVERS.md` §2). This study is a new
candidate and carries its own registered limit of 24.

**The current inherited value is not a freeze.** `pointer_contract.py:90` still reads
`PASSES = practice.PASSES  # 10, INHERITED AND NOT FREEZABLE AS-IS`, and `pointer_schedule` documents
`OPEN:` on the value itself (`:269`). This protocol records the same open item.

**What the projection looks like today, and it is a projection, not a reading.** At the old machine's measured rate
of about **0.6682 s per presentation**, the stratified schedule's extra **358** presentations per pass cost roughly
**+2,392 s** over ten passes, which fits the 12,300 s deadline against the practice run's **5,465.811116 s** — but
the pointer machine's own rate is **unmeasured**, and the smoke job measures it. Per DG9: if a job projects above
about **11,000 s**, the owner must approve a larger reservation first (§11).

**Two constraints that are not free.** First, the pass count cannot be raised to buy power at the gate: the gate's
power is a property of the test and the population, not of the training length (§1.3). Raised training length is
the cheapest available improvement to the neurons; it is not a substitute for a gate that can see a gain. Second,
this is the only place in this protocol where a claim-bearing number is written after the protocol is frozen, and
it is written before any claim-bearing job launches.

---

## 7. Integrity — I0 to I4, adapted for this machine

Read by `records/typed_pointer_001/evaluate_gates.py`, **not by prose**. Any failure makes the study `VOID`.

**Unit: a question** (`query_id`), correct at a checkpoint only if **every** one of its records is correct.

| gate | condition |
|---|---|
| **I0** | the study has exactly the three seeds: 20260917, 20260918, 20260919 |
| **I1** | every job `completed_deliverable`, cleanup complete, worker status equals **the new worker's own `SUCCESS_STATUS`**, every name in the new worker's `EXPECTED_ARTIFACTS` present, every scoring file readable, **and the job is claim-bearing** (see below) |
| **I2** | held and excluded ids equal the frozen split (§2.1 digests); every record in every main and interference batch log is a **trained** record; the logged main and interference update counts match the frozen schedule exactly |
| **I3** | the in-job DG4 evidence of §7.1 — the `^6` sub-block identity against the practice start, the independent second build, the three pairwise-different seeds, and the identical start with and without the checkpoint check — all as the job recorded them |
| **I4** | per job the frozen main, interference and replay update counts, and reloads and replays exact |

**I1 carries a condition this table did not originally list, added and acknowledged 2026-09-19.**
`records/typed_pointer_001/evaluate_gates.py` voids a receipt whose job was **not claim-bearing** — the code
`I1:<seed>:REDUCED_SCHEDULE:<mode>` with the reason *"the job did not run the REGISTERED plan, so it is not a
claim-bearing run and may not print a label."* The worker can run a shrunken schedule through the environment
request `CNCM_POINTER_REDUCED_SCHEDULE` (`cncm/typed_pointer_worker.py:142`, `:268-299`), which sets
`claim_bearing = False` and records `mode: "REDUCED"` in `schedule_plan.json`, **without changing a single
registered constant** — that is its entire purpose and it is what makes the smoke job possible at all.

**This is a strengthening of the I-list, not a divergence from it, and it is the coordinator's decision.**
Rationale: a reduced run delivers normally and reports the worker's `SUCCESS_STATUS`, so without this condition a
smoke job could satisfy every original I1 requirement and print `LEARNS_NEW_WORLDS` — a learning claim from a run
that was never registered to make one. Refusing it can only ever **withhold** a label, never manufacture one, so it
cannot create a false claim; and it can never void a legitimate claim-bearing job, because such a job sets no
reduced request and therefore returns `claim_bearing = True`. The condition is accepted.

**I1 and I3 are new, and the practice reader cannot be reused (RK8).** The practice I1 imports
`cncm.typed_practice_worker` (`evaluate_gates.py:162-165`) and the practice I3 compares the start weights against
the matched study's `initial_checkpoint` (`:182-189`), which the pointer container can never match, so any failure
would collapse into `VOID`. The pointer reader is a new file at `records/typed_pointer_001/evaluate_gates.py`,
outside `cncm/` and `cas_meta2/`.

### 7.1 I3 — the in-job DG4 checks, and their corrected form

DG4 as first worded cannot pass, and the correction is load-bearing. `model_state_identity` digests the **whole**
`module.state_dict()` (`learner.py:111`, `:306`), and the pointer container holds far more than three tensors, so a
pointer run's whole-module identity can never equal the practice value even when the `^6` weights are identical
(V3). The corrected form is the four recorded checks:

1. build `matched._framework(torch, device, seed)` **FIRST** and digest **the three `^6` tensors alone** —
   `state_identity(torch, {"left.weight": ..., "right.weight": ..., "merge.weight": ...})` — and compare that
   against the practice start's recorded value for the same seed;
2. build the whole model a second time, independently, and require equal identity;
3. require the three seeds' identities pairwise different;
4. require the start identical with and without the checkpoint check.

`measurements.json` must record **which of the two identity forms was used** — whole-module or three-tensor. They
are not the same number, and nothing fails loudly at the point of the mistake.

**The three practice-start targets are the pin file's values, and the two recorded versions do not agree.**
`INTERFACE_SPEC_SHARED.md:678-681` gives seed 20260917 as
`82d2037ca88593233f1176913b91f54d419ebacd23f5abc4e12bd71795feb794`, seed 20260918 as
`bc906a0bdd9f0b31e58653bd47ff70dfa2e40b0fbc35f36cc693c97ac3f0d753` and seed 20260919 as
`d437bbeb1b13a4fd31f1a158d17485821ba52da4a29f1de7b00d8ccd583598f0`. `pre_design/contract_pins/checkpoint_pins.json:81`
records seed 20260918's `initial.pt` identity as
`35081019e8b56f0c0c14aa8168262c23dab4c662c385ddcf26edc794a179b706` and `:84` records seed 20260919's as
`91279389cfc22df46415dd56a26b1285fb3ef1ecd59e3aaccef553564528c12e`.

`RESOLVED BY EVIDENCE, 2026-09-19, without running a model:` the probe's own output artifact
(`pre_design/measurements/framework_probe/probe_out.txt`) records `recorded_model_state_identity` as
`82d2037ca88593233f1176913b91f54d419ebacd23f5abc4e12bd71795feb794` for seed 20260917 (line 48),
`35081019e8b56f0c0c14aa8168262c23dab4c662c385ddcf26edc794a179b706` for seed 20260918 (line 99) and
`91279389cfc22df46415dd56a26b1285fb3ef1ecd59e3aaccef553564528c12e` for seed 20260919 (line 150), and
`FINDINGS.md:25-28` independently ties `91279389…12e` to seed 20260919. Read straight from each
`receipt_<seed>/checkpoints/initial_checkpoint.json`, the real on-disk values are the same three
(`metadata.model_state_identity`). So the pin file and the probe artifact agree with each other and with the
checkpoints, and the two seed-20260918/20260919 strings in `INTERFACE_SPEC_SHARED.md:679-680` appear to be an error
in that document.

`CONFLICT:` `INTERFACE_SPEC_SHARED.md:678-681` and `pre_design/contract_pins/checkpoint_pins.json:81`, `:84` state
different `model_state_identity` values for seeds 20260918 and 20260919, and both files are in the repository at
HEAD `026e6473`. **The in-job check must use the pin-file values**, which agree with the on-disk checkpoints and
with the probe's own output artifact. This resolution is a reading of artifacts on disk, not a measurement; a later
agent should still confirm it inside the job, where the check is comparative and will fail loudly if the value is
wrong.

### 7.2 The checkpoint check, in its two phases, and their ordering

The checkpoint check is the part of this study the owner approved as "option 1 ... plus the checkpoint check". It
runs inside each job, on the same machine, and its results are **reported only, never a gate input**. Its artifact
is always written with a `status` field of `COMPLETE` or `FAILED` inside it, and every module it needs is imported
at start-up, outside any `try` (RK6: a missing artifact or a poisoned `attestor.snapshot()` turns a reported check
into a failed job after the money is spent).

- **The $0 half is DONE** and is not recomputed on the GPU. It is the recorded pre-block result of
  `pre_design/INPUT_DEFECT_MEASUREMENT.md` plus its independent reproduction, because the encoder is frozen and
  `binding.py` rows and permutations are SHA-256 based, so the pre-block vectors are identical at every checkpoint
  (V2).
- **Phase A runs FIRST.** Restore that seed's practice checkpoints `initial`, `pass_01`, `final` with
  `PracticeCourseLearner.restore_checkpoint`; for every slot of all 564 records compute the post-block vector by
  copying the forward internals; verify by rebuilding logits bit-for-bit against `restored.predict` (M4); seal the
  vectors create-only. **Phase A reads PUBLIC vectors only and derives NO answer.** It must finish BEFORE the
  pointer model is seeded or built, because restoring overwrites all three global RNG streams
  (`learner.py:358-362`, M3).
- **Phase B runs LAST.** After all pointer evaluations, reloads and replays: derive answers and fit the
  trained-world → held-world ridge probe per kind, on the post-block vectors at each checkpoint, and on the pointer
  machine's node states at `initial` / `pass_01` / `final`. Deriving answers earlier would breach the registered
  custody rule (`practice_contract.py:11-12`; `typed_course_worker.py:149`, FP3).

**Cost, told to the owner and accepted.** About 9–15 minutes per job, about **$0.38–$0.63 per job** at $2.52/hour
(M2), from 173.8 s warm and 300.5 s cold per 564-packet evaluation. Only `initial`, `pass_01` and `final` are
shipped; `prelast` and `retained` stay unshipped so the check costs what the owner was told.

**The `^6` identity check digests the three `^6` tensors only**, because `model_state_identity` digests the whole
`module.state_dict()`. And **it is an in-job check on AWS only**: a local build reproduces the practice weights to
within **7.450580596923828e-09** but not byte-exactly, because `state_identity` is a byte-exact SHA-256 over tensor
bytes and a difference at that scale makes two identities differ even though the weights are numerically equal
(`measurements/framework_probe/FINDINGS.md:19-35`). On the AWS instance the build IS bit-exact: the practice
study's own integrity check I0–I4 PASSED in all three seeds (`FINDINGS.md:37-41`). **Consequence, stated so no
builder adds the wrong local test:** do not add a local test that asserts the fresh `^6` identity equals the
practice study's recorded start. It will fail for the wrong reason and send a builder looking for a seed bug. A
local $0 smoke may still assert the reproducible parts: building `_framework` twice with the same seed gives
identical weights, and the three seeds' builds are pairwise different (`FINDINGS.md:53-55`).

---

## 8. Mechanism-free baselines, registered

Registered before the run. A win is uninterpretable until it beats the cheapest method that does not have the
mechanism (hand-off §2). Every one of these is **printed beside the label**; none of them is a gate.

| baseline | what it is | measured score |
|---|---|---|
| **the untrained machine** | the model at pass 0, before any training | its own pass-0 reading, reported |
| **the registered input-blind shortcut** | for each kind, the most common trained answer written in the learner's own output symbols — worlds as their global `W` aliases, nodes as their per-world `N` aliases — ties by text. It is the best single answer the machine could give while ignoring the input. | removes **0** eligible questions (`lk6_gate_population_out.txt:17`, `:61`); the fitted majority symbol scores **0 of 45** held-eligible and **0 of 9** on `reach` (`REVIEW_SYNTHESIS.md` §6.4) |
| **the flag-rule baselines** | FP2 `parts(declared_whole) = participants − declared_whole`; the `reach` flag rule; the edge flag rule; the all-flags rule R13 | FP2 removes **3** (`parts`), the `reach` flag rule **0**, the edge flag rule **0** (`:20-22`); R13 alone scores **13 of 45** (LK8) |
| **the rank-only baseline** | point at the alphabetically last node in every node slot, reading **only** the rank and no adjacency | removes **5** if rank is an input (`parts` 1, `reach` 4) (`:30`, `:67`). **Registered anyway**, even though rank is not an input, so the removal list of §4.2 stays reproducible |
| **the oracle one-hop ceilings** | apply the checker's own rule to the input: `parts` = children of the whole argument; `edge_account` = the full adjacency of the focus world; `reach` = DIRECT iff part is a child, else ABSENT | **5/5**, **5/5**, **1/9** of their eligible held questions (`:37-39`) |
| **the majority-symbol baseline fitted on trained records** | the most common trained answer per kind, fitted on **trained** records only | **0 of 45** held-eligible, **0 of 9** on `reach` (`REVIEW_SYNTHESIS.md` §6.4). The custody rule forbids fitting it on held answers |
| **the remaining zero-learning pointing policies** | argument node; part argument; focus world plus declared whole; PRESENT for every non-argument node; PRESENT for every node and every edge pair; rank 0 | **5/45**, **0/45**, **5/45**, **1/45**, **1/45**, **0** (`lk3_pointer_policies_out.txt`; `lk6_gate_population_out.txt:29-33`) |
| **the equal-logits policy** | a machine that emits tied logits everywhere | already answers **1/45** (LK10). Any question it answers is reported separately from the gains |

**`CONFLICT:`** — none of these baselines may be fitted on held answers. `REVIEW_SYNTHESIS.md` §6.4 records that an
earlier reading of this protocol's own evidence fitted a majority-symbol baseline on held records, found a skew,
and was **withdrawn as an error**: the skew can only be reached by reading the held answers, so it is the answer
key, not a baseline. Every number in the table above is a **trained-only** fit or a **public-input-only** rule.

---

## 9. Claim status, and the vocabulary

### 9.1 The vocabulary

Claim-status words in force are the project's own, from the legend of
`<worktree root>/docs/CAS_HARNESS_SPEC_SHEET.md`: **REAL**, **VALIDATED**, **LICENSED**, **NOT LICENSED**,
**GREY**, **VACUOUS**, **WITHDRAWN**, **ENGINEERED-NOT-VALIDATED**, **FLAG_FOR_HUMAN_REVIEW**. In addition, and as
the measurement documents use them: **OPEN**, **MEASURED**, **INFERRED**. No new status word is coined here.

Two of them are used in this document in the sense the project fixes for them, and both matter here:

- **`VACUOUS`** — the test could not be read, because a precondition failed. **The label was never tested, rather
  than tested and rejected.** It is not a `FAIL` and must never be averaged into a pass rate. §4.6's six
  permutation claims are `VACUOUS`.
- **`ENGINEERED-NOT-VALIDATED`** — the machinery is built and the design is sound, but no result has come out of
  it. Capacity, not evidence. This is where the pointer machine stands today.

### 9.2 The rule that nothing in prose may upgrade the status

**The gate program's printed label IS the claim status.** Nothing in any prose document, result write-up, commit
message, README or report may upgrade it, soften it, or restate it as a partial success. A failed hard gate is a
**FAILURE**, never "PASS with caveats." A `GREY` is not a soft yes. A `VACUOUS` test is not a `FAIL` and not a
pass. Negative results are kept, not deleted.

The claim status must therefore come from a deterministic program reading — raw result, frozen threshold,
registered controls, hard-gate results (`INTERFACE_SPEC_POINTER.md:166`, `INTERFACE_SPEC_PIPELINE.md:1411-1418`).

**Current claim state, unchanged by this document.** Nothing has been run, so there is no new claim:

- `REAL` (negative): the old machine does not transfer to never-practised worlds (commit `8cdbad81`).
- `REAL` (negative, measured for $0): the old machine's input makes such transfer impossible **for the four
  per-bit kinds probed** — `parts`, `context`, `role_set`, `edge_account`. "Impossible for ANY learner, all kinds"
  is **INFERRED, not measured**.
- `OPEN`: whether a pointer machine's neurons learn a skill that transfers. Nothing built end to end, nothing run.
- `NOT LICENSED`: any claim about the pointer machine, CASformer attention, or the architecture family.

---

## 10. Limits this protocol does not remove

- **Five worlds, same size, same bank.** Held worlds have the sizes and question kinds of trained ones and no exact
  twin, but they share partial structure with trained worlds. A layout-level habit learned on one world can be
  right on another. That is a kind of generalisation, and it is not "reading a new world from scratch."
- **Held worlds are not unseen.** Held worlds pass through the trainable world encoder as **wrong** world-choice
  candidates in **1,340 of 8,180** training presentations (definition 460, context 470, analogy 410, DG5). The
  honest wording, which this protocol adopts, is **"never the focus of a trained question"**, never "never seen."
- **Questions about one world move together.** The gate requires gains in two worlds and two kinds, but it does not
  model world-level clustering; a world-resampled check is a later analysis. The three seeds are replications, not
  independent samples of questions.
- **The gate's power is limited, and this is a design fact, not a caveat.** See §1.3.
- **`correspondence` is unreachable by this head.** It is reported as a declared false negative, not as evidence
  about the machine (§3).
- **The gate uses the question as its unit, and a question is correct only when all its records are.** 15 of the 45
  eligible questions are decided by a single record (LK11), so the per-question reading is coarse by construction.
  The per-record figure is reported beside it (§4.5) but is never the label.
- **Whether the neurons keep what the encoder gives them** (the 96.3758 % linear-availability question) is not
  measured here.
- Anything about the other teaching order, other learning rates, or architecture changes.
- **The `correspondence` head's inexpressibility is a finding about this head design on this corpus**, not about
  whether a joint edge-aware scorer could do better. It was never built.

---

## 11. Freeze, dry-run and launch

Summarised from `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md` §9, in order. Every step is explicit; none is
optional.

1. **Write the nine files of §11.1 and the tests; `pytest` green.** The pure baseline that must not regress is
   **89 passed in 328.56 s** at HEAD `52fea7ed` (`INTERFACE_SPEC_POINTER.md:24-26`).
2. **Adversarial pre-flight review of the BUILT code, TWICE: fix, then review again.** Record both as
   `records/typed_pointer_001/PREFLIGHT_REVIEW.md` with findings files. This is required because the practice
   study's second review found three leaks that the first redesign created.
3. **Stand-in dry run** (`preflight_dry_run.py`): real everything except the learner; create-only publisher
   simulation; write-audit hook. It must print `PREFLIGHT_PASS` for all three seeds. The pointer version needs its
   own `staging` directory name and its own `expected` integrity-failure list, because the pointer reader's I3 is
   redefined.
4. **GPU smoke per §11.3.** The whole list runs in the single approved AWS smoke job. As recorded at HEAD `026e6473`,
   S1, S2, S7, S8 and S9 could run locally and S5 could not assert the `^6` identity there; the amended venue rule
   of §11.3 removes the laptop from the smoke path entirely. **S10 needs the short AWS smoke job the owner approved**
   (§0.2 item 2).
5. **Commit everything and push.** The package is built from git HEAD blobs, so any uncommitted `.py` fails
   `INPUT_NOT_COMMITTED`. Never commit a CRLF `.py`; the repo is `eol=lf`.
6. **`python records/typed_pointer_001/prepare_study.py`** → `admission_001/{study.json, 2026091X/{request,
   authority,owner}.json, rehearsal}`. That freeze is committed and pushed **BEFORE the first launch**.
   `study.json` carries this document's `protocol_sha256`. **This is the step where the open §6 value is filled in.**
7. **Launch sequentially, in the background, logging to a file:**
   `python records/typed_pointer_001/execute_study.py --execute records/typed_pointer_001/admission_001/study.json <sha256>`.
   It stops on the first failure with an explicit `stop_unless`, never `assert` (`python -O` strips asserts from a
   spend path). One job at a time, because the us-west-2 GPU quota is 8 vCPU. **Change NO `.py` under `cncm/` or
   `cas_meta2/` until all three jobs have launched**, because each re-validates the inventory (RK9).
8. **The gate program's printed label IS the claim status.** Write `records/typed_pointer_001/POINTER_STUDY_RESULT.md`,
   update `records/MACHINE_STATE_001/STATUS.md`, `CHANGELOG.md` and the spec-sheet row with artifact paths, **in the
   same commit**. Back up receipts to `D:\tksCAS-archive\cncm_typed_pointer_001_<date>` with sha256 checks. Commit,
   push, and report to the owner in plain English.

**On a failed job: read the console output before re-spending** (free `get_console_output`), never guess and
relaunch. The study has `automatic_retries: 0` and stops on the first failure.

**The owner's signed per-job records.** The machine changed, so there are three new owner-signed per-job records
(DG9). Each job gets its own `owner.json`, carrying the owner's words verbatim from §0.2 — all five decisions — and
`validate_owner` checks both the CANDIDATE and the job. Owner approval must be an executable signed record, not
prose.

### 11.1 AWS facts

| fact | value | source |
|---|---|---|
| account | **807562639912** | hand-off §9 |
| region | **us-west-2** | hand-off §9 |
| instance | **g7.2xlarge**, RTX PRO 4500 | hand-off §9 |
| observed rate | **$2.52 / hour** | hand-off §9 |
| bucket | `job + "-807562639912"` | hand-off §9; `pointer_contract.py:85` |
| study token | **`tpntr`** — giving a bucket of **exactly 63** characters, the maximum the pattern allows | `pointer_contract.py:81-84`; `INTERFACE_SPEC_POINTER.md:41` |
| reservation | **$15.00** per job, **$45.00** total cap | `pointer_contract.py:117`; hand-off §12 |
| practice instance time | 6,064 / 6,082 / 6,025 s, about **$12.72** total | hand-off §9 |
| credentials | local (`~/.aws/`), **never printed or copied** | hand-off §2, §9 |
| ledger | the canonical ledger at the `meta1` worktree path; **never hand-edited** | `AWS_SMOKE_S10_PLAN.md` §6 |

**Two traps recorded by the pipeline spec, both of which fail a launch before the reservation is made:**

- the reservation **caller** passes the candidate module's amount while the study records `"15.00"`; changing one
  without the other fails every launch at `PRACTICE_RESERVATION_CALLER`;
- the new worker's FAILED status must be added to `failure_statuses`, or a failed job is read as `REMOTE_FINISHED`
  and collection then demands an artifact manifest a failed worker cannot have produced.

Test P2 pins the 63-character bucket for all three seeds. Test P6 pins the launcher overrides.

### 11.2 The nine files

| # | file (under CNCM) | what it contains |
|---|---|---|
| 1 | `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_contract.py` | Pure. Imports the practice split and schedule unchanged. New `CANDIDATE`, `CONFIG_SCHEMA`, `JOB_PATTERN` with the `tpntr` token, `CHECKPOINT_PINS`, `MATERIAL`, an `input_inventory` wrapper, a new `DESIGN`, the tier lists, the frozen baselines and the gate population, the new `expected_main_delta` formula, `parse_job` / `make_config` / `validate_config`. |
| 2 | `.../typed_teaching/pointer_inputs.py` | Pure, deterministic public reader with a digest. Per-world node flags, directed adjacency, domain-word ids, query kind/rule/argument marks, and the `role_set` excerpt word ids. Never reads supports, cue, instruction, node labels, or any order-like channel. `label_cache` built once with a pinned digest. |
| 3 | `.../typed_teaching/pointer_learner.py` | Torch only when called. `PointerCourseLearner` per §5.4: one container `module` holding every learned weight including the `^6` block from `matched._framework` built FIRST; dense-matmul message passing with K = 8 shared rounds and RMS normalisation at the inputs; the pointer heads; outputs exactly `loss_plan.validate_prediction`'s field set. |
| 4 | `cncm/typed_pointer_worker.py` | Adapted from `typed_practice_worker.py`, reusing `_publish`, `_publish_bytes`, `_move_in`, `_append`, `_seal_predictions`, `_train_logged`, `_stage_and_train`, `_evaluate`, `_split_score` and `base._ProgressWriter`, `_state`, `_check_state`, `_partial_checkpoint`, `_score_seal`, `_write_bytes`, `counter_delta`, `_representatives`. Phase order: preflight → packets → checkpoint check PHASE A → seed + double build → main passes with evaluations → retention/interference → reloads/replays → PHASE B probes → ablations → source verification → deliver. Own `EXPECTED_ARTIFACTS` (< 500 names, unique, `required_count == len + 3`) and own expected-work check. |
| 5 | `research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py` | Copy of the practice launcher with the five schema constants, `WORKER_NAME`, `CANDIDATE`, `CONFIG_SCHEMA`, `JOB_PATTERN`, `_probe()` → `cncm.typed_pointer_worker` keeping the four-constant check, `EXPERIMENT`, `BOUNDS`, `worker_config`, the request/authority/owner validators including the three bindings, `bootstrap_source()` keeping the `count == 2` check, its own `render_worker()`, `evidence_contract()`, a `reservation_plan_for` with a new `task_scope`, and a `git_package_bytes` allowlist admitting the 18 checkpoint paths through `MATERIAL`. `PACKAGING_SOURCES` adds `"aws/typed_pointer_launch.py"`. |
| 6 | `records/typed_pointer_001/evaluate_gates.py` | Copy of the practice reader with a new I1 and a new I3 carrying the corrected DG4 evidence of §7.1. Primary label keyed on RELATIONAL, the all-kinds result as a flag, per-tier and per-kind tables, the relational removals applied to the population, the oracle ceilings printed, and the exact arithmetic unchanged. New output schema string. |
| 7 | `records/typed_pointer_001/{prepare_study.py, execute_study.py, preflight_dry_run.py, holdout_audit.py}` | Adaptations of the four practice drivers. The owner's verbatim text and all five decisions of §0.2 go into every job's `owner.json`. |
| 8 | `docs/CNCM_TYPED_POINTER_STUDY_v0.1.md` | **This document.** The frozen protocol, whose sha256 becomes `study.json`'s `protocol_sha256`. |
| 9 | `tests/test_typed_pointer_study.py` | The test map of §11.3, with a self-contained `sys.path` block at the top and the `public_only` numeric-import guard. |

**Build status at HEAD `026e6473`, stated honestly.** (See the note after this paragraph: HEAD has since moved to
`e3ee21c1`, and nothing in this build-status snapshot changes with it.) `pointer_contract.py` is built. Its own test
file was reported
green at **20 passed in 128.86 s** and an independent contract verifier exists at
`pre_design/verify_contract.py` carrying **25 checks**. **That verifier is not green**: a re-run reports **25
checks, 3 failed**, and the three failures are exactly the checks that still assert the **as-is** schedule —
`pointer_schedule(10) reproduces the practice batches digest`,
`pointer_schedule(10) has 147 updates/pass and 818 presentations/pass` (it measures `147 / 1176`), and
`pointer_schedule(10) matches the practice pointer_schedule line for line`. All three are made false by the owner's
stratified decision (§5.1). The other **22** checks pass. The checked-in `pre_design/verify_contract_out.txt` is
staler still, at **18 checks, 1 failed**. `pointer_inputs.py` exists in the working tree and is **IN BUILD**. The
seven remaining files are **planned**; none has been started. So the contract and its independent verifier are not
yet consistent with each other, and this protocol records that rather than reporting the verifier as green.

**A concurrent edit landed on `pointer_contract.py` while this document was being written**, and it is now committed
at HEAD **`e3ee21c1`**: the rank feature flag is `False` with the status string
`EXCLUDED_2026_09_19_ORDER_DEPENDENT_QUESTIONS_REMOVED_INSTEAD`. At the commit this protocol was drafted against
(`026e6473`) the flag was `True`; both states are recorded in §12, and the decision of §5.3 is what this protocol
freezes. The verified schedule constants (`STRATIFIED = True`, `PASSES = practice.PASSES`,
`MAX_PASSES_PERMITTED = 24`, `LEARNER_MAX_UPDATES_CEILING = 3544`, both `batches_digest` values, and the empty
`REMOVALS` placeholder) are **unchanged by that commit** and match what §4.2, §5.1 and §6 of this protocol state.
The verifier's three failing checks described above are unaffected by that edit, because they test the schedule and
not the rank flag. See §12.

### 11.3 The test map and the smoke list

P1–P14 are pure, $0, no torch. **S1–S10 are one AWS smoke job** per §11.3, **not claim-bearing**, except S10 which
is the run of the worker's own `run()` end to end.

| ID | test |
|---|---|
| P1 | Holdout and schedule identical to the practice study: the three digests of §2.1, 45 eligible / 5 shortcut. |
| P2 | Bucket length ≤ 63 for all three seeds. |
| P3 | Inventory has the 18 pinned checkpoint rows and stays within the row, byte and member bounds. |
| P4 | The restore-identity freeze test for all 9 checkpoints. |
| P5 | Package dry run with a fake git reader: archive ≤ 24 MiB; the rendered worker names `typed_pointer_worker` and never the old worker. |
| P6 | Launcher overrides: the watchdog accepts the new job pattern and refuses the practice one; `bind_authority`; `task_scope`; `failure_statuses`; `_probe` constants. |
| P7 | `EXPECTED_ARTIFACTS` unique, < 500, covers the checkpoint-check files, `required_count == len + 3`. |
| P8 | The worker refuses Windows BEFORE any numeric import and delivers a FAILED result with the new schema. |
| P9 | `pointer_inputs` purity, determinism and cache equality for all 230 labels; per-packet read time bounded. |
| P10 | Inputs exclude supports, cue, instruction, and **every** order-like channel (no rank feature); include the reach rule. |
| P11 | The planned-work formula matches the real schedule. |
| P12 | Gate reader: a flag-copy-only outcome gets no label; the exact arithmetic; the new I3. Re-run against the **final** population of 18, not before it. |
| P13 | The frozen flag-rule and rank-rule baselines and the removal lists of §4.2. |
| P14 | Custody: the checker is imported and targets derived only after the first pointer seal, except in phase B. |

| ID | smoke |
|---|---|
| S1 | All 8 kinds forward and backward under deterministic mode, bit-identical twice. |
| S2 | `train_sealed_batch` on a batch missing most kinds and on an interference batch. |
| S3 | export → restore → predict identical; replay from `prelast` equals `final`. |
| S4 | Evaluation leaves state unchanged. |
| S5 | Identical start with the check on and off, and the `^6` sub-block identity equal to the matched start. **AWS only.** |
| S6 | Phase A restores all 3 checkpoints and rebuilt logits equal `restored.predict` bit-for-bit; a forced failure still writes the artifact. |
| S7 | Time one pass plus one evaluation → projected job time. **This is the measurement that sets `PASSES` (§6).** |
| S8 | Score bounds and loss agreement. |
| S9 | No order-like channel at all — a node must influence the answer only through its declared features (raw flags), never through its position in the packet, its position in the file, or any part of its ref. Engineering only, never evidence. |
| S10 | The worker's `run()` end to end on a shrunken schedule, on the real AWS instance. |

**Where smoke runs: the whole list S1–S10 runs in ONE AWS job, not on the laptop.** As recorded at HEAD `026e6473`,
S1, S2, S7 (module level), S8 and S9 could run on the local RTX 4070 by driving the network module directly, in the
venv `~/venvs/cas-gpu`, dev only, and only **S10 needed the AWS instance**. That is **superseded**. HEAD `e3ee21c1`
records the owner's order of 2026-09-19 — quoted verbatim in the hand-off as *"STOP SAY FOCUSING ON '$0.00 spent.
Nothing on AWS.' … PLEASE REMEMBER THIS SO USE AWS"* — and `AWS_SMOKE_S10_PLAN.md` §3.1 (uncommitted in the working tree at the time this protocol was written) states the consequence: the local GPU is a laptop GPU, it is **not** a smoke-test
venue, and **every one of S1–S10 runs in the single approved AWS job**, which is the cheapest way to obey the order
because they share one boot, one package install and one instance. None of S1–S9 trains anything, so together they
add only a few minutes; they are not claim-bearing and are recorded as plumbing. The approved smoke remains a
**fourth** AWS job beyond the three claim-bearing ones, and its reservation goes through the launcher's own
reservation path into the canonical ledger, **never by hand**.

> **AMENDED 2026-09-19.** This paragraph said S1–S9 *"leave the total under the approved $1"* and that the smoke's
> reservation is *"small and recorded"*. Neither survives §0.2 item 2's correction: S10 alone is about **$0.96** of
> the approved $1, so anything added crosses it; and the launcher can only reserve **$15.00**, with no refund
> function anywhere in `budget.py`. The smoke therefore runs at a **$15.00 cap commitment with an actual cost of
> about $1**, which is what the owner's standing pre-approval covers. **What does not change:** the smoke is not
> claim-bearing, its receipts are voided by the gate program (`I1:<seed>:REDUCED_SCHEDULE:<mode>` in
> `records/typed_pointer_001/evaluate_gates.py`), and no registered constant is modified to make it fit.

`CONFLICT:` — **the venue rule for the smoke changed while this document was being written.** As recorded in
`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md` at HEAD `026e6473` (its §2 and §9), the standing rule was
"GPU-first. No neural work on local CPU. Local RTX 4070 = smoke/dev only. Every claim-bearing run on AWS GPU (not
Bedrock)." The amended rule, now committed at HEAD `e3ee21c1` and detailed in `AWS_SMOKE_S10_PLAN.md` §3.1, makes
the local RTX 4070 **not** a smoke venue and adds that "$0 is a status, not an achievement." The hand-off at
`026e6473` and this document were therefore in conflict on the smoke's venue. **The amended rule is the newer owner
order and governs the venue**, and this document follows it. Two things are unchanged: the approved envelope (~$13
expected, $45 reserved, plus the approved sub-$1 smoke) and the requirement to ask before exceeding it. §13's
`$0.00` is a factual statement of what this study has spent to date, not a virtue claimed on its behalf.

### 11.4 The standing rules

- **Plain English in every reply to the owner**, every time: meaning first, then the precise term; define jargon on
  first use; keep every literal exact; separate claim states.
- **The agent is NOT the research governor.** Do not pick a replacement hypothesis after a failed gate. A failed
  hard gate is a FAILURE, never "PASS with caveats." The claim status is what the frozen gate program prints.
  Owner approval must be an executable signed record.
- **GPU-first, and AWS is the venue — not the laptop.** No neural work on local CPU — fail closed `GPU_REQUIRED`,
  never silent CPU fallback. The local RTX 4070 is not a smoke venue; the whole smoke list of §11.3 runs in the one
  approved AWS job. Every claim-bearing run runs on AWS GPU, never Bedrock. Owner order 2026-09-19, committed at
  HEAD `e3ee21c1`; see the `CONFLICT:` in §11.3.
- **Never weaken a gate.** Not to make a result appear, and not to make a negative look better. A gate's power is
  part of its design and is disclosed before the run (§1.3), not adjusted after it.
- **Never edit shared modules, and never write to `CAS_RRK_v0.1`.** That directory belongs to a separate
  workstream. New files only, under the CNCM homebase.
- **Every result goes to `CHANGELOG.md` and to the spec sheet in the same commit**, with a dated change-log row and
  an artifact path. A status with no checkable artifact is not a status.
- **Receipts backed up to `D:\tksCAS-archive\`** with sha256 checks.
- **Never delete a negative result.** Numbers exact, never rounded.
- The evidence publisher is **create-only**: any file under `results/` that grows or is rewritten fails the final
  upload with `EVIDENCE_DIGEST_CONFLICT`. Write `<name>.partial` then rename; grow logs in a staging dir outside
  `results/`.
- Windows: the repo is `eol=lf`. `Path.write_text` emits CRLF and a CRLF `.py` fails the package build. Some OLD
  files are committed WITH CRLF — never "renormalize" them.
- Read the console before re-spending when an AWS job fails.
- **The worktree lives under OneDrive, and files can transiently vanish from a listing.** Do not conclude a file is
  lost from one failed listing; re-check and compare size and modification time. Snapshot every new file with a
  commit the moment it first appears.

### 11.5 Owner items

**Answered — do not re-ask.** The five decisions of §0.2. Plus: the two corrections were accepted, the smoke job was
approved, the gate change was confirmed, the purpose question was answered, and the training question was answered.

**Still open, and it is the only one.** **The budget, conditional.** If the smoke timing projects a job above about
**11,000 s**, a larger per-job reservation needs a **NEW** approval. The approved envelope is about **$13** expected
and **$45** reserved in total. Nothing has been re-asked yet.

The hand-off lists one further item — authorisation of the Vercel MCP server in an interactive `claude` session —
and records it as unrelated to this work and untouched. It is not an item for this study.

---

## 12. Every `CONFLICT:` and `UNCERTAIN:` in this document

Collected here so a reader can find them without hunting.

- **`CONFLICT:` §11.3** — the standing rule for where the smoke runs changed while this document was being written.
  The hand-off at HEAD `026e6473` allowed the local RTX 4070 as a smoke/dev venue and made only S10 AWS. HEAD
  `e3ee21c1` records an amended owner order of 2026-09-19, quoted verbatim in the hand-off as *"STOP SAY FOCUSING ON
  '$0.00 spent. Nothing on AWS.' … PLEASE REMEMBER THIS SO USE AWS"*, and `AWS_SMOKE_S10_PLAN.md` §3.1 states the
  consequence: the local GPU is not a smoke venue, so **S1–S10 all run in the one approved AWS job** (a few extra
  minutes, still under the approved $1), and "$0 is a status, not an achievement." **The amended rule is newer and
  governs the venue. The approved envelope (~$13 expected, $45 reserved, plus the approved sub-$1 smoke) and the
  requirement to ask before exceeding it are unchanged.**
- **`RESOLVED:` §4.3 (was a per-world `CONFLICT:`, retired 2026-09-19 by R1-15) — there was never a disagreement.** `INTERFACE_SPEC_POINTER.md:46` and `lk6_gate_population_out.txt:14` print the **same** five
  per-held-world counts for the same 29 eligible RELATIONAL questions, in different orders: the spec's cited source (`r4_reach_lexical.py:58`) uses an unsorted `Counter`, while the leaks run sorts by world id.
  Re-derived from the frozen material and confirmed by `pointer_contract.VERIFIED_RELATIONAL_BY_WORLD`, so **the spec's per-world figures may be quoted.** The gate population was never affected, because removals are
  applied per `query_id`. No `CONFLICT:` on the per-world spread remains anywhere in this document.
- **`CONFLICT:` §4.3** — the three sources put the post-removal relational population at different values from
  different removal stages: the learnability lens at **25** (29 − 4 flag-solved), the leaks run at **23** (29 − 6),
  and this protocol at **18** (29 − 6 shortcut-rule, − 5 architectural-inexpressibility). All three are exact and
  they count different things; `REVIEW_SYNTHESIS.md` §12.2 records the distinction, and the leaks run is
  authoritative because it enumerates every rule class rather than one. §4.3 freezes 18.
- **`UNCERTAIN:` §4.3** — the `reach` question whose id ends `2077da4b16f7` is attributed by the learnability lens
  to "the draft's stated flags alone" and by `lk6_gate_population_out.txt:68` to the PRESENT-for-all pointing
  policy, while the leaks run's `reach` flag rule removes **0** eligible questions (`:21`). It is the same question
  and it is removed under both readings, so the population is unaffected; only the attribution, and therefore which
  baseline row it belongs in, is undetermined.
- **`UNCERTAIN:` §5.2** — the saturation fraction for **torch-default with the INPUT placement** is not among the
  figures the learnability lens printed; the lens printed torch-default with the *output* placement (7.65–13.42 %).
  The worker's pass-0 assertion must measure the combination actually built rather than assume that number carries
  over. This protocol does not guess the value.
- **`CONFLICT:` §7.1** — `INTERFACE_SPEC_SHARED.md:678-681` and `pre_design/contract_pins/checkpoint_pins.json:81`,
  `:84` state different `model_state_identity` values for seeds 20260918 and 20260919. The pin-file values agree with
  the on-disk checkpoints and with the probe's own output artifact, and the in-job check must use them.
- **`CONFLICT:` §11.2 and §12** — the code-inventory row count is quoted as **236** for the practice study
  (`INTERFACE_SPEC_PIPELINE.md:730-732`) and as "236 + 18" in the pipeline review
  (`DESIGN_REVIEW_PIPELINE_LENS.md:196`), but `baseline.input_inventory` globs every `.py` under `cncm/` and
  `cas_meta2/` at read time (`worker_contract.py:138-143`) and the pointer build adds four new `.py` files under
  those two trees. `UNCERTAIN:` whether 236 is the row count after the new files exist or before. **No agent should
  quote 254 as a verified number.** The bound (≤ 2000 rows, ≤ 96 MiB) is not in danger either way.
- **`CONFLICT:` §11.2 and §12** — the design draft's own text still carries two open readings that
  `REVIEW_SYNTHESIS.md` §11 has since settled: the `correspondence` gate-population question, and the
  `node_rank_feature` flag value. In both cases the later record is the decision and this protocol follows it; the
  design draft is a draft and is not edited here.
- **`CONFLICT:` §4.3 and §11.2 — RECORDED AT HEAD `026e6473` AND ONE HALF SINCE RESOLVED, so both states are
  stated.** At HEAD `026e6473`, `pointer_contract.py` carried `"node_rank_feature": True` with
  `"node_rank_decision_status": "REGISTERED_INCLUDED_REOPENED_AT_6cb0b348_PENDING_LENS_A"`, while
  `REVIEW_SYNTHESIS.md` §10.2 and §12.3 require the flag to be set **False** — a real conflict at that commit. HEAD
  `e3ee21c1` then landed the flag as `False`. **CORRECTED 2026-09-19 (R1 item 6): the status string quoted here at
  drafting time said the order-dependent questions were "removed instead", and THAT CLAIM WAS FALSE — measured, the five
  rank-solvable questions (`parts` 1, `reach` 4, 2 kinds, 2 worlds) are NOT removed and REMAIN INSIDE the population of
  18. The FEATURE is excluded; the QUESTIONS were never removed. The current status string is
  `EXCLUDED_2026_09_19_RANK_FEATURE_OFF_RANK_SOLVABLE_QUESTIONS_NOT_REMOVED`.** `UNCERTAIN:` the
  `REMOVALS` placeholder is *not* closed by that commit — `REMOVALS["flag_rule"]` and `REMOVALS["rank_rule"]` are
  still empty, so the contract still refuses to be read as a finished population and §4.3's per-question lists have
  not yet been written into it. Separately, `UNCERTAIN:` the inline comment that landed with `e3ee21c1` records the
  rank-adoption arithmetic differently from this protocol (`18 to 13` and `7/13 = 0.5385` where §4.3 freezes
  `23 to 18` and `7/18 = 0.3889`). Both figures can be true of different stages, as `REVIEW_SYNTHESIS.md` §12.2
  warns; §4.3's figures are the ones this protocol freezes, because they are the ones the frozen population of 18
  is built from.
- **`CONFLICT:` §11.2** — the independent contract verifier at `pre_design/verify_contract.py` is not green at HEAD
  `026e6473`: a re-run reports **25 checks, 3 failed**, and the three failures are exactly the checks that still
  assert the as-is schedule that the owner's stratified decision makes false. The other 22 pass, and the checked-in
  `pre_design/verify_contract_out.txt` is staler still at **18 checks, 1 failed**.
- **`UNCERTAIN:` §11.2** — `AWS_SMOKE_S10_PLAN.md` §7 records two questions the smoke plan does not answer: whether
  the smoke should run phase A on one checkpoint or all three, and whether the 8-update training slice is long
  enough to expose a mid-run failure such as the score bound. The plan's own recommendations are one checkpoint and
  no duplication of S8. Neither is a claim-bearing decision, and neither is settled by this protocol.

---

## 13. Nothing has been run

**Nothing has been run. No gate has been claimed. `$0.00` has been spent.**

- No AWS job of this study has been launched. No AWS resources exist for it.
- The smoke job (S10) is approved by the owner and **has not been run**.
- The pointer learner has never been trained. No pass-0 reading exists for it.
- No gate has been evaluated, so there is no `LEARNS_NEW_WORLDS`, no `NO_TRANSFER_TO_NEW_WORLDS` and no `VOID` for
  this study. The label of the **practice** study (`NO_TRANSFER_TO_NEW_WORLDS`, commit `8cdbad81`) is the old
  machine's and says nothing about this one.
- Every number in this document is either read from a source cited beside it or is arithmetic on such numbers. No
  number here is a measurement of the pointer machine.
- The nine files of §11.2 are partly built and partly planned (§11.2's build-status note). Nothing is claim-bearing
  until the sequence of §11 has been run and the gate program prints a label.
