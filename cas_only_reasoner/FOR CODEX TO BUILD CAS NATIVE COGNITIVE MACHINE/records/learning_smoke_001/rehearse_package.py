"""Data-only rehearsal of a caller-pinned committed ingestion smoke package.

No tensor, model, provider, or network execution is allowed. A real Windows
worker refusal is the expected result; it does not establish CUDA readiness.
"""
from __future__ import annotations

import argparse
import ast
import builtins
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import socket
import stat
import subprocess
import sys
import time
from uuid import uuid4
from zipfile import ZipFile

SCHEMA = "cncm-ingestion-package-rehearsal/1"
MANIFEST = "graph6_curriculum_source_manifest.json"
PILOT = "research/CAS_META_2_COMPOSITION"
WORKER = "ingestion_smoke_worker.py"
MAX_ARCHIVE = 24 * 1024**2
MAX_EXPANDED = 96 * 1024**2
MAX_MEMBER = 4 * 1024**2
FORBIDDEN = frozenset({"torch", "numpy", "tensorflow", "jax", "jaxlib", "casformer", "cas_cjt",
                      "boto3", "botocore", "openai", "anthropic", "requests", "httpx"})
PREFIXES = ("cncm", "cas_meta2", "aws", "research")


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def hashed(raw):
    return sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def save(path, value):
    raw = canonical(value)
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(Path(path).read_bytes() == raw, "REHEARSAL_WRITE_READBACK")
    return {"path": str(Path(path).resolve()), "bytes": len(raw), "sha256": hashed(raw)}


def safe_name(name):
    require(type(name) is str and 0 < len(name) <= 1024, "REHEARSAL_MEMBER_NAME")
    path = PurePosixPath(name)
    require(bool(path.parts) and not path.is_absolute() and path.as_posix() == name and not name.endswith("/")
            and ".." not in path.parts and "\\" not in name and ":" not in name,
            "REHEARSAL_UNSAFE_MEMBER:" + repr(name))
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
    for part in path.parts:
        require(part and not part.endswith((".", " ")) and all(ord(c) >= 32 for c in part)
                and not any(c in '<>"|?*' for c in part)
                and part.split(".", 1)[0].upper() not in reserved, "REHEARSAL_WINDOWS_PATH_ALIAS")
    return path


def pinned_json(path, expected):
    require(type(expected) is str and re.fullmatch(r"[0-9a-f]{64}", expected), "REHEARSAL_PIN_REQUIRED")
    raw = Path(path).read_bytes()
    require(hashed(raw) == expected, "REHEARSAL_PIN_MISMATCH:" + str(path))
    return raw, json.loads(raw)


def current_members(root, rows):
    checked = {}
    for name, identity in rows.items():
        safe_name(name)
        path = root / name
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root),
                "REHEARSAL_SOURCE_PATH:" + name)
        raw = path.read_bytes()
        require(len(raw) == identity["bytes"] and hashed(raw) == identity["sha256"],
                "REHEARSAL_SOURCE_CHANGED:" + name)
        checked[name] = identity
    return checked


def verified_archive(receipt_path, receipt_sha):
    receipt_raw, receipt = pinned_json(receipt_path, receipt_sha)
    require(type(receipt) is dict and receipt.get("status") == "SOURCE_ONLY_NO_LAUNCH",
            "REHEARSAL_PACKAGE_STATUS")
    require(type(receipt.get("source_sha")) is str and re.fullmatch(r"[0-9a-f]{40}", receipt["source_sha"]),
            "REHEARSAL_COMMIT_REQUIRED")
    archive_path = Path(receipt["archive"])
    require(archive_path.is_absolute() and archive_path.is_file() and not archive_path.is_symlink(),
            "REHEARSAL_ARCHIVE_PATH")
    require(type(receipt["archive_bytes"]) is int and 0 < receipt["archive_bytes"] <= MAX_ARCHIVE
            and archive_path.stat().st_size == receipt["archive_bytes"], "REHEARSAL_ARCHIVE_BOUND")
    raw = archive_path.read_bytes()
    require(hashed(raw) == receipt["archive_sha256"], "REHEARSAL_ARCHIVE_SHA")
    members = {}
    with ZipFile(BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [row.filename for row in infos]
        require(0 < len(names) <= 2000 and len(names) == len(set(names)) == receipt["member_count"],
                "REHEARSAL_MEMBER_COUNT")
        require(len({name.casefold() for name in names}) == len(names), "REHEARSAL_CASE_ALIAS")
        require(sum(row.file_size for row in infos) <= MAX_EXPANDED + MAX_MEMBER, "REHEARSAL_EXPANDED_BOUND")
        for info in infos:
            safe_name(info.filename)
            mode = (info.external_attr >> 16) & 0xFFFF
            require(not info.is_dir() and not (info.flag_bits & 1)
                    and stat.S_IFMT(mode) in (0, stat.S_IFREG)
                    and 0 <= info.file_size <= MAX_MEMBER, "REHEARSAL_MEMBER_KIND_OR_SIZE")
            members[info.filename] = archive.read(info)
    require(MANIFEST in members and hashed(members[MANIFEST]) == receipt["manifest_sha256"],
            "REHEARSAL_MANIFEST_SHA")
    manifest = json.loads(members[MANIFEST])
    require(canonical(manifest) == canonical(receipt["manifest"]), "REHEARSAL_MANIFEST_RECEIPT")
    require(manifest["source_sha"] == receipt["source_sha"] and manifest["worker_script"] == WORKER
            and manifest["root_manifest"] == MANIFEST, "REHEARSAL_PACKAGE_IDENTITY")
    require(type(manifest["members"]) is list and manifest["members"] == sorted(set(manifest["members"]))
            and set(members) == set(manifest["members"]) | {MANIFEST}
            and set(manifest["files_sha256"]) == set(manifest["members"])
            and set(manifest["files_bytes"]) == set(manifest["members"]), "REHEARSAL_MANIFEST_COVERAGE")
    require(manifest["member_count"] == len(members), "REHEARSAL_MANIFEST_COUNT")
    for name in manifest["members"]:
        require(type(manifest["files_bytes"][name]) is int
                and len(members[name]) == manifest["files_bytes"][name]
                and hashed(members[name]) == manifest["files_sha256"][name], "REHEARSAL_MEMBER_SHA:" + name)
    require(sum(len(value) for name, value in members.items() if name != MANIFEST) == manifest["expanded_bytes"],
            "REHEARSAL_MANIFEST_EXPANDED_BYTES")
    return receipt_raw, receipt, members


def install_guards():
    attempts = {"imports": [], "network": [], "processes": []}
    require(not FORBIDDEN.intersection(sys.modules), "REHEARSAL_FORBIDDEN_PRELOADED")
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in FORBIDDEN:
            attempts["imports"].append(name)
            raise RuntimeError("REHEARSAL_FORBIDDEN_IMPORT:" + name)
        return original(name, *args, **kwargs)
    class DenyImport:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in FORBIDDEN:
                attempts["imports"].append(fullname)
                raise RuntimeError("REHEARSAL_FORBIDDEN_IMPORT:" + fullname)
    def network(*args, **kwargs):
        attempts["network"].append("socket")
        raise RuntimeError("REHEARSAL_NETWORK_FORBIDDEN")
    def process(*args, **kwargs):
        attempts["processes"].append("process")
        raise RuntimeError("REHEARSAL_CHILD_PROCESS_FORBIDDEN")
    builtins.__import__ = guarded
    sys.meta_path.insert(0, DenyImport())
    for name in ("socket", "SocketType", "create_connection", "getaddrinfo", "socketpair", "fromfd"):
        if hasattr(socket, name):
            setattr(socket, name, network)
    for name in ("Popen", "run", "call", "check_call", "check_output"):
        setattr(subprocess, name, process)
    os.system = process
    def audit(event, arguments):
        if event.startswith("socket."):
            network()
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.spawn"}:
            process()
    sys.addaudithook(audit)
    return attempts


def imported_sources(root, members):
    result = []
    for name, module in sorted(sys.modules.items()):
        if name.split(".")[0] not in PREFIXES:
            continue
        source = getattr(module, "__file__", None)
        if source is None:
            paths = list(getattr(module, "__path__", ()))
            require(paths and all(Path(p).resolve().is_relative_to(root) for p in paths),
                    "REHEARSAL_FOREIGN_NAMESPACE:" + name)
            result.append({"module": name, "namespace_paths": [str(Path(p).resolve()) for p in paths]})
            continue
        path = Path(source).resolve()
        require(path.is_relative_to(root), "REHEARSAL_FOREIGN_IMPORT:" + name)
        relative = path.relative_to(root).as_posix()
        require(relative in members and path.suffix == ".py", "REHEARSAL_UNPINNED_IMPORT:" + name)
        raw = path.read_bytes()
        require(len(raw) == members[relative]["bytes"] and hashed(raw) == members[relative]["sha256"],
                "REHEARSAL_IMPORTED_BYTES:" + name)
        result.append({"module": name, "path": relative, **members[relative]})
    require(all(any(row["module"] == name for row in result) for name in ("cncm", "cas_meta2", "aws")),
            "REHEARSAL_EXPECTED_IMPORTS_MISSING")
    return result


def checked_inner_timeout(tree):
    """Check the learner subprocess, independently of transport join timeouts."""
    limits = [node for node in tree.body if isinstance(node, ast.Assign)
              and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
              and node.targets[0].id == "MAX_WALL_SECONDS"]
    stores = [node for node in ast.walk(tree) if isinstance(node, ast.Name)
              and isinstance(node.ctx, ast.Store) and node.id == "MAX_WALL_SECONDS"]
    require(len(limits) == len(stores) == 1 and isinstance(limits[0].value, ast.Constant)
            and type(limits[0].value.value) is int and limits[0].value.value == 1200,
            "REHEARSAL_TIMEOUT_CONSTANT")
    expected_argv = ast.dump(ast.parse("[python, '-B', str(runner), str(root)]", mode="eval").body)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "run"
             and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess"
             and len(node.args) == 1 and ast.dump(node.args[0]) == expected_argv]
    require(len(calls) == 1, "REHEARSAL_INNER_DISPATCH")
    dispatch = calls[0]
    bindings = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                and node.value is dispatch and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "inner"]
    timeout = [keyword.value for keyword in dispatch.keywords if keyword.arg == "timeout"]
    require(len(bindings) == len(timeout) == 1 and isinstance(timeout[0], ast.Name)
            and timeout[0].id == "MAX_WALL_SECONDS"
            and not any(keyword.arg is None for keyword in dispatch.keywords),
            "REHEARSAL_TIMEOUT_DISPATCH")
    return {"subprocess_line": dispatch.lineno, "timeout_name": "MAX_WALL_SECONDS", "timeout_seconds": 1200}


def child(args):
    evidence = Path(args.output).resolve()
    root = Path(args.extracted).resolve()
    report = {"schema": SCHEMA, "status": "FAILED", "interpreter": sys.executable,
              "python_version": sys.version, "isolated": sys.flags.isolated,
              "optimization": sys.flags.optimize, "dont_write_bytecode": sys.dont_write_bytecode}
    attempts = None
    try:
        require(platform.system() == "Windows", "REHEARSAL_EXPECTS_REAL_WINDOWS_GUARD")
        require(sys.flags.isolated == 1 and sys.flags.optimize == 0 and sys.dont_write_bytecode,
                "REHEARSAL_INTERPRETER_FLAGS")
        _, custody = pinned_json(args.custody, args.custody_sha256)
        require(custody["extracted"] == str(root) and custody["helper_sha256"] == hashed(Path(__file__).read_bytes()),
                "REHEARSAL_CHILD_CUSTODY")
        members = custody["members"]
        current_members(root, members)
        _, receipt = pinned_json(evidence / "package_receipt.json", custody["receipt_sha256"])
        attempts = install_guards()
        sys.path.insert(0, str(root))
        sys.path.insert(0, str(root / PILOT))
        from aws import ingestion_smoke_launch as launch
        from cncm import rpa_learning_worker as worker
        from aws import run_evidence
        require(launch.PROJECT.resolve() == root and launch.ROOT.resolve() == root / PILOT,
                "REHEARSAL_LAUNCH_ROOT")
        config = {**launch.worker_config("cas-meta2-ingestionsmoke-20260916000000-00000000",
                                        source_sha=receipt["source_sha"]),
                  "bucket": "local-rehearsal-no-provider"}
        require(worker.validate_config(config, root) == config, "REHEARSAL_CONFIG_INVALID")
        require(canonical(config["inputs"]) == canonical(receipt["manifest"]["inputs"]),
                "REHEARSAL_CONFIG_MANIFEST_INPUTS")
        save(root / "config.json", config)
        save(evidence / "config.json", config)
        source = (root / WORKER).read_bytes()
        expected_source = run_evidence.unified_worker_source(launch.render_worker()).encode("utf-8")
        require(source == expected_source, "REHEARSAL_GENERATED_WORKER_MISMATCH")
        tree = ast.parse(source, str(root / WORKER))
        inner = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
                 and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                 and node.targets[0].id == "INNER_RUNNER" and isinstance(node.value, ast.Constant)]
        require(len(inner) == 1 and type(inner[0]) is str, "REHEARSAL_INNER_RUNNER_MISSING")
        timeout_dispatch = checked_inner_timeout(tree)
        sys.argv = [str(root / WORKER) + "::INNER_RUNNER", str(root)]
        failure = None
        try:
            exec(compile(inner[0], sys.argv[0], "exec"), {"__name__": "__main__"})
        except ValueError as error:
            failure = str(error)
        require(failure == "TEACHING_GPU:LINUX_WORKER_REQUIRED", "REHEARSAL_WRONG_GUARD:" + repr(failure))
        require(not any(attempts.values()) and not FORBIDDEN.intersection(sys.modules), "REHEARSAL_FORBIDDEN_ACTIVITY")
        results = root / "results"
        envelope_raw = (results / "result.json").read_bytes()
        envelope = json.loads(envelope_raw)
        require(envelope["schema"] == worker.RESULT_SCHEMA and envelope["status"] == "INGESTION_SMOKE_FAILED"
                and envelope["failure"] == {"type": "ValueError", "detail": failure}, "REHEARSAL_FAILURE_ENVELOPE")
        require((results / "result.json.sha256").read_text().strip() == hashed(envelope_raw), "REHEARSAL_ENVELOPE_SIDECAR")
        inventory = json.loads((results / "artifacts/manifest.json").read_bytes())
        require(inventory["artifacts"] == envelope["artifacts"], "REHEARSAL_FAILURE_MANIFEST")
        require({row["name"] for row in inventory["artifacts"]} == {"worker_report.json", "measurements.json"},
                "REHEARSAL_PRE_NUMERIC_ARTIFACTS")
        for row in inventory["artifacts"]:
            safe_name(row["name"])
            raw = (results / "artifacts" / row["name"]).read_bytes()
            require(len(raw) == row["bytes"] and hashed(raw) == row["sha256"], "REHEARSAL_FAILURE_ARTIFACT_SHA")
        worker_report = json.loads((results / "artifacts/worker_report.json").read_bytes())
        require(worker_report["failure"] == envelope["failure"] and "runtime" not in worker_report
                and worker_report["learning_improvement_established"] is False, "REHEARSAL_PRE_CUDA_FAILURE")
        imports = imported_sources(root, members)
        current_members(root, members)
        report.update(status="PASSED", source_sha=receipt["source_sha"], package_receipt_sha256=custody["receipt_sha256"],
                      actual_inner_runner_sha256=hashed(inner[0].encode()), actual_guard_failure=failure,
                      timeout_dispatch=timeout_dispatch,
                      imported_modules=imports, imported_source_files=len({r["path"] for r in imports if "path" in r}),
                      source_members_unchanged=True, failure_envelope_sha256=hashed(envelope_raw),
                      guard_attempts=attempts, numeric_tensor_calls=0, learner_forward_calls=0, provider_calls=0,
                      boundary="Exact source/import/configuration/dispatch check and expected Windows refusal only. No CUDA execution, numeric equality, training, provider readiness, or learning claim.")
    except BaseException as error:
        report.update(error={"type": type(error).__name__, "detail": str(error)}, guard_attempts=attempts)
        raise
    finally:
        save(evidence / "child_receipt.json", report)
    print(json.dumps({"status": report["status"], "guard": report["actual_guard_failure"],
                      "imported_source_files": report["imported_source_files"]}))
    return 0


def parent(args):
    started = time.monotonic()
    output = Path(args.output).resolve()
    helper = Path(__file__).resolve()
    inner = helper.parents[2]
    require(output.is_relative_to(inner / "records") and not output.exists() and output.parent.is_dir(),
            "REHEARSAL_NEW_RECORD_DIRECTORY_REQUIRED")
    output.mkdir()
    report = {"schema": SCHEMA, "status": "FAILED", "helper_sha256": hashed(helper.read_bytes()),
              "package_receipt_path": str(Path(args.package_receipt).resolve()),
              "package_receipt_sha256": args.package_receipt_sha256, "interpreter": sys.executable,
              "python_version": sys.version, "optimization": sys.flags.optimize}
    destination = None
    try:
        require(sys.flags.optimize == 0, "REHEARSAL_OPTIMIZATION_FORBIDDEN")
        receipt_raw, receipt, payload = verified_archive(args.package_receipt, args.package_receipt_sha256)
        (output / "package_receipt.json").write_bytes(receipt_raw)
        homes = [p for p in reversed(helper.parents) if p.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"]
        require(homes, "REHEARSAL_PHYSICAL_HOME_NOT_FOUND")
        scratch_root = homes[0] / "_tmp"
        scratch_root.mkdir(exist_ok=True)
        require(not scratch_root.is_symlink(), "REHEARSAL_SCRATCH_SYMLINK")
        destination = scratch_root / ("ingestion_rehearsal_" + uuid4().hex[:12])
        destination.mkdir()
        require(destination.resolve().parent == scratch_root.resolve(), "REHEARSAL_SCRATCH_SCOPE")
        for name, raw in payload.items():
            relative = safe_name(name)
            target = destination.joinpath(*relative.parts)
            require(target.resolve().is_relative_to(destination.resolve()), "REHEARSAL_EXTRACT_SCOPE")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(raw)
        members = {name: {"bytes": len(raw), "sha256": hashed(raw)} for name, raw in sorted(payload.items())}
        current_members(destination, members)
        short_helper = destination / "_rehearse.py"
        require(short_helper.name.casefold() not in {name.casefold() for name in members}, "REHEARSAL_HELPER_MEMBER_COLLISION")
        with short_helper.open("xb") as stream:
            stream.write(helper.read_bytes())
        custody = save(output / "custody.json", {"extracted": str(destination.resolve()), "members": members,
            "helper_sha256": report["helper_sha256"], "receipt_sha256": args.package_receipt_sha256})
        command = [sys.executable, "-I", "-B", str(short_helper), "--child", "--extracted", str(destination),
                   "--custody", custody["path"], "--custody-sha256", custody["sha256"], "--output", str(output)]
        report.update(source_sha=receipt["source_sha"], archive_sha256=receipt["archive_sha256"],
                      manifest_sha256=receipt["manifest_sha256"], member_count=len(members),
                      extracted=str(destination), custody=custody, command=command)
        try:
            completed = subprocess.run(command, cwd=Path(sys.executable).parent, capture_output=True, timeout=120,
                env={**os.environ, "PYTHONPATH": "", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"})
            stdout, stderr, code = completed.stdout, completed.stderr, completed.returncode
        except subprocess.TimeoutExpired as error:
            stdout, stderr, code = error.stdout or b"", error.stderr or b"", None
            report["timeout_seconds"] = 120
        (output / "stdout.txt").write_bytes(stdout)
        (output / "stderr.txt").write_bytes(stderr)
        report.update(subprocess_returncode=code, stdout_sha256=hashed(stdout), stderr_sha256=hashed(stderr))
        current_members(destination, members)
        require(hashed(helper.read_bytes()) == report["helper_sha256"]
                and short_helper.read_bytes() == helper.read_bytes(), "REHEARSAL_HELPER_CHANGED")
        require(pinned_json(args.package_receipt, args.package_receipt_sha256)[0] == receipt_raw,
                "REHEARSAL_RECEIPT_CHANGED")
        require(hashed(Path(receipt["archive"]).read_bytes()) == receipt["archive_sha256"], "REHEARSAL_ARCHIVE_CHANGED")
        report["source_members_unchanged"] = True
        if (destination / "results").is_dir():
            for path in sorted((destination / "results").rglob("*")):
                if path.is_file():
                    require(not path.is_symlink(), "REHEARSAL_RESULT_SYMLINK")
                    target = output / "child_results" / path.relative_to(destination / "results")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("xb") as stream:
                        stream.write(path.read_bytes())
        require(code == 0, "REHEARSAL_CHILD_FAILED:" + str(code))
        child_report = json.loads((output / "child_receipt.json").read_bytes())
        require(child_report["status"] == "PASSED" and child_report["source_members_unchanged"] is True,
                "REHEARSAL_CHILD_RECEIPT")
        report.update(status="PASSED", child_receipt_sha256=hashed((output / "child_receipt.json").read_bytes()),
                      imported_source_files=child_report["imported_source_files"],
                      boundary=child_report["boundary"])
    except BaseException as error:
        report["error"] = {"type": type(error).__name__, "detail": str(error)}
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        report["artifacts"] = [{"path": p.relative_to(output).as_posix(), "bytes": p.stat().st_size,
                                "sha256": hashed(p.read_bytes())}
                               for p in sorted(output.rglob("*")) if p.is_file()]
        save(output / "receipt.json", report)
    print(json.dumps({key: report.get(key) for key in ("status", "member_count", "subprocess_returncode", "elapsed_seconds", "error")}))
    return 0 if report["status"] == "PASSED" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-receipt")
    parser.add_argument("--package-receipt-sha256")
    parser.add_argument("--output", required=True)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--extracted")
    parser.add_argument("--custody")
    parser.add_argument("--custody-sha256")
    args = parser.parse_args(argv)
    if args.child:
        require(all((args.extracted, args.custody, args.custody_sha256)), "REHEARSAL_CHILD_ARGUMENTS")
        return child(args)
    require(args.package_receipt and args.package_receipt_sha256, "REHEARSAL_PACKAGE_PIN_ARGUMENTS")
    return parent(args)


if __name__ == "__main__":
    raise SystemExit(main())
