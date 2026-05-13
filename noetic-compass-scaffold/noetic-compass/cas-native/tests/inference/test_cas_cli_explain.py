"""Tests for the `cas explain` subcommand (Step 4 of post-Stage-3 build).

Lightweight tests run unconditionally (dispatcher registration, banner
mention, argparse, missing-archive error). Heavy tests require the real
local archive at `D:\\tksCAS-archive\\` and the dev pack; they are skipped
when either is absent, so CI / fresh checkouts never block on them.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import pytest

from cas_native.inference import cas_cli
from cas_native.inference.stage3_local_loader import DEFAULT_ARCHIVE_ROOT


# ---------------------------------------------------------------------------
# Lightweight (no model, no archive)
# ---------------------------------------------------------------------------

def test_explain_subcommand_registered_in_COMMANDS():
    """`COMMANDS["explain"]` exists and is the explain handler.

    The dispatcher's historical name is `SUBCOMMANDS`; Step 4 spec names
    it `COMMANDS`. Both must point at the same callable.
    """
    assert "explain" in cas_cli.COMMANDS
    assert callable(cas_cli.COMMANDS["explain"])
    assert cas_cli.COMMANDS["explain"] is cas_cli._cmd_explain
    assert cas_cli.COMMANDS is cas_cli.SUBCOMMANDS


def test_explain_in_dispatcher_help_banner():
    """Running `cas help` mentions the `explain` subcommand so users can
    discover it from the top-level banner."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cas_cli.main(["help"])
    out = buf.getvalue()
    assert rc == 0
    assert "explain" in out
    # And the specific Step 4 phrasing the banner exposes.
    assert "explain EXPR" in out or "cas explain EXPR" in out


def test_explain_argparse_accepts_required_arg(monkeypatch):
    """Calling `explain` with zero args returns non-zero and prints a
    helpful error that names what was missing."""
    err_buf = io.StringIO()
    with redirect_stderr(err_buf):
        rc = cas_cli.main(["explain"])
    err = err_buf.getvalue()
    assert rc != 0
    assert "expression required" in err.lower() or "expression" in err.lower()


def test_explain_argparse_accepts_json_flag(tmp_path):
    """`--json` is a valid flag.

    We point at a guaranteed-missing archive so the call returns early
    (before loading anything). The point is that argparse accepts the
    flag without erroring on parse.
    """
    missing = tmp_path / "does_not_exist"
    err_buf = io.StringIO()
    out_buf = io.StringIO()
    with redirect_stderr(err_buf), redirect_stdout(out_buf):
        rc = cas_cli.main([
            "explain",
            "let stageA0_4_857 = ^7^P_{F5}; stageA0_4_857 -> stageA0_4_857",
            "--json",
            "--archive-root", str(missing),
        ])
    err = err_buf.getvalue()
    assert rc == 2
    # Argparse parse failures use prefix "usage:" / "error:"; the missing-
    # archive path message is our handler's message. Confirm argparse did
    # NOT reject --json.
    assert "unrecognized arguments" not in err.lower()
    assert "--json" not in err.lower() or "archive root not found" in err.lower()


def test_explain_returns_2_on_empty_archive(tmp_path):
    """When archive_root points at a nonexistent dir, return non-zero AND
    print a clear message naming the missing path."""
    missing = tmp_path / "no_archive_here"
    err_buf = io.StringIO()
    with redirect_stderr(err_buf):
        rc = cas_cli.main([
            "explain",
            "let stageA0_4_857 = ^7^P_{F5}; stageA0_4_857 -> stageA0_4_857",
            "--archive-root", str(missing),
        ])
    err = err_buf.getvalue()
    assert rc == 2
    assert "archive root not found" in err.lower()
    assert str(missing) in err


def test_explain_unknown_flag_is_rejected(tmp_path):
    """Unknown flags are rejected by argparse with non-zero exit. Pins
    that we use argparse rather than swallowing unknown args silently."""
    with pytest.raises(SystemExit) as exc:
        cas_cli.main([
            "explain",
            "let stageA0_4_857 = ^7^P_{F5}",
            "--definitely-not-a-flag", "x",
        ])
    assert exc.value.code != 0


def test_prompt_chooses_rpm_phrasing_for_arrow_expression():
    """The training prompt for chain-shaped inputs must match the dev pack
    phrasing exactly. If we change this without thinking, the model sees
    an out-of-distribution prompt and drift is the explanation."""
    prompt = cas_cli._explain_prompt_for_expression(
        "let stageA0_4_857 = ^7^P_{F5}; stageA0_4_857 -> stageA0_4_857"
    )
    assert prompt == "Explain this rpm chain expression."


def test_prompt_falls_back_for_non_chain_expression():
    """No `->` in the expression → generic phrasing. Avoids fabricating
    an rpm-chain prompt for a non-chain shape."""
    prompt = cas_cli._explain_prompt_for_expression("^3^P_{F2}|A")
    assert prompt == "Explain this expression."


def test_slot_trace_summary_empty():
    s = cas_cli._explain_slot_trace_summary([])
    assert s == {"length": 0, "counts": {}, "longest_stage_var_run": 0}


def test_slot_trace_summary_counts_and_run():
    """STAGE_VAR id = 2. trace 0 2 2 0 2 2 2 0 → longest run is 3."""
    s = cas_cli._explain_slot_trace_summary([0, 2, 2, 0, 2, 2, 2, 0])
    assert s["length"] == 8
    assert s["counts"] == {"0": 3, "2": 5}
    assert s["longest_stage_var_run"] == 3


def test_explain_passes_max_cas_prefix_len_192_to_collator():
    """Regression pin per Codex re-audit `40d5935` (2026-05-13):
    Stage 3 was trained with max_cas_prefix_len=192. The
    NativeNLCollator default is 32, which silently truncates ~3+ stage
    RPM chains and drops later identifiers before the model sees them.
    `cas explain` MUST pass an explicit cap (read from manifest, fall
    back to 192). Source-level check so the test doesn't depend on
    loading the 664 MB archive."""
    src = open(cas_cli.__file__, encoding="utf-8").read()
    # The collator construction must pass max_cas_prefix_len explicitly
    assert "max_cas_prefix_len=cas_prefix_cap" in src or \
           "max_cas_prefix_len=192" in src, (
        "cas explain must pass max_cas_prefix_len to SimplexCollator "
        "(read from manifest with 192 fallback per Codex 40d5935)"
    )
    # The manifest read must be present (forward-compatibility)
    assert 'bundle.manifest.get("config", {}).get("max_cas_prefix_len"' in src, (
        "cas explain must derive the cap from the loaded manifest"
    )
    # The fallback value must be 192 (Stage 3 training value)
    assert "192" in src


# ---------------------------------------------------------------------------
# Heavy: end-to-end against the real local archive + dev pack
# Skipped when archive absent so this never blocks CI.
# ---------------------------------------------------------------------------

_REAL_CKPT = (
    DEFAULT_ARCHIVE_ROOT / "stage_e3_20260513T043823Z" / "ckpt_final.pt"
)
# cas_cli.__file__ → .../cas-native/inference/cas_cli.py; repo root with
# cas-synthetic/ is parents[4].
_REAL_DEV = (
    Path(cas_cli.__file__).resolve().parents[4]
    / "cas-synthetic" / "data" / "path_d"
    / "rpm_copy_grounding_v2_dev.jsonl"
)


def _load_dev_record_0() -> dict:
    """Read record 0 from the dev pack so the heavy tests use the same
    expression the smoke harness uses."""
    with _REAL_DEV.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                return json.loads(line)
    raise RuntimeError("dev pack appears empty")


@pytest.mark.skipif(
    not _REAL_CKPT.exists() or not _REAL_DEV.exists(),
    reason=(
        f"requires real archive at {_REAL_CKPT} and dev pack at {_REAL_DEV}; "
        "skipped otherwise"
    ),
)
def test_explain_end_to_end_real_archive():
    """Feed dev record 0's cas_expression to `cas explain` and confirm the
    output dict is structurally valid + gates pass.

    Decode is greedy and deterministic-ish but no specific generated
    string is asserted — only structural and coverage gates.
    """
    record = _load_dev_record_0()
    expression = record["cas_expression"]
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        rc = cas_cli.main([
            "explain", expression,
            "--json",
            "--no-save-report",
        ])
    err = err_buf.getvalue()
    assert rc == 0, f"explain returned {rc}; stderr={err!r}"
    payload = json.loads(out_buf.getvalue())

    # Structural shape
    assert payload["command"] == "cas explain"
    assert payload["version"] == 1
    assert payload["input_cas_expression"] == expression
    model_info = payload["model"]
    assert model_info["manifest_ablation_mode"] == "e3", (
        f"expected Stage 3 e3 checkpoint; got {model_info!r}"
    )
    assert isinstance(model_info["load_seconds"], (int, float))
    assert isinstance(model_info["decode_seconds"], (int, float))

    # Generated text non-empty
    gen = payload["generated_english"]
    assert isinstance(gen, str) and gen, (
        f"generated_english empty; payload={payload!r}"
    )

    # Identifier breakdown reflects the input
    idents = payload["identifiers"]
    assert idents["expected"], "input expression has no stage identifiers?"
    # At least one canonical identifier copied — same loose gate as Step 3.
    assert idents["copied"], (
        f"no canonical identifiers copied into generated text. "
        f"expected={idents['expected']!r}  emitted={idents['emitted']!r}  "
        f"generated={gen!r}"
    )
    assert 0.0 <= idents["coverage"] <= 1.0

    # Slot summary shape
    slot = payload["slot_summary"]
    assert isinstance(slot["length"], int) and slot["length"] > 0
    # STAGE_VAR id = 2; at least one STAGE_VAR position is required so
    # we know the model attempted source-grounded emission, not pure LM.
    assert slot["counts"].get("2", 0) >= 1, (
        f"no STAGE_VAR positions in slot trace; slot={slot!r}"
    )

    # Gates
    gates = payload["gates"]
    assert gates["no_crash"] is True
    assert gates["generated_non_empty"] is True
    assert gates["ge_one_identifier_copied"] is True


@pytest.mark.skipif(
    not _REAL_CKPT.exists() or not _REAL_DEV.exists(),
    reason=(
        f"requires real archive at {_REAL_CKPT} and dev pack at {_REAL_DEV}; "
        "skipped otherwise"
    ),
)
def test_explain_json_mode_is_valid_json():
    """`--json` output must round-trip cleanly through json.loads. The
    end-to-end test already does this; this test isolates the contract."""
    record = _load_dev_record_0()
    out_buf = io.StringIO()
    with redirect_stdout(out_buf):
        rc = cas_cli.main([
            "explain", record["cas_expression"],
            "--json",
            "--no-save-report",
        ])
    assert rc == 0
    payload = json.loads(out_buf.getvalue())  # raises on invalid JSON
    assert isinstance(payload, dict)
    assert payload["command"] == "cas explain"
