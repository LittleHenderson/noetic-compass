"""Validate the GPU preflight and build a fail-closed canary evidence manifest."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Any, Sequence


SCHEMA = "cas_harness_tks_definition_anchor_canary_bundle.v1"
MODEL_ID = "EleutherAI/pythia-160m"
MODEL_REVISION = "50f5173d932e8e61f858120bcb800b97af589f46"
MODEL_PARAMETER_COUNT = 162_322_944
PREFLIGHT_SHA256 = "b689da7f7c42c733f0725d445eed758c8b6b06cbc2f1c3a1fd46bccf34dc3b34"
HELPER_SHA256 = "4fed8ddbf9aa7cf899a87c3773d232e0c9ef3927ae3f7b953e1e1738e414024a"
TEST_SHA256 = "5f226eebe0043966fcd6a2b5867478522cc6e5a949f310761933637978206aaf"
PROTOCOL_SHA256 = "d0e154c7ac9913425a16de8d9394b391ae0c788c1bfcdd8959e4d2554b10b715"
RUNNER_SHA256 = "5b069f43af2d50cbc9cfd4735f316497b0c8ab26762cc871d18cd38edee761da"
ARM_MANIFEST_SHA256 = "5ef95e61b8df526fec1d66d59635f8b2a6d0f298537019463cd4babefa9b0d5b"
STAGE7_SHA256 = "c2fa18078feaad6f4970f31a380b67557f3684bb871f96695dbf00c750516d75"
SENSITIVITY_SHA256 = "0868b37a718798cb30a7db8b8a23f5326d4e1ae2b6464842d16218e97ec1751a"


def parse_args(argv: Sequence[str] | None = None) -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("validate-preflight", "build"), required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--canary-source-dir", type=Path, required=True)
    parser.add_argument("--preflight-receipt", type=Path, required=True)
    parser.add_argument("--preflight-log", type=Path)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--canary-output-dir", type=Path)
    parser.add_argument("--canary-log", type=Path)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected a JSON object: {path}")
    return payload


def require_file(path: Path, *, expected_sha256: str | None = None) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise RuntimeError(f"Required file is missing: {resolved}")
    if expected_sha256 is not None:
        actual = sha256_file(resolved)
        if actual != expected_sha256:
            raise RuntimeError(
                f"SHA-256 mismatch for {resolved}: expected {expected_sha256}, got {actual}"
            )
    return resolved


def file_entry(role: str, path: Path) -> dict[str, Any]:
    resolved = require_file(path)
    return {
        "role": role,
        "path": str(resolved),
        "bytes": int(resolved.stat().st_size),
        "sha256": sha256_file(resolved),
    }


def validate_preflight(path: Path) -> dict[str, Any]:
    resolved = require_file(path, expected_sha256=PREFLIGHT_SHA256)
    payload = read_json(resolved)
    expected = {
        "status": "PREFLIGHT_PASS",
        "licensing_status": "NOT_LICENSED_PREFLIGHT_ONLY",
        "claim_eligible": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(
                f"Preflight {key} mismatch: expected {value!r}, got {payload.get(key)!r}"
            )
    model = payload.get("model")
    if not isinstance(model, dict):
        raise RuntimeError("Preflight model object is missing")
    model_expected = {
        "model_id": MODEL_ID,
        "requested_revision": MODEL_REVISION,
        "parameter_count": MODEL_PARAMETER_COUNT,
        "device": "cuda",
        "first_parameter_dtype": "torch.float16",
        "revision_binding": "VERIFIED_EXACT",
    }
    for key, value in model_expected.items():
        if model.get(key) != value:
            raise RuntimeError(
                f"Preflight model.{key} mismatch: expected {value!r}, got {model.get(key)!r}"
            )
    if model.get("resolved_commit_hashes") != [MODEL_REVISION]:
        raise RuntimeError("Preflight resolved model commit is not the exact pinned revision")
    equivalence = payload.get("equivalence")
    if not isinstance(equivalence, dict):
        raise RuntimeError("Preflight equivalence object is missing")
    if equivalence.get("all_required_checks_pass") is not True:
        raise RuntimeError("Preflight did not pass every required hook-equivalence check")
    if equivalence.get("block_count") != 12:
        raise RuntimeError("Preflight did not verify exactly 12 transformer blocks")
    final_mapping = equivalence.get("final_block_to_pre_final_norm")
    if not isinstance(final_mapping, dict) or final_mapping.get("exact_equal") is not True:
        raise RuntimeError("Preflight final block/pre-final-norm mapping is not exact")
    return payload


def static_paths(args: Any) -> list[tuple[str, Path, str | None]]:
    repo = args.repository_root.resolve()
    source = args.canary_source_dir.resolve()
    items: list[tuple[str, Path, str | None]] = [
        ("canary_helper", source / "run_tks_definition_anchor_canary.py", HELPER_SHA256),
        ("canary_helper_test", source / "test_tks_definition_anchor_canary.py", TEST_SHA256),
        ("bundle_builder", Path(__file__), None),
        (
            "frozen_protocol",
            repo / "docs/reference/tks_definition_anchor_diagnostic_protocol_20260721.json",
            PROTOCOL_SHA256,
        ),
        (
            "frozen_runner",
            repo / "noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/run_tks_definition_anchor_diagnostic.py",
            RUNNER_SHA256,
        ),
        (
            "definition_arm_manifest",
            repo / "docs/reference/tks_definition_anchor_diagnostic_arms_20260721.json",
            ARM_MANIFEST_SHA256,
        ),
        (
            "stage7_scenario_bank",
            repo / "noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/stage7_foundation_rolebound_pilot_20260526.json",
            STAGE7_SHA256,
        ),
        (
            "sensitivity_scenario_bank_validated_not_captured",
            repo / "noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/foundation28_balanced_v0_20260526.json",
            SENSITIVITY_SHA256,
        ),
        ("gpu_hook_preflight_receipt", args.preflight_receipt, PREFLIGHT_SHA256),
    ]
    if args.preflight_log is not None:
        items.append(("gpu_hook_preflight_log", args.preflight_log, None))
    if args.source_archive is not None:
        items.append(("frozen_source_archive", args.source_archive, None))
    return items


def validate_static_inputs(args: Any) -> list[dict[str, Any]]:
    validate_preflight(args.preflight_receipt)
    entries: list[dict[str, Any]] = []
    for role, path, expected in static_paths(args):
        resolved = require_file(path, expected_sha256=expected)
        entries.append(file_entry(role, resolved))
    return entries


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite: {path}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        if temporary.read_bytes() != encoded:
            raise RuntimeError("Manifest temporary-file reopen mismatch")
        os.replace(temporary, path)
        if path.read_bytes() != encoded or read_json(path) != payload:
            raise RuntimeError("Manifest final reopen mismatch")
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_text(path: Path, text: str) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite: {path}")
    encoded = text.encode("utf-8")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        if temporary.read_bytes() != encoded:
            raise RuntimeError("SHA256SUMS temporary-file reopen mismatch")
        os.replace(temporary, path)
        if path.read_bytes() != encoded:
            raise RuntimeError("SHA256SUMS final reopen mismatch")
    finally:
        if temporary.exists():
            temporary.unlink()


def build(args: Any) -> dict[str, Any]:
    if args.canary_output_dir is None or args.canary_log is None:
        raise RuntimeError("build mode requires --canary-output-dir and --canary-log")
    output = args.canary_output_dir.resolve()
    workspace = Path("/workspace").resolve()
    if output != workspace and workspace not in output.parents:
        raise RuntimeError(f"Canary output is not on persistent /workspace: {output}")
    raw = require_file(output / "tks_definition_anchor_canary_vectors.npz")
    receipt_path = require_file(output / "tks_definition_anchor_canary_receipt.json")
    log_path = require_file(args.canary_log)
    receipt = read_json(receipt_path)
    if receipt.get("status") != "CANARY_PASS":
        raise RuntimeError("Canary receipt status is not CANARY_PASS")
    if receipt.get("licensing_status") != "NOT_LICENSED_CANARY_ONLY":
        raise RuntimeError("Canary receipt licensing status mismatch")
    if receipt.get("claim_eligible") is not False:
        raise RuntimeError("Canary receipt must remain claim_eligible=false")
    raw_receipt = receipt.get("raw_npz")
    if not isinstance(raw_receipt, dict):
        raise RuntimeError("Canary raw NPZ verification is missing")
    if raw_receipt.get("status") != "LOCAL_DIAGNOSTIC_ARTIFACT_ATOMIC_WRITE_REOPEN_VERIFIED":
        raise RuntimeError("Canary raw NPZ atomic reopen status mismatch")
    if raw_receipt.get("sha256") != sha256_file(raw):
        raise RuntimeError("Canary raw NPZ hash does not match its receipt")

    entries = validate_static_inputs(args)
    entries.extend(
        [
            file_entry("canary_raw_npz", raw),
            file_entry("canary_json_receipt", receipt_path),
            file_entry("canary_combined_stdout_stderr_log", log_path),
        ]
    )
    manifest_path = output / "tks_definition_anchor_canary_artifact_manifest.json"
    sums_path = output / "SHA256SUMS"
    manifest = {
        "schema_version": SCHEMA,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "CANARY_PASS",
        "licensing_status": "NOT_LICENSED_CANARY_ONLY",
        "claim_eligible": False,
        "preflight_binding": {
            "status": "PREFLIGHT_PASS",
            "sha256": PREFLIGHT_SHA256,
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
        },
        "canary_execution_difference": {
            "canary_device_map": "cuda:0",
            "full_diagnostic_device_map": "auto",
            "reason": "Single-GPU canary forbids silent CPU/disk offload; full run follows frozen protocol.",
        },
        "files": entries,
        "durability": {
            "runpod_persistent_workspace": True,
            "off_pod_copy_verified": False,
            "independent_object_store": "OPEN",
        },
        "non_claim": (
            "Operational capture canary only. Not semantic validation, causal/output control, "
            "prompt-injection detection, universality, 300B execution, production readiness, "
            "an Evidence Packet, ACCEPT, LICENSED evidence, or an external claim."
        ),
    }
    atomic_json(manifest_path, manifest)
    sums_entries = [*entries, file_entry("canary_artifact_manifest", manifest_path)]
    sums = "".join(f"{item['sha256']}  {item['path']}\n" for item in sums_entries)
    atomic_text(sums_path, sums)
    for item in sums_entries:
        if sha256_file(Path(item["path"])) != item["sha256"]:
            raise RuntimeError(f"Post-write verification failed: {item['path']}")
    return {
        "status": "CANARY_BUNDLE_MANIFEST_VERIFIED",
        "manifest": file_entry("canary_artifact_manifest", manifest_path),
        "sha256sums": file_entry("canary_sha256sums", sums_path),
        "file_count": len(sums_entries),
        "licensing_status": "NOT_LICENSED_CANARY_ONLY",
        "claim_eligible": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    static_entries = validate_static_inputs(args)
    if args.mode == "validate-preflight":
        print(
            json.dumps(
                {
                    "status": "PREFLIGHT_AND_STATIC_INPUTS_VERIFIED",
                    "preflight_sha256": PREFLIGHT_SHA256,
                    "static_file_count": len(static_entries),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(json.dumps(build(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
