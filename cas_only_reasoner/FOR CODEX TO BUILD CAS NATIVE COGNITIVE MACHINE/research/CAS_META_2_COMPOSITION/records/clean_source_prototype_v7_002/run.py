"""Prepared clean-source v7 proof. Run only after the owner supplies a frozen SHA."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ACTIVE_ROOT = HERE.parents[1]
OUTER_NAME = "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
OUTER = [path for path in ACTIVE_ROOT.parents if path.name == OUTER_NAME][-1]
PACKAGE_RELATIVE = Path("cas_only_reasoner") / OUTER_NAME / "research/CAS_META_2_COMPOSITION"
BASE_MANIFEST_PIN = "36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1"
MERGED_MANIFEST_PIN = "19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29"
TASKS_PIN = "ed6bb0978d34b549917e1ea1b846091f103577936f846bc01db152b19ddbac46"
PINS_PIN = "9d66a81fbdc0e4041cd09d460c821f3cf68e244610ed49831324b5accf74084d"
LOADER_PIN = "5db831d685b2343a16b93cbc3d3c16e53978ebf0e3cf9da8fefd7d10692708b0"
INTEGRATION = "records/prototype_training_integration_v7_001"
MERGED = INTEGRATION + "/checks_002/positive_merge/bundle"
BASE = "records/contrast_v6_bundle_probe_001/dataset"
PUBLIC = "records/contrast_v7_bridge_checks_001/roundtrip/trainer_input"
PUBLIC_FILES = ("manifest.json", "train.json", "validation.json", "test_public.json",
                "tokenizer.json", "training_imports.json", "base_manifest.json", "base_train.json")
REQUIRED_TEST_MODULES = ("test_contrast_v7_cold_child", "test_contrast_v7_orchestration",
                         "test_contrast_v7_smoke_private")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(raw):
    return sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def no_links(path):
    for item in (path, *path.parents):
        require(not item.is_symlink() and not getattr(item, "is_junction", lambda: False)(),
                "AUDIT_PATH_LINK_REFUSED:" + str(item))


def read(path):
    no_links(path)
    require(path.is_file(), "AUDIT_REGULAR_FILE_REQUIRED:" + str(path))
    return path.read_bytes()


def write(path, raw):
    no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def save(path, value):
    write(path, json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n")


class Audit:
    def __init__(self, source, output):
        self.source, self.output = source, output
        self.repo = OUTER / "_worktrees" / ("prototype-v7-audit-" + source[:8])
        self.root = self.repo / PACKAGE_RELATIVE
        self.processes, self.commands = [], []
        self.validator = self.profile = self.builder = None

    def git(self, *args, repo=None, data=None):
        command = ["git", "-C", str(repo or self.repo), *args]
        result = subprocess.run(command, input=data, capture_output=True, timeout=120)
        self.commands.append({"command": command, "returncode": result.returncode,
            "stdin_sha256": digest(data) if data is not None else None,
            "stdout_sha256": digest(result.stdout), "stderr_sha256": digest(result.stderr)})
        require(result.returncode == 0, "AUDIT_GIT_FAILED:" + result.stderr.decode(errors="replace"))
        return result.stdout

    def blobs(self, names):
        names = sorted(set(names))
        for name in names:
            require(name and "\\" not in name and ":" not in name and "\n" not in name
                and not name.startswith("/") and all(x not in ("", ".", "..") for x in name.split("/")),
                "AUDIT_UNSAFE_GIT_PATH")
        requests = "".join(self.source + ":" + name + "\n" for name in names).encode()
        stream = io.BytesIO(self.git("cat-file", "--batch", data=requests))
        values = {}
        for name in names:
            header = stream.readline().decode().strip().split()
            require(len(header) == 3 and header[1] == "blob", "REQUIRED_INPUT_NOT_COMMITTED:" + name)
            raw = stream.read(int(header[2]))
            require(len(raw) == int(header[2]) and stream.read(1) == b"\n", "GIT_BLOB_TRUNCATED")
            values[name] = raw
        require(stream.read() == b"", "GIT_BLOB_TRAILING_BYTES")
        self.commands[-1]["requested_blob_paths"] = names
        return values

    def checked_module(self, relative, name):
        path = self.root / relative
        key = path.relative_to(self.repo).as_posix()
        require(self.blobs([key])[key] == read(path), "PREIMPORT_SOURCE_NOT_COMMITTED:" + relative)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def stage(self, name, command, cwd, timeout, env=None):
        started = datetime.now(timezone.utc).isoformat()
        clock = time.monotonic()
        print(json.dumps({"stage": name, "started_utc": started}), flush=True)
        try:
            process = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired as error:
            process = subprocess.CompletedProcess(command, 124, error.stdout or b"", error.stderr or b"")
            timed_out = True
        for suffix, raw in (("stdout", process.stdout), ("stderr", process.stderr)):
            write(self.output / (name + "." + suffix + ".txt"), raw)
        result = {"name": name, "command": command, "cwd": str(cwd), "returncode": process.returncode,
            "timeout_seconds": timeout, "timed_out": timed_out, "started_utc": started,
            "finished_utc": datetime.now(timezone.utc).isoformat(), "wall_seconds": time.monotonic() - clock,
            "stdout_sha256": digest(process.stdout), "stderr_sha256": digest(process.stderr),
            "termination_boundary": "subprocess.run kills and waits for its direct child on timeout; independently detached grandchildren are not covered."}
        save(self.output / (name + ".process.json"), result)
        self.processes.append(result)
        print(json.dumps(result), flush=True)
        return result

    def create(self):
        active_repo = Path(self.git("rev-parse", "--show-toplevel", repo=ACTIVE_ROOT).decode().strip())
        require(self.git("rev-parse", self.source + "^{commit}", repo=active_repo).decode().strip() == self.source,
                "EXACT_SOURCE_COMMIT_REQUIRED")
        # The audit runner itself must be in the frozen source, not an untracked input.
        self_inputs = {}
        for path in (Path(__file__).resolve(), HERE / "README.md"):
            key = path.relative_to(active_repo).as_posix()
            frozen = self.git("cat-file", "blob", self.source + ":" + key, repo=active_repo)
            require(read(path) == frozen, "AUDIT_TOOL_NOT_IN_FROZEN_SOURCE:" + key)
            self_inputs[key] = digest(frozen)
        no_links(self.repo)
        require(self.repo.parent.resolve() == (OUTER / "_worktrees").resolve()
                and not self.repo.exists(), "NEW_CONTAINED_WORKTREE_REQUIRED")
        save(self.output / "creation_preflight.json", {"source_sha": self.source,
            "worktree": str(self.repo), "absent_before": True, "self_inputs_sha256": self_inputs})
        result = self.stage("worktree_creation", ["git", "-C", str(active_repo), "-c", "core.autocrlf=false",
            "worktree", "add", "--detach", str(self.repo), self.source], active_repo, 300)
        require(result["returncode"] == 0, "CLEAN_WORKTREE_CREATION_FAILED")
        require(self.git("rev-parse", "HEAD").decode().strip() == self.source, "CLEAN_HEAD_MISMATCH")
        status = self.git("status", "--porcelain", "--untracked-files=all").decode()
        write(self.output / "initial_git_status.txt", status.encode())
        require(not status.strip(), "PRISTINE_INITIAL_CHECKOUT_REQUIRED")
        return status

    def snapshot(self):
        require(self.git("rev-parse", "HEAD").decode().strip() == self.source, "SOURCE_HEAD_CHANGED")
        tracked = self.git("status", "--porcelain", "--untracked-files=no").decode()
        required, groups = {}, {}

        def add(group, path, pin=None):
            no_links(path)
            require(path.resolve().is_relative_to(self.repo.resolve()), "AUDIT_INPUT_OUTSIDE_SOURCE")
            key = path.relative_to(self.repo).as_posix()
            if pin is not None and key in required and required[key] is not None:
                require(required[key] == pin, "AUDIT_EXPECTED_PIN_CONFLICT:" + key)
            required[key] = pin if pin is not None else required.get(key)
            groups.setdefault(group, set()).add(key)

        p = self.profile
        admission = read(self.root.parents[1] / p.ADMISSION_PATH)
        pins_raw = read(self.root.parents[1] / p.SOURCE_PINS_PATH)
        allowlist = p.launch_allowlist(admission, pins_raw)
        frozen_pins = {**p.frozen_inputs(admission), **p.launch_pins(pins_raw)}
        for name in sorted(allowlist):
            p.safe_name(name)
            add("closed_v7_launch_inputs", self.root.parents[1] / name, frozen_pins.get(name))
        sources = self.validator.source_snapshot()
        for name, pin in sources.items():
            add("canonical_source", self.root / name, pin)
        baseline_path = self.root.parent / "CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"
        baseline_raw = read(baseline_path)
        require(digest(baseline_raw) == self.validator.BASELINE_MANIFEST_SHA256, "PROTECTED_MANIFEST_CHANGED")
        baseline = json.loads(baseline_raw)
        require(baseline["baseline_sha"] == self.validator.BASELINE_SHA and len(baseline["files"]) == 316,
                "PROTECTED_316_REQUIRED")
        add("protected_manifest", baseline_path, self.validator.BASELINE_MANIFEST_SHA256)
        for row in baseline["files"]:
            add("protected_316", self.root.parent / row["path"], row["sha256"])

        merged_raw = read(self.root / MERGED / "manifest.json")
        base_raw = read(self.root / BASE / "manifest.json")
        require(digest(merged_raw) == MERGED_MANIFEST_PIN and digest(base_raw) == BASE_MANIFEST_PIN,
                "KNOWN_FIXTURE_MANIFEST_CHANGED")
        merged, base = json.loads(merged_raw), json.loads(base_raw)
        require(merged["base"]["seed"] == 926603 and base["seed"] == 926603, "KNOWN_DIAGNOSTIC_SEED_REQUIRED")
        require(digest(pins_raw) == PINS_PIN and json.loads(pins_raw) == merged["source"], "KNOWN_SOURCE_PINS_CHANGED")
        for directory, manifest, pin in ((MERGED, merged, MERGED_MANIFEST_PIN), (BASE, base, BASE_MANIFEST_PIN)):
            for name, expected in {"manifest.json": pin, **manifest["sha256"]}.items():
                require("/" not in name and "\\" not in name and ":" not in name, "KNOWN_FIXTURE_BASENAME_REQUIRED")
                add("known_portable_inputs", self.root / directory / name, expected)
        required_in_launch = ["records/contrast_v7_cold_child_review_001/probe.py",
                              "records/contrast_v7_cold_child_review_001/sitecustomize.py"]
        required_in_launch += [MERGED + "/" + name for name in ("manifest.json", *merged["sha256"])]
        required_in_launch += [PUBLIC + "/" + name for name in PUBLIC_FILES]
        for name in required_in_launch:
            require(p.PILOT + "/" + name in allowlist, "INCLUDED_TEST_DEPENDENCY_ABSENT_FROM_CLOSED_PACKAGE:" + name)
            add("included_test_dependencies", self.root / name)
        for name in ("records/contrast_v7_bridge_checks_001/run.py",
                     "records/contrast_v7_bridge_checks_001/source_pins.json",
                     "records/contrast_v7_exclusions_001/build.py", "records/contrast_v7_exclusions_001/test_build.py",
                     "records/contrast_v6_exclusions_001/inventory.json", INTEGRATION + "/adapter.py",
                     INTEGRATION + "/public_data.py", INTEGRATION + "/test_public_data.py",
                     INTEGRATION + "/test_adapter.py", INTEGRATION + "/run_checks.py"):
            add("known_portable_inputs", self.root / name)
        add("literal_256", self.root / "records/contrast_curriculum_v6_probe_001/tasks.json", TASKS_PIN)
        add("known_portable_inputs", self.root / INTEGRATION / "public_data.py", LOADER_PIN)
        for name, pin in merged["source"]["frozen_files_sha256"].items():
            add("known_portable_inputs", self.root / name, pin)
        for name in ("run.py", "README.md"):
            add("audit_tool", self.root / "records/clean_source_prototype_v7_002" / name)

        blobs = self.blobs(required)
        modes = {}
        for entry in self.git("ls-tree", "-r", "-z", self.source).split(b"\0"):
            if entry:
                meta, name = entry.split(b"\t", 1)
                modes[name.decode()] = meta.split()[0].decode()
        identities, mismatches = {}, []
        for name in sorted(required):
            raw = read(self.repo / name)
            actual, committed = digest(raw), digest(blobs[name])
            expected = required[name] or committed
            identities[name] = {"expected_sha256": expected, "git_sha256": committed,
                "checkout_sha256": actual, "bytes": len(raw), "git_mode": modes.get(name)}
            if expected != committed or raw != blobs[name] or modes.get(name) not in ("100644", "100755"):
                mismatches.append(name)
        members = {name: blobs[(self.root.parents[1] / name).relative_to(self.repo).as_posix()] for name in allowlist}
        launch, launch_error = None, None
        try:
            launch = self.builder.make_manifest(members, self.source)
        except Exception as error:
            launch_error = {"type": type(error).__name__, "message": str(error)}
        tasks = json.loads(read(self.root / "records/contrast_curriculum_v6_probe_001/tasks.json"))
        require(len(tasks) == 256, "ORIGINAL_256_COUNT_CHANGED")
        return {"source_sha": self.source, "tracked_status": tracked, "all_checked_files": len(identities),
            "files": identities, "groups": {key: sorted(value) for key, value in sorted(groups.items())},
            "source_files": len(sources), "protected_files": len(groups["protected_316"]),
            "closed_v7_source_files": len(allowlist), "closed_allowlist_sha256": digest(canonical(sorted(allowlist))),
            "closed_launch_manifest": launch, "closed_launch_validation_error": launch_error,
            "git_blob_or_checkout_mismatches": mismatches,
            "protected_manifest_sha256": digest(baseline_raw), "original_training_tasks": len(tasks),
            "known_fixture_seed": 926603, "known_merged_manifest_sha256": digest(merged_raw),
            "known_base_manifest_sha256": digest(base_raw), "known_splits": merged["splits"],
            "private_fixture_labels_are_already_exposed_diagnostic_data": True,
            "raw_failure_packet_or_current_task_inputs_opened": False}


def test_counts(output):
    receipt_path = output / "receipt.json"
    receipt = json.loads(read(receipt_path)) if receipt_path.exists() else {}
    text = read(output / "stdout.txt").decode(errors="replace") if (output / "stdout.txt").exists() else ""
    summaries = [line for line in text.splitlines() if re.search(r"\b\d+ (?:passed|failed|errors?)\b", line)
                 and (" in " in line or line.startswith("="))]
    summary = summaries[-1] if summaries else None
    parsed = {}
    if summary:
        for key, expression in {"failed_test_functions": r"(\d+) failed", "skipped": r"(\d+) skipped",
            "deselected": r"(\d+) deselected", "warnings": r"(\d+) warnings?", "errors": r"(\d+) errors?"}.items():
            found = re.findall(expression, summary)
            parsed[key] = int(found[-1]) if found else 0
    selected = {name: [] for name in REQUIRED_TEST_MODULES}
    if (output / "tests.xml").exists():
        for case in ET.parse(output / "tests.xml").getroot().iter("testcase"):
            for name in selected:
                if name in case.get("classname", ""):
                    selected[name].append({"classname": case.get("classname"), "name": case.get("name"),
                        "failed": case.find("failure") is not None, "error": case.find("error") is not None,
                        "skipped": case.find("skipped") is not None})
    return {"canonical_receipt": receipt, "raw_summary": summary, "summary_counts": parsed,
        "required_test_module_junit_entries": selected,
        "required_test_modules_executed": all(rows and all(not any(row[k] for k in ("failed", "error", "skipped"))
                                                            for row in rows) for rows in selected.values()),
        "count_boundary": "Canonical function and subtest counts are reported separately. JUnit totals include subtests; these overlapping counts are never added."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{40}", args.source), "EXACT_40_HEX_SOURCE_SHA_REQUIRED")
    output = args.output.absolute()
    no_links(output)
    require(output.parent.resolve() == HERE.resolve() and not output.exists(), "NEW_IMMEDIATE_RECORD_CHILD_REQUIRED")
    output.mkdir(exist_ok=False)
    audit = Audit(args.source, output)
    started = time.monotonic()
    result = {"schema": "cas-meta2-clean-prototype-source-audit/7", "completed": False,
        "status": "CLEAN_PROTOTYPE_SOURCE_CHECKS_FAILED", "source_sha": args.source,
        "runner_command": [sys.executable, *sys.argv],
        "worktree": str(audit.repo), "package": str(audit.root), "output": str(output), "errors": [],
        "existing_environment": {"python": sys.version, "executable": sys.executable},
        "fresh_environment_or_install": False, "core_autocrlf_on_checkout": False,
        "neural_execution": False, "provider_calls": False, "paid_execution": False,
        "registered_task_generation": False, "training_or_heldout_result_claim": False,
        "boundary": "Clean committed source and guarded pure checks in an existing environment. Old diagnostic fixtures and synthetic/mocked execution are permitted; no fresh registered tasks, models, GPU, providers, packet reopening, installation or learning claim."}
    original_hooks = tuple(sys.meta_path)
    before = after = None
    full_output = audit.root / "records/clean_source_prototype_v7_002/full_validation"
    try:
        result["initial_git_status"] = audit.create()
        audit.validator = audit.checked_module("tools/validate_local_v3.py", "clean_v7_canonical_validator")
        require(not any(audit.validator.forbidden_import(name) for name in sys.modules),
                "PRELOADED_NEURAL_OR_PROVIDER_MODULE_REFUSED")
        sys.meta_path.insert(0, audit.validator.NoNeuralOrProviderImports())
        audit.profile = audit.checked_module("tools/experiment_profiles_prototype_v7.py", "clean_v7_profile")
        audit.builder = audit.checked_module("tools/build_launch_bundle_prototype_v7.py", "clean_v7_source_builder")
        before = audit.snapshot()
        save(output / "source_before.json", before)
        require(not before["tracked_status"].strip() and not before["git_blob_or_checkout_mismatches"]
                and before["closed_launch_validation_error"] is None, "SOURCE_BEFORE_MISMATCH")
        print(json.dumps({"stage": "source_before", "files": before["all_checked_files"],
            "closed_source_files": before["closed_v7_source_files"], "protected": before["protected_files"]}), flush=True)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
            PYTEST_ADDOPTS="", PYTEST_PLUGINS="", CUDA_VISIBLE_DEVICES="",
            CAS_META1_RUN_GPU_TESTS="0", CAS_META2_RUN_GPU_TESTS="0")
        env.pop("PYTHONPATH", None)
        result["environment_overrides"] = {key: env[key] for key in (
            "PYTHONDONTWRITEBYTECODE", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_ADDOPTS", "PYTEST_PLUGINS",
            "CUDA_VISIBLE_DEVICES", "CAS_META1_RUN_GPU_TESTS", "CAS_META2_RUN_GPU_TESTS")}
        result["inherited_pythonpath_removed"] = True
        require(not full_output.exists(), "NEW_CANONICAL_OUTPUT_REQUIRED")
        audit.stage("full_validator", [sys.executable, "-B", str(audit.root / "tools/validate_local_v3.py"),
            "--output", str(full_output)], audit.root, 660, env)
    except BaseException as error:
        result["errors"].append({"stage": "audit", "type": type(error).__name__, "message": str(error),
                                 "traceback": traceback.format_exc()})
    finally:
        if before is not None:
            try:
                after = audit.snapshot()
                save(output / "source_after.json", after)
            except BaseException as error:
                result["errors"].append({"stage": "source_after", "type": type(error).__name__,
                                         "message": str(error), "traceback": traceback.format_exc()})
        try:
            if full_output.exists():
                copied = {}
                for path in sorted(full_output.iterdir()):
                    if path.is_file():
                        raw = read(path)
                        write(output / "full_validator_artifacts" / path.name, raw)
                        copied[path.name] = digest(raw)
                result["copied_artifact_sha256"] = copied
                result["full_validator"] = test_counts(full_output)
            if audit.repo.exists():
                result["final_git_status"] = audit.git("status", "--porcelain", "--untracked-files=all").decode()
                result["final_tracked_git_status"] = audit.git("status", "--porcelain", "--untracked-files=no").decode()
        except BaseException as error:
            result["errors"].append({"stage": "final_records", "type": type(error).__name__, "message": str(error)})
        sys.meta_path[:] = original_hooks
        versions = {}
        for distribution in ("pytest", "jsonschema", "torch", "boto3", "botocore"):
            try:
                versions[distribution] = importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                versions[distribution] = None
        result["existing_environment"]["distribution_metadata_only"] = versions
        result["source_unchanged"] = before is not None and before == after
        result["processes"] = audit.processes
        result["all_checked_files"] = before["all_checked_files"] if before else None
        result["closed_v7_source_files"] = before["closed_v7_source_files"] if before else None
        result["protected_files"] = before["protected_files"] if before else None
        result["git_blob_or_checkout_mismatches"] = {"before": before.get("git_blob_or_checkout_mismatches") if before else None,
            "after": after.get("git_blob_or_checkout_mismatches") if after else None}
        full = result.get("full_validator", {})
        result["completed"] = bool(result["source_unchanged"] and not result["errors"]
            and not result.get("final_tracked_git_status", "MISSING")
            and all(row["returncode"] == 0 and not row["timed_out"] for row in audit.processes)
            and full.get("canonical_receipt", {}).get("completed") and full.get("required_test_modules_executed"))
        if result["completed"]:
            result["status"] = "CLEAN_PROTOTYPE_SOURCE_CHECKS_PASSED"
        result["wall_seconds"] = time.monotonic() - started
        save(output / "git_commands.json", audit.commands)
        save(output / "receipt.json", result)
    print(json.dumps({key: result[key] for key in ("completed", "status", "source_sha", "all_checked_files",
        "closed_v7_source_files", "source_unchanged", "errors", "wall_seconds")}, indent=2), flush=True)
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
