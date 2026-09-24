"""Q4-SDG-1 A-versus-B 0.2 runner. NEURAL -- one AWS T4 (Linux) only, never this laptop.

Arms (q4_ab_rules.py, spec Q4_SDG_AB_SPEC_v0_2.md): A = visible Q3 v0.7 G train rows minus the reserved panel rows;
B = the pinned CAS SDG lesson package (families A-C, train split) minus any panel content. Same model, loss,
optimizer, learning rate, clipping and number of single-example updates; pair i uses seed SEEDS[i] for both arms.

Stages, in order. Any stop writes STOP.json with a code from q4_ab_rules.STOP_CODES; nothing is retried.
  pin       Q4_SDG_DATA_PINS.json must hold the frozen B package's pin (else B_PACKAGE_NOT_PINNED).
  gpu       explicit cuda:N; nvidia-smi reports no compute user; torch 2.11.0+cu128 and Python 3.14; CUDA
            deterministic settings (fails closed with GPU_REQUIRED without CUDA; there is no CPU path).
  q3        visible Q3 rows (pinned manifest), targets recompiled from the visible text with the pinned compiler
            (engine python); the diagnostic selection, the 48 inspected dev rows, SP1, EDIT64 and the A pool must
            reproduce the digests frozen in q4_ab_rules.py.
  stage0    the original checkpoint (run_001) must replay its 16 saved dev decodes exactly on THIS machine, and the
            model rebuilt with seed 20260921 in q4_smoke_job's call order must reproduce update 1.
  b_package the package is rebuilt here (q4_sdg_curriculum.build, --expect-engine python) and must equal the pin.
  prep      prep.json: panels, edits, pools and class counts (create-only).
  smoke     64 updates of A (twice, same seed: must be identical) and B (same starting tensors as A), on thinned
            panels; then a time projection that must fit the time left (else PROJECTED_OVER_TIME).
  runs      A1 B1 A2 B2 A3 B3: UPDATES single-example updates each; the shared panels and the input-use measures at
            every checkpoint; the final weights saved with their sha256; a fresh-process reload check.

CUSTODY. No eval file and no sealed file is ever opened: Q3 rows come through q4_error_panel.visible_rows, B rows
through q4_sdg_curriculum.load_visible_lessons, and every target is recompiled from visible text. The B rebuild
WRITES its own sealed_* sidecars (they are part of the pinned package); this program never reads them. Outputs are
create-only; a used output directory is never reused.

  python -B q4_ab_train.py run --run-dir <run_001> --data-dir data/q3_v0_7 --out <new dir> --device cuda:0
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import q4_ab_prep as prep  # noqa: E402
import q4_ab_rules as rules  # noqa: E402
import q4_error_panel as ep  # noqa: E402
import q4_sdg_curriculum as sdg  # noqa: E402
from learner_q4_decoder import TOKENS, DecodeLimits, free_decode  # noqa: E402
from learner_q4_representation import encode_observation  # noqa: E402

RESULT_SCHEMA = "helm-cas-expression-lab.q4-sdg-ab-result/0.2"
OTHER_SOURCES = ("q4_ab_train.py", "q4_ab_rules.py", "q4_ab_prep.py", "read_q4_ab_results.py", "q4_error_panel.py",
                 "q4_sdg_curriculum.py", "q4_panel_evaluation.py", "historical_compiler.py",
                 "pinned_sources/compiler_pre_ohm_61ed5a45.py", "Q3_DATA_PINS.json", "Q4_SDG_DATA_PINS.json",
                 "Q4_SDG_AB_SPEC_v0_2.md", "test_q4_ab.py")
RELOAD_ROWS = 16
RELOAD_TIMEOUT_SECONDS = 300


class JobStop(Exception):
    def __init__(self, code, detail=""):
        if code not in rules.STOP_CODES:
            raise ValueError("UNKNOWN_STOP_CODE: %s" % code)
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def stop_code(error):
    """The frozen stop code of a JobStop or of a PrepError-style message 'CODE: detail'; None for anything else."""
    if isinstance(error, JobStop):
        return error.code
    if not isinstance(error, ValueError):
        return None
    head = str(error).split(":")[0].strip()
    return head if head in rules.STOP_CODES else None


class Deadline:
    def __init__(self, seconds, code):
        self.end, self.code = time.monotonic() + seconds, code

    def left(self):
        return self.end - time.monotonic()

    def check(self):
        if time.monotonic() >= self.end:
            raise JobStop(self.code)


class Deadlines:
    """The job's deadline and, inside it, the current run's deadline."""
    def __init__(self, *deadlines):
        self.items = deadlines

    def check(self):
        for item in self.items:
            item.check()


def source_hashes():
    from q4_checkpoint import runtime_source_pins
    return {"runtime_source_pins": runtime_source_pins(),
            "other_lf_sha256": {name: sdg.lf_sha256(HERE / name) if (HERE / name).is_file() else None
                                for name in OTHER_SOURCES}}


def require_device(device):
    if type(device) is not str or re.fullmatch(r"cuda:[0-9]+", device) is None:
        raise JobStop("GPU_REQUIRED", "an explicit cuda:N device is required; there is no CPU path")


def set_deterministic(torch):
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def gpu_gates(device):
    """Before any CUDA context exists: an idle GPU, then CUDA, the pinned versions and deterministic settings."""
    from q4_smoke_job import JobError, _check_device_idle
    try:
        _check_device_idle(device)
    except JobError as error:
        raise JobStop("GPU_BUSY_OR_UNKNOWN", str(error)) from None
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    if os.environ["CUBLAS_WORKSPACE_CONFIG"] != ":4096:8":
        raise JobStop("CUBLAS_WORKSPACE_CONFIG_DIFFERS")
    import torch
    if not torch.cuda.is_available():
        raise JobStop("GPU_REQUIRED", "CUDA is unavailable; no CPU fallback")
    python = "%d.%d" % sys.version_info[:2]
    if torch.__version__ != rules.EXPECTED_TORCH or python != rules.EXPECTED_PYTHON:
        raise JobStop("RUNTIME_VERSION_MISMATCH", "torch %s, python %s" % (torch.__version__, python))
    set_deterministic(torch)
    return {"torch": torch.__version__, "cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
            "python": platform.python_version(), "platform": platform.platform(),
            "device_name": torch.cuda.get_device_name(device),
            "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled()}


def state_sha256(model):
    """sha256 over (name, dtype, shape, raw bytes) of every state tensor, sorted by name. Independent of torch.save."""
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().to("cpu").contiguous()
        digest.update(("%s|%s|%s|" % (name, value.dtype, tuple(value.shape))).encode("utf-8"))
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


# ------------------------------------------------------------------------------------------------------------
# Stage 0: the diagnostic's reproduction, on this machine, before anything is trained
# ------------------------------------------------------------------------------------------------------------
def stage0(q3prep, compiler, device, out):
    import torch
    from learner_q4_neural import NeuralConfig, build_model
    from q4_checkpoint import load_checkpoint
    records = q3prep["records"]
    model = load_checkpoint(records["dir"] / "checkpoint", expected_identity=records["identity"],
                            expected_weights_sha256=rules.RUN_001_WEIGHTS_SHA256, width=64, device=device)
    reproduced, mismatches = ep.stage0(model, records, q3prep["dev"])
    del model
    torch.manual_seed(ep.INIT_SEED)
    torch.cuda.manual_seed_all(ep.INIT_SEED)
    set_deterministic(torch)
    initial = build_model(NeuralConfig(64), device=device)
    train = q3prep["train"]
    first = train[ep.consumed_positions(len(train))[0]]
    first_row = ep.compiled_row(first, compiler, "update_1", {"split": "train", "update": 1})
    check = ep.update_1_check(ep.backward_norms(initial, first_row, device, None), records["updates"][0],
                              first["record_id"])
    del initial
    status = "REPRODUCED_16_OF_16" if not mismatches else "NOT_REPRODUCED_%d_OF_16_DIFFER" % len(mismatches)
    ep.write_once(out / "stage0.json", {"schema": RESULT_SCHEMA, "status": status, "mismatches": mismatches,
                                        "reproduced": reproduced, "reinit_update_1": check,
                                        "frozen_sha256": rules.frozen_sha256()})
    if mismatches:
        raise JobStop("STAGE0_NOT_REPRODUCED", status)
    if not check["reproduced"]:
        raise JobStop("REINIT_NOT_REPRODUCED", "update-1 loss or gradient norm differs")


# ------------------------------------------------------------------------------------------------------------
# Evaluation at one checkpoint (forward only; never touches the optimizer or the training order)
# ------------------------------------------------------------------------------------------------------------
def runtime_edits(edit_items, rows_by_id):
    out = []
    for item in edit_items:
        if item["to"] is None:
            continue
        row = rows_by_id[item["row"]]
        prefix = tuple(row["target_tokens"][:item["position"]])
        out.append({"row": item["row"], "source_observation": row["observation"],
                    "observation": item["observation"], "prefix": prefix,
                    "allowed": prep.allowed_next(prefix), "old": TOKENS.index(item["old_token"]),
                    "new": TOKENS.index(item["new_token"])})
    return out


def evaluate(model, panels, edits, partners, deadlines):
    limits = DecodeLimits(max_tokens=rules.EVAL_DECODE_MAX_TOKENS)
    record, bottlenecks = {"panels": {}}, {}
    timing = collections.Counter()
    for name, rows in panels.items():
        out_rows = []
        by_slot = collections.defaultdict(lambda: [0, 0])
        for row in rows:
            deadlines.check()
            started = time.monotonic()
            bottleneck = model.encode(encode_observation(row["observation"]))
            result = free_decode(bottleneck, model.next_logits, limits)
            timing["decode_seconds"] += time.monotonic() - started
            timing["decode_rows"] += 1
            timing["decode_steps"] += result.steps
            if name == "SP1":
                bottlenecks[row["record_id"]] = bottleneck
            started = time.monotonic()
            logits = ep.teacher_logits(model, row)
            target = row["target_tokens"]
            bits = "".join("1" if ep.choose(values, row["allowed"][i]) == target[i] else "0"
                           for i, values in enumerate(logits))
            timing["tf_seconds"] += time.monotonic() - started
            timing["tf_rows"] += 1
            for kind, bit in zip(row["slot_kinds"], bits):
                by_slot[kind][0] += bit == "1"
                by_slot[kind][1] += 1
            tokens = list(result.tokens)
            wrong = sdg.first_wrong_decision(result.tokens, target)
            out_rows.append({"id": row["record_id"], "outcome": result.outcome, "free": tokens,
                             "exact": int(result.outcome == "GENERATED" and tokens == list(target)), "tf": bits,
                             "fwd": None if wrong is None else wrong["mistake"]})
        record["panels"][name] = {
            "rows": out_rows, "n": len(out_rows), "exact": sum(r["exact"] for r in out_rows),
            "distinct_free_outputs": len({tuple(r["free"]) for r in out_rows}),
            "tf_by_slot": {k: list(v) for k, v in sorted(by_slot.items())}}
    values = []
    started = time.monotonic()
    for edit in edits:
        deadlines.check()
        b0 = bottlenecks.get(edit["row"]) or model.encode(encode_observation(edit["source_observation"]))
        bottlenecks.setdefault(edit["row"], b0)
        b1 = model.encode(encode_observation(edit["observation"]))
        l0, l1 = model.next_logits(b0, edit["prefix"]), model.next_logits(b1, edit["prefix"])
        p0, p1 = ep.softmax(l0), ep.softmax(l1)
        values.append([p0[edit["new"]], p1[edit["new"]], p0[edit["old"]], p1[edit["old"]],
                       ep.choose(l0, edit["allowed"]), ep.choose(l1, edit["allowed"]),
                       ep.summary_change(b0.values, b1.values)["cosine"]])
    timing["edit_seconds"] += time.monotonic() - started
    timing["edits"] += len(values)
    record["edits"] = {"columns": ["p_new_original", "p_new_edited", "p_old_original", "p_old_edited",
                                   "masked_choice_original", "masked_choice_edited", "summary_cosine"],
                       "values": values}
    cosines = [ep.summary_change(bottlenecks[a].values, bottlenecks[b].values)["cosine"]
               for a, b in partners if a in bottlenecks and b in bottlenecks]
    record["summary_similarity"] = {"partner_cosine": ep.describe_values(cosines)}
    record["timing"] = dict(timing)
    return record


# ------------------------------------------------------------------------------------------------------------
# One run: build exactly as q4_smoke_job._worker, then UPDATES single-example updates with checkpoints
# ------------------------------------------------------------------------------------------------------------
def train_run(*, arm, seed, pool, shared_panels, edits, partners, updates, checkpoints, run_dir, device,
              job_deadline, identity_base, thin=None):
    import torch
    from learner_q4_neural import NeuralConfig, build_model
    from q4_checkpoint import save_checkpoint
    run_dir.mkdir(parents=True, exist_ok=False)
    deadlines = Deadlines(job_deadline, Deadline(rules.RUN_WALL_SECONDS, "RUN_WALL_LIMIT"))
    started = time.monotonic()
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    set_deterministic(torch)
    model = build_model(NeuralConfig(rules.WIDTH), device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=rules.LEARNING_RATE)
    stream = prep.stream_indices(len(pool), seed, updates)
    teach = [prep.with_allowed(dict(pool[i], panel="TEACH_FIT"))
             for i in prep.stream_indices(len(pool), seed, rules.TEACH_FIT_ROWS)]
    panels = dict(shared_panels, TEACH_FIT=teach)
    if thin is not None:
        panels = {name: rows[::thin] for name, rows in panels.items()}
    init_sha = state_sha256(model)
    identity = dict(identity_base, arm=arm, seed=seed, updates=updates)
    ep.write_once(run_dir / "run_manifest.json", {
        "schema": RESULT_SCHEMA, "arm": arm, "seed": seed, "updates": updates, "checkpoints": list(checkpoints),
        "pool_rows": len(pool), "pool_ids_digest": prep.ids_digest(pool),
        "stream_digest": rules.sha(rules.canonical(stream)), "init_state_sha256": init_sha,
        "teach_fit": [prep.panel_row_record(r) for r in panels["TEACH_FIT"]],
        "panel_sizes": {name: len(rows) for name, rows in panels.items()}, "edits": len(edits),
        "identity": identity, "frozen_sha256": rules.frozen_sha256()})
    inputs = [encode_observation(row["observation"]) for row in pool]
    targets = [tuple(row["target_tokens"]) for row in pool]
    windows, first_updates, window = [], [], collections.Counter()
    totals = collections.Counter()
    train_seconds, eval_seconds = 0.0, 0.0
    for update in range(updates + 1):
        if update in checkpoints:
            t0 = time.monotonic()
            record = evaluate(model, panels, edits, partners, deadlines)
            eval_seconds += time.monotonic() - t0
            record.update(schema=RESULT_SCHEMA, arm=arm, seed=seed, checkpoint=update,
                          weights_state_sha256=state_sha256(model), frozen_sha256=rules.frozen_sha256(),
                          elapsed_seconds=time.monotonic() - started)
            ep.write_once(run_dir / ("checkpoint_%05d.json" % update), record)
        if update == updates:
            break
        deadlines.check()
        t0 = time.monotonic()
        index = stream[update]
        target = targets[index]
        optimizer.zero_grad(set_to_none=True)
        logits = model.teacher_forced_logits(inputs[index], target[:-1])
        gold = torch.tensor(target, dtype=torch.long, device=model._device())
        loss = torch.nn.functional.cross_entropy(logits, gold)
        if not torch.isfinite(loss).item():
            raise JobStop("NUMERICAL_FAILURE", "training loss at update %d" % (update + 1))
        loss.backward()
        try:
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), rules.CLIP_NORM, error_if_nonfinite=True)
        except RuntimeError as error:
            raise JobStop("NUMERICAL_FAILURE", "gradient at update %d: %s" % (update + 1, error)) from None
        optimizer.step()
        loss_value, norm_value = float(loss.item()), float(norm.item())
        train_seconds += time.monotonic() - t0
        tokens, source = len(target), len(inputs[index].byte_ids)
        totals["target_tokens"] += tokens
        totals["source_bytes"] += source
        if update < 128:
            first_updates.append({"update": update + 1, "row": pool[index]["record_id"], "loss": loss_value,
                                  "pre_clip_gradient_norm": norm_value})
        window["n"] += 1
        window["loss_sum"] += loss_value
        window["loss_max"] = max(window["loss_max"], loss_value)
        window["norm_sum"] += norm_value
        window["norm_max"] = max(window["norm_max"], norm_value)
        window["clipped"] += norm_value > rules.CLIP_NORM
        window["target_tokens"] += tokens
        if window["n"] == rules.LOSS_WINDOW or update + 1 == updates:
            windows.append({"last_update": update + 1, "n": window["n"], "loss_mean": window["loss_sum"] / window["n"],
                            "loss_max": window["loss_max"], "norm_mean": window["norm_sum"] / window["n"],
                            "norm_max": window["norm_max"], "clipped": window["clipped"],
                            "target_tokens": window["target_tokens"]})
            window = collections.Counter()
    ep.write_once(run_dir / "updates.json", {"windows": windows, "first_128_updates": first_updates})
    saved = save_checkpoint(model, run_dir / "checkpoint", identity=identity)
    result = {"schema": RESULT_SCHEMA, "status": "COMPLETE", "arm": arm, "seed": seed, "updates": updates,
              "presentations": updates, "distinct_rows_seen": len(set(stream)), "pool_rows": len(pool),
              "target_tokens": totals["target_tokens"], "source_bytes": totals["source_bytes"],
              "init_state_sha256": init_sha, "final_state_sha256": state_sha256(model),
              "final_weights_sha256": saved["weights_sha256"], "identity": identity,
              "train_seconds": train_seconds, "eval_seconds": eval_seconds,
              "wall_seconds": time.monotonic() - started,
              "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(model._device()),
              "frozen_sha256": rules.frozen_sha256()}
    ep.write_once(run_dir / "run_result.json", result)
    del model, optimizer
    return result


def comparable(record):
    """A checkpoint record without its timing: two identical runs must give identical comparable records."""
    return {k: v for k, v in record.items() if k not in ("timing", "elapsed_seconds")}


def smoke_and_project(*, pools, shared_panels, edits, partners, device, job_deadline, identity_base, out):
    """Tiny runs first: A twice (same seed) must be identical; B must start from A's tensors; then the projection."""
    seed = rules.SEEDS[0]
    smoke_edits = edits[::rules.SMOKE_EDIT_STRIDE]
    results = {}
    for name, arm in (("A_first", "A"), ("A_repeat", "A"), ("B_first", "B")):
        results[name] = train_run(arm=arm, seed=seed, pool=pools[arm], shared_panels=shared_panels, edits=smoke_edits,
                                  partners=partners, updates=rules.SMOKE_UPDATES, checkpoints=rules.SMOKE_CHECKPOINTS,
                                  run_dir=out / "smoke" / name, device=device, job_deadline=job_deadline,
                                  identity_base=dict(identity_base, smoke=True), thin=rules.SMOKE_STRIDE)
    same = results["A_first"]["final_state_sha256"] == results["A_repeat"]["final_state_sha256"]
    for point in rules.SMOKE_CHECKPOINTS:
        a = ep.read_json(out / "smoke" / "A_first" / ("checkpoint_%05d.json" % point))
        b = ep.read_json(out / "smoke" / "A_repeat" / ("checkpoint_%05d.json" % point))
        same = same and rules.canonical(comparable(a)) == rules.canonical(comparable(b))
    pair_init = results["A_first"]["init_state_sha256"] == results["B_first"]["init_state_sha256"]
    timing = collections.Counter()
    for name in results:
        for point in rules.SMOKE_CHECKPOINTS:
            timing.update(ep.read_json(out / "smoke" / name / ("checkpoint_%05d.json" % point))["timing"])
    per_update = max(r["train_seconds"] / rules.SMOKE_UPDATES for r in results.values())
    rows_full = sum(len(rows) for rows in shared_panels.values()) + rules.TEACH_FIT_ROWS
    eval_full = (timing["decode_seconds"] / max(1, timing["decode_rows"]) * rows_full
                 + timing["tf_seconds"] / max(1, timing["tf_rows"]) * rows_full
                 + timing["edit_seconds"] / max(1, timing["edits"]) * len(edits))
    per_run = rules.UPDATES * per_update + len(rules.CHECKPOINTS) * eval_full + rules.RELOAD_ALLOWANCE_SECONDS
    projected = float(rules.PROJECTION_SAFETY) * per_run * len(rules.RUN_ORDER)
    summary = {"schema": RESULT_SCHEMA, "deterministic_repeat": same, "pair_init_equal": pair_init,
               "seconds_per_update": per_update, "projected_eval_seconds_per_checkpoint": eval_full,
               "projected_seconds_per_run": per_run, "projected_seconds_all_runs_with_safety": projected,
               "seconds_left_in_job": job_deadline.left(), "run_wall_seconds": rules.RUN_WALL_SECONDS,
               "timing_totals": dict(timing), "smoke_runs": {k: {x: v[x] for x in ("init_state_sha256",
                                                                                    "final_state_sha256",
                                                                                    "train_seconds", "eval_seconds")}
                                                             for k, v in results.items()},
               "note": "smoke results are never read by read_q4_ab_results.py; they gate and time the job only"}
    ep.write_once(out / "smoke_summary.json", summary)
    if not same:
        raise JobStop("SMOKE_NONDETERMINISTIC", "two identical smoke runs differ")
    if not pair_init:
        raise JobStop("SMOKE_PAIR_INIT_MISMATCH", "arms A and B do not start from the same tensors")
    if projected > job_deadline.left() or float(rules.PROJECTION_SAFETY) * per_run > rules.RUN_WALL_SECONDS:
        raise JobStop("PROJECTED_OVER_TIME", "%.0f s projected, %.0f s left" % (projected, job_deadline.left()))
    return summary


def reload_in_fresh_process(run_dir, prep_path, device, job_deadline):
    """A separate Python process reloads the saved final weights and repeats 16 SP1 decodes; it writes its record."""
    timeout = min(RELOAD_TIMEOUT_SECONDS, max(1, int(job_deadline.left())))
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "reload", "--run-dir", str(run_dir),
               "--prep", str(prep_path), "--device", device]
    with (run_dir / "reload.log").open("xb") as log:
        try:
            code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = "TIMEOUT"
    return code


def reload_check(run_dir, prep_path, device):
    require_device(device)
    run_dir = Path(run_dir)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    import torch
    from q4_checkpoint import load_checkpoint
    set_deterministic(torch)
    result = ep.read_json(run_dir / "run_result.json")
    final = ep.read_json(run_dir / ("checkpoint_%05d.json" % result["updates"]))
    rows = ep.read_json(prep_path)["panels"]["SP1"][:RELOAD_ROWS]
    model = load_checkpoint(run_dir / "checkpoint", expected_identity=result["identity"],
                            expected_weights_sha256=result["final_weights_sha256"], width=rules.WIDTH, device=device)
    saved = {r["id"]: r for r in final["panels"]["SP1"]["rows"]}
    limits = DecodeLimits(max_tokens=rules.EVAL_DECODE_MAX_TOKENS)
    mismatches = []
    for row in rows:
        again = free_decode(model.encode(encode_observation(row["observation"])), model.next_logits, limits)
        before = saved.get(row["id"])
        if before is None or list(again.tokens) != before["free"] or again.outcome != before["outcome"]:
            mismatches.append({"id": row["id"], "now": list(again.tokens), "saved": None if before is None else before["free"]})
    state_equal = state_sha256(model) == result["final_state_sha256"]
    ep.write_once(run_dir / "reload_check.json", {
        "schema": RESULT_SCHEMA, "status": "RELOAD_REPRODUCED" if not mismatches and state_equal else "RELOAD_MISMATCH",
        "rows_checked": len(rows), "mismatches": mismatches, "state_sha256_equal": state_equal,
        "weights_sha256": result["final_weights_sha256"], "process": "fresh Python process", "pid": os.getpid()})
    return 0


# ------------------------------------------------------------------------------------------------------------
def run(run_dir, data_dir, out, *, device="cuda:0", max_wall_seconds=rules.JOB_WALL_SECONDS):
    require_device(device)                       # before any torch import, file write or data read
    if type(max_wall_seconds) is not int or not 600 <= max_wall_seconds <= rules.JOB_WALL_SECONDS:
        raise JobStop("JOB_WALL_LIMIT", "max_wall_seconds must be in 600..%d" % rules.JOB_WALL_SECONDS)
    job_deadline = Deadline(max_wall_seconds, "JOB_WALL_LIMIT")
    started = time.monotonic()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    stage = "pin"
    try:
        entry = prep.read_pin_entry()
        stage = "gpu"
        runtime = gpu_gates(device)
        ep.write_once(out / "gates.json", {"schema": RESULT_SCHEMA, "runtime": runtime, "b_pin": entry,
                                           "frozen_sha256": rules.frozen_sha256()})
        stage = "q3"
        compiler = sdg.Compiler()
        if compiler.engine != rules.B_PACKAGE["engine"]:
            raise JobStop("COMPILER_ENGINE_NOT_PYTHON", compiler.engine)
        q3prep = prep.prepare_q3(run_dir, data_dir, compiler, strict=True)
        stage = "stage0"
        stage0(q3prep, compiler, device, out)
        stage = "b_package"
        package_dir = HERE / rules.B_PACKAGE["data_dir"]
        try:
            sdg.build(package_dir, rules.B_PACKAGE["size"], seed=rules.B_PACKAGE["seed"],
                      feedback_seed=rules.B_PACKAGE["feedback_seed"], expect_engine=rules.B_PACKAGE["engine"])
        except (sdg.LessonError, OSError) as error:
            raise JobStop("B_PACKAGE_BUILD_FAILED", str(error)) from None
        prep.check_package(package_dir, entry)
        bprep = prep.prepare_b(package_dir, compiler, q3prep["panel_contents"])
        stage = "prep"
        record = prep.prep_record(q3prep, bprep, entry["manifest_sha256"])
        ep.write_once(out / "prep.json", record)
        identity_base = {"experiment": rules.EXPERIMENT, "schema": rules.SCHEMA, "frozen_sha256": rules.frozen_sha256(),
                         "b_package_manifest_sha256": entry["manifest_sha256"],
                         "q3_manifest_sha256": rules.Q3_MANIFEST_SHA256,
                         "prep_sha256": rules.sha(rules.canonical(record)),
                         "source_pins": source_hashes()["runtime_source_pins"]}
        shared = {"SP1": [prep.with_allowed(r) for r in q3prep["sp1"]],
                  "SP2": [prep.with_allowed(r) for r in q3prep["sp2"]],
                  "B_DEV": [prep.with_allowed(r) for r in bprep["b_dev"]]}
        edits = runtime_edits(q3prep["edit_items"], {r["record_id"]: r for r in q3prep["sp1"]})
        partners = record["sp1_partners"]
        pools = {"A": q3prep["a_pool"], "B": bprep["b_pool"]}
        stage = "smoke"
        smoke_and_project(pools=pools, shared_panels=shared, edits=edits, partners=partners, device=device,
                          job_deadline=job_deadline, identity_base=identity_base, out=out)
        stage = "runs"
        reloads = {}
        for arm, seed in rules.RUN_ORDER:
            run_path = out / "runs" / ("%s_%d" % (arm, seed))
            train_run(arm=arm, seed=seed, pool=pools[arm], shared_panels=shared, edits=edits, partners=partners,
                      updates=rules.UPDATES, checkpoints=rules.CHECKPOINTS, run_dir=run_path, device=device,
                      job_deadline=job_deadline, identity_base=identity_base)
            reloads[run_path.name] = reload_in_fresh_process(run_path, out / "prep.json", device, job_deadline)
        ep.write_once(out / "job_result.json", {
            "schema": RESULT_SCHEMA, "status": "COMPLETE", "label": rules.LABEL, "experiment": rules.EXPERIMENT,
            "runs": ["%s_%d" % x for x in rules.RUN_ORDER], "reload_exit_codes": reloads,
            "sources": source_hashes(), "frozen_sha256": rules.frozen_sha256(),
            "elapsed_seconds": time.monotonic() - started,
            "custody": "no eval file and no sealed file opened; targets recompiled from visible text; the B "
                       "rebuild wrote its own sidecars, never read"})
    except BaseException as error:
        code = stop_code(error)
        try:
            if code is not None:
                ep.write_once(out / "STOP.json", {"code": code, "detail": str(error), "stage": stage,
                                                  "elapsed_seconds": time.monotonic() - started})
            ep.write_once(out / "job_result.json", {
                "schema": RESULT_SCHEMA, "status": "STOPPED" if code else "FAILED", "stop_code": code,
                "stage": stage, "type": type(error).__name__, "message": str(error), "label": rules.LABEL,
                "sources": source_hashes(), "frozen_sha256": rules.frozen_sha256(),
                "elapsed_seconds": time.monotonic() - started})
        except OSError:
            pass
        raise
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    go = sub.add_parser("run")
    go.add_argument("--run-dir", required=True)
    go.add_argument("--data-dir", required=True)
    go.add_argument("--out", required=True)
    go.add_argument("--device", default="cuda:0")
    go.add_argument("--max-wall-seconds", type=int, default=rules.JOB_WALL_SECONDS)
    again = sub.add_parser("reload")
    again.add_argument("--run-dir", required=True)
    again.add_argument("--prep", required=True)
    again.add_argument("--device", default="cuda:0")
    args = parser.parse_args(argv)
    if args.mode == "reload":
        return reload_check(args.run_dir, args.prep, args.device)
    print(run(args.run_dir, args.data_dir, args.out, device=args.device, max_wall_seconds=args.max_wall_seconds))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except JobStop as error:
        print("Q4_AB_STOPPED: %s" % error, file=sys.stderr)
        sys.exit(3)
    except ValueError as error:          # PrepError, PanelError, LessonError, CheckpointError, JobError, Q3LoadError
        code = stop_code(error)
        print("Q4_AB_%s: %s" % ("STOPPED" if code else "FAILED", error), file=sys.stderr)
        sys.exit(3 if code else 1)
