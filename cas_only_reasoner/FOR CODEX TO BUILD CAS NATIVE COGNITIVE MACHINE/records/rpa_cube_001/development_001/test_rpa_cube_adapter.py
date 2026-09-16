"""Draft conformance tests; kept out of the active compound checkpoint suite."""
from collections import deque
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import subprocess
import sys

import pytest

from cncm import rpa_cube_adapter as bridge
from cncm.canonical import canonical_json, digest
from cncm.model import ContractError
from cncm.rpa_model import AtlasSnapshot, LinkType, NodeStatus

cube_node, cube_profile = bridge.cube_node, bridge.cube_profile
EXPECTED_BUNDLE = "b3df2633ec6a49c6ad81d1572334ac00bcd123d09672d7a53a05979fc70b2c16"
DENIED = {"torch", "numpy", "boto3", "botocore", "requests", "cas_cjt"}
ROOT = Path(bridge.__file__).resolve().parents[1]


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED:
            raise AssertionError("PROHIBITED_IMPORT:" + fullname)


@pytest.fixture(autouse=True)
def deny_neural_provider_imports():
    finder = Deny()
    sys.meta_path.insert(0, finder)
    yield
    sys.meta_path.remove(finder)


def source(bundle, namespace="authored_fixture", version=1, raw=None):
    raw = canonical_json(bundle).encode() if raw is None else raw
    return bridge.cube_source_receipt(raw, expected_file_sha256=sha256(raw).hexdigest(),
        expected_bundle_digest=cube_node.bundle_digest(bundle), source_namespace=namespace,
        observation_id="explicit_observation", observation_time="2026-09-16 supplied fixture inspection",
        record_version=version)


def project(bundle, namespace="authored_fixture", view="view_context", version=1):
    receipt = source(bundle, namespace, version)
    return bridge.cube_atlas_from_bundle(bundle, expected_bundle_digest=receipt.canonical_bundle_digest,
                                         source_receipt=receipt, view_id=view)


@pytest.fixture(scope="module")
def bundle():
    value = cube_node.load_bundle()
    assert cube_node.bundle_digest(value) == EXPECTED_BUNDLE
    return value


@pytest.fixture(scope="module")
def document(bundle):
    return project(bundle)


def lesson(document, bundle, case=None, assistance="unassisted", **kwargs):
    case = case or cube_node.answer_cases(bundle, document.to_dict()["view_id"])["cases"][0]
    return bridge.compile_atlas_lesson(document, bundle=bundle,
        expected_bundle_digest=cube_node.bundle_digest(bundle), operation=case["op"],
        question=case["question"], assistance=assistance, **kwargs)


def test_all_source_records_and_faces_resolve(bundle, document):
    wire = document.to_dict()
    assert wire["catalog"]["bundle"] == bundle
    assert len(document.atlas.nodes) == 43
    assert len(document.atlas.links) == 47
    assert len(wire["catalog"]["cube_index"]) == 6
    assert len(bundle["views"]) == 3 and len(bundle["mappings"]) == 1
    seen_faces = set()
    for node in document.atlas.nodes:
        fields = dict(node.fields)
        if "catalog_key" not in fields:
            continue
        row = wire["catalog"]["cube_index"][fields["catalog_key"]]
        cube = bundle["cube_nodes"][row["source_path"][1]]
        assert row["record_digest"] == digest(cube)
        if "face_path" in fields:
            face_key = fields["face_path"].split(".")[1]
            assert fields["availability"] == cube["faces"][face_key]["availability"]
            assert cube["faces"][face_key]["provenance_refs"]
            seen_faces.add((cube["node_id"], face_key))
    assert len(seen_faces) == 36
    branches = [row for row in document.atlas.links if row.projection.startswith("source_contains_branch:")]
    assert {row.projection.split(":", 1)[1] for row in branches} == {row["branch_id"] for row in bundle["branches"]}
    assert all(row.relation is LinkType.CONTAINS_PART for row in document.atlas.links)


def test_source_bytes_file_and_canonical_identity(bundle):
    raw = cube_node.pinned_bundle_path().read_bytes()
    receipt = source(bundle, raw=raw)
    assert receipt.source_file_sha256 != receipt.canonical_bundle_digest
    doc = bridge.cube_atlas_from_bytes(raw, expected_file_sha256=sha256(raw).hexdigest(),
        expected_bundle_digest=EXPECTED_BUNDLE, source_namespace="authored_fixture",
        observation_id="explicit_observation", observation_time="supplied time", record_version=1)
    assert doc.catalog["bundle"] == bundle
    for kwargs in ({"source_file_sha256": "0" * 64}, {"canonical_bundle_digest": "0" * 64},
                   {"source_namespace": "bad namespace"}, {"source_bytes": raw + b" invalid"}):
        with pytest.raises(ContractError):
            replace(receipt, **kwargs)
    with pytest.raises(ContractError, match="typed source"):
        bridge.cube_atlas_from_bundle(bundle, expected_bundle_digest=EXPECTED_BUNDLE, source_receipt=receipt.to_dict())
    with pytest.raises(ContractError, match="digest mismatch"):
        bridge.cube_atlas_from_bundle(bundle, expected_bundle_digest="0" * 64, source_receipt=receipt)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff', b"[]", b"{}"])
def test_malformed_json_refused(raw):
    with pytest.raises(ContractError):
        bridge.cube_source_receipt(raw, expected_file_sha256=sha256(raw).hexdigest(),
            expected_bundle_digest="0" * 64, source_namespace="fixture", observation_id="explicit",
            observation_time="supplied", record_version=1)


def test_all_306_compilations_match_reference(bundle):
    counts = {}
    for view in ("view_formal", "view_context", "view_analogy"):
        document = project(bundle, view=view)
        cases = cube_node.answer_cases(bundle, view)["cases"]
        assert len(cases) == 51
        count = 0
        for case in cases:
            for assistance in ("guided", "unassisted"):
                before = document.to_dict()
                actual = lesson(document, bundle, case, assistance)
                existing = cube_profile.compile_lesson(bundle, case, assistance=assistance, view_id=view)
                learner = actual["learner_input"]
                teacher = actual["teacher_sidecar"]
                assert set(learner) == {"record_id", "public", "encoded_options"}
                assert learner["public"] == existing["encoding"]["public"]
                assert learner["encoded_options"] == existing["encoding"]["encoded_options"]
                assert teacher["expected_answer"] == case["correct"]
                assert teacher["encoded_correct_index"] == existing["encoding"]["encoded_correct_index"]
                assert teacher["visibility"] == existing["visibility"]
                assert teacher["answer_status"] == "GRAPH_DERIVED_TEACHER_REFERENCE_NOT_LEARNER_PREDICTION"
                assert actual["binding"]["compiler_calls"] == 1
                for key in ("neural_calls", "optimizer_updates", "delivered_neural_lessons"):
                    assert actual["binding"][key] == 0
                assert actual["binding"]["competence_established"] is False
                assert actual["binding"]["cache_identity_bound"] is False
                assert document.to_dict() == before
                assert all(row.relation is not LinkType.REACHABLE_VIA for row in document.atlas.links)
                count += 1
        counts[view] = count
    assert counts == {"view_formal": 102, "view_context": 102, "view_analogy": 102}


def test_legacy_target_free_failure_is_preserved(bundle):
    case = cube_node.answer_cases(bundle)["cases"][0]
    with pytest.raises(KeyError, match="correct"):
        cube_profile.compile_public_exercise(bundle, cube_profile.public_case(case), assistance="guided")


def test_target_mutation_and_deletion_cannot_steer_input(bundle, document):
    actual = lesson(document, bundle)
    original = deepcopy(actual["learner_input"])
    for mode in ("replace", "delete", "mutate"):
        changed = deepcopy(actual)
        if mode == "replace":
            changed["teacher_sidecar"] = {"expected_answer": "invented"}
        elif mode == "delete":
            del changed["teacher_sidecar"]
        else:
            changed["teacher_sidecar"]["expected_answer"] = ["invented"]
        assert changed["learner_input"] == original
        assert lesson(document, bundle)["learner_input"] == original
    with pytest.raises(ContractError, match="disagrees"):
        bridge.check_teacher_target(actual, "invented")
    agreement = bridge.check_teacher_target(actual, actual["teacher_sidecar"]["expected_answer"])
    assert agreement["agrees"]
    assert agreement["scope"] == "SUPPLIED_EXPORT_LOCAL_CONSISTENCY_ONLY"
    assert agreement["source_reconstructed"] is False
    assert agreement["source_authenticity_established"] is False
    with pytest.raises(TypeError):
        bridge.compile_atlas_lesson(document, bundle=bundle, expected_bundle_digest=EXPECTED_BUNDLE,
            operation="LIST_PARTS", question={"idea": "Bicycle"}, assistance="guided", correct="invented")
    with pytest.raises(ContractError, match="question fields"):
        bridge.compile_atlas_lesson(document, bundle=bundle, expected_bundle_digest=EXPECTED_BUNDLE,
            operation="LIST_PARTS", question={"idea": "Bicycle", "correct": "invented"}, assistance="guided")


def test_witness_routes_are_real_contains_chains(bundle, document):
    branches = {row["branch_id"]: row for row in bundle["branches"]}
    by_label = {v: k for k, v in cube_node.view_labels(bundle, "view_context").items()}
    for case in cube_node.answer_cases(bundle)["cases"]:
        if case["op"] != "REACHED_VIA":
            continue
        teacher = lesson(document, bundle, case)["teacher_sidecar"]
        assert set(teacher["reference_branch_ids"]) <= set(branches)
        if case["correct"] == "absent":
            assert teacher["reference_paths"] == []
        else:
            assert len(teacher["reference_paths"]) == 1
            chain = teacher["reference_paths"][0]
            position = by_label[case["question"]["idea"]]
            for branch_id in chain:
                assert branches[branch_id]["source_node_id"] == position
                position = branches[branch_id]["target_node_id"]
            assert position == by_label[case["question"]["part"]]
            if case["correct"].startswith("via:"):
                assert branches[chain[0]]["target_node_id"] == by_label[case["correct"][4:]]
    for op in ("Why", "How", "reachable_via", "contains"):
        with pytest.raises(ContractError, match="unsupported scored operation"):
            bridge.compile_atlas_lesson(document, bundle=bundle, expected_bundle_digest=EXPECTED_BUNDLE,
                operation=op, question={}, assistance="guided")


def test_public_input_identity_closes_legacy_cache_hole(bundle, document):
    # Rename only a branch ID and all its references: same family/question/options,
    # but the compiler's ordered problem string changes. Legacy task ID is stale.
    def rename(value):
        if type(value) is dict:
            return {key: rename(item) for key, item in value.items()}
        if type(value) is list:
            return [rename(item) for item in value]
        return "zz_branch_01" if value == "branch_01" else value
    moved = rename(bundle)
    changed = project(moved)
    case = cube_node.answer_cases(bundle)["cases"][0]
    first, second = lesson(document, bundle, case), lesson(changed, moved, case)
    legacy_a = cube_profile.compile_lesson(bundle, case, assistance="unassisted")
    legacy_b = cube_profile.compile_lesson(moved, case, assistance="unassisted")
    assert legacy_a["task_id"] == legacy_b["task_id"]
    assert first["learner_input"]["public"] != second["learner_input"]["public"]
    assert first["learner_input"]["encoded_options"] == second["learner_input"]["encoded_options"]
    assert first["learner_input"]["record_id"] != second["learner_input"]["record_id"]
    assert first["binding"]["semantic_question_id"] == second["binding"]["semantic_question_id"]
    with pytest.raises(ContractError):
        lesson(document, moved, case)


def test_explicit_encoded_cache_context_binds_identity(bundle, document):
    context = {"model_checkpoint_digest": "1" * 64, "tokenizer_digest": "2" * 64, "encoder_digest": "3" * 64}
    first = lesson(document, bundle, encoding_context=context)
    assert first["binding"]["cache_identity_bound"] is True
    for key in context:
        changed = {**context, key: "4" * 64}
        assert lesson(document, bundle, encoding_context=changed)["learner_input"]["record_id"] != first["learner_input"]["record_id"]
    with pytest.raises(ContractError):
        lesson(document, bundle, encoding_context={**context, "target": 1})


def test_canonical_ids_survive_rename_but_context_and_revision_do_not_collapse(bundle, document):
    moved = cube_node.rename_bundle(bundle, {"Bicycle": "Carrier", "Wheel": "Roller"})
    renamed = project(moved)
    keys = lambda doc: {row["cube_node_id"]: row["idea_id"] for row in doc.catalog["cube_index"].values()}
    assert keys(document) == keys(renamed)
    assert document.atlas.current_state_id != renamed.atlas.current_state_id
    assert keys(project(bundle, namespace="another_source")) != keys(document)
    assert bridge.canonical_cube_id("authored_fixture", "other_context", "node_001") != keys(document)["node_001"]
    revised = deepcopy(bundle)
    revised["cube_nodes"][0]["revision"] += 1
    newer = project(revised, version=2)
    assert keys(newer) == keys(document)
    assert set(newer.catalog["cube_index"]) != set(document.catalog["cube_index"])
    assert {n.view_key for n in newer.atlas.nodes} != {n.view_key for n in document.atlas.nodes}
    original = lesson(document, bundle, {"op": "LIST_PARTS", "question": {"idea": "Bicycle"}})
    renamed_lesson = lesson(renamed, moved, {"op": "LIST_PARTS", "question": {"idea": "Carrier"}})
    assert original["binding"]["semantic_question_id"] == renamed_lesson["binding"]["semantic_question_id"]
    assert renamed_lesson["teacher_sidecar"]["expected_answer"] == ["Frame", "Roller"]


def test_reorder_preserves_answers_and_rewire_changes_them(bundle, document):
    reordered = cube_node.reorder_bundle(bundle)
    reordered_document = project(reordered)
    case = {"op": "LIST_PARTS", "question": {"idea": "Cart"}}
    assert lesson(document, bundle, case)["teacher_sidecar"]["expected_answer"] == lesson(reordered_document, reordered, case)["teacher_sidecar"]["expected_answer"]
    rewired = cube_node.rewire_bundle(bundle, branch_id="branch_04", new_source="node_004", new_target="node_003")
    rewired_document = project(rewired)
    assert lesson(document, bundle, case)["teacher_sidecar"]["expected_answer"] != lesson(rewired_document, rewired, case)["teacher_sidecar"]["expected_answer"]
    with pytest.raises(ContractError, match="AMBIGUOUS"):
        lesson(rewired_document, rewired, {"op": "FIND_SHARED_PART", "question": {"a": "Bicycle", "b": "Cart"}})


@pytest.mark.parametrize("mutation", ["predicate", "context", "duplicate", "dangling", "cycle", "stale_face", "stale_mapping", "face_mapping", "face_view", "top_target"])
def test_invalid_source_graphs_fail_closed(bundle, mutation):
    bad = deepcopy(bundle)
    if mutation == "predicate":
        bad["branches"][0]["predicate"] = "triggers"
        bad["relation_profiles"] = {"stored_predicates": ["contains", "triggers"]}
    elif mutation == "context":
        bad["cube_nodes"][0]["context_id"] = "elsewhere"
    elif mutation == "duplicate":
        bad["cube_nodes"].append(deepcopy(bad["cube_nodes"][0]))
    elif mutation == "dangling":
        bad["branches"][0]["target_node_id"] = "missing"
    elif mutation == "cycle":
        bad = cube_node.rewire_bundle(bad, branch_id="branch_05", new_source="node_002", new_target="node_001", rebuild=False)
    elif mutation == "stale_face":
        bad["cube_nodes"][0]["faces"]["face_5"]["structured"]["direct_branch_refs"] = []
    elif mutation == "stale_mapping":
        bad["views"][0]["node_labels"]["node_001"] = "Changed"
    elif mutation == "face_mapping":
        bad["cube_nodes"][0]["faces"]["face_4"]["structured"]["mapping_refs"] = ["missing"]
    elif mutation == "face_view":
        bad["cube_nodes"][0]["faces"]["face_2"]["structured"]["view_refs"] = ["missing"]
    else:
        bad["private_target"] = "answer"
    with pytest.raises(ContractError):
        project(bad)


def test_incomplete_inventory_cannot_license_absence(bundle):
    partial = deepcopy(bundle)
    partial["context"]["contains_inventory_complete"] = False
    for cube in partial["cube_nodes"]:
        cube["faces"]["face_5"]["structured"]["completeness"] = "partial"
    doc = project(partial)
    assert doc.catalog["bundle"]["context"]["contains_inventory_complete"] is False
    for case in ({"op": "LIST_PARTS", "question": {"idea": "Frame"}},
                 {"op": "REACHED_VIA", "question": {"idea": "Frame", "part": "Rim"}},
                 {"op": "FIND_SHARED_PART", "question": {"a": "Frame", "b": "Platform"}}):
        with pytest.raises(ContractError, match="complete inventory"):
            lesson(doc, partial, case)


@pytest.mark.parametrize("kind", ["subset", "duplicate"])
def test_partial_presentation_is_refused_instead_of_widened(bundle, kind):
    changed = deepcopy(bundle)
    refs = changed["views"][0]["branch_refs"]
    if kind == "subset":
        refs.pop()
    else:
        refs.append(refs[0])
    # This remains legal authoring data in the frozen source schema, but its
    # compiler ignores view selection. The new bridge cannot silently widen it.
    cube_node.validate_bundle(changed)
    with pytest.raises(ContractError, match="complete view coverage"):
        project(changed)


def test_unknown_not_applicable_and_empty_stay_distinct(bundle):
    changed = deepcopy(bundle)
    changed["cube_nodes"][0]["faces"]["face_1"].update(availability="unknown", structured={})
    changed["cube_nodes"][0]["faces"]["face_3"].update(availability="not_applicable", structured={})
    document = project(changed)
    inventory = {dict(node.fields).get("availability"): node for node in document.atlas.nodes
                 if dict(node.fields).get("availability") in ("unknown", "not_applicable")}
    assert inventory["unknown"].status is NodeStatus.UNKNOWN
    assert inventory["not_applicable"].status is NodeStatus.OBSERVED
    assert document.catalog["bundle"] == changed
    # The empty direct inventory of a leaf is present and complete, unlike an
    # unknown face. The author explicitly declared the source graph complete.
    empty = lesson(document, changed, {"op": "LIST_PARTS", "question": {"idea": "Frame"}})
    assert empty["teacher_sidecar"]["expected_answer"] == []


def test_focus_hypothesis_and_copies_preserve_actual_source(bundle, document):
    before, expected = document.to_dict(), lesson(document, bundle)["learner_input"]
    for node in document.atlas.nodes:
        focused = document.focus(node.node_id)
        assert focused.atlas.current_state_id == document.atlas.current_state_id
        assert lesson(focused, bundle)["learner_input"] == expected
    rewired = cube_node.rewire_bundle(bundle, branch_id="branch_04", new_source="node_004", new_target="node_003")
    hypothesis = document.with_hypothesis(project(rewired))
    assert hypothesis.atlas.current_state_id == document.atlas.current_state_id
    assert hypothesis.atlas.node_map()[hypothesis.atlas.hypothesis_branch_id].status is NodeStatus.HYPOTHETICAL
    assert hypothesis.atlas.focus_node_id == hypothesis.atlas.hypothesis_branch_id
    assert lesson(hypothesis, bundle)["learner_input"] == expected
    assert document.to_dict() == before
    export = document.to_dict()
    export["catalog"]["bundle"]["cube_nodes"][0]["core"]["label"] = "mutated"
    catalog = document.catalog
    catalog["bundle"]["sources"].clear()
    compiled = lesson(document, bundle)
    compiled["teacher_sidecar"]["question"]["idea"] = "mutated"
    compiled["learner_input"]["public"]["observations"][0]["values"][0] = 99
    assert document.to_dict() == before
    assert lesson(document, bundle)["learner_input"] == expected
    restored = bridge.load_cube_atlas_document(hypothesis.to_dict(), source_receipts=hypothesis._receipts)
    assert restored.to_dict() == hypothesis.to_dict()


def test_source_and_projection_corruption_fail_closed(bundle, document):
    for field in ("catalog", "source_receipt", "atlas", "scope"):
        wire = document.to_dict()
        if field == "catalog":
            next(iter(wire["catalog"]["cube_index"].values()))["record_digest"] = "0" * 64
        elif field == "source_receipt":
            wire[field]["source_namespace"] = "forged"
        elif field == "atlas":
            wire[field]["nodes"][0]["label"] = "forged"
        else:
            wire[field] = "WORLD_TRUTH"
        with pytest.raises(ContractError):
            bridge.load_cube_atlas_document(wire, source_receipts=document._receipts)
        forged = bridge.CubeAtlasDocument(canonical_json(wire), document._receipts)
        with pytest.raises(ContractError):
            lesson(forged, bundle)


def test_catalog_paging_is_exact_digest_bound_and_deferred(document):
    seen = []
    page = bridge.catalog_page(document, limit=2)
    assert (page["offset"], page["stop"], page["total"], page["deferred"]) == (0, 2, 6, 4)
    first = deepcopy(page)
    while True:
        seen.extend(row["catalog_key"] for row in page["rows"])
        if page["next_cursor"] is None:
            break
        page = bridge.catalog_page(document, limit=2, cursor=page["next_cursor"])
    assert seen == sorted(document.catalog["cube_index"])
    for field, value in (("anchor", "0" * 64), ("next_offset", 4), ("limit", 3)):
        cursor = deepcopy(first["next_cursor"])
        cursor[field] = value
        with pytest.raises(ContractError):
            bridge.catalog_page(document, limit=2, cursor=cursor)
    focused = document.focus(document.atlas.nodes[-1].node_id)
    assert bridge.catalog_page(focused, limit=2, cursor=first["next_cursor"])["offset"] == 2
    for kwargs in ({"limit": 21}, {"limit": True}, {"offset": -1}, {"offset": 7}):
        with pytest.raises(ContractError):
            bridge.catalog_page(document, **kwargs)


def _ordinary_bfs(atlas, root, max_depth, max_nodes):
    nodes = {node.node_id: node for node in atlas.nodes}
    adjacency = {key: [] for key in nodes}
    for link in sorted(atlas.links, key=lambda row: row.link_id):
        adjacency[link.source_id].append(link)
    queue, visited, seen = deque([(root, 0)]), [root], {nodes[root].view_key}
    traversed, revisited, deferred = [], [], []
    while queue:
        node, depth = queue.popleft()
        for link in adjacency[node]:
            if nodes[link.target_id].view_key in seen:
                traversed.append(link.link_id)
                revisited.append(link.link_id)
            elif depth >= max_depth:
                deferred.append((node, link.link_id, link.target_id, "max_depth"))
            elif len(visited) >= max_nodes:
                deferred.append((node, link.link_id, link.target_id, "max_nodes"))
            else:
                seen.add(nodes[link.target_id].view_key)
                visited.append(link.target_id)
                traversed.append(link.link_id)
                queue.append((link.target_id, depth + 1))
    return visited, traversed, revisited, deferred


def test_identical_ordinary_graph_bfs_budgets_revisits_deferred(document):
    atlas = document.atlas
    assert atlas.flat_graph() == atlas.to_dict()
    for root in (atlas.current_state_id, *[row["atlas_node_id"] for row in document.catalog["cube_index"].values()]):
        for depth in (0, 1, 2, 4, 32):
            for budget in (1, 3, 7, 43):
                ordinary = _ordinary_bfs(atlas, root, depth, budget)
                actual = atlas.expand(root_id=root, max_depth=depth, max_nodes=budget, relations=(LinkType.CONTAINS_PART,))
                assert list(actual.visited_node_ids) == ordinary[0]
                assert list(actual.traversed_link_ids) == ordinary[1]
                assert list(actual.revisited_link_ids) == ordinary[2]
                assert [(row.source_id, row.link_id, row.target_id, row.reason) for row in actual.deferred] == ordinary[3]


def test_bounds_reject_before_unbounded_processing(bundle, document, monkeypatch):
    monkeypatch.setattr(bridge, "MAX_SOURCE_BYTES", 50)
    with pytest.raises(ContractError, match="bound"):
        project(bundle)
    monkeypatch.undo()
    monkeypatch.setattr(bridge, "MAX_CATALOG_BYTES", 50)
    with pytest.raises(ContractError, match="bound"):
        project(bundle)
    monkeypatch.undo()
    monkeypatch.setattr(bridge, "MAX_DOCUMENT_BYTES", 50)
    with pytest.raises(ContractError, match="bound"):
        project(bundle)
    monkeypatch.undo()
    monkeypatch.setattr(bridge, "MAX_LESSON_BYTES", 50)
    with pytest.raises(ContractError, match="bound"):
        lesson(document, bundle)
    monkeypatch.undo()
    oversized = deepcopy(bundle)
    oversized["cube_nodes"] *= 11
    with pytest.raises(ContractError, match="count bound"):
        project(oversized)
    cycle = {}
    cycle["cycle"] = cycle
    with pytest.raises(ContractError, match="cycle"):
        bridge._bounded(cycle, 1000, "probe")


def test_no_world_truth_or_learner_competence_claim(bundle, document):
    assert document.to_dict()["scope"] == bridge.SCOPE
    assert document.to_dict()["source_receipt"]["world_truth_established"] is False
    assert document.to_dict()["source_receipt"]["authorship_authenticated"] is False
    assert all(node.status is not NodeStatus.VERIFIED for node in document.atlas.nodes)
    actual = lesson(document, bundle)
    assert actual["binding"]["competence_established"] is False
    assert actual["teacher_sidecar"]["how_status"] == "UNSUPPORTED_NO_ACTION_CONTRACT"


def test_fresh_process_denies_model_tensor_provider_imports():
    code = '''
import sys, importlib.abc, json
class Deny(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'torch','numpy','boto3','botocore','requests','cas_cjt'}:
   raise AssertionError('PROHIBITED_IMPORT:'+fullname)
sys.meta_path.insert(0,Deny())
from cncm import rpa_cube_adapter as a
raw=a.cube_node.pinned_bundle_path().read_bytes(); b=a.cube_node.load_bundle()
count=0
for view in ('view_formal','view_context','view_analogy'):
 d=a.cube_atlas_from_bytes(raw,expected_file_sha256=a.sha256(raw).hexdigest(),expected_bundle_digest=a.cube_node.bundle_digest(b),source_namespace='fixture',observation_id='explicit',observation_time='supplied',record_version=1,view_id=view)
 for case in a.cube_node.answer_cases(b,view)['cases']:
  for assistance in ('guided','unassisted'):
   x=a.compile_atlas_lesson(d,bundle=b,expected_bundle_digest=a.cube_node.bundle_digest(b),operation=case['op'],question=case['question'],assistance=assistance)
   assert x['teacher_sidecar']['expected_answer']==case['correct']
   count+=x['binding']['compiler_calls']
assert not ({'torch','numpy','boto3','botocore','requests','cas_cjt'} & set(sys.modules))
print(json.dumps({'compiler_calls':count,**{k:x['binding'][k] for k in ('neural_calls','optimizer_updates','delivered_neural_lessons')}}))
'''
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"compiler_calls": 306, "neural_calls": 0,
        "optimizer_updates": 0, "delivered_neural_lessons": 0}
