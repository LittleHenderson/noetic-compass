"""Receipt the public pause/resume workflow without changing old evidence.

This is a local builder reproduction, not a substitute for GLM's re-audit.
"""

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
OLD_SOURCE = "fda27bcff9c38af5941a15433db6ae7d59bf0d9a"
OLD_EVIDENCE = "35a81a774dd1b2be1106b6f7403d410e28c81e4c"
OLD = ROOT / "records" / "validation"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()


def head(path):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return dict(connection.execute("SELECT * FROM active_head").fetchone())
    finally:
        connection.close()


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    git_root = Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    prefix = ROOT.relative_to(git_root).as_posix() + "/"
    old_hashes = load(OLD / "payload_sha256.json")
    for relative, expected in old_hashes.items():
        path = OLD / relative
        if file_hash(path) != expected:
            raise AssertionError("Original evidence changed: " + relative)
        committed = subprocess.check_output(
            ["git", "show", OLD_EVIDENCE + ":" + path.relative_to(git_root).as_posix()], cwd=ROOT)
        if committed != path.read_bytes():
            raise AssertionError("Original evidence not preserved in Git: " + relative)
    tracked = subprocess.check_output(
        ["git", "ls-files", "."], cwd=ROOT, text=True).splitlines()
    debris = [p for p in tracked if any(
        part.startswith(("_te", "_final", "_verify_", "api-review-")) for part in Path(p).parts)]
    if debris:
        raise AssertionError("Scratch files tracked: " + repr(debris))
    dump(output / "preservation.json", {
        "old_source_commit": OLD_SOURCE, "old_evidence_commit": OLD_EVIDENCE,
        "old_payload_files_checked": len(old_hashes), "committed_bytes_equal": True,
        "git_common_dir": subprocess.check_output(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=ROOT, text=True).strip(),
        "tracked_scratch_files": debris, "no_scratch_deleted": True,
        "original_glm_raw_failure_bundle_available": False,
    })
    commands = []

    def command(name, arguments, rejection=None):
        argv = [sys.executable, "-m", "cas_meta.demo", *map(str, arguments)]
        completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False)
        (output / (name + ".stdout.txt")).write_text(completed.stdout, encoding="utf-8")
        (output / (name + ".stderr.txt")).write_text(completed.stderr, encoding="utf-8")
        commands.append({"name": name, "argv": argv, "cwd": str(ROOT),
                         "returncode": completed.returncode, "expected_rejection": rejection})
        dump(output / "commands.json", commands)
        print(name + ": exit " + str(completed.returncode), flush=True)
        if rejection is None:
            if completed.returncode:
                raise AssertionError(name + " failed: " + completed.stderr)
        elif not completed.returncode or rejection not in completed.stderr:
            raise AssertionError(name + " did not produce " + rejection)
        return completed

    # Reproduce the reported failure CLASS on a copy of the published builder
    # pair. This is not the unavailable original GLM checkpoint or traceback.
    stale = output / "published_pair_copy"
    stale.mkdir()
    for name in ("checkpoint.json", "compiled.db"):
        shutil.copyfile(OLD / "demo" / name, stale / name)
    old_checkpoint = load(stale / "checkpoint.json")
    actual_head = head(stale / "compiled.db")
    dump(output / "native_head_diagnosis.json", {
        "expected_head_from_checkpoint": old_checkpoint["head"],
        "actual_sqlite_active_head": actual_head,
        "checkpoint_sha256": file_hash(stale / "checkpoint.json"),
        "binding_run_id": old_checkpoint["binding"]["run_id"],
        "checkpoint_fields": sorted(old_checkpoint),
        "binding_fields": sorted(old_checkpoint["binding"]),
        "cause": "Published step-4 checkpoint paired with already-completed step-5 database.",
        "native_head_is_git_head": False,
        "original_glm_failure_identical_cause_proven": False,
    })
    command("published_pair_rejection", ["--resume", stale, "--expected-digest",
            file_hash(stale / "checkpoint.json")], "NATIVE_HEAD_MISMATCH")
    if head(stale / "compiled.db") != actual_head:
        raise AssertionError("Rejection changed native state")

    prepared = output / "prepared"
    command("prepare", ["--prepare", prepared])
    receipt = load(prepared / "creation_receipt.json")
    checkpoint = load(prepared / "checkpoint.json")
    snapshot_hashes = {p.name: file_hash(p) for p in (prepared / "paused").iterdir()}

    def copied(name):
        path = output / name
        shutil.copytree(prepared / "paused", path)
        return path

    wrong = copied("wrong_digest_bundle")
    before = head(wrong / "compiled.db")
    command("wrong_digest", ["--resume", wrong, "--expected-digest", "0" * 64],
            "CHECKPOINT_RECEIPT_MISMATCH")
    if head(wrong / "compiled.db") != before:
        raise AssertionError("Wrong digest changed native state")
    for missing in ("compiled.db", "checkpoint.json"):
        target = copied("missing_" + missing.replace(".", "_"))
        (target / missing).unlink()  # Only this probe's newly created copy.
        before_files = {p.name: file_hash(p) for p in target.iterdir()}
        command("missing_" + missing.replace(".", "_"),
                ["--resume", target, "--expected-digest", receipt["checkpoint_digest"]],
                "MISSING_CHECKPOINT_DEPENDENCY:" + missing)
        if {p.name: file_hash(p) for p in target.iterdir()} != before_files:
            raise AssertionError("Missing-dependency rejection changed files")

    continuation = copied("continuation")
    command("resume", ["--resume", continuation, "--expected-digest", receipt["checkpoint_digest"]])
    worker = load(continuation / "worker_result.json")
    events = load(continuation / "meta_trace.json")
    assert worker["restored_frames"] == checkpoint["frames"]
    assert worker["native_head_before"] == checkpoint["head"]
    assert events[:len(checkpoint["events"])] == checkpoint["events"]
    assert [e["cjt_id"] for e in events if e["kind"] == "NATIVE"] == ["A", "B", "C", "R", "C"]
    assert (worker["spent_before"], worker["spent"]) == (288, 360)
    assert (worker["remaining_before"], worker["remaining_after"]) == (224, 152)
    assert worker["model_digest_before"] == worker["model_digest_after"] == receipt["model_digest"]
    assert worker["repair_closed"] and worker["done"]
    before = head(continuation / "compiled.db")
    command("repeat_consumed_bundle", ["--resume", continuation, "--expected-digest",
            receipt["checkpoint_digest"]], "NATIVE_HEAD_MISMATCH")
    assert head(continuation / "compiled.db") == before

    second = output / "second_prepared"
    command("second_prepare", ["--prepare", second])
    other = load(second / "checkpoint.json")
    assert checkpoint["binding"]["run_id"] != other["binding"]["run_id"]
    assert checkpoint["head"] == other["head"]
    assert receipt["checkpoint_digest"] != load(second / "creation_receipt.json")["checkpoint_digest"]
    assert all(checkpoint["binding"][k] == other["binding"][k]
               for k in ("program_digest", "model_digest"))
    dump(output / "checkpoint_identity_comparison.json", {
        "first_run_id": checkpoint["binding"]["run_id"],
        "second_run_id": other["binding"]["run_id"],
        "first_digest": receipt["checkpoint_digest"],
        "second_digest": load(second / "creation_receipt.json")["checkpoint_digest"],
        "same_native_head": True, "same_program_and_model": True,
        "purpose": "Per-run complete artifact identity, not cross-run semantic equivalence.",
    })
    assert snapshot_hashes == {p.name: file_hash(p) for p in (prepared / "paused").iterdir()}
    assert all(file_hash(OLD / name) == expected for name, expected in old_hashes.items())
    source_hashes = {p: file_hash(ROOT / p) for p in tracked
                     if p.startswith(("cas_meta/", "tests/", "tools/", "programs/", "schemas/"))
                     or p in ("README.md", "requirements-meta.txt", ".gitignore")}
    dump(output / "source_sha256.json", source_hashes)
    dump(output / "receipt.json", {
        "status": "CAS_META_0_RESTART_WORKFLOW_LOCAL_CHECKS_PASSED",
        "tested_source_commit": source_commit,
        "old_source_commit": OLD_SOURCE, "old_evidence_commit": OLD_EVIDENCE,
        "fixed_weights": True, "guards_retained": True,
        "prepare_and_resume_are_separate_cli_processes": True,
        "paused_bundle_preserved": True,
        "continuation": worker,
        "original_glm_command_and_raw_failure_bundle": "NOT_AVAILABLE",
        "external_auditor_updated_verdict": "PENDING",
        "full_fractal_acceptance": "NOT_CLAIMED",
    })
    dump(output / "payload_sha256.json", {p.relative_to(output).as_posix(): file_hash(p)
                                          for p in sorted(output.rglob("*")) if p.is_file()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output.resolve())
