"""Run the exact committed numeric dispatch up to its real Windows CUDA refusal."""
from hashlib import sha256
import ast
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

HOME = Path(__file__).resolve().parents[1]
COMP = HOME / "research/CAS_META_2_COMPOSITION"
OUTER_HOME = next(p for p in reversed(HOME.parents) if p.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
    with path.open("xb") as stream: stream.write(raw)
    return sha256(raw).hexdigest()


def child(root, output):
    import builtins
    import platform
    assert platform.system() == "Windows" and sys.flags.isolated and sys.dont_write_bytecode
    denied = {"torch", "numpy", "cas_cjt", "casformer", "boto3", "botocore", "requests", "httpx", "openai", "anthropic"}
    attempted = []
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in denied:
            attempted.append(name); raise AssertionError("LOCAL_NUMERIC_OR_PROVIDER_IMPORT:" + name)
        return original(name, *args, **kwargs)
    builtins.__import__ = guarded
    def audit(event, args):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.startfile"}:
            attempted.append(event); raise AssertionError("LOCAL_EXECUTION_OR_NETWORK")
    sys.addaudithook(audit)
    manifest = json.loads((root / "graph6_curriculum_source_manifest.json").read_bytes())
    source = (root / manifest["worker_script"]).read_bytes()
    tree = ast.parse(source)
    inners = [n.value.value for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
              and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "INNER_RUNNER" and isinstance(n.value, ast.Constant)]
    assert len(inners) == 1
    sys.argv = [str(root / manifest["worker_script"]) + "::INNER_RUNNER", str(root)]
    failure = None
    try:
        exec(compile(inners[0], sys.argv[0], "exec"), {"__name__": "__main__"})
    except ValueError as error:
        failure = str(error)
    assert failure == "TEACHING_GPU:LINUX_WORKER_REQUIRED", repr(failure)
    assert not attempted and not denied.intersection(sys.modules)
    result_path = root / "results/result.json"
    result_raw = result_path.read_bytes()
    result = json.loads(result_raw)
    assert result["failure"] == {"schema": "cncm.typed-course-failure/0.1", "type": "ValueError", "detail": failure}
    assert (root / "results/result.json.sha256").read_text().strip() == sha256(result_raw).hexdigest()
    modules = []
    for name, module in sorted(sys.modules.copy().items()):
        if name == "cncm" or name.startswith("cncm.") or name == "cas_meta2" or name.startswith("cas_meta2."):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(root)
            rel = path.relative_to(root).as_posix()
            assert sha256(path.read_bytes()).hexdigest() == manifest["files_sha256"][rel]
            modules.append({"module": name, "path": rel, "sha256": manifest["files_sha256"][rel]})
    save(output / "child_receipt.json", {"status": "PASSED", "actual_guard_failure": failure,
        "actual_inner_sha256": sha256(inners[0].encode()).hexdigest(), "loaded_modules": modules,
        "forbidden_attempts": attempted, "numeric_calls": 0, "provider_calls": 0})


def run(package_path, output):
    sys.path[:0] = [str(HOME), str(COMP)]
    from aws import typed_course_launch as launch
    package_raw = package_path.read_bytes(); package = json.loads(package_raw)
    raw = Path(package["archive"]).read_bytes()
    assert sha256(raw).hexdigest() == package["archive_sha256"] and len(raw) == package["archive_bytes"]
    assert len(raw) <= launch.shared.MAX_ARCHIVE_BYTES
    assert output.is_relative_to(HOME / "records/typed_numeric_001") and not output.exists()
    output.mkdir(parents=True)
    root = OUTER_HOME / "_tmp" / ("tcr_" + sha256(str(output).encode()).hexdigest()[:12])
    assert not root.exists() and root.resolve().is_relative_to(OUTER_HOME.resolve())
    root.mkdir(parents=True)
    save(output / "extraction.json", {"path": str(root), "archive_sha256": package["archive_sha256"]})
    with ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist(); launch.shared.checked_names(names)
        assert len(names) <= launch.shared.MAX_MEMBER_COUNT
        infos = archive.infolist()
        assert all(0 <= i.file_size <= launch.shared.MAX_MEMBER_BYTES for i in infos)
        assert sum(i.file_size for i in infos) <= launch.shared.MAX_EXPANDED_BYTES
        manifest_raw = archive.read(launch.shared.MANIFEST_NAME)
        assert sha256(manifest_raw).hexdigest() == package["manifest_sha256"]
        manifest = json.loads(manifest_raw)
        assert set(names) == set(manifest["members"]) | {launch.shared.MANIFEST_NAME}
        for info in infos:
            data = archive.read(info)
            if info.filename != launch.shared.MANIFEST_NAME:
                assert sha256(data).hexdigest() == manifest["files_sha256"][info.filename]
                assert len(data) == manifest["files_bytes"][info.filename]
            target = root / info.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream: stream.write(data)
    job = "cas-meta2-typedcourse-20260917000000-" + package["source_sha"][:8]
    config = launch.worker_config(job, source_sha=package["source_sha"])
    save(root / "config.json", config)
    child_result = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child", str(root), str(output)],
                                  cwd=root, capture_output=True, timeout=120)
    (output / "stdout.txt").write_bytes(child_result.stdout); (output / "stderr.txt").write_bytes(child_result.stderr)
    assert child_result.returncode == 0, child_result.stderr.decode(errors="replace")[-3000:]
    checked = json.loads((output / "child_receipt.json").read_bytes()); assert checked["status"] == "PASSED"
    for name in manifest["members"]:
        assert sha256((root / name).read_bytes()).hexdigest() == manifest["files_sha256"][name]
    receipt = {"status": "PASSED", "source_sha": package["source_sha"], "archive_sha256": package["archive_sha256"],
        "manifest_sha256": package["manifest_sha256"], "package_receipt_sha256": sha256(package_raw).hexdigest(),
        "child_receipt_sha256": sha256((output / "child_receipt.json").read_bytes()).hexdigest(),
        "helper_sha256": sha256(Path(__file__).read_bytes()).hexdigest(), "members_unchanged": len(manifest["members"]),
        "boundary": "Actual extracted dispatch and expected pre-CUDA Windows refusal. No local numeric/provider execution."}
    save(output / "receipt.json", receipt); print(json.dumps(receipt))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        child(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve())
    elif len(sys.argv) == 3:
        run(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
    else:
        raise SystemExit("usage: rehearse_typed_course_package.py PACKAGE_RECEIPT NEW_OUTPUT")
