"""Phase 3 tests for cas_native.inference.rpm_retry.

Coverage:
  - prompt construction: hints derived from drift kinds, no hint
    when drifts have no actionable axes
  - gating: should_attempt_retry honors chain_parsed, drifts present,
    structure intact
  - comparison: retry_strictly_beats_original requires strictly fewer
    drifts AND preserved stage coverage AND edge match if applicable
"""
from __future__ import annotations

from cas_native.inference.rpm_repair import (
    RpmRepairLog,
    SemanticDrift,
)
from cas_native.inference.rpm_retry import (
    build_corrective_prompt,
    retry_strictly_beats_original,
    should_attempt_retry,
)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def test_corrective_prompt_includes_noetic_hint_when_noetic_drifts():
    drifts = [SemanticDrift(
        stage_var="stageD",
        expected_expr="^9^P_{F3}",
        rendered_clause="stageD name something that struck a chord...",
        expected_noetic=9,
        expected_domain="P",
        expected_drive=3,
        drift_kinds=["noetic_missing", "noetic_wrong"],
        notes=["expected ^9 missing", "found ^4 instead"],
    )]
    prompt, axes = build_corrective_prompt(
        source_cas="let stageA = ^0^P; let stageD = ^9^P_{F3}; stageA -> stageD",
        drifts=drifts,
    )
    assert "noetic" in axes
    assert "popped into mind" in prompt
    assert "Describe the following CAS expression" in prompt


def test_corrective_prompt_includes_drive_hint_when_drive_drifts():
    drifts = [SemanticDrift(
        stage_var="stageD",
        expected_expr="^9^P_{F3}",
        rendered_clause="...",
        expected_noetic=9, expected_domain="P", expected_drive=3,
        drift_kinds=["drive_missing", "drive_wrong"],
        notes=[],
    )]
    prompt, axes = build_corrective_prompt(
        source_cas="let stageD = ^9^P_{F3}; stageD -> stageE",
        drifts=drifts,
    )
    assert "drive" in axes
    assert "vitality and energy" in prompt


def test_corrective_prompt_includes_domain_hint_when_domain_drifts():
    drifts = [SemanticDrift(
        stage_var="stageD",
        expected_expr="^4^E",
        rendered_clause="...",
        expected_noetic=4, expected_domain="E", expected_drive=None,
        drift_kinds=["domain_missing"],
        notes=[],
    )]
    prompt, axes = build_corrective_prompt(
        source_cas="let stageD = ^4^E; stageD -> stageE",
        drifts=drifts,
    )
    assert "domain" in axes
    assert "evaluative" in prompt


def test_corrective_prompt_dedupes_repeated_axes():
    """If two stages drift on the same axis-value pair, only one
    hint line is emitted (compact prompt)."""
    drifts = [
        SemanticDrift(
            stage_var="stageW",
            expected_expr="^9^C_{F3}",
            rendered_clause="...",
            expected_noetic=9, expected_domain="C", expected_drive=3,
            drift_kinds=["noetic_missing"],
            notes=[],
        ),
        SemanticDrift(
            stage_var="stageP",
            expected_expr="^9^E_{F3}",
            rendered_clause="...",
            expected_noetic=9, expected_domain="E", expected_drive=3,
            drift_kinds=["noetic_missing"],
            notes=[],
        ),
    ]
    prompt, axes = build_corrective_prompt(
        source_cas="...",
        drifts=drifts,
    )
    # The ^9 noetic hint appears only ONCE despite two drifts on it.
    assert prompt.count("popped into mind") == 1


def test_corrective_prompt_no_hints_falls_back_to_default():
    """When drifts have no actionable axes (e.g., all expected_* are
    None), the prompt is the standard format and axes_used is empty.
    The retry caller should detect the empty axes and skip."""
    drifts = [SemanticDrift(
        stage_var="stageD", expected_expr="?", rendered_clause="...",
        expected_noetic=None, expected_domain=None, expected_drive=None,
        drift_kinds=["noetic_missing"],
        notes=[],
    )]
    prompt, axes = build_corrective_prompt(
        source_cas="let stageD = ^0^P; stageD -> stageE",
        drifts=drifts,
    )
    assert axes == []
    assert "vocabulary mappings" not in prompt


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

def test_should_attempt_retry_true_when_drifts_with_intact_structure():
    log = RpmRepairLog(
        chain_parsed=True,
        n_stages_expected=4,
        n_stages_found_post_repair=4,
        edge_present_in_source=True,
        edge_matched_post_repair=True,
        semantic_drifts=[
            SemanticDrift(
                stage_var="stageD", expected_expr="^9^P_{F3}",
                rendered_clause="...", expected_noetic=9,
                expected_domain="P", expected_drive=3,
                drift_kinds=["noetic_missing"], notes=[],
            )
        ],
    )
    ok, reason = should_attempt_retry(log)
    assert ok is True
    assert "drift-only" in reason


def test_should_attempt_retry_false_when_no_drifts():
    log = RpmRepairLog(
        chain_parsed=True, n_stages_expected=4,
        n_stages_found_post_repair=4,
        edge_present_in_source=True, edge_matched_post_repair=True,
    )
    ok, reason = should_attempt_retry(log)
    assert ok is False
    assert "no semantic drifts" in reason


def test_should_attempt_retry_false_when_chain_not_parsed():
    log = RpmRepairLog(chain_parsed=False)
    ok, reason = should_attempt_retry(log)
    assert ok is False


def test_should_attempt_retry_false_when_stages_missing():
    """If Phase 1 didn't recover all stage_vars, retry won't help."""
    log = RpmRepairLog(
        chain_parsed=True, n_stages_expected=4,
        n_stages_found_post_repair=3,
        edge_present_in_source=True, edge_matched_post_repair=True,
        semantic_drifts=[SemanticDrift(
            stage_var="stageD", expected_expr="^9^P_{F3}",
            rendered_clause="...", expected_noetic=9,
            expected_domain="P", expected_drive=3,
            drift_kinds=["noetic_missing"], notes=[],
        )],
    )
    ok, reason = should_attempt_retry(log)
    assert ok is False
    assert "stage coverage" in reason


def test_should_attempt_retry_false_when_edge_unmatched():
    """If the closing edge wasn't matched after Phase 1, the structural
    skeleton is broken; retry would compound the problem."""
    log = RpmRepairLog(
        chain_parsed=True, n_stages_expected=4,
        n_stages_found_post_repair=4,
        edge_present_in_source=True, edge_matched_post_repair=False,
        semantic_drifts=[SemanticDrift(
            stage_var="stageD", expected_expr="^9^P_{F3}",
            rendered_clause="...", expected_noetic=9,
            expected_domain="P", expected_drive=3,
            drift_kinds=["noetic_missing"], notes=[],
        )],
    )
    ok, reason = should_attempt_retry(log)
    assert ok is False
    assert "edge" in reason


# ---------------------------------------------------------------------------
# Comparison heuristic
# ---------------------------------------------------------------------------

def _log_with_n_drifts(
    n_drifts: int, n_stages: int = 4, edge_matched: bool = True,
) -> RpmRepairLog:
    return RpmRepairLog(
        chain_parsed=True, n_stages_expected=4,
        n_stages_found_post_repair=n_stages,
        edge_present_in_source=True, edge_matched_post_repair=edge_matched,
        semantic_drifts=[
            SemanticDrift(
                stage_var=f"s{i}", expected_expr="^0^P",
                rendered_clause="x",
                expected_noetic=0, expected_domain="P", expected_drive=None,
                drift_kinds=["noetic_missing"], notes=[],
            )
            for i in range(n_drifts)
        ],
    )


def test_retry_wins_when_strictly_fewer_drifts_and_structure_intact():
    orig = _log_with_n_drifts(3)
    retry = _log_with_n_drifts(1)
    better, reason = retry_strictly_beats_original(
        original_log=orig, retry_log=retry,
    )
    assert better is True
    assert "strictly better" in reason


def test_retry_loses_when_same_drift_count():
    orig = _log_with_n_drifts(2)
    retry = _log_with_n_drifts(2)
    better, reason = retry_strictly_beats_original(
        original_log=orig, retry_log=retry,
    )
    assert better is False
    assert "not strictly less" in reason


def test_retry_loses_when_more_drifts():
    orig = _log_with_n_drifts(1)
    retry = _log_with_n_drifts(3)
    better, _ = retry_strictly_beats_original(
        original_log=orig, retry_log=retry,
    )
    assert better is False


def test_retry_loses_when_stage_coverage_regressed():
    orig = _log_with_n_drifts(3, n_stages=4)
    retry = _log_with_n_drifts(0, n_stages=3)  # zero drifts but lost a stage
    better, reason = retry_strictly_beats_original(
        original_log=orig, retry_log=retry,
    )
    assert better is False
    assert "stage coverage" in reason


def test_retry_loses_when_edge_broken():
    orig = _log_with_n_drifts(3, edge_matched=True)
    retry = _log_with_n_drifts(0, edge_matched=False)
    better, reason = retry_strictly_beats_original(
        original_log=orig, retry_log=retry,
    )
    assert better is False
    assert "edge" in reason


# ---------------------------------------------------------------------------
# Log structure
# ---------------------------------------------------------------------------

def test_retry_log_to_dict_serializable():
    from cas_native.inference.rpm_retry import RpmRetryLog
    log = RpmRetryLog(
        attempted=True, used_retry=False,
        reason="retry not strictly better",
        n_drifts_original=3, n_drifts_retry=2,
        hint_axes=["noetic", "drive"],
        corrective_prompt="Describe...",
    )
    d = log.to_dict()
    for key in [
        "attempted", "used_retry", "reason",
        "n_drifts_original", "n_drifts_retry",
        "hint_axes", "corrective_prompt",
    ]:
        assert key in d
    import json
    json.dumps(d)
