"""Frozen development/final tasks from existing, historically excluded patterns."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import random

from .course import digest, require, _record_task
from ..graph_teaching import final_panel, reference, face_corpus, face_tasks, face_roles
from ..graph_teaching.face_experiment import episode_task


def build_panels(exclusions, *, topology_key):
    require(exclusions.get("complete") is True, "COMPLEMENTARY_HISTORICAL_EXCLUSIONS_INCOMPLETE")
    banned = set(exclusions["excluded_topologies"])
    available = {}
    for shape in final_panel.enumerate_patterns().values():
        key = topology_key(shape)
        if key not in banned and final_panel._supports_all_reach(shape):
            available[key] = shape
    require(len(available) >= 36, "COMPLEMENTARY_PANEL_SUPPLY_BELOW_36")
    panels = {"development_components": [], "development_whole_tasks": [],
              "development_earlier_skills": [], "final_application": [],
              "final_components": [], "final_earlier_skills": []}
    family_rows = []
    for index, (topology, shape) in enumerate(sorted(available.items())[:36]):
        split = "development" if index < 6 else "final"
        family_id = "complementary_" + topology
        family = final_panel._family(shape, 2026091600 + index)
        graph = family["graph"]
        records = deepcopy(family["records"])
        root, part, kind, direct = final_panel._reach_case(family, ("direct", "via", "absent")[index % 3])
        from ..graph_teaching import lessons
        q = {"op": "REACHED_VIA", "idea": root, "part": part}
        records.append(lessons._record("complementary_audit", index, "whole_part", "REACHED_VIA",
                       graph, q, kind, final_panel._reach_options(random.Random(index), kind, direct),
                       reference.derivation_for("REACHED_VIA", graph, q)))
        tasks = []
        for record in records:
            question = {"op": record["op"], **record["question"]}
            task = _record_task(graph, question, record["options"], record["correct"], family_id)
            task["split"] = split
            tasks.append(task)
        panels["development_whole_tasks" if split == "development" else "final_application"].extend(tasks)
        # Same-root component audit kept in same split; duplicate semantic question
        # explicitly preserved and counted, never advertised as a new family.
        panels["development_components" if split == "development" else "final_components"].append(deepcopy(tasks[-1]))
        family_rows.append({"family_id": family_id, "split": split, "topology": topology,
                            "stats": final_panel.pattern_stats(shape)})
    built = face_corpus.families()
    for split, panel in ((face_corpus.DEVELOPMENT, "development_earlier_skills"),
                         (face_corpus.FINAL_HELD_OUT, "final_earlier_skills")):
        for family in face_corpus.by_split(split, built):
          for face in face_roles.FACE_NUMBERS:
            episode = face_tasks.compile_episode(family, face, face_roles.ROLE_FROM_CONTENT,
                                                 arm="none", built=built)
            task = episode_task(episode)
            task["audit_face"] = face
            task["semantic_question_id"] = task["record_id"]
            panels[panel].append(task)
    manifest = {"schema": "cas.complementary-data/0.1", "complete": True,
                "exclusions_sha256": digest(exclusions), "families": family_rows,
                "panels": panels, "counts": {key: len(rows) for key, rows in panels.items()},
                "historically_examined_earlier_skill_audit": True,
                "novelty_class": "new directed topology, larger graph than 3-4-node CFC training",
                "envelope_amendment": "Application audit uses EXISTING 8-10-node enumerator; report as structural/size transfer, never same-difficulty transfer.",
                "coverage": {"final_operations": dict(Counter(t["op"] for t in panels["final_application"])),
                             "final_families": 30, "development_families": 6},
                "retention_rule": "RETENTION_UNASSESSED without initial measured accuracy >= 0.5"}
    manifest["data_sha256"] = digest(manifest)
    return manifest


def validate_manifest(document):
    raw = deepcopy(document)
    identity = raw.pop("data_sha256", None)
    require(identity == digest(raw), "COMPLEMENTARY_DATA_HASH")
    require(raw.get("complete") is True, "COMPLEMENTARY_DATA_NOT_FROZEN")
    families = raw["families"]
    train = {entry["topology"] for entry in families if entry["split"] == "development"}
    final = {entry["topology"] for entry in families if entry["split"] == "final"}
    require(len(train) == 6 and len(final) == 30 and not train & final,
            "COMPLEMENTARY_FAMILY_SPLIT")
    for key, count in {"final_application": 90, "final_components": 30,
                       "development_whole_tasks": 18, "development_components": 6,
                       "final_earlier_skills": 96, "development_earlier_skills": 96}.items():
        require(len(raw["panels"][key]) == count, "COMPLEMENTARY_PANEL_COUNT:" + key)
    return document
