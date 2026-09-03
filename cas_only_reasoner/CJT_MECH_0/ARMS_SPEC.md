# CJT-MECH-0 -- ARMS, TRAINING, EVALUATION AND FILE CONTRACT (build spec v0.1, 2026-09-03)

Binding for every builder of this bench. World contract: `frw1/world.py` (`OBS_DIM = 110`,
`N_ACTIONS = 14`, `K = 6`, slot layout in `Env.obs()`), ceiling: `frw1/solver.py`.
Design authority: `../CJT_OHM_CLEANROOM/CJT_MECH_0_DESIGN_v0_2.md`. Authorization:
`OWNER_AUTHORIZATION_20260903_BUILD_AND_RUN.md`.

## 0. Files (flat names; every module the remote entrypoint imports must be in this list)

```
frw1/world.py            world family, Env, dataset, digests            (done)
frw1/solver.py           ExactSolver, BeliefTracker (M8 ceiling, K1)   (done)
frw1/policies.py         mechanism-free fixed policies MF + run_policy   (builder A)
gates_world.py           K1 K2 K3 K4 K9 K10 K11 + receipts               (builder A)
gates_structure.py       K5 K6 K7 K8 + receipts                         (builder B)
arms.py                  M0..M7, M9 (torch), param counting, absorption helpers   (builder C)
run_cjt_mech0.py         remote entrypoint: GPU_REQUIRED, train all arms x seeds, learning
                         curves, dev-transfer eval, protected eval (one use), raw flush, receipt  (builder C)
status_program.py        frozen status law: raw results + PREREG.json -> statuses            (builder C)
PREREG.json              frozen constants, seeds, thresholds, digests                        (builder C, frozen before launch)
launch_cjt_mech0.py      AWS launcher, copied from CMB_RP0_v0_1/launch_cmb_rp0.py pattern     (builder D)
receipts/                gate receipts (JSON), one per gate, PASS/FAIL/INSTRUMENT_INVALID
```

Rules for all builders: numpy + stdlib for everything except `arms.py` / `run_cjt_mech0.py`
(torch). No torch on local CPU for training; `run_cjt_mech0.py` starts with a fail-closed
`GPU_REQUIRED` check. Local CPU is permitted for the gates, the dataset, the solver, and for
*constructing* torch modules to count parameters (no training, no inference loop). Every gate
script contains its own positive and negative control in the same code path and emits
`PASS / FAIL / INSTRUMENT_INVALID` plus a JSON receipt with exact numbers.

## 1. Splits (from `build_dataset(registry_seed=20260903, n_train_worlds=20, n_heldout_worlds=2, split_seed=424242)`)

```
train         train_episodes            (20 worlds x [6 singles + 7 pairs] = 260)      -- training distribution
dev-transfer  heldout_episodes restricted to the 20 training worlds AND |F| == 2         -- held-out PAIRS on known worlds; used for learning curves during development
protected     heldout_episodes with |F| == 3 on training worlds, PLUS every episode on
              the 2 held-out worlds                                                       -- ONE USE, opened only by run_cjt_mech0.py's final stage
twin          twin_episodes                                                               -- negative-control world (structureless)
```

Identity assertion (K6): no (world_id, F) pair is shared between train and any other split;
observation arrays of the first 50 train and first 50 protected episodes are pairwise non-identical.

## 2. Shared input encoding (identical for every arm; part of every arm's parameter count)

```
slot k  (17 numbers from Env.obs, k = 0..5)  ->  e_k = relu(W_s z_k + b_s),   W_s: 17 -> 16   (shared across k)
globals (8 numbers)                           ->  g   = relu(W_g z_g + b_g),   W_g: 8 -> 8
```

## 3. Arms

All practical arms output logits over the 14 actions; the policy is softmax over those logits.
`GRUCell(in, h)` is `torch.nn.GRUCell`. Module hidden size `H_MOD` and generic hidden size
`H_GEN` are chosen by builder C so that every practical arm's trainable parameter count is within
2 percent of M1's (K7 reports the exact counts; pad with an unused-but-trained linear layer if
needed and say so in the receipt).

```
MF   mechanism-free fixed policies (frw1/policies.py): majority action; cheapest-probe-then-fix;
     fix-in-cost-order-blind; react-to-codes (fix the class named by the last PREREQ code, else
     the class whose fix just failed's parent); random. K1 adds the exact-enumeration fixed policies.
M0   FLAT:      MLP  concat(e_0..e_5, g) -> 64 -> 14   (no recurrence; hidden reset every tick)
M1   GENERIC:   GRUCell(104, H_GEN) over ticks on concat(e_0..e_5, g) -> Linear(H_GEN, 14)     THE BAR
M2   ANON:      6 x GRUCell(24, H_MOD); module j reads concat(e_pi(j), g), pi a fixed random
                non-identity permutation drawn once from seed 777; concat hiddens -> Linear(6*H_MOD, 14)
M2b  ALT-TAX:   as M2 but module j reads the slot with the j-th cheapest probe cost in the
                current world (ties by index) -- a sensible non-cause taxonomy, world-dependent
M3   ROUTED:    6 x GRUCell(24, H_MOD); module j reads concat(sum_k softmax(A_j)_k e_k, g) with
                A a learned 6x6 logit matrix (36 extra params); concat hiddens -> Linear(6*H_MOD, 14)
M4   CJT:       6 x GRUCell(24, H_MOD); module k reads concat(e_k, g)  (EVIDENCE PORT: aligned);
                module k's hidden -> Linear(H_MOD, 2) = logits for [probe(k), fix(k)]  (OUTPUT CONTRACT);
                mean of hiddens -> Linear(H_MOD, 2) = logits for [execute, abstain];
                the 14 logits are assembled in action order and softmaxed jointly (uniform routing)
M5   CJT+alpha: M4 plus the CAS-Ohm law with NO learned parameter:
                V_k = u * budget_frac + w * [last verdict in {off_axis, opposite}] + [o_k != CLEAR]
                R_k = (c_k + d_k) / 10 + lambda * min(n_k, 3) + R_floor
                rho_k = [o_k != CLEAR];  m_k = mask_k;  i_k = m_k * rho_k * V_k / R_k;  I = sum_k i_k
                alpha_k = i_k / I if I > 0 else NO_READY_CJT
                module k's two logits += log(alpha_k + 1e-6);  if NO_READY_CJT: all module logits = -1e9
                constants: u = 1.0, w = 1.0, lambda = 0.5, R_floor = 0.1  (frozen in PREREG.json)
M6   +I_total:  M5 plus a compute knob: per tick the module GRUCells run n_t refinement steps on the
                same input, n_t = 1 + round(2 * min(I, I_ref) / I_ref) in {1,2,3}, I_ref = 6 * (1 + 1 + 1) / (0.3 + R_floor)
                (the value of I when every class is unknown, pressure maximal, costs minimal).
                Its matched control is M5 run at a FIXED 2 refinement steps (report both).
M7   +typed diagnosis: M6 plus private delivery: the fields e_k, e_named_k and the last verdict are
                zeroed in every module's input EXCEPT the module whose class was acted on last
                (execute / abstain deliver the verdict to no module but to the global head);
                and the temporal law: after a verified intended verdict all n_k are treated as 0 in R_k.
M8   EXACT:     frw1/solver.py ExactSolver + BeliefTracker (ceiling for policy quality; not learned)
M9   ORACLE:    M1 with the true fault set one-hot (6 numbers) appended to the globals (ceiling only)
```

Mechanism-swap (evaluation-time only, M4-M7): rewire module k to read slot pi(k) for the
fixed non-identity pi of M2; report the damage; it is a mechanism-use check, never evidence of value.

## 4. Training (identical for every arm)

```
algorithm       REINFORCE with a per-arm moving-average baseline (beta 0.9), entropy bonus 0.01,
                Adam lr 3e-3, gradient clip 1.0, batch 64 episodes, reward 1 on verified success
episodes        TOTAL_EPISODES = 30000 per arm per seed (batches of 64 drawn uniformly from train)
seeds           5: [11, 23, 47, 61, 89]   (arm init + episode sampling; the world dataset is fixed)
curve           every 1000 episodes: evaluate (greedy argmax policy) on ALL train episodes and ALL
                dev-transfer episodes; record success rate, next_tick_recovery, probes, wrong actions,
                violations, budget spent, mean ticks
twin            every arm also trained and evaluated on the twin split (5000 episodes) for K10 / the
                negative control
protected       ONLY after the whole sweep: the final checkpoint of every arm x seed evaluated once
                on the protected split; results written to a separate file PROTECTED_RESULTS.json
examples-to-    first curve checkpoint at which train success >= 0.9 * M8 train success for that seed
threshold       (M8 train success is computed by the harness with the solver); None if never reached
```

Raw results file `CJT_MECH0_RAW.json` is flushed after every arm x seed (the launcher syncs it to
S3 every 3 minutes). Receipt `CJT_MECH0_RECEIPT.json` with the compute block (gpu, cuda, torch,
capability, pythonhashseed, peak_vram_bytes, wall_s), dataset digests, arm parameter counts, and
`determinism.content_hash`.

## 5. Status program (`status_program.py`, frozen thresholds in `PREREG.json`)

Per sub-question, paired by seed (5 pairs), on the protected split unless stated:

```
CONTROLS   POSITIVE: M9 protected success - M0 protected success >= 0.15  (else INSTRUMENT_INVALID)
           NEGATIVE: twin split: max - min success over M0..M7 < 0.03   (else INSTRUMENT_INVALID)
           HELD-OUT IDENTITY: K6 receipt PASS                            (else INSTRUMENT_INVALID)
           MF FLOOR: best MF protected success is the floor; any practical arm below floor + 0.02
                     has NO RESULT on any sub-question
Q-PORTS    SUPPORTED iff M4 beats M1 AND M2 AND M3 by >= 0.05 mean paired success on protected
           AND on dev-transfer, with at least 4 of 5 seeds positive against each
           REFUTED iff M4 - max(M1, M2, M3) <= 0 on protected;  else INCONCLUSIVE
Q-SPEC     M4 vs M2b by the same rule (SUPPORTED means the aligned grouping beats the cost-tier grouping)
Q-ALPHA    M5 vs M4 and M5 vs M3, same rule
Q-ITOTAL   M6 vs M5-at-2-steps, same rule
Q-DIAG     M7 vs M6, same rule
Q-HEADROOM headroom = M8 protected success - best practical arm; report; "no headroom" iff < 0.03
Q-SAMPLE   examples-to-threshold ratio M4 / M1 (median over seeds); SUPPORTED iff <= 0.7 with 4 of 5 seeds < 1
Compound   MECHANISM_BINDING_VALUE   Q-PORTS SUPPORTED and headroom >= 0.03
           SENSIBLE_FACTORIZATION_VALUE_NOT_CAS   Q-PORTS SUPPORTED and Q-SPEC not SUPPORTED
           CAS_OHM_ROUTING_VALUE / CAS_OHM_COMPUTE_VALUE / TYPED_DIAGNOSIS_VALUE   the matching Q SUPPORTED
           NO_MECHANISM_VALUE   Q-PORTS REFUTED or INCONCLUSIVE
```

No OR-join anywhere; every compound status names the exact sub-question results it requires.
The program prints every number it used.
