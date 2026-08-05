"""Shared knob-resolution helpers — single source of truth for what the
worker actually uses from ``req.method_config["knobs"]``.

This module exists so that:

  * ``pythia_runner.run_pythia`` (real model)
  * ``event_stream.stream_fake_trace`` (demo mode)
  * the ``KnobResolutionEvent`` echoed to the cockpit diagnostic disclosure

all resolve knobs the same way (defaults → coercion → clamp), and the
echo cannot drift out of sync with the runner. Tests pin the values
emitted into ``KnobResolutionEvent`` against the values the runner uses,
which means a future refactor that loses knob plumbing will break a
test rather than silently downgrade to a window-dressing toggle.

The shape of ``resolve_knobs`` mirrors the ``KnobResolutionEvent``
contract — keyed by ``method_id``, each value is a dict of
``knob_name -> resolved_value``. Only knobs the worker actually
consumes are present; knobs that exist on the panel but aren't wired
to a computation path are deliberately omitted so the disclosure
cannot give a false-positive "✓" against a no-op knob.
"""

from __future__ import annotations

from typing import Any

from ..schemas.requests import CreateSessionRequest
from .cover_library import COVER_LIBRARY


# -- defaults (post-coercion values the worker reaches for) ----------------

DEFAULT_FOUNDATION_TOP_K = 8
DEFAULT_RPM_THRESHOLD = 0.0
DEFAULT_ERASER_GAIN = 1.0
DEFAULT_ERASER_DRIVE = "F1"
DEFAULT_INVERSION_SEVERITY_THRESHOLD = 0.0


def raw_knobs(req: CreateSessionRequest) -> dict[str, dict[str, Any]]:
    """Pull the per-method knob bag from ``method_config`` defensively."""
    if not req.method_config:
        return {}
    raw = req.method_config.get("knobs", {})
    if not isinstance(raw, dict):
        return {}
    # Filter to mappings so a malformed UI payload can't crash the worker.
    return {k: v for k, v in raw.items() if isinstance(v, dict)}


def enabled_methods(req: CreateSessionRequest) -> set[str]:
    if not req.method_config:
        return set()
    raw = req.method_config.get("enabled_methods", [])
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw}


# -- per-knob resolution ---------------------------------------------------


def resolve_top_k(raw: Any) -> int:
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_FOUNDATION_TOP_K
    return parsed if parsed > 0 else DEFAULT_FOUNDATION_TOP_K


def resolve_layer_range(raw: Any) -> list[int]:
    """Coerce the layer-range knob into a sorted list of non-negative ints.

    Accepts:
      * list of ints / numeric strings -> [int, int, ...]
      * [low, high] inclusive pair -> [low, low+1, ..., high]
      * anything else -> []
    Empty list means "no layer filter" downstream (use all layers).
    """
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)):
        return []
    # If it looks like a [low, high] pair, expand it.
    if len(raw) == 2 and all(isinstance(x, (int, float)) for x in raw):
        low, high = int(raw[0]), int(raw[1])
        if low <= high:
            return [i for i in range(low, high + 1) if i >= 0]
        return []
    out: list[int] = []
    for item in raw:
        try:
            n = int(item)
        except (TypeError, ValueError):
            continue
        if n >= 0:
            out.append(n)
    return sorted(set(out))


def resolve_rpm_threshold(raw: Any) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_RPM_THRESHOLD
    return max(0.0, min(1.0, v))


def resolve_inversion_threshold(raw: Any) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_INVERSION_SEVERITY_THRESHOLD
    return max(0.0, min(1.0, v))


def resolve_eraser_gain(raw: Any) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_ERASER_GAIN
    return max(0.0, v)


def resolve_drive(raw: Any) -> str:
    """Coerce a drive selector into a known drive string.

    Falls back to the default ``F1`` when missing or malformed.
    Does NOT enforce membership in ``COVER_LIBRARY``. The runner preserves
    the requested drive and emits a typed ``REJECTED_NO_COORDINATES`` result;
    an unsupported drive is never treated as a successful no-op.
    """
    if isinstance(raw, str) and raw.startswith("F"):
        return raw
    return DEFAULT_ERASER_DRIVE


# -- aggregate resolution echoed back to the cockpit ----------------------


def resolve_knobs(req: CreateSessionRequest) -> dict[str, dict[str, Any]]:
    """Resolve every knob the worker consumes, return the echo shape.

    Only knobs that influence at least one computation path are
    included. The "Knob diagnostic" disclosure in the cockpit relies
    on this list — if a method is missing here, the disclosure shows
    "(no resolved knobs)" rather than fabricating a match against a
    no-op channel.
    """
    raw = raw_knobs(req)
    methods = enabled_methods(req)

    out: dict[str, dict[str, Any]] = {}

    # foundation_probe — controls top-K activated neurons + the layer
    # subset that contributes them.
    fp = raw.get("foundation_probe", {})
    out["foundation_probe"] = {
        "top_k": resolve_top_k(fp.get("top_k")),
        "layer_range": resolve_layer_range(fp.get("layer_range")),
    }

    # rpm_gate_check — Mode 7 edge threshold.
    rpm = raw.get("rpm_gate_check", {})
    out["rpm_gate_check"] = {
        "strictness_threshold": resolve_rpm_threshold(rpm.get("strictness_threshold")),
    }

    # inversion_scan — only meaningful when method is enabled, but we
    # always echo the resolved threshold so the cockpit can show "Sent
    # 0.7 / Resolved 0.7" alongside the "not active" state.
    inv = raw.get("inversion_scan", {})
    out["inversion_scan"] = {
        "severity_threshold": resolve_inversion_threshold(inv.get("severity_threshold")),
        "active": "inversion_scan" in methods,
    }

    # drive_local_eraser — drive + gain. Cover-set membership is
    # checked via ``COVER_LIBRARY`` so the cockpit can flag drives
    # that will receive a typed fail-closed intervention result.
    eraser = raw.get("drive_local_eraser", {})
    drive = resolve_drive(eraser.get("drive"))
    out["drive_local_eraser"] = {
        "drive": drive,
        "gain": resolve_eraser_gain(eraser.get("gain")),
        "cover_available": drive in COVER_LIBRARY,
        "active": "drive_local_eraser" in methods,
    }

    # blindspot_detection — drive scope used by the cover overlay.
    bs = raw.get("blindspot_detection", {})
    bs_drive = bs.get("scope") or bs.get("drive")
    if bs_drive == "all_7":
        out["blindspot_detection"] = {
            "scope": "all_7",
            "drive": "all_7",
            "cover_available": True,
        }
        return out
    bs_resolved = resolve_drive(bs_drive)
    out["blindspot_detection"] = {
        "scope": bs_resolved,
        "drive": bs_resolved,
        "cover_available": bs_resolved in COVER_LIBRARY,
    }

    return out
