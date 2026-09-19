# INTERFACE SPEC — pipeline and lifecycle contract for the pointer machine

**Purpose.** This document is the extraction contract for the CNCM pointer study. It names every
function, constant, code and file position a builder needs in order to write
`cncm/typed_pointer_worker.py`, `aws/typed_pointer_launch.py`, `records/typed_pointer_001/*.py`,
`cas_meta2/typed_teaching/pointer_contract.py`, `pointer_inputs.py`, `pointer_learner.py` and
`tests/test_typed_pointer_study.py` **without reading the whole tree again**. It exists so those
builders can satisfy RK1–RK10, FP1–FP3 and DG1–DG10 of
`records/typed_pointer_001/pre_design/DESIGN_REVIEW_PIPELINE_LENS.md` (the "review" below).

**Produced by static reading only.** No torch, no GPU, no network, no AWS call, no execution of any
project module. $0. Nothing existing was edited.

**Frozen point of reference.** Branch `codex/cncm-vision-next`, HEAD `52fea7ed`. Every `file:line`
below is a line number in that revision as read by the file reader (1-based, counting every physical
line). Where a line range is given it is inclusive of both ends.

**Path conventions.** `CNCM` =
`<WN>\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE`, where
`<WN>` = `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE
COGNITIVE MACHINE\_worktrees\vision-next`. Every relative path below is relative to `CNCM`. The
git worktree root (the directory the repository is committed from) is `<WN>`; the git prefix inside
the repository is `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/`
(`research/CAS_META_2_COMPOSITION/aws/graph_training_curriculum_launch.py:34`).

**One deliberate notation.** `require(cond, "CODE")` below always means the module-local helper in
force for that file. It is `ValueError` subclass or `ValueError` — never an `assert` — because
`python -O` strips asserts (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:374`). The prefix of
the raised message is part of the contract:
`worker_contract.require` raises `ValueError("TYPED_WORKER:" + reason)` (`worker_contract.py:62-64`);
`matched_contract.require` raises `ValueError("TYPED_MATCHED:" + reason)` (`matched_contract.py:58-60`),
and **the practice worker inherits the `TYPED_MATCHED:` prefix** because
`practice_contract.py:71` binds `canonical, require = matched.canonical, matched.require` and
`typed_practice_worker.py:58` binds them again from `practice_contract`.

---

# A. `cncm/typed_practice_worker.py` — the file to adapt

495 lines. Header docstring 1–23 (the eight deliberate differences from `typed_matched_worker`).
Module imports 24–34. Constants 36–58.

## A.0 Module constants (verbatim)

| Name | Line | Value / definition |
|---|---|---|
| `CANDIDATE` | 36 | `contract.CANDIDATE` = `"CNCM_TYPED_PRACTICE_LEARNING_001"` (`practice_contract.py:33`) |
| `CONFIG_SCHEMA` | 37 | `contract.CONFIG_SCHEMA` = `"cncm.typed-practice-worker-config/0.1"` (`practice_contract.py:34`) |
| `RESULT_SCHEMA` | 38 | `"cncm.typed-practice-worker-result/0.1"` |
| `FAILURE_SCHEMA` | 39 | `"cncm.typed-practice-failure/0.1"` |
| `SUCCESS_STATUS` | 40 | `"COMPLETE_TYPED_PRACTICE_ARM"` |
| `BOUNDARY` | 41 | `contract.DESIGN["boundary"]` (string, `practice_contract.py:214-217`) |
| `PASSES` | 42 | `contract.PASSES` = `10` (`practice_contract.py:39`) |
| `CHECKPOINTS` | 43 | `contract.PASS_CHECKPOINTS` = `(0, 1, 2, 4, 6, 8, 10)` (`:57`) |
| `FULL` | 44 | `contract.FULL_COURSE_CHECKPOINTS` = `(0, 1, 10)` (`:58`) |
| `HELD_ONLY` | 45 | `tuple(n for n in CHECKPOINTS if n not in FULL)` = `(2, 4, 6, 8)` |
| `CHECKPOINT_NAMES` | 46 | `("initial", "pass_01", "prelast", "final", "retained")` |
| `EVALUATIONS` | 47–48 | `("course_p00","course_p01","course_p10") + ("heldback_p02","heldback_p04","heldback_p06","heldback_p08") + ("development_p00","development_p01","development_p02","development_p04","development_p06","development_p08","development_p10") + ("retention_before","retention_after")` — **16 names** |
| `EXPECTED_ARTIFACTS` | 49–57 | see A.3 — **80 names** (verified against the delivered manifest, 80 entries) |
| `canonical`, `require` | 58 | `contract.canonical`, `contract.require` (= matched's) |

## A.1 The full `run()` phase skeleton, in order

Signature, line 213:

```python
def run(config, root, results, artifacts, attestor=None):
```

`started = time.monotonic()` is line 214 and is the single clock every deadline in this worker and
every `started=` argument to a shared helper is measured from.

| # | Lines | Phase name emitted | What happens |
|---|---|---|---|
| 0 | 215 | — | `root, results, artifacts = Path(...).resolve()` for all three |
| 1 | 216 | — | `config = contract.validate_config(config, root)` — rebuilds the whole config from the live tree and requires canonical identity (`practice_contract.py:243-250`, `CONFIG_FIELDS`, `CONFIG_IDENTITY`) |
| 2 | 217 | — | `frozen, tokenizer, development = contract.load_material(root)` (pure) |
| 3 | 219–220 | — | `require(not artifacts.exists() and artifacts.parent == results and not (results/"result.json").exists(), "FRESH_RESULT_DIRECTORY")` — **before any directory is made** |
| 4 | 221–222 | — | `results.mkdir(parents=True, exist_ok=True)`; `artifacts.mkdir()` |
| 5 | 223–225 | — | `staging = results.parent / "practice_staging"`; `require(not staging.exists(), "FRESH_STAGING_DIRECTORY")`; `staging.mkdir()` — **the staging directory is a sibling of `results/`, outside it**, so the create-only publisher never sees a growing file |
| 6 | 226–235 | — | `report` dict built with schema `"cncm.typed-practice-worker-report/0.1"` and fields `candidate, job, source_sha, inputs, design, condition, model_seed, boundary, learning_on_held_back_established, phase`; `main, progress = None, None`; `work = []`; inner `def phase(name, **values)` sets `report["phase"] = name` and returns `progress.emit(name, **values)`. **`phase()` must not be called before line 238** because `progress` is `None` until then |
| 7 | 238 | — | `progress = base._ProgressWriter(results, started)` (creates `results/evidence/`) |
| 8 | 239 | `preflight` | `phase("preflight")` |
| 9 | 240 | — | `os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"` — **must precede the CUDA context**: deterministic cuBLAS otherwise refuses matrix ops on this runtime (comment at 328–329 of the base worker) |
| 10 | 241–242 | — | `from cas_meta2.teaching_cycle.gpu_adapter import _cuda`; `torch, device = _cuda()`. **This is the Windows refusal point** (A.5) |
| 11 | 243 | — | `torch.cuda.reset_peak_memory_stats(device)` |
| 12 | 244–247 | — | `require(attestor is not None and callable(getattr(attestor,"snapshot",None)), "SOURCE_ATTESTOR_REQUIRED")`; `loaded_before = attestor.snapshot()`; `from .rpa_learning_worker import verify_worker_packages`; `packages_before = verify_worker_packages(root)` |
| 13 | 248–251 | — | `report["runtime"] = {"device", "torch_version", "cuda_version", "gpu_name"}`; `require(torch_version == "2.11.0+cu128" and cuda_version == "12.8" and "RTX PRO 4500" in gpu_name, "RUNTIME_MISMATCH")` |
| 14 | 252–254 | — | `torch.use_deterministic_algorithms(True)`; `torch.backends.cuda.matmul.allow_tf32 = False`; `torch.backends.cudnn.allow_tf32 = False` |
| 15 | 256–279 | `public_packet_preparation` | `packets = dict(contract.public_packets(frozen))`; `held, trained, excluded = contract.split(frozen)`; `require(held == design["held_back_record_ids"] and excluded == design["excluded_record_ids"], "HOLDOUT_IDENTITY")`; `held_set/trained_set/excluded_set`; `held_worlds = set(contract.held_worlds(frozen))`; `held_packets`; `development_packets = contract.development_packets(development)`; `retention_packets = dict(contract.retention_packets(frozen))`; `retention_held`; `batches, stats = contract.practice_schedule(frozen)`; `require(canonical(stats) == canonical(design["schedule"]), "PRACTICE_SCHEDULE_IDENTITY")`; `require(all(key in trained_set for b in batches for key in b["record_ids"]), "UNTRAINABLE_IN_TRAINING")`; `interference = contract.interference_batches(frozen)`; `require(..., "UNTRAINABLE_IN_INTERFERENCE")`; `representatives = base._representatives(packets)`; publish `protocol_material.json` (273–279) |
| 16 | 281–292 | `fresh_initialization` | `from ...encoder import build_frozen_typed_encoder`; `from ...practice_learner import PracticeCourseLearner`; `updates_total = stats["main_updates"] + contract.INTERFERENCE_UPDATES` (= 1486); construct `main` with `matched._framework(torch, device, design["model_seed"])`, the frozen encoder, `optimizer_config=design["optimizer_config"]`, `run_context={"run_id","course_sha256","condition","source_seed"}`, `limits={"max_updates": updates_total, "max_core_calls": contract.MAX_CORE_CALLS, "max_wall_seconds": contract.WORKER_DEADLINE_SECONDS}`, `device=device`; `report["initial_model_identity"] = main.run_identity["initial_model_identity"]` |
| 17 | 293–300 | — | `checkpoint_pins, predictions = {}, {}`; inner `def checkpoint(name)` → `phase(name + "_checkpoint", completed_updates=main.cursor)`, `pin = main.export_checkpoint(staging / (name + ".pt"))`, `_move_in(...)` into `artifacts`, record `checkpoint_pins[name] = {**pin, "path": str(artifacts/(name+".pt"))}`, publish `<name>_checkpoint.json` |
| 18 | 302 | `initial_checkpoint` | `checkpoint("initial")` |
| 19 | 303–305 | `initial_encoding` | `encoding = {"initial": base._encoding_checks(torch, main.encoder, packets, representatives, started=time.monotonic(), all_packets=True, progress=phase, phase="initial_encoding")}`; `_deadline(started)` |
| 20 | 306–307 | — | `report["scores"], report["development_scores"] = {}, []`; `sides = {"held_back": held_set, "trained": trained_set, "excluded": excluded_set}` |
| 21 | 309–324 | — | inner `def evaluate_at(number)`: if `number in FULL` → `"course_p%02d"` over all `packets` and `report["scores"][name] = {"correct","total", **_split_score(scored, sides)}`; else `"heldback_p%02d"` over `held_packets` with a nested `"held_back"` split; then always `"development_p%02d"` over `development_packets`, appended to `report["development_scores"]` as `{"pass","cursor","correct","total"}` |
| 22 | 326 | `course_p00_*`, `development_p00_*` | `evaluate_at(0)` |
| 23 | 327–358 | `main_training` | the ten-pass loop, below |
| 24 | 359 | — | `require(main.cursor == stats["main_updates"] and not any(staging.iterdir()), "PRACTICE_MAIN_INCOMPLETE")` |
| 25 | 360–362 | — | `report["main_training_delta"] = matched._sum_deltas(main_deltas)`; **`require(canonical(report["main_training_delta"]) == canonical(expected_main_delta(stats)), "MAIN_TRAINING_COUNTERS")` (line 361)**; `work.append({"phase":"main_training","delta":...})` |
| 26 | 363–364 | — | `require(checkpoint_pins["initial"]["metadata"]["model_state_identity"] != checkpoint_pins["final"]["metadata"]["model_state_identity"], "TRAINABLE_CORE_UNCHANGED")` |
| 27 | 366–368 | `retention_before` | `retention_sides = {"held_world": retention_held, "trained_world": set(retention_packets) - retention_held}`; first `_evaluate` of `retention_packets` |
| 28 | 369–384 | `interference_training` | 16 batches from `interference` (each with `cursor=None`), logged by `_train_logged` into `interference_batches.jsonl`/`interference_updates.jsonl`, then `_move_in` both | 
| 29 | 381–383 | — | `require(report["interference_delta"]["optimizer_updates"] == contract.INTERFERENCE_UPDATES and report["interference_delta"]["prediction_calls"] == contract.INTERFERENCE_UPDATES * contract.INTERFERENCE_BATCH, "INTERFERENCE_COUNTS")` (16 and 128) |
| 30 | 385 | `retained_checkpoint` | `checkpoint("retained")` |
| 31 | 386–392 | `retention_after` | second `_evaluate` of `retention_packets`; `report["retention_scores"] = {"before": {correct,total}, "after": {correct,total}, "before_by_side", "after_by_side", "starting_competence_met": 2*before["correct"] >= before["total"]}` |
| 32 | 393–396 | `final_encoding` | `encoding["final"] = base._encoding_checks(..., all_packets=False, phase="final_encoding")`; `_deadline(started)`; publish `encoding_checks.json` |
| 33 | 398–420 | `<name>_reconstruction` | reloads for `(("initial","course_p00"), ("final", "course_p10"), ("retained", None))` — see A.8 |
| 34 | 421–446 | `replay_1`, `replay_2` | the two replay branches from `prelast` — see A.8 |
| 35 | 447–448 | — | publish `replay_report.json` = `{"reloads","replays","boundary": "Same-process same-worker reconstruction only."}` |
| 36 | 449–456 | — | `totals = matched._sum_deltas([row["delta"] for row in work])`; `expected_updates = stats["main_updates"] + contract.INTERFERENCE_UPDATES + contract.REPLAY_UPDATES` (= 1488); `require(totals["optimizer_updates"] == totals["backward_calls"] == expected_updates, "GLOBAL_UPDATE_COUNTS")`; `report["global_actual_work"] = {"phases": work, "totals", "historical_restored_counters_counted_again": False, "main_presentations", "interference_presentations", "encoder_main_counters"}` |
| 37 | 457–462 | `final_source_verification` | `require(canonical(contract.input_inventory(root)) == canonical(config["inputs"]), "SOURCES_CHANGED")`; `packages_after = verify_worker_packages(root)`; `require(packages_before["source_files"] == packages_after["source_files"], "WHEEL_SOURCES_CHANGED")`; publish `installed_sources.json`, `loaded_sources.json` (`{"before": loaded_before, "after": attestor.snapshot()}`) |
| 38 | 463–467 | — | `_deadline(started)`; `report.update(status=SUCCESS_STATUS, checkpoint_reload_verified=True, peak_cuda_allocated_bytes, peak_cuda_reserved_bytes, elapsed_seconds)` |
| 39 | 468–469 | `delivery` | `phase("delivery", main_updates=..., global_updates=...)`; `return deliver(results, artifacts, report, failed=False)` |
| 40 | 470–495 | `failed/<phase>` | the failure path, below |

### The main pass loop, lines 329–358 (one iteration = one pass)

```
329  for number in range(1, PASSES + 1):
330-332  names = ("pass_%02d_batches.jsonl", "pass_%02d_updates.jsonl") % number
         batches_log, updates_log = staging / names[0], staging / names[1]
         both created with .touch(exist_ok=False)
333      losses, gradients = [], []
334      for batch in (b for b in batches if b["pass"] == number):
335-336      if batch["cursor"] == stats["main_updates"] - 1: checkpoint("prelast")   # cursor 1469
337          before = deepcopy(main.counters)
338-339      last_seal, update = _train_logged(main, batch, packets, staging, batches_log, updates_log, started=started)
340          main_deltas.append(base.counter_delta(main.counters, before))
341          losses.append(update["raw_batch_loss"]); gradients.append(update["gradient_squared_norm"])
342          report["completed_main_updates"] = main.cursor
343-345      if main.cursor % 10 == 0: phase("main_training", completed_main_updates=main.cursor,
                                        total_main_updates=stats["main_updates"], current_pass=number)
346-347  _move_in(batches_log, artifacts / names[0]); _move_in(updates_log, artifacts / names[1])
348-350  report["pass_summaries"].append({"pass","updates","cursor_end","mean_raw_batch_loss",
                                    "first_raw_batch_loss","last_raw_batch_loss","mean_gradient_squared_norm"})
351-352  if number < PASSES: base._partial_checkpoint(main, results, main.cursor)
353-354  if number == 1: checkpoint("pass_01")
355-356  if number == PASSES: checkpoint("final")
357-358  if number in CHECKPOINTS: evaluate_at(number)
```

Two properties the pointer worker must keep: `last_seal` is the raw byte string of the last sealed
batch (used by the replay check at 432), and the checkpoints are taken **between** the update that
lands on the checkpoint cursor and the next update, so `final` is taken at `cursor == 1470` and
`prelast` at `cursor == 1469`.

### The failure path, lines 470–495

1. Salvage: every file left in `staging` with `st_size > 0` is moved into `artifacts` under
   `"failed_" + leftover.name` (473–479); a salvage error is recorded, never re-raised
   (480–481, `report["staging_salvage_failure"]`).
2. `report.update(status="TYPED_PRACTICE_FAILED", elapsed_seconds=..., failure={"schema": FAILURE_SCHEMA, "type": type(error).__name__, "detail": str(error)[:1000]}, completed_work_phases=work)` (483–485).
3. `report["partial_main"] = {"cursor","model_revision","counters","learner_failed"}` if `main` exists (486–488).
4. `progress.emit("failed/" + report["phase"], completed_updates=0 if main is None else main.cursor)` inside
   its own `try` (489–493).
5. `deliver(results, artifacts, report, failed=True)` (494) then **`raise`** (495).

## A.2 The reusable helpers — exact signatures and semantics

All in `cncm/typed_practice_worker.py` unless marked `base.` (= `cncm/typed_course_worker.py`).

### `_deadline(started)` — 61–62
`require(time.monotonic() - started < contract.WORKER_DEADLINE_SECONDS, "PRACTICE_DEADLINE_EXCEEDED")`.
12,300 s (`practice_contract.py:64`). Called between every unit of work (144, 305, 395, 401, 422, 463)
and always handed `started` — never a fresh clock — so the whole job is bounded.

### `_publish_bytes(path, raw)` — 65–76 — **create-only and whole**
```python
def _publish_bytes(path, raw):
```
* requires `type(raw) is bytes and not path.exists() and not path.is_symlink() and not partial.exists()` → `"PUBLISH_DESTINATION"`;
* writes `<name>.partial` with `open("xb")`, `write`, `flush`, `os.fsync(stream.fileno())`;
* re-checks the destination is still absent → `"PUBLISH_DESTINATION"`;
* `os.replace(partial, path)`;
* `require(path.read_bytes() == raw, "PUBLISH_READBACK")`;
* returns `{"name": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}`.

This is the write-then-rename pattern the whole study rests on: the live publisher uploads each new
name under `results/` exactly once, create-only, and skips only `*.partial`/`*.tmp`
(`records/typed_practice_001/preflight_dry_run.py:185`); a file that grew after its first upload
fails the final upload with `EVIDENCE_DIGEST_CONFLICT`
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:113-114`).

### `_publish(path, value)` — 79–80
`return _publish_bytes(path, canonical(value))`. `canonical` appends `b"\n"` and sorts keys
(`worker_contract.py:67-69`).

### `_move_in(staged, path)` — 83–90 — create-only
```python
def _move_in(staged, path):
```
`require(staged.is_file() and not staged.is_symlink() and not path.exists(), "MOVE_IN_DESTINATION")`;
`raw = staged.read_bytes()`; `os.replace(staged, path)`; `require(path.read_bytes() == raw, "MOVE_IN_READBACK")`;
same return shape as `_publish_bytes`. Used for every large file that grew in staging (pass logs,
`.pt` checkpoints, replay seals, salvaged failures).

### `_seal_predictions(path, predictions, *, phase, expected_ids)` — 93–96
`require([p["record_id"] for p in predictions] == expected_ids, "PREDICTION_REGISTRY_ORDER")`, then
publishes `{"schema": "cncm.typed-course-prediction-seal/0.1", "phase": phase, "predictions": predictions}`.

### `_append(path, raw)` — 99–104 — staging only, never `results/`
```python
def _append(path, raw):
```
`require(type(raw) is bytes and raw.endswith(b"\n") and raw.count(b"\n") == 1 and not Path(path).is_symlink(), "APPEND_LINE")`;
`open("ab")`, `write`, `flush`, `os.fsync`. One complete JSON line per call — the requirement is a
single canonical line, so a JSONL log stays record-aligned and a torn write cannot produce a partial
line that parses.

### `_stage_and_train(learner, batch, packets, seal_path, *, started)` — 107–122
```python
def _stage_and_train(learner, batch, packets, seal_path, *, started):
```
1. `_deadline(started)`;
2. `require(batch["cursor"] in (None, learner.cursor), "PRACTICE_BATCH_CURSOR")` — the practice
   schedule's cursors are `0..1469` but the interference batches carry `cursor=None`, hence the tuple;
3. `selected = [packets[key] for key in batch["record_ids"]]`;
4. `staged = learner.stage_batch(selected, batch["depth"], cursor=learner.cursor, occurrence_ids=batch["occurrence_ids"])`;
5. `pin = base._write_bytes(seal_path, staged["bytes"])` — **create-only, fsync, readback**
   (`typed_course_worker.py:40-48`, codes `OUTPUT_BYTES`, `OUTPUT_READBACK`);
6. `require(pin["sha256"] == staged["sha256"], "STAGED_SEAL_DIGEST")`;
7. `from cas_meta2.typed_teaching import checker` (line 116) — **the custody boundary**, see A.9;
8. `targets = [checker.derive_target(p["source"], p["record"]["query"]) for p in selected]`;
9. `update = learner.train_sealed_batch(seal_path, expected_sha256=pin["sha256"], target_receipts=targets)`;
10. `require(update["gradient_squared_norm"] > 0, "ZERO_TRAINING_GRADIENT")`;
11. `update["correction_identities"] = [{"record_id": key, "target_digest": target["target_digest"]} for key, target in zip(batch["record_ids"], targets)]`;
12. returns `(staged["bytes"], update)`.

### `_train_logged(learner, batch, packets, staging, batches_log, updates_log, *, started)` — 125–133
```python
def _train_logged(learner, batch, packets, staging, batches_log, updates_log, *, started):
```
`seal_path = staging / "seal.json"`; `require(not seal_path.exists(), "STAGING_SEAL_EXISTS")`;
`raw, update = _stage_and_train(...)`; `_append(batches_log, raw)`; `_append(updates_log, canonical(update))`;
`seal_path.unlink()`; returns `(raw, update)`. The single reusable seal path in staging is why this is
serialised — one update at a time, never concurrent.

### `_evaluate(learner, packets, phase_name, artifacts, *, started, progress, work)` — 136–160
```python
def _evaluate(learner, packets, phase_name, artifacts, *, started, progress, work):
```
Returns `(by_record_id, scored)` where `by_record_id = {row["record_id"]: row for row in rows}`.
1. `_deadline(started)`;
2. `state = base._state(learner.torch, learner)`; `counters = deepcopy(learner.counters)`;
3. `progress(phase_name + "_predictions", completed_packets=0, total_packets=len(packets))`;
4. `for packet in packets.values(): _deadline(started); rows.append(learner.predict(packet, 8))` with a
   progress emit every 50 rows and at the end — **depth 8 for every evaluation**;
5. `path = artifacts / (phase_name + "_predictions.json")`; `pin = _seal_predictions(path, rows, phase=phase_name, expected_ids=list(packets))`;
6. `scored = base._score_seal(path, pin, packets, started=time.monotonic(), progress=progress)` — the
   shared scorer's own deadline is the *matched* study's, so it is handed a **fresh** clock and this
   worker's deadline is re-checked immediately after (153);
7. `scored["boundary"] = BOUNDARY`; publish `<phase>_scoring.json`;
8. `require(state == base._state(learner.torch, learner), "EVALUATION_CHANGED_LEARNED_STATE")`;
9. `delta = base.counter_delta(learner.counters, counters)`; `require(delta["optimizer_updates"] == delta["backward_calls"] == 0, "EVALUATION_UPDATED_MODEL")`;
10. `work.append({"phase": phase_name, "delta": delta, "elapsed_seconds": time.monotonic() - began})`.

### `_split_score(scored, sides)` — 163–171
```python
def _split_score(scored, sides):
```
`sides` is `{name: set(record_ids)}`. Returns `{name: {"correct": int, "total": int}}` initialised for
every named side, incremented per row of `scored["rows"]`. No `require`, no failure mode.

### `expected_main_delta(stats)` — 174–180
```python
def expected_main_delta(stats):
    updates, presentations = stats["main_updates"], stats["presentations"]
    return {"slot_forwards": stats["presentation_slots"], "core_forward_calls": stats["planned_slot_core_passes"],
            "core_forward_attempts": stats["planned_slot_core_passes"],
            "sample_core_passes": stats["planned_slot_core_passes"], "prediction_calls": presentations,
            "staged_batches": updates, "private_loss_plan_calls": presentations, "backward_attempts": updates,
            "backward_calls": updates, "optimizer_step_attempts": updates, "optimizer_updates": updates}
```

**Exactly what the check at line 361 counts.** It compares the canonical bytes of
`report["main_training_delta"]` — the **sum, over the 1,470 main-training updates, of
`base.counter_delta(main.counters, before)`**, where `before = deepcopy(main.counters)` is taken
immediately before each update (337, 340) — against the eleven keys and values above. It counts
*planned* machine work as the learner itself counted it:

| key | value for the practice study | meaning |
|---|---|---|
| `slot_forwards` | 32,280 (`presentation_slots`) | one slot forward per presentation-slot |
| `core_forward_calls`, `core_forward_attempts`, `sample_core_passes` | 124,510 (`planned_slot_core_passes`) | slot forward × rounds drawn for that batch's depth |
| `prediction_calls`, `private_loss_plan_calls` | 8,180 (`presentations`) | one per presentation |
| `staged_batches`, `backward_attempts`, `backward_calls`, `optimizer_step_attempts`, `optimizer_updates` | 1,470 (`main_updates`) | one per update |

Consequences a builder must respect:
* `counter_delta` requires `set(after) == set(before)` (`typed_course_worker.py:56`, `COUNTER_FIELDS`),
  so **the new learner's `counters` dict must have exactly the key set that the new
  `expected_main_delta(stats)` returns** — not a superset, not a subset, because line 361 compares
  canonical bytes of a `dict`.
* The eleven names above are the practice machine's old per-slot counts. DG10
  (`DESIGN_REVIEW_PIPELINE_LENS.md:171-175`) says the pointer worker needs a **new formula keyed on
  packet forwards and rounds × worlds read**, and its own test against real counters (P11). The key
  names are free to change; the set-equality rule is not.
* `base.validate_training_delta` (`typed_course_worker.py:62-69`) is hard-coded to the *course*
  study's numbers and is **not** on the practice path — do not reuse it.
* The stand-in learner in the dry run declares exactly these eleven names
  (`records/typed_practice_001/preflight_dry_run.py:42-44`); a new dry run must declare the new
  eleven.

### `deliver(results, artifacts, report, *, failed)` — 183–210
```python
def deliver(results, artifacts, report, *, failed):
```
1. `artifacts.mkdir(parents=True, exist_ok=True)`;
2. if `not failed`: `require(set(EXPECTED_ARTIFACTS) - {"worker_report.json", "measurements.json"} <= {p.name for p in artifacts.iterdir()}, "PRACTICE_REQUIRED_ARTIFACTS")` (187–188);
3. `_publish(artifacts / "worker_report.json", report)`;
4. `summary = {key: report.get(key) for key in ("job","source_sha","status","runtime","elapsed_seconds","condition","model_seed","failure","main_training_delta","interference_delta","global_actual_work","checkpoint_reload_verified","scores","development_scores","retention_scores","pass_summaries","initial_model_identity")}`; `summary.update(learning_on_held_back_established=False, boundary=BOUNDARY)`; publish `measurements.json`;
5. walk `sorted(artifacts.iterdir())` skipping `*.partial`, requiring each is a file, not a symlink and
   `st_size <= 64 * 1024 ** 2` (`"ARTIFACT_BOUND"`), collecting `{"name","bytes","sha256"}`;
6. `require(len(entries) <= 500, "ARTIFACT_COUNT")` (line 203);
7. publish `manifest.json` = `{"artifacts": entries}`;
8. `result = {"schema": RESULT_SCHEMA, "job": report["job"], "artifacts": entries, "status": "TYPED_PRACTICE_FAILED" if failed else "TYPED_PRACTICE_DELIVERED", "summary": summary, "failure": report.get("failure"), "boundary": BOUNDARY}`;
9. `pin = _publish(Path(results) / "result.json", result)`; `_publish_bytes(Path(results)/"result.json.sha256", (pin["sha256"] + "\n").encode("ascii"))`;
10. returns `result`.

`manifest.json` sits in `artifacts/` and is **not** in `EXPECTED_ARTIFACTS`; the gate reader reads it
(`records/typed_practice_001/evaluate_gates.py:161`).

## A.3 `EXPECTED_ARTIFACTS` — 49–57, and the `required_count` rule

```python
EXPECTED_ARTIFACTS = (
    tuple("pass_%02d_%s.jsonl" % (n, kind) for n in range(1, PASSES + 1) for kind in ("batches", "updates"))
    + ("interference_batches.jsonl", "interference_updates.jsonl")
    + tuple(phase + suffix for phase in EVALUATIONS for suffix in ("_predictions.json", "_scoring.json"))
    + tuple(name + suffix for name in CHECKPOINT_NAMES for suffix in (".pt", "_checkpoint.json"))
    + tuple(name + "_reload_predictions.json" for name in ("initial", "final", "retained"))
    + tuple("replay_%d_%s" % (n, s) for n in (1, 2) for s in ("batch.json", "update.json", "predictions.json"))
    + ("replay_report.json", "encoding_checks.json", "installed_sources.json", "loaded_sources.json",
       "protocol_material.json", "worker_report.json", "measurements.json"))
```

Name formation, counted:

| group | count | form |
|---|---|---|
| `pass_%02d_%s.jsonl` | 10 × 2 = 20 | `pass_01_batches.jsonl` … `pass_10_updates.jsonl` |
| interference | 2 | `interference_batches.jsonl`, `interference_updates.jsonl` |
| evaluations | 16 × 2 = 32 | `<phase>_predictions.json`, `<phase>_scoring.json` |
| checkpoints | 5 × 2 = 10 | `initial.pt`, `initial_checkpoint.json`, `pass_01.pt`, `prelast.pt`, `final.pt`, `retained.pt` + their `_checkpoint.json` |
| reloads | 3 | `initial_reload_predictions.json`, `final_reload_predictions.json`, `retained_reload_predictions.json` |
| replays | 2 × 3 = 6 | `replay_1_batch.json`, `replay_1_update.json`, `replay_1_predictions.json`, `replay_2_*` |
| fixed | 7 | `replay_report.json`, `encoding_checks.json`, `installed_sources.json`, `loaded_sources.json`, `protocol_material.json`, `worker_report.json`, `measurements.json` |
| **total** | **80** | confirmed against the delivered `collected/results/artifacts/manifest.json` (80 entries, `records/typed_practice_001/receipt_20260917/collected/results/result.json` "artifacts": 80) |

**The `required_count` rule.** `deliver` excludes `worker_report.json` and `measurements.json` from the
pre-check (187) because it writes them itself, but **all 80 names must be in the lifecycle evidence
contract**. `evidence_contract()` (`aws/typed_practice_launch.py:180-190`) builds
`names = {"results/result.json": …, "results/result.json.sha256": …, "results/artifacts/manifest.json": …}`
and then updates it with `"results/artifacts/" + name` for every name in `_probe().EXPECTED_ARTIFACTS`;
`run_evidence.contract` sets `required_count = len(entries)` (`aws/run_evidence.py:151`). Therefore

```
evidence_contract()["required_count"] == len(EXPECTED_ARTIFACTS) + 3      # 80 + 3 = 83
```

which is exactly the assertion at `tests/test_typed_practice_study.py:165`
(`assert launch.evidence_contract()["required_count"] == len(names) + 3`), and P7 restates it
(`DESIGN_REVIEW_PIPELINE_LENS.md:246`). The contract freezes before the worker starts and is held
independently of what the worker uploads (`aws/graph_training_candidate_launch.py:750-761`,
`EVIDENCE_CONTRACT_SCHEMA`, `EVIDENCE_CONTRACT_AUTHORITY_MISMATCH`).

## A.4 The Windows refusal — and why P8 depends on the ordering

* Call site: `cncm/typed_practice_worker.py:241-242`
  (`from cas_meta2.teaching_cycle.gpu_adapter import _cuda` then `torch, device = _cuda()`), reached
  after `progress` exists (238), after `phase("preflight")` (239) and after
  `os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"` (240), and **before** any tensor is created.
* The refusal itself: `aws/../cas_meta2/teaching_cycle/gpu_adapter.py:37-39`

  ```python
  def execution_guard():
      require(platform.system() == "Linux", "LINUX_WORKER_REQUIRED")
      require(os.environ.get("CAS_META2_RUN_TEACHING_CYCLE") == "1", "EXPLICIT_ENABLE_REQUIRED")
  ```
  with `require` raising `ValueError("TEACHING_GPU:" + reason)` (`gpu_adapter.py:27-29`). So a Windows
  host raises `ValueError("TEACHING_GPU:LINUX_WORKER_REQUIRED")`.
* **The ordering that makes this "before any numeric import":** `_cuda()` (`gpu_adapter.py:42-49`)
  calls `execution_guard()` **first** and only then runs `import torch` (line 44). `gpu_adapter.py`
  imports no numeric module at module level (docstring line 1: "importing this file does not import
  torch"). So `import gpu_adapter` is safe on Windows, and the platform check fires before torch is
  ever imported. Inside `_cuda`, after torch: `CUDA_REQUIRED_NO_CPU_FALLBACK`,
  `EXACTLY_ONE_VISIBLE_GPU_REQUIRED`, `T4_NOT_ADMITTED`.
* `CAS_META2_RUN_TEACHING_CYCLE=1` is exported by the packaged bootstrap
  (`aws/typed_matched_launch.py:171`, `os.environ['CAS_META2_RUN_TEACHING_CYCLE'] = '1'`), never by the
  worker.
* Because the failure happens inside `run()`'s `try`, the `except` at 470 runs and
  `deliver(failed=True)` writes a complete FAILED envelope. The rehearsal confirms both halves:
  `records/typed_practice_001/prepare_study.py:93` requires a non-zero exit with
  `b'LINUX_WORKER_REQUIRED' in proc.stderr`, and `:95` requires
  `result['status'] == 'TYPED_PRACTICE_FAILED'`. **P8** is the pytest version
  (`tests/test_typed_practice_study.py:299-307`): it monkeypatches
  `gpu_adapter.platform.system → "Windows"`, calls `worker.run(config, ROOT, results, results/"artifacts")`
  with **no attestor**, expects `ValueError` matching `"LINUX_WORKER_REQUIRED"`, and then asserts
  `json.loads((results/"result.json").read_bytes())["status"] == "TYPED_PRACTICE_FAILED"`.

## A.5 `torch.use_deterministic_algorithms(True)` at line 252 and everything around it

Lines 240–254, in order, and each is load-bearing:

1. **240** `os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"` — set before torch is imported and
   before the CUDA context; without it deterministic cuBLAS refuses matrix operations on this CUDA
   runtime (`typed_course_worker.py:328-330`).
2. **241–242** `_cuda()` → torch, device (Windows/enable/GPU checks, A.4).
3. **243** `torch.cuda.reset_peak_memory_stats(device)` so the peak reported at 465–466 measures this
   job only.
4. **250–251** `RUNTIME_MISMATCH` pins `torch_version == "2.11.0+cu128"`, `cuda_version == "12.8"`,
   `"RTX PRO 4500" in gpu_name`.
5. **252** `torch.use_deterministic_algorithms(True)`.
6. **253–254** `torch.backends.cuda.matmul.allow_tf32 = False`; `torch.backends.cudnn.allow_tf32 = False`.

RK7 (`DESIGN_REVIEW_PIPELINE_LENS.md:71-73`) warns that strict mode may reject CUDA scatter, index and
embedding-backward paths, and some `linalg` solvers. The prescribed mitigation: dense adjacency
matrix multiplies, one-hot matrix multiplies instead of embedding lookups, a closed-form ridge solve,
proved by GPU smoke S1. A pointer worker must reproduce 252–254 verbatim and add nothing that strict
mode refuses.

## A.6 Shared helpers taken from `cncm/typed_course_worker.py` — exact signatures

| Helper | Lines | Signature | Semantics and codes |
|---|---|---|---|
| `_write_bytes` | 40–48 | `_write_bytes(path, raw)` | create-only (`"xb"`), flush, fsync, readback. `"OUTPUT_BYTES"` (raw not bytes / path is symlink), `"OUTPUT_READBACK"`. Returns `{"name","bytes","sha256"}` |
| `_write` | 51–52 | `_write(path, value)` | `_write_bytes(path, canonical(value))` |
| `counter_delta` | 55–59 | `counter_delta(after, before)` | `"COUNTER_FIELDS"` (both dicts, equal key sets), `"COUNTER_VALUES"` (all ints, `after[k] >= before[k] >= 0`). Returns `{k: after[k]-before[k]}` |
| `validate_training_delta` | 62–69 | `validate_training_delta(delta)` | course-study-only hard-coded 11 counters; `"MAIN_TRAINING_COUNTERS"`. Not used by the practice worker |
| `_deadline` | 72–73 | `_deadline(started)` | `"DEADLINE_EXCEEDED"` against `contract.MAX_WALL_SECONDS` |
| `_ProgressWriter` | 76–112 | class; `__init__(self, results, started)`; `emit(self, phase, **values)` | see below |
| `_partial_checkpoint` | 115–139 | `_partial_checkpoint(learner, results, completed_updates)` | see below |
| `_sealed_predictions` | 142–145 | `_sealed_predictions(path, predictions, *, phase, expected_ids)` | `"PREDICTION_REGISTRY_ORDER"`; `_write` seal with schema `"cncm.typed-course-prediction-seal/0.1"` |
| `_score_seal` | 148–168 | `_score_seal(path, pin, packets, *, started, progress=None)` | see below |
| `_train_step` | 171–188 | `_train_step(learner, batch, packets, artifacts, *, prefix, started, progress=None)` | course worker's own staged-train path; `"STAGED_SEAL_DIGEST"`; returns `(pin, result)` |
| `_fresh_framework` | 191–197 | `_fresh_framework(torch, device)` | seeds `torch.manual_seed`, `torch.cuda.manual_seed_all`, `random.seed` with `contract.MODEL_SEED`, then `build_graph_training_framework(torch, device, seed=contract.MODEL_SEED, encoder={"d_model": 64})`. **The practice worker does not use it** — it uses `matched._framework(torch, device, design["model_seed"])` |
| `_rng` | 200–202 | `_rng(torch)` | `{"torch_cpu": get_rng_state(), "torch_cuda": get_cuda_rng_state_all(), "python": random.getstate()}` |
| `_state` | 205–210 | `_state(torch, learner)` | see below |
| `_check_state` | 213–216 | `_check_state(torch, learner, checkpoint)` | see below |
| `_representatives` | 219–225 | `_representatives(packets)` | first packet per `record["query"]["kind"]`; `"EIGHT_KIND_COVERAGE"` requires the set `{"role_set","definition","context","analogy","correspondence","parts","edge_account","reach"}`; returns `{kind: record_id}` in sorted-kind order |
| `_encoding_checks` | 228–275 | `(torch, encoder, packets, representatives, *, started, all_packets, progress=None, phase="encoding_checks")` | see A.8 |
| `deliver` | 278–301 | `deliver(results, artifacts, report, *, failed)` | course variant: `"REQUIRED_ARTIFACTS"`, `"FLAT_ARTIFACT_BOUND"` (64 MiB), `"ARTIFACT_COUNT_BOUND"` (**400**, line 294), result statuses `"TYPED_COURSE_FAILED"`/`"TYPED_COURSE_DELIVERED"` |

### `_state(torch, learner)` — 205–210
```python
def _state(torch, learner):
    from cas_meta2.typed_teaching.learner import state_identity
    return {"model_state_identity": state_identity(torch, dict(learner.module.state_dict())),
            "optimizer_state_identity": state_identity(torch, learner.optimizer.state_dict()),
            "rng_state_identity": state_identity(torch, _rng(torch)),
            "encoder_state_identity": state_identity(torch, learner.encoder.export_state())}
```
`state_identity(torch, value)` is `cas_meta2/typed_teaching/learner.py:47`. `_state` therefore demands
exactly four learner attributes: `.module` (with `state_dict()`), `.optimizer`, `.encoder` (with
`export_state()`) and a usable torch RNG. RK2
(`DESIGN_REVIEW_PIPELINE_LENS.md:31-44`) requires the new `PointerCourseLearner` to expose
`.torch`, `.optimizer`, `.encoder`, `.counters`, `.cursor`, `.model_revision`, `.failed`,
`.run_identity_digest` for exactly this reason, and §5.2 of the hand-out adds: keep the frozen typed
encoder object reachable as `learner.encoder` even though the pointer machine does not use its packet
vectors (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:255-256`).

### `_check_state(torch, learner, checkpoint)` — 213–216
```python
def _check_state(torch, learner, checkpoint):
    actual = _state(torch, learner)
    require(all(actual[k] == checkpoint["metadata"][k] for k in actual), "RESTORED_STATE_MISMATCH")
    return actual
```
Compares all four identities to `checkpoint["metadata"]`, i.e. the metadata half of what
`export_checkpoint` returned. Used after every restore (407, 428, 435, 462 in the base worker) and
twice in the replay branch (428 and 435 → proves the replay's single update landed the weights on
`final`).

### `_partial_checkpoint(learner, results, completed_updates)` — 115–139
```python
def _partial_checkpoint(learner, results, completed_updates):
```
Publishes a recoverable partial state **without adding a name to the artifact contract**, under
`results/evidence/`:
* `name = "main_checkpoint_%04d" % completed_updates`;
* `checkpoint_path = results/evidence/<name>.pt`, `metadata_path = results/evidence/<name>.json`;
* `require(all(not p.exists() and not p.is_symlink() ...), "PARTIAL_CHECKPOINT_ALREADY_EXISTS")` — checked
  before and again after the staging write (122–123 and 135–136);
* builds inside `tempfile.TemporaryDirectory(dir=results.parent, prefix=".typed-checkpoint-")` — **same
  filesystem, outside `results/`** — `learner.export_checkpoint(staged)`, reads the staged bytes back,
  `require(len(raw) == pin["bytes"] and sha256(raw).hexdigest() == pin["sha256"], "PARTIAL_CHECKPOINT_READBACK")`;
* metadata = `{"schema": "cncm.typed-course-partial-checkpoint/0.1", "completed_main_updates", "main_course_complete": False, "checkpoint": pin, "boundary": "Partial recovery state; not completed-course acceptance or a learning result."}`;
* `staged.rename(checkpoint_path)`, `staged_metadata.rename(metadata_path)`; returns the metadata dict.

Called by the practice worker only between passes: `if number < PASSES: base._partial_checkpoint(main, results, main.cursor)` (351–352) → 9 files per run, at cursors 147, 294, …, 1323. They land in
`results/evidence/`, not `results/artifacts/`, so they do not count against the 500-artifact bound.

### `_score_seal(path, pin, packets, *, started, progress=None)` — 148–168
```python
def _score_seal(path, pin, packets, *, started, progress=None):
```
Docstring line 149: *"Only this post-readback path imports the private semantic checker."*
1. `raw = Path(path).read_bytes()`;
2. `require(len(raw) == pin["bytes"] and sha256(raw).hexdigest() == pin["sha256"], "SCORING_SEAL_CHANGED")`;
3. `seal = json.loads(raw)`;
4. `require([p["record_id"] for p in seal["predictions"]] == list(packets), "SCORING_REGISTRY_ORDER")`;
5. `phase = seal["phase"] + "_scoring"`; progress row `(phase, completed_packets=0, total_packets=len(packets))`;
6. `from cas_meta2.typed_teaching import checker` (**line 157**);
7. per prediction: `_deadline(started)`; `checked = checker.check_answer(packet["source"], packet["record"]["query"], prediction["answer"])`; row `= {"record_id": prediction["record_id"], "prediction_id": prediction["prediction_id"], **checked}`; progress every 50;
8. returns `{"schema": "cncm.typed-course-private-scoring/0.1", "public_seal": pin, "phase": seal["phase"], "rows": rows, "correct": sum(r["correct"] for r in rows), "total": len(rows), "boundary": BOUNDARY}`.

`checker.check_answer(public, query, answer)` (`checker.py:281-296`) returns, and therefore each
scoring row carries, the real keys:
`schema` (`"cas.typed-teaching-private-check/0.1"`), `query_id`, `source_digest`, `kind`, `rule`,
`answer_digest`, `target_digest`, `checker_profile_digest`, `correct` (bool),
`admissible_answer_count`, `witnesses`, `boundary`, `check_digest`. The gate reader consumes
`row['record_id']` and `row['correct']` only (`evaluate_gates.py:79`).
`checker.derive_target(public, query)` (`checker.py:243-268`) returns
`schema` (`"cas.typed-teaching-private-target/0.1"`), `query_id`, `source_digest`, `kind`, `rule`,
`checker_profile`, `checker_profile_digest`, `admissible_answers`, `witnesses`, `coverage`, `boundary`,
`target_digest`. `MAX_ADMISSIBLE_ANSWERS = 64`, `MAX_TARGET_BYTES = 512 * 1024` (`checker.py:21-22`).

### `_ProgressWriter` — 76–112
```python
class _ProgressWriter:
    def __init__(self, results, started):
    def emit(self, phase, **values):
```
* `__init__`: `self.results, self.started, self.index = Path(results), started, 0`; `self.directory = self.results / "evidence"`; `self.directory.mkdir(exist_ok=True)`.
* `emit`: `require(self.index < 10000, "PROGRESS_INDEX_BOUND")`; destination
  `results/evidence/typed_progress_%04d.json`; `require(not path.exists() and not path.is_symlink(), "PROGRESS_ALREADY_EXISTS")`
  (checked again at 104 after the staging write).
* Row: `{"schema": "cncm.typed-course-progress/0.1", "index": self.index, "typed_course_phase": phase, "elapsed_seconds": round(time.monotonic() - self.started, 2), **values}`.
* Atomic pattern: `tempfile.NamedTemporaryFile(mode="wb", dir=self.results.parent, prefix=".typed-progress-", suffix=".json", delete=False)`
  → write, flush, fsync → `staged.rename(path)` → `require(path.read_bytes() == raw, "PROGRESS_READBACK")`
  → `self.index += 1` → `print(json.dumps(row, sort_keys=True, allow_nan=False), flush=True)`
  (the console line is the only live telemetry). `finally:` unlinks a leftover staged file.
* 10,000 progress rows is the hard cap; the practice job emits well under 100.

## A.7 Checkpoint export/restore, reload/replay — and `_encoding_checks`

### Export (via the inner `checkpoint(name)` closure, 295–300)
`pin = main.export_checkpoint(staging / (name + ".pt"))` → `_move_in(...)` into `artifacts` →
`checkpoint_pins[name] = {**pin, "path": str(artifacts/(name+".pt"))}` → publish
`<name>_checkpoint.json`. `pin` carries (from the stand-in's shape at
`preflight_dry_run.py:125-129`, which mirrors the real learner) the keys `path`, `sha256`, `bytes`,
`run_identity_digest`, `metadata`; `metadata` carries `run_identity`, `run_identity_digest`,
`model_revision`, `cursor`, `counters`, `elapsed_seconds`, `training_mode` and the four identities of
`_state`. The gate reader reads `metadata["model_state_identity"]`
(`evaluate_gates.py:183-185`); I4/the worker read `metadata` through `_check_state`.

`export_checkpoint` refuses to run with a staged batch pending (`assert self._pending is None` in the
stand-in, `preflight_dry_run.py:118`) — a real learner must do the same, because a checkpoint taken
mid-update is not a state the pipeline can restore.

### Restore, reloads — 398–420
```python
final_name = "course_p%02d" % PASSES                     # "course_p10"
for name, expected_name in (("initial", "course_p00"), ("final", final_name), ("retained", None)):
    _deadline(started); phase(name + "_reconstruction")
    pin = checkpoint_pins[name]
    restored = PracticeCourseLearner.restore_checkpoint(
        torch, matched._framework(torch, device, design["model_seed"]),
        path=artifacts / (name + ".pt"), expected_sha256=pin["sha256"],
        expected_run_identity_digest=main.run_identity_digest, device=device)
    exact = base._check_state(torch, restored, pin)
    before = deepcopy(restored.counters)
    selected = list(retention_packets)[:8] if name == "retained" else list(representatives.values())
    source_packets = retention_packets if name == "retained" else packets
    expected = retained_predictions if name == "retained" else predictions[expected_name]
    rows = [restored.predict(source_packets[key], 8) for key in selected]
    require(all(canonical(row) == canonical(expected[row["record_id"]]) for row in rows), "RELOAD_PREDICTION_MISMATCH")
    _seal_predictions(artifacts / (name + "_reload_predictions.json"), rows, phase=name + "_reload", expected_ids=selected)
    delta = base.counter_delta(restored.counters, before)
    work.append({"phase": name + "_reload", "delta": delta})
    reloads.append({"phase": name, "checkpoint_sha256": pin["sha256"], "exact_state": exact,
                    "prediction_ids": selected, "delta": delta})
    del restored
```
Restore signature: `PracticeCourseLearner.restore_checkpoint(torch, framework, *, path, expected_sha256, expected_run_identity_digest, device)`; it is a **classmethod**. Every restore is handed a
**freshly built framework for the same seed**, not the live one.

### Replay — 421–446
```python
for branch in (1, 2):
    _deadline(started); phase("replay_%d" % branch)
    pin = checkpoint_pins["prelast"]
    restored = PracticeCourseLearner.restore_checkpoint(torch, matched._framework(torch, device, design["model_seed"]),
        path=artifacts / "prelast.pt", expected_sha256=pin["sha256"],
        expected_run_identity_digest=main.run_identity_digest, device=device)
    base._check_state(torch, restored, pin)
    before = deepcopy(restored.counters)
    staged_seal = staging / ("replay_%d_batch.json" % branch)
    raw, update = _stage_and_train(restored, batches[-1], packets, staged_seal, started=started)
    require(raw == last_seal, "REPLAY_PREUPDATE_MISMATCH")
    _move_in(staged_seal, artifacts / ("replay_%d_batch.json" % branch))
    _publish(artifacts / ("replay_%d_update.json" % branch), update)
    exact = base._check_state(torch, restored, checkpoint_pins["final"])
    rows = [restored.predict(packets[key], 8) for key in representatives.values()]
    require(all(canonical(row) == canonical(predictions[final_name][row["record_id"]]) for row in rows), "REPLAY_FINAL_MISMATCH")
    _seal_predictions(artifacts / ("replay_%d_predictions.json" % branch), rows, phase="replay_%d" % branch,
                      expected_ids=list(representatives.values()))
    delta = base.counter_delta(restored.counters, before)
    require(delta["optimizer_updates"] == delta["backward_calls"] == 1, "REPLAY_COUNTS")
    work.append({"phase": "replay_%d" % branch, "delta": delta})
    replays.append({"branch": branch, "restored_cursor": stats["main_updates"] - 1,
                    "committed_cursor": restored.cursor, "exact_state": exact, "delta": delta})
    del restored
```
The replay re-runs the **last main batch** (`batches[-1]`, cursor 1469) from `prelast` and demands the
resulting state equals `final` (`_check_state` against `checkpoint_pins["final"]`, 435) and that the
predictions equal the `final` predictions (437). `raw == last_seal` (432) proves the sealed public
bytes are reproducible from the pre-last checkpoint.

### `_encoding_checks` — `typed_course_worker.py:228–275`
```python
def _encoding_checks(torch, encoder, packets, representatives, *, started, all_packets,
                     progress=None, phase="encoding_checks"):
```
Called from the practice worker as
`base._encoding_checks(torch, main.encoder, packets, representatives, started=time.monotonic(), all_packets=True, progress=phase, phase="initial_encoding")` (303–304) and with `all_packets=False, phase="final_encoding"` (393–394); both results are published together as
`encoding_checks.json` with keys `"initial"` and `"final"` (303/393 and 396).

What it does:
1. `before = encoder.work_counters()`; `keys = list(packets) if all_packets else list(representatives.values())`;
2. per key: `vector = encoder.encode_packet(packets[key])`;
   `require(tuple(vector.shape) == (64,) and bool(torch.isfinite(vector).all().item()), "PACKET_ENCODE_NONFINITE")`;
   `norm = float(torch.linalg.vector_norm(vector).item())`;
   `require(math.isfinite(norm) and abs(norm - 1.0) <= 2e-5, "PACKET_UNIT_NORM")`; collect norms;
3. per representative: `cached = encoder.encode_packet(packet)` vs `direct = encoder.encode_packet(packet, use_cache=False)`;
   `require(torch.equal(cached, direct), "PACKET_CACHE_DIRECT_MISMATCH")`;
   `plan = slots.compile_slots(packet)`; `slot = plan["slots"][0]`;
   `cached_slot = encoder.encode_slot(packet, plan, slot)` vs `direct_slot = encoder.encode_slot(packet, plan, slot, use_cache=False)`;
   `require(torch.equal(cached_slot, direct_slot) and bool(torch.isfinite(direct_slot).all().item()), "SLOT_CACHE_DIRECT_MISMATCH")`;
   `require(math.isfinite(norm) and abs(norm - 1.0) <= 2e-5, "SLOT_UNIT_NORM")`; append
   `{"kind","record_id","slot_id","packet_exact": True,"slot_exact": True,"slot_norm"}`;
4. `readout = encoder.readout_rows`;
   `require(bool(torch.isfinite(readout).all().item()) and int(torch.unique(readout, dim=0).shape[0]) == 90, "READOUT_NONFINITE_OR_DUPLICATE")`;
   `require(bool((torch.abs(torch.linalg.vector_norm(readout, dim=1) - 1.0) <= 2e-5).all().item()), "READOUT_UNIT_NORM")`;
5. returns `{"finite_unit_packet_count": len(keys), "packet_norm_range": [min(norms), max(norms)], "representatives": rows, "readout_distinct_unit_rows": 90, "frozen_identity": encoder.verify_frozen(), "counters_before": before, "counters_after": encoder.work_counters()}`.

Every loop re-checks `_deadline(started)` against the **matched** deadline it was handed (237, 248);
the practice worker therefore hands it `time.monotonic()` and re-checks its own deadline immediately
after (305, 395).

**What a pointer replacement must check instead (V1, `DESIGN_REVIEW_PIPELINE_LENS.md:179`).** The old
checks are about the frozen encoder's packet vectors and its 90 readout rows, which the pointer
machine never uses. The replacement must assert, on the **pointer input reader**:
finite values; cached read equal to uncached read (`use_cache=False`-style equality); the label /
declaration token cache pinned by digest and built exactly once (RK3,
`DESIGN_REVIEW_PIPELINE_LENS.md:46-50`); and **no leak of node aliases or node order** (P10, DG3). It
must keep the same shape — a dict published as `encoding_checks.json` — because the name is in
`EXPECTED_ARTIFACTS`, and it must keep `_deadline` discipline.

## A.8 The custody boundary — where the checker is imported, and the phase ordering that enforces it

The registered rule: *"so that the worker never reads a correct answer before training"*
(`practice_contract.py:11-12`) and *"Only this post-readback path imports the private semantic
checker"* (`typed_course_worker.py:149`).

Import sites of `cas_meta2.typed_teaching.checker` on the worker path:

| Site | Line | Position in the ordering |
|---|---|---|
| `typed_practice_worker._stage_and_train` | `typed_practice_worker.py:116` | after `base._write_bytes(seal_path, staged["bytes"])` (114) and after `STAGED_SEAL_DIGEST` (115); `derive_target` at 117 |
| `typed_course_worker._score_seal` | `typed_course_worker.py:157` | after the readback and digest check `SCORING_SEAL_CHANGED` (151) and `SCORING_REGISTRY_ORDER` (153) |
| `typed_course_worker._train_step` | `typed_course_worker.py:182` | after `_write_bytes` of the seal and `STAGED_SEAL_DIGEST` (178–179) |
| `typed_course_worker.run` (course worker's own training loop) | `typed_course_worker.py:405` | after `MAIN_STAGE_SEAL` (403) |
| `evaluate_gates._admissible` | `evaluate_gates.py:100` | post-run, local, by the operator |
| `holdout_audit.answer_texts` | `holdout_audit.py:44` | local audit only — "which is why the worker never runs it" (`holdout_audit.py:4-5`) |

The invariant, in one sentence: **no code path may derive a target before the exact public bytes for
that batch exist durably and their digest has been read back.** The two ways it is enforced:

1. **Seal before targets, inside one update** — `_stage_and_train`, steps 4→5→6→8 of A.2.
   `train_sealed_batch(seal_path, expected_sha256=pin["sha256"], target_receipts=targets)` then binds
   the targets to the sealed file's digest, so the learner cannot be trained against a target derived
   from different public bytes.
2. **Seal before scoring, at every evaluation** — `_evaluate` writes and pins
   `<phase>_predictions.json` (149) and only `_score_seal` reads it back and imports the checker
   (152 → `typed_course_worker.py:151,157`).

The point-in-time consequence that FP3 (`DESIGN_REVIEW_PIPELINE_LENS.md:115-121`) turns into a
requirement: the checkpoint check's **Phase A** may restore old checkpoints and extract public
vectors only, and must be finished before any answer is derived and before the pointer model is
seeded (M3, `:188`: restoring an old checkpoint overwrites the global torch CPU/CUDA/Python RNG state
and `matched._framework` re-seeds). **Phase B** — deriving answers and fitting the trained→held ridge
probe — runs **last**, after the pointer evaluations, reloads and replays. P14 is the test
(`DESIGN_REVIEW_PIPELINE_LENS.md:253`).

---

# B. `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/worker_contract.py`

The task's path `cas_meta2/typed_teaching/worker_contract.py` resolves to
`research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/worker_contract.py` (172 lines) under `CNCM`.
`practice_contract` does **not** inherit from it directly: it does
`from . import matched_contract as matched` (`practice_contract.py:31`), and `matched_contract` does
`from . import course_plan, source, worker_contract as baseline` (`matched_contract.py:16`). So the
inventory function that actually runs is a three-layer chain, and each layer appends.

## B.1 The code-inventory scope — `worker_contract.input_inventory`, lines 135–156

```python
def input_inventory(root):
    root = Path(root).resolve(strict=True)
    names = set(MATERIAL) | {WHEEL_PREFIX + name for name in WHEELS}
    for prefix in ("cncm", "research/CAS_META_2_COMPOSITION/cas_meta2"):        # 138
        paths = list((root / prefix).rglob("*.py"))                             # 139
        require(paths, "SOURCE_PACKAGE_MISSING:" + prefix)                      # 140
        for path in paths:
            require(not path.is_symlink()
                    and path.resolve(strict=True).is_relative_to(root), "SOURCE_PATH")   # 142
            names.add(path.relative_to(root).as_posix())                        # 143
    ...
```

**Exactly what is hashed:**

| source | pattern | anchor |
|---|---|---|
| `cncm/` | **every `.py`, recursive** | `worker_contract.py:138-143` |
| `research/CAS_META_2_COMPOSITION/cas_meta2/` | **every `.py`, recursive** | `worker_contract.py:138-143` |
| `MATERIAL` keys | fixed list of pinned data files | `worker_contract.py:137` + `:26-29` |
| `WHEEL_PREFIX + name` for `name in WHEELS` | the two pinned wheels | `worker_contract.py:137` + `:31-35` |
| `matched_contract.DEVELOPMENT_PATH` | appended by the matched layer | `matched_contract.py:173-178` |

`MATERIAL` at the base layer is
`COURSE_PATH = "records/typed_course_001/checks_002/public_course.json"` (4,165,195 bytes, sha256
`cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987`) and
`TOKENIZER_PATH = "records/typed_interface_001/checks_002/training_tokenizer.json"` (447,140 bytes,
sha256 `bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c`) — `worker_contract.py:24-29`.
The matched layer adds `records/typed_matched_001/development_001/compact_development.json`
(685,549 bytes, sha256 `5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4`) —
`matched_contract.py:25-27, 32`. The live inventory for the practice study is **236 rows**
(`records/typed_practice_001/admission_001/20260917/authority.json` → `worker_config.inputs`), first
row `{'bytes': 2222, 'path': 'cncm/__init__.py', 'sha256': '88c22b44…8de4'}`.

**RK9 in one line:** because `input_inventory` globs the live tree, **any `.py` added under `cncm/` or
`cas_meta2/` between the authority and the launch changes `inputs_sha256` and blocks the remaining
jobs** (`DESIGN_REVIEW_PIPELINE_LENS.md:82-88`); and any uncommitted `.py` fails the package build with
`PRACTICE_INPUT_NOT_COMMITTED` (`aws/typed_practice_launch.py:222`). Analysis scripts must live under
`records/`.

## B.2 Status vocabulary and `SUCCESS_STATUS`, and what a FAILED result must contain

`worker_contract.py` itself defines **no** status vocabulary — it defines only
`CANDIDATE = "CNCM_TYPED_COURSE_ACCEPTANCE_001"` (line 15), `CONFIG_SCHEMA =
"cncm.typed-course-worker-config/0.1"` (16) and `JOB_PATTERN = r"cas-meta2-typedcourse-\d{14}-[a-f0-9]{8}"` (17).
The status vocabulary lives in the worker modules, and the launcher must mirror it exactly.

| Layer | Name | Line | Value |
|---|---|---|---|
| contract | `CONFIG_SCHEMA` (course) | `worker_contract.py:16` | `"cncm.typed-course-worker-config/0.1"` |
| contract | `CONFIG_SCHEMA` (practice) | `practice_contract.py:34` | `"cncm.typed-practice-worker-config/0.1"` |
| worker | `RESULT_SCHEMA` | `typed_practice_worker.py:38` | `"cncm.typed-practice-worker-result/0.1"` |
| worker | `FAILURE_SCHEMA` | `typed_practice_worker.py:39` | `"cncm.typed-practice-failure/0.1"` |
| worker | `SUCCESS_STATUS` | `typed_practice_worker.py:40` | `"COMPLETE_TYPED_PRACTICE_ARM"` |
| worker | result `status` (delivered) | `typed_practice_worker.py:206` | `"TYPED_PRACTICE_DELIVERED"` |
| worker | result `status` (failed) | `typed_practice_worker.py:206` | `"TYPED_PRACTICE_FAILED"` |
| worker | report `status` (failed) | `typed_practice_worker.py:483` | `"TYPED_PRACTICE_FAILED"` |
| report | report `schema` | `typed_practice_worker.py:226` | `"cncm.typed-practice-worker-report/0.1"` |
| launcher | request/authority/owner schemas | `aws/typed_practice_launch.py:39-41` | `"cncm.typed-practice-request/0.1"`, `"cncm.typed-practice-authority/0.1"`, `"cncm.typed-practice-owner/0.1"` |
| launcher | `failure_statuses` | `aws/typed_practice_launch.py:365` | `("WORKER_FAILED", "REMOTE_WORKER_FAILED", "TYPED_PRACTICE_FAILED")` |

(The course worker's parallel triple is at `typed_course_worker.py:22-24`: result
`"cncm.typed-course-worker-result/0.1"`, failure `"cncm.typed-course-failure/0.1"`, success
`"COMPLETE_EXPOSED_TYPED_COURSE_AND_SAME_PROCESS_RELOAD_OBSERVED"`; its delivered/failed result
statuses are `"TYPED_COURSE_DELIVERED"`/`"TYPED_COURSE_FAILED"` at line 297.)

**What a FAILED result must contain.** On any exception, `deliver(failed=True)` writes
`results/result.json` (`typed_practice_worker.py:205-208`) plus `results/result.json.sha256` (209) with:

```json
{"schema": "cncm.typed-practice-worker-result/0.1", "job": "<job>", "artifacts": [ {"name","bytes","sha256"}, … ],
 "status": "TYPED_PRACTICE_FAILED",
 "summary": {…"failure": {"schema": "cncm.typed-practice-failure/0.1", "type": "<ExcClass>", "detail": "<str(error)[:1000]>"},
             "status": "TYPED_PRACTICE_FAILED", "elapsed_seconds": <float>, …},
 "failure": {"schema": "cncm.typed-practice-failure/0.1", "type": "<ExcClass>", "detail": "<str(error)[:1000]>"},
 "boundary": "<BOUNDARY>"}
```
and `artifacts/worker_report.json` + `artifacts/measurements.json` are always written, even on the
failure path (189, 195), so a failed job still has an inventory. Observed shape:
`records/typed_practice_001/receipt_20260917/collected/results/result.json` has key set
`['artifacts','boundary','failure','job','schema','status','summary']`.

## B.3 Every limit relevant to MATERIAL and inventory

| Limit | Value | Anchor |
|---|---|---|
| single member / pinned material file | `MAX_MEMBER_BYTES = 4 * 1024 ** 2` (4 MiB) | `worker_contract.py:20`; enforced `:75` `"MATERIAL_SIZE:<name>"`, `:78` `"MATERIAL_BYTES:<name>"` |
| inventory row count | `<= 2000` | `worker_contract.py:155` `"INPUT_TOTAL_BOUND"`; repeated `matched_contract.py:177` |
| inventory total bytes | `<= 96 * 1024 ** 2` (96 MiB) | `worker_contract.py:155` |
| per-row file check | must be a regular file, `<= MAX_MEMBER_BYTES` | `worker_contract.py:147` `"INPUT_MEMBER_BOUND:<name>"` |
| material pins | `{bytes, sha256}` must equal MATERIAL row | `worker_contract.py:151` `"INPUT_MATERIAL_PIN"` |
| wheel pins | sha256 must equal `WHEELS[name]` | `worker_contract.py:153` `"INPUT_WHEEL_PIN"` |
| package member count | `MAX_MEMBER_COUNT = 2000` | `aws/graph_training_curriculum_launch.py:143`; enforced `aws/typed_practice_launch.py:238` `"PRACTICE_PACKAGE_BOUND"` |
| package member bytes | `MAX_MEMBER_BYTES = 4 * 1024**2` | `graph_training_curriculum_launch.py:142`; enforced `typed_practice_launch.py:226` `"PRACTICE_MEMBER_BOUND"` |
| expanded package bytes | `MAX_EXPANDED_BYTES = 96 * 1024**2` | `graph_training_curriculum_launch.py:144`; enforced `typed_practice_launch.py:239` |
| archive bytes | `MAX_ARCHIVE_BYTES = 24 * 1024**2` | `graph_training_curriculum_launch.py:145`; enforced `typed_practice_launch.py:247` `"PRACTICE_ARCHIVE_BOUND"` |
| artifact file bytes | `64 * 1024**2` per file | `typed_practice_worker.py:200` `"ARTIFACT_BOUND"`; base worker `64 MiB` at `typed_course_worker.py:291` |
| artifact file count | `<= 500` under `results/` (practice), `<= 400` (course) | `typed_practice_worker.py:203` `"ARTIFACT_COUNT"`; `typed_course_worker.py:294` `"ARTIFACT_COUNT_BOUND"` |
| result object bytes read at wait | `128 * 1024**2` | `graph_training_curriculum_launch.py:1016` |
| ledger job-id pattern | `cas-meta[0-9]+-[a-zA-Z0-9-]+` | `aws/budget.py:105` |
| job pattern | `cas-meta2-tprac-\d{14}-([a-f0-9]{8})-m-(20260917\|20260918\|20260919)` | `practice_contract.py:35` |
| bucket pattern | `[a-z0-9][a-z0-9-]{1,61}[a-z0-9]` — **≤ 63 chars** | `practice_contract.py:226`; RK4 |

RK4 arithmetic (`DESIGN_REVIEW_PIPELINE_LENS.md:52-55` plus measurement): the bucket is
`job + "-807562639912"`, so the study token after `cas-meta2-` must be **≤ 5 characters**. The
hand-out's choice is `tpntr` (`HANDOFF…:280`), which gives exactly 63 characters; `tprac` also gives
63, `tptr` gives 62, `tpoint` gives 64 and is refused, `tpointer` gives 66. P2 is the length test.

---

# C. `research/CAS_META_2_COMPOSITION/aws/typed_practice_launch.py` — the launcher to override (RK5)

447 lines. Module docstring 1–10; imports 11–32; constants 34–74.

## C.0 Constants and the time ordering

| Name | Line | Value |
|---|---|---|
| `ROOT` / `PROJECT` | 22–23 | `ROOT = Path(__file__).resolve().parents[1]` (`…/aws`), `PROJECT = ROOT.parents[1]` (`…/CAS_META_2_COMPOSITION`); both inserted on `sys.path` (24–26) |
| imported modules | 27–32 | `aws.typed_matched_launch as matched`, `aws.graph_training_candidate_launch as lifecycle`, `aws.graph_training_curriculum_launch as shared`, `aws.recurrent_cjt_launch as worker_template`, `aws.run_evidence`, `aws.budget`, and `cas_meta2.typed_teaching.practice_contract as contract` |
| `require, canonical, digest` | 34 | `shared.require, shared.canonical, shared.digest` |
| `CANDIDATE`, `CONFIG_SCHEMA` | 35–36 | from the contract |
| `RESULT_SCHEMA` / `FAILURE_SCHEMA` | 37–38 | identical strings to the worker's (the `_probe()` binding) |
| `REQUEST_SCHEMA` / `AUTHORITY_SCHEMA` / `OWNER_SCHEMA` | 39–41 | `"cncm.typed-practice-{request,authority,owner}/0.1"` |
| `WORKER_NAME` | 42 | `"typed_practice_worker.py"` |
| `JOB_PATTERN` | 43 | `contract.JOB_PATTERN` |
| `MAX_WALL_SECONDS` | 44 | 12,600 (numeric child timeout) |
| `OUTER_TIMEOUT_SECONDS` | 45 | 13,500 (setup + worker + publication) |
| `BOOT_WATCHDOG_SECONDS` | 46 | 14,100 (guest-owned poweroff) |
| `INSTANCE_SECONDS_MAX` | 47 | 14,400 (launcher wait budget) |
| `RESERVATION_USD` | 48 | `"15.00"` |
| `OPTIMIZER_UPDATES_MAX` | 50 | `1488` = 1,470 + 16 + 2 |
| `TRANSIENT_ERROR_CODES` | 52–56 | 15 codes plus `RequestTimeTooSkewed`, `RequestExpired` |
| `TRANSIENT_ERROR_CLASSES` | 59–61 | `EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError, ConnectionClosedError, ResponseStreamingError, IncompleteReadError, ProxyConnectionError, ConnectionError, HTTPClientError` |
| `MAX_TRANSIENT_WAIT_ERRORS` | 62 | `500` |
| `EXPERIMENT` | 63 | `{"profile": "typed_practice_v1", "candidate": CANDIDATE, "entrypoint": "cncm.typed_practice_worker.run"}` |
| `BOUNDS` | 64–66 | `{"training": True, "optimizer_updates_max": 1488, "max_wall_seconds": 12600, "jobs": 1, "automatic_retries": 0, "reservation_usd": "15.00", "instance_type": "g7.2xlarge", "region": "us-west-2", "instance_seconds_max": 14400}` |
| `DESIGN` | 67 | `json.loads(canonical(contract.DESIGN))` — the frozen design bytes, hashed into the authority |
| `CANONICAL_LEDGER` | 68 | `matched.CANONICAL_LEDGER` → the **meta1 worktree** path (see F) |
| `PACKAGING_SOURCES` | 69–71 | see C.2 |
| ordering guard | 72–74 | `require(shared.RESOURCE_PLAN["instance_seconds_max"] < BOOT_WATCHDOG_SECONDS < INSTANCE_SECONDS_MAX and contract.WORKER_DEADLINE_SECONDS < MAX_WALL_SECONDS < OUTER_TIMEOUT_SECONDS < BOOT_WATCHDOG_SECONDS, "PRACTICE_TIME_ORDER")` — i.e. 12,300 < 12,600 < 13,500 < 14,100 < 14,400 |

## C.1 Every function to override, with what it hard-codes today

### `_probe()` — 77–82
```python
def _probe():
    import importlib
    probe = importlib.import_module("cncm.typed_practice_worker")
    for name in ("CANDIDATE", "CONFIG_SCHEMA", "RESULT_SCHEMA", "FAILURE_SCHEMA"):
        require(getattr(probe, name) == globals()[name], "PRACTICE_PROBE_CONTRACT:" + name)
    return probe
```
Hard-codes: the module path `cncm.typed_practice_worker` and the four global names. Called by
`evidence_contract()` (184). **Must be rewritten** for `cncm.typed_pointer_worker`; the RK5
instruction is to *keep the constant check* (`DESIGN_REVIEW_PIPELINE_LENS.md:64`). This is the
mechanism that makes a mismatched package impossible: the launcher cannot build an evidence contract
for a worker whose four contract constants disagree.

### `frozen_inputs()` / `frozen_inputs_hash()` — 85–90
```python
def frozen_inputs():
    return contract.input_inventory(PROJECT)
def frozen_inputs_hash():
    return digest(canonical(frozen_inputs()))
```
Hard-codes: `PROJECT` as the inventory root and `practice_contract.input_inventory`. A new contract
must supply its own `input_inventory` (appending the 18 checkpoint files, F/§5.1).

### `worker_config(job, *, source_sha)` — 93–96
```python
def worker_config(job, *, source_sha):
    _, model_seed = contract.parse_job(job)
    return contract.make_config(PROJECT, source_sha=source_sha, job=job, model_seed=model_seed,
                                bucket=job + "-" + shared.RESOURCE_PLAN["account"])
```
Hard-codes: the practice `parse_job` (which returns `(CONDITION, model_seed)`, model seed in **group 2**
of the pattern), and the bucket suffix `shared.RESOURCE_PLAN["account"]` = `"807562639912"`. The bucket
string is therefore `job + "-807562639912"` (`shared.RESOURCE_PLAN` at
`graph_training_curriculum_launch.py:85`), and the same string is asserted against
`self.bound_config["bucket"]` at 321 and 370.

### `validate_request(request)` — 99–107
```python
def validate_request(request):
    require(type(request) is dict and set(request) == {"schema", "job", "source_sha", "archive_sha256",
                                                       "manifest_sha256", "launch_authorized"}, "PRACTICE_REQUEST_FIELDS")
    require(request["schema"] == REQUEST_SCHEMA, "PRACTICE_REQUEST_SCHEMA")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]), "PRACTICE_REQUEST_JOB")
    for key, pattern in (("source_sha", shared.HEX40), ("archive_sha256", shared.HEX64), ("manifest_sha256", shared.HEX64)):
        require(type(request[key]) is str and pattern.fullmatch(request[key]), "PRACTICE_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "PRACTICE_REQUEST_INERT")
    return request
```
Hard-codes: the exact six-field set and `launch_authorized is False` (the request file can never
authorize spend). `HEX40 = re.compile(r"[a-f0-9]{40}\Z")`, `HEX64` similarly
(`graph_training_curriculum_launch.py:75-76`).

### `_check_bounds(document, code)` — 110–112
Iterates `BOUNDS.items()` and requires `type(document.get(key)) is type(expected) and document[key] == expected`
→ `code + ":" + key`. Called with `"PRACTICE_AUTHORITY_BOUND"` (124) and `"PRACTICE_OWNER_BOUND"` (144).
A new launcher must supply its own `BOUNDS` (updates max, reservation, wall seconds, instance type).

### `validate_authority(authority)` — 115–131 (the requested lines 125–127 are the binding loop)
```python
def validate_authority(authority):
    identity = {"job", "source_sha", "archive_sha256", "manifest_sha256"}
    fields = identity | set(BOUNDS) | {"schema", "candidate", "owner_authorization_sha256", "inputs_sha256",
                                       "design_sha256", "evidence_contract_sha256", "worker_config"}
    require(type(authority) is dict and set(authority) == fields, "PRACTICE_AUTHORITY_FIELDS")
    require(authority["schema"] == AUTHORITY_SCHEMA and authority["candidate"] == CANDIDATE, "PRACTICE_AUTHORITY_CANDIDATE")
    validate_request({**{key: authority[key] for key in identity}, "schema": REQUEST_SCHEMA, "launch_authorized": False})
    require(type(authority["owner_authorization_sha256"]) is str
            and shared.HEX64.fullmatch(authority["owner_authorization_sha256"]), "PRACTICE_OWNER_HASH")
    _check_bounds(authority, "PRACTICE_AUTHORITY_BOUND")
    for key, expected in (("inputs_sha256", frozen_inputs_hash()), ("design_sha256", digest(canonical(DESIGN))),
                          ("evidence_contract_sha256", run_evidence.contract_digest(evidence_contract()))):
        require(authority[key] == expected, "PRACTICE_AUTHORITY_BINDING:" + key)          # 125-127
    expected = worker_config(authority["job"], source_sha=authority["source_sha"])
    require(type(authority["worker_config"]) is dict and canonical(authority["worker_config"]) == canonical(expected),
            "PRACTICE_AUTHORITY_CONFIG")
    return authority
```
**What lines 125–127 pin** and why they are the RK9 gate: `inputs_sha256` must equal
`frozen_inputs_hash()` **recomputed from the live tree at execute time** — so any `.py` byte added to
`cncm/` or `cas_meta2/` after the authority was written makes the hash differ and the launch is
refused. `design_sha256` pins `launch.DESIGN` (i.e. the new `pointer_contract.DESIGN`).
`evidence_contract_sha256` pins the evidence contract, which is itself derived from
`_probe().EXPECTED_ARTIFACTS`. A new launcher must redefine all three (they are module-local
references to its own `frozen_inputs_hash`, `DESIGN` and `evidence_contract`).

### `validate_owner(path, authority)` — 134–145
```python
def validate_owner(path, authority):
    raw = Path(path).read_bytes()
    require(digest(raw) == authority["owner_authorization_sha256"], "PRACTICE_OWNER_FILE_HASH")
    record = json.loads(raw)
    require(type(record) is dict and record.get("schema") == OWNER_SCHEMA and record.get("candidate") == CANDIDATE,
            "PRACTICE_OWNER_SCOPE")
    quote = record.get("owner_instruction_raw")
    require(type(quote) is str and bool(quote.strip()), "PRACTICE_OWNER_QUOTE")
    require(record.get("job") == authority["job"], "PRACTICE_OWNER_JOB")
    require(type(record.get("bounds")) is dict, "PRACTICE_OWNER_BOUNDS")
    _check_bounds(record["bounds"], "PRACTICE_OWNER_BOUND")
    return record
```
Hard-codes: `OWNER_SCHEMA`, `CANDIDATE`, the mandatory non-empty `owner_instruction_raw`, the
job-identity requirement (one owner record per job), and the bounds equality. DG9 requires three new
owner records for the pointer machine (`DESIGN_REVIEW_PIPELINE_LENS.md:167-169`).

### `validate_ledger_path(value)` — 148–149
`return matched.validate_ledger_path(value)`, which is
```python
def validate_ledger_path(value):
    require(isinstance(value, (str, Path)), "TYPED_LEDGER_PATH_REQUIRED")
    path = Path(value).expanduser().resolve()
    require(path == CANONICAL_LEDGER.resolve() and path.is_file(), "TYPED_CANONICAL_META1_LEDGER_REQUIRED")
    return path
```
(`typed_matched_launch.py:130-134`). Hard-codes: equality with the meta1 ledger path. A new launcher
may keep delegating to this function unchanged — there is only one budget ledger.

### `bootstrap_source()` — 152–155
```python
def bootstrap_source():
    source = matched.bootstrap_source()
    require(source.count("typed_matched_worker") == 2, "PRACTICE_BOOTSTRAP_TEMPLATE_CHANGED")
    return source.replace("typed_matched_worker", "typed_practice_worker")
```
`matched.bootstrap_source()` (`typed_matched_launch.py:137-177`) returns a 38-line stdlib-only child
program: it reads `config.json` and the manifest from `ROOT`, checks `source_sha`, `inputs_sha256`,
`manifest["inputs"]`, the design subset (`MANIFEST_STUDY_DESIGN`), the per-row `files_sha256`/
`files_bytes` join (`MANIFEST_INPUT_JOIN`), refuses a dirty process (`FRESH_PROCESS`), verifies and
execs `cncm/typed_source_attestation.py` (`BOOTSTRAP_PIN`, `BOOTSTRAP_PATH`, `BOOTSTRAP_BYTES`),
installs the attestor, inserts both sys.path roots, sets
`os.environ['CAS_META2_RUN_TEACHING_CYCLE'] = '1'`, then
`from cncm import typed_matched_worker` and calls
`typed_matched_worker.run(CONFIG, root=ROOT, results=RESULTS, artifacts=ARTIFACTS, attestor=ATTESTOR)`.
The two occurrences of `typed_matched_worker` are the import (line 172) and the call (line 175).
**A new launcher must supply its own `bootstrap_source()` with the same `count == 2` check** (RK5:
"keeping the count check", `DESIGN_REVIEW_PIPELINE_LENS.md:231`), replacing with
`typed_pointer_worker`.

### `render_worker()` — 158–177
```python
def render_worker():
    tree = ast.parse(worker_template.render_worker())
    replacements = {"INNER_RUNNER": bootstrap_source(), "RESULT_SCHEMA": RESULT_SCHEMA,
                    "FAILURE_SCHEMA": FAILURE_SCHEMA, "MAX_WALL_SECONDS": MAX_WALL_SECONDS}
    ...
    require(found == set(replacements) and timeouts == 1 and regions == 1, "PRACTICE_WORKER_TEMPLATE_CHANGED")
    tree.body[0] = ast.Expr(ast.Constant(CANDIDATE + ": ten-pass practice with held-back questions; "
                                         "no learning claim is made by the worker."))
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"
```
Hard-codes, and why each matters: the four replaced constants; the single keyword
`timeout=MAX_WALL_SECONDS + 1800` rewritten to `MAX_WALL_SECONDS` (169–170); the single subscript
`config['region']` rewritten to `config['design']` (171–173); the exact counts `timeouts == 1` and
`regions == 1`; and the body[0] docstring. The template is
`aws/recurrent_cjt_launch.render_worker()` (`worker_template` at line 30). **This function is
module-level and cannot be inherited safely** — its `replacements` are read from *this module's*
globals, so a subclass-only approach would render the practice worker. A new launcher must define its
own `render_worker()` (copy, with its own globals).

### `evidence_contract()` — 180–190
```python
def evidence_contract():
    names = {"results/result.json": "terminal envelope", "results/result.json.sha256": "envelope digest",
             "results/artifacts/manifest.json": "artifact inventory"}
    names.update({"results/artifacts/" + name: "complete typed-practice worker evidence"
                  for name in _probe().EXPECTED_ARTIFACTS})
    return run_evidence.contract(EXPERIMENT["profile"], [
        run_evidence.requirement(key, title, kind="json" if key.endswith(".json") else "file")
        for key, title in names.items()], notes=[…3 strings…])
```
Hard-codes: the three fixed keys, the probe source of names, `EXPERIMENT["profile"]` = `"typed_practice_v1"`,
and the three note strings (including "1470 main, 16 interference and 2 validation replay updates,
1488 actual total"). `run_evidence.contract` (`aws/run_evidence.py:142-161`) sets
`required_count = len(entries)`, `cannot_shrink_after_a_failure: True`,
`worker_may_not_amend_required: True`. Verified `required_count == 83`.

### `package_data_files()` — 193–195
```python
def package_data_files():
    return tuple(sorted(set(shared.PILOT + name for name in PACKAGING_SOURCES)
                        | {shared.WORKER_REQUIREMENTS} | {item["path"] for item in frozen_inputs()}))
```
`shared.PILOT = "research/CAS_META_2_COMPOSITION/"` (`graph_training_curriculum_launch.py:35`);
`shared.WORKER_REQUIREMENTS = PILOT + "requirements-gpu.txt"` (`:148`).

### `git_package_bytes(root, commit, name)` — 198–204
```python
def git_package_bytes(root, commit, name):
    require(type(commit) is str and shared.HEX40.fullmatch(commit), "PRACTICE_SOURCE_COMMIT")
    shared.checked_names([name])
    permitted = (name.startswith("research/") or name in contract.MATERIAL
                 or (name.startswith("cncm/") and name.endswith(".py")))
    require(permitted, "PRACTICE_SOURCE_MEMBER_SCOPE")
    return shared._run_git(["-c", "core.autocrlf=false", "show", commit + ":" + shared.GIT_PREFIX + name], root)
```
**This is the RK5 blocker for the checkpoint files.** The allowlist is exactly three clauses:
any `research/…` path; a path named in the contract's `MATERIAL`; a `cncm/….py`. The 18 checkpoint
files live under `records/typed_practice_001/receipt_<seed>/checkpoints/…`, which matches **none** of
them, so the build fails with `PRACTICE_SOURCE_MEMBER_SCOPE` (`DESIGN_REVIEW_PIPELINE_LENS.md:62`).
The new launcher must widen the allowlist to the new contract's `MATERIAL` **and** add the 18 files to
that MATERIAL (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:243-245`). Note `core.autocrlf=false`
and `git show <commit>:<GIT_PREFIX><name>` — the package is built from committed blobs, which is why an
uncommitted `.py` fails at `:222` with `PRACTICE_INPUT_NOT_COMMITTED`.

### `build_practice_package(output, *, source_sha, git_bytes_fn=None)` — 207–255
Builds `source.zip` + `receipt.json` into `records/…/package_<sha8>`; requires a fresh path under
`ROOT / "records"` (`PRACTICE_FRESH_PACKAGE_PATH`), an exact 40-hex commit
(`PRACTICE_SOURCE_COMMIT`), the packaging sources to be byte-identical to the working copy
(`PRACTICE_PACKAGING_SOURCE_NOT_COMMITTED:<name>`, 218–219), every inventory row to match its committed
blob (`PRACTICE_INPUT_NOT_COMMITTED:<path>`, 222), the member/expanded/archive bounds (226, 238–239,
247), and stamps the manifest with `frozen_budget` (`main_updates: 1488-18 = 1470`,
`interference_updates: 16`, `validation_replay_updates: 2`), `typed_design`, `inputs`,
`inputs_sha256` and `transport` (229–237).

### `reservation_plan_for(design)` — 258–263
```python
def reservation_plan_for(design):
    plan = shared.reservation_plan()
    plan["runtime_seconds_max"] = INSTANCE_SECONDS_MAX        # 14400
    plan["task_scope"] = "cncm_typed_practice_001"
    plan["frozen_budget"] = json.loads(canonical(design))
    return plan
```
`shared.reservation_plan()` (`graph_training_curriculum_launch.py:1513-1523`) returns
`{"instance_count": 1, "runtime_seconds_max": 7200, "instance_type": "g7.2xlarge", "account_id": "807562639912",
"region": "us-west-2", "automatic_retries": 0, "on_demand_hourly_usd_max": "2.52",
"ancillary_reserved_usd": "1.48", "task_scope": "graph_first_teaching_candidate_001_curriculum_002",
"campaign_scope": "cas-meta2-composition-campaign", "frozen_budget": {…5 frozen keys…}}`.
Hard-codes: the practice `task_scope` (which is what labels the ledger row —
`DESIGN_REVIEW_PIPELINE_LENS.md:60`: "The budget ledger would be silently mislabeled") and the
runtime envelope. A new `task_scope` such as `"cncm_typed_pointer_001"` is mandatory.
`budget.validate_plan(plan, "15.00")` (`aws/budget.py:116-127`) computes
`bound = 2.52 * 14400 / 3600 + 1.48 = 11.56` and requires the reservation `>= bound`
(`RESERVATION_BELOW_DECLARED_COST_BOUND`); with `"7.00"` it refuses. Test 179 asserts exactly this.

### `class TypedPracticeProvider(matched.TypedMatchedProvider)` — 266–371
Base class: `TypedMatchedProvider(lifecycle.CandidateProvider)` (`typed_matched_launch.py:281`).

| method | lines | what it hard-codes | what a new provider must do |
|---|---|---|---|
| `reservation_plan(self)` | 267–269 | `require(hasattr(self,"bound_config"), "PRACTICE_RESERVATION_CONFIG_REQUIRED")`; returns `reservation_plan_for(self.bound_config["design"])` | keep shape, inherit the new module-level `reservation_plan_for` |
| `reserve(self, amount)` | 271–280 | `require(not self._reserved and amount == shared.RESERVATION_USD, "PRACTICE_RESERVATION_CALLER")` (so the caller's amount must be **`"7.00"`**, the shared constant, even though the recorded reservation is `"15.00"`); records `RESERVATION_USD` via `self.budget.reserve_budget(self.job, self.source_sha, self.archive_sha256, RESERVATION_USD, self.reservation_plan(), self.ledger_path)`; returns `{**receipt, "aws_side_reservation": self._record_aws_side_reservation(receipt)}` | change the frozen amount to the new reservation (still `"15.00"` unless the envelope changes, DG9) |
| `_transient(self, error)` | 282–287 | client-error code ∈ `TRANSIENT_ERROR_CODES`; `ConnectionError`/`TimeoutError`; else class name ∈ `TRANSIENT_ERROR_CLASSES` | inherit unchanged |
| `wait(self, job, timeout, *, poll_interval=5.0)` | 289–316 | see C.3 | inherit unchanged |
| `_user_data(self, bucket)` | 318–357 | practice `JOB_PATTERN` (`"PRACTICE_WATCHDOG_JOB"`), `bound_config["bucket"] == bucket` (`"PRACTICE_CONFIG_BUCKET"`), the anchor `"PY=''"` exactly once (`"PRACTICE_BOOTSTRAP_CONFIG_ANCHOR"`), the delimiter `"CNCM_PRACTICE_BOOTSTRAP_BODY"` (`"PRACTICE_BOOTSTRAP_DELIMITER"`), `--on-boot=14100s`, `13500s` outer timeout | new pattern check + new delimiter and comment names |
| `bind_authority(self, authority)` | 359–365 | calls the **module-level** `validate_authority` (practice candidate and config: `:359-360`) → hard fail with the new candidate; binds `self.bound_config = json.loads(canonical(authority["worker_config"]))`, `self.worker_name, self.result_schema = WORKER_NAME, RESULT_SCHEMA`, and `self.failure_statuses = ("WORKER_FAILED", "REMOTE_WORKER_FAILED", "TYPED_PRACTICE_FAILED")` | **must be overridden**: new validator, new `WORKER_NAME`, new `failure_statuses` including the new worker's FAILED status |
| `_worker_config(self, bucket)` | 367–371 | `require(hasattr(self,"bound_config"), "PRACTICE_AUTHORITY_NOT_BOUND")`; `require(self.region == BOUNDS["region"], "PRACTICE_PROVIDER_REGION")`; `require(bucket == self.bound_config["bucket"], "PRACTICE_PROVIDER_BUCKET")`; returns `json.loads(canonical(self.bound_config))` | update the error-prefix strings; logic unchanged |

## C.2 `PACKAGING_SOURCES` — 69–71, and what must be added

```python
PACKAGING_SOURCES = tuple("aws/" + name + ".py" for name in (
    "typed_practice_launch", "typed_matched_launch", "recurrent_cjt_launch", "graph_training_candidate_launch",
    "graph_training_curriculum_launch", "run_evidence", "budget", "__init__"))
```

Every name here is prefixed with `shared.PILOT` = `research/CAS_META_2_COMPOSITION/` by
`package_data_files()` (194), committed at `build_practice_package` (217–219), and **asserted byte-equal
to the working copy** at 218–219 → `PRACTICE_PACKAGING_SOURCE_NOT_COMMITTED:<name>`. The rule
(`DESIGN_REVIEW_PIPELINE_LENS.md:63`) is: *the new launcher and every launcher it imports must be
listed*. So the pointer launcher's tuple must be

```python
PACKAGING_SOURCES = tuple("aws/" + name + ".py" for name in (
    "typed_pointer_launch",                       # NEW — the launcher itself
    "typed_practice_launch", "typed_matched_launch", "recurrent_cjt_launch",
    "graph_training_candidate_launch", "graph_training_curriculum_launch",
    "run_evidence", "budget", "__init__"))
```
(`typed_practice_launch` stays because a copied/subclassing pointer launcher imports it; if the pointer
launcher is a **copy** that imports only `matched`/`lifecycle`/`shared`/`worker_template`/`run_evidence`/
`budget`, then `typed_practice_launch` may be dropped — but only if nothing in the module imports it.)

## C.3 How the job is launched, the bucket, the reservation, and the wait loop

### Launch
`main()` (406–443) parses `--execute`, `--package`, `--source-sha`, `--request`, `--request-sha256`,
`--authority`, `--authority-sha256`, `--receipt-dir`, `--owner-authorization`, `--ledger-path`,
`--profile` (412–415); with no `--execute` it prints `{"status": "PLAN_ONLY", "design": DESIGN, "bounds": BOUNDS, "provider_calls": 0, "reservation_created": False}` and touches nothing (421–424). With
`--execute` it requires all seven inputs (`"PRACTICE_EXPLICIT_INPUTS"`), verifies the two file hashes
(`"PRACTICE_REQUEST_AUTHORITY_FILE_HASH"`), validates request, authority and owner, validates the ledger
path, constructs the provider with
`clients=lifecycle._clients(args.profile)`, `client_error=lifecycle._client_error()`,
`source_archive=lifecycle._locate_archive(request["archive_sha256"])` (435–438), then calls
`execute(...)`.

`execute(...)` (391–403) validates all three records, resolves and checks the provider's ledger path
(`"PRACTICE_PROVIDER_LEDGER_MISMATCH"`), requires `isinstance(provider, TypedPracticeProvider)`
(`"PRACTICE_PROVIDER_REQUIRED"`), calls `provider.bind_authority(authority)`, and delegates to
`lifecycle.execute` with its own four injected callables.

`lifecycle.execute(request, authority, provider, *, ledger_path, receipt_dir, owner_authorization_path, validate_request_fn, validate_authority_fn, evidence_contract, validate_reserved_transition_fn)`
(`aws/graph_training_candidate_launch.py:687-816`) is the fixed sequence:

1. validate request + authority (704–705);
2. owner record hash match (`"OWNER_AUTHORIZATION_RECORD_MISMATCH"`, 709) and `require_owner_record_bounds` (714–719);
3. request/authority job + source equality (`"REQUEST_AUTHORITY_MISMATCH"`, 720–722) and the two hash
   equalities (`"REQUEST_AUTHORITY_HASH_MISMATCH:" + key`, 723–724);
4. **fail closed before the reservation**: `provider.source_archive` must exist and hash to
   `request["archive_sha256"]` (726–735, `"CANDIDATE_SOURCE_ARCHIVE_REQUIRED_BEFORE_RESERVATION"`);
5. `ledger_before = read_ledger(ledger_path)`; `validate_reservation_scope(...)` (737–738);
   `require(not any(entry["job"] == request["job"] ...), "JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY")` (739–741);
6. `prepare_evidence(receipt_dir …)` and write `intent.json` including `ledger_before` and
   `owner_record_bounds` (742–749);
7. write `evidence_contract.json` and check `"EVIDENCE_CONTRACT_SCHEMA"` /
   `"EVIDENCE_CONTRACT_AUTHORITY_MISMATCH"` (753–761); `provider.configure_evidence(directory, evidence_contract)` (762);
8. inside `try:` — `preflight = validate_preflight(provider.preflight())` → `preflight.json` (774–775);
9. **`reservation = provider.reserve(RESERVATION_USD)`** (776) — note this passes the *candidate*
   module's `RESERVATION_USD`, which is imported from the curriculum module (`graph_training_candidate_launch.py:32`)
   and is therefore `"7.00"`, **not** the study's `"15.00"`. That is why
   `TypedPracticeProvider.reserve` requires `amount == shared.RESERVATION_USD` and then records its own
   `RESERVATION_USD` of `"15.00"` (274–277);
10. `ledger_after = read_ledger(ledger_path)` (777); `validate_reserved_transition_fn(ledger_before, ledger_after, reservation, request)` (778);
11. `require(reservation.get("aws_side_reservation", {}).get("status") == "RECORDED", "AWS_RESERVATION_RECORD_REQUIRED")` (779–780) → `reservation.json` (781);
12. `permit = {"job","source_sha","archive_sha256","manifest_sha256","reservation","preflight","resource_plan": scope()}` (783–787);
13. **`launched = provider.launch(request["job"], permit)`** (788) → `launch.json` (789);
14. **`outcome = provider.wait(request["job"], timeout=RESOURCE_PLAN["instance_seconds_max"])`** (790–791);
15. **`collected = provider.collect(request["job"])`** (792);
16. `finally: cleanup = provider.cleanup(request["job"], collection_verified=verified)` (810–815);
    status is `AWS_CANDIDATE_FINISHED` / `AWS_CANDIDATE_FAILED` / `AWS_CANDIDATE_LAUNCH_FAILED` (796–800).

`provider.launch` is the curriculum provider's (`graph_training_curriculum_launch.py:884-…`):
`require(job == self.job and self._reserved and not self._launch_called, "CURRICULUM_LAUNCH_STATE")`;
the permit check `CURRICULUM_PERMIT_INVALID` (888–893); `bucket = self._bucket_name()`;
`worker_role = self.job + "-worker"`; `self.source_archive` bytes re-hashed (`CURRICULUM_SOURCE_ARCHIVE_HASH`);
`self._ensure_bucket(s3)`; `put_object input/source.zip` and `input/config.json`
(= `canonical(self._worker_config(bucket))`); IAM role + job-only policy + instance profile + wait; a
security group with all egress revoked and **only TCP 443** re-authorised; `bootstrap = self._user_data(bucket)`;
first default subnet in `AZ_PREFERENCE` (`CURRICULUM_NO_SUBNET_IN_AN_AVAILABLE_ZONE`); `run_instances`
with `ImageId=frozen["ami"]`, `InstanceType="g7.2xlarge"`, `MinCount=MaxCount=1`, `ClientToken=self.job`,
`InstanceInitiatedShutdownBehavior="terminate"`, `MetadataOptions={"HttpTokens":"required","HttpEndpoint":"enabled"}`,
gp3 75 GiB encrypted EBS, tags `cas_meta_job`. The AMI is `ami-0fbbd0facbc9e3cff`
(`graph_training_curriculum_launch.py:87`).

### The bucket
`self._bucket_name()` (`graph_training_curriculum_launch.py:787-788`) is
```python
def _bucket_name(self):
    return self.job + "-" + RESOURCE_PLAN["account"]
```
so the bucket is `job + "-807562639912"`. It is created by `_ensure_bucket` (790–802) with
`LocationConstraint == self.region`, tagged `cas_meta_job`, and a full public-access block. The same
string is produced independently by `worker_config` (`typed_practice_launch.py:96`) and re-checked
against `self.bound_config["bucket"]` inside `_user_data` (`:321`) and `_worker_config` (`:370`). The
observed value: `cas-meta2-tprac-20260918234544-daeb6497-m-20260917-807562639912` (63 chars).
S3 enforces `[a-z0-9][a-z0-9-]{1,61}[a-z0-9]` → RK4.

### The reservation
`provider.reserve(amount)` (271–280) → `budget.reserve_budget(...)` (see F). Then
`validate_reserved_transition(before, after, receipt, request, *, expected_plan)` (374–388):
`current["revision"] == prior["revision"] + 1` (`"RESERVATION_REVISION_MISMATCH"`);
`current["reservations"][:-1] == prior["reservations"]` (`"RESERVATION_NOT_APPEND_ONLY"`);
`current["previous_state_sha256"] == budget.digest(budget.encoded(prior))` (`"RESERVATION_PREDECESSOR_MISMATCH"`);
the new entry's `job`/`source_sha`/`archive_sha256` equal the request
(`"RESERVATION_IDENTITY_MISMATCH:" + key`);
`entry["status"] == budget.STATUS` and `budget.amount(entry["reserved_usd"]) == budget.amount(RESERVATION_USD)`
(`"PRACTICE_RESERVATION_AMOUNT_FROZEN"`);
`entry["plan"] == expected_plan` and `entry["plan_sha256"] == budget.digest(budget.encoded(expected_plan))`
(`"RESERVATION_RESOURCE_PLAN_MISMATCH"`);
`receipt["ledger_sha256"] == after["ledger_sha256"]` (`"RESERVATION_RECEIPT_HASH_MISMATCH"`).

### The wait / transient-error loop — 289–316
```python
def wait(self, job, timeout, *, poll_interval=5.0):
    require(timeout == shared.RESOURCE_PLAN["instance_seconds_max"], "PRACTICE_WAIT_CALLER")
    deadline = time.monotonic() + INSTANCE_SECONDS_MAX
    transient = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {"worker_status": "REMOTE_TIMED_OUT"}
        try:
            outcome = super().wait(job, min(remaining, shared.RESOURCE_PLAN["instance_seconds_max"]),
                                   poll_interval=poll_interval)
        except Exception as error:
            if not self._transient(error) or transient >= MAX_TRANSIENT_WAIT_ERRORS:
                raise
            transient += 1
            self._event("wait_transient_error", "RETRYING", error=type(error).__name__,
                        detail=str(error)[:300], count=transient)
            time.sleep(max(5.0, min(30.0, poll_interval * 6)))
            continue
        if outcome.get("worker_status") != "REMOTE_TIMED_OUT":
            return outcome
```
Why it exists: the inherited poll refuses any timeout above the shared 7,200 s plan
(`require(job == self.job and self._instance_id is not None and 0 < timeout <= RESOURCE_PLAN["instance_seconds_max"], "CURRICULUM_WAIT_STATE")`,
`graph_training_curriculum_launch.py:1007-1009`), and the inherited poll has no SDK retries, so a
network blip on the operator's laptop would end a 2-hour job and terminate the instance. The
practice's version accumulates 14,400 s in segments the parent accepts, resumes over transient
errors, and ends only on a terminal instance state, the worker's own result, or a non-transient error.
Test coverage: `tests/test_typed_practice_study.py:227-262`.

The parent poll itself (1005–1042) is worth knowing: it polls `s3.get_object(Bucket, Key="results/result.json")`
with a 128 MiB body bound, requires `result["schema"] == getattr(self, "result_schema", RESULT_SCHEMA)`
→ `"CURRICULUM_RESULT_IDENTITY"` (1018–1020), and returns `{"worker_status": "REMOTE_FAILED"}` when
`result["status"] in getattr(self, "failure_statuses", ("REMOTE_WORKER_FAILED",))` (1023–1025), else
`{"worker_status": "REMOTE_FINISHED"}` (1026); a `terminated`/`shutting-down` instance returns
`REMOTE_FAILED` with `instance_state` (1038–1040); the loop's expiry returns `REMOTE_TIMED_OUT` (1042).

### Why `failure_statuses` is load-bearing — curriculum lines 1018, 1023, 1096
* **1018–1020** — the poll demands `result.get("schema") == getattr(self, "result_schema", RESULT_SCHEMA)`.
  The pointer launcher's `RESULT_SCHEMA` **must be byte-identical to the pointer worker's**
  `RESULT_SCHEMA` (`typed_practice_worker.py:38` is `"cncm.typed-practice-worker-result/0.1"`; the
  launcher repeats it at `:37` and `_probe()` re-checks the equality). A mismatch raises
  `CURRICULUM_RESULT_IDENTITY` and the job is read as neither finished nor failed.
* **1023–1025** — a result whose `status` is in `failure_statuses` is reported as `REMOTE_FAILED`, so
  the lifecycle records a clean worker failure instead of a launch failure. Since the pointer worker
  will report `"TYPED_POINTER_FAILED"` (or whatever the new triple is), the tuple at
  `typed_practice_launch.py:365` must be widened/replaced; otherwise a failed worker is read as
  `REMOTE_FINISHED`.
* **1096** — in `_collect_declared`, a result whose status is in `failure_statuses` skips the artifact
  demand: `collected["artifacts_available"] = False`, `collected["reason"] = "REMOTE_WORKER_FAILED"`,
  `_collect_partial(...)` (1095–1103). The comment at 1097–1099 records the attempted lesson: "A
  failed worker never reaches the artifact upload, so demanding a manifest here would turn a clean,
  fully recorded worker failure into a confusing launch failure". If the new status is missing from
  the tuple, a failed job demands a manifest that cannot exist.
`_artifact_name(entry)` is `graph_training_curriculum_launch.py:1582`.

## C.4 Result schema and collection path (curriculum `:1018`, `:1023`, `:1096`)

The three lines the task names are the three places the launcher's view of the worker's result is
fixed, all quoted above. The surrounding contract they enforce: the worker's own
`results/result.json` must carry `schema` (exact match), `status` (member of `failure_statuses` iff
failed), and `artifacts` (a list whose entries name the files, read at 1090–1092 via
`_artifact_name`). The collection path is:
`collect(job)` (1061–1071) → `_collect_declared(job)` (1073–…) → `_verify_collection(...)`;
`_collect_declared` first fetches `results/result.json.sha256` and requires it to equal
`digest(self._result_raw)` (`"CURRICULUM_RESULT_SHA_MISMATCH"`, 1080–1083), writes
`curriculum_result.json` and `curriculum_result.json.sha256` into the evidence directory, and seeds
the `collected` dict with keys `result`, `sha256`, `result_sha256`, `artifacts`,
`artifact_expectations`, `artifacts_collected`, `artifacts_missing` (1086–1094).
`_collect_partial` (1044–1059) additionally best-effort fetches `results/result_partial.json` and
`results/failure.json` into `collected["preserved"]`.

---

# D. `records/typed_practice_001/evaluate_gates.py` — the gate reader to copy

252 lines. Docstring 1–16 (the unit of evidence is a **question**, `query_id`). `ROOT = Path(__file__).resolve().parents[2]`
(line 27) = `CNCM`; both `ROOT` and `ROOT / 'research/CAS_META_2_COMPOSITION'` go on `sys.path` (28–30).
Constants 32–36.

## D.1 The integrity chain I0–I4, exact line ranges and what each compares

| Check | Lines | What it compares | Failure code |
|---|---|---|---|
| **I0** | 149–154 | `study["jobs"]` must be a list of dicts whose `model_seed`s, as strings, equal `sorted(str(s) for s in contract.MODEL_SEEDS)`, and every job must have a string `receipt_dir`. On failure `jobs` is set to `[]`. | `'I0:STUDY_MUST_HAVE_EXACTLY_THE_THREE_SEEDS_WITH_RECEIPTS'` |
| **I1** | 158–168 | `receipt/result.json` → `completed_deliverable is True and cleanup.complete is True`; `artifacts/worker_report.json` → `status == worker.SUCCESS_STATUS`; `artifacts/manifest.json` → `set(worker.EXPECTED_ARTIFACTS) <= {row["name"]}`. Imports `from cncm import typed_practice_worker as worker` at line 162. | `'I1:%d' % seed`, or `'I1:%d:%s' % (seed, type(error).__name__)` on `(OSError, ValueError, KeyError, TypeError)`; the exception path `continue`s to the next seed |
| **I2** | 169–181 | `artifacts/protocol_material.json` → `held_back_record_ids == held` **and** `excluded_record_ids == excluded` (re-derived locally at 136); every `record_id` appearing in the 10 `pass_%02d_batches.jsonl` files plus `interference_batches.jsonl` must be in `trained_set`; and the total number of log lines must equal `main_updates + INTERFERENCE_UPDATES` (= 1470 + 16 = 1486) | `'I2:%d'` / `'I2:%d:%s'` |
| **I3** | 182–189 | `artifacts/initial_checkpoint.json["metadata"]["model_state_identity"]` must equal the same field of `records/typed_matched_001/receipt_<seed>_m/collected/results/artifacts/initial_checkpoint.json` (`MATCHED_RECEIPTS` at line 36) — i.e. the same random start as the matched study | `'I3:%d'` / `'I3:%d:%s'` |
| **I4** | 190–199 | `artifacts/replay_report.json` and `worker_report.json`: `main_training_delta["optimizer_updates"] == main_updates` (1470); `interference_delta["optimizer_updates"] == INTERFERENCE_UPDATES` (16); `global_actual_work["totals"]["optimizer_updates"] == main_updates + INTERFERENCE_UPDATES + REPLAY_UPDATES` (1488); `len(replay["replays"]) == 2`; `len(replay["reloads"]) == 3` | `'I4:%d'` / `'I4:%d:%s'` |
| **scoring load** | 200–206 | loads `course_p00`, `course_p01`, `course_p10` and `heldback_p02/04/06/08` via `_rows` (77–79, which reads `<phase>_scoring.json` and returns `{record_id: bool(correct)}`) | `'I1:%d:SCORING_%s'` and `continue` — the seed is dropped entirely |

**RK8 in one line.** I1 names `cncm.typed_practice_worker` at line 162 and I3 compares against the
*matched* study's `initial_checkpoint.json` at 184–185. A pointer container can never match the
matched study's ^6-only `model_state_identity`, so every seed would fail I3 and the reader would print
`VOID` (`DESIGN_REVIEW_PIPELINE_LENS.md:77-80`). The new reader must move outside `cncm/` and
`cas_meta2/` (`records/typed_pointer_001/evaluate_gates.py`) with a new I1 (new worker module) and a
new I3 that instead verifies the in-job-recorded DG4 evidence:
(a) `matched._framework(torch, device, seed)`'s ^6 identity equals the matched start,
(b) two independent builds of the whole model are identical, (c) the three seeds' identities are
pairwise different, (d) the start is identical with and without the checkpoint check
(`DESIGN_REVIEW_PIPELINE_LENS.md:140-146`; V3 at `:181` warns that an I3 comparing the job to itself is
vacuous).

## D.2 The exact gate arithmetic

```python
ALPHA = Fraction(1, 100)                 # 32
MIN_IMPROVED_KINDS = 2                   # 33
MIN_IMPROVED_WORLDS = 2                  # 34
```

**The per-seed exact one-sided binomial test** — `binomial_upper_tail(b, n)`, lines 39–43:
```python
def binomial_upper_tail(b, n):
    """Exact one-sided P(X >= b | n, 1/2)."""
    if n == 0:
        return Fraction(1)
    return Fraction(sum(comb(n, k) for k in range(b, n + 1)), 2 ** n)
```
Exact rational arithmetic (`fractions.Fraction`, `math.comb`), never floating point: `n == 0` → `1`,
`binomial_upper_tail(10, 10) == Fraction(1, 1024)`, `binomial_upper_tail(5, 10) == Fraction(638, 1024)`
(`tests/test_typed_practice_study.py:312-314`).

**The paired counts** — `paired(before, after, keys)`, lines 46–49:
```python
def paired(before, after, keys):
    b = sum(1 for k in keys if not before[k] and after[k])
    c = sum(1 for k in keys if before[k] and not after[k])
    return {'wrong_to_right': b, 'right_to_wrong': c, 'pairs': len(keys)}
```
`b` counts **discordant** questions that went wrong→right; `c` those that went right→wrong (ties
excluded from both). `n = b + c`, i.e. the test conditions on the discordant pairs.

**The per-seed test** — `seed_test(before, after, keys, kind_of, world_of=None)`, lines 57–70:
```python
    test = paired(before, after, keys)
    b, c = test['wrong_to_right'], test['right_to_wrong']
    p = binomial_upper_tail(b, b + c)
    improved = [k for k in keys if not before[k] and after[k]]
    kinds = sorted({kind_of[k] for k in improved})
    worlds = sorted({world_of[k] for k in improved}) if world_of is not None else None
    passed = b > c and p <= ALPHA and len(kinds) >= MIN_IMPROVED_KINDS
    if world_of is not None:
        passed = passed and len(worlds) >= MIN_IMPROVED_WORLDS
    test.update(p_one_sided=str(p), p_float=float(p), improved_kinds=kinds, improved_worlds=worlds, passed=passed)
```
So a seed passes iff **all** of:
1. `b > c` strictly;
2. `p = P(X >= b | b+c, 1/2) <= 1/100` (exact `Fraction` comparison; `p_one_sided` is recorded as the
   exact rational string, `p_float` as a float for reporting);
3. the improved questions span **≥ 2 distinct kinds**;
4. when `world_of` is supplied, the improved questions span **≥ 2 distinct held worlds**.

**Minimum passing `b` with `c = 0`:** 7 (`2^-7 = 1/128 = 0.0078125 <= 0.01`); `b = 6` gives
`1/64 = 0.015625 > 0.01` and fails. This is the registered reminder at
`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:251-252`, and it is the number the pointer protocol
must restate after the FP2/DG3 removals.

**The question unit** — `question_outcomes(record_correct, questions)`, lines 52–54:
`{query_id: all(record_correct[r] for r in records)}` — a question is correct only if **every** one of
its records is correct.

**How the three seeds combine** — lines 226–235:
```python
    complete = not failures and len(seeds) == 3
    gates = {'integrity': {'pass': complete, 'failures': failures}}
    if complete:
        for name in ('G_LEARN_p0_to_p10', 'MORE_PRACTICE_p1_to_p10', 'TRAINED_p0_to_p10', 'TRAINED_p1_to_p10'):
            gates[name] = {'pass': all(s[name]['passed'] for s in seeds.values()),
                           'per_seed': {str(k): s[name]['passed'] for k, s in seeds.items()}}
        label = 'LEARNS_NEW_WORLDS' if gates['G_LEARN_p0_to_p10']['pass'] else 'NO_TRANSFER_TO_NEW_WORLDS'
        flags = {'more_practice_helps_new_worlds': gates['MORE_PRACTICE_p1_to_p10']['pass'],
                 'trained_questions_rise_from_start': gates['TRAINED_p0_to_p10']['pass'],
                 'trained_questions_rise_with_more_practice': gates['TRAINED_p1_to_p10']['pass']}
    else:
        label, flags = 'VOID', {}
```
**Unanimity, not pooling**: each seed is tested on its own and `all(...)` requires all three to pass.
The docstring gives the reason (lines 9–11): "the seeds share the encoder, data and schedule, so they
are replications, not extra sample size." The four per-seed tests are:

| test | comparison | keys | `world_of`? |
|---|---|---|---|
| `G_LEARN_p0_to_p10` (216) | `heldq[0]` → `heldq[10]` | `eligible` | yes |
| `MORE_PRACTICE_p1_to_p10` (217) | `heldq[1]` → `heldq[10]` | `eligible` | yes |
| `TRAINED_p0_to_p10` (218) | `trainq[0]` → `trainq[10]` | `sorted(trained_questions)` | no |
| `TRAINED_p1_to_p10` (219) | `trainq[1]` → `trainq[10]` | `sorted(trained_questions)` | no |

`heldq[n]` are the per-checkpoint question outcomes for the *held* questions at every loaded
checkpoint `{0,1,2,4,6,8,10}` (207); `trainq[n]` exist only for checkpoints `(0,1,10)` (208), because
the trained questions are only ever scored in the three full-course runs.

## D.3 The label vocabulary and every path that yields `VOID`

Output schema: `'cncm.typed-practice-gate-reading/0.3'` (line 238). Top-level keys of the reading
(238–245): `schema`, `protocol`, `alpha`, `min_improved_kinds`, `min_improved_worlds`, `label`, `flags`,
`gates`, `seeds`, `held_worlds`, `held_questions`, `eligible_questions`, `shortcut_questions`,
`shortcut_answers`, `held_records`, `trained_records`, `excluded_records`, `main_updates`. Observed
values: `alpha "1/100"`, `min_improved_kinds 2`, `min_improved_worlds 2`, `label
"NO_TRANSFER_TO_NEW_WORLDS"`, `held_questions 50`, `eligible_questions 45`, `shortcut_questions 5`,
`held_records 127`, `trained_records 358`, `excluded_records 79`, `main_updates 1470`; `gates` keys
`['G_LEARN_p0_to_p10','MORE_PRACTICE_p1_to_p10','TRAINED_p0_to_p10','TRAINED_p1_to_p10','integrity']`.

Three labels only:

| label | exact condition | anchor |
|---|---|---|
| `'LEARNS_NEW_WORLDS'` | `complete` is `True` **and** `gates['G_LEARN_p0_to_p10']['pass']` is `True`, i.e. all three seeds pass the eligible-held test | 232 |
| `'NO_TRANSFER_TO_NEW_WORLDS'` | `complete` is `True` and that gate is `False` | 232 |
| `'VOID'` | **any other outcome.** Exactly two ways: (a) `failures` is non-empty, (b) `len(seeds) != 3`. `flags` is `{}` and no gate is evaluated | 236–237 |

**Every path into `VOID`:** any I0 failure (149–154, which also empties `jobs`); any I1 failure
including the `except` branch (166–168) and the I1 failure inside the scoring-load `except` (204–206,
which `continue`s); any I2, I3 or I4 failure (180–182, 188–189, 198–199); or a study whose job list
does not contain exactly the three model seeds. In the practice study all four integrity checks PASSed
(`gates.integrity = {"failures": [], "pass": true}`) and the label came from the gate, not from
integrity. In the dry run, by construction, `I3` fails for all three seeds, so the label is `VOID` —
which is exactly what `PREFLIGHT_PASS` requires (E.3).

**FP1 is a label-level defect, not an integrity defect.** With the unchanged primary gate, a pure
input-flag copier scores `b = 10`, `c = 0` on the 10 eligible DIRECT_READ questions (definition 5 +
context 5) over 5 worlds, so `p = 1/1024 = 0.0009765625 <= 0.01`, and it also clears ≥ 2 kinds and
≥ 2 worlds → `G_LEARN_p0_to_p10` passes in every seed and the program prints `LEARNS_NEW_WORLDS`
(`DESIGN_REVIEW_PIPELINE_LENS.md:101-108`). The fix is structural, not prose: `LEARNS_NEW_WORLDS` must
require the **RELATIONAL** test (correspondence 5, edge_account 5, reach 9, analogy 5, parts 5 = 29
eligible questions over 5 worlds), the all-kinds result becomes a reported flag, and a test must show
that a flag-copy-only outcome receives no label (P12). FP2 adds that the relational tier is not
flag-free: an edge-free rule `parts(whole = declared_whole) = participants − whole` solves 3 of the 5
eligible held parts questions, so a frozen per-question flag-rule baseline must remove flag-solved
questions from the population before the run. DG3 adds that 2 of the 9 eligible held reach questions
depend on hidden alphabetical node order and must be either made world-independent (a per-world rank
feature) plus a registered rank-only baseline, or removed before the run.

## D.4 How the 45 eligible questions and the 5 removed shortcut questions are derived, and the digests

**The population.** `held_questions = contract.held_back_questions(frozen)` (`evaluate_gates.py:139`;
`practice_contract.py:120-127`) maps each held `query_id` to its sorted held record ids: **50
questions** over **127 held records** in **5 held worlds**. `trained_questions` is built the same way
from the trained records (141–144) and totals 189 questions.

**The removed shortcut questions.** `shortcut_answers(frozen, trained)` (109–116):
```python
def shortcut_answers(frozen, trained):
    """Per kind, the most common trained answer in alias form (ties by text): the input-blind constant."""
    bank_order = _bank_order(frozen)
    counts = {}
    for row in frozen['registry']:
        if row['record_id'] in trained:
            counts.setdefault(row['query']['kind'], Counter())[alias_form(_admissible(frozen, row)[0], bank_order)] += 1
    return {kind: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for kind, c in counts.items()}
```
The answer is put into **the learner's own output symbols** first (`alias_form`, 93–96): node
references `world-<64hex>/n<k>` become per-world `N<k>` (`NODE_REF` at 89) and world ids become their
global `W<i>` index in the sorted bank order (`WORLD_REF` at 90, `_bank_order` at 105–106). Then the
most common *trained* admissible answer per kind is taken, ties broken by the text ascending. This is
the "most common thing the machine could emit while ignoring the input".

`eligible_questions(frozen, trained, questions)` (119–129) then walks every held question, takes
`row = by_id[records[0]]`, computes `forms = {alias_form(value, bank_order) for value in _admissible(frozen, row)}`
(the full **admissible set**, not just the first answer) and moves the question to `shortcut_hit` iff
`shortcut[kind]` is among those forms, else to `eligible`:
```python
        (shortcut_hit if shortcut.get(row['query']['kind']) in forms else eligible).append(q)
```
Returns `(sorted(eligible), sorted(shortcut_hit), shortcut)`.

Observed: **45 eligible, 5 shortcut** (`gates` reading and `tests/test_typed_practice_study.py:110`).
The 5 removed questions are held **`reach`** questions whose admissible set contains the direct
answer: the frozen shortcut for `reach` is exactly
`{"state": "DIRECT", "via": null}` (`tests/test_typed_practice_study.py:111`), which is the `_reach`
result returned at `checker.py:133`, and `records/typed_practice_001/PRACTICE_STUDY_RESULT.md:28`
labels the removed group "held-back shortcut questions (of 5; `reach` → `DIRECT`)".
`shortcut_answers` is reported in full for all eight kinds in the reading.

The per-kind composition of the 45 is reported, not re-derived, in this specification:
DIRECT_READ 10 (definition 5 + context 5) and RELATIONAL 29 (correspondence 5, edge_account 5, reach 9,
analogy 5, parts 5) — `DESIGN_REVIEW_PIPELINE_LENS.md:105-108` and `:225`. Sum 39.
`UNCERTAIN: that the remaining 6 of the 45 eligible questions are exactly the role_set questions is an
arithmetic inference here (45 − 10 − 29 = 6), consistent with the held-back role_set record count of 6
in the frozen schedule stats (`held_back_kinds` in
`records/typed_practice_001/admission_001/20260917/authority.json` → `worker_config.design.schedule`),
but I did not re-run `eligible_questions` to confirm it.`

**The digests recorded.** Three digests of the holdout side are frozen in the schedule stats and
re-checked by the plan's tests (P1). Exact values, read from
`records/typed_practice_001/admission_001/20260917/authority.json` → `worker_config.design.schedule`:

| key | value |
|---|---|
| `held_back_record_ids_digest` | `668e6ce73c426d1fcf8f2391e1a08d90c045ffb37fba95fc64e2658f5369ab1d` |
| `excluded_record_ids_digest` | `b82108e14554a9fe746a7cfcb1e2cb181a99a3019dc39a3596805f10934c2621` |
| `batches_digest` | `daf95831dd6f054f0395e9a868c513650982bd1912247adc698ca067433bc857` |
| `source_schedule_digest` (the matched MIXED schedule the practice passes were built from) | `1772c0a53933aa92ea7dfb6b2ce53dcd1089cb3634b089427caba3369977d275` |
| `retention_record_ids_digest`, `interference_batches_digest`, `development_digest` | carried in the same design dict (`practice_contract.py:233-238`); the retained panel is 96 records and the development panel 59 packets |

These are computed by `source.digest(...)` over canonical JSON (`practice_contract.py:168-169`), and the
same values must appear in the pointer contract's design because the pointer study reuses the split
and the schedule unchanged (`HANDOFF…:253-254`, P1).

---

# E. The four driver scripts under `records/typed_practice_001/`

All four set `ROOT = Path(__file__).resolve().parents[2]` (= `CNCM`) and prepend
`ROOT` and `ROOT / 'research/CAS_META_2_COMPOSITION'` to `sys.path`.

## E.1 `prepare_study.py` — 108 lines

**Purpose** (docstring 1–4): freeze the three practice-study jobs **before the first result**;
package and rehearsal only, no launch. "One owner record per job, because the inherited lifecycle
allows one job per owner record."

**CLI:** none. `if __name__ == '__main__': prepare()` (108).

**Imports/anchors:** `from aws import typed_practice_launch as launch` (17);
`from cas_meta2.typed_teaching import practice_contract as contract` (18);
`PROTOCOL = ROOT / 'docs/CNCM_TYPED_PRACTICE_STUDY_v0.1.md'` (20);
the owner question/answer/terms constants (21–27); `MAXIMUM_NEW_RESERVATION_USD = '45.00'` (28).

**What it writes:**

| Artifact | Line | Notes |
|---|---|---|
| `records/typed_practice_001/admission_001/` | 42–43 | `output.mkdir()` — **fails if it already exists**, so a freeze is never re-done in place |
| `research/CAS_META_2_COMPOSITION/records/typed_practice_001/package_<sha8>/source.zip` and `receipt.json` | 44–46 | `launch.build_practice_package(package_parent / ('package_' + source_sha[:8]), source_sha=source_sha)` |
| `admission_001/<seed>/{owner.json, request.json, authority.json}` | 52–72 | one directory per seed; every file written with `write()` (31–34) which uses `path.open('xb')` — create-only — and returns `{'path','bytes','sha256'}` |
| `admission_001/rehearsal/**` | 77–86 | the real `source.zip` unzipped (`ZipFile`), with a path-escape check (`target.is_relative_to(rehearsal.resolve())`, 82), plus the first job's `config.json` |
| `admission_001/rehearsal_stdout.txt`, `rehearsal_stderr.txt` | 91–92 | raw bytes of the rehearsal child |
| `admission_001/study.json` | 96–104 | the freeze record |

**The rehearsal** (75–95): parses `launch.bootstrap_source()` with `ast.parse` (87–88), runs it with
`subprocess.run([sys.executable, '-B', '-I', '-c', code, str(rehearsal)], cwd=rehearsal, capture_output=True, timeout=900)`,
then **asserts** `proc.returncode != 0 and b'LINUX_WORKER_REQUIRED' in proc.stderr` (93) and
`result['status'] == 'TYPED_PRACTICE_FAILED'` (95). The rehearsal is therefore also a live test of the
packaged loader and of the Windows refusal ordering.

**Asserts (not `require`) — five of them:** `assert not dirty` (40,
`'COMMIT_FIRST_THE_PACKAGE_IS_BUILT_FROM_HEAD'`), `assert len(MODEL_SEEDS) * float(launch.RESERVATION_USD) <= float(MAXIMUM_NEW_RESERVATION_USD)` (41), and the three rehearsal asserts (82, 93, 95).
`git rev-parse HEAD` and `git status --porcelain -- .` are the two git calls (38–39).

**`study.json` — the full key set** (from `admission_001/study.json`): top level
`["automatic_retries", "jobs", "jobs_execute_sequentially", "maximum_new_reservation_usd",
"numeric_runs_completed", "package_archive", "package_archive_sha256", "package_manifest_sha256",
"protocol_sha256", "rehearsal", "reservation_per_job_usd", "schema", "source_sha", "status"]`;
each element of `jobs` has key set `["authority", "condition", "job", "model_seed", "owner",
"receipt_dir", "request"]`, where `request`/`authority`/`owner` are pins
`{"path": <absolute>, "bytes": <int>, "sha256": <hex64>}`. Real values:

```json
{"schema": "cncm.typed-practice-study-admission/0.1",
 "status": "FROZEN_BEFORE_FIRST_RUN",
 "source_sha": "daeb649799c991f8f0eddf539269dc7f6f3cd6f8",
 "package_archive_sha256": "d02f2aae96a6063f09e821d97878bbcf39ece1ea19c88bcb7d30e31df9818ca1",
 "package_manifest_sha256": "e42848ed40063d33d9837bdded6c2c4f8dcb258770a3ae716dfe813fa4d71206",
 "protocol_sha256": "300c50b1bf62a323bcd1d37867ea54f9006f4e284298cba861679281b9c88945",
 "maximum_new_reservation_usd": "45.00", "reservation_per_job_usd": "15.00",
 "jobs_execute_sequentially": true, "automatic_retries": 0, "numeric_runs_completed": 0,
 "rehearsal": "EXACT_PACKAGE_WINDOWS_REFUSAL_BEFORE_NUMERIC_IMPORT",
 "jobs": [{"job": "cas-meta2-tprac-20260918234544-daeb6497-m-20260917",
           "condition": "MIXED_SAME_ITEMS", "model_seed": 20260917,
           "receipt_dir": "…\\records\\typed_practice_001\\receipt_20260917", …}, …]}
```
(`package_archive` is present in the file as well; it is an absolute path string.) The file is one
line of canonical JSON; `study.json` sha256 is
`0a329f32db44920773638d8b62cb1641b55ae592e41bc5a1d4bb7f274f37a3b6`
(`records/typed_practice_001/PRACTICE_STUDY_RESULT.md:8-9`).

**`request.json` — full key set** `["archive_sha256", "job", "launch_authorized", "manifest_sha256",
"schema", "source_sha"]` (355 bytes):
```json
{"archive_sha256":"d02f2aae…818ca1","job":"cas-meta2-tprac-20260918234544-daeb6497-m-20260917",
 "launch_authorized":false,"manifest_sha256":"e42848ed…d71206",
 "schema":"cncm.typed-practice-request/0.1","source_sha":"daeb649799c991f8f0eddf539269dc7f6f3cd6f8"}
```

**`authority.json` — full key set** (58,570 bytes) `["archive_sha256", "automatic_retries", "candidate",
"design_sha256", "evidence_contract_sha256", "inputs_sha256", "instance_seconds_max", "instance_type",
"job", "jobs", "manifest_sha256", "max_wall_seconds", "optimizer_updates_max",
"owner_authorization_sha256", "region", "reservation_usd", "schema", "source_sha", "training",
"worker_config"]`. Non-`worker_config` values observed:
`candidate "CNCM_TYPED_PRACTICE_LEARNING_001"`, `design_sha256` (64 hex),
`evidence_contract_sha256 "1211fed0c24f58c4fa2c22766f5a7fc97d3fa2884a90849d6a10e26fd5f6b449"`,
`inputs_sha256 "3302329de93249d3c1e90b83cb5646c64eb0fecaa951a22348342bc7d1f101c8"`,
`instance_seconds_max 14400`, `instance_type "g7.2xlarge"`, `jobs 1`, `max_wall_seconds 12600`,
`optimizer_updates_max 1488`, `owner_authorization_sha256 "b851e01c…a405bb"`, `region "us-west-2"`,
`reservation_usd "15.00"`, `schema "cncm.typed-practice-authority/0.1"`, `automatic_retries 0`,
`training true`. `worker_config` key set `["bucket", "design", "inputs", "inputs_sha256", "job", "schema", "source_sha"]`
with `bucket == job + "-807562639912"`, `inputs` = 236 rows of `{"bytes","path","sha256"}`, and
`design` keys:
`["automatic_retries","boundary","candidate","condition","d_model","depths","development_digest",
"development_packets","encoder_seed","excluded_record_ids","full_course_checkpoints",
"held_back_record_ids","held_worlds","holdout_rule","holdout_unit","initialization",
"instance_seconds_max","instance_type","interference_batch","interference_batches_digest",
"interference_trained_records_only","interference_updates","jobs","launch_enabled",
"learner_max_updates_ceiling","learning_on_held_back_established","main_targets","max_core_calls",
"max_input_tokens","max_wall_seconds","model_seed","model_seeds","optimizer_class","optimizer_config",
"optimizer_foreach","optimizer_fused","owner_approval","package","partial_course_is_success",
"pass_checkpoints","passes","prediction_depth","projection_scope","purpose","region",
"registered_learner_unchanged","replay","replay_counts","replay_updates","reporting_loss",
"reservation_usd","retention_packets","retention_record_ids_digest","schedule","source_attestation",
"source_seed","training_loss","worker_deadline_seconds"]` — 58 keys, of which `schedule` is the
16-key stats dict quoted in D.4. Note `"registered_learner_unchanged": True` and
`"initialization": "REGISTERED_RANDOM_SAME_AS_MATCHED_STUDY_PER_MODEL_SEED"` are exactly the two DG10
fields that would be false for the pointer machine (`DESIGN_REVIEW_PIPELINE_LENS.md:171-175`).

**`owner.json` — full key set** (1,142 bytes) `["answered_utc_date", "bounds", "candidate", "condition",
"job", "model_seed", "owner_instruction_raw", "owner_question", "owner_selected_option_terms",
"schema", "scope"]`:
```json
{"answered_utc_date":"2026-09-18",
 "bounds":{"automatic_retries":0,"instance_seconds_max":14400,"instance_type":"g7.2xlarge","jobs":1,
           "max_wall_seconds":12600,"optimizer_updates_max":1488,"region":"us-west-2",
           "reservation_usd":"15.00","training":true},
 "candidate":"CNCM_TYPED_PRACTICE_LEARNING_001","condition":"MIXED_SAME_ITEMS",
 "job":"cas-meta2-tprac-20260918234544-daeb6497-m-20260917","model_seed":20260917,
 "owner_instruction_raw":"Practice test (Recommended)",
 "owner_question":"Which AWS experiment should I build and launch first? …",
 "owner_selected_option_terms":"Same machine, same random start, 10x more practice …",
 "schema":"cncm.typed-practice-owner/0.1",
 "scope":"One of three practice-study seeds under the owner-approved $45.00 cap; no automatic retry."}
```
`bounds` must satisfy `_check_bounds` against `launch.BOUNDS` exactly (type and value), and
`owner_instruction_raw` must be non-empty and verbatim. For the pointer study the owner text is the
2026-09-19 order quoted in `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:77`
(*"do option 1, pointer answers plus the checkpoint check …"*) plus the two accepted corrections
(`:88-91`) — three new records, one per job (DG9).

## E.2 `execute_study.py` — 50 lines

**Purpose** (docstring 1): explicit sequential execution of the frozen three-job study; stop on the
first failure.

**CLI** (48–50):
```
python execute_study.py --execute STUDY_JSON SHA256
```
`if len(sys.argv) != 4 or sys.argv[1] != '--execute': raise SystemExit('Explicit --execute STUDY SHA256 required')`,
then `execute(sys.argv[2], sys.argv[3])`.

**The `stop_unless` failure discipline** (13–16):
```python
def stop_unless(condition, reason):
    """Explicit stop: never an assert, which `python -O` would remove and let the study spend on."""
    if not condition:
        raise SystemExit('PRACTICE_STUDY_STOPPED:' + reason)
```
Every guard in the file is a `stop_unless`; there is no `assert` (`HANDOFF…:374`). The guard codes and
what each protects:

| code | line | condition |
|---|---|---|
| `STUDY_SHA256` | 22 | `sha256(path.read_bytes()).hexdigest() == expected_sha256` — the **second CLI argument is the sha256 of `study.json` itself**, so the frozen bytes cannot be swapped after the operator read them |
| `STUDY_SHAPE` | 24 | `study['status'] == 'FROZEN_BEFORE_FIRST_RUN' and len(study['jobs']) == 3` |
| `PROTOCOL_CHANGED` | 25–26 | sha256 of `docs/CNCM_TYPED_PRACTICE_STUDY_v0.1.md` equals `study['protocol_sha256']` — the protocol document is pinned into the freeze |
| `PIN:<name>` | 29–30 | for each of `request`, `authority`, `owner`: `len(raw) == pin['bytes'] and sha256(raw).hexdigest() == pin['sha256']` |
| `EXISTING_ATTEMPT_NO_AUTOMATIC_RETRY` | 31 | `not Path(job['receipt_dir']).exists()` |
| `INCOMPLETE_JOB` | 37 | the launcher's returned code is `0` |
| `JOB_NOT_DELIVERED_OR_NOT_CLEANED_UP` | 40–41 | `lifecycle['completed_deliverable'] is True and lifecycle['cleanup']['complete'] is True` |

**The sequential-per-job behaviour** (27–42): a plain `for job in study['jobs']:` loop with no
concurrency, no thread, no retry — the docstring of the hand-out states the reason: us-west-2 GPU quota
is 8 vCPU, so **one job at a time** (`HANDOFF…:346`). Per iteration it

1. re-pins all three records (28–30),
2. refuses an existing receipt dir (31),
3. prints `{"starting": job["job"]}` (32),
4. calls the launcher **in-process** with exactly seven arguments (33–36):
   ```python
   code = launch.main(['--execute', '--request', job['request']['path'], '--request-sha256', job['request']['sha256'],
       '--authority', job['authority']['path'], '--authority-sha256', job['authority']['sha256'],
       '--owner-authorization', job['owner']['path'], '--receipt-dir', job['receipt_dir'],
       '--ledger-path', str(launch.CANONICAL_LEDGER)])
   ```
5. `stop_unless(code == 0, 'INCOMPLETE_JOB')` (37),
6. re-reads `receipt_dir/result.json` and requires delivered + cleaned-up (39–41),
7. prints `{"complete": job["job"], "seed_summary": evaluate_gates.seed_summary(receipt)}` (42) — a
   per-job readout for the operator log, not a gate.

**After the loop** (43–45): `reading = evaluate_gates.evaluate(path)` on the study file, written
**create-only** to `path.parent / 'gate_reading.json'` with `open('xb')` (44), then printed as
`{"label": reading['label'], "gates": reading['gates']}`. The printed label **is** the claim status
(`evaluate_gates.py:1-4`). The observed run log is
`records/typed_practice_001/execute_study_log.txt` (7,792 bytes); the produced reading is
`records/typed_practice_001/admission_001/gate_reading.json` (17,183 bytes).

## E.3 `preflight_dry_run.py` — 282 lines

**Purpose** (docstring 1–15): drive the practice worker end to end with a **non-neural stand-in
learner**, $0, no torch, no GPU. Everything the worker does is real except the neural parts.

**CLI** (278–281): `python preflight_dry_run.py SCRATCH_DIR`; `scratch.mkdir(parents=True, exist_ok=False)` (228).

**What it stands in for** — `install_stand_ins()` (146–168), applied before `worker.run`:

| real thing | stand-in | line |
|---|---|---|
| `gpu_adapter._cuda` | a lambda returning a `SimpleNamespace` fake torch (`__version__ "2.11.0+cu128"`, `version.cuda "12.8"`, `cuda.get_device_name → "NVIDIA RTX PRO 4500 (stand-in)"`, no-op `reset_peak_memory_stats`, no-op `use_deterministic_algorithms`, tf32 flags) and `"cuda:0"` | 147–153 |
| `rpa_learning_worker.verify_worker_packages` | `lambda root: {"source_files": ["stand-in"]}` | 154 |
| `encoder.build_frozen_typed_encoder` | `lambda *a, **k: SimpleNamespace(work_counters=lambda: {})` | 155 |
| `matched_worker._framework` | `lambda torch_, device, seed: SimpleNamespace(module=None, seed=seed)` | 156 |
| `practice_learner.PracticeCourseLearner` | `StandInLearner` (55–143): weights are a sha256 hash chain over sealed batches; counters follow the real learner's counting (slot counts × depth per packet, real `slots.compile_slots` counts); `state()`, `export_checkpoint`, `restore_checkpoint` implemented | 157 |
| `base._state` | `lambda torch_, learner: learner.state()` | 158 |
| `base._encoding_checks` | `lambda *a, **k: {"stand_in": True}` | 159 |
| `checker.derive_target` | the **real** function, memoised by `query_id + ":" + focus_world_id` | 160–167 |
| `checker.check_answer` | `lambda source, query, answer: {"correct": int(answer["stand_in"][:2], 16) % 3 == 0}` — a fast stand-in, deliberately **not** a real answer | 168 |

**Two extra proof apparatuses:**

1. `CreateOnlyPublisher` (171–206): a background thread scanning `results/` several times a second. It
   stores the first sha256 seen per relative path, skips `*.partial`/`*.tmp`, and records a conflict if
   stored bytes later differ — the exact rule whose AWS-side failure is `EVIDENCE_DIGEST_CONFLICT`.
2. `_write_audit` (212–223) installed with `sys.addaudithook` (230): records every write-mode `open`
   of a path under an active `results/` whose name does not end `.partial` (`WRITE_VIOLATIONS`).

**The run** (226–255): for each of the three seeds it builds a job name, creates
`scratch/receipt_<seed>/collected/results`, builds the config with
`contract.make_config(ROOT, source_sha="d"*40, job=job, bucket=job + "-807562639912", model_seed=seed)`,
and calls `worker.run(config, ROOT, results, results / "artifacts", attestor=SimpleNamespace(snapshot=lambda: {"stand_in": True}))`
**with the audit hook active and the publisher running**. Then it writes a synthetic
`receipt/result.json` = `{"completed_deliverable": True, "cleanup": {"complete": True}}` (253) so the
real gate reader's I1 passes, and collects `publishing[seed]` = `{"scans", "files", "conflicts",
"direct_writes_under_results", "staging_left", "partial_left"}`.

**Then the real gate reader runs on the three dry-run receipts** (258–263).

**The `PREFLIGHT_PASS` condition** (263):
```python
verdict = "PREFLIGHT_PASS" if (failures == expected and reading["label"] == "VOID" and clean) else "PREFLIGHT_FAIL"
```
where `expected = ["I3:%d" % seed for seed in contract.MODEL_SEEDS]` (260) and `clean` is
`all(not row["conflicts"] and row["files"] > 0 and not row["direct_writes_under_results"] and not row["staging_left"] and not row["partial_left"] for row in publishing.values())` (261–262).
So **exactly three integrity failures (I3 for each seed) and nothing else**, a `VOID` label, and a
clean publishing/staging audit. The docstring states the logic (13–15): "Expected: integrity I1, I2 and
I4 PASS, and I3 FAILS (the stand-in's start is not the matched study's start), so the label is VOID.
Anything else is a bug found for $0." The `main()` exit code is `0` only for `PREFLIGHT_PASS` (281–282).
The summary dict (264–273) has schema `"cncm.typed-practice-preflight-dry-run/0.2"` and keys `verdict`,
`expected_integrity_failures`, `observed_integrity_failures`, `label_on_stand_in`,
`worker_seconds_per_seed`, `create_only_publisher_simulation`, `main_updates_per_seed`, `gate_population`
(the six counts `held_questions/eligible_questions/shortcut_questions/held_records/trained_records/excluded_records`), and `boundary`.
The produced result file is `records/typed_practice_001/preflight_dry_run_result.json` (1,502 bytes).

Consequence for the pointer dry run: it must use the **pointer** gate reader, its own
`staging = results.parent / "<new>_staging"` name (the current one hard-codes
`results.parent / "practice_staging"` at 247), and a new `expected` integrity-failure list — because
the pointer reader's I3 is redefined by DG4 and may legitimately fail or pass for the stand-in.

## E.4 `holdout_audit.py` — 79 lines

**Purpose** (docstring 1–16): derive the held-back split **from the frozen RULES independently of the
contract's constants**. Local, post-hoc and pre-run audit only; it imports the private checker because
it reads correct answers, "which is why the worker never runs it: the contract carries the frozen
result, and a test asserts that this module re-derives exactly that result from the rules."

**CLI:** none — `if __name__ == '__main__':` (74–79) loads the material, calls `derive(frozen)` and
prints counts (with the full values for `held_worlds`, `answer_only_exposed`, `exposure_counts`).

**What it re-derives:**

1. `shape_signature(world)` (32–36): the eligibility key — `(len(sorted node refs), tuple(sorted (position[source], position[target]) for each contains edge over sorted-ref positions), position.get(world['declared_whole']))`. A world is **eligible** only if its signature is unique across the whole 64-world bank (59).
2. `record_text(row)` (39–40): canonical JSON of the row minus `record_id` — the same text the contract
   hashes to detect mentions (`practice_contract._record_text:84-85`).
3. `answer_texts(frozen)` (43–48): per record, the canonical JSON of the **admissible answer values**
   from `checker.derive_target(course._public(frozen['bank'], row['source_world_id']), row['query'])["admissible_answers"]`.
4. `derive(frozen, answers=None)` (51–71): builds `shapes = defaultdict(list)` over the bank; `eligible`
   = course worlds whose signature is unique; `exposure[w]` = every record on another world that
   mentions `w` **in its text or in its answers**; `held_worlds` = the 5 eligible worlds with the
   smallest exposure, **ties by world id** (`sorted((len(exposure[w]), w) for w in eligible)[:5]`);
   `held` = all records focused on a held world; `excluded` = the union of exposures minus `held`;
   `answer_only` = excluded records that do **not** mention a held world in their text (the analogy
   answer-carriers); `trained` = the rest. Returns
   `{'eligible_worlds', 'held_worlds', 'held', 'excluded', 'answer_only_exposed', 'trained', 'exposure_counts'}`.

**What the test asserts about it** (`tests/test_typed_practice_study.py:114-124`): `derived["held_worlds"] == list(contract.HELD_WORLDS)`,
`derived["answer_only_exposed"] == sorted(contract.ANSWER_EXPOSED_RECORD_IDS)` (6 ids,
`practice_contract.py:49-55`), `(derived["held"], derived["trained"], derived["excluded"]) == (held, trained, excluded)`,
and `len(derived["eligible_worlds"]) == 12`. The pointer study keeps this file's derivation unchanged
and re-uses the frozen split (P1), so the audit stays a re-derivation of *the same* rules.

---

# F. The budget ledger

## F.1 The exact structure

Two copies exist in the workspace; **only one is canonical**.

| Path | Role |
|---|---|
| `<WN>\_worktrees\meta1\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\research\CAS_META_2_COMPOSITION\records\budget\campaign_ledger.json` | **CANONICAL** — the launcher's `CANONICAL_LEDGER`; 264,965 bytes at read time |
| `<CNCM>\research\CAS_META_2_COMPOSITION\records\budget\campaign_ledger.json` | **STALE SNAPSHOT** — 187,160 bytes; `revision 84`, `updated_utc "2026-09-17T10:55:41.083129+00:00"`, `total_reserved_usd "501.00"`, 86 reservations, last job `cas-meta2-tmat-20260917072721-e6bdf305-m-20260919`. It contains **none** of the three practice-study reservations. The launcher refuses it (`TYPED_CANONICAL_META1_LEDGER_REQUIRED`). |

Top-level key set of the ledger (both copies, identical): `["amendment", "approval", "no_automatic_refund",
"owner_task_cap_usd", "predecessor", "previous_state_sha256", "remaining_unreserved_usd", "reservations",
"revision", "schema", "scope", "total_reserved_usd", "updated_utc"]`.

Real head values of the canonical copy at read time:

```json
{"schema": "cas-meta-campaign-budget/2",
 "revision": 87,
 "previous_state_sha256": "fa6304ddc8e6aea0763f5beac9addc568ef681144f4d3cb639dcddf62a916e38",
 "owner_task_cap_usd": "5000.00",
 "total_reserved_usd": "546.00",
 "remaining_unreserved_usd": "4454.00",
 "no_automatic_refund": true,
 "scope": "All CASformer campaign and further research, inclusive of prior META1 reservations",
 "updated_utc": "2026-09-19T03:13:52.026331+00:00",
 "reservations": [ … 89 entries … ],
 "predecessor": {"path": …, "sha256": …}, "approval": {"path": …, "sha256": …}, "amendment": {"path": …, "sha256": …}}
```

The `amendment` binding is the owner's 2026-09-12 instruction that raised the operating cap from
$400.00 to $5000.00 with a $400.00 floor; `aws/budget.py:27-43` carries the same three numbers as
`CAP_ORIGINAL`, `CAP_FLOOR`, `CAP`, and `validate_amendment` (`:148-172`) refuses any amendment whose
`evidence_kind` is not `"owner_instruction_in_session"`
(`OWNER_AMENDMENT_PROVENANCE_MUST_BE_HONEST`).

**A reservation entry — exact key set** (`aws/budget.py:394`):
`["archive_sha256", "job", "plan", "plan_sha256", "reserved_usd", "reserved_utc", "source_sha", "status"]`.
Real last entry: `job` = `"cas-meta2-tprac-20260918234544-daeb6497-m-20260919"`, `reserved_usd` = `"15.00"`
(a **string**), `status` = `"RESERVED_NO_AUTOMATIC_REFUND"` (= `budget.STATUS`, `budget.py:44`).
`plan` key set: `["account_id", "ancillary_reserved_usd", "automatic_retries", "campaign_scope",
"frozen_budget", "instance_count", "instance_type", "on_demand_hourly_usd_max", "region",
"runtime_seconds_max", "task_scope"]` — exactly `reservation_plan_for(design)` from C.1, with
`frozen_budget` = the whole 58-key design dict.

**The sidecars** (`budget.paths`, `budget.py:257-259`): `<ledger>.lock` and `<ledger>.history/`.
`read_locked` (303–326) requires the history directory to contain exactly `f"{n:08d}.json" for n in
range(revision + 1)` (`PENDING_OR_MISSING_BUDGET_HISTORY_FAIL_CLOSED`), each entry's revision to match
its index (`HISTORY_REVISION_MISMATCH`), each `previous_state_sha256` to hash the previous entry
(`BROKEN_BUDGET_HISTORY_CHAIN`), append-only reservation lists (`BUDGET_HISTORY_NOT_APPEND_ONLY`), and
the history tail to equal the head (`LEDGER_HISTORY_MISMATCH`). Observed: 88 files (revisions 0–87).
`publish` (329–351) writes the write-ahead history file first, then a temp file in the ledger's
directory and `os.replace` onto the ledger (with retry on Windows `PermissionError`).

## F.2 `CANONICAL_LEDGER` in the launcher

`aws/typed_matched_launch.py:48-50`:
```python
CANONICAL_LEDGER = (WORKSPACE_HOME / "_worktrees/meta1/cas_only_reasoner/"
    "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/"
    "records/budget/campaign_ledger.json")
```
with `WORKSPACE_HOME` found by walking up from `…/aws` to the parent named
`"FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"` (`typed_matched_launch.py:20-21`).
`aws/typed_practice_launch.py:68` re-exports it as `CANONICAL_LEDGER = matched.CANONICAL_LEDGER`, and
`execute_study.py:36` passes `str(launch.CANONICAL_LEDGER)` as `--ledger-path`.
`validate_ledger_path` (`typed_matched_launch.py:130-134`) requires the resolved path to equal this
exactly, so the pointer launcher needs **no** override here — it should keep delegating to
`matched.validate_ledger_path`.

Do not confuse this with `aws/budget.py:21-22`:
`ROOT = Path(__file__).resolve().parents[1]; CANONICAL_LEDGER = ROOT / "records" / "budget" / "campaign_ledger.json"`,
which resolves to the **CNCM-tree (stale) copy**. It is only a default argument
(`budget.py:354, 382, 387`) and is never used on the launch path, because every call site passes the
validated meta1 path explicitly.

## F.3 How a new reservation is recorded — never by hand

The builder does **nothing** to the ledger. The chain is:

1. `execute_study.py:33-36` passes `--ledger-path str(launch.CANONICAL_LEDGER)`;
2. `launch.main` (434) → `launch.validate_ledger_path(...)` → `execute(...)` (439–440) → requires
   `Path(provider.ledger_path).resolve() == ledger_path` (396) and passes it to `lifecycle.execute`;
3. `lifecycle.execute` (776) calls `provider.reserve(RESERVATION_USD)`;
4. `TypedPracticeProvider.reserve` (271–280) builds `self.reservation_plan()` and calls
   `self.budget.reserve_budget(self.job, self.source_sha, self.archive_sha256, RESERVATION_USD, self.reservation_plan(), self.ledger_path)`;
5. `budget.reserve_budget` (387–399) validates the plan against the amount
   (`validate_plan`, `:389`), takes the exclusive lock, re-reads and re-validates the whole chain
   (`read_locked`), refuses a duplicate job id (`JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY`), builds the
   entry above, re-checks the campaign total (`CAMPAIGN_BUDGET_EXHAUSTED`), bumps `revision`,
   sets `previous_state_sha256` to the digest of the previous complete state, appends, recomputes
   `total_reserved_usd`/`remaining_unreserved_usd`/`updated_utc`, publishes, and returns
   `{"reservation": entry, "ledger_path", "ledger_sha256", "revision", "total_reserved_usd", "remaining_unreserved_usd"}`;
6. `lifecycle.execute` (777–781) re-reads the ledger, calls the injected
   `validate_reserved_transition` (374–388), and requires the AWS-side receipt
   (`provider._record_aws_side_reservation`, `graph_training_curriculum_launch.py:804-820`) to have
   `status == "RECORDED"` (`AWS_RESERVATION_RECORD_REQUIRED`).

For the pointer study, the **only** ledger-facing change a builder must make is in the new launcher's
`reservation_plan_for()`: a new `task_scope` (today `"cncm_typed_practice_001"`,
`typed_practice_launch.py:261`) so the ledger row is labelled correctly
(`DESIGN_REVIEW_PIPELINE_LENS.md:60`), plus the amount if the envelope changes. Hand-editing
`campaign_ledger.json` is both unnecessary and unsafe: `reservations_total` refuses a duplicate job id
(`DUPLICATE_JOB_RESERVATION`), refuses any status other than `RESERVED_NO_AUTOMATIC_REFUND`
(`REFUNDS_OR_STATUS_MUTATIONS_FORBIDDEN`), and the history chain check would reject a hand-written
head (`LEDGER_HISTORY_MISMATCH`).

---

# G. Tests

## G.1 `tests/test_typed_practice_study.py` — the 24 collected tests

The file defines **22 test functions** at lines 55–323 plus one helper (`_gates_module`, 31–35) and one
fixture (`_provider`, 185–194). One function is parametrised three ways, so the collected case count is
**24** — which is what `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:48` reports ("24 tests, ~128 s").

| # | test | line | one line |
|---|---|---|---|
| 1 | `test_held_back_is_whole_worlds_and_leak_free` | 55 | 5 worlds / 127 held / 358 trained / 79 excluded, 50 questions, every held world's records all held, no trained record mentions a held world, no question is split across sides, all 8 kinds held |
| 2 | `test_ten_identical_passes_train_only_trained_records` | 77 | `main_updates == len(batches) == 1470`, `updates_per_pass == 147`, cursors `range(len(batches))`, all ten passes identical, only trained records, occurrence ids unique |
| 3 | `test_interference_draws_only_trained_records` | 90 | 16 batches of 8, all from trained records |
| 4 | `test_update_bound_is_pinned_to_the_schedule` | 98 | `launch.OPTIMIZER_UPDATES_MAX == main_updates + 16 + 2`, `main_updates + 16 <= practice_learner.PRACTICE_MAX_UPDATES`, and `worker.expected_main_delta(stats)["optimizer_updates"] == 1470` |
| 5 | `test_gate_population_is_frozen` | 105 | the gate reader's `eligible_questions` returns `(45, 5)` and the `reach` shortcut is exactly `{"state": "DIRECT", "via": null}` |
| 6 | `test_holdout_split_rederives_from_its_rules_with_the_answer_checker` | 114 | `holdout_audit.derive(frozen)` reproduces `HELD_WORLDS`, the 6 answer-exposed ids, the three id lists, and 12 eligible worlds |
| 7 | `test_gate_counts_questions_and_one_flip_cannot_pass` | 127 | one improved question fails; seven in one kind fails; seven across two kinds passes with `p_one_sided == "1/128"`; a question is correct only if all its records are; one world fails the ≥2-world rule, two worlds pass |
| 8 | `test_publish_is_whole_and_create_only` | 147 | `worker._publish_bytes` writes 3 bytes, leaves no `.partial`, and a second call raises `PUBLISH_DESTINATION` |
| 9 | `test_artifact_contract_is_bounded_and_covers_every_checkpoint` | 154 | `EXPECTED_ARTIFACTS` unique, `< 500`, basenames only; contains the `course_p{00,01,10}`, `heldback_p{02,04,06,08}`, every `development_p*_scoring.json`, `pass_10_batches.jsonl`, `interference_updates.jsonl`, `retained.pt`, `replay_2_update.json`, `pass_01.pt`, `prelast.pt`; and `launch.evidence_contract()["required_count"] == len(names) + 3` |
| 10 | `test_time_envelope_is_ordered_and_longer_than_the_shared_two_hours` | 168 | 12300 < 12600 < 13500 < 14100 < 14400, the shared plan is 7200, and `BOUNDS` carries 12600 and `"15.00"` |
| 11 | `test_reservation_plan_admits_fifteen_dollars_for_four_hours_and_not_seven` | 175 | plan runtime 14400, `task_scope "cncm_typed_practice_001"`, `validate_plan(plan, "15.00") == Decimal("11.56")`, `"7.00"` raises `RESERVATION_BELOW_DECLARED_COST_BOUND`, `3 × 15.00 <= 45.00` |
| 12 | `test_reservation_uses_the_practice_amount_and_refuses_a_retry` | 197 | `reserve("7.00")` records `"15.00"` with runtime 14400; a second reserve raises; a provider with no budget raises `PRACTICE_RESERVATION_CALLER` |
| 13 | `test_reserved_transition_requires_the_frozen_fifteen_dollars` | 209 | a synthetic ledger at `"15.00"` passes, one at `"7.00"` raises `PRACTICE_RESERVATION_AMOUNT_FROZEN` |
| 14 | `test_wait_continues_past_the_shared_two_hour_segment` | 227 | two 7200 s segments; the caller must pass exactly 7200 or `PRACTICE_WAIT_CALLER` |
| 15 | `test_wait_survives_a_transient_network_error_and_not_a_real_one` | 241 | a `ConnectionError` is retried and the event `wait_transient_error` is emitted; `EndpointConnectionError` is transient, `NoCredentialsError` is not; a `ValueError("CURRICULUM_RESULT_IDENTITY")` propagates |
| 16 | `test_guest_watchdog_uses_the_practice_envelope` | 264 | the rendered user-data contains `--on-boot=14100s`, ` 13500s ` and `boot_deadline_seconds=14100`, and neither `6900` nor `4200s` |
| 17 | `test_rendered_worker_binds_the_practice_entrypoint` | 272 | `launch.render_worker()` parses and names `typed_practice_worker`, never `typed_matched_worker`, and carries `12600` |
| 18 | `test_practice_learner_changes_only_the_two_ceilings` | 278 | `validate_practice_limits` accepts the practice limits and raises `PRACTICE_LEARNER_LIMITS` on 2049 updates / 14401 s / 1000001 core calls; `practice_profile()["changes"] == "UPDATE_AND_WALL_CEILINGS_ONLY"` |
| 19 | `test_owner_record_must_name_its_own_job` | 288 | an owner record for the right job passes; the same record against a job with a different seed raises `PRACTICE_OWNER_JOB` |
| 20 | `test_worker_refuses_windows_before_any_numerical_import` | 299 | with `gpu_adapter.platform.system → "Windows"`, `worker.run` raises matching `LINUX_WORKER_REQUIRED`, the bucket is ≤ 63 chars, the design holds the split, and `results/result.json` says `TYPED_PRACTICE_FAILED` |
| 21 | `test_gate_arithmetic_is_exact` | 310 | `binomial_upper_tail` returns `1`, `Fraction(1,1024)`, `Fraction(638,1024)`; `paired` returns `{"wrong_to_right":1,"right_to_wrong":1,"pairs":3}` |
| 22 | `test_unfrozen_job_parameters_rejected` (×3 params: seed `20260920`, `-a-` instead of `-m-`, a trailing `-retry`) | 320 | every such job string raises from `contract.parse_job` |

**The self-contained `sys.path` block a new test file must repeat** — lines 15–18, verbatim:

```python
# Self-contained import path: do not depend on another test module having run first.
for _extra in (Path(__file__).resolve().parents[1], Path(__file__).resolve().parents[1] / "research/CAS_META_2_COMPOSITION"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))
```
followed by the module-level imports it enables (20–24):
```python
from cas_meta2.typed_teaching import practice_contract as contract
from cas_meta2.typed_teaching import practice_learner
from cncm import typed_practice_worker as worker
from aws import typed_practice_launch as launch
from aws import typed_matched_launch as matched_launch
```
and the three module constants (26–28): `ROOT = Path(__file__).resolve().parents[1]`,
`SOURCE = "a" * 40`, `JOB = "cas-meta2-tprac-20260918000000-aaaaaaaa-m-20260917"`.
The reason it must be repeated: other test modules rely on import side effects, so a test file that
assumes a prior module has already fixed `sys.path` passes or fails depending on collection order.

## G.2 How the tests avoid importing torch — the numeric-import guard

Lines 38–47:
```python
@pytest.fixture(autouse=True)
def public_only(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "numpy", "boto3", "botocore", "cas_cjt", "casformer"}:
            raise AssertionError("NUMERIC_PROVIDER_IMPORT:" + name)
        if name.endswith(("graph_teaching.final_panel", "graph_teaching.reference")):
            raise AssertionError("FINAL_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
```
An `autouse` fixture replaces `builtins.__import__` for the whole module, so **any** import of a
top-level `torch`, `numpy`, `boto3`, `botocore`, `cas_cjt` or `casformer` — from any module, at any
depth — raises `AssertionError("NUMERIC_PROVIDER_IMPORT:<name>")`, and any import of the final-panel or
reference modules raises `AssertionError("FINAL_IMPORT:<name>")`.

This works because the production code never imports a numeric module at import time:

* `cas_meta2/teaching_cycle/gpu_adapter.py` explicitly does not import torch at module level
  (docstring line 1) and imports it inside `_cuda()` at line 44, **after** the platform check;
* `cncm/typed_course_worker.py` imports torch only through `_cuda()` (line 331–332);
* the practice worker likewise (line 241–242), so importing `cncm.typed_practice_worker` is torch-free;
* `cas_meta2/typed_teaching/practice_contract.py` is documented "No teacher, final panel, numerical
  runtime or provider is imported here" (lines 5–6) and imports only `course_plan`, `source`,
  `matched_contract` and the standard library;
* `records/typed_practice_001/evaluate_gates.py` imports nothing numeric at module level — the private
  checker is imported lazily inside `_admissible` (line 100) and `practice_contract` at run time.

The mechanism is import-hook-based, not file-based: the guard fires only if a module is actually
imported during a test. Test 20 exploits it deliberately — it monkeypatches
`gpu_adapter.platform.system` so `_cuda()` raises **before** reaching `import torch`, which is why the
whole Windows-refusal path is testable with no torch installed.

---

# BUILDER CHECKLIST

Ordered. Every line names the deliverable, the finding it satisfies, and the existing anchor to copy
or replace. Numbers 1–7 and 9 are the hand-out's build plan
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:278-289`); 8 is the frozen protocol doc.

### Stage 0 — before any code (findings that change what is frozen, not what is written)

1. **Re-run the two uncaptured review lenses** (leaks/shortcuts/vacuity; can-it-learn) before writing
   design v0.2 — `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:258-269`. Deliverable: findings files
   under `records/typed_pointer_001/` (never under `cncm/` or `cas_meta2/` — RK9,
   `DESIGN_REVIEW_PIPELINE_LENS.md:82-88`).
2. **Freeze the FP2 per-question flag-rule baseline** and the **DG3 removal list** (or the rank feature
   plus its rank-only no-learning baseline) and state the resulting minimum passing `b` in the protocol
   — FP2 `DESIGN_REVIEW_PIPELINE_LENS.md:110-113`; DG3 `:135-138`; arithmetic `:251-252`; test P13 `:252`.
3. **Write `docs/CNCM_TYPED_POINTER_STUDY_v0.1.md`** with the RELATIONAL primary gate (FP1,
   `:101-108`), the frozen per-question baseline and removals, the checkpoint-check Phase A/B ordering
   (FP3, `:115-121`), the K=8 choice (DG1, `:124-128`), the rule embedding (DG2, `:130-133`), the
   "never the focus of a trained question" wording (DG5, `:148-151`), and the owner's verbatim text
   (`HANDOFF…:77`). Its sha256 becomes `study.json`'s `protocol_sha256`
   (`prepare_study.py:25-26`, `:99`).

### Stage 1 — the four pure/new source files (all under `cncm/` or `cas_meta2/`: commit before freezing)

4. **`research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_contract.py`** (pure).
   Copy the shape of `practice_contract.py:33-81` and `:195-250`. Must contain: a new `CANDIDATE`;
   a new `CONFIG_SCHEMA`; a new `JOB_PATTERN` whose study token is **≤ 5 chars** (RK4,
   `DESIGN_REVIEW_PIPELINE_LENS.md:52-55`; `practice_contract.py:35`, `:226`); `MATERIAL` extended with
   the **18 checkpoint files** pinned by sha256 (and the `MATERIAL`-based `git_package_bytes` allowlist
   in the launcher, RK5 `:62`); `input_inventory` = the matched wrapper plus the checkpoint rows
   (`matched_contract.py:173-178`); a new `DESIGN` without the two false fields
   (`"registered_learner_unchanged"`, the old `initialization`) and with a new planned-work formula
   (DG10, `:171-175`); deadlines; `parse_job`/`make_config`/`validate_config`
   (`practice_contract.py:77-81`, `:221-250`); and `require`/`canonical` re-exported.
   Imports `practice_contract` and re-uses `split`, `practice_schedule`, `interference_batches`,
   `retention_packets`, `development_packets`, `held_back_questions` **unchanged**
   (`HANDOFF…:253-254`).
5. **`.../typed_teaching/pointer_inputs.py`** (pure, deterministic, digested): per-world node flags,
   adjacency, domain-word ids, query kind/rule/argument marks, excerpt ids with world refs replaced by
   placeholders; never reads supports, cue, instruction or node order — `HANDOFF…:281`; RK3
   tokenize-once and pinned digest `DESIGN_REVIEW_PIPELINE_LENS.md:46-50`; V1 replacement checks `:179`;
   P9/P10 `:248-249`.
6. **`.../typed_teaching/pointer_learner.py`** (torch only when called): `PointerCourseLearner` per RK2
   (`:31-44`) with ONE container `module` holding every learned weight including the ^6 block from
   `matched._framework(torch, device, seed)` built **first**; own `__init__`, `predict`,
   `stage_batch`, `train_sealed_batch` (RK1 `:25-29`: finite grads on participating weights, ≥1 grad
   overall, `zero_grad(set_to_none=True)` + AdamW skips `None` grads — register it, log per-update which
   weights got grads), `export_checkpoint`, `restore_checkpoint`, `profile`; borrows
   `TypedCourseLearner._tensor_loss`; never calls `scope_parameters`; exposes `.torch`, `.encoder`,
   `.optimizer`, `.counters`, `.cursor`, `.model_revision`, `.failed`, `.run_identity_digest`
   (needed by `typed_course_worker.py:205-210`). Dense matmuls + one-hot, K=8 fixed with depth recorded
   only (DG1, `:124-128`); RMS-normalise each round (DG7, `:157-161`); prediction schema exactly
   `loss_plan.validate_prediction`'s field set, slots in `slot["symbols"]` order (DG6, `:153-155`);
   new `counters` key set matching the new `expected_main_delta` (A.2). Smoke S1–S9 before any spend
   (`:255-265`).
7. **`cncm/typed_pointer_worker.py`** — the file this spec's section A describes.
   * Own constants and `EXPECTED_ARTIFACTS` (< 500 files, unique, required_count = len + 3; P7
     `DESIGN_REVIEW_PIPELINE_LENS.md:246`) — section A.3.
   * Own `expected_main_delta` and the check in its place of
     `typed_practice_worker.py:174-180` and `:361` (DG10).
   * Reuse `_publish`, `_publish_bytes`, `_move_in`, `_append`, `_seal_predictions`, `_train_logged`,
     `_stage_and_train`, `_evaluate`, `_split_score` (`typed_practice_worker.py:65-171`) and
     `base._ProgressWriter`, `base._state`, `base._check_state`, `base._partial_checkpoint`,
     `base._score_seal`, `base._write_bytes`, `base.counter_delta`, `base._representatives`
     (`typed_course_worker.py:40-225`) — `DESIGN_REVIEW_PIPELINE_LENS.md:226`.
   * Keep the Windows refusal where it is, before any numeric import (A.4; P8 `:247`).
   * `torch.use_deterministic_algorithms(True)` and the two tf32 flags exactly as
     `typed_practice_worker.py:252-254` (RK7 `:71-73`).
   * Phase order (hand-out `:283`, FP3, M3): preflight → packets → **checkpoint check phase A**
     (restore the 3 old checkpoints of this seed, extract and seal PUBLIC vectors only, prove rebuilt
     logits equal `restored.predict` bit-for-bit — M4 `:189`, V2 `:180`) → seed + double build (DG4
     `:140-146`) → 10 passes with evaluations → retention/interference → reloads/replays → **phase B
     probes** (derive answers and fit the ridge probe last) → ablations (DG8 `:163-165`) → source
     verification → deliver. Phase A must finish before the pointer model is seeded (M3 `:188`).
   * The checkpoint check must always write its artifact with a `status` of COMPLETE or FAILED inside,
     and must import every module it needs **at start-up, outside any try** (RK6 `:66-69`), because a
     poisoned `attestor.snapshot()` raises `FAILED_IMPORTS` at final source verification
     (`typed_source_attestation.py:98`).
   * The custody boundary of section A.8 is unchanged: seal durably, read back, digest-check, and only
     then import the checker and derive targets. P14 (`:253`).
   * Replace `base._encoding_checks` with the pointer input checks (V1 `:179`).
8. **`research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py`** — the launcher this spec's section C
   describes. Copy the practice module and change, in this order:
   * `RESULT_SCHEMA`, `FAILURE_SCHEMA`, `REQUEST_SCHEMA`, `AUTHORITY_SCHEMA`, `OWNER_SCHEMA`,
     `WORKER_NAME`, `CANDIDATE`, `CONFIG_SCHEMA`, `JOB_PATTERN` (`typed_practice_launch.py:35-43`);
   * `_probe()` → `cncm.typed_pointer_worker`, keeping the four-constant equality check (RK5 `:64`);
   * `EXPERIMENT["profile"]` and `["entrypoint"]` (`:63`);
   * `BOUNDS` and the ordering guard (`:64-74`);
   * `worker_config` → the new contract's `parse_job`/`make_config` (`:93-96`);
   * `validate_request`/`validate_authority`/`validate_owner` and all their codes (`:99-145`) — including
     the three bindings at `:125-127` that enforce RK9;
   * `bootstrap_source()` → `typed_pointer_worker`, keeping the `count == 2` check (RK5 `:231`);
   * `render_worker()` with its own globals (`:158-177`) — it cannot be inherited;
   * `evidence_contract()` → the new probe and a new `EXPERIMENT["profile"]` (`:180-190`), and confirm
     `required_count == len(EXPECTED_ARTIFACTS) + 3`;
   * `PACKAGING_SOURCES` — **add `"typed_pointer_launch"`** and every launcher it imports (C.2, RK5 `:63`);
   * `git_package_bytes` — widen the allowlist so the 18 checkpoint files under
     `records/typed_practice_001/receipt_<seed>/checkpoints/` are admitted (they must be in the new
     `MATERIAL`) (RK5 `:62`);
   * `reservation_plan_for` — new `task_scope` (RK5 `:60`);
   * `TypedPointerProvider` subclassing the practice provider: override `reservation_plan`, `reserve`
     (frozen amount), `_user_data` (new pattern check, new delimiter, its own envelope), and
     `bind_authority` (new validator, new `WORKER_NAME`, new `failure_statuses` including the new worker's
     FAILED status) (RK5 `:57-64`); keep `_probe()`'s constant check and the wait/`_transient` logic;
   * `validate_reserved_transition`, `execute`, `main` re-pointed at the new functions (`:374-443`).
9. **`records/typed_pointer_001/evaluate_gates.py`** — the gate reader this spec's section D describes.
   Copy `records/typed_practice_001/evaluate_gates.py`; it must live **outside** `cncm/` and `cas_meta2/`
   (RK9 `:82-88`). New I1 (new worker module and status), and a new I3 carrying the DG4 evidence
   (RK8 `:77-80`, DG4 `:140-146`, V3 `:181`). Primary label keyed on **RELATIONAL** (FP1 `:101-108`),
   the all-kinds result reported as a flag, per-tier and per-kind tables (`HANDOFF…:249-250`), the FP2
   and DG3 removals applied to the population (`:110-113`, `:135-138`), and the exact arithmetic of
   D.2 unchanged. A test must show a flag-copy-only outcome receives no label. New output schema string
   (today `'cncm.typed-practice-gate-reading/0.3'`, `evaluate_gates.py:238`).
10. **`records/typed_pointer_001/{prepare_study.py, execute_study.py, preflight_dry_run.py, holdout_audit.py}`**
    — section E. `prepare_study.py` keeps its five `assert`s and its rehearsal
    (`prepare_study.py:40-41, 82, 93, 95`); `execute_study.py` keeps `--execute STUDY SHA256`, the
    `stop_unless` codes and the seven launcher arguments (`execute_study.py:22-41, 49-50`);
    `preflight_dry_run.py` keeps the stand-ins, `CreateOnlyPublisher` and the write audit, with its own
    `staging` name and its own `expected` integrity-failure list, and prints `PREFLIGHT_PASS` only when
    `failures == expected and label == "VOID" and clean` (`preflight_dry_run.py:247, 260-263`);
    `holdout_audit.py` re-derives the same rules (`holdout_audit.py:32-71`). The owner's 2026-09-19 text
    goes verbatim into every job's `owner.json` (`HANDOFF…:286`, `:77`), one record per job (DG9).
11. **`tests/test_typed_pointer_study.py`** — section G.2's self-contained `sys.path` block repeated
    verbatim (`tests/test_typed_practice_study.py:15-18`), the same `public_only` import guard
    (`:38-47`), and P1–P14 (`DESIGN_REVIEW_PIPELINE_LENS.md:239-253`), including P2 (bucket ≤ 63),
    P3 (the 18 pinned checkpoint rows within the row/byte/member bounds), P4 (the RK10 restore-identity
    freeze for all 9 checkpoints, `:90-97`), P5 (package dry run: archive ≤ 24 MiB, rendered worker
    `typed_pointer_worker`, no old worker), P6 (launcher overrides: watchdog accepts the new job pattern
    and refuses the practice one; `bind_authority`; `task_scope`; `failure_statuses`; `_probe`
    constants), P7, P8, P9, P10, P11, P12, P13, P14.

### Stage 2 — freeze, package, dry-run, launch (hand-out §9)

12. Commit everything (the package is built from `git show <commit>:<path>` blobs —
    `typed_practice_launch.py:204`, `:222`) and push; `prepare_study.py` asserts a clean tree first
    (`prepare_study.py:38-40`).
13. `python records/typed_pointer_001/prepare_study.py` → `admission_001/{study.json, 2026091X/{request,authority,owner}.json, rehearsal}`; commit + push the freeze **before** the first launch
    (`HANDOFF…:342-343`).
14. GPU smoke per §7 S1–S9 locally (dev only, not claim-bearing); S10 (the worker end to end) on AWS
    **only after the owner's OK** (`HANDOFF…:309-313`, §12 item 2).
15. Launch sequentially in the background:
    `python records/typed_pointer_001/execute_study.py --execute records/typed_pointer_001/admission_001/study.json <sha256>`
    — one job at a time, `stop_unless` on the first failure, and **no `.py` change under `cncm/` or
    `cas_meta2/` until all three jobs have launched** (RK9; `HANDOFF…:344-347`).
16. Read the result: the label `records/typed_pointer_001/evaluate_gates.py` prints **is** the claim
    status. Write `records/typed_pointer_001/POINTER_STUDY_RESULT.md`, update
    `records/MACHINE_STATE_001/STATUS.md`, `<WN>\CHANGELOG.md` and
    `<WN>\docs\CAS_HARNESS_SPEC_SHEET.md` (with artifact paths) in the same commit, back the receipts up
    to `D:\tksCAS-archive\cncm_typed_pointer_001_<date>`, commit, push, then report in plain English.

### Findings → deliverable index

| finding | satisfied by checklist item | primary anchor |
|---|---|---|
| RK1 | 6 (`train_sealed_batch`) | `learner.py:271`, `:185`; review `:25-29` |
| RK2 | 6 (`PointerCourseLearner`) | `learner.py:82-101, 336, 341`; `graph_teaching/trainer.py:86-87`; review `:31-44` |
| RK3 | 4, 5 (token cache pinned once) | `tokenization.py:151`; review `:46-50` |
| RK4 | 4 (`JOB_PATTERN` ≤ 5-char token), 11 (P2) | `practice_contract.py:226`; review `:52-55` |
| RK5 | 8 (launcher) | `typed_practice_launch.py:201-203, 261, 320, 359-360, 365`; review `:57-64` |
| RK6 | 7 (checkpoint-check artifact always written; imports at start-up) | `typed_practice_worker.py:187-188`; `typed_source_attestation.py:98`; review `:66-69` |
| RK7 | 6, 7 (dense matmuls, one-hot, rigid flag block) | `typed_practice_worker.py:252`; review `:71-73` |
| RK8 | 9 (new gate reader, new I1/I3) | `evaluate_gates.py:162-165, 182-189, 226-237`; review `:77-80` |
| RK9 | 4, 5, 6, 7, 9 (nothing new under `cncm/`/`cas_meta2/` after the freeze), 12, 15 | `worker_contract.py:138-143`; `typed_practice_launch.py:125-127`; review `:82-88` |
| RK10 | 11 (P4 restore-identity test) | review `:90-97` |
| FP1 | 3, 9, 11 (RELATIONAL primary; flag reported; P12) | `evaluate_gates.py:232`, `:33-34`; review `:101-108` |
| FP2 | 2, 3, 9, 11 (frozen per-question flag-rule baseline; removals) | review `:110-113` |
| FP3 | 3, 7 (Phase A public-only first, Phase B last) | `practice_contract.py:11-12`; `typed_course_worker.py:149`; review `:115-121` |
| DG1 | 6 (fixed K=8) | review `:124-128` |
| DG2 | 5, 6 (rule embedding in the query) | review `:130-133` |
| DG3 | 2, 3, 9, 11 (rank feature + rank baseline, or removal) | review `:135-138` |
| DG4 | 7 (in-job double build, seed spread, with/without check), 9 (new I3) | review `:140-146` |
| DG5 | 3 (wording: "never the focus of a trained question") | review `:148-151` |
| DG6 | 6 (exact prediction schema) | `loss_plan.validate_prediction`; `slots.py:88`; review `:153-155` |
| DG7 | 6 (RMS each round; S8) | `slots.py:248`; `learner.py:261`; review `:157-161` |
| DG8 | 7 (ablations on restored copies, in `EXPECTED_ARTIFACTS`, timed, create-only) | review `:163-165` |
| DG9 | 3, 10 (three new owner records); 14 (smoke timing before reserving more) | review `:167-169`; `HANDOFF…:395-396` |
| DG10 | 4, 7 (new DESIGN, new planned-work formula) | `typed_practice_worker.py:174-180, 361`; `practice_contract.py:210, 213`; review `:171-175` |
| V1/V2/V3, M1–M4 | 5, 7 (pointer input checks; pre-block vectors once; DG4 I3; one checkpoint path; true cost; Phase A before seeding; `encode_slot` + `recurrence.run_passes` equality proof) | review `:177-189` |
