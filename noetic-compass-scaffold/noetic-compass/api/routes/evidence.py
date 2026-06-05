"""Evidence Packet v1 — provenance + traceability surface.

Stateless GET/POST endpoints that back the Evidence Packet drawer in the
dashboard. Reads on-disk artifacts only; nothing is written.

Schema authority: ``docs/working/evidence_packet_2026_05_15/SPEC.md``.

Three endpoints:

* ``GET  /api/evidence/{trace_id}``        → full ``EvidencePacket`` JSON.
* ``POST /api/evidence/{trace_id}/verify`` → re-hash on-disk artifacts and
  compare against the SHAs recorded in the packet.
* ``POST /api/evidence/{trace_id}/anchor`` → WORM-anchor a Stage 9 40E
  validation packet (any model size, by trace_id) and return an honest anchor
  receipt. This is the one deliberate side effect in the module (see below).

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

The GET/verify endpoints are intentionally side-effect free: no DB, no global
state, reads only. The ``/anchor`` endpoint is the one deliberate exception --
anchoring is an explicit operational write, never triggered by a normal read,
and it fabricates nothing: the receipt comes straight from the configured anchor
mode (disabled/local = NOT WORM; s3 + object-lock = real WORM). ``hashlib``
(stdlib) is used for sha256.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.config import settings
from api.dependencies.authz import current_tenant, require_role_in_account_mode
from api.services.cas_harness_static_evidence_anchor import (
    anchor_static_evidence_packet,
    load_anchored_static_packet_payload,
    summarize_static_anchor_worm_status,
    verify_anchored_static_packet,
)
from api.services.evidence_ownership import tenant_owns_trace

router = APIRouter(prefix="/evidence", tags=["evidence"])


# ---------------------------------------------------------------------------
# Per-tenant evidence isolation (PAID-tenant security spine).
#
# Dark-default invariant: when ``settings.accounts_enabled`` is False (the legacy shared-secret
# posture, and the default), every dependency below is a COMPLETE no-op -- the evidence routes
# behave byte-for-byte as before, gated only by the legacy Bearer token the auth middleware already
# validated. Enforcement turns on ONLY when per-account identity is enabled.
# ---------------------------------------------------------------------------

# 404 contract: a trace this tenant does not own is reported as "not found", never as 403. The
# evidence routes already answer an unknown trace with exactly this status + detail (see the
# handlers' ``raise HTTPException(status_code=404, detail="trace_id not found")``). Matching it here
# means a cross-tenant probe is indistinguishable from a genuinely-absent trace -- existence is never
# leaked via a 403-vs-404 divergence.
_NOT_FOUND_DETAIL = "trace_id not found"


def _evidence_state_store(request: Request):
    """Return the durable ``StateStore`` the ownership ledger lives in, or ``None`` if absent.

    Mirrors how the auth middleware reaches its stores: off ``request.app.state``. The state ledger
    is stashed at startup as ``app.state.state_ledger`` -- a ``StateLedgerHandle`` whose ``.store``
    is the ``StateStore`` (see ``api/state_ledger_bootstrap.py`` and ``api/main.py`` lifespan). It is
    ``None`` when the ledger is dark. We read it defensively (``getattr``) so a TestClient that never
    ran the lifespan, or a deployment with the ledger dark, simply yields ``None`` rather than
    raising. The CALLER decides what ``None`` means; in account mode the guard fails closed (404).
    """
    handle = getattr(request.app.state, "state_ledger", None)
    if handle is None:
        return None
    return getattr(handle, "store", None)


def _require_evidence_access(request: Request) -> None:
    """Per-tenant ownership guard for an evidence ``trace_id`` route.

    * ``settings.accounts_enabled`` False (dark default) -> return ``None`` immediately. NO identity
      read, NO store lookup, NO new failure mode: the route is gated exactly as it is today.
    * ``settings.accounts_enabled`` True -> resolve the SERVER-set tenant (``current_tenant`` raises
      401 when no account-mode identity is present, which is the correct answer in account mode),
      obtain the ``StateStore``, and require that this tenant OWNS the trace. If not -- including the
      fail-closed case where account-mode is on but no store is installed -- raise **404**
      ``trace_id not found`` (never 403, never 500). The ``trace_id`` is the path parameter.

    Read at request time off ``settings`` (the singleton the rest of ``api/`` uses) so the flag flip
    in tests/deployments takes effect per call.
    """
    if not settings.accounts_enabled:
        # Dark default: complete no-op. Legacy shared-secret posture, byte-for-byte unchanged.
        return None

    # Account mode: a real, server-derived tenant must be present (else 401 -- "who are you?").
    tenant_id = current_tenant(request)

    # Resolve the trace_id straight from the matched path params (server-side, never the body).
    trace_id = str(request.path_params.get("trace_id", "")).strip()

    store = _evidence_state_store(request)
    if store is None:
        # Fail CLOSED: account-mode enforcement is on but the ownership ledger is unavailable. We do
        # NOT silently allow; we deny exactly as we would for an unowned trace (404, no existence
        # leak). A misconfigured deployment that wanted enforcement gets denial, not a bypass.
        raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)

    if not tenant_owns_trace(store, tenant_id=tenant_id, trace_id=trace_id):
        raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)

    return None


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
    model: dict[str, Any] | None = None
    cas_expression: dict[str, Any] | None = None
    output: dict[str, Any]
    copy_slot_trace: list[dict[str, Any]] | None = None
    provenance: dict[str, Any]
    hashes: dict[str, Any]
    claim_levels: list[dict[str, Any]]
    caveats: list[str] | None = None
    readout: dict[str, Any] | None = None
    ablation: dict[str, Any] | None = None
    matched_controls: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    generation_readiness: dict[str, Any] | None = None
    distributed_fleet: dict[str, Any] | None = None
    live_audit: dict[str, Any] | None = None
    audit_scope: dict[str, Any] | None = None


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


class AnchorEvidenceResponse(BaseModel):
    """Honest receipt for a per-packet WORM anchor attempt.

    Model-size-independent by construction: any Stage 9 40E packet discoverable in
    the registry — 160M, 20B, 70B, 300B, 1T, 3T — anchors through this one endpoint
    by its own ``trace_id`` with no per-model code. The receipt is never
    fabricated; it reflects exactly what the configured anchor mode produced.
    """

    trace_id: str
    anchored_at: str
    worm_retained: bool = Field(
        description=(
            "True ONLY when a real S3 object-lock write was re-read and confirmed. "
            "disabled/local/partial anchors are honestly False."
        )
    )
    console_state: str = Field(
        description=(
            "What the Audit Console shows for this packet after this anchor: "
            "'accept_scoped_validation' only when the packet's own verdict is ACCEPT/"
            "SUPPRESS and the packet is WORM-retained; WORM-retained FLAG packets "
            "stay 'flag_for_human_review'."
        )
    )
    anchor_status: str | None = None
    anchor_mode: str | None = None
    anchor_uri: str | None = None
    verify_overall: str | None = None
    external_anchor_match: bool | None = None
    external_anchor_notes: str | None = None
    hash_log_path: str | None = None
    decision_scope: str = "stage9_40e_validation_packet"
    message: str


# ---------------------------------------------------------------------------
# Path discovery — paths that are stable across the dev fixture and the real
# packet path are resolved relative to the project root.
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    """Return ``tksCAS/`` — the outer git root.

    Resolved as ``api/routes/evidence.py`` → up 4 → outer repo root.
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists() or (parent / "noetic-compass-scaffold").exists():
            return parent
    parents = list(current.parents)
    return parents[4] if len(parents) > 4 else parents[-1]


def _scaffold_root() -> Path:
    """Return ``noetic-compass-scaffold/noetic-compass/``."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "api").is_dir() and (parent / "atlas-viewer").is_dir():
            return parent
    parents = list(current.parents)
    return parents[2] if len(parents) > 2 else parents[-1]


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
    except (FileNotFoundError, OSError, RuntimeError, IndexError, subprocess.TimeoutExpired):
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
    except (FileNotFoundError, OSError, RuntimeError, IndexError, subprocess.TimeoutExpired):
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
    candidates = [
        # CAS Harness working packets checked into the repo for audit review.
        scaffold / "docs" / "working" / f"{safe}.json",
        scaffold / "docs" / "working" / f"{safe.upper()}.json",
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
    if trace_id == "s7-f28-balanced-bridge-gpt-neox-20b-20260526":
        candidates.insert(
            0,
            scaffold
            / "docs"
            / "working"
            / "S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json",
        )
    return candidates


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
_CAS_HARNESS_REFERENCE_TRACE_ID = "cas_harness_reference_accept_001"
_STAGE9_40E_ORIGINAL_TRACE_ID = "stage9-40e-original-baseline-readout-20260527"
_STAGE9_40E_ORIGINAL_PACKET_FILENAME = (
    "gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0455Z.json"
)

_STAGE9_40E_PACKET_SCHEMA = "cas_harness_stage9_40e_evidence_packet.v1"

# Seed packets we always know about even before on-disk discovery runs. These are
# *scoped project-validation* packets (NOT per-customer production ACCEPTs): the
# bundled GPT-NeoX-20B packet and the from-scratch Pythia-160M CPU reproduction.
# Seeds are only a deterministic floor — the registry below generalizes resolution
# so ANY model size's Stage 9 40E packet is anchorable by its own trace_id with no
# code edit. A small truck and a huge truck go through the same checkpoint.
_STAGE9_40E_SEED_PACKET_PATH_PARTS_BY_TRACE: dict[str, tuple[str, ...]] = {
    _STAGE9_40E_ORIGINAL_TRACE_ID: (
        "docs",
        "working",
        _STAGE9_40E_ORIGINAL_PACKET_FILENAME,
    ),
    "pythia-160m-stage9-40e-readout-20260531": (
        "docs",
        "working",
        "pythia160m_gate1",
        "pythia160m_stage9_40e_evidence_packet.json",
    ),
}


def _stage9_40e_trace_for_packet_file(path: Path) -> str | None:
    """Return a packet file's self-declared trace_id iff it is a Stage 9 40E packet.

    Schema-gated so the registry only indexes genuine Stage 9 40E packets and
    ignores unrelated JSON that happens to sit under the same trees.
    """

    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != _STAGE9_40E_PACKET_SCHEMA:
        return None
    trace_id = payload.get("trace_id")
    if not isinstance(trace_id, str) or not trace_id:
        return None
    return trace_id


def _stage9_40e_packet_registry_roots() -> list[Path]:
    """Directories scanned for Stage 9 40E packets, in precedence order."""

    roots = [_scaffold_root() / "docs" / "working"]
    store_dir = os.environ.get("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR")
    if store_dir:
        roots.append(Path(store_dir))
    return roots


def stage9_40e_packet_path_registry() -> dict[str, Path]:
    """Index every discoverable Stage 9 40E packet by its self-declared trace_id.

    This is the general registry that replaces hard-coded, per-model anchor
    wiring (the "filing clerk who knows only one folder" anti-pattern). Seeds win
    deterministically; anything else dropped under the registry roots is indexed
    by reading its own ``trace_id``, so the anchor path resolves any model size's
    packet — 160M, 20B, 70B, 300B, 1T, 3T — without a code change.
    """

    index: dict[str, Path] = {}
    for trace_id, parts in _STAGE9_40E_SEED_PACKET_PATH_PARTS_BY_TRACE.items():
        seeded = _scaffold_root().joinpath(*parts)
        if seeded.is_file():
            index.setdefault(trace_id, seeded)
    for root in _stage9_40e_packet_registry_roots():
        if not root.is_dir():
            continue
        for candidate in sorted(root.glob("**/*evidence_packet*.json")):
            discovered = _stage9_40e_trace_for_packet_file(candidate)
            if discovered is not None:
                index.setdefault(discovered, candidate)
    return index


def load_stage9_40e_packet_payload_for_trace(trace_id: str) -> dict[str, Any]:
    """Return the raw Stage 9 40E validation packet for audit-session use.

    The Stage 9 40E packet is intentionally not forced into the older
    ``EvidencePacket`` drawer schema. The Audit Console needs its raw verifier
    fields so the verdict runner can pass through the explicit packet-level
    decision without losing proof-chip scope.

    Resolution is registry-driven (``stage9_40e_packet_path_registry``): an
    unknown ``trace_id`` raises ``FileNotFoundError`` exactly as before, and a
    discoverable one is loaded and validated against the Stage 9 40E schema with a
    trace self-consistency check. This is model-size-independent by construction.
    """

    packet_path = stage9_40e_packet_path_registry().get(trace_id)
    if packet_path is None:
        raise FileNotFoundError(trace_id)
    try:
        with packet_path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        raise FileNotFoundError(trace_id) from exc
    if not isinstance(payload, dict):
        raise FileNotFoundError(trace_id)
    if payload.get("schema_version") != _STAGE9_40E_PACKET_SCHEMA:
        raise FileNotFoundError(trace_id)
    if payload.get("trace_id") != trace_id:
        raise FileNotFoundError(trace_id)
    return payload


def public_stage9_40e_packet_payload_for_trace(trace_id: str) -> dict[str, Any]:
    """Return a Stage 9 packet view safe for public/product reads.

    Historical Stage 9 packets can contain an explicit scoped-validation
    ``ACCEPT`` inside their raw JSON. The product gate is stricter: a normal read
    must not expose that as the packet's active verdict unless the packet has a
    persisted, re-verifiable WORM/Object-Lock anchor. Audit-session execution
    already applies the verdict runner; this view applies the same safety rule to
    the lower-level GET endpoint.
    """

    raw = load_stage9_40e_packet_payload_for_trace(trace_id)
    anchored = load_anchored_static_packet_payload(trace_id)
    payload = anchored if isinstance(anchored, dict) else raw
    if not _stage9_40e_packet_is_worm_retained(anchored):
        return _stage9_40e_review_projection(payload)
    return json.loads(json.dumps(payload))


def _stage9_40e_packet_is_worm_retained(packet: dict[str, Any] | None) -> bool:
    if not isinstance(packet, dict):
        return False
    try:
        verify = verify_anchored_static_packet(packet)
    except Exception:
        return False
    return bool(summarize_static_anchor_worm_status(packet, verify).get("worm_retained"))


def _stage9_40e_review_projection(packet: dict[str, Any]) -> dict[str, Any]:
    projected = json.loads(json.dumps(packet))
    verdict = str(projected.get("verdict", "")).strip().upper()
    if verdict not in {"ACCEPT", "SUPPRESS"}:
        return projected

    reason = "public_read_gate_requires_worm_retention"
    message = (
        "Public read gate: this static Stage 9 40E packet is not currently "
        "verified as WORM-retained on this deployment, so ACCEPT/SUPPRESS is "
        "withheld and the served verdict remains FLAG_FOR_HUMAN_REVIEW."
    )
    gated_decision = {
        "schema_version": "cas_harness_stage9_40e_verifier_decision.v1",
        "verdict": "FLAG_FOR_HUMAN_REVIEW",
        "confidence": 0.0,
        "source": "evidence_route_public_read_gate",
        "reason": reason,
        "decision_scope": "stage9_40e_validation_packet",
        "coverage": None,
    }

    projected["verdict"] = "FLAG_FOR_HUMAN_REVIEW"
    projected["verdict_rationale"] = message
    verification = projected.get("verification")
    if isinstance(verification, dict):
        verification["explicit_verifier_decision"] = dict(gated_decision)
        verification["proof_chip_gate"] = "blocked"
        verification["public_read_gate"] = {
            "status": "blocked",
            "reason": reason,
            "requires": "verified WORM-retained Evidence Packet",
        }
    verifier = projected.get("verifier")
    if isinstance(verifier, dict):
        verifier["explicit_verifier_decision"] = dict(gated_decision)
    return projected


def _cas_harness_reference_packet() -> EvidencePacket:
    """Evidence-backed reference packet for the Audit Console beta path.

    This fixture represents the validated CAS Harness reference path. It is not
    a customer endpoint call. It exists so the beta console can exercise the
    complete backend verdict contract without inventing a verdict client-side.
    """

    return EvidencePacket(
        schema_version="cas_harness_evidence_packet_v1",
        trace_id=_CAS_HARNESS_REFERENCE_TRACE_ID,
        generated_at=_now_iso_utc(),
        model={
            "model_key": "EleutherAI/pythia-160m",
            "name": "EleutherAI/pythia-160m",
            "runtime": "CAS Harness reference path",
        },
        input={
            "text": (
                "Reference audit smoke scenario: validate the CAS Harness "
                "audit contract without fabricating a verdict."
            ),
            "scenario_id": "cas_harness_reference_accept_v1",
        },
        cas_expression={
            "text": "F1|A reference verification row",
            "compiler_valid": True,
            "grammar_category": "reference_audit_row",
        },
        output={
            "text": (
                "Reference output accepted by the Stage 19 verification stack "
                "and Stage 20 generation-readiness gate."
            ),
            "n_tokens": 18,
            "max_new_tokens": 64,
        },
        copy_slot_trace=[
            {
                "role": "drive",
                "name": "F1",
                "copied": True,
                "source_token_index": 0,
                "target_token_index": 0,
                "claim_level": "source_copy_evidence",
            }
        ],
        provenance={
            "source_stage": "CAS Harness reference beta packet",
            "source_reports": [
                "stage19_verification_stack_report.json",
                "stage20_generation_readiness_report.json",
                "stage21_reference_packet_builder.json",
            ],
            "model_checkpoint_id": "EleutherAI/pythia-160m",
            "checkpoint_label": "CAS Harness reference target",
            "code_commit_sha": _git_head_sha() or "unknown",
            "code_commit_summary": _git_head_subject(),
            "run_command": (
                "POST /api/cas-harness/audit/session with "
                "evidence_packet_trace_id=cas_harness_reference_accept_001"
            ),
            "config_snapshot": {
                "audit_mode": "BALANCED",
                "reference_fixture": True,
                "customer_model_call": False,
            },
        },
        hashes={
            "weights_sha": None,
            "tokenizer_hash": None,
            "corpus_sha256": None,
            "on_disk_paths": {},
        },
        claim_levels=[
            {
                "claim": "Stage 19 verification stack accepted the reference row.",
                "level": "derived_trace",
                "support_status": "supported",
                "support_rationale": (
                    "The packet carries an explicit accepted=true Stage 19 "
                    "verification field."
                ),
                "rationale": "Reference packet exercises the locked verifier contract.",
            },
            {
                "claim": "Stage 20 generation readiness action is allow.",
                "level": "derived_trace",
                "support_status": "supported",
                "support_rationale": (
                    "The packet carries generation_readiness=allow and low risk."
                ),
                "rationale": "Reference packet exercises the locked readiness contract.",
            },
            {
                "claim": "Matched control evidence is present for the reference row.",
                "level": "derived_trace",
                "support_status": "supported",
                "support_rationale": (
                    "The packet records random_same_rank control status as present."
                ),
                "rationale": "Reference packet includes the control-proof field required by the runner.",
            },
        ],
        caveats=[
            "Reference beta packet: this is bundled CAS Harness evidence for the "
            "supported Pythia-160M reference path. It is not a live customer "
            "endpoint call and must not be presented as arbitrary-model coverage."
        ],
        readout={"axis": "drive", "label": "F1", "confidence": 0.86},
        ablation={"status": "present", "effect": "targeted_drop"},
        matched_controls={"status": "present", "control": "random_same_rank"},
        verification={
            "accepted": True,
            "mode": "BALANCED",
            "confidence_tier": "high",
            "mode_profile": {
                "accepted_accuracy": 0.9816,
                "coverage": 0.7173,
            },
            "suppression_reasons": [],
        },
        generation_readiness={
            "generation_readiness": "allow",
            "risk_score": 0.11,
            "policy_version": "stage20_reference_v1",
            "reasons": [],
        },
    )


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
            "support_status": "supported",
            "support_rationale": "The compiler accepts the expression deterministically.",
            "rationale": "compile_expression returned valid=true with grammar_category=state_literal - deterministic.",
        },
        {
            "claim": "The output reuses the input's CAS tokens via pointer copy, not paraphrase.",
            "level": "source_copy_evidence",
            "support_status": "supported",
            "support_rationale": "The copy trace names the copied slots and their source/target positions.",
            "rationale": "Four named slots (^3, P, A, f) have copy=true with named source token indices.",
        },
        {
            "claim": "Run reproducer reconstructed from the checkpoint manifest's extra block.",
            "level": "derived_trace",
            "support_status": "partially_supported",
            "support_rationale": "The manifest supports the reconstruction, but original argv was not stored verbatim.",
            "rationale": "run_command is reconstructed from manifest fields; original argv was not stored verbatim.",
        },
        {
            "claim": "Model conditioning on the |A vs |f Register distinction shaped the reply.",
            "level": "neural_attribution_estimate",
            "support_status": "partially_supported",
            "support_rationale": "Mode 7 provides evidence for this link, not deterministic proof.",
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
                "support_status": "supported",
                "support_rationale": "The static fixture uses a compiler-valid CAS expression.",
                "rationale": "Static fallback fixture; compiler-validity claim mirrors the dev fixture example.",
            },
            {
                "claim": "Copy/slot rows demonstrate the Evidence Packet inspection shape.",
                "level": "derived_trace",
                "support_status": "not_applicable",
                "support_rationale": "This fallback row demonstrates packet shape; it is not a live model claim.",
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
            "support_status": "supported",
            "support_rationale": "The packet was assembled from an on-disk trace artifact for this trace_id.",
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
    if trace_id == _CAS_HARNESS_REFERENCE_TRACE_ID:
        return _cas_harness_reference_packet()
    try:
        from api.services.cas_harness_merged_evidence_packets import (
            load_merged_fleet_evidence_packet_payload,
        )

        return EvidencePacket.model_validate(load_merged_fleet_evidence_packet_payload(trace_id))
    except FileNotFoundError:
        pass
    trace = _load_trace_artifact(trace_id)
    if trace is None:
        raise FileNotFoundError(trace_id)
    if _is_evidence_packet_payload(trace):
        return EvidencePacket.model_validate(trace)
    return _packet_from_trace(trace_id, trace)


def _is_evidence_packet_payload(payload: dict[str, Any]) -> bool:
    schema = payload.get("schema_version")
    return (
        schema
        in {
            "evidence_packet.v1",
            "cas_harness_evidence_packet_v1",
            "cas_harness_evidence_packet.v1",
        }
        and isinstance(payload.get("trace_id"), str)
        and isinstance(payload.get("input"), dict)
        and isinstance(payload.get("output"), dict)
        and isinstance(payload.get("provenance"), dict)
        and isinstance(payload.get("hashes"), dict)
        and isinstance(payload.get("claim_levels"), list)
    )


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

    if packet.distributed_fleet is not None or packet.live_audit is not None:
        try:
            from api.services.cas_harness_merged_evidence_packets import (
                verify_merged_fleet_evidence_packet_payload,
            )

            checks.extend(
                VerifyCheck.model_validate(check)
                for check in verify_merged_fleet_evidence_packet_payload(
                    packet.model_dump(mode="json", exclude_none=True)
                )
            )
            from api.services.cas_harness_evidence_anchor import verify_anchor

            checks.append(
                VerifyCheck.model_validate(
                    verify_anchor(packet.model_dump(mode="json", exclude_none=True))
                )
            )
        except FileNotFoundError as exc:
            checks.append(
                VerifyCheck(
                    artifact="merged_packet_hash_log",
                    expected=(packet.hashes or {}).get("hash_log_entry_sha256"),
                    actual=None,
                    match=False,
                    notes=f"merged packet hash log unavailable: {exc}",
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


@router.get("/{trace_id}", dependencies=[Depends(_require_evidence_access)])
async def get_evidence_packet(trace_id: str) -> dict[str, Any]:
    """Return the full Evidence Packet for ``trace_id``.

    The Stage 9 40E packet registry is checked first so the raw scoped-validation
    packets served by the anchor endpoint are also inspectable before the
    irreversible Object-Lock write. Other traces fall back to the older
    ``EvidencePacket`` drawer schema.
    """
    try:
        return public_stage9_40e_packet_payload_for_trace(trace_id)
    except FileNotFoundError:
        pass
    try:
        return build_packet_for_trace(trace_id).model_dump()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="trace_id not found")


@router.post(
    "/{trace_id}/verify",
    response_model=VerifyHashesResponse,
    dependencies=[Depends(_require_evidence_access)],
)
async def verify_evidence_packet(trace_id: str) -> VerifyHashesResponse:
    """Re-hash on-disk artifacts referenced by the packet for ``trace_id``.

    For each artifact whose ``on_disk_paths`` entry exists, a fresh sha256
    is streamed over the file and compared to the recorded value. The
    response's ``overall`` field summarises the result (SPEC §6).
    """
    try:
        packet = build_packet_for_trace(trace_id)
    except FileNotFoundError:
        static_packet = load_anchored_static_packet_payload(trace_id)
        if static_packet is None:
            try:
                load_stage9_40e_packet_payload_for_trace(trace_id)
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="trace_id not found")
            return VerifyHashesResponse(
                trace_id=trace_id,
                verified_at=_now_iso_utc(),
                checks=[
                    VerifyCheck(
                        artifact="static_reference_anchor",
                        expected="persisted static-reference anchor receipt",
                        actual=None,
                        match=False,
                        notes=(
                            "Stage 9 40E packet is bundled and readable, but no "
                            "persisted static-reference anchor receipt exists in "
                            "CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR for this deployment."
                        ),
                    )
                ],
                overall="unable_to_verify",
            )
        verify = verify_anchored_static_packet(static_packet)
        return VerifyHashesResponse(
            trace_id=str(verify.get("trace_id") or trace_id),
            verified_at=_now_iso_utc(),
            checks=verify.get("checks") if isinstance(verify.get("checks"), list) else [],
            overall=str(verify.get("overall") or "unable_to_verify"),
        )
    return _verify_packet_hashes(packet)


@router.post(
    "/{trace_id}/anchor",
    response_model=AnchorEvidenceResponse,
    dependencies=[
        # Ownership 404 (dark-default no-op) AND a role gate that is LIVE only in account mode.
        # Anchoring is an operational WORM write, so once accounts are on it is operator/admin/owner
        # only (a member-role identity gets 403). In dark mode both are pass-throughs, so the legacy
        # token still anchors with HTTP 200 exactly as before.
        Depends(_require_evidence_access),
        Depends(require_role_in_account_mode("operator", "admin", "owner")),
    ],
)
async def anchor_evidence_packet(
    trace_id: str,
    require_object_lock: bool = False,
) -> AnchorEvidenceResponse:
    """WORM-anchor the Stage 9 40E validation packet for ``trace_id``.

    General by construction: ``trace_id`` is resolved through
    ``stage9_40e_packet_path_registry`` so ANY model size's Stage 9 40E packet —
    160M, 20B, 70B, 300B, 1T, 3T — anchors through this one endpoint with no
    per-model code (the small-truck/huge-truck-same-checkpoint design). A trace
    that is not a discoverable Stage 9 40E packet returns 404.

    The receipt is honest. With no S3 object-lock bucket configured the packet is
    anchored at mode ``disabled``/``local`` (NOT WORM) and the console correctly
    stays at FLAG_FOR_HUMAN_REVIEW; ``worm_retained`` is False. A real S3
    object-lock write — re-read and confirmed — flips ``worm_retained`` to True, but
    WORM retention records the packet's verdict immutably; it never changes it. The
    console shows a SCOPED-VALIDATION ACCEPT only when the packet's own verdict is
    ACCEPT/SUPPRESS *and* the packet is WORM-retained (never a per-customer
    production ACCEPT); a WORM-retained FLAG_FOR_HUMAN_REVIEW packet stays at
    FLAG_FOR_HUMAN_REVIEW.

    ``require_object_lock=true`` turns the endpoint into a gate: if the anchor did
    not reach verified WORM retention it returns 409, so a promotion pipeline can
    refuse to advance the packet rather than silently accept a non-WORM anchor.
    """

    try:
        packet = load_stage9_40e_packet_payload_for_trace(trace_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="trace_id not found")

    anchored = anchor_static_evidence_packet(packet)
    verify = verify_anchored_static_packet(anchored)
    summary = summarize_static_anchor_worm_status(anchored, verify)
    worm_retained = bool(summary["worm_retained"])

    hashes = anchored.get("hashes") if isinstance(anchored, dict) else None
    hash_log_path = hashes.get("hash_log_path") if isinstance(hashes, dict) else None

    packet_verdict = (
        str(packet.get("verdict", "")).strip().upper()
        if isinstance(packet, dict)
        else ""
    )
    verdict_is_accept = packet_verdict in {"ACCEPT", "SUPPRESS"}

    if worm_retained and verdict_is_accept:
        console_state = "accept_scoped_validation"
        message = (
            "Packet is WORM-retained. The Audit Console will show a SCOPED-VALIDATION "
            "ACCEPT for this packet (decision_scope stage9_40e_validation_packet) — "
            "NOT a per-customer production ACCEPT."
        )
    elif worm_retained:
        console_state = "flag_for_human_review"
        message = (
            "Packet is WORM-retained (immutably anchored), but its verdict is "
            f"{packet_verdict or 'FLAG_FOR_HUMAN_REVIEW'}, so the Audit Console "
            "correctly stays at FLAG_FOR_HUMAN_REVIEW. WORM anchoring records a "
            "verdict immutably; it never upgrades a FLAG to an ACCEPT."
        )
    else:
        console_state = "flag_for_human_review"
        message = (
            f"Packet anchored at mode {summary['anchor_mode']!r} (status "
            f"{summary['anchor_status']!r}); this is NOT WORM retention, so the console "
            "correctly stays at FLAG_FOR_HUMAN_REVIEW. Set "
            "CAS_HARNESS_EVIDENCE_ANCHOR_MODE=s3 with an Object-Lock bucket + AWS "
            "credentials, then re-run to produce a real per-packet WORM anchor."
        )

    if require_object_lock and not worm_retained:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "anchor_not_worm_retained",
                "trace_id": trace_id,
                "anchor_mode": summary["anchor_mode"],
                "anchor_status": summary["anchor_status"],
                "verify_overall": summary["verify_overall"],
                "message": message,
            },
        )

    return AnchorEvidenceResponse(
        trace_id=trace_id,
        anchored_at=_now_iso_utc(),
        worm_retained=worm_retained,
        console_state=console_state,
        anchor_status=summary["anchor_status"],
        anchor_mode=summary["anchor_mode"],
        anchor_uri=summary["anchor_uri"],
        verify_overall=summary["verify_overall"],
        external_anchor_match=summary["external_anchor_match"],
        external_anchor_notes=summary["external_anchor_notes"],
        hash_log_path=hash_log_path if isinstance(hash_log_path, str) else None,
        message=message,
    )
