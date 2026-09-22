"""MEASURED FACTS about how the CAS compiler handles a thought inside a thought, pinned so nobody has to re-derive them.

Historical subject: the pre-CAS-Ohm compiler snapshot, LF sha256 61ed5a45970459e4...
The active compiler and offline package also expose CAS-Ohm; run() compares their legacy nesting behavior.
First measured 2026-09-21 on text 8169188ad73df8fc... by my own probes and by five independent
examiners plus a critic who re-ran twelve of their experiments (all twelve confirmed). RE-MEASURED the same day after the
compiler was changed (book meaning for the Nesting Operator; defects fixed): the facts marked FIXED below flipped and
are pinned in their new form; the name-keyed set limit is kept on purpose (owner decision pending). Symbolic only; no model is involved.

Three levels are kept apart in every test name:
    WRITES   the compiler stores which expression is inside which (in the parse tree, the `ast`)
    APPLIES  the surrounding expression changes how the inner one is worked out, as the canon book says
    (TEACH is not a property of the compiler: today no generated training example contains the ring sign or a set inside a set)

These are facts about THIS compiler text. If the compiler changes, the first test fails and every fact below must be re-measured.

Run:  python -m pytest research/helm_cas_expression_lab/test_compiler_nesting_facts.py -q      (about a second)
"""
import pathlib
import sys
import importlib.util

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import q3_behaviour_records as q3  # noqa: E402

COMPILER_SHA256_LF = "61ed5a45970459e49a6948282ce4060e7c3d3d3f7042078228bc97ff252b2527"
RING = "∘"          # the ring operator, the book's Nesting Operator sign
IN, NOT_IN, SUBSET = "∈", "∉", "⊆"
compile_expression, PIN = q3._load_compiler()
_current_path = HERE.parents[3] / "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py"
_current_spec = importlib.util.spec_from_file_location("_cas_nesting_current_regression", _current_path)
_current_module = importlib.util.module_from_spec(_current_spec)
sys.modules[_current_spec.name] = _current_module
_current_spec.loader.exec_module(_current_module)


def run(text):
    artifact = compile_expression(text).to_dict()
    # Historical targets remain bound to their old bytes; the active compiler
    # must still agree on every nesting fact exercised by this suite.
    current = _current_module.compile_expression(text).to_dict()
    for key in ("valid", "ast", "result", "warnings", "error"):
        assert current.get(key) == artifact.get(key), (key, text)
    result = artifact.get("result")
    if isinstance(result, dict) and result.get("kind") == "program":
        result = result.get("final_result")
    return artifact, result


def ring(*parts):
    return (" %s " % RING).join(parts)


def test_these_facts_are_about_this_exact_compiler_text():
    assert PIN["sha256"] == COMPILER_SHA256_LF, "the compiler changed: re-measure every fact in this file"
    import hashlib
    snapshot = HERE / PIN["snapshot_path"]
    assert hashlib.sha256(snapshot.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == COMPILER_SHA256_LF
    bundle = HERE.parents[3] / "dist/cas-offline/api/notation/compiler.py"
    assert bundle.read_bytes().replace(b"\r\n", b"\n") == _current_path.read_bytes().replace(b"\r\n", b"\n")


# ---------------------------------------------------------------- the ring operator: WRITES
def test_WRITES_the_ring_keeps_the_order_you_wrote():
    _, a = run(ring("^8^C", "^3^C"))
    _, b = run(ring("^3^C", "^8^C"))
    assert a["kind"] == b["kind"] == "fractal" and a["sequence"] == [8, 3] and b["sequence"] == [3, 8]


def test_WRITES_the_parse_tree_keeps_which_thought_is_inside_which_but_the_value_does_not():
    left_art, left = run("(%s) %s ^2^C" % (ring("^8^C", "^3^C"), RING))
    right_art, right = run("^8^C %s (%s)" % (RING, ring("^3^C", "^2^C")))
    assert left == right and left["sequence"] == [8, 3, 2]                      # the VALUE is one flat list: grouping is gone
    assert left_art["ast"] != right_art["ast"]                                  # the TREE still knows
    assert left_art["ast"]["op"] == "CIRC" and left_art["ast"]["left"]["op"] == "CIRC" and right_art["ast"]["right"]["op"] == "CIRC"


def test_WRITES_ten_levels_deep():
    text = "^1^C"
    for k in (2, 3, 4, 5, 6, 7, 8, 9, 0):
        text = "(%s %s ^%d^C)" % (text, RING, k)
    art, value = run(text)
    assert art["valid"] and value["sequence"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 0] and value["orbit_length"] == 10   # 'orbit_length' is just the list length


# ---------------------------------------------------------------- the ring operator: does NOT APPLY the book's meaning
def test_APPLIES_NOT_the_one_computed_number_is_a_plain_sum_so_order_cannot_change_it():
    for a in range(10):
        for b in range(10):
            _, ab = run(ring("^%d^C" % a, "^%d^C" % b))
            _, ba = run(ring("^%d^C" % b, "^%d^C" % a))
            assert ab["composed_operator"] == ba["composed_operator"] == "CO-%d" % ((a + b) % 10)


def test_APPLIES_NOT_a_noetic_nested_with_its_opposite_does_not_return_to_idea():
    _, nested = run(ring("^8^C", "^9^C"))
    assert nested["composed_operator"] == "CO-7"          # the book's Dual Cancellation would give ^0
    _, divided = run("^8^C / ^9^C")
    assert divided["kind"] == "state" and divided["dominant_state"] == "C0"      # only DIVISION cancels


def test_FIXED_drives_and_registers_on_nested_thoughts_are_kept_in_the_nesting_block():
    _, plain = run(ring("^8^C", "^3^C"))
    _, marked = run(ring("^8^C_{F2}|A", "^3^C|f"))
    legacy = {"kind", "sequence", "composed_operator", "orbit_length", "domain"}
    assert {k: plain[k] for k in legacy} == {k: marked[k] for k in legacy}      # the legacy fields still drop them ...
    assert [(t["drive"], t["register"]) for t in marked["nesting"]["terms"]] == [("F2", "A"), (None, "f")]   # ... the nesting block keeps them
    assert marked["nesting"]["innermost"] == "^8^C_{F2}|A" and marked["nesting"]["governing"] == "^3^C|f"


def test_FIXED_a_thought_can_be_nested_in_a_thought_of_another_domain_with_a_warning():
    art, value = run(ring("^8^P", "^3^C"))
    assert art["valid"] and value["nesting"]["crosses_domains"] is True and any("crosses Domains" in w for w in art["warnings"])
    art, _ = run("(^2^C + ^5^C) %s ^3^C" % RING)
    assert not art["valid"]                                           # a sum still cannot be nested: only single states and fractals


def test_APPLIES_the_books_meaning_is_now_computed_beside_the_legacy_digit_sum():
    _, nested = run(ring("^8^C", "^9^C"))
    assert nested["composed_operator"] == "CO-7"                                          # legacy digit sum, unchanged
    assert nested["nesting"]["canonical_form"]["form"] == ["^0^C"]                        # Dual Cancellation, computed
    assert nested["nesting"]["orbit_class"] == "stabilizing"
    _, other = run(ring("^9^C", "^8^C"))
    assert other["nesting"]["canonical_form"]["agreed"] is False and "N3" in other["nesting"]["open_questions"]   # the book is in two minds: reported, not decided


# ---------------------------------------------------------------- sets as meta-logic: EXECUTED, and they match the book
def test_the_built_in_universes_are_counted_by_the_compiler():
    sizes = {"Noetics": 10, "Domains": 4, "Registers": 4, "Drives": 7, "States": 40, "Foundations": 7, "SubFoundations": 28, "Foundation_1": 4}
    for name, n in sizes.items():
        assert run("|%s|" % name)[1]["value"] == n
    assert run("|States| = 40")[1]["holds"] is True and run("|States| = 41")[1]["holds"] is False     # a wrong count is FALSE, not an error
    # the compiler's 28 are 7 Drives x 4 REGISTERS -- the positional mirror of the owner's canonical 28 Foundations
    assert run("Foundation_3")[1]["elements"] == ["F3|A", "F3|E", "F3|T", "F3|f"]
    import foundations28
    assert {foundations28.to_cas_position(s) for s in foundations28.symbols()} == set(run("SubFoundations")[1]["elements"])


def test_member_of_and_subset_of_are_different_and_both_are_computed():
    assert run("^2 %s NoeticSet{^2, ^7}" % IN)[1]["holds"] is True
    assert run("NoeticSet{^2} %s NoeticSet{^2, ^7}" % SUBSET)[1]["holds"] is True
    assert run("NoeticSet{^2} %s NoeticSet{^2, ^7}" % IN)[1]["holds"] is False      # a set is not a MEMBER of a set of Noetics
    assert run("^2 %s NoeticSet{^3}" % NOT_IN)[1]["holds"] is True


# ---------------------------------------------------------------- a set inside a set: WRITES, with a name-only limit
def test_WRITES_a_set_can_sit_inside_a_set_three_levels_deep_without_being_flattened():
    program = "let S1 = NoeticSet{^2}; let S2 = {S1}; let S3 = {S2}; "
    assert run(program + "S2 %s S3" % IN)[1]["holds"] is True
    assert run(program + "S1 %s S3" % IN)[1]["holds"] is False        # S1 is inside S2, which is inside S3: not flattened
    assert run(program + "^2 %s S3" % IN)[1]["holds"] is False
    assert run(program + "|S3|")[1]["value"] == 1
    assert not run("NoeticSet{NoeticSet{^2, ^7}, ^3}")[0]["valid"]     # a TYPED set stays one kind of thing; only bare braces hold sets


def test_LIMIT_the_outer_set_remembers_the_inner_set_by_NAME_not_by_what_is_in_it():
    # STILL TRUE on purpose: a content-keyed version was built and withdrawn after review; set identity is the owner's call.
    program = "let S1 = NoeticSet{^2, ^7}; let S2 = {S1, NoeticSet{^3}}; "
    assert run(program + "S1 %s S2" % IN)[1]["holds"] is True
    assert run(program + "NoeticSet{^2, ^7} %s S2" % IN)[1]["holds"] is False     # same contents, spelled out: not recognised
    assert run(program + "NoeticSet{^3} %s S2" % IN)[1]["holds"] is True          # recognised only because it was spelled this way when S2 was built
    _, s2 = run(program + "S2")
    assert sorted(s2["elements"]) == ["NoeticSet{CO-3}", "S1"]


def test_LIMIT_an_expression_put_into_a_set_is_worked_out_first_and_only_a_label_is_kept():
    _, s = run("{^2^C + ^5^C, ^3^C}")
    assert sorted(s["elements"]) == ["C2", "C3"]                       # the sum is gone; only the label of its answer remains (still true)
    program = "let S4 = {%s}; " % ring("^8^C", "^3^C")
    assert run(program + "(%s) %s S4" % (ring("^8^C", "^3^C"), IN))[1]["holds"] is True      # FIXED: a ring result in a set is found again, order and all
    assert run(program + "(%s) %s S4" % (ring("^3^C", "^8^C"), IN))[1]["holds"] is False
    assert run("let R1 = ^5^P -> ^5^C; let Q5 = {R1}; R1 %s Q5" % IN)[1]["holds"] is True    # FIXED: so is a relation


def test_LIMIT_single_letters_are_reserved():
    art, _ = run("let S1 = NoeticSet{^2}; let C = {S1}; |C|")
    assert not art["valid"] and "is reserved in CAS notation" in art["error"]     # P, C, E, O (domains) and T, A, f, E (registers) are not free names; the message now says so


# ---------------------------------------------------------------- the picture: boxes inside boxes already exist for sets
def test_the_diagram_draws_a_set_inside_a_set_as_a_box_inside_a_box():
    build_diagram = _current_module.build_diagram
    raw_compile = _current_module.compile_expression
    diagram = build_diagram(raw_compile("{NoeticSet{^2, ^7}, NoeticSet{^3}}").ast)
    outer = [c for c in diagram["containers"] if c["kind"] == "typed_meta_set"][0]
    inner = {c["id"]: c for c in diagram["containers"] if c["kind"] == "noetic_cluster"}
    assert "containment" in diagram["layouts"] and set(outer["contains"]) == set(inner)
    assert sorted(inner["container:NoeticSet_CO-2_CO-7"]["contains"]) == ["noetic:CO-2", "noetic:CO-7"]
    ring_diagram = build_diagram(raw_compile("(%s) %s ^2^C" % (ring("^8^C", "^3^C"), RING)).ast)
    assert ring_diagram["containers"] == [] and len(ring_diagram["edges"]) > 0      # a ring expression is drawn as a branching web, not as containment
