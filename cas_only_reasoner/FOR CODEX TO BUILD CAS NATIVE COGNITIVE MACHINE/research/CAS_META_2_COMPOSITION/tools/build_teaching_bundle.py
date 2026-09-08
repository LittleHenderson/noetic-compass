"""Build committed training bytes, then admit an extracted copy in a fresh pure process."""
import argparse
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {"torch", "numpy", "sqlite3", "_sqlite3", "boto3", "botocore", "casformer", "cas_cjt", "cas_meta"}


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("PURE_BUNDLE_FORBIDDEN_IMPORT:" + fullname)


def guard():
    assert not FORBIDDEN.intersection(sys.modules)
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        if event.startswith("socket.") or event == "sqlite3.connect":
            raise RuntimeError("PURE_BUNDLE_FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha")
    parser.add_argument("--output")
    parser.add_argument("--child")
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args(argv)
    assert sys.flags.isolated and sys.dont_write_bytecode
    guard()
    if args.child:
        root = Path(args.child).absolute()
        sys.path.insert(0, str(root))
        from cas_meta2.teaching_cycle.worker_contract import load_bundle
        from cas_meta2.teaching_cycle.worker import verify_loaded_sources
        result = load_bundle(root, args.manifest_sha256)
        # Import all worker orchestration modules without touching CUDA.
        from cas_meta2.teaching_cycle import runner, gpu_adapter, guided_application
        verify_loaded_sources(root)
        assert not FORBIDDEN.intersection(sys.modules)
        print(json.dumps({"status": "CLEAN_EXTRACTED_PURE_ADMISSION_PASSED",
            "source_commit": result["manifest"]["source_commit"],
            "source_sha256": result["manifest"]["source_sha256"],
            "manifest_sha256": result["manifest_sha256"],
            "train": len(result["training_cases"]), "development": len(result["development_cases"]),
            "loaded_sources": {name: module.__file__ for name, module in sys.modules.items()
                               if name == "cas_meta2" or name.startswith("cas_meta2.")},
            "neural_execution": False, "provider_calls": 0}))
        return 0
    assert args.source_sha and args.output
    sys.path.insert(0, str(ROOT))
    from cas_meta2.teaching_cycle.package import build_bundle
    from cas_meta2.teaching_cycle.worker_contract import extract_bundle
    output = Path(args.output).absolute()
    receipt = build_bundle(args.source_sha, output)
    extracted = output / "extracted"
    extract_bundle(output / "training.zip", extracted, receipt["archive_sha256"], receipt["manifest_sha256"])
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child", str(extracted),
               "--manifest-sha256", receipt["manifest_sha256"]]
    process = subprocess.run(command, cwd=extracted, capture_output=True, timeout=120,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for name, raw in (("clean_stdout.txt", process.stdout), ("clean_stderr.txt", process.stderr)):
        with (output / name).open("xb") as stream:
            stream.write(raw)
    result = {"command": command, "exit_code": process.returncode,
        "archive_sha256": receipt["archive_sha256"], "manifest_sha256": receipt["manifest_sha256"],
        "source_commit": args.source_sha, "python": sys.version,
        "stdout_sha256": sha256(process.stdout).hexdigest(), "stderr_sha256": sha256(process.stderr).hexdigest(),
        "boundary": "Committed-byte package and clean extracted imports only; no CUDA or provider execution."}
    with (output / "clean_check.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(result))
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
