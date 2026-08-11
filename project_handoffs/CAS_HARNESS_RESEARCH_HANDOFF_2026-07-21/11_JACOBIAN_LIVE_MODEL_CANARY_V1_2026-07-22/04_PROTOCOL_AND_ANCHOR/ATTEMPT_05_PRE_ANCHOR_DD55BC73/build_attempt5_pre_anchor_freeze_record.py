"""Create and independently verify the Attempt 5 pre-anchor freeze record."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


BASE = Path(__file__).resolve().parent
CONTROL = BASE / "control"
PRE = BASE / "environment_pre"
OPERATOR = BASE / "operator"
EXACT_WORKER = Path(
    r"C:\tmp\cas-jlcv1-attempt5-reconstruct-f72b89cd"
    r"\noetic-compass-scaffold\noetic-compass\live-trace-worker"
)
sys.path.insert(0, str(EXACT_WORKER))

from research.jacobian_lens_rfc3161 import (  # noqa: E402
    RFC3161_POLICY_OID,
    build_rfc3161_sha256_query,
)


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def artifact(path: Path, expected_bytes: int, expected_sha256: str) -> dict[str, object]:
    payload = path.read_bytes()
    observed_sha = hashlib.sha256(payload).hexdigest()
    if len(payload) != expected_bytes or observed_sha != expected_sha256:
        raise RuntimeError(f"frozen artifact differs: {path}")
    return {
        "relative_path": path.relative_to(BASE).as_posix(),
        "byte_count": len(payload),
        "sha256": observed_sha,
    }


def parse_key_value_receipt(path: Path) -> dict[str, str]:
    value: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, separator, item = line.partition("=")
        if not separator or not key or key in value:
            raise RuntimeError(f"malformed key-value receipt: {path}")
        value[key] = item
    return value


EXPECTED_RUN_ID = (
    "jlcv1-rfc3161-"
    "dd55bc73ab446ccc794d26c2aeaa2eec2b0997d1384db9752e0f7615d804c380"
)
EXPECTED_COMMIT = "f72b89cd2ec574400ffe69ad7bd1540791fb73c3"
EXPECTED_TREE = "71c45fd5999b1d3f31636bbae8bd199d166ab2f5"
EXPECTED_PARENT = "be97bc7f76d1e9f5e501702660678d4af3081f5e"
EXPECTED_NONCE = "5c47d99e959b3137a8b77f4f4b469a16eb3ca4c4794e0bae0f99100013fc4842"
REMOTE_ROOT = "/workspace/cas-jlcv1-official-f72b89cd-dd55bc73"

core = {
    "implementation_bundle": artifact(
        CONTROL / "jacobian_lens_canary_v1_implementation.bundle",
        36_549_194,
        "360dfc7fab45b780eec2a52b049d9bdb660bc33251fb86dcecd5bc5e8748074b",
    ),
    "implementation_manifest": artifact(
        CONTROL / "jacobian_lens_canary_v1_implementation_manifest.json",
        5_689,
        "cb72ea06ef560b12eeeb0ec843aa46b777d16185bc41089339439a489ca51579",
    ),
    "implementation_manifest_reconstructed": artifact(
        CONTROL / "jacobian_lens_canary_v1_implementation_manifest_reconstructed.json",
        5_689,
        "cb72ea06ef560b12eeeb0ec843aa46b777d16185bc41089339439a489ca51579",
    ),
    "network_guard_plan": artifact(
        CONTROL / "jacobian_lens_canary_v1_network_guard_plan.json",
        7_320,
        "d015aa87c3ee86292e9f1743d0be89fa2604daa0264782b2a518811f4f760f69",
    ),
    "nonce_record": artifact(
        CONTROL / "jacobian_lens_canary_v1_nonce_record.json",
        646,
        "701675e54b7a6bb6e4de3e374f1ada87a330e495b830f61b0c62f3a894088aa0",
    ),
    "controller_capture": artifact(
        CONTROL / "jacobian_lens_canary_v1_provider_controller_capture.json",
        1_248,
        "b0ed2192892b5a9e84ced9b021df7d7620d2dd0f9aaf6fa916276049ffd75dce",
    ),
    "runner_tool_binding": artifact(
        CONTROL / "jacobian_lens_canary_v1_runner_tool_binding.json",
        450,
        "ce16acc6a576cccee2dc13700e09af779570ec0319d6064c109e385020acc70c",
    ),
    "receiver_tool_binding": artifact(
        CONTROL / "jacobian_lens_canary_v1_receiver_tool_binding.json",
        747,
        "68a318796c9b02ca142cdce227bb273cb5cae5baace3118f790735312410bbf0",
    ),
    "base_protocol_raw": artifact(
        CONTROL / "jacobian_lens_canary_v0_raw.json",
        16_292,
        "fb302300829889072c68e5fd0f0e9ac1710daa58aab4aae5abc76a8eee360cb1",
    ),
    "base_protocol_canonical": artifact(
        CONTROL / "jacobian_lens_canary_v0_canonical.json",
        14_190,
        "1a6745617a641649fa9f270220c17921409b05b8168cfcb806b2056e6763aff5",
    ),
    "pre_environment": artifact(
        PRE / "pre.environment.json",
        3_683,
        "4ecd72100da14ccaa657cdd47ae85e8ba5373b66b6c5a71581aea597435ce097",
    ),
    "pre_critical_runtime_files": artifact(
        PRE / "pre.critical_runtime_files.json",
        3_336_110,
        "2484391419db0447f11507266ca080997858ee0d61f2f2290ec40eae83950943",
    ),
    "pre_installed_distributions": artifact(
        PRE / "pre.installed_distributions.json",
        50_708,
        "7a90d9e7e575349ac24f3ee43dbd3236402a3aa788e179967d4102d838b1e8cb",
    ),
    "pre_nvidia_smi": artifact(
        PRE / "pre.nvidia_smi.txt",
        109,
        "9840a3a45b1f38a5a9cb70a96a573a01331313853545536d97620a3ab9fd8b9e",
    ),
    "pre_runtime_layout": artifact(
        PRE / "pre.runtime_layout.json",
        33_977,
        "1fae9cd0c47fa41cc95d3a3fd874b1dbf213df6187994293d0ece948360890c2",
    ),
    "protocol": artifact(
        CONTROL / "jacobian_lens_canary_v1_protocol.json",
        8_141,
        "a038e18087a31956339f235a852e59a0fc67bc4088434f502787df68428abf34",
    ),
    "launch_target_paths": artifact(
        CONTROL / "jacobian_lens_canary_v1_launch_target_paths.json",
        2_606,
        "ceebdc5a9720bc3c466760bab3c9b378f70c2317293177adf3e9126b35ff9643",
    ),
    "anchor_payload": artifact(
        CONTROL / "jacobian_lens_canary_v1_anchor_payload.json",
        3_858,
        "240d6f2de585c3f098d96b05a02fee4a121b3deb30f0165a28c40a79fe79c991",
    ),
    "rfc3161_query": artifact(
        CONTROL / "jacobian_lens_canary_v1_anchor_request.tsq",
        104,
        "e73850302dc31015af2cd5624eed70d445ef553a7de9acca640d5ba9cca9a846",
    ),
}

nonce_record = json.loads(
    (CONTROL / "jacobian_lens_canary_v1_nonce_record.json").read_bytes()
)
protocol = json.loads((CONTROL / "jacobian_lens_canary_v1_protocol.json").read_bytes())
pre_main = json.loads((PRE / "pre.environment.json").read_bytes())
if (
    nonce_record["run_id"] != EXPECTED_RUN_ID
    or nonce_record["rfc3161_query_nonce_hex"] != EXPECTED_NONCE
    or protocol["execution_boundary"]["run_id"] != EXPECTED_RUN_ID
    or protocol["implementation_binding"]["code_commit"] != EXPECTED_COMMIT
    or pre_main["run_id"] != EXPECTED_RUN_ID
    or pre_main["phase"] != "PRE"
    or pre_main["claim_boundary"]["claim_status"] != "NOT_LICENSED"
):
    raise RuntimeError("Attempt 5 run-identity binding differs")

payload_bytes = (CONTROL / "jacobian_lens_canary_v1_anchor_payload.json").read_bytes()
query_bytes = (CONTROL / "jacobian_lens_canary_v1_anchor_request.tsq").read_bytes()
expected_query = build_rfc3161_sha256_query(
    data=payload_bytes,
    nonce_hex=EXPECTED_NONCE,
)
if query_bytes != expected_query:
    raise RuntimeError("RFC3161 query does not match payload, policy, and nonce")

pre_reverify = json.loads((OPERATOR / "PRE_INDEPENDENT_REVERIFY.json").read_bytes())
if (
    (OPERATOR / "PRE_INDEPENDENT_REVERIFY.exit").read_bytes() != b"0\n"
    or pre_reverify["status"] != "CURRENT_RUNTIME_FILES_MATCH_CAPTURE"
    or pre_reverify["main_sha256"] != core["pre_environment"]["sha256"]
    or pre_reverify["file_records_verified"] != 16_351
    or pre_reverify["bytes_verified"] != 5_085_465_464
    or pre_reverify["claim_status"] != "NOT_LICENSED"
    or pre_reverify["provider_authenticated"] is not False
):
    raise RuntimeError("PRE independent re-verification differs")

continuity = parse_key_value_receipt(OPERATOR / "LIVE_CONTINUITY_CHECK_V2.txt")
if (
    (OPERATOR / "LIVE_CONTINUITY_CHECK_V2.exit").read_bytes() != b"0\n"
    or (OPERATOR / "LIVE_CONTINUITY_CHECK_V2.stderr.txt").read_bytes() != b""
    or continuity["continuity"] != "PASS"
    or continuity["run_id"] != EXPECTED_RUN_ID
    or continuity["commit"] != EXPECTED_COMMIT
    or continuity["tree"] != EXPECTED_TREE
    or continuity["parent"] != EXPECTED_PARENT
    or continuity["compute_application_count"] != "0"
    or continuity["rfc3161_query_status"] != "UNSENT"
    or continuity["external_tsa_transmission"] != "NONE"
    or continuity["model_or_cuda_execution"] != "NONE"
    or continuity["claim_boundary"] != "SHADOW / NONE / NOT_LICENSED"
):
    raise RuntimeError("live continuity evidence differs")

offline_decode = artifact(
    OPERATOR / "RFC3161_QUERY_OFFLINE_DECODE.txt",
    359,
    "363b88fb7da69e27a04daa3cc1de3aaac875124b7d1491fc3a086d3e6a83d948",
)
offline_decode_stderr = artifact(
    OPERATOR / "RFC3161_QUERY_OFFLINE_DECODE.stderr.txt",
    76,
    "7fc52fead3a7c53c93c78471a6e1431ca9504546a9f0e76a1009439dd709eff2",
)
pre_reverify_receipt = artifact(
    OPERATOR / "PRE_INDEPENDENT_REVERIFY.json",
    348,
    "8470274c8298e93474fd9f9d0205624752c9a5b68d7eae8b2f764131cc50f949",
)
continuity_receipt = artifact(
    OPERATOR / "LIVE_CONTINUITY_CHECK_V2.txt",
    1_033,
    "3014d7143b47447955a2a64e4a7124602682c33c94192196631369c0ecc696bf",
)
continuity_script = artifact(
    BASE / "attempt5_live_continuity_check.sh",
    (BASE / "attempt5_live_continuity_check.sh").stat().st_size,
    hashlib.sha256((BASE / "attempt5_live_continuity_check.sh").read_bytes()).hexdigest(),
)
continuity_wrapper = artifact(
    BASE / "run_attempt5_live_continuity_v2.sh",
    712,
    "ed3d3e8766410b99598fad0fbc615ef9a6213e53553b190867ebbd46f78c1f91",
)
mapping_builder = artifact(
    BASE / "build_attempt5_target_path_mapping.py",
    (BASE / "build_attempt5_target_path_mapping.py").stat().st_size,
    hashlib.sha256((BASE / "build_attempt5_target_path_mapping.py").read_bytes()).hexdigest(),
)
publication_receipt = artifact(
    OPERATOR / "PREANCHOR_CONTROL_PUBLICATION.txt",
    783,
    "ce63d40cf59337d1f6005583e70363e11fcec71b360c21bd5dcc09592b5e98ed",
)

for forbidden in (
    CONTROL / "jacobian_lens_canary_v1_anchor_response.tsr",
    CONTROL / "jacobian_lens_canary_v1_anchor_receipt.json",
    CONTROL / "jacobian_lens_canary_v1_launch_configuration.json",
):
    if forbidden.exists():
        raise RuntimeError(f"forbidden pre-anchor artifact exists: {forbidden}")

query_sha = core["rfc3161_query"]["sha256"]
approval_text = (
    "I approve sending the exact 104-byte RFC3161 query with SHA-256 "
    f"{query_sha} to DigiCert."
)
record = {
    "schema_version": "cas_harness_research_shadow.attempt_pre_anchor_freeze.v2",
    "protocol_id": "JACOBIAN_LENS_CANARY_V1",
    "attempt": 5,
    "recorded_at_utc": datetime.now(timezone.utc)
    .isoformat(timespec="seconds")
    .replace("+00:00", "Z"),
    "controlling_status": (
        "PRE_ANCHOR_FROZEN / WAITING_FOR_EXPLICIT_BYTE_SPECIFIC_TSA_APPROVAL / "
        "NO_EXTERNAL_TSA_TRANSMISSION / NO_MODEL_OR_CUDA_EXECUTION / "
        "SHADOW / NONE / NOT_LICENSED"
    ),
    "run_identity": {
        "run_id": EXPECTED_RUN_ID,
        "rfc3161_query_nonce_hex": EXPECTED_NONCE,
        "research_pod_instance_id": "zp2s9pscgncn0b",
        "production_pod_instance_id": "hilj2rzs54gi06",
        "remote_root": REMOTE_ROOT,
        "candidate_commit": EXPECTED_COMMIT,
        "candidate_tree": EXPECTED_TREE,
        "candidate_parent": EXPECTED_PARENT,
    },
    "superseded_setup_identity": {
        "run_id": (
            "jlcv1-rfc3161-"
            "eeec3ec7b73df3a068f8d07e3fb274f2f110eaa646914e0af1bb2205f7f8902e"
        ),
        "nonce_record_sha256": (
            "51d13dc619bc81600c6a9057fdd3bf7eac91846cd0d44ae485fdcbbedde931e2"
        ),
        "remote_root": "/workspace/cas-jlcv1-official-f72b89cd-eeec3ec7",
        "status": "SUPERSEDED_SETUP_IDENTITY_NEVER_RESUME_OR_REUSE",
        "pre_present": False,
        "query_present": False,
        "model_or_cuda_execution_present": False,
    },
    "frozen_artifacts": core,
    "rfc3161_query_contract": {
        "byte_count": len(query_bytes),
        "sha256": hashlib.sha256(query_bytes).hexdigest(),
        "message_imprint_algorithm": "SHA-256",
        "message_imprint": hashlib.sha256(payload_bytes).hexdigest(),
        "policy_oid": RFC3161_POLICY_OID,
        "nonce_hex": EXPECTED_NONCE,
        "certificate_requested": True,
        "reconstructed_query_byte_match": True,
        "offline_openssl_decode": offline_decode,
        "offline_openssl_decode_stderr": offline_decode_stderr,
        "transmission_status": "UNSENT",
    },
    "pre_validation": {
        "original_capture_exit_status": "UNAVAILABLE",
        "original_capture_exit_status_reason": (
            "The original SSH parent did not preserve its child exit status."
        ),
        "five_create_once_artifacts_present": True,
        "independent_reverification": pre_reverify_receipt,
        "independent_reverification_exit_code": 0,
        "current_runtime_file_records_verified": 16_351,
        "current_runtime_bytes_verified": 5_085_465_464,
        "result": "PRE_PASS",
        "provider_authenticated": False,
        "claim_status": "NOT_LICENSED",
    },
    "live_continuity_check": {
        "receipt": continuity_receipt,
        "script": continuity_script,
        "wrapper": continuity_wrapper,
        "checked_at_utc": continuity["checked_at_utc"],
        "result": "PASS",
        "host_identity_sha256": continuity["host_identity_sha256"],
        "boot_id_sha256": continuity["boot_id_sha256"],
        "machine_id_sha256": continuity["machine_id_sha256"],
        "gpu_uuid": continuity["gpu_uuid"],
        "gpu_total_memory_bytes": int(continuity["gpu_total_memory_bytes"]),
        "driver_version": continuity["driver_version"],
        "compute_application_count": int(continuity["compute_application_count"]),
        "repository_clean": True,
        "output_entry_count": 0,
        "runlog_entry_count": 0,
        "environment_post_entry_count": 0,
        "production_pod_used_or_changed": False,
    },
    "publication_and_builder_evidence": {
        "preanchor_control_publication": publication_receipt,
        "publication_remote_shell_exit_status_observed": 0,
        "publication_exit_record_limitation": (
            "The first wrapper wrote literal ASCII '0n'; continuity-v2 "
            "independently rehashed every published control artifact."
        ),
        "launch_target_mapping_builder": mapping_builder,
    },
    "negative_artifact_inventory": {
        "rfc3161_response_present": False,
        "anchor_receipt_present": False,
        "launch_configuration_present": False,
        "producer_receipt_present": False,
        "receiver_receipt_present": False,
        "execution_receipt_present": False,
        "post_environment_present": False,
        "external_tsa_transmission_present": False,
        "model_or_cuda_execution_evidence_present": False,
    },
    "approval_boundary": {
        "approval_required": True,
        "approval_received": False,
        "approval_is_query_byte_specific": True,
        "approval_is_single_use": True,
        "all_prior_attempt_approvals_reusable": False,
        "required_exact_text": approval_text,
    },
    "claim_boundary": {
        "mode": "SHADOW",
        "verdict_influence": "NONE",
        "claim_status": "NOT_LICENSED",
        "scientific_model_result": False,
        "product_readiness_inference": False,
        "whole_project_score": "approximately 0.33 / 1.00",
    },
}

output = BASE / "ATTEMPT_05_PRE_ANCHOR_FREEZE_RECORD.json"
payload = canonical(record)
with output.open("xb") as handle:
    handle.write(payload)

reopened = output.read_bytes()
if reopened != payload or json.loads(reopened) != record:
    raise RuntimeError("Attempt 5 pre-anchor freeze record failed create-once reopening")

print(
    json.dumps(
        {
            "byte_count": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "required_exact_approval": approval_text,
        },
        sort_keys=True,
    )
)
