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
    }[skill_id]
    base.update(content)
    base.update(overrides)
    return base


CHAIN = ["quantity_grounding", "counting_order", "integer_comparison",
         "addition", "subtraction", "multiplication", "division",
         "fractions", "algebra_distribute", "linear_equations"]


def _teach_chain(path, upto):
    for skill_id in CHAIN[:CHAIN.index(upto) + 1]:
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
    assert set(SKILLS) == set(CHAIN)


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
