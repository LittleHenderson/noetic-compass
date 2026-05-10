"""Phase 1 tests for cas_native.inference.rpm_repair.

Coverage targets per user directive 2026-05-10:
  - parser: single let / multiple lets / no-let-no-op / no-edge-graceful
  - identifier repair: exact / off-by-one digit / dropped prefix /
    multiple drifted stages
  - edge repair: rendered head/tail wrong / arrow vs phrase variants /
    edge already correct
  - no-op: non-RPM source (state literal, recipe, fractal,
    meta-logic, CRO) returns input unchanged with chain_parsed=False
"""
from __future__ import annotations

from cas_native.inference.rpm_repair import (
    FinalEdge,
    RpmChain,
    RpmRepairLog,
    StageBinding,
    StageSemantics,
    find_stage_clauses,
    parse_rpm_chain,
    parse_stage_semantics,
    repair_rpm_rendering,
    verify_rpm_semantics,
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def test_parse_single_let_with_edge():
    cas = "let stageA0_3_0234 = ^0^P; let stageW3_3_0234 = ^9^C_{F3}; stageA0_3_0234 -> stageW3_3_0234"
    chain = parse_rpm_chain(cas)
    assert chain is not None
    assert [s.var for s in chain.stages] == ["stageA0_3_0234", "stageW3_3_0234"]
    assert chain.edge == FinalEdge(head="stageA0_3_0234", tail="stageW3_3_0234")


def test_parse_multiple_lets_preserves_source_order():
    cas = (
        "let stageA0_2_0277 = ^0^P; "
        "let stageD2_2_0277 = ^5^P_{F2}; "
        "let stageW2_2_0277 = ^5^C_{F2}; "
        "let stageP2_2_0277 = ^5^E_{F2}; "
        "stageA0_2_0277 -> stageP2_2_0277"
    )
    chain = parse_rpm_chain(cas)
    assert chain is not None
    assert [s.var for s in chain.stages] == [
        "stageA0_2_0277", "stageD2_2_0277",
        "stageW2_2_0277", "stageP2_2_0277",
    ]
    assert chain.edge.head == "stageA0_2_0277"
    assert chain.edge.tail == "stageP2_2_0277"


def test_parse_unicode_arrow_edge():
    cas = "let stageA = ^0^P; let stageB = ^9^P_{F3}; stageA → stageB"
    chain = parse_rpm_chain(cas)
    assert chain is not None
    assert chain.edge == FinalEdge(head="stageA", tail="stageB")


def test_parse_no_let_returns_none():
    """Non-RPM shapes must return None — the structural gate Phase 1
    uses to no-op on state literals, recipes, fractals, meta-logic,
    CRO."""
    assert parse_rpm_chain("^0^P|A") is None
    assert parse_rpm_chain("^4^P + ^1^P") is None
    assert parse_rpm_chain("Θ(Ω_x) = 1*^7^O + 2*^6^C_{F3} → Ω_x") is None
    assert parse_rpm_chain("Φ<3:7:1>") is None
    assert parse_rpm_chain("PartitionOf(Noetics, NoeticCluster{^5})") is None
    assert parse_rpm_chain("(^4^C|A × ^4^C|E) = ^4^C|Ω_clarity") is None


def test_parse_lets_without_edge_returns_chain_with_none_edge():
    cas = "let stageA = ^0^P; let stageB = ^9^P_{F3};"
    chain = parse_rpm_chain(cas)
    assert chain is not None
    assert len(chain.stages) == 2
    assert chain.edge is None


# ---------------------------------------------------------------------------
# No-op contract
# ---------------------------------------------------------------------------

def test_repair_no_op_for_non_rpm_source():
    rendered = "Something that struck a chord in cognitive thinking."
    out, log = repair_rpm_rendering(
        source_cas="^4^C|A", rendered=rendered,
    )
    assert out == rendered
    assert log.chain_parsed is False
    assert log.n_repairs == 0


def test_repair_no_op_for_empty_rendered():
    chain_cas = "let stageA = ^0^P; let stageB = ^9^P_{F3}; stageA -> stageB"
    out, log = repair_rpm_rendering(source_cas=chain_cas, rendered="")
    assert out == ""
    assert log.chain_parsed is False  # empty short-circuits before parsing


# ---------------------------------------------------------------------------
# Identifier repair
# ---------------------------------------------------------------------------

def test_repair_exact_match_makes_no_changes():
    cas = "let stageA = ^0^P; let stageB = ^9^P_{F3}; stageA -> stageB"
    rendered = (
        "Let stageA name a foundational thought, let stageB name "
        "something that popped to mind. stageA leads to stageB."
    )
    out, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    assert out == rendered
    assert log.chain_parsed is True
    assert log.n_stages_expected == 2
    assert log.n_stages_found_pre_repair == 2
    assert log.n_stages_found_post_repair == 2
    assert log.edge_matched_pre_repair is True
    assert log.edge_matched_post_repair is True
    assert log.n_repairs == 0


def test_repair_off_by_one_digit_drift():
    """The audit's record-20 finding: model emitted A0_2_0272 instead
    of source A0_2_0277. Phase 1 must repair this."""
    cas = (
        "let stageA0_2_0277 = ^0^P; "
        "let stageD2_2_0277 = ^5^P_{F2}; "
        "stageA0_2_0277 -> stageD2_2_0277"
    )
    rendered = (
        "Let stageA0_2_0277 name a foundational thought, "
        "let stageD2_2_0272 name something. "
        "stageA0_2_0272 leads to stageD2_2_0272."
    )
    out, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    # All three drifted occurrences of *0272 should now be *0277.
    assert "0272" not in out
    assert out.count("stageA0_2_0277") >= 1
    assert out.count("stageD2_2_0277") >= 2
    assert log.n_repairs >= 2  # at least the drifted stage + the edge
    kinds = {r.kind for r in log.repairs}
    assert "stage_identifier" in kinds


def test_repair_missing_stage_prefix():
    """Audit's 'malformed stage suffixes' finding: model dropped the
    'stage' prefix, emitting bare 'A0_3_0234' instead of full
    'stageA0_3_0234'."""
    cas = "let stageA0_3_0234 = ^0^P; let stageW3_3_0234 = ^9^C_{F3}; stageA0_3_0234 -> stageW3_3_0234"
    rendered = (
        "Let A0_3_0234 name a foundational thought, "
        "let W3_3_0234 name cognitive thinking shaped by vitality."
    )
    out, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    assert "stageA0_3_0234" in out
    assert "stageW3_3_0234" in out
    kinds = [r.kind for r in log.repairs]
    assert "missing_stage_prefix" in kinds


def test_repair_multiple_drifted_stages():
    cas = (
        "let stageA0_2_0287 = ^0^P; "
        "let stageD2_2_0287 = ^2^P_{F2}; "
        "let stageW2_2_0287 = ^2^C_{F2}; "
        "stageA0_2_0287 -> stageW2_2_0287"
    )
    # Two different drifts: A0 has dropped suffix, D2 has wrong digit.
    rendered = (
        "Let stageA0_2_028 name a foundational thought, "
        "let stageD2_2_0282 name something drawn to wisdom, "
        "let stageW2_2_0287 name cognitive attention."
    )
    out, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    assert "stageA0_2_0287" in out
    assert "stageD2_2_0287" in out
    assert "stageW2_2_0287" in out
    # Pre-repair only stageW matched exactly; post-repair all three do.
    assert log.n_stages_found_pre_repair == 1
    assert log.n_stages_found_post_repair == 3


def test_repair_does_not_touch_genuinely_different_identifiers():
    """Sanity: a stage-shaped token that is too far from any source
    stage_var must NOT be rewritten — that would be over-reach."""
    cas = "let stageA0_3_0234 = ^0^P; let stageW3_3_0234 = ^9^C_{F3}; stageA0_3_0234 -> stageW3_3_0234"
    rendered = (
        "Let stageA0_3_0234 name a foundational thought, "
        "let stageQQ_99_9999 name something completely different."
    )
    out, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    # Genuinely different identifier preserved verbatim.
    assert "stageQQ_99_9999" in out
    # Source stage stayed intact.
    assert "stageA0_3_0234" in out


# ---------------------------------------------------------------------------
# Edge repair
# ---------------------------------------------------------------------------

def test_repair_wrong_edge_head_and_tail_phrasing():
    """Audit's 'wrong final edge' finding: target says
    `stageA0_2_0287 -> stageD2_2_0287`; generation said
    `stageD2_2_028 leads to stageW2_2_028`."""
    cas = (
        "let stageA0_2_0287 = ^0^P; "
        "let stageD2_2_0287 = ^2^P_{F2}; "
        "stageA0_2_0287 -> stageD2_2_0287"
    )
    rendered = (
        "Let stageA0_2_0287 name a foundational thought, "
        "let stageD2_2_0287 name something drawn to wisdom. "
        "stageW2_2_028 leads to stageP2_2_028."  # both wrong
    )
    out, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    # The edge phrase should now reference the source edge.
    assert "stageA0_2_0287 leads to stageD2_2_0287" in out
    assert log.edge_matched_pre_repair is False
    assert log.edge_matched_post_repair is True


def test_repair_preserves_connector_word():
    cas = "let stageA = ^0^P; let stageB = ^9^P_{F3}; stageA -> stageB"
    rendered = (
        "Let stageA name a foundational thought, "
        "let stageB name something. stageX flows into stageY."
    )
    out, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    assert "stageA flows into stageB" in out


def test_repair_unicode_arrow_in_rendered_text():
    cas = "let stageA = ^0^P; let stageB = ^9^P_{F3}; stageA -> stageB"
    rendered = "Let stageA name X, let stageB name Y. stageX → stageY."
    out, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    assert "stageA → stageB" in out


def test_repair_no_recognized_edge_phrase_logs_but_does_not_synthesize():
    """If the rendered text has no recognized edge phrase, Phase 1
    must NOT invent one — that would risk breaking the prose. The
    log records the absence."""
    cas = "let stageA = ^0^P; let stageB = ^9^P_{F3}; stageA -> stageB"
    rendered = "Let stageA name X, let stageB name Y. End."
    out, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    # No edge in rendered text, no edge synthesized.
    assert "leads to" not in out
    assert "flows into" not in out
    assert "->" not in out
    assert log.edge_matched_pre_repair is False
    assert log.edge_matched_post_repair is False


def test_repair_edge_already_correct_is_no_op_for_edge():
    cas = "let stageA = ^0^P; let stageB = ^9^P_{F3}; stageA -> stageB"
    rendered = "Let stageA name X, let stageB name Y. stageA leads to stageB."
    out, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    assert out == rendered
    assert log.edge_matched_pre_repair is True
    assert log.edge_matched_post_repair is True
    assert all(r.kind != "final_edge" for r in log.repairs)


# ---------------------------------------------------------------------------
# Log structure
# ---------------------------------------------------------------------------

def test_log_to_dict_round_trip_serializable():
    cas = (
        "let stageA0_2_0287 = ^0^P; "
        "let stageD2_2_0287 = ^2^P_{F2}; "
        "stageA0_2_0287 -> stageD2_2_0287"
    )
    rendered = (
        "Let stageA0_2_0287 name a foundational thought, "
        "let stageD2_2_0282 name something. "
        "stageW leads to stageP."
    )
    _, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    d = log.to_dict()
    # All expected keys present.
    for key in [
        "chain_parsed", "n_stages_expected",
        "n_stages_found_pre_repair", "n_stages_found_post_repair",
        "edge_present_in_source", "edge_matched_pre_repair",
        "edge_matched_post_repair", "n_repairs", "repairs",
        "n_semantic_drifts", "semantic_drifts",
    ]:
        assert key in d, key
    # JSON-serializable smoke (no exotic types).
    import json
    json.dumps(d)


# ---------------------------------------------------------------------------
# Phase 2 — semantic verifier (flag-only, never rewrites)
# ---------------------------------------------------------------------------

def test_parse_stage_semantics_basic():
    """Decompose source expressions across all four axes."""
    s = parse_stage_semantics("^0^P")
    assert s == StageSemantics(noetic=0, domain="P", drive=None, register=None)

    s = parse_stage_semantics("^9^P_{F3}")
    assert s == StageSemantics(noetic=9, domain="P", drive=3, register=None)

    s = parse_stage_semantics("^4^C|A")
    assert s == StageSemantics(noetic=4, domain="C", drive=None, register="A")

    s = parse_stage_semantics("^9^P_{F3}|T")
    assert s == StageSemantics(noetic=9, domain="P", drive=3, register="T")


def test_parse_stage_semantics_handles_optional_fields():
    """When axes are missing in source, parser returns None for those."""
    s = parse_stage_semantics("^7")
    assert s.noetic == 7
    assert s.domain is None
    assert s.drive is None
    assert s.register is None


def test_find_stage_clauses_segments_at_next_stage():
    """Each stage_var maps to text from its first occurrence to the
    next stage_var's first occurrence (or end of text)."""
    text = (
        "Let stageA0 name a foundational thought, "
        "let stageW name cognitive thinking shaped by wisdom, "
        "and stageA0 leads to stageW."
    )
    clauses = find_stage_clauses(text, ["stageA0", "stageW"])
    # stageA0 clause runs to the first occurrence of stageW.
    assert "foundational thought" in clauses["stageA0"]
    assert "cognitive thinking" not in clauses["stageA0"]
    # stageW clause runs to end of text and includes the closing edge.
    assert "cognitive thinking" in clauses["stageW"]


def test_find_stage_clauses_missing_stage_returns_empty_string():
    """Stages that don't appear in rendered text map to ''."""
    text = "Let stageA0 name a foundational thought."
    clauses = find_stage_clauses(text, ["stageA0", "stageMISSING"])
    assert "foundational thought" in clauses["stageA0"]
    assert clauses["stageMISSING"] == ""


def test_verify_returns_no_drift_when_clause_is_faithful():
    """A clause that hits all expected indicators produces no drift."""
    chain = RpmChain(
        stages=[
            StageBinding(var="stageA0", expr="^0^P"),
            StageBinding(var="stageD", expr="^9^P_{F3}"),
        ],
        edge=FinalEdge(head="stageA0", tail="stageD"),
    )
    rendered = (
        "Let stageA0 name a foundational thought, "
        "let stageD name something that popped into mind in the "
        "principled foundation driven by vitality and energy. "
        "stageA0 leads to stageD."
    )
    drifts = verify_rpm_semantics(rendered, chain)
    assert drifts == []


def test_verify_flags_noetic_wrong_when_struck_a_chord_replaces_popped():
    """The audit's record-19 finding: target ^9 wants
    'popped to mind' but model emitted 'struck a chord' (^4 indicator).
    Phase 2 must flag both noetic_missing AND noetic_wrong."""
    chain = RpmChain(
        stages=[
            StageBinding(var="stageA0_3_0234", expr="^0^P"),
            StageBinding(var="stageD3_3_0234", expr="^9^P_{F3}"),
        ],
        edge=FinalEdge(head="stageA0_3_0234", tail="stageD3_3_0234"),
    )
    rendered = (
        "Let stageA0_3_0234 name a foundational thought, "
        "let stageD3_3_0234 name something that struck a chord in the "
        "realm of wisdom and insight."
    )
    drifts = verify_rpm_semantics(rendered, chain)
    # stageA0 has clean ^0^P content; stageD has both noetic AND drive drift.
    drift_for_d = [d for d in drifts if d.stage_var == "stageD3_3_0234"]
    assert len(drift_for_d) == 1
    d = drift_for_d[0]
    assert "noetic_missing" in d.drift_kinds
    assert "noetic_wrong" in d.drift_kinds
    # Drive ^F3 expected (vitality), F2 (wisdom) found instead.
    assert "drive_missing" in d.drift_kinds
    assert "drive_wrong" in d.drift_kinds
    assert d.expected_noetic == 9
    assert d.expected_drive == 3


def test_verify_flags_domain_wrong():
    """When source says ^E but rendered clause uses 'cognitive'
    instead of 'evaluative', flag domain_wrong."""
    chain = RpmChain(
        stages=[StageBinding(var="stageA", expr="^4^E_{F1}")],
        edge=None,
    )
    rendered = (
        "Let stageA name something that struck a chord in the "
        "cognitive thinking arena driven by unity."
    )
    drifts = verify_rpm_semantics(rendered, chain)
    assert len(drifts) == 1
    d = drifts[0]
    assert "domain_missing" in d.drift_kinds
    assert "domain_wrong" in d.drift_kinds
    assert d.expected_domain == "E"


def test_verify_phase2_does_not_rewrite_final_text():
    """Phase 2 directive 2026-05-10: log only, never rewrite. Even
    when drifts are detected, ``final_text`` from repair_rpm_rendering
    must equal the post-Phase-1 text verbatim."""
    cas = "let stageA0 = ^0^P; let stageD = ^9^P_{F3}; stageA0 -> stageD"
    rendered = (
        "Let stageA0 name a foundational thought, "
        "let stageD name something that struck a chord in the realm "
        "of wisdom and insight. stageA0 leads to stageD."
    )
    out, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    # Drifts logged.
    assert len(log.semantic_drifts) >= 1
    # But final_text NOT rewritten — "struck a chord" still present,
    # "popped" still absent, "wisdom" still present, "vitality" still absent.
    assert "struck a chord" in out
    assert "wisdom" in out
    assert "popped" not in out
    assert "vitality" not in out


def test_verify_returns_empty_when_chain_has_no_stages():
    """Defensive: if for some reason the chain came back with empty
    stages, semantic verifier produces no drifts."""
    drifts = verify_rpm_semantics(
        "anything", RpmChain(stages=[], edge=None),
    )
    assert drifts == []


def test_to_dict_serializes_semantic_drifts_with_axis_fields():
    cas = "let stageA0 = ^0^P; let stageD = ^9^P_{F3}; stageA0 -> stageD"
    rendered = (
        "Let stageA0 name a foundational thought, "
        "let stageD name something that struck a chord in the realm "
        "of wisdom. stageA0 leads to stageD."
    )
    _, log = repair_rpm_rendering(source_cas=cas, rendered=rendered)
    d = log.to_dict()
    drifts = d["semantic_drifts"]
    assert len(drifts) >= 1
    sample = drifts[0]
    # All structured fields present + serializable.
    for key in [
        "stage_var", "expected_expr", "rendered_clause",
        "expected_noetic", "expected_domain", "expected_drive",
        "drift_kinds", "notes",
    ]:
        assert key in sample, key
    import json
    json.dumps(d)  # smoke


def test_chain_parsed_flag_true_for_rpm_false_otherwise():
    cas_rpm = "let stageA = ^0^P; let stageB = ^9^P_{F3}; stageA -> stageB"
    _, log_rpm = repair_rpm_rendering(
        source_cas=cas_rpm, rendered="Let stageA name X, stageA -> stageB.",
    )
    assert log_rpm.chain_parsed is True

    _, log_non = repair_rpm_rendering(
        source_cas="^4^P|A", rendered="something",
    )
    assert log_non.chain_parsed is False
