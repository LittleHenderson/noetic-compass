# CJT-MECH-0 -- Mechanism-Anchored Neural CJT Cell. FULL DESIGN v0.2 (DOCUMENTATION ONLY)

```
Status            DESIGN.  Owner approved the QUESTION (goal set 2026-09-02: "approved, resume the
                  ledger verification then design CJT-MECH-0").  NOT AUTHORIZED TO BUILD.  $0.
                  No world code, no arms, no GPU, no AWS, no training exist for this design.
Supersedes        CJT_MECH_0_DESIGN_BRIEF_v0_1.md section-by-section (the question is unchanged)
Next gate         adversarial design review (must be allowed to return DO_NOT_BUILD), then an
                  owner-signed record before any $0 construction begins
Depends on        CJT_OHM_STATE_OF_EVIDENCE.md, CJT_OHM_CLAIM_LEDGER.json, p6/P6_RESOLUTION.md
```

Plain English: this document says exactly what world the bench would use, what each competing
controller is, what "type governs mechanism" means in code, how CAS-Ohm enters, what numbers would
be read, what status words the program could emit, and what would kill the bench for free before
any neural spend. Every design choice names the recorded death it exists to avoid.

---

## 1. The question (unchanged from v0.1, owner-approved)

> Does a mechanism-bound recurrent CJT controller reach verified next-tick recovery with fewer
> examples, fewer wrong actions and better transfer to unseen fault combinations than matched
> generic recurrent controllers, in a partially observed world where diagnostic probes cost budget,
> repair actions are state-dependent and non-commutative, and the gold outcome is produced by the
> environment and a verifier rather than by a type-to-repair table?

Two things this design does NOT test, deliberately: verifier-gated plasticity and retention
(objective O5; a later bench), and the transformer substrate (O8; the possibility document). This
bench is a small recurrent controller over a synthetic-but-not-authored world family.

## 2. Design principles, each tied to a recorded death

| principle | the death it prevents (ledger id) |
|---|---|
| Type is a **port, a contract, a law and an authority**, never a name or an index | EX1 nameplate (`EX1-01/02`), D0 relabelling (`D0-01/02`), S0 order index (`S0-08`) |
| The **optimal policy must not be a closed form**; probes cost, faults hide, actions do not commute | D1 trivial repair (`D1-01`) |
| The **world family is registered and drawn**, never authored to match an arm; the same draws serve every arm | S0 world-generator-as-status-dial (`S0-14`, `GOV-09`) |
| **Held-out is asserted held out** by array comparison; every table carries a **capacity-matched mechanism-free baseline** | P6 (`CR-P6-02..05`) |
| **CAS-Ohm is a control law** with independently grounded `V` and `R`; nothing generates weights | additive identity (`OHM0R-01`), `V/R` non-identifiability (`OHM0R-02/03`) |
| **Equal information for every practical arm**; the oracle is a ceiling, not a competitor; no repair table anywhere | fairness rule (`GOV-04/05`), D1 requirement 4 (`D0-16`) |
| A **matched non-CAS factorization** is an arm from day one, and the existing Gate-1A "S7" must not be reused for it (it is a relabelling of CAS) | CAS-specificity frontier (`SHEET-13/14`), `RC0-16` |
| **Status by program** from raw results, frozen thresholds and controls; sub-questions never OR-joined; failed control = no verdict | P6 status-by-prose (`CR-P6-06`), eta-epsilon goal substitution (`ETAEPS-14`) |
| **Epsilon is typed** (`R_floor`), collisions are exact under the implemented equation | D0 side channel (`D0-12`, `S0-11`) |
| Every number has a script, a digest, raw output and a receipt; no chat-only number | the whole record (`CR-REC-*`) |

## 3. The world family: FAULT-RECOVERY WORLD `FRW-1`

### 3.1 What an episode is

A task is being attempted by a machine that cannot see why it is stuck. Between one and three
hidden **faults** are active. The controller has a **budget**. Each tick it may **probe** one field
(pay to see whether a fault of that class is active), **fix** one class (pay to attempt a repair),
**execute** (attempt the task; the verifier answers), or **abstain**. Success is a verified
`intended` Effect within budget. The score that matters is whether the controller recovers on the
tick after it first learns something from the verifier.

### 3.2 Registry, instance, and what is drawn

- **Cause registry** (fixed, 8 classes): `GOAL_UNCLEAR`, `KNOWLEDGE_MISSING`, `RESOURCE_SHORT`,
  `POLICY_CLOSED`, `MEMORY_STALE`, `TOOL_BROKEN`, `CONTEXT_MISMATCH`, `PREREQ_UNMET`. Names are for
  humans; every controller sees only class ids `0..7` and their per-instance metadata.
- **World instance** (drawn per training world, seed-registered): `K = 6` active classes drawn from
  the 8; per-class probe cost `c_k` and fix cost `d_k` drawn from registered ranges; a **prerequisite
  DAG** over the 6 classes drawn from a registry of admissible DAGs (at least 3 edges, acyclic; e.g.
  a fix of class `b` is effective only after class `a` is clear if `a -> b`); a **collision hash**
  for the tick-0 activation (see 3.3).
- **Episode** (drawn per episode): the active fault set `F` (1-3 classes), the budget
  `B = round(0.6 * sum_k c_k + min_k d_k)` so that probing everything is unaffordable.
- **Held-out split**: training episodes use all singletons and a registered half of the pairs;
  the protected split uses the other half of the pairs and all triples, plus two DAGs never seen
  in training. Train and held-out draws come from separate seed streams and are **asserted
  non-identical by array comparison before any number is read** (the P6 law).

### 3.3 Observation model -- collisions by construction

At tick 0 every arm sees the same activation vector `a_0`: a fixed function of the **number** of
active faults and the collision hash, so that every fault set of the same size in the same world is
indistinguishable at tick 0. Under the implemented equation these collisions are **bit-identical**
(integer-valued activation; no epsilon anywhere in the observation path). A reader that only has
`a_0` therefore cannot do better than chance over fault sets of equal size; this is the
information-limited floor and it is reported as such.

Every observation slot `k` carries: provenance class id `k`, probe result `o_k in {UNKNOWN, CLEAR,
FAULT}`, probe cost `c_k`, fix cost `d_k`, policy mask `m_k in {0,1}` (1 = fixing class `k` is
allowed now), failure count `n_k` (fixes of class `k` that failed so far), last typed failure code
`e_k` (see 3.4). Global fields: budget left, tick index, last verifier verdict. **Every arm receives
the identical slot vectors.** The mask `m_k` is environment metadata, visible to all.

### 3.4 Actions, non-commutativity, verifier

| action | cost | effect |
|---|---|---|
| `probe(k)` | `c_k` | reveals `o_k` |
| `fix(k)` | `d_k` | if `k in F` and every DAG prerequisite of `k` is clear: removes `k` from `F`; if `k in F` but a prerequisite is unmet: no change, `n_k += 1`, typed failure code `e_k = PREREQ(a)` naming one unmet prerequisite class `a`; if `k not in F`: no change, `n_k += 1`, `e_k = NOT_A_FAULT`; if `m_k = 0`: **policy violation** counted, no change |
| `execute` | 1 | verifier returns `intended` if `F` is empty, `off_axis` if `F` is non-empty and `POLICY_CLOSED` is not in `F`, `opposite` if `POLICY_CLOSED in F` (an unauthorized attempt), never the hidden set |
| `abstain` | 0 | ends the episode with `unassessed` |

Order matters: fixing `b` before `a` when `a -> b` wastes `d_b` and reveals only a prerequisite
code; fixing `a` first makes the later `fix(b)` succeed. Probing before fixing saves wasted fixes.
Executing before all faults are cleared costs a tick and reveals only a coarse verdict. Executing
under a closed policy is a violation.

The verifier is an environment function of the hidden state. It never returns the hidden set. It is
identical for every arm. Its verdict is an observation, not a training label.

### 3.5 Why no closed form reaches the ceiling (to be PROVED at $0, not assumed)

With varying costs, an unknown DAG and an unaffordable full probe, the value-optimal policy depends
on the belief over `F` given probe results and failure codes. Gate K1 (section 7) computes the
exact optimal policy per instance by enumeration (the state space is small: 2^6 fault sets x probe
knowledge x budget) and checks that **no fixed probe order + fixed fix order** reaches it within a
registered margin on the dev split. If one does, the world is D1 again and the design returns
`DO_NOT_BUILD`.

## 4. Arms -- every practical arm gets the same slots, the same actions, the same budget, the same mask, matched parameters (within 2 percent) and the same optimizer, steps and seeds

Shared encoder: each slot `k` is embedded by the same small MLP into `z_k`; globals into `z_g`.
What differs is **who may read which `z_k`, who may emit which action, and what law routes them**.

```
MF   MECHANISM-FREE BASELINES   majority action; "probe cheapest unknown, then fix in cost order, then
                                execute"; linear and tree readers on the concatenated slots
M0   FLAT GENERIC               MLP on [z_0..z_5, z_g] -> action logits
M1   GENERIC RECURRENT          GRU over ticks on the same input -> action logits   (THE BAR)
M2   ANONYMOUS MODULAR          6 module-GRUs; module j reads slot pi(j) for a fixed random pi
                                drawn once; module outputs pooled -> action logits
M2b  ALTERNATIVE TAXONOMY       6 module-GRUs grouped by a different sensible rule (slots grouped
                                by cost tier), same capacity                       (CAS-SPECIFICITY CONTROL)
M3   LEARNED-ROUTING MODULAR    6 module-GRUs, each reads all slots, learned softmax gate
M4   CJT WITHOUT CAS-OHM        module k reads slot k only (EVIDENCE PORT) plus z_g; module k may
                                emit only {probe(k), fix(k)} proposals (OUTPUT CONTRACT); a global
                                head emits {execute, abstain}; uniform routing; module k alone
                                reads e_k and n_k (MEMORY PORT)
M5   M4 + CAS-OHM alpha         routing by i_k = m_k * rho_k * V_k / R_k  (section 5)
M6   M5 + I_total               I_total sets how many proposals may be enacted this tick
                                (1, 2 or 3 actions) -- the compute knob
M7   M6 + typed diagnosis and   the verifier verdict and typed failure codes are delivered ONLY to
     next-tick feedback         the module whose class was last acted on; that module's R_k is
                                updated by the temporal law (section 5); no other module sees them
M8   MODEL-BASED SEARCH         exact belief-state search on the known world model (ceiling for
                                policy quality; not learned; the bar for "is there headroom")
M9   FULL-STATE ORACLE          sees F; ceiling only; never a competitor
```

Mechanism-swap test (the causal test that replaces label-shuffle): train M4-M7 once, freeze, then
at evaluation rewire module `k` to read slot `pi(k)` for a non-identity `pi`. Damage is expected
and is a **mechanism-use check only**; it proves nothing about value (owner ruling, `D0-16`).

What the CAS arm gets that M1 does not: **sparsity of evidence access aligned to the world's
causal factorization, an output contract, a memory port and a temporal law**. What it does NOT get:
any table from class to correct action; the environment's action ids are visible to all arms
equally. If M2 (misaligned ports) or M2b (differently grouped ports) matches M4-M7, the value is not
in the alignment; if M1 matches, the value is not in the ports at all.

## 5. CAS-Ohm as a control law inside M5-M7 (no learned parameter in the law)

```
V_k   drive / pressure on class k     = u * (budget_left / B) + w * [last verdict was off_axis or opposite]
                                        + (1 - o_k_is_CLEAR)          -- goal pressure, verifier demand, unknown-ness
R_k   effective resistance of class k = (c_k + d_k) / c_max + n_k * lambda + R_floor
rho_k readiness                       = 1 if o_k != CLEAR else 0     (a cleared class is not ready for repair)
m_k   hard mask                       = policy mask from the environment (exact 0 or 1)
i_k   = m_k * rho_k * V_k / R_k
I_total = sum_k i_k
alpha_k = i_k / I_total               if I_total > 0, else the typed state NO_READY_CJT (M5-M7 emit
                                        {execute, abstain} only)
```

`u, w, lambda, R_floor` are registered constants, not learned. `R_floor` is the typed denominator
floor; collisions are checked for bit-identity under this implemented equation (Gate K5). The
generic arms receive `c_k, d_k, n_k, m_k, o_k`, the budget and the verdict as inputs, so they can
learn any routing they like; the law only fixes the CJT arms' routing shape. The temporal law in
M7: after a typed failure code on class `k`, `R_k` rises by `lambda`; after a verified `intended`,
all `R_k` reset -- delivered only to the module that acted (the type-bound memory port).

Separate sub-questions, separate statuses, never OR-joined:

```
Q-PORTS     M4 vs M1, M2, M2b, M3      does aligned typed structure help at all, and is it the alignment
Q-ALPHA     M5 vs M4 and vs M3          does the V/R routing law beat uniform and learned routing
Q-ITOTAL    M6 vs M5 at matched MEAN actions per episode
Q-DIAG      M7 vs M6                    does typed delivery of verdicts and failure codes help
Q-HEADROOM  best practical arm vs M8    is there anything left to win
```

## 6. Outcomes and the status program

Primary outcomes (all on the protected split, one use): verified next-tick recovery rate; wrong-action
rate; probes per episode; budget spent; steps to recovery; held-out fault-combination transfer
(recovery on unseen pairs and triples); **examples to threshold** (training episodes needed to reach
90 percent of the M8 ceiling on the dev split, read from the learning curve); policy violations;
trace fidelity (does the arm's own routing trace name the classes it actually probed and fixed).
Repair-label accuracy is logged and is not a primary outcome (`D1-18`).

Controls, in the same code path as the measurement:
- POSITIVE: M9 and M8 beat M0 by at least the registered margin on the dev split; otherwise the
  world is unreadable -> `INSTRUMENT_INVALID`.
- NEGATIVE: a **structureless twin** world (no DAG, probes free, faults visible at tick 0) where all
  practical arms must tie within the registered spread; otherwise the harness manufactures
  differences -> `INSTRUMENT_INVALID`.
- HELD-OUT IDENTITY: train and protected draws asserted non-identical -> else `INSTRUMENT_INVALID`.
- MECHANISM-FREE: every table shows MF; any practical arm that fails to beat the best MF by the
  registered margin has no result to report.

Per sub-question the frozen program emits exactly one of `SUPPORTED / REFUTED / INCONCLUSIVE /
INSTRUMENT_INVALID`, from: paired-by-seed differences over at least 5 seeds, registered absolute
margins, a registered paired test, and the controls. Candidate margins (to be frozen at
preregistration, not here): recovery `+0.05`, examples-to-threshold ratio `<= 0.7`, transfer gap
`+0.05`, negative-control spread `< 0.03`. Compound statuses the program may emit for the whole
bench, each requiring specific sub-question results and none reachable by OR:

```
MECHANISM_BINDING_VALUE          Q-PORTS SUPPORTED against M1 AND M2 AND M3, with Q-HEADROOM showing headroom
SENSIBLE_FACTORIZATION_VALUE     Q-PORTS SUPPORTED against M1, M2, M3 but NOT against M2b  (typing helps; CAS does not)
CAS_OHM_ROUTING_VALUE            Q-ALPHA SUPPORTED     (separately; never folded into the line above)
CAS_OHM_COMPUTE_VALUE            Q-ITOTAL SUPPORTED
TYPED_DIAGNOSIS_VALUE            Q-DIAG SUPPORTED
NO_MECHANISM_VALUE               Q-PORTS REFUTED or INCONCLUSIVE
INSTRUMENT_INVALID               any control failed
```

No status word stronger than `SUPPORTED_NARROWLY` enters the ledger without a different-family or
human replication.

## 7. Zero-cost kill gates, run BEFORE any neural arm exists (any failure -> DO_NOT_BUILD)

```
K1  CLOSED-FORM CHECK      exact optimal policy by enumeration vs every fixed probe/fix order on the dev
                           split; a fixed order within the registered margin of optimal kills the bench (D1)
K2  CHEAP READERS          linear, tree, kNN on concatenated slots at tick 0 and after one probe;
                           majority action; must sit far below the M8 ceiling on recovery
K3  SHORTCUTS              candidate identity, construction order, episode index, cost ordering,
                           any metadata that predicts F above chance -> kill
K4  GRAPH SHORTCUTS        one-hop and two-hop rules over (probe result -> fix) must not reach the ceiling
K5  EPSILON / COLLISIONS   tick-0 activations of equal-size fault sets bit-identical under the
                           implemented equation; V/R routing with R_floor leaks no ordering of F
K6  HELD-OUT IDENTITY      train vs protected arrays non-identical; no episode shared
K7  CAPACITY MATCH         trainable parameters of M0-M7 within 2 percent; report the exact counts
K8  ABSORPTION             untrained M4: all 719 non-identity port permutations x signed parameter
                           permutations must NOT reproduce the function; M2 (random pi) must be
                           absorbed by construction -> proves the test can see absorption
K9  WORLD-FAMILY DIAL      re-draw the world family with a different registry seed and a different
                           DAG registry; the ranking of MF vs M8 must be stable; the generator has no
                           knob that selects which practical arm wins (tested by running K1-K4 on 3 draws)
K10 STRUCTURELESS TWIN     the negative-control world exists and M8 == MF there (nothing to learn)
K11 MECHANISM-FREE FLOOR   the best MF policy is registered in the status program as the floor
```

Each gate is a deterministic script with its own positive and negative control in the same file,
emits `PASS / FAIL / INSTRUMENT_INVALID`, and writes a receipt. Local CPU is allowed for these:
they are dataset generation and small enumeration, not neural work.

## 8. Audit and governance plan

1. This design goes to an **adversarial design review** with at least five lenses (answer key and
   shortcut; fairness and capacity; statistics and status law; world-generator dial; CAS-specificity
   and matched taxonomy). The review must be free to return `DO_NOT_BUILD`.
2. A **preregistration** freezes: world registry and seeds, arms and parameter counts, constants
   `u, w, lambda, R_floor`, margins, paired test, controls, the status program, the protected split
   digests, the cost ceiling, and the auditor. Its digest is signed into the owner's phase record.
3. **Auditor named before any run**: different model family (DeepSeek R1 or Llama via Bedrock for
   language-only audits) or a human; Claude and GLM recused where they built or authored.
4. **Protected split one use**; the status program, not prose, reads it.
5. Every run: receipt with instance, region, container digest, code and data digests, seeds,
   wall-clock, cost estimate and actual.

## 9. Compute plan

- `$0`: world generator, gates K1-K11, absorption test, structureless twin, MF baselines -- local
  CPU control-plane work, each script under five minutes.
- Neural arms: AWS GPU only (g4dn.xlarge T4 is enough for GRUs of this size), all arms and seeds
  as separate jobs from one container digest, auto-terminating, hard ceiling to be set by the owner
  (candidate `USD 10` for the dev sweep, `USD 5` for the single protected evaluation).
- Nothing runs on local CPU that trains a neural arm.

## 10. What each outcome would and would not license

- `MECHANISM_BINDING_VALUE`: a typed, aligned, contract-bound controller learns this world family
  faster and transfers better than matched generic controllers. It would NOT license "CAS is
  right"; that needs M2b to lose as well and, later, a real language substrate.
- `SENSIBLE_FACTORIZATION_VALUE`: structure helps, the CAS grouping is not special. Honest and
  useful; it redirects the program toward O7.
- `CAS_OHM_ROUTING_VALUE` / `CAS_OHM_COMPUTE_VALUE` / `TYPED_DIAGNOSIS_VALUE`: each stands alone.
- `NO_MECHANISM_VALUE`: the stop criterion for the CAS-Ohm performance lane in this world family
  (owner handoff section 14), with CAS-Ohm kept as telemetry and governance.

## 11. What could still be wrong with this design (for the reviewers)

- The cause registry and the DAG registry are still written by the builder; K9 tests robustness to
  re-draws but cannot prove the family is not tuned toward typed arms.
- M4's output contract ("module k may propose only probe(k) and fix(k)") may be the answer key in
  disguise; the reviewers must decide whether it exceeds what the fairness rule allows, and whether
  M2 and M2b are the right neutralizers.
- The V/R law's constants are registered, not learned; a badly chosen `lambda` could sink M5-M7
  for reasons that have nothing to do with the law's shape.
- Examples-to-threshold on a learning curve is sensitive to the optimizer; matched optimizer and
  seeds reduce but do not remove that.
- A small GRU may saturate the world so that every arm reaches the ceiling; then only
  examples-to-threshold carries information, and the margins must be set for it.

## 12. Owner decisions requested (nothing else is)

1. Accept this design for adversarial review, or return it.
2. After review: authorize or refuse the `$0` construction of the world family and gates K1-K11.
3. Name the auditor for the neural phase now.

```
Design status   v0.2 -- awaiting adversarial review and owner ruling
Build status    NOT AUTHORIZED
Spend           $0
```
