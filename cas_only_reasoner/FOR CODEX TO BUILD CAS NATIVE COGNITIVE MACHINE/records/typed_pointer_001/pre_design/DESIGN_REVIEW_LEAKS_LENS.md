# Adversarial design review — leaks, built-in answers, shortcuts and vacuity

> Second review lens on `records/typed_pointer_001/pre_design/DESIGN_DRAFT_v0.1.md`. Read-only, $0, pure Python,
> no torch, no GPU, no network. It builds on `DESIGN_REVIEW_PIPELINE_LENS.md` (RK1–RK10, FP1–FP3, DG1–DG10, V1–V3,
> M1–M4) and re-derives none of it; everything below is new or is an exact number where the first lens had a count.
> Scratch scripts and raw stdout: `records/typed_pointer_001/pre_design/measurements/leaks_review/`
> (`lk0_material.py`, `lk1_answer_carriers.py`, `lk2_single_flag.py`, `lk3_pointer_policies.py`,
> `lk4_permutation_vacuity.py`, `lk5_pipeline_routes.py`, `lk6_gate_population.py`, each with `<name>_out.txt`).
> The scripts share three regenerable caches in that folder (`lk_cache_admissible.json`, `lk_cache_packets.pkl`,
> `lk_cache_order.json`); they are not deliverables and can be deleted.

> **This report answers the two items that `DESIGN_DRAFT_v0.2.md` left PENDING on this lens** (v0.2 appeared while
> this review was running, so it is reviewed here only for those two items):
> 1. v0.2 §7 "PENDING — leaks, shortcuts and vacuity" and §5.1's "WAITING on lens A for the complete removal list":
>    the complete removal list is **LK16** below, with per-rule eligible counts and the exact `query_id` values, and
>    the answer to v0.2's rank-feature question is **LK7**: the rank feature adds a 5-question shortcut
>    (parts 1, reach 4), taking the relational population from 23 to 18.
> 2. v0.2 line 657 ("29 − 3 − 2 = 24") is short by one removal: the PRESENT-for-every-node pointing policy also
>    answers 1 eligible held reach question, so the population **without** the rank feature is 29 − 3 − 2 − 1 = **23**,
>    and **with** the rank feature 29 − 3 − 2 − 1 − 5 = **18**. Both need b = 7 for c = 0 at p ≤ 0.01.
> v0.2's items that this lens also touches (the role_set excerpt, the analogy/correspondence candidate lists, the
> chance floors, the non-REACH vacuity claims) are LK1–LK6 and LK13–LK15.

VERDICT: **the proposed input carries held answers in three of the eight kinds, and the relational tier as
defined is not shortcut-free.** role_set's `focal_excerpt` **is** the answer — a published clause-prefix rule with
zero learned weights reproduces 6/6 held-back and 30/30 trained role_set records, and it survives the design's
own "position-free bag of token vectors" reading. definition and context are each the answer's own fields, fed
back as two input flags (5/5 and 5/5 of their eligible held questions, no learning). Inside the RELATIONAL tier a
single new input flag — the node's rank among the world's sorted refs — solves 5 of the 45 eligible held
questions by itself (parts 1/5, reach 4/9), and one adjacency hop solves all 5 parts questions and all 5
edge_account questions. Measured over the whole course, only **reach** is name-order dependent (held 5/26,
trained 11/71, every other kind 0/…), so the permutation-vacuity law is real but narrow, and adopting DG3's rank
feature would destroy it — because rank *is* the node alias (244/244 node refs have their sorted position equal
to their own stored index). The label only means something if LEARNS_NEW_WORLDS is printed from the RELATIONAL
test on a population of **23** questions (analogy 5, correspondence 5, edge_account 5, parts 2, reach 6) after
the six measured removals, with role_set reported separately and never counted; the minimum passing b for c = 0
at p ≤ 0.01 is **b = 7** (2⁻⁷ = 1/128 = 0.0078125), i.e. 7/23 = 0.3043 of that population, and the gate's
"≥ 2 kinds, ≥ 2 held worlds" constraint is still satisfiable (5 kinds, 5 worlds).

---

## LEAK

**LK1 — role_set: the focal excerpt IS the answer. [BLOCKS_LABEL]**
- Evidence (measured, `lk1_answer_carriers.py` PART B, `lk2_single_flag.py` is silent here because no flag is needed):
  - A line-prefix rule — read each line's clause prefix, look up the published role map — reproduces the checker's
    role answer for **6/6** held-back role_set records (6/6 held-back eligible questions) and **30/30** trained
    records (30/30 trained questions); excluded 0/0.
  - The DESIGN's own reading (a position-free bag of token vectors, draft §2.1 line 39) reproduces it **identically**:
    6/6 held, 30/30 trained. Across all 36 distinct token-bag signatures in the course, **0** carry more than one
    distinct role answer.
  - The rule is published: `focal.py:48-49` fixes `_ROLES = {definition:[1], context:[2], analogy:[3],
    correspondence:[4], parts:[5], account:[5,6], reference:[]}` and `focal.grammar_profile()` (`focal.py:69-83`)
    prints the prefix→roles contract; `derive_roles` (`focal.py:246-272`) reads **nothing** but the excerpt and the
    source it asserts against. The input list feeds that same excerpt (§2.1 line 39).
  - Held status values are all UNIQUE (6 of 6); trained 24 UNIQUE + 6 AMBIGUOUS, so the status field is also free.
- Resolution (build instruction): role_set must be registered as ANSWER_IN_INPUT and reported only — it may not
  enter any learning population and its gains may never contribute to LEARNS_NEW_WORLDS. If role_set is to be a
  real test, the input must stop containing the clause name (e.g. feed only the clause payload with the role
  vocabulary held out, or hold out the prefix strings themselves), and that change needs its own pre-run
  measurement of the new zero-learning rule. Do not "report the tier split" and leave it in the label.

**LK2 — definition and context are the answer's own fields, supplied as two input flags. [BLOCKS_LABEL]**
- Evidence (`lk1_answer_carriers.py` PART C, `lk2_single_flag.py` R13, `lk3_pointer_policies.py` "point at the
  argument node"/"point at the FOCUS world"):
  - definition flag copy (`is_declared_whole` + `is_focus_world`): **5/5** held-back eligible questions, 5/5 all held
    questions, 15/15 held records, 18/18 trained questions, 36/36 trained records, 19/19 excluded records.
  - context flag copy (`is_participant` + `is_focus_world`): **5/5**, 5/5, 17/17, 19/19, 41/41, 12/12.
  - No single flag does it (best single-flag rules: definition 1/5 with `is_focus_world` alone, context 0/5), so the
    flag copier needs exactly **two** flags per kind; those two flags are §2.1 lines 32-38 (per-node
    `is declared_whole` / `is participant`, per-world `is the focus world`, plus every world's kind/function/setting
    declaration text). `checker.py:169-183` computes the answers from exactly those declarations.
  - Every world's kind/function/setting declaration **text** is also an input (§2.1 line 38), so `kind_ref`,
    `function_ref` and `setting_ref` are additionally solvable by matching the focus world's own declaration text
    against the other 63 — a text match, not a graph operation.
- Resolution: keep definition and context as the DIRECT_READ tier, and make the gate program's label depend on the
  RELATIONAL population **only** (FP1's fix), with the DIRECT_READ table printed next to it. The registered
  flag-copy baseline (P12/P13) must carry these exact numbers, and P12 must show a flag-copy-only outcome prints
  NO label.

**LK3 — analogy: the candidate list plus a 6-to-9-element admissible set makes a guess ~13–15% per record, and
NO_MATCH is never the answer anywhere in the course. [FALSE_POSITIVE_RISK]**
- Evidence (`lk1_answer_carriers.py` PART E):
  - The `world_id` slot lists NO_MATCH + all 64 worlds (`slots.py:95`); `checker.py:213-237` accepts **any** world
    with a different declared domain and an isomorphic graph, and `check_answer` counts a prediction correct if it
    equals any admissible answer.
  - Admissible-answer multiplicity: held records **6 (10 records)** or **9 (7 records)**; trained **6 (3)** or
    **9 (33)**; excluded 6 (5) / 9 (12). NO_MATCH is admissible in **0/17** held, **0/36** trained, **0/17**
    excluded records — the symbol is dead, so "never NO_MATCH" is a free constant.
  - Worlds with a different declared domain: 48 of 64 in every record (16 worlds per domain × 4 domains), so one
    admissible world out of the remaining pool is right with probability 123/816 over all held records
    (576/4550 against the full 65-symbol list).
  - The "name the single different-domain world, else NO_MATCH" rule solves 0/17 held (no record has a single
    different-domain world), so the domain word is a 25% narrowing, not an answer.
- Resolution: register the per-question chance band and print it in the gate output; require the gained-question
  list to show, per gained analogy question, its admissible-answer count. A per-seed gain made only of
  multi-admissible analogy questions must be visible as such. Do not remove analogy (it is one of only three kinds
  with a non-zero admissible floor after the strict removals), but never let it be the only improved kind.

**LK4 — correspondence: the mode slot is a constant, the candidate space is never forced, and a mapping is a
1-in-24 guess. [FALSE_POSITIVE_RISK]**
- Evidence (`lk1_answer_carriers.py` PART E, `lk5_pipeline_routes.py` PART 2):
  - NO_MATCH is admissible in **0/20** held, **0/54** trained, **0/14** excluded records: the two-symbol mode slot
    (`slots.py:99`) is a constant across the entire course, so "always MAPPING" is free with no input read.
  - The forced-candidate shortcut (`slots.py:118`, `answers.py:298-304`: one candidate when the node counts differ)
    fires **0/88** records, and node counts differ in 0/88, edge counts differ in 0/88 — no free questions here.
  - Admissible mappings / syntactic candidates: held **24/500**, trained **135/1116**, excluded **34/260**; per
    record the multiplicity is 1 (16 held records), 2 (4 held records).
  - A predicted bijection is scored by `slots._candidate_scores` (`slots.py:259-273`) as a normalized distribution
    and then compared as a single assembled answer; the joint training loss rewards *any* member of the valid set
    (`learner.py:202-220`), so worlds with automorphisms give partial credit.
  - Correspondence is never trained on a held record (held presentations 0 of 1510; `lk5` PART 2), and no trained
    correspondence target is a held world (11 distinct trained targets, none held).
- Resolution: register that the mode slot carries no information; print per-kind correspondence accuracy against the
  measured chance (24/500 over the held correspondence records) and against the admissible multiplicity; require the
  gained-question list to show each gained correspondence question's admissible-mapping count.

**LK5 — `is primary label` and `is participant` are the same fact. [NOTE]**
- Evidence (`lk1_answer_carriers.py` PART H, `lk2_single_flag.py` R2 vs R4): `primary_labels == participants` in
  **64/64** worlds, and `participants_basis` is `PRIMARY_AUTHORED_LABELS_FIRST_THREE` in **64/64**. Rules R2 and R4
  give identical numbers (held reach records 5/26 each; trained context questions 1/19 each; 0/45 eligible for both).
- Resolution: drop `is primary label` / `primary rank` from the §2.1 input list (one fact, two flags), or state in the
  design that the list carries four independent node flags, not six.

**LK6 — the declared participants list is an authored order, and "rank" is literally the node alias. [NOTE]**
- Evidence (`lk1_answer_carriers.py` PART H, `lk1` PART G):
  - Declared `participants` is in sorted-ref order in only **14/64** worlds (example world: participants `n2, n1, n3`),
    so participant rank 1..3 carries an authoring order that is not a graph fact.
  - Node refs are `<world_id>/n<k>` and the public validator **rebuilds** them positionally
    (`source.py:254` `TYPED_SOURCE_WORLD_RECONSTRUCTION`, hit when a reviewer tried to rename them): the sorted
    position of a node ref equals its own stored index for **244/244** nodes, and `slots.alias_table`
    (`slots.py:55-60`) makes `N<i>` from the same sorted order. So "the node's rank among the world's sorted node
    refs" (DG3's proposed fix) **is** the public node alias the design says it excludes (§2.1 line 35).
  - Reach is the only kind whose answer is not name-blind: held **5/26**, trained **11/71**, excluded **2/10** records
    change under renaming; every other kind is **0/…** (`lk4_permutation_vacuity.py` PART B).
- Resolution: if DG3 is resolved by adding the rank feature, the design must say (a) the input now carries the node
  alias index, (b) the pointer machine is no longer permutation-equivariant, and (c) the §5 vacuity paragraph does
  not apply to it. The removal option (below) is the cheaper resolution and keeps the vacuity law intact.

---

## SHORTCUT

**LK7 — one input flag — the node's rank among the world's sorted refs — solves 5 of the 45 eligible held
questions by itself. [BLOCKS_LABEL]**
- Evidence (`lk2_single_flag.py` R10, `lk3_pointer_policies.py` "pick the node with the HIGHEST rank",
  `lk6_gate_population.py` REMOVAL 4):
  - "point at the alphabetically LAST node ref in every node slot": **5/45** held-back eligible questions
    (parts 1/5, reach 4/9); held records 1/9 (parts) and 10/26 (reach); trained 9/189 questions.
  - The mirror rule ("rank 0", the alphabetically first node) solves **0/45** eligible with one flag
    (`lk2_single_flag.py` R8; parts 0/5, reach 0/9), and 1/45 only when it is combined with the focus-world flag
    (`lk3`, definition 1/5).
  - Because rank == alias (LK6), this shortcut only exists if the rank feature of DG3 is adopted — but then it is
    fully learnable from the input and it lands inside the RELATIONAL tier.
- Resolution: register the "alphabetically last node" rule as a per-question baseline in the contract (P13). If the
  rank feature is adopted, remove its 5 questions from the relational population; the exact ids are printed by
  `lk6_gate_population.py` ("rank-last pointing"). If the rank feature is not adopted, the same 5 questions stay in
  the population but the protocol must state that the answer of 4 reach questions happens to coincide with the
  alphabetically last ref, which a name-blind machine can only reach structurally.

**LK8 — FP2, as its own measured line. [FALSE_POSITIVE_RISK]**
- Evidence (`lk1_answer_carriers.py` PART D and `lk2_single_flag.py` R12, `lk6_gate_population.py` REMOVAL 2):
  `parts(declared_whole) = participants − declared_whole` solves **3/5** held-back eligible parts questions,
  **3/5** held-back questions overall, **3/9** held records, **4/19** trained questions, **4/44** trained records,
  0/0 excluded. The same construction applied to edge_account (`declared_whole → participants − whole`) solves
  **0/5** held-eligible (0/17 held records, 0/46 trained) and to reach (`DIRECT` when whole == declared_whole and
  the part is a participant) **0/9** held-eligible (5/14 held questions — all five are the reach questions the
  registered input-blind shortcut already removes — 5/26 held records, 19/71 trained).
- Resolution: adopt FP2's fix with these numbers, i.e. remove the 3 identified parts questions **and** register the
  reach/edge flag rules as baselines that remove nothing further. The three removed question ids are printed by
  `lk6_gate_population.py` under "FP2 parts".

**LK9 — one adjacency hop solves every held parts question and every held edge_account question. [FALSE_POSITIVE_RISK]**
- Evidence (`lk1_answer_carriers.py` PART D, `lk6_gate_population.py` ORACLE RULES):
  - `parts = children of the query's whole argument`: **5/5** held-back eligible questions, 5/5 held questions,
    9/9 held records, 19/19 trained questions, 44/44 trained records.
  - `edge_account = the complete adjacency of the focus world`: **5/5**, 5/5, 17/17, 19/19, 46/46, 7/7.
  - `reach = DIRECT iff the part is a child, else ABSENT`: **1/9** held-eligible, 6/14 held questions, 6/26 held
    records, 26/50 trained questions, 26/71 trained records.
  - The adjacency enters message passing by design (§2.1 line 36), and the readout heads never see it — so these
    answers need one round of message passing and a linear readout, not relation chains.
- Resolution (explicit builder decision, must be frozen in the protocol): register the one-hop rule as a
  per-question ceiling and report **two** populations — PRIMARY (23 questions) which keeps the one-hop questions,
  and STRICT (16 questions: analogy 5, correspondence 5, reach 6) which removes them. If the label is printed from
  PRIMARY, the protocol must state that parts and edge_account are one-hop-copy kinds and that their gains cannot
  by themselves justify "relational reasoning" prose.

**LK10 — the rest of the zero-learning pointing policies, measured. [NOTE]**
- Evidence (`lk3_pointer_policies.py`, held-back eligible questions out of 45, / records out of 127 held / 358 trained):
  - point at the query's argument node: 5/45 (definition 5/5; 20/189 trained) — the DIRECT_READ flag copier again.
  - point at the query's `part` argument: 0/45 (0/189 trained).
  - point at the focus world in world-choice slots and the declared whole in node slots: 5/45 (definition 5/5).
  - PRESENT for every non-argument node: 1/45 (reach 1/9; 6/189 trained).
  - PRESENT for every node, edge pairs including self-pairs: 1/45 (reach 1/9; 1/189 trained);
    excluding self-pairs: identical, 1/45.
  - majority symbol per slot, fitted on the trained records' correct answers: **0/45** eligible, 5/50 held-all
    (reach 5/14 — again the already-removed five), 32/189 trained. The fitted table is printed by `lk3`
    (e.g. `role_set role → ABSENT`, `reach reach → DIRECT`, `edge edge → ABSENT`, `correspondence mode → MAPPING`,
    `definition whole → N0`, `analogy world_id → W18`).
  - ALL SYMBOLS TIED at 0.0 (what an untrained pointer machine with equal logits emits, `slots.py:293` argmax over
    the declared order): **1/45** eligible (reach 1/9), 1/189 trained — so an equal-logit machine already answers
    one eligible reach question and is right-to-wrong risk on it.
- Resolution: put these six policies and their measured numbers into the frozen baseline test (P13); the
  equal-logits policy in particular must be reported as the p0 expectation, and any question it already answers must
  be reported separately from the gains (it cannot be a gain, only a `c`).

**LK11 — one in three eligible questions is decided by a single record. [FALSE_POSITIVE_RISK]**
- Evidence (`lk5_pipeline_routes.py` PART 4): records per held-back question 1 (20 questions), 3 (14), 4 (15), 5 (1);
  held questions decided by a single record: **20 of 50** (parts 4, reach 10, role_set 6), of which **15 of 45** are
  eligible. Combined with LK3/LK4 (admissible-answer multiplicity 6–9 for analogy, 2 for 4 held correspondence
  records), a single lucky symbol can flip a whole question from wrong to right.
- Resolution: require the gate reader to print, per gained question, its record count and admissible-answer count;
  require the gained-question list to be part of the printed label output, not just the totals.

**LK12 — the existing input-blind removal is not leaky in the constant direction, but it is not frozen. [NOTE]**
- Evidence (`lk5_pipeline_routes.py` PART 5): the registered removal uses the most common **first** admissible
  trained answer per kind (`evaluate_gates.py:109-116`); recomputed independently it is **5** ({reach: 5}), identical
  to the gate's list. Using instead the most common **any** admissible trained answer removes the same 5 questions
  and no others. The best single alias-form constant per kind solves **0/45** eligible questions except reach
  (5/14 held questions, all inside the 5 already removed).
- Resolution: keep the rule, but freeze its output as an explicit id list in the pointer contract (P13) rather than
  recomputing it at gate time from the trained set; any later change to the split, the checker profile or the alias
  order silently changes the population otherwise.

---

## VACUOUS

**LK13 — which permutation claims cannot fail, with the measurement behind each. [NOTE]**
- Evidence (`lk4_permutation_vacuity.py` PART B; renaming the focus world's node refs and re-deriving the private
  answer with the checker's own rule functions, exactly as `measurements/pipeline_review/r4_reach_lexical.py` does):
  only reach is name-order dependent — held **5/26**, trained **11/71**; definition 0/15 and 0/36, context 0/17 and
  0/41, parts 0/9 and 0/44, edge_account 0/17 and 0/46, correspondence 0/20 and 0/54, analogy 0/17 and 0/36.
  role_set is recorded as 0/6 and 0/30 **by construction** rather than by renaming: its answer is a function of the
  excerpt text alone (LK1), so no renaming can move it.
- Therefore these are **VACUOUS** as evidence about learning, and must be listed as vacuous in the protocol:
  1. node-relabelling invariance of any world-level output (definition `kind_ref`/`function_ref`, context
     `setting_ref`, analogy `world_id`) — the world vector is a **mean** over node states (§2.2), so those logits are
     identical for every renaming;
  2. node-relabelling equivariance of the node heads (draft S9) — the readout index is the node's sorted-ref
     position, so a pass proves the wiring, not the learning (the draft already says this; keep it that way);
  3. any "the assembled answer is unchanged when node refs are shuffled" metric — for the seven kinds that are
     name-blind by construction it can only pass;
  4. the checkpoint probe's accuracy as a transfer measure — the probe reads node vectors and never a position, so
     it is order-invariant by construction (V2's half is also vacuous on its own terms: the pre-block vectors are
     identical at every checkpoint);
  5. I3 as written ("initial model identity re-derives from the seed") — the pure-Python reader cannot run torch
     (DG4/V3);
  6. the registered secondary flag RELATIONAL_TRANSFER **as printed** — with the 6 measured shortcut questions still
     inside the 29, it is satisfied by the same copying FP1 identified.
- Resolution: write these six lines into the frozen protocol as VACUOUS, and print them next to the label so no
  reader mistakes a passing invariance test for evidence.

**LK14 — adopting the rank feature breaks the vacuity law itself. [FALSE_POSITIVE_RISK]**
- Evidence: `lk1_answer_carriers.py` PART H (244/244 node refs: sorted position == stored index) and PART G; the
  draft's claim ("invariance tests on node relabelling are VACUOUS for a permutation-equivariant pointer machine",
  §5) is true only while the input carries no order-derived feature.
- Resolution: if DG3 is resolved by adding rank, the protocol must (a) withdraw that sentence, (b) register that the
  machine can now read a per-node index equal to the public alias, and (c) replace the equivariance test with the
  no-alias-channel test E1 below, which can no longer be stated as an equivariance property.

**LK15 — required permutation tests (engineering only; none is learning evidence). [NOTE]**
- From `lk4_permutation_vacuity.py` PART E, with the measured facts above as the reason each is needed:
  - E1 no-alias-channel: rename every node ref in every world and assert the pointer input tensors are
    byte-identical, except through the registered rank feature if it is adopted.
  - E2 wiring: permute a world's node rows and assert the node-head logits permute by exactly that permutation while
    the world vector g_w stays bit-identical.
  - E3 symbol-row alignment: assert the node tensor row order is the reader's order and that slot symbol order still
    maps row *i* to alias `N<i>` (`slots.py:88`, `:101`, `:103`, `:107`).
  - E4 rank feature (only if adopted): assert every rank is the sorted-ref position and that rank is the only
    order-derived feature.
  - E5 answer-side precondition: the frozen test must carry the per-record renaming-dependence list (2 eligible reach
    questions, ids printed by `lk4` PART C and `lk6` REMOVAL 3) so a name-determined answer cannot sit in the gate.
- Resolution: add E1–E5 to the pre-launch test list (P13 in the hand-off) as engineering checks, and count none of
  them as evidence of learning.

---

## REQUIRED_REMOVALS

**LK16 — the exact removal list for the RELATIONAL tier, and the resulting population. [BLOCKS_LABEL]**
- Evidence and counting rule (`lk6_gate_population.py`): a question is removed when **every** record of it is
  answered correctly by a registered no-learning rule. Unit of evidence is the question, as in the gate
  (`evaluate_gates.py:52-54`). Removals, per rule, counted over the 45 eligible held questions:
  - the registered input-blind shortcut: **0** eligible (its 5 removals are reach questions, made before eligibility);
  - FP2 `parts(declared_whole) = participants − declared_whole`: **3** (parts);
  - reach flag rule `DIRECT if whole == declared_whole and part is a participant`: **0**;
  - edge flag rule `declared_whole → participants − whole`: **0**;
  - name-order dependence (a name-blind machine cannot know the answer): **2** (reach) — the whole-course counts are
    held 5/26, trained 11/71, excluded 2/10 records;
  - rank-0 pointing: **0**;
  - **rank-last pointing (only if the rank feature is adopted): 5** (parts 1, reach 4);
  - PRESENT-for-every-node / every-edge pointing: **1** (reach);
  - argument-node pointing: **0**; best fitted constant: **0**.
  - Union without the rank feature: **6** questions → RELATIONAL 29 − 6 = **23**
    (analogy 5, correspondence 5, edge_account 5, parts 2, reach 6), spread 4 / 4 / 7 / 5 / 3 over the five held
    worlds. Union with the rank feature: **11** → **18** (analogy 5, correspondence 5, edge_account 5, parts 1,
    reach 2), spread 4 / 3 / 3 / 5 / 3.
  - STRICT variants (also removing the one-hop adjacency questions — 11 eligible questions are solved by those
    rules, of which 7 are still in the primary population): **16** without rank
    (analogy 5, correspondence 5, reach 6) and **12** with rank (analogy 5, correspondence 5, reach 2).
  - Minimum passing b for c = 0 at p ≤ 0.01 by the gate's own exact test (`evaluate_gates.py:39-43`,
    `binomial_upper_tail(b, b) = 2**-b`): **b = 7** for every one of those populations
    (2⁻⁷ = 1/128 = 0.0078125 ≤ 0.01; 2⁻⁶ = 1/64 = 0.0156250 > 0.01). Required share:
    7/23 = 0.3043 (primary, no rank), 7/18 = 0.3889 (with rank), 7/16 = 0.4375 (strict, no rank),
    7/12 = 0.5833 (strict, with rank). Gains in ≥ 2 kinds and ≥ 2 held worlds remain satisfiable in every variant
    (5 kinds / 5 worlds; strict-with-rank 3 kinds / 5 worlds).
  - The eligible all-eight-kinds population for reference: 45 − 6 = 39 (or 45 − 11 = 34 with rank).
- Resolution (build instruction): freeze the removal list as explicit `query_id` values in
  `pointer_contract.py` (the ids are printed by `lk6_gate_population.py` under "removal ids by rule"), print it in
  the gate reading, and make the primary label
  `G_LEARN_p0_to_p10` on the **23-question RELATIONAL population** (or 18 with the rank feature), with DIRECT_READ
  and TEXT printed alongside and never counted. State the minimum passing b = 7 and the population size in the
  protocol so the binomial reading is transparent.

**LK17 — the strict population's arithmetic is a false-negative trap. [FALSE_NEGATIVE_RISK]**
- Evidence (`lk6_gate_population.py` GATE ARITHMETIC): if the one-hop adjacency questions are also removed, the
  population is 16 (or 12 with rank) and b = 7 then requires 7/16 = 0.4375 (or 7/12 = 0.5833) of it; the kinds left
  are analogy, correspondence and reach (edge_account survives only in the strict-no-rank variant), which includes
  the two kinds with the largest chance floors (LK3, LK4). All three seeds must pass, so a stricter population
  raises the chance that a genuinely learning machine prints NO_TRANSFER_TO_NEW_WORLDS.
- Resolution: pick the population before the run, in writing, and register the strict variant as a **reported**
  sensitivity analysis rather than the label's population — or, if the strict variant is the label's population,
  accept in the protocol that b = 7 is 7/12 = 0.5833 of it and that kinds with a ≥ 6-of-65 chance floor carry the
  required kind spread.

**LK18 — four smaller pipeline routes to a wrong label, measured. [NOTE]**
- Evidence (`lk5_pipeline_routes.py`):
  1. **depth**: training runs at depths 1/2/4/8 (38/37/34/38 batches of pass 1) for every kind — 1070/1510
     correspondence, 1610/2310 reach, 1280/1720 parts, 560/780 role_set, 340/460 definition, 350/470 context,
     260/410 analogy, 380/520 edge_account presentations are at depth < 8 — while every evaluation uses 8
     (`typed_practice_worker.py:145`). Fix K = 8 (DG1) and register that the learner must not condition on `depth`,
     or the p0-to-p10 gain can include depth extrapolation rather than learning.
  2. **joint correspondence loss**: the valid set comes from the private target (`loss_plan.py:100-105`) and is
     applied only to trained records; trained records naming a held world 0, trained correspondence targets naming a
     held world 0 of 11 distinct targets, analogy answers naming a held world in the trained set 0. The route is not
     a leak to held worlds; its effect is that the mode slot is a forced constant (LK4).
  3. **checkpoints**: the label reads pass 0 and pass 10 of the FULL-course evaluation
     (`evaluate_gates.py:201-203`, `:216`), the dedicated held-back checkpoints 2/4/6/8 gate nothing, and the
     `retained` checkpoint (post-interference) is outside every gate (`typed_practice_worker.py:355-358` vs
     `:366-385`), so the 16 definition+context interference updates cannot flatter the label. What is NOT reported
     is the held-back trajectory at 2/4/6/8 as a monotonicity check; register it as a printed, non-gating curve.
  4. **removal rules**: the removal is computed at gate time and is data-dependent (LK12); freeze it.
- Resolution: fold (1), (3) and (4) into the frozen protocol as printed requirements; (2) needs no change but should
  be quoted in the protocol so the mode slot's constant nature is on the record.

---

### Files created by this review

- `records/typed_pointer_001/pre_design/DESIGN_REVIEW_LEAKS_LENS.md` (this report)
- `records/typed_pointer_001/pre_design/measurements/leaks_review/` —
  `lk0_material.py`, `lk1_answer_carriers.py`, `lk2_single_flag.py`, `lk3_pointer_policies.py`,
  `lk4_permutation_vacuity.py`, `lk5_pipeline_routes.py`, `lk6_gate_population.py`, and each script's raw stdout as
  `<name>_out.txt`.
- Regenerable caches in the same folder (not deliverables): `lk_cache_admissible.json`, `lk_cache_packets.pkl`,
  `lk_cache_order.json`.