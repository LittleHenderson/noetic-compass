"""Adversarial public-only grammar checks; no teacher or numerical execution."""
from copy import deepcopy
import json

import pytest

from cas_meta2.typed_teaching import answers as a, source as s


def family(labels=("Whole", "Part", "Tip"), *, edges=None, domain="fixture"):
    edges = edges if edges is not None else [(labels[0], labels[1]), (labels[1], labels[2])]
    return {"family_id": "fixture:" + domain, "domain": domain, "archetype": "caller-declared",
            "rendering": 0, "kind": "declared kind", "labels": tuple(labels),
            "branches": tuple({"source": x, "target": y} for x, y in edges),
            "split": "training", "setting": "declared setting",
            "function": "declared function for " + labels[0]}


@pytest.fixture(scope="module")
def public():
    focus = family()
    other = family(("Box", "Bag", "Item"), domain="other")
    wrong = family(("Tree", "Left", "Right"),
                   edges=[("Tree", "Left"), ("Tree", "Right")], domain="wrong")
    return s.public_source(s.compile_source(focus, bank=s.freeze_bank([focus, other, wrong])))


def world(public, key=None):
    key = key or public["focus_world_id"]
    return next(w for w in public["worlds"] if w["world_id"] == key)


def node(public, label):
    return next(n["ref"] for n in world(public)["nodes"] if n["label"] == label)


def query(public, kind):
    args = {}
    rule = None
    if kind == "role_set":
        args = {"focal_excerpt": "Whole contains Part ; Part contains Tip"}
    if kind == "correspondence":
        args = {"target_world_id": next(w["world_id"] for w in public["worlds"]
                                       if w["declarations"]["domain"] == "other")}
    if kind == "parts":
        args = {"whole": node(public, "Whole")}
    if kind == "reach":
        args = {"whole": node(public, "Whole"), "part": node(public, "Tip")}
        rule = "first_direct_constituent_lexical_v1"
    return a.compile_query(public, kind=kind, rule=rule, arguments=args)


def payload(public, kind, q):
    wid = public["focus_world_id"]
    if kind == "role_set":
        return {"roles": [5, 6], "status": "AMBIGUOUS"}
    if kind == "definition":
        return {"whole": node(public, "Whole"),
                "kind_ref": a.declaration_ref(wid, "kind"),
                "function_ref": a.declaration_ref(wid, "function")}
    if kind == "context":
        return {"setting_ref": a.declaration_ref(wid, "setting"),
                "participants": sorted(n["ref"] for n in world(public)["nodes"])}
    if kind == "analogy":
        return {"world_id": q["arguments"].get("target_world_id", public["bank"]["world_ids"][0])}
    if kind == "correspondence":
        return a.correspondence_candidates(public, q)[1]
    if kind == "parts":
        return {"nodes": [node(public, "Part")]}
    if kind == "edge_account":
        return {"edges": sorted(({"source": e["source"], "target": e["target"]}
                                for e in world(public)["contains"]),
                               key=lambda e: (e["source"], e["target"]))}
    return {"state": "VIA", "via": node(public, "Part")}


@pytest.mark.parametrize("kind", list(a.RULES))
def test_typed_round_trip_for_all_declared_kinds(public, kind):
    q = query(public, kind)
    answer = a.make_answer(public, q, payload(public, kind, q))
    assert a.decode_answer(public, q, a.encode_answer(public, q, answer)) == answer
    assert a.answer_space(public, q)["semantic_correctness_checked"] is False
    assert a.validate_query(public, q) == q


@pytest.mark.parametrize("kind", list(a.RULES))
def test_answer_and_query_closed_fields_bind_source_kind_and_rule(public, kind):
    q = query(public, kind)
    answer = a.make_answer(public, q, payload(public, kind, q))
    for field, changed in (("schema", "old"), ("kind", "FACE_APPLY"), ("query_id", "other")):
        bad = deepcopy(answer)
        bad[field] = changed
        with pytest.raises(a.AnswerContractError):
            a.validate_answer(public, q, bad)
    for field in ("correct", "hidden_face", "negatives", "teacher"):
        bad = deepcopy(q)
        bad[field] = "private"
        with pytest.raises(a.AnswerContractError):
            a.validate_query(public, bad)
    bad = deepcopy(q)
    bad["source_digest"] = "a" * 64
    with pytest.raises(a.AnswerContractError):
        a.validate_query(public, bad)


def test_role_universe_does_not_depend_on_selected_subset_or_external_facts(public):
    q = query(public, "role_set")
    assert a.answer_space(public, q)["inventory"]["role_ids"] == [1, 2, 3, 4, 5, 6]
    for roles in ([], [1], [5], [6], [5, 6], [1, 2, 3, 4, 5, 6]):
        status = "INSUFFICIENT" if not roles else "UNIQUE" if len(roles) == 1 else "AMBIGUOUS"
        a.make_answer(public, q, {"roles": roles, "status": status})
    with pytest.raises(a.AnswerContractError):
        a.make_answer(public, q, {"roles": [5, 6], "status": "UNIQUE"})
    with pytest.raises(a.AnswerContractError):
        a.make_answer(public, q, {"roles": [True], "status": "UNIQUE"})


def test_analogy_entire_bank_including_wrong_shape_focus_and_no_match(public):
    q = query(public, "analogy")
    inv = a.answer_space(public, q)["inventory"]
    assert inv["world_ids"] == public["bank"]["world_ids"]
    assert public["focus_world_id"] in inv["world_ids"]
    for wid in inv["world_ids"] + [None]:
        a.make_answer(public, q, {"world_id": wid})


def test_declarations_include_wrong_worlds_and_no_singleton_truth_mask(public):
    q = query(public, "definition")
    inv = a.answer_space(public, q)["inventory"]
    assert len(inv["kind_refs"]) == len(inv["function_refs"]) == len(public["worlds"])
    for w in public["worlds"]:
        a.make_answer(public, q, {"whole": node(public, "Tip"),
            "kind_ref": a.declaration_ref(w["world_id"], "kind"),
            "function_ref": a.declaration_ref(w["world_id"], "function")})
    q = query(public, "context")
    for w in public["worlds"]:
        a.make_answer(public, q, {"setting_ref": a.declaration_ref(w["world_id"], "setting"),
                                 "participants": []})


def test_incorrect_well_formed_graph_answers_pass_syntax(public):
    q = query(public, "parts")
    a.make_answer(public, q, {"nodes": []})
    a.make_answer(public, q, {"nodes": [node(public, "Tip")]})  # Indirect, not direct.
    a.make_answer(public, q, {"nodes": [node(public, "Whole")]})
    q = query(public, "edge_account")
    inv = a.answer_space(public, q)["inventory"]
    assert len(inv["edge_pairs"]) == 9  # All pairs, not just two declared edges.
    a.make_answer(public, q, {"edges": []})
    a.make_answer(public, q, {"edges": [{"source": node(public, "Tip"),
                                       "target": node(public, "Whole")}]})
    a.make_answer(public, q, {"edges": [{"source": node(public, "Tip"),
                                       "target": node(public, "Tip")}]})
    q = query(public, "reach")
    for state in ("ABSENT", "DIRECT"):
        a.make_answer(public, q, {"state": state, "via": None})
    for n in world(public)["nodes"]:
        a.make_answer(public, q, {"state": "VIA", "via": n["ref"]})


def test_mapping_candidates_are_all_syntax_not_only_isomorphisms(public):
    q = query(public, "correspondence")
    candidates = a.correspondence_candidates(public, q)
    assert len(candidates) == 7
    assert candidates[0] == {"status": "NO_MATCH", "pairs": []}
    for candidate in candidates:
        a.make_answer(public, q, candidate)
    source_edges = {(e["source"], e["target"]) for e in world(public)["contains"]}
    target_edges = {(e["source"], e["target"]) for e in world(public, q["arguments"]["target_world_id"])["contains"]}
    valid = []
    for candidate in candidates[1:]:
        mapping = {p["source"]: p["target"] for p in candidate["pairs"]}
        valid.append({(mapping[x], mapping[y]) for x, y in source_edges} == target_edges)
    assert sum(valid) == 1 and sum(not v for v in valid) == 5


@pytest.mark.parametrize("edges,expected", [
    ([(0, 1), (0, 2), (0, 3)], 6),
    ([(0, 1), (0, 2), (1, 3), (2, 3)], 2),
])
def test_symmetric_graphs_do_not_prune_valid_or_invalid_mapping_candidates(edges, expected):
    left, right = ("Root", "First", "Second", "Third"), ("Box", "Cloth", "Rope", "Strand")
    f = family(left, edges=[(left[x], left[y]) for x, y in edges])
    g = family(right, edges=[(right[x], right[y]) for x, y in edges], domain="other")
    p = s.public_source(s.compile_source(f, bank=s.freeze_bank([f, g])))
    target = next(w["world_id"] for w in p["worlds"] if w["world_id"] != p["focus_world_id"])
    q = a.compile_query(p, kind="correspondence", arguments={"target_world_id": target})
    candidates = a.correspondence_candidates(p, q)
    assert len(candidates) == 25
    target_edges = {(e["source"], e["target"]) for e in world(p, target)["contains"]}
    matches = 0
    for row in candidates[1:]:
        a.make_answer(p, q, row)
        m = {v["source"]: v["target"] for v in row["pairs"]}
        matches += {(m[e["source"]], m[e["target"]]) for e in world(p)["contains"]} == target_edges
    assert matches == expected


def test_public_ten_node_syntax_does_not_admit_factorial_execution():
    labels = tuple("Node" + chr(65 + i) for i in range(10))
    f = family(labels, edges=list(zip(labels, labels[1:])))
    p = s.public_source(s.compile_source(f, bank=s.freeze_bank([f])))
    q = a.compile_query(p, kind="correspondence", arguments={"target_world_id": p["focus_world_id"]})
    nodes = sorted(n["ref"] for n in world(p)["nodes"])
    a.make_answer(p, q, {"status": "MAPPING", "pairs": [{"source": n, "target": n} for n in nodes]})
    with pytest.raises(a.AnswerContractError, match="PERMUTATION_BOUND"):
        a.correspondence_candidates(p, q)
    with pytest.raises(a.AnswerContractError, match="PERMUTATION_LIMIT"):
        a.correspondence_candidates(p, q, max_nodes=10)
    q = a.compile_query(p, kind="edge_account")
    assert len(a.answer_space(p, q)["inventory"]["edge_pairs"]) == 100


def test_reach_variants_are_distinct_and_require_a_declared_rule(public):
    args = {"whole": node(public, "Whole"), "part": node(public, "Tip")}
    with pytest.raises(a.AnswerContractError, match="EXPLICIT_REACH"):
        a.compile_query(public, kind="reach", arguments=args)
    queries = [a.compile_query(public, kind="reach", rule=rule, arguments=args)
               for rule in a.RULES["reach"]]
    assert queries[0]["query_id"] != queries[1]["query_id"]
    # Same syntax, separately identified meanings. No semantic checker is run.
    assert a.answer_space(public, queries[0])["inventory"] == a.answer_space(public, queries[1])["inventory"]


def test_no_temporal_order_claim_from_static_contains(public):
    assert world(public)["branch_order"]["process_order"] is None
    with pytest.raises(a.AnswerContractError, match="TYPED_RULE"):
        a.compile_query(public, kind="edge_account", rule="declared_process_order_v1")
    assert "NOT_PROCESS" in a.answer_space(public, query(public, "edge_account"))["inventory"]["order"]


@pytest.mark.parametrize("bad_nodes", [
    lambda refs: [refs[0], refs[0]],
    lambda refs: list(reversed(refs)),
    lambda refs: ["unknown"],
    lambda refs: [True],
])
def test_no_silent_set_repair(public, bad_nodes):
    refs = sorted(n["ref"] for n in world(public)["nodes"])
    with pytest.raises(a.AnswerContractError):
        a.make_answer(public, query(public, "parts"), {"nodes": bad_nodes(refs)})


def test_scoped_reference_cannot_be_mixed_between_worlds(public):
    foreign = next(w["nodes"][0]["ref"] for w in public["worlds"]
                   if w["world_id"] != public["focus_world_id"])
    with pytest.raises(a.AnswerContractError):
        a.make_answer(public, query(public, "parts"), {"nodes": [foreign]})
    with pytest.raises(a.AnswerContractError):
        a.compile_query(public, kind="parts", arguments={"whole": foreign})


def test_canonical_wire_rejects_duplicates_whitespace_unknown_fields_and_wrong_bytes(public):
    q = query(public, "parts")
    answer = a.make_answer(public, q, {"nodes": []})
    raw = a.encode_answer(public, q, answer)
    cases = [raw + b"\n", b"\xff", raw.replace(b'"schema":', b'"schema":"duplicate","schema":'),
             json.dumps({**answer, "teacher": "hidden"}).encode(), b"{}", raw.decode()]
    for bad in cases:
        with pytest.raises(a.AnswerContractError):
            a.decode_answer(public, q, bad)


def test_returned_values_do_not_alias_public_or_payload(public):
    q = query(public, "parts")
    values = {"nodes": [node(public, "Part")]}
    answer = a.make_answer(public, q, values)
    values["nodes"].clear()
    assert answer["value"]["nodes"] == [node(public, "Part")]
    validated = a.validate_answer(public, q, answer)
    validated["value"]["nodes"].clear()
    assert answer["value"]["nodes"] == [node(public, "Part")]


def test_focal_excerpt_is_explicit_and_public(public):
    with pytest.raises(a.AnswerContractError):
        a.compile_query(public, kind="role_set")
    with pytest.raises(a.AnswerContractError):
        a.compile_query(public, kind="role_set", arguments={"focal_excerpt": " ", "face": 6})
    q = query(public, "role_set")
    changed = a.compile_query(public, kind="role_set", arguments={"focal_excerpt": "A definition."})
    assert q["query_id"] != changed["query_id"]
    assert a.answer_space(public, q)["inventory"] == a.answer_space(public, changed)["inventory"]


def test_malformed_text_and_self_reach_refused_with_contract_error(public):
    with pytest.raises(a.AnswerContractError, match="ENCODING"):
        a.compile_query(public, kind="role_set", arguments={"focal_excerpt": chr(0xD800)})
    with pytest.raises(a.AnswerContractError, match="DISTINCT_NODES"):
        a.compile_query(public, kind="reach", rule=a.RULES["reach"][0],
                        arguments={"whole": node(public, "Whole"), "part": node(public, "Whole")})
