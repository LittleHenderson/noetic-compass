"""Development-only legacy data construction, without opening a final panel.

Tasks retain the canonical legacy public AND teacher fields. They are teaching
records, not safe inference packets. Component-panel repeats use explicit record
membership instead of copies. Legacy target-conditioned choice construction is
preserved for exact reproduction and remains UNRESOLVED for new-study admission.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import inspect
from pathlib import Path
import random
import re

from . import course
from ..graph_teaching import final_panel, reference, face_corpus, face_tasks, face_roles, lessons
from ..graph_teaching.face_experiment import episode_task

SCHEMA = "cas.complementary-development-data/0.1"
SUPPLY_SCHEMA = "cas.complementary-development-supply/0.1"
PANELS = ("development_whole_tasks", "development_components", "development_earlier_skills")
DEVELOPMENT_FAMILIES = 6
LEGACY_MINIMUM_SUPPLY = 36
LIMITATIONS = {
    "study_admission": "UNRESOLVED",
    "legacy_option_construction": "UNRESOLVED_TARGET_CONDITIONED_LEGACY_CHOICES",
    "legacy_choice_detail": "Canonical _family/_reach_options and public_records retain their target-conditioned choice behavior; reproduction does not establish independent choices.",
    "transfer_scope": "Application candidates have 8-10 nodes versus 3-4-node CFC training; structural/size transfer, not same-difficulty transfer.",
    "earlier_skill_scope": "Historically examined development role-recognition audit; shared authored family/support metadata is not novel topology evidence.",
    "custody_scope": "Caller-supplied conservative exclusions identify retained history; complete does not prove absolute historical nonexposure or authenticated custody.",
    "final_scope": "Unused eligible topologies are public candidate supply only; no final questions, answers, panel, protocol or scoring freeze is constructed.",
    "learning_scope": "Pure source construction is not learner execution, retained skill, improved learning or accepted study evidence.",
}
require, digest = course.require, course.digest


def _sha(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            "DEVELOPMENT_SHA256")


def _checked_exclusions(exclusions):
    fields = {"schema", "complete", "inventory_sha256", "archives", "excluded_topologies", "failures",
              "rule", "actual_neural_presentations", "actual_provider_calls"}
    require(type(exclusions) is dict and set(exclusions) == fields, "DEVELOPMENT_EXCLUSION_FIELDS")
    require(exclusions["schema"] == "cas.complementary-exclusions/0.1"
            and exclusions["complete"] is True and exclusions["failures"] == [],
            "COMPLEMENTARY_HISTORICAL_EXCLUSIONS_INCOMPLETE")
    _sha(exclusions["inventory_sha256"])
    for key in ("actual_neural_presentations", "actual_provider_calls"):
        require(type(exclusions[key]) is int and exclusions[key] == 0, "DEVELOPMENT_EXCLUSION_EXECUTION_BOUND")
    require(type(exclusions["rule"]) is str and bool(exclusions["rule"]), "DEVELOPMENT_EXCLUSION_RULE")
    banned = exclusions["excluded_topologies"]
    require(type(banned) is list and len(banned) <= 4096 and banned == sorted(set(banned)),
            "DEVELOPMENT_EXCLUSION_TOPOLOGIES")
    for key in banned:
        _sha(key)
    archives = exclusions["archives"]
    require(type(archives) is list and 0 < len(archives) <= 256, "DEVELOPMENT_EXCLUSION_ARCHIVES")
    for row in archives:
        require(type(row) is dict and set(row) == {"path", "sha256", "graph_records", "topologies", "errors"}
                and type(row["path"]) is str and bool(row["path"]) and row["errors"] == [], "DEVELOPMENT_EXCLUSION_ARCHIVE")
        _sha(row["sha256"])
        for key in ("graph_records", "topologies"):
            require(type(row[key]) is int and row[key] >= 0, "DEVELOPMENT_EXCLUSION_ARCHIVE_COUNT")
    require(len({r["path"] for r in archives}) == len(archives), "DEVELOPMENT_EXCLUSION_DUPLICATE_ARCHIVE")
    return set(banned)


def reach_availability(shape):
    """Structural existence of direct/via/absent cases; no labels or questions.

    The canonical enumerator emits small DAGs. A non-direct reachable node gives
    a via case; a distinct unreachable node gives an absent case. No family,
    reference answer, choice list, question or record is produced by this probe.
    """
    require(type(shape) is dict and 0 < len(shape) <= 10, "DEVELOPMENT_SHAPE")
    require(all(type(k) is str and type(v) in (tuple, list) and v
                and all(type(p) is str for p in v) and len(v) == len(set(v))
                for k, v in shape.items()), "DEVELOPMENT_SHAPE_EDGES")
    nodes = set(shape) | {part for parts in shape.values() for part in parts}
    require(len(nodes) <= 10, "DEVELOPMENT_SHAPE_BOUND")
    available = {"direct": False, "via": False, "absent": False}
    for root, parts in shape.items():
        direct, reached, pending = set(parts), set(), list(parts)
        while pending:
            node = pending.pop()
            if node not in reached:
                reached.add(node)
                pending.extend(shape.get(node, ()))
        require(root not in reached, "DEVELOPMENT_SHAPE_CYCLE")
        available["direct"] |= bool(direct)
        available["via"] |= bool(reached - direct)
        available["absent"] |= bool(nodes - reached - {root})
    return available


def _source_identity(topology_key):
    modules = (course, course.adapter, course.verified_training, final_panel, reference,
               face_corpus, face_tasks, face_roles, lessons)
    files = {Path(module.__file__).resolve() for module in modules} | {Path(__file__).resolve()}
    files.update((Path(__file__).with_name("data.py").resolve(),
                  Path(inspect.getsourcefile(episode_task)).resolve(),
                  Path(inspect.getsourcefile(final_panel.Graph)).resolve()))
    key_source = inspect.getsourcefile(topology_key)
    require(key_source is not None and Path(key_source).is_file(), "DEVELOPMENT_TOPOLOGY_SOURCE_REQUIRED")
    files.add(Path(key_source).resolve())
    root = Path(__file__).resolve().parents[2]
    rows = []
    for path in sorted(files):
        require(path.is_relative_to(root), "DEVELOPMENT_SOURCE_SCOPE")
        raw = path.read_bytes()
        rows.append({"path": path.relative_to(root).as_posix(), "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    return {"files": rows, "topology_callable": topology_key.__module__ + "." + topology_key.__qualname__}


def _supply(exclusions, topology_key):
    banned = _checked_exclusions(exclusions)
    require(callable(topology_key), "DEVELOPMENT_TOPOLOGY_CALLABLE")
    available, rows, seen = {}, [], set()
    patterns = final_panel.enumerate_patterns()
    require(type(patterns) is dict and 0 < len(patterns) <= 4096, "DEVELOPMENT_ENUMERATOR_BOUND")
    for shape in patterns.values():
        key = topology_key(shape)
        _sha(key)
        require(key not in seen, "DEVELOPMENT_TOPOLOGY_COLLISION")
        seen.add(key)
        reach = reach_availability(shape)
        excluded = key in banned
        eligible = not excluded and all(reach.values())
        if eligible:
            available[key] = shape
        rows.append({"topology": key, "shape_sha256": digest(shape), "stats": final_panel.pattern_stats(shape),
                     "excluded": excluded, "reach_availability": reach, "eligible": eligible})
    require(len(available) >= LEGACY_MINIMUM_SUPPLY, "COMPLEMENTARY_PANEL_SUPPLY_BELOW_36")
    selected = sorted(available)[:DEVELOPMENT_FAMILIES]
    for row in rows:
        row["development_index"] = selected.index(row["topology"]) if row["topology"] in selected else None
    result = {"schema": SUPPLY_SCHEMA, "exclusions_sha256": digest(exclusions),
              "source_identity": _source_identity(topology_key), "topologies": sorted(rows, key=lambda r: r["topology"]),
              "development_topologies": selected, "excluded_topologies_outside_enumerator": sorted(banned - seen),
              "counts": {"enumerated": len(rows), "excluded": sum(r["excluded"] for r in rows),
                         "potential": sum(not r["excluded"] for r in rows), "eligible": len(available),
                         "potential_without_all_reach": sum(not r["excluded"] and not r["eligible"] for r in rows),
                         "development_families": len(selected), "unconstructed_eligible": len(available) - len(selected)},
              "selection": "First six sorted eligible topology keys, matching canonical development allocation; no new final allocation.",
              "limitations": deepcopy(LIMITATIONS)}
    result["supply_sha256"] = digest(result)
    return result, [(key, available[key]) for key in selected]


def candidate_supply(exclusions, *, topology_key):
    """Return public topology metadata only; no task constructor is called."""
    return _supply(exclusions, topology_key)[0]


def build_development(exclusions, *, topology_key):
    """Construct the legacy development split only; never call build_panels.

    ``tasks`` contains one exact copy per record ID, including private teacher
    fields. ``panel_record_ids`` preserves canonical order and explicit repeated
    membership. ``panel_tasks`` reconstructs an old development panel if needed.
    """
    source_before = digest(exclusions)
    supply, selected = _supply(exclusions, topology_key)
    tasks, memberships, panel_ids, families = {}, {}, {name: [] for name in PANELS}, []

    def add(task, panel):
        record_id = task["record_id"]
        require(type(record_id) is str and record_id, "DEVELOPMENT_RECORD_ID")
        if record_id in tasks:
            require(digest(tasks[record_id]) == digest(task), "DEVELOPMENT_RECORD_ID_CONFLICT")
        else:
            tasks[record_id] = deepcopy(task)
            memberships[record_id] = []
        require(record_id not in panel_ids[panel], "DEVELOPMENT_DUPLICATE_WITHIN_PANEL")
        panel_ids[panel].append(record_id)
        memberships[record_id].append(panel)

    for index, (topology, shape) in enumerate(selected):
        family_id = "complementary_" + topology
        family = final_panel._family(shape, 2026091600 + index)
        graph = family["graph"]
        records = deepcopy(family["records"])
        reached = final_panel._reach_case(family, ("direct", "via", "absent")[index % 3])
        require(reached is not None, "DEVELOPMENT_REACH_SUPPLY_MISMATCH")
        root, part, kind, direct = reached
        question = {"op": "REACHED_VIA", "idea": root, "part": part}
        records.append(lessons._record("complementary_audit", index, "whole_part", "REACHED_VIA",
            graph, question, kind, final_panel._reach_options(random.Random(index), kind, direct),
            reference.derivation_for("REACHED_VIA", graph, question)))
        require(len(records) == 3, "DEVELOPMENT_THREE_CANONICAL_TASKS")
        for record in records:
            question = {"op": record["op"], **record["question"]}
            task = course._record_task(graph, question, record["options"], record["correct"], family_id)
            task["split"] = "development"
            add(task, PANELS[0])
        add(task, PANELS[1])
        families.append({"family_id": family_id, "split": "development", "topology": topology,
                         "stats": final_panel.pattern_stats(shape)})
    built = face_corpus.families()  # authored family/support metadata, no final episodes
    earlier_families = face_corpus.by_split(face_corpus.DEVELOPMENT, built)
    require(len(earlier_families) == 16, "DEVELOPMENT_EARLIER_FAMILY_COUNT")
    for family in earlier_families:
        require(family["split"] == "development", "DEVELOPMENT_EARLIER_SPLIT")
        for face in face_roles.FACE_NUMBERS:
            episode = face_tasks.compile_episode(family, face, face_roles.ROLE_FROM_CONTENT, arm="none", built=built)
            task = episode_task(episode)
            task["audit_face"] = face
            task["semantic_question_id"] = task["record_id"]
            add(task, PANELS[2])
    require([len(panel_ids[name]) for name in PANELS] == [18, 6, 96]
            and len(tasks) == 114, "DEVELOPMENT_PANEL_COUNTS")
    require(source_before == digest(exclusions), "DEVELOPMENT_EXCLUSIONS_MUTATED")
    result = {"schema": SCHEMA, "status": "DEVELOPMENT_ONLY_LEGACY_REPRODUCTION_NOT_STUDY_ADMISSION",
              "split": "development", "candidate_supply": supply, "families": families,
              "tasks": list(tasks.values()), "panel_record_ids": panel_ids, "memberships": memberships,
              "counts": {"unique_records": len(tasks), "panel_memberships": sum(map(len, panel_ids.values())),
                         "duplicate_component_memberships": len(panel_ids[PANELS[1]]),
                         "panels": {key: len(value) for key, value in panel_ids.items()},
                         "unique_operations": dict(Counter(row["op"] for row in tasks.values()))},
              "limitations": deepcopy(LIMITATIONS), "final_questions_constructed": 0,
              "final_answers_constructed": 0, "neural_calls": 0, "provider_calls": 0}
    result["data_sha256"] = digest(result)
    return result


def validate_development(document, *, exclusions, topology_key):
    """Reconstruct exactly from supplied source/exclusions, still development-only.

    Canonical comparison rejects resealed altered records and bool/number aliases.
    The caller must independently pin the source/exclusions when custody matters.
    """
    require(type(document) is dict, "DEVELOPMENT_DOCUMENT_TYPE")
    body = deepcopy(document)
    identity = body.pop("data_sha256", None)
    require(type(identity) is str and identity == digest(body), "DEVELOPMENT_DATA_HASH")
    expected = build_development(exclusions, topology_key=topology_key)
    require(digest(document) == digest(expected), "DEVELOPMENT_SOURCE_RECONSTRUCTION")
    return document


def panel_tasks(document, panel):
    """Copy records in explicit membership order; these still include teachers."""
    require(panel in PANELS, "DEVELOPMENT_PANEL_UNKNOWN")
    by_id = {row["record_id"]: row for row in document["tasks"]}
    require(len(by_id) == len(document["tasks"]), "DEVELOPMENT_DUPLICATE_RECORD")
    return [deepcopy(by_id[record_id]) for record_id in document["panel_record_ids"][panel]]
