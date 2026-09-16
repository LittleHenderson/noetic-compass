"""Private semantic checks using public fixtures only; no numerical execution."""
from copy import deepcopy
import builtins
import json
import sys

import pytest

from cas_meta2.typed_teaching import answers as a, checker as c, focal as f, source as s


@pytest.fixture(autouse=True)
def no_models_or_legacy_teachers(monkeypatch):
    original = builtins.__import__
    denied = {"torch", "numpy", "tensorflow", "jax", "cas_cjt", "casformer", "boto3",
              "botocore", "requests", "httpx", "openai", "anthropic", "transformers"}
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in denied or name.startswith("cas_meta2.graph_teaching"):
            raise AssertionError("FORBIDDEN_CHECKER_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    yield
    assert not denied.intersection(name.split(".")[0] for name in sys.modules)


def family(labels=("Whole", "Part", "Tip"), *, edges=None, domain="one"):
    edges = edges if edges is not None else list(zip(labels, labels[1:]))
    return {"family_id": "fixture:" + domain, "domain": domain, "archetype": "UNTRUSTED_NAME",
            "rendering": 0, "kind": "same declared kind", "labels": tuple(labels),
            "branches": tuple({"source": x, "target": y} for x, y in edges),
            "split": "training", "setting": "same declared setting",
            "function": "same declared function"}


def public_for(focus, *others):
    return s.public_source(s.compile_source(focus, bank=s.freeze_bank([focus, *others])))


@pytest.fixture(scope="module")
def public():
    return public_for(family(), family(("Box", "Bag", "Item"), domain="two"),
                      family(("Tree", "Left", "Right"), domain="three",
                             edges=[("Tree", "Left"), ("Tree", "Right")]))


def world(public, wid=None):
    return next(w for w in public["worlds"] if w["world_id"] == (wid or public["focus_world_id"]))


def ref(public, label, wid=None):
    return next(n["ref"] for n in world(public, wid)["nodes"] if n["label"] == label)


def domain_world(public, domain):
    return next(w["world_id"] for w in public["worlds"] if w["declarations"]["domain"] == domain)


def query(public, kind, **arguments):
    return a.compile_query(public, kind=kind, arguments=arguments)


def check(public, request, value):
    return c.check_answer(public, request, a.make_answer(public, request, value))


def values(target):
    return [answer["value"] for answer in target["admissible_answers"]]


@pytest.mark.parametrize("kind", ["definition", "context", "parts", "edge_account", "analogy", "correspondence"])
def test_targets_are_deterministic_bound_and_syntactically_admissible(public, kind):
    args = {"whole": ref(public, "Whole")} if kind == "parts" else {}
    if kind == "correspondence":
        args = {"target_world_id": domain_world(public, "two")}
    request = query(public, kind, **args)
    before = deepcopy((public, request))
    target = c.derive_target(public, request)
    assert target == c.derive_target(public, request) == c.validate_target(public, request, target)
    assert (public, request) == before
    assert target["source_digest"] == s.public_digest(public)
    assert target["query_id"] == request["query_id"]
    assert target["checker_profile_digest"] == c.checker_profile()["profile_digest"]
    for answer in target["admissible_answers"]:
        assert a.validate_answer(public, request, answer) == answer
        assert c.check_answer(public, request, answer)["correct"] is True


def test_declaration_references_are_focused_facts_not_equal_text_aliases(public):
    wid, other = public["focus_world_id"], domain_world(public, "two")
    q = query(public, "definition")
    good = {"whole": ref(public, "Whole"), "kind_ref": a.declaration_ref(wid, "kind"),
            "function_ref": a.declaration_ref(wid, "function")}
    assert check(public, q, good)["correct"] is True
    for field in ("kind", "function"):
        bad = {**good, field + "_ref": a.declaration_ref(other, field)}
        assert check(public, q, bad)["correct"] is False
    assert check(public, q, {**good, "whole": ref(public, "Part")})["correct"] is False
    q = query(public, "context")
    good = {"setting_ref": a.declaration_ref(wid, "setting"),
            "participants": sorted(world(public)["declarations"]["participants"])}
    assert check(public, q, good)["correct"] is True
    assert check(public, q, {**good, "setting_ref": a.declaration_ref(other, "setting")})["correct"] is False
    assert check(public, q, {**good, "participants": good["participants"][:-1]})["correct"] is False


def test_parts_are_direct_and_leaf_inventory_can_be_empty(public):
    q = query(public, "parts", whole=ref(public, "Whole"))
    assert values(c.derive_target(public, q)) == [{"nodes": [ref(public, "Part")]}]
    assert not check(public, q, {"nodes": sorted([ref(public, "Part"), ref(public, "Tip")])})["correct"]
    leaf = query(public, "parts", whole=ref(public, "Tip"))
    assert check(public, leaf, {"nodes": []})["correct"] is True


def test_edge_account_is_complete_set_not_an_ordered_process(public):
    q = query(public, "edge_account")
    correct = values(c.derive_target(public, q))[0]
    assert len(correct["edges"]) == 2
    assert not check(public, q, {"edges": correct["edges"][:1]})["correct"]
    assert not check(public, q, {"edges": [{"source": ref(public, "Whole"), "target": ref(public, "Whole")} ]})["correct"]
    target = c.derive_target(public, q)
    assert target["witnesses"][0]["evidence"]["order"].endswith("NOT_PROCESS")
    f = family(domain="procedural")
    f["branches"] = tuple(reversed(f["branches"]))
    p = public_for(f)
    target = c.derive_target(p, query(p, "edge_account"))
    assert len(values(target)[0]["edges"]) == 2
    assert world(p)["branch_order"]["process_order"] is None


@pytest.mark.parametrize("edges,expected", [
    ([(0, 1), (0, 2), (0, 3)], 6),
    ([(0, 1), (0, 2), (1, 3), (2, 3)], 2),
])
def test_all_symmetric_correspondences_are_accepted(edges, expected):
    lhs, rhs = ("Root", "A", "B", "C"), ("Box", "X", "Y", "Z")
    f = family(lhs, edges=[(lhs[x], lhs[y]) for x, y in edges])
    g = family(rhs, edges=[(rhs[x], rhs[y]) for x, y in edges], domain="two")
    p = public_for(f, g)
    q = query(p, "correspondence", target_world_id=domain_world(p, "two"))
    target = c.derive_target(p, q)
    assert len(target["admissible_answers"]) == expected
    outcomes = [check(p, q, value)["correct"] for value in a.correspondence_candidates(p, q)]
    assert len(outcomes) == 25 and sum(outcomes) == expected and outcomes[0] is False
    assert target["coverage"]["permutations_checked"] == 24


def test_graph_isomorphism_is_unrooted_and_not_based_on_declared_whole():
    p = public_for(family(("Leaf", "Root", "Tip"), edges=[("Root", "Leaf"), ("Root", "Tip")]),
                   family(("Box", "Left", "Right"), edges=[("Box", "Left"), ("Box", "Right")], domain="two"))
    q = query(p, "correspondence", target_world_id=domain_world(p, "two"))
    target = c.derive_target(p, q)
    assert len(target["admissible_answers"]) == 2
    assert all(next(pair["target"] for pair in v["pairs"] if pair["source"] == ref(p, "Leaf"))
               != world(p, domain_world(p, "two"))["declared_whole"] for v in values(target))


def test_no_match_is_semantic_and_does_not_mean_no_candidate_was_offered(public):
    q = query(public, "correspondence", target_world_id=domain_world(public, "three"))
    assert len(a.correspondence_candidates(public, q)) == 7
    assert values(c.derive_target(public, q)) == [{"status": "NO_MATCH", "pairs": []}]
    assert check(public, q, {"status": "NO_MATCH", "pairs": []})["correct"] is True


def test_analogy_accepts_every_matching_cross_domain_world_and_excludes_same_domain():
    f = family()
    p = public_for(f, family(("Box", "Bag", "Item"), domain="two"),
                   family(("Case", "Pouch", "Lid"), domain="three"),
                   family(("Same", "Middle", "Leaf"), domain="one"),
                   family(("Tree", "Left", "Right"), edges=[("Tree", "Left"), ("Tree", "Right")], domain="four"))
    q = query(p, "analogy")
    target = c.derive_target(p, q)
    assert {v["world_id"] for v in values(target)} == {domain_world(p, "two"), domain_world(p, "three")}
    assert target["coverage"]["worlds_checked"] == 5
    assert not check(p, q, {"world_id": None})["correct"]
    assert not check(p, q, {"world_id": p["focus_world_id"]})["correct"]
    assert not check(p, q, {"world_id": domain_world(p, "four")})["correct"]


def test_analogy_compares_full_graph_not_a_shared_two_edge_motif():
    lhs, rhs = ("Root", "A", "B", "C"), ("Box", "X", "Y", "Z")
    p = public_for(family(lhs, edges=[("Root", "A"), ("A", "B"), ("Root", "C")]),
                   family(rhs, domain="two"))
    q = query(p, "analogy")
    assert values(c.derive_target(p, q)) == [{"world_id": None}]


def test_full_training_bank_remains_64_and_all_nine_other_domain_chain2_matches_survive():
    families = s.training_families()
    p = s.public_source(s.compile_source(families[0], bank=s.freeze_bank(families)))
    before = deepcopy(p)
    q = query(p, "analogy")
    target = c.derive_target(p, q)
    assert len(p["bank"]["world_ids"]) == target["coverage"]["worlds_checked"] == 64
    assert len(values(target)) == 9
    assert {world(p, v["world_id"])["declarations"]["domain"] for v in values(target)} == {
        "grammatical", "procedural", "container"}
    assert p == before


@pytest.mark.parametrize("kind,large_focus", [("analogy", False), ("analogy", True), ("correspondence", False), ("correspondence", True)])
def test_large_graph_oracle_refuses_instead_of_silently_no_match(kind, large_focus):
    small = family()
    large = family(("NodeA", "NodeB", "NodeC", "NodeD", "NodeE"), domain="two")
    p = public_for(large, small) if large_focus else public_for(small, large)
    args = {"target_world_id": domain_world(p, "one" if large_focus else "two")} if kind == "correspondence" else {}
    with pytest.raises(c.SemanticCheckError, match="ISOMORPHISM_BOUND"):
        c.derive_target(p, query(p, kind, **args))


def test_analogy_checks_bound_before_same_domain_exclusion():
    p = public_for(family(), family(("NodeA", "NodeB", "NodeC", "NodeD", "NodeE")))
    with pytest.raises(c.SemanticCheckError, match="ISOMORPHISM_BOUND"):
        c.derive_target(p, query(p, "analogy"))


@pytest.mark.parametrize("rule,expected_label,path_labels", [
    ("first_direct_constituent_lexical_v1", "A", ["Whole", "A", "C", "Goal"]),
    ("bfs_immediate_predecessor_lexical_v1", "B", ["Whole", "B", "Goal"]),
])
def test_reach_rule_selects_declared_first_hop_or_bfs_predecessor(rule, expected_label, path_labels):
    f = family(("Whole", "A", "B", "C", "Goal"), edges=[
        ("Whole", "B"), ("B", "Goal"), ("Whole", "A"), ("A", "C"), ("C", "Goal")])
    p = public_for(f)
    q = a.compile_query(p, kind="reach", rule=rule, arguments={"whole": ref(p, "Whole"), "part": ref(p, "Goal")})
    target = c.derive_target(p, q)
    assert values(target) == [{"state": "VIA", "via": ref(p, expected_label)}]
    assert target["witnesses"][0]["evidence"]["path"] == [ref(p, label) for label in path_labels]


@pytest.mark.parametrize("rule", a.RULES["reach"])
def test_reach_direct_precedence_absence_and_lexical_ties(rule):
    f = family(("Whole", "A", "B", "Goal"), edges=[
        ("Whole", "B"), ("B", "Goal"), ("Whole", "A"), ("A", "Goal")])
    p = public_for(f)
    q = a.compile_query(p, kind="reach", rule=rule, arguments={"whole": ref(p, "Whole"), "part": ref(p, "Goal")})
    assert values(c.derive_target(p, q)) == [{"state": "VIA", "via": ref(p, "A")}]
    f["branches"] += ({"source": "Whole", "target": "Goal"},)
    p = public_for(f)
    q = a.compile_query(p, kind="reach", rule=rule, arguments={"whole": ref(p, "Whole"), "part": ref(p, "Goal")})
    assert values(c.derive_target(p, q)) == [{"state": "DIRECT", "via": None}]
    absent = a.compile_query(p, kind="reach", rule=rule, arguments={"whole": ref(p, "Goal"), "part": ref(p, "Whole")})
    target = c.derive_target(p, absent)
    assert values(target) == [{"state": "ABSENT", "via": None}]
    assert target["witnesses"][0]["evidence"]["reachable_nodes_including_start"] == [ref(p, "Goal")]


def test_malformed_prediction_refuses_before_semantics(public, monkeypatch):
    q = query(public, "parts", whole=ref(public, "Whole"))
    predicted = a.make_answer(public, q, {"nodes": []})
    predicted["value"]["nodes"] = ["foreign"]
    def forbidden(*args, **kwargs):
        raise AssertionError("SEMANTICS_CALLED_FOR_MALFORMED_PREDICTION")
    monkeypatch.setattr(c, "derive_target", forbidden)
    with pytest.raises(a.AnswerContractError):
        c.check_answer(public, q, predicted)


@pytest.mark.parametrize("mutation", ["answer", "witness", "coverage", "profile", "extra"])
def test_resealed_private_receipt_is_independently_rederived(public, mutation):
    q = query(public, "parts", whole=ref(public, "Whole"))
    target = c.derive_target(public, q)
    if mutation == "answer": target["admissible_answers"][0]["value"]["nodes"] = []
    if mutation == "witness": target["witnesses"][0]["evidence"]["direct_edges"] = []
    if mutation == "coverage": target["coverage"] = {"caller_says_correct": True}
    if mutation == "profile": target["checker_profile"]["max_isomorphism_nodes"] = True
    if mutation == "extra": target["private_override"] = True
    target["target_digest"] = c._digest({k: v for k, v in target.items() if k != "target_digest"})
    with pytest.raises(c.SemanticCheckError, match="TARGET_BINDING"):
        c.validate_target(public, q, target)


def test_stale_source_or_wrong_query_cannot_borrow_a_target(public):
    q = query(public, "parts", whole=ref(public, "Whole"))
    target = c.derive_target(public, q)
    other = query(public, "parts", whole=ref(public, "Part"))
    with pytest.raises(c.SemanticCheckError, match="TARGET_BINDING"):
        c.validate_target(public, other, target)
    changed = public_for(family(edges=[("Whole", "Tip"), ("Tip", "Part")]))
    with pytest.raises(a.AnswerContractError):
        c.derive_target(changed, q)


def test_outputs_do_not_alias_inputs_or_repeated_targets(public):
    q = query(public, "parts", whole=ref(public, "Whole"))
    target = c.derive_target(public, q)
    validated = c.validate_target(public, q, target)
    validated["admissible_answers"][0]["value"]["nodes"].clear()
    assert target == c.derive_target(public, q)
    checked = c.check_answer(public, q, target["admissible_answers"][0])
    checked["witnesses"][0]["evidence"].clear()
    assert target == c.derive_target(public, q)


def test_semantics_use_only_public_world_facts_not_source_constructors(public, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("SOURCE_OR_LEGACY_CONSTRUCTOR_USED")
    for name in ("training_families", "freeze_bank", "compile_source", "source_profile", "_material"):
        monkeypatch.setattr(s, name, forbidden)
    q = query(public, "analogy")
    target = c.derive_target(public, q)
    assert values(target) == [{"world_id": domain_world(public, "two")}]


@pytest.mark.parametrize("template,expected", [(1, [1]), (2, [2]), (3, [3]),
                                                (4, [4]), (5, [5]), (6, [5, 6])])
def test_roles_derive_only_from_focal_text_and_source(public, template, expected, monkeypatch):
    text = f.render_excerpt(public, template=template)
    q = query(public, "role_set", focal_excerpt=text)
    def forbidden(*args, **kwargs):
        raise AssertionError("RENDERER_USED_BY_PRIVATE_CHECKER")
    monkeypatch.setattr(f, "render_excerpt", forbidden)
    target = c.derive_target(public, q)
    status = "UNIQUE" if len(expected) == 1 else "AMBIGUOUS"
    assert values(target) == [{"roles": expected, "status": status}]
    assert c.validate_target(public, q, target) == target
    assert check(public, q, {"roles": expected, "status": status})["correct"]
    assert not check(public, q, {"roles": [1, 2, 3, 4, 5, 6], "status": "AMBIGUOUS"})["correct"]
    assert target["coverage"]["background_and_worked_supports_are_focal"] is False
    if template == 6:
        assert not check(public, q, {"roles": [6], "status": "UNIQUE"})["correct"]
        assert not check(public, q, {"roles": [5], "status": "UNIQUE"})["correct"]


def test_neutral_valid_focal_reference_is_insufficient_not_an_arbitrary_role(public):
    text = f.PREFIXES["reference"] + json.dumps({"world_id": public["focus_world_id"]},
                                               sort_keys=True, separators=(",", ":"))
    q = query(public, "role_set", focal_excerpt=text)
    assert values(c.derive_target(public, q)) == [{"roles": [], "status": "INSUFFICIENT"}]
    assert not check(public, q, {"roles": [1], "status": "UNIQUE"})["correct"]


def test_false_or_free_language_focal_content_never_produces_a_target(public):
    prefix = f.PREFIXES["account"]
    text = f.render_excerpt(public, template=6)
    payload = json.loads(text[len(prefix):])
    payload["edges"] = []
    false = prefix + json.dumps(payload, sort_keys=True, separators=(",", ":"))
    for text in (false, "This must be role six because the teacher says so."):
        q = query(public, "role_set", focal_excerpt=text)
        with pytest.raises(f.FocalContractError):
            c.derive_target(public, q)
