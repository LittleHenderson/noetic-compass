"""Post-actor matched-control adjudication for WELD v3."""

from __future__ import annotations

import argparse
import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .actor import ACTOR_RECEIPT_FILENAME
from .core import (
    ACTOR_RECEIPT_SCHEMA,
    ACTOR_RECEIPT_SEAL_SCHEMA,
    ADJUDICATION_SCHEMA,
    ALLOWED_DECISIONS,
    CUSTODIAN_RELEASE_SCHEMA,
    EXTERNAL_COMMITMENT_EVIDENCE_SCHEMA,
    TRUTH_SCHEMA,
    WeldProtocolError,
    information_profile_hash,
    is_within,
    load_json,
    require_exact_keys,
    require_high_entropy_hex,
    require_mapping,
    require_nonempty_string,
    require_sha256,
    sha256_bytes,
    sha256_file,
    utc_now,
    validate_actor_output,
    validate_public_cases,
    write_exclusive_json,
)
from .freeze import verify_freeze


ADJUDICATION_FILENAME = "adjudication.json"
ACTOR_RECEIPT_SEAL_FILENAME = "actor_receipt_seal.json"
CUSTODIAN_RELEASE_FILENAME = "custodian_release.json"
EXTERNAL_COMMITMENT_EVIDENCE_FILENAME = "external_commitment_evidence.json"


def _parse_utc(value: Any, where: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise WeldProtocolError(f"{where} must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise WeldProtocolError(f"{where} is not a valid timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise WeldProtocolError(f"{where} must be UTC")
    return parsed


def _external_evidence_path(
    raw_path: Path, *, prereg_root: Path, result_dir: Path, where: str
) -> Path:
    path = raw_path.resolve()
    if not raw_path.is_absolute() or not path.is_file():
        raise WeldProtocolError(f"{where} must be an absolute existing file")
    if is_within(path, prereg_root) or is_within(path, result_dir):
        raise WeldProtocolError(f"{where} must remain outside preregistration and result roots")
    return path


def _validate_actor_receipt(
    document: Any, freeze_receipt: Mapping[str, Any]
) -> Mapping[str, Any]:
    item = require_mapping(document, "actor receipt")
    keys = {
        "schema_version",
        "phase_status",
        "actor_completed_utc",
        "freeze_id",
        "freeze_receipt_sha256",
        "protocol_id",
        "profile",
        "claim_ceiling",
        "public_cases_sha256",
        "runtime_pre_attestation",
        "runtime_post_attestation",
        "truth_channel",
        "adapter_command_shape",
        "cross_case_cwd_policy",
        "invocation_count",
        "invocations",
        "outputs",
    }
    require_exact_keys(item, keys, "actor receipt")
    if item["schema_version"] != ACTOR_RECEIPT_SCHEMA or item["phase_status"] != "SEALED":
        raise WeldProtocolError("actor receipt is not sealed")
    if item["freeze_id"] != freeze_receipt["freeze_id"]:
        raise WeldProtocolError("actor receipt belongs to another freeze")
    if item["profile"] != freeze_receipt["profile"]:
        raise WeldProtocolError("actor receipt profile differs from freeze")
    if item["protocol_id"] != freeze_receipt["protocol_id"]:
        raise WeldProtocolError("actor receipt protocol differs from freeze")
    expected_ceiling = (
        "MOCK_PROTOCOL_TEST_ONLY"
        if item["profile"] == "MOCK_TEST_ONLY"
        else "ENGINEERED_NOT_VALIDATED"
    )
    if item["claim_ceiling"] != expected_ceiling:
        raise WeldProtocolError("actor receipt exceeds its frozen claim ceiling")
    if item["truth_channel"] != "COMMITMENT_ONLY_NO_PLAINTEXT_ARGUMENT":
        raise WeldProtocolError("actor receipt does not attest the commitment-only channel")
    if (
        item["runtime_pre_attestation"] != freeze_receipt["runtime_attestation"]
        or item["runtime_post_attestation"] != freeze_receipt["runtime_attestation"]
    ):
        raise WeldProtocolError("actor pre/post runtime attestations differ from the freeze")
    if item["cross_case_cwd_policy"] != "FRESH_EMPTY_UNIQUE_CWD_PER_CASE":
        raise WeldProtocolError("actor receipt does not enforce per-case working directories")
    expected_command_shape = (
        "ONE_BOUND_RUST_EXECUTABLE_NO_CASE_ARGUMENTS"
        if item["profile"] == "PRODUCTION_RUST"
        else "ONE_BOUND_MOCK_ADAPTER_NO_CASE_ARGUMENTS"
    )
    if item["adapter_command_shape"] != expected_command_shape:
        raise WeldProtocolError("actor adapter command shape differs from its frozen profile")
    if not isinstance(item["outputs"], list) or not item["outputs"]:
        raise WeldProtocolError("actor receipt has no outputs")
    invocations = item["invocations"]
    if not isinstance(invocations, list) or not invocations:
        raise WeldProtocolError("actor receipt has no adapter invocations")
    count = item["invocation_count"]
    if (
        not isinstance(count, int)
        or isinstance(count, bool)
        or count <= 0
        or count != len(invocations)
        or count != len(item["outputs"])
    ):
        raise WeldProtocolError("actor invocation count must equal its non-empty output count")
    invocation_keys = {
        "sequence",
        "case_id",
        "adapter_invoked",
        "started_utc",
        "completed_utc",
        "input_sha256",
        "stdout_sha256",
        "stderr_sha256",
        "returncode",
        "isolated_cwd_token",
    }
    seen_cases: set[str] = set()
    seen_cwds: set[str] = set()
    latest_invocation_completion: datetime | None = None
    for index, raw in enumerate(invocations, start=1):
        invocation = require_mapping(raw, f"actor receipt.invocations[{index - 1}]")
        require_exact_keys(
            invocation, invocation_keys, f"actor receipt.invocations[{index - 1}]"
        )
        if (
            not isinstance(invocation["sequence"], int)
            or isinstance(invocation["sequence"], bool)
            or invocation["sequence"] != index
            or invocation["adapter_invoked"] is not True
        ):
            raise WeldProtocolError("actor invocation sequence or execution marker is invalid")
        case_id = require_nonempty_string(
            invocation["case_id"], f"actor receipt.invocations[{index - 1}].case_id"
        )
        if case_id in seen_cases:
            raise WeldProtocolError("actor invocation case_id is duplicated")
        seen_cases.add(case_id)
        started = _parse_utc(invocation["started_utc"], "actor invocation.started_utc")
        completed = _parse_utc(invocation["completed_utc"], "actor invocation.completed_utc")
        if completed < started:
            raise WeldProtocolError("actor invocation completed before it started")
        if latest_invocation_completion is None or completed > latest_invocation_completion:
            latest_invocation_completion = completed
        for field in ("input_sha256", "stdout_sha256", "stderr_sha256", "isolated_cwd_token"):
            require_sha256(invocation[field], f"actor invocation.{field}")
        if invocation["stderr_sha256"] != sha256_bytes(b"") or invocation["returncode"] != 0:
            raise WeldProtocolError("actor invocation was not a clean zero-exit execution")
        if invocation["stdout_sha256"] == sha256_bytes(b""):
            raise WeldProtocolError("actor invocation recorded an empty output channel")
        if invocation["isolated_cwd_token"] in seen_cwds:
            raise WeldProtocolError("actor reused a working directory between cases")
        seen_cwds.add(invocation["isolated_cwd_token"])
    output_case_ids: set[str] = set()
    for index, output in enumerate(item["outputs"]):
        if not isinstance(output, dict) or not isinstance(output.get("case_id"), str):
            raise WeldProtocolError(f"actor receipt.outputs[{index}] lacks a string case_id")
        output_case_ids.add(output["case_id"])
    if seen_cases != output_case_ids:
        raise WeldProtocolError("actor invocation records do not match actor outputs")
    actor_completed = _parse_utc(item["actor_completed_utc"], "actor receipt.actor_completed_utc")
    if latest_invocation_completion is None or actor_completed < latest_invocation_completion:
        raise WeldProtocolError("actor completion timestamp predates an invocation")
    return item


def _validate_external_commitment_evidence(
    document: Any, commitment: Mapping[str, Any], freeze_receipt: Mapping[str, Any]
) -> Mapping[str, Any]:
    item = require_mapping(document, "external commitment evidence")
    keys = {
        "schema_version",
        "custodian_id",
        "external_commitment_receipt_id",
        "created_utc",
        "entropy_source",
        "hmac_key_size_bytes",
        "salt_size_bytes",
        "commitment_status",
        "external_anchor_id",
    }
    require_exact_keys(item, keys, "external commitment evidence")
    if item["schema_version"] != EXTERNAL_COMMITMENT_EVIDENCE_SCHEMA:
        raise WeldProtocolError("unsupported external commitment evidence schema")
    for field in ("custodian_id", "external_commitment_receipt_id"):
        if item[field] != commitment[field]:
            raise WeldProtocolError(f"external commitment evidence {field} differs from freeze")
    if item["entropy_source"] != commitment["entropy_source"]:
        raise WeldProtocolError("external commitment entropy source differs from freeze")
    if item["hmac_key_size_bytes"] != commitment["hmac_key_size_bytes"]:
        raise WeldProtocolError("external commitment key size differs from freeze")
    if item["salt_size_bytes"] != commitment["salt_size_bytes"]:
        raise WeldProtocolError("external commitment salt size differs from freeze")
    if item["commitment_status"] != "EXTERNALLY_ANCHORED_BEFORE_FREEZE":
        raise WeldProtocolError("truth commitment lacks external pre-freeze evidence")
    require_nonempty_string(item["external_anchor_id"], "external commitment.external_anchor_id")
    created = _parse_utc(item["created_utc"], "external commitment.created_utc")
    frozen = _parse_utc(freeze_receipt["created_utc"], "freeze receipt.created_utc")
    if created > frozen:
        raise WeldProtocolError("external commitment evidence was created after the freeze")
    return item


def _validate_actor_seal(
    document: Any,
    *,
    actor_path: Path,
    actor_receipt: Mapping[str, Any],
    freeze_receipt: Mapping[str, Any],
) -> Mapping[str, Any]:
    item = require_mapping(document, "actor receipt seal")
    keys = {
        "schema_version",
        "seal_status",
        "freeze_id",
        "actor_receipt_sha256",
        "actor_receipt_size_bytes",
        "actor_invocation_count",
        "actor_output_count",
        "custodian_id",
        "external_anchor_id",
        "seal_nonce_hex",
        "sealed_utc",
        "truth_release_status_at_seal",
    }
    require_exact_keys(item, keys, "actor receipt seal")
    if item["schema_version"] != ACTOR_RECEIPT_SEAL_SCHEMA:
        raise WeldProtocolError("unsupported actor receipt seal schema")
    if item["seal_status"] != "EXTERNALLY_ANCHORED":
        raise WeldProtocolError("actor receipt identity is not externally anchored")
    if item["truth_release_status_at_seal"] != "NOT_RELEASED":
        raise WeldProtocolError("actor receipt was not sealed before truth release")
    if item["freeze_id"] != freeze_receipt["freeze_id"]:
        raise WeldProtocolError("actor receipt seal belongs to another freeze")
    require_sha256(item["actor_receipt_sha256"], "actor receipt seal.actor_receipt_sha256")
    if item["actor_receipt_sha256"] != sha256_file(actor_path):
        raise WeldProtocolError("actor receipt changed after its external seal")
    if item["actor_receipt_size_bytes"] != actor_path.stat().st_size:
        raise WeldProtocolError("actor receipt size changed after its external seal")
    if item["actor_invocation_count"] != actor_receipt["invocation_count"]:
        raise WeldProtocolError("actor seal invocation count differs from actor receipt")
    if item["actor_output_count"] != len(actor_receipt["outputs"]):
        raise WeldProtocolError("actor seal output count differs from actor receipt")
    require_nonempty_string(item["custodian_id"], "actor receipt seal.custodian_id")
    require_nonempty_string(item["external_anchor_id"], "actor receipt seal.external_anchor_id")
    require_high_entropy_hex(item["seal_nonce_hex"], "actor receipt seal.seal_nonce_hex")
    completed = _parse_utc(actor_receipt["actor_completed_utc"], "actor receipt.actor_completed_utc")
    sealed = _parse_utc(item["sealed_utc"], "actor receipt seal.sealed_utc")
    if sealed < completed:
        raise WeldProtocolError("actor receipt seal predates actor completion")
    return item


def _validate_custodian_release(
    document: Any,
    *,
    commitment: Mapping[str, Any],
    actor_path: Path,
    actor_seal_path: Path,
    actor_seal: Mapping[str, Any],
) -> tuple[Mapping[str, Any], bytes]:
    item = require_mapping(document, "custodian release")
    keys = {
        "schema_version",
        "release_status",
        "custodian_id",
        "external_commitment_receipt_id",
        "actor_receipt_seal_sha256",
        "actor_receipt_sha256",
        "hmac_key_hex",
        "released_utc",
        "external_release_receipt_id",
    }
    require_exact_keys(item, keys, "custodian release")
    if item["schema_version"] != CUSTODIAN_RELEASE_SCHEMA:
        raise WeldProtocolError("unsupported custodian release schema")
    if item["release_status"] != "RELEASED_AFTER_EXTERNALLY_ANCHORED_ACTOR_RECEIPT":
        raise WeldProtocolError("custodian did not attest release after actor sealing")
    if item["custodian_id"] != commitment["custodian_id"]:
        raise WeldProtocolError("custodian release identity differs from truth commitment")
    if item["custodian_id"] != actor_seal["custodian_id"]:
        raise WeldProtocolError("actor seal and truth release use different custodians")
    if item["external_commitment_receipt_id"] != commitment["external_commitment_receipt_id"]:
        raise WeldProtocolError("custodian release references another commitment receipt")
    require_sha256(item["actor_receipt_seal_sha256"], "custodian release.actor_receipt_seal_sha256")
    if item["actor_receipt_seal_sha256"] != sha256_file(actor_seal_path):
        raise WeldProtocolError("custodian release references another actor seal")
    require_sha256(item["actor_receipt_sha256"], "custodian release.actor_receipt_sha256")
    if item["actor_receipt_sha256"] != sha256_file(actor_path):
        raise WeldProtocolError("custodian release references another actor receipt")
    require_nonempty_string(
        item["external_release_receipt_id"], "custodian release.external_release_receipt_id"
    )
    key_hex = require_high_entropy_hex(item["hmac_key_hex"], "custodian release.hmac_key_hex")
    key = bytes.fromhex(key_hex)
    if len(key) != commitment["hmac_key_size_bytes"]:
        raise WeldProtocolError("released HMAC key size differs from the commitment")
    if hashlib.sha256(key).hexdigest() != commitment["hmac_key_sha256"]:
        raise WeldProtocolError("released HMAC key does not match the frozen key commitment")
    sealed = _parse_utc(actor_seal["sealed_utc"], "actor receipt seal.sealed_utc")
    released = _parse_utc(item["released_utc"], "custodian release.released_utc")
    if released <= sealed:
        raise WeldProtocolError("truth key release must occur after actor receipt sealing")
    return item, key


def _validate_truth(document: Any, protocol_id: str) -> list[Mapping[str, Any]]:
    root = require_mapping(document, "sealed truth")
    require_exact_keys(root, {"schema_version", "protocol_id", "pairs"}, "sealed truth")
    if root["schema_version"] != TRUTH_SCHEMA or root["protocol_id"] != protocol_id:
        raise WeldProtocolError("sealed truth schema or protocol_id changed")
    pairs = root["pairs"]
    if not isinstance(pairs, list) or not pairs:
        raise WeldProtocolError("sealed truth must contain at least one pair")
    result: list[Mapping[str, Any]] = []
    seen_pair_ids: set[str] = set()
    for index, raw in enumerate(pairs):
        pair = require_mapping(raw, f"sealed truth.pairs[{index}]")
        require_exact_keys(
            pair,
            {
                "pair_id",
                "target_case_id",
                "control_case_id",
                "target_expected_decision",
                "control_expected_decision",
            },
            f"sealed truth.pairs[{index}]",
        )
        pair_id = require_nonempty_string(pair["pair_id"], f"sealed truth.pairs[{index}].pair_id")
        if pair_id in seen_pair_ids:
            raise WeldProtocolError(f"duplicate sealed truth pair_id {pair_id}")
        seen_pair_ids.add(pair_id)
        if pair["target_case_id"] == pair["control_case_id"]:
            raise WeldProtocolError("target and control must be different public cases")
        for field in ("target_expected_decision", "control_expected_decision"):
            if pair[field] not in ALLOWED_DECISIONS:
                raise WeldProtocolError(f"sealed truth {field} is outside the closed enum")
        if pair["target_expected_decision"] != "REPAIR_ACCEPTED":
            raise WeldProtocolError("a target must preregister REPAIR_ACCEPTED")
        if pair["control_expected_decision"] != "NO_REPAIR_NEEDED":
            raise WeldProtocolError("a matched control must preregister NO_REPAIR_NEEDED")
        result.append(pair)
    return result


def adjudicate(
    freeze_path: Path,
    sealed_truth_path: Path,
    actor_receipt_seal_path: Path,
    custodian_release_path: Path,
    external_commitment_evidence_path: Path,
) -> Mapping[str, Any]:
    freeze_receipt = verify_freeze(freeze_path)
    if freeze_receipt["profile"] == "PRODUCTION_RUST":
        raise WeldProtocolError(
            "PRODUCTION_RUST adjudication is blocked until a trusted external-anchor "
            "signature verifier is implemented in a new frozen protocol revision"
        )
    prereg_root = Path(freeze_receipt["prereg_root_absolute"])
    result_dir = Path(freeze_receipt["result_dir_absolute"])
    actor_path = result_dir / ACTOR_RECEIPT_FILENAME
    if not actor_path.is_file():
        raise WeldProtocolError("sealed actor receipt must exist before truth release")

    actor_receipt = _validate_actor_receipt(load_json(actor_path), freeze_receipt)
    if actor_receipt["freeze_receipt_sha256"] != sha256_file(freeze_path.resolve()):
        raise WeldProtocolError("freeze receipt changed after the actor phase")
    if actor_receipt["public_cases_sha256"] != sha256_file(prereg_root / "public_cases.json"):
        raise WeldProtocolError("public cases changed after the actor phase")

    commitment = require_mapping(
        load_json(prereg_root / "truth_commitment.json"), "truth commitment"
    )
    commitment_evidence_path = _external_evidence_path(
        external_commitment_evidence_path,
        prereg_root=prereg_root,
        result_dir=result_dir,
        where="external commitment evidence",
    )
    if sha256_file(commitment_evidence_path) != commitment["external_commitment_receipt_sha256"]:
        raise WeldProtocolError("external commitment evidence differs from the frozen hash")
    _validate_external_commitment_evidence(
        load_json(commitment_evidence_path), commitment, freeze_receipt
    )

    actor_seal_path = _external_evidence_path(
        actor_receipt_seal_path,
        prereg_root=prereg_root,
        result_dir=result_dir,
        where="actor receipt seal",
    )
    actor_seal = _validate_actor_seal(
        load_json(actor_seal_path),
        actor_path=actor_path,
        actor_receipt=actor_receipt,
        freeze_receipt=freeze_receipt,
    )
    release_path = _external_evidence_path(
        custodian_release_path,
        prereg_root=prereg_root,
        result_dir=result_dir,
        where="custodian release",
    )
    custodian_release, hmac_key = _validate_custodian_release(
        load_json(release_path),
        commitment=commitment,
        actor_path=actor_path,
        actor_seal_path=actor_seal_path,
        actor_seal=actor_seal,
    )
    truth_path = _external_evidence_path(
        sealed_truth_path,
        prereg_root=prereg_root,
        result_dir=result_dir,
        where="sealed truth",
    )
    external_paths = {
        truth_path,
        actor_seal_path,
        release_path,
        commitment_evidence_path,
    }
    if len(external_paths) != 4:
        raise WeldProtocolError("truth and external custody evidence must be distinct files")
    truth_bytes = truth_path.read_bytes()
    salt = bytes.fromhex(commitment["salt_hex"])
    committed_message = (
        commitment["domain_separator"].encode("ascii") + b"\x00" + salt + b"\x00" + truth_bytes
    )
    observed_truth_hmac = hmac.new(hmac_key, committed_message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(observed_truth_hmac, commitment["sealed_truth_hmac_sha256"]):
        raise WeldProtocolError("released truth does not match the frozen HMAC commitment")
    observed_truth_hash = hashlib.sha256(truth_bytes).hexdigest()

    cases = validate_public_cases(load_json(prereg_root / "public_cases.json"))
    cases_by_id = {case["case_id"]: case for case in cases}
    outputs = actor_receipt["outputs"]
    invocations_by_id = {
        invocation["case_id"]: invocation for invocation in actor_receipt["invocations"]
    }
    outputs_by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw_output in enumerate(outputs):
        output = require_mapping(raw_output, f"actor receipt.outputs[{index}]")
        case_id = output.get("case_id")
        if case_id not in cases_by_id:
            raise WeldProtocolError("actor receipt contains an output for an unknown public case")
        if case_id in outputs_by_id:
            raise WeldProtocolError("actor receipt contains duplicate case outputs")
        validated_output = validate_actor_output(output, cases_by_id[case_id])
        if invocations_by_id[case_id]["input_sha256"] != validated_output["input_sha256"]:
            raise WeldProtocolError("actor invocation input hash differs from its output")
        outputs_by_id[case_id] = validated_output
    if len(outputs_by_id) != len(outputs) or set(outputs_by_id) != set(cases_by_id):
        raise WeldProtocolError("actor receipt must contain exactly one output per public case")
    pairs = _validate_truth(load_json(truth_path), actor_receipt["protocol_id"])

    assigned_cases: set[str] = set()
    pair_results = []
    for pair in pairs:
        target_id = pair["target_case_id"]
        control_id = pair["control_case_id"]
        if target_id not in cases_by_id or control_id not in cases_by_id:
            raise WeldProtocolError("sealed truth references an unknown public case")
        if target_id in assigned_cases or control_id in assigned_cases:
            raise WeldProtocolError("a public case may occur in only one committed pair")
        assigned_cases.update({target_id, control_id})
        target_output = outputs_by_id[target_id]
        control_output = outputs_by_id[control_id]
        target_pass = target_output["decision"] == pair["target_expected_decision"]
        control_pass = control_output["decision"] == pair["control_expected_decision"]
        target_profile_hash = information_profile_hash(cases_by_id[target_id])
        control_profile_hash = information_profile_hash(cases_by_id[control_id])
        information_matched = target_profile_hash == control_profile_hash
        pair_pass = target_pass and control_pass and information_matched
        pair_results.append(
            {
                "pair_id": pair["pair_id"],
                "target_case_id": target_id,
                "control_case_id": control_id,
                "target_observed_decision": target_output["decision"],
                "target_expected_decision": pair["target_expected_decision"],
                "target_verdict": "PASS" if target_pass else "FAIL",
                "control_observed_decision": control_output["decision"],
                "control_expected_decision": pair["control_expected_decision"],
                "control_verdict": "PASS" if control_pass else "FAIL",
                "target_information_profile_sha256": target_profile_hash,
                "control_information_profile_sha256": control_profile_hash,
                "information_match_verdict": "PASS" if information_matched else "FAIL",
                "pair_verdict": "PASS" if pair_pass else "FAIL",
            }
        )
    if assigned_cases != set(cases_by_id):
        raise WeldProtocolError("every public case must belong to exactly one committed pair")

    overall_pass = all(pair["pair_verdict"] == "PASS" for pair in pair_results)
    result = {
        "schema_version": ADJUDICATION_SCHEMA,
        "adjudicated_utc": utc_now(),
        "freeze_id": freeze_receipt["freeze_id"],
        "actor_receipt_sha256": sha256_file(actor_path),
        "actor_receipt_seal_sha256": sha256_file(actor_seal_path),
        "external_commitment_evidence_sha256": sha256_file(commitment_evidence_path),
        "custodian_release_sha256": sha256_file(release_path),
        "sealed_truth_sha256": observed_truth_hash,
        "sealed_truth_hmac_sha256": observed_truth_hmac,
        "custodian_id": custodian_release["custodian_id"],
        "profile": freeze_receipt["profile"],
        "model_adapter_status": {"J1": "NOT_RUN", "J2": "NOT_RUN", "STAGE5": "NOT_RUN"},
        "claim_ceiling": (
            "MOCK_PROTOCOL_TEST_ONLY"
            if freeze_receipt["profile"] == "MOCK_TEST_ONLY"
            else "ENGINEERED_NOT_VALIDATED"
        ),
        "pair_results": pair_results,
        "overall_verdict": "PASS" if overall_pass else "FAIL",
    }
    write_exclusive_json(result_dir / ADJUDICATION_FILENAME, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Adjudicate a sealed WELD-v3 actor receipt")
    parser.add_argument("freeze_receipt", type=Path)
    parser.add_argument("sealed_truth", type=Path)
    parser.add_argument("actor_receipt_seal", type=Path)
    parser.add_argument("custodian_release", type=Path)
    parser.add_argument("external_commitment_evidence", type=Path)
    args = parser.parse_args()
    result = adjudicate(
        args.freeze_receipt,
        args.sealed_truth,
        args.actor_receipt_seal,
        args.custodian_release,
        args.external_commitment_evidence,
    )
    print(result["overall_verdict"])


if __name__ == "__main__":
    main()
