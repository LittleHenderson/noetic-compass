"""Exact-byte worker protocol carriers for the isolated Harness v2 kernel.

This module validates deterministic structure and exact bindings only.  It is
not an authenticator, nonce store, trusted clock, WORM substrate, scientific
decision maker, license grant, product route, or disclosure authority.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any

from ._strict_json import (
    canonical_json_bytes,
    canonical_sha256,
    freeze_json,
    load_json_object,
    sha256_bytes,
    thaw_json,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_bool,
    expect_enum,
    expect_git_sha,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_sha256,
    expect_string,
    expect_timestamp,
    parse_artifact_ref,
    require_unique,
)
from .preregistration import PreregistrationArtifact, PreregistrationChain


WORKER_AUTHORIZATION_SCHEMA = "cas_harness_v2.worker_authorization.v1"
WORKER_TERMINAL_RECEIPT_SCHEMA = "cas_harness_v2.worker_terminal_receipt.v1"
WORKER_AUTHORIZATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.worker-authorization+json"
)
WORKER_TERMINAL_RECEIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.worker-terminal-receipt+json"
)
PREREGISTRATION_MEDIA_TYPE = "application/vnd.cas-harness.preregistration+json"

_RUN_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_LOWER_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_TIME_ASSURANCE = {"semantic": "FRESHNESS_ONLY", "trust": "NOT_TRUSTED"}
_AUTHORITY = {
    "scope": "STRUCTURE_ONLY",
    "authentication": "NOT_PROVIDED",
    "durable_one_use": "NOT_PROVIDED",
    "trusted_time": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "scientific_conclusion": "NOT_ESTABLISHED",
    "license": "NOT_GRANTED",
    "product": "NOT_AUTHORIZED",
    "disclosure": "HELD",
}


@dataclass(frozen=True, slots=True)
class WorkerAuthorizationArtifact:
    """A replayable exact-byte structural authorization carrier."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    authorization_id: str
    issued_at: str
    expires_at: str
    run_nonce_b64url: str
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.authorization_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=WORKER_AUTHORIZATION_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class WorkerTerminalReceiptArtifact:
    """A terminal worker result bound to one authorization carrier."""

    raw_bytes: bytes
    sha256: str
    byte_length: int
    receipt_id: str
    terminal_status: str
    worker_started_at: str
    terminal_at: str
    authorization_sha256: str
    payload: Mapping[str, Any]
    outcome_artifact_refs: tuple[ArtifactRef, ...]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.receipt_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=WORKER_TERMINAL_RECEIPT_MEDIA_TYPE,
        )

    @property
    def outcome_access_receipt_ref(self) -> ArtifactRef:
        """The exact receipt reference accepted by PreregistrationChain."""

        return self.artifact_ref


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _require_chain(
    chain: PreregistrationChain,
    *,
    require_pre_outcome: bool,
) -> PreregistrationArtifact:
    if type(chain) is not PreregistrationChain:
        raise SchemaValidationError("chain must be an exact PreregistrationChain")
    chain.assert_integrity()
    if require_pre_outcome and chain.outcome_access is not None:
        raise SchemaValidationError("worker protocol requires a pre-outcome preregistration chain")
    return chain.base


def _pre_outcome_chain_sha256(chain: PreregistrationChain) -> str:
    """Recompute the public chain digest as it existed before outcome access."""

    return canonical_sha256(
        {
            "schema_version": "cas_harness_v2.preregistration_chain.v1",
            "base_preregistration_sha256": chain.base.sha256,
            "amendment_sha256s": [item.sha256 for item in chain.amendments],
            "outcome_access": None,
        }
    )


def _pre_outcome_artifact_refs(
    chain: PreregistrationChain,
) -> tuple[ArtifactRef, ...]:
    """Return only artifacts frozen before the outcome-access event."""

    refs: list[ArtifactRef] = list(chain.base.artifact_refs)
    for amendment in chain.amendments:
        refs.extend(amendment.artifact_refs)
    return tuple(refs)


def _expected_preregistration_binding(
    chain: PreregistrationChain,
    base: PreregistrationArtifact,
) -> dict[str, Any]:
    base_ref = ArtifactRef(
        artifact_id=base.preregistration_id,
        sha256=base.sha256,
        byte_length=base.byte_length,
        media_type=PREREGISTRATION_MEDIA_TYPE,
    )
    return {
        "base_artifact": _artifact_ref_value(base_ref),
        "pre_outcome_chain_sha256": _pre_outcome_chain_sha256(chain),
        "claim_id": base.claim_id,
        "claim_record_sha256": base.claim_record_sha256,
        "protected_design_sha256": base.protected_design_sha256,
    }


def _expected_identity_binding(base: PreregistrationArtifact) -> dict[str, str]:
    identities = base.payload["identities"]
    return {
        "model_canonical_sha256": canonical_sha256(identities["model"]),
        "code_canonical_sha256": canonical_sha256(identities["code"]),
        "environment_canonical_sha256": canonical_sha256(identities["environment"]),
        "combined_canonical_sha256": canonical_sha256(identities),
    }


def _expected_required_design(base: PreregistrationArtifact) -> dict[str, Any]:
    return {
        "controls": [
            {
                "control_id": row["control_id"],
                "canonical_sha256": canonical_sha256(row),
            }
            for row in base.payload["controls"]
        ],
        "falsifiers": [
            {
                "falsifier_id": row["falsifier_id"],
                "canonical_sha256": canonical_sha256(row),
            }
            for row in base.payload["falsifiers"]
        ],
    }


def _require_exact_value(value: Any, expected: Any, path: str) -> None:
    if value != expected:
        raise SchemaValidationError(f"{path} does not exactly match the preregistered binding")


def _validate_freshness_window(value: Any) -> tuple[str, str]:
    path = "$.freshness"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={"issued_at", "expires_at", "semantic", "trust"},
        path=path,
    )
    issued_at = expect_timestamp(obj["issued_at"], f"{path}.issued_at")
    expires_at = expect_timestamp(obj["expires_at"], f"{path}.expires_at")
    if obj["semantic"] != _TIME_ASSURANCE["semantic"]:
        raise SchemaValidationError("$.freshness.semantic must remain FRESHNESS_ONLY")
    if obj["trust"] != _TIME_ASSURANCE["trust"]:
        raise SchemaValidationError("$.freshness.trust must remain NOT_TRUSTED")
    if _time(expires_at) <= _time(issued_at):
        raise SchemaValidationError("authorization freshness expiry must follow issuance")
    return issued_at, expires_at


def _validate_receipt_freshness(
    value: Any,
    *,
    authorization: WorkerAuthorizationArtifact,
) -> tuple[str, str]:
    path = "$.freshness"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={"worker_started_at", "terminal_at", "semantic", "trust"},
        path=path,
    )
    worker_started_at = expect_timestamp(
        obj["worker_started_at"], f"{path}.worker_started_at"
    )
    terminal_at = expect_timestamp(obj["terminal_at"], f"{path}.terminal_at")
    if obj["semantic"] != _TIME_ASSURANCE["semantic"]:
        raise SchemaValidationError("$.freshness.semantic must remain FRESHNESS_ONLY")
    if obj["trust"] != _TIME_ASSURANCE["trust"]:
        raise SchemaValidationError("$.freshness.trust must remain NOT_TRUSTED")
    if _time(worker_started_at) < _time(authorization.issued_at):
        raise SchemaValidationError("worker start precedes authorization issuance")
    if _time(terminal_at) < _time(worker_started_at):
        raise SchemaValidationError("terminal timestamp precedes worker start")
    if _time(terminal_at) > _time(authorization.expires_at):
        raise SchemaValidationError("terminal timestamp exceeds the freshness window")
    return worker_started_at, terminal_at


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _validate_preregistration_binding(
    value: Any,
    *,
    chain: PreregistrationChain,
    base: PreregistrationArtifact,
) -> ArtifactRef:
    path = "$.preregistration_binding"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "base_artifact",
            "pre_outcome_chain_sha256",
            "claim_id",
            "claim_record_sha256",
            "protected_design_sha256",
        },
        path=path,
    )
    base_ref = parse_artifact_ref(obj["base_artifact"], f"{path}.base_artifact")
    expect_sha256(obj["pre_outcome_chain_sha256"], f"{path}.pre_outcome_chain_sha256")
    expect_machine_id(obj["claim_id"], f"{path}.claim_id")
    expect_sha256(obj["claim_record_sha256"], f"{path}.claim_record_sha256")
    expect_sha256(obj["protected_design_sha256"], f"{path}.protected_design_sha256")
    _require_exact_value(
        obj,
        _expected_preregistration_binding(chain, base),
        path,
    )
    if not base_ref.verify_bytes(base.raw_bytes):
        raise SchemaValidationError("preregistration base artifact does not verify exact bytes")
    return base_ref


def _validate_identity_binding(value: Any, base: PreregistrationArtifact) -> None:
    path = "$.identity_binding"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "model_canonical_sha256",
            "code_canonical_sha256",
            "environment_canonical_sha256",
            "combined_canonical_sha256",
        },
        path=path,
    )
    for key in obj:
        expect_sha256(obj[key], f"{path}.{key}")
    _require_exact_value(obj, _expected_identity_binding(base), path)


def _validate_required_design(value: Any, base: PreregistrationArtifact) -> None:
    path = "$.required_design"
    obj = expect_object(value, path)
    expect_keys(obj, required={"controls", "falsifiers"}, path=path)
    controls = expect_list(obj["controls"], f"{path}.controls")
    falsifiers = expect_list(obj["falsifiers"], f"{path}.falsifiers")
    for index, row in enumerate(controls):
        row_path = f"{path}.controls[{index}]"
        item = expect_object(row, row_path)
        expect_keys(item, required={"control_id", "canonical_sha256"}, path=row_path)
        expect_machine_id(item["control_id"], f"{row_path}.control_id")
        expect_sha256(item["canonical_sha256"], f"{row_path}.canonical_sha256")
    for index, row in enumerate(falsifiers):
        row_path = f"{path}.falsifiers[{index}]"
        item = expect_object(row, row_path)
        expect_keys(item, required={"falsifier_id", "canonical_sha256"}, path=row_path)
        expect_machine_id(item["falsifier_id"], f"{row_path}.falsifier_id")
        expect_sha256(item["canonical_sha256"], f"{row_path}.canonical_sha256")
    _require_exact_value(obj, _expected_required_design(base), path)


def _validate_execution_mapping(
    value: Any,
    *,
    base: PreregistrationArtifact,
) -> tuple[str, ...]:
    path = "$.execution_mapping"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "fleet_id",
            "job_id",
            "audit_id",
            "assigned_worker_id",
            "layer_start",
            "layer_end",
            "shard_id",
            "assigned_methods",
            "expected_outputs",
            "lease_model",
        },
        path=path,
    )
    for field in ("fleet_id", "job_id", "audit_id", "assigned_worker_id", "shard_id"):
        expect_machine_id(obj[field], f"{path}.{field}")
    layer_start = expect_int(obj["layer_start"], f"{path}.layer_start")
    layer_end = expect_int(obj["layer_end"], f"{path}.layer_end")
    if layer_end < layer_start:
        raise SchemaValidationError("$.execution_mapping.layer_end must be at least layer_start")

    assigned_values = expect_list(obj["assigned_methods"], f"{path}.assigned_methods")
    assigned_methods = tuple(
        expect_machine_id(item, f"{path}.assigned_methods[{index}]")
        for index, item in enumerate(assigned_values)
    )
    require_unique(assigned_methods, f"{path}.assigned_methods")
    expected_values = expect_list(obj["expected_outputs"], f"{path}.expected_outputs")
    expected_outputs = tuple(
        expect_machine_id(item, f"{path}.expected_outputs[{index}]")
        for index, item in enumerate(expected_values)
    )
    require_unique(expected_outputs, f"{path}.expected_outputs")

    lease_model_path = f"{path}.lease_model"
    lease_model = expect_object(obj["lease_model"], lease_model_path)
    expect_keys(
        lease_model,
        required={
            "model_id",
            "model_revision",
            "model_artifact_manifest_path",
            "model_artifact_manifest_sha256",
            "execution_mode",
        },
        path=lease_model_path,
    )
    model_id = expect_string(
        lease_model["model_id"], f"{lease_model_path}.model_id", maximum=512
    )
    model_revision = expect_git_sha(
        lease_model["model_revision"], f"{lease_model_path}.model_revision"
    )
    preregistered_model = base.payload["identities"]["model"]
    if model_id != preregistered_model["model_id"]:
        raise SchemaValidationError("lease model_id does not match preregistered model identity")
    if model_revision != preregistered_model["revision"]:
        raise SchemaValidationError(
            "lease model_revision does not match preregistered model identity"
        )
    manifest_path = expect_string(
        lease_model["model_artifact_manifest_path"],
        f"{lease_model_path}.model_artifact_manifest_path",
        maximum=4096,
    )
    if manifest_path != manifest_path.strip() or not (
        manifest_path.startswith("/") or _WINDOWS_ABSOLUTE_PATH_RE.match(manifest_path)
    ):
        raise SchemaValidationError(
            "lease model_artifact_manifest_path must be an absolute canonical path"
        )
    manifest_sha = expect_string(
        lease_model["model_artifact_manifest_sha256"],
        f"{lease_model_path}.model_artifact_manifest_sha256",
        maximum=64,
    )
    if not _LOWER_SHA256_RE.fullmatch(manifest_sha):
        raise SchemaValidationError(
            "lease model_artifact_manifest_sha256 must be 64 lowercase hex characters"
        )
    expect_enum(
        lease_model["execution_mode"],
        {"dry_run_control_plane", "external_probe_command"},
        f"{lease_model_path}.execution_mode",
    )
    return expected_outputs


def _validate_run_nonce(value: Any) -> str:
    path = "$.nonce_binding.run_nonce"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={"value_b64url", "profile", "structural_assurance"},
        path=path,
    )
    encoded = expect_string(obj["value_b64url"], f"{path}.value_b64url", maximum=43)
    if not _RUN_NONCE_RE.fullmatch(encoded):
        raise SchemaValidationError(f"{path}.value_b64url must be unpadded base64url for 32 bytes")
    try:
        decoded = base64.b64decode(encoded + "=", altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise SchemaValidationError(f"{path}.value_b64url is not canonical base64url") from exc
    if len(decoded) != 32 or base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != encoded:
        raise SchemaValidationError(f"{path}.value_b64url must encode exactly 32 bytes")
    if obj["profile"] != "CALLER_DECLARED_CSPRNG_256_BIT":
        raise SchemaValidationError(f"{path}.profile must remain CALLER_DECLARED_CSPRNG_256_BIT")
    if obj["structural_assurance"] != "LENGTH_AND_ENCODING_ONLY":
        raise SchemaValidationError(f"{path}.structural_assurance must remain LENGTH_AND_ENCODING_ONLY")
    return encoded


def _validate_nonce_binding(value: Any) -> str:
    path = "$.nonce_binding"
    obj = expect_object(value, path)
    expect_keys(obj, required={"run_nonce", "durable_enforcement"}, path=path)
    run_nonce = _validate_run_nonce(obj["run_nonce"])
    if obj["durable_enforcement"] != "EXTERNAL_REQUIRED_NOT_PROVIDED":
        raise SchemaValidationError(
            "$.nonce_binding.durable_enforcement must remain EXTERNAL_REQUIRED_NOT_PROVIDED"
        )
    return run_nonce


def _validate_authority(value: Any) -> None:
    path = "$.authority"
    obj = expect_object(value, path)
    expect_keys(obj, required=set(_AUTHORITY), path=path)
    if obj != _AUTHORITY:
        raise SchemaValidationError("$.authority must retain every STRUCTURE_ONLY limitation")


def _validate_governance(value: Any, base: PreregistrationArtifact) -> None:
    path = "$.governance"
    obj = expect_object(value, path)
    expected = base.payload["governance"]
    expect_keys(obj, required=set(expected), path=path)
    if obj != expected:
        raise SchemaValidationError(
            "$.governance must remain the preregistered Ring 4 / NOT LICENSED / HELD state"
        )


def build_worker_authorization(
    *,
    chain: PreregistrationChain,
    authorization_id: str,
    issued_at: str,
    expires_at: str,
    execution_mapping: Mapping[str, Any],
    run_nonce: bytes | bytearray | memoryview,
) -> WorkerAuthorizationArtifact:
    """Build and immediately strict-load one prospective authorization carrier.

    ``run_nonce`` must already have been generated by the caller's prospective,
    durable issuance boundary.  This helper verifies only the exact 32-byte
    value and constructs the kernel's deliberately limited structural carrier;
    it cannot prove randomness, one-use consumption, trusted time, WORM
    retention, execution authentication, licensing, or disclosure authority.
    """

    base = _require_chain(chain, require_pre_outcome=True)
    if type(run_nonce) not in (bytes, bytearray, memoryview):
        raise SchemaValidationError("run_nonce must be exact bytes-like input")
    nonce_snapshot = bytes(run_nonce)
    if len(nonce_snapshot) != 32:
        raise SchemaValidationError("run_nonce must contain exactly 32 bytes")
    if not isinstance(execution_mapping, Mapping):
        raise SchemaValidationError("execution_mapping must be a mapping")

    value = {
        "schema_version": WORKER_AUTHORIZATION_SCHEMA,
        "authorization_id": authorization_id,
        "freshness": {
            "issued_at": issued_at,
            "expires_at": expires_at,
            **_TIME_ASSURANCE,
        },
        "preregistration_binding": _expected_preregistration_binding(chain, base),
        "identity_binding": _expected_identity_binding(base),
        "required_design": _expected_required_design(base),
        "execution_mapping": thaw_json(execution_mapping),
        "nonce_binding": {
            "run_nonce": {
                "value_b64url": base64.urlsafe_b64encode(nonce_snapshot)
                .decode("ascii")
                .rstrip("="),
                "profile": "CALLER_DECLARED_CSPRNG_256_BIT",
                "structural_assurance": "LENGTH_AND_ENCODING_ONLY",
            },
            "durable_enforcement": "EXTERNAL_REQUIRED_NOT_PROVIDED",
        },
        "authority": dict(_AUTHORITY),
        "governance": thaw_json(base.payload["governance"]),
    }
    return load_worker_authorization(canonical_json_bytes(value), chain=chain)


def _load_worker_authorization(
    raw: bytes | bytearray | memoryview,
    *,
    chain: PreregistrationChain,
    require_pre_outcome: bool,
) -> WorkerAuthorizationArtifact:
    """Load one exact authorization, optionally for sealed-chain verification."""

    base = _require_chain(chain, require_pre_outcome=require_pre_outcome)
    snapshot, obj = load_json_object(raw)
    expect_keys(
        obj,
        required={
            "schema_version",
            "authorization_id",
            "freshness",
            "preregistration_binding",
            "identity_binding",
            "required_design",
            "execution_mapping",
            "nonce_binding",
            "authority",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != WORKER_AUTHORIZATION_SCHEMA:
        raise SchemaValidationError(
            f"schema_version must equal {WORKER_AUTHORIZATION_SCHEMA!r}"
        )
    authorization_id = expect_machine_id(obj["authorization_id"], "$.authorization_id")
    issued_at, expires_at = _validate_freshness_window(obj["freshness"])
    predecessor_time = (
        chain.amendments[-1].created_at
        if chain.amendments
        else base.payload["created_at"]
    )
    if _time(issued_at) <= _time(predecessor_time):
        raise SchemaValidationError(
            "authorization issuance must follow the frozen preregistration chain"
        )
    base_ref = _validate_preregistration_binding(
        obj["preregistration_binding"], chain=chain, base=base
    )
    _validate_identity_binding(obj["identity_binding"], base)
    _validate_required_design(obj["required_design"], base)
    _validate_execution_mapping(obj["execution_mapping"], base=base)
    run_nonce = _validate_nonce_binding(obj["nonce_binding"])
    _validate_authority(obj["authority"])
    _validate_governance(obj["governance"], base)

    pre_outcome_refs = _pre_outcome_artifact_refs(chain)
    existing_artifact_ids = {reference.artifact_id for reference in pre_outcome_refs}
    if authorization_id in existing_artifact_ids or authorization_id == base_ref.artifact_id:
        raise SchemaValidationError("authorization_id collides with a preregistration artifact")
    refs = (base_ref, *pre_outcome_refs)
    require_unique((reference.artifact_id for reference in refs), "worker authorization refs")
    return WorkerAuthorizationArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        authorization_id=authorization_id,
        issued_at=issued_at,
        expires_at=expires_at,
        run_nonce_b64url=run_nonce,
        payload=freeze_json(obj),
        artifact_refs=tuple(refs),
    )


def load_worker_authorization(
    raw: bytes | bytearray | memoryview,
    *,
    chain: PreregistrationChain,
) -> WorkerAuthorizationArtifact:
    """Load one exact authorization only while the chain is pre-outcome."""

    return _load_worker_authorization(
        raw,
        chain=chain,
        require_pre_outcome=True,
    )


def replay_worker_authorization_for_terminal(
    raw: bytes | bytearray | memoryview,
    *,
    chain: PreregistrationChain,
) -> WorkerAuthorizationArtifact:
    """Replay a prior authorization during terminal/post-seal verification.

    This surface may read an already sealed chain but cannot issue, amend, or
    consume an authorization.  Callers must independently prove that the exact
    carrier was retained prospectively before execution.
    """

    return _load_worker_authorization(
        raw,
        chain=chain,
        require_pre_outcome=False,
    )


def _same_authorization(
    left: WorkerAuthorizationArtifact,
    right: WorkerAuthorizationArtifact,
) -> bool:
    return (
        left.raw_bytes == right.raw_bytes
        and left.sha256 == right.sha256
        and left.byte_length == right.byte_length
        and left.authorization_id == right.authorization_id
        and left.issued_at == right.issued_at
        and left.expires_at == right.expires_at
        and left.run_nonce_b64url == right.run_nonce_b64url
        and left.payload == right.payload
        and left.artifact_refs == right.artifact_refs
    )


def _replay_authorization_carrier(
    authorization: WorkerAuthorizationArtifact | bytes | bytearray | memoryview,
    *,
    chain: PreregistrationChain,
) -> WorkerAuthorizationArtifact:
    """Replay exact authorization bytes and reject forged artifact projections."""

    if type(authorization) is WorkerAuthorizationArtifact:
        replayed = replay_worker_authorization_for_terminal(
            authorization.raw_bytes,
            chain=chain,
        )
        if not _same_authorization(replayed, authorization):
            raise SchemaValidationError(
                "authorization carrier does not match a fresh exact-byte loader replay"
            )
        return replayed
    if type(authorization) in (bytes, bytearray, memoryview):
        return replay_worker_authorization_for_terminal(
            authorization,
            chain=chain,
        )
    raise SchemaValidationError(
        "authorization must be an exact WorkerAuthorizationArtifact or exact bytes-like carrier"
    )


def _validate_terminal(
    value: Any,
    *,
    expected_outputs: tuple[str, ...],
) -> tuple[str, tuple[ArtifactRef, ...]]:
    path = "$.terminal"
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={
            "status",
            "produced_output_effect",
            "produced_outputs",
            "missing_outputs",
            "error",
        },
        path=path,
    )
    status = expect_enum(obj["status"], {"COMPLETED", "FAILED"}, f"{path}.status")
    output_values = expect_list(
        obj["produced_outputs"], f"{path}.produced_outputs", nonempty=False
    )
    refs: list[ArtifactRef] = []
    observed: list[str] = []
    for index, row in enumerate(output_values):
        row_path = f"{path}.produced_outputs[{index}]"
        item = expect_object(row, row_path)
        expect_keys(item, required={"output_name", "artifact"}, path=row_path)
        output_name = expect_machine_id(item["output_name"], f"{row_path}.output_name")
        reference = parse_artifact_ref(item["artifact"], f"{row_path}.artifact")
        refs.append(reference)
        observed.append(output_name)
    require_unique(observed, f"{path}.produced_outputs.output_name")
    require_unique(
        (reference.artifact_id for reference in refs),
        f"{path}.produced_outputs.artifact_id",
    )
    missing_values = expect_list(
        obj["missing_outputs"], f"{path}.missing_outputs", nonempty=False
    )
    missing = tuple(
        expect_machine_id(item, f"{path}.missing_outputs[{index}]")
        for index, item in enumerate(missing_values)
    )
    require_unique(missing, f"{path}.missing_outputs")

    if status == "COMPLETED":
        if (
            obj["produced_output_effect"]
            != "DECLARED_OUTPUTS_NOT_SCIENTIFICALLY_ASSESSED"
        ):
            raise SchemaValidationError(
                "completed terminal receipt must retain the unassessed-output effect"
            )
        if obj["error"] is not None:
            raise SchemaValidationError("completed terminal receipt requires error=null")
        if tuple(observed) != expected_outputs or missing:
            raise SchemaValidationError(
                "completed terminal receipt must produce every expected output in order with none missing"
            )
    else:
        if (
            obj["produced_output_effect"]
            != "QUARANTINED_PARTIAL_NEGATIVE_EVIDENCE_ONLY"
        ):
            raise SchemaValidationError(
                "failed terminal receipt must quarantine every partial output"
            )
        observed_set = set(observed)
        missing_set = set(missing)
        expected_set = set(expected_outputs)
        if (
            observed_set.intersection(missing_set)
            or observed_set.union(missing_set) != expected_set
            or tuple(observed)
            != tuple(item for item in expected_outputs if item in observed_set)
            or missing != tuple(item for item in expected_outputs if item in missing_set)
        ):
            raise SchemaValidationError(
                "failed terminal receipt produced and missing outputs must form the exact ordered expected-output partition"
            )
        error = expect_object(obj["error"], f"{path}.error")
        expect_keys(
            error,
            required={"code", "category", "message", "retryable"},
            path=f"{path}.error",
        )
        expect_machine_id(error["code"], f"{path}.error.code")
        expect_enum(
            error["category"],
            {
                "INPUT_REJECTED",
                "EXECUTION_FAILED",
                "RESOURCE_EXHAUSTED",
                "CALLBACK_FAILED",
                "INTERNAL_ERROR",
            },
            f"{path}.error.category",
        )
        expect_string(error["message"], f"{path}.error.message", maximum=4000)
        expect_bool(error["retryable"], f"{path}.error.retryable")
    return status, tuple(refs)


def build_worker_terminal_receipt(
    *,
    chain: PreregistrationChain,
    authorization: WorkerAuthorizationArtifact | bytes | bytearray | memoryview,
    receipt_id: str,
    worker_started_at: str,
    terminal_at: str,
    terminal_status: str,
    produced_outputs: Sequence[Mapping[str, Any]],
    missing_outputs: Sequence[str],
    error: Mapping[str, Any] | None,
) -> WorkerTerminalReceiptArtifact:
    """Build and strict-load one terminal carrier from a retained authorization.

    Every preregistration, identity, design, execution, nonce, authority, and
    governance field is derived from a fresh exact-byte authorization replay.
    The caller supplies only terminal observations; this helper cannot accept a
    promoted binding or status effect.  It remains a structural carrier builder,
    not execution authentication, trusted time, durable replay protection,
    scientific assessment, licensing, product, or disclosure authority.
    """

    loaded_authorization = _replay_authorization_carrier(
        authorization,
        chain=chain,
    )
    if type(produced_outputs) not in (list, tuple):
        raise SchemaValidationError("produced_outputs must be an exact list or tuple")
    if not all(isinstance(row, Mapping) for row in produced_outputs):
        raise SchemaValidationError("produced_outputs must contain only mappings")
    if type(missing_outputs) not in (list, tuple):
        raise SchemaValidationError("missing_outputs must be an exact list or tuple")
    if error is not None and not isinstance(error, Mapping):
        raise SchemaValidationError("error must be a mapping or null")

    terminal_effects = {
        "COMPLETED": "DECLARED_OUTPUTS_NOT_SCIENTIFICALLY_ASSESSED",
        "FAILED": "QUARANTINED_PARTIAL_NEGATIVE_EVIDENCE_ONLY",
    }
    if type(terminal_status) is not str:
        raise SchemaValidationError("terminal_status must be COMPLETED or FAILED")
    produced_output_effect = terminal_effects.get(terminal_status)
    if produced_output_effect is None:
        raise SchemaValidationError("terminal_status must be COMPLETED or FAILED")

    value = {
        "schema_version": WORKER_TERMINAL_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "authorization": _artifact_ref_value(loaded_authorization.artifact_ref),
        "freshness": {
            "worker_started_at": worker_started_at,
            "terminal_at": terminal_at,
            **_TIME_ASSURANCE,
        },
        "preregistration_binding": thaw_json(
            loaded_authorization.payload["preregistration_binding"]
        ),
        "identity_binding": thaw_json(
            loaded_authorization.payload["identity_binding"]
        ),
        "required_design": thaw_json(
            loaded_authorization.payload["required_design"]
        ),
        "execution_mapping": thaw_json(
            loaded_authorization.payload["execution_mapping"]
        ),
        "nonce_binding": thaw_json(loaded_authorization.payload["nonce_binding"]),
        "terminal": {
            "status": terminal_status,
            "produced_output_effect": produced_output_effect,
            "produced_outputs": [thaw_json(row) for row in produced_outputs],
            "missing_outputs": list(missing_outputs),
            "error": None if error is None else thaw_json(error),
        },
        "authority": thaw_json(loaded_authorization.payload["authority"]),
        "governance": thaw_json(loaded_authorization.payload["governance"]),
    }
    return load_worker_terminal_receipt(
        canonical_json_bytes(value),
        authorization=loaded_authorization,
        chain=chain,
    )


def load_worker_terminal_receipt(
    raw: bytes | bytearray | memoryview,
    *,
    authorization: WorkerAuthorizationArtifact | bytes | bytearray | memoryview,
    chain: PreregistrationChain,
) -> WorkerTerminalReceiptArtifact:
    """Load a terminal receipt and replay every authorization/chain binding."""

    authorization = _replay_authorization_carrier(authorization, chain=chain)
    base = _require_chain(chain, require_pre_outcome=False)
    sealed_outcome_access = chain.outcome_access
    snapshot, obj = load_json_object(raw)
    expect_keys(
        obj,
        required={
            "schema_version",
            "receipt_id",
            "authorization",
            "freshness",
            "preregistration_binding",
            "identity_binding",
            "required_design",
            "execution_mapping",
            "nonce_binding",
            "terminal",
            "authority",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != WORKER_TERMINAL_RECEIPT_SCHEMA:
        raise SchemaValidationError(
            f"schema_version must equal {WORKER_TERMINAL_RECEIPT_SCHEMA!r}"
        )
    receipt_id = expect_machine_id(obj["receipt_id"], "$.receipt_id")
    authorization_ref = parse_artifact_ref(obj["authorization"], "$.authorization")
    if authorization_ref != authorization.artifact_ref or not authorization_ref.verify_bytes(
        authorization.raw_bytes
    ):
        raise SchemaValidationError("receipt authorization does not bind the exact carrier bytes")
    worker_started_at, terminal_at = _validate_receipt_freshness(
        obj["freshness"], authorization=authorization
    )

    for field in (
        "preregistration_binding",
        "identity_binding",
        "required_design",
        "execution_mapping",
        "nonce_binding",
        "authority",
        "governance",
    ):
        if canonical_sha256(obj[field]) != canonical_sha256(authorization.payload[field]):
            raise SchemaValidationError(
                f"$.{field} does not exactly match the authorization carrier"
            )
    _validate_preregistration_binding(
        obj["preregistration_binding"], chain=chain, base=base
    )
    _validate_identity_binding(obj["identity_binding"], base)
    _validate_required_design(obj["required_design"], base)
    expected_outputs = _validate_execution_mapping(obj["execution_mapping"], base=base)
    _validate_nonce_binding(obj["nonce_binding"])
    _validate_authority(obj["authority"])
    _validate_governance(obj["governance"], base)
    status, outcome_refs = _validate_terminal(
        obj["terminal"], expected_outputs=expected_outputs
    )

    existing_ids = {
        authorization.authorization_id,
        *(reference.artifact_id for reference in authorization.artifact_refs),
    }
    if receipt_id in existing_ids:
        raise SchemaValidationError("receipt_id collides with a bound artifact identifier")
    outcome_ids = {reference.artifact_id for reference in outcome_refs}
    if receipt_id in outcome_ids or outcome_ids.intersection(existing_ids):
        raise SchemaValidationError("terminal output artifact identifiers are not unique")
    refs = (authorization.artifact_ref, *authorization.artifact_refs, *outcome_refs)
    require_unique((reference.artifact_id for reference in refs), "worker terminal receipt refs")
    artifact = WorkerTerminalReceiptArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        receipt_id=receipt_id,
        terminal_status=status,
        worker_started_at=worker_started_at,
        terminal_at=terminal_at,
        authorization_sha256=authorization.sha256,
        payload=freeze_json(obj),
        outcome_artifact_refs=outcome_refs,
        artifact_refs=tuple(refs),
    )
    if sealed_outcome_access is not None:
        if sealed_outcome_access.receipt != artifact.artifact_ref:
            raise SchemaValidationError(
                "sealed outcome-access event does not bind this exact terminal receipt"
            )
        if sealed_outcome_access.execution_completed_at != artifact.terminal_at:
            raise SchemaValidationError(
                "sealed outcome-access completion time does not match the terminal receipt"
            )
    return artifact
