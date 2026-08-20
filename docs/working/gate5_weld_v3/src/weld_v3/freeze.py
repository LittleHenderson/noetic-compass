"""Create and verify a WELD-v3 preregistration freeze."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

from .core import (
    FREEZE_SCHEMA,
    MODEL_ADAPTER_STATUS,
    TRUTH_COMMITMENT_SCHEMA,
    WeldProtocolError,
    canonical_json_bytes,
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
    validate_protocol,
    validate_public_cases,
    write_exclusive_json,
)
from .runtime import attest_binding


FROZEN_FILENAMES = (
    "protocol.json",
    "public_cases.json",
    "runtime_binding.json",
    "model_adapter_contracts.json",
    "truth_commitment.json",
)
FREEZE_FILENAME = "freeze_receipt.json"


def _validate_model_contracts(document: Any) -> Mapping[str, Any]:
    item = require_mapping(document, "model adapter contracts")
    require_exact_keys(
        item,
        {
            "schema_version",
            "experimental_status",
            "provider_calls",
            "candidate_snapshot_commit",
            "contracts",
        },
        "model adapter contracts",
    )
    if item["schema_version"] != "weld-v3-model-adapter-contracts/1":
        raise WeldProtocolError("unsupported model adapter contract schema")
    if item["experimental_status"] != "NOT_RUN" or item["provider_calls"] != "FORBIDDEN":
        raise WeldProtocolError("model adapters must remain NOT_RUN with provider calls FORBIDDEN")
    if item["candidate_snapshot_commit"] != "34442035c69e7feccd6c3b67447568776fe3528f":
        raise WeldProtocolError("model adapter candidate snapshot commit changed")
    contracts = require_mapping(item["contracts"], "model adapter contracts.contracts")
    if set(contracts) != set(MODEL_ADAPTER_STATUS):
        raise WeldProtocolError("model adapter contracts must be exactly J1, J2, and STAGE5")
    for name, contract in contracts.items():
        record = require_mapping(contract, f"model adapter contract {name}")
        if record.get("status") != "NOT_RUN":
            raise WeldProtocolError(f"model adapter contract {name} is not NOT_RUN")
    return item


def _validate_truth_commitment(document: Any) -> Mapping[str, Any]:
    item = require_mapping(document, "truth commitment")
    require_exact_keys(
        item,
        {
            "schema_version",
            "algorithm",
            "domain_separator",
            "salt_hex",
            "hmac_key_sha256",
            "sealed_truth_hmac_sha256",
            "custodian_id",
            "external_commitment_receipt_id",
            "external_commitment_receipt_sha256",
            "entropy_source",
            "hmac_key_size_bytes",
            "salt_size_bytes",
            "custody",
            "commitment_status",
        },
        "truth commitment",
    )
    if (
        item["schema_version"] != TRUTH_COMMITMENT_SCHEMA
        or item["algorithm"] != "hmac-sha256"
        or item["domain_separator"] != "WELD-V3-SEALED-TRUTH-V2"
    ):
        raise WeldProtocolError("unsupported truth commitment")
    salt_hex = require_high_entropy_hex(item["salt_hex"], "truth commitment.salt_hex")
    require_sha256(item["hmac_key_sha256"], "truth commitment.hmac_key_sha256")
    require_sha256(
        item["sealed_truth_hmac_sha256"], "truth commitment.sealed_truth_hmac_sha256"
    )
    require_nonempty_string(item["custodian_id"], "truth commitment.custodian_id")
    require_nonempty_string(
        item["external_commitment_receipt_id"],
        "truth commitment.external_commitment_receipt_id",
    )
    require_sha256(
        item["external_commitment_receipt_sha256"],
        "truth commitment.external_commitment_receipt_sha256",
    )
    if item["entropy_source"] != "EXTERNAL_OS_CSPRNG_AT_LEAST_256_BITS":
        raise WeldProtocolError("truth commitment lacks the required external CSPRNG assertion")
    if (
        not isinstance(item["hmac_key_size_bytes"], int)
        or isinstance(item["hmac_key_size_bytes"], bool)
        or item["hmac_key_size_bytes"] < 32
    ):
        raise WeldProtocolError("truth commitment HMAC key must be at least 32 bytes")
    if (
        not isinstance(item["salt_size_bytes"], int)
        or isinstance(item["salt_size_bytes"], bool)
        or item["salt_size_bytes"] != len(bytes.fromhex(salt_hex))
    ):
        raise WeldProtocolError("truth commitment salt byte count is inconsistent")
    if item["custody"] != "EXTERNAL_UNAVAILABLE_DURING_ACTOR_PHASE":
        raise WeldProtocolError("truth must be held outside the actor phase")
    if item["commitment_status"] != "EXTERNALLY_COMMITTED":
        raise WeldProtocolError("truth commitment is not EXTERNALLY_COMMITTED")
    return item


def _assert_frozen_inventory(root: Path, *, receipt_expected: bool) -> None:
    expected = set(FROZEN_FILENAMES)
    if receipt_expected:
        expected.add(FREEZE_FILENAME)
    if not root.is_dir():
        raise WeldProtocolError(f"preregistration root does not exist: {root}")
    actual = {item.name for item in root.iterdir()}
    if actual != expected or any(not item.is_file() for item in root.iterdir()):
        raise WeldProtocolError(
            f"preregistration inventory must be exactly {sorted(expected)}; got {sorted(actual)}"
        )


def _assert_result_dir_pre_result(result_dir: Path) -> None:
    if result_dir.exists():
        if not result_dir.is_dir():
            raise WeldProtocolError("predeclared result path exists and is not a directory")
        if any(result_dir.iterdir()):
            raise WeldProtocolError("results already exist; preregistration must precede results")


def create_freeze(
    prereg_root: Path, result_dir: Path, *, allow_mock: bool = False
) -> Mapping[str, Any]:
    root = prereg_root.resolve()
    result = result_dir.resolve()
    if not prereg_root.is_absolute() or not result_dir.is_absolute():
        raise WeldProtocolError("preregistration and result paths must be absolute")
    if is_within(result, root) or is_within(root, result):
        raise WeldProtocolError("preregistration and result roots must not be nested")
    _assert_frozen_inventory(root, receipt_expected=False)
    _assert_result_dir_pre_result(result)

    protocol = validate_protocol(load_json(root / "protocol.json"))
    validate_public_cases(load_json(root / "public_cases.json"))
    binding = load_json(root / "runtime_binding.json")
    runtime_attestation = attest_binding(binding, allow_mock=allow_mock)
    _validate_model_contracts(load_json(root / "model_adapter_contracts.json"))
    _validate_truth_commitment(load_json(root / "truth_commitment.json"))

    file_hashes = {name: sha256_file(root / name) for name in FROZEN_FILENAMES}
    freeze_core = {
        "protocol_id": protocol["protocol_id"],
        "prereg_root_absolute": str(root),
        "result_dir_absolute": str(result),
        "profile": binding["profile"],
        "file_hashes": file_hashes,
    }
    receipt = {
        "schema_version": FREEZE_SCHEMA,
        "freeze_id": sha256_bytes(canonical_json_bytes(freeze_core)),
        "created_utc": utc_now(),
        **freeze_core,
        "mock_authorized": binding["profile"] == "MOCK_TEST_ONLY" and allow_mock,
        "runtime_attestation": runtime_attestation,
        "external_anchor_status": "NOT_RUN",
    }
    write_exclusive_json(root / FREEZE_FILENAME, receipt)
    return receipt


def verify_freeze(freeze_path: Path) -> Mapping[str, Any]:
    path = freeze_path.resolve()
    if path.name != FREEZE_FILENAME or not path.is_file():
        raise WeldProtocolError("freeze path must name an existing freeze_receipt.json")
    root = path.parent
    _assert_frozen_inventory(root, receipt_expected=True)
    receipt = require_mapping(load_json(path), "freeze receipt")
    keys = {
        "schema_version",
        "freeze_id",
        "created_utc",
        "protocol_id",
        "prereg_root_absolute",
        "result_dir_absolute",
        "profile",
        "file_hashes",
        "mock_authorized",
        "runtime_attestation",
        "external_anchor_status",
    }
    require_exact_keys(receipt, keys, "freeze receipt")
    if receipt["schema_version"] != FREEZE_SCHEMA:
        raise WeldProtocolError("unsupported freeze receipt schema")
    if Path(receipt["prereg_root_absolute"]).resolve() != root:
        raise WeldProtocolError("freeze receipt preregistration path changed")
    result_dir = Path(receipt["result_dir_absolute"])
    if not result_dir.is_absolute():
        raise WeldProtocolError("freeze receipt result path is not absolute")
    expected_hashes = receipt["file_hashes"]
    if not isinstance(expected_hashes, dict) or set(expected_hashes) != set(FROZEN_FILENAMES):
        raise WeldProtocolError("freeze receipt file inventory changed")
    for name in FROZEN_FILENAMES:
        require_sha256(expected_hashes[name], f"freeze receipt.file_hashes.{name}")
        if sha256_file(root / name) != expected_hashes[name]:
            raise WeldProtocolError(f"frozen file changed after preregistration: {name}")
    protocol = validate_protocol(load_json(root / "protocol.json"))
    validate_public_cases(load_json(root / "public_cases.json"))
    _validate_model_contracts(load_json(root / "model_adapter_contracts.json"))
    _validate_truth_commitment(load_json(root / "truth_commitment.json"))
    binding = load_json(root / "runtime_binding.json")
    if binding.get("profile") != receipt["profile"]:
        raise WeldProtocolError("runtime profile changed after freeze")
    if receipt["profile"] == "MOCK_TEST_ONLY" and receipt["mock_authorized"] is not True:
        raise WeldProtocolError("mock freeze lacks explicit test-only authorization")
    if receipt["profile"] == "PRODUCTION_RUST" and receipt["mock_authorized"] is not False:
        raise WeldProtocolError("production freeze may not authorize mocks")
    if receipt["external_anchor_status"] != "NOT_RUN":
        raise WeldProtocolError("this protocol does not claim an external freeze anchor")
    freeze_core = {
        "protocol_id": protocol["protocol_id"],
        "prereg_root_absolute": str(root),
        "result_dir_absolute": str(result_dir.resolve()),
        "profile": receipt["profile"],
        "file_hashes": expected_hashes,
    }
    if sha256_bytes(canonical_json_bytes(freeze_core)) != receipt["freeze_id"]:
        raise WeldProtocolError("freeze identifier does not match frozen content")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze a WELD-v3 preregistration bundle")
    parser.add_argument("prereg_root", type=Path)
    parser.add_argument("result_dir", type=Path)
    parser.add_argument("--allow-mock", action="store_true", help="test protocol only")
    args = parser.parse_args()
    receipt = create_freeze(args.prereg_root, args.result_dir, allow_mock=args.allow_mock)
    print(receipt["freeze_id"])


if __name__ == "__main__":
    main()
