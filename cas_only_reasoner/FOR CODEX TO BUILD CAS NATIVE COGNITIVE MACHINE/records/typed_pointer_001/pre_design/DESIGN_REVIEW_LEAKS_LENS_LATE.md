# Late adversarial review of DESIGN_DRAFT_v0.1 — leaks, built-in answers, shortcuts, vacuity lens

> Returned 2026-09-19 AFTER the builder had re-run this lens and frozen design v0.2. Kept for the record; what is new relative to the frozen protocol is in `LATE_REVIEW_ADDENDUM_20260919.md`. Scratch scripts it names were not kept.

MEASUREMENT_NOTE: every number below comes from pure-Python scripts. No model was loaded and no GPU was used ($0). The scripts are in C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner\12c87ae7-c1f0-44b3-9b95-de65d5efbd48\scratchpad\design_review\ : build_facts.py (answer sets and the 45 eligible questions, taken from evaluate_gates.eligible_questions), leak_rules.py, leak_more.py, leak_template.py, leak_analogy.py, leak_analogy2.py, leak_corr2.py, leak_reach_lex.py, leak_reach_rule.py, leak_excerpt.py, leak_supports.py, leak_misc.py, leak_dev2.py, leak_union.py, leak_norank.py, leak_amb_overlap.py.
Baseline facts (MEASURED): 127 held records / 50 held questions. 45 of them are eligible for the gate and 5 are removed as shortcut questions (reach -> DIRECT). Eligible questions per kind: reach 9, role_set 6, and 5 each for definition, context, correspondence, analogy, parts and edge_account. Eligible questions per held world: 9, 10, 9, 8, 9.

VERDICT: As drafted, G_LEARN and the new RELATIONAL_TRANSFER flag can both be passed without any relational learning. Three things cause this: (a) the proposed input flags are the answers, (b) the participant-rank flags act as a hidden node alias, and (c) every held world has the same shape as some trained world once node names are ignored. With the current course, every one of the 29 relational eligible questions is solved by at least one no-relation baseline.

FINDINGS

F1 | FALSE_POSITIVE_RISK (critical) | MEASURED
Claim: Copying the proposed flags and excerpt text passes G_LEARN with no relational learning.
Evidence: Each rule below is fixed and uses no relations. Record and question counts are right / total.
- definition: whole = the declared_whole flag; kind_ref and function_ref = the focus-world flag. Held 15/15 records, 5/5 questions. Trained 36/36 records, 18/18 questions.
- context: setting_ref = focus flag; participants = the participant flag. Held 17/17 records, 5/5 questions. Trained 41/41 records, 19/19 questions.
- role_set: excerpt prefix -> roles, using focal.py:48 _ROLES. Held 6/6 questions. Trained 30/30.
- correspondence: map participant rank r to rank r; status MAPPING when the node counts are equal. Held 20/20 records, 5/5 questions. Trained 54/54 records, 19/19 questions.
- reach: a flag table keyed on (rank of whole, rank of part, rule, n), fitted on trained records only. Held 9/14 questions, 4/9 eligible. Trained 41/50 questions.
Arithmetic (evaluate_gates.py:39-70): an exact one-sided test needs b >= 7 when c = 0, b >= 10 when c = 1, b >= 12 when c = 2 and b >= 14 when c = 3.
- A flag learner fitted on trained records gets b = 25 (definition 5, context 5, role_set 6, correspondence 5, reach 4). That is p ≈ 3.0e-8, 5 kinds, 5 worlds.
- The DIRECT_READ tier alone gets b = 10, p = 0.000977. With c = 1 it is still p = 0.00586. Both pass.
- An untrained pointer machine is near chance on these kinds, so b is close to the full count (INFERRED). Examples: definition ≈ 1/4 × 1/64 × 1/64; role_set = 1/64.
Fix: Do not let definition, context or role_set count toward any "learns" label. Report them as READS_INPUT_FIELDS (a plumbing check). They must not count toward the ">= 2 kinds" rule.

F2 | FALSE_POSITIVE_RISK (critical) | MEASURED
Claim: The proposed flags "participant rank 1..3" and "primary rank 1..3" are a structural node alias. The draft's §2.1 promise of "NO node alias index" is broken.
Evidence:
- primary_labels == participants in 64/64 bank worlds. participants[0] == declared_whole in 64/64. So several proposed flags are exact duplicates.
- In 4-node worlds the ranks 0/1/2/3 are all distinct, so rank names every node uniquely.
- Written in rank coordinates, the edge list of all 64 worlds takes only 6 patterns. These are the 6 isomorphism classes.
- rank r -> rank r solves correspondence on 5/5 held questions (F1).
- "First other-domain world with the same rank-edge list" solves analogy on 17/17 held records and 36/36 trained records.
- RELATIONAL_TRANSFER can be passed by flags alone. Fitted on trained records: b = 9 (correspondence 5, reach 4), p = 0.00195, 2 kinds, 5 worlds. Best rule chosen on held: b = 12, p = 0.000244, 3 kinds.
Fix: Remove participant rank and primary rank. Remove is_primary, because it duplicates is_participant. Keep is_declared_whole. Keep an unordered is_participant only if context stays as a DIRECT_READ kind.

F3 | FALSE_POSITIVE_RISK (critical; the §5 ladder label is false) | MEASURED
Claim: The held worlds are only "twin-free" in the old machine's coordinates. For the pointer machine every held world has twins, so the held set contains no new shapes.
Evidence:
- holdout_audit.py:32-36 defines a twin by edges over sorted-ref positions plus the whole position. That is the old N-alias view.
- Ignoring node names, the bank has 6 shape classes. All 6 appear among the 19 trained-focus worlds. This holds with no flags, with the whole flag, and with rank flags.
- Trained-focus worlds that share each held world's shape: 22704554 -> 2, 28f61f2d -> 1, 4090ec49 -> 3, 6e1fcbda -> 1, 98c6352d -> 3.
- A lookup table keyed by (template, argument ranks) and fitted on trained records scores on held questions: parts 5/5, edge_account 5/5, reach 12/14 (9/9 eligible), correspondence 5/5, analogy 3/5. That is 27 of the 29 relational eligible questions.
- The union of all no-relation baselines solves 29/29 relational eligible questions (leak_union.py).
- The draft's §5 line "label our held-out as STRUCTURAL-level transfer (new worlds, new shapes)" is false for this held set.
Fix: Relabel any pass as "seen shapes, new labels". Structural transfer to new shapes needs held worlds whose shape class is absent from training. That means new material, or the development panel after the F6 fix.

F4 | FALSE_POSITIVE_RISK | MEASURED
Claim: Degree counts solve analogy and most of correspondence. No isomorphism search is needed, even with ranks removed.
Evidence:
- analogy: "first other-domain world with the same (n, e, out-degree multiset, in-degree multiset)" gets 5/5 held questions and 36/36 trained records. Using only (n, e, whole out-degree) gets 3/5.
- correspondence: a per-node signature (out-degree, in-degree, is_whole, is_participant) makes every consistent mapping correct on 4/5 held questions.
- This matches the earlier CMB-RP0 lesson that a graph-degree count can stand in for structure.
Fix: Register the degree-signature rules as mechanism-free baselines before the run. Remove the questions they solve from the relational population.

F5 | DESIGN_GAP (the eligible set is computed in the wrong output space) | READ + MEASURED
Claim: The gate removes constant answers written in N/W alias form (evaluate_gates.py:109-129). The pointer machine cannot emit alias constants. Its own constant answers are never removed.
Evidence: Input-blind answers in pointer form, scored on held questions:
- reach DIRECT: 5/14 held questions, 0/9 eligible (these are the 5 questions already removed).
- reach VIA the rank-3 participant: 5/9 eligible. VIA rank-2: 3/9. ABSENT: 1/9.
- reach VIA the whole argument, or VIA the part argument: 0/14.
- parts "participants minus the argument": 3/5. parts "PRESENT for all non-argument nodes": 0/5. parts "whole argument only": 0/5. parts none: 0/5.
- edge_account none: 0/5. analogy NO_MATCH: 0/5. analogy "focus world": never admissible, because the focus world always has the same domain.
- definition, context and correspondence are one fixed pointer pattern each: 15/15.
So reach -> DIRECT is no longer the only input-blind answer.
Fix: Recompute the shortcut set in pointer space inside the gate program, and freeze it before the run.

F6 | VACUOUS (development panel) | MEASURED
Claim: Almost all of the ten-node development panel is answered by a constant.
Evidence: The panel has 59 questions: 53 reach and 6 parts. ABSENT answers 42/53 reach questions and DIRECT answers 8/53. Only 3 VIA-reach questions and 6 parts questions are left, and 1 of those parts questions is solved by participants_minus_arg. This fits the earlier result where an untrained seed (20260918) scored 17/59.
Fix: Before the draft's §5 calls the panel "a further structural step", remove the questions answered by ABSENT or DIRECT and enlarge the panel. With 8 questions left, a pass needs 7 wrong -> right and none right -> wrong.

F7 | DESIGN_GAP (answer not fixed by the input) | MEASURED
Claim: Some reach answers depend on information the pointer machine does not receive.
Evidence:
- The question vector q holds only the kind (draft §2.1). The reach rule is left out. Swapping the rule changes the answer for 1 eligible held question (1/26 held records) and 9/71 trained records (5 trained questions).
- The reach rules break ties by lexical order of node refs. Ref order equals alphabetical label order in 64/64 worlds. The frozen hash label vectors carry no alphabetical order. 2 eligible held questions (5 records) have 2 or more structurally valid VIA answers, so for this machine they are coin flips. Trained records affected: 11/71. Rank order matches lexical order in 0/5 of the held cases.
Fix: Add the reach rule to q. Remove lexically ambiguous reach questions from the gate population, or change the checker so it accepts every structurally valid VIA answer.

F8 | LEAK, conditional (safe only if each question is answered without memory of other questions) | MEASURED
Claim: Held excerpts and supports contain answers about held worlds.
Evidence:
- 0/6 held role_set excerpts name another held world.
- 6/6 contain the exact correct answer to another eligible held question. Those questions cover 4 kinds and 5 worlds: correspondence 06e475e2 and 9b29b95c, definition 8da43399, analogy 497decac and ace89d2f, parts 6d9f6280.
- Held supports: 90 held records carry supports. 16 support entries are about other held worlds. None of them is an identical held question.
- Trained records never name a held world (practice_contract.py:113-115).
Fix: Add an integrity test. A held packet predicted alone must give byte-identical output to the same packet predicted inside the full evaluation stream. Forbid batch norm, caches keyed by world, and test-time adaptation. Assert by code that supports, cue and instruction are never read.

F9 | VACUOUS (as learning evidence) | MEASURED + READ
Claim: role_set is text classification by prefix.
Evidence: Every course excerpt is a single clause (focal.py:30-49). The prefix, and also the JSON field names, determine the roles. The rule gets 36/36. Every excerpt type that appears in the held set also appears in training.
Fix: Put role_set in the TEXT tier and exclude it from the "learns" labels.

F10 | MINOR (a second channel for rank information) | MEASURED
Claim: Declaration text points at specific nodes.
Evidence: The function text names the whole node plus one other label in 64/64 worlds. That other node is participant rank 2 in 64/65 mentions, and a child of the whole in 56/65.
Fix: Do not feed declaration token vectors to any node-level head, or remove node labels from the declaration text.

F11 | VACUOUS controls (permutation-equivariance and the baseline choice) | READ + INFERRED
- Node relabelling and world-alias permutation are vacuous controls for this machine. The draft already says so for node relabelling; the same applies to world aliases.
- The p0 (untrained machine) baseline does not control for flag copying (F1). The project rule applies: add a mechanism-free baseline.
- The draft's §5 ablation (reset one component at a time) is vacuous if it resets W_in or the heads, because everything breaks trivially. It should reset only the message-passing and ^6 weights, and report per tier. The flag tiers should not drop; that serves as a negative control.
- Probes of node states for targets that are linear in the input are vacuous at the initial checkpoint (h0 = W_in x). One-hop relations can also be read at initialisation through random message passing. Report only gains over the initial checkpoint.
- Automorphic candidates tie exactly and are then broken by lexical ref order (slots.py:33-34). This compounds F7.

F12 | DESIGN_GAP | MEASURED
Claim: The held worlds do pass through training.
Evidence: For world-choice slots the draft reads all 64 worlds. Held worlds are therefore encoded and receive gradient as negative candidates in 113 trained records per pass (definition 36, context 41, analogy 36). This is the same exposure class as the old full-bank packet. It must not be described as "never seen".
Other: All 5 held worlds share the domain "mechanical" and the setting "in a workshop".

CLEAN (checked, no leak found) | MEASURED / READ
- SOURCE header holds only {focus_world_id, bank{bank_digest, complete_within_supplied_bank, coverage, selection, world_ids}}. Nothing answer-bearing.
- role_catalog: 1 distinct value across all 564 records.
- Instruction text: exactly 1 per (kind, rule).
- Analogy candidates are always the whole 64-world bank. Correspondence candidates come from grammar only (answers.py:285-304).
- Held-world labels are new, except Chuck (held rank 2, trained rank 3) and Gear (held rank 3, trained rank 2). No label-memorisation leak.
- A "most popular trained analogy answer, different domain" rule gets 0/17 held. The answer-exposure exclusion works.

ANSWERS TO THE BRIEF
(1) No field the draft reads carries a held question's answer, as long as supports, cue and instruction are truly ignored and each question is answered without memory of other questions. The held role_set excerpts do not name other held worlds (0/6). Each one does contain another eligible held question's exact answer (F8).
(2) Yes. Definition and context are 100% flag copying. Correspondence is 100% rank copying. role_set is 100% prefix. reach is 4/9 eligible by rank flags. See F1 and F2 for the rules and counts on held and trained records.
(3) Flag copying passes G_LEARN (b = 25, p ≈ 3.0e-8) and RELATIONAL_TRANSFER (b = 9, p = 0.00195). What is left after fixes:
- Remove ranks and register the unordered-flag, constant and degree baselines: 12 relational questions remain (parts 2, reach 4, edge_account 5, correspondence 1; 5 worlds). Removing the lexically ambiguous reach question leaves 11.
- The derived subset (reach + correspondence) is 4 questions. The best possible p is 0.0625, so it can never reach 0.01 on this course.
- The adjacency-read subset (edge_account 5 + parts 2) passes only at 7/7 with c = 0. That would mean "copies the input edge list", not reasoning.
- If the template baseline is also registered, 0 questions remain.
(4) reach -> DIRECT is no longer the only input-blind answer. The new pointer-space shortcuts are listed in F5.
(5) See F11.

RECOMMENDED GATE (freeze in code before the run)
1. Input: remove rank and primary flags. Add the reach rule to q. Never let declaration text reach node heads.
2. Population P_REL: held eligible questions of kinds {reach, correspondence, analogy, parts, edge_account}, minus every question solved by a registered no-relation baseline B, computed by a frozen pure-Python program. B includes:
   - B1: the alias-form constant.
   - B2: the pointer-space constants from F5.
   - B3: per-node-flag rules using the final flag set, both fitted on trained records and the best rule on held.
   - B4: the degree-signature rules from F4.
   - B5: lexically ambiguous reach questions.
3. Test, per seed: trained full machine at pass 10 versus a trained twin with message passing removed (same flags, heads, schedule and seed) at pass 10. Exact McNemar test with b > c and p <= 0.01, on at least 2 kinds from {reach, correspondence, analogy} and at least 2 worlds. All 3 seeds must pass.
4. Labels:
   - Gains on definition, context and role_set are reported as READS_INPUT_FIELDS only.
   - A pass that rests on edge_account and parts is labelled READS_INPUT_ADJACENCY.
   - Any pass is scoped to "seen shapes, new labels" (F3).
   - A "new shapes" claim needs structurally novel held worlds, or the development panel after the F6 fix. Neither exists yet, so on this course the derived-relational gate is underpowered by construction and should be declared so before the run.
