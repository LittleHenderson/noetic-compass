"""Tests for the `cas atlas-save` subcommand (Agent D, Atlas v0).

Closes the REPL → Atlas pipeline: a traceability_v0 trace produced by
`cas explain` (or piped from stdin) gets parked in the directory the
dashboard viewer reads.

All tests are lightweight — they don't load torch / the Stage 3
checkpoint / the dev pack. Atlas-save is pure stdlib JSON shuffling.
"""
from __future__ import annotations

import io
import json
import sys
import uuid
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import pytest

from cas_native.inference import cas_cli


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_valid_trace(
    *,
    trace_id: str | None = None,
    created_at: str = "2026-05-13T17:30:00Z",
    node_count: int = 7,
    edge_count: int = 6,
) -> dict:
    """A minimal but structurally complete traceability_v0 trace."""
    return {
        "schema_version": "traceability_v0",
        "trace_id": trace_id or str(uuid.uuid4()),
        "created_at": created_at,
        "input": {
            "input_kind": "cas_expression",
            "cas_expression": "^3^P|A",
            "source_tokens": [{"index": 0, "token": "^3^P|A"}],
        },
        "output": {
            "english": "principled aversion in the analytical register",
            "n_tokens": 8,
        },
        "copy": {
            "copied_identifiers": [],
            "missed_identifiers": [],
            "coverage": None,
            "per_identifier": [],
        },
        "slot_trace": {
            "length": 12,
            "slot_counts_by_label": {"plain": 12},
            "longest_stage_var_run": 0,
            "raw_trace": None,
        },
        "confidence": {
            "qualitative_coverage": "unknown",
            "slot_quality": "unknown structure",
            "caveats": [],
            "warning_flags": [],
        },
        "thought_tree": {
            "root": {"id": "root", "label": "ROOT", "children": []},
            "nodes": [{"id": "root", "label": "ROOT"}],
            "edges": [],
            "node_count": node_count,
            "edge_count": edge_count,
        },
    }


def _make_explain_report_with_embedded_trace() -> dict:
    """Shape of `output` from `cas_cli._cmd_explain` — embeds the
    traceability_v0 dict under `traceability_v0`. Tests that
    `atlas-save` unwraps it automatically."""
    return {
        "command": "cas explain",
        "version": 1,
        "input_cas_expression": "^3^P|A",
        "generated_english": "stub",
        "traceability_v0": _make_valid_trace(),
    }


# ---------------------------------------------------------------------------
# Dispatcher / banner registration
# ---------------------------------------------------------------------------

def test_atlas_save_registered_in_dispatcher():
    """The subcommand must be discoverable from the COMMANDS table."""
    assert "atlas-save" in cas_cli.COMMANDS
    assert callable(cas_cli.COMMANDS["atlas-save"])
    assert cas_cli.COMMANDS["atlas-save"] is cas_cli._cmd_atlas_save


def test_atlas_save_in_help_banner():
    """`cas help` should advertise the new subcommand."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cas_cli.main(["help"])
    out = buf.getvalue()
    assert rc == 0
    assert "atlas-save" in out


def test_atlas_save_missing_from_arg_errors(tmp_path, monkeypatch):
    """Calling `atlas-save` with no source returns non-zero and prints
    a message naming --from."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    err_buf = io.StringIO()
    out_buf = io.StringIO()
    with redirect_stderr(err_buf), redirect_stdout(out_buf):
        rc = cas_cli.main(["atlas-save"])
    err = err_buf.getvalue()
    assert rc != 0
    assert "--from" in err


# ---------------------------------------------------------------------------
# Reading a valid trace from a file
# ---------------------------------------------------------------------------

def test_save_valid_trace_from_file(tmp_path):
    """Read a valid trace from a file; save it into a temp out-dir;
    confirm the file is on disk with the documented prefix."""
    trace = _make_valid_trace()
    src = tmp_path / "trace_input.json"
    src.write_text(json.dumps(trace), encoding="utf-8")

    out_dir = tmp_path / "atlas_traces"
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", str(src),
            "--out-dir", str(out_dir),
        ])
    assert rc == 0, f"err={err_buf.getvalue()!r}"

    saved_files = list(out_dir.glob("trace_*.json"))
    assert len(saved_files) == 1, (
        f"expected exactly one trace_*.json; got {saved_files!r}"
    )
    saved_path = saved_files[0]
    assert saved_path.name.startswith("trace_")
    assert saved_path.suffix == ".json"

    # The saved JSON must round-trip cleanly.
    loaded = json.loads(saved_path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "traceability_v0"
    assert loaded["trace_id"] == trace["trace_id"]

    # Stdout should print the path (first line) and a summary mentioning
    # node/edge counts.
    out = out_buf.getvalue()
    assert str(saved_path) in out
    assert "nodes" in out and "edges" in out


def test_save_filename_pattern_matches_trace_glob(tmp_path):
    """`trace_*.json` is the documented glob for the viewer; pin it."""
    trace = _make_valid_trace(trace_id="abc-123", created_at="2026-05-13T17:30:00Z")
    src = tmp_path / "in.json"
    src.write_text(json.dumps(trace), encoding="utf-8")
    out_dir = tmp_path / "atlas"

    out_buf = io.StringIO()
    with redirect_stdout(out_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", str(src),
            "--out-dir", str(out_dir),
        ])
    assert rc == 0
    saved = list(out_dir.glob("trace_*.json"))
    assert saved, f"no trace_*.json files in {out_dir}"
    # Filename should embed the trace_id and a (filename-safe) timestamp.
    name = saved[0].name
    assert "abc-123" in name
    # Colons stripped (Windows filename safety).
    assert ":" not in name


def test_save_custom_filename_honored(tmp_path):
    """`--filename` override is respected verbatim."""
    trace = _make_valid_trace()
    src = tmp_path / "in.json"
    src.write_text(json.dumps(trace), encoding="utf-8")
    out_dir = tmp_path / "atlas"
    out_buf = io.StringIO()
    with redirect_stdout(out_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", str(src),
            "--out-dir", str(out_dir),
            "--filename", "my_pinned_trace.json",
        ])
    assert rc == 0
    assert (out_dir / "my_pinned_trace.json").exists()


# ---------------------------------------------------------------------------
# Stdin path
# ---------------------------------------------------------------------------

def test_save_reads_stdin_dash(tmp_path, monkeypatch):
    """`--from -` reads from stdin and saves correctly."""
    trace = _make_valid_trace()
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(trace)))

    out_dir = tmp_path / "atlas_stdin"
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", "-",
            "--out-dir", str(out_dir),
        ])
    assert rc == 0, f"err={err_buf.getvalue()!r}"
    saved = list(out_dir.glob("trace_*.json"))
    assert len(saved) == 1
    loaded = json.loads(saved[0].read_text(encoding="utf-8"))
    assert loaded["trace_id"] == trace["trace_id"]


def test_save_reads_stdin_uppercase_keyword(tmp_path, monkeypatch):
    """`--from STDIN` is also accepted (case-friendly UX)."""
    trace = _make_valid_trace()
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(trace)))
    out_dir = tmp_path / "atlas_stdin_caps"
    out_buf = io.StringIO()
    with redirect_stdout(out_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", "STDIN",
            "--out-dir", str(out_dir),
        ])
    assert rc == 0
    assert list(out_dir.glob("trace_*.json"))


def test_save_unwraps_embedded_explain_report(tmp_path):
    """`cas explain --json` output embeds the trace under
    `traceability_v0`. `atlas-save` should unwrap it so the pipe
    `cas explain ... | cas atlas-save --from -` Just Works."""
    embedded = _make_explain_report_with_embedded_trace()
    src = tmp_path / "explain_report.json"
    src.write_text(json.dumps(embedded), encoding="utf-8")
    out_dir = tmp_path / "atlas_unwrap"

    out_buf = io.StringIO()
    with redirect_stdout(out_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", str(src),
            "--out-dir", str(out_dir),
        ])
    assert rc == 0
    saved = list(out_dir.glob("trace_*.json"))
    assert len(saved) == 1
    loaded = json.loads(saved[0].read_text(encoding="utf-8"))
    # Saved file is the BARE trace, not the explain report.
    assert loaded["schema_version"] == "traceability_v0"
    assert "command" not in loaded


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_validate_strict_wrong_schema_version_exits_2(tmp_path):
    """Wrong schema_version under --validate-strict → exit code 2."""
    trace = _make_valid_trace()
    trace["schema_version"] = "trace_v0"  # the deprecated name
    src = tmp_path / "bad_schema.json"
    src.write_text(json.dumps(trace), encoding="utf-8")
    out_dir = tmp_path / "atlas"

    err_buf = io.StringIO()
    out_buf = io.StringIO()
    with redirect_stderr(err_buf), redirect_stdout(out_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", str(src),
            "--out-dir", str(out_dir),
            "--validate-strict",
        ])
    assert rc == 2
    assert "schema_version" in err_buf.getvalue()
    # And we did NOT write a file under strict mode.
    assert not list(out_dir.glob("trace_*.json"))


def test_validate_strict_missing_key_exits_2(tmp_path):
    """Missing required key under --validate-strict → exit code 2."""
    trace = _make_valid_trace()
    del trace["thought_tree"]
    src = tmp_path / "missing_key.json"
    src.write_text(json.dumps(trace), encoding="utf-8")
    out_dir = tmp_path / "atlas"

    err_buf = io.StringIO()
    out_buf = io.StringIO()
    with redirect_stderr(err_buf), redirect_stdout(out_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", str(src),
            "--out-dir", str(out_dir),
            "--validate-strict",
        ])
    assert rc == 2
    err = err_buf.getvalue()
    assert "missing required" in err.lower()
    assert "thought_tree" in err


def test_partial_trace_saved_without_strict_with_warning(tmp_path):
    """Without --validate-strict, a partial trace SAVES but stderr
    contains a warning. Exit code 0 — graceful degradation."""
    trace = _make_valid_trace()
    del trace["thought_tree"]
    src = tmp_path / "partial.json"
    src.write_text(json.dumps(trace), encoding="utf-8")
    out_dir = tmp_path / "atlas_partial"

    err_buf = io.StringIO()
    out_buf = io.StringIO()
    with redirect_stderr(err_buf), redirect_stdout(out_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", str(src),
            "--out-dir", str(out_dir),
        ])
    assert rc == 0
    err = err_buf.getvalue()
    assert "warning" in err.lower()
    saved = list(out_dir.glob("trace_*.json"))
    assert len(saved) == 1


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

def test_default_out_dir_uses_home_cas_atlas_traces(tmp_path, monkeypatch):
    """Default out-dir is `~/.cas_atlas/traces/` — monkeypatched home
    redirects to a tmp dir so we don't pollute the real home."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    trace = _make_valid_trace()
    src = tmp_path / "in.json"
    src.write_text(json.dumps(trace), encoding="utf-8")

    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", str(src),
        ])
    assert rc == 0, f"err={err_buf.getvalue()!r}"
    default_dir = tmp_path / ".cas_atlas" / "traces"
    assert default_dir.exists()
    saved = list(default_dir.glob("trace_*.json"))
    assert len(saved) == 1


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

def test_missing_source_file_exits_1(tmp_path):
    """A nonexistent --from path exits 1 with a clear stderr message."""
    err_buf = io.StringIO()
    with redirect_stderr(err_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", str(tmp_path / "does_not_exist.json"),
            "--out-dir", str(tmp_path / "out"),
        ])
    assert rc == 1
    err = err_buf.getvalue()
    assert "does not exist" in err.lower()


def test_invalid_json_exits_1(tmp_path):
    """A malformed JSON file exits 1 with a parse-error message."""
    src = tmp_path / "broken.json"
    src.write_text("{not valid json", encoding="utf-8")
    err_buf = io.StringIO()
    with redirect_stderr(err_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", str(src),
            "--out-dir", str(tmp_path / "out"),
        ])
    assert rc == 1
    assert "parse" in err_buf.getvalue().lower() or \
           "json" in err_buf.getvalue().lower()


def test_from_repl_history_errors_with_helpful_message(tmp_path):
    """--from-repl-history is reserved but not yet wired; today it
    errors with a clear "pipe a trace file instead" message."""
    err_buf = io.StringIO()
    with redirect_stderr(err_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from-repl-history",
            "--out-dir", str(tmp_path / "out"),
        ])
    assert rc != 0
    err = err_buf.getvalue()
    assert "not yet persistent" in err.lower() or \
           "pipe a trace file" in err.lower()


# ---------------------------------------------------------------------------
# Summary line contract
# ---------------------------------------------------------------------------

def test_summary_line_includes_node_and_edge_counts(tmp_path):
    """The one-line summary must include node + edge counts so users
    can sanity-check the saved trace at a glance."""
    trace = _make_valid_trace(node_count=11, edge_count=10)
    src = tmp_path / "in.json"
    src.write_text(json.dumps(trace), encoding="utf-8")
    out_dir = tmp_path / "atlas_summary"

    out_buf = io.StringIO()
    with redirect_stdout(out_buf):
        rc = cas_cli.main([
            "atlas-save",
            "--from", str(src),
            "--out-dir", str(out_dir),
        ])
    assert rc == 0
    out = out_buf.getvalue()
    assert "11 nodes" in out
    assert "10 edges" in out
    assert trace["trace_id"] in out
