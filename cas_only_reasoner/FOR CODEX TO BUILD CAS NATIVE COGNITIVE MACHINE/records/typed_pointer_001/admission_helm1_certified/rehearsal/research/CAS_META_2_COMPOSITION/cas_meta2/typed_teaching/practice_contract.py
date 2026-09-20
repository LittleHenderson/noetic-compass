"""Pure admission for the practice study: does more practice teach the neurons, on worlds they never practised?

Owner-approved 2026-09-18 ("Practice test"): the same machine and the same random start as the matched
study, ten passes over the course instead of one, and about one in five questions held back and never
trained on. No teacher, final panel, numerical runtime or provider is imported here.

HELD BACK BY WORLD, AND ONLY WORLDS WITH NO LOOK-ALIKE. Two adversarial pre-flight reviews (2026-09-18,
records/typed_practice_001/PREFLIGHT_REVIEW.md) showed that in this course a held-back question can reach
training through a rule twin, a worked support, a correct analogy answer, a correspondence target, or a
look-alike world whose answers transfer by position. The split therefore follows four rules, derived from
the frozen course by records/typed_practice_001/holdout_audit.py and frozen here as constants so that the
worker never reads a correct answer before training:

1. only course worlds with no shape twin anywhere in the 64-world bank are eligible;
2. a world's exposure is every other-world record that mentions it anywhere (query, arguments, cue,
   instruction, worked supports) or whose correct answers name it;
3. the five eligible worlds with the smallest exposure, ties by world id, are held back;
4. every exposure record of a held world is excluded from training.

Result on the frozen course: 5 worlds, 127 held records, 50 questions, all eight kinds; 79 records excluded
(6 of them only through their correct answers); 358 records trained. A test re-derives all of it.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import re

from . import course_plan, source
from . import matched_contract as matched

CANDIDATE = "CNCM_TYPED_PRACTICE_LEARNING_001"
CONFIG_SCHEMA = "cncm.typed-practice-worker-config/0.1"
JOB_PATTERN = r"cas-meta2-tprac-\d{14}-([a-f0-9]{8})-m-(20260917|20260918|20260919)"
CONDITION = course_plan.MIXED
MODEL_SEEDS = matched.MODEL_SEEDS
ENCODER_SEED, SOURCE_SEED = matched.ENCODER_SEED, matched.SOURCE_SEED
PASSES = 10
HELD_WORLD_COUNT = 5
# Frozen by records/typed_practice_001/holdout_audit.py (rules above); re-derived by a test.
HELD_WORLDS = (
    "world-22704554ac881d9846c94b37c5aabc5790edf38f7810692028f0b5e8ce8e4952",
    "world-28f61f2d7941a373f50285be7e57b1a9b8ec85bc0aff9e2d18c683e9f86b4547",
    "world-4090ec49174f1d031b16507663d875616c489382d0be1fdf7f4616aeb3dde9fc",
    "world-6e1fcbdadc4a1aff1b5deddf2d84b9db1ca75b2ba9bbf98e2b202145a33d14be",
    "world-98c6352de9137e679b7d2a460ab99be2791d9c719b0808b2fe3bbb09375534a9")
# Records that mention no held world in their text but whose CORRECT ANSWERS name one (analogy).
ANSWER_EXPOSED_RECORD_IDS = (
    "typed-input-092dc3b89a0480d462945ca7447bac511c81358714e48059922cd9b469f8a53e",
    "typed-input-0e7f54633dc16b4de85b9a0881fc99ec94f6a2d18d271fb121c8bf408746dff2",
    "typed-input-4ffb71835e32c454abb30ffb9648affc43f32ec27d2e5842ec2339db4dfe86b3",
    "typed-input-63c29b86b3946d0debaf34f2c4c88b409a2006323f4eb21809db621ca8585905",
    "typed-input-8c5a211e761bd9277abdab44e0539552a89994ed3e84d7b9baae720dc04dacd7",
    "typed-input-c11f4e62202a8201ca4fd7c5de058c4cd69a4be64d38c2b9003259005ac662f0")
KINDS = ("role_set", "definition", "context", "analogy", "correspondence", "parts", "edge_account", "reach")
PASS_CHECKPOINTS = (0, 1, 2, 4, 6, 8, 10)
FULL_COURSE_CHECKPOINTS = (0, 1, 10)
INTERFERENCE_UPDATES, INTERFERENCE_BATCH = 16, 8
REPLAY_UPDATES = 2
LEARNER_MAX_UPDATES_CEILING = 2048
MAX_CORE_CALLS = 600000
# Worker deadline < numeric child timeout < outer bound < guest boot watchdog < launcher wait.
WORKER_DEADLINE_SECONDS = 12300
MAX_WALL_SECONDS = 12600
RESERVATION_USD = "15.00"        # 4 h x $2.52 + $1.48 ancillary = $11.56, rounded up; owner cap $45 for 3 jobs
INSTANCE_SECONDS_MAX = 14400
DEVELOPMENT_PATH, DEVELOPMENT_PIN = matched.DEVELOPMENT_PATH, matched.DEVELOPMENT_PIN
COURSE_PATH = matched.COURSE_PATH
MATERIAL = deepcopy(matched.MATERIAL)
canonical, require = matched.canonical, matched.require
load_material, public_packets = matched.load_material, matched.public_packets
development_packets, retention_packets = matched.development_packets, matched.retention_packets
input_inventory, material_inputs = matched.input_inventory, matched.material_inputs


def parse_job(job):
    require(type(job) is str, "JOB")
    match = re.fullmatch(JOB_PATTERN, job)
    require(match is not None, "JOB")
    return CONDITION, int(match.group(2))


def _record_text(row):
    return canonical({key: value for key, value in row.items() if key != "record_id"}).decode("utf-8")


def held_worlds(frozen):
    """The five frozen held worlds, validated against the frozen course."""
    matched._frozen(frozen)
    course_worlds = {row["source_world_id"] for row in frozen["registry"]}
    require(len(HELD_WORLDS) == HELD_WORLD_COUNT and set(HELD_WORLDS) <= course_worlds, "HOLDOUT_WORLDS")
    return list(HELD_WORLDS)


def split(frozen):
    """(held_back, trained, excluded) record ids, each sorted, disjoint, covering the 564-record registry."""
    worlds = set(held_worlds(frozen))
    registry = frozen["registry"]
    held = sorted(row["record_id"] for row in registry if row["source_world_id"] in worlds)
    held_ids = set(held)
    mentioning = {row["record_id"] for row in registry if row["record_id"] not in held_ids
                  and any(world in _record_text(row) for world in worlds)}
    answer_exposed = set(ANSWER_EXPOSED_RECORD_IDS)
    require(answer_exposed <= {row["record_id"] for row in registry} and not answer_exposed & held_ids
            and not answer_exposed & mentioning, "HOLDOUT_ANSWER_EXPOSED")
    excluded_ids = mentioning | answer_exposed
    excluded = sorted(excluded_ids)
    trained = sorted(row["record_id"] for row in registry
                     if row["record_id"] not in held_ids and row["record_id"] not in excluded_ids)
    require(held and trained and len(held) + len(trained) + len(excluded) == len(registry) == 564, "HOLDOUT_SPLIT")
    by_id = {row["record_id"]: row for row in registry}
    for key in trained:
        # No trained record mentions a held world anywhere in its text (answers: ANSWER_EXPOSED_RECORD_IDS).
        require(not any(world in _record_text(by_id[key]) for world in worlds), "HOLDOUT_LEAK")
    require({by_id[k]["query"]["kind"] for k in held} == set(KINDS), "HOLDOUT_KIND_COVERAGE")
    return held, trained, excluded


def held_back_questions(frozen):
    """Held query ids -> their record ids. A question is the unit of the gate, not a record."""
    held = set(split(frozen)[0])
    questions = {}
    for row in frozen["registry"]:
        if row["record_id"] in held:
            questions.setdefault(row["query"]["query_id"], []).append(row["record_id"])
    return {key: sorted(value) for key, value in sorted(questions.items())}


def practice_schedule(frozen):
    """Ten passes of the MIXED course keeping only trained records. Returns (batches, stats)."""
    base, base_stats = matched.schedule(frozen, CONDITION)
    held, trained, excluded = split(frozen)
    keep_set = set(trained)
    one_pass = []
    for batch in base:
        keep = [at for at, key in enumerate(batch["record_ids"]) if key in keep_set]
        if not keep:
            continue
        one_pass.append({"round": batch["round"], "phase": batch["phase"], "depth": batch["depth"],
                         "source_cursor": batch["cursor"],
                         "record_ids": [batch["record_ids"][at] for at in keep],
                         "occurrence_ids": [batch["occurrence_ids"][at] for at in keep],
                         "presentation_ids": [batch["presentation_ids"][at] for at in keep]})
    batches = []
    for number in range(1, PASSES + 1):
        for batch in one_pass:
            occurrences = ["typed-occurrence-" + source.digest({"domain": "typed-practice-v1", "pass": number,
                                                               "occurrence": occurrence})
                           for occurrence in batch["occurrence_ids"]]
            batches.append({**deepcopy(batch), "cursor": len(batches), "pass": number,
                            "occurrence_ids": occurrences,
                            "presentation_ids": ["practice-p%02d-%s" % (number, p) for p in batch["presentation_ids"]]})
    require(all(key in keep_set for b in batches for key in b["record_ids"]), "HOLDOUT_TRAINED")
    require(all(len(b["occurrence_ids"]) == len(set(b["occurrence_ids"])) for b in batches), "OCCURRENCE_UNIQUE")
    counts = matched._slot_counts(frozen)
    held_ids = set(held)
    stats = {"condition": CONDITION, "source_seed": SOURCE_SEED, "passes": PASSES, "holdout_unit": "FOCUS_WORLD",
             "held_worlds": held_worlds(frozen), "updates_per_pass": len(one_pass), "main_updates": len(batches),
             "presentations_per_pass": sum(len(b["record_ids"]) for b in one_pass),
             "presentations": sum(len(b["record_ids"]) for b in batches),
             "planned_slot_core_passes": sum(counts[k] * b["depth"] for b in batches for k in b["record_ids"]),
             "presentation_slots": sum(counts[k] for b in batches for k in b["record_ids"]),
             "held_back_records": len(held), "trained_records": len(trained), "excluded_records": len(excluded),
             "held_back_questions": len(held_back_questions(frozen)),
             "held_back_kinds": dict(sorted(Counter(r["query"]["kind"] for r in frozen["registry"]
                                                   if r["record_id"] in held_ids).items())),
             "held_back_record_ids_digest": source.digest(held), "excluded_record_ids_digest": source.digest(excluded),
             "source_schedule_digest": base_stats["batches_digest"], "batches_digest": source.digest(batches),
             "actual_compute_measured": False}
    require(0 < stats["main_updates"] + INTERFERENCE_UPDATES <= LEARNER_MAX_UPDATES_CEILING, "PRACTICE_UPDATE_BOUND")
    return deepcopy(batches), stats


def interference_batches(frozen):
    """The matched interference rule, drawn only from trained records: 16 batches of 8, alternating kinds."""
    trained = set(split(frozen)[1])
    pools = {kind: sorted(row["record_id"] for row in frozen["registry"] if row["query"]["kind"] == kind
                          and row["supports"] == [] and row["record_id"] in trained)
             for kind in ("definition", "context")}
    require(all(pools.values()), "INTERFERENCE_POOL")
    count = INTERFERENCE_UPDATES * INTERFERENCE_BATCH
    records = [pools[("definition", "context")[i % 2]][(i // 2) % len(pools[("definition", "context")[i % 2]])]
               for i in range(count)]
    return [{"cursor": None, "round": 1000 + batch, "phase": "OTHER_QUESTION_RETENTION_INTERVAL", "depth": 8,
             "record_ids": records[batch * INTERFERENCE_BATCH:(batch + 1) * INTERFERENCE_BATCH],
             "occurrence_ids": ["typed-occurrence-" + source.digest({"domain": "practice-interference-v1", "ordinal": i,
                                                                     "record_id": records[i]})
                                for i in range(batch * INTERFERENCE_BATCH, (batch + 1) * INTERFERENCE_BATCH)],
             "presentation_ids": ["practice-interference-%04d" % i
                                  for i in range(batch * INTERFERENCE_BATCH, (batch + 1) * INTERFERENCE_BATCH)]}
            for batch in range(INTERFERENCE_UPDATES)]


# Registered machine and procedure fields, inherited unchanged from the matched study's design.
_INHERITED = ("d_model", "max_input_tokens", "prediction_depth", "depths", "optimizer_class", "optimizer_foreach",
              "optimizer_fused", "optimizer_config", "training_loss", "reporting_loss", "main_targets", "replay",
              "replay_counts", "package", "source_attestation", "projection_scope", "region", "instance_type")
DESIGN = {**{key: deepcopy(matched.DESIGN[key]) for key in _INHERITED},
    "candidate": CANDIDATE, "purpose": "DOES_PRACTICE_TEACH_THE_NEURONS_ON_WORLDS_THEY_NEVER_PRACTISED",
    "partial_course_is_success": False, "jobs": 1, "automatic_retries": 0, "reservation_usd": RESERVATION_USD,
    "instance_seconds_max": INSTANCE_SECONDS_MAX, "launch_enabled": False,
    "owner_approval": "2026-09-18 AskUserQuestion answer 'Practice test (Recommended)'",
    "condition": CONDITION, "source_seed": SOURCE_SEED, "encoder_seed": ENCODER_SEED,
    "model_seeds": list(MODEL_SEEDS), "passes": PASSES, "holdout_unit": "FOCUS_WORLD",
    "holdout_rule": "NO_SHAPE_TWIN_IN_BANK_FEWEST_MENTIONING_RECORDS_TIES_BY_ID_FIRST_5_ALL_MENTIONING_EXCLUDED",
    "pass_checkpoints": list(PASS_CHECKPOINTS), "full_course_checkpoints": list(FULL_COURSE_CHECKPOINTS),
    "interference_updates": INTERFERENCE_UPDATES, "interference_batch": INTERFERENCE_BATCH,
    "interference_trained_records_only": True, "held_worlds": list(HELD_WORLDS), "replay_updates": REPLAY_UPDATES,
    "initialization": "REGISTERED_RANDOM_SAME_AS_MATCHED_STUDY_PER_MODEL_SEED",
    "learner_max_updates_ceiling": LEARNER_MAX_UPDATES_CEILING, "max_core_calls": MAX_CORE_CALLS,
    "worker_deadline_seconds": WORKER_DEADLINE_SECONDS, "max_wall_seconds": MAX_WALL_SECONDS,
    "registered_learner_unchanged": True,
    "boundary": "Typed exposed-course practice on one teaching order. Held-back questions are about five course "
                "worlds the machine never practised on (same world sizes and question kinds as training); the "
                "development panel is out-of-distribution ten-node parts/reach. No protected final-study, general "
                "CAS architecture, or full-machine claim.",
    "learning_on_held_back_established": False}


def make_config(root, *, source_sha, job, bucket, model_seed):
    require(type(source_sha) is str and re.fullmatch(r"[0-9a-f]{40}", source_sha), "SOURCE_SHA")
    require(type(model_seed) is int and model_seed in MODEL_SEEDS, "MODEL_SEED")
    require(parse_job(job) == (CONDITION, model_seed) and re.fullmatch(JOB_PATTERN, job).group(1) == source_sha[:8],
            "JOB_PARAMETERS")
    require(type(bucket) is str and re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket), "BUCKET")
    frozen, _, development = load_material(root)
    batches, stats = practice_schedule(frozen)
    held, trained, excluded = split(frozen)
    retention = list(retention_packets(frozen))
    interference = interference_batches(frozen)
    rows = input_inventory(root)
    design = {**deepcopy(DESIGN), "model_seed": model_seed, "schedule": stats,
        "held_back_record_ids": held, "excluded_record_ids": excluded,
        "development_digest": development["development_digest"],
        "development_packets": len(development["packets"]), "retention_packets": len(retention),
        "retention_record_ids_digest": source.digest([key for key, _ in retention]),
        "interference_batches_digest": source.digest(interference)}
    return {"schema": CONFIG_SCHEMA, "source_sha": source_sha, "job": job, "bucket": bucket,
        "design": design, "inputs": rows, "inputs_sha256": sha256(canonical(rows)).hexdigest()}


def validate_config(config, root):
    require(type(config) is dict and set(config) == {"schema", "source_sha", "job", "bucket", "design", "inputs",
                                                     "inputs_sha256"}, "CONFIG_FIELDS")
    _, seed = parse_job(config["job"])
    expected = make_config(root, source_sha=config["source_sha"], job=config["job"], bucket=config["bucket"],
                           model_seed=seed)
    require(canonical(config) == canonical(expected), "CONFIG_IDENTITY")
    return deepcopy(expected)
