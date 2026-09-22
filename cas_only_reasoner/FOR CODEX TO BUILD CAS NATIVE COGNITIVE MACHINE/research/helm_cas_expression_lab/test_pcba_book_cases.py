"""Independent book-derived and adversarial tests for the structural PCBA checker.

Fixtures cite the local CAS_PCBA_Engineer manuscript, with SHA-256 over UTF-8
text normalized to LF. These tests do not claim that declarations execute or
that an unresolved book rule has been ratified.

Appendix_C_CCDL_Language_Reference.md:
452d64308f860b1c0e5b6c3f4d9c8a91760822baa9b9fcd1a6e12a4797983d8f
Chapter_04_Your_First_Cognitive_Circuit.md:
13ef9030ebf9189dbedc31c40332accbaaa1552a1681bb56ac9d354dc368329e
Chapter_17_CCB_Design_Process.md:
ab58f6ef9dcc7a49c262bc9bc41835ec450b344a26340b91ce2feef52cfa5d07
"""

import pytest

from pcba_check import check_pcba_document


# Chapter 4, lines 94-111: the printed listing omits comment-only lines here.
# Appendix C, line 753 requires bias at/above cause; this listing violates it.
FIRST_CIRCUIT = """
circuit first_circuit {
    input: prompt;
    output: response;
    node question: ^8^C_{F2}|A;
    node experience: ^5^E_{F4}|f;
    node answer: ^9^C_{F6}|A;
    resistor r1: Resistor< question, R=30 >;
    cjt c1: CJT< question | experience => answer > [β=2.4];
    probe tp1: answer;
}
"""

# Appendix C, lines 570-583: direct quotation, comments/spacing omitted.
# P->E is a published downward route. The .2 upward route is printed as legal;
# the general low-gain feedback admission policy still needs an owner decision.
BOOK_LAYOUT = """
board csb_v0 {
    layer P: [ bias_charter: ^5^P_{F7}|T, policy_aversion: ^3^P_{F7}|f ];
    layer C: [ understand: ^1^C_{F2}|A ];
    layer E: [ weigh: ^6^E_{F6}|A ];
    layer O: [ respond: ^9^O_{F5}|E ];
    via v1: ^5^P -> ^1^C;
    via v2: ^3^P -> ^6^E;
    via v3: ^6^E -> ^9^O;
    via v4: ^9^O -> ^5^P [β=0.2];
}
"""


def _check(source):
    report = check_pcba_document(source)
    assert isinstance(report, dict)
    assert report["schema"]
    assert report["parse_status"] in {"PASS", "FAIL", "UNSUPPORTED"}
    assert report["structural_status"] in {"PASS", "FAIL", "UNVERIFIED", "NOT_RUN"}
    assert isinstance(report["valid"], bool)
    assert report["execution_status"] == "NOT_IMPLEMENTED"
    assert report["helm_status"] == "NOT_TRAINED"
    assert isinstance(report["netlist"], dict)
    assert report["document"] is None or isinstance(report["document"], dict)
    for diagnostic in report["diagnostics"]:
        assert diagnostic["code"]
        assert diagnostic["message"]
        assert diagnostic["severity"] in {"error", "warning", "unverified"}
        assert isinstance(diagnostic["line"], int)
        assert isinstance(diagnostic["column"], int)
        assert diagnostic["line"] >= 1
        assert diagnostic["column"] >= 1
    if report["parse_status"] != "PASS":
        assert report["structural_status"] == "NOT_RUN"
        assert report["valid"] is False
    else:
        assert report["document"] is not None
    if report["structural_status"] in {"FAIL", "UNVERIFIED", "NOT_RUN"}:
        assert report["valid"] is False
    if report["valid"]:
        assert report["parse_status"] == report["structural_status"] == "PASS"
        assert not any(d["severity"] in {"error", "unverified"}
                       for d in report["diagnostics"])
    return report


def _errors(report):
    return [d for d in report["diagnostics"] if d["severity"] == "error"]


def _codes(report, severity=None):
    return {d["code"] for d in report["diagnostics"]
            if severity is None or d["severity"] == severity}


def _structural_error(source, code=None, words=()):
    report = _check(source)
    assert report["parse_status"] == "PASS", report
    assert report["structural_status"] == "FAIL", report
    assert _errors(report), report
    if code is not None:
        assert code in _codes(report, "error"), report
    if words:
        messages = " ".join(d["message"].lower() for d in _errors(report))
        assert any(word in messages for word in words), report
    return report


def _typed_board(body):
    # Same-domain typed nodes isolate graph/gain checks from cross-domain policy.
    # Equal literal values do not identify nets: Appendix C, line 232.
    return """
board gain_case {
    node a: ^1^C_{F2}|A;
    node b: ^2^C_{F2}|A;
    node c: ^3^C_{F2}|A;
    node bias: ^5^P_{F7}|T;
""" + body + "\n}"


def test_chapter4_reads_but_violates_bias_rule():
    _structural_error(FIRST_CIRCUIT, code="E-CJT-002")


def test_printed_layout_does_not_invent_adjacent_tier_requirement():
    report = _check(BOOK_LAYOUT)
    assert report["parse_status"] == "PASS", report
    assert not _errors(report), report
    assert report["structural_status"] in {"PASS", "UNVERIFIED"}, report


def test_downward_via_can_skip_a_layer():
    # Appendix C 578 is a P -> E route; no declaration of C is necessary.
    report = _check("""
board downward {
    layer P: [ guard: ^3^P_{F7}|f ];
    layer E: [ judge: ^6^E_{F6}|A ];
    via v2: ^3^P -> ^6^E;
}
""")
    assert report["parse_status"] == "PASS", report
    assert not _errors(report), report


def test_printed_unqualified_upward_via_is_invalid():
    # Chapter 17, lines 259-265 is an intentional faulty-layout exercise.
    _structural_error("""
board mini {
    layer P: [ guard: ^3^P_{F7}|f ];
    layer E: [ judge: ^6^E_{F6}|A ];
    layer O: [ act: ^9^O_{F5}|E ];
    via v1: ^6^E -> ^3^P;
    via v2: ^3^P -> ^9^O;
}
""", words=("upward", "feedback", "descent", "domain"))


def test_layer_declared_domain_must_match_its_state():
    # Appendix C, line 589.
    _structural_error(
        "board wrong_layer { layer P: [ guard: ^3^E_{F7}|f ]; }",
        words=("layer", "domain"),
    )


@pytest.mark.parametrize("second", [
    "layer C: [ repeated: ^2^C ];",
    "layer P: [ repeated: ^2^P ];",
    "node repeated: ^2^C;",
])
def test_duplicate_layer_entry_names_are_not_overwritten(second):
    _structural_error(
        "board duplicate { layer C: [ repeated: ^1^C ]; " + second + " }",
        words=("duplicate", "already", "redeclared"),
    )


def test_distinct_names_with_equal_literals_remain_distinct_nets():
    # Appendix C, line 232: naming a shared node creates actual connectivity.
    report = _check("""
board separate_nets {
    node a: ^1^C;
    node b: ^1^C;
    node c: ^1^C;
    node d: ^1^C;
    node bias: ^5^P;
    cjt forward: CJT< a | bias => b > [β=3];
    feedback disconnected: c -> d [β=0.5];
}
""")
    assert report["parse_status"] == "PASS", report
    assert "E-CJT-005" not in _codes(report, "error"), report


def test_forward_references_are_resolved_after_all_declarations():
    # Appendix C, line 20 explicitly permits order-independent declarations.
    report = _check("""
board forward_references {
    cjt stage: CJT< question | charter => answer > [β=0.2];
    probe observe: answer;
    node answer: ^9^C_{F6}|A;
    node question: ^8^C_{F2}|A;
    node charter: ^5^P_{F7}|T;
}
""")
    assert report["parse_status"] == "PASS", report
    assert not _errors(report), report


@pytest.mark.parametrize("body", [
    "cjt stage: CJT< missing | bias => b > [β=0.2];",
    "cjt stage: CJT< a | missing => b > [β=0.2];",
    "cjt stage: CJT< a | bias => missing > [β=0.2];",
    "feedback back: missing -> a [β=0.2];",
    "feedback back: a -> missing [β=0.2];",
    "probe observe: missing;",
    "series a -> missing;",
    "transition move_path: missing -> b;",
])
def test_undefined_references_are_not_dropped_from_the_graph(body):
    _structural_error(
        _typed_board(body), words=("missing", "undefined", "undeclared", "unknown")
    )


def test_declared_io_terminals_are_references_but_have_no_invented_domain():
    # Appendix C 207-210 allows terminal references but supplies no state type.
    report = _check("""
circuit ports {
    input: prompt;
    output: response;
    node charter: ^5^P_{F7}|T;
    cjt stage: CJT< prompt | charter => response > [β=0.2];
}
""")
    assert report["parse_status"] == "PASS", report
    assert not _errors(report), report
    assert report["structural_status"] == "UNVERIFIED", report


def test_unused_disconnected_io_is_legal_but_inert():
    # Appendix C 212 explicitly permits disconnected input/output terminals.
    report = _check("""
circuit inert_ports {
    input: prompt;
    output: response;
    node question: ^8^C_{F2}|A;
    node charter: ^5^P_{F7}|T;
    node answer: ^9^C_{F6}|A;
    cjt stage: CJT< question | charter => answer > [β=0.2];
}
""")
    assert report["parse_status"] == "PASS", report
    assert not _errors(report), report
    assert any(d["severity"] == "warning" for d in report["diagnostics"]), report


@pytest.mark.parametrize("declaration", ["input: ;", "output: ;"])
def test_empty_terminal_lists_are_not_accepted(declaration):
    report = _check("circuit ports { " + declaration + " }")
    assert report["parse_status"] != "PASS", report
    assert report["valid"] is False


def test_missing_io_does_not_make_a_pure_layout_board_invalid():
    # Appendix C, line 605 explicitly admits layers-only layout boards.
    report = _check("board layout { layer P: [ charter: ^5^P_{F7}|T ]; }")
    assert report["parse_status"] == "PASS", report
    assert not _errors(report), report


@pytest.mark.parametrize("statement", [
    "layer P: [ charter: ^5^P ];",
    "via route: ^5^P -> ^1^C;",
])
def test_circuit_does_not_admit_board_only_items(statement):
    # Appendix C 597: board is a superset of circuit, not the reverse.
    report = _check("circuit schematic { " + statement + " }")
    assert report["valid"] is False, report
    assert report["parse_status"] != "PASS" or _errors(report), report


@pytest.mark.parametrize("beta,feedback", [("2", "0.5"), ("3", "0.5"), ("1", "1")])
def test_known_cause_effect_cycle_product_at_least_one_is_rejected(beta, feedback):
    # Appendix C 528 and 757: beta is cause->effect and round-trip >=1 fails.
    _structural_error(_typed_board(
        "cjt stage: CJT< a | bias => b > [β=" + beta + "];"
        "feedback back: b -> a [β=" + feedback + "];"
    ), code="E-CJT-005")


def test_omitted_cjt_beta_uses_documented_unity_default():
    # Appendix C 528: beta default is 1.0, not unknown and not zero.
    _structural_error(_typed_board(
        "cjt stage: CJT< a | bias => b >;"
        "feedback back: b -> a [β=1];"
    ), code="E-CJT-005")


def test_subunit_known_cycle_does_not_raise_divergence():
    report = _check(_typed_board(
        "cjt stage: CJT< a | bias => b > [β=2];"
        "feedback back: b -> a [β=0.2];"
    ))
    assert report["parse_status"] == "PASS", report
    assert "E-CJT-005" not in _codes(report, "error"), report


def test_parallel_edges_do_not_hide_an_unstable_cycle():
    # Keeping only the first a->b edge incorrectly sees .2*.5 instead of 3*.5.
    _structural_error(_typed_board(
        "cjt quiet: CJT< a | bias => b > [β=0.2];"
        "cjt loud: CJT< a | bias => b > [β=3];"
        "feedback back: b -> a [β=0.5];"
    ), code="E-CJT-005")


def test_a_second_cycle_sharing_a_node_is_also_checked():
    # a->b->a is stable; a->c->a is unstable. A global visited set can miss it.
    _structural_error(_typed_board(
        "cjt quiet: CJT< a | bias => b > [β=0.2];"
        "feedback quiet_return: b -> a [β=0.2];"
        "cjt loud: CJT< a | bias => c > [β=3];"
        "feedback loud_return: c -> a [β=0.5];"
    ), code="E-CJT-005")


def test_three_edge_cycle_product_is_checked():
    _structural_error(_typed_board(
        "cjt first: CJT< a | bias => b > [β=2];"
        "cjt second: CJT< b | bias => c > [β=2];"
        "feedback back: c -> a [β=0.3];"
    ), code="E-CJT-005")


def test_unknown_feedback_gain_in_a_cycle_is_explicitly_unverified():
    # Appendix C 277 calls beta optional but does not give feedback a default.
    report = _check(_typed_board(
        "cjt stage: CJT< a | bias => b > [β=2];"
        "feedback back: b -> a;"
    ))
    assert report["parse_status"] == "PASS", report
    assert report["structural_status"] == "UNVERIFIED", report
    assert not _errors(report), report
    assert any(d["severity"] == "unverified" for d in report["diagnostics"]), report


def test_bias_cycle_uses_gm_not_cause_effect_beta():
    # Appendix C 532 and 542: gm is bias->effect; beta is cause->effect.
    _structural_error("""
board bias_loop {
    node cause: ^1^P;
    node govern: ^5^P;
    node effect: ^2^P;
    cjt stage: CJT< cause | govern => effect > [β=0.1, gm=3];
    feedback back: effect -> govern [β=0.5];
}
""", code="E-CJT-005")


def test_large_beta_does_not_create_a_false_bias_loop_divergence():
    report = _check("""
board bias_loop {
    node cause: ^1^P;
    node govern: ^5^P;
    node effect: ^2^P;
    cjt stage: CJT< cause | govern => effect > [β=10, gm=0.1];
    feedback back: effect -> govern [β=0.5];
}
""")
    assert report["parse_status"] == "PASS", report
    assert "E-CJT-005" not in _codes(report, "error"), report


def test_missing_gm_in_bias_cycle_cannot_be_replaced_with_beta():
    # Appendix C 532 gives gm a model-dependent default, not numeric unity.
    report = _check("""
board bias_loop {
    node cause: ^1^P;
    node govern: ^5^P;
    node effect: ^2^P;
    cjt stage: CJT< cause | govern => effect > [β=0.1];
    feedback back: effect -> govern [β=0.5];
}
""")
    assert report["parse_status"] == "PASS", report
    assert report["structural_status"] == "UNVERIFIED", report
    assert "E-CJT-005" not in _codes(report, "error"), report


@pytest.mark.parametrize("parameter", ["gm", "rπ"])
def test_zero_model_parameters_satisfy_the_written_nonnegative_range(parameter):
    # Appendix C 532-533 says >=0, not >0. Execution remains unimplemented.
    report = _check(_typed_board(
        "cjt stage: CJT< a | bias => b > [β=0.2, " + parameter + "=0];"
    ))
    assert report["parse_status"] == "PASS", report
    assert not _errors(report), report


@pytest.mark.parametrize("parameters", ["β=-1", "gm=-1", "rπ=-1", "sat=0", "cutoff=1", "cutoff=0.7, sat=0.5"])
def test_invalid_cjt_ranges_are_structural_errors(parameters):
    # Appendix C 524-540 contains these explicit scalar constraints.
    _structural_error(_typed_board(
        "cjt stage: CJT< a | bias => b > [" + parameters + "];"
    ))


def test_declared_cutoff_region_does_not_fabricate_runtime_activation():
    # E-CJT-003 needs measured activation; the region enum alone cannot prove it.
    report = _check(_typed_board(
        "cjt stage: CJT< a | bias => b > [β=0.2, region=cutoff];"
    ))
    assert report["parse_status"] == "PASS", report
    assert "E-CJT-003" not in _codes(report, "error"), report
