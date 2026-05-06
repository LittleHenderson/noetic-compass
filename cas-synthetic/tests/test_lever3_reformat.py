"""Tests for Lever 3 paired-data reformatting.

No real corpus files are touched here. The tests use tiny synthetic rows.
"""

from __future__ import annotations

import importlib.util as _importlib_util
import json
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = (
    _REPO_ROOT
    / "cas-synthetic"
    / "scripts"
    / "reformat_lever3_paired_to_native_nl.py"
)
_TMP_ROOT = _REPO_ROOT / "manual_tmp_test" / "codex_tier3_dialogue"


def _load_module():
    mod_name = "reformat_lever3_paired_to_native_nl_module"
    spec = _importlib_util.spec_from_file_location(mod_name, _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = _importlib_util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


mod = _load_module()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _paths(name: str) -> tuple[Path, Path, Path]:
    _TMP_ROOT.mkdir(parents=True, exist_ok=True)
    for path in _TMP_ROOT.glob(f"{name}*"):
        if path.is_file():
            path.unlink()
    return (
        _TMP_ROOT / f"{name}_input.jsonl",
        _TMP_ROOT / f"{name}_out.jsonl",
        _TMP_ROOT / f"{name}_manifest.json",
    )


def _row(*, row_id: str, reply: str) -> dict:
    return {
        "id": row_id,
        "bucket": "v74_baseline",
        "user_prompt": "I keep practicing this every day until it becomes automatic.",
        "assistant_response": reply,
        "cas_expression": "^7^C_{F1}|A",
        "generation_metadata": {"model": "unit-test"},
        "provenance": {"template_id": "unit"},
    }


def test_strict_mode_rejects_cas_explanation_rows():
    input_path, out_path, manifest_path = _paths("strict")
    _write_jsonl(input_path, [
        _row(
            row_id="bad",
            reply="The exact CAS expression is ^7^C_{F1}|A with register A.",
        )
    ])
    assert mod.run(
        inputs=[input_path],
        out_path=out_path,
        manifest_path=manifest_path,
        include_explanatory=False,
        limit=None,
    ) == 0
    assert _read_jsonl(out_path) == []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["total_records"] == 0
    assert manifest["failure_counts"]


def test_strict_mode_rejects_explanation_without_literal_cas_word():
    input_path, out_path, manifest_path = _paths("strict_meta")
    _write_jsonl(input_path, [
        _row(
            row_id="meta",
            reply=(
                "Use PartitionOf(SubFoundations, Foundation_1). The notation "
                "preserves typed finite meta-logic construct."
            ),
        )
    ])
    assert mod.run(
        inputs=[input_path],
        out_path=out_path,
        manifest_path=manifest_path,
        include_explanatory=False,
        limit=None,
    ) == 0
    assert _read_jsonl(out_path) == []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert any("explanatory_reply" in key for key in manifest["failure_counts"])


def test_include_explanatory_marks_auxiliary_not_conversational():
    input_path, out_path, manifest_path = _paths("aux")
    _write_jsonl(input_path, [
        _row(
            row_id="bad",
            reply="The exact CAS expression is ^7^C_{F1}|A with register A.",
        )
    ])
    assert mod.run(
        inputs=[input_path],
        out_path=out_path,
        manifest_path=manifest_path,
        include_explanatory=True,
        limit=None,
    ) == 0
    rows = _read_jsonl(out_path)
    assert len(rows) == 1
    assert rows[0]["training_lane"] == "cas_explanation_auxiliary"
    assert rows[0]["use_for_conversational_lm"] is False
    assert rows[0]["validator_pass"] is False
    assert rows[0]["noetic"] == "^7"
    assert rows[0]["domain"] == "C"
    assert rows[0]["drive"] == "F1"
    assert rows[0]["register"] == "A"


def test_clean_reply_can_be_conversational_lm_row():
    input_path, out_path, manifest_path = _paths("clean")
    _write_jsonl(input_path, [
        _row(
            row_id="good",
            reply="Doing it every day is what turns the idea into muscle memory.",
        )
    ])
    assert mod.run(
        inputs=[input_path],
        out_path=out_path,
        manifest_path=manifest_path,
        include_explanatory=False,
        limit=None,
    ) == 0
    rows = _read_jsonl(out_path)
    assert len(rows) == 1
    assert rows[0]["tier"] == "tier3_reformatted"
    assert rows[0]["training_lane"] == "conversational_lm"
    assert rows[0]["use_for_conversational_lm"] is True
    assert rows[0]["prompt"] == rows[0]["prompt_text"]
    assert rows[0]["reply"] == rows[0]["reply_text"]
