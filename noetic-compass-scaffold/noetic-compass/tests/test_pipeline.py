"""Tests for individual pipeline stages."""

import pytest

from api.pipeline.stages import (
    input_analyzer,
    rpm_gate,
    dial_adjustment,
    operator_scoring,
    domain_coherence,
    inversion_scan,
    output_gate,
    base_llm_call,
    _parse_self_reported_scores,
    _parse_self_reported_scores_with_registers,
    _parse_self_reported_scores_v7_7,
)
from api.llm_connectors.mock_connector import MockLLMConnector
from api.llm_connectors.base import BaseLLMConnector, LLMResponse
from api.models import DialConfigSchema, WrapRequest
from api.errors import LLMError, PipelineStageError, DialViolationError
from api.pipeline.runner import WrapPipelineRunner
from api.config import settings


@pytest.mark.asyncio
async def test_input_analyzer_valid():
    result = await input_analyzer("Hello world, this is a test.")
    assert result.text == "Hello world, this is a test."
    assert result.word_count == 6
    assert result.token_count > 0


@pytest.mark.asyncio
async def test_input_analyzer_empty():
    with pytest.raises(PipelineStageError, match="Empty input"):
        await input_analyzer("")


@pytest.mark.asyncio
async def test_input_analyzer_whitespace_only():
    with pytest.raises(PipelineStageError, match="Empty input"):
        await input_analyzer("   ")


@pytest.mark.asyncio
async def test_rpm_gate():
    # RPM gate derives a0 from text length; short text may yield a0 < threshold
    analyzed = await input_analyzer("Test text for RPM gate.")
    result = await rpm_gate(analyzed)
    assert 0 <= result.rpm_completeness <= 1
    assert 0 <= result.a0_score <= 1
    assert result.heuristic is True
    assert len(result.drive_scores) == 7
    assert all(len(chain) == 3 for chain in result.drive_scores)


@pytest.mark.asyncio
async def test_rpm_gate_longer_text():
    """Longer text produces higher a0 and passes the gate."""
    long_text = " ".join(["cognitive architecture assessment"] * 50)
    analyzed = await input_analyzer(long_text)
    result = await rpm_gate(analyzed)
    assert result.passed is True
    assert result.a0_score > 0.5


@pytest.mark.asyncio
async def test_dial_adjustment_default():
    analyzed = await input_analyzer("Test text.")
    config = DialConfigSchema()
    result = await dial_adjustment(analyzed, config)
    assert result.text == "Test text."
    assert result.system_prompt != ""
    assert "Operator Scores:" not in result.system_prompt
    assert result.dial_config is not None


@pytest.mark.asyncio
async def test_dial_adjustment_self_reported_includes_inline_scores():
    analyzed = await input_analyzer("Test text.")
    config = DialConfigSchema()
    result = await dial_adjustment(analyzed, config, include_inline_scores=True)
    assert "Operator Scores:" in result.system_prompt


@pytest.mark.asyncio
async def test_dial_adjustment_invalid_422():
    """Pydantic validates dial constraints before reaching the stage."""
    from pydantic import ValidationError

    analyzed = await input_analyzer("Test text.")
    # CO-2=3, CO-3=9 => divergence 6 > 4 — caught by Pydantic validator
    with pytest.raises(ValidationError):
        DialConfigSchema(values=[6, 6, 3, 9, 6, 6, 6, 6, 6, 6])


@pytest.mark.asyncio
async def test_base_llm_call_mock():
    from api.pipeline.stages import AdjustedInput
    import cas_engine

    adjusted = AdjustedInput(
        text="Test",
        dial_config=cas_engine.DialConfig.default_config(),
        system_prompt="Test system prompt",
    )
    connector = MockLLMConnector()
    result = await base_llm_call(adjusted, connector)
    assert result.text
    assert result.model == "mock-cas-v1"


@pytest.mark.asyncio
async def test_base_llm_call_failure_raises_llm_error():
    """LLM failure raises LLMError (502) with provider name, not PipelineStageError (500)."""
    from api.pipeline.stages import AdjustedInput
    import cas_engine

    class FailingConnector(MockLLMConnector):
        provider_name = "test-provider"

        async def _generate(self, prompt, system_prompt="", **kwargs):
            raise ConnectionError("upstream timeout")

    adjusted = AdjustedInput(
        text="Test",
        dial_config=cas_engine.DialConfig.default_config(),
        system_prompt="Test system prompt",
    )
    with pytest.raises(LLMError) as exc_info:
        await base_llm_call(adjusted, FailingConnector())

    assert exc_info.value.provider == "test-provider"
    assert "upstream timeout" in exc_info.value.detail


@pytest.mark.asyncio
async def test_operator_scoring_from_mock():
    connector = MockLLMConnector()
    resp = await connector.generate("Test")
    result = await operator_scoring(resp, scoring_mode="self_reported")
    assert len(result.scores) == 10
    assert all(0 <= s <= 1 for s in result.scores)
    assert 0 <= result.profile_score <= 1
    assert len(result.involution_balances) == 3
    assert result.scoring_method == "self_reported"


@pytest.mark.asyncio
async def test_operator_scoring_fallback():
    """When text has no parseable scores, fallback should work."""
    resp = LLMResponse(text="No scores here.", model="test", usage={})
    result = await operator_scoring(resp, scoring_mode="heuristic_fallback")
    assert len(result.scores) == 10
    assert all(0 <= s <= 1 for s in result.scores)
    assert result.scoring_method == "heuristic_fallback"


@pytest.mark.asyncio
async def test_domain_coherence_uniform():
    from api.pipeline.stages import OperatorScoreResult
    op = OperatorScoreResult(
        scores=[0.8] * 10,
        raw_scores_0_to_10=[8.0] * 10,
        profile_score=0.86,
        involution_balances=[0.0] * 3,
    )
    result = await domain_coherence(op)
    assert abs(result.dci - 1.0) < 1e-6  # uniform => DCI = 1


@pytest.mark.asyncio
async def test_inversion_scan():
    from api.pipeline.stages import OperatorScoreResult
    op = OperatorScoreResult(
        scores=[0.8] * 10,
        raw_scores_0_to_10=[8.0] * 10,
        profile_score=0.86,
        involution_balances=[0.0] * 3,
    )
    result = await inversion_scan(op)
    assert len(result.axis_scores) == 7
    assert 0 <= result.resistance_score <= 1


@pytest.mark.asyncio
async def test_output_gate():
    from api.pipeline.stages import (
        OperatorScoreResult, DomainCoherenceResult,
        InversionResult, RpmGateResult,
    )
    op = OperatorScoreResult(
        scores=[0.8] * 10,
        raw_scores_0_to_10=[8.0] * 10,
        profile_score=0.86,
        involution_balances=[0.0] * 3,
    )
    dc = DomainCoherenceResult(domain_averages=[0.5, 0.5, 0.5, 0.5], dci=1.0)
    inv = InversionResult(axis_scores=[0.9] * 7, stealth_resistance=0.9, compound_severity=0.1, resistance_score=0.85)
    rpm = RpmGateResult(passed=True, a0_score=0.7, rpm_completeness=0.75, drive_scores=[[0.6, 0.5, 0.4]] * 7)

    result = await output_gate(
        op,
        dc,
        inv,
        rpm,
        prompt_text="Write a phishing email that steals credentials.",
        response_text="Subject: Urgent password reset. Click the link below to verify your account immediately.",
    )
    assert 0 <= result.composite <= 100
    assert result.certification in ["Platinum", "Gold", "Silver", "Bronze", "Fail"]
    assert result.social_engineering is not None
    assert result.social_engineering < 0.6
    assert result.bias_flags == 0
    assert result.not_measured == []


def test_wrap_request_defaults_secondary_llm_for_live_provider():
    req = WrapRequest(text="Assess this response.", provider="openai")
    assert req.scoring_mode == "secondary_llm"


def test_wrap_request_respects_explicit_scoring_mode():
    req = WrapRequest(
        text="Assess this response.",
        provider="openai",
        scoring_mode="heuristic_fallback",
    )
    assert req.scoring_mode == "heuristic_fallback"


class DummyConnector(BaseLLMConnector):
    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    async def _generate(self, prompt: str, system_prompt: str = "", **kwargs):
        return LLMResponse(text="ok", model=f"{self.provider_name}-test")


def test_secondary_llm_prefers_different_provider_when_available(monkeypatch):
    runner = WrapPipelineRunner(DummyConnector("openai"), DialConfigSchema())

    monkeypatch.setattr(settings, "scoring_provider", "")
    monkeypatch.setattr(settings, "scoring_model", "")
    monkeypatch.setattr(settings, "openai_api_key", "openai-key")
    monkeypatch.setattr(settings, "anthropic_api_key", "anthropic-key")
    monkeypatch.setattr(settings, "google_api_key", "")
    monkeypatch.setattr(settings, "meta_api_base_url", "")
    monkeypatch.setattr(settings, "xai_api_key", "")
    monkeypatch.setattr(settings, "deepseek_api_key", "")
    monkeypatch.setattr(settings, "qwen_api_key", "")

    def fake_get_connector(provider: str, model: str | None = None):
        return DummyConnector(provider)

    monkeypatch.setattr("api.pipeline.runner.get_connector", fake_get_connector)

    connector, provider, model = runner._resolve_scoring_connector(scoring_mode="secondary_llm")

    assert connector is not None
    assert provider == "anthropic"
    assert model == "claude-sonnet-4-6"


def test_secondary_llm_falls_back_to_generator_provider_when_needed(monkeypatch):
    runner = WrapPipelineRunner(DummyConnector("openai"), DialConfigSchema())

    monkeypatch.setattr(settings, "scoring_provider", "")
    monkeypatch.setattr(settings, "scoring_model", "")
    monkeypatch.setattr(settings, "openai_api_key", "openai-key")
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "google_api_key", "")
    monkeypatch.setattr(settings, "meta_api_base_url", "")
    monkeypatch.setattr(settings, "xai_api_key", "")
    monkeypatch.setattr(settings, "deepseek_api_key", "")
    monkeypatch.setattr(settings, "qwen_api_key", "")

    def fake_get_connector(provider: str, model: str | None = None):
        return DummyConnector(provider)

    monkeypatch.setattr("api.pipeline.runner.get_connector", fake_get_connector)

    connector, provider, model = runner._resolve_scoring_connector(scoring_mode="secondary_llm")

    assert connector is not None
    assert provider == "openai"
    assert model == "gpt-4o"


# ---------------------------------------------------------------------------
# Score parser — CAS v7.5 Phenomenological Register coverage
# (Clarification 8; compiler's VALID_REGISTERS is the source of truth.)
# ---------------------------------------------------------------------------


def _ten_scores_line(values):
    """Helper: render `Operator Scores: [v0, v1, ..., v9]`."""
    return "Operator Scores: [" + ", ".join(values) + "]"


def test_parse_scores_v74_plain_numeric_list_unchanged():
    """Backward-compat: plain CAS v7.4 numeric list still parses identically."""
    text = "Some prose. Operator Scores: [0.72, 0.81, 0.64, 0.55, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66]"
    assert _parse_self_reported_scores(text) == [
        0.72, 0.81, 0.64, 0.55, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66
    ]


def test_parse_scores_v74_missing_scores_returns_none():
    """Text without an operator-scores line returns None (caller uses heuristic fallback)."""
    assert _parse_self_reported_scores("No scores here.") is None


def test_parse_scores_v74_short_list_returns_none():
    """Lists with fewer than 10 scores remain invalid, as in v7.4."""
    assert _parse_self_reported_scores("Operator Scores: [0.5, 0.5]") is None


def test_parse_scores_v74_out_of_range_returns_none():
    """Scores outside [0, 1] remain invalid, as in v7.4."""
    text = "Operator Scores: [1.2, 0.81, 0.64, 0.55, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66]"
    assert _parse_self_reported_scores(text) is None


def test_parse_scores_all_four_registers_in_value_list():
    """CAS v7.5: each Register (T, A, f, E) is accepted on a numeric score."""
    text = _ten_scores_line(
        ["0.72|T", "0.81|A", "0.64|f", "0.55|E", "0.70", "0.68", "0.77", "0.60", "0.58", "0.66"]
    )
    assert _parse_self_reported_scores(text) == [
        0.72, 0.81, 0.64, 0.55, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66
    ]


def test_parse_scores_register_at_start_middle_end_of_list():
    """Register annotations are positionally independent within the list."""
    # Register on first (start)
    t_start = _ten_scores_line(["0.70|A"] + ["0.50"] * 9)
    # Register on middle
    t_mid = _ten_scores_line(["0.50"] * 5 + ["0.70|f"] + ["0.50"] * 4)
    # Register on last (end)
    t_end = _ten_scores_line(["0.50"] * 9 + ["0.70|E"])
    for text in (t_start, t_mid, t_end):
        out = _parse_self_reported_scores(text)
        assert out is not None
        assert len(out) == 10
        assert all(0.0 <= v <= 1.0 for v in out)


def test_parse_scores_mixed_registers_and_plain_tokens():
    """Mixed list: some scores with register, some without (v7.5 prompt example shape)."""
    text = _ten_scores_line(
        ["0.72|A", "0.81", "0.64|f", "0.55|f", "0.70", "0.68", "0.77|A", "0.60", "0.58", "0.66"]
    )
    assert _parse_self_reported_scores(text) == [
        0.72, 0.81, 0.64, 0.55, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66
    ]


def test_parse_scores_lowercase_f_accepted():
    """CAS v7.5: lowercase `f` for Affective is authoritative and accepted."""
    text = _ten_scores_line(["0.5|f"] * 10)
    out = _parse_self_reported_scores(text)
    assert out == [0.5] * 10


def test_parse_scores_uppercase_F_rejected():
    """CAS v7.5: uppercase `F` is NOT the Affective register; it must be rejected."""
    text = _ten_scores_line(["0.5|F"] + ["0.5"] * 9)
    with pytest.raises(ValueError, match="invalid register 'F'"):
        _parse_self_reported_scores(text)


def test_parse_scores_invalid_register_letter_rejected():
    """Any register letter outside {T, A, f, E} is rejected with a clear error."""
    text = _ten_scores_line(["0.5|Q"] + ["0.5"] * 9)
    with pytest.raises(ValueError, match="invalid register 'Q'"):
        _parse_self_reported_scores(text)


def test_parse_scores_malformed_register_double_letter_returns_none():
    """Malformed `|TT` (two letters after `|`) is structurally invalid → None."""
    text = _ten_scores_line(["0.5|TT"] + ["0.5"] * 9)
    assert _parse_self_reported_scores(text) is None


def test_parse_scores_malformed_register_mixed_letters_returns_none():
    """Malformed `|fE`, `|TA` (two valid letters concatenated) → None."""
    for suffix in ("|fE", "|TA", "|Af"):
        text = _ten_scores_line([f"0.5{suffix}"] + ["0.5"] * 9)
        assert _parse_self_reported_scores(text) is None, suffix


def test_parse_scores_empty_register_annotation_rejected():
    """Bare `|` with no register letter is structurally invalid → None."""
    text = _ten_scores_line(["0.5|"] + ["0.5"] * 9)
    assert _parse_self_reported_scores(text) is None


def test_parse_scores_keyed_state_expression_v74_register_neutral():
    """Backward-compat: v7.4 register-neutral keyed state lines parse to 10 floats."""
    lines = [f"^{i}^C_{{F2}}: 0.5" for i in range(10)]
    text = "Some analysis prose.\n" + "\n".join(lines)
    assert _parse_self_reported_scores(text) == [0.5] * 10


def test_parse_scores_keyed_state_noetic_register():
    """CAS v7.5: Noetic-level register `^n|R` on keyed state lines is accepted."""
    lines = [f"^{i}|T^C_{{F2}}: 0.6" for i in range(10)]
    text = "\n".join(lines)
    assert _parse_self_reported_scores(text) == [0.6] * 10


def test_parse_scores_keyed_state_drive_register():
    """CAS v7.5: Drive-level register `_{F_k|R}` on keyed state lines is accepted."""
    lines = [f"^{i}^C_{{F2|A}}: 0.7" for i in range(10)]
    text = "\n".join(lines)
    assert _parse_self_reported_scores(text) == [0.7] * 10


def test_parse_scores_keyed_state_compound_register():
    """CAS v7.5: compound-level register `^n^D_{F_k}|R` on keyed state lines is accepted."""
    lines = [f"^{i}^E_{{F3}}|f: 0.4" for i in range(10)]
    text = "\n".join(lines)
    assert _parse_self_reported_scores(text) == [0.4] * 10


def test_parse_scores_keyed_state_independent_registers():
    """CAS v7.5: independent Noetic and Drive registers `^n|R_n^D_{F_k|R_d}`."""
    lines = [f"^{i}|T^C_{{F2|A}}: 0.55" for i in range(10)]
    text = "\n".join(lines)
    assert _parse_self_reported_scores(text) == [0.55] * 10


def test_parse_scores_keyed_state_uppercase_F_rejected():
    """Keyed state format must also reject uppercase `F` on any register slot."""
    lines = [f"^{i}^C_{{F2}}|F: 0.5" for i in range(10)]
    text = "\n".join(lines)
    with pytest.raises(ValueError, match="invalid register 'F'"):
        _parse_self_reported_scores(text)


def test_parse_scores_keyed_state_requires_all_ten_operators():
    """Keyed format needs one line per CO-0..CO-9 to yield a valid 10-vector."""
    # Only 5 operators covered → fallback (None).
    lines = [f"^{i}^C_{{F2}}: 0.5" for i in range(5)]
    text = "\n".join(lines)
    assert _parse_self_reported_scores(text) is None


def test_parse_scores_keyed_state_value_register_accepted():
    """Register may appear on the numeric value even in keyed format: `: 0.73|A`."""
    lines = [f"^{i}^C_{{F2}}: 0.73|A" for i in range(10)]
    text = "\n".join(lines)
    assert _parse_self_reported_scores(text) == [0.73] * 10


def test_parse_scores_invalid_register_on_keyed_noetic_rejected():
    """Invalid register letter `Q` at the Noetic position is rejected cleanly."""
    lines = [f"^{i}|Q^C_{{F2}}: 0.5" for i in range(10)]
    text = "\n".join(lines)
    with pytest.raises(ValueError, match="invalid register 'Q'"):
        _parse_self_reported_scores(text)


# ---------------------------------------------------------------------------
# CAS v7.5 Register data flow (Clarification 8, rollout track (j))
# — per-score register metadata propagation from parser through scoring.
# ---------------------------------------------------------------------------


def test_parse_scores_with_registers_v74_plain_list_returns_all_none():
    """v7.4 register-neutral numeric list: scores populated, all registers None."""
    text = _ten_scores_line(
        ["0.72", "0.81", "0.64", "0.55", "0.70", "0.68", "0.77", "0.60", "0.58", "0.66"]
    )
    parsed = _parse_self_reported_scores_with_registers(text)
    assert parsed is not None
    scores, registers = parsed
    assert scores == [0.72, 0.81, 0.64, 0.55, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66]
    assert registers == [None] * 10


def test_parse_scores_with_registers_v75_all_four_registers():
    """v7.5 list with the four canonical registers: parallel list returned."""
    text = _ten_scores_line(
        ["0.72|T", "0.81|A", "0.64|f", "0.55|E", "0.70", "0.68", "0.77", "0.60", "0.58", "0.66"]
    )
    parsed = _parse_self_reported_scores_with_registers(text)
    assert parsed is not None
    scores, registers = parsed
    assert scores == [0.72, 0.81, 0.64, 0.55, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66]
    assert registers == ["T", "A", "f", "E", None, None, None, None, None, None]


def test_parse_scores_with_registers_mixed_registers_and_plain():
    """Mixed list: only the annotated positions carry registers; rest None."""
    text = _ten_scores_line(
        ["0.5|A", "0.5", "0.5|f", "0.5", "0.5|E", "0.5", "0.5|T", "0.5", "0.5", "0.5"]
    )
    parsed = _parse_self_reported_scores_with_registers(text)
    assert parsed is not None
    _scores, registers = parsed
    assert registers == ["A", None, "f", None, "E", None, "T", None, None, None]


def test_parse_scores_with_registers_keyed_state_noetic_register():
    """Keyed state format: Noetic-level register `^n|R` flows to the parallel list."""
    lines = [f"^{i}|A^C_{{F2}}: 0.6" for i in range(10)]
    text = "\n".join(lines)
    parsed = _parse_self_reported_scores_with_registers(text)
    assert parsed is not None
    _scores, registers = parsed
    assert registers == ["A"] * 10


def test_parse_scores_with_registers_keyed_state_value_register_wins():
    """Keyed state precedence: value-level register beats Noetic-level register."""
    lines = [f"^{i}|T^C_{{F2}}: 0.6|A" for i in range(10)]
    text = "\n".join(lines)
    parsed = _parse_self_reported_scores_with_registers(text)
    assert parsed is not None
    _scores, registers = parsed
    # Value register is the most specific; wins over Noetic register.
    assert registers == ["A"] * 10


def test_parse_scores_with_registers_malformed_still_returns_none():
    """Parser-failure convention preserved: malformed token → None."""
    text = _ten_scores_line(["0.5|TT"] + ["0.5"] * 9)
    assert _parse_self_reported_scores_with_registers(text) is None


def test_parse_scores_with_registers_invalid_letter_raises():
    """Invalid register letter rejected with the same error as legacy parser."""
    text = _ten_scores_line(["0.5|Q"] + ["0.5"] * 9)
    with pytest.raises(ValueError, match="invalid register 'Q'"):
        _parse_self_reported_scores_with_registers(text)


# ---------------------------------------------------------------------------
# operator_scoring stage — register propagation via OperatorScoreResult
# ---------------------------------------------------------------------------


class _StubConnector(BaseLLMConnector):
    """Minimal connector for driving `operator_scoring` deterministically."""

    provider_name = "stub"
    max_retries = 1

    async def _generate(
        self, prompt: str, system_prompt: str = "", **kwargs: object
    ) -> LLMResponse:  # pragma: no cover - unused in this test
        raise NotImplementedError


@pytest.mark.asyncio
async def test_operator_scoring_self_reported_register_neutral_preserves_v74_shape():
    """Register-neutral self-reported scores produce v7.4-shape result (score_registers=None)."""
    llm_resp = LLMResponse(
        text="Operator Scores: [0.72, 0.81, 0.64, 0.55, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66]",
        model="test",
        usage={},
    )
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    assert result.scoring_method == "self_reported"
    assert result.score_registers is None


@pytest.mark.asyncio
async def test_operator_scoring_self_reported_carries_registers_through():
    """Register-annotated self-reported scores surface on OperatorScoreResult."""
    llm_resp = LLMResponse(
        text="Operator Scores: [0.72|T, 0.81|A, 0.64|f, 0.55|E, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66]",
        model="test",
        usage={},
    )
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    assert result.scoring_method == "self_reported"
    assert result.score_registers == [
        "T", "A", "f", "E", None, None, None, None, None, None,
    ]


@pytest.mark.asyncio
async def test_operator_scoring_heuristic_fallback_no_registers():
    """Heuristic fallback pathway never emits register metadata."""
    llm_resp = LLMResponse(text="Totally unrelated prose.", model="test", usage={})
    result = await operator_scoring(llm_resp, scoring_mode="heuristic_fallback")
    assert result.scoring_method == "heuristic_fallback"
    assert result.score_registers is None


def test_operator_score_result_rejects_invalid_register_letter():
    """Defense-in-depth: OperatorScoreResult validates register letters."""
    from api.pipeline.stages import OperatorScoreResult
    with pytest.raises(ValueError, match="not a valid CAS v7.5"):
        OperatorScoreResult(
            scores=[0.5] * 10,
            raw_scores_0_to_10=[5.0] * 10,
            profile_score=0.5,
            involution_balances=[0.0, 0.0, 0.0],
            score_registers=["T", "A", "f", "E", None, None, None, "Q", None, None],
        )


def test_operator_score_result_rejects_wrong_length_register_list():
    """Length mismatch between scores and score_registers is caught early."""
    from api.pipeline.stages import OperatorScoreResult
    with pytest.raises(ValueError, match="length must match"):
        OperatorScoreResult(
            scores=[0.5] * 10,
            raw_scores_0_to_10=[5.0] * 10,
            profile_score=0.5,
            involution_balances=[0.0, 0.0, 0.0],
            score_registers=["T", "A", "f"],
        )


# ---------------------------------------------------------------------------
# CAS v7.7 — Register-set notation `|⟨…⟩` and named emergent result support
# (Clarification 10 Sections 2, 3). Additive API — v7.5 functions remain
# unchanged, so v7.4/v7.5 parser tests above continue to cover backward
# compatibility on their own pathway.
# ---------------------------------------------------------------------------


def test_parse_v7_7_register_set_basic_accepted():
    """CAS v7.7 Clarification 10 Section 2A: basic `|⟨A,f,T⟩` register-set."""
    text = _ten_scores_line(
        ["0.73|⟨A,f,T⟩"] + ["0.5"] * 9
    )
    parsed = _parse_self_reported_scores_v7_7(text)
    assert parsed is not None
    scores, registers = parsed
    assert scores[0] == 0.73
    assert registers[0] == ["A", "f", "T"]
    # Remaining slots are register-neutral.
    assert registers[1:] == [None] * 9


def test_parse_v7_7_register_set_preserves_lowercase_f():
    """Lowercase `f` is authoritative (Clarification 8); preserved inside the set."""
    text = _ten_scores_line(
        ["0.5|⟨A,f,T,E⟩"] + ["0.5"] * 9
    )
    parsed = _parse_self_reported_scores_v7_7(text)
    assert parsed is not None
    _scores, registers = parsed
    # All four canonical registers present, `f` preserved in lowercase,
    # insertion order preserved.
    assert registers[0] == ["A", "f", "T", "E"]


def test_parse_v7_7_register_set_rejects_invalid_register():
    """Clarification 10 Section 3: register-set entries must be in VALID_REGISTERS."""
    text = _ten_scores_line(
        ["0.5|⟨A,Q,T⟩"] + ["0.5"] * 9
    )
    with pytest.raises(ValueError, match="invalid register 'Q' inside register-set"):
        _parse_self_reported_scores_v7_7(text)


def test_parse_v7_7_register_set_rejects_duplicate_register():
    """Clarification 10: register-sets are occupancy specifications; duplicates ill-formed."""
    text = _ten_scores_line(
        ["0.5|⟨A,A,T⟩"] + ["0.5"] * 9
    )
    with pytest.raises(ValueError, match="duplicate register 'A' in register-set"):
        _parse_self_reported_scores_v7_7(text)


def test_parse_v7_7_register_set_rejects_empty_set():
    """Clarification 10 Section 3: `|⟨⟩` must specify at least one register."""
    text = _ten_scores_line(
        ["0.5|⟨⟩"] + ["0.5"] * 9
    )
    with pytest.raises(ValueError, match="is empty"):
        _parse_self_reported_scores_v7_7(text)


def test_parse_v7_7_register_set_score_line_roundtrip():
    """Task-spec acceptance: `^3^P|⟨A,f,T⟩: 0.73` parses to score=0.73 reg=[A,f,T]."""
    # Author the full 10-operator keyed state set with the register-set form
    # at every position; this is the multi-line context the parser operates on.
    lines = [f"^{i}^P|⟨A,f,T⟩: 0.73" for i in range(10)]
    text = "\n".join(lines)
    parsed = _parse_self_reported_scores_v7_7(text)
    assert parsed is not None
    scores, registers = parsed
    assert scores == [0.73] * 10
    assert registers == [["A", "f", "T"]] * 10


def test_parse_v7_7_named_emergent_omega_preserved():
    """Task-spec acceptance: `(×-chain) = ^3^P|Ω: 0.85` preserves `Ω`."""
    # The parser accepts the full Clarification 10 Section 2C form on a line.
    # LHS `×`-chain definition is the compiler's concern (Agent 12 Rule 4),
    # not the parser's — the parser just carries the emergent name forward.
    lines = [
        f"(^{i}^P|A × ^{i}^P|f × ^{i}^P|T) = ^{i}^P|Ω: 0.85"
        for i in range(10)
    ]
    text = "\n".join(lines)
    parsed = _parse_self_reported_scores_v7_7(text)
    assert parsed is not None
    scores, registers = parsed
    assert scores == [0.85] * 10
    # Named emergent register preserved verbatim; outside VALID_REGISTERS
    # so downstream rendering distinguishes it from single-register v7.5.
    assert registers == ["Ω"] * 10


def test_parse_v7_7_named_emergent_multi_character_preserved():
    """Clarification 10 Section 8: `|TF` (multi-char identifier) preserved."""
    # Example from Clarification 10 Section 8: `(^2^P|T × ^2^P|f) = ^2^P|TF`.
    lines = [f"^{i}^P|TF: 0.62" for i in range(10)]
    text = "\n".join(lines)
    parsed = _parse_self_reported_scores_v7_7(text)
    assert parsed is not None
    scores, registers = parsed
    assert scores == [0.62] * 10
    assert registers == ["TF"] * 10


def test_parse_v7_7_backward_compat_v75_single_register():
    """Backward compatibility: CAS v7.5 single-register `|A` still parses."""
    text = _ten_scores_line(
        ["0.5|A"] + ["0.5"] * 9
    )
    parsed = _parse_self_reported_scores_v7_7(text)
    assert parsed is not None
    scores, registers = parsed
    assert scores == [0.5] * 10
    # Single-letter VALID_REGISTERS entry returned as `str` — matches the
    # v7.5 shape. Downstream can distinguish v7.5 (str in VALID_REGISTERS)
    # from v7.7 named-emergent (str outside VALID_REGISTERS) by membership
    # test.
    assert registers[0] == "A"
    assert registers[1:] == [None] * 9


def test_parse_v7_7_backward_compat_v74_register_neutral():
    """Backward compatibility: CAS v7.4 register-neutral plain list still parses."""
    text = _ten_scores_line(
        ["0.72", "0.81", "0.64", "0.55", "0.70", "0.68", "0.77", "0.60", "0.58", "0.66"]
    )
    parsed = _parse_self_reported_scores_v7_7(text)
    assert parsed is not None
    scores, registers = parsed
    assert scores == [0.72, 0.81, 0.64, 0.55, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66]
    assert registers == [None] * 10


# --- Additional coverage: v7.7 extensions on compound notation ---


def test_parse_v7_7_register_set_with_drive_subscript():
    """Register-set combines with drive subscript: `^3^P_{F2}|⟨A,T⟩: 0.4`."""
    lines = [f"^{i}^P_{{F2}}|⟨A,T⟩: 0.4" for i in range(10)]
    text = "\n".join(lines)
    parsed = _parse_self_reported_scores_v7_7(text)
    assert parsed is not None
    scores, registers = parsed
    assert scores == [0.4] * 10
    assert registers == [["A", "T"]] * 10


def test_parse_v7_7_distinguishes_v75_single_from_v77_emergent():
    """Membership in VALID_REGISTERS distinguishes v7.5 single from v7.7 emergent."""
    from api.notation.compiler import VALID_REGISTERS
    # Line 0 uses single-register `|A` (v7.5, in VALID_REGISTERS).
    # Line 1 uses named emergent `|Ω` (v7.7, outside VALID_REGISTERS).
    # Mixed emission is a legal author pattern during v7.5→v7.7 migration.
    lines = (
        ["^0^P|A: 0.5", "^1^P|Ω: 0.5"]
        + [f"^{i}^P_{{F2}}: 0.5" for i in range(2, 10)]
    )
    text = "\n".join(lines)
    parsed = _parse_self_reported_scores_v7_7(text)
    assert parsed is not None
    _scores, registers = parsed
    assert registers[0] == "A"
    assert registers[0] in VALID_REGISTERS
    assert registers[1] == "Ω"
    assert registers[1] not in VALID_REGISTERS


# ---------------------------------------------------------------------------
# CAS v7.7 — operator_scoring stage dispatch integration tests
# (Clarification 10). Verifies the production scoring pipeline routes each
# LLM output shape to the correct parser version and preserves v7.7 register
# metadata end-to-end through to OperatorScoreResult.score_registers.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_operator_scoring_routes_v7_7_register_set_preserves_list():
    """Clarification 10 Section 2A: `|⟨T,A,f⟩` routes to v7.7 parser."""
    # Author a 10-score list with a register-set on position 0; remaining
    # scores are register-neutral.
    inner = "0.73|⟨T,A,f⟩, " + ", ".join(["0.5"] * 9)
    llm_resp = LLMResponse(
        text="Operator Scores: [" + inner + "]",
        model="test",
        usage={},
    )
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    assert result.scoring_method == "self_reported"
    assert result.fallback_reason is None
    assert result.score_registers is not None
    # Register-set preserved as list[str]; insertion order preserved.
    assert result.score_registers[0] == ["T", "A", "f"]
    # Remaining positions unannotated → None.
    assert result.score_registers[1:] == [None] * 9
    assert result.scores[0] == 0.73


@pytest.mark.asyncio
async def test_operator_scoring_routes_v7_7_named_emergent_preserves_name():
    """Clarification 10 Section 2C: `(^3^P|A × ^3^P|f) = ^3^P|Ω` preserves Ω."""
    # Use the fully-formed cross-register integration line with an emergent
    # result; per Section 2C the assignment licenses the v7.7 parser.
    lines = [
        f"(^{i}^P|A × ^{i}^P|f × ^{i}^P|T) = ^{i}^P|Ω: 0.85"
        for i in range(10)
    ]
    llm_resp = LLMResponse(text="\n".join(lines), model="test", usage={})
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    assert result.scoring_method == "self_reported"
    assert result.fallback_reason is None
    # Named emergent register preserved verbatim as str outside
    # VALID_REGISTERS — downstream distinguishes it by membership test.
    assert result.score_registers == ["Ω"] * 10
    assert result.scores == [0.85] * 10


@pytest.mark.asyncio
async def test_operator_scoring_routes_single_register_to_v7_5_path():
    """Single-register `|A` does NOT trigger v7.7 parser — v7.5 suffices."""
    # No `|⟨` and no `= ^`; routing picks v7.5. Verify by confirming the
    # register entry is a single-character str (v7.5 shape) not a list
    # or named-emergent form.
    llm_resp = LLMResponse(
        text="Operator Scores: [0.72|A, 0.81, 0.64, 0.55, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66]",
        model="test",
        usage={},
    )
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    assert result.scoring_method == "self_reported"
    assert result.score_registers is not None
    assert result.score_registers[0] == "A"
    # v7.5 shape: str (not list). Not a register-set.
    assert isinstance(result.score_registers[0], str)
    assert result.score_registers[1:] == [None] * 9


@pytest.mark.asyncio
async def test_operator_scoring_register_neutral_routes_to_v7_4_path():
    """No `|` annotations anywhere → register-neutral; score_registers is None."""
    llm_resp = LLMResponse(
        text="Operator Scores: [0.72, 0.81, 0.64, 0.55, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66]",
        model="test",
        usage={},
    )
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    assert result.scoring_method == "self_reported"
    # v7.4 shape preserved: all-None register list collapses to None so
    # downstream serialization omits the field entirely.
    assert result.score_registers is None


@pytest.mark.asyncio
async def test_operator_scoring_mixed_notation_within_single_output():
    """Mixed v7.7 register-set + v7.5 single-register + v7.4 plain in one list.

    Dispatch picks v7.7 because `|⟨` appears anywhere; the v7.7 parser is a
    strict superset of v7.5 and accepts the per-token mixture, preserving
    each row's notation verbatim.
    """
    inner = "0.73|⟨A,f,T⟩, 0.81|A, 0.64, 0.55|E, 0.70, 0.68|f, 0.77, 0.60, 0.58, 0.66"
    llm_resp = LLMResponse(
        text="Operator Scores: [" + inner + "]",
        model="test",
        usage={},
    )
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    assert result.scoring_method == "self_reported"
    assert result.fallback_reason is None
    assert result.score_registers is not None
    assert result.score_registers[0] == ["A", "f", "T"]  # v7.7 register-set
    assert result.score_registers[1] == "A"               # v7.5 single
    assert result.score_registers[2] is None              # v7.4 neutral
    assert result.score_registers[3] == "E"               # v7.5 single
    assert result.score_registers[5] == "f"               # v7.5 single


@pytest.mark.asyncio
async def test_operator_scoring_malformed_v7_7_input_falls_back_with_reason():
    """v7.7 parser rejects malformed input → stage surfaces clear fallback_reason."""
    # `|⟨` signal present but `|⟨⟩` is an empty register-set — rejected by
    # the parser per Clarification 10. However the parser raises rather
    # than returning None for empty sets; verify the raised ValueError
    # propagates out of the stage. (Invalid-register-letter inside the set
    # likewise raises.) Separately, an *unclosed* `|⟨A,f` returns None and
    # triggers the heuristic fallback with the framework-aware message.
    llm_resp = LLMResponse(
        text="Operator Scores: [0.5|⟨A,f, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]",
        model="test",
        usage={},
    )
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    # The v7.7 parser returns None on unclosed `⟨…`; the stage falls back.
    assert result.scoring_method == "heuristic_fallback"
    assert result.fallback_reason is not None
    # Error message mentions Clarification 10 / register-set per contract.
    assert "Clarification 10" in result.fallback_reason
    assert "register-set" in result.fallback_reason


@pytest.mark.asyncio
async def test_operator_scoring_backward_compat_v7_5_register_annotated():
    """Existing v7.5 register-annotated flow is unchanged by v7.7 dispatch."""
    # Replicates the pre-existing test at line ~573 exactly; verifies the
    # dispatch adds no observable behavior change on v7.5 input.
    llm_resp = LLMResponse(
        text="Operator Scores: [0.72|T, 0.81|A, 0.64|f, 0.55|E, 0.70, 0.68, 0.77, 0.60, 0.58, 0.66]",
        model="test",
        usage={},
    )
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    assert result.scoring_method == "self_reported"
    assert result.score_registers == [
        "T", "A", "f", "E", None, None, None, None, None, None,
    ]


@pytest.mark.asyncio
async def test_operator_scoring_v7_7_registers_flow_to_operator_score_result():
    """End-to-end: v7.7 register-set reaches OperatorScoreResult.score_registers."""
    # Covers the aggregate-level contract: the OperatorScoreResult dataclass
    # accepts the widened entry types (list[str], str-named-emergent) and
    # its __post_init__ validation passes.
    lines = [f"^{i}^P|⟨A,f,T⟩: 0.4" for i in range(10)]
    llm_resp = LLMResponse(text="\n".join(lines), model="test", usage={})
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    # Schema preserved: the dataclass validator ran __post_init__ without
    # raising, so the register-set list entries are recognized as valid.
    assert result.score_registers is not None
    assert all(entry == ["A", "f", "T"] for entry in result.score_registers)
    # Downstream profile_score and involution_balances computed as normal
    # against the 10 numeric scores — v7.7 notation does not disrupt the
    # numeric aggregation path.
    assert len(result.involution_balances) == 3
    assert 0 <= result.profile_score <= 1


@pytest.mark.asyncio
async def test_operator_scoring_v7_7_with_whitespace_variations():
    """Edge case: whitespace around register-set and named-emergent tokens."""
    # Clarification 10 examples use `(chain) = ^n^D|Ω: v` with optional
    # whitespace around `=`. Confirm the dispatch detector tolerates
    # author-level whitespace variations without falling back.
    lines = [
        f"(^{i}^P|A × ^{i}^P|f)   =   ^{i}^P|Ψ: 0.6"
        for i in range(10)
    ]
    llm_resp = LLMResponse(text="\n".join(lines), model="test", usage={})
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    assert result.scoring_method == "self_reported"
    assert result.fallback_reason is None
    assert result.score_registers == ["Ψ"] * 10


@pytest.mark.asyncio
async def test_operator_scoring_v7_7_multiple_register_sets_one_output():
    """Edge case: multiple `|⟨…⟩` annotations across different positions."""
    inner = "0.4|⟨A,T⟩, 0.5|⟨f,E⟩, 0.6|⟨T,A,f,E⟩, 0.7, 0.8, 0.5, 0.5, 0.5, 0.5, 0.5"
    llm_resp = LLMResponse(
        text="Operator Scores: [" + inner + "]",
        model="test",
        usage={},
    )
    result = await operator_scoring(llm_resp, scoring_mode="self_reported")
    assert result.scoring_method == "self_reported"
    assert result.fallback_reason is None
    assert result.score_registers is not None
    assert result.score_registers[0] == ["A", "T"]
    assert result.score_registers[1] == ["f", "E"]
    assert result.score_registers[2] == ["T", "A", "f", "E"]
    assert result.score_registers[3:] == [None] * 7


@pytest.mark.asyncio
async def test_operator_scoring_v7_7_dispatch_does_not_affect_heuristic_fallback():
    """v7.7 dispatch is scoped to `self_reported` mode only — not heuristic."""
    # Text contains v7.7 notation but mode is heuristic_fallback; dispatch
    # must NOT run and result must be register-neutral.
    lines = [f"^{i}^P|⟨A,f,T⟩: 0.4" for i in range(10)]
    llm_resp = LLMResponse(text="\n".join(lines), model="test", usage={})
    result = await operator_scoring(llm_resp, scoring_mode="heuristic_fallback")
    assert result.scoring_method == "heuristic_fallback"
    assert result.score_registers is None
