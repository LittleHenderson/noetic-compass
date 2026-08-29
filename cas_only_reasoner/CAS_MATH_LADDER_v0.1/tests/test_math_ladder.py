"""The mathematical apprenticeship laws: IR bridge, prerequisite
graph, packet schema (authority refusals), SDG determinism, the
counterexample attack, skill gating, the substitution law, and the
full twelve-step ladder end to end - promotion, every typed
rejection, rollback, and determinism."""

import json
import os

import pytest

from mathschool import (SKILLS, SkillStore, Student, attack_equation,
                        generate, next_missing, teach, teachable_now,
                        validate_packet, verify_identity)
from mathschool.mathir import (MathParseError, number_to_words,
                               parse_equation, parse_expr,
                               render_expr)
from mathschool.sdg import DEV_SEED, PROTECTED_SEED


# ------------------------------------------------------------- packets
def _packet(skill_id, **overrides):
    base = {
        "lesson_id": f"TEST_{skill_id}",
        "skill_id": skill_id,
        "teacher_model": "hand_authored_test_teacher",
        "teacher_revision": "test",
        "explanation": f"a lesson about {skill_id}",
        "provenance": "test_channel",
    }
    content = {
        "quantity_grounding": {
            "worked_examples": ["1 + 1 = 2", "2 + 1 = 3"],
            "common_mistake": "2 = 3"},
        "counting_order": {
            "worked_examples": ["4 + 1 = 5", "7 + 1 = 8"],
            "common_mistake": "5 + 1 = 5"},
        "integer_comparison": {
            "worked_examples": ["3 = 3", "0 - 2 = -2"],
            "common_mistake": "3 = 4"},
        "addition": {
            "worked_examples": ["3 + 4 = 7", "5 + 6 = 11"],
            "common_mistake": "3 + 4 = 12"},
        "subtraction": {
            "worked_examples": ["9 - 4 = 5", "7 - 2 = 5"],
            "common_mistake": "7 - 2 = 9"},
        "multiplication": {
            "worked_examples": ["3 * 4 = 12", "5 * 6 = 30"],
            "common_mistake": "3 * 4 = 7"},
        "division": {
            "worked_examples": ["12 = 4 * 3", "10 * 1/2 = 5"],
            "common_mistake": "12 = 4 * 2"},
        "fractions": {
            "worked_examples": ["1/2 + 1/4 = 3/4", "2/4 = 1/2"],
            "common_mistake": "1/2 + 1/3 = 2/5"},
        "algebra_distribute": {
            "formal_rule": "a * (b + c) = a * b + a * c",
            "worked_examples": ["2 * (3 + 4) = 2 * 3 + 2 * 4",
                                "5 * (1 + 6) = 5 * 1 + 5 * 6"],
            "common_mistake": "a * (b + c) = a * b + c"},
        "linear_equations": {
            "method": ["expand", "isolate"],
            "worked_examples": [
                {"equation": "2 * (x + 3) = 14", "variable": "x",
                 "solution": "4"},
                {"equation": "3 * y + 2 = 17", "variable": "y",
                 "solution": "5"}],
            "common_mistake": "2 * 4 = 11"},
        "functions_evaluation": {
            "worked_examples": ["2 * 3 + 1 = 7", "3 * 2^2 = 12"],
            "common_mistake": "2 * 3 + 1 = 8"},
        "coordinate_slope": {
            "worked_examples": ["(6 - 2) * 1/2 = 2", "4 * 1/2 = 2"],
            "common_mistake": "4 * 1/2 = 4"},
        "geometry_points": {
            "worked_examples": ["2^2 + 3^2 = 13", "(4 - 1)^2 = 9"],
            "common_mistake": "2^2 + 3^2 = 10"},
        "geometry_shapes": {
            "worked_examples": ["4 * 6 * 1/2 = 12",
                                "3 * 4 * 1/2 = 6"],
            "common_mistake": "4 * 6 * 1/2 = 24"},
        "sequences": {
            "worked_examples": ["2 + 4 * 3 = 14", "3 * 2^3 = 24"],
            "common_mistake": "2 + 4 * 3 = 18"},
        "derivatives_polynomial": {
            "worked_examples": ["2 * 3 = 6", "3 * 2^2 = 12"],
            "common_mistake": "2 * 3 = 5"},
        "integrals_polynomial": {
            "worked_examples": ["3^2 - 1 = 8", "1/2 * 4 = 2"],
            "common_mistake": "3^2 - 1 = 7"},
        "matrices_2x2": {
            "worked_examples": ["1 * 4 - 2 * 3 = -2",
                                "2 * 5 - 1 * 3 = 7"],
            "common_mistake": "1 * 4 - 2 * 3 = 2"},
        "probability_finite": {
            "worked_examples": ["3 * 1/6 = 1/2", "1 - 1/6 = 5/6"],
            "common_mistake": "1 - 1/6 = 1/6"},
        "statistics_basic": {
            "worked_examples": ["(1 + 2 + 6) * 1/3 = 3",
                                "(2 + 4) * 1/2 = 3"],
            "common_mistake": "(1 + 2 + 6) * 1/3 = 4"},
        "axiom_commutativity": {
            "formal_rule": "a + b = b + a",
            "worked_examples": ["2 + 3 = 3 + 2", "5 + 1 = 1 + 5"],
            "common_mistake": "2 - 3 = 3 - 2"},
        "axiom_square_expand": {
            "formal_rule": "(a + b)^2 = a^2 + 2 * a * b + b^2",
            "worked_examples": [
                "(2 + 3)^2 = 2^2 + 2 * 2 * 3 + 3^2",
                "(1 + 4)^2 = 25"],
            "common_mistake": "(a + b)^2 = a^2 + b^2"},
        "formal_proofs": {
            "worked_examples": ["(2 + 1)^2 = 9", "2 * (3 + 4) = 14"],
            "common_mistake": "(2 + 1)^2 = 5"},
        "conjecture_discovery": {
            "worked_examples": ["(2 + 3) * (2 - 3) = -5",
                                "2^2 - 3^2 = -5"],
            "common_mistake": "(2 + 3) * (2 - 3) = 5"},
    }[skill_id]
    base.update(content)
    base.update(overrides)
    return base


CHAIN = ["quantity_grounding", "counting_order", "integer_comparison",
         "addition", "subtraction", "multiplication", "division",
         "fractions", "algebra_distribute", "linear_equations"]

CHAIN_FULL = CHAIN + [
    "functions_evaluation", "coordinate_slope", "geometry_points",
    "geometry_shapes", "sequences", "derivatives_polynomial",
    "integrals_polynomial", "matrices_2x2", "probability_finite",
    "statistics_basic", "axiom_commutativity", "axiom_square_expand",
    "formal_proofs", "conjecture_discovery"]


def _teach_chain(path, upto, chain=None):
    chain = chain or CHAIN
    for skill_id in chain[:chain.index(upto) + 1]:
        episode = teach(_packet(skill_id), path)
        assert episode["verdict"] == "PROMOTED", \
            f"{skill_id}: {episode['verdict']} " \
            f"{episode['stages'][-1]}"


# ---------------------------------------------------------------- IR
def test_infix_bridge_round_trips_exactly():
    for text in ("3 + 4", "2 * (x + 3)", "1/2 + 1/4",
                 "(a + b)^2", "-x + 5"):
        expr = parse_expr(text)
        again = parse_expr(render_expr(expr))
        from mathschool.mathir import canonical
        assert canonical(expr) == canonical(again)
    with pytest.raises(MathParseError):
        parse_expr("3 +")
    with pytest.raises(MathParseError):
        parse_equation("3 + 4")
    assert number_to_words(parse_expr("7").q) == "seven"


# -------------------------------------------------------------- graph
def test_rpm_names_the_first_missing_prerequisite():
    assert next_missing("linear_equations", []) \
        == "quantity_grounding"
    assert next_missing("addition", ["quantity_grounding"]) \
        == "counting_order"
    assert teachable_now([]) == ["quantity_grounding"]
    assert set(CHAIN_FULL) == set(SKILLS)
    assert len(SKILLS) == 24


# ------------------------------------------------------------- schema
def test_packet_authority_fields_refused():
    for field in ("verified", "promote", "checker", "protected",
                  "threshold"):
        defects = validate_packet(_packet("addition",
                                          **{field: True}))
        assert any("forbidden authority field" in d for d in defects)


def test_packet_bad_formal_content_refused():
    defects = validate_packet(_packet(
        "addition", worked_examples=["3 + 4 = 7", "3 + = 7"]))
    assert any("does not parse" in d for d in defects)


# ---------------------------------------------------------------- SDG
def test_sdg_is_deterministic_and_channels_differ():
    a = generate("addition", "computation", DEV_SEED, 8)
    b = generate("addition", "computation", DEV_SEED, 8)
    assert a == b
    protected = generate("addition", "computation", PROTECTED_SEED, 8)
    assert protected != a


def test_counterexample_attack_finds_exact_witnesses():
    witness = attack_equation("a * (b + c) = a * b + c")
    assert witness is not None and "point" in witness
    holds, _ = verify_identity("a * (b + c) = a * b + a * c")
    assert holds
    assert attack_equation("3 + 4 = 12") is not None
    assert attack_equation("3 + 4 = 7") is None


# ------------------------------------------------------------- student
def test_skill_gating_yields_typed_cannot():
    student = Student(SkillStore())
    result = student.solve({"exercise_id": "x", "skill_id": "addition",
                            "kind": "arith", "op": "add",
                            "a": "3", "b": "4", "expected": "7"})
    assert result["status"] == "CANNOT_MISSING_SKILL"
    assert result["missing_skill"] == "addition"


def test_tampered_store_refused(tmp_path):
    path = os.path.join(tmp_path, "skills.json")
    store = SkillStore()
    store.save(path)
    payload = json.load(open(path, encoding="utf-8"))
    payload["revision"] = 99
    json.dump(payload, open(path, "w", encoding="utf-8"))
    with pytest.raises(Exception, match="digest mismatch"):
        SkillStore.load(path)


# -------------------------------------------------------------- ladder
def test_full_chain_promotes_l0_through_l4(tmp_path):
    path = os.path.join(tmp_path, "skills.json")
    _teach_chain(path, "linear_equations")
    store = SkillStore.load(path)
    assert store.promoted_ids() == sorted(CHAIN)
    # the student now SOLVES a fresh equation, verified by
    # substitution into the original
    student = Student(store)
    result = student.solve({"exercise_id": "q", "skill_id":
                            "linear_equations", "kind": "solve",
                            "equation": "2 * (x + 3) = 14",
                            "variable": "x", "expected": "4"})
    assert result["status"] == "SOLVED"
    assert result["answer"] == "4"
    assert result["verified_by"] == "substitution_into_original"


def test_prerequisite_missing_is_typed_and_names_the_gap(tmp_path):
    path = os.path.join(tmp_path, "skills.json")
    episode = teach(_packet("addition"), path)
    assert episode["verdict"] == "REJECTED_PREREQUISITE_MISSING"
    assert "quantity_grounding" in episode["stages"][0]["detail"]


def test_wrong_worked_example_rejected_with_witness(tmp_path):
    path = os.path.join(tmp_path, "skills.json")
    _teach_chain(path, "counting_order")
    packet = _packet("addition",
                     worked_examples=["3 + 4 = 8", "5 + 6 = 11"])
    episode = teach(packet, path)
    assert episode["verdict"] == "REJECTED_EXAMPLE"
    assert "FALSE" in episode["stages"][-1]["detail"]


def test_false_rewrite_rule_killed_by_counterexample(tmp_path):
    path = os.path.join(tmp_path, "skills.json")
    _teach_chain(path, "multiplication")
    packet = _packet("algebra_distribute",
                     formal_rule="a * (b + c) = a * b + c",
                     worked_examples=["2 * (3 + 4) = 14",
                                      "3 * (1 + 2) = 9"])
    episode = teach(packet, path)
    assert episode["verdict"] == "REJECTED_RULE_COUNTEREXAMPLE"
    assert "counterexample" in episode["stages"][-1]["detail"]


def test_true_statement_offered_as_mistake_is_rejected(tmp_path):
    path = os.path.join(tmp_path, "skills.json")
    _teach_chain(path, "counting_order")
    packet = _packet("addition", common_mistake="3 + 4 = 7")
    episode = teach(packet, path)
    assert episode["verdict"] == "REJECTED_MISTAKE_NOT_A_MISTAKE"


def test_reteaching_a_promoted_skill_quarantines(tmp_path):
    path = os.path.join(tmp_path, "skills.json")
    _teach_chain(path, "quantity_grounding")
    episode = teach(_packet("quantity_grounding"), path)
    assert episode["verdict"] == "QUARANTINED_ALREADY_PROMOTED"


def test_episode_is_deterministic_and_carries_the_authority_seals(
        tmp_path):
    path_a = os.path.join(tmp_path, "a.json")
    path_b = os.path.join(tmp_path, "b.json")
    a = teach(_packet("quantity_grounding"), path_a)
    b = teach(_packet("quantity_grounding"), path_b)
    assert a["episode_digest"] == b["episode_digest"]
    assert a["checker_digest"]
    assert a["rollback_pointer"]["parent_revision"] == 0
    ohm = [s for s in a["stages"] if s["stage"] == "CAS_OHM_PROFILE"]
    assert len(ohm) == 1
    profile = json.loads(ohm[0]["detail"])
    assert profile["flow_before"] == "cutoff"
    assert profile["flow_after"] == "active"
    assert profile["P_cap_before"] == 0.0
    assert profile["P_cap_after"] == 1.0


# ------------------------------------------------- the FULL ladder
def test_full_ladder_promotes_l0_through_l10(tmp_path):
    """Every level of the goal ladder, end to end: 24 skills, the
    prover producing independently-verified proofs, and the L10
    discovery round proving NOVEL identities and refuting perturbed
    ones with exact witnesses."""
    path = os.path.join(tmp_path, "skills.json")
    _teach_chain(path, "conjecture_discovery", chain=CHAIN_FULL)
    store = SkillStore.load(path)
    assert len(store.promoted_ids()) == 24

    student = Student(store)
    from mathschool.mathir import canonical, parse_expr
    d = student.solve({"exercise_id": "d", "skill_id": "x",
                       "kind": "derivative",
                       "expr": "3 * x^2 + 5 * x", "variable": "x",
                       "expected_equal_to": "6 * x + 5"})
    assert canonical(parse_expr(d["answer_expr"])) \
        == canonical(parse_expr("6 * x + 5"))
    i = student.solve({"exercise_id": "i", "skill_id": "x",
                       "kind": "integral", "expr": "2 * x",
                       "variable": "x", "a": "0", "b": "3",
                       "expected": "9"})
    assert i["answer"] == "9"
    assert i["verified_by"] == "differentiate_back_check"

    from mathschool.advanced import examiner_verify_proof
    proof = student.solve({"exercise_id": "p", "skill_id": "x",
                           "kind": "prove",
                           "lhs_text": "(x + 2)^2",
                           "rhs_text": "4 * x + 4 + x^2",
                           "expected": "proved"})
    assert proof["status"] == "SOLVED"
    assert examiner_verify_proof("(x + 2)^2", "4 * x + 4 + x^2",
                                 proof["steps"])

    from mathschool.advanced import examiner_verify_discovery
    round_result = student.solve({"exercise_id": "r",
                                  "skill_id": "x",
                                  "kind": "discovery_round",
                                  "seed": 7, "budget": 40,
                                  "min_proved": 1,
                                  "min_refuted": 2,
                                  "expected": "discovery_verified"})
    ok, detail = examiner_verify_discovery(
        round_result, round_result["library_used"], 1, 2)
    assert ok, detail
    for item in round_result.get("conjectures", []):
        assert "CONJECTURE" in item["status"]


def test_proof_steps_cannot_smuggle_false_schemas():
    """The independent proof examiner refuses a step justified by a
    FALSE schema, even if the endpoints happen to look right."""
    from mathschool.advanced import examiner_verify_proof
    fake_steps = [{"rule": "evil", "direction": "forward",
                   "lhs_schema": "a * (b + c)",
                   "rhs_schema": "a * b + c",
                   "from": "(2 * (x + 3))",
                   "to": "((2 * x) + 3)"}]
    assert not examiner_verify_proof("2 * (x + 3)", "2 * x + 3",
                                     fake_steps)


def test_discovery_examiner_rejects_non_novel_and_false_claims():
    from mathschool.advanced import examiner_verify_discovery
    library = [("a * (b + c)", "a * b + a * c")]
    fake = {"proved": [{"claim": "a * (b + c) = a * b + a * c"}],
            "refuted": [{"claim": "1 + 1 = 3",
                         "witness": {"point": {}}},
                        {"claim": "2 + 2 = 5",
                         "witness": {"point": {}}}]}
    ok, detail = examiner_verify_discovery(fake, library, 1, 2)
    assert not ok and "not novel" in detail
    false_claim = {"proved": [{"claim": "a + b = a * b"}],
                   "refuted": []}
    ok, detail = examiner_verify_discovery(false_claim, library, 1, 0)
    assert not ok and "NOT true" in detail
