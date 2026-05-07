"""Tests for the Path D Wave 3 NL-annotation smoke pipeline.

Five guard rails:

1. **Prompt builders** — each slot's builder produces non-empty system+user
   prompts that include the load-bearing inputs (expression / corrected /
   error / category).
2. **Response parsing** — ``parse_cas_from_response`` strips fences, labels,
   and trailing commentary, returning a single-line CAS expression.
3. **Leakage detection** — mirrors b4_failure_eval; flags ``^3^P``, ``F3``,
   ``|⟨``, ``Δ°``, ``RPM`` in user-facing replies, ignores plain prose.
4. **Schema conformance** — a generated SampleRecord serializes with every
   required field present.
5. **Cost-cap guard** — ``CostTracker`` flags would-exceed correctly; the
   pipeline early-stops when projected cost crosses cap.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = (
    _REPO_ROOT
    / "cas-synthetic"
    / "scripts"
    / "generate_path_d_wave3_smoke.py"
)


def _load_module():
    name = "path_d_wave3_smoke_under_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


REQUIRED_RECORD_FIELDS = (
    "sample_id",
    "slot",
    "source_id",
    "source_grammar_category_or_error_class",
    "prompt_to_model",
    "model_used",
    "raw_response",
    "generated_cas",
    "compiler_validated",
    "compiler_validation_attempts",
    "leakage_in_reply",
    "input_tokens",
    "output_tokens",
    "estimated_cost_usd",
    "timestamp_utc",
)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def test_cas_to_english_prompt_includes_expression_and_category():
    m = _load_module()
    seed = {
        "seed_id": "seed_x",
        "expression": "^3^P|A",
        "grammar_category": "state_literal",
    }
    sys_p, user_p = m.build_cas_to_english_prompt(seed)
    assert sys_p and isinstance(sys_p, str)
    assert "CAS" in sys_p
    assert "^3^P|A" in user_p
    assert "state_literal" in user_p


def test_english_to_cas_prompt_initial_has_no_prior_error():
    m = _load_module()
    seed = {
        "seed_id": "seed_y",
        "expression": "^2^C × ^5^P",
        "grammar_category": "binary_composition",
        "axes": {
            "noetics_used": [2, 5],
            "domains_used": ["C", "P"],
            "drives_used": [],
            "registers_used": [],
            "operators_used": ["×"],
        },
    }
    sys_p, user_p = m.build_english_to_cas_prompt(seed)
    assert "binary_composition" in user_p
    assert "previous attempt" not in user_p


def test_english_to_cas_prompt_retry_includes_prior_error():
    m = _load_module()
    seed = {
        "seed_id": "seed_y",
        "expression": "^2^C × ^5^P",
        "grammar_category": "binary_composition",
        "axes": {},
    }
    _, user_p = m.build_english_to_cas_prompt(
        seed, prior_attempt="^2^C ×* ^5^P", prior_error="parsing@5: bad token"
    )
    assert "previous attempt" in user_p
    assert "^2^C ×* ^5^P" in user_p
    assert "parsing@5: bad token" in user_p


def test_invalid_to_explanation_prompt_has_error_and_expression():
    m = _load_module()
    inv = {
        "invalid_id": "inv_x",
        "expression": "Phi<6 2>",
        "compiler_error_message": "parsing@6: expected RANGLE, got NUMBER",
        "error_class": "parse",
    }
    sys_p, user_p = m.build_invalid_to_explanation_prompt(inv)
    assert "Phi<6 2>" in user_p
    assert "parsing@6: expected RANGLE, got NUMBER" in user_p
    assert "parse" in user_p


def test_invalid_to_corrected_prompt_has_corrected_form():
    m = _load_module()
    inv = {
        "invalid_id": "inv_y",
        "expression": "^3^",
        "corrected_form": "^3^P",
        "compiler_error_message": "parsing@3: expected DOMAIN, got EOF",
        "error_class": "parse",
    }
    sys_p, user_p = m.build_invalid_to_corrected_prompt(inv)
    assert "^3^P" in user_p
    assert "^3^" in user_p


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def test_parse_cas_strips_markdown_fence():
    m = _load_module()
    s = "```cas\n^3^P|A\n```"
    assert m.parse_cas_from_response(s) == "^3^P|A"


def test_parse_cas_strips_label_prefix():
    m = _load_module()
    assert m.parse_cas_from_response("CAS: ^3^P|A") == "^3^P|A"
    assert m.parse_cas_from_response("Expression: ^2^C × ^5^P") == "^2^C × ^5^P"


def test_parse_cas_takes_first_nonempty_line():
    m = _load_module()
    s = "\n\n^3^P|A\n\nFoo bar"
    assert m.parse_cas_from_response(s) == "^3^P|A"


def test_parse_cas_empty_input():
    m = _load_module()
    assert m.parse_cas_from_response("") == ""


# ---------------------------------------------------------------------------
# Leakage detection
# ---------------------------------------------------------------------------


def test_detect_leakage_flags_state_literals():
    m = _load_module()
    assert m.detect_leakage("The state ^3^P represents principled aversion.")


def test_detect_leakage_flags_drive_subscript():
    m = _load_module()
    assert m.detect_leakage("This is anchored in F3 vitality.")


def test_detect_leakage_flags_register_set_marker():
    m = _load_module()
    assert m.detect_leakage("Register-set notation |⟨A,f,T⟩ is shown.")


def test_detect_leakage_flags_RPM():
    m = _load_module()
    assert m.detect_leakage("This violates RPM admissibility.")


def test_detect_leakage_clean_prose_passes():
    m = _load_module()
    assert not m.detect_leakage(
        "The mind is drawn toward an idea it has affinity for, "
        "an attraction that orients action."
    )


def test_detect_leakage_handles_empty():
    m = _load_module()
    assert not m.detect_leakage("")
    assert not m.detect_leakage(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Schema conformance
# ---------------------------------------------------------------------------


def test_sample_record_serializes_with_all_required_fields():
    m = _load_module()
    rec = m.SampleRecord(
        sample_id="wave3_cas_to_english_00000",
        slot="cas_to_english",
        source_id="seed_x",
        source_grammar_category_or_error_class="state_literal",
        prompt_to_model="<<SYSTEM>>...<<USER>>...",
        model_used=m.HAIKU_MODEL,
        raw_response="A drawn-toward attraction.",
        generated_cas=None,
        compiler_validated=None,
        compiler_validation_attempts=0,
        leakage_in_reply=False,
        input_tokens=12,
        output_tokens=20,
        estimated_cost_usd=0.000132,
        timestamp_utc="2026-05-07T01:23:45Z",
    )
    record = rec.to_record()
    for field in REQUIRED_RECORD_FIELDS:
        assert field in record, f"missing field: {field}"
    assert record["model_used"] == m.HAIKU_MODEL


# ---------------------------------------------------------------------------
# Cost tracker
# ---------------------------------------------------------------------------


def test_cost_tracker_accumulates_and_flags_cap():
    m = _load_module()
    cost = m.CostTracker(cost_cap_usd=0.01)
    # Sonnet at $3/$15 per million; 1000 in / 500 out = 0.003 + 0.0075 = 0.0105
    cost.add(slot="english_to_cas", model=m.SONNET_MODEL,
             input_tokens=1000, output_tokens=500)
    assert cost.total_cost_usd == pytest.approx(0.0105, rel=1e-3)
    assert cost.would_exceed()
    assert cost.per_slot_count["english_to_cas"] == 1


def test_cost_tracker_haiku_pricing_correct():
    m = _load_module()
    cost = m.CostTracker(cost_cap_usd=10.0)
    # Haiku at $1/$5 per million; 1M in / 1M out → $1 + $5 = $6
    cost.add(slot="cas_to_english", model=m.HAIKU_MODEL,
             input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost.total_cost_usd == pytest.approx(6.0, rel=1e-6)


# ---------------------------------------------------------------------------
# Stratified sampler
# ---------------------------------------------------------------------------


def test_stratified_sample_covers_all_buckets_when_target_allows():
    import random as _r
    m = _load_module()
    items = (
        [{"id": f"a{i}", "cat": "A"} for i in range(100)]
        + [{"id": f"b{i}", "cat": "B"} for i in range(100)]
        + [{"id": f"c{i}", "cat": "C"} for i in range(100)]
    )
    out = m.stratified_sample(items, key="cat", target_n=30, rng=_r.Random(1))
    cats = {it["cat"] for it in out}
    assert cats == {"A", "B", "C"}
    assert len(out) == 30


def test_stratified_sample_thin_bucket_does_not_explode():
    import random as _r
    m = _load_module()
    items = (
        [{"id": f"a{i}", "cat": "A"} for i in range(100)]
        + [{"id": "b0", "cat": "B"}]   # only one item in B
    )
    out = m.stratified_sample(items, key="cat", target_n=10, rng=_r.Random(1))
    assert len(out) == 10
    cats = {it["cat"] for it in out}
    assert "A" in cats
    # B may or may not appear (only 1 item), but result must be valid.


# ---------------------------------------------------------------------------
# Cost-cap guard end-to-end (mocked client; no real API).
# ---------------------------------------------------------------------------


def _make_seed(seed_id: str, cat: str, expr: str = "^0") -> dict:
    return {
        "seed_id": seed_id,
        "expression": expr,
        "grammar_category": cat,
        "axes": {},
    }


def _make_invalid(invalid_id: str, cls: str, expr: str = "^X") -> dict:
    return {
        "invalid_id": invalid_id,
        "source_seed_id": "seed_x",
        "expression": expr,
        "corrected_form": "^0",
        "error_class": cls,
        "compiler_error_message": "parsing@0: bad",
    }


def test_pipeline_hits_cost_cap_and_stops(tmp_path: Path):
    m = _load_module()
    seeds = [
        _make_seed(f"seed_{i}", "state_literal", "^0")
        for i in range(20)
    ]
    invalids = [
        _make_invalid(f"inv_{i}", "parse", "^X")
        for i in range(20)
    ]
    seeds_path = tmp_path / "seeds.jsonl"
    invalids_path = tmp_path / "invalids.jsonl"
    out_dir = tmp_path / "out"
    seeds_path.write_text("\n".join(json.dumps(s) for s in seeds), encoding="utf-8")
    invalids_path.write_text(
        "\n".join(json.dumps(i) for i in invalids), encoding="utf-8"
    )

    # Mock client: every call returns enough tokens that ~3 calls hit cap.
    fake_client = MagicMock()
    # Each Sonnet call: ~1000 in + 500 out → $0.0105.
    # Each Haiku call: ~1000 in + 500 out → $0.001 + $0.0025 = $0.0035.
    def call_fn(model, system_prompt, user_message, max_output_tokens=400, temperature=0.7):
        return m.ApiCallResult(
            text="A short paraphrase.",
            input_tokens=1000,
            output_tokens=500,
            error_reason=None,
        )
    fake_client.call.side_effect = call_fn

    # Stub compile_expression — declare every output valid so the pipeline
    # doesn't endlessly retry.
    fake_artifact = MagicMock()
    fake_artifact.valid = True
    fake_artifact.error = None
    def fake_compile(_expr):
        return fake_artifact

    result = m.run_smoke(
        seeds_path=seeds_path,
        invalids_path=invalids_path,
        out_dir=out_dir,
        target_total=80,           # plenty of headroom
        cost_cap_usd=0.05,         # tight cap → should hit fast
        seed=42,
        client=fake_client,
        compile_expression=fake_compile,
    )

    assert result["stopped_reason"] == "hit_cost_cap"
    assert result["total_cost_usd"] > 0.0
    assert result["total_cost_usd"] <= 0.05  # never exceeded the cap
    # Manifest + main JSONL were written.
    assert Path(result["main_path"]).exists()
    assert Path(result["cost_manifest_path"]).exists()
    # Total samples written must be small (cap stops us early).
    total_recs = sum(result["per_slot_count"].values())
    assert total_recs >= 1
    assert total_recs <= 30


def test_pipeline_completes_when_cap_is_generous(tmp_path: Path):
    m = _load_module()
    seeds = [_make_seed(f"seed_{i}", "state_literal", "^0") for i in range(8)]
    invalids = [_make_invalid(f"inv_{i}", "parse", "^X") for i in range(8)]
    seeds_path = tmp_path / "seeds.jsonl"
    invalids_path = tmp_path / "invalids.jsonl"
    out_dir = tmp_path / "out"
    seeds_path.write_text("\n".join(json.dumps(s) for s in seeds), encoding="utf-8")
    invalids_path.write_text(
        "\n".join(json.dumps(i) for i in invalids), encoding="utf-8"
    )

    fake_client = MagicMock()
    def call_fn(model, system_prompt, user_message, max_output_tokens=400, temperature=0.7):
        return m.ApiCallResult(
            text="Short reply.",
            input_tokens=100,
            output_tokens=50,
            error_reason=None,
        )
    fake_client.call.side_effect = call_fn

    fake_artifact = MagicMock()
    fake_artifact.valid = True
    fake_artifact.error = None
    fake_compile = MagicMock(return_value=fake_artifact)

    result = m.run_smoke(
        seeds_path=seeds_path,
        invalids_path=invalids_path,
        out_dir=out_dir,
        target_total=8,            # tiny target — should complete cleanly
        cost_cap_usd=10.0,
        seed=42,
        client=fake_client,
        compile_expression=fake_compile,
    )
    assert result["stopped_reason"] == "completed"
    # Cost manifest exists and is well-formed.
    cost_manifest = json.loads(Path(result["cost_manifest_path"]).read_text(encoding="utf-8"))
    assert cost_manifest["stopped_reason"] == "completed"
    assert "actual_cost_per_sample" in cost_manifest
    assert "ready_for_full_scale_decision" in cost_manifest


def test_pipeline_logs_compiler_rejections(tmp_path: Path):
    m = _load_module()
    seeds = [_make_seed(f"seed_{i}", "state_literal", "^0") for i in range(3)]
    invalids = [_make_invalid(f"inv_{i}", "parse", "^X") for i in range(3)]
    seeds_path = tmp_path / "seeds.jsonl"
    invalids_path = tmp_path / "invalids.jsonl"
    out_dir = tmp_path / "out"
    seeds_path.write_text("\n".join(json.dumps(s) for s in seeds), encoding="utf-8")
    invalids_path.write_text(
        "\n".join(json.dumps(i) for i in invalids), encoding="utf-8"
    )

    fake_client = MagicMock()
    def call_fn(model, system_prompt, user_message, max_output_tokens=400, temperature=0.7):
        return m.ApiCallResult(
            text="garbage_cas_token",
            input_tokens=50,
            output_tokens=25,
            error_reason=None,
        )
    fake_client.call.side_effect = call_fn

    # Compiler rejects every english_to_cas attempt.
    invalid_artifact = MagicMock()
    invalid_artifact.valid = False
    invalid_artifact.error = "parsing@0: garbage"
    valid_artifact = MagicMock()
    valid_artifact.valid = True
    valid_artifact.error = None

    def selective_compile(expr):
        if "garbage" in (expr or ""):
            return invalid_artifact
        return valid_artifact

    result = m.run_smoke(
        seeds_path=seeds_path,
        invalids_path=invalids_path,
        out_dir=out_dir,
        target_total=8,
        cost_cap_usd=10.0,
        seed=42,
        client=fake_client,
        compile_expression=selective_compile,
    )
    # Every english_to_cas sample should have been rejected after 3 attempts.
    assert result["rejection_counts"].get("english_to_cas", 0) >= 1
    rejected_path = Path(result["rejected_path"])
    assert rejected_path.exists()
    rejected_lines = [
        json.loads(line)
        for line in rejected_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rejected_lines) >= 1
    for r in rejected_lines:
        assert r["last_error"]
        assert r["attempts_used"] == m.COMPILER_VALIDATION_MAX_ATTEMPTS


def test_dry_run_writes_synthetic_records(tmp_path: Path):
    m = _load_module()
    seeds = [_make_seed(f"seed_{i}", "state_literal", "^0") for i in range(4)]
    invalids = [_make_invalid(f"inv_{i}", "parse", "^X") for i in range(4)]
    seeds_path = tmp_path / "seeds.jsonl"
    invalids_path = tmp_path / "invalids.jsonl"
    out_dir = tmp_path / "out"
    seeds_path.write_text("\n".join(json.dumps(s) for s in seeds), encoding="utf-8")
    invalids_path.write_text(
        "\n".join(json.dumps(i) for i in invalids), encoding="utf-8"
    )
    result = m.run_smoke(
        seeds_path=seeds_path,
        invalids_path=invalids_path,
        out_dir=out_dir,
        target_total=8,
        cost_cap_usd=10.0,
        seed=42,
        dry_run=True,
    )
    main_path = Path(result["main_path"])
    assert main_path.exists()
    lines = main_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 4
    rec0 = json.loads(lines[0])
    for field in REQUIRED_RECORD_FIELDS:
        assert field in rec0
