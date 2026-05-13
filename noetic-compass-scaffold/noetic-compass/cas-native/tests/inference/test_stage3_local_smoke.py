"""Tests for the Stage 3 one-record local smoke script.

The heavy test (`test_smoke_against_real_archive`) only runs when the
real `D:\\tksCAS-archive\\` is present AND the dev pack file is present.
The lightweight tests run unconditionally.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cas_native.inference import stage3_local_smoke as smoke
from cas_native.inference.stage3_local_loader import DEFAULT_ARCHIVE_ROOT


# ---------------------------------------------------------------------------
# Lightweight (no model, no archive)
# ---------------------------------------------------------------------------

def test_module_imports_cleanly():
    """Smoke module imports without ImportError. Cheap regression pin."""
    assert hasattr(smoke, "run_stage3_local_smoke")
    assert hasattr(smoke, "main")
    assert hasattr(smoke, "_load_record")
    assert hasattr(smoke, "_slot_trace_summary")


def test_slot_trace_summary_empty():
    s = smoke._slot_trace_summary([])
    assert s == {"length": 0, "counts": {}, "longest_stage_var_run": 0}


def test_slot_trace_summary_counts_and_run():
    # SLOT_STAGE_VAR_ID = 2 per simplex_collator constants.
    # trace: 0 2 2 0 2 2 2 0 → longest run of 2s is 3
    s = smoke._slot_trace_summary([0, 2, 2, 0, 2, 2, 2, 0])
    assert s["length"] == 8
    assert s["counts"] == {"0": 3, "2": 5}
    assert s["longest_stage_var_run"] == 3


def test_slot_trace_summary_no_stage_var():
    s = smoke._slot_trace_summary([0, 1, 0, 1, 0])
    assert s["longest_stage_var_run"] == 0


def test_load_record_raises_on_missing_file(tmp_path):
    missing = tmp_path / "nope.jsonl"
    with pytest.raises(FileNotFoundError, match=r"Dev pack not found"):
        smoke._load_record(missing, idx=0)


def test_load_record_raises_on_index_out_of_range(tmp_path):
    p = tmp_path / "tiny.jsonl"
    p.write_text(
        '{"id": "a"}\n{"id": "b"}\n', encoding="utf-8",
    )
    with pytest.raises(IndexError, match=r"out of range"):
        smoke._load_record(p, idx=5)


def test_load_record_returns_correct_record(tmp_path):
    p = tmp_path / "tiny.jsonl"
    p.write_text(
        '{"id": "a", "x": 1}\n'
        '{"id": "b", "x": 2}\n'
        '{"id": "c", "x": 3}\n',
        encoding="utf-8",
    )
    assert smoke._load_record(p, idx=0)["id"] == "a"
    assert smoke._load_record(p, idx=2)["id"] == "c"


def test_smoke_passes_max_cas_prefix_len_192_to_collator():
    """Regression pin per Codex re-audit `40d5935` (2026-05-13):
    Stage 3 was trained with max_cas_prefix_len=192. The
    NativeNLCollator default is 32, which silently truncates ~3+ stage
    RPM chains. The smoke MUST pass an explicit cap (read from manifest,
    fall back to 192). Source-level check so the test doesn't depend on
    loading the 664 MB archive."""
    src = open(smoke.__file__, encoding="utf-8").read()
    # The collator construction must pass max_cas_prefix_len explicitly
    assert "max_cas_prefix_len=cas_prefix_cap" in src or \
           "max_cas_prefix_len=192" in src, (
        "stage3_local_smoke must pass max_cas_prefix_len to SimplexCollator "
        "(read from manifest with 192 fallback per Codex 40d5935)"
    )
    # The manifest read must be present (forward-compatibility)
    assert 'bundle.manifest.get("config", {}).get("max_cas_prefix_len"' in src, (
        "smoke must derive the cap from the loaded manifest, not hardcode"
    )
    # The fallback value must be 192 (Stage 3 training value)
    assert "192" in src


def test_smoke_report_surfaces_max_cas_prefix_len():
    """Regression pin per Codex audit `92eb3a2` (2026-05-13): the
    smoke report dict MUST surface the cap explicitly so future trace
    consumers (chat REPL, Mode 7, Atlas) can prove the encoder saw
    the full CAS expression. Source-level check."""
    src = open(smoke.__file__, encoding="utf-8").read()
    assert '"max_cas_prefix_len": cas_prefix_cap' in src, (
        "stage3_local_smoke report dict must include `max_cas_prefix_len` "
        "per Codex 92eb3a2 audit"
    )


# ---------------------------------------------------------------------------
# Heavy: end-to-end against the real local archive + dev pack
# Skipped when archive absent so this never blocks CI.
# ---------------------------------------------------------------------------

_REAL_CKPT = (
    DEFAULT_ARCHIVE_ROOT / "stage_e3_20260513T043823Z" / "ckpt_final.pt"
)
# smoke.__file__ is at .../cas-native/inference/stage3_local_smoke.py;
# repo root with cas-synthetic/ is parents[4].
_REAL_DEV = (
    Path(smoke.__file__).resolve().parents[4]
    / "cas-synthetic" / "data" / "path_d"
    / "rpm_copy_grounding_v2_dev.jsonl"
)


@pytest.mark.skipif(
    not _REAL_CKPT.exists() or not _REAL_DEV.exists(),
    reason=(
        f"requires real archive at {_REAL_CKPT} "
        f"and dev pack at {_REAL_DEV}; skipped otherwise"
    ),
)
def test_smoke_against_real_archive_record_0_gates_pass():
    """Run the smoke against the actual local archive + dev pack record 0.
    Asserts the gates Codex named:
      - no crash
      - generated text non-empty
      - >= 1 of 4 canonical identifiers recovered
      - no NaN/Inf

    Disables save_report so the test doesn't leave .tmp/ artifacts behind.
    """
    report = smoke.run_stage3_local_smoke(
        record_idx=0,
        save_report=False,
    )

    # Structural shape
    assert report["manifest_ablation_mode"] == "e3", (
        "expected to load the Stage 3 e3 checkpoint; got "
        f"{report['manifest_ablation_mode']!r}"
    )
    assert report["record_idx"] == 0
    assert report["record_id"] is not None

    # Gates (one-by-one so failure messages name the specific gate)
    gates = report["gates"]
    assert gates["no_crash"] is True
    assert gates["generated_non_empty"], (
        f"generated text was empty for record id={report['record_id']!r}; "
        f"prompt={report['prompt_text']!r}"
    )
    assert gates["ge_one_canonical_recovered"], (
        f"recovered {report['recovery']['n_recovered']}/"
        f"{report['recovery']['n_target']} canonical identifiers; "
        f"loose gate required at least 1. "
        f"generated_identifiers={report['recovery']['generated_identifiers']!r}, "
        f"canonical={report['canonical_identifiers']!r}"
    )
    assert gates["lm_finite"] is True
    assert gates["overall_pass"] is True, (
        f"overall gate failed: {gates!r}"
    )
