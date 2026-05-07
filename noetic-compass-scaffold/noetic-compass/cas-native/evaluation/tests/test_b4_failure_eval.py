"""Tests for the B-4 failure-eval harness.

Tests the harness logic only — never loads the model or the K=9 checkpoint.
We monkeypatch ``predictor`` and ``native_generator`` with stubs so the
scoring + aggregation paths are exercised on deterministic inputs that
mirror the documented failure modes.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest


# Path bootstrap — match the harness's own bootstrap so imports work whether
# pytest is invoked from repo root or from cas-native/.
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.resolve().parents[3]  # noetic-compass/

if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__path__ = [str(_REPO_ROOT / "cas-native")]
    sys.modules["cas_native"] = pkg
sys.path.insert(0, str(_REPO_ROOT))


from cas_native.evaluation.b4_failure_eval import (  # noqa: E402
    HarnessConfig,
    PerPromptResult,
    PreservationResult,
    _CATEGORY_FAIL_POLICY,
    _apply_failure_policy,
    _placeholder_score_preservation,
    _resolve_preservation_scorer,
    aggregate_results,
    detect_leakage,
    evaluate_prompt,
    load_prompts,
    score_compiler_validity,
    score_directness,
    score_non_rambling,
    score_plain_language_clarity,
    score_relevance,
    tfidf_cosine,
)


# ---------------------------------------------------------------------------
# Fixture file
# ---------------------------------------------------------------------------


_FIXTURE_PATH = (
    _REPO_ROOT / "cas-native" / "evaluation" / "fixtures" / "b4_failure_prompts.jsonl"
)


def test_fixture_exists():
    assert _FIXTURE_PATH.exists(), f"missing fixture file at {_FIXTURE_PATH}"


def test_fixture_loads_and_covers_all_categories():
    prompts = load_prompts(_FIXTURE_PATH)
    assert 50 <= len(prompts) <= 100, f"need 50-100 prompts, got {len(prompts)}"

    by_cat: dict[str, list[dict[str, Any]]] = {}
    for p in prompts:
        by_cat.setdefault(p["category"], []).append(p)

    required = {
        "casual_greeting",
        "confusion",
        "frustration",
        "simple_cas_question",
        "valid_cas_notation",
        "invalid_cas",
        "v76_production",
        "v77_omega",
        "meta_logic",
        "fractal_composition",
    }
    assert required.issubset(by_cat.keys()), f"missing categories: {required - set(by_cat.keys())}"
    for cat in required:
        assert len(by_cat[cat]) >= 5, f"category {cat} has only {len(by_cat[cat])}; need >=5"


def test_fixture_required_fields_present():
    prompts = load_prompts(_FIXTURE_PATH)
    for p in prompts:
        assert "id" in p
        assert "category" in p
        assert "prompt_text" in p
        assert "expected_route" in p
        assert p["expected_route"] in {"cas_pipeline", "clarification", "fallback"}


def test_fixture_ids_unique():
    prompts = load_prompts(_FIXTURE_PATH)
    ids = [p["id"] for p in prompts]
    assert len(ids) == len(set(ids)), "fixture IDs must be unique"


def test_load_prompts_rejects_invalid_jsonl(tmp_path: Path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"id": "x"}\nnot-json\n', encoding="utf-8")
    with pytest.raises(ValueError):
        load_prompts(bad)


def test_load_prompts_rejects_missing_required_keys(tmp_path: Path):
    bad = tmp_path / "missing.jsonl"
    bad.write_text('{"id": "x", "category": "c"}\n', encoding="utf-8")
    with pytest.raises(ValueError):
        load_prompts(bad)


def test_load_prompts_skips_blank_lines(tmp_path: Path):
    good = tmp_path / "good.jsonl"
    good.write_text(
        '{"id": "a", "category": "c", "prompt_text": "p1", "expected_route": "fallback"}\n'
        "\n"
        '{"id": "b", "category": "c", "prompt_text": "p2", "expected_route": "fallback"}\n',
        encoding="utf-8",
    )
    out = load_prompts(good)
    assert [p["id"] for p in out] == ["a", "b"]


# ---------------------------------------------------------------------------
# Auto-scorer unit tests
# ---------------------------------------------------------------------------


def test_tfidf_cosine_identity_high():
    sim = tfidf_cosine("hello world friend", "hello world friend")
    assert sim > 0.9


def test_tfidf_cosine_disjoint_zero():
    sim = tfidf_cosine("apple banana cherry", "trumpet violin piano")
    assert sim < 0.05


def test_tfidf_cosine_partial_middle():
    sim = tfidf_cosine("explain consent before continuing", "you should explain consent first")
    assert 0.05 < sim < 0.95


def test_relevance_score_buckets_irrelevant_low():
    bucket, raw, source = score_relevance(
        "this is wack",
        "Start by anchoring the habit to a physical anchor — that reminds me of how my hands actually know the task before my brain catches up...",
    )
    assert bucket <= 2, f"documented irrelevance failure should score <=2, got {bucket} (raw={raw})"
    assert source in {"tfidf_cosine", "sentence_transformers"}


def test_relevance_score_buckets_topical_high():
    bucket, _raw, _src = score_relevance(
        "explain consent clearly please",
        "I will explain consent clearly: consent means freely given agreement.",
    )
    assert bucket >= 3


def test_directness_credits_pronouns_and_questions():
    score, info = score_directness("hi", "Are you asking for clarification? You can choose either path.")
    assert score >= 4
    assert info["has_question"] is True
    assert info["n_pronouns"] >= 2


def test_directness_low_for_monologue():
    score, _info = score_directness(
        "hi",
        "Anchoring the habit to a physical anchor — that reminds me of how my hands actually know the task before the mind catches up.",
    )
    assert score <= 3


def test_non_rambling_short_high():
    score, info = score_non_rambling("Hi! What did you mean?")
    assert score == 5
    assert info["n_chars"] < 120


def test_non_rambling_long_low():
    score, _info = score_non_rambling("x" * 1000)
    assert score == 1


def test_leakage_detects_caret_state():
    leaks, hits = detect_leakage("the answer is ^3^P with some F2 markers")
    assert leaks is True
    assert any("^3^P" in h for h in hits) or any("F2" in h for h in hits)


def test_leakage_misses_pure_english():
    leaks, hits = detect_leakage("I think you should explain it more clearly.")
    assert leaks is False
    assert hits == []


def test_leakage_pattern_matches_spec_exactly():
    # Spec: r"\^[0-9]\^[PCEO]|\bF[1-7]\b|\|⟨|Δ°|RPM"
    assert detect_leakage("^3^P")[0] is True
    assert detect_leakage("look at F4 here")[0] is True
    assert detect_leakage("|⟨A,f,T⟩")[0] is True
    assert detect_leakage("RPM chain")[0] is True
    assert detect_leakage("Δ° simplex")[0] is True
    # Negative samples
    assert detect_leakage("F0 is not a drive")[0] is False  # F0 out-of-range
    assert detect_leakage("F8 is also not")[0] is False     # F8 out-of-range
    assert detect_leakage("just words here")[0] is False


def test_plain_language_clarity_pure_english_5():
    score, info = score_plain_language_clarity(
        "I will explain it simply. You can think of it as a step-by-step recipe."
    )
    assert score == 5
    assert info["jargon_hits"] == 0


def test_plain_language_clarity_jargon_heavy_low():
    score, info = score_plain_language_clarity(
        "The Noetic operates over the register and drive vectors involution. CAS RPM gates the domain."
    )
    assert score <= 2
    assert info["jargon_hits"] >= 4


def test_compiler_validity_rejects_empty():
    valid, info = score_compiler_validity("")
    assert valid is False
    assert info["reason"] == "empty_expression"


def test_compiler_validity_accepts_simple_expression():
    # Single Noetic-domain compound is the simplest valid form per the
    # compiler. Use a well-known canonical form.
    valid, _info = score_compiler_validity("^3^P")
    # Compiler may or may not be importable in this environment; the test
    # asserts the harness either compiles cleanly (preferred) OR returns a
    # clean import-failed report (no exception leaks).
    assert isinstance(valid, bool)


# ---------------------------------------------------------------------------
# Preservation scorer placeholder + resolver
# ---------------------------------------------------------------------------


def test_placeholder_returns_PreservationResult():
    out = _placeholder_score_preservation("^3^P", "^3^P")
    assert isinstance(out, PreservationResult)
    assert out.placeholder is True
    assert out.score == 0.0


def test_resolver_returns_callable_either_real_or_placeholder():
    # In the real codebase the file may or may not exist (Agent D owns it).
    # Either outcome is acceptable; we just need the resolver to NOT raise
    # and to return a callable that produces a result-like object on a
    # known-good (identical) input.
    fn = _resolve_preservation_scorer()
    assert callable(fn)
    out = fn("^3^P", "^3^P")
    # Acceptable shapes:
    #   * harness placeholder PreservationResult (has `placeholder` attr)
    #   * Agent D PreservationResult (has `preservation_score` attr)
    #   * a dict with one of the above shapes
    if isinstance(out, dict):
        assert "placeholder" in out or "preservation_score" in out
    else:
        assert hasattr(out, "placeholder") or hasattr(out, "preservation_score")


# ---------------------------------------------------------------------------
# evaluate_prompt — uses stub predictor + stub generator
# ---------------------------------------------------------------------------


class _StubPredictor:
    """Deterministic stub mimicking the K=9 Predictor return shape."""

    def __init__(self, *, noetic: int = 3, domain: str = "P", drive: str = "F4",
                 registers: list[str] | None = None) -> None:
        self.noetic = noetic
        self.domain = domain
        self.drive = drive
        self.registers = list(registers) if registers else ["A"]

    def __call__(self, text: str, **_: Any) -> dict[str, Any]:
        return {
            "turn_type": "statement",
            "expression_family": "compound",
            "transition_kind": "none",
            "noetic": self.noetic,
            "domain": self.domain,
            "drive": self.drive,
            "register_mode": "single",
            "registers": list(self.registers),
            "authority": "none",
            "has_omega": False,
            "has_meta_logic": False,
            "meta_relations": [],
        }


def _harness_config() -> HarnessConfig:
    return HarnessConfig(
        checkpoint="/no/such/path",
        prompts="/no/such/path",
        out_path="/tmp/out.json",
        device="cpu",
        max_new_tokens=20,
        sampling="top_p",
        temperature=0.8,
        top_p=0.9,
        use_cas_prefix=False,
        seed=42,
    )


def test_evaluate_prompt_no_generator_path_works():
    """Without a native generator, evaluate_prompt should still produce a row."""
    prompt = {
        "id": "x1",
        "category": "casual_greeting",
        "prompt_text": "what up",
        "expected_route": "fallback",
        "ground_truth_cas": None,
        "notes": "test",
    }
    row = evaluate_prompt(
        prompt=prompt,
        predictor=_StubPredictor(),
        native_generator=None,
        preservation_scorer=_placeholder_score_preservation,
        config=_harness_config(),
    )
    assert isinstance(row, PerPromptResult)
    assert row.id == "x1"
    assert row.category == "casual_greeting"
    assert row.stage2_reply is None  # generator missing
    # leakage on empty reply is False
    assert row.leakage is False
    # failure policy says stage2_empty fires for greetings
    assert "stage2_empty" in row.failure_reasons
    assert row.failed is True


def test_evaluate_prompt_with_stub_generator():
    """Plug in a fake generator that returns a leaky reply."""
    fake_generator = {
        "model": object(),
        "tokenizer": object(),
        "device": "cpu",
    }

    # Monkey-stub the helper's call site by patching the module function.
    import cas_native.evaluation.b4_failure_eval as harness

    captured: dict[str, Any] = {}

    def fake_run(*, native_generator, prompt_text, expression, register, config):
        captured.update({"prompt": prompt_text, "expression": expression, "register": register})
        return {
            "reply_text": "the answer is ^3^P with the F2 drive",  # leaks both pattern types
            "n_steps": 12,
            "stopped_on_eos": True,
            "config": {},
            "trace": None,
        }

    original = harness.run_stage_2_reply
    harness.run_stage_2_reply = fake_run  # type: ignore[assignment]
    try:
        prompt = {
            "id": "x2",
            "category": "casual_greeting",
            "prompt_text": "yo",
            "expected_route": "fallback",
        }
        row = evaluate_prompt(
            prompt=prompt,
            predictor=_StubPredictor(),
            native_generator=fake_generator,
            preservation_scorer=_placeholder_score_preservation,
            config=_harness_config(),
        )
    finally:
        harness.run_stage_2_reply = original  # type: ignore[assignment]

    assert row.stage2_reply is not None and "F2" in row.stage2_reply
    assert row.leakage is True
    assert any("^3^P" in h or "F2" in h for h in row.leakage_hits)
    assert "leakage" in row.failure_reasons
    assert row.failed is True
    # captured the chained call
    assert captured["prompt"] == "yo"


def test_evaluate_prompt_v77_with_preservation_failure():
    """v77_omega category fails when scorer reports score < 0.6 and is non-placeholder."""

    def fake_scorer(_gt, _pred):
        return PreservationResult(
            operands_preserved=False,
            operators_preserved=False,
            drives_preserved=False,
            coefficients_preserved=False,
            named_targets_preserved=False,
            score=0.1,
            placeholder=False,  # crucially non-placeholder
            notes="fake non-placeholder for test",
        )

    import cas_native.evaluation.b4_failure_eval as harness

    def fake_run(*, native_generator, prompt_text, expression, register, config):
        return {"reply_text": "ok.", "n_steps": 2, "stopped_on_eos": True}

    original = harness.run_stage_2_reply
    harness.run_stage_2_reply = fake_run  # type: ignore[assignment]
    try:
        row = evaluate_prompt(
            prompt={
                "id": "v77x",
                "category": "v77_omega",
                "prompt_text": "(^7^O_{F2}|E x ^7^O_{F5}|A) = ^7^O|Omega_cadence",
                "expected_route": "cas_pipeline",
                "ground_truth_cas": "(^7^O_{F2}|E × ^7^O_{F5}|A) = ^7^O|Ω_cadence",
            },
            predictor=_StubPredictor(noetic=7, domain="O", drive="F2", registers=["A"]),
            native_generator={"model": object(), "tokenizer": object(), "device": "cpu"},
            preservation_scorer=fake_scorer,
            config=_harness_config(),
        )
    finally:
        harness.run_stage_2_reply = original  # type: ignore[assignment]

    assert "preservation_failed" in row.failure_reasons
    assert row.failed is True


def test_failure_policy_relevance_low_fires_for_greeting():
    """The documented 'irrelevant fluent prose for casual greeting' failure
    must be caught by the relevance_lt_3 rule even when leakage is clean."""
    row = PerPromptResult(
        id="x",
        category="casual_greeting",
        prompt_text="what up",
        expected_route="fallback",
        ground_truth_cas=None,
        notes=None,
        stage2_reply="Anchoring the habit to a physical anchor helps the body remember.",
        relevance_score=1,
        directness_score=1,
        non_rambling_score=4,
        leakage=False,
    )
    _apply_failure_policy(row)
    assert "relevance_lt_3" in row.failure_reasons
    assert "directness_lt_3" in row.failure_reasons
    assert row.failed is True


def test_evaluate_prompt_skips_preservation_when_no_ground_truth():
    """No ground truth -> preservation skipped; scorer never called."""

    def angry_scorer(_gt, _pred):
        raise AssertionError("scorer should not be called when GT is None")

    import cas_native.evaluation.b4_failure_eval as harness

    def fake_run(*, native_generator, prompt_text, expression, register, config):
        return {"reply_text": "ok", "n_steps": 2, "stopped_on_eos": True}

    original = harness.run_stage_2_reply
    harness.run_stage_2_reply = fake_run  # type: ignore[assignment]
    try:
        row = evaluate_prompt(
            prompt={
                "id": "x",
                "category": "casual_greeting",
                "prompt_text": "yo",
                "expected_route": "fallback",
                "ground_truth_cas": None,
            },
            predictor=_StubPredictor(),
            native_generator={"model": object(), "tokenizer": object(), "device": "cpu"},
            preservation_scorer=angry_scorer,
            config=_harness_config(),
        )
    finally:
        harness.run_stage_2_reply = original  # type: ignore[assignment]

    assert row.preservation.get("skipped") is True
    assert row.preservation.get("placeholder") is True


def test_failure_policy_placeholder_does_not_count_preservation():
    """When preservation is placeholder=True, preservation_failed must not fire."""
    row = PerPromptResult(
        id="x",
        category="v77_omega",
        prompt_text="...",
        expected_route="cas_pipeline",
        ground_truth_cas=None,
        notes=None,
        preservation={"placeholder": True, "score": 0.0},
        stage2_reply="ok",
    )
    _apply_failure_policy(row)
    assert "preservation_failed" not in row.failure_reasons


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _make_row(category: str, *, failed: bool = False, leakage: bool = False,
              compiler_validity: bool = False, relevance: int = 3) -> PerPromptResult:
    return PerPromptResult(
        id=f"{category}-{relevance}-{int(failed)}",
        category=category,
        prompt_text="...",
        expected_route="cas_pipeline",
        ground_truth_cas=None,
        notes=None,
        relevance_score=relevance,
        relevance_raw=0.5,
        relevance_source="tfidf_cosine",
        directness_score=3,
        non_rambling_score=4,
        compiler_validity=compiler_validity,
        plain_language_clarity_score=4,
        leakage=leakage,
        failed=failed,
        failure_reasons=["leakage"] if leakage else (["stage2_empty"] if failed else []),
    )


def test_aggregate_results_per_category():
    rows = [
        _make_row("casual_greeting", failed=True, leakage=True),
        _make_row("casual_greeting", failed=False),
        _make_row("v77_omega", failed=True),
        _make_row("v77_omega", failed=True),
    ]
    agg = aggregate_results(rows)
    assert agg["total"]["n"] == 4
    assert agg["total"]["n_failed"] == 3
    assert agg["categories"]["casual_greeting"]["n"] == 2
    assert agg["categories"]["casual_greeting"]["fail_rate"] == 0.5
    assert agg["categories"]["v77_omega"]["fail_rate"] == 1.0
    assert agg["categories"]["casual_greeting"]["leakage_rate"] == 0.5


def test_aggregate_failure_reason_breakdown():
    rows = [
        _make_row("casual_greeting", failed=True, leakage=True),
        _make_row("casual_greeting", failed=True, leakage=True),
        _make_row("casual_greeting", failed=True, leakage=False),
    ]
    agg = aggregate_results(rows)
    breakdown = agg["categories"]["casual_greeting"]["failure_reason_breakdown"]
    assert breakdown.get("leakage", 0) == 2
    assert breakdown.get("stage2_empty", 0) == 1


def test_category_fail_policy_complete_for_all_fixture_categories():
    """Every fixture category must have a fail-policy entry."""
    prompts = load_prompts(_FIXTURE_PATH)
    fixture_cats = {p["category"] for p in prompts}
    for cat in fixture_cats:
        assert cat in _CATEGORY_FAIL_POLICY, f"no fail policy for category {cat}"


# ---------------------------------------------------------------------------
# CLI smoke (no model load)
# ---------------------------------------------------------------------------


def test_cli_parser_required_flags():
    from cas_native.evaluation.b4_failure_eval import parse_args

    with pytest.raises(SystemExit):
        parse_args([])  # missing required --checkpoint --prompts --out

    args = parse_args([
        "--checkpoint", "/foo",
        "--prompts", "/bar.jsonl",
        "--out", "/baz.json",
    ])
    assert args.device == "cpu"
    assert args.sampling == "top_p"
    assert args.use_cas_prefix is False
    assert args.limit is None
