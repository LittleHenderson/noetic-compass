"""Exact isolated bootstrap for the receipt-gated Pythia V4 executor."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping


LOCK_SCHEMA = "cas_harness_pythia160m_execution_lock.v4"
STARTUP_SCHEMA = "cas_harness_pythia160m_startup_contract.v3"
FORBIDDEN_FRAMEWORKS = frozenset({"torch", "transformers", "tokenizers", "safetensors"})


class V4BootstrapError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise V4BootstrapError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def _verify(path: Path, record: Mapping[str, Any], label: str) -> None:
    _require(path.is_file(), f"{label} missing")
    _require(path.stat().st_size == int(record.get("byte_count", -1)), f"{label} size drift")
    _require(sha256_file(path) == record.get("sha256"), f"{label} hash drift")


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    _require(spec is not None and spec.loader is not None, f"Cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def validate_startup_chain(
    *, repo_root: Path, lock_path: Path, startup_contract_path: Path
) -> dict[str, Any]:
    _require(not (FORBIDDEN_FRAMEWORKS & set(sys.modules)), "Framework imported before bootstrap validation")
    repo_root = repo_root.resolve()
    lock_path = lock_path.resolve()
    lock = load_json(lock_path)
    _require(lock.get("schema_version") == LOCK_SCHEMA, "Execution lock schema drift")
    _require(
        lock.get("status")
        == "PROSPECTIVE_EXECUTION_LOCK / EXECUTOR_AUDITOR_MODEL_FREE_PASS / RUN_NOT_AUTHORIZED",
        "Execution lock status drift",
    )
    startup_record = lock["frozen_files"]["startup_contract_v3"]
    expected_startup = repo_root / startup_record["path"]
    _require(_same_path(startup_contract_path, expected_startup), "Startup contract path drift")
    _verify(expected_startup, startup_record, "startup_contract_v3")
    startup = load_json(expected_startup)
    _require(startup.get("schema_version") == STARTUP_SCHEMA, "Startup contract schema drift")
    interpreter = startup["interpreter"]
    executable = Path(interpreter["path"])
    _require(_same_path(Path(sys.executable), executable), "Interpreter path drift")
    _verify(executable, interpreter, "interpreter")
    _require(sys.flags.isolated == 1, "Python isolated flag is required")
    _require(sys.flags.no_user_site == 1, "Python no-user-site flag is required")
    _require(sys.flags.dont_write_bytecode == 1, "Python no-bytecode flag is required")
    _require(startup["invocation"]["required_flags"] == ["-I", "-B"], "Invocation flag drift")
    _require(startup["invocation"]["shell"] == "none", "Shell use prohibited")
    package_root = Path(startup["package_root"]["path"])
    _require(package_root.is_dir(), "Frozen package root missing")
    for package in startup["package_entrypoints"]:
        _verify(package_root / package["relative_path"], package, f"package.{package['distribution']}")
    for label in ("executor", "auditor", "bootstrap"):
        record = lock["frozen_files"][label]
        path = repo_root / record["path"]
        _verify(path, record, label)
    _require(
        _same_path(repo_root / lock["frozen_files"]["bootstrap"]["path"], Path(__file__)),
        "Unexpected bootstrap module",
    )
    return {
        "repo_root": repo_root,
        "lock": lock,
        "lock_path": lock_path,
        "lock_sha256": sha256_file(lock_path),
        "startup_contract_path": expected_startup,
        "startup_contract_sha256": sha256_file(expected_startup),
        "package_root": package_root,
        "frameworks_imported": [],
        "model_loads": 0,
        "output_created": False,
    }


def execute_with_receipt(
    validation: Mapping[str, Any], *, receipt_path: Path, output_root: Path
) -> int:
    package_root = str(validation["package_root"])
    _require(package_root not in sys.path, "Package root already present")
    sys.path.insert(0, package_root)
    executor_path = Path(validation["repo_root"]) / validation["lock"]["frozen_files"]["executor"]["path"]
    executor = _load_module(executor_path, "cas_pythia_v4_receipt_executor")
    result = executor.execute_authorized_run(
        repo_root=Path(validation["repo_root"]),
        lock_path=Path(validation["lock_path"]),
        receipt_path=receipt_path,
        output_root=output_root,
    )
    return 0 if result else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--startup-contract", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)
    try:
        validation = validate_startup_chain(
            repo_root=args.repo_root,
            lock_path=args.lock,
            startup_contract_path=args.startup_contract,
        )
        if args.validate_only:
            report = {
                "status": "V4_EXECUTION_STARTUP_MODEL_FREE_PASS / RUN_NOT_AUTHORIZED",
                "lock_sha256": validation["lock_sha256"],
                "startup_contract_sha256": validation["startup_contract_sha256"],
                "frameworks_imported": [],
                "model_loads": 0,
                "output_created": False,
                "receipt_created": False,
            }
        else:
            _require(args.receipt is not None, "Fresh one-use V4 receipt is missing")
            _require(args.output_root is not None, "V4 output root is missing")
            return execute_with_receipt(
                validation, receipt_path=args.receipt, output_root=args.output_root
            )
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "FAIL_CLOSED / RUN_NOT_STARTED",
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "frameworks_imported": sorted(FORBIDDEN_FRAMEWORKS & set(sys.modules)),
                    "model_loads": 0,
                    "output_created": False,
                    "receipt_created": False,
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
