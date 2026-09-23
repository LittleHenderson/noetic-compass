"""Builder checks for additive Stage 2 contracts; no model or course execution.

These public, authored fixtures are not the independent acceptance oracle or
the sealed HSET questions. Run on the selected AWS CPU worker, not the laptop.
"""
from copy import deepcopy
import math

import pytest

from cas_meta2.typed_teaching import (
    answers, answers_v2, checker, checker_v2, course, focal, slots, slots_v2, source,
)


def _family(n=5, *, domain="focus", prefix="F", edges=None):
    labels = tuple(f"{prefix}{i}" for i in range(n))
    edges = list(zip(range(n), range(1, n))) if edges is None else edges
    return {
        "family_id": "stage2-builder:" + domain + ":" + prefix,
        "domain": domain, "archetype": "UNTRUSTED_BUILDER_FIXTURE",
        "rendering": 0, "kind": "declared fixture kind", "labels": labels,
        "branches": tuple({"source": labels[a], "target": labels[b]} for a, b in edges),
        "split": "training", "setting": "declared fixture setting",
        "function": "declared fixture function",
    }


def _public(focus, *bank):
    frozen = source.freeze_bank(list(bank) if bank else [focus])
    return source.public_source(source.compile_source(focus, bank=frozen))


def _pair(n=5, *, edges=None, target_edges=None, target_n=None, target_domain="other"):
    return _public(
        _family(n, edges=edges),
        _family(n if target_n is None else target_n, domain=target_domain,
                prefix="T", edges=edges if target_edges is None else target_edges),
    )


def _world(public, focus=True):
    return next(w for w in public["worlds"]
                if (w["world_id"] == public["focus_world_id"]) == focus)


def _query(public, kind):
    refs = sorted(node["ref"] for node in _world(public)["nodes"])
    args, rule = {}, None
    if kind == "correspondence":
        args = {"target_world_id": _world(public, False)["world_id"]}
    elif kind == "parts":
        args = {"whole": refs[0]}
    elif kind == "reach":
        args = {"whole": refs[0], "part": refs[-1]}
        rule = "first_direct_constituent_lexical_v1"
    elif kind == "role_set":
        world = _world(public)
        args = {"focal_excerpt": focal.PREFIXES["definition"] + source.canonical({
            "whole": world["declared_whole"],
            "kind_ref": answers.declaration_ref(world["world_id"], "kind"),
            "function_ref": answers.declaration_ref(world["world_id"], "function"),
        })}
    return answers.compile_query(public, kind=kind, arguments=args, rule=rule)


def _packet(public, kind="correspondence"):
    query = _query(public, kind)
    row = {
        "schema": course.PACKET_SCHEMA,
        "source_digest": source.public_digest(public),
        "source_world_id": public["focus_world_id"], "query": query,
        "cue": None, "instruction": course.REQUESTS[kind],
        "role_catalog": deepcopy(course.ROLE_CATALOG), "supports": [],
    }
    packet = {"source": deepcopy(public),
              "record": {"record_id": "typed-input-" + source.digest(row), **row}}
    return course.validate_model_packet(packet)


def _values(target):
    return [a["value"] for a in target["admissible_answers"]]


def _scores(plan):
    return {slot["slot_id"]: {symbol: ((i + 1) * (j + 1)) / 7.0
                             for j, symbol in enumerate(slot["symbols"])}
            for i, slot in enumerate(plan["slots"])}


def _target_without_profile(target):
    return {key: value for key, value in target.items()
            if key not in {"checker_profile", "checker_profile_digest", "target_digest"}}


KINDS = ("role_set", "definition", "context", "parts", "edge_account",
         "reach", "analogy", "correspondence")


def test_profiles_are_separate_and_do_not_mutate_original_contract():
    old = deepcopy(checker.checker_profile())
    new = checker_v2.checker_profile()
    assert old["schema"] == "cas.typed-teaching-semantic-profile/0.1"
    assert old["max_isomorphism_nodes"] == checker.MAX_ISOMORPHISM_NODES == 4
    assert new["schema"] == "cas.typed-teaching-semantic-profile/0.2"
    assert new["max_isomorphism_nodes"] == checker_v2.MAX_ISOMORPHISM_NODES == 6
    assert new["profile_digest"] != old["profile_digest"]
    assert "frozen" not in new["schema"].lower()
    assert {k: v for k, v in new.items() if k not in {
        "schema", "max_isomorphism_nodes", "profile_digest"}} == {
        k: v for k, v in old.items() if k not in {
            "schema", "max_isomorphism_nodes", "profile_digest"}}
    public = _pair(5)
    checker_v2.derive_target(public, _query(public, "analogy"))
    slots_v2.compile_slots(_packet(public))
    assert checker.checker_profile() == old
    assert answers.MAX_PERMUTATION_NODES == 4
    assert slots.profile()["correspondence_max_nodes"] == 4
    assert slots_v2.profile()["correspondence_max_nodes"] == 6
    with pytest.raises(checker.SemanticCheckError, match="ISOMORPHISM_BOUND"):
        checker.derive_target(public, _query(public, "analogy"))
    with pytest.raises(answers.AnswerContractError, match="PERMUTATION_BOUND"):
        slots.compile_slots(_packet(public))


@pytest.mark.parametrize("n", [3, 4])
@pytest.mark.parametrize("kind", KINDS)
def test_small_targets_preserve_answers_coverage_witnesses_and_decisions(n, kind):
    public = _pair(n)
    query = _query(public, kind)
    original = checker.derive_target(public, query)
    revised = checker_v2.derive_target(public, query)
    assert source.canonical(_target_without_profile(revised)) == source.canonical(
        _target_without_profile(original))
    assert revised["target_digest"] != original["target_digest"]
    for answer in original["admissible_answers"]:
        old_result = checker.check_answer(public, query, answer)
        new_result = checker_v2.check_answer(public, query, answer)
        for field in ("correct", "admissible_answer_count", "answer_digest", "witnesses"):
            assert new_result[field] == old_result[field]


@pytest.mark.parametrize("n", [3, 4])
@pytest.mark.parametrize("kind", KINDS)
def test_small_slot_plans_and_decoder_outputs_are_byte_identical(n, kind):
    packet = _packet(_pair(n), kind)
    original = slots.compile_slots(packet)
    revised = slots_v2.compile_slots(packet)
    assert source.canonical(revised).encode() == source.canonical(original).encode()
    scores = _scores(original)
    old_decision = slots.score_decisions(packet, scores)
    new_decision = slots_v2.score_decisions(packet, scores)
    assert new_decision == old_decision
    assert slots_v2.assemble_answer(packet, new_decision) == slots.assemble_answer(packet, old_decision)


@pytest.mark.parametrize("n", [5, 6])
@pytest.mark.parametrize("kind", ["analogy", "correspondence"])
def test_chain_matching_at_new_bounds_is_complete(n, kind):
    public = _pair(n)
    query = _query(public, kind)
    target = checker_v2.derive_target(public, query)
    other = _world(public, False)
    if kind == "analogy":
        assert _values(target) == [{"world_id": other["world_id"]}]
        assert sum(row["permutations_checked"] for row in target["coverage"]["decisions"]) == math.factorial(n)
    else:
        expected = {"status": "MAPPING", "pairs": [
            {"source": left["ref"], "target": right["ref"]}
            for left, right in zip(_world(public)["nodes"], other["nodes"])]}
        assert _values(target) == [expected]
        assert target["coverage"]["matching_bijections"] == 1
        assert target["coverage"]["permutations_checked"] == math.factorial(n)
    assert checker_v2.check_answer(public, query, target["admissible_answers"][0])["correct"]


@pytest.mark.parametrize("n", [5, 6])
def test_same_domain_match_is_excluded_only_for_analogy(n):
    public = _pair(n, target_domain="focus")
    target = checker_v2.derive_target(public, _query(public, "analogy"))
    assert _values(target) == [{"world_id": None}]
    assert target["coverage"]["decisions"][0]["reason"] == "SAME_DECLARED_DOMAIN"
    assert target["coverage"]["decisions"][0]["permutations_checked"] == 0
    correspondence = checker_v2.derive_target(public, _query(public, "correspondence"))
    assert _values(correspondence)[0]["status"] == "MAPPING"


@pytest.mark.parametrize("kind", ["analogy", "correspondence"])
def test_degree_colliding_nonisomorphic_trees_produce_no_match(kind):
    # Rooted branch depths are (3, 1) versus (2, 2). Both have two degree-(1,1)
    # nodes, two degree-(1,0) leaves and one degree-(0,2) root.
    long_arm = [(0, 1), (0, 2), (1, 3), (3, 4)]
    balanced = [(0, 1), (0, 2), (1, 3), (2, 4)]
    degrees = lambda edges: sorted((sum(b == i for _, b in edges),
                                    sum(a == i for a, _ in edges)) for i in range(5))
    assert degrees(long_arm) == degrees(balanced)
    public = _pair(5, edges=long_arm, target_edges=balanced)
    target = checker_v2.derive_target(public, _query(public, kind))
    expected = {"world_id": None} if kind == "analogy" else {"status": "NO_MATCH", "pairs": []}
    assert _values(target) == [expected]
    coverage = target["coverage"] if kind == "correspondence" else target["coverage"]["decisions"][0]
    assert coverage["reason"] == "NO_EDGE_PRESERVING_BIJECTION"
    assert coverage["permutations_checked"] == 120


def test_five_node_star_retains_all_twenty_four_valid_mappings():
    public = _pair(5, edges=[(0, i) for i in range(1, 5)])
    query = _query(public, "correspondence")
    target = checker_v2.derive_target(public, query)
    assert len(target["admissible_answers"]) == target["coverage"]["matching_bijections"] == 24
    encoded = [source.canonical(answer).encode() for answer in target["admissible_answers"]]
    assert encoded == sorted(set(encoded))
    assert all(len(answer["value"]["pairs"]) == 5 for answer in target["admissible_answers"])


def test_six_node_star_refuses_120_correct_maps_without_truncating_syntax():
    public = _pair(6, edges=[(0, i) for i in range(1, 6)])
    query = _query(public, "correspondence")
    with pytest.raises(checker_v2.SemanticCheckError, match="TARGET_SET_BOUND"):
        checker_v2.derive_target(public, query)
    assert len(answers_v2.correspondence_candidates(public, query)) == 721
    # One accepted world remains one analogy answer, regardless of automorphisms.
    assert len(checker_v2.derive_target(public, _query(public, "analogy"))["admissible_answers"]) == 1


@pytest.mark.parametrize("kind", ["analogy", "correspondence"])
@pytest.mark.parametrize("same_domain", [False, True])
def test_seven_node_target_is_refused_even_before_domain_or_count_rejection(kind, same_domain):
    public = _pair(5, target_n=7, target_domain="focus" if same_domain else "other")
    query = _query(public, kind)
    with pytest.raises(checker_v2.SemanticCheckError, match="ISOMORPHISM_BOUND"):
        checker_v2.derive_target(public, query)
    if kind == "correspondence":
        with pytest.raises(answers.AnswerContractError, match="PERMUTATION_BOUND"):
            answers_v2.correspondence_candidates(public, query)


def test_sixty_four_bank_worlds_plus_separate_focus_are_admitted():
    focus = _family(5)
    public = _public(focus, *[_family(5, domain=f"domain{i}", prefix=f"T{i}N") for i in range(64)])
    assert len(public["worlds"]) == 65
    assert len(public["bank"]["world_ids"]) == 64
    target = checker_v2.derive_target(public, _query(public, "analogy"))
    assert len(target["admissible_answers"]) == 64
    assert {value["world_id"] for value in _values(target)} == set(public["bank"]["world_ids"])
    assert sum(row["permutations_checked"] for row in target["coverage"]["decisions"]) == 64 * 120


def test_sixty_five_bank_worlds_are_refused_at_source_boundary():
    families = [_family(3, domain=f"domain{i}", prefix=f"T{i}N") for i in range(65)]
    with pytest.raises(ValueError, match="TYPED_SOURCE_BANK_BOUND"):
        source.freeze_bank(families)
    public = _public(families[64], *families[:64])
    public["bank"]["world_ids"] = sorted(world["world_id"] for world in public["worlds"])
    with pytest.raises(ValueError, match="TYPED_SOURCE_PUBLIC_BANK_REFS"):
        source.validate_public(public)


@pytest.mark.parametrize("n, count", [(5, 121), (6, 721)])
def test_extended_slot_plans_keep_every_syntactic_complete_assignment(n, count):
    packet = _packet(_pair(n))
    plan = slots_v2.compile_slots(packet)
    assert plan["schema"] == slots_v2.PLAN_SCHEMA
    assert plan["profile"]["correspondence_max_nodes"] == 6
    assert len(plan["slots"]) == n + 1
    candidates = plan["correspondence_candidates"]
    assert len(candidates) == count
    assert candidates[0]["value"] == {"status": "NO_MATCH", "pairs": []}
    assert len({row["candidate_id"] for row in candidates}) == count
    assert [row["value"] for row in candidates] == answers_v2.correspondence_candidates(
        packet["source"], packet["record"]["query"])
    assert slots_v2.validate_plan(packet, plan) == plan


@pytest.mark.parametrize("n", [5, 6])
def test_wrong_but_syntactic_assignment_remains_selectable_and_is_not_repaired(n):
    packet = _packet(_pair(n))
    plan = slots_v2.compile_slots(packet)
    chosen = plan["correspondence_candidates"][-1]
    scores = {slot["slot_id"]: {symbol: -20.0 for symbol in slot["symbols"]}
              for slot in plan["slots"]}
    scores[plan["slots"][0]["slot_id"]]["MAPPING"] = 20.0
    alias = {node["ref"]: node["alias"] for world in plan["aliases"]["worlds"] for node in world["nodes"]}
    by_source = {slot["coordinates"][0]: slot for slot in plan["slots"][1:]}
    for pair in chosen["value"]["pairs"]:
        scores[by_source[pair["source"]]["slot_id"]][alias[pair["target"]]] = 20.0
    decision = slots_v2.score_decisions(packet, scores)
    assert decision["correspondence_candidate_id"] == chosen["candidate_id"]
    answer = slots_v2.assemble_answer(packet, decision)
    assert answer["value"] == chosen["value"]
    assert answers.validate_answer(packet["source"], packet["record"]["query"], answer) == answer
    assert not checker_v2.check_answer(packet["source"], packet["record"]["query"], answer)["correct"]


@pytest.mark.parametrize("n", [5, 6])
def test_complete_assignment_probabilities_preserve_original_decoder_and_reference(n):
    packet = _packet(_pair(n))
    plan = slots_v2.compile_slots(packet)
    scores = _scores(plan)
    result = slots_v2.candidate_scores(packet, scores)
    assert result == slots._candidate_scores(plan, scores)
    assert math.fsum(math.exp(row["log_probability"]) for row in result) == pytest.approx(1.0)
    mode = scores[plan["slots"][0]["slot_id"]]
    mode_mass = math.exp(mode["MAPPING"]) + math.exp(mode["NO_MATCH"])
    assert math.exp(result[0]["log_probability"]) == pytest.approx(math.exp(mode["NO_MATCH"]) / mode_mass)
    alias = {node["ref"]: node["alias"] for world in plan["aliases"]["worlds"] for node in world["nodes"]}
    by_source = {slot["coordinates"][0]: slot for slot in plan["slots"][1:]}
    weights = [math.prod(math.exp(scores[by_source[pair["source"]]["slot_id"]][alias[pair["target"]]])
                         for pair in candidate["value"]["pairs"])
               for candidate in plan["correspondence_candidates"][1:]]
    normalizer = math.fsum(weights)
    for row, weight in zip(result[1:], weights):
        assert math.exp(row["log_probability"]) == pytest.approx(
            math.exp(mode["MAPPING"]) / mode_mass * weight / normalizer)
    shifted = deepcopy(scores)
    for slot in plan["slots"][1:]:
        shifted[slot["slot_id"]] = {symbol: value + 17.0 for symbol, value in shifted[slot["slot_id"]].items()}
    shifted_result = slots_v2.candidate_scores(packet, shifted)
    assert [row["log_probability"] for row in shifted_result] == pytest.approx(
        [row["log_probability"] for row in result])


@pytest.mark.parametrize("invalid", [True, float("nan"), float("inf"), -float("inf"), 1000001, "0"])
def test_extended_decoder_refuses_nonfinite_non_numeric_or_unbounded_scores(invalid):
    packet = _packet(_pair(5))
    plan = slots_v2.compile_slots(packet)
    scores = _scores(plan)
    scores[plan["slots"][0]["slot_id"]]["MAPPING"] = invalid
    with pytest.raises(ValueError, match="TYPED_SLOT_SCORE_SCALAR"):
        slots_v2.score_decisions(packet, scores)


def test_decisions_and_plans_cannot_cross_packet_bindings():
    first = _packet(_pair(5))
    second = _packet(_pair(5, target_domain="different"))
    plan = slots_v2.compile_slots(first)
    decision = slots_v2.score_decisions(first, _scores(plan))
    with pytest.raises(ValueError, match="TYPED_SLOT_DECISION_BINDING"):
        slots_v2.assemble_answer(second, decision)
    with pytest.raises(ValueError, match="TYPED_SLOT_PLAN_RECONSTRUCTION"):
        slots_v2.validate_plan(second, plan)


@pytest.mark.parametrize("invalid", [-1, 0, 7, True, 6.0])
def test_permutation_limit_rejects_invalid_or_expanded_bounds(invalid):
    public = _pair(5)
    with pytest.raises(answers.AnswerContractError, match="TYPED_PERMUTATION_LIMIT"):
        answers_v2.correspondence_candidates(public, _query(public, "correspondence"), max_nodes=invalid)


def test_unequal_node_inventories_force_no_match_without_partial_mapping():
    packet = _packet(_pair(5, target_n=6))
    plan = slots_v2.compile_slots(packet)
    assert plan["forced_candidate_count"] == 1
    assert len(plan["correspondence_candidates"]) == 1
    scores = _scores(plan)
    result = slots_v2.candidate_scores(packet, scores)
    assert result[0]["log_probability"] == 0.0
    answer = slots_v2.assemble_answer(packet, slots_v2.score_decisions(packet, scores))
    assert answer["value"] == {"status": "NO_MATCH", "pairs": []}
    assert checker_v2.check_answer(packet["source"], packet["record"]["query"], answer)["correct"]
