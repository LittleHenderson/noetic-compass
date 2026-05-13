"""Local Stage 3 loader — hash-verified, fails loudly on any mismatch.

Step 2 of the post-Stage-3 integration plan per Codex audit `c4a339b`
(2026-05-13T08:25Z). The trained Stage 3 model lives at
`D:\\tksCAS-archive\\stage_e3_20260513T043823Z\\` (per
`docs/working/candidate_e/checkpoint_archive_registry.md`). This module
builds the bridge from "files on disk" to "loaded model in memory" with
hash gates so we can't silently load a corrupted or wrong checkpoint.

Public surface:
    - `verify_archive(archive_root=...)` — cheap pre-flight; computes sha256
      on the four load-bearing files and cross-checks against the pinned
      constants AND the manifest's embedded tokenizer hashes. Returns a
      hash-verification dict. Raises `RuntimeError` on any mismatch.
    - `load_stage3_local(archive_root=..., device="cpu")` — full happy-path
      load. Verifies, parses the manifest, builds the model with the
      manifest's training config, loads weights with `strict=True`, returns
      a `Stage3LocalBundle`.

Bounded scope (per `decisions.md` 2026-05-13T08:30Z): no inference run, no
CLI surface, no chat REPL touch. Step 3 (one-record smoke) and Step 4
(CAS-input CLI) are separate.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import torch


# ---------------------------------------------------------------------------
# Pinned sha256 constants — must match `docs/working/candidate_e/
# checkpoint_archive_registry.md`. If the registry is updated for any
# load-bearing file, these constants update in lockstep.
# ---------------------------------------------------------------------------

STAGE3_CKPT_SHA256 = (
    "5ac364e78419ec8591d25120ce9314f87d2c816467fcf9875802d3d831903a88"
)
STAGE3_CKPT_MANIFEST_SHA256 = (
    "28c13127e919097ee3337eab13bcb929c6b104ee5afecd6f7af64e80d05a9dd6"
)
TOKENIZER_SHA256 = (
    "9c544425c9c08140070b2f3929adef864bbfafb0c00c1d687f2d6b98e0589b9b"
)
ENGLISH_BPE_SHA256 = (
    "ac4d12a6d26cc1194ea31fee8cdc07d52a0a759964810956b13cafea08a06889"
)

# Default archive root (Windows-only D: drive per project convention).
# Tests override this via the `archive_root` arg to point at a tempdir.
DEFAULT_ARCHIVE_ROOT = Path(r"D:\tksCAS-archive")


@dataclass
class Stage3LocalBundle:
    """Everything Step 3+ needs to run inference against the Stage 3 model.

    Fields:
        model: a `_SimplexMVPModel` instance in eval mode, weights loaded.
        tokenizer: a `HybridCASTokenizer` with the english_bpe attached.
        english_bpe_path: the local archive path to the english_bpe.json
            (the tokenizer holds it via `with_english_bpe`, but downstream
            consumers sometimes need the raw path).
        manifest: the parsed `ckpt_final.pt.manifest.json` contents
            (training config, lineage, tokenizer hashes).
        hash_report: dict mapping load-bearing filename → sha256 string,
            computed at load time. Useful for downstream "what did we
            actually load" logging.
    """
    model: Any
    tokenizer: Any
    english_bpe_path: Path
    manifest: dict[str, Any]
    hash_report: dict[str, str]


def _sha256_file(path: Path) -> str:
    """Compute hex sha256 of a file. Streams in 1 MB chunks so the 664 MB
    checkpoint doesn't load into memory."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _expected_files(archive_root: Path) -> dict[str, tuple[Path, str]]:
    """Return the four load-bearing files keyed by short name:
    (absolute path, expected sha256)."""
    stage3_dir = archive_root / "stage_e3_20260513T043823Z"
    tokenizer_dir = archive_root / "stage6_v6_artifacts"
    return {
        "ckpt_final.pt": (
            stage3_dir / "ckpt_final.pt", STAGE3_CKPT_SHA256,
        ),
        "ckpt_final.pt.manifest.json": (
            stage3_dir / "ckpt_final.pt.manifest.json",
            STAGE3_CKPT_MANIFEST_SHA256,
        ),
        "tokenizer.json": (
            tokenizer_dir / "tokenizer.json", TOKENIZER_SHA256,
        ),
        "english_bpe.json": (
            tokenizer_dir / "english_bpe.json", ENGLISH_BPE_SHA256,
        ),
    }


def verify_archive(archive_root: Optional[Path] = None) -> dict[str, str]:
    """Verify the four load-bearing files exist and their sha256 hashes
    match the pinned constants AND the manifest's embedded tokenizer hashes.

    Args:
        archive_root: defaults to `DEFAULT_ARCHIVE_ROOT`. Tests override
            with a tempdir.

    Returns:
        Mapping short-filename → computed sha256 (hex string). All four
        load-bearing files are present in the dict, and each value equals
        the pinned constant for that file.

    Raises:
        RuntimeError: if any file is missing, any hash mismatches, or the
            manifest's `tokenizer_info.*_sha256` fields disagree with the
            pinned constants. Error message names the specific file and
            the expected vs actual hash so debugging is direct.
    """
    root = Path(archive_root) if archive_root else DEFAULT_ARCHIVE_ROOT
    if not root.exists():
        raise RuntimeError(
            f"Archive root not found at {root!s}. The Stage 3 model and "
            f"tokenizer artifacts are expected to live under "
            f"`stage_e3_20260513T043823Z/` and `stage6_v6_artifacts/`. "
            f"See docs/working/candidate_e/checkpoint_archive_registry.md."
        )

    expected = _expected_files(root)
    report: dict[str, str] = {}

    for short_name, (path, expected_hash) in expected.items():
        if not path.exists():
            raise RuntimeError(
                f"Missing load-bearing file `{short_name}` at expected "
                f"path {path!s}. Cannot load Stage 3 model. Restore from "
                f"pod source (per registry) or re-run the local backup."
            )
        actual = _sha256_file(path)
        if actual != expected_hash:
            raise RuntimeError(
                f"sha256 mismatch on `{short_name}` at {path!s}.\n"
                f"  expected: {expected_hash}\n"
                f"  actual:   {actual}\n"
                f"This means either the file was corrupted in transit / "
                f"on disk, OR the registry's pinned hash is stale "
                f"relative to the file. Investigate before loading."
            )
        report[short_name] = actual

    # Three-way cross-check: the trainer manifest embeds the tokenizer +
    # english_bpe sha256s it was trained against. Those MUST match our
    # pinned constants AND the just-computed file hashes. If they differ,
    # the registry pin or the manifest embed has drifted.
    manifest_path = expected["ckpt_final.pt.manifest.json"][0]
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    tok_info = manifest.get("tokenizer_info", {})
    manifest_tok_sha = tok_info.get("tokenizer_sha256")
    manifest_bpe_sha = tok_info.get("english_bpe_sha256")
    if manifest_tok_sha != TOKENIZER_SHA256:
        raise RuntimeError(
            f"tokenizer sha256 disagreement between registry pin and "
            f"trainer manifest. "
            f"registry pin: {TOKENIZER_SHA256!r}, "
            f"manifest embed: {manifest_tok_sha!r}. "
            f"The trained model expects the manifest-embedded tokenizer."
        )
    if manifest_bpe_sha != ENGLISH_BPE_SHA256:
        raise RuntimeError(
            f"english_bpe sha256 disagreement between registry pin and "
            f"trainer manifest. "
            f"registry pin: {ENGLISH_BPE_SHA256!r}, "
            f"manifest embed: {manifest_bpe_sha!r}."
        )

    return report


def load_stage3_local(
    archive_root: Optional[Path] = None,
    device: str = "cpu",
) -> Stage3LocalBundle:
    """Full happy-path local load. Verifies hashes, parses manifest, builds
    the model with the manifest's training config, loads weights with
    strict=True, returns a `Stage3LocalBundle` ready for inference.

    Args:
        archive_root: defaults to `DEFAULT_ARCHIVE_ROOT`.
        device: torch device string; defaults to "cpu" because Step 2 is
            local-laptop scope. Step 3+ may pass "cuda:0".

    Raises:
        RuntimeError: same conditions as `verify_archive` plus
            `RuntimeError` from `load_checkpoint` if the state_dict shape
            disagrees with the rebuilt model architecture (strict=True).
    """
    hash_report = verify_archive(archive_root)
    root = Path(archive_root) if archive_root else DEFAULT_ARCHIVE_ROOT
    expected = _expected_files(root)

    ckpt_path = expected["ckpt_final.pt"][0]
    manifest_path = expected["ckpt_final.pt.manifest.json"][0]
    tokenizer_path = expected["tokenizer.json"][0]
    english_bpe_path = expected["english_bpe.json"][0]

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Build the model using the training config recorded in the manifest.
    # Mirrors `evaluation/evaluate_candidate_e_stage2.py:build_model_and_load`
    # — the canonical load path.
    from cas_native.training.train_simplex_mvp import (
        build_simplex_mvp_model, SimplexTrainConfig, DEFAULT_LOSS_WEIGHTS,
    )
    from cas_native.training.simplex_checkpoint import load_checkpoint
    from cas_native.training.tokenizer import HybridCASTokenizer

    cfg_dict = manifest.get("config", {})
    cfg = SimplexTrainConfig(
        data_path="", output_dir="",
        d_model=int(cfg_dict.get("d_model", 384)),
        encoder_n_layers=int(cfg_dict.get("encoder_n_layers", 4)),
        decoder_n_layers=int(cfg_dict.get("decoder_n_layers", 6)),
        encoder_n_heads=int(cfg_dict.get("encoder_n_heads", 6)),
        decoder_n_heads=int(cfg_dict.get("decoder_n_heads", 6)),
        batch_size=1,
        max_cas_prefix_len=int(cfg_dict.get("max_cas_prefix_len", 192)),
    )
    cfg.loss_weights = dict(DEFAULT_LOSS_WEIGHTS)

    tokenizer = HybridCASTokenizer.load(str(tokenizer_path))
    tokenizer = tokenizer.with_english_bpe(str(english_bpe_path))
    vocab_size = int(tokenizer.vocab_size)

    model = build_simplex_mvp_model(
        cfg, vocab_size=vocab_size, vocab_size_english=vocab_size,
    )
    load_checkpoint(
        str(ckpt_path), model=model, optimizer=None,
        map_location="cpu", strict=True, restore_rng=False,
    )
    model = model.to(torch.device(device))
    model.eval()

    return Stage3LocalBundle(
        model=model,
        tokenizer=tokenizer,
        english_bpe_path=english_bpe_path,
        manifest=manifest,
        hash_report=hash_report,
    )
