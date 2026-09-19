# CNCM pointer machine — design draft v0.1 (for adversarial review, not frozen)

Owner order 2026-09-19 (verbatim): "do option 1, pointer answers plus the checkpoint check BUT EXAMINE THIS TO SEE IF AND HOW IT
OR ANYTHING IN HERE CAN HELP: <PDF>". Option 1 as offered: "Pointer answers + checkpoint check (my recommendation). ... answers by
pointing at a part of the question's own input: 'this node here.' That pointing skill is the same for any world ... The paid run would
be about the same size as this one (about $13, with $45 reserved). The checkpoint check from option 3 runs on the same machine at no
extra cost." Standing owner ruling: "IT MUST BE LEARNING AT THE NEURON LEVEL" — rule-layer gains never count.

## 1. Why the old machine could not transfer (diagnosis to be confirmed by measurement)

- Every question packet holds ALL 64 bank worlds (71 frame lines, 64 of them WORLD lines, ~51 KB). The frozen hash encoder sums
  every line into ONE 64-number vector, so the packet vector is nearly the same for every question; the focus world is ~1/64 of it.
- Each answer slot adds a query vector = hash of (kind, field, group, WORLD ALIAS, node coordinates "W6/N2", symbols). A held-back world
  has world aliases never seen in training (W6, W10, W17, W35, W49), so its slot query vectors are unrelated random vectors.
- Binding permutations depend on line ordinal and token position, so the same fact at a different line gets a different hash.
- Answers are fixed readout rows (N0..N9, W0..W64): "N2" means "the node that sorts third in THIS world", nothing general.
- Prior measurement (records/encoder_capacity_001/BINDING_VARIANTS_RESULT.md §1, §5): "the packet is inert per slot" and "the answer
  is a function of the slot's own name" — a per-name memoriser reads context bits at 98.5926%. That is memorisation by design.

## 2. The pointer machine (new learner; everything else in the pipeline reused)

Interface kept: `predict(packet, depth)`, `stage_batch`, `train_sealed_batch`, checkpoints — same prediction schema: for every slot of
the EXISTING slot plan (`slots.compile_slots`), a logit per declared symbol. So `slots.score_decisions`, `slots.assemble_answer`,
the private checker, `learner._tensor_loss` (including the joint correspondence loss), the seal-before-targets discipline, the holdout
split, the schedule and the gate reader all stay exactly as in the practice study. Only HOW the logits are computed changes.

### 2.1 Input reading (pure, public-only, deterministic; no answer computation)

From the public packet only (never supports, worked answers, instruction or cue — ignored entirely):
- Worlds read: the focus world; the correspondence target world; for world-choice slots (definition kind_ref/function_ref, context
  setting_ref, analogy world_id) every world the slot lists.
- Per node, ONLY its own raw fields: frozen token vector of its label (sum of the frozen encoder's projection rows for the label's
  tokens, unit norm), flags {is declared_whole, is participant, participant rank 1..3, is primary label, primary rank 1..3}, and
  question flags {is the query's `whole` argument, is the query's `part` argument}. NO node alias index, NO degree counts, NO
  derived relation (children, reachability, isomorphism) — those are what must be learned.
- Directed "contains" adjacency (parent -> child) of each read world is given ONLY to message passing, never to a readout head.
- Per world: frozen token vectors of its domain, kind, function and setting declaration text; flag {is the focus world},
  {is the correspondence target}.
- Query: kind (8, learned embedding); for role_set the focal excerpt text as a frozen bag of token vectors (position-free).

### 2.2 Network (all learned weights on GPU; ~45K parameters)

- Node embedding h0 = W_in x (linear).
- World encoder: `depth` (=8, the worker's existing argument) rounds of message passing with SHARED weights (a recurrence, like the
  old 8-pass recurrence): h <- h + ^6( W_self h + W_down sum(parents) + W_up sum(children) ), where ^6 is the registered
  `_DecomposeTransform` (CASformer v0.2, contract cas.cjt.operation.^6.decompose/0.2) used unchanged as the update function.
  World vector g_w = mean of final node states + W_decl (declaration text vectors).
- Question vector q = E_kind[kind] + W_arg (h_whole, h_part if present) + W_txt (excerpt vector, role_set only).
- Pointer heads (every head sees only states, never raw adjacency):
  - node yes/no slots (parts nodes, context participants): 2 logits from MLP[h_v, q].
  - edge yes/no slots (edge_account pairs a->b): 2 logits from MLP[h_a, h_b, q].
  - role yes/no slots (role_set): 2 logits from MLP[q, E_role[r]] (roles are fixed world-independent categories).
  - node-choice slots (definition whole; reach VIA_Nk; correspondence mapping_target): logit(v) = <W_p q_slot, h_v>, where q_slot =
    q (+ h_source for correspondence); fixed options (reach ABSENT/DIRECT, analogy NO_MATCH, correspondence mode) are learned option
    vectors scored against q (and g_F, g_T for the correspondence mode).
  - world-choice slots: logit(w) = <W_w [q; g_F], g_w + flag features>.
- Output = the same {slot_id: {symbol: logit}} the old learner produced.

### 2.3 CAS reading
The world encoder is ^6 Male ("An Idea impregnated with another Idea, the Ideas an Idea is composed of") applied along the "contains"
composition graph — decomposition carried by the registered ^6 operation. No new CAS primitive is claimed; this is an engineering
architecture that reuses the registered ^6 block.

## 3. Study design (reuses the practice study protocol)

- Same course, same frozen holdout (5 twin-free worlds, 127 held records / 50 questions; 79 excluded; 358 trained), same schedule
  (10 passes, 147 updates/pass, 1,470 main + 16 interference + 2 replay), same evaluations (course at passes 0/1/10, held-back at
  2/4/6/8, development panel of ten-node worlds at every checkpoint, retention before/after interference), 3 model seeds
  20260917/18/19, AWS g7.2xlarge, $15 reserved per job, one job at a time.
- Primary gate (unchanged from the practice study, so results are comparable): G_LEARN_p0_to_p10 on the 45 eligible held-back
  questions (5-question input-blind shortcut removed), per seed exact one-sided binomial on discordant questions, b > c, p <= 0.01,
  gains in >= 2 kinds and >= 2 held worlds, all three seeds must pass. Labels: LEARNS_NEW_WORLDS / NO_TRANSFER_TO_NEW_WORLDS / VOID.
- NEW registered secondary flag RELATIONAL_TRANSFER: the same test restricted to the relational kinds (parts, edge_account, reach,
  correspondence, analogy) — kinds whose answer needs relations among input elements, not one input flag. Reported by the program.
- NEW registered per-kind tiering, fixed before the run: DIRECT_READ kinds (definition, context: answer is one input flag or the
  focus marker) / RELATIONAL kinds (above) / TEXT kind (role_set). Any LEARNS_NEW_WORLDS verdict must print the per-tier split so
  a flag-copying win cannot be read as relational reasoning.
- Integrity: I0-I4 re-implemented for this machine (I3 becomes: initial model identity re-derives from the seed).
- Mechanism-free baselines (registered): (a) the same machine untrained (p0) — this is G_LEARN's own baseline; (b) the input-blind
  shortcut; (c) a one-flag rule per DIRECT_READ kind computed from the same input reading (reported, shows which kinds are
  flag-solvable without any learning).

## 4. Checkpoint check (owner-approved)
- $0 half (pure Python, local): cross-world linear probe on the OLD machine's frozen encoder output — fit on trained-world slots,
  test on held-world slots — per kind, vs the published in-world 96.3758% (which was fitted on the same worlds).
- GPU half (inside each AWS job, first phase so a failure is cheap): restore the practice-study checkpoints of the same seed
  (initial, pass_01, final), compute each slot's pre-block ("encoded") and post-block vectors, fit the same trained->held linear probe
  on the GPU, report per kind. And for the pointer machine: the same probe on its node states at initial / pass_01 / final.
  Reported, not gating.

## 5. What the PDF contributes (owner asked)
Adopted: (1) the held-out ladder (p.17) — label our held-out as STRUCTURAL-level transfer (new worlds, new shapes) and the ten-node
development panel as a further structural step; (2) strategy-formation acceptance (p.17-18): "disable learned artifact -> benefit
decreases" — the untrained-machine comparison plus a post-run ablation (reset the trained weights of one component at a time,
report the held-back drop); (3) truth-firewall sensitivity (p.15): relevant-evidence change must be able to change the answer — noted
as the next study (counterfactual held worlds), not in v0.1; invariance tests on node relabelling are VACUOUS for a
permutation-equivariant pointer machine (project law) and are NOT counted as evidence; (4) "Learning leakage — freeze criteria before
the held-out run; same information across controls" (p.32) — already our discipline; (5) evidence classes (p.10): the result is
BOUNDED_SOFTWARE_EVIDENCE-class, never "authenticated". Rejected for this study: the TypeSafe/Jev external model (external
intelligence is not neuron learning; the PDF itself says the contract forbids training on Jev outputs, p.20; project rule against
foreign models); JEV transport/recovery infrastructure (our AWS lifecycle already has create-only evidence and replay).
