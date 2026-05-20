"""CAS Harness EvidencePacket v1 — read-only serving surface.

Stage 21B: backend route that serves the Stage 21A EvidencePacket v1 schema to
the Atlas reviewer drawer. The endpoint is the implementation target named in
``research/cas_probe/CAS_HARNESS_PRODUCT_EVIDENCE_PACKET_20260519.json``
(``implementation_target.api = /api/harness/evidence/{trace_id}``).

Authority: schema, validator, and markdown renderer live in
``research/cas_probe/evidence_packet.py`` (Stage 21A). This module consumes
those three primitives and does not redefine them.

Two endpoints (both auth-required by default via ``JWTAuthMiddleware``):

* ``GET  /harness/evidence/{trace_id}``          — full ``EvidencePacket`` JSON.
* ``GET  /harness/evidence/{trace_id}/markdown`` — reviewer-readable Markdown.

Storage layer
-------------
For this MVP wiring the packet store is a directory of ``{trace_id}.json``
files, configured via the ``harness_evidence_packets_dir`` setting (env
``NC_EVIDENCE_PACKETS_DIR``). When a ``{trace_id}.md`` file is present on
disk it is served verbatim; otherwise the Markdown is rendered on the fly via
``render_evidence_packet_markdown``. Production deployments should swap this
file-backed store for the canonical packet store as a follow-on.

Boundary properties enforced
----------------------------
1. ``trace_id`` matches a strict UUID4-or-alphanumeric-with-underscore regex.
   Anything else is rejected with HTTP 400 BEFORE any filesystem access.
2. Resolved on-disk path must be contained under the configured packets
   directory (``Path.resolve().relative_to(packets_dir.resolve())``). This
   is the second layer of the path-traversal guard.
3. Files exceeding 8 MiB are refused with HTTP 413 — a defensive bound that
   should never be hit by a well-formed packet (canonical samples are <10 KB)
   but bounds the work this endpoint performs per request.
4. Every served packet round-trips through ``validate_evidence_packet``. A
   schema validation failure surfaces as HTTP 500 with a generic message;
   the underlying detail is logged for internal audit, not leaked.
5. Reserved language: response details use "evidence packet not found",
   "validation failed", etc. HTTP status codes carry the failure semantics.

This module is intentionally side-effect free: no DB, no writes, no global
state, no new dependencies beyond the existing FastAPI/pydantic stack.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from api.config import settings


logger = logging.getLogger("noetic.harness_evidence")

router = APIRouter(prefix="/harness/evidence", tags=["harness_evidence"])


# ---------------------------------------------------------------------------
# Boundary constants.
# ---------------------------------------------------------------------------


# Strict trace_id regex: UUID4 form OR alphanumeric-plus-underscore-plus-hyphen.
# This rejects path-separator characters, parent-directory tokens, leading
# dots, quotes, whitespace, and every other path-traversal vector before
# any filesystem access is attempted.
_TRACE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")

# 8 MiB — packet samples are <10 KB; this is a defensive ceiling.
_MAX_PACKET_BYTES = 8 * 1024 * 1024


# ---------------------------------------------------------------------------
# Stage 21A schema module — imported by path because ``research/cas_probe``
# is not a Python package on disk (no ``__init__.py``). The path is anchored
# to this file's location so it is stable across cwd changes.
# ---------------------------------------------------------------------------


def _load_evidence_packet_module() -> Any:
    """Load ``research/cas_probe/evidence_packet.py`` as a module.

    Imported once at module init and cached. Raises ``RuntimeError`` only if
    the Stage 21A module is missing entirely — that is a deployment-level
    misconfiguration, not a per-request failure.
    """
    scaffold_root = Path(__file__).resolve().parents[2]
    module_path = scaffold_root / "research" / "cas_probe" / "evidence_packet.py"
    if not module_path.is_file():
        raise RuntimeError(
            f"Stage 21A evidence_packet module not found at {module_path}"
        )
    spec = importlib.util.spec_from_file_location(
        "noetic_harness_evidence_packet_v1", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Failed to load Stage 21A evidence_packet module spec from {module_path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_evidence_packet_module = _load_evidence_packet_module()
validate_evidence_packet = _evidence_packet_module.validate_evidence_packet
render_evidence_packet_markdown = _evidence_packet_module.render_evidence_packet_markdown
EvidencePacketValidationError = _evidence_packet_module.EvidencePacketValidationError


# ---------------------------------------------------------------------------
# Packets directory resolver — reads from settings each call so test-time
# monkeypatching of ``settings.harness_evidence_packets_dir`` takes effect.
# ---------------------------------------------------------------------------


def _packets_dir() -> Path:
    """Return the configured packets directory as a resolved Path."""
    return Path(settings.harness_evidence_packets_dir).resolve()


def _validate_trace_id(trace_id: str) -> None:
    """Raise HTTP 400 if ``trace_id`` does not match the strict character set.

    This is the first layer of the path-traversal guard. It runs before any
    filesystem access. The detail is reserved-language neutral.
    """
    if not _TRACE_ID_RE.match(trace_id):
        raise HTTPException(status_code=400, detail="trace_id is not well-formed")


def _resolve_packet_path(trace_id: str, suffix: str) -> Path:
    """Resolve ``{packets_dir}/{trace_id}.{suffix}`` with containment check.

    The trace_id is already regex-validated when this is called, but we still
    perform the ``relative_to`` containment check as a defence-in-depth layer
    (``Path.resolve().relative_to(packets_dir.resolve())``). Anything that
    resolves outside the packets directory raises HTTP 400.
    """
    packets_dir = _packets_dir()
    candidate = (packets_dir / f"{trace_id}.{suffix}").resolve()
    try:
        candidate.relative_to(packets_dir)
    except ValueError:
        # The regex guard should make this branch unreachable, but it is
        # the load-bearing safety check — never remove.
        raise HTTPException(status_code=400, detail="trace_id is not well-formed")
    return candidate


def _enforce_size_cap(path: Path) -> None:
    """Raise HTTP 413 if the file exceeds the size cap."""
    try:
        size = path.stat().st_size
    except OSError:
        # The size check runs after we have confirmed the file exists, so an
        # OSError here is genuinely a server-side filesystem issue.
        logger.error("harness_evidence stat failed for %s", path)
        raise HTTPException(status_code=500, detail="evidence packet read failed")
    if size > _MAX_PACKET_BYTES:
        raise HTTPException(status_code=413, detail="evidence packet exceeds size cap")


def _load_and_validate_packet(trace_id: str) -> dict[str, Any]:
    """Return the validated packet dict for ``trace_id``, or raise the right HTTPException.

    Raises:
        HTTPException(400) — trace_id is malformed (caller usually validates first).
        HTTPException(404) — packet file does not exist.
        HTTPException(413) — packet file exceeds the size cap.
        HTTPException(500) — packet file is corrupted / fails schema validation.
    """
    _validate_trace_id(trace_id)
    json_path = _resolve_packet_path(trace_id, "json")
    if not json_path.is_file():
        raise HTTPException(status_code=404, detail="evidence packet not found")
    _enforce_size_cap(json_path)
    try:
        raw = json_path.read_text(encoding="utf-8")
        packet = json.loads(raw)
    except (OSError, UnicodeDecodeError) as exc:
        logger.error("harness_evidence read failed for %s: %s", trace_id, exc)
        raise HTTPException(status_code=500, detail="evidence packet read failed")
    except json.JSONDecodeError as exc:
        logger.error("harness_evidence JSON decode failed for %s: %s", trace_id, exc)
        raise HTTPException(status_code=500, detail="evidence packet validation failed")
    try:
        validate_evidence_packet(packet)
    except EvidencePacketValidationError as exc:
        # Internal audit log carries the detail; the client only sees the
        # generic reserved-language message. Schema details are not leaked.
        logger.error("harness_evidence schema validation failed for %s: %s", trace_id, exc)
        raise HTTPException(status_code=500, detail="evidence packet validation failed")
    return packet


def _load_markdown(trace_id: str, packet: dict[str, Any]) -> str:
    """Return the Markdown for ``trace_id``.

    If ``{trace_id}.md`` exists on disk we serve it verbatim (subject to the
    same size cap). Otherwise we render it on the fly via the Stage 21A
    ``render_evidence_packet_markdown`` helper.
    """
    md_path = _resolve_packet_path(trace_id, "md")
    if md_path.is_file():
        _enforce_size_cap(md_path)
        try:
            return md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.error("harness_evidence md read failed for %s: %s", trace_id, exc)
            raise HTTPException(status_code=500, detail="evidence packet read failed")
    # Render on the fly. render_evidence_packet_markdown re-runs validation
    # internally; the packet was just validated, so this is a fast path.
    try:
        return render_evidence_packet_markdown(packet)
    except EvidencePacketValidationError as exc:
        logger.error("harness_evidence render failed for %s: %s", trace_id, exc)
        raise HTTPException(status_code=500, detail="evidence packet validation failed")


# ---------------------------------------------------------------------------
# Route handlers.
# ---------------------------------------------------------------------------


@router.get("/{trace_id}")
async def get_harness_evidence_packet(trace_id: str) -> dict[str, Any]:
    """Return the CAS Harness EvidencePacket v1 JSON for ``trace_id``.

    Auth: required (JWT Bearer, enforced by ``JWTAuthMiddleware``).

    Boundary properties:

    * ``trace_id`` is regex-validated before any filesystem access (400 on
      malformed input).
    * Resolved path must be contained under the configured packets directory.
    * Files larger than 8 MiB return 413 unread.
    * Every packet round-trips through ``validate_evidence_packet``; a
      schema failure returns 500 with a generic reserved-language message.
    * Returns 404 with detail ``evidence packet not found`` when no packet
      file exists for the given trace_id.

    Production note: this is a file-backed MVP store. The canonical packet
    store is a follow-on to this ticket.
    """
    return _load_and_validate_packet(trace_id)


@router.get("/{trace_id}/markdown", response_class=PlainTextResponse)
async def get_harness_evidence_packet_markdown(trace_id: str) -> PlainTextResponse:
    """Return the reviewer-readable Markdown for ``trace_id``.

    Content-Type is ``text/markdown; charset=utf-8``. If ``{trace_id}.md``
    exists on disk it is served verbatim; otherwise the Markdown is rendered
    on the fly via the Stage 21A ``render_evidence_packet_markdown`` helper.

    Auth, regex validation, containment check, size cap, and schema
    round-trip identical to ``GET /{trace_id}``.
    """
    packet = _load_and_validate_packet(trace_id)
    markdown = _load_markdown(trace_id, packet)
    return PlainTextResponse(content=markdown, media_type="text/markdown; charset=utf-8")
