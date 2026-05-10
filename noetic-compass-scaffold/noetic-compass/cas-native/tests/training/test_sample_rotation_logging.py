"""Tests for the rotated-sample telemetry path in train_native_nl_gen.

Per project memory `feedback_rotating_sample_prompts_required.md`
(2026-05-08): any trainer with mid-run sample telemetry MUST rotate
through diverse records and emit per-event ``record_id``, ``task``,
and ``category`` so a single bad record can't masquerade as systemic
failure (cas-native v1 retrain near-miss 2026-05-08).

These unit tests cover the helpers that pull task/category metadata
out of records (``_record_task_type`` / ``_record_category``) and
the event emitter that writes them into ``sample_reply`` events.
The rotation pool resolution itself is exercised by the CLI parser
via the ``--sample-record-indices`` flag and the integration smoke
in v1c_post_bundle_smoke (this file covers the unit-level contracts
those layers depend on).
"""
from __future__ import annotations

import io
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(ROOT / "cas-native")]
sys.modules.setdefault("cas_native", pkg)
sys.path.insert(0, str(ROOT))

from cas_native.training.train_native_nl_gen import (  # noqa: E402
    _record_category,
    _record_task_type,
    build_parser,
    emit_sample_reply_event,
    emit_sample_reply_error_event,
)


def test_record_task_type_prefers_v1mix_then_task_then_slot():
    rec = {
        "v1mix_task_type": "cas_to_english",
        "task_type": "secondary",
        "slot": "secondary_slot",
    }
    assert _record_task_type(rec) == "cas_to_english"

    rec = {"task_type": "invalid_to_explanation", "slot": "slot_x"}
    assert _record_task_type(rec) == "invalid_to_explanation"

    rec = {"slot": "english_to_cas"}
    assert _record_task_type(rec) == "english_to_cas"


def test_record_task_type_returns_empty_when_no_signal():
    assert _record_task_type({}) == ""
    assert _record_task_type({"v1mix_task_type": ""}) == ""
    assert _record_task_type({"v1mix_task_type": "   "}) == ""
    assert _record_task_type({"v1mix_task_type": 123}) == ""


def test_record_category_handles_present_and_absent():
    assert _record_category({"category": "rpm_chain"}) == "rpm_chain"
    assert _record_category({"category": ""}) == ""
    assert _record_category({}) == ""
    assert _record_category({"category": None}) == ""


def test_emit_sample_reply_event_includes_task_and_category():
    """sample_reply events must carry task_type + category for traceability.

    The rotated-sample-prompts memory mandates these fields so a single
    record's behavior cannot masquerade as systemic failure across the
    whole rotation pool.
    """
    record = {
        "id": "v1mix_paraphrase_4242",
        "v1mix_task_type": "cas_to_english",
        "category": "compound_state",
        "prompt_text": "Translate the CAS expression below.",
        "reply_text": "Something composed of...",
        "cas_expression": "^7^C_{F2}|T",
        "register": "T",
    }
    generated = {
        "reply_text": "Practice makes perfect for cognitive wisdom.",
        "n_steps": 12,
        "stopped_on_eos": True,
        "config": {"sampling": "greedy"},
        "token_ids": list(range(64)),
    }
    buf = io.StringIO()
    event = emit_sample_reply_event(
        event_id="event-abc",
        checkpoint_id="ckpt-xyz",
        step=1234,
        epoch=2,
        sample_index=7,
        record=record,
        generated=generated,
        out_stream=buf,
    )
    # Returned event mirrors the JSON line.
    assert event["task_type"] == "cas_to_english"
    assert event["category"] == "compound_state"
    assert event["record_id"] == "v1mix_paraphrase_4242"
    assert event["sample_index"] == 7
    # Stream line is parseable JSON with the same fields.
    line = buf.getvalue().strip()
    parsed = json.loads(line)
    assert parsed["task_type"] == "cas_to_english"
    assert parsed["category"] == "compound_state"
    assert parsed["record_id"] == "v1mix_paraphrase_4242"


def test_emit_sample_reply_error_event_also_carries_task_and_category():
    """Errors during sampling must also pin which record/task/category
    failed so the rotation can be audited post-run."""
    record = {
        "id": "rec_err",
        "v1mix_task_type": "invalid_to_explanation",
        "category": "set_constructor",
        "prompt_text": "explain",
        "cas_expression": "let X = ^99^P; X -> Y",
    }
    buf = io.StringIO()
    event = emit_sample_reply_error_event(
        event_id="evt-err",
        checkpoint_id="ckpt-1",
        step=10,
        epoch=0,
        sample_index=3,
        record=record,
        error=ValueError("bad expression"),
        out_stream=buf,
    )
    assert event["task_type"] == "invalid_to_explanation"
    assert event["category"] == "set_constructor"
    assert event["error_type"] == "ValueError"
    assert event["sample_index"] == 3


def test_parser_accepts_sample_record_indices_csv():
    """``--sample-record-indices`` is the canonical rotation flag.

    Whitespace tolerance, trailing commas, and integer parsing are all
    deferred until run-time resolution so the parser only stores the
    raw string. This test pins the contract.
    """
    args = build_parser().parse_args([
        "--data-path", "X",
        "--output-dir", "Y",
        "--sample-every-steps", "50",
        "--sample-record-indices", "3, 7, 19, 41",
    ])
    assert args.sample_record_indices == "3, 7, 19, 41"
    # Legacy --sample-record-index keeps working when --sample-record-indices empty.
    args2 = build_parser().parse_args([
        "--data-path", "X",
        "--output-dir", "Y",
        "--sample-every-steps", "50",
        "--sample-record-index", "11",
    ])
    assert args2.sample_record_indices == ""
    assert args2.sample_record_index == 11


def test_parser_default_sample_record_indices_is_empty_string():
    """Default leaves rotation off so existing runs (incl. prior smoke
    invocations) keep behaving identically."""
    args = build_parser().parse_args([
        "--data-path", "X",
        "--output-dir", "Y",
    ])
    assert args.sample_record_indices == ""
    assert args.sample_record_index == 0
