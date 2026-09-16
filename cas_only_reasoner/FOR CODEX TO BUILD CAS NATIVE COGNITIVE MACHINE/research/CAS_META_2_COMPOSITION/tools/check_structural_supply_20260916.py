"""Deterministic source-supply and public-contrast audit; no neural imports.

This inventories EXISTING generators only. It never authors or freezes a panel,
loads a checkpoint, instantiates a learner, or calls a provider. Topology identity
is exact directed unlabelled graph identity for the small supported graphs, not
family-ID identity or a claim of semantic novelty.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import permutations, product
import json
from math import factorial
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_meta2.graph_teaching import (adapter, contrast_probe, curriculum,
                                    face_corpus, face_evaluation, final_panel,
                                    lessons)

SCHEMA = "cas.structural-supply-audit/0.1"
DEFAULT_COMPLEMENTARY = Path(r"C:\Users\wakil\Downloads\Complementary_Recurrent_CJT_Teaching_v0.1_Builder_Handoff (1)\complementary_cjt_teaching_v0_1")
DEFAULT_PERSPECTIVE = Path(r"C:\Users\wakil\Downloads\Connected_Perspective_Learning_CAS_Ohm_v0.1_Builder_Handoff")
RETAINED = ROOT / "records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-graph6curr-20260910133000-aecb5d07"


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def topology_key(nodes, edges):
    """Exact canonical directed topology, with isolated nodes retained.

    Degree partitions prune only permutations that cannot be isomorphisms.
    Enumerating all orders within each partition is exact; node labels and input
    ordering cannot change the result. This is bounded to small source graphs.
    """
    nodes = tuple(nodes)
    edges = tuple(tuple(edge) for edge in edges)
    if len(set(nodes)) != len(nodes) or not nodes:
        raise ValueError("UNIQUE_NONEMPTY_NODES_REQUIRED")
    if len(set(edges)) != len(edges):
        raise ValueError("DUPLICATE_EDGE")
    if any(len(edge) != 2 or any(node not in nodes for node in edge) for edge in edges):
        raise ValueError("UNKNOWN_EDGE_NODE")
    groups = defaultdict(list)
    for node in nodes:
        groups[(sum(target == node for source, target in edges),
                sum(source == node for source, target in edges))].append(node)
    groups = [tuple(groups[key]) for key in sorted(groups)]
    work = 1
    for group in groups:
        work *= factorial(len(group))
    if work > 500000:
        raise ValueError("EXACT_TOPOLOGY_PERMUTATION_BUDGET_EXCEEDED")
    best = None
    for orders in product(*(permutations(group) for group in groups)):
        order = tuple(node for group in orders for node in group)
        indexes = {node: index for index, node in enumerate(order)}
        value = tuple(sorted((indexes[source], indexes[target]) for source, target in edges))
        if best is None or value < best:
            best = value
    return digest({"nodes": len(nodes), "edges": best})


def shape_key(shape):
    nodes = sorted(set(shape) | {part for parts in shape.values() for part in parts})
    return topology_key(nodes, [(whole, part) for whole, parts in shape.items() for part in parts])


def family_key(family):
    return topology_key(family["labels"], [(b["source"], b["target"]) for b in family["branches"]])


def graph_key(graph):
    if any(relation["kind"] != "contains" for relation in graph["relations"]):
        raise ValueError("CONTAINMENT_ONLY_AUDIT")
    return topology_key([node["identifier"] for node in graph["nodes"]],
                        [(relation["source"], relation["target"]) for relation in graph["relations"]])


def face_inventory():
    families = face_corpus.families()
    rows = [{"family_id": family["family_id"], "split": family["split"],
             "archetype": family["archetype"], "topology": family_key(family)}
            for family in families]
    train = {row["topology"] for row in rows if row["split"] == face_corpus.TRAINING}
    counts = {}
    for split in face_corpus.SPLITS:
        subset = [row for row in rows if row["split"] == split]
        keys = {row["topology"] for row in subset}
        counts[split] = {"root_family_ids": len(subset), "topologies": len(keys),
                         "topologies_absent_from_training": len(keys - train)}
    panel = face_evaluation.panel()
    return {"root_family_ids": len(rows), "exact_topologies": len({r["topology"] for r in rows}),
            "splits": counts, "rdcjt_panel_items": len(panel),
            "rdcjt_panel_root_family_ids": len({r["family_id"] for r in panel}),
            "rows": rows,
            "boundary": "Family-held-out is distinct from topology-held-out. The RDCJT panel is already examined and cannot become the proposed new panel."}


def existing_pattern_inventory():
    patterns = final_panel.enumerate_patterns()
    exact = {shape_key(shape) for shape in patterns.values()}
    templates = {shape_key(shape) for shape in lessons.WHOLE_PART_TEMPLATES}
    bases = {shape_key(shape) for shape in curriculum.BASE_SHAPES}
    varied = {graph_key(record["graph"]) for record in curriculum.varied_records()}
    # Old panel construction probes first 45 candidates. Excluding all 45 is
    # conservative and does not claim the unselected 15 were measured by a model.
    old_candidates = final_panel.select_patterns(45)
    examined_candidate_keys = {shape_key(shape) for _, shape in old_candidates}
    survivors = exact - templates - bases - varied - examined_candidate_keys
    return {"enumerator_pattern_keys": len(patterns), "exact_topologies": len(exact),
            "legacy_template_topologies": len(templates),
            "varied_base_topologies": len(bases), "actual_varied_topologies": len(varied),
            "conservatively_excluded_old_panel_candidate_topologies": len(examined_candidate_keys),
            "potential_topologies_after_these_exclusions": len(survivors),
            "potential_topology_digests": sorted(survivors),
            "source_envelope": {"nodes": [final_panel.MIN_NODES, final_panel.MAX_NODES],
                                "relations": [final_panel.MIN_RELATIONS, final_panel.MAX_RELATIONS],
                                "max_direct_parts": final_panel.MAX_DIRECT_PARTS,
                                "max_depth_in_existing_stat_convention": final_panel.MAX_DEPTH},
            "boundary": "Existing enumerator supply only. No new examples were authored. Potential supply is not a frozen compatible panel: all historical exposures, reference operations, root-family grouping, intended training envelope, vocabulary and renderer/learner bindings remain to be checked. This envelope is larger than the 3-4-node face corpus.",
            "new_panel_compiled": False, "all_prior_exposures_checked": False}


def probe_public_audit():
    records = curriculum.varied_records()
    index = {record["record_id"]: record for record in records}
    # All records are deliberately included for software audit; these True flags
    # are not learner measurements or claims of correctness.
    cases = contrast_probe.validate_probe_cases(contrast_probe.build_probe_cases(
        records, set(index)))
    rows = []
    for case in cases:
        original = index[case["record_id"]]
        original_public = adapter.public_records(original, "cas")["public"]
        for name, variant in case["variants"].items():
            if name == "original" or variant is None:
                continue
            edited = {**original, **variant}
            # Follow the CURRENT production helper, rather than reconstructing
            # the inherited pre-repair merge algorithm in this audit.
            task = contrast_probe.public_probe_input(original, variant, arm="cas")
            rows.append({"record_id": original["record_id"], "contrast": name,
                         "graph_changed": original["graph"] != edited["graph"],
                         "question_changed": original["question"] != edited["question"],
                         "public_problem_unchanged": original_public["problem"] == task["public"]["problem"],
                         "whole_public_unchanged": original_public == task["public"],
                         "record_id_unchanged": task["record_id"] == original["record_id"],
                         "original_public_sha256": digest(original_public),
                         "variant_public_sha256": digest(task["public"]),
                         "variant_has_three_distinct_options": len({digest(o) for o in variant["options"]}) == 3})
    source = ROOT / "cas_meta2/graph_teaching/contrast_probe.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    function_names = {node.name for node in ast.walk(tree)
                      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return {"audit_mode": "PURE_DATA_NO_LEARNER", "cases": len(cases),
            "by_contrast": {name: {"variants": sum(r["contrast"] == name for r in rows),
                                   "public_problem_unchanged": sum(r["contrast"] == name and r["public_problem_unchanged"] for r in rows),
                                   "whole_public_unchanged": sum(r["contrast"] == name and r["whole_public_unchanged"] for r in rows),
                                   "record_id_unchanged": sum(r["contrast"] == name and r["record_id_unchanged"] for r in rows),
                                   "three_distinct_options": sum(r["contrast"] == name and r["variant_has_three_distinct_options"] for r in rows)}
                            for name in ("renamed", "reordered", "rewired")},
            "implementation_audited": "CURRENT_WORKING_SOURCE_PUBLIC_PROBE_INPUT",
            "list_length_inputs_function_present": "list_length_inputs" in function_names,
            "length_permutations_per_list_case": [len(list(contrast_probe.list_length_inputs(
                contrast_probe.public_probe_input(index[case["record_id"]], case["variants"]["original"]))))
                for case in cases if case["op"] == "LIST_PARTS"],
            "rows": rows,
            "source_inspection_findings": [
                "Current public_probe_input re-renders each graph/question and supplies a contrast-prefixed public-content identity; byte measurements above use this actual helper.",
                "Current run_probe calls public_probe_input and list_length_inputs, reverses renamed predictions before comparison, and checks before/after parameter identity when available.",
                "Current length permutations expose slot sensitivity and selected lengths; they do not prove a causal length bias and do not record logits or vector norms.",
                "A separate hash-bound checkpoint restoration/dispatch and owner-authorized AWS GPU request are required before a neural contrast result."],
            "neural_measurements": 0}


def source_identities(paths):
    return [{"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()}
            for path in paths]


def build_report(complementary=DEFAULT_COMPLEMENTARY, perspective=DEFAULT_PERSPECTIVE):
    cpath = complementary / "Complementary_Teaching_Profile_v0.1.json"
    ppath = perspective / "Perspective_Resonance_Profile_v0.1.json"
    cp = json.loads(cpath.read_bytes())
    pp = json.loads(ppath.read_bytes())
    retained_path = RETAINED / "curriculum_result.json"
    retained = json.loads(retained_path.read_bytes())
    source_paths = [ROOT / "cas_meta2/graph_teaching" / (name + ".py") for name in
                    ("face_corpus", "face_evaluation", "lessons", "curriculum", "fresh_panel",
                     "final_panel", "contrast_probe", "adapter", "real_framework")]
    source_paths += [cpath, ppath, retained_path, Path(__file__)]
    source_paths += [complementary / "Complementary_CJT_Teaching_Directive_v0.1.md",
                     perspective / "Connected_Perspective_Learning_and_CAS_Ohm_v0.1.md",
                     perspective / "Perspective_Family_Authoring_Example.json"]
    fixture = json.loads((perspective / "Perspective_Family_Authoring_Example.json").read_bytes())
    return {"schema": SCHEMA, "status": "FREEZE_NOT_READY",
            "evidence_kind": "PURE_DETERMINISTIC_SOURCE_AND_PUBLIC_BYTES",
            "neural_execution": False, "provider_calls": 0, "checkpoint_loading": False,
            "face_corpus": face_inventory(),
            "other_existing_source_supply": existing_pattern_inventory(),
            "retained_examined_panel": {"path": str(retained_path), **retained["panel"],
                                        "checkpoint_files_present_not_loaded": len(list(RETAINED.rglob("*.pt")))},
            "directives": {"complementary_execution_enabled": cp["execution_enabled"],
                           "complementary_binding_state": cp["binding_state"],
                           "proposed_application_panel": cp["evaluation"]["new_application_panel_proposed"],
                           "perspective_execution_enabled": pp["execution_enabled"],
                           "perspective_parent_schedule": pp["comparison"]["parent_schedule"],
                           "perspective_new_training_slots": pp["comparison"]["new_training_slots"],
                           "perspective_fixture_root_families": 1,
                           "perspective_fixture_views": len(fixture["views"]),
                           "perspective_fixture_is_balanced_corpus": not fixture["not_a_balanced_training_corpus"]},
            "contrast_probe": probe_public_audit(),
            "decision": {"requires_new_authored_examples_established": False,
                         "can_freeze_current_directives": False,
                         "next_source_action": "Bind an opt-in candidate to unused EXISTING enumerator patterns only after excluding all historical root families/semantic cases and checking the 8-10-node source envelope against intended teaching. If that cannot meet the proposed 30 x 3 panel, state the shortfall and explicitly revise count/novelty class before freeze.",
                         "complementary_blockers": ["No compiled versioned panel with complete historical-exposure exclusions",
                                                   "Component/whole relevance, operation coverage and retention panels remain unbound",
                                                   "Checkpoint, optimizer, actual schedule/worker/resource identities remain unbound"],
                         "perspective_blocker": "Must pin one compatible frozen complementary profile before freeze; reference fixture is one family, not an extra corpus."},
            "source_identities": source_identities(source_paths)}


def markdown(report):
    supply = report["other_existing_source_supply"]
    lines = ["# Structural supply and contrast feasibility — pure audit",
             "", "Status: **FREEZE_NOT_READY**. No model, checkpoint, GPU or provider was used.",
             "", "The 96 face families contain exactly six directed topologies. Training, development and final splits each contain all six. The 216-item RDCJT panel uses 16 already examined root families; it cannot become the new complementary panel.",
             "", f"Overall structural exhaustion is not established: the existing final_panel enumerator contains {supply['exact_topologies']} exact topologies. Conservatively excluding its first 45 historical panel candidates plus legacy teaching and actual varied-course structures leaves {supply['potential_topologies_after_these_exclusions']} potential topologies. This is source supply, not a frozen panel or proof that all those structures are unexamined. Its 8–10-node envelope differs from the 3–4-node face corpus.",
             "", "Next source action: bind unused existing patterns to a versioned candidate panel, with all historical exposure exclusions and exact semantic/root-family grouping. Check the supported teaching envelope, operations, vocabulary and actual learner rendering before freezing. No new examples were authored. If supply fails those checks, explicitly revise the proposed counts/novelty class; a new ID or rename is not an unseen reasoning problem.",
             "", "Current contrast transport audit after the local repair:",
             "", "- The actual public_probe_input helper re-renders all variants and supplies new public-content identities. Exact current counts and byte hashes appear in report.json.",
             "- list_length_inputs emits six option-slot permutations per list case. Renamed predictions are compared after reversing the label map. These are software checks, not neural measurements.",
             "- The original report in the parent directory is preserved as a historical pre-repair algorithm audit; it must not describe the repaired working source.",
             "- Bind the retained checkpoints and restored encoder/tokenizer to the repaired adapter; record score/option identities and unchanged parameters. Only a separately authorized AWS GPU run can measure the model.",
             "", "Complementary remains unbound at the dataset, checkpoint/optimizer, schedule/worker and resource levels. Perspective must pin the compatible complementary schedule first; its six-view authoring fixture supplies one root family and zero new training slots.",
             "", "See report.json for exact source hashes, topology digests, public-byte digests and remaining limits."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT.resolve() / "records")
    output.mkdir(parents=True, exist_ok=False)
    report = build_report()
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "REPORT.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output),
                      "exact_existing_pattern_topologies": report["other_existing_source_supply"]["exact_topologies"],
                      "potential_remaining_topologies": report["other_existing_source_supply"]["potential_topologies_after_these_exclusions"],
                      "neural_execution": False}))


if __name__ == "__main__":
    main()
