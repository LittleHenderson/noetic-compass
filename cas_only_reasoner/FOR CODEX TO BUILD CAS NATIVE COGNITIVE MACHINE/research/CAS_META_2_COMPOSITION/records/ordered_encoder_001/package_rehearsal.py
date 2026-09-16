"""Data-only exact-package rehearsal; never starts a provider or imports torch."""
from __future__ import annotations

import ast
import builtins
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import platform
import socket
import subprocess
import sys
import time
from zipfile import ZipFile

SOURCE_SHA = "e47349be13ee5449d31ae8d5cc3962ae2571ba15"
ARCHIVE_SHA = "57b17ab62301a4f026cde31fe54bec7e3988ee26f08a54e8072b1b6f6e167a0c"
MANIFEST_SHA = "0f23fb81dd93b143c7edbe1d425fd23bc70c2f02769cd3f81a65ea7aa55c185a"
MANIFEST = "graph6_curriculum_source_manifest.json"
PILOT = "research/CAS_META_2_COMPOSITION"


def hashed(raw):
    return sha256(raw).hexdigest()


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    Path(path).write_bytes(raw)
    return {"path": str(path), "bytes": len(raw), "sha256": hashed(raw)}


def child(extracted):
    extracted = Path(extracted).resolve()
    pilot = extracted / PILOT
    assert platform.system() == "Windows", "This non-neural rehearsal expects the real Windows guard"
    denied = []
    forbidden = {"torch", "tensorflow", "jax", "boto3", "botocore", "casformer", "cas_cjt", "numpy"}
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in forbidden:
            denied.append(name)
            raise AssertionError("NON_NEURAL_REHEARSAL_IMPORT_FORBIDDEN:" + name)
        return original_import(name, *args, **kwargs)

    def deny_network(*args, **kwargs):
        raise AssertionError("NON_NEURAL_REHEARSAL_NETWORK_FORBIDDEN")

    builtins.__import__ = guarded_import
    socket.socket = deny_network
    socket.create_connection = deny_network
    socket.getaddrinfo = deny_network
    sys.path.insert(0, str(pilot))
    from aws import ordered_encoder_launch as launch
    from cas_meta2.graph_teaching import ordered_encoder, ordered_encoder_probe as probe

    # This is the actual launcher configuration plus the transport's bucket
    # injection. The inert rehearsal job grants no provider authority.
    config = {**launch.worker_config("cas-meta2-orderedencoder-20260916000000-00000000", source_sha=SOURCE_SHA),
              "bucket": "local-rehearsal-no-provider"}
    assert probe.validate_config(config, pilot) == config
    manifest = json.loads((extracted / MANIFEST).read_bytes())
    assert manifest["source_sha"] == config["source_sha"] == SOURCE_SHA
    assert manifest["inputs"] == config["inputs"]
    save(extracted / "config.json", config)
    audit = probe.algebraic_audit(pilot)
    assert audit["changed_answer_collisions"] == 96
    assert audit["reorder_controls"] == 32 and len(audit["pairs"]) == 128
    assert audit["neural_calls"] == 0

    worker = extracted / "ordered_encoder_worker.py"
    worker_tree = ast.parse(worker.read_bytes(), str(worker))
    matches = [node.value.value for node in worker_tree.body
               if isinstance(node, ast.Assign) and len(node.targets) == 1
               and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "INNER_RUNNER"
               and isinstance(node.value, ast.Constant)]
    assert len(matches) == 1 and isinstance(matches[0], str)
    sys.argv = [str(worker) + "::INNER_RUNNER", str(extracted)]
    failure = None
    try:
        exec(compile(matches[0], sys.argv[0], "exec"), {"__name__": "__main__"})
    except ValueError as error:
        failure = str(error)
    assert failure == "TEACHING_GPU:LINUX_WORKER_REQUIRED", failure
    assert not denied, denied
    assert not forbidden.intersection(sys.modules)
    envelope_path = extracted / "results/result.json"
    raw = envelope_path.read_bytes()
    envelope = json.loads(raw)
    assert envelope["schema"] == probe.RESULT_SCHEMA
    assert envelope["status"] == "ORDERED_ENCODER_DIAGNOSTIC_FAILED"
    assert envelope["failure"]["message"] == failure
    assert envelope["optimizer_updates"] == envelope["summary"]["learner_forward_calls"] == 0
    assert (extracted / "results/result.json.sha256").read_text().strip() == hashed(raw)
    artifacts = json.loads((extracted / "results/artifacts/manifest.json").read_bytes())
    for entry in artifacts["artifacts"]:
        payload = (extracted / "results/artifacts" / entry["name"]).read_bytes()
        assert len(payload) == entry["bytes"] and hashed(payload) == entry["sha256"]
    imported = {}
    for name, module in tuple(sys.modules.items()):
        if name.split(".")[0] in {"aws", "cas_meta2"} and getattr(module, "__file__", None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(pilot), (name, str(path))
            imported[name] = path.relative_to(extracted).as_posix()
    report = {"status": "EXTRACTED_PACKAGE_WINDOWS_GUARD_REHEARSAL_PASSED",
              "source_sha": SOURCE_SHA, "config": config,
              "algebraic_audit": audit, "ordered_profile": ordered_encoder.PROFILE_ID,
              "actual_inner_runner_sha256": hashed(matches[0].encode()),
              "actual_guard_failure": failure, "imported_package_modules": imported,
              "forbidden_import_attempts": denied, "provider_calls": 0,
              "numeric_tensor_calls": 0, "learner_forward_calls": 0,
              "failure_envelope_sha256": hashed(raw),
              "boundary": "Actual committed source, configuration and dispatch only. Windows refusal is expected; this proves no Linux/CUDA execution, numeric equality, training result or provider readiness."}
    save(extracted / "rehearsal_child.json", report)
    print(json.dumps({"status": report["status"], "algebraic_pairs": 128,
                      "guard": failure, "imported_modules": len(imported)}))
    return 0


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        return child(sys.argv[2])
    directory = Path(__file__).resolve().parent
    package = directory / "package_e47349be"
    receipt_raw = (package / "receipt.json").read_bytes()
    receipt = json.loads(receipt_raw)
    archive = package / "source.zip"
    archive_raw = archive.read_bytes()
    assert len(archive_raw) == receipt["archive_bytes"] == 641091
    assert hashed(archive_raw) == receipt["archive_sha256"] == ARCHIVE_SHA
    assert receipt["source_sha"] == SOURCE_SHA and receipt["manifest_sha256"] == MANIFEST_SHA
    scratch = (directory / "_scratch").resolve()
    destination = scratch / "package_e47349be"
    assert destination.is_relative_to(scratch)
    assert not (directory / "package_rehearsal_e47349be.json").exists(), "Preserve prior completed rehearsal"
    # An interrupted pre-child extraction may be reused only byte-for-byte.
    destination.mkdir(parents=True, exist_ok=True)
    checked = {}
    with ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert len(names) == len(set(names)) == receipt["member_count"] == 61
        manifest_raw = bundle.read(MANIFEST)
        assert hashed(manifest_raw) == MANIFEST_SHA
        manifest = json.loads(manifest_raw)
        assert manifest == receipt["manifest"] and manifest["source_sha"] == SOURCE_SHA
        assert set(names) == set(manifest["members"]) | {MANIFEST}
        for name in names:
            path = PurePosixPath(name)
            assert not path.is_absolute() and ".." not in path.parts and "\\" not in name and ":" not in name
            assert path.as_posix() == name
            raw = bundle.read(name)
            if name != MANIFEST:
                assert hashed(raw) == manifest["files_sha256"][name]
                assert len(raw) == manifest["files_bytes"][name]
            output = destination.joinpath(*path.parts)
            assert output.resolve().is_relative_to(destination)
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                assert output.read_bytes() == raw, "Existing extraction bytes differ: " + name
            else:
                output.write_bytes(raw)
            checked[name] = {"sha256": hashed(raw), "bytes": len(raw)}
    assert sum(row["bytes"] for name, row in checked.items() if name != MANIFEST) == manifest["expanded_bytes"]
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child", str(destination)]
    started = time.monotonic()
    # Windows CreateProcess rejects this deeply nested extraction as its cwd.
    # Isolated mode removes cwd imports; every package/output path is absolute.
    completed = subprocess.run(command, cwd=Path(sys.executable).parent, capture_output=True, timeout=90,
                               env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""})
    stdout = directory / "package_rehearsal_e47349be.stdout.txt"
    stderr = directory / "package_rehearsal_e47349be.stderr.txt"
    stdout.write_bytes(completed.stdout)
    stderr.write_bytes(completed.stderr)
    assert all(hashed((destination / name).read_bytes()) == row["sha256"] for name, row in checked.items())
    proof = {"schema": "cas-ordered-encoder-package-rehearsal/1",
             "status": "PASSED" if completed.returncode == 0 else "FAILED",
             "source_sha": SOURCE_SHA, "archive_sha256": ARCHIVE_SHA,
             "manifest_sha256": MANIFEST_SHA, "receipt_sha256": hashed(receipt_raw),
             "script_sha256": hashed(Path(__file__).read_bytes()),
             "member_count": len(checked), "members": checked,
             "source_members_unchanged": True, "subprocess_command": command,
             "subprocess_cwd": str(Path(sys.executable).parent),
             "subprocess_returncode": completed.returncode,
             "elapsed_seconds": time.monotonic() - started,
             "stdout_sha256": hashed(completed.stdout), "stderr_sha256": hashed(completed.stderr),
             "boundary": "Pure package/import/dispatch rehearsal. No numeric tensors, neural execution, provider calls, resource reservation or learning claim."}
    child_path = destination / "rehearsal_child.json"
    if child_path.exists():
        proof["child_report"] = json.loads(child_path.read_bytes())
    save(directory / "package_rehearsal_e47349be.json", proof)
    print(json.dumps({key: proof[key] for key in ("status", "member_count", "subprocess_returncode", "elapsed_seconds")}))
    if completed.returncode:
        print(completed.stderr.decode(errors="replace"))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
