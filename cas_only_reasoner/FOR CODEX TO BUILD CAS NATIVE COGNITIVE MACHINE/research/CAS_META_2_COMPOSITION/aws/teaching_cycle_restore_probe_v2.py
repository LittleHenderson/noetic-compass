"""Slice-two pinned AWS-only restore proof; no optimizer step, prediction or saved-state write.

This helper is outside the unchanged worker bundle. A separate parent must
admit its raw receipt before releasing training. Importing it is inert.
The second slice allows up to 900 seconds for its larger retained history
and the frozen controller's quadratic replay work. This is a bound, not a
measured guarantee or additional training allocation.
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import stat
import sys
import time
from zipfile import ZipFile

SCHEMA = "cas-teaching-gpu-restore/1"
JOB_ROOT = "/opt/cas-teaching/job"
CAMPAIGN_ROOT = JOB_ROOT + "/train/campaign"
RESUME_SUMMARY = "train_continued_001/campaign_summary.json"
RETAINED_SUMMARY = "train/campaign_summary.json"
ARMS = ("cas.aligned", "cas.ordinary", "generic.aligned", "generic.ordinary")
BYTE_LIMIT = 1024**3
FILE_LIMIT = 64 * 1024**2


class RestoreError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise RestoreError("TEACHING_RESTORE:" + code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def safe(path):
    path = Path(path).absolute()
    require(".." not in path.parts, "PARENT_PATH_REJECTED")
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (path, *path.parents)), "LINK_PATH_REJECTED")
    return path


def identity(path, maximum=FILE_LIMIT):
    path = safe(path)
    observed = path.stat()
    require(stat.S_ISREG(observed.st_mode) and observed.st_nlink == 1
            and 0 < observed.st_size <= maximum, "SINGLE_LINK_BOUNDED_FILE_REQUIRED")
    digest, count = sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024**2):
            count += len(chunk)
            require(count <= observed.st_size, "FILE_GREW")
            digest.update(chunk)
    require(count == observed.st_size, "FILE_SIZE_CHANGED")
    return {"bytes": count, "sha256": digest.hexdigest()}


def pinned(path, expected, maximum=FILE_LIMIT):
    require(type(expected) is str and re.fullmatch(r"[a-f0-9]{64}", expected)
            and expected != "0" * 64, "EXTERNAL_PIN_REQUIRED")
    actual = identity(path, maximum)
    require(actual["sha256"] == expected, "FILE_PIN_MISMATCH")
    return actual


def verify_source_bundle(bundle, archive):
    """No package code executes until its extracted bytes match the pinned ZIP."""
    bundle = safe(bundle)
    require(bundle.is_dir(), "SOURCE_BUNDLE_REQUIRED")
    expected, total = {}, 0
    with ZipFile(archive) as source:
        require(len(source.infolist()) == 17, "FROZEN_SOURCE_MEMBER_COUNT")
        for member in source.infolist():
            name = member.filename
            require(name == member.orig_filename and not member.is_dir() and not member.flag_bits & 1
                    and stat.S_IFMT(member.external_attr >> 16) in (0, stat.S_IFREG)
                    and "\\" not in name and not name.startswith("/")
                    and all(part not in ("", ".", "..") and ":" not in part for part in name.split("/"))
                    and name.casefold() not in expected, "SOURCE_MEMBER_INVALID")
            require(0 < member.file_size <= FILE_LIMIT, "SOURCE_MEMBER_BYTE_BOUND")
            total += member.file_size
            require(total <= FILE_LIMIT, "SOURCE_EXPANDED_BYTE_BOUND")
            raw = source.read(member)
            require(identity(bundle / name) == {"bytes": len(raw), "sha256": sha256(raw).hexdigest()},
                    "EXTRACTED_SOURCE_CHANGED")
            expected[name.casefold()] = name
    actual = []
    for directory, dirs, files in os.walk(bundle, followlinks=False):
        for name in dirs:
            safe(Path(directory) / name)
        for name in files:
            entry = safe(Path(directory) / name)
            actual.append(entry.relative_to(bundle).as_posix())
    require(set(actual) == set(expected.values()), "EXTRACTED_SOURCE_INVENTORY_CHANGED")
    return {"files": len(actual), "bytes": total}


def verify_tree(job_root, manifest):
    """Check both prior roots exactly, including unexpected empty directories."""
    root = safe(job_root)
    require(manifest.get("schema") == "cas-teaching-prior-state/2"
            and manifest.get("summary_path") == RESUME_SUMMARY
            and manifest.get("retained_summary_path") == RETAINED_SUMMARY,
            "SLICE_TWO_PRIOR_SUMMARIES_REQUIRED")
    expected = manifest["members"]
    require(type(expected) is dict and 0 < len(expected) < 20000, "MEMBER_BOUND")
    require(RESUME_SUMMARY in expected and RETAINED_SUMMARY in expected, "BOTH_PRIOR_SUMMARIES_REQUIRED")
    expected_dirs = {"train", "train_continued_001"}
    for name in expected:
        require(type(name) is str
                and (name in (RESUME_SUMMARY, RETAINED_SUMMARY) or name.startswith("train/campaign/"))
                and "\\" not in name
                and all(p not in ("", ".", "..") and ":" not in p for p in name.split("/")), "MEMBER_PATH_INVALID")
        parts = name.split("/")
        expected_dirs.update("/".join(parts[:end]) for end in range(1, len(parts)))
    seen, dirs, total = {}, {"train", "train_continued_001"}, 0
    for prior_root in ("train", "train_continued_001"):
        tree = safe(root / prior_root)
        require(tree.is_dir(), "PRIOR_TREE_REQUIRED")
        for directory, dirnames, filenames in os.walk(tree, followlinks=False):
            for name in dirnames:
                entry = safe(Path(directory) / name)
                require(entry.is_dir(), "REGULAR_DIRECTORY_REQUIRED")
                relative = entry.relative_to(root).as_posix()
                require(relative in expected_dirs, "UNEXPECTED_PRIOR_DIRECTORY")
                dirs.add(relative)
            for name in filenames:
                entry = safe(Path(directory) / name)
                relative = entry.relative_to(root).as_posix()
                require(relative in expected, "UNEXPECTED_PRIOR_FILE")
                observed = identity(entry)
                require(observed == expected[relative], "PRIOR_FILE_CHANGED")
                seen[relative] = observed
                total += observed["bytes"]
                require(total <= BYTE_LIMIT, "PRIOR_TREE_BYTE_BOUND")
    require(set(seen) == set(expected) and dirs == expected_dirs, "PRIOR_TREE_INCOMPLETE")
    require(total == manifest["expanded_bytes"], "PRIOR_TREE_SIZE_MISMATCH")
    return {"files": len(seen), "bytes": total, "sha256": sha256(canonical(seen)).hexdigest()}


def optimizer_fingerprint(value, torch):
    """Exact values/dtypes/shapes, excluding device placement only.

    AdamW may place its scalar step counter on CPU after load. Host transfers
    here serialize bytes; they do not run a model or optimizer on the host.
    """
    nodes, tensor_bytes = 0, 0

    def visit(item, depth):
        nonlocal nodes, tensor_bytes
        nodes += 1
        require(depth <= 64 and nodes <= 100000, "OPTIMIZER_STRUCTURE_BOUND")
        if torch.is_tensor(item):
            require(bool(torch.isfinite(item).all().item()), "NONFINITE_OPTIMIZER_TENSOR")
            size = item.numel() * item.element_size()
            tensor_bytes += size
            require(0 <= size <= FILE_LIMIT and tensor_bytes <= FILE_LIMIT, "OPTIMIZER_TENSOR_BYTE_BOUND")
            raw_tensor = item.detach().contiguous().reshape(-1).view(torch.uint8).cpu()
            raw = bytes(raw_tensor.untyped_storage())
            require(len(raw) == size, "OPTIMIZER_STORAGE_LENGTH_MISMATCH")
            return ["tensor", str(item.dtype), list(item.shape), len(raw), sha256(raw).hexdigest()]
        if item is None:
            return ["none"]
        if type(item) is bool:
            return ["bool", item]
        if type(item) is int:
            return ["int", str(item)]
        if type(item) is float:
            require(math.isfinite(item), "NONFINITE_OPTIMIZER_NUMBER")
            return ["float", item.hex()]
        if type(item) is str:
            require(len(item) <= 4096, "OPTIMIZER_STRING_BOUND")
            return ["str", item]
        if type(item) in (list, tuple):
            return [type(item).__name__, [visit(x, depth + 1) for x in item]]
        if type(item) in (dict, OrderedDict):
            require(all(type(key) in (int, str) for key in item), "OPTIMIZER_KEY_TYPE_INVALID")
            pairs = [[visit(key, depth + 1), visit(val, depth + 1)] for key, val in item.items()]
            return ["mapping", sorted(pairs, key=lambda row: canonical(row[0]))]
        raise RestoreError("TEACHING_RESTORE:OPTIMIZER_TYPE_INVALID")

    description = visit(value, 0)
    return sha256(canonical(description)).hexdigest()


def verify_optimizer_devices(learner, torch):
    """CUDA moments are required; only AdamW's scalar step may stay on CPU."""
    count = 0
    parameters = [p for group in learner.optimizer.param_groups for p in group["params"]]
    require({id(p) for p in learner.optimizer.state} <= {id(p) for p in parameters},
            "OPTIMIZER_STATE_PARAMETER_SCOPE_MISMATCH")
    for parameter, values in learner.optimizer.state.items():
        require(parameter.device == learner.device and type(values) is dict,
                "OPTIMIZER_PARAMETER_DEVICE_INVALID")
        require(set(values) in ({"step", "exp_avg", "exp_avg_sq"},
                               {"step", "exp_avg", "exp_avg_sq", "max_exp_avg_sq"}),
                "ADAMW_STATE_FIELDS_INVALID")
        for key, tensor in values.items():
            require(torch.is_tensor(tensor), "ADAMW_STATE_TENSOR_REQUIRED")
            if key == "step":
                require(tensor.numel() == 1 and
                        (tensor.device == parameter.device or str(tensor.device) == "cpu"),
                        "ADAMW_STEP_DEVICE_INVALID")
            else:
                require(tensor.device == parameter.device and tensor.shape == parameter.shape
                        and tensor.dtype == parameter.dtype, "ADAMW_MOMENT_DEVICE_OR_GEOMETRY_INVALID")
            count += 1
    require(learner.steps == 0 or count > 0, "LOADED_OPTIMIZER_STATE_EMPTY")
    return count


def restore_arms(*, learners, data, manifest, summary, campaign_root, session_type,
                 allocation_type, torch, checkpoint_load, tick=lambda: None):
    """Call the frozen session constructor, with all write/update paths denied."""
    require(set(learners) == set(ARMS), "FOUR_LEARNERS_REQUIRED")
    results = {}
    for arm in ARMS:
        tick()
        learner = learners[arm]
        expected = manifest["arms"][arm]
        report = summary["arms"][arm]
        root = safe(Path(campaign_root) / arm)
        transaction = expected["committed_transactions"]
        latest = root / f"journal/txn-{transaction:08d}"
        checkpoint = latest / "candidate.pt"
        pinned(checkpoint, expected["checkpoint_file_sha256"])
        pinned(latest / "receipt.json", expected["checkpoint_receipt_sha256"])
        require((root / "journal/journal.json").is_file() and transaction >= 1,
                "COMMITTED_JOURNAL_REQUIRED")
        initial = learner.state_identity()
        require(initial["run_id"] == expected["run_id"]
                and initial["checkpoint_sha256"] == report["initial_checkpoint"]["state_sha256"]
                and learner.steps == 0, "INITIAL_CANDIDATE_MISMATCH")
        forbidden = []

        def deny(*args, **kwargs):
            forbidden.append("write_or_learning_attempt")
            raise RestoreError("TEACHING_RESTORE:LEARNING_OR_WRITE_FORBIDDEN")

        # This process only restores. Never call a learner's teaching/prediction
        # path or allow an absent checkpoint to silently create a new initial one.
        hooks = ((learner, "teach"), (learner, "predict"), (learner, "save_checkpoint"),
                 (learner.optimizer, "step"))
        originals = [(owner, name, getattr(owner, name)) for owner, name in hooks]
        try:
            for owner, name, _ in originals:
                setattr(owner, name, deny)
            session = session_type(learner, data["training_cases"], data["development_cases"],
                arm.split(".")[1], root, data["manifest"]["source_sha256"],
                allocation=allocation_type(**data["manifest"]["profile"]["allocation"]),
                seed=data["manifest"]["profile"]["seed"], execution_mode="cuda")
            tick()
            state = learner.state_identity()
            require(not forbidden and learner.steps == expected["committed_optimizer_steps"]
                    and session.event_count == expected["committed_optimizer_steps"]
                    and session.cursor == expected["committed_cursor"]
                    and session.pending_development is expected["pending_development"], "RESTORED_CURSOR_MISMATCH")
            require(state["run_id"] == expected["run_id"]
                    and state["checkpoint_sha256"] == expected["checkpoint_state_sha256"]
                    and state["scope_sha256"] == initial["scope_sha256"]
                    and state["training_cases_sha256"] == manifest["training_cases_sha256"]
                    and state["record_registry_sha256"] == initial["record_registry_sha256"],
                    "RESTORED_MODEL_OR_SCOPE_MISMATCH")
            # The frozen loader already checked model/config/tokenizer/scope.
            # Independently compare the optimizer values it actually installed.
            saved = checkpoint_load(checkpoint, map_location=learner.device, weights_only=True)
            require(type(saved) is dict and saved.get("steps") == learner.steps
                    and saved.get("run_id") == state["run_id"]
                    and saved.get("model_state_sha256") == state["checkpoint_sha256"],
                    "SAVED_PAYLOAD_IDENTITY_MISMATCH")
            loaded_sha = optimizer_fingerprint(learner.optimizer.state_dict(), torch)
            saved_sha = optimizer_fingerprint(saved["optimizer"], torch)
            require(loaded_sha == saved_sha, "RESTORED_OPTIMIZER_MISMATCH")
            device_count = verify_optimizer_devices(learner, torch)
            pinned(checkpoint, expected["checkpoint_file_sha256"])
            require(not forbidden and learner.steps == expected["committed_optimizer_steps"],
                    "RESTORE_CHANGED_STEP_COUNT")
            results[arm] = {**expected, "optimizer_state_sha256": loaded_sha,
                "saved_optimizer_state_sha256": saved_sha, "scope_sha256": state["scope_sha256"],
                "training_cases_sha256": state["training_cases_sha256"],
                "record_registry_sha256": state["record_registry_sha256"],
                "initial_state_sha256": initial["checkpoint_sha256"],
                "optimizer_tensors_device_checked": device_count,
                "optimizer_steps_performed": 0, "predictions_run": False}
        finally:
            for owner, name, original in originals:
                setattr(owner, name, original)
    tick()
    return results


def _parser():
    parser = argparse.ArgumentParser()
    for name in ("bundle", "bundle-manifest-sha256", "source-archive", "source-archive-sha256",
                 "prior-archive", "prior-archive-sha256", "prior-manifest", "prior-manifest-sha256",
                 "validator", "validator-sha256", "probe-sha256", "material-sha256", "output",
                 "job", "run-id", "expected-instance-id", "expected-account", "expected-region",
                 "expected-instance-type"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--max-seconds", type=int, required=True)
    return parser


def _environment_guard(args):
    require(platform.system() == "Linux" and sys.flags.isolated and sys.dont_write_bytecode,
            "ISOLATED_NO_BYTECODE_LINUX_REQUIRED")
    require(os.environ.get("CAS_META2_RUN_TEACHING_CYCLE") == "1", "EXPLICIT_ENABLE_REQUIRED")
    require(sys.version_info[:2] in ((3, 11), (3, 12)), "REGISTERED_PYTHON_REQUIRED")
    require(type(args.max_seconds) is int and 0 < args.max_seconds <= 900, "RESTORE_TIME_BOUND")
    pattern = r"cas-meta2-teaching-[0-9]{14}-[a-f0-9]{8}"
    require(re.fullmatch(pattern, args.job) and re.fullmatch(pattern, args.run_id)
            and args.job != args.run_id, "NEW_JOB_ORIGINAL_RUN_REQUIRED")
    require(args.expected_account == "807562639912" and args.expected_region == "us-west-2"
            and args.expected_instance_type == "g7.2xlarge", "REGISTERED_PROVIDER_SCOPE_REQUIRED")
    require(str(safe(args.output)) == JOB_ROOT + "/restore", "FIXED_FRESH_RESTORE_OUTPUT_REQUIRED")


def main(argv=None):
    args = _parser().parse_args(argv)
    started = time.monotonic()
    _environment_guard(args)  # Before neural imports or any output write.
    output = safe(args.output)
    require(not output.exists() and output.parent.is_dir(), "EXCLUSIVE_FRESH_OUTPUT_REQUIRED")
    output.mkdir()
    receipt = {"schema": SCHEMA, "status": "RESTORE_BLOCKED", "job": args.job, "run_id": args.run_id,
        "pid": os.getpid(), "bundle_manifest_sha256": args.bundle_manifest_sha256,
        "material_sha256": args.material_sha256, "source_archive_sha256": args.source_archive_sha256,
        "prior_archive_sha256": args.prior_archive_sha256, "prior_manifest_sha256": args.prior_manifest_sha256,
        "probe_sha256": args.probe_sha256, "validator_sha256": args.validator_sha256,
        "input_tree_unchanged": False, "optimizer_steps_performed": 0, "predictions_run": False,
        "actual_restore": "UNEXECUTED", "arms": {}, "provider_identity_proved": False,
        "boundary": "GPU restore only. Not retention after new learning, predictions, final correctness, "
                    "bitwise-identical future updates or permission to train. Parent admission is required."}
    manifest, before = None, None

    def tick():
        require(time.monotonic() - started < args.max_seconds, "RESTORE_DEADLINE_REACHED")

    try:
        pinned(__file__, args.probe_sha256)
        pinned(args.validator, args.validator_sha256)
        pinned(args.source_archive, args.source_archive_sha256, 512 * 1024**2)
        pinned(args.prior_archive, args.prior_archive_sha256, 512 * 1024**2)
        pinned(args.prior_manifest, args.prior_manifest_sha256, 4 * 1024**2)
        spec = importlib.util.spec_from_file_location("_cas_prior_state_validator", safe(args.validator))
        require(spec is not None and spec.loader is not None, "VALIDATOR_LOADER_REQUIRED")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        manifest = validator.validate_package(args.prior_archive, args.prior_manifest,
            archive_sha256=args.prior_archive_sha256, manifest_sha256=args.prior_manifest_sha256,
            expected_bindings={"logical_run_id": args.run_id, "original_campaign_root": CAMPAIGN_ROOT,
                "bundle_manifest_sha256": args.bundle_manifest_sha256,
                "source_archive_sha256": args.source_archive_sha256,
                "material_receipt_sha256": args.material_sha256})
        before = verify_tree(JOB_ROOT, manifest)
        receipt.update(source_sha256=manifest["source_sha256"], summary_sha256=manifest["summary_sha256"],
                       prior_tree_before=before)
        tick()
        bundle = safe(args.bundle)
        receipt["source_bundle"] = verify_source_bundle(bundle, args.source_archive)
        sys.path.insert(0, str(bundle))
        from cas_meta2.teaching_cycle import worker
        from cas_meta2.teaching_cycle.worker_contract import load_bundle, archive_payloads
        worker.verify_loaded_sources(bundle)
        data = load_bundle(bundle, args.bundle_manifest_sha256)
        # Verify the source ZIP as well as the extracted bundle independently.
        archive_payloads(args.source_archive, args.source_archive_sha256, args.bundle_manifest_sha256)
        require(data["manifest"]["source_sha256"] == manifest["source_sha256"]
                and data["manifest"]["profile"] == manifest["profile"], "FROZEN_BUNDLE_MISMATCH")
        summary = worker.read_pinned_json(Path(JOB_ROOT) / manifest["summary_path"], manifest["summary_sha256"])
        receipt["instance"] = worker.observe_instance(args.expected_instance_id, args.expected_account,
            args.expected_region, args.expected_instance_type)
        receipt["reference"] = worker.verify_installed_reference(bundle)
        from cas_meta2.teaching_cycle.gpu_adapter import _cuda
        torch, device = _cuda()
        require(torch.__version__ == "2.11.0+cu128" and torch.version.cuda == "12.8"
                and "RTX PRO 4500" in torch.cuda.get_device_name(device), "REGISTERED_CUDA_ENVIRONMENT_REQUIRED")
        receipt["environment"] = {"python": sys.version, "torch": torch.__version__,
            "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(device), "device": str(device)}
        tick()
        learners, matching = worker._learners(data, args.run_id)
        from cas_meta2.teaching_cycle.runner import TrainingSession
        from cas_meta2.teaching_cycle.controller import Allocation
        worker.verify_loaded_sources(bundle)
        receipt["actual_restore"] = "STARTED"
        receipt["arms"] = restore_arms(learners=learners, data=data, manifest=manifest, summary=summary,
            campaign_root=CAMPAIGN_ROOT, session_type=TrainingSession, allocation_type=Allocation,
            torch=torch, checkpoint_load=torch.load, tick=tick)
        worker.verify_loaded_sources(bundle)
        pinned(__file__, args.probe_sha256)
        pinned(args.validator, args.validator_sha256)
        load_bundle(bundle, args.bundle_manifest_sha256)
        receipt["matching"] = matching
        tick()
        receipt.update(status="RESTORED_NO_TRAINING", actual_restore="FOUR_ARMS_RESTORED")
    except Exception as error:
        code = str(error)
        # Never include arbitrary SDK/model payloads or input contents in errors.
        receipt["error"] = code if re.fullmatch(r"[A-Z][A-Z0-9_:]{1,180}", code) else type(error).__name__
        receipt["status"] = "RESTORE_BLOCKED"
    finally:
        if manifest is not None and before is not None:
            try:
                after = verify_tree(JOB_ROOT, manifest)
                receipt["prior_tree_after"] = after
                receipt["input_tree_unchanged"] = after == before
                require(after == before, "RESTORE_MUTATED_PRIOR_TREE")
            except Exception as error:
                receipt.update(status="RESTORE_BLOCKED", input_tree_unchanged=False,
                               tree_error=type(error).__name__)
        receipt["wall_seconds"] = time.monotonic() - started
        if receipt["wall_seconds"] >= args.max_seconds:
            receipt.update(status="RESTORE_BLOCKED", error="TEACHING_RESTORE:RESTORE_DEADLINE_REACHED")
        raw = canonical(receipt) + b"\n"
        with (output / "restore_receipt.json").open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    print(json.dumps({"status": receipt["status"], "path": str(output / "restore_receipt.json"),
                      "sha256": sha256(raw).hexdigest()}))
    return 0 if receipt["status"] == "RESTORED_NO_TRAINING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
