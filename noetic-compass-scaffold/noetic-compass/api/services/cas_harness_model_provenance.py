"""Model provenance / license / weight-hash manifest gate for frontier-scale runs.

This is frontier run-gate (5) of the experimental 300B-4T lane. Opening the
frontier request path (``accept_experimental_frontier``) only says the caller
accepts experimental risk; it does **not** say CAS Harness knows *which* weights
will be audited, that they are open-weight, or that they are what the caller
claims. This module is the gate that makes a real frontier run carry a verifiable
statement of model identity, source, license, and per-weight-file SHA-256.

Honesty contract (mirrors the WORM "not retained until re-read" gate in
``cas_harness_static_evidence_anchor.py``):

* We never claim a model's weights are *verified* unless a SHA-256 was actually
  recomputed from the bytes on disk and matched the declared digest.
* A well-formed manifest whose hashes have only been *declared* (not recomputed)
  is ``PROVENANCE_DECLARED_NOT_VERIFIED`` -- enough to *create* a frontier run,
  never enough on its own to reach a customer ACCEPT. The probe workers that
  actually load the weights are where hashes get recomputed; the verifier +
  WORM anchor still gate the final verdict downstream.
* A missing manifest, an identity mismatch, an unrecognized (non open-weight)
  license, a malformed digest, or a recomputed-hash *mismatch* is
  ``PROVENANCE_REJECTED`` and refuses the run.

The module records and checks provenance. It does **not** grant or adjudicate
license rights -- it asserts only that the declared license is a recognized
open-weight identifier, consistent with CAS Harness auditing open-weight /
internal-access models only.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Literal

ProvenanceStatus = Literal[
    "PROVENANCE_VERIFIED",
    "PROVENANCE_DECLARED_NOT_VERIFIED",
    "PROVENANCE_REJECTED",
]

MANIFEST_VERSION = "cas_model_provenance_manifest_v1"

# Recognized open-weight license identifiers. CAS Harness audits open-weight /
# internal-access models only, so a frontier manifest must declare one of these.
# This is an allowlist of *recognized* open-weight licenses, not a legal ruling:
# we record the declared license and check it is a known open-weight tag. Extend
# deliberately -- an unknown tag is refused (honest) rather than waved through.
_OPEN_WEIGHT_LICENSE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "apache-2.0",
        "mit",
        "bsd-2-clause",
        "bsd-3-clause",
        "cc-by-4.0",
        "cc-by-sa-4.0",
        "openrail",
        "openrail++",
        "bigscience-openrail-m",
        "bigscience-bloom-rail-1.0",
        "creativeml-openrail-m",
        "bigcode-openrail-m",
        "llama2",
        "llama3",
        "llama3.1",
        "llama3.2",
        "llama3.3",
        "gemma",
        "qwen",
        "tongyi-qianwen",
        "deepseek",
        "falcon-llm-license",
    }
)

# Common spelling variants normalized onto canonical allowlist tags.
_LICENSE_ALIASES: dict[str, str] = {
    "apache2": "apache-2.0",
    "apache-2": "apache-2.0",
    "apache-license-2.0": "apache-2.0",
    "bsd-3": "bsd-3-clause",
    "bsd-2": "bsd-2-clause",
    "llama-2": "llama2",
    "llama-3": "llama3",
    "llama-3.1": "llama3.1",
    "llama-3.2": "llama3.2",
    "llama-3.3": "llama3.3",
    "qwen-license": "qwen",
    "tongyi-qianwen-license": "tongyi-qianwen",
    "deepseek-license": "deepseek",
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FILE_HASH_CHUNK_BYTES = 65536


def _canonical_json(value: object) -> str:
    """Deterministic JSON encoding, matching the merged-evidence-packet idiom."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_file_sha256(path: str | Path) -> str:
    """Chunked SHA-256 of a file's bytes (the worker-side verification primitive)."""

    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_FILE_HASH_CHUNK_BYTES), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def normalize_license_id(license_id: str) -> str:
    normalized = re.sub(r"[\s_]+", "-", license_id.strip().lower())
    return _LICENSE_ALIASES.get(normalized, normalized)


def is_recognized_open_weight_license(license_id: str) -> bool:
    return normalize_license_id(license_id) in _OPEN_WEIGHT_LICENSE_ALLOWLIST


def frontier_provenance_requirement_notice() -> str:
    return (
        "A frontier-scale (300B-4T) run requires a model provenance/license/weight-hash "
        "manifest: declared model identity, source URI, a recognized open-weight license, "
        "and a SHA-256 for every weight file. Provenance is run-gate (5); accepting "
        "experimental-frontier risk unlocks the request path but does not by itself "
        "establish provenance."
    )


@dataclass(frozen=True)
class WeightFileRef:
    """One weight file's declared identity: relative path + SHA-256 (+ size)."""

    path: str
    sha256: str
    size_bytes: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path, "sha256": self.sha256, "size_bytes": self.size_bytes}


@dataclass(frozen=True)
class ModelProvenanceManifest:
    """Caller-supplied statement of where the audited weights come from.

    ``model_id`` + ``revision`` reproduce the exact open-weight load path the
    probe workers use (``AutoModelForCausalLM.from_pretrained(model_id,
    revision=...)``), so a worker can recompute and match the declared hashes.
    """

    model_id: str
    source_uri: str
    license_id: str
    weight_files: tuple[WeightFileRef, ...]
    revision: str | None = None
    total_size_bytes: int | None = None
    publisher: str | None = None
    signed_by: str | None = None
    manifest_version: str = MANIFEST_VERSION

    def content_digest(self) -> str:
        """A content fingerprint of the declared manifest.

        This is a deterministic SHA-256 over the declared fields -- an integrity
        digest, NOT a cryptographic signature. A real signed attestation
        (sigstore/cosign/GPG over ``signed_by``) is a labelled future enhancement;
        this digest only detects accidental drift of the manifest contents.
        """

        payload = {
            "manifest_version": self.manifest_version,
            "model_id": self.model_id,
            "revision": self.revision,
            "source_uri": self.source_uri,
            "license_id": self.license_id,
            "publisher": self.publisher,
            "signed_by": self.signed_by,
            "total_size_bytes": self.total_size_bytes,
            "weight_files": [ref.to_dict() for ref in self.weight_files],
        }
        return _sha256_hex(_canonical_json(payload))

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_version": self.manifest_version,
            "model_id": self.model_id,
            "revision": self.revision,
            "source_uri": self.source_uri,
            "license_id": self.license_id,
            "publisher": self.publisher,
            "signed_by": self.signed_by,
            "total_size_bytes": self.total_size_bytes,
            "weight_files": [ref.to_dict() for ref in self.weight_files],
            "content_digest": self.content_digest(),
        }


@dataclass(frozen=True)
class WeightFileVerification:
    """Per-file verification outcome: declared, then (if possible) recomputed."""

    path: str
    declared_sha256: str
    verified: bool
    recomputed_sha256: str | None
    note: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "declared_sha256": self.declared_sha256,
            "verified": self.verified,
            "recomputed_sha256": self.recomputed_sha256,
            "note": self.note,
        }


@dataclass(frozen=True)
class ProvenanceSummary:
    """Honest rollup of a provenance check, mirroring the WORM summarizer shape."""

    status: ProvenanceStatus
    model_id: str | None
    license_id: str | None
    license_recognized: bool
    source_uri: str | None
    revision: str | None
    weight_file_count: int
    verified_file_count: int
    all_hashes_verified: bool
    manifest_content_digest: str | None
    notice: str
    reasons: tuple[str, ...] = ()
    file_verifications: tuple[WeightFileVerification, ...] = ()

    @property
    def accepted(self) -> bool:
        """True when the manifest is good enough to *create* a frontier run."""

        return self.status != "PROVENANCE_REJECTED"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "model_id": self.model_id,
            "license_id": self.license_id,
            "license_recognized": self.license_recognized,
            "source_uri": self.source_uri,
            "revision": self.revision,
            "weight_file_count": self.weight_file_count,
            "verified_file_count": self.verified_file_count,
            "all_hashes_verified": self.all_hashes_verified,
            "manifest_content_digest": self.manifest_content_digest,
            "notice": self.notice,
            "reasons": list(self.reasons),
            "file_verifications": [v.to_dict() for v in self.file_verifications],
        }


def _rejected(reasons: list[str], *, model_id: str | None = None) -> ProvenanceSummary:
    return ProvenanceSummary(
        status="PROVENANCE_REJECTED",
        model_id=model_id,
        license_id=None,
        license_recognized=False,
        source_uri=None,
        revision=None,
        weight_file_count=0,
        verified_file_count=0,
        all_hashes_verified=False,
        manifest_content_digest=None,
        notice=(
            "Model provenance manifest rejected: "
            + "; ".join(reasons)
            + ". "
            + frontier_provenance_requirement_notice()
        ),
        reasons=tuple(reasons),
    )


def summarize_model_provenance(
    *,
    manifest: ModelProvenanceManifest | None,
    expected_model_id: str,
    weights_root: str | Path | None = None,
) -> ProvenanceSummary:
    """Check a provenance manifest and return an honest tri-state summary.

    ``weights_root`` is the directory holding the actual weight files. When it is
    provided and a file exists under it, the declared SHA-256 is recomputed and
    matched (worker-side path). At API create time no weights are present, so
    ``weights_root`` is ``None`` and a good manifest lands at
    ``PROVENANCE_DECLARED_NOT_VERIFIED`` -- the honest state.
    """

    if manifest is None:
        return _rejected(
            ["no model provenance manifest attached"], model_id=expected_model_id
        )

    reasons: list[str] = []

    declared_model_id = (manifest.model_id or "").strip()
    if not declared_model_id:
        reasons.append("manifest model_id is empty")
    elif declared_model_id != expected_model_id.strip():
        reasons.append(
            f"manifest model_id '{declared_model_id}' does not match the requested "
            f"model_id '{expected_model_id.strip()}'"
        )

    if not (manifest.source_uri or "").strip():
        reasons.append("manifest source_uri is empty")

    license_recognized = is_recognized_open_weight_license(manifest.license_id or "")
    if not (manifest.license_id or "").strip():
        reasons.append("manifest license_id is empty")
    elif not license_recognized:
        reasons.append(
            f"declared license '{manifest.license_id}' is not a recognized open-weight "
            "license identifier (CAS Harness audits open-weight models only; it records "
            "provenance, it does not grant or adjudicate license rights)"
        )

    if not manifest.weight_files:
        reasons.append("manifest declares no weight files")

    # Per-file structural checks + optional recompute. We still collect file
    # verifications even when an earlier field failed, so the summary is informative.
    file_verifications: list[WeightFileVerification] = []
    verified_count = 0
    recomputed_any = False
    all_present_and_matched = bool(manifest.weight_files)
    seen_paths: set[str] = set()

    for ref in manifest.weight_files:
        path = (ref.path or "").strip()
        declared = (ref.sha256 or "").strip().lower()

        if not path:
            reasons.append("a weight file entry has an empty path")
            all_present_and_matched = False
            continue
        if path in seen_paths:
            reasons.append(f"duplicate weight file path '{path}'")
        seen_paths.add(path)

        if not _SHA256_RE.match(declared):
            reasons.append(
                f"weight file '{path}' has a malformed SHA-256 (expected 64 lowercase hex chars)"
            )
            all_present_and_matched = False
            file_verifications.append(
                WeightFileVerification(
                    path=path,
                    declared_sha256=ref.sha256,
                    verified=False,
                    recomputed_sha256=None,
                    note="malformed declared SHA-256",
                )
            )
            continue

        if weights_root is None:
            all_present_and_matched = False
            file_verifications.append(
                WeightFileVerification(
                    path=path,
                    declared_sha256=declared,
                    verified=False,
                    recomputed_sha256=None,
                    note="declared only; not recomputed (no weights available at this stage)",
                )
            )
            continue

        candidate = Path(weights_root) / path
        if not candidate.is_file():
            all_present_and_matched = False
            file_verifications.append(
                WeightFileVerification(
                    path=path,
                    declared_sha256=declared,
                    verified=False,
                    recomputed_sha256=None,
                    note="weight file not present under weights_root; verification deferred",
                )
            )
            continue

        recomputed = compute_file_sha256(candidate)
        recomputed_any = True
        if recomputed == declared:
            verified_count += 1
            file_verifications.append(
                WeightFileVerification(
                    path=path,
                    declared_sha256=declared,
                    verified=True,
                    recomputed_sha256=recomputed,
                    note="recomputed SHA-256 matches declared",
                )
            )
        else:
            all_present_and_matched = False
            reasons.append(
                f"weight file '{path}' SHA-256 mismatch: declared {declared}, recomputed {recomputed}"
            )
            file_verifications.append(
                WeightFileVerification(
                    path=path,
                    declared_sha256=declared,
                    verified=False,
                    recomputed_sha256=recomputed,
                    note="recomputed SHA-256 does NOT match declared",
                )
            )

    if reasons:
        rejected = _rejected(reasons, model_id=declared_model_id or expected_model_id)
        return ProvenanceSummary(
            status="PROVENANCE_REJECTED",
            model_id=rejected.model_id,
            license_id=manifest.license_id,
            license_recognized=license_recognized,
            source_uri=manifest.source_uri,
            revision=manifest.revision,
            weight_file_count=len(manifest.weight_files),
            verified_file_count=verified_count,
            all_hashes_verified=False,
            manifest_content_digest=manifest.content_digest(),
            notice=rejected.notice,
            reasons=tuple(reasons),
            file_verifications=tuple(file_verifications),
        )

    all_hashes_verified = all_present_and_matched and recomputed_any
    if all_hashes_verified:
        status: ProvenanceStatus = "PROVENANCE_VERIFIED"
        notice = (
            f"Model provenance verified: all {len(manifest.weight_files)} declared weight-file "
            f"SHA-256 digests were recomputed and matched. License "
            f"'{manifest.license_id}' is a recognized open-weight license. CAS Harness "
            "records and checks provenance; it does not grant or adjudicate license rights."
        )
    else:
        status = "PROVENANCE_DECLARED_NOT_VERIFIED"
        notice = (
            f"Model provenance manifest is well-formed and declares "
            f"{len(manifest.weight_files)} weight-file SHA-256 digest(s), but the hashes "
            "have NOT been recomputed against the actual weights at this stage "
            "(verification is deferred to the probe workers that load the weights). Treat "
            f"provenance as declared, not verified. License '{manifest.license_id}' is a "
            "recognized open-weight license."
        )

    return ProvenanceSummary(
        status=status,
        model_id=declared_model_id,
        license_id=manifest.license_id,
        license_recognized=license_recognized,
        source_uri=manifest.source_uri,
        revision=manifest.revision,
        weight_file_count=len(manifest.weight_files),
        verified_file_count=verified_count,
        all_hashes_verified=all_hashes_verified,
        manifest_content_digest=manifest.content_digest(),
        notice=notice,
        reasons=(),
        file_verifications=tuple(file_verifications),
    )


def validate_frontier_provenance(
    *,
    expected_model_id: str,
    manifest: ModelProvenanceManifest | None,
    weights_root: str | Path | None = None,
) -> ProvenanceSummary:
    """Frontier run-gate: raise ``ValueError`` unless provenance is acceptable.

    Acceptable means PROVENANCE_VERIFIED or PROVENANCE_DECLARED_NOT_VERIFIED -- a
    well-formed, identity-matching, open-weight-licensed manifest is enough to
    *create* a frontier run. PROVENANCE_REJECTED (missing/mismatched/unrecognized/
    malformed/hash-mismatch) refuses it. Callers convert this ValueError to HTTP 422.
    """

    summary = summarize_model_provenance(
        manifest=manifest,
        expected_model_id=expected_model_id,
        weights_root=weights_root,
    )
    if summary.status == "PROVENANCE_REJECTED":
        raise ValueError(
            "frontier-scale run refused: invalid model provenance manifest -- "
            + "; ".join(summary.reasons)
            + ". "
            + frontier_provenance_requirement_notice()
        )
    return summary
