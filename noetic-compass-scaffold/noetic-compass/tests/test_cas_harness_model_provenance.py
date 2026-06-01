"""Unit tests for the frontier model-provenance gate (frontier run-gate 5).

These exercise the honesty contract directly at the service layer:

* A missing manifest, an identity mismatch, an unrecognized license, a malformed
  digest, or a recomputed-hash mismatch is ``PROVENANCE_REJECTED`` and the
  frontier validator raises (callers turn that into HTTP 422).
* A well-formed, identity-matching, open-weight-licensed manifest whose hashes
  have only been *declared* (no weights on disk yet) is
  ``PROVENANCE_DECLARED_NOT_VERIFIED`` -- enough to create a run, never a verdict.
* Only when a SHA-256 is recomputed from real bytes and matches do we reach
  ``PROVENANCE_VERIFIED``.
"""

from __future__ import annotations

import hashlib

import pytest

from api.services.cas_harness_model_provenance import (
    ModelProvenanceManifest,
    WeightFileRef,
    compute_file_sha256,
    is_recognized_open_weight_license,
    normalize_license_id,
    summarize_model_provenance,
    validate_frontier_provenance,
)

_VALID_HASH = "a" * 64
_OTHER_HASH = "b" * 64


def _manifest(
    *,
    model_id: str = "meta-llama/Llama-3.1-405B",
    source_uri: str = "https://huggingface.co/meta-llama/Llama-3.1-405B",
    license_id: str = "llama3.1",
    weight_files: tuple[WeightFileRef, ...] | None = None,
    revision: str | None = "main",
) -> ModelProvenanceManifest:
    if weight_files is None:
        weight_files = (
            WeightFileRef(path="model-00001-of-00002.safetensors", sha256=_VALID_HASH),
            WeightFileRef(path="model-00002-of-00002.safetensors", sha256=_OTHER_HASH),
        )
    return ModelProvenanceManifest(
        model_id=model_id,
        source_uri=source_uri,
        license_id=license_id,
        weight_files=weight_files,
        revision=revision,
    )


def test_missing_manifest_is_rejected():
    summary = summarize_model_provenance(
        manifest=None, expected_model_id="meta-llama/Llama-3.1-405B"
    )
    assert summary.status == "PROVENANCE_REJECTED"
    assert summary.accepted is False
    assert any("no model provenance manifest" in r for r in summary.reasons)


def test_well_formed_manifest_without_weights_is_declared_not_verified():
    manifest = _manifest()
    summary = summarize_model_provenance(
        manifest=manifest, expected_model_id="meta-llama/Llama-3.1-405B"
    )
    assert summary.status == "PROVENANCE_DECLARED_NOT_VERIFIED"
    assert summary.accepted is True
    assert summary.license_recognized is True
    assert summary.weight_file_count == 2
    assert summary.verified_file_count == 0
    assert summary.all_hashes_verified is False
    # Honest notice: declared, NOT verified.
    assert "NOT been recomputed" in summary.notice
    # Each declared file is carried through, marked unverified.
    assert len(summary.file_verifications) == 2
    assert all(v.verified is False for v in summary.file_verifications)
    assert all(v.recomputed_sha256 is None for v in summary.file_verifications)


def test_model_id_mismatch_is_rejected():
    manifest = _manifest(model_id="someone-else/Other-Model")
    summary = summarize_model_provenance(
        manifest=manifest, expected_model_id="meta-llama/Llama-3.1-405B"
    )
    assert summary.status == "PROVENANCE_REJECTED"
    assert any("does not match the requested" in r for r in summary.reasons)


def test_unrecognized_license_is_rejected():
    manifest = _manifest(license_id="proprietary-closed-weights")
    summary = summarize_model_provenance(
        manifest=manifest, expected_model_id="meta-llama/Llama-3.1-405B"
    )
    assert summary.status == "PROVENANCE_REJECTED"
    assert summary.license_recognized is False
    assert any("not a recognized open-weight license" in r for r in summary.reasons)


def test_empty_source_uri_is_rejected():
    manifest = _manifest(source_uri="   ")
    summary = summarize_model_provenance(
        manifest=manifest, expected_model_id="meta-llama/Llama-3.1-405B"
    )
    assert summary.status == "PROVENANCE_REJECTED"
    assert any("source_uri is empty" in r for r in summary.reasons)


def test_no_weight_files_is_rejected():
    manifest = _manifest(weight_files=())
    summary = summarize_model_provenance(
        manifest=manifest, expected_model_id="meta-llama/Llama-3.1-405B"
    )
    assert summary.status == "PROVENANCE_REJECTED"
    assert any("no weight files" in r for r in summary.reasons)


def test_malformed_sha256_is_rejected():
    manifest = _manifest(
        weight_files=(
            WeightFileRef(path="model.safetensors", sha256="not-a-real-hash"),
        )
    )
    summary = summarize_model_provenance(
        manifest=manifest, expected_model_id="meta-llama/Llama-3.1-405B"
    )
    assert summary.status == "PROVENANCE_REJECTED"
    assert any("malformed SHA-256" in r for r in summary.reasons)


def test_duplicate_weight_path_is_rejected():
    manifest = _manifest(
        weight_files=(
            WeightFileRef(path="model.safetensors", sha256=_VALID_HASH),
            WeightFileRef(path="model.safetensors", sha256=_OTHER_HASH),
        )
    )
    summary = summarize_model_provenance(
        manifest=manifest, expected_model_id="meta-llama/Llama-3.1-405B"
    )
    assert summary.status == "PROVENANCE_REJECTED"
    assert any("duplicate weight file path" in r for r in summary.reasons)


def test_recomputed_match_is_verified(tmp_path):
    # Write two real files and declare their true SHA-256.
    contents = {
        "model-00001-of-00002.safetensors": b"the quick brown fox",
        "model-00002-of-00002.safetensors": b"jumps over the lazy dog",
    }
    refs = []
    for name, data in contents.items():
        (tmp_path / name).write_bytes(data)
        true_hash = hashlib.sha256(data).hexdigest()
        refs.append(WeightFileRef(path=name, sha256=true_hash, size_bytes=len(data)))

    manifest = _manifest(weight_files=tuple(refs))
    summary = summarize_model_provenance(
        manifest=manifest,
        expected_model_id="meta-llama/Llama-3.1-405B",
        weights_root=tmp_path,
    )
    assert summary.status == "PROVENANCE_VERIFIED"
    assert summary.accepted is True
    assert summary.all_hashes_verified is True
    assert summary.verified_file_count == 2
    assert all(v.verified for v in summary.file_verifications)
    assert all(v.recomputed_sha256 is not None for v in summary.file_verifications)


def test_recomputed_mismatch_is_rejected(tmp_path):
    name = "model.safetensors"
    (tmp_path / name).write_bytes(b"real bytes on disk")
    # Declare a DIFFERENT (but well-formed) hash than the bytes actually hash to.
    manifest = _manifest(
        weight_files=(WeightFileRef(path=name, sha256=_VALID_HASH),)
    )
    summary = summarize_model_provenance(
        manifest=manifest,
        expected_model_id="meta-llama/Llama-3.1-405B",
        weights_root=tmp_path,
    )
    assert summary.status == "PROVENANCE_REJECTED"
    assert any("SHA-256 mismatch" in r for r in summary.reasons)
    # The recomputed value is surfaced honestly in the per-file record.
    mismatch = next(v for v in summary.file_verifications if v.path == name)
    assert mismatch.verified is False
    assert mismatch.recomputed_sha256 == compute_file_sha256(tmp_path / name)


def test_missing_file_under_weights_root_defers_to_declared(tmp_path):
    # weights_root provided, but the declared file isn't there: not a mismatch,
    # just deferred -- so the manifest is still acceptable (declared-not-verified).
    manifest = _manifest(
        weight_files=(WeightFileRef(path="absent.safetensors", sha256=_VALID_HASH),)
    )
    summary = summarize_model_provenance(
        manifest=manifest,
        expected_model_id="meta-llama/Llama-3.1-405B",
        weights_root=tmp_path,
    )
    assert summary.status == "PROVENANCE_DECLARED_NOT_VERIFIED"
    assert summary.accepted is True
    deferred = summary.file_verifications[0]
    assert deferred.verified is False
    assert "deferred" in deferred.note


def test_validate_frontier_provenance_raises_on_rejected():
    with pytest.raises(ValueError) as exc:
        validate_frontier_provenance(
            expected_model_id="meta-llama/Llama-3.1-405B", manifest=None
        )
    assert "frontier-scale run refused" in str(exc.value)
    assert "model provenance" in str(exc.value)


def test_validate_frontier_provenance_returns_summary_when_acceptable():
    manifest = _manifest()
    summary = validate_frontier_provenance(
        expected_model_id="meta-llama/Llama-3.1-405B", manifest=manifest
    )
    assert summary.status == "PROVENANCE_DECLARED_NOT_VERIFIED"
    assert summary.accepted is True


def test_license_normalization_and_aliases():
    assert normalize_license_id("Apache 2.0") == "apache-2.0"
    assert normalize_license_id("apache2") == "apache-2.0"
    assert normalize_license_id("LLaMA-3.1") == "llama3.1"
    assert is_recognized_open_weight_license("MIT") is True
    assert is_recognized_open_weight_license("Llama 3.3") is True
    assert is_recognized_open_weight_license("totally-made-up") is False


def test_content_digest_is_deterministic_and_sensitive():
    a = _manifest()
    b = _manifest()
    assert a.content_digest() == b.content_digest()
    # Changing any declared field changes the digest.
    c = _manifest(source_uri="https://example.com/other")
    assert c.content_digest() != a.content_digest()
