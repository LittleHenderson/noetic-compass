"""Reproduce the pure cube bridge in a new scratch evidence directory.

No learner, tensor, provider, training or deployment code is invoked. A source
snapshot precedes project imports; actual transitive imports must match it after
the run. Existing output directories and artifacts are never overwritten.
"""
from __future__ import annotations

import argparse
from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in HERE.parents if (parent / "cncm/rpa_cube_adapter.py").is_file())
COMPOSITION = ROOT / "research/CAS_META_2_COMPOSITION"
EXPECTED_ADAPTER = "00d4bdd06109dfa3324da548b37d5b10c6b117256d95f98eb875aa95938e1e62"
EXPECTED_BUNDLE_FILE = "9e62538b807d0b7a6fc04890c4ee0504db53e45bc34b62504f001d7f0610eb32"
EXPECTED_BUNDLE = "b3df2633ec6a49c6ad81d1572334ac00bcd123d09672d7a53a05979fc70b2c16"
EXPECTED_RPA_MODEL = "323a53b951644a93603cd2f56204fd5a038a3161f4778e28777e650a4f966f01"
DENIED = {"torch", "numpy", "boto3", "botocore", "requests", "cas_cjt"}
ATTEMPTS = []
COUNTS = {"bridge_compiler_calls": 0, "legacy_comparison_compiler_calls": 0,
          "legacy_target_free_probe_calls": 0, "neural_calls": 0,
          "learner_invocations": 0, "optimizer_updates": 0,
          "delivered_neural_lessons": 0, "provider_calls": 0}


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED:
            ATTEMPTS.append(fullname)
            raise RuntimeError("PROHIBITED_IMPORT:" + fullname)


def seal(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def write_bytes(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def write_json(path, value):
    write_bytes(path, (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())


def write_jsonl(path, rows):
    write_bytes(path, ("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
                               + "\n" for row in rows)).encode())


def ordinary_bfs(atlas, root, max_depth, max_nodes):
    nodes = {row.node_id: row for row in atlas.nodes}
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
                deferred.append([node, link.link_id, link.target_id, "max_depth"])
            elif len(visited) >= max_nodes:
                deferred.append([node, link.link_id, link.target_id, "max_nodes"])
            else:
                seen.add(nodes[link.target_id].view_key)
                visited.append(link.target_id)
                traversed.append(link.link_id)
                queue.append((link.target_id, depth + 1))
    return {"visited": visited, "traversed": traversed, "revisited": revisited, "deferred": deferred}


def run(args, output, before):
    sys.meta_path.insert(0, Deny())
    assert not (DENIED & set(sys.modules)), "forbidden module present before project import"
    sys.path.insert(0, str(ROOT))
    from cncm import rpa_cube_adapter as bridge
    from cncm.canonical import canonical_json, digest
    from cncm.model import ContractError
    from cncm.rpa_model import LinkType, NodeStatus
    node, profile = bridge.cube_node, bridge.cube_profile
    assert seal(Path(bridge.__file__))["sha256"] == args.expected_adapter_sha256
    assert seal(ROOT / "cncm/rpa_model.py")["sha256"] == EXPECTED_RPA_MODEL
    raw = node.pinned_bundle_path().read_bytes()
    bundle = json.loads(raw)
    assert sha256(raw).hexdigest() == EXPECTED_BUNDLE_FILE
    assert node.bundle_digest(bundle) == EXPECTED_BUNDLE
    write_bytes(output / "source_bundle.json", raw)

    def receipt_for(value, raw_source=None, namespace="pinned_cube_fixture"):
        source = canonical_json(value).encode() if raw_source is None else raw_source
        return bridge.cube_source_receipt(source, expected_file_sha256=sha256(source).hexdigest(),
            expected_bundle_digest=node.bundle_digest(value), source_namespace=namespace,
            observation_id=args.observation_id, observation_time=args.observation_time, record_version=1)

    receipt = receipt_for(bundle, raw)
    write_json(output / "source_receipt.json", receipt.to_dict())

    def project(value, view, receipt_value=None):
        return bridge.cube_atlas_from_bundle(value, expected_bundle_digest=node.bundle_digest(value),
            source_receipt=receipt_value or receipt_for(value), view_id=view)

    def compile_lesson(document, value, case, assistance, **kwargs):
        COUNTS["bridge_compiler_calls"] += 1
        return bridge.compile_atlas_lesson(document, bundle=value, expected_bundle_digest=node.bundle_digest(value),
            operation=case["op"], question=case["question"], assistance=assistance, **kwargs)

    comparisons, learners, teachers, bindings = [], [], [], []
    provenance, navigations, traversals, target_isolation, views = [], [], [], [], {}
    for view_id in ("view_formal", "view_context", "view_analogy"):
        document = project(bundle, view_id, receipt)
        original = document.to_dict()
        assert original["catalog"]["bundle"] == bundle
        assert original["source_receipt"]["world_truth_established"] is False
        assert original["source_receipt"]["authorship_authenticated"] is False
        assert len(document.atlas.nodes) == 43 and len(document.atlas.links) == 47
        assert all(row.relation is LinkType.CONTAINS_PART for row in document.atlas.links)
        assert all(row.status is not NodeStatus.VERIFIED for row in document.atlas.nodes)
        lookup = {row["cube_node_id"]: row for row in document.catalog["cube_index"].values()}
        labels, atlas_nodes = node.view_labels(bundle, view_id), document.atlas.node_map()
        faces = []
        for cube in bundle["cube_nodes"]:
            index = lookup[cube["node_id"]]
            assert index["record_digest"] == digest(cube)
            assert bundle["cube_nodes"][index["source_path"][1]] == cube
            assert atlas_nodes[index["atlas_node_id"]].label == labels[cube["node_id"]]
            assert index["idea_id"] == bridge.canonical_cube_id(receipt.source_namespace, cube["context_id"], cube["node_id"])
            for face_key in node.FACE_KEYS:
                candidates = [row for row in document.atlas.nodes
                    if dict(row.fields).get("catalog_key") in original["catalog"]["cube_index"]
                    and original["catalog"]["cube_index"][dict(row.fields)["catalog_key"]]["cube_node_id"] == cube["node_id"]
                    and dict(row.fields).get("face_path") == "faces." + face_key]
                assert len(candidates) == 1
                face = cube["faces"][face_key]
                assert dict(candidates[0].fields)["availability"] == face["availability"]
                assert set(face["provenance_refs"]) <= {row["source_id"] for row in bundle["sources"]}
                faces.append({"cube_node_id": cube["node_id"], "face": face_key,
                              "record_digest": digest(face), "atlas_node_id": candidates[0].node_id})
        branches = []
        for branch in bundle["branches"]:
            links = [row for row in document.atlas.links if row.projection == "source_contains_branch:" + branch["branch_id"]]
            assert len(links) == 1
            link = links[0]
            assert link.source_id == lookup[branch["source_node_id"]]["atlas_node_id"]
            assert link.target_id == lookup[branch["target_node_id"]]["atlas_node_id"]
            branches.append({"branch_id": branch["branch_id"], "record_digest": digest(branch),
                             "atlas_link_id": link.link_id, "relation": link.relation.value})
        provenance.append({"view_id": view_id, "cube_index": original["catalog"]["cube_index"],
            "faces": faces, "branches": branches, "view_record_digest": digest(next(row for row in bundle["views"] if row["view_id"] == view_id)),
            "mapping_records": [{"mapping_id": row["mapping_id"], "digest": digest(row)} for row in bundle["mappings"]]})
        write_json(output / (view_id + ".document.json"), original)
        cases = node.answer_cases(bundle, view_id)["cases"]
        assert len(cases) == 51
        baselines = {}
        for case in cases:
            for assistance in ("guided", "unassisted"):
                result = compile_lesson(document, bundle, case, assistance)
                COUNTS["legacy_comparison_compiler_calls"] += 1
                legacy = profile.compile_lesson(bundle, case, assistance=assistance, view_id=view_id)
                public, teacher, binding = result["learner_input"], result["teacher_sidecar"], result["binding"]
                assert set(public) == {"record_id", "public", "encoded_options"}
                assert public["public"] == legacy["encoding"]["public"]
                assert public["encoded_options"] == legacy["encoding"]["encoded_options"]
                assert teacher["expected_answer"] == case["correct"]
                assert teacher["encoded_correct_index"] == legacy["encoding"]["encoded_correct_index"]
                assert teacher["visibility"] == legacy["visibility"]
                assert binding["compiler_calls"] == 1 and binding["competence_established"] is False
                assert binding["cache_identity_bound"] is False
                assert all(binding[key] == 0 for key in ("neural_calls", "optimizer_updates", "delivered_neural_lessons"))
                assert document.to_dict() == original
                learners.append(deepcopy(public)); teachers.append(deepcopy(teacher)); bindings.append(deepcopy(binding))
                comparisons.append({"view_id": view_id, "operation": case["op"], "question": case["question"],
                    "assistance": assistance, "record_id": public["record_id"], "public_digest": digest(public["public"]),
                    "ordered_choices_digest": digest(public["encoded_options"]), "visibility_digest": digest(teacher["visibility"]),
                    "teacher_digest": digest(teacher), "legacy_task_id": legacy["task_id"], "match": True})
                baselines[(case["case_key"], assistance)] = result
        first_case = cases[0]
        baseline = baselines[(first_case["case_key"], "unassisted")]
        for focused_node in document.atlas.nodes:
            focused = document.focus(focused_node.node_id)
            result = compile_lesson(focused, bundle, first_case, "unassisted")
            assert result == baseline
            assert focused.atlas.current_state_id == document.atlas.current_state_id
            navigations.append({"view_id": view_id, "focus": focused_node.node_id,
                "current_state_id": focused.atlas.current_state_id,
                "learner_input_digest": digest(result["learner_input"]), "base_unchanged": document.to_dict() == original})
        # Teacher records can be edited or removed in an external working copy;
        # neither operation can change the separately copied learner input.
        for mutation in ("delete", "replace", "change"):
            altered = deepcopy(baseline)
            if mutation == "delete":
                del altered["teacher_sidecar"]
            elif mutation == "replace":
                altered["teacher_sidecar"] = {"expected_answer": "invented"}
            else:
                altered["teacher_sidecar"]["expected_answer"] = "invented"
            assert altered["learner_input"] == baseline["learner_input"]
            assert compile_lesson(document, bundle, first_case, "unassisted") == baseline
            target_isolation.append({"view_id": view_id, "mutation": mutation,
                                     "learner_input_digest": digest(baseline["learner_input"]), "unchanged": True})
        roots = [document.atlas.current_state_id] + [row["atlas_node_id"] for row in lookup.values()]
        for root in roots:
            for depth in (0, 1, 2, 4, 32):
                for budget in (1, 3, 7, 43):
                    expected = ordinary_bfs(document.atlas, root, depth, budget)
                    actual = document.atlas.expand(root_id=root, max_depth=depth, max_nodes=budget,
                                                   relations=(LinkType.CONTAINS_PART,))
                    projection = {"visited": list(actual.visited_node_ids), "traversed": list(actual.traversed_link_ids),
                        "revisited": list(actual.revisited_link_ids), "deferred":
                        [[row.source_id, row.link_id, row.target_id, row.reason] for row in actual.deferred]}
                    assert projection == expected
                    traversals.append({"view_id": view_id, "root": root, "depth_budget": depth,
                                       "node_budget": budget, "result": projection, "match": True})
        views[view_id] = (document, first_case, baseline)
    assert len(comparisons) == 306
    assert len({row["record_id"] for row in learners}) == 306
    assert len(provenance) == 3 and len(navigations) == 129 and len(traversals) == 420
    write_jsonl(output / "learner_inputs.jsonl", learners)
    write_jsonl(output / "teacher_sidecars.jsonl", teachers)
    write_jsonl(output / "lesson_bindings.jsonl", bindings)
    write_json(output / "compiler_comparisons.json", comparisons)
    write_json(output / "source_projection_conformance.json", provenance)
    write_json(output / "navigation_conformance.json", navigations)
    write_json(output / "target_isolation.json", target_isolation)
    write_json(output / "traversal_conformance.json", traversals)

    document, case, baseline = views["view_context"]
    rewired = node.rewire_bundle(bundle, branch_id="branch_04", new_source="node_004", new_target="node_003")
    rewired_receipt = receipt_for(rewired)
    hypothetical = document.with_hypothesis(project(rewired, "view_context", rewired_receipt))
    result = compile_lesson(hypothetical, bundle, case, "unassisted")
    assert result == baseline
    assert hypothetical.atlas.current_state_id == document.atlas.current_state_id
    assert hypothetical.atlas.node_map()[hypothetical.atlas.hypothesis_branch_id].status is NodeStatus.HYPOTHETICAL
    restored = bridge.load_cube_atlas_document(hypothetical.to_dict(), source_receipts=hypothetical._receipts)
    assert restored.to_dict() == hypothetical.to_dict()
    write_json(output / "hypothesis.document.json", hypothetical.to_dict())
    write_bytes(output / "hypothesis_bundle.json", rewired_receipt.source_bytes)
    write_json(output / "hypothesis_source_receipt.json", rewired_receipt.to_dict())
    write_json(output / "hypothesis_conformance.json", {"base_current_state_id": document.atlas.current_state_id,
        "selected_hypothesis_id": hypothetical.atlas.hypothesis_branch_id,
        "learner_input_digest": digest(result["learner_input"]), "base_input_unchanged": True,
        "hypothesis_source_digest": rewired_receipt.canonical_bundle_digest, "runtime_commit": False})

    pages, seen, cursor = [], [], None
    while True:
        page = bridge.catalog_page(document, limit=2, cursor=cursor)
        pages.append(page)
        seen.extend(row["catalog_key"] for row in page["rows"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert seen == sorted(document.catalog["cube_index"])
    write_json(output / "catalog_pages.json", pages)
    refusals = []

    def refuses(name, callback, exception=ContractError):
        try:
            callback()
        except exception as exc:
            refusals.append({"name": name, "exception": type(exc).__name__, "message": str(exc)})
        else:
            raise AssertionError("expected refusal did not occur: " + name)

    refuses("disagreeing_teacher_target", lambda: bridge.check_teacher_target(baseline, "invented"))
    refuses("wrong_source_bundle_digest", lambda: bridge.cube_atlas_from_bundle(bundle,
        expected_bundle_digest="0" * 64, source_receipt=receipt))
    from dataclasses import replace
    refuses("wrong_source_file_digest", lambda: replace(receipt, source_file_sha256="0" * 64))
    refuses("wrong_source_namespace", lambda: replace(receipt, source_namespace="bad namespace"))
    corrupt = document.to_dict(); corrupt["atlas"]["nodes"][0]["label"] = "forged"
    refuses("resealed_stale_projection", lambda: bridge.load_cube_atlas_document(corrupt, source_receipts=document._receipts))
    cursor = deepcopy(pages[0]["next_cursor"]); cursor["next_offset"] = 4
    refuses("corrupt_page_cursor", lambda: bridge.catalog_page(document, limit=2, cursor=cursor))
    private = deepcopy(bundle); private["context"]["expected_answer"] = "secret"
    refuses("private_target_in_source_context", lambda: project(private, "view_context"))
    partial = deepcopy(bundle); partial["views"][0]["branch_refs"].pop()
    refuses("partial_view_would_widen_input", lambda: project(partial, "view_context"))
    foreign = deepcopy(bundle)
    foreign["cube_nodes"][0]["faces"]["face_5"]["structured"].update(completeness="partial", direct_branch_refs=["branch_03"])
    refuses("foreign_partial_face_inventory", lambda: project(foreign, "view_context"))
    predicates = deepcopy(bundle); predicates["branches"][0]["predicate"] = "triggers"
    refuses("undeclared_predicate", lambda: project(predicates, "view_context"))
    bad_node = deepcopy(bundle); bad_node["branches"][0]["target_node_id"] = "missing"
    refuses("dangling_branch", lambda: project(bad_node, "view_context"))
    duplicate = deepcopy(bundle); duplicate["cube_nodes"].append(deepcopy(duplicate["cube_nodes"][0]))
    refuses("duplicate_cube_id", lambda: project(duplicate, "view_context"))
    cycle = node.rewire_bundle(bundle, branch_id="branch_05", new_source="node_002", new_target="node_001", rebuild=False)
    refuses("contains_cycle", lambda: project(cycle, "view_context"))
    oversized = b" " * (bridge.MAX_SOURCE_BYTES + 1)
    refuses("oversized_source_bytes", lambda: replace(receipt, source_bytes=oversized))
    unknown = deepcopy(bundle); unknown["context"]["contains_inventory_complete"] = False
    for cube in unknown["cube_nodes"]:
        cube["faces"]["face_5"]["structured"]["completeness"] = "partial"
    incomplete_document = project(unknown, "view_context")
    refuses("incomplete_inventory_cannot_license_absence", lambda: compile_lesson(incomplete_document, unknown,
        {"op": "REACHED_VIA", "question": {"part": "Rim", "idea": "Frame"}}, "unassisted"))
    for operation in ("Why", "How", "reachable_via"):
        refuses("unsupported_operation_" + operation, lambda operation=operation: compile_lesson(document, bundle,
            {"op": operation, "question": {}}, "guided"))
    long_labels = {cube["core"]["label"]: "a" * 300 + str(index) for index, cube in enumerate(bundle["cube_nodes"])}
    long_bundle = node.rename_bundle(bundle, long_labels)
    long_document = project(long_bundle, "view_context")
    long_case = {"op": "LIST_PARTS", "question": {"idea": long_labels["Bicycle"]}}
    refuses("lossy_three_choice_encoding", lambda: compile_lesson(long_document, long_bundle, long_case, "guided"))
    COUNTS["legacy_target_free_probe_calls"] += 1
    refuses("preserved_legacy_target_free_failure", lambda: profile.compile_public_exercise(bundle,
        profile.public_case(case), assistance="guided"), KeyError)
    write_json(output / "refusal_probes.json", refusals)

    def rename_branch(value):
        if type(value) is dict:
            return {key: rename_branch(item) for key, item in value.items()}
        if type(value) is list:
            return [rename_branch(item) for item in value]
        return "zz_branch_01" if value == "branch_01" else value
    reordered_source = rename_branch(bundle)
    changed = compile_lesson(project(reordered_source, "view_context"), reordered_source, case, "unassisted")
    old_a = profile.compile_lesson(bundle, case, assistance="unassisted")
    old_b = profile.compile_lesson(reordered_source, case, assistance="unassisted")
    COUNTS["legacy_comparison_compiler_calls"] += 2
    assert old_a["task_id"] == old_b["task_id"]
    assert baseline["learner_input"]["public"] != changed["learner_input"]["public"]
    assert baseline["learner_input"]["encoded_options"] == changed["learner_input"]["encoded_options"]
    assert baseline["learner_input"]["record_id"] != changed["learner_input"]["record_id"]
    assert baseline["binding"]["semantic_question_id"] == changed["binding"]["semantic_question_id"]
    write_json(output / "cache_identity_conformance.json", {"legacy_task_id_unchanged": old_a["task_id"],
        "first_learner_input": baseline["learner_input"], "second_learner_input": changed["learner_input"],
        "semantic_question_id": baseline["binding"]["semantic_question_id"],
        "statement": "Input identity changes when public bytes change; no cache or encoder was invoked."})
    copied = document.to_dict(); copied["catalog"]["bundle"]["sources"].clear()
    assert document.catalog["bundle"] == bundle
    assert bridge.load_cube_atlas_document(document.to_dict(), source_receipts=(receipt,)).to_dict() == document.to_dict()
    actual_modules = []
    for name, module in sorted(sys.modules.items()):
        file = getattr(module, "__file__", None)
        if not file or not str(file).endswith(".py"):
            continue
        path = Path(file).resolve()
        if path.is_relative_to(ROOT / "cncm") or path.is_relative_to(COMPOSITION / "cas_meta2"):
            identity = seal(path)
            assert before[str(path)] == identity, "changed source: " + str(path)
            actual_modules.append({"module": name, "path": path.relative_to(ROOT).as_posix(), **identity})
    assert not ATTEMPTS and not (DENIED & set(sys.modules))
    assert node.pinned_bundle_path().read_bytes() == raw
    write_json(output / "actual_imports.json", {"modules": actual_modules,
        "prohibited_import_attempts": ATTEMPTS, "prohibited_imports_present": sorted(DENIED & set(sys.modules))})
    return {"matching_compilations": len(comparisons), "views": 3, "questions_per_view": 51,
        "assistance_levels": ["guided", "unassisted"], "nodes_per_view": 43, "links_per_view": 47,
        "canonical_cubes": 6, "faces": 36, "source_contains_branches": 5,
        "focus_checks": len(navigations), "matched_directed_bfs_checks": len(traversals),
        "refusal_probes": len(refusals), "actual_project_imports": len(actual_modules),
        "work_counts": COUNTS, "competence_established": False,
        "scope": "Faithful authored-source projection and lesson preparation only; no learning or runtime execution."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--observation-id", required=True)
    parser.add_argument("--observation-time", required=True)
    parser.add_argument("--expected-adapter-sha256", default=EXPECTED_ADAPTER)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if not output.is_relative_to(HERE) or output == HERE:
        raise ValueError("acceptance output must be a new child of this scratch directory")
    output.mkdir(parents=True, exist_ok=False)
    before = {str(path.resolve()): seal(path)
              for directory in (ROOT / "cncm", COMPOSITION / "cas_meta2") for path in directory.rglob("*.py")}
    write_json(output / "run_context.json", {"argv": sys.argv, "cwd": str(Path.cwd()),
        "python": {"executable": sys.executable, "version": sys.version},
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "helper": {"path": str(Path(__file__).resolve()), **seal(Path(__file__))},
        "adapter_expected_sha256": args.expected_adapter_sha256,
        "observation_metadata": {"observation_id": args.observation_id, "observation_time": args.observation_time}})
    write_json(output / "project_sources_before.json", [{"path": Path(path).relative_to(ROOT).as_posix(), **identity}
                                                       for path, identity in sorted(before.items())])
    try:
        result = run(args, output, before)
        # Check the actual run's source footprint, not merely configured paths.
        for row in json.loads((output / "actual_imports.json").read_text())["modules"]:
            assert seal(ROOT / row["path"]) == {key: row[key] for key in ("bytes", "sha256")}
        write_json(output / "acceptance_summary.json", result)
        artifacts = [{"path": path.relative_to(output).as_posix(), **seal(path)}
                     for path in sorted(output.rglob("*")) if path.is_file()]
        receipt = {"schema_version": "cncm.rpa-cube-acceptance/0.1", "status": "PASS",
            "completed_utc": datetime.now(timezone.utc).isoformat(), "results": result,
            "source_byte_identity_checked_before_and_after": True,
            "bundle_file_sha256": EXPECTED_BUNDLE_FILE, "bundle_digest": EXPECTED_BUNDLE,
            "adapter_sha256": args.expected_adapter_sha256, "helper_identity": seal(Path(__file__)),
            "artifacts": artifacts, "boundary": "Pure compiler/projection evidence; no learned competence claim."}
        write_json(output / "receipt.json", receipt)
        for row in artifacts:
            assert seal(output / row["path"]) == {key: row[key] for key in ("bytes", "sha256")}
        print(json.dumps({"status": "PASS", "output": str(output), "receipt": seal(output / "receipt.json"), **result}, sort_keys=True))
    except BaseException as exc:
        write_json(output / "failure.json", {"status": "FAIL", "exception": type(exc).__name__,
            "message": str(exc), "traceback": traceback.format_exc(), "work_counts": COUNTS,
            "prohibited_import_attempts": ATTEMPTS, "observed_utc": datetime.now(timezone.utc).isoformat()})
        raise


if __name__ == "__main__":
    main()
