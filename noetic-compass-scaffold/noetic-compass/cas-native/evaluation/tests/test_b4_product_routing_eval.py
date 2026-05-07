"""Tests for the B-4 product-routing eval harness.

Mirrors the stub-based testing pattern of test_b4_failure_eval.py: the
predictor and native generator are stubbed out, the K=9 checkpoint and
the model are never loaded. The OODGate is the real thing (it's pure
Python, no I/O, deterministic) so the routing decisions exercised here
are the same ones the product would make.
"""

from __future__ import annotations

import sys
import types
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest


# Path bootstrap matches test_b4_failure_eval.py.
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.resolve().parents[3]  # noetic-compass/

if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__path__ = [str(_REPO_ROOT / "cas-native")]
    sys.modules["cas_native"] = pkg
sys.path.insert(0, str(_REPO_ROOT))


from cas_native.evaluation.b4_failure_eval import (  # noqa: E402
    HarnessConfig,
    _placeholder_score_preservation,
)
from cas_native.evaluation.b4_product_routing_eval import (  # noqa: E402
    PerPromptRoutingResult,
    aggregate_routing_results,
    apply_routing_failure_policy,
    build_comparison_block,
    build_k9_result_for_gate,
    evaluate_prompt_routing,
    is_route_match,
    parse_args,
)
from cas_native.inference.ood_gate import (  # noqa: E402
    OODGate,
    RouteDecision,
)


# ---------------------------------------------------------------------------
# Stub Predictor (deterministic, no model load)
# ---------------------------------------------------------------------------


class _StubPredictor:
    """Mirrors test_b4_failure_eval._StubPredictor."""

    def __init__(
        self,
        *,
        noetic: int = 3,
        domain: str = "P",
        drive: str = "F4",
        registers: list[str] | None = None,
    ) -> None:
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


def _gate() -> OODGate:
    return OODGate(confidence_threshold=0.4, casual_word_limit=10)


# ---------------------------------------------------------------------------
# is_route_match — the load-bearing routing-correctness predicate
# ---------------------------------------------------------------------------


def test_is_route_match_cas_pipeline():
    assert is_route_match("cas_pipeline", RouteDecision.CAS_PIPELINE) is True
    assert is_route_match("cas_pipeline", RouteDecision.CONVERSATIONAL_FALLBACK) is False
    assert is_route_match("cas_pipeline", RouteDecision.CLARIFICATION) is False
    assert is_route_match("cas_pipeline", RouteDecision.NEED_CONTEXT) is False


def test_is_route_match_fallback():
    assert is_route_match("fallback", RouteDecision.CONVERSATIONAL_FALLBACK) is True
    assert is_route_match("fallback", RouteDecision.CAS_PIPELINE) is False
    assert is_route_match("fallback", RouteDecision.CLARIFICATION) is False


def test_is_route_match_clarification_accepts_need_context():
    """Fixture vocabulary doesn't distinguish CLARIFICATION from NEED_CONTEXT;
    both align with the 'I can't ship this without more context' semantic."""
    assert is_route_match("clarification", RouteDecision.CLARIFICATION) is True
    assert is_route_match("clarification", RouteDecision.NEED_CONTEXT) is True
    assert is_route_match("clarification", RouteDecision.CAS_PIPELINE) is False


def test_is_route_match_unknown_expected_returns_false():
    assert is_route_match("not_a_route", RouteDecision.CAS_PIPELINE) is False


# ---------------------------------------------------------------------------
# build_k9_result_for_gate — chat.py mirror
# ---------------------------------------------------------------------------


def test_build_k9_result_for_gate_no_signal_adds_ood_note():
    pred = {"noetic": 3, "domain": "P", "registers": ["A"]}
    out = build_k9_result_for_gate(pred, has_cas_signal=False)
    assert "notes" in out
    assert any("no CAS signal detected" in n for n in out["notes"])
    # original pred fields are preserved
    assert out["noetic"] == 3
    assert out["domain"] == "P"


def test_build_k9_result_for_gate_with_signal_omits_note():
    pred = {"noetic": 3, "domain": "P", "registers": ["A"]}
    out = build_k9_result_for_gate(pred, has_cas_signal=True)
    assert "notes" not in out
    assert out["noetic"] == 3


# ---------------------------------------------------------------------------
# evaluate_prompt_routing — gated path (casual prompt)
# ---------------------------------------------------------------------------


def test_casual_prompt_routes_to_fallback_and_skips_stage2(monkeypatch):
    """A casual greeting must route to CONVERSATIONAL_FALLBACK and the native
    generator must NEVER be invoked (Stage 2 skipped)."""
    import cas_native.evaluation.b4_product_routing_eval as harness

    def _no_signal(_text: str) -> dict[str, Any]:
        return {"has_signal": False}

    # Force the no-signal branch deterministically without importing the shim.
    monkeypatch.setattr(harness, "_detect_signal_safe", _no_signal)

    # Stage-2 must NOT be called when gated. If it is, fail loudly.
    def _exploding_run_stage_2(*args, **kwargs):
        raise AssertionError("Stage 2 must not run for gated prompts")

    monkeypatch.setattr(harness, "run_stage_2_reply", _exploding_run_stage_2)

    prompt = {
        "id": "greet_test_01",
        "category": "casual_greeting",
        "prompt_text": "what up",
        "expected_route": "fallback",
        "ground_truth_cas": None,
    }
    row = evaluate_prompt_routing(
        prompt=prompt,
        predictor=_StubPredictor(),
        native_generator={"model": object(), "tokenizer": object(), "device": "cpu"},
        preservation_scorer=_placeholder_score_preservation,
        config=_harness_config(),
        gate=_gate(),
    )
    assert row.gated is True
    assert row.actual_route == RouteDecision.CONVERSATIONAL_FALLBACK.value
    assert row.stage2_reply is None
    assert (row.gate_canned_response or "").strip()  # canned reply present
    assert row.failed is False  # gated routing IS success for casual_greeting


def test_confusion_prompt_routes_to_clarification(monkeypatch):
    """A long-form confusion prompt with no CAS signal goes to CLARIFICATION."""
    import cas_native.evaluation.b4_product_routing_eval as harness

    monkeypatch.setattr(
        harness, "_detect_signal_safe", lambda _t: {"has_signal": False}
    )

    def _exploding_run_stage_2(*args, **kwargs):
        raise AssertionError("Stage 2 must not run when gated")

    monkeypatch.setattr(harness, "run_stage_2_reply", _exploding_run_stage_2)

    prompt = {
        "id": "conf_test_01",
        "category": "confusion",
        # >= 10 words to land in CLARIFICATION rather than FALLBACK
        "prompt_text": "I really have absolutely no idea what you are even asking me here",
        "expected_route": "clarification",
        "ground_truth_cas": None,
    }
    row = evaluate_prompt_routing(
        prompt=prompt,
        predictor=_StubPredictor(),
        native_generator={"model": object(), "tokenizer": object(), "device": "cpu"},
        preservation_scorer=_placeholder_score_preservation,
        config=_harness_config(),
        gate=_gate(),
    )
    assert row.gated is True
    assert row.actual_route == RouteDecision.CLARIFICATION.value
    assert row.stage2_reply is None
    assert row.route_match is True  # 'clarification' allows CLARIFICATION


# ---------------------------------------------------------------------------
# evaluate_prompt_routing — pipeline path (valid CAS prompt)
# ---------------------------------------------------------------------------


def test_valid_cas_prompt_routes_to_pipeline_and_runs_stage2(monkeypatch):
    """A signal-bearing CAS prompt with a confident K=9 result must reach
    Stage 2 (the native generator), not the gate's canned branch."""
    import cas_native.evaluation.b4_product_routing_eval as harness

    # Pretend detect_cas_signal said "has_signal=True" so the gate's OOD
    # sentinel path is bypassed.
    monkeypatch.setattr(
        harness, "_detect_signal_safe", lambda _t: {"has_signal": True}
    )

    captured: dict[str, Any] = {}

    def _fake_run_stage_2(*, native_generator, prompt_text, expression, register, config):
        captured["called"] = True
        captured["expression"] = expression
        captured["register"] = register
        return {
            "reply_text": "Yes, I understand. Could you say more about consent?",
            "n_steps": 12,
            "stopped_on_eos": True,
        }

    monkeypatch.setattr(harness, "run_stage_2_reply", _fake_run_stage_2)

    prompt = {
        "id": "valid_test_01",
        "category": "valid_cas_notation",
        "prompt_text": "Tell me you understand consent before we keep going",
        "expected_route": "cas_pipeline",
        "ground_truth_cas": "^3^P_{F7}|A",
    }
    row = evaluate_prompt_routing(
        prompt=prompt,
        predictor=_StubPredictor(noetic=3, domain="P", drive="F7", registers=["A"]),
        native_generator={"model": object(), "tokenizer": object(), "device": "cpu"},
        preservation_scorer=_placeholder_score_preservation,
        config=_harness_config(),
        gate=_gate(),
    )
    assert row.gated is False
    assert row.actual_route == RouteDecision.CAS_PIPELINE.value
    assert captured.get("called") is True  # Stage 2 ran
    assert row.stage2_reply is not None and "consent" in row.stage2_reply
    assert row.route_match is True


def test_v77_prompt_blocked_by_gate_marks_routing_regression(monkeypatch):
    """If the gate erroneously blocks a v77_omega prompt, the row must be
    flagged as a routing regression — that is the headline failure mode this
    eval is designed to catch."""
    import cas_native.evaluation.b4_product_routing_eval as harness

    # Force no-signal even though the prompt is valid CAS; this simulates a
    # mis-detection regression upstream of the gate.
    monkeypatch.setattr(
        harness, "_detect_signal_safe", lambda _t: {"has_signal": False}
    )

    def _exploding_run_stage_2(*args, **kwargs):
        raise AssertionError("Stage 2 must not run when gated")

    monkeypatch.setattr(harness, "run_stage_2_reply", _exploding_run_stage_2)

    prompt = {
        "id": "v77_test_01",
        "category": "v77_omega",
        # short and contains "yo" / casual-ish; gate will route to FALLBACK.
        "prompt_text": "yo what",
        "expected_route": "cas_pipeline",
        "ground_truth_cas": "(^7^O_{F2}|E × ^7^O_{F5}|A) = ^7^O|Ω_cadence",
    }
    row = evaluate_prompt_routing(
        prompt=prompt,
        predictor=_StubPredictor(),
        native_generator={"model": object(), "tokenizer": object(), "device": "cpu"},
        preservation_scorer=_placeholder_score_preservation,
        config=_harness_config(),
        gate=_gate(),
    )
    assert row.gated is True
    assert row.actual_route != RouteDecision.CAS_PIPELINE.value
    assert "regression_gate_blocked_pipeline" in row.failure_reasons
    assert row.failed is True


# ---------------------------------------------------------------------------
# route_match correctness on regression
# ---------------------------------------------------------------------------


def test_route_match_true_when_actual_matches_expected(monkeypatch):
    """When a casual prompt expects 'fallback' and the gate routes to
    CONVERSATIONAL_FALLBACK, route_match must be True."""
    import cas_native.evaluation.b4_product_routing_eval as harness

    monkeypatch.setattr(
        harness, "_detect_signal_safe", lambda _t: {"has_signal": False}
    )
    monkeypatch.setattr(
        harness,
        "run_stage_2_reply",
        lambda **_: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    prompt = {
        "id": "match_ok_01",
        "category": "casual_greeting",
        "prompt_text": "yo",
        "expected_route": "fallback",
        "ground_truth_cas": None,
    }
    row = evaluate_prompt_routing(
        prompt=prompt,
        predictor=_StubPredictor(),
        native_generator=None,
        preservation_scorer=_placeholder_score_preservation,
        config=_harness_config(),
        gate=_gate(),
    )
    assert row.actual_route == RouteDecision.CONVERSATIONAL_FALLBACK.value
    assert row.route_match is True


def test_route_match_false_when_casual_erroneously_pipelined(monkeypatch):
    """REGRESSION CHECK: a casual prompt that erroneously routes to the CAS
    pipeline (gate failure) must report route_match=False — that's the
    documented B-3 failure mode this harness exists to catch."""
    import cas_native.evaluation.b4_product_routing_eval as harness

    # Force has_signal=True so the OOD-sentinel branch of the gate is
    # bypassed AND the predictor returns confident output -> CAS_PIPELINE
    # for a prompt whose fixture says 'fallback'. This is the regression
    # the harness must surface.
    monkeypatch.setattr(
        harness, "_detect_signal_safe", lambda _t: {"has_signal": True}
    )

    def _fake_stage_2(*, native_generator, prompt_text, expression, register, config):
        return {
            "reply_text": "(some long-winded irrelevant fluent-prose reply about embodied habits)",
            "n_steps": 80,
            "stopped_on_eos": False,
        }

    monkeypatch.setattr(harness, "run_stage_2_reply", _fake_stage_2)

    prompt = {
        "id": "regression_01",
        "category": "casual_greeting",
        "prompt_text": "yo",
        "expected_route": "fallback",
        "ground_truth_cas": None,
    }
    row = evaluate_prompt_routing(
        prompt=prompt,
        predictor=_StubPredictor(),
        native_generator={"model": object(), "tokenizer": object(), "device": "cpu"},
        preservation_scorer=_placeholder_score_preservation,
        config=_harness_config(),
        gate=_gate(),
    )
    assert row.gated is False  # gate let it through
    assert row.actual_route == RouteDecision.CAS_PIPELINE.value
    # expected_route='fallback' -> CONVERSATIONAL_FALLBACK only; CAS_PIPELINE is wrong.
    assert row.route_match is False
    # The raw-model failure policy fires for the casual_greeting category
    # because the prompt and reply have low topical overlap.
    assert row.failed is True


# ---------------------------------------------------------------------------
# Failure policy — direct unit tests
# ---------------------------------------------------------------------------


def test_failure_policy_pipeline_required_blocked_marks_regression():
    row = PerPromptRoutingResult(
        id="x",
        category="v76_production",
        prompt_text="...",
        expected_route="cas_pipeline",
        actual_route="conv_fallback",
        route_match=False,
        gated=True,
        gate_canned_response="canned",
        gate_reason="ood",
        ground_truth_cas="Θ(Ω) = 1.0*^3^P_{F2}|A → Ω",
        notes=None,
    )
    apply_routing_failure_policy(row)
    assert row.failed is True
    assert "regression_gate_blocked_pipeline" in row.failure_reasons


def test_failure_policy_gated_casual_passes():
    row = PerPromptRoutingResult(
        id="x",
        category="casual_greeting",
        prompt_text="yo",
        expected_route="fallback",
        actual_route="conv_fallback",
        route_match=True,
        gated=True,
        gate_canned_response="Hey — that one's outside what I can read as CAS structure.",
        gate_reason="...",
        ground_truth_cas=None,
        notes=None,
    )
    # Auto-scorer values that the gated branch would produce for a non-leaky
    # short canned response (set explicitly to validate the policy ignores
    # them for gated rows).
    row.relevance_score = 1
    row.directness_score = 1
    row.non_rambling_score = 5
    apply_routing_failure_policy(row)
    assert row.failed is False
    assert row.failure_reasons == []


def test_failure_policy_gated_canned_leakage_fails():
    """Defensive: if the gate's canned response somehow contains CAS notation
    (contract violation), the row must be flagged."""
    row = PerPromptRoutingResult(
        id="x",
        category="casual_greeting",
        prompt_text="yo",
        expected_route="fallback",
        actual_route="conv_fallback",
        route_match=True,
        gated=True,
        gate_canned_response="bogus ^3^P leak",
        gate_reason="...",
        ground_truth_cas=None,
        notes=None,
        leakage=True,
    )
    apply_routing_failure_policy(row)
    assert row.failed is True
    assert "gate_canned_response_leaks_cas_notation" in row.failure_reasons


def test_failure_policy_invalid_cas_pass_when_response_nonempty():
    row = PerPromptRoutingResult(
        id="x",
        category="invalid_cas",
        prompt_text="explain ^11^X_{F9}|Z",
        expected_route="cas_pipeline",
        actual_route="cas_pipeline",
        route_match=True,
        gated=False,
        gate_canned_response=None,
        gate_reason="...",
        ground_truth_cas=None,
        notes=None,
        stage2_reply="That notation doesn't compile; ^11 is out of range.",
    )
    apply_routing_failure_policy(row)
    assert row.failed is False


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _row(category: str, *, gated: bool, actual: RouteDecision, expected: str,
         failed: bool = False) -> PerPromptRoutingResult:
    return PerPromptRoutingResult(
        id=f"{category}-{actual.value}-{int(failed)}",
        category=category,
        prompt_text="...",
        expected_route=expected,
        actual_route=actual.value,
        route_match=is_route_match(expected, actual),
        gated=gated,
        gate_canned_response="canned" if gated else None,
        gate_reason="",
        ground_truth_cas=None,
        notes=None,
        failed=failed,
        failure_reasons=["regression_gate_blocked_pipeline"] if failed else [],
    )


def test_aggregate_routing_results_per_category():
    rows = [
        _row("casual_greeting", gated=True, actual=RouteDecision.CONVERSATIONAL_FALLBACK, expected="fallback"),
        _row("casual_greeting", gated=True, actual=RouteDecision.CONVERSATIONAL_FALLBACK, expected="fallback"),
        _row("casual_greeting", gated=False, actual=RouteDecision.CAS_PIPELINE, expected="fallback", failed=True),
        _row("v77_omega", gated=False, actual=RouteDecision.CAS_PIPELINE, expected="cas_pipeline"),
        _row("v77_omega", gated=True, actual=RouteDecision.CONVERSATIONAL_FALLBACK, expected="cas_pipeline", failed=True),
    ]
    agg = aggregate_routing_results(rows)
    assert agg["total"]["n"] == 5
    assert agg["total"]["n_failed"] == 2
    assert agg["categories"]["casual_greeting"]["n"] == 3
    assert agg["categories"]["casual_greeting"]["route_match_rate"] == pytest.approx(2 / 3)
    assert agg["categories"]["casual_greeting"]["gated_rate"] == pytest.approx(2 / 3)
    assert agg["categories"]["v77_omega"]["fail_rate"] == pytest.approx(0.5)
    assert agg["categories"]["v77_omega"]["route_match_rate"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Comparison block
# ---------------------------------------------------------------------------


def test_comparison_block_unavailable_when_no_raw_manifest():
    block = build_comparison_block(raw_manifest=None, product_aggregate={"total": {}, "categories": {}})
    assert block == {"available": False}


def test_comparison_block_per_category_format():
    raw_manifest = {
        "aggregate": {
            "total": {"fail_rate": 0.866, "n": 60},
            "categories": {
                "casual_greeting": {"fail_rate": 1.0, "n": 6},
                "v77_omega": {"fail_rate": 1.0, "n": 6},
            },
        }
    }
    product_agg = {
        "total": {"fail_rate": 0.20, "n": 60},
        "categories": {
            "casual_greeting": {"fail_rate": 0.0, "n": 6},
            "v77_omega": {"fail_rate": 0.5, "n": 6},
        },
    }
    block = build_comparison_block(raw_manifest=raw_manifest, product_aggregate=product_agg)
    assert block["available"] is True
    # Per-category structure
    cas_cmp = block["per_category"]["casual_greeting"]
    assert cas_cmp["raw_model_fail_rate"] == pytest.approx(1.0)
    assert cas_cmp["product_fail_rate"] == pytest.approx(0.0)
    assert cas_cmp["delta"] == pytest.approx(-1.0)
    assert cas_cmp["raw_n"] == 6
    assert cas_cmp["product_n"] == 6
    # v77 partial improvement
    v77_cmp = block["per_category"]["v77_omega"]
    assert v77_cmp["delta"] == pytest.approx(-0.5)
    # Totals
    assert block["total"]["raw_model_fail_rate"] == pytest.approx(0.866)
    assert block["total"]["product_fail_rate"] == pytest.approx(0.20)
    assert block["total"]["delta"] == pytest.approx(0.20 - 0.866)


def test_comparison_block_handles_categories_only_in_one_side():
    """Categories present in one manifest but not the other must not crash."""
    raw_manifest = {
        "aggregate": {
            "total": {"fail_rate": 0.5, "n": 10},
            "categories": {
                "only_in_raw": {"fail_rate": 1.0, "n": 5},
            },
        }
    }
    product_agg = {
        "total": {"fail_rate": 0.0, "n": 10},
        "categories": {
            "only_in_product": {"fail_rate": 0.0, "n": 5},
        },
    }
    block = build_comparison_block(raw_manifest=raw_manifest, product_aggregate=product_agg)
    assert block["available"] is True
    assert "only_in_raw" in block["per_category"]
    assert "only_in_product" in block["per_category"]
    assert block["per_category"]["only_in_raw"]["product_fail_rate"] == 0.0
    assert block["per_category"]["only_in_product"]["raw_model_fail_rate"] == 0.0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_parser_required_flags():
    with pytest.raises(SystemExit):
        parse_args([])  # missing --checkpoint --prompts --out

    args = parse_args([
        "--checkpoint", "/foo",
        "--prompts", "/bar.jsonl",
        "--out", "/baz.json",
    ])
    assert args.device == "cpu"
    assert args.sampling == "top_p"
    assert args.gate_confidence_threshold == 0.4
    assert args.gate_casual_word_limit == 10
    assert args.raw_model_manifest is None
    assert args.no_rewrite is False


def test_cli_parser_accepts_raw_manifest_and_gate_overrides():
    args = parse_args([
        "--checkpoint", "/foo",
        "--prompts", "/bar.jsonl",
        "--out", "/baz.json",
        "--raw-model-manifest", "/raw.json",
        "--gate-confidence-threshold", "0.55",
        "--gate-casual-word-limit", "12",
        "--no-rewrite",
    ])
    assert str(args.raw_model_manifest).replace("\\", "/").endswith("/raw.json")
    assert args.gate_confidence_threshold == 0.55
    assert args.gate_casual_word_limit == 12
    assert args.no_rewrite is True


# ---------------------------------------------------------------------------
# Manifest serialization sanity (asdict round-trip)
# ---------------------------------------------------------------------------


def test_per_prompt_routing_result_is_serializable():
    """The manifest writes asdict(row); ensure the dataclass is fully
    JSON-serializable with default field types."""
    import json as _json

    row = PerPromptRoutingResult(
        id="x",
        category="casual_greeting",
        prompt_text="yo",
        expected_route="fallback",
        actual_route="conv_fallback",
        route_match=True,
        gated=True,
        gate_canned_response="canned",
        gate_reason="ood",
        ground_truth_cas=None,
        notes=None,
    )
    d = asdict(row)
    payload = _json.dumps(d)
    assert "\"gated\": true" in payload
    assert "\"route_match\": true" in payload
