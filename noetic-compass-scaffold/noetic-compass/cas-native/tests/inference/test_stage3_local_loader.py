"""Tests for the local Stage 3 loader.

Tests cover the four load-bearing assertions Codex's audit named for the
loader (commit `c4a339b`): the loader (a) loads from the archive path,
(b) verifies hashes, (c) builds the model, (d) fails loudly on any
mismatch.

Happy-path test (`test_load_stage3_local_happy_path_against_real_archive`)
is skipped automatically when the real `D:\\tksCAS-archive\\` is not
present, so CI / fresh checkouts without the archive don't fail. Failure-
path tests run unconditionally — they use tempdirs with carefully-crafted
bad bytes so they don't depend on the real archive.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from cas_native.inference.stage3_local_loader import (
    DEFAULT_ARCHIVE_ROOT,
    ENGLISH_BPE_SHA256,
    STAGE3_CKPT_MANIFEST_SHA256,
    STAGE3_CKPT_SHA256,
    Stage3LocalBundle,
    TOKENIZER_SHA256,
    load_stage3_local,
    verify_archive,
)


# ---------------------------------------------------------------------------
# Helpers — synthesize an archive in tempdir whose hashes match the
# pinned constants. Used by the failure-path tests to set up a "known good"
# baseline and then mutate it.
# ---------------------------------------------------------------------------

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _make_synthetic_archive(tmp: Path) -> Path:
    """Build a fake archive at `tmp` whose files have arbitrary content but
    where we know the sha256 of each. We then PATCH the loader's pinned
    constants in the test so that the synthetic-archive bytes match what
    the loader expects. This lets us test the loader's error paths
    without needing the real 664 MB checkpoint on disk.
    """
    (tmp / "stage_e3_20260513T043823Z").mkdir(parents=True, exist_ok=True)
    (tmp / "stage6_v6_artifacts").mkdir(parents=True, exist_ok=True)

    ckpt_path = tmp / "stage_e3_20260513T043823Z" / "ckpt_final.pt"
    manifest_path = (
        tmp / "stage_e3_20260513T043823Z" / "ckpt_final.pt.manifest.json"
    )
    tokenizer_path = tmp / "stage6_v6_artifacts" / "tokenizer.json"
    bpe_path = tmp / "stage6_v6_artifacts" / "english_bpe.json"

    # Arbitrary bytes — the test computes their hashes and patches the
    # pinned constants to match.
    ckpt_bytes = b"fake checkpoint bytes for testing"
    tokenizer_bytes = b'{"fake": "tokenizer"}'
    bpe_bytes = b'{"fake": "english_bpe"}'

    # Manifest must reference the same hashes in tokenizer_info or the
    # three-way cross-check will fail.
    manifest_obj = {
        "ablation_mode": "e3",
        "config": {
            "d_model": 384,
            "encoder_n_layers": 4, "encoder_n_heads": 6,
            "decoder_n_layers": 6, "decoder_n_heads": 6,
            "max_cas_prefix_len": 192,
        },
        "tokenizer_info": {
            "tokenizer_sha256": _sha256_bytes(tokenizer_bytes),
            "english_bpe_sha256": _sha256_bytes(bpe_bytes),
        },
    }
    manifest_bytes = json.dumps(manifest_obj, sort_keys=True).encode("utf-8")

    ckpt_path.write_bytes(ckpt_bytes)
    manifest_path.write_bytes(manifest_bytes)
    tokenizer_path.write_bytes(tokenizer_bytes)
    bpe_path.write_bytes(bpe_bytes)

    return tmp


def _patch_pins_to_match_synthetic(monkeypatch, tmp: Path) -> None:
    """Override the pinned sha256 constants so they match the synthetic
    archive's actual bytes. Failure-path tests then mutate the archive
    and verify the loader catches the mismatch."""
    import cas_native.inference.stage3_local_loader as mod
    ckpt = (tmp / "stage_e3_20260513T043823Z" / "ckpt_final.pt").read_bytes()
    mani = (
        tmp / "stage_e3_20260513T043823Z" / "ckpt_final.pt.manifest.json"
    ).read_bytes()
    tok = (tmp / "stage6_v6_artifacts" / "tokenizer.json").read_bytes()
    bpe = (tmp / "stage6_v6_artifacts" / "english_bpe.json").read_bytes()
    monkeypatch.setattr(mod, "STAGE3_CKPT_SHA256", _sha256_bytes(ckpt))
    monkeypatch.setattr(mod, "STAGE3_CKPT_MANIFEST_SHA256", _sha256_bytes(mani))
    monkeypatch.setattr(mod, "TOKENIZER_SHA256", _sha256_bytes(tok))
    monkeypatch.setattr(mod, "ENGLISH_BPE_SHA256", _sha256_bytes(bpe))


# ---------------------------------------------------------------------------
# verify_archive — pinned constants present in source (regression pin)
# ---------------------------------------------------------------------------

def test_pinned_hashes_present_in_source():
    """Each load-bearing sha256 from the registry must appear as a module-
    level constant. A refactor that drops one of these is silent unless
    pinned by a test.
    """
    import cas_native.inference.stage3_local_loader as mod
    src = open(mod.__file__, encoding="utf-8").read()
    assert "5ac364e78419ec8591d25120ce9314f87d2c816467fcf9875802d3d831903a88" in src
    assert "28c13127e919097ee3337eab13bcb929c6b104ee5afecd6f7af64e80d05a9dd6" in src
    assert "9c544425c9c08140070b2f3929adef864bbfafb0c00c1d687f2d6b98e0589b9b" in src
    assert "ac4d12a6d26cc1194ea31fee8cdc07d52a0a759964810956b13cafea08a06889" in src


def test_pinned_constants_match_registry_doc():
    """Each pinned sha256 in the loader must appear verbatim in
    `docs/working/candidate_e/checkpoint_archive_registry.md`. This is the
    contract between code and registry; if either drifts, this test
    catches it."""
    from pathlib import Path
    # Test file: tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/
    #            tests/inference/test_stage3_local_loader.py
    # Repo root with docs/ is 5 levels up from the test file.
    registry_path = (
        Path(__file__).resolve().parents[5]
        / "docs" / "working" / "candidate_e"
        / "checkpoint_archive_registry.md"
    )
    registry = registry_path.read_text(encoding="utf-8")
    assert STAGE3_CKPT_SHA256 in registry, "Stage 3 ckpt hash missing from registry"
    assert STAGE3_CKPT_MANIFEST_SHA256 in registry, "ckpt manifest hash missing from registry"
    assert TOKENIZER_SHA256 in registry, "tokenizer hash missing from registry"
    assert ENGLISH_BPE_SHA256 in registry, "english_bpe hash missing from registry"


# ---------------------------------------------------------------------------
# verify_archive — failure paths (run unconditionally)
# ---------------------------------------------------------------------------

def test_verify_raises_when_archive_root_missing(tmp_path):
    """Pointing at a nonexistent dir must raise with a clear message."""
    missing = tmp_path / "does_not_exist"
    with pytest.raises(RuntimeError, match=r"Archive root not found"):
        verify_archive(archive_root=missing)


def test_verify_raises_when_ckpt_missing(tmp_path, monkeypatch):
    """Synthesize a good archive, then delete the checkpoint binary.
    Loader must raise with the checkpoint filename in the message."""
    _make_synthetic_archive(tmp_path)
    _patch_pins_to_match_synthetic(monkeypatch, tmp_path)
    (tmp_path / "stage_e3_20260513T043823Z" / "ckpt_final.pt").unlink()
    with pytest.raises(RuntimeError, match=r"Missing load-bearing file `ckpt_final\.pt`"):
        verify_archive(archive_root=tmp_path)


def test_verify_raises_when_tokenizer_missing(tmp_path, monkeypatch):
    """Symmetric: missing tokenizer must raise with the tokenizer filename."""
    _make_synthetic_archive(tmp_path)
    _patch_pins_to_match_synthetic(monkeypatch, tmp_path)
    (tmp_path / "stage6_v6_artifacts" / "tokenizer.json").unlink()
    with pytest.raises(RuntimeError, match=r"Missing load-bearing file `tokenizer\.json`"):
        verify_archive(archive_root=tmp_path)


def test_verify_raises_on_ckpt_hash_mismatch(tmp_path, monkeypatch):
    """Corrupt the checkpoint by appending a byte. Loader must raise
    naming both expected and actual hash."""
    _make_synthetic_archive(tmp_path)
    _patch_pins_to_match_synthetic(monkeypatch, tmp_path)
    ckpt_path = tmp_path / "stage_e3_20260513T043823Z" / "ckpt_final.pt"
    with ckpt_path.open("ab") as f:
        f.write(b"\x00")  # corrupt
    with pytest.raises(RuntimeError, match=r"sha256 mismatch on `ckpt_final\.pt`"):
        verify_archive(archive_root=tmp_path)


def test_verify_raises_on_tokenizer_manifest_disagreement(tmp_path, monkeypatch):
    """Mutate the manifest so its embedded tokenizer_sha256 disagrees with
    the registry pin (without touching the actual tokenizer file). The
    three-way cross-check must catch this."""
    _make_synthetic_archive(tmp_path)
    _patch_pins_to_match_synthetic(monkeypatch, tmp_path)
    manifest_path = (
        tmp_path / "stage_e3_20260513T043823Z" / "ckpt_final.pt.manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["tokenizer_info"]["tokenizer_sha256"] = "0" * 64  # wrong hash
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    # Manifest content changed → re-pin manifest hash so the manifest-file
    # check passes and the tokenizer-cross-check is what fails.
    import cas_native.inference.stage3_local_loader as mod
    monkeypatch.setattr(
        mod, "STAGE3_CKPT_MANIFEST_SHA256", _sha256_bytes(manifest_bytes),
    )
    with pytest.raises(
        RuntimeError, match=r"tokenizer sha256 disagreement",
    ):
        verify_archive(archive_root=tmp_path)


def test_verify_returns_report_on_happy_synthetic(tmp_path, monkeypatch):
    """Synthetic happy path: the loader's verify_archive must return a
    hash report with all four files, each matching the patched pin."""
    _make_synthetic_archive(tmp_path)
    _patch_pins_to_match_synthetic(monkeypatch, tmp_path)
    report = verify_archive(archive_root=tmp_path)
    assert set(report.keys()) == {
        "ckpt_final.pt", "ckpt_final.pt.manifest.json",
        "tokenizer.json", "english_bpe.json",
    }
    import cas_native.inference.stage3_local_loader as mod
    assert report["ckpt_final.pt"] == mod.STAGE3_CKPT_SHA256
    assert report["tokenizer.json"] == mod.TOKENIZER_SHA256


# ---------------------------------------------------------------------------
# load_stage3_local — happy path against real archive (skipped if absent)
# ---------------------------------------------------------------------------

_REAL_ARCHIVE = DEFAULT_ARCHIVE_ROOT
_REAL_CKPT = (
    _REAL_ARCHIVE / "stage_e3_20260513T043823Z" / "ckpt_final.pt"
)


@pytest.mark.skipif(
    not _REAL_CKPT.exists(),
    reason=(
        f"real Stage 3 archive not present at {_REAL_CKPT}; "
        "skip the heavy happy-path test (~30 sec on CPU)"
    ),
)
def test_load_stage3_local_happy_path_against_real_archive():
    """End-to-end: load against the actual archive, confirm the bundle
    is structurally valid. Runs only when the local archive is present.

    Not a full smoke (no inference); just a "the file paths line up and
    state_dict shape matches" check. Step 3 (one-record local smoke) is
    where actual inference gets exercised.
    """
    bundle = load_stage3_local(device="cpu")
    assert isinstance(bundle, Stage3LocalBundle)
    # Model loaded + in eval mode
    assert bundle.model is not None
    assert not bundle.model.training, "model must be in eval() after load"
    # Tokenizer attached + has BPE merged
    assert bundle.tokenizer is not None
    assert bundle.tokenizer.vocab_size > 0
    # Manifest parsed
    assert bundle.manifest.get("ablation_mode") == "e3", (
        "manifest must report ablation_mode='e3' for the Stage 3 checkpoint"
    )
    # Hash report has all four files
    assert set(bundle.hash_report.keys()) == {
        "ckpt_final.pt", "ckpt_final.pt.manifest.json",
        "tokenizer.json", "english_bpe.json",
    }
    # Each reported hash matches the pinned constant
    assert bundle.hash_report["ckpt_final.pt"] == STAGE3_CKPT_SHA256
    assert bundle.hash_report["ckpt_final.pt.manifest.json"] == STAGE3_CKPT_MANIFEST_SHA256
    assert bundle.hash_report["tokenizer.json"] == TOKENIZER_SHA256
    assert bundle.hash_report["english_bpe.json"] == ENGLISH_BPE_SHA256
