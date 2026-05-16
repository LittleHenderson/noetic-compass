"""Evidence Packet v1 — provenance + traceability surface.

Stateless GET/POST endpoints that back the Evidence Packet drawer in the
dashboard. Reads on-disk artifacts only; nothing is written.

Schema authority: ``docs/working/evidence_packet_2026_05_15/SPEC.md``.

Two endpoints:

* ``GET  /api/evidence/{trace_id}``        → full ``EvidencePacket`` JSON.
* ``POST /api/evidence/{trace_id}/verify`` → re-hash on-disk artifacts and
  compare against the SHAs recorded in the packet.

The packet is assembled from three sources:

1. The per-trace JSON written by ``traceability_v0`` /
   ``cas_native.trace.generation_trace`` (if present on this host).
2. The checkpoint manifest produced by the training run that authored the
   trace — known good example at
   ``noetic-compass-scaffold/noetic-compass/.tmp/stage4_track1_realdata_smoke_claude/checkpoint_manifest.json``.
3. ``git log`` for the current code commit (or the manifest's
   ``git_commit_sha`` when present).

The endpoint exposes a dev-fixture mode (``trace_id == "dev_example_001"``)
that returns a complete, hand-built packet so Agent C can build the UI
without waiting for real traces to land on this host. The dev fixture is
clearly flagged via ``caveats``.

Claim-level taxonomy (SPEC §2):

* ``cas_hard_trace``           — compiler-validated CAS / supervised slot.
* ``source_copy_evidence``     — pointer/slot copy evidence from source.
* ``derived_trace``            — reconstructed from logs / re-tokenized.
* ``neural_attribution_estimate``
                               — Mode 7 mechanistic attribution data; this
                                 is evidence, not proof.

This module is intentionally side-effect free: no DB, no global state, no
new dependencies. ``hashlib`` (stdlib) is used for sha256.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/evidence", tags=["evidence"])


# ---------------------------------------------------------------------------
# Pydantic models — packet shape and verify-response shape (SPEC §4 + §6).
# ---------------------------------------------------------------------------


class EvidencePacket(BaseModel):
    """The full v1 Evidence Packet.

    Field shape matches SPEC §4 byte-for-field. See the SPEC for source
    provenance of each field.
    """

    schema_version: str = "evidence_packet.v1"
    trace_id: str
    generated_at: str = Field(description="ISO-8601 UTC timestamp the packet was assembled.")

    input: dict[str, Any]
    cas_expression: dict[str, Any] | None = None
    output: dict[str, Any]
    copy_slot_trace: list[dict[str, Any]] | None = None
    provenance: dict[str, Any]
    hashes: dict[str, Any]
    claim_levels: list[dict[str, Any]]
    caveats: list[str] | None = None


class VerifyCheck(BaseModel):
    """One entry in the verify response — one artifact, one comparison.

    ``artifact`` is one of ``weights | tokenizer | english_bpe | corpus | code_commit``
    per SPEC §6.
    """

    artifact: str
    expected: str | None
    actual: str | None
    match: bool
    notes: str | None = None


class VerifyHashesResponse(BaseModel):
    trace_id: str
    verified_at: str
    checks: list[VerifyCheck]
    overall: str  # "all_match" | "partial_mismatch" | "unable_to_verify"


# ---------------------------------------------------------------------------
# Path discovery — paths that are stable across the dev fixture and the real
# packet path are resolved relative to the project root.
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    """Return ``tksCAS/`` — the outer git root.

    Resolved as ``api/routes/evidence.py`` → up 4 → outer repo root.
    """
    return Path(__file__).resolve().parents[4]


def _scaffold_root() -> Path:
    """Return ``noetic-compass-scaffold/noetic-compass/``."""
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Provenance helpers.
# ---------------------------------------------------------------------------


def _now_iso_utc() -> str:
    """Return current UTC time as an ISO-8601 string with second resolution."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_head_sha() -> str | None:
    """Return the current ``git rev-parse HEAD`` SHA, or ``None`` on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(_project_root()),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def _git_head_subject() -> str | None:
    """Return the subject line of the current HEAD commit, or ``None``."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=str(_project_root()),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    subject = result.stdout.strip()
    return subject or None


def _sha256_file(path: Path, chunk_size: int = 1 << 20) -> str | None:
    """Stream sha256 over a file. Returns ``None`` if the file is unreadable.

    Uses a 1 MiB chunk by default to keep RAM bounded for large checkpoints.
    """
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except (FileNotFoundError, PermissionError, OSError):
        return None


# ---------------------------------------------------------------------------
# Path allowlist + size guard — packets carry on-disk paths that the verify
# endpoint will re-hash. The packet writer is trusted, but the route is a
# POST endpoint, so we defense-in-depth: only roots under the project root
# or scaffold root are eligible, and files larger than the size cap are
# refused before any bytes are read.
# ---------------------------------------------------------------------------


# 8 GiB — well above the largest plausible model checkpoint we ship today
# (Stage 4 v0.2 model_final.pt is ~460 MB) but a hard upper bound on the
# work this endpoint will do per request.
_MAX_VERIFY_FILE_BYTES = 8 * 1024 * 1024 * 1024


def _verify_allowed_roots() -> tuple[Path, ...]:
    """Roots under which artifacts may live to be eligible for hashing."""
    return (_project_root().resolve(), _scaffold_root().resolve())


def _path_is_inside(path: Path, root: Path) -> bool:
    """Return ``True`` if ``path`` is the same as, or nested under, ``root``.

    Compatible with Python 3.8+ (avoids ``Path.is_relative_to``).
    """
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_allowed_path(path_str: str) -> tuple[Path | None, str | None]:
    """Resolve ``path_str`` and verify it lives under an allowed root.

    Returns ``(resolved_path, None)`` on success or ``(None, reason)`` if
    the path is outside the allowlist, missing, oversized, or otherwise
    not eligible to be hashed.
    """
    try:
        candidate = Path(path_str).resolve()
    except (OSError, RuntimeError):
        return None, "path could not be resolved"

    if not any(_path_is_inside(candidate, root) for root in _verify_allowed_roots()):
        return None, "path is outside allowed roots"

    if not candidate.is_file():
        return None, "file not found locally"

    try:
        size = candidate.stat().st_size
    except OSError:
        return None, "failed to stat file"
    if size > _MAX_VERIFY_FILE_BYTES:
        return (
            None,
            f"file exceeds max verify size of {_MAX_VERIFY_FILE_BYTES} bytes",
        )

    return candidate, None


# ---------------------------------------------------------------------------
# Trace discovery — looks for a per-trace JSON file in the conventional spots.
# ---------------------------------------------------------------------------


def _candidate_trace_paths(trace_id: str) -> list[Path]:
    """Return on-disk locations to search for a trace artifact, in order."""
    safe = trace_id.replace("/", "_").replace("\\", "_")
    scaffold = _scaffold_root()
    project = _project_root()
    return [
        # SPEC §7 Step 1 — canonical path served to the UI.
        scaffold / "dashboard" / "public" / "traces" / f"{safe}.json",
        # Conventional Mode 7 live capture location.
        scaffold / "cas-native" / "trace" / "captures" / f"{safe}.json",
        # Generation-trace location (per-generate JSON dump).
        scaffold / ".tmp" / "traces" / f"{safe}.json",
        # Project-level capture directory used by Atlas v0 fixtures.
        project / "cas-synthetic" / "data" / "traces" / f"{safe}.json",
        # Worktree-style scratch directory occasionally used by tests.
        scaffold / "cas-native" / "trace" / f"{safe}.json",
    ]


def _load_trace_artifact(trace_id: str) -> dict[str, Any] | None:
    """Load a per-trace JSON dump if one is present in any conventional path."""
    for candidate in _candidate_trace_paths(trace_id):
        if candidate.is_file():
            try:
                with candidate.open("r", encoding="utf-8") as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, OSError):
                continue
    return None


def _load_checkpoint_manifest(manifest_path: Path) -> dict[str, Any] | None:
    if not manifest_path.is_file():
        return None
    try:
        with manifest_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Dev fixture — a complete example packet built from real on-disk files
# (the stage4 smoke checkpoint manifest is real and present on this host).
# ---------------------------------------------------------------------------


_DEV_FIXTURE_TRACE_ID = "dev_example_001"


def _dev_fixture_packet() -> EvidencePacket:
    """Build the dev-fixture packet from real on-disk paths where possible.

    Every claim_level row exercised in tests is present in this fixture:
    ``cas_hard_trace``, ``source_copy_evidence``, ``derived_trace``, and
    ``neural_attribution_estimate``.
    """
    scaffold = _scaffold_root()
    ckpt_dir = scaffold / ".tmp" / "stage4_track1_realdata_smoke_claude"
    manifest_path = ckpt_dir / "checkpoint_manifest.json"
    manifest = _load_checkpoint_manifest(manifest_path) or {}

    weights_path = ckpt_dir / "model_final.pt"
    tokenizer_path = ckpt_dir / "tokenizer.json"
    english_bpe_path = ckpt_dir / "english_bpe.json"

    weights_sha = manifest.get("weights_sha")
    tokenizer_hash = (
        manifest.get("extra", {}).get("tokenizer", {}).get("tokenizer_hash")
    )
    english_bpe_hash = (
        manifest.get("extra", {}).get("tokenizer", {}).get("english_bpe_hash")
    )
    corpus_sha256 = manifest.get("trained_from_corpus_hash")

    code_commit_sha = manifest.get("git_commit_sha") or _git_head_sha() or "unknown"

    # Build a realistic run-command reproducer. Pulled from the manifest's
    # extra block when present, otherwise fall back to a known reproducer.
    run_command = manifest.get("extra", {}).get("run_command") or (
        "python -m cas_native.training.run_stage4 "
        "--corpus cas-synthetic/data/native_nl/wave3_step2_5 "
        "--checkpoint-dir noetic-compass-scaffold/noetic-compass/.tmp/"
        "stage4_track1_realdata_smoke_claude --epochs 1 --limit 100000"
    )

    config_snapshot: dict[str, Any] = {
        "checkpoint_id": manifest.get("checkpoint_id"),
        "code_version": manifest.get("code_version"),
        "schema_version": manifest.get("schema_version"),
        "n_epochs_completed": manifest.get("n_epochs_completed"),
        "n_train_records": manifest.get("n_train_records"),
        "final_loss_total": manifest.get("final_loss_total"),
        "trained_at_timestamp": manifest.get("trained_at_timestamp"),
    }
    curriculum = manifest.get("extra", {}).get("curriculum")
    if curriculum:
        config_snapshot["curriculum"] = curriculum

    # SPEC §4: on_disk_paths uses {weights_path, tokenizer_path, corpus_path}.
    on_disk_paths: dict[str, str] = {
        "weights_path": str(weights_path),
        "tokenizer_path": str(tokenizer_path),
    }
    if english_bpe_path.is_file():
        on_disk_paths["english_bpe_path"] = str(english_bpe_path)

    hashes: dict[str, Any] = {
        "weights_sha": weights_sha,
        "tokenizer_hash": tokenizer_hash,
        "english_bpe_hash": english_bpe_hash,
        "corpus_sha256": corpus_sha256,
        "on_disk_paths": on_disk_paths,
    }

    input_block: dict[str, Any] = {
        "text": "What does ^3^P|A mean and why is it different from ^3^E|f?",
        "user_id": "dev_user",
        "session_id": "dev_session_001",
    }

    cas_expression_block: dict[str, Any] = {
        "text": "^3^P|A",
        "compiler_valid": True,
        "grammar_category": "state_literal",
    }

    output_block: dict[str, Any] = {
        "text": (
            "^3^P|A is principled aversion expressed analytically — you "
            "reason your way to 'this is wrong' in a way that holds across "
            "particulars. ^3^E|f is felt aversion in the evaluative domain — "
            "the visceral 'no' the body lands on before the analysis."
        ),
        "n_tokens": 58,
        "max_new_tokens": 128,
    }

    # SPEC §4 §4.4 — copy_slot_trace[] uses role / name / copied /
    # source_token_index / target_token_index / claim_level.
    copy_slot_trace: list[dict[str, Any]] = [
        {
            "role": "noetic",
            "name": "^3",
            "copied": True,
            "source_token_index": 18,
            "target_token_index": 0,
            "claim_level": "source_copy_evidence",
        },
        {
            "role": "domain",
            "name": "P",
            "copied": True,
            "source_token_index": 21,
            "target_token_index": 2,
            "claim_level": "source_copy_evidence",
        },
        {
            "role": "register",
            "name": "A",
            "copied": True,
            "source_token_index": 23,
            "target_token_index": 4,
            "claim_level": "source_copy_evidence",
        },
        {
            "role": "register",
            "name": "f",
            "copied": True,
            "source_token_index": 53,
            "target_token_index": 24,
            "claim_level": "source_copy_evidence",
        },
    ]

    # SPEC §4 §4.5 — provenance.
    provenance: dict[str, Any] = {
        "model_checkpoint_id": manifest.get("checkpoint_id") or "unknown",
        "checkpoint_label": "Stage 4 Track 1 - realdata smoke (Claude)",
        "code_commit_sha": code_commit_sha,
        "code_commit_summary": _git_head_subject(),
        "run_command": run_command,
        "config_snapshot": config_snapshot,
    }

    claim_levels: list[dict[str, Any]] = [
        {
            "claim": "The expression ^3^P|A is a valid CAS state literal.",
            "level": "cas_hard_trace",
            "rationale": "compile_expression returned valid=true with grammar_category=state_literal - deterministic.",
        },
        {
            "claim": "The output reuses the input's CAS tokens via pointer copy, not paraphrase.",
            "level": "source_copy_evidence",
            "rationale": "Four named slots (^3, P, A, f) have copy=true with named source token indices.",
        },
        {
            "claim": "Run reproducer reconstructed from the checkpoint manifest's extra block.",
            "level": "derived_trace",
            "rationale": "run_command is reconstructed from manifest fields; original argv was not stored verbatim.",
        },
        {
            "claim": "Model conditioning on the |A vs |f Register distinction shaped the reply.",
            "level": "neural_attribution_estimate",
            "rationale": "Mode 7 attribution flags register_head among the top-3 contributors; this is evidence, not proof.",
        },
    ]

    caveats: list[str] = [
        "Dev fixture: this packet was assembled without a live trace artifact. "
        "The input/output/copy_slot_trace rows are illustrative; checkpoint, "
        "weights, tokenizer, and corpus hashes are real and verifiable against "
        "the on-disk files at the recorded paths.",
    ]

    return EvidencePacket(
        trace_id=_DEV_FIXTURE_TRACE_ID,
        generated_at=_now_iso_utc(),
        input=input_block,
        cas_expression=cas_expression_block,
        output=output_block,
        copy_slot_trace=copy_slot_trace,
        provenance=provenance,
        hashes=hashes,
        claim_levels=claim_levels,
        caveats=caveats,
    )


def _dev_fixture_fallback_packet(reason: str | None = None) -> EvidencePacket:
    """Return a static dev packet when host-specific fixture assembly fails.

    The dev fixture is the drawer's first-run credibility surface. It must
    never 500 just because Render lacks a scratch checkpoint, git metadata, or
    another local-only artifact. Real trace packets should still fail loudly
    when malformed; this fallback is scoped only to ``dev_example_001``.
    """
    caveat = (
        "Dev fixture fallback: host-specific evidence artifacts were not "
        "available on this deployment, so this packet uses static example "
        "content and leaves hash verification unavailable."
    )
    if reason:
        caveat += f" Internal reason: {reason[:160]}"

    return EvidencePacket(
        trace_id=_DEV_FIXTURE_TRACE_ID,
        generated_at=_now_iso_utc(),
        input={
            "text": "What does ^3^P|A mean and why is it different from ^3^E|f?",
            "user_id": "dev_user",
            "session_id": "dev_session_001",
        },
        cas_expression={
            "text": "^3^P|A",
            "compiler_valid": True,
            "grammar_category": "state_literal",
        },
        output={
            "text": (
                "^3^P|A is principled aversion expressed analytically. "
                "^3^E|f is felt aversion in the evaluative domain. This "
                "fallback packet exists so reviewers can inspect the Evidence "
                "Packet surface even when deployment-local artifacts are absent."
            ),
            "n_tokens": 35,
            "max_new_tokens": 128,
        },
        copy_slot_trace=[
            {
                "role": "noetic",
                "name": "^3",
                "copied": True,
                "source_token_index": 2,
                "target_token_index": 0,
                "claim_level": "source_copy_evidence",
            },
            {
                "role": "domain",
                "name": "P",
                "copied": True,
                "source_token_index": 3,
                "target_token_index": 2,
                "claim_level": "source_copy_evidence",
            },
            {
                "role": "register",
                "name": "A",
                "copied": True,
                "source_token_index": 4,
                "target_token_index": 4,
                "claim_level": "source_copy_evidence",
            },
        ],
        provenance={
            "model_checkpoint_id": "dev_fixture_fallback",
            "checkpoint_label": "Static Evidence Packet fixture",
            "code_commit_sha": "unknown",
            "code_commit_summary": None,
            "run_command": "GET /api/evidence/dev_example_001",
            "config_snapshot": {
                "fixture_mode": "static_fallback",
                "hash_verification": "unavailable_on_this_host",
            },
        },
        hashes={
            "weights_sha": None,
            "tokenizer_hash": None,
            "english_bpe_hash": None,
            "corpus_sha256": None,
            "on_disk_paths": {},
        },
        claim_levels=[
            {
                "claim": "The expression ^3^P|A is a valid CAS state literal.",
                "level": "cas_hard_trace",
                "rationale": "Static fallback fixture; compiler-validity claim mirrors the dev fixture example.",
            },
            {
                "claim": "Copy/slot rows demonstrate the Evidence Packet inspection shape.",
                "level": "derived_trace",
                "rationale": "Rows are illustrative because deployment-local artifacts were unavailable.",
            },
        ],
        caveats=[caveat],
    )


# ---------------------------------------------------------------------------
# Real packet assembly (when a trace artifact is on disk).
# ---------------------------------------------------------------------------


def _packet_from_trace(trace_id: str, trace: dict[str, Any]) -> EvidencePacket:
    """Assemble an EvidencePacket from a real trace artifact.

    The trace artifact follows the schema written by
    ``cas_native.trace.generation_trace`` /
    ``cas_native.trace.live_capture`` — i.e., it carries ``input``,
    ``output``, ``cas_expression``, ``per_identifier``-style copy data, a
    ``model_checkpoint_id``, and a ``checkpoint_manifest_path``.

    Any subset of those fields may be missing; this function fills sensible
    defaults rather than failing.
    """
    manifest_path_raw = trace.get("checkpoint_manifest_path")
    manifest_path = Path(manifest_path_raw) if manifest_path_raw else None
    manifest: dict[str, Any] = {}
    if manifest_path and manifest_path.is_file():
        manifest = _load_checkpoint_manifest(manifest_path) or {}

    tokenizer_meta = manifest.get("extra", {}).get("tokenizer", {}) if manifest else {}

    code_commit_sha = (
        trace.get("code_commit_sha")
        or manifest.get("git_commit_sha")
        or _git_head_sha()
        or "unknown"
    )

    on_disk_paths: dict[str, str] = {}
    weights_path = tokenizer_meta.get("checkpoint_path") or trace.get("weights_path")
    if weights_path:
        on_disk_paths["weights_path"] = str(weights_path)
    tok_path = tokenizer_meta.get("tokenizer_path") or trace.get("tokenizer_path")
    if tok_path:
        on_disk_paths["tokenizer_path"] = str(tok_path)
    if tokenizer_meta.get("english_bpe_path"):
        on_disk_paths["english_bpe_path"] = str(tokenizer_meta["english_bpe_path"])
    if trace.get("corpus_path"):
        on_disk_paths["corpus_path"] = str(trace["corpus_path"])

    hashes: dict[str, Any] = {
        "weights_sha": manifest.get("weights_sha") or trace.get("weights_sha"),
        "tokenizer_hash": tokenizer_meta.get("tokenizer_hash") or trace.get("tokenizer_hash"),
        "english_bpe_hash": tokenizer_meta.get("english_bpe_hash"),
        "corpus_sha256": manifest.get("trained_from_corpus_hash") or trace.get("corpus_sha256"),
        "on_disk_paths": on_disk_paths,
    }

    provenance: dict[str, Any] = {
        "model_checkpoint_id": trace.get("model_checkpoint_id")
        or manifest.get("checkpoint_id")
        or "unknown",
        "checkpoint_label": trace.get("checkpoint_label"),
        "code_commit_sha": code_commit_sha,
        "code_commit_summary": trace.get("code_commit_summary") or _git_head_subject(),
        "run_command": trace.get("run_command")
        or manifest.get("extra", {}).get("run_command"),
        "config_snapshot": {
            "code_version": manifest.get("code_version"),
            "schema_version": manifest.get("schema_version"),
            "trained_at_timestamp": manifest.get("trained_at_timestamp"),
        },
    }

    claim_levels: list[dict[str, Any]] = trace.get("claim_levels") or [
        {
            "claim": "Trace artifact loaded from disk for this trace_id.",
            "level": "derived_trace",
            "rationale": "Reconstructed from the trace JSON; original generation context preserved verbatim.",
        }
    ]

    return EvidencePacket(
        trace_id=trace_id,
        generated_at=_now_iso_utc(),
        input=trace.get("input") or {"text": ""},
        cas_expression=trace.get("cas_expression"),
        output=trace.get("output") or {"text": ""},
        copy_slot_trace=trace.get("copy_slot_trace"),
        provenance=provenance,
        hashes=hashes,
        claim_levels=claim_levels,
        caveats=trace.get("caveats"),
    )


def build_packet_for_trace(trace_id: str) -> EvidencePacket:
    """Top-level packet builder. Returns the dev fixture for the dev id; for
    any other id loads the on-disk trace artifact; raises ``FileNotFoundError``
    if neither path applies.
    """
    if trace_id == _DEV_FIXTURE_TRACE_ID:
        try:
            return _dev_fixture_packet()
        except Exception as exc:
            return _dev_fixture_fallback_packet(f"{type(exc).__name__}: {exc}")
    trace = _load_trace_artifact(trace_id)
    if trace is None:
        raise FileNotFoundError(trace_id)
    return _packet_from_trace(trace_id, trace)


# ---------------------------------------------------------------------------
# Hash verification.
# ---------------------------------------------------------------------------


# Maps the SPEC's verify-response artifact name (left) to:
#   (packet hashes-key holding the expected sha, on_disk_paths-key holding the
#    path to re-hash).
_ARTIFACT_BINDINGS: tuple[tuple[str, str, str], ...] = (
    ("weights", "weights_sha", "weights_path"),
    ("tokenizer", "tokenizer_hash", "tokenizer_path"),
    ("english_bpe", "english_bpe_hash", "english_bpe_path"),
    ("corpus", "corpus_sha256", "corpus_path"),
)


def _verify_packet_hashes(packet: EvidencePacket) -> VerifyHashesResponse:
    """Re-hash on-disk artifacts referenced by ``packet`` and compare.

    For each artifact whose expected SHA is declared in the packet we look
    up the corresponding ``on_disk_paths`` entry, stream a fresh sha256
    over the file, and emit a check row. ``code_commit`` is verified
    separately via ``git rev-parse HEAD``.

    Artifacts whose expected SHA is absent from the packet are skipped
    entirely — they never appear in the check list.
    """
    checks: list[VerifyCheck] = []
    hashes = packet.hashes or {}
    on_disk_paths: dict[str, Any] = hashes.get("on_disk_paths") or {}

    for artifact, sha_key, path_key in _ARTIFACT_BINDINGS:
        expected = hashes.get(sha_key)
        if expected is None:
            continue
        path_str = on_disk_paths.get(path_key)
        if not path_str:
            checks.append(
                VerifyCheck(
                    artifact=artifact,
                    expected=expected,
                    actual=None,
                    match=False,
                    notes="no on_disk_paths entry for this artifact",
                )
            )
            continue
        path, reject_reason = _resolve_allowed_path(path_str)
        if path is None:
            checks.append(
                VerifyCheck(
                    artifact=artifact,
                    expected=expected,
                    actual=None,
                    match=False,
                    notes=reject_reason or "path rejected",
                )
            )
            continue
        actual = _sha256_file(path)
        if actual is None:
            checks.append(
                VerifyCheck(
                    artifact=artifact,
                    expected=expected,
                    actual=None,
                    match=False,
                    notes="failed to read file for hashing",
                )
            )
            continue
        checks.append(
            VerifyCheck(
                artifact=artifact,
                expected=expected,
                actual=actual,
                match=(actual == expected),
            )
        )

    # code_commit — git-based check.
    expected_commit = (packet.provenance or {}).get("code_commit_sha")
    if expected_commit is not None and expected_commit != "unknown":
        actual_commit = _git_head_sha()
        if actual_commit is None:
            checks.append(
                VerifyCheck(
                    artifact="code_commit",
                    expected=expected_commit,
                    actual=None,
                    match=False,
                    notes="git rev-parse HEAD failed (not a git checkout or git not on PATH)",
                )
            )
        else:
            checks.append(
                VerifyCheck(
                    artifact="code_commit",
                    expected=expected_commit,
                    actual=actual_commit,
                    match=(actual_commit == expected_commit),
                    notes=(
                        "expected commit was HEAD when the trace was authored; "
                        "mismatch is normal once HEAD has moved past that commit"
                        if actual_commit != expected_commit
                        else None
                    ),
                )
            )

    if not checks:
        overall = "unable_to_verify"
    elif all(c.match for c in checks):
        overall = "all_match"
    elif all(not c.match and (c.actual is None) for c in checks):
        overall = "unable_to_verify"
    else:
        overall = "partial_mismatch"

    return VerifyHashesResponse(
        trace_id=packet.trace_id,
        verified_at=_now_iso_utc(),
        checks=checks,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Route handlers.
# ---------------------------------------------------------------------------


@router.get("/{trace_id}", response_model=EvidencePacket)
async def get_evidence_packet(trace_id: str) -> EvidencePacket:
    """Return the full Evidence Packet for ``trace_id``.

    The dev fixture id ``dev_example_001`` is always available. Any other
    id requires a per-trace JSON artifact on disk in one of the
    conventional locations (see ``_candidate_trace_paths``).
    """
    try:
        return build_packet_for_trace(trace_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="trace_id not found")


@router.post("/{trace_id}/verify", response_model=VerifyHashesResponse)
async def verify_evidence_packet(trace_id: str) -> VerifyHashesResponse:
    """Re-hash on-disk artifacts referenced by the packet for ``trace_id``.

    For each artifact whose ``on_disk_paths`` entry exists, a fresh sha256
    is streamed over the file and compared to the recorded value. The
    response's ``overall`` field summarises the result (SPEC §6).
    """
    try:
        packet = build_packet_for_trace(trace_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="trace_id not found")
    return _verify_packet_hashes(packet)
