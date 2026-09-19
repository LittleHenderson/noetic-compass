# INTERFACE_SPEC_POINTER — the NEW API surface for the pointer build

> Written 2026-09-19 by the orchestrating agent, HEAD `7276f4f2`. This file fixes the names, signatures and return
> schemas of everything the pointer study ADDS. It deliberately does not restate shared APIs: those are already
> pinned with `file:line` anchors in `INTERFACE_SPEC_SHARED.md` and `INTERFACE_SPEC_PIPELINE.md`, which this file
> references and must not contradict.
>
> Purpose: so that several builders can work in parallel against a fixed surface, and so that design v0.2 can
> reference one place instead of restating it.
>
> **Open items are marked `OPEN:` at the point of use.** They are decisions waiting on the two adversarial reviews
> (leaks/shortcuts; per-kind learnability). Everything not marked OPEN is decided.

## 0. Roots, imports, interpreters

- CNCM root: the `FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE` directory inside
  `_worktrees/vision-next/cas_only_reasoner/`.
- Every pure module starts with the same import block the practice modules use:
  ```python
  import sys; from pathlib import Path
  CNCM = Path(__file__).resolve().parents[N]          # resolve to the CNCM root
  sys.path[:0] = [str(CNCM), str(CNCM / "research" / "CAS_META_2_COMPOSITION")]
  ```
- **Two interpreters, never interchangeable** (measured 2026-09-19):
  - pure tests: the **system** Python (`python -m pytest`, pytest 9.0.2) from the CNCM root — **89 passed in 328.56 s**
    at HEAD `52fea7ed` is the baseline that must not regress;
  - anything importing torch on a device: `~/venvs/cas-gpu/Scripts/python.exe` (torch 2.11.0+cu128, CUDA on the
    RTX 4070, 8,188 MiB). The system Python's torch raises `Torch not compiled with CUDA enabled`.
- Windows: write files with the Write tool or `write_bytes`. `Path.write_text` emits CRLF and the repo is `eol=lf`;
  a CRLF `.py` fails the AWS package build with `INPUT_NOT_COMMITTED`.

## 1. `cas_meta2/typed_teaching/pointer_contract.py` (pure, no torch)

A near-copy of `practice_contract.py` (250 lines) with these differences:

| Name | Value / rule |
|---|---|
| `CANDIDATE` | `"CNCM_TYPED_POINTER_LEARNING_001"` |
| `CONFIG_SCHEMA` | `"cncm.typed-pointer-worker-config/0.1"` |
| `JOB_PATTERN` | `r"cas-meta2-tpntr-\d{14}-([a-f0-9]{8})-m-(20260917\|20260918\|20260919)"` |
| study token | `tpntr` — **verified 2026-09-19**: the bucket is exactly **63** characters, which is the maximum the regex `[a-z0-9][a-z0-9-]{1,61}[a-z0-9]` allows. A 6-character token gives 64 and is rejected. |
| `CHECKPOINT_PINS` | load or inline the constants in `pre_design/contract_pins/checkpoint_pins.json` — 18 files, **15,259,777 bytes**, all nine sidecar sha256 values verified against the real bytes |
| `MATERIAL` | `deepcopy(practice.MATERIAL)` **plus** the 18 checkpoint rows. Keys are CNCM-root-relative and carry exactly `bytes` + `sha256`. Without these the launcher rejects the files (`PRACTICE_SOURCE_MEMBER_SCOPE`, review RK5). |
| `input_inventory(root)` | wrapper: `practice.input_inventory(root)` plus the 18 checkpoint rows, sorted by path, re-checked against `INPUT_TOTAL_BOUND` (≤ 2000 rows, ≤ 96 MiB) |
| `TIERS` | `DIRECT_READ = ("definition", "context")`; `RELATIONAL = ("parts", "edge_account", "reach", "correspondence", "analogy")`; `TEXT = ("role_set",)` |
| `RELATIONAL_POPULATION` | `OPEN:` the frozen, per-question list after the registered removals. Verified inputs: 45 eligible questions = 10 DIRECT_READ + **29 RELATIONAL** + 6 `role_set`. The 29 is split by KIND as correspondence 5, edge_account 5, reach 9, analogy 5, parts 5, and split by HELD WORLD as **relational only** — `world-98c6352d` 6, `world-28f61f2d` 5, `world-6e1fcbda` 6, `world-22704554` 5, `world-4090ec49` 7, summing to 29 (source: `pipeline_review/r4_reach_lexical.py`, line `relational eligible per world`). Do not confuse these with the ALL-KIND per-world counts 8 / 9 / 10 / 9 / 9, which sum to 45 (source: `measurements/leaks_review/lk1_answer_carriers_out.txt` line 12, `eligible by world`). Known removals: FP2 flag rule solves **3 of 5** eligible held `parts`; DG3 node-order dependence covers **2 of 9** eligible held `reach`. **Lens A has additionally measured that the input's own adjacency solves `parts` 5/5 and `edge_account` 5/5 with no learned weights (`lk1_answer_carriers_out.txt` lines 58-66), which is a wider leak than FP2 — see `REVIEW_SYNTHESIS.md` §1.** WAITING on lens A for the complete removal list. |
| `MIN_PASSING_B` | smallest `b` with `2**-b <= 0.01` at `c = 0` → **7** (`2**-7 = 0.0078125`). State it in the protocol and re-derive it in a test. |
| `DESIGN` | new. Must NOT inherit `practice_contract.DESIGN` wholesale (review DG10): that dict carries `"registered_learner_unchanged": True` and old-machine work counts (`planned_slot_core_passes` 124510). Keep the `_INHERITED` keys that are genuinely machine-independent; replace `purpose`, the work formula, and add the pointer fields. |
| `expected_main_delta(stats)` | `OPEN:` the pointer machine's own counter key set. `typed_practice_worker.py:361` compares canonical bytes of summed per-update deltas, and `counter_delta` requires the two snapshots' key sets to match exactly — an extra or missing counter key fails `MAIN_TRAINING_COUNTERS` **after the spend**. The learner's `counters` dict and this function must be derived from one shared source of truth. |
| `parse_job`, `make_config`, `validate_config` | same shapes as practice, with the new schema/CANDIDATE |

Reused **unchanged by import**, never re-derived (the hold-out must stay byte-identical to the practice study):
`split`, `held_back_questions`, `practice_schedule`, `interference_batches`, `retention_packets`,
`development_packets`, `load_material`, `public_packets`. Test P1 pins their digests:
held `668e6ce73c426d1fcf8f2391e1a08d90c045ffb37fba95fc64e2658f5369ab1d`,
excluded `b82108e14554a9fe746a7cfcb1e2cb181a99a3019dc39a3596805f10934c2621`,
batches `daf95831dd6f054f0395e9a868c513650982bd1912247adc698ca067433bc857`.

## 2. `cas_meta2/typed_teaching/pointer_inputs.py` (pure, no torch)

The public-only reader. Pure, deterministic, digestible. **Never reads** `supports`, `cue`, `instruction`, or any
answer; never computes a target.

```python
def label_cache(root) -> dict            # built ONCE; pinned digest; avoids the 0.0111-0.0254 s/call
                                         # tokenizer rebuild (tokenization.py:151). 230 distinct labels, 244 nodes.
def read_packet(packet) -> dict          # the whole per-record input, no answers
def input_digest(reading) -> str         # sha256 over the canonical reading
def slot_readings(reading, slots) -> list[dict]   # one entry per slot of the EXISTING slot plan
```

`read_packet` returns, per record:

| Key | Content |
|---|---|
| `focus_world` | the focus world read as a graph: nodes with their own raw flags, directed `contains` adjacency |
| `worlds` | `{world_id: graph}` for the focus world, the correspondence target, and every world a world-choice slot lists |
| `query` | `kind` (8-way learned id), `rule` (learned id — review DG2: swapping the reach rule changes 11 answers), the argument node ids where present |
| `node_flags` | per node: `is_declared_whole`, `is_participant` + rank 1..3, `is_primary_label` + rank 1..3, `is_whole_argument`, `is_part_argument`, `rank` among the world's sorted node refs |
| `excerpt` | `role_set` only: frozen bag of token ids, position-free |

Decisions already taken:
- **The node rank feature IS included** (resolves DG3). Rationale: without it the machine trains on contradictory
  targets for the order-dependent reach questions, and those questions are answerable only by that order. A
  **rank-only, no-learning baseline is registered** and the questions it solves are removed from the gate population.
- **`OPEN:` whether node LABEL words survive at all.** Lens B is measuring whether held-world labels occur in
  training; the outgoing agent recommends dropping them (no rule uses them, and they add a memorisation channel).
  Do not finalise this line until lens B reports.

## 3. `cas_meta2/typed_teaching/pointer_learner.py` (torch only when called)

`class PointerCourseLearner` — a NEW class. It must NOT subclass into the shared learner's scope checks.

- `self.module` is **ONE container** holding every learned weight, the registered `^6` block included. Never call
  `scope_parameters` on it (`graph_teaching/trainer.py:86-87` freezes every non-`^6` weight).
- Required methods, matching the shared contract so the worker's helpers keep working: `__init__`, `predict`,
  `stage_batch`, `train_sealed_batch`, `export_checkpoint`, `restore_checkpoint`, `profile`.
- Own `profile()` — `restore_checkpoint` compares the module-level `profile()` (`learner.py:336`) over a transitive
  list of **22 files**; a new class must ship its own.
- Own `train_sealed_batch`: the shared one requires a finite gradient on **every** parameter of `self.module`
  (`learner.py:271`) while `stage_batch` zeroes with `set_to_none=True` (`learner.py:185`), so any per-kind head a
  batch did not touch dies immediately (review RK1, measured: `role_set` absent from 1,150 of 1,470 batches). The
  replacement requires finiteness only on parameters that actually received a gradient, requires **at least one**,
  and registers that AdamW skips both the update and the weight decay for `None`-gradient parameters.
- Attributes the worker reads: `torch`, `module`, `optimizer`, `encoder` (the frozen typed encoder, kept so
  `base._state` / `_check_state` / `export_state` keep working), `counters`, `cursor`, `model_revision`, `failed`,
  `run_identity_digest`.
- Borrow `TypedCourseLearner._tensor_loss` by calling it, so the joint correspondence loss is unchanged.
- The `^6` block comes from `cncm.typed_matched_worker._framework(torch, device, seed)` (`:43-48`), built FIRST.
- **`OPEN:` the exact head set** — it follows from the input list, so lens B's expressivity table decides it.
  Fixed already: K = 8 shared message-passing rounds regardless of the batch's `depth` (DG1); RMS-normalise each
  round (DG7); dense adjacency matmuls and one-hot matmuls, never embedding lookups, under
  `torch.use_deterministic_algorithms(True)` (RK7).

## 4. `cncm/typed_pointer_worker.py`

Adapted from `typed_practice_worker.py` (454 lines). Reuse `_publish`, `_move_in`, `_append`, `_train_logged`,
`_evaluate`, `_split_score`, and `base._ProgressWriter`, `_state`, `_check_state`, `_partial_checkpoint`,
`_score_seal`. Own `EXPECTED_ARTIFACTS` (< 500 names, unique, `required_count == len + 3`).

Phase order is fixed and load-bearing:

```
preflight → packets → checkpoint check PHASE A → seed + double build → 10 passes with evaluations
→ retention/interference → reloads/replays → checkpoint check PHASE B → ablations → source verification → deliver
```

- **PHASE A must finish before the pointer model is seeded** (review M3): restoring an old checkpoint overwrites all
  three RNG streams (`learner.py:358-362`) with no save/restore. Phase A restores the three checkpoints, extracts
  and seals **public vectors only**, and never reads an answer.
- **PHASE B runs last** (review FP3): deriving answers before training would breach the registered custody rule
  (`practice_contract.py:11-12`).
- The checkpoint-check artifact is always written with a `status` field of `COMPLETE` or `FAILED` inside, and every
  module it needs is imported at start-up outside any `try` (review RK6: a missing artifact or a poisoned
  `attestor.snapshot()` turns a "reported" check into a failed job after the money is spent).
- The `^6` identity check digests **the three `^6` tensors only** — `model_state_identity` digests the whole
  `module.state_dict()` (`learner.py:111`, `:306`) so a container can never equal it (see FINDINGS.md in
  `measurements/framework_probe/`). This check is **in-job on AWS only**: a local build reproduces the practice
  weights to within **7.450580596923828e-09** but not byte-exactly, and `state_identity` is a byte-exact hash.
- Windows refusal happens **before** any numeric import so the test P8 ordering holds.

## 5. `research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py`

Copy `typed_practice_launch.py` and change: the five schema constants, `WORKER_NAME`, `CANDIDATE`,
`CONFIG_SCHEMA`, `JOB_PATTERN`; `_probe()` → `cncm.typed_pointer_worker` keeping the four-constant check;
`EXPERIMENT`; `BOUNDS`; `worker_config`; the request/authority/owner validators including the three bindings;
`bootstrap_source()` → `typed_pointer_worker` keeping the `count == 2` check; `render_worker()` with its own module
globals (it cannot be inherited); `evidence_contract()` with the new probe and `required_count == len+3`;
`reservation_plan_for` with a new `task_scope`; and `git_package_bytes` admitting the 18 checkpoint paths through
the new `MATERIAL`. `PACKAGING_SOURCES` must add `"aws/typed_pointer_launch.py"`.

Two traps recorded by the pipeline spec:
- the reservation **caller** passes the candidate module's amount (`"7.00"`) while the study records `"15.00"`;
  changing one without the other fails every launch at `PRACTICE_RESERVATION_CALLER` before the reservation;
- the new worker's FAILED status must be added to `failure_statuses`, or a failed job is read as `REMOTE_FINISHED`
  and collection then demands an artifact manifest a failed worker cannot have produced.

## 6. `records/typed_pointer_001/evaluate_gates.py`

A copy of the practice reader with a new I1 (the new worker's `SUCCESS_STATUS` and `EXPECTED_ARTIFACTS`) and a new
I3 (the DG4 in-job checks recorded for the reader). **The printed label IS the claim status** — never prose.

- Primary label keyed on the **RELATIONAL** tier, per the owner's 2026-09-19 confirmation.
- `LEARNS_NEW_WORLDS` requires: per seed, exact one-sided binomial on discordant question pairs with `b > c` and
  `p <= 0.01`; gains in ≥ 2 kinds and ≥ 2 held worlds; **all three seeds**; computed over `RELATIONAL_POPULATION`.
- The all-kinds result is reported as a flag, never as the label.
- A test must show that a flag-copy-only outcome (b=10, c=0 over definition+context) receives **no** label.

## 7. Drivers — `records/typed_pointer_001/{prepare_study.py, execute_study.py, preflight_dry_run.py, holdout_audit.py}`

Adapted from the practice versions (108 / 50 / 282 / 79 lines). Every job's `owner.json` carries the owner's words
verbatim, including the three decisions of 2026-09-19. `prepare_study.py` writes
`admission_001/{study.json, 2026091X/{request,authority,owner}.json}`; that freeze is committed and pushed BEFORE
the first launch. `execute_study.py` runs one job at a time and stops on the first failure with an explicit
`stop_unless`, never `assert` (`python -O` strips asserts from a spend path).

## 8. Test map — `tests/test_typed_pointer_study.py`

Self-contained `sys.path` block at the top (the other tests rely on side effects). Pure, no torch, numeric-import
guard. P1 holdout/schedule digests · P2 bucket length for every seed · P3 the 18 pins within bounds · P4
restore-identity freeze for all 9 checkpoints · P5 package dry run (`typed_pointer_worker`, archive ≤ 24 MiB) · P6
launcher overrides · P7 `EXPECTED_ARTIFACTS` unique, < 500, `required_count == len + 3` · P8 Windows refusal before
any numeric import · P9 input reader purity/determinism/cache equality · P10 inputs exclude supports/cue/instruction
and include the reach rule · P11 planned-work formula vs the real schedule · P12 flag-copy-only gets no label ·
P13 frozen flag-rule/rank-rule baselines and removal lists · P14 custody ordering.
