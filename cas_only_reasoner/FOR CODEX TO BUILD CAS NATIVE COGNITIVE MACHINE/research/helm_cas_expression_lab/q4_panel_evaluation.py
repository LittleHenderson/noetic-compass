"""Source-bound, split-aware Q4 checkpoint evaluation; no training or migration.

Preparation reconstructs exposure from the frozen single-example shuffle and
completed update receipts. It does not claim per-example training receipts exist.
Execution uses the unchanged historical CUDA model, never a CPU substitute.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import re
import secrets
import shutil
import subprocess
import sys
import time

SCHEMA = "helm.q4-three-panel-evaluation/0.1"
HISTORICAL_SOURCE = "d4c3fc7643201a83693ea9073c14ab42ecc5a570"
PLAN_SHA = "9dacc83627422d704c9db58f5ddbac82936e7d52211ec061247419fbad78095c"
WEIGHTS_SHA = "d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477"
PANELS = ("teaching_fit", "new_content_familiar_structure", "new_structure")
HERE = Path(__file__).resolve().parent


class PanelError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(body):
    return hashlib.sha256(body).hexdigest()


def read(path):
    from q3_load import strict_loads
    return strict_loads(Path(path).read_bytes(), str(path))


def write_once(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")


def file_pin(path, *, lf=False):
    path = Path(path).resolve()
    body = path.read_bytes()
    return {"path": str(path), "bytes": len(body), "sha256": sha(body),
            "sha256_lf": sha(body.replace(b"\r\n", b"\n")) if lf else None}


def skeleton(ast, *, operators=True):
    """Ordered shape; binary operation survives, all StateLiteral content erased."""
    from learner_q4_decoder import ast_to_tokens
    ast_to_tokens(ast)  # reject unknown fields/types, not silently collapse them

    def visit(node):
        if node["node"] == "StateLiteral":
            return "L"
        return [node["op"] if operators else "B", visit(node["left"]), visit(node["right"])]
    return visit(ast)


def shape_key(ast, *, operators=True):
    return sha(canonical(skeleton(ast, operators=operators)))


def dimensions(ast):
    if ast["node"] == "StateLiteral":
        return 1, 0
    left, right = dimensions(ast["left"]), dimensions(ast["right"])
    return 1 + left[0] + right[0], 1 + max(left[1], right[1])


def consumed_indices(count, seed, updates):
    if any(type(x) is not int for x in (count, seed, updates)) or not 1 <= updates <= count <= 2048:
        raise PanelError("UNSUPPORTED_EXPOSURE_SCHEDULE")
    order = list(range(count))
    random.Random(seed).shuffle(order)
    return order[:updates]


def make_row(visible, ast, origin):
    return {"visible": deepcopy(visible), "reference_ast": deepcopy(ast),
            "reference_kind": "FROZEN_COMPILER_TARGET_OR_DECLARED_CONTENT_MUTATION_NOT_LEARNED",
            "origin": origin, "content_sha256": sha(canonical(ast)),
            "ordered_operator_shape_sha256": shape_key(ast),
            "ordered_bare_shape_sha256": shape_key(ast, operators=False),
            "size_depth": list(dimensions(ast))}


def build_panels(train, dev, consumed, n=16):
    if type(n) is not int or not 1 <= n <= 16 or len(consumed) < n:
        raise PanelError("PANEL_LIMIT")
    if len(set(consumed)) != len(consumed) or any(type(i) is not int or not 0 <= i < len(train) for i in consumed):
        raise PanelError("EXPOSURE_INDICES_INVALID")
    contents = {sha(canonical(sealed["target_ast"])) for _, sealed in train}
    observations = {visible["observation"] for visible, _ in train}
    shapes = {shape_key(sealed["target_ast"]) for _, sealed in train}
    bare_shapes = {shape_key(sealed["target_ast"], operators=False) for _, sealed in train}
    exposed_shapes = {shape_key(train[i][1]["target_ast"]) for i in consumed}
    pool_dimensions = {dimensions(sealed["target_ast"]) for _, sealed in train}
    teaching = [make_row(train[i][0], train[i][1]["target_ast"],
                         {"kind": "EXACT_CONSUMED_ROW", "training_position": i,
                          "update": consumed.index(i) + 1}) for i in consumed[:n]]
    familiar = []
    for i in consumed[:n]:
        visible, sealed = train[i]
        first = re.search(r"\^[0-9]", visible["observation"])
        if first is None:
            raise PanelError("MUTATION_SOURCE_SYNTAX")
        for digit in range(10):
            ast = deepcopy(sealed["target_ast"])
            leaf = ast
            while leaf["node"] == "BinaryExpr":
                leaf = leaf["left"]
            if leaf["operator"] != first.group():
                raise PanelError("MUTATION_SOURCE_TARGET_ALIGNMENT")
            leaf["operator"] = "^" + str(digit)
            observation = visible["observation"][:first.start()] + leaf["operator"] + visible["observation"][first.end():]
            content = sha(canonical(ast))
            if content in contents or observation in observations:
                continue
            row_visible = dict(visible, observation=observation,
                               record_id="q4-panel-" + sha(observation.encode("utf-8"))[:24])
            familiar.append(make_row(row_visible, ast, {"kind": "FIRST_LEAF_NOETIC_MUTATION",
                            "source_record_id": visible["record_id"], "source_training_position": i,
                            "verification": "TOKEN_AND_AST_SUBSTITUTION_CHECKED_NOT_RECOMPILED"}))
            contents.add(content)
            observations.add(observation)
            break
        else:
            raise PanelError("NO_CONTENT_DISJOINT_VARIANT")
    novel = []
    for visible, sealed in dev:
        ast = sealed["target_ast"]
        if shape_key(ast) in shapes or shape_key(ast, operators=False) in bare_shapes:
            continue
        row = make_row(visible, ast, {"kind": "FROZEN_DEVELOPMENT_ROW", "already_inspected": True})
        row["matched_teaching_pool_size_depth"] = dimensions(ast) in pool_dimensions
        novel.append(row)
        if len(novel) == n:
            break
    if len(novel) != n:
        raise PanelError("INSUFFICIENT_NEW_STRUCTURES")
    panels = dict(zip(PANELS, (teaching, familiar, novel)))
    validate_panels(panels, train, consumed)
    return panels, {"teaching_pool_rows": len(train), "actual_consumed_rows": len(consumed),
                    "teaching_pool_operator_shapes": len(shapes),
                    "actually_consumed_operator_shapes": len(exposed_shapes),
                    "teaching_pool_bare_shapes": len(bare_shapes),
                    "selection": "first 16 update-ordered consumed rows; first absent digit per source; first 16 dev novel shapes",
                    "structure_definition": "ordered binary operator/tree skeleton; leaf content erased",
                    "new_structure_additional_check": "also absent by ordered bare topology across all teaching pool rows"}


def validate_panels(panels, train, consumed):
    if set(panels) != set(PANELS):
        raise PanelError("PANEL_NAMES")
    source_ids = {train[i][0]["record_id"]: train[i] for i in consumed}
    all_contents = {sha(canonical(s["target_ast"])) for _, s in train}
    all_observations = {v["observation"] for v, _ in train}
    exposed_shapes = {shape_key(train[i][1]["target_ast"]) for i in consumed}
    all_shapes = {shape_key(s["target_ast"]) for _, s in train}
    all_bare = {shape_key(s["target_ast"], operators=False) for _, s in train}
    ids, contents = set(), set()
    for panel, rows in panels.items():
        if not 1 <= len(rows) <= 16:
            raise PanelError("PANEL_LIMIT")
        for row in rows:
            visible, ast = row["visible"], row["reference_ast"]
            content, shape = sha(canonical(ast)), shape_key(ast)
            if row["content_sha256"] != content or row["ordered_operator_shape_sha256"] != shape:
                raise PanelError("ROW_FINGERPRINT_MISMATCH")
            if visible["record_id"] in ids or content in contents:
                raise PanelError("PANEL_CONTENT_OVERLAP")
            ids.add(visible["record_id"])
            contents.add(content)
            if panel == "teaching_fit":
                original = source_ids.get(visible["record_id"])
                if original is None or original[0] != visible or original[1]["target_ast"] != ast:
                    raise PanelError("TEACHING_NOT_CONSUMED")
            elif panel == "new_content_familiar_structure":
                if content in all_contents or visible["observation"] in all_observations or shape not in exposed_shapes:
                    raise PanelError("FAMILIAR_PANEL_CONTAMINATED")
            elif shape in all_shapes or shape_key(ast, operators=False) in all_bare:
                raise PanelError("NEW_STRUCTURE_CONTAMINATED")


def _source_modules(source_lab, expected_pins):
    source_lab = Path(source_lab).resolve()
    for name, digest in expected_pins.items():
        if Path(name).name != name or sha((source_lab / name).read_bytes().replace(b"\r\n", b"\n")) != digest:
            raise PanelError("HISTORICAL_SOURCE_MISMATCH: " + name)
    sys.path.insert(0, str(source_lab))
    import q4_checkpoint
    if q4_checkpoint.runtime_source_pins() != expected_pins:
        raise PanelError("IMPORTED_SOURCE_MISMATCH")
    return q4_checkpoint


def prepare(source_lab, historical_run, authorization, *, gpu_uuid, n=16):
    run = Path(historical_run).resolve()
    plan = read(run / "plan.json")
    if sha(canonical(plan)) != PLAN_SHA:
        raise PanelError("HISTORICAL_PLAN_MISMATCH")
    checkpoint = _source_modules(source_lab, plan["source_pins"])
    from q3_load import load_split, manifest_sha, check_contract_binding
    from q4_device_capacity import shared_display_policy
    result = read(run / "result.json")
    updates = [read_line for read_line in (json.loads(line) for line in (run / "updates.jsonl").read_text().splitlines())]
    if (result.get("actual_updates") != plan["max_updates"] or result.get("engineering_status") != "ENGINEERING_RUN_COMPLETED"
            or result.get("checkpoint_weights_sha256") != WEIGHTS_SHA
            or [u.get("update") for u in updates] != list(range(1, 129))
            or plan["train_examples"] != 2048 or plan["max_updates"] != 128):
        raise PanelError("COMPLETED_EXPOSURE_NOT_ESTABLISHED")
    identity = {"source_pins": plan["source_pins"], "data_version": plan["data_version"],
                "manifest_sha256": plan["manifest_sha256"], "contract_digest": plan["contract_digest"],
                "environment": plan["environment"], "plan_sha256": PLAN_SHA, "authorization": result["authorization"]}
    checkpoint.verify_checkpoint(run / "checkpoint", expected_identity=identity, expected_width=64,
                                 expected_weights_sha256=WEIGHTS_SHA)
    data = Path(plan["data_dir"])
    if manifest_sha(data) != plan["manifest_sha256"] or check_contract_binding(data) != plan["contract_digest"]:
        raise PanelError("DATA_IDENTITY_MISMATCH")
    train, dev = load_split(data, "G", "train"), load_split(data, "G", "dev")
    indices = consumed_indices(len(train), plan["seed"], 128)
    panels, selection = build_panels(train, dev, indices, n)
    files = [run / name for name in ("plan.json", "result.json", "updates.jsonl", "checkpoint/manifest.json", "checkpoint/model_state.pt")]
    files += [data / name for name in ("manifest.json", "visible_G_train.jsonl", "sealed_G_train.jsonl", "visible_G_dev.jsonl", "sealed_G_dev.jsonl")]
    files += [Path(authorization).resolve(), Path(__file__).resolve()]
    return {"schema": SCHEMA, "status": "PREPARED_DIAGNOSTIC_NOT_CLAIM_BEARING",
            "historical_source_commit": HISTORICAL_SOURCE, "historical_run": str(run),
            "source_lab": str(Path(source_lab).resolve()), "source_pins": plan["source_pins"],
            "checkpoint_identity": identity, "weights_sha256": WEIGHTS_SHA, "files": [file_pin(p) for p in files],
            "authorization": {"mode": "STANDING_USER_CONVERSATION", "record": file_pin(authorization),
                              "limits_amendment": "Explicit 2026-09-23 GPU evaluation selection; supersedes CPU selection only; no owner identity fabricated"},
            "resources": {"device": "cuda:0", "max_wall_seconds": 120, "max_predictions": 48,
                          "actual_updates": 0, "cpu_threads": 2, "jobs": 1, "retries": 0,
                          "cloud": False, "paid_api": False, "cpu_fallback": False,
                          "device_policy": shared_display_policy(gpu_uuid)},
            "consumed_training_positions": indices,
            "exposure_evidence": "Reconstructed from pinned worker random.Random(seed).shuffle, 128 sequential single-example updates and completed checkpoint; per-row training IDs were not logged",
            "selection": selection, "panels": panels}


def validate_manifest(manifest, expected_sha):
    if sha(canonical(manifest)) != expected_sha or manifest.get("schema") != SCHEMA:
        raise PanelError("FROZEN_INPUT_MANIFEST_MISMATCH")
    for pin in manifest["files"]:
        if file_pin(pin["path"]) != pin:
            raise PanelError("FROZEN_FILE_MISMATCH: " + pin["path"])
    checkpoint = _source_modules(manifest["source_lab"], manifest["source_pins"])
    checkpoint.verify_checkpoint(Path(manifest["historical_run"]) / "checkpoint",
                                 expected_identity=manifest["checkpoint_identity"], expected_width=64,
                                 expected_weights_sha256=WEIGHTS_SHA)
    from q3_load import load_split
    plan = read(Path(manifest["historical_run"]) / "plan.json")
    train = load_split(Path(plan["data_dir"]), "G", "train")
    if manifest["consumed_training_positions"] != consumed_indices(len(train), plan["seed"], plan["max_updates"]):
        raise PanelError("EXPOSURE_MANIFEST_MISMATCH")
    validate_panels(manifest["panels"], train, manifest["consumed_training_positions"])
    dev = load_split(Path(plan["data_dir"]), "G", "dev")
    rebuilt, _ = build_panels(train, dev, manifest["consumed_training_positions"],
                              len(manifest["panels"]["teaching_fit"]))
    if canonical(rebuilt) != canonical(manifest["panels"]):
        raise PanelError("PANEL_SELECTION_OR_REFERENCE_DRIFT")
    from q4_device_capacity import validate_policy
    resources = manifest["resources"]
    expected = {"device": "cuda:0", "max_wall_seconds": 120, "max_predictions": 48,
                "actual_updates": 0, "cpu_threads": 2, "jobs": 1, "retries": 0,
                "cloud": False, "paid_api": False, "cpu_fallback": False,
                "device_policy": validate_policy(resources["device_policy"])}
    if canonical(resources) != canonical(expected):
        raise PanelError("RESOURCE_LIMIT_DRIFT")
    return checkpoint


def active_learning_jobs():
    """Local Windows process check; provider telemetry remains a separate guard."""
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        raise PanelError("LOCAL_JOB_INVENTORY_SHELL_UNAVAILABLE")
    command = [executable, "-NoProfile", "-NonInteractive", "-Command",
               "@(Get-CimInstance Win32_Process -ErrorAction Stop -Filter \"Name like '%python%'\" | Select-Object ProcessId,CommandLine) | ConvertTo-Json -Compress"]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=10,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if completed.returncode != 0:
        raise PanelError("LOCAL_JOB_INVENTORY_UNAVAILABLE")
    rows = json.loads(completed.stdout or "[]")
    if isinstance(rows, dict):
        rows = [rows]
    matches = []
    for row in rows:
        command_line = row.get("CommandLine")
        if command_line is None:
            raise PanelError("PYTHON_JOB_COMMAND_UNAVAILABLE")
        match = re.search(r"(?:preflight|execute_study|q4_smoke_job|typed_pointer_worker|rt[127]_(?:run|diag)|train_[a-z0-9_]+)\.py", command_line, re.I)
        if match:
            matches.append({"pid": row["ProcessId"], "entry_point": match.group()})
    return {"inventory_executable": executable, "python_processes_checked": len(rows), "matching_learning_jobs": matches,
            "limits": "Known learning entry points; GPU admission checks capacity independently"}


def grade(ast, reference):
    try:
        prediction_shape = shape_key(ast)
        valid = True
    except (ValueError, TypeError, KeyError):
        prediction_shape, valid = None, False
    return {"canonical_exact": valid and ast == reference, "parse_valid": valid,
            "operator_structure_exact": valid and prediction_shape == shape_key(reference)}


def summarize(predictions):
    result = {}
    for name in PANELS:
        rows = [row for row in predictions if row["panel"] == name]
        result[name] = {"n": len(rows), **{metric: sum(row["checks"][metric] for row in rows)
                         for metric in ("canonical_exact", "parse_valid", "operator_structure_exact")}}
    return result


def _worker(manifest_path, expected_sha, output):
    manifest = read(manifest_path)
    checkpoint = validate_manifest(manifest, expected_sha)
    out = Path(output)
    nonce = os.environ.pop("HELM_Q4_PANEL_NONCE", "")
    if not nonce or sha(nonce.encode()) != read(out / "claim.json")["nonce_sha256"]:
        raise PanelError("SUPERVISED_WORKER_REQUIRED")
    write_once(out / "worker_started.json", {"pid": os.getpid(), "manifest_sha256": expected_sha})
    import torch
    environment = manifest["checkpoint_identity"]["environment"]
    if (str(torch.__version__) != environment["torch_distribution"]
            or torch.version.cuda != environment["torch_build"]["cuda"]
            or sys.version.split()[0] != environment["python"]):
        raise PanelError("HISTORICAL_RUNTIME_VERSION_MISMATCH")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    from learner_q4_representation import from_visible_record
    model = checkpoint.load_checkpoint(Path(manifest["historical_run"]) / "checkpoint",
                expected_identity=manifest["checkpoint_identity"], expected_weights_sha256=WEIGHTS_SHA,
                width=64, device="cuda:0")
    predictions = []
    with (out / "predictions.jsonl").open("xb") as stream:
        for panel, rows in manifest["panels"].items():
            for row in rows:
                generated = model.generate(from_visible_record(row["visible"]))
                prediction = {"panel": panel, "record_id": row["visible"]["record_id"],
                              "outcome": generated.outcome, "ast": generated.ast, "steps": generated.steps}
                stream.write(canonical(prediction) + b"\n")
                stream.flush()
                predictions.append(prediction)
    # All predictions fixed before target-based scoring; no target enters generate.
    rows = {row["visible"]["record_id"]: row for values in manifest["panels"].values() for row in values}
    for prediction in predictions:
        prediction["checks"] = grade(prediction["ast"], rows[prediction["record_id"]]["reference_ast"])
    validate_manifest(manifest, expected_sha)
    write_once(out / "checks.json", predictions)
    write_once(out / "result.json", {"status": "DIAGNOSTIC_MEASURED_NOT_CERTIFIED", "actual_updates": 0,
               "manifest_sha256": expected_sha, "weights_sha256": WEIGHTS_SHA,
               "panels": summarize(predictions), "torch": torch.__version__, "cuda": torch.version.cuda,
               "device": torch.cuda.get_device_name(0), "cpu_threads": torch.get_num_threads(),
               "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(0),
               "limitations": ["Small deterministic samples; not independent hidden evaluation",
                               "Familiar-content references use a declared token/AST substitution, not recompilation",
                               "No optimizer, updates, training, compiler answers as predictions, or capability certificate"]})


def execute(manifest_path, expected_sha, output):
    manifest = read(manifest_path)
    validate_manifest(manifest, expected_sha)
    out = Path(output).resolve()
    if any(out == Path(pin["path"]).parent or out.is_relative_to(Path(manifest["historical_run"])) for pin in manifest["files"]):
        raise PanelError("OUTPUT_MUST_BE_NEW_SEPARATE_DIRECTORY")
    out.mkdir(parents=False, exist_ok=False)
    nonce = secrets.token_hex(32)
    write_once(out / "claim.json", {"manifest_sha256": expected_sha, "nonce_sha256": sha(nonce.encode())})
    from q4_smoke_job import _device_lock_path, _wait_for_worker
    from q4_device_capacity import check_prelaunch
    started, status, failure, returncode = time.monotonic(), "FAILED", None, None
    lock, owns_lock = _device_lock_path("cuda:0"), False
    resource = manifest["resources"]
    try:
        with lock.open("xb") as stream:
            owns_lock = True
            stream.write(canonical({"pid": os.getpid(), "manifest_sha256": expected_sha}))
        jobs = active_learning_jobs()
        write_once(out / "local_job_check.json", jobs)
        if jobs["matching_learning_jobs"]:
            raise PanelError("OTHER_LEARNING_JOB_ACTIVE")
        write_once(out / "device_prelaunch.json", check_prelaunch(resource["device_policy"], "cuda:0"))
        env = dict(os.environ, HELM_Q4_PANEL_NONCE=nonce, CUBLAS_WORKSPACE_CONFIG=":4096:8", PYTHONDONTWRITEBYTECODE="1")
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "_worker", "--manifest", str(Path(manifest_path).resolve()),
                   "--sha256", expected_sha, "--output", str(out)]
        with (out / "worker.log").open("xb") as log:
            with subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)) as process:
                try:
                    returncode = _wait_for_worker(process, resource, started, out)
                    if returncode != 0:
                        raise PanelError("WORKER_FAILED: " + str(returncode))
                    result = read(out / "result.json")
                    if result["actual_updates"] != 0 or result["manifest_sha256"] != expected_sha:
                        raise PanelError("WORKER_RESULT_MISMATCH")
                    status = "COMPLETE"
                except BaseException:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=10)
                    raise
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        if owns_lock:
            lock.unlink()
        write_once(out / "supervisor.json", {"status": status, "failure": failure, "returncode": returncode,
                   "manifest_sha256": expected_sha, "elapsed_seconds": time.monotonic() - started,
                   "automatic_retries": 0, "authorization": manifest["authorization"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    prep = sub.add_parser("prepare")
    for name in ("source-lab", "historical-run", "authorization", "gpu-uuid", "output"):
        prep.add_argument("--" + name, required=True)
    for mode in ("execute", "_worker", "verify"):
        cmd = sub.add_parser(mode)
        cmd.add_argument("--manifest", required=True)
        cmd.add_argument("--sha256", required=True)
        if mode != "verify":
            cmd.add_argument("--output", required=True)
    args = vars(parser.parse_args())
    mode = args.pop("mode")
    if mode == "prepare":
        output = args.pop("output")
        manifest = prepare(**args)
        write_once(output, manifest)
        print(sha(canonical(manifest)))
    elif mode == "verify":
        validate_manifest(read(args["manifest"]), args["sha256"])
        print("VERIFIED_NO_NEURAL_EXECUTION")
    else:
        (execute if mode == "execute" else _worker)(args["manifest"], args["sha256"], args["output"])


if __name__ == "__main__":
    main()
