"""Target-free lineage for all 1,152 complementary teaching presentations.

Only literal schedule declarations are read from preserved source. Selector
logic is implemented here; legacy task/answer compilers are never imported.
This is a planned curriculum, not admitted inference or measured learning.
"""
from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from . import source

SCHEMA = "cas.typed-teaching-course-plan/0.1"
ALT, MIXED, DAG = "ALT_COMPONENT_WHOLE", "MIXED_SAME_ITEMS", "ORDINARY_DEPENDENCY_GRAPH"
CONDITIONS = (ALT, MIXED, DAG)
SEEDS = (101, 202, 303)
PARTNER_POLICY = "AUTHORED_ORDER_CYCLIC_AFTER_FOCUS_TRAINING_SAME_ARCHETYPE_FIRST_DIFFERENT_DOMAIN"
ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
LEGACY_FILES = (
    "graph_teaching/face_schedule.py", "graph_teaching/face_roles.py",
    "graph_teaching/face_tasks.py", "recurrent_cjt/course.py", "recurrent_cjt/recurrence.py",
    "rpm_cfc_constructor/diagnosis.py", "complementary_teaching/course.py",
)
SEMANTIC_CHANGES = (
    "Legacy choices, correct indices, private targets and answer-shaped options are not reproduced.",
    "All roles remain; Face5 question selection awaits the declared public-source-only rule.",
    "Recognition retains its source face as private lineage, not a learner-visible role label; focal excerpt construction remains separate.",
    "Analogy uses a separately frozen public training bank; the legacy hidden chosen partner is not an answer authority.",
    "Correspondence target-world selection and symmetry-equivalent answers require explicit public query semantics.",
    "Static edge accounts preserve graph declarations, not invented temporal process order.",
    "Worked support source families and requested faces are retained; new support payloads need the separate typed teaching admission.",
)
require, digest, canonical = source.require, source.digest, source.canonical


def _ast(path):
    return ast.parse(path.read_bytes(), str(path))


def _literal(path, name):
    values = [node.value for node in _ast(path).body if isinstance(node, ast.Assign)
              and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
              and node.targets[0].id == name]
    require(len(values) == 1, "TYPED_COURSE_LITERAL:" + name)
    return ast.literal_eval(values[0])


def source_profile():
    paths = [Path(__file__), *(PACKAGE / name for name in LEGACY_FILES), ROOT / "cncm/rpa_learning_match.py"]
    rows = []
    for path in paths:
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT), "TYPED_COURSE_SOURCE_SCOPE")
        raw = path.read_bytes()
        require(len(raw) <= 1024 * 1024, "TYPED_COURSE_SOURCE_BOUND")
        rows.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    body = {"schema": "cas.typed-teaching-course-source-profile/0.1", "files": sorted(rows, key=lambda r: r["path"]),
            "training_source_profile": source.source_profile(),
            "source_role": "PRESERVED_SELECTOR_CODE_AND_LITERAL_DECLARATIONS_NOT_LEGACY_TASK_EXECUTION"}
    return {**body, "profile_digest": digest(body)}


def _contract():
    schedule = PACKAGE / "graph_teaching/face_schedule.py"
    recurrence = PACKAGE / "recurrent_cjt/recurrence.py"
    complementary = PACKAGE / "complementary_teaching/course.py"
    require(_literal(complementary, "SEEDS") == SEEDS, "TYPED_COURSE_SOURCE_SEEDS_CHANGED")
    require(_literal(complementary, "CONDITIONS")[:2] == (ALT, MIXED), "TYPED_COURSE_SOURCE_CONDITIONS_CHANGED")
    stages = _literal(schedule, "STAGE_FACES")
    require([(s["stage"], s["face"]) for s in stages] == [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 5)],
            "TYPED_COURSE_STAGE_CONTRACT")
    cohorts, cohort_size = (_literal(schedule, name) for name in ("CFC_COHORTS", "CFC_CUBES_PER_COHORT"))
    require(type(cohorts) is int and cohorts == 6 and type(cohort_size) is int and cohort_size == 4,
            "TYPED_COURSE_COHORT_CONTRACT")
    depths = _literal(recurrence, "ROUND_DEPTH_SCHEDULE")
    require(len(depths) == 16 and Counter(depths) == {1: 4, 2: 4, 4: 4, 8: 4}, "TYPED_COURSE_DEPTH_CONTRACT")
    tree = _ast(PACKAGE / "rpm_cfc_constructor/diagnosis.py")
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "phase_batches"]
    require(len(functions) == 1, "TYPED_COURSE_BATCH_FUNCTION")
    values = [node.value for node in functions[0].body if isinstance(node, ast.Assign)
              and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "declared"]
    require(len(values) == 1, "TYPED_COURSE_BATCH_LITERAL")
    batches = ast.literal_eval(values[0])
    require(batches == {"WITHIN_CUBE": [8, 8, 8, 4], "ACROSS_FACE": [8, 4],
                        "RETURN_TO_CUBE": [8], "OLD_SKILL_MAINTENANCE": [8]}, "TYPED_COURSE_BATCH_CONTRACT")
    return {"stages": stages, "cohorts": cohorts, "cohort_size": cohort_size, "depths": depths, "batches": batches}


def _supports(family, offset, families):
    pool = [f for f in families if f["family_id"] != family["family_id"]
            and not f["family_id"].startswith(family["family_id"])]
    start = offset % len(pool)
    rotated = pool[start:] + pool[:start]
    selected, domains = [], set()
    for row in rotated:
        if row["domain"] not in domains:
            selected.append(row); domains.add(row["domain"])
        if len(selected) == 3: break
    for row in rotated:
        if len(selected) == 3: break
        if row not in selected: selected.append(row)
    require(len(selected) == 3, "TYPED_COURSE_SUPPORT_COUNT")
    return [f["family_id"] for f in selected]


def _other_faces(face, offset):
    others = [value for value in range(1, 7) if value != face]
    index = offset % len(others)
    return (others[index:] + others[:index])[:2]


def event_key(event):
    """Exact preserved face_schedule.event_key, not a legacy learner record ID."""
    return "|".join((event["movement"], event["profile"], event["family_id"], str(event["face"]),
                     ",".join(event.get("support_ids") or ()), str(event.get("offset", 0))))


def _events(round_index, families, contract):
    start = round_index % contract["cohorts"] * contract["cohort_size"]
    cohort = (families[start:] + families[:start])[:contract["cohort_size"]]
    events = []
    for position, family in enumerate(cohort):
        for stage in contract["stages"]:
            events.append({"movement": "WITHIN_CUBE", "stage": stage["stage"], "stage_id": stage["stage_id"],
                "round": round_index, "profile": "FACE_APPLY", "face": stage["face"], "family_id": family["family_id"],
                "support_ids": _supports(family, (round_index + position + stage["stage"]) % len(families), families)
                               if stage["stage"] < 7 else [], "offset": position, "assisted": True})
    for face in range(1, 7):
        events.append({"movement": "ACROSS_FACE", "decision": "role_recognition", "round": round_index,
            "profile": "ROLE_FROM_CONTENT", "face": face, "family_id": cohort[face % len(cohort)]["family_id"],
            "support_ids": [], "group": _other_faces(face, (round_index + face) % 5 + 1), "assisted": False})
        events.append({"movement": "ACROSS_FACE", "decision": "content_comparison", "round": round_index,
            "profile": "FACE_APPLY", "face": face, "family_id": cohort[(face + 1) % len(cohort)]["family_id"],
            "support_ids": [], "offset": face, "assisted": False})
    for family in cohort:
        for decision, face, offset in (("missing_face", 4, 0), ("whole_idea", 5, 1)):
            events.append({"movement": "RETURN_TO_CUBE", "decision": decision, "round": round_index,
                "profile": "FACE_APPLY", "face": face, "family_id": family["family_id"],
                "support_ids": [], "offset": offset, "assisted": False})
    require(len(events) == 48, "TYPED_COURSE_EVENT_COUNT")
    return events


def _occurrence(seed, round_index, logical_phase, ordinal, event, families, *, teaching_role, pair_id=None,
                part_label=None, maintenance_source_round=None):
    lineage = {"round_index": round_index, "logical_phase": logical_phase, "source_ordinal": ordinal,
               "source_round_index": event["round"], "maintenance_source_round_index": maintenance_source_round,
               "legacy_pair_id": pair_id}
    profile, face = event["profile"], event["face"]
    def partner(family_id):
        if face != 4:
            return None
        focus = families[family_id]
        pool = [row for row in families.values() if row["split"] == "training"
                and row["archetype"] == focus["archetype"]]
        position = next(i for i, row in enumerate(pool) if row["family_id"] == family_id)
        rotated = pool[position + 1:] + pool[:position + 1]
        candidates = [row["family_id"] for row in rotated if row["domain"] != focus["domain"]]
        require(candidates, "TYPED_COURSE_TRAINING_PARTNER_MISSING")
        return candidates[0]
    intent = {"profile": profile, "face": face, "family_id": event["family_id"],
        "support_family_ids": list(event["support_ids"]),
        "support_intents": [{"family_id": value, "face": face, "profile": "FACE_APPLY",
                             "training_partner_family_id": partner(value)} for value in event["support_ids"]],
        "training_partner_family_id": partner(event["family_id"]),
        "whole_label": families[event["family_id"]]["labels"][0], "part_label": part_label,
        "question_selection": ("PENDING_PUBLIC_SOURCE_FACE5_RULE" if profile == "FACE_APPLY" and face == 5 else
                               "ROUND_INDEXED_PUBLIC_LABEL" if profile == "REACHED_VIA" else
                               "DECLARED_WHOLE_INVENTORY" if profile == "LIST_PARTS" else "DECLARED_FACE_OR_FOCAL_EXCERPT"),
        "focal_excerpt_required": profile == "ROLE_FROM_CONTENT"}
    return {"occurrence_id": "typed-occurrence-" + digest({"seed": seed, **lineage}),
            "legacy_event_key": event_key(event) if pair_id is None else None,
            "source_event": deepcopy(event), "lineage": lineage, "teaching_role": teaching_role, "intent": intent}


def dependency_batches(nodes, *, batch_size=8):
    require(type(nodes) is list and 0 < len(nodes) <= 16 and type(batch_size) is int and 0 < batch_size <= 16,
            "TYPED_COURSE_DAG_BOUND")
    for row in nodes:
        require(type(row) is dict and set(row) == {"id", "prerequisites"} and type(row["id"]) is str
                and type(row["prerequisites"]) is list and all(type(v) is str for v in row["prerequisites"])
                and len(row["prerequisites"]) == len(set(row["prerequisites"])), "TYPED_COURSE_DAG_ROW")
    known = {row["id"] for row in nodes}
    require(len(known) == len(nodes) and all(set(row["prerequisites"]) <= known and row["id"] not in row["prerequisites"]
                                           for row in nodes), "TYPED_COURSE_DAG_REFERENCES")
    completed, result = set(), []
    while len(completed) != len(nodes):
        ready = [row["id"] for row in nodes if row["id"] not in completed and set(row["prerequisites"]) <= completed]
        require(ready, "TYPED_COURSE_DAG_CYCLE")
        selected = ready[:batch_size]; result.append(selected); completed.update(selected)
    return result


def compile_plan(seed, condition, *, expected_source_profile_digest=None):
    require(type(seed) is int and seed in SEEDS, "TYPED_COURSE_SEED")
    require(type(condition) is str and condition in CONDITIONS, "TYPED_COURSE_CONDITION")
    profile = source_profile()
    if expected_source_profile_digest is not None:
        require(expected_source_profile_digest == profile["profile_digest"], "TYPED_COURSE_SOURCE_PROFILE_CHANGED")
    contract, families = _contract(), list(source.training_families())
    index = {f["family_id"]: f for f in families}
    shift = SEEDS.index(seed)
    depths = list(contract["depths"][shift:] + contract["depths"][:shift])
    occurrences, batches, traces = [], [], []
    presentation_cursor = 0
    def append_batch(round_index, phase, depth, rows):
        nonlocal presentation_cursor
        batches.append({"cursor": len(batches), "round": round_index + 1, "phase": phase, "depth": depth,
            "occurrence_ids": [row["occurrence_id"] for row in rows],
            "presentation_ids": ["course-presentation-%04d" % (presentation_cursor + i) for i in range(len(rows))]})
        presentation_cursor += len(rows)
    for round_index, depth in enumerate(depths):
        events = _events(round_index, families, contract)
        for phase in ("WITHIN_CUBE", "ACROSS_FACE", "RETURN_TO_CUBE"):
            selected = [event for event in events if event["movement"] == phase]
            rows = [_occurrence(seed, round_index, phase, i, event, index, teaching_role="CFC_FOUNDATION")
                    for i, event in enumerate(selected)]
            occurrences.extend(rows)
            start = 0
            for size in contract["batches"][phase]:
                append_batch(round_index, phase, depth, rows[start:start + size]); start += size
            require(start == len(rows), "TYPED_COURSE_PHASE_SHAPE")
        cohort = list(dict.fromkeys(event["family_id"] for event in events))
        pairs = []
        for family_id in cohort:
            family = index[family_id]; whole = family["labels"][0]
            labels = sorted(label for label in family["labels"] if label != whole)
            for slot in range(2):
                part = labels[(round_index + slot) % len(labels)]
                cq, wq = {"op": "REACHED_VIA", "idea": whole, "part": part}, {"op": "LIST_PARTS", "idea": whole}
                pair_id = digest([family_id, cq, wq])
                pair = {}
                for role, operation in (("COMPONENT", "REACHED_VIA"), ("WHOLE", "LIST_PARTS")):
                    event = {"movement": "SUPPLEMENT", "round": round_index, "profile": operation, "face": 5,
                        "family_id": family_id, "support_ids": [], "offset": slot, "assisted": False}
                    pair[role] = _occurrence(seed, round_index, role, len(pairs), event, index,
                        teaching_role=role, pair_id=pair_id, part_label=part if role == "COMPONENT" else None)
                pairs.append(pair)
        require(len(pairs) == 8, "TYPED_COURSE_EIGHT_PAIRS")
        rotation = (seed + round_index + 1) % 8
        pairs = pairs[rotation:] + pairs[:rotation]
        components, wholes = ([pair[role] for pair in pairs] for role in ("COMPONENT", "WHOLE"))
        occurrences.extend(components + wholes)
        if condition == ALT:
            supplements = [components, wholes]
        elif condition == MIXED:
            supplements = [[row for position in range(start, start + 4) for row in (components[position], wholes[position])]
                           for start in (0, 4)]
        else:
            nodes, mapping = [], {}
            for position, pair in enumerate(pairs):
                component, whole = "component:%d" % position, "whole:%d" % position
                nodes.extend(({"id": component, "prerequisites": []}, {"id": whole, "prerequisites": [component]}))
                mapping[component], mapping[whole] = pair["COMPONENT"], pair["WHOLE"]
            planned = dependency_batches(nodes)
            supplements = [[mapping[key] for key in batch] for batch in planned]
            traces.append({"round": round_index + 1, "nodes": nodes, "batches": planned,
                           "pair_ids": [pair["COMPONENT"]["lineage"]["legacy_pair_id"] for pair in pairs]})
        require([len(rows) for rows in supplements] == [8, 8], "TYPED_COURSE_SUPPLEMENT_GROUPS")
        for position, rows in enumerate(supplements):
            append_batch(round_index, "SUPPLEMENT_%d" % (position + 1), depth, rows)
        maintenance_round = max(0, round_index - contract["cohorts"])
        maintenance = [event for event in _events(maintenance_round, families, contract) if event["movement"] == "RETURN_TO_CUBE"]
        rows = [_occurrence(seed, round_index, "OLD_SKILL_MAINTENANCE", i, event, index,
                    teaching_role="MAINTENANCE", maintenance_source_round=maintenance_round) for i, event in enumerate(maintenance)]
        occurrences.extend(rows); append_batch(round_index, "OLD_SKILL_MAINTENANCE", depth, rows)
    ids = [row["occurrence_id"] for row in occurrences]
    require(len(ids) == len(set(ids)) == 1152 and len(batches) == 160, "TYPED_COURSE_COMPLETE_OCCURRENCE_SHAPE")
    require(Counter(key for batch in batches for key in batch["occurrence_ids"]) == Counter(ids), "TYPED_COURSE_OCCURRENCE_COVERAGE")
    counts = {"presentations": len(ids), "groups": len(batches), "rounds": 16,
        "by_role": dict(sorted(Counter(row["teaching_role"] for row in occurrences).items())),
        "by_profile": dict(sorted(Counter(row["intent"]["profile"] for row in occurrences).items())),
        "by_face": dict(sorted(Counter(str(row["intent"]["face"]) for row in occurrences).items())),
        "worked_support_presentations": sum(len(row["intent"]["support_intents"]) for row in occurrences),
        "unique_query_families": len({row["intent"]["family_id"] for row in occurrences}),
        "batch_depth_units_planned": sum(row["depth"] for row in batches),
        "sample_core_passes_planned": sum(row["depth"] * len(row["occurrence_ids"]) for row in batches),
        "compute_measured": False}
    body = {"schema": SCHEMA, "source_seed": seed, "condition": condition, "source_profile": profile,
        "depths": depths, "occurrences": occurrences, "batches": batches, "counts": counts,
        "ordinary_graph_policy": {"scope": "SUPPLEMENTS_ONLY_FOUNDATION_AND_MAINTENANCE_UNCHANGED",
            "edge_meaning": "COMPONENT_BEFORE_WHOLE_TEACHING_POLICY_NOT_LOGICAL_NECESSITY",
            "release": "AFTER_PREREQUISITE_BATCH_COMMIT_PLANNED_ONLY", "traces": traces,
            "same_order_as_alt_for_current_eight_pair_policy": condition == DAG},
        "maintenance_policy": "max(0, round_index-6): retained declared legacy choice, not recovered necessity",
        "comparison_partner_policy": PARTNER_POLICY + "; authored curriculum graph selection, not an answer or unbiased random pairing",
        "semantic_changes": list(SEMANTIC_CHANGES), "status": "TARGET_FREE_LINEAGE_PLAN_NOT_EXECUTION_ADMISSION"}
    require(source_profile() == profile, "TYPED_COURSE_SOURCE_CHANGED_DURING_PLAN")
    return {**body, "plan_digest": digest(body)}


def validate_plan(plan):
    source._bounded(plan)
    require(type(plan) is dict and type(plan.get("source_seed")) is int
            and type(plan.get("source_profile")) is dict, "TYPED_COURSE_PLAN_FIELDS")
    expected = compile_plan(plan["source_seed"], plan.get("condition"),
        expected_source_profile_digest=plan.get("source_profile", {}).get("profile_digest"))
    require(canonical(plan) == canonical(expected), "TYPED_COURSE_PLAN_RECONSTRUCTION")
    return deepcopy(expected)
