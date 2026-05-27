"""Tests for the v1 Evidence Packet routes.

Covers:

* 200 happy path on the dev-fixture trace id.
* 404 for an unknown trace id.
* All 7 SPEC sections present and shaped per SPEC §4.
* All four claim_level kinds present.
* Verify happy path — re-hash an existing on-disk file and confirm match
  semantics (matches hashlib's digest; ``match`` reflects expected==actual).
* Verify with a missing file — surfaced as ``file not found locally``.
* Auth gating — both endpoints require Bearer auth.

These tests use the project's standard ``client`` and ``auth_headers``
fixtures from ``tests/conftest.py``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


_DEV_TRACE_ID = "dev_example_001"
_CAS_HARNESS_REFERENCE_TRACE_ID = "cas_harness_reference_accept_001"
_S7_F28_TRACE_ID = "s7-f28-balanced-bridge-gpt-neox-20b-20260526"
_KNOWN_CHECKPOINT_DIR = (
    Path(__file__).resolve().parents[1]
    / ".tmp"
    / "stage4_track1_realdata_smoke_claude"
)


# ---------------------------------------------------------------------------
# Auth gating.
# ---------------------------------------------------------------------------


def test_evidence_get_requires_auth(client):
    resp = client.get(f"/evidence/{_DEV_TRACE_ID}")
    assert resp.status_code == 401


def test_evidence_verify_requires_auth(client):
    resp = client.post(f"/evidence/{_DEV_TRACE_ID}/verify")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET happy path — dev fixture.
# ---------------------------------------------------------------------------


def test_evidence_get_dev_fixture_200(client, auth_headers):
    resp = client.get(f"/evidence/{_DEV_TRACE_ID}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Schema-version and identity (SPEC §4).
    assert body["schema_version"] == "evidence_packet.v1"
    assert body["trace_id"] == _DEV_TRACE_ID
    assert body["generated_at"].endswith("Z"), "generated_at must be ISO-8601 UTC"


def test_evidence_get_dev_fixture_has_all_seven_sections(client, auth_headers):
    resp = client.get(f"/evidence/{_DEV_TRACE_ID}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Section 1: Input.
    assert body["input"]["text"]
    # Section 2: CAS expression.
    assert body["cas_expression"]["compiler_valid"] is True
    # Section 3: Output.
    assert body["output"]["text"]
    # Section 4: Copy / slot trace.
    assert isinstance(body["copy_slot_trace"], list) and body["copy_slot_trace"]
    # Section 5: Provenance.
    assert "provenance" in body
    assert body["provenance"]["model_checkpoint_id"]
    assert body["provenance"]["code_commit_sha"]
    # Section 6: Hashes.
    assert "hashes" in body
    assert "on_disk_paths" in body["hashes"]
    # Section 7: Claim levels.
    assert isinstance(body["claim_levels"], list) and body["claim_levels"]


def test_copy_slot_trace_matches_spec_shape(client, auth_headers):
    """SPEC §4: each copy_slot_trace row has role / name / copied /
    source_token_index / target_token_index / claim_level."""
    resp = client.get(f"/evidence/{_DEV_TRACE_ID}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()

    valid_roles = {
        "noetic",
        "domain",
        "drive",
        "register",
        "stage_var",
        "omega",
        "identifier",
    }
    for row in body["copy_slot_trace"]:
        assert row["role"] in valid_roles, f"unknown role: {row['role']}"
        assert "name" in row
        assert "copied" in row
        assert "claim_level" in row


def test_hashes_on_disk_paths_uses_spec_keys(client, auth_headers):
    """SPEC §4: on_disk_paths uses {weights_path, tokenizer_path, corpus_path,
    english_bpe_path?} — NOT keys named for the hashes themselves."""
    resp = client.get(f"/evidence/{_DEV_TRACE_ID}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()

    on_disk_paths = body["hashes"]["on_disk_paths"]
    allowed = {"weights_path", "tokenizer_path", "english_bpe_path", "corpus_path"}
    for k in on_disk_paths.keys():
        assert k in allowed, f"on_disk_paths key {k!r} not in SPEC's allowed set"
    assert "weights_path" in on_disk_paths


def test_evidence_get_dev_fixture_covers_all_four_claim_levels(client, auth_headers):
    resp = client.get(f"/evidence/{_DEV_TRACE_ID}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    seen = {row["level"] for row in body["claim_levels"]}
    expected = {
        "cas_hard_trace",
        "source_copy_evidence",
        "derived_trace",
        "neural_attribution_estimate",
    }
    missing = expected - seen
    assert not missing, f"claim_levels missing kinds: {missing}; got {seen}"


def test_evidence_claim_rows_separate_evidence_type_from_support(client, auth_headers):
    resp = client.get(f"/evidence/{_DEV_TRACE_ID}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    allowed_support = {
        "supported",
        "partially_supported",
        "unsupported",
        "contradicted",
        "not_applicable",
        "unknown",
    }
    for row in body["claim_levels"]:
        assert "level" in row, "level is evidence type, not claim support"
        assert "support_status" in row
        assert row["support_status"] in allowed_support
        assert "support_rationale" in row


def test_evidence_get_dev_fixture_caveats_flag_dev_mode(client, auth_headers):
    resp = client.get(f"/evidence/{_DEV_TRACE_ID}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["caveats"], "dev fixture must declare caveats"
    assert any("dev fixture" in c.lower() for c in body["caveats"])


# ---------------------------------------------------------------------------
# GET 404.
# ---------------------------------------------------------------------------


def test_evidence_get_unknown_trace_id_404(client, auth_headers):
    resp = client.get(
        "/evidence/this_trace_id_does_not_exist_xyz_42", headers=auth_headers
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "trace_id not found"


def test_evidence_get_cas_harness_reference_packet_has_verifier_contract(
    client,
    auth_headers,
):
    resp = client.get(f"/evidence/{_CAS_HARNESS_REFERENCE_TRACE_ID}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["schema_version"] == "cas_harness_evidence_packet_v1"
    assert body["trace_id"] == _CAS_HARNESS_REFERENCE_TRACE_ID
    assert body["model"]["model_key"] == "EleutherAI/pythia-160m"
    assert body["readout"]["label"] == "F1"
    assert body["ablation"]["status"] == "present"
    assert body["matched_controls"]["status"] == "present"
    assert body["verification"]["accepted"] is True
    assert body["verification"]["mode_profile"]["accepted_accuracy"] == 0.9816
    assert body["generation_readiness"]["generation_readiness"] == "allow"
    assert any("stage19" in report for report in body["provenance"]["source_reports"])
    assert any("stage20" in report for report in body["provenance"]["source_reports"])


def test_evidence_get_s7_f28_packet_from_working_docs(client, auth_headers):
    resp = client.get(f"/evidence/{_S7_F28_TRACE_ID}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["schema_version"] == "cas_harness_evidence_packet_v1"
    assert body["trace_id"] == _S7_F28_TRACE_ID
    assert body["provenance"]["method_label"] == "S7-F28-BALANCED-BRIDGE"
    assert body["model"]["name"] == "EleutherAI/gpt-neox-20b"
    assert body["readout"]["heldout_accuracy"] == 0.868622
    assert body["ablation"]["label_specific_cover_ablation"]["drop_from_clean"] == 0.124424
    assert body["output"]["probe_readable"]["delta_vs_none_mean"] == 0.596413
    assert body["verification"]["explicit_verifier_decision"]["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["verification"]["explicit_verifier_decision"]["confidence"] == 0.803571
    assert body["verification"]["packet_integrity"]["status"] == "present_only_not_verifier_clean"
    assert any("Packet proof is present-only" in caveat for caveat in body["caveats"])


def test_evidence_verify_s7_f28_packet_is_present_only_not_clean(client, auth_headers):
    resp = client.post(f"/evidence/{_S7_F28_TRACE_ID}/verify", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["trace_id"] == _S7_F28_TRACE_ID
    assert body["overall"] == "partial_mismatch"

    corpus_check = next(
        (check for check in body["checks"] if check["artifact"] == "corpus"),
        None,
    )
    assert corpus_check is not None
    assert corpus_check["match"] is False
    assert corpus_check["actual"] is None
    assert corpus_check["notes"] in {
        "path is outside allowed roots",
        "file not found locally",
    }

    code_commit_check = next(
        (check for check in body["checks"] if check["artifact"] == "code_commit"),
        None,
    )
    assert code_commit_check is not None
    assert code_commit_check["match"] is False
    assert "HEAD has moved" in code_commit_check["notes"]


def test_evidence_verify_cas_harness_reference_packet_is_unavailable_not_mismatch(
    client,
    auth_headers,
):
    resp = client.post(
        f"/evidence/{_CAS_HARNESS_REFERENCE_TRACE_ID}/verify",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["trace_id"] == _CAS_HARNESS_REFERENCE_TRACE_ID
    assert body["checks"], "code_commit check should still surface provenance"
    assert body["overall"] in {"all_match", "partial_mismatch", "unable_to_verify"}
    assert not any(
        check["artifact"] in {"weights", "tokenizer"} and check["notes"] == "no on_disk_paths entry for this artifact"
        for check in body["checks"]
    )


# ---------------------------------------------------------------------------
# Verify happy path — sha256 a known existing file and confirm match.
# ---------------------------------------------------------------------------


def _hashlib_sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.mark.skipif(
    not (_KNOWN_CHECKPOINT_DIR / "model_final.pt").is_file(),
    reason="stage4 smoke checkpoint not present on this host; verify path can't be tested",
)
def test_evidence_verify_streams_sha256_over_real_file(client, auth_headers):
    """Verify endpoint must stream sha256 over model_final.pt and report the
    live digest as ``actual``, with ``match`` reflecting whether it equals
    the manifest's recorded ``weights_sha``.

    We assert two invariants that must hold on any host where the file
    exists:

    1. ``actual`` matches ``hashlib.sha256`` computed over the same bytes.
    2. ``match`` equals ``expected == actual`` — i.e., the comparison logic
       is consistent, regardless of whether the recorded SHA agrees with
       the on-disk file (which is environmental).
    """
    manifest = json.loads(
        (_KNOWN_CHECKPOINT_DIR / "checkpoint_manifest.json").read_text(encoding="utf-8")
    )
    expected_weights_sha = manifest["weights_sha"]
    independent_sha = _hashlib_sha256_of(_KNOWN_CHECKPOINT_DIR / "model_final.pt")

    resp = client.post(
        f"/evidence/{_DEV_TRACE_ID}/verify", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["trace_id"] == _DEV_TRACE_ID
    assert body["checks"], "must produce at least one check row"

    weights_check = next(
        (c for c in body["checks"] if c["artifact"] == "weights"), None
    )
    assert weights_check is not None, "weights check missing"
    assert weights_check["expected"] == expected_weights_sha
    assert (
        weights_check["actual"] == independent_sha
    ), "endpoint's streaming sha256 must match hashlib's digest of the same file"
    assert weights_check["match"] == (
        weights_check["actual"] == weights_check["expected"]
    ), "match flag must reflect expected==actual"


@pytest.mark.skipif(
    not (_KNOWN_CHECKPOINT_DIR / "model_final.pt").is_file(),
    reason="stage4 smoke checkpoint not present on this host",
)
def test_evidence_verify_overall_field_is_present(client, auth_headers):
    resp = client.post(
        f"/evidence/{_DEV_TRACE_ID}/verify", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall"] in {"all_match", "partial_mismatch", "unable_to_verify"}


def test_evidence_verify_artifact_names_match_spec(client, auth_headers):
    """SPEC §6: artifact ∈ {weights, tokenizer, english_bpe, corpus, code_commit}."""
    resp = client.post(
        f"/evidence/{_DEV_TRACE_ID}/verify", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    allowed = {"weights", "tokenizer", "english_bpe", "corpus", "code_commit"}
    for c in body["checks"]:
        assert c["artifact"] in allowed, f"unknown artifact name: {c['artifact']!r}"


# ---------------------------------------------------------------------------
# Verify with a missing file — surfaced as ``file not found locally``.
# ---------------------------------------------------------------------------


def test_evidence_verify_handles_missing_file(client, auth_headers, monkeypatch):
    """When an on_disk_paths entry points to a path inside the allowed roots
    that doesn't exist on this host, the check is surfaced with
    ``match=False`` and ``notes='file not found locally'``.
    """
    from api.routes import evidence as evidence_route

    # Patch the dev-fixture builder to point at a path inside the scaffold
    # root that doesn't exist, so we exercise the missing-file branch (not
    # the outside-allowed-roots branch — that is tested separately).
    real_builder = evidence_route._dev_fixture_packet
    scaffold_root = evidence_route._scaffold_root().resolve()

    def _patched_builder():
        packet = real_builder()
        packet.hashes["weights_sha"] = "deadbeef" * 8
        packet.hashes["tokenizer_hash"] = "cafebabe" * 8
        packet.hashes["on_disk_paths"] = {
            "weights_path": str(scaffold_root / ".tmp" / "no_such_dir" / "model_final.pt"),
            "tokenizer_path": str(scaffold_root / ".tmp" / "no_such_dir" / "tokenizer.json"),
        }
        # Drop optional keys so they don't generate extra "no_path" checks.
        packet.hashes.pop("english_bpe_hash", None)
        packet.hashes.pop("corpus_sha256", None)
        return packet

    monkeypatch.setattr(evidence_route, "_dev_fixture_packet", _patched_builder)

    resp = client.post(
        f"/evidence/{_DEV_TRACE_ID}/verify", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    weights_check = next(
        (c for c in body["checks"] if c["artifact"] == "weights"), None
    )
    assert weights_check is not None
    assert weights_check["match"] is False
    assert weights_check["notes"] == "file not found locally"


def test_evidence_verify_rejects_paths_outside_allowed_roots(
    client, auth_headers, monkeypatch
):
    """Paths that resolve outside the project / scaffold roots are rejected
    before any bytes are read. Defence-in-depth: the packet writer is
    trusted, but the verify endpoint never reads arbitrary host files.
    """
    from api.routes import evidence as evidence_route

    real_builder = evidence_route._dev_fixture_packet

    def _patched_builder():
        packet = real_builder()
        packet.hashes["weights_sha"] = "deadbeef" * 8
        packet.hashes["on_disk_paths"] = {
            # Absolute path outside both project root and scaffold root.
            "weights_path": "/etc/hosts",
        }
        packet.hashes.pop("tokenizer_hash", None)
        packet.hashes.pop("english_bpe_hash", None)
        packet.hashes.pop("corpus_sha256", None)
        return packet

    monkeypatch.setattr(evidence_route, "_dev_fixture_packet", _patched_builder)

    resp = client.post(
        f"/evidence/{_DEV_TRACE_ID}/verify", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    weights_check = next(
        (c for c in body["checks"] if c["artifact"] == "weights"), None
    )
    assert weights_check is not None
    assert weights_check["match"] is False
    assert weights_check["actual"] is None
    assert weights_check["notes"] == "path is outside allowed roots"


def test_evidence_verify_unknown_trace_id_404(client, auth_headers):
    resp = client.post(
        "/evidence/this_trace_id_does_not_exist_xyz_42/verify",
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Pure-function sanity check on the sha256 streamer.
# ---------------------------------------------------------------------------


def test_sha256_streamer_matches_hashlib(tmp_path):
    from api.routes.evidence import _sha256_file

    payload = b"evidence packet v1 sha256 stream test" * 32
    p = tmp_path / "blob.bin"
    p.write_bytes(payload)

    expected = hashlib.sha256(payload).hexdigest()
    assert _sha256_file(p) == expected


def test_sha256_streamer_returns_none_on_missing(tmp_path):
    from api.routes.evidence import _sha256_file

    assert _sha256_file(tmp_path / "nope.bin") is None


def test_path_helpers_tolerate_shallow_deploy_paths(monkeypatch, tmp_path):
    from api.routes import evidence as evidence_route

    deployed_file = tmp_path / "api" / "routes" / "evidence.py"
    deployed_file.parent.mkdir(parents=True)
    deployed_file.write_text("# deployed path sentinel\n", encoding="utf-8")
    monkeypatch.setattr(evidence_route, "__file__", str(deployed_file))

    assert evidence_route._project_root().exists()
    assert evidence_route._scaffold_root().exists()


# ---------------------------------------------------------------------------
# Packet builder exposed at module level.
# ---------------------------------------------------------------------------


def test_build_packet_for_trace_dev_fixture_returns_packet():
    from api.routes.evidence import (
        EvidencePacket,
        build_packet_for_trace,
    )

    packet = build_packet_for_trace(_DEV_TRACE_ID)
    assert isinstance(packet, EvidencePacket)
    assert packet.trace_id == _DEV_TRACE_ID
    assert packet.schema_version == "evidence_packet.v1"


def test_build_packet_for_trace_dev_fixture_falls_back_on_internal_error(monkeypatch):
    """The example Evidence Packet must never 500 on deployment hosts that
    lack local scratch artifacts. If fixture assembly crashes, the dev id
    returns a static, caveated packet instead.
    """
    from api.routes import evidence as evidence_route

    def _boom():
        raise RuntimeError("simulated fixture host mismatch")

    monkeypatch.setattr(evidence_route, "_dev_fixture_packet", _boom)

    packet = evidence_route.build_packet_for_trace(_DEV_TRACE_ID)
    assert packet.trace_id == _DEV_TRACE_ID
    assert packet.provenance["model_checkpoint_id"] == "dev_fixture_fallback"
    assert packet.hashes["on_disk_paths"] == {}
    assert any("fallback" in c.lower() for c in packet.caveats or [])


def test_build_packet_for_trace_unknown_raises_filenotfound():
    from api.routes.evidence import build_packet_for_trace

    with pytest.raises(FileNotFoundError):
        build_packet_for_trace("this_does_not_exist_xyz")
