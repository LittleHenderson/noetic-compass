"""Exact isolated-process bootstrap for prospective Pythia-160M V3 research.

This module is standard-library-only until a validated fixture or a separately
authorized execution path deliberately imports the frozen frameworks. It never
loads a tokenizer or model itself.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
from typing import Any, Mapping


LOCK_SCHEMA = "cas_harness_pythia160m_research_lock.v3"
ENVIRONMENT_SCHEMA = "cas_harness_pythia160m_environment_manifest.v3"
CONTRACT_SCHEMA = "cas_harness_pythia160m_startup_contract.v3"
FORBIDDEN_FRAMEWORK_MODULES = frozenset(
    {"torch", "transformers", "tokenizers", "safetensors"}
)


class PythiaV3BootstrapError(RuntimeError):
    """The exact startup contract could not be trusted."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PythiaV3BootstrapError(f"Cannot read trusted JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PythiaV3BootstrapError(f"Trusted JSON must be an object: {path}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PythiaV3BootstrapError(message)


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def _verify_file(path: Path, record: Mapping[str, Any]) -> None:
    _require(path.is_file(), f"Missing frozen file: {path}")
    _require(path.stat().st_size == int(record["byte_count"]), f"Byte-count drift: {path}")
    _require(sha256_file(path) == str(record["sha256"]), f"SHA-256 drift: {path}")


def validate_startup_chain(
    *,
    repo_root: Path,
    lock_path: Path,
    contract_path: Path,
) -> dict[str, Any]:
    """Validate the interpreter, package root, bootstrap, and lock chain."""

    before = FORBIDDEN_FRAMEWORK_MODULES & set(sys.modules)
    _require(not before, f"Framework imported before startup validation: {sorted(before)}")
    repo_root = repo_root.resolve()
    lock_path = lock_path.resolve()
    contract_path = contract_path.resolve()
    lock = load_json(lock_path)
    _require(lock.get("schema_version") == LOCK_SCHEMA, "Unsupported V3 lock schema")
    _require(
        lock.get("status")
        == "PROSPECTIVE_SUCCESSOR_LOCK / EXECUTOR_AUDITOR_LOCAL_STATIC_PASS / RUN_NOT_AUTHORIZED",
        "V3 successor lock is not prospective and unauthorized",
    )
    _require(
        lock.get("startup_path_status")
        == "EXACT_ISOLATED_STARTUP_LOCAL_PASS / RUN_NOT_AUTHORIZED",
        "V3 startup-path status drift",
    )

    frozen = lock.get("frozen_files", {})
    environment_record = frozen.get("environment_manifest", {})
    environment_path = repo_root / str(environment_record.get("path", ""))
    _verify_file(environment_path, environment_record)
    environment = load_json(environment_path)
    _require(
        environment.get("schema_version") == ENVIRONMENT_SCHEMA,
        "Environment-manifest schema drift",
    )
    contract_record = environment.get("startup_contract", {})
    expected_contract_path = repo_root / str(contract_record.get("path", ""))
    _require(_same_path(contract_path, expected_contract_path), "Startup-contract path drift")
    _verify_file(contract_path, contract_record)

    contract = load_json(contract_path)
    _require(contract.get("schema_version") == CONTRACT_SCHEMA, "Startup-contract schema drift")
    _require(contract.get("status") == "PROSPECTIVE / RUN_NOT_AUTHORIZED", "Startup-contract status drift")
    interpreter = contract.get("interpreter", {})
    expected_executable = Path(str(interpreter.get("path", "")))
    actual_executable = Path(sys.executable)
    _require(_same_path(actual_executable, expected_executable), "Interpreter path drift")
    _verify_file(actual_executable, interpreter)
    _require(sys.flags.isolated == 1, "Python isolated flag is required")
    _require(sys.flags.no_user_site == 1, "Python no-user-site flag is required")
    _require(sys.flags.dont_write_bytecode == 1, "Python no-bytecode flag is required")

    invocation = contract.get("invocation", {})
    _require(invocation.get("required_flags") == ["-I", "-B"], "Invocation flag drift")
    _require(invocation.get("shell") == "none", "Shell invocation is prohibited")
    _require(invocation.get("pythonpath_environment_allowed") is False, "PYTHONPATH must remain ignored")

    package_root = Path(str(contract.get("package_root", {}).get("path", "")))
    _require(package_root.is_dir(), f"Frozen package root missing: {package_root}")
    _require(
        os.path.normcase(str(package_root.resolve()))
        == os.path.normcase(str(package_root)),
        "Frozen package root is not canonical",
    )
    for package in contract.get("package_entrypoints", []):
        entrypoint = package_root / str(package["relative_path"])
        _verify_file(entrypoint, package)

    bootstrap_record = contract.get("bootstrap", {})
    bootstrap_path = repo_root / str(bootstrap_record.get("path", ""))
    _verify_file(bootstrap_path, bootstrap_record)
    _require(_same_path(bootstrap_path, Path(__file__)), "Unexpected bootstrap module")
    for key in ("executor", "auditor"):
        record = contract.get(key, {})
        path = repo_root / str(record.get("path", ""))
        _verify_file(path, record)
        _require(
            frozen.get(key, {}).get("sha256") == record.get("sha256"),
            f"Lock/{key} startup binding drift",
        )
    for record in contract.get("immutable_v2_delegate", {}).values():
        path = repo_root / str(record.get("path", ""))
        _verify_file(path, record)

    for record in lock.get("preserved_v2_evidence", {}).values():
        path = repo_root / str(record.get("path", ""))
        _verify_file(path, record)

    package_root_text = os.path.normcase(str(package_root))
    _require(
        all(os.path.normcase(str(Path(item))) != package_root_text for item in sys.path if item),
        "Frozen package root was present before validated insertion",
    )
    after = FORBIDDEN_FRAMEWORK_MODULES & set(sys.modules)
    _require(not after, f"Startup validation imported framework: {sorted(after)}")
    return {
        "repo_root": repo_root,
        "lock": lock,
        "lock_path": lock_path,
        "lock_sha256": sha256_file(lock_path),
        "contract": contract,
        "contract_path": contract_path,
        "contract_sha256": sha256_file(contract_path),
        "package_root": package_root,
        "interpreter_sha256": sha256_file(actual_executable),
        "frameworks_imported": [],
        "model_loads": 0,
        "gpu_queries": 0,
        "output_created": False,
    }


def install_frozen_package_root(validation: Mapping[str, Any]) -> None:
    package_root = str(validation["package_root"])
    _require(package_root not in sys.path, "Frozen package root already inserted")
    sys.path.insert(0, package_root)
    _require(sys.path[0] == package_root, "Frozen package root insertion failed")


def run_framework_import_fixture(validation: Mapping[str, Any]) -> dict[str, Any]:
    """Import only the frozen frameworks under the guard; never load a model."""

    install_frozen_package_root(validation)
    delegate_record = validation["contract"]["immutable_v2_delegate"]["executor"]
    delegate_path = Path(validation["repo_root"]) / str(delegate_record["path"])
    delegate = _load_module("cas_pythia160m_v2_guard_fixture", delegate_path)
    delegate._set_offline_environment()
    guard = delegate.CompatibleZeroNetworkGuard()
    original_socket = socket.socket
    guard.install()
    try:
        _require(isinstance(socket.socket, type), "Guarded socket is not a class")
        _require(issubclass(socket.socket, original_socket), "Guarded socket is incompatible")
        try:
            socket.socket()
        except delegate.PythiaResearchNetworkBlocked:
            pass
        else:
            raise PythiaV3BootstrapError("Zero-network guard allowed socket construction")
        torch = importlib.import_module("torch")
        transformers = importlib.import_module("transformers")
        package_root = Path(str(validation["package_root"]))
        _require(
            Path(str(torch.__file__)).resolve().is_relative_to(package_root),
            "torch imported outside frozen package root",
        )
        _require(
            Path(str(transformers.__file__)).resolve().is_relative_to(package_root),
            "transformers imported outside frozen package root",
        )
        expected = {
            item["distribution"]: item["version"]
            for item in validation["contract"]["package_entrypoints"]
        }
        _require(str(torch.__version__).split("+", 1)[0] == expected["torch"], "torch version drift")
        _require(str(transformers.__version__) == expected["transformers"], "transformers version drift")
        return {
            "status": "FRESH_INTERPRETER_FRAMEWORK_IMPORT_PASS / RUN_NOT_AUTHORIZED",
            "isolated": sys.flags.isolated,
            "no_user_site": sys.flags.no_user_site,
            "dont_write_bytecode": sys.flags.dont_write_bytecode,
            "interpreter_sha256": validation["interpreter_sha256"],
            "contract_sha256": validation["contract_sha256"],
            "package_root": str(package_root),
            "torch_version": str(torch.__version__),
            "transformers_version": str(transformers.__version__),
            "torch_origin": str(Path(str(torch.__file__)).resolve()),
            "transformers_origin": str(Path(str(transformers.__file__)).resolve()),
            "network_attempts_blocked": guard.attempts,
            "socket_restored": True,
            "model_loads": 0,
            "tokenizer_loads": 0,
            "gpu_queries": 0,
            "output_created": False,
            "receipt_created": False,
        }
    finally:
        guard.restore()


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    _require(spec is not None and spec.loader is not None, f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def execute_with_future_receipt(
    validation: Mapping[str, Any],
    *,
    receipt_path: Path,
    output_root: Path,
) -> int:
    """Enter the receipt-gated executor without importing a framework here."""

    install_frozen_package_root(validation)
    contract = validation["contract"]
    executor_path = Path(validation["repo_root"]) / str(contract["executor"]["path"])
    os.environ["CAS_PYTHIA160M_V3_BOOTSTRAP_ACTIVE"] = str(validation["contract_sha256"])
    executor = _load_module("cas_pythia160m_v3_executor", executor_path)
    return int(
        executor.execute_authorized_run(
            repo_root=Path(validation["repo_root"]),
            lock_path=Path(validation["lock_path"]),
            receipt_path=receipt_path,
            output_root=output_root,
            startup_contract_sha256=str(validation["contract_sha256"]),
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--framework-import-fixture", action="store_true")
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)
    try:
        validation = validate_startup_chain(
            repo_root=args.repo_root,
            lock_path=args.lock,
            contract_path=args.contract,
        )
        if args.framework_import_fixture:
            report = run_framework_import_fixture(validation)
        elif args.validate_only:
            report = {
                "status": "STARTUP_CHAIN_MODEL_FREE_PASS / RUN_NOT_AUTHORIZED",
                "lock_sha256": validation["lock_sha256"],
                "contract_sha256": validation["contract_sha256"],
                "frameworks_imported": [],
                "model_loads": 0,
                "gpu_queries": 0,
                "output_created": False,
                "receipt_created": False,
            }
        else:
            _require(args.receipt is not None, "Future execution receipt is missing")
            _require(args.output_root is not None, "Future execution output root is missing")
            return execute_with_future_receipt(
                validation,
                receipt_path=args.receipt,
                output_root=args.output_root,
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL_CLOSED / RUN_NOT_STARTED",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "frameworks_imported": sorted(
                        FORBIDDEN_FRAMEWORK_MODULES & set(sys.modules)
                    ),
                    "model_loads": 0,
                    "tokenizer_loads": 0,
                    "gpu_queries": 0,
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
