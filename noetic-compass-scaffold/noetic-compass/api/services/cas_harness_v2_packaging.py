"""Fail-closed byte verification for the explicitly packaged Harness-v2 kernel."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


PACKAGING_PROVENANCE_SCHEMA = "cas_harness_v2.packaged_mirror_provenance.v1"
PACKAGED_KERNEL_FILES = frozenset(
    {
        "__init__.py",
        "_strict_json.py",
        "_validation.py",
        "artifacts.py",
        "comparison_adapters.py",
        "comparison_departure_metrics.py",
        "comparison_execution_boundary.py",
        "comparison_model_protocol.py",
        "comparison_prompt_injection_layers.py",
        "comparison_shared_protocol.py",
        "comparison_shared_runner.py",
        "comparison_steering_effects.py",
        "comparison_steering_protocol.py",
        "diagnostic_calibration_disposition.py",
        "diagnostic_calibration_fit.py",
        "diagnostic_evidence_coverage_dispersion.py",
        "diagnostic_execution_protocol.py",
        "diagnostic_lifecycle.py",
        "diagnostic_phase_coordinator.py",
        "diagnostic_preregistration.py",
        "diagnostic_prompt_context_inventory.py",
        "diagnostic_prompt_context_provenance.py",
        "diagnostic_stagec_corpus_authoring_scaffold.py",
        "diagnostic_stagec_historical_source_inventory.py",
        "diagnostic_stagec_prerequisite_admission.py",
        "diagnostic_stagec_prerequisite_external_intake.py",
        "diagnostic_stagec_runpod_authorization_v2.py",
        "diagnostic_stagec_runtime_activation.py",
        "diagnostic_study_protocol.py",
        "distributed_probe_contract.py",
        "evidence_packet.py",
        "evidence_packet_builder.py",
        "historical_evidence_import.py",
        "jspace_shadow_contract.py",
        "preregistration.py",
        "stagec_outcome.py",
        "stagec_runpod_readonly_preflight.py",
        "stagec_runpod_runner.py",
        "study_protocol.py",
        "surface_meaning_preservation.py",
        "universal_probe_contract.py",
        "worker_protocol.py",
    }
)
_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class HarnessV2PackagingError(RuntimeError):
    """The packaged kernel no longer matches its exact provenance record."""


def verify_packaged_harness_v2_kernel(
    package_dir: Path | None = None,
) -> str:
    """Verify every admitted package byte before importing the research kernel.

    The result is the uppercase SHA-256 of the provenance record itself.  This
    is a packaging integrity check inside the current repository/image trust
    boundary, not a signature, independent attestation, or license authority.
    """

    root = (
        Path(package_dir)
        if package_dir is not None
        else Path(__file__).resolve().parents[2] / "cas_harness_v2"
    )
    if not root.is_dir() or root.is_symlink():
        raise HarnessV2PackagingError(
            "The packaged Harness-v2 kernel directory is unavailable."
        )
    provenance_path = root / "PACKAGING_PROVENANCE.json"
    try:
        provenance_raw = provenance_path.read_bytes()
        provenance = json.loads(
            provenance_raw.decode("utf-8"), object_pairs_hook=_unique_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise HarnessV2PackagingError(
            "The packaged Harness-v2 provenance record is invalid."
        ) from exc
    if type(provenance) is not dict or set(provenance) != {
        "schema_version",
        "canonical_source_path",
        "packaged_destination_path",
        "copy_policy",
        "source_files",
        "authority_limitations",
    }:
        raise HarnessV2PackagingError(
            "The packaged Harness-v2 provenance shape changed."
        )
    if (
        provenance.get("schema_version") != PACKAGING_PROVENANCE_SCHEMA
        or provenance.get("canonical_source_path") != "src/cas_harness_v2"
        or provenance.get("packaged_destination_path")
        != "noetic-compass-scaffold/noetic-compass/cas_harness_v2"
        or provenance.get("copy_policy") != "BYTE_FOR_BYTE_SOURCE_MIRROR"
        or provenance.get("authority_limitations")
        != {
            "canonical_source_remains_authoritative": True,
            "deployment_readiness": "NOT ESTABLISHED",
            "license_authority": "NOT GRANTED",
            "schema_fork_permitted": False,
        }
    ):
        raise HarnessV2PackagingError(
            "The packaged Harness-v2 provenance authority boundary changed."
        )
    rows = provenance.get("source_files")
    if type(rows) is not dict or set(rows) != PACKAGED_KERNEL_FILES:
        raise HarnessV2PackagingError(
            "The packaged Harness-v2 file inventory changed."
        )
    actual_python_files = {
        path.name for path in root.iterdir() if path.is_file() and path.suffix == ".py"
    }
    if actual_python_files != PACKAGED_KERNEL_FILES:
        raise HarnessV2PackagingError(
            "The packaged Harness-v2 Python surface differs from provenance."
        )
    for filename in sorted(PACKAGED_KERNEL_FILES):
        row = rows.get(filename)
        if type(row) is not dict or set(row) != {"sha256", "size_bytes"}:
            raise HarnessV2PackagingError(
                "A packaged Harness-v2 file identity is malformed."
            )
        expected_sha = row.get("sha256")
        expected_size = row.get("size_bytes")
        if (
            type(expected_sha) is not str
            or not _LOWER_SHA256.fullmatch(expected_sha)
            or type(expected_size) is not int
            or isinstance(expected_size, bool)
            or expected_size < 1
        ):
            raise HarnessV2PackagingError(
                "A packaged Harness-v2 file identity is malformed."
            )
        path = root / filename
        if not path.is_file() or path.is_symlink():
            raise HarnessV2PackagingError(
                "A packaged Harness-v2 source file is unavailable."
            )
        try:
            body = path.read_bytes()
        except OSError as exc:
            raise HarnessV2PackagingError(
                "A packaged Harness-v2 source file cannot be read."
            ) from exc
        if len(body) != expected_size or not hashlib.sha256(body).hexdigest() == expected_sha:
            raise HarnessV2PackagingError(
                "A packaged Harness-v2 source file differs from provenance."
            )
    return hashlib.sha256(provenance_raw).hexdigest().upper()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate provenance key")
        result[key] = value
    return result


__all__ = [
    "HarnessV2PackagingError",
    "PACKAGED_KERNEL_FILES",
    "PACKAGING_PROVENANCE_SCHEMA",
    "verify_packaged_harness_v2_kernel",
]
