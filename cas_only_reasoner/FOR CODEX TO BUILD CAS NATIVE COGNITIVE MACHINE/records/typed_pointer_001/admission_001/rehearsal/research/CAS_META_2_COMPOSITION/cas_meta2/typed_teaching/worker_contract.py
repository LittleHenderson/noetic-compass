"""Pure admission contract for the complete typed teaching engineering run.

No provider calls, tensors, main-target loading or semantic checking occur here.
The sealed course includes audit lineage: only model_packet may reach a learner.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

CANDIDATE = "CNCM_TYPED_COURSE_ACCEPTANCE_001"
CONFIG_SCHEMA = "cncm.typed-course-worker-config/0.1"
JOB_PATTERN = r"cas-meta2-typedcourse-\d{14}-[a-f0-9]{8}"
SOURCE_SEED = 101
MODEL_SEED = ENCODER_SEED = 20260916
MAX_MEMBER_BYTES = 4 * 1024 ** 2
# Full encoding, baseline, teaching, final evaluation and replay share this cap.
# The first GPU attempt exposed substantial CPU preprocessing/validation cost.
MAX_WALL_SECONDS = 3300
COURSE_PATH = "records/typed_course_001/checks_002/public_course.json"
TOKENIZER_PATH = "records/typed_interface_001/checks_002/training_tokenizer.json"
MATERIAL = {
    COURSE_PATH: {"bytes": 4165195, "sha256": "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987"},
    TOKENIZER_PATH: {"bytes": 447140, "sha256": "bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c"},
}
TOKENIZER_DIGEST = "5ce5aa8b26334eb517c820ebae66216fe20439d1f91ede0ada6e64cc03edf798"
WHEEL_PREFIX = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
WHEELS = {
    "casformer_reference-0.1.0-py3-none-any.whl": "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee",
    "cas_neural_cjt-0.2.0-py3-none-any.whl": "6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9",
}
DESIGN = {
    "candidate": CANDIDATE, "purpose": "COMPLETE_EXPOSED_TRAINING_COURSE_ENGINEERING_ACCEPTANCE",
    "source_seed": SOURCE_SEED, "condition": "ALT_COMPONENT_WHOLE",
    "model_seed": MODEL_SEED, "encoder_seed": ENCODER_SEED,
    "registry_packets": 564, "main_presentations": 1152, "main_optimizer_updates": 160,
    "validation_replay_updates": 2, "global_optimizer_updates_max": 162,
    "training_slot_calls": 4613, "training_core_forward_calls": 17178,
    "rounds": 16, "depths": [1, 2, 4, 8], "d_model": 64, "max_input_tokens": 32768,
    "prediction_depth": 8, "initial_and_final_prediction_packets": 564,
    "optimizer_class": "torch.optim.AdamW", "optimizer_foreach": False, "optimizer_fused": False,
    "optimizer_config": {"learning_rate": 0.003, "weight_decay": 0.01, "betas": [0.9, 0.999], "eps": 1e-8},
    "training_loss": "RAW_FIELD_MEAN_TASK_MEAN_BATCH_MEAN",
    "reporting_loss": "ALPHABET_LOG_NORMALIZED_FIELDS_SEPARATE_FROM_TRAINING",
    "main_targets": "DERIVE_PRIVATELY_ONLY_AFTER_EXACT_PUBLIC_PREDICTION_SEAL",
    "replay": "INDEPENDENT_SAME_PROCESS_RESTORE_FROM_PRE_LAST_UPDATE_CHECKPOINT",
    "replay_counts": "TWO_ADDITIONAL_BRANCH_STEPS_AND_ALL_THEIR_EXPOSURES_ARE_SEPARATE",
    "package": "PINNED_COURSE_TOKENIZER_SOURCES_AND_WHEELS_NO_PRIVATE_TARGET_BUNDLE",
    "source_attestation": "FRESH_PROCESS_MANIFEST_LOADER_COMPILES_EXACT_SOURCE_BYTES",
    "projection_scope": "ALL_PUBLIC_FRAMES_NO_TEACHER_FILTER_NO_SEMANTIC_REPAIR",
    "partial_course_is_success": False, "learning_advantage_established": False,
    "max_wall_seconds": MAX_WALL_SECONDS, "jobs": 1, "automatic_retries": 0,
    "reservation_usd": "7.00", "region": "us-west-2", "instance_type": "g7.2xlarge",
    "launch_enabled": False,
}


def require(condition, reason):
    if not condition:
        raise ValueError("TYPED_WORKER:" + reason)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def read_pinned(root, name, expected):
    path = Path(root).resolve(strict=True) / name
    require(not path.is_symlink() and path.resolve(strict=True).is_relative_to(Path(root).resolve()), "MATERIAL_PATH")
    require(path.is_file() and path.stat().st_size == expected["bytes"] <= MAX_MEMBER_BYTES, "MATERIAL_SIZE:" + name)
    with path.open("rb") as stream:
        raw = stream.read(MAX_MEMBER_BYTES + 1)
    require(len(raw) == expected["bytes"] and sha256(raw).hexdigest() == expected["sha256"], "MATERIAL_BYTES:" + name)
    return raw


def validate_schedule(frozen):
    """Cross-check an already byte-pinned course; never reconstruct its teacher."""
    require(type(frozen) is dict and frozen.get("source_seed") == SOURCE_SEED
            and type(frozen["source_seed"]) is int
            and frozen.get("condition") == DESIGN["condition"], "COURSE_IDENTITY")
    registry, batches, presentations = frozen["registry"], frozen["batches"], frozen["presentations"]
    require(type(registry) is list and len(registry) == 564
            and type(batches) is list and len(batches) == 160
            and type(presentations) is list and len(presentations) == 1152, "COURSE_COUNTS")
    ids = [r["record_id"] for r in registry]
    require(len(set(ids)) == 564 and ids == sorted(ids), "REGISTRY_IDENTITY")
    by_id = {r["record_id"]: r for r in registry}
    flat, presentation_ids, seen_depths, kinds = [], [], set(), Counter()
    for cursor, batch in enumerate(batches):
        require(type(batch) is dict and set(batch) == {"cursor", "depth", "occurrence_ids", "phase",
                "presentation_ids", "record_ids", "round"}, "BATCH_FIELDS")
        require(type(batch["cursor"]) is int and batch["cursor"] == cursor, "BATCH_CURSOR")
        require(type(batch["depth"]) is int and batch["depth"] in DESIGN["depths"], "BATCH_DEPTH")
        require(type(batch["round"]) is int and 1 <= batch["round"] <= 16, "BATCH_ROUND")
        require(type(batch["record_ids"]) is list and 1 <= len(batch["record_ids"]) <= 8
                and len(batch["record_ids"]) == len(batch["occurrence_ids"]) == len(batch["presentation_ids"]), "BATCH_SHAPE")
        seen_depths.add(batch["depth"])
        for occurrence, record in zip(batch["occurrence_ids"], batch["record_ids"]):
            require(record in by_id, "BATCH_UNKNOWN_RECORD")
            flat.append({"occurrence_id": occurrence, "record_id": record})
            kinds[by_id[record]["query"]["kind"]] += 1
        presentation_ids.extend(batch["presentation_ids"])
    require(flat == presentations and len({r["occurrence_id"] for r in flat}) == 1152, "PRESENTATION_JOIN")
    require(presentation_ids == ["course-presentation-%04d" % i for i in range(1152)], "PRESENTATION_ORDER")
    require({r["record_id"] for r in flat} == set(ids) and seen_depths == set(DESIGN["depths"]), "COMPLETE_COVERAGE")
    require(dict(sorted(kinds.items())) == {"analogy": 80, "context": 80, "correspondence": 208,
        "definition": 80, "edge_account": 80, "parts": 213, "reach": 315, "role_set": 96}, "KIND_COUNTS")
    return {"registry_packets": len(ids), "main_presentations": len(flat), "groups": len(batches),
            "kind_counts": dict(sorted(kinds.items())), "planned_compute_only": True}


def load_material(root):
    from .tokenization import FrameTokenizer
    frozen = json.loads(read_pinned(root, COURSE_PATH, MATERIAL[COURSE_PATH]))
    schedule = validate_schedule(frozen)
    tokenizer = FrameTokenizer.from_dict(json.loads(read_pinned(root, TOKENIZER_PATH, MATERIAL[TOKENIZER_PATH])))
    require(tokenizer.digest == TOKENIZER_DIGEST and tokenizer.to_dict()["max_tokens"] == 32768, "TOKENIZER_IDENTITY")
    return frozen, tokenizer, schedule


def public_packets(frozen):
    from .course import model_packet
    # model_packet validates the closed public fields only. validate_course would
    # call the teacher and must not be substituted on this prediction path.
    for row in frozen["registry"]:
        yield row["record_id"], model_packet(frozen, row["record_id"])


def input_inventory(root):
    root = Path(root).resolve(strict=True)
    names = set(MATERIAL) | {WHEEL_PREFIX + name for name in WHEELS}
    for prefix in ("cncm", "research/CAS_META_2_COMPOSITION/cas_meta2"):
        paths = list((root / prefix).rglob("*.py"))
        require(paths, "SOURCE_PACKAGE_MISSING:" + prefix)
        for path in paths:
            require(not path.is_symlink() and path.resolve(strict=True).is_relative_to(root), "SOURCE_PATH")
            names.add(path.relative_to(root).as_posix())
    rows = []
    for name in sorted(names):
        path = root / name
        require(path.is_file() and path.stat().st_size <= MAX_MEMBER_BYTES, "INPUT_MEMBER_BOUND:" + name)
        raw = path.read_bytes()
        row = {"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
        if name in MATERIAL:
            require({k: row[k] for k in ("bytes", "sha256")} == MATERIAL[name], "INPUT_MATERIAL_PIN")
        if name.startswith(WHEEL_PREFIX):
            require(row["sha256"] == WHEELS[name[len(WHEEL_PREFIX):]], "INPUT_WHEEL_PIN")
        rows.append(row)
    require(len(rows) <= 2000 and sum(r["bytes"] for r in rows) <= 96 * 1024 ** 2, "INPUT_TOTAL_BOUND")
    return rows


def make_config(root, *, source_sha, job, bucket):
    require(type(source_sha) is str and re.fullmatch(r"[0-9a-f]{40}", source_sha), "SOURCE_SHA")
    require(type(job) is str and re.fullmatch(JOB_PATTERN, job), "JOB")
    require(type(bucket) is str and re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket), "BUCKET")
    rows = input_inventory(root)
    return {"schema": CONFIG_SCHEMA, "source_sha": source_sha, "job": job, "bucket": bucket,
            "design": deepcopy(DESIGN), "inputs": rows, "inputs_sha256": sha256(canonical(rows)).hexdigest()}


def validate_config(config, root):
    require(type(config) is dict and set(config) == {"schema", "source_sha", "job", "bucket", "design", "inputs", "inputs_sha256"}, "CONFIG_FIELDS")
    expected = make_config(root, source_sha=config["source_sha"], job=config["job"], bucket=config["bucket"])
    require(canonical(config) == canonical(expected), "CONFIG_IDENTITY")
    return deepcopy(config)
