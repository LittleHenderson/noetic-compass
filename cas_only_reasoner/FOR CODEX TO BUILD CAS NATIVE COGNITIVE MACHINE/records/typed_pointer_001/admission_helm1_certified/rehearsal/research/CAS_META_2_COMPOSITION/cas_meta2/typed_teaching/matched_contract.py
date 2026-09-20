"""Pure admission for paired full-course order, development and retention runs.

The preserved ALT course supplies exact public records and authored occurrence
lineage. MIXED changes only their scheduling. No teacher, final panel, numerical
runtime or provider is imported here. Planned work is not observed compute.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

from . import course_plan, source, worker_contract as baseline

CANDIDATE = "CNCM_TYPED_MATCHED_LEARNING_001"
CONFIG_SCHEMA = "cncm.typed-matched-worker-config/0.1"
JOB_PATTERN = r"cas-meta2-tmat-\d{14}-([a-f0-9]{8})-(a|m)-(20260917|20260918|20260919)"
CONDITIONS = (course_plan.ALT, course_plan.MIXED)
MODEL_SEEDS = (20260917, 20260918, 20260919)
ENCODER_SEED, SOURCE_SEED = 20260916, 101
MAX_WALL_SECONDS = 3300
DEVELOPMENT_PATH = "records/typed_matched_001/development_001/compact_development.json"
# Frozen only after the separate public-only constructor's guarded receipt.
DEVELOPMENT_PIN = {"bytes": 685549, "sha256": "5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4"}
COURSE_PATH, TOKENIZER_PATH = baseline.COURSE_PATH, baseline.TOKENIZER_PATH
TOKENIZER_DIGEST = baseline.TOKENIZER_DIGEST
WHEEL_PREFIX, WHEELS = baseline.WHEEL_PREFIX, baseline.WHEELS
MAX_MEMBER_BYTES = baseline.MAX_MEMBER_BYTES
MATERIAL = {**deepcopy(baseline.MATERIAL), DEVELOPMENT_PATH: deepcopy(DEVELOPMENT_PIN)}
canonical = baseline.canonical

DESIGN = {**deepcopy(baseline.DESIGN), "candidate": CANDIDATE,
    "purpose": "PAIRED_EXPOSED_COURSE_ORDER_DEVELOPMENT_AND_RETENTION",
    "source_seed": SOURCE_SEED, "encoder_seed": ENCODER_SEED,
    "model_seeds": list(MODEL_SEEDS), "conditions": list(CONDITIONS),
    "development_checkpoints": [0, 40, 80, 120, 160],
    "retention_checkpoints": [160, 176], "interference_optimizer_updates": 16,
    "interference_presentations": 128, "interference_depth": 8,
    "interference_kinds": ["definition", "context"],
    "learner_optimizer_updates_max": 176, "global_optimizer_updates_max": 178,
    "retention_policy": "TRAINING_PARTS_REACH_WITH_WORKED_SUPPORTS_REMOVED_AND_RECORDS_RESEALED",
    "interference_policy": "ALTERNATE_UNASSISTED_DEFINITION_CONTEXT_SORTED_REGISTRY_ROUND_ROBIN_16_BATCHES_OF_8",
    "retention_boundary": "OTHER_QUESTION_TEACHING_SAME_PUBLIC_BANK_NO_PARTS_REACH_EDGE_CORRECTIONS_NOT_CONTENT_UNSEEN",
    "development_boundary": "PUBLIC_DEVELOPMENT_TOPOLOGIES_NO_TRAINING_CORRECTIONS_NO_FINAL_PANEL",
    "comparator_boundary": "CURRICULUM_ORDER_COMPARISON_NOT_CAS_ARCHITECTURE_SUPERIORITY",
    "ordinary_graph_equals_alt": True, "main_training_types_unchanged": True,
    "main_updates": 160, "max_wall_seconds": MAX_WALL_SECONDS,
    "paired_initialization_required": True, "paired_initialization_observed": False,
    "equal_planned_work_is_equal_wall_time": False,
    "learning_advantage_established": False}
DESIGN.pop("condition")
DESIGN.pop("model_seed")


def require(value, reason):
    if not value:
        raise ValueError("TYPED_MATCHED:" + reason)


def parse_job(job):
    require(type(job) is str, "JOB")
    match = re.fullmatch(JOB_PATTERN, job)
    require(match is not None, "JOB")
    return (course_plan.ALT if match.group(2) == "a" else course_plan.MIXED, int(match.group(3)))


def _frozen(frozen):
    # Verify the exact preserved course before trusting its record/lineage join.
    raw = (source.canonical(frozen) + "\n").encode()
    pin = baseline.MATERIAL[COURSE_PATH]
    require(len(raw) == pin["bytes"] and sha256(raw).hexdigest() == pin["sha256"], "COURSE_BYTES")
    baseline.validate_schedule(frozen)


def _slot_counts(frozen):
    nodes = {w["world_id"]: len(w["nodes"]) for w in frozen["bank"]["worlds"]}
    result = {}
    for row in frozen["registry"]:
        kind, count = row["query"]["kind"], nodes[row["source_world_id"]]
        values = {"role_set": 6, "definition": 3, "context": 1 + count, "analogy": 1,
                  "correspondence": 1 + count, "parts": count, "edge_account": count * count, "reach": 1}
        require(kind in values, "SLOT_KIND")
        result[row["record_id"]] = values[kind]
    return result


def schedule(frozen, condition):
    """Return (batches, planned_stats) joined by exact occurrence identity."""
    require(type(condition) is str and condition in CONDITIONS, "CONDITION")
    _frozen(frozen)
    original = {p["occurrence_id"]: p["record_id"] for p in frozen["presentations"]}
    original_occurrences = {o["occurrence_id"]: o for o in frozen["plan"]["occurrences"]}
    require(len(original) == len(original_occurrences) == 1152 and set(original) == set(original_occurrences), "OCCURRENCE_COVERAGE")
    plans = {c: course_plan.compile_plan(SOURCE_SEED, c) for c in (*CONDITIONS, course_plan.DAG)}
    for plan in plans.values():
        occurrences = {o["occurrence_id"]: o for o in plan["occurrences"]}
        require(source.canonical(occurrences) == source.canonical(original_occurrences), "OCCURRENCE_LINEAGE_CHANGED")
    rebuilt = {c: [{**b, "record_ids": [original[o] for o in b["occurrence_ids"]]}
                   for b in plan["batches"]] for c, plan in plans.items()}
    require(source.canonical(rebuilt[course_plan.ALT]) == source.canonical(frozen["batches"]), "ALT_BATCHES_CHANGED")
    require(rebuilt[course_plan.ALT] == rebuilt[course_plan.DAG], "DAG_ALT_AUDIT")
    require(rebuilt[course_plan.ALT] != rebuilt[course_plan.MIXED], "CONTRAST_NOT_DISTINCT")
    def membership(batches):
        return Counter((key, batch["depth"]) for batch in batches for key in batch["record_ids"])
    require(membership(rebuilt[course_plan.ALT]) == membership(rebuilt[course_plan.MIXED]), "PACKET_DEPTH_MULTISET")
    # All differences must be inside the two declared supplement groups.
    for left, right in zip(rebuilt[course_plan.ALT], rebuilt[course_plan.MIXED]):
        if not left["phase"].startswith("SUPPLEMENT_"):
            require(left == right, "NONSUPPLEMENT_CHANGED")
    batches = rebuilt[condition]
    counts = _slot_counts(frozen)
    work = sum(counts[k] * b["depth"] for b in batches for k in b["record_ids"])
    slot_calls = sum(counts[k] for b in batches for k in b["record_ids"])
    require(len(batches) == 160 and sum(len(b["record_ids"]) for b in batches) == 1152
            and work == 17178 and slot_calls == 4613, "MATCHED_MAIN_WORK")
    stats = {"condition": condition, "source_seed": SOURCE_SEED, "groups": 160, "presentations": 1152,
        "unique_packets": 564, "presentation_slots": slot_calls, "planned_slot_core_passes": work,
        "packet_depth_multiset_digest": source.digest(sorted((key, depth, n) for (key, depth), n in membership(batches).items())),
        "source_plan_digest": plans[condition]["plan_digest"], "batches_digest": source.digest(batches),
        "occurrence_lineage_digest": source.digest(original_occurrences),
        "ordinary_graph_equals_alt": True, "contrast_distinct": True, "actual_compute_measured": False}
    return deepcopy(batches), stats


def public_packets(frozen):
    yield from baseline.public_packets(frozen)


def retention_packets(frozen):
    """Unassisted source-identical parts/reach probes; never teacher-derived."""
    from . import course
    _frozen(frozen)
    seen = {}
    for record in frozen["registry"]:
        if record["query"]["kind"] not in ("parts", "reach"):
            continue
        row = deepcopy(record); row["supports"] = []
        row["record_id"] = "typed-input-" + source.digest({k: v for k, v in row.items() if k != "record_id"})
        public = {"focus_world_id": row["source_world_id"], "worlds": frozen["bank"]["worlds"], "bank": frozen["bank"]["bank"]}
        packet = course.validate_model_packet({"source": public, "record": row})
        if row["record_id"] in seen:
            require(source.canonical(seen[row["record_id"]]) == source.canonical(packet), "RETENTION_ID_COLLISION")
        seen[row["record_id"]] = packet
    require(seen, "RETENTION_EMPTY")
    for key in sorted(seen):
        yield key, deepcopy(seen[key])


def interference_batches(frozen):
    _frozen(frozen)
    pools = {kind: sorted(row["record_id"] for row in frozen["registry"] if row["query"]["kind"] == kind and row["supports"] == [])
             for kind in ("definition", "context")}
    require(all(pools.values()), "INTERFERENCE_POOL")
    records = [pools[("definition", "context")[i % 2]][(i // 2) % len(pools[("definition", "context")[i % 2]])]
               for i in range(128)]
    return [{"cursor": 160 + batch, "round": 17 + batch, "phase": "OTHER_QUESTION_RETENTION_INTERVAL", "depth": 8,
             "record_ids": records[batch*8:(batch+1)*8],
             "occurrence_ids": ["typed-occurrence-" + source.digest({"domain": "matched-interference-v1", "ordinal": i, "record_id": records[i]})
                                for i in range(batch*8, (batch+1)*8)],
             "presentation_ids": ["interference-presentation-%04d" % i for i in range(batch*8, (batch+1)*8)]}
            for batch in range(16)]


def material_inputs(root):
    require(type(DEVELOPMENT_PIN) is dict, "DEVELOPMENT_PIN_NOT_FROZEN")
    baseline.read_pinned(root, DEVELOPMENT_PATH, DEVELOPMENT_PIN)
    return [{"path": name, **deepcopy(pin)} for name, pin in sorted({**baseline.MATERIAL, DEVELOPMENT_PATH: DEVELOPMENT_PIN}.items())]


def input_inventory(root):
    rows = baseline.input_inventory(root)
    development = next(row for row in material_inputs(root) if row["path"] == DEVELOPMENT_PATH)
    result = sorted([*rows, development], key=lambda r: r["path"])
    require(len(result) <= 2000 and sum(r["bytes"] for r in result) <= 96 * 1024 ** 2, "INPUT_TOTAL_BOUND")
    return result


def load_material(root):
    from .development import expand_development
    frozen, tokenizer, _ = baseline.load_material(root)
    material_inputs(root)
    development = expand_development(json.loads(baseline.read_pinned(root, DEVELOPMENT_PATH, DEVELOPMENT_PIN)))
    require(development["tokenizer_digest"] == tokenizer.digest and development["main_targets_constructed"] == 0
            and development["final_questions_constructed"] == 0, "DEVELOPMENT_BOUNDARY")
    return frozen, tokenizer, development


def development_packets(development):
    """Stable declared panel order; exact source material is admitted separately."""
    from . import course
    require(development.get("main_targets_constructed") == 0 and development.get("final_questions_constructed") == 0,
        "DEVELOPMENT_BOUNDARY")
    packets = {}
    for packet in development["packets"]:
        checked = course.validate_model_packet(packet)
        key = checked["record"]["record_id"]
        require(key not in packets and checked["record"]["supports"] == [] and checked["record"]["query"]["kind"] in ("parts", "reach"),
            "DEVELOPMENT_PACKET")
        packets[key] = checked
    require(len(packets) == 59, "DEVELOPMENT_COUNT")
    return packets


def make_config(root, *, source_sha, job, bucket, condition, model_seed):
    require(type(source_sha) is str and re.fullmatch(r"[0-9a-f]{40}", source_sha), "SOURCE_SHA")
    require(type(condition) is str and condition in CONDITIONS, "CONDITION")
    require(type(model_seed) is int and model_seed in MODEL_SEEDS, "MODEL_SEED")
    require(parse_job(job) == (condition, model_seed) and re.fullmatch(JOB_PATTERN, job).group(1) == source_sha[:8], "JOB_PARAMETERS")
    require(type(bucket) is str and re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket), "BUCKET")
    frozen, _, development = load_material(root)
    batches, stats = schedule(frozen, condition)
    retention = list(retention_packets(frozen))
    interference = interference_batches(frozen)
    rows = input_inventory(root)
    design = {**deepcopy(DESIGN), "condition": condition, "model_seed": model_seed,
        "schedule": stats, "development_digest": development["development_digest"],
        "development_packets": len(development["packets"]), "retention_packets": len(retention),
        "retention_record_ids_digest": source.digest([key for key, _ in retention]),
        "interference_batches_digest": source.digest(interference),
        "interference_slot_calls": sum(_slot_counts(frozen)[key] for b in interference for key in b["record_ids"])}
    return {"schema": CONFIG_SCHEMA, "source_sha": source_sha, "job": job, "bucket": bucket,
        "design": design, "inputs": rows, "inputs_sha256": sha256(canonical(rows)).hexdigest()}


def validate_config(config, root):
    require(type(config) is dict and set(config) == {"schema", "source_sha", "job", "bucket", "design", "inputs", "inputs_sha256"}, "CONFIG_FIELDS")
    condition, seed = parse_job(config["job"])
    expected = make_config(root, source_sha=config["source_sha"], job=config["job"], bucket=config["bucket"],
                           condition=condition, model_seed=seed)
    require(canonical(config) == canonical(expected), "CONFIG_IDENTITY")
    return deepcopy(expected)
