"""Fresh pure coordinator using only the retained seed-926603 diagnostic bytes."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FORBIDDEN = {"torch", "casformer", "cas_cjt", "cas_meta", "tensorflow", "jax", "cupy", "boto3", "botocore"}
MANIFEST_PIN = "19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29"
PINS_PIN = "9d66a81fbdc0e4041cd09d460c821f3cf68e244610ed49831324b5accf74084d"
LOADER_PIN = "5db831d685b2343a16b93cbc3d3c16e53978ebf0e3cf9da8fefd7d10692708b0"
JOB = "cas-meta2-20000101000000-00000001"


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def main(output):
    output = Path(output).resolve()
    assert output.is_relative_to(ROOT / "runs") and not output.exists()
    assert not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                   for p in (output, *output.parents))
    output.mkdir(parents=True, exist_ok=False)
    state = {"phase": "setup", "private_reads": [], "launches": [], "forbidden_attempts": []}

    def audit(event, arguments):
        if event == "import" and arguments[0].split(".")[0] in FORBIDDEN:
            state["forbidden_attempts"].append(arguments[0])
            raise AssertionError("COORDINATOR_NEURAL_PROVIDER_IMPORT_REFUSED")
        if event in ("socket.connect", "socket.bind", "os.system"):
            state["forbidden_attempts"].append(event)
            raise AssertionError("COORDINATOR_EXTERNAL_ACTION_REFUSED")
        if event == "subprocess.Popen":
            assert state["phase"] == "cold"
        if event == "open" and isinstance(arguments[0], (str, bytes)):
            name = os.fsdecode(arguments[0]).replace("\\", "/")
            if name.endswith("/test_private.json") and state["phase"] == "prepare":
                assert (output / "evaluation/predictions_seal.json").is_file()
                assert (output / "evaluation/predictions.jsonl").is_file()
                state["private_reads"].append({"path": name, "sealed_before_open": True})

    sys.addaudithook(audit)
    sys.path.insert(0, str(ROOT))
    from cas_meta2.contrast_v7 import native_evaluation as n
    from cas_meta2 import campaign_v3
    baseline_root = ROOT.parent / "CAS_META_1_LEARNED_SELECTION"
    sys.path.insert(0, str(baseline_root))
    from cas_meta1 import baseline
    before_sources = n.t.source_identity()
    baseline_bytes = baseline.verify_baseline()
    # Expose only exact frozen wheel package files for find_spec + byte checks.
    # This is neither an environment installation nor a package import.
    wheel_root = output / "frozen_wheel_files"
    wheel_root.mkdir()
    wheel_pins = {}
    for package, (name, pin) in baseline.WHEELS.items():
        wheel = ROOT.parent / "CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist" / name
        raw = wheel.read_bytes()
        assert sha256(raw).hexdigest() == pin
        wheel_pins[package] = pin
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.infolist():
                if member.is_dir() or not member.filename.startswith(package + "/"):
                    continue
                parts = member.filename.split("/")
                assert all(part not in ("", ".", "..") for part in parts)
                destination = wheel_root.joinpath(*parts)
                assert destination.resolve().is_relative_to(wheel_root.resolve())
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as stream:
                    stream.write(archive.read(member))
    sys.path.insert(0, str(wheel_root))
    installed_before = baseline.verify_installed_wheels()

    def discoveries():
        # This is the exact find_spec function used by frozen baseline checking.
        found = {}
        for package in baseline.WHEELS:
            spec = baseline.importlib.util.find_spec(package)
            found[package] = None if spec is None else spec.origin
        return found

    discovery_before = discoveries()
    hooks_before, paths_before = list(sys.meta_path), list(sys.path)
    source = ROOT / "records/prototype_training_integration_v7_001/checks_002/positive_merge/bundle"
    manifest_raw = (source / "manifest.json").read_bytes()
    assert sha256(manifest_raw).hexdigest() == MANIFEST_PIN
    manifest = json.loads(manifest_raw)
    assert manifest["base"]["seed"] == 926603 and manifest["base"]["exclusion_count"] == 0
    dataset = output / "dataset"
    dataset.mkdir()
    bundle_hashes = {"manifest.json": MANIFEST_PIN, **manifest["sha256"]}
    for name, pin in bundle_hashes.items():
        raw = (source / name).read_bytes()
        assert sha256(raw).hexdigest() == pin
        (dataset / name).write_bytes(raw)
    pins = output / "source_pins.json"
    pins_raw = (ROOT / "records/contrast_v7_bridge_checks_001/source_pins.json").read_bytes()
    assert sha256(pins_raw).hexdigest() == PINS_PIN
    pins.write_bytes(pins_raw)
    config = n.c.Config(**manifest["base"]["config"]).checked()
    training = output / "synthetic_training_fixture"
    training.mkdir()
    publics = json.loads((dataset / "test_public.json").read_bytes())
    actions = {arm: {"status": "REJECTED", "reason": "PURE_TEST_NO_MODEL"} for arm in n.t.ARMS}
    predictions = [{"case_index": i, "public_sha256": n.d.digest(n.c.canonical(public)),
                    "actions": deepcopy(actions)} for i, public in enumerate(publics)]
    neural_raw = b"".join(n.c.canonical(row) + b"\n" for row in predictions)
    (training / "neural_predictions.jsonl").write_bytes(neural_raw)
    synthetic_gate = {"schema": "cas-meta2-training-parent-gate/7", "completed": True,
                      "private_test_labels_opened": False, "manifest_sha256": MANIFEST_PIN,
                      "predictions_sha256": sha256(neural_raw).hexdigest(),
                      "process_receipt_sha256": "0" * 64}
    state["phase"] = "prepare"
    prepared = n.prepare(dataset, training, output / "evaluation", gate=synthetic_gate)
    assert len(prepared["splits"]["test"]) == 9 and len(state["private_reads"]) >= 1
    assert list(sys.meta_path) == hooks_before and list(sys.path) == paths_before
    state["phase"] = "cold"
    receipts = []
    mutation = {"kind": None}

    def real_local_child(command, directory, deadline, *, environment):
        """Truthful Windows process-group shim for this Linux-only API's pure test."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=False)
        now = time.monotonic()
        assert now < deadline <= now + 181
        request_path = Path(command[4])
        if mutation["kind"] == "request_before_child":
            request_path.write_bytes(request_path.read_bytes() + b" ")
        env = dict(environment)
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                   PYTHONPATH=str(HERE) + os.pathsep + str(ROOT),
                   CAS_V7_PURE_COLD_CHILD_TEST="1", CAS_V7_PURE_COLD_CHILD_JOB=JOB,
                   CAS_V7_PURE_COLD_CHILD_MARKER=str(directory / "bootstrap.json"),
                   CUDA_VISIBLE_DEVICES="")
        started, clock = datetime.now(timezone.utc).isoformat(), time.monotonic()
        with (directory / "stdout.txt").open("xb") as stdout, (directory / "stderr.txt").open("xb") as stderr:
            options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
                       else {"start_new_session": True})
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, **options)
            child.wait(timeout=max(0.01, deadline - time.monotonic()))
        result = {"schema": "cas-meta2-campaign-subprocess/3", "completed": child.returncode == 0,
            "command": command, "cwd": str(ROOT), "returncode": child.returncode,
            "timed_out": False, "pid": child.pid, "new_process_group": True, "automatic_retry": False,
            "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
            "wall_seconds": time.monotonic() - clock, "pure_test_platform_adapter": True,
            "group_mechanism": "CREATE_NEW_PROCESS_GROUP" if os.name == "nt" else "start_new_session",
            "stdout_sha256": sha256((directory / "stdout.txt").read_bytes()).hexdigest(),
            "stderr_sha256": sha256((directory / "stderr.txt").read_bytes()).hexdigest()}
        save(directory / "actual_process_receipt.json", result)
        checked = deepcopy(result)
        if mutation["kind"] == "bad_exit":
            checked["completed"] = False
        elif mutation["kind"] == "same_pid":
            checked["pid"] = os.getpid()
        save(directory / "process_receipt.json", checked)
        if mutation["kind"] == "request_after_exit":
            request_path.write_bytes(request_path.read_bytes() + b" ")
        receipts.append(str(directory / "actual_process_receipt.json"))
        state["launches"].append({"pid": child.pid, "returncode": child.returncode,
                                   "command": command, "mutation": mutation["kind"]})
        if child.returncode:
            raise RuntimeError("PURE_TEST_REAL_CHILD_FAILED:" + str(child.returncode))
        return checked

    checked_exit = {"passed": False, "read_after_exit": False}
    original_exit, original_read = n.checks.process_exit, n.checks.read

    def process_exit(*args, **kwargs):
        result = original_exit(*args, **kwargs)
        checked_exit["passed"] = True
        return result

    def checked_read(path):
        if Path(path).name == "cold_dataset_validation.json":
            assert checked_exit["passed"]
            checked_exit["read_after_exit"] = True
        return original_read(path)

    kwargs = dict(job=JOB, expected_manifest_sha256=MANIFEST_PIN, curriculum_seed=926603,
                  curriculum_config=config, excluded=frozenset(), pins=pins,
                  expected_pins_sha256=PINS_PIN, expected_loader_sha256=LOADER_PIN,
                  expected_source=before_sources)
    with (patch.object(campaign_v3, "_run_process", real_local_child),
          patch.object(n.checks, "process_exit", process_exit),
          patch.object(n.checks, "read", checked_read)):
        report = n.cold_validation(dataset, output / "evaluation", **kwargs, deadline=time.monotonic() + 175)
        assert report["completed"] and report["splits"] == manifest["splits"]
        assert checked_exit["read_after_exit"] and not any(name.split(".")[0] in FORBIDDEN for name in sys.modules)
        discovery_after = discoveries()
        assert discovery_after == discovery_before
        assert list(sys.meta_path) == hooks_before and list(sys.path) == paths_before
        # Each negative request uses a new directory and real child. No task generation.
        failures = {}
        changes = {
            "wrong_source": {"expected_source": {"wrong": "0" * 64}},
            "wrong_manifest": {"expected_manifest_sha256": "0" * 64},
            "wrong_loader": {"expected_loader_sha256": "0" * 64},
            "wrong_pins": {"expected_pins_sha256": "0" * 64},
            "wrong_seed": {"curriculum_seed": 926604},
            "wrong_config": {"curriculum_config": n.c.Config(**{**manifest["base"]["config"], "train_flat": 64})},
            "wrong_exclusions": {"excluded": frozenset({"0" * 64})},
            "request_before_child": {}, "request_after_exit": {}, "bad_exit": {}, "same_pid": {}
        }
        for name, change in changes.items():
            directory = output / name
            directory.mkdir()
            mutation["kind"] = name
            checked_exit.update(passed=False, read_after_exit=False)
            try:
                n.cold_validation(dataset, directory, **{**kwargs, **change}, deadline=time.monotonic() + 175)
            except (ValueError, RuntimeError) as error:
                failures[name] = {"type": type(error).__name__, "message": str(error),
                    "report_read_after_rejection": checked_exit["read_after_exit"],
                    "child_report_exists": (directory / "cold_dataset_validation.json").exists()}
            else:
                raise AssertionError("MUTATION_WAS_ACCEPTED:" + name)
            assert checked_exit["read_after_exit"] is False
        mutation["kind"] = None
    after_sources = n.t.source_identity()
    assert after_sources == before_sources
    assert baseline.verify_baseline() == baseline_bytes and discoveries() == discovery_before
    installed_after = baseline.verify_installed_wheels()
    assert installed_after == installed_before
    assert list(sys.meta_path) == hooks_before and list(sys.path) == paths_before
    assert all(sha256((dataset / name).read_bytes()).hexdigest() == pin for name, pin in bundle_hashes.items())
    assert not state["forbidden_attempts"]
    exit_markers = []
    for name in ("evaluation", *changes):
        marker = output / name / "cold_validation_process/bootstrap_exit.json"
        value = json.loads(marker.read_bytes())
        assert value["forbidden_attempts"] == [] and value["neural_or_provider_modules"] == []
        exit_markers.append({"case": name, **value})
    result = {"completed": True, "pure_local_test": True, "actual_aws": False, "neural_execution": False,
        "coordinator_pid": os.getpid(), "fixture_seed": 926603, "manifest_sha256": MANIFEST_PIN,
        "source_pins_sha256": PINS_PIN, "loader_sha256": LOADER_PIN, "source_before": before_sources,
        "source_after": after_sources, "protected_baseline": baseline_bytes, "source_unchanged": True,
        "frozen_wheel_file_fixture": {"path": str(wheel_root), "wheel_sha256": wheel_pins,
            "installed_environment_changed": False, "package_modules_imported": False,
            "verified_before": installed_before, "verified_after": installed_after},
        "dataset_files_unchanged": True, "splits": report["splits"], "cold_report": report,
        "private_opening_order": state["private_reads"], "real_process_receipts": receipts,
        "find_spec_before": discovery_before, "find_spec_after": discovery_after,
        "coordinator_hooks_and_path_unchanged": True, "negative_cases": failures,
        "child_exit_markers": exit_markers, "synthetic_training_gate": True,
        "synthetic_neural_predictions": True, "state": state,
        "boundary": "Saved diagnostic bytes only. Actual cold validator and real exited children; local request and process-group test shims. No model loading, GPU, provider, new task generation, trained prediction or fresh-install claim."}
    save(output / "probe_receipt.json", result)
    print(json.dumps({"completed": True, "output": str(output), "negative_cases": len(failures),
                      "child_processes": len(receipts), "splits": report["splits"]}), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
