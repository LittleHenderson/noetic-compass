from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON = Path(r"C:\Python314\python.exe")
BOOTSTRAP = (
    REPO_ROOT
    / "noetic-compass-scaffold/noetic-compass/api/services/"
    "cas_harness_pythia160m_v3_bootstrap.py"
)
LOCK = (
    REPO_ROOT
    / "docs/working/research_intervention_pythia160m_v3/"
    "PYTHIA160M_RESEARCH_SUCCESSOR_LOCK_V3.json"
)
CONTRACT = (
    REPO_ROOT
    / "docs/working/research_intervention_pythia160m_v3/"
    "PYTHIA160M_STARTUP_CONTRACT_V3.json"
)
ENVIRONMENT = (
    REPO_ROOT
    / "docs/working/research_intervention_pythia160m_v3/"
    "PYTHIA160M_ENVIRONMENT_MANIFEST_V3.json"
)
FRAMEWORK_ROOTS = {"torch", "transformers", "tokenizers", "safetensors"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _command(
    *,
    lock: Path = LOCK,
    contract: Path = CONTRACT,
    mode: str,
    extra: list[str] | None = None,
) -> list[str]:
    return [
        str(PYTHON),
        "-I",
        "-B",
        str(BOOTSTRAP),
        "--repo-root",
        str(REPO_ROOT),
        "--lock",
        str(lock),
        "--contract",
        str(contract),
        mode,
        *(extra or []),
    ]


def _run(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def _report(completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert lines, completed.stderr
    value = json.loads(lines[-1])
    assert isinstance(value, dict)
    return value


def _mutated_chain(
    tmp_path: Path,
    *,
    mutate_contract,
) -> tuple[Path, Path]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    environment = json.loads(ENVIRONMENT.read_text(encoding="utf-8"))
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    mutate_contract(contract)
    contract_path = tmp_path / "contract.json"
    _write_json(contract_path, contract)
    environment["startup_contract"] = {
        "path": str(contract_path),
        "byte_count": contract_path.stat().st_size,
        "sha256": _sha256(contract_path),
    }
    environment_path = tmp_path / "environment.json"
    _write_json(environment_path, environment)
    lock["frozen_files"]["environment_manifest"] = {
        "path": str(environment_path),
        "byte_count": environment_path.stat().st_size,
        "sha256": _sha256(environment_path),
    }
    lock_path = tmp_path / "lock.json"
    _write_json(lock_path, lock)
    return lock_path, contract_path


def test_exact_isolated_framework_import_fixture_blocks_network_without_model_load() -> None:
    completed = _run(_command(mode="--framework-import-fixture"))
    assert completed.returncode == 0, completed.stderr
    report = _report(completed)
    assert report["status"] == "FRESH_INTERPRETER_FRAMEWORK_IMPORT_PASS / RUN_NOT_AUTHORIZED"
    assert report["isolated"] == 1
    assert report["no_user_site"] == 1
    assert report["dont_write_bytecode"] == 1
    assert report["network_attempts_blocked"] == 1
    assert report["socket_restored"] is True
    assert report["torch_version"] == "2.11.0+cpu"
    assert report["transformers_version"] == "5.8.1"
    assert report["model_loads"] == 0
    assert report["tokenizer_loads"] == 0
    assert report["gpu_queries"] == 0
    assert report["output_created"] is False
    assert report["receipt_created"] is False


def test_exact_model_free_chain_validates_without_framework_import() -> None:
    completed = _run(_command(mode="--validate-only"))
    assert completed.returncode == 0, completed.stderr
    report = _report(completed)
    assert report["status"] == "STARTUP_CHAIN_MODEL_FREE_PASS / RUN_NOT_AUTHORIZED"
    assert report["frameworks_imported"] == []
    assert report["model_loads"] == 0
    assert report["gpu_queries"] == 0
    assert report["output_created"] is False


def test_missing_package_root_fails_closed_before_framework_import(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing-site-packages"
    lock, contract = _mutated_chain(
        tmp_path,
        mutate_contract=lambda value: value["package_root"].update({"path": str(missing)}),
    )
    completed = _run(_command(lock=lock, contract=contract, mode="--validate-only"))
    assert completed.returncode == 2
    report = _report(completed)
    assert "Frozen package root missing" in str(report["error"])
    assert report["frameworks_imported"] == []
    assert report["model_loads"] == 0
    assert report["output_created"] is False
    assert not missing.exists()


def test_drifted_package_root_fails_closed_before_framework_import(
    tmp_path: Path,
) -> None:
    drifted = tmp_path / "wrong-site-packages"
    drifted.mkdir()
    lock, contract = _mutated_chain(
        tmp_path,
        mutate_contract=lambda value: value["package_root"].update({"path": str(drifted)}),
    )
    completed = _run(_command(lock=lock, contract=contract, mode="--validate-only"))
    assert completed.returncode == 2
    report = _report(completed)
    assert "Missing frozen file" in str(report["error"])
    assert report["frameworks_imported"] == []
    assert report["model_loads"] == 0
    assert report["output_created"] is False


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("path", r"C:\Python314\missing-python.exe", "Interpreter path drift"),
        ("sha256", "0" * 64, "SHA-256 drift"),
    ],
)
def test_missing_or_drifted_interpreter_fails_closed(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    lock, contract = _mutated_chain(
        tmp_path,
        mutate_contract=lambda body: body["interpreter"].update({field: value}),
    )
    completed = _run(_command(lock=lock, contract=contract, mode="--validate-only"))
    assert completed.returncode == 2
    report = _report(completed)
    assert message in str(report["error"])
    assert report["frameworks_imported"] == []
    assert report["model_loads"] == 0
    assert report["output_created"] is False


def test_future_execute_missing_receipt_fails_before_framework_import_or_output(
    tmp_path: Path,
) -> None:
    output_root = (
        REPO_ROOT
        / "docs/working/research_intervention_pythia160m_v3/runs/"
        "pythia160m-riv3-missingreceipt0001"
    )
    assert not output_root.exists()
    environment = os.environ.copy()
    environment["CAS_PYTHIA160M_RESEARCH_ENABLED"] = "1"
    environment["CAS_PYTHIA160M_RESEARCH_LIVE"] = "0"
    completed = _run(
        _command(
            mode="--execute",
            extra=[
                "--receipt",
                str(tmp_path / "missing-receipt.json"),
                "--output-root",
                str(output_root),
            ],
        ),
        env=environment,
    )
    assert completed.returncode == 2
    report = _report(completed)
    assert report["error"] == "Fresh one-use owner authorization receipt is missing"
    assert report["frameworks_imported"] == []
    assert report["model_loads"] == 0
    assert report["tokenizer_loads"] == 0
    assert report["gpu_queries"] == 0
    assert report["output_created"] is False
    assert report["receipt_created"] is False
    assert not output_root.exists()


def test_v2_terminal_evidence_and_one_use_artifacts_remain_exact() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    for record in lock["preserved_v2_evidence"].values():
        path = REPO_ROOT / record["path"]
        assert path.is_file()
        assert path.stat().st_size == record["byte_count"]
        assert _sha256(path) == record["sha256"]


def test_v3_modules_have_standard_library_only_top_level_imports() -> None:
    for path in (
        BOOTSTRAP,
        REPO_ROOT
        / "noetic-compass-scaffold/noetic-compass/api/services/"
        "cas_harness_pythia160m_research_executor_v3.py",
        REPO_ROOT
        / "noetic-compass-scaffold/noetic-compass/api/services/"
        "cas_harness_pythia160m_research_auditor_v3.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert not any(
            f"import {root}" in source or f"from {root}" in source
            for root in FRAMEWORK_ROOTS
        )
