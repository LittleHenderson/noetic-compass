# A4 — Seed-18 bounded comparison: unchanged continuation versus one predefined lower learning rate (preregistration, 2026-09-27)

Status: **PREPARED_NOT_ADMITTED_NOT_RUN.** This document fixes the design before any result exists. It authorizes
nothing: no GPU job, no reservation, no launch. Executed serially in the lead session (no worker). Machine-readable
twin: `A4_SEED18_CONDITIONS.json`. Every number below is copied from Codex's committed records on
`origin/codex/helm-cm2x-replication-2-20260926` (tip `b44a3596…`) and is not re-measured here.

## 1. What is protected

- The original seed-18 checkpoints and evidence are never modified. Both arms start from **copies**, hash-verified
  against the recorded manifest before use; the originals stay in the private archive.
- Nothing belonging to the seed-19 continuation (Codex, 20 to 40 passes) is read for decisions, written, or
  interrupted. This preparation does not wait for it and does not compete with it for the one experiment GPU.
- Codex C3's neural-growth files are not touched. The Q4 experiment and its negative result stay intact.
- No local model run, no CPU inference, no automatic sweep.

## 2. Reference run (the "verified clean pass-20 seed-18 checkpoint" comes from here)

| Item | Value (Codex record) |
|---|---|
| Job | `cas-meta2-tpntr-20260926054903-c45f775f-m-20260918` |
| Instance | `i-06e9e0febc3881439`, `g7.2xlarge`, `us-west-2`, launched `2026-09-26T05:57:31Z`, operator ended `2026-09-26T10:54:44.527596+00:00`, exit `0` |
| Scientific source | `c45f775f225dd06cc20cdf313f0a0398486e0d61` (basis `a5fcf527b5f2c47a3a9b1f170977c55371845af0`); package `38761e9595c321eeab09a368a699a993b7db7616c4f2f15fb716dc78a9066119`, manifest `f083fb087ce2eac2394b81856a2aea8f239e7b7d327d27a71160e4dcb6bc2b5d` |
| Optimizer | AdamW, `learning_rate 0.003`, `betas [0.9, 0.999]`, `eps 1e-08`, `weight_decay 0.01`; schedule `CONSTANT_AS_HELM_1_0` (`planned_main_updates null`) |
| Training amount | 20 passes, 147 updates per pass, 2940 main updates (pass 10 = 1470); 2958 optimizer updates in total including 16 interference and 2 replay steps |
| Seeds | model seed `20260918`, `source_seed 101`, `encoder_seed 20260916`; condition `MIXED_SAME_ITEMS`; course `cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987` |
| Public readouts pass 10 → 20 | course 502→487/564; held-back 115→111/127; trained 322→315/358; excluded 65→61/79; development 8→17/59 (`MEASURED_NOT_CERTIFIED`, single seed) |
| Pass-10 checkpoint metadata | `main_checkpoint_1470.json`: cursor 1470, model_revision 1470, `model_state_identity 59a899d848fa0957a1136f02353e2d5d96b15e496e6dd952c00ff71cb4b7266a`, `optimizer_state_identity d3449130ea0453b45599da48a70f17a1d42470d24ab1155cb510ee531fcc6faa`, 4025999 bytes |
| Pass-20 checkpoint candidate | receipt `artifact_manifest.json`: `final.pt` 4025999 bytes sha256 `5a8a306911bbe50b7d65e13227e8d4acfbaac871f2eb2b0ae0c0f5bb1b6e7341` with `final_checkpoint.json` 31598 bytes sha256 `c30ad905b5193cf219c52816e0c40bda294c9ec745564ac6cf3c36bf3d9a6e4b`; also present `prelast.pt` (`8e16f36c…`) and `retained.pt` (`4e66f573…`) |
| Receiver | 128 required artifacts verified, 839 objects, receipt `f85ab054a1441654cc1f33dc6b59d7e3a41db73560df228fa3398deab27a26c2` |

**Open identity question (Codex).** The run made 2958 updates, 18 of them interference and replay steps after the
main course. The metadata that says which `.pt` holds cursor **2940** (main course complete, no interference or
replay step applied) is in the private archive, not in git. Codex names the exact file, size and sha256 of that
state; if `final.pt` is the post-2958 state, the start copy is the pass-20 main-course state instead. Both arms
start from the same named file.

## 3. The two conditions

| Factor | Arm A: unchanged continuation | Arm B: one predefined change |
|---|---|---|
| Start state | copy of the same verified pass-20 seed-18 checkpoint (model, optimizer, encoder, three RNG streams, cursor, revision, counters) | identical copy |
| Scientific source | `c45f775f…`, unchanged | unchanged |
| Architecture, dimensions, learnable names | unchanged (53 learnable tensors as listed in `main_checkpoint_1470.json`) | unchanged |
| Training examples, split, order, holdout, scoring | unchanged; cursor continues from the copy | unchanged |
| Optimizer | AdamW with the checkpoint's moments preserved, `weight_decay 0.01`, `betas [0.9, 0.999]`, `eps 1e-08` | same, moments preserved, **no reset** |
| Learning rate | constant `0.003` (`CONSTANT_AS_HELM_1_0`) | constant **`0.001`** (one third), schedule label stays constant |
| Training amount | +10 passes = +1470 main updates, to pass 30 | identical |
| Interference and replay checks | as in the reference protocol, unchanged | unchanged |
| Best-checkpoint selection | none | none |
| Automatic retries | 0 | 0 |

The single change is the constant learning rate `0.003 → 0.001`. Fixed now, before any result; it will not be
adjusted while watching the development score. Rationale, stated once: the reference's pass 10→20 held-back count
fell by 4/127 while development rose by 9/59, and Codex's source comments record gradient-norm growth at this rate in
an earlier run; a lower constant rate is the smallest single continuation change that does not add a schedule
shape. The source's own warmup-then-cosine option was not chosen because, resumed at cursor 2940, its cosine
position depends on `planned_main_updates` semantics that must be confirmed on the exact `c45f775f` bytes.

An optimizer reset is **not** part of Arm B. If the owner wants a reset, it is a separate third condition, not a
modification of Arm B.

## 4. Predeclared readouts and decision rules

- Endpoints: the same public panels as the reference, at pass 25 (development panel only) and pass 30 (development
  59, held-back 127, course 564, trained 358, excluded 79). Fixed in advance; nothing else is read for a claim.
- Primary comparison: development correct/59 at pass 30, Arm B minus Arm A, each also reported against the shared
  start value 17/59. Secondary: held-back 111/127, course 487/564, trained 315/358, excluded 61/79 deltas.
- Licensed statement, whatever the numbers: "on seed 20260918, continued for 1470 updates from the same pass-20
  state, the `0.001` arm differed from the `0.003` arm by k/59 on the fixed development panel and by the listed
  deltas on the other panels." No improvement, significance, phase-transition, general-learning or CAS claim.
- No selection among checkpoints, panels or subsets after the fact; no second plan change based on the first arm.
- Interference-retention before/after is reported as measured, not as a pass-to-pass comparison.

## 5. Operational finding: both arms need a declared continuation seam (Codex)

Inspected on the archived copy of `pointer_learner.py` from Codex's 2026-09-22 failure-research record
(`records/helm_failure_research_20260922/agents/A2/source_copies/helm2/`, sha256
`21dabd21bb2909ff5990e2b11fd45b75558dce82992c34edfe12f8f556cd5084`), which is **not** the exact `c45f775f` file
(Codex's `GROWTH_RECON.md` gives that file's sha256 as `0f424d86…`; neither archived copy matches it). Read, not run.

- `restore_checkpoint` rebuilds the learner from the checkpoint's own metadata: `optimizer_config=init_args["optimizer_config"]`
  and `limits=init_args["limits"]` (copy lines 2140-2141), after `_validate_init_args` (line 2129) and a
  `TYPED_CHECKPOINT_RUN_IDENTITY` match against an `expected_run_identity_digest`.
- The step learning rate is read each update from `optimizer_config["learning_rate"]` (copy lines 1825, 2006-2008).
- `TYPED_CHECKPOINT_CURSOR` requires `cursor <= limits["max_updates"]`; the pass-10 metadata records
  `max_updates 2956`, `max_wall_seconds 23100`, `max_core_calls 600000`.

Consequences, if the exact `c45f775f` bytes agree: (1) the restore path takes the learning rate from the checkpoint,
so Arm B cannot be expressed as a plain resume with a different argument; (2) continuing past 2958 updates exceeds
the recorded `max_updates`, so **Arm A also** needs the limits raised. Both arms therefore require one declared
continuation seam: a new run identity, a migration record (`init_args.optimizer_config.learning_rate` and
`init_args.limits` old → new, everything else byte-equal), and the untouched original as the rollback target. The
seed-19 continuation (20 to 40 passes) must be solving the same seam now; reusing Codex's seam unchanged for Arm A
keeps the seed-18 arms comparable with seed-19's continuation. The seam is Codex's file scope, not Claude's.

## 6. File scope request and what Claude will write

- Claude writes only under `research/cas_closed_loop_1/claude_lead_20260927/` (this preparation and its records).
- The experimental copies, their admission records (`request.json`, `authority.json`, `owner.json`, `study.json`
  in Codex's `cncm.typed-pointer-*/0.1` schemas) and any continuation seam live in Codex's records tree at a path
  Codex names, for example `records/typed_pointer_001/seed18_continuation_20260927/{armA_unchanged,armB_lr0.001}/`.
  Claude does not write configuration files there and will not write any file another worker writes.
- Requested from Codex: the explicit experimental file scope; the pass-20 state identity (section 2); confirmation
  of the seam on the exact `c45f775f` bytes; the continuation seam's own identity once cut for seed 19.

## 7. Cost and compute, prospective only

The reference measured 17263.692052139 worker seconds for 2940 main updates plus checks. Half the main course per
arm projects to roughly 8600 worker seconds per arm before fixed overhead, about USD 6 per arm at the recorded
`2.52` hourly rate and about USD 12 to 14 for both arms with the reference's ancillary allowance. This is a sizing
estimate from Codex's numbers, not a reservation, forecast record or ledger entry; the canonical ledger
(`campaign_ledger.json`, revision 110, total reserved `899.40` at 2026-09-26T18:36:58Z) is Codex's, and any
reservation follows Codex's `budget.validate_plan` rule. One experiment GPU at a time: these arms run sequentially and
only after the seed-19 continuation has released the GPU.

## 8. Not authorized by this document

A launch; a reservation; a sweep over rates; any change to `c45f775f` scientific source; an optimizer reset;
a 4x/8x extension; CASalescence; any edit to seed-19 or Q4 material.
