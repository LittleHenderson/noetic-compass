"""Independent V3 adapter over the immutable standard-library V2 auditor."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
from typing import Any


BASE_AUDITOR_SHA256 = "0d632894fca5c57fdf77f0bb44766bf7a20ae97be6c622ae75c8cfcbd5f10d02"
LOCK_SCHEMA = "cas_harness_pythia160m_research_lock.v3"
RESULT_SCHEMA = "cas_harness_pythia160m_research_result.v3"
AUDIT_SCHEMA = "cas_harness_pythia160m_research_audit.v3"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_base() -> Any:
    path = Path(__file__).with_name("cas_harness_pythia160m_research_auditor.py")
    if not path.is_file() or sha256_file(path) != BASE_AUDITOR_SHA256:
        raise RuntimeError("Immutable V2 auditor binding drift")
    spec = importlib.util.spec_from_file_location("cas_pythia160m_v2_auditor_immutable", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load immutable V2 auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.LOCK_SCHEMA = LOCK_SCHEMA
    module.RESULT_SCHEMA = RESULT_SCHEMA
    module.AUDIT_SCHEMA = AUDIT_SCHEMA
    return module


def validate_lock_independently(repo_root: Path, lock_path: Path) -> dict[str, Any]:
    base = _load_base()
    original = base.validate_lock_independently
    lock = original(repo_root, lock_path)
    if lock.get("lock_id") != "PYTHIA160M_RESEARCH_INTERVENTION_V3_20260729":
        raise base.PythiaResearchAuditError("V3 lock ID drift")
    if (
        lock.get("status")
        != "PROSPECTIVE_SUCCESSOR_LOCK / EXECUTOR_AUDITOR_LOCAL_STATIC_PASS / RUN_NOT_AUTHORIZED"
    ):
        raise base.PythiaResearchAuditError("V3 lock status drift")
    if (
        lock.get("startup_path_status")
        != "EXACT_ISOLATED_STARTUP_LOCAL_PASS / RUN_NOT_AUTHORIZED"
    ):
        raise base.PythiaResearchAuditError("V3 startup-path status drift")
    for record in lock.get("preserved_v2_evidence", {}).values():
        path = repo_root.resolve() / record["path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(record["byte_count"])
            or sha256_file(path) != record["sha256"]
        ):
            raise base.PythiaResearchAuditError(f"Preserved V2 evidence drift: {path}")
    environment = base.load_json(
        repo_root.resolve() / lock["frozen_files"]["environment_manifest"]["path"]
    )
    contract_record = environment.get("startup_contract", {})
    contract_path = repo_root.resolve() / str(contract_record.get("path", ""))
    if (
        not contract_path.is_file()
        or contract_path.stat().st_size != int(contract_record["byte_count"])
        or sha256_file(contract_path) != contract_record["sha256"]
    ):
        raise base.PythiaResearchAuditError("V3 startup-contract binding drift")
    return lock


def audit_result_mapping(**kwargs: Any) -> dict[str, Any]:
    base = _load_base()
    return dict(base.audit_result_mapping(**kwargs))


def audit_result_directory(
    *, repo_root: Path, lock_path: Path, result_root: Path
) -> dict[str, Any]:
    base = _load_base()
    base.validate_lock_independently = validate_lock_independently
    return dict(
        base.audit_result_directory(
            repo_root=repo_root,
            lock_path=lock_path,
            result_root=result_root,
        )
    )
