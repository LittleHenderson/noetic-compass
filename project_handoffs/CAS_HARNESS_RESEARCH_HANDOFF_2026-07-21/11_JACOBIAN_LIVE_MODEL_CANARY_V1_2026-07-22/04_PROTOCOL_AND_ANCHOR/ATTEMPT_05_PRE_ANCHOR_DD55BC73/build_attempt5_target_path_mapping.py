"""Create the exact Attempt 5 launch-target path mapping once."""

from __future__ import annotations

import json
from pathlib import Path


REMOTE_ROOT = "/workspace/cas-jlcv1-official-f72b89cd-dd55bc73"
REMOTE_CONTROL = f"{REMOTE_ROOT}/control"

paths = {
    "base_protocol_path": f"{REMOTE_CONTROL}/jacobian_lens_canary_v0_raw.json",
    "dependency_bundle_root": f"{REMOTE_ROOT}/dependency",
    "implementation_git_bundle_path": (
        f"{REMOTE_CONTROL}/jacobian_lens_canary_v1_implementation.bundle"
    ),
    "implementation_manifest_path": (
        f"{REMOTE_CONTROL}/jacobian_lens_canary_v1_implementation_manifest.json"
    ),
    "model_manifest_path": (
        f"{REMOTE_ROOT}/frozen/model/pythia_160m_model_manifest_v1.json"
    ),
    "model_publication_marker_path": (
        f"{REMOTE_ROOT}/frozen/model/"
        "pythia_160m_model_manifest_v1.json.publication.json"
    ),
    "model_snapshot_root": "/workspace/cas-model-a8969eb7",
    "network_guard_plan_receipt_path": (
        f"{REMOTE_CONTROL}/jacobian_lens_canary_v1_network_guard_plan.json"
    ),
    "openssl_executable": "/usr/bin/openssl",
    "output_directory": f"{REMOTE_ROOT}/output",
    "protocol_anchor_receipt_path": (
        f"{REMOTE_CONTROL}/jacobian_lens_canary_v1_anchor_receipt.json"
    ),
    "protocol_path": f"{REMOTE_CONTROL}/jacobian_lens_canary_v1_protocol.json",
    "provider_metadata_path": (
        f"{REMOTE_ROOT}/frozen/source/jspace_provider_metadata.json"
    ),
    "repository_root": (
        f"{REMOTE_ROOT}/repo/noetic-compass-scaffold/noetic-compass"
    ),
    "rfc3161_query_path": (
        f"{REMOTE_CONTROL}/jacobian_lens_canary_v1_anchor_request.tsq"
    ),
    "rfc3161_response_path": (
        f"{REMOTE_CONTROL}/jacobian_lens_canary_v1_anchor_response.tsr"
    ),
    "runner_git_executable": "/usr/bin/git",
    "source_attestation_path": (
        f"{REMOTE_ROOT}/frozen/source/jspace_source_attestation.json"
    ),
    "source_manifest_path": (
        f"{REMOTE_ROOT}/frozen/source/jspace_source_snapshot_v1.json"
    ),
    "source_publication_marker_path": (
        f"{REMOTE_ROOT}/frozen/source/"
        "jspace_source_snapshot_v1.json.verified.publication.json"
    ),
    "token_manifest_path": (
        f"{REMOTE_ROOT}/frozen/tokens/jspace_wikitext_blocks_v1.json"
    ),
    "token_publication_marker_path": (
        f"{REMOTE_ROOT}/frozen/tokens/"
        "jspace_wikitext_blocks_v1.json.publication.json"
    ),
}

if len(paths) != 22:
    raise RuntimeError("launch mapping does not contain exactly 22 path fields")

value = {
    "paths": paths,
    "protocol_id": "JACOBIAN_LENS_CANARY_V1",
    "schema_version": (
        "cas_harness_research_shadow.jacobian_lens_launch_target_paths.v1"
    ),
}
payload = json.dumps(
    value,
    ensure_ascii=True,
    allow_nan=False,
    sort_keys=True,
    separators=(",", ":"),
).encode("ascii")

output = (
    Path(__file__).resolve().parent
    / "control"
    / "jacobian_lens_canary_v1_launch_target_paths.json"
)
with output.open("xb") as handle:
    handle.write(payload)

parsed = json.loads(output.read_bytes())
if parsed != value or output.read_bytes() != payload:
    raise RuntimeError("launch mapping create-once verification failed")

print(
    json.dumps(
        {
            "byte_count": len(payload),
            "path_count": len(paths),
            "remote_root": REMOTE_ROOT,
        },
        sort_keys=True,
    )
)
