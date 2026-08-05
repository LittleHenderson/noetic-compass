"""Receipt-gated V3 wrapper around the immutable V2 scientific executor.

The V2 implementation remains byte-exact for historical validation. This
wrapper changes only startup/authorization lineage and delegates the frozen
scientific request plan after V3 gates pass.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping


LOCK_SCHEMA = "cas_harness_pythia160m_research_lock.v3"
RECEIPT_SCHEMA = "cas_harness_pythia160m_research_authorization.v3"
RESULT_SCHEMA = "cas_harness_pythia160m_research_result.v3"
RUN_ID_RE = re.compile(r"^pythia160m-riv3-[a-z0-9]{16,64}$")
NONCE_RE = re.compile(r"^[0-9a-f]{64}$")
BASE_EXECUTOR_SHA256 = "b5f51f854f1ae0b3241bf57e617c439ef0871f76eb06eefc6677ff410619e78e"
FORBIDDEN_FRAMEWORK_MODULES = frozenset(
    {"torch", "transformers", "tokenizers", "safetensors"}
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_base() -> Any:
    path = Path(__file__).with_name("cas_harness_pythia160m_research_executor.py")
    if not path.is_file() or sha256_file(path) != BASE_EXECUTOR_SHA256:
        raise RuntimeError("Immutable V2 executor binding drift")
    spec = importlib.util.spec_from_file_location("cas_pythia160m_v2_immutable", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load immutable V2 executor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _require(condition: bool, message: str, error: type[Exception] = RuntimeError) -> None:
    if not condition:
        raise error(message)


def _verify_v2_preservation(repo_root: Path, lock: Mapping[str, Any]) -> None:
    for record in lock.get("preserved_v2_evidence", {}).values():
        path = repo_root / str(record["path"])
        _require(path.is_file(), f"Missing preserved V2 evidence: {path}")
        _require(path.stat().st_size == int(record["byte_count"]), f"V2 evidence byte drift: {path}")
        _require(sha256_file(path) == record["sha256"], f"V2 evidence hash drift: {path}")


def _configure_base(base: Any) -> None:
    base.LOCK_SCHEMA = LOCK_SCHEMA
    base.RECEIPT_SCHEMA = RECEIPT_SCHEMA
    base.RESULT_SCHEMA = RESULT_SCHEMA
    base.RUN_ID_RE = RUN_ID_RE
    base.PROHIBITED_NETWORK_MESSAGE = "network prohibited by Pythia-160M research lock V3"


def validate_successor_lock(repo_root: Path, lock_path: Path) -> dict[str, Any]:
    before = FORBIDDEN_FRAMEWORK_MODULES & set(sys.modules)
    _require(not before, f"Framework imported before V3 lock validation: {sorted(before)}")
    base = _load_base()
    _configure_base(base)
    original = base.validate_successor_lock
    validation = original(repo_root, lock_path)
    lock = validation["lock"]
    _require(lock.get("lock_id") == "PYTHIA160M_RESEARCH_INTERVENTION_V3_20260729", "V3 lock ID drift")
    _require(
        lock.get("status")
        == "PROSPECTIVE_SUCCESSOR_LOCK / EXECUTOR_AUDITOR_LOCAL_STATIC_PASS / RUN_NOT_AUTHORIZED",
        "V3 lock status drift",
    )
    _require(
        lock.get("startup_path_status")
        == "EXACT_ISOLATED_STARTUP_LOCAL_PASS / RUN_NOT_AUTHORIZED",
        "V3 startup-path status drift",
    )
    _verify_v2_preservation(repo_root.resolve(), lock)
    environment = base.load_json(
        repo_root.resolve() / lock["frozen_files"]["environment_manifest"]["path"]
    )
    contract_record = environment.get("startup_contract", {})
    contract_path = repo_root.resolve() / str(contract_record.get("path", ""))
    base._verify_file(contract_path, contract_record)
    contract = base.load_json(contract_path)
    _require(contract.get("schema_version") == "cas_harness_pythia160m_startup_contract.v3", "Startup contract schema drift")
    for key in ("executor", "auditor"):
        _require(
            contract.get(key, {}).get("sha256") == lock["frozen_files"][key]["sha256"],
            f"V3 startup {key} binding drift",
        )
    validation["status"] = "V3_SUCCESSOR_LOCK_MODEL_FREE_PASS / RUN_NOT_AUTHORIZED"
    validation["startup_contract_sha256"] = sha256_file(contract_path)
    return validation


def validate_owner_receipt(
    repo_root: Path,
    lock_path: Path,
    receipt_path: Path,
    output_root: Path,
    *,
    now: datetime | None = None,
) -> Any:
    base = _load_base()
    _configure_base(base)
    validation = validate_successor_lock(repo_root, lock_path)
    auth_error = base.PythiaResearchAuthorizationError
    base._require(receipt_path.is_file(), "Fresh one-use owner authorization receipt is missing", auth_error)
    receipt = base.load_json(receipt_path)
    base._require(receipt.get("schema_version") == RECEIPT_SCHEMA, "Receipt schema drift", auth_error)
    base._require(
        receipt.get("authorization_kind") == "OWNER_ONE_USE_OFFLINE_PYTHIA160M_RESEARCH",
        "Receipt authorization kind drift",
        auth_error,
    )
    base._require(receipt.get("status") == "AUTHORIZED_ONE_USE", "Receipt status drift", auth_error)
    base._require(receipt.get("one_use") is True, "Receipt must be one-use", auth_error)
    base._require(receipt.get("lock_sha256") == validation["lock_sha256"], "Receipt lock binding drift", auth_error)
    lock = validation["lock"]
    frozen = lock["frozen_files"]
    for field, key in (
        ("model_manifest_sha256", "model_manifest"),
        ("prompt_split_sha256", "prompt_split"),
        ("intervention_map_sha256", "intervention_map_v2"),
        ("environment_manifest_sha256", "environment_manifest"),
        ("compute_manifest_sha256", "compute_manifest"),
        ("executor_sha256", "executor"),
        ("auditor_sha256", "auditor"),
    ):
        base._require(receipt.get(field) == frozen[key]["sha256"], f"Receipt binding drift: {field}", auth_error)
    base._require(
        receipt.get("startup_contract_sha256") == validation["startup_contract_sha256"],
        "Receipt startup-contract binding drift",
        auth_error,
    )
    base._require(receipt.get("model_id") == base.EXPECTED_MODEL_ID, "Receipt model drift", auth_error)
    base._require(receipt.get("model_revision") == base.EXPECTED_REVISION, "Receipt revision drift", auth_error)
    base._require(receipt.get("seeds") == lock["experiment"]["seeds"], "Receipt seed drift", auth_error)
    base._require(receipt.get("compute_cap") == lock["compute_cap"], "Receipt compute-cap drift", auth_error)
    run_id = str(receipt.get("run_id", ""))
    nonce = str(receipt.get("nonce", ""))
    base._require(bool(RUN_ID_RE.fullmatch(run_id)), "Receipt run ID is invalid", auth_error)
    base._require(bool(NONCE_RE.fullmatch(nonce)), "Receipt nonce must be lowercase 64-hex", auth_error)
    source_commit = base._current_source_commit(repo_root)
    base._require(receipt.get("source_commit") == source_commit, "Receipt source commit is stale", auth_error)
    expected_output = (
        repo_root.resolve()
        / "docs/working/research_intervention_pythia160m_v3/runs"
        / run_id
    ).resolve()
    base._require(output_root.resolve() == expected_output, "Output root is not the isolated V3 run namespace", auth_error)
    base._require(receipt.get("output_root") == str(expected_output), "Receipt output binding drift", auth_error)
    base._require(not expected_output.exists(), "Output root already exists", auth_error)
    payload = dict(receipt)
    recorded_payload_hash = payload.pop("receipt_payload_sha256", None)
    base._require(recorded_payload_hash == base.canonical_sha256(payload), "Receipt payload hash drift", auth_error)
    current = now or datetime.now(timezone.utc)
    try:
        created = datetime.fromisoformat(str(receipt["created_at"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(receipt["expires_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise auth_error("Receipt timestamps are invalid") from exc
    base._require(created.tzinfo is not None and expires.tzinfo is not None, "Receipt timestamps need timezone", auth_error)
    base._require(created <= current <= expires, "Receipt is not currently valid", auth_error)
    base._require((expires - created).total_seconds() <= 86400, "Receipt validity exceeds 24 hours", auth_error)
    nonce_marker = (
        repo_root.resolve()
        / "docs/working/research_intervention_pythia160m_v3/nonce_ledger"
        / f"{hashlib.sha256(nonce.encode('ascii')).hexdigest()}.used"
    ).resolve()
    base._require(not nonce_marker.exists(), "Receipt nonce is stale or consumed", auth_error)
    return base.AuthorizedExecutionToken(
        run_id=run_id,
        nonce=nonce,
        receipt_sha256=sha256_file(receipt_path),
        lock_sha256=validation["lock_sha256"],
        source_commit=source_commit,
        output_root=expected_output,
        nonce_marker=nonce_marker,
        validated_at=current.isoformat(),
    )


def execute_authorized_run(
    *,
    repo_root: Path,
    lock_path: Path,
    receipt_path: Path,
    output_root: Path,
    startup_contract_sha256: str,
) -> int:
    """Delegate only after the exact V3 bootstrap and future receipt agree."""

    _require(not (FORBIDDEN_FRAMEWORK_MODULES & set(sys.modules)), "Framework imported before V3 authorization")
    base = _load_base()
    _configure_base(base)
    validation = validate_successor_lock(repo_root, lock_path)
    _require(
        os.environ.get("CAS_PYTHIA160M_V3_BOOTSTRAP_ACTIVE") == startup_contract_sha256,
        "Exact V3 bootstrap attestation missing",
    )
    _require(
        startup_contract_sha256 == validation["startup_contract_sha256"],
        "V3 bootstrap attestation drift",
    )
    base.validate_successor_lock = validate_successor_lock
    base.validate_owner_receipt = validate_owner_receipt
    return int(
        base.execute_authorized_run(
            repo_root=repo_root,
            lock_path=lock_path,
            receipt_path=receipt_path,
            output_root=output_root,
        )
    )
