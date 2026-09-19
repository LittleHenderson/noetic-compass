# Late adversarial review of DESIGN_DRAFT_v0.1 — can it learn each kind lens

> Returned 2026-09-19 AFTER the builder had re-run this lens and frozen design v0.2. Kept for the record; what is new relative to the frozen protocol is in `LATE_REVIEW_ADDENDUM_20260919.md`. Scratch scripts it names were not kept.

- Scope: 17 findings across 14 local pure-Python checks, with no torch and no model run.
- Main result: the held-back set is not a new-world test for this machine. For a machine that ignores node names and reads only the flags and the "contains" edges, every held-back world is a same-shape copy of worlds it trained on.
- Labels used below: MEASURED = I ran a check; READ = I read the code; INFERRED = reasoning, not run.

```
SCRIPTS: C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner\12c87ae7-c1f0-44b3-9b95-de65d5efbd48\scratchpad\design_review\
  (load.py, m_sched.py, m_worlds.py, m_reach.py, m_flags.py, m_wl.py, m_twins.py, m_noadj.py, m_analogy.py, m_classes.py, m_corr2.py, m_dev.py, m_devlab.py, m_batches.py, m_tok.py, m_excerpt.py)
Paths below are relative to CNCM = C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE
TT = research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching

=== PER-KIND RULE vs PROPOSED MACHINE (can it be expressed with the draft's inputs?) ===
definition   READ TT/checker.py:169-177. Answer = declared_whole flag + focus-world flag. Expressible. A pure flag copy.
context      READ checker.py:178-183. Answer = focus flag + participant flags. Expressible. A pure flag copy.
parts        READ checker.py:184-189. Answer = children of the query whole. Needs 1 round of message passing. Expressible.
edge_account READ checker.py:190-195. Answer = the full edge set, order-free.
             MEASURED (m_wl.py): structure-only 1-WL node colours give 0 edge-readout ambiguities over all 64 worlds.
             Expressible, but concatenation MLP[h_a,h_b,q] is a weak way to learn a pairwise test (see F9).
reach        READ checker.py:115-153 and answers.py:32-33. TWO rules:
             - first_direct_constituent_lexical_v1: first child in sorted-ref order that has a path.
             - bfs_immediate_predecessor_lexical_v1: BFS in sorted-neighbour order; the answer is the node just before the part.
             The answer depends on ref order when there are ties, and on the rule. See F5, F6.
correspondence READ checker.py:96-112 and 200-212, loss_plan.py:100-105. ALL valid bijections are admissible,
             and the loss is over the whole valid set. No order dependence.
             MEASURED: 88/88 correspondence records are MAPPING. NO_MATCH never occurs (F10).
analogy      READ checker.py:213-237. All matching worlds in other domains are admissible. No order dependence.
             MEASURED: 1-WL separates all 6 shape classes. Mean pooling vs sum pooling: 0 collisions (m_wl.py).
             Expressivity is fine; the scoring head is not (F9).
role_set     READ TT/focal.py:45-46, 146-177. Roles = a fixed function of each clause's prefix.
             MEASURED: 36/36 excerpts have exactly 1 clause, 6 clause types x 6 records. A keyword classifier.
Order dependence overall: ONLY reach needs lexical order (sets are order-free; "first three participants" is given directly as flags).
MEASURED facts behind this:
- Node refs n0..n3 follow alphabetical label order in 64/64 worlds (m_worlds.py).
- A frozen token vector does not encode alphabetical rank, so lexical tie-breaks cannot be learned except by memorising label pairs.

=== FINDINGS (most severe first) ===

F1 FALSE_POSITIVE_RISK (top) | MEASURED (m_twins.py, m_classes.py, m_wl.py, m_analogy.py)
The held-back set is not "new worlds / new shapes" for a permutation-equivariant pointer machine.
- The holdout's "twin-free" rule is POSITIONAL: it compares edge lists over sorted N-alias positions plus the whole's position
  (records/typed_practice_001/holdout_audit.py:8-10, 32-36). That rule was built for the old alias machine.
- Under the pointer machine's own equivalence, every held world has trained twins. That equivalence is isomorphism preserving
  the draft's node flags (whole / participant rank 2 / rank 3 / non-participant):
  - 22704554 has 2 twins, 28f61f2d has 1, 4090ec49 has 3, 6e1fcbda has 1, 98c6352d has 3.
  - The 64 bank worlds contain only 6 isomorphism classes (sizes 8, 8, 12, 12, 12, 12).
  - The 24 course worlds form 6 classes of sizes 3-5 under unlabelled, coarse-flag and rank-flag labellings. No class has only one world.
- Question level: 34/34 eligible held questions of kinds context, correspondence, definition, edge_account, parts and reach
  have a trained question with the same input for this machine (same kind and rule, flag-preserving isomorphic world, arguments
  in the same roles). Each has at least one such trained twin with the same answer.
- Analogy: 3 of 5 held questions have a trained analogy question with an IDENTICAL valid-answer set.
- Only 2 eligible held questions (analogy on 6e1fcbda and 28f61f2d) have no twin. Their best possible result is b=2, p=0.25, so they cannot pass.
- Consequences:
  - A LEARNS_NEW_WORLDS or RELATIONAL_TRANSFER label would mean "handles new label words on shapes it already saw".
  - It would not mean relational transfer.
  - Draft §5 line 92 ("STRUCTURAL-level transfer (new worlds, new shapes)") is false as written.
  - The "same holdout, so the results are comparable" argument (§3 line 66) fails, because how new a world is depends on the machine.
- FIX:
  - Re-derive the holdout under flag-preserving isomorphism (focus world, plus target world for correspondence, plus argument roles, kind and rule).
  - This is impossible inside this course (no single-world classes), so author NEW-SHAPE held worlds.
  - For isomorphism kinds, stay within 4 nodes (checker.py:20 MAX_ISOMORPHISM_NODES=4). The bank uses only five 4-node classes
    and one 3-node class. Other 4-node DAG shapes exist, e.g. the in-star (INFERRED).
  - Also register a "twin-lookup" baseline: answer = the mapped answer of the trained twin. It scores at least 37/45 here.
  - Move the primary structural claim to structurally novel worlds.

F2 FALSE_POSITIVE_RISK | MEASURED (m_flags.py, m_noadj.py) + READ
The primary gate and the new RELATIONAL_TRANSFER flag can both pass from flag copying alone.
- DIRECT_READ kinds are 100% flag-solvable by construction (checker.py:169-183).
  - MEASURED: whole == participants[0] and participants == primary_labels in 64/64 worlds.
  - Eligible held: definition 5 + context 5 = 10 questions, 2 kinds, 5 worlds.
  - If the untrained machine misses them, b=10, c=0 gives p = 2^-10 = 0.00098, so G_LEARN passes. (INFERRED gate arithmetic from evaluate_gates.py:57-70.)
- Correspondence:
  - The rule "map participant rank k to rank k, non-participant to non-participant" reads no edge.
  - It is valid on 5/5 held and 19/19 trained correspondence questions.
  - The mode head is a constant (always MAPPING).
- Reach: a no-adjacency lookup keyed on (rule, role of whole, role of part), fitted on trained records, gets 4/9 eligible held reach questions.
- RELATIONAL_TRANSFER from flags alone: 5 + 4 = 9, across 2 kinds and 2 or more worlds. p = 0.00195, so it passes.
- The old shortcut exclusion was defined in N-alias/W-alias symbol space (evaluate_gates.py:109-129). It does not catch the pointer machine's flag-level constants.
  - MEASURED: trained flag-level constants answer 5/5 eligible held correspondence and 3/9 eligible held reach.
- Draft §3 lines 75-77 put correspondence under RELATIONAL. Under the draft's own inputs it is DIRECT_READ.
- FIX:
  - Before the run, register machine-specific mechanism-free baselines:
    (a) a flag-level constant per kind;
    (b) the no-adjacency flag lookup;
    (c) the rank-identity correspondence rule;
    (d) the twin lookup.
  - Remove every held question solved by (a)-(d) from the gate population, the same way the old input-blind shortcut was removed.
  - Also feed the declaration flags (whole / participant) ONLY to the definition and context heads. The relational encoder gets structure plus query-argument flags only.
  - MEASURED (m_corr2.py): even coarse flags without ranks still solve correspondence on 1 held question outright and 2 more
    through lexical first-wins decoding. So masking is needed; dropping the ranks alone is not enough.

F3 RUN_KILLER | READ + MEASURED
"Interface kept, only the logits change" is not reusable as stated.
- TT/learner.py:81-86 requires the registered plastic scope to be exactly {left.weight, merge.weight, right.weight} of ^6
  (graph_teaching/trainer.py:79-91 freezes all other parameters). Extra parameters make the constructor raise.
- cncm/typed_practice_worker.py:174-181 and 361 require main-training counters equal to per-slot recurrence counts
  (core_forward_calls = sum of slots x depth). A pointer machine fails "MAIN_TRAINING_COUNTERS" only AFTER all 1,470 paid updates.
- learner.py:271 requires p.grad to be non-None for every parameter.
  - MEASURED (m_batches.py): 0/1,470 batches contain all 8 kinds.
  - Batches in which a head gets no gradient: role head 1,150, excerpt W_txt 1,150, edge head 950, world head 920,
    node head 320, W_arg 190, pointer 70.
  - Copying this check kills the run at update 1.
- FIX:
  - Write a new learner class with its own admitted plastic scope. This is a change to the registered plasticity contract, so it needs an owner-signed phase record.
  - Write a new expected-work contract for the worker.
  - Accept None or zero gradients for idle heads.
  - Run main() end to end on the local RTX 4070 as a smoke test before launch.

F4 RUN_KILLER risk | READ learner.py:261 + INFERRED
- The scalar-vs-tensor loss check uses rel_tol = abs_tol = 2e-5. The scalar side is float64 from float32-rounded scores; the tensor side is float32 logsumexp.
- The residual h <- h + ^6(...) is never normalised, and the pointer logits <W_p q, h_v> are unbounded.
- Once |logit| reaches about 200-300, float32 rounding (ulp(256) ≈ 3e-5) exceeds the tolerance. The learner sets failed and the run dies mid-training.
- The old machine stayed safe: RMS reinjection (recurrent_cjt/recurrence.py:182-215) and a frozen unit readout kept logits bounded.
- FIX: per-round RMSNorm or LayerNorm; bounded logits (cosine x learned scale, or c*tanh(s/c), c ≈ 20); or compute the tensor loss in float64.

F5 DESIGN_GAP | MEASURED (m_reach.py)
The reach rule is missing from the input.
- The draft's q = E_kind + W_arg + W_txt carries no rule.
- Questions where the two rules give different answers: held 1 (4090ec49 n1->n2, answer VIA n3; the other rule gives n0), trained 5, excluded 1.
- 13 of 51 (world, whole, part) triples are asked under both rules.
  At least 2 trained triples (71465a41 n2->n1: n3 vs n0; 54fa2f86 n2->n0: n3 vs n1) are identical inputs with contradictory targets.
- Development panel: all 53 reach questions use first_direct.
- FIX: add E_rule (9 kind x rule ids) to q. query["rule"] is public structured data.

F6 DESIGN_GAP | MEASURED (m_reach.py)
Lexical ties in reach cannot be learned without order.
- Held: 2 of 14 reach questions (98c6352d n2->n0 under both rules; candidates n1/n3 are the two sides of a diamond, which are automorphic).
- Trained: 5 of 50 questions (3b0abc92, 68987078, 2e7a50f3 diamonds). The lexically smaller side always wins.
- With label vectors in the input, the machine must memorise which label is alphabetically first. That does not transfer.
- MEASURED coincidence: "pick the higher participant rank" matches 2 of 3 trained tie worlds and the held one.
  A flag-based tie rule would be right on held for the wrong reason.
- If labels are removed, the tied sides get exactly equal logits. The decoder's "first wins" rule (slots.py:29, 293) then
  returns the lexical answer for free.
- FIX: either restore a within-world ref-ordinal feature for reach only (the rule is explicitly lexical, so this is legitimate),
  or remove tie questions from the gate. In both cases, report how many decisions were settled by exact ties, separately.

F7 DESIGN_GAP | MEASURED (m_sched.py) + READ
Depth is not 8 during training, and states are not normalised.
- The schedule depth per batch is 1: 380, 2: 370, 4: 340, 8: 380 (worker_contract.py:43; typed_practice_worker.py:112 passes batch["depth"]).
- Prediction always uses depth 8.
- If rounds = depth, about 51% of updates train the heads on 1-2 round states:
  - reach needs up to 3 hops (MEASURED: paths of 3 edges exist, e.g. 4090ec49);
  - state scale drifts with depth (^6 has no bias and a linear merge; neural.py:104-126).
- INFERRED: at default init the residual map behaves like (I + J)^rounds and grows until tanh saturates.
  Heads are trained across a 1x-8x spread of round counts and evaluated only at 8.
- FIX: fixed K rounds independent of the schedule's depth (K ≥ longest path; course 3, development ≤ 2 hops, MEASURED), or
  per-round RMSNorm plus a gated (GRU-style) update. Record the choice in the design.

F8 DESIGN_GAP (memorisation channel) | READ + MEASURED
- No answer reads node label text. checker.py and focal.py use node["ref"], edges, declared refs and domain equality only.
  Declaration kind/function/setting text is only an identity (answers.py:128-132).
- So label vectors and kind/function/setting text vectors carry zero task value. They are pure per-world identity features
  (MEASURED: 68 distinct labels in the trained focus worlds; W_in can keep all of them).
- AdamW weight decay 0.01 at lr 3e-3 shrinks weights by about 4.3% over 1,470 steps (INFERRED). That is no pressure against using labels.
- Held worlds share labels "Chuck" and "Gear" with trained worlds, which invites spurious carry-over.
- Development panel: labels "DevkNodej" are out of vocabulary and fall back to bytes (90 byte tokens for 10 labels).
  MEASURED within-world label cosine: 0.909-0.911 on development vs 0.000 on the course.
  Any label use makes the development panel an input-shift test.
- FIX:
  - Drop node label and kind/function/setting text vectors. Drop participant/primary RANKS and primary flags (duplicates).
  - Keep a constant 1 feature. READ: without it, unflagged nodes stay exactly zero forever, since ^6 has no bias and tanh(0)=0.
  - Keep is_whole and is_participant (routed per F2), the query-argument flags, and domain text only inside the analogy head.

F9 DESIGN_GAP (head expressivity) | READ + INFERRED
- World-choice logit <W_w[q;g_F], g_w> and the correspondence mode "option · [q, g_F, g_T]" are linear in g_w (or in g_F, g_T).
  They cannot express "g_w equals g_F". The argmax goes to the largest projection, not the match.
- Node mapping logit (q + h_s)^T W_p^T h_t:
  - The q term cancels in the joint bijection sum.
  - Only a positive-semidefinite form guarantees the true isomorphism wins, by rearrangement.
  - The draft does not constrain W_p.
- FIX:
  - Analogy: score −||P g_F − P g_w||² or cosine, plus a learned same-domain penalty.
  - Correspondence nodes: score −||A h_s − A h_t||².
  - Edge head: h_a^T M h_b plus an MLP.
  - Use sum pooling (or mean plus a count). No collision measured, but sum is the 1-WL-safe choice.

F10 VACUOUS | MEASURED (m_noadj.py)
- NO_MATCH is never a correct answer anywhere in the course: correspondence 88/88 records MAPPING; analogy 15/15 trained and 5/5 held
  questions have 6 or 9 valid worlds.
- So the NO_MATCH option vectors and the correspondence mode head only learn a constant.
- Any gain on the mode is a constant, not a relation.
- FIX: report mode and NO_MATCH as untestable. Do not count them as relational evidence.

F11 DESIGN_GAP | MEASURED (m_dev.py)
The development panel can be read with the same inputs but is a poor test as it stands.
- It has 59 packets: 6 parts + 53 reach, 65 worlds per packet, 6 focus worlds of 9-10 nodes, disconnected forests.
  Same schema: nodes, contains, declared_whole, participants, primary_labels.
- Reach answers: 42 of 53 ABSENT, 8 DIRECT, 3 VIA. Trained reach records: VIA 45, DIRECT 25, ABSENT 1.
  - A constant "ABSENT" scores 42/53, above every old-study score (max 17/59).
  - The ABSENT option is trained on 1 record.
- Participants are always [whole, n0, n1]. n0 and n1 are often grandchildren or in other components, unlike the course, where
  participant ranks follow the shape. Rank-based habits fail here (also a point for dropping ranks).
- No lexical ties; at most 2 hops (so the depth problem does not bite here).
- FIX: register a constant-ABSENT baseline and per-state (balanced) accuracy. Add ABSENT cases to the course or label the development result descriptive.

F12 DESIGN_GAP (size, attribution, governance) | INFERRED from draft §2.2 lines 43-56
- Parameter count, assuming 64-d and x = 64-d label + 11 flags:
  | part | parameters |
  |---|---|
  | W_in | 4,800 |
  | W_self / W_down / W_up | 12,288 |
  | ^6 | 16,384 |
  | W_decl (4 fields concatenated, 256->64) | 16,384 (4,096 if summed first) |
  | E_kind | 512 |
  | W_arg | 8,192 |
  | W_txt | 4,096 |
  | node MLP | ~8.4K |
  | edge MLP | ~12.5K |
  | role MLP + E_role | ~8.7K |
  | W_p | 4,096 |
  | W_w | 8,192 |
  | option vectors | ~0.5K |
- Total ≈ 93K-105K, not "~45K". The registered ^6 block is only 16-18%.
- The CAS reading (§2.3) needs attribution evidence. FIX: add controls, registered before the run:
  - ^6 frozen at random init, everything else trained;
  - ^6 replaced by an equal-size MLP or GRU.
  If transfer is the same, "^6 learned" is NOT LICENSED.

F13 FALSE_POSITIVE_RISK (minor) | MEASURED counts + READ draft §2.1 line 31
- World-choice slots list all 64 worlds, so the trainable encoder processes the 5 held worlds as negatives in every trained
  definition (36), context (41) and analogy (36) record: 113 of 358 trained records.
- The encoder therefore gets gradient on held-world graphs, so "never practised" does not strictly hold at the input level.
- FIX: stop gradients through non-focus candidate encodings, or document this as input exposure.

F14 MINOR | MEASURED (m_excerpt.py, m_tok.py)
- role_set is 6-way keyword classification.
- Prefix tokens carry 5-35% of the bag's squared norm. JSON punctuation dominates, and world-id hex tokens are in the vocabulary.
- Learnable, and it transfers at the text surface only. Keep it in the TEXT tier and out of relational claims.

F15 MINOR | MEASURED (m_sched.py)
Optimiser adequacy.
- Batch sizes: 8: 450, 4: 390, 6: 250, 3: 170, 7: 80, 5: 70, 2: 40, 1: 20. Mean 5.56.
- 8,180 presentations over 358 records (about 22.8 each), 19 trained worlds.
- 1,470 AdamW steps at 3e-3 are enough to fit (the old loss was still falling). Under-fitting is not the risk; memorisation is.
- Unused heads keep drifting on stale Adam momentum.
- FIX: no warmup is needed. Add gradient clipping (for example 1.0). Treat weight decay as inactive.

F16 MINOR | READ encoder.py (CUDA-only _device)
The $0 checkpoint probe (§4).
- The frozen encoder is CUDA-only. A "pure-Python local" probe needs a float64 re-derivation through binding.py, which is not the CUDA bytes.
- Its outcome is fixed by the hash design (held world aliases W6/W10/W17/W35/W49, MEASURED, hash to vectors unrelated to training).
- Register the expected value (a constant predictor) before running. Otherwise the result is VACUOUS.

F17 MINOR
- A question counts as right only if every record is right. The pointer machine ignores cue, supports and instruction, so all records of a
  question get identical predictions and the question score equals the record score.
- This makes the gate less strict than for the old machine. Harmless, but state it.

=== RECOMMENDED ARCHITECTURE (with reasons) ===
1. Node input = [1, is_query_whole, is_query_part] for relational kinds; add is_declared_whole / is_participant only for
   definition/context. No labels, no ranks, no primary flags, no kind/function/setting text. (F2, F8; the constant input is needed per F8.)
2. q = E[(kind, rule)] + W_arg(h_whole, h_part) (+ W_txt excerpt for role_set only). (F5)
3. Fixed K message-passing rounds (not the schedule's depth), RMSNorm each round, gated residual; sum pooling. (F4, F7)
4. Distance-based heads for analogy and correspondence; bilinear edge head; logits capped by c*tanh(s/c). (F4, F9)
5. Reach ties: add a ref-ordinal feature for reach only, OR remove tie questions from the gate; report exact-tie decisions. (F6)
6. New learner class + admitted plastic scope (owner-signed) + new counter contract; allow idle-head gradients; run main() end to end
   on the 4070 (smoke only) before any AWS launch. (F3)
7. Study: new-shape held worlds (≤4 nodes for isomorphism kinds); pre-registered pointer-specific baselines (flag constant,
   no-adjacency lookup, rank-identity, twin lookup, constant ABSENT) that define the gate population; ^6 attribution controls. (F1, F2, F11, F12)
Without item 7, even a perfect run cannot license "transfers to new structure". The best it can show is invariance to new label words on shapes it already saw.
```
