"""Traceability v0 — the structured trace every CAS reply ships with.

Codex 2026-05-13 audit `8e0ae2d`: "Traceability v0 first. Then Step 5B
NL bridge. Why: traceability is the thing that makes CAS different.
Once trace v0 exists, every CAS answer and every future NL answer can
show what CAS read / what the model generated / source references
carried over / missed / slot pattern / confidence-warnings / Thought
Tree JSON."

This module produces the canonical trace dict per
`decisions.md` 2026-05-13T17:30Z. Sibling to:
- `cas_trace_schema_v0_2026_05_13.md` — the bigger Mode 7 spec
- `plain_english.py` — translator the trace reuses
- `thought_tree.py` — node-edge builder the trace embeds

Public surface:
- `build_v0_trace(report) -> dict` — pure function, JSON-serializable

Bounded scope (per `decisions.md` 2026-05-13T17:30Z):
- v0 only. No per-position lm_logits / p_copy tensors (Mode 7 full).
- No activation hooks. No simplex trajectory. No layer L2.
- No Inversion Replay alternates (ghost branches).
- No visual rendering — emits JSON the Atlas UI consumes.

Discipline (mirrors Plain English Mode "does not lie" rule):
- Every field in the trace is derivable from a field in the input
  report. The trace NEVER fabricates.
- Warning flags fire only when their structural condition is met.
- Object traceability is mandatory: trace_id + created_at + version
  (per user memory `feedback_object_traceability_required.md`).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from cas_native.inference.plain_english import human_slot_label
from cas_native.inference.thought_tree import build_thought_tree


SCHEMA_VERSION = "traceability_v0"


def _iso_now() -> str:
    """Return the current UTC time as a stable ISO8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _humanized_slot_counts(counts: dict[str, Any]) -> dict[str, int]:
    """Map raw slot-id keys (string ints from JSON dumps) to human labels.
    Falls back to the raw id label for unknown slot ids — never fabricates."""
    out: dict[str, int] = {}
    if not isinstance(counts, dict):
        return out
    for raw_id, count in counts.items():
        try:
            slot_id = int(raw_id)
        except (TypeError, ValueError):
            out[str(raw_id)] = int(count) if isinstance(count, (int, float)) else 0
            continue
        label = human_slot_label(slot_id)
        # Aggregate when labels collide (shouldn't happen with documented ids
        # but stays safe).
        out[label] = out.get(label, 0) + (int(count) if isinstance(count, (int, float)) else 0)
    return out


def _per_identifier_entries(
    expected: list[str], emitted: list[str], copied: list[str],
) -> list[dict[str, Any]]:
    """Per-expected-identifier breakdown. Each entry shows the position
    in input (= index in `expected`) and position in output. Handles
    REPEATED IDENTIFIERS correctly per Codex audit `95fcecf`: the Nth
    occurrence of identifier X in `expected` maps to the Nth occurrence
    in `emitted` (or None if the model emitted fewer copies than the
    input had references).

    Examples:
      expected=['a','a','b'], emitted=['a','b']
        → [{a, copied, in=0, out=0},
           {a, missed, in=1, out=None},
           {b, copied, in=2, out=1}]
    """
    copied_set = set(copied)
    # Track per-identifier usage of emitted positions so repeats consume
    # distinct output positions, not all-point-at-position-0.
    used_emitted_positions: dict[str, list[int]] = {}
    for j, e in enumerate(emitted):
        used_emitted_positions.setdefault(e, []).append(j)
    # Mutable cursor over each identifier's emitted positions
    cursor: dict[str, int] = {}

    entries: list[dict[str, Any]] = []
    for in_pos, ident in enumerate(expected):
        positions = used_emitted_positions.get(ident, [])
        next_idx = cursor.get(ident, 0)
        if next_idx < len(positions):
            out_pos: Optional[int] = positions[next_idx]
            cursor[ident] = next_idx + 1
            # Status is "copied" if the model emitted this Nth
            # occurrence; "missed" if it ran out.
            status = "copied"
        else:
            out_pos = None
            # Identifier appears in copied set somewhere → distinguish
            # "model emitted SOME copies but not this Nth one" (missed
            # at this position) from "never emitted at all". Both render
            # as missed in v0; the difference is observable in the
            # position fields.
            status = "missed"
        entries.append({
            "identifier": ident,
            "status": status,
            "position_in_input": in_pos,
            "position_in_output": out_pos,
            # NOTE: copied_set membership is preserved as a separate
            # boolean so consumers can distinguish "appears at least
            # once in output" from "this specific occurrence was copied".
            "identifier_ever_copied": ident in copied_set,
        })
    return entries


def _warning_flags(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the structured warning list. Each flag fires only when its
    condition is met. UI consumers display these as badges.

    Per Codex audit `95fcecf` 2026-05-13: identifier-related warnings
    MUST NOT fire when the input contains no identifiers (like the bare
    state expression `^3^P|A`). Identifier checks are gated on
    `len(expected) > 0` explicitly.

    Severity bands:
      info    — informational, structural observation
      warning — output may be incomplete or low-confidence
      error   — gate-level failure (e.g. crashed mid-decode)
    """
    flags: list[dict[str, Any]] = []
    idents = report.get("identifiers", {}) or {}
    coverage = idents.get("coverage")
    expected = idents.get("expected", []) or []
    emitted = idents.get("emitted", []) or []
    copied = idents.get("copied", []) or []
    gates = report.get("gates", {}) or {}
    model = report.get("model", {}) or {}

    # Identifier-related warnings: only fire when the input HAD
    # identifiers to copy. A bare state expression like `^3^P|A` has
    # zero expected identifiers and should not produce coverage warnings.
    input_has_identifiers = len(expected) > 0

    if input_has_identifiers:
        if isinstance(coverage, (int, float)) and 0.0 < coverage < 0.5:
            flags.append({
                "kind": "low_coverage",
                "severity": "warning",
                "message": (
                    f"Only {len(copied)} of {len(expected)} source "
                    f"references were carried over."
                ),
            })
        if len(emitted) == 0:
            flags.append({
                "kind": "no_identifiers_emitted",
                "severity": "warning",
                "message": (
                    "The output did not contain any of the expected "
                    "source references."
                ),
            })

    # Structural warnings independent of identifier presence:
    decode_secs = model.get("decode_seconds")
    if isinstance(decode_secs, (int, float)) and decode_secs > 10.0:
        flags.append({
            "kind": "slow_decode",
            "severity": "info",
            "message": (
                f"Decoding took {decode_secs:.1f}s, longer than usual. "
                f"The model may have been uncertain."
            ),
        })
    if gates.get("no_crash") is False:
        flags.append({
            "kind": "decode_crash",
            "severity": "error",
            "message": "The model decode path raised an exception.",
        })
    if gates.get("generated_non_empty") is False:
        flags.append({
            "kind": "empty_output",
            "severity": "error",
            "message": "The model generated no output.",
        })

    return flags


def _source_tokens(cas_expression: str) -> list[dict[str, Any]]:
    """Return whitespace-tokenized source CAS with stable indexes.

    Per Codex audit `95fcecf` 2026-05-13: source tokens need indexes,
    not just strings. UI consumers (Thought Tree, Atlas) need to
    attribute output positions to specific source token indexes for
    visual lines from output → source.

    NOT the HybridCASTokenizer output — the UI consumer wants
    human-readable tokens, not BPE pieces.

    Returns list of `{"index": int, "token": str}` dicts, JSON-ready.
    """
    if not cas_expression:
        return []
    return [
        {"index": i, "token": tok}
        for i, tok in enumerate(cas_expression.split())
    ]


def build_v0_trace(report: dict[str, Any]) -> dict[str, Any]:
    """Build a Traceability v0 dict from a cas-explain report.

    Args:
        report: dict returned by `cas_cli._cmd_explain` (or the smoke
            harness). Must contain `input_cas_expression`,
            `generated_english`, `identifiers`, `slot_summary`,
            `plain_english`. Other fields are tolerated.

    Returns:
        A JSON-serializable dict matching the v0 schema. The cas-explain
        report can embed this dict under `traceability_v0` so saved
        `.tmp/cas_explain_*.json` files contain everything the UI
        consumer needs.
    """
    cas_expression = report.get("input_cas_expression") or ""
    generated = report.get("generated_english") or ""
    n_tokens = report.get("n_tokens_generated") or 0

    idents = report.get("identifiers", {}) or {}
    expected = list(idents.get("expected", []) or [])
    emitted = list(idents.get("emitted", []) or [])
    copied = list(idents.get("copied", []) or [])
    missing = list(idents.get("missing", []) or [])
    coverage = idents.get("coverage")

    slot_summary = report.get("slot_summary", {}) or {}
    plain = report.get("plain_english", {}) or {}

    # Caveats: any plain-english caveat plus a placeholder for future
    # warning text. The structured warning_flags are surfaced
    # separately for UI badges.
    caveats: list[str] = []
    if cav := plain.get("confidence_caveat"):
        caveats.append(cav)

    trace = {
        "schema_version": SCHEMA_VERSION,
        "trace_id": str(uuid.uuid4()),
        "created_at": _iso_now(),
        "input": {
            "cas_expression": cas_expression,
            "source_tokens": _source_tokens(cas_expression),
        },
        "output": {
            "english": generated,
            "n_tokens": int(n_tokens) if isinstance(n_tokens, (int, float)) else 0,
        },
        "copy": {
            "copied_identifiers": copied,
            "missed_identifiers": missing,
            "coverage": coverage,
            "per_identifier": _per_identifier_entries(expected, emitted, copied),
        },
        "slot_trace": {
            "length": slot_summary.get("length", 0) or 0,
            "slot_counts_by_label": _humanized_slot_counts(
                slot_summary.get("counts", {}) or {}
            ),
            "longest_stage_var_run": slot_summary.get("longest_stage_var_run", 0) or 0,
            # raw_trace is NOT in the cas-explain report today (only the
            # summary is); v0 records this as None so the field exists
            # but is honestly empty. Mode 7 full will populate it from
            # the live decode path.
            "raw_trace": report.get("slot_type_trace"),
        },
        "confidence": {
            "qualitative_coverage": plain.get("qualitative_coverage", "unknown"),
            "slot_quality": plain.get("qualitative_slot_quality", "unknown structure"),
            "caveats": caveats,
            "warning_flags": _warning_flags(report),
        },
        "thought_tree": build_thought_tree(report),
    }
    return trace


def trace_to_json(trace: dict[str, Any]) -> str:
    """Serialize a v0 trace to a stable JSON string. The UI consumer can
    parse this directly; the `default=str` fallback handles any
    non-JSON-native values that slip through."""
    return json.dumps(trace, indent=2, default=str, sort_keys=False)
