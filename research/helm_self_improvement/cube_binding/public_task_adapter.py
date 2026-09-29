"""Public cube graph -> actual c45f775f typed Parts packet, never old choices."""
from copy import deepcopy

from .contracts import (PUBLIC_PROFILE, SCIENTIFIC_SOURCE, binding_sidecar,
                        bounded_copy, checked_cube, digest, public_runtime, require)


def compile_parts(bundle, request, declarations):
    """No target/analyst/cache/retrieval argument. Return public and audit separately.

    declarations supplies domain/kind/function/setting and exactly three public
    primary_node_ids. These explicit presentation facts are frozen before query
    selection; no invented 'training' provenance is needed by this bridge.
    Every node's prose/faces, all worked examples and all retrieval are excluded.
    """
    request, declarations = bounded_copy(request), bounded_copy(declarations)
    require(type(request) is dict and set(request) == {"op", "whole_node_id", "view_id"},
            "CB1_REQUEST_FIELDS_OR_LEGACY_CODEC")
    require(request["op"] == "LIST_PARTS", "CB1_TASK_NOT_SUPPORTED")
    require(type(declarations) is dict and set(declarations) ==
            {"domain", "kind", "function", "setting", "primary_node_ids"}, "CB1_DECLARATION_FIELDS")
    rt = public_runtime()
    cube = checked_cube(bundle, rt)
    require(cube["context"]["contains_inventory_complete"] is True, "CB1_INVENTORY_UNOBSERVED")
    labels = rt["cube_node"].view_labels(cube, request["view_id"])
    require(request["whole_node_id"] in labels, "CB1_WHOLE_UNKNOWN")
    primary = declarations["primary_node_ids"]
    require(type(primary) is list and len(primary) == 3 and len(set(primary)) == 3
            and all(ref in labels for ref in primary), "CB1_PRIMARY_DECLARATION")
    graph = rt["cube_node"].graph_record(cube, request["view_id"])
    edges = [{"source": row["source"], "target": row["target"]} for row in graph["relations"]]
    # Sort by public endpoints, never branch UUIDs, private targets or audit order.
    edges.sort(key=lambda row: (row["source"], row["target"]))
    source, answers, course, slots = (rt[key] for key in ("source", "answers", "course", "slots"))
    world = source._world(source._facts(sorted(labels.values()), edges, declarations,
                                       [labels[ref] for ref in primary]))
    public = source.validate_public({"focus_world_id": world["world_id"],
                                     "worlds": [world], "bank": source._bank_record([world])})
    refs = {n["label"]: n["ref"] for n in world["nodes"]}
    query = answers.compile_query(public, kind="parts", rule="direct_contains_v1",
                                  arguments={"whole": refs[labels[request["whole_node_id"]]]})
    body = {"schema": course.PACKET_SCHEMA, "source_digest": source.public_digest(public),
            "source_world_id": world["world_id"], "query": query, "cue": None,
            "instruction": course.REQUESTS["parts"], "role_catalog": deepcopy(course.ROLE_CATALOG),
            "supports": []}
    packet = course.validate_model_packet({"source": public,
        "record": {"record_id": "typed-input-" + source.digest(body), **body}})
    plan = slots.compile_slots(packet)
    require(plan["kind"] == "parts" and len(plan["slots"]) == len(labels)
            and all(s["field"] == "node" and s["symbols"] == ["ABSENT", "PRESENT"]
                    for s in plan["slots"]), "CB1_CURRENT_SLOT_CONTRACT")
    mapping = {ref: refs[label] for ref, label in labels.items()}
    profile = rt["cube_profile"].visibility_profile("LIST_PARTS", "unassisted")
    mask = rt["cube_profile"].withheld_field_paths(cube, list(labels), "LIST_PARTS", "unassisted")
    sidecar = binding_sidecar(cube, packet_sha256=digest(packet), node_mapping=mapping, runtime=rt)
    return {"packet": packet, "slot_plan": plan, "sidecar": sidecar,
            "visibility": {"profile": PUBLIC_PROFILE, "legacy_profile": profile,
                "legacy_mask_all_nodes": mask, "visible_faces": [], "retrieval_entries": [],
                "worked_supports": [], "cache_policy": "PUBLIC_BYTES_MODEL_ENCODER_PROFILE_ONLY",
                "extra_mask": "ALL_NODE_CORE_PROSE_AND_SIX_FACE_CONTENTS_ALL_NEIGHBORS",
                "declarations": "EXPLICIT_PUBLIC_PRESENTATION_FACTS_NOT_EVALUATOR_TARGETS"},
            "neural_execution": "NOT_RUN"}


def cache_key(packet, *, checkpoint_sha256, encoder_sha256):
    for value in (checkpoint_sha256, encoder_sha256):
        require(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
                "CB1_CACHE_MODEL_IDENTITY")
    checked = public_runtime()["course"].validate_model_packet(packet)
    require(checked["record"]["query"]["kind"] == "parts" and checked["record"]["supports"] == []
            and checked["record"]["cue"] is None and len(checked["source"]["worlds"]) == 1,
            "CB1_UNASSISTED_CACHE_ONLY")
    return digest({"packet": checked, "checkpoint": checkpoint_sha256,
                   "encoder": encoder_sha256, "scientific_source": SCIENTIFIC_SOURCE,
                   "visibility": PUBLIC_PROFILE})


def decode_parts(packet, scores):
    """Actual unchanged slot decision/assembly. Scores are never repaired."""
    rt = public_runtime()
    checked = rt["course"].validate_model_packet(packet)
    require(checked["record"]["query"]["kind"] == "parts" and checked["record"]["supports"] == []
            and checked["record"]["cue"] is None and len(checked["source"]["worlds"]) == 1,
            "CB1_TASK_NOT_SUPPORTED")
    decisions = rt["slots"].score_decisions(checked, scores)
    return rt["slots"].assemble_answer(checked, decisions)


def analysis_binding_rows(packet, scheme):
    """Public-only connection to Claude's row scheme; never a learner input.

    Uses public labels as fillers, not world hashes/branch IDs/author annotations.
    The original pointer reader orders node rows by scoped /n rank. Real capture
    alignment must still be witnessed before fitting or editing a model.
    """
    from .role_schemes import public_graph, row_binding_sets
    checked = public_runtime()["course"].validate_model_packet(packet)
    require(checked["record"]["query"]["kind"] == "parts" and checked["record"]["supports"] == []
            and checked["record"]["cue"] is None and len(checked["source"]["worlds"]) == 1,
            "CB1_ANALYSIS_PACKET_PROFILE")
    require(scheme.kind == "RELATION_ENDPOINT", "CB1_ANALYSIS_ROW_SCHEME")
    world = checked["source"]["worlds"][0]
    nodes = sorted(world["nodes"], key=lambda n: n["ref"])
    require(all(n["ref"] == world["world_id"] + "/n" + str(i) for i, n in enumerate(nodes)),
            "CB1_ANALYSIS_ROW_ORDER")
    labels = {n["ref"]: n["label"] for n in nodes}
    branches = [{"source_node_id": labels[e["source"]], "predicate": "contains",
                 "target_node_id": labels[e["target"]]} for e in world["contains"]]
    graph = public_graph(scheme, branches, nodes=[n["label"] for n in nodes])
    sets = row_binding_sets(scheme, graph)
    return {"packet_sha256": digest(checked), "origin": "AUTHORED_PUBLIC_GRAPH_NOT_NEURAL_CAPTURE",
            "rows": tuple({"row": i, "node_ref": n["ref"], "public_label": n["label"],
                           "binding_set": binding} for i, (n, binding) in enumerate(zip(nodes, sets))),
            "capture_alignment": "REAL_WITNESS_NOT_RUN", "fit_authorized": False}
