"""One bounded, explicitly authorized CUDA R1 engineering job. Default: prepare.

Preparation reads only source/pin/contract/manifest metadata, never data rows.
Execution requires an Ed25519 signature from a separately owner-pinned key;
neither a status string nor this program supplies human authorization. No cloud,
API, automatic retry, resume, eval-split access, or CPU neural fallback exists.
The actual neural worker has NOT been run during code-only implementation.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time

from q4_checkpoint import canonical, digest, runtime_source_pins

HERE = Path(__file__).resolve().parent
REPO_ROOT = next((path for path in HERE.parents if (path / ".git").exists()), HERE)
PLAN_SCHEMA = "helm-cas-expression-lab.q4-smoke-plan/0.1"
AUTH_SCHEMA = "helm-cas-expression-lab.q4-signed-job/0.1"


class JobError(ValueError):
    pass


def _read_json(path):
    from q3_load import strict_loads
    try:
        return strict_loads(Path(path).read_text(encoding="utf-8"), str(path))
    except (OSError, UnicodeError, ValueError) as error:
        raise JobError("INVALID_JOB_JSON") from error


def _bounded_int(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise JobError("INVALID_PLAN: %s must be in %d..%d" % (name, low, high))
    return value


def _environment_metadata():
    from q4_runtime_metadata import environment_metadata
    return environment_metadata()


def prepare_plan(*, data_dir, data_version, output, seed=20260921, width=64,
                 max_updates=128, max_wall_seconds=1800, train_examples=2048, dev_examples=16,
                 device="cuda:0") -> dict:
    """Metadata-only preparation; this function does NOT authorize execution."""
    _bounded_int(seed, "seed", 0, 2**32 - 1)
    _bounded_int(max_updates, "max_updates", 1, 128)
    _bounded_int(max_wall_seconds, "max_wall_seconds", 1, 1800)
    _bounded_int(train_examples, "train_examples", 1, 2048)
    _bounded_int(dev_examples, "dev_examples", 1, 256)
    if type(width) is not int or width not in (64, 128):
        raise JobError("INVALID_PLAN: width must be 64 or 128")
    if type(device) is not str or re.fullmatch(r"cuda:[0-9]+", device) is None:
        raise JobError("GPU_REQUIRED: explicit CUDA device required")
    data, out = Path(data_dir).resolve(), Path(output).resolve()
    if out == data or out.is_relative_to(data) or data.is_relative_to(out):
        raise JobError("INVALID_PLAN: output and source data must not contain one another")
    from q3_load import check_pins, check_contract_binding, manifest_of, manifest_sha
    pin = check_pins(data)
    contract = check_contract_binding(data)
    manifest = manifest_of(data)
    if type(data_version) is not str or manifest.get("schema") != data_version:
        raise JobError("DATA_VERSION_MISMATCH: name the exact pinned dataset version")
    counts = manifest.get("counts", {})
    if (type(counts.get("G_train")) is not int or counts["G_train"] < train_examples
            or type(counts.get("G_dev")) is not int or counts["G_dev"] < dev_examples):
        raise JobError("INVALID_PLAN: requested rows exceed the pinned G train/dev counts")
    return {"schema": PLAN_SCHEMA, "status": "PREPARED_NOT_AUTHORIZATION", "task": "T14_R1_G_ENGINEERING_SMOKE",
            "data_dir": str(data), "data_version": data_version, "manifest_sha256": manifest_sha(data),
            "export_report_sha256": pin["export_report_sha256"], "contract_digest": contract,
            "contracts_file_sha256": digest((HERE / "OPERATION_CONTRACTS.json").read_bytes().replace(b"\r\n", b"\n")),
            "pins_file_sha256": digest((HERE / "Q3_DATA_PINS.json").read_bytes().replace(b"\r\n", b"\n")),
            "source_pins": runtime_source_pins(), "output": str(out), "seed": seed, "width": width,
            "max_updates": max_updates, "max_wall_seconds": max_wall_seconds, "train_examples": train_examples,
            "dev_examples": dev_examples, "device": device, "family": "G", "splits": ["train", "dev"],
            "learning_rate": 0.001, "clip_norm": 1.0, "max_concurrent_jobs": 1,
            "numerical_policy": "CUDA_FLOAT32_DETERMINISTIC_OR_FAIL_NO_FALLBACK",
            "environment": _environment_metadata(),
            "evaluation_custody": "EVALUATION_NOT_INDEPENDENT", "resume": False}


def validate_plan(plan: dict) -> dict:
    if type(plan) is not dict:
        raise JobError("INVALID_PLAN: object required")
    try:
        fresh = prepare_plan(**{key: plan[key] for key in
                                ("data_dir", "data_version", "output", "seed", "width", "max_updates",
                                 "max_wall_seconds", "train_examples", "dev_examples", "device")})
    except KeyError as error:
        raise JobError("INVALID_PLAN: required field missing") from error
    if canonical(fresh) != canonical(plan):
        raise JobError("PLAN_DRIFT: source, data, limits, or immutable plan fields changed")
    return fresh


def verify_authorization(plan: dict, authorization, trusted_public_key, trusted_key_sha256: str) -> None:
    """Verify scope/expiry/signature, not the human ownership of an arbitrary key.

The OWNER must establish the external key fingerprint independently, before the
job. This tool never generates a key/signature or treats a local approval word
as authority. The public key must not be inside the source/data/output tree.
"""
    keypath = Path(trusted_public_key).resolve()
    if any(keypath.is_relative_to(root) for root in (REPO_ROOT, Path(plan["data_dir"]), Path(plan["output"]))):
        raise JobError("UNTRUSTED_KEY_LOCATION: keep the owner trust anchor outside job-controlled trees")
    try:
        raw_key = keypath.read_bytes()
    except OSError as error:
        raise JobError("TRUST_ANCHOR_UNAVAILABLE") from error
    if (type(trusted_key_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", trusted_key_sha256) is None
            or len(raw_key) != 32 or digest(raw_key) != trusted_key_sha256):
        raise JobError("TRUST_ANCHOR_MISMATCH")
    auth = _read_json(authorization)
    if (type(auth) is not dict or set(auth) != {"schema", "plan_sha256", "expires_utc", "signature_base64"}
            or auth["schema"] != AUTH_SCHEMA or auth["plan_sha256"] != digest(canonical(plan))):
        raise JobError("JOB_NOT_AUTHORIZED: signed plan identity differs")
    try:
        expiry = datetime.fromisoformat(auth["expires_utc"].replace("Z", "+00:00"))
        if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
            raise ValueError("expired or timezone missing")
        signature = base64.b64decode(auth["signature_base64"], validate=True)
        payload = {key: value for key, value in auth.items() if key != "signature_base64"}
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(raw_key).verify(signature, canonical(payload))
    except ImportError as error:
        raise JobError("AUTH_VERIFIER_UNAVAILABLE: cryptography required; no bypass") from error
    except Exception as error:
        raise JobError("JOB_NOT_AUTHORIZED: bad signature or expiry") from error


def _write_json(path: Path, value):
    with path.open("xb") as stream:
        stream.write(canonical(value) + b"\n")


def _device_lock_path(device: str) -> Path:
    # Conservative local-smoke scope: one Q4 neural job across this user's GPUs.
    # Do not key by CUDA ordinal, which need not be a physical nvidia-smi index.
    return Path(tempfile.gettempdir()) / "helm-q4-neural-job.lock"


def _check_device_idle(device: str):
    """Read provider process metadata; missing/unreadable capacity fails closed."""
    if os.environ.get("CUDA_VISIBLE_DEVICES"):
        raise JobError("GPU_MAPPING_UNSUPPORTED: explicit physical device indexing required")
    try:
        result = subprocess.run(["nvidia-smi", "--query-compute-apps=pid",
                                 "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise JobError("GPU_CAPACITY_UNAVAILABLE: cannot inspect selected device") from error
    if result.returncode != 0:
        raise JobError("GPU_CAPACITY_UNAVAILABLE: nvidia-smi query failed")
    if result.stdout.strip():
        raise JobError("GPU_BUSY_OR_UNKNOWN: selected device reports compute users")


def execute_plan(plan_path, authorization, trusted_public_key, trusted_key_sha256):
    """Reserve one output, supervise one worker, kill on timeout; never retry."""
    plan = validate_plan(_read_json(plan_path))
    verify_authorization(plan, authorization, trusted_public_key, trusted_key_sha256)
    out = Path(plan["output"])
    out.mkdir(parents=False, exist_ok=False)  # existing output means already used; never overwrite/resume
    nonce = secrets.token_hex(32)
    _write_json(out / "claim.json", {"plan_sha256": digest(canonical(plan)), "worker_nonce_sha256": digest(nonce.encode()),
                                     "supervisor_pid": os.getpid()})
    _write_json(out / "plan.json", plan)
    environment = dict(os.environ, HELM_Q4_WORKER_NONCE=nonce, CUBLAS_WORKSPACE_CONFIG=":4096:8")
    command = [sys.executable, str(Path(__file__).resolve()), "_worker", "--plan", str(Path(plan_path).resolve()),
               "--authorization", str(Path(authorization).resolve()), "--trusted-public-key", str(Path(trusted_public_key).resolve()),
               "--trusted-key-sha256", trusted_key_sha256]
    started = time.monotonic()
    status, returncode = "FAILED", None
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    device_lock = _device_lock_path(plan["device"])
    owns_lock = False
    try:
        with device_lock.open("xb") as lock:
            owns_lock = True
            lock.write(canonical({"pid": os.getpid(), "plan_sha256": digest(canonical(plan))}))
        _check_device_idle(plan["device"])
        with (out / "worker.log").open("xb") as log:
            with subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=environment,
                                  creationflags=flags) as process:
                try:
                    remaining = max(0, plan["max_wall_seconds"] - (time.monotonic() - started))
                    returncode = process.wait(timeout=remaining)
                    if returncode == 0:
                        result = _read_json(out / "result.json")
                        if (result.get("plan_sha256") != digest(canonical(plan))
                                or result.get("actual_updates") != plan["max_updates"]):
                            raise JobError("WORKER_RESULT_MISMATCH")
                        status = "COMPLETE"
                except subprocess.TimeoutExpired:
                    process.kill()
                    returncode = process.wait(timeout=10)
                    status = "BUDGET_EXHAUSTED"
                except BaseException:
                    process.kill()
                    returncode = process.wait(timeout=10)
                    raise
    finally:
        if owns_lock:
            device_lock.unlink()
        _write_json(out / "supervisor.json", {"status": status, "returncode": returncode,
                                               "elapsed_seconds": time.monotonic() - started,
                                               "plan_sha256": digest(canonical(plan)), "automatic_retries": 0})
    if status != "COMPLETE":
        raise JobError(status + ": preserved output; no retry or resume")
    return out


def _worker(plan_path, authorization, trusted_public_key, trusted_key_sha256):
    plan = validate_plan(_read_json(plan_path))
    verify_authorization(plan, authorization, trusted_public_key, trusted_key_sha256)
    out = Path(plan["output"])
    nonce = os.environ.pop("HELM_Q4_WORKER_NONCE", "")
    claim = _read_json(out / "claim.json")
    if (not nonce or claim.get("plan_sha256") != digest(canonical(plan))
            or claim.get("worker_nonce_sha256") != digest(nonce.encode())):
        raise JobError("WORKER_NOT_OWNED: use the supervised execute command")
    # Exclusive worker lock is retained after success or failure: one launch only.
    _write_json(out / "worker_started.json", {"pid": os.getpid(), "plan_sha256": digest(canonical(plan))})
    deadline = time.monotonic() + plan["max_wall_seconds"]

    def check_deadline():
        if time.monotonic() >= deadline:
            raise JobError("BUDGET_EXHAUSTED: worker deadline")

    # Targets are read only inside the authorized supervised worker, never prepare.
    from q3_load import load_split, load_visible
    from learner_q4_representation import from_visible_record
    from learner_q4_decoder import ast_to_tokens, free_decode
    from learner_q4_neural import NeuralConfig, build_model
    from q4_checkpoint import save_checkpoint
    pairs = load_split(Path(plan["data_dir"]), "G", "train")[:plan["train_examples"]]
    training_inputs = [from_visible_record(visible) for visible, _ in pairs]
    training_targets = [ast_to_tokens(sealed["target_ast"]) for _, sealed in pairs]
    del pairs
    dev_visible = load_visible(Path(plan["data_dir"]), "G", "dev")[:plan["dev_examples"]]
    import random
    import torch
    torch.manual_seed(plan["seed"])
    torch.cuda.manual_seed_all(plan["seed"])
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    model = build_model(NeuralConfig(plan["width"]), device=plan["device"])
    optimizer = torch.optim.AdamW(model.parameters(), lr=plan["learning_rate"])
    order = list(range(len(training_inputs)))
    random.Random(plan["seed"]).shuffle(order)
    with (out / "updates.jsonl").open("xb") as updates:
        for update in range(plan["max_updates"]):
            check_deadline()
            index = order[update % len(order)]
            target = training_targets[index]
            optimizer.zero_grad(set_to_none=True)
            logits = model.teacher_forced_logits(training_inputs[index], target[:-1])
            gold = torch.tensor(target, dtype=torch.long, device=model._device())
            loss = torch.nn.functional.cross_entropy(logits, gold)
            if not torch.isfinite(loss).item():
                raise JobError("NUMERICAL_FAILURE: training loss")
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), plan["clip_norm"], error_if_nonfinite=True)
            optimizer.step()
            updates.write(canonical({"update": update + 1, "class": "main", "loss": float(loss.item()),
                                     "pre_clip_gradient_norm": float(norm.item()), "clip_norm": plan["clip_norm"],
                                     "learning_rate": plan["learning_rate"]}) + b"\n")
            updates.flush()
    identity = {"source_pins": plan["source_pins"], "data_version": plan["data_version"],
                "manifest_sha256": plan["manifest_sha256"], "contract_digest": plan["contract_digest"],
                "environment": plan["environment"],
                "plan_sha256": digest(canonical(plan))}
    check_deadline()
    checkpoint_manifest = save_checkpoint(model, out / "checkpoint", identity=identity)
    predictions = []
    with (out / "dev_predictions.jsonl").open("xb") as stream:
        for row in dev_visible:
            check_deadline()
            vector = model.encode(from_visible_record(row))

            def bounded_logits(bottleneck, generated):
                check_deadline()
                return model.next_logits(bottleneck, generated)

            prediction = free_decode(vector, bounded_logits)
            record = {"record_id": row["record_id"], "outcome": prediction.outcome, "ast": prediction.ast,
                      "steps": prediction.steps}
            predictions.append(record)
            stream.write(canonical(record) + b"\n")
            stream.flush()
    # Separate evaluator stage; dev targets appear only AFTER predictions are fixed.
    dev_pairs = load_split(Path(plan["data_dir"]), "G", "dev")[:plan["dev_examples"]]
    by_depth = {}
    for prediction, (visible, sealed) in zip(predictions, dev_pairs):
        if prediction["record_id"] != visible["record_id"]:
            raise JobError("PREDICTION_IDENTITY_MISMATCH")
        key = str(sealed["depth"])
        score = by_depth.setdefault(key, {"n": 0, "generated": 0, "canonical_exact": 0})
        score["n"] += 1
        score["generated"] += prediction["outcome"] == "GENERATED"
        score["canonical_exact"] += prediction["ast"] == sealed["target_ast"]
    validate_plan(plan)
    _write_json(out / "result.json", {"engineering_status": "ENGINEERING_RUN_COMPLETED",
                                      "representation_status": "MEASURED_ON_DEV_ONLY_NOT_CERTIFIED",
                                      "operation_status": "NOT_EVALUATED", "benefit_status": "NOT_EVALUATED",
                                      "evaluation_custody": "EVALUATION_NOT_INDEPENDENT",
                                      "actual_updates": plan["max_updates"], "dev_by_depth": by_depth,
                                      "checkpoint_weights_sha256": checkpoint_manifest["weights_sha256"],
                                      "runtime": {"environment": plan["environment"], "torch": torch.__version__,
                                                   "cuda": torch.version.cuda,
                                                   "device_name": torch.cuda.get_device_name(model._device())},
                                      "fresh_process_reload": "NOT_EXECUTED", "eval_split_access": False,
                                      "plan_sha256": digest(canonical(plan))})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    prepare = modes.add_parser("prepare", help="metadata-only dry run; no neural execution")
    prepare.add_argument("--data-dir", required=True)
    prepare.add_argument("--data-version", required=True)
    prepare.add_argument("--output", required=True)
    prepare.add_argument("--plan-out")
    for name, default in (("seed", 20260921), ("width", 64), ("max-updates", 128),
                          ("max-wall-seconds", 1800), ("train-examples", 2048), ("dev-examples", 16)):
        prepare.add_argument("--" + name, type=int, default=default)
    prepare.add_argument("--device", default="cuda:0")
    for mode in ("execute", "_worker"):
        command = modes.add_parser(mode, help="signed authorized job" if mode == "execute" else argparse.SUPPRESS)
        for option in ("plan", "authorization", "trusted-public-key", "trusted-key-sha256"):
            command.add_argument("--" + option, required=True)
    args = vars(parser.parse_args(argv))
    mode = args.pop("mode")
    if mode == "prepare":
        plan_out = args.pop("plan_out")
        plan = prepare_plan(**args)
        if plan_out:
            _write_json(Path(plan_out), plan)
        print(json.dumps({"plan": plan, "plan_sha256": digest(canonical(plan))}, indent=2))
    elif mode == "execute":
        args["plan_path"] = args.pop("plan")
        print(execute_plan(**args))
    else:
        args["plan_path"] = args.pop("plan")
        _worker(**args)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Q4_JOB_FAILED: %s" % error, file=sys.stderr)
        raise SystemExit(1)
