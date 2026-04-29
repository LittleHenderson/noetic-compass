"""Tests for Level 3 conversational SDG validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from cas_synthetic.scripts.validate_level3_conversations import main as cli_main
from cas_synthetic.generator.conversational import Level3ConversationalGenerator
from cas_synthetic.validation.level3_conversation_validator import (
    Level3ConversationValidator,
)
from cas_synthetic.validation.level3_review_gate import (
    Level3ReviewThresholds,
    review_records,
    write_review_markdown,
)


@dataclass
class FakeArtifact:
    valid: bool
    error: str | None = None


def _valid_record(**overrides):
    record = {
        "id": "lvl3-001",
        "source_level2_id": "lvl2-001",
        "bucket": "sdg_dialogue",
        "cas_expression": "^2^P",
        "user_prompt": "How should I reason about this pattern?",
        "natural_language_mapping": "Maps the prompt to a principled CAS state.",
        "assistant_response": "This suggests a reflective framing, not a certainty.",
        "follow_up_question": "What evidence would change your confidence?",
        "soft_operator_targets": [0.1] * 10,
        "soft_domain_targets": {"P": 0.6, "C": 0.4},
        "tags": ["conversation", "sdg"],
        "provenance": {"source": "inline-test"},
    }
    record.update(overrides)
    return record


def _fixture_path(name: str) -> Path:
    return Path(__file__).with_name(name)


def _level2_source(**overrides):
    record = {
        "prompt": "A person wants clarity before taking action.",
        "response": "The source expression marks a principled cognitive state.",
        "cas_expression": "^2^P_{F3}|A",
        "_meta": {
            "bucket": "v75_register",
            "is_valid": True,
            "violation_type": None,
            "distance_to_valid": 0.0,
        },
    }
    record.update(overrides)
    return record


def test_valid_inline_fixture_passes_and_compiles():
    calls: list[str] = []

    def compile_expression(expression: str):
        calls.append(expression)
        return FakeArtifact(valid=True)

    validator = Level3ConversationValidator(compile_expression=compile_expression)
    summary = validator.validate_records([_valid_record()])

    assert summary.ok
    assert summary.total == 1
    assert summary.valid == 1
    assert summary.compiler_checked == 1
    assert calls == ["^2^P"]


def test_generator_preserves_cas_expression_and_emits_schema_fields():
    generator = Level3ConversationalGenerator(seed=7, variants_per_source=2)
    source = _level2_source()

    records = [
        ex.to_dict()
        for ex in generator.iter_source_record(
            source,
            source_index=0,
            source_line=1,
            source_path="level2_fixture.jsonl",
        )
    ]

    assert len(records) == 2
    for record in records:
        assert record["cas_expression"] == source["cas_expression"]
        assert record["bucket"] == "v75_register"
        assert len(record["soft_operator_targets"]) == 10
        assert len(record["soft_domain_targets"]) == 4
        assert abs(sum(record["soft_operator_targets"]) - 1.0) <= 1e-6
        assert abs(sum(record["soft_domain_targets"]) - 1.0) <= 1e-6
        assert record["provenance"]["level3_spec_version"] == "0.1.0"
        assert record["provenance"]["generation_method"] == "deterministic_template"


def test_generator_is_deterministic_for_same_seed():
    source = _level2_source()
    kwargs = dict(source_index=3, source_line=4, source_path="level2_fixture.jsonl")

    first = [
        ex.to_dict()
        for ex in Level3ConversationalGenerator(seed=11, variants_per_source=3)
        .iter_source_record(source, **kwargs)
    ]
    second = [
        ex.to_dict()
        for ex in Level3ConversationalGenerator(seed=11, variants_per_source=3)
        .iter_source_record(source, **kwargs)
    ]

    assert first == second


def test_generator_can_emit_recoverable_translation_style():
    source = _level2_source(cas_expression="^2^P_{F3}|A")
    generator = Level3ConversationalGenerator(
        seed=3,
        variants_per_source=2,
        style_ids=["recoverable_translation"],
    )

    records = [
        ex.to_dict()
        for ex in generator.iter_source_record(
            source,
            source_index=0,
            source_line=1,
            source_path="level2_fixture.jsonl",
        )
    ]

    assert len(records) == 2
    for record in records:
        assert "Noetic ^2" in record["user_prompt"]
        assert "domain P" in record["user_prompt"]
        assert "drive F3" in record["user_prompt"]
        assert "register |A" in record["user_prompt"]
        assert record["cas_expression"] == "^2^P_{F3}|A"
        assert record["provenance"]["template_id"] == "recoverable_translation"


def test_generator_rejects_unknown_style_id():
    try:
        Level3ConversationalGenerator(style_ids=["does_not_exist"])
    except RuntimeError as exc:
        assert "does_not_exist" in str(exc)
    else:
        raise AssertionError("expected unknown style id to fail")


def test_generator_skips_invalid_level2_sources_by_default():
    path = _fixture_path("_level3_level2_sources.jsonl")
    valid_source = _level2_source(cas_expression="^2^P")
    invalid_source = _level2_source(
        cas_expression="^2^P|A * ^2^P|f",
        _meta={
            "bucket": "v77_rule_four",
            "is_valid": False,
            "violation_type": "rule_four_missing_emergent",
            "distance_to_valid": 1.0,
        },
    )

    try:
        path.write_text(
            json.dumps(valid_source) + "\n" + json.dumps(invalid_source) + "\n",
            encoding="utf-8",
        )
        generator = Level3ConversationalGenerator(seed=13, variants_per_source=2)
        records = [ex.to_dict() for ex in generator.iter_jsonl(path)]

        assert len(records) == 2
        assert {record["source_level2_id"] for record in records} == {"level2-000000"}
        assert all(record["cas_expression"] == "^2^P" for record in records)
    finally:
        if path.exists():
            path.unlink()


def test_jsonl_loader_flags_missing_required_field_and_bad_distribution():
    invalid = _valid_record(soft_domain_targets={"P": 0.8})
    invalid.pop("follow_up_question")
    path = _fixture_path("_level3_loader_fixture.jsonl")

    try:
        path.write_text(json.dumps(invalid) + "\n", encoding="utf-8")
        validator = Level3ConversationValidator(skip_compiler=True)
        summary = validator.validate_jsonl(path)

        assert not summary.ok
        assert summary.total == 1
        assert summary.invalid == 1
        assert summary.compiler_skipped == 1
        assert any("missing required fields" in error for error in summary.issues[0].errors)
        assert any("soft_domain_targets must sum" in error for error in summary.issues[0].errors)
    finally:
        if path.exists():
            path.unlink()


def test_assistant_response_rejects_overclaiming_keywords():
    validator = Level3ConversationValidator(skip_compiler=True)
    report = validator.validate_record(
        _valid_record(
            assistant_response="I diagnose this and guarantee what will happen next."
        )
    )

    assert not report.ok
    assert any("diagnose" in error for error in report.errors)
    assert any("guarantee" in error for error in report.errors)
    assert any("will happen" in error for error in report.errors)


def test_quoted_banned_keywords_are_allowed():
    validator = Level3ConversationValidator(skip_compiler=True)
    report = validator.validate_record(
        _valid_record(
            assistant_response=(
                "Avoid overclaiming phrases like 'diagnose', 'will happen', or 'guarantee'."
            )
        )
    )

    assert report.ok


def test_compiler_invalid_artifact_marks_record_invalid():
    validator = Level3ConversationValidator(
        compile_expression=lambda expression: FakeArtifact(
            valid=False,
            error=f"bad syntax in {expression}",
        )
    )

    report = validator.validate_record(_valid_record(cas_expression="bad-cas"))

    assert not report.ok
    assert any("failed compiler validation" in error for error in report.errors)


def test_cli_prints_counts_and_returns_nonzero(capsys):
    path = _fixture_path("_level3_cli_fixture.jsonl")

    try:
        path.write_text(
            json.dumps(
                _valid_record(
                    assistant_response="This will happen exactly as described."
                )
            )
            + "\n",
            encoding="utf-8",
        )

        exit_code = cli_main([str(path), "--skip-compiler"])
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "Total records:      1" in captured.out
        assert "Invalid records:    1" in captured.out
        assert "will happen" in captured.out
    finally:
        if path.exists():
            path.unlink()


def test_review_gate_passes_diverse_records_and_writes_markdown():
    records = []
    for index in range(12):
        records.append(
            _valid_record(
                id=f"lvl3-{index:03d}",
                bucket="v75_register" if index % 2 else "v77_omega",
                cas_expression=f"^{index % 10}^P",
                user_prompt=f"How should I read case {index} as a CAS conversation?",
                assistant_response=(
                    f"The expression ^{index % 10}^P preserves the target for "
                    f"case {index} and should be treated as a structured map."
                ),
            )
        )

    result = review_records(
        records,
        thresholds=Level3ReviewThresholds(
            min_prompt_unique_ratio=0.80,
            min_response_unique_ratio=0.80,
            min_bucket_prompt_unique_ratio=0.80,
        ),
    )
    report_path = _fixture_path("_level3_review_report.md")
    try:
        write_review_markdown(result, report_path)

        assert result.ok
        assert result.metrics["unique_user_prompts"] == 12
        assert report_path.read_text(encoding="utf-8").startswith(
            "# Level 3 Conversational Review"
        )
    finally:
        if report_path.exists():
            report_path.unlink()


def test_review_gate_fails_low_prompt_diversity():
    records = [
        _valid_record(
            id=f"lvl3-low-{index}",
            bucket="v77_rule_four",
            cas_expression=f"^{index % 10}^P",
            user_prompt="Explain this CAS expression.",
            assistant_response=(
                f"The expression ^{index % 10}^P is a structured map for "
                "the pattern, not a final judgment."
            ),
        )
        for index in range(20)
    ]

    result = review_records(
        records,
        thresholds=Level3ReviewThresholds(
            min_prompt_unique_ratio=0.50,
            min_bucket_prompt_unique_ratio=0.50,
        ),
    )

    assert not result.ok
    assert any("prompt uniqueness ratio" in failure for failure in result.failures)
