"""Pure admission for the pointer study: does a machine that points at the question's own input learn
answers about worlds it never read?

Owner-approved 2026-09-19: option 1, "pointer answers plus the checkpoint check", after both corrections
were accepted. The course, the hold-out, the teaching order, the ten passes and the random start are the
practice study's, reused BY IMPORT and never re-derived, so the two studies are comparable question for
question. What changes is the machine's relation to its input: one focus world is read as a small directed
graph, the question is expressed by pointing at that graph's nodes, and the answer is a pointer into the
input instead of a label drawn from a fixed bank. No teacher, final panel, numerical runtime or provider
is imported here.

DELIBERATE OPEN ITEMS, each written as a mechanism waiting for a measured decision, never guessed:

* ``REMOVALS`` -- the per-question lists already solved by a registered flag rule (review FP2) or by a
  registered rank/order rule (review DG3). It is an explicit, typed, currently EMPTY placeholder. While it
  is empty, ``relational_population`` refuses to be read as a finished population
  (``RELATIONAL_POPULATION_UNRECONCILED``).
* ``MAIN_COUNTERS`` -- the pointer machine's own counter key set (INTERFACE_SPEC_POINTER section 1). The
  planned-work FORMULA is registered in ``DESIGN["planned_work"]``; the key set is not guessed.
* Two decisions moved AFTER the interface spec was written at HEAD ``7276f4f2``, and this module carries
  them as recorded status rather than as settled choices: HEAD ``6cb0b348`` reopens the node rank decision
  (a rank-only single-flag rule eats 4 of the 9 eligible held ``reach`` questions), and
  ``DESIGN_DRAFT_v0.2.md`` section 6.4 measures that the input's own ``contains`` adjacency already answers
  every eligible held ``parts`` and ``edge_account`` question with no learned weights. Both narrow the
  RELATIONAL tier, so they are lens A / owner decisions, not this file's.

THE GATE IS KEYED ON THE RELATIONAL TIER (review FP1): copying one input flag alone passes the practice
gate (definition 5 + context 5 held questions, b=10, c=0, p=0.0009765625), so a gain on the DIRECT_READ
kinds alone must never produce the primary label. The all-kinds result is a reported flag, never the label.

Why MATERIAL carries the eighteen practice checkpoints: the checkpoint check restores the three practice
checkpoints per seed and compares the registered ``^6`` sub-block, and the launch-time ``git_package_bytes``
scope admits ``records/`` paths only when the new contract lists them in MATERIAL (pipeline review RK5).
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import importlib.util
from pathlib import Path
import re

from . import course_plan, matched_contract as matched, practice_contract as practice, source

# `canonical` and `require` are the shared pair, so every failure raises `ValueError("TYPED_MATCHED:" + code)`.
canonical, require = matched.canonical, matched.require

CANDIDATE = "CNCM_TYPED_POINTER_LEARNING_001"
CONFIG_SCHEMA = "cncm.typed-pointer-worker-config/0.1"
STUDY_TOKEN = "tpntr"
JOB_PATTERN = r"cas-meta2-tpntr-\d{14}-([a-f0-9]{8})-m-(20260917|20260918|20260919)"
# Bucket = job + "-807562639912"; 63 characters is the maximum this pattern allows (RK4).
BUCKET_PATTERN = r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]"
BUCKET_SUFFIX = "-807562639912"

CONDITION = practice.CONDITION
MODEL_SEEDS = practice.MODEL_SEEDS
SOURCE_SEED, ENCODER_SEED = practice.SOURCE_SEED, practice.ENCODER_SEED
PASSES = practice.PASSES
PASS_CHECKPOINTS = practice.PASS_CHECKPOINTS
FULL_COURSE_CHECKPOINTS = practice.FULL_COURSE_CHECKPOINTS
INTERFERENCE_UPDATES, INTERFERENCE_BATCH = practice.INTERFERENCE_UPDATES, practice.INTERFERENCE_BATCH
REPLAY_UPDATES = practice.REPLAY_UPDATES
# Registered envelope carried over from the practice study. Cost for the new machine is UNMEASURED (DG9).
LEARNER_MAX_UPDATES_CEILING = practice.LEARNER_MAX_UPDATES_CEILING
MAX_CORE_CALLS = practice.MAX_CORE_CALLS
WORKER_DEADLINE_SECONDS = practice.WORKER_DEADLINE_SECONDS
MAX_WALL_SECONDS = practice.MAX_WALL_SECONDS
RESERVATION_USD = practice.RESERVATION_USD
INSTANCE_SECONDS_MAX = practice.INSTANCE_SECONDS_MAX

# Reused UNCHANGED by import: the hold-out must stay byte-identical to the practice study (test P1).
digest = source.digest
split = practice.split
held_worlds = practice.held_worlds
held_back_questions = practice.held_back_questions
practice_schedule = practice.practice_schedule
interference_batches = practice.interference_batches
retention_packets = practice.retention_packets
development_packets = practice.development_packets
load_material = practice.load_material
public_packets = practice.public_packets
material_inputs = practice.material_inputs

# The three tiers, fixed before the run. Primary label: RELATIONAL. TEXT is reported, never labelled on.
DIRECT_READ = ("definition", "context")
RELATIONAL = ("parts", "edge_account", "reach", "correspondence", "analogy")
TEXT = ("role_set",)
TIERS = {"DIRECT_READ": DIRECT_READ, "RELATIONAL": RELATIONAL, "TEXT": TEXT}
require(sorted([*DIRECT_READ, *RELATIONAL, *TEXT]) == sorted(practice.KINDS)
        and len({*DIRECT_READ, *RELATIONAL, *TEXT}) == len(practice.KINDS), "TIERS_COVERAGE")

# Smallest b with 2**-b <= 0.01 at c = 0: 2**-7 = 0.0078125 <= 0.01 (test P12/design re-derives it).
MIN_PASSING_B = 7

# ---------------------------------------------------------------------------------------------------
# The 18 checkpoint pins, inlined from records/typed_pointer_001/pre_design/contract_pins/checkpoint_pins.json
# (generated by make_pins.py beside it; test P3 compares every value against that JSON).
#
# Inlined rather than read at import time ON PURPOSE: the pins JSON is not a MATERIAL entry, so a
# packaged worker would not be shipped it, and an import-time read would fail the whole job before any
# work was done. Keys are CNCM-root-relative and carry EXACTLY `bytes` and `sha256` (worker_contract.py:26-29).
# ---------------------------------------------------------------------------------------------------
CHECKPOINT_PINS = {
    "records/typed_practice_001/receipt_20260917/checkpoints/final.pt":
        {"bytes": 1717107, "sha256": "24686285c3618b2f352dc3f245bd82de1a2bb07e989c1082c6f57c3d891a333c"},
    "records/typed_practice_001/receipt_20260917/checkpoints/final_checkpoint.json":
        {"bytes": 22953, "sha256": "95e86d62a3ac70f21d523c232bb830330ca78992c0546a6c62c7316eaf55ea36"},
    "records/typed_practice_001/receipt_20260917/checkpoints/initial.pt":
        {"bytes": 1583505, "sha256": "0c1af5abb80cec2f67373fbf51c49d6e02f2edb4dc957de7bc8b9b494df98e7f"},
    "records/typed_practice_001/receipt_20260917/checkpoints/initial_checkpoint.json":
        {"bytes": 22913, "sha256": "b9d7712a23096baba2e2df9433a3f8d19778c0d0a0b17658ea297e66d08b7a30"},
    "records/typed_practice_001/receipt_20260917/checkpoints/pass_01.pt":
        {"bytes": 1717107, "sha256": "c562469a930818cef8a8d1eea3d9d986bb40c87023640424a45fa7cee19a97d4"},
    "records/typed_practice_001/receipt_20260917/checkpoints/pass_01_checkpoint.json":
        {"bytes": 22941, "sha256": "8f201e058c0a86d4b7820d679dc89769ee23f0db3b72e1175cb59249e753bfab"},
    "records/typed_practice_001/receipt_20260918/checkpoints/final.pt":
        {"bytes": 1717171, "sha256": "01cabdac9f1c01efe445859ae743aa50a7600e884fdc12a11803b49a8e0424e4"},
    "records/typed_practice_001/receipt_20260918/checkpoints/final_checkpoint.json":
        {"bytes": 22953, "sha256": "b4342a8ce3b2775ef617f51ab98fcc4f7f921f922378f1a023edebf13db26067"},
    "records/typed_practice_001/receipt_20260918/checkpoints/initial.pt":
        {"bytes": 1583569, "sha256": "21e8758c7ec5b37da2bf741b714a2a958303f0ba20962697e410cf800382c6b3"},
    "records/typed_practice_001/receipt_20260918/checkpoints/initial_checkpoint.json":
        {"bytes": 22914, "sha256": "93abe51582d0b93ebe2579546801259f458823c57c7aaf0c8fc6a4e150e77e90"},
    "records/typed_practice_001/receipt_20260918/checkpoints/pass_01.pt":
        {"bytes": 1717107, "sha256": "460250c30a7e96b8eb0f426a16ffb2b070b493d969e427a3c7feb22e9e82a091"},
    "records/typed_practice_001/receipt_20260918/checkpoints/pass_01_checkpoint.json":
        {"bytes": 22946, "sha256": "09e90c83dcfc17335f82868393aedb14eb3df9aa3b5a60fb708c09bfef08ec52"},
    "records/typed_practice_001/receipt_20260919/checkpoints/final.pt":
        {"bytes": 1717107, "sha256": "9cca11430a0488bb8e211f8adf291999f179ae8d20a95631145d4f40763422b9"},
    "records/typed_practice_001/receipt_20260919/checkpoints/final_checkpoint.json":
        {"bytes": 22953, "sha256": "c1ac9c3b783d2a7c02295270fb51e20177f5b30a2725c8334f1d4e1b94fae17b"},
    "records/typed_practice_001/receipt_20260919/checkpoints/initial.pt":
        {"bytes": 1583569, "sha256": "90cb22f297f4e8fe9e3585e9fa74ab6565f47fafa81d8941341a2b091d4de656"},
    "records/typed_practice_001/receipt_20260919/checkpoints/initial_checkpoint.json":
        {"bytes": 22914, "sha256": "7e3d9386ee9b36d1b51f9573d3cf56a1eb52b242a2b7f2b012ecfb9e1967d182"},
    "records/typed_practice_001/receipt_20260919/checkpoints/pass_01.pt":
        {"bytes": 1717107, "sha256": "31334ab72bbaad57d15a8557bb4ca7e36e2ad8181732281f4520f3e412fd2f87"},
    "records/typed_practice_001/receipt_20260919/checkpoints/pass_01_checkpoint.json":
        {"bytes": 22941, "sha256": "b58e8a3feda8957f9b649c7e68d30b36f9e95ac0c055a6beb2aee5dd616e7f30"},
}
CHECKPOINT_PINS_COUNT = 18
CHECKPOINT_PINS_BYTES = 15259777
require(len(CHECKPOINT_PINS) == CHECKPOINT_PINS_COUNT, "CHECKPOINT_PINS_COUNT")
require(all(set(pin) == {"bytes", "sha256"} for pin in CHECKPOINT_PINS.values()), "CHECKPOINT_PIN_KEYS")
require(sum(pin["bytes"] for pin in CHECKPOINT_PINS.values()) == CHECKPOINT_PINS_BYTES, "CHECKPOINT_PINS_BYTES")
require(not set(CHECKPOINT_PINS) & set(practice.MATERIAL), "CHECKPOINT_PINS_OVERLAP")

# practice.MATERIAL plus the 18 checkpoint rows. Nothing else is added and no row gains a key.
MATERIAL = {**deepcopy(practice.MATERIAL), **deepcopy(CHECKPOINT_PINS)}
require(set(CHECKPOINT_PINS) <= set(MATERIAL) and len(MATERIAL) == 21, "CHECKPOINT_PINS_MATERIAL")
require(all(set(row) == {"bytes", "sha256"} for row in MATERIAL.values()), "MATERIAL_ROW_KEYS")


def _checkpoint_rows(root):
    """The 18 shipped checkpoints read off disk and re-checked against their pins, as inventory rows."""
    rows = []
    for name in sorted(CHECKPOINT_PINS):
        path = Path(root) / name
        require(path.is_file() and not path.is_symlink(), "MATERIAL_PATH:" + name)
        raw = path.read_bytes()
        require(len(raw) <= matched.MAX_MEMBER_BYTES, "INPUT_MEMBER_BOUND:" + name)
        row = {"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
        require({key: row[key] for key in ("bytes", "sha256")} == CHECKPOINT_PINS[name], "MATERIAL_BYTES:" + name)
        rows.append(row)
    return rows


def input_inventory(root):
    """practice.input_inventory(root) plus the 18 checkpoint rows, sorted by path, bound re-checked.

    Without the checkpoint rows the launch-time package scope rejects the files the checkpoint check needs
    (`PRACTICE_SOURCE_MEMBER_SCOPE`, pipeline review RK5).
    """
    root = Path(root).resolve(strict=True)
    rows = [*practice.input_inventory(root), *_checkpoint_rows(root)]
    rows.sort(key=lambda row: row["path"])
    require(len({row["path"] for row in rows}) == len(rows), "INPUT_ROW_IDENTITY")
    require(len(rows) <= 2000 and sum(row["bytes"] for row in rows) <= 96 * 1024 ** 2, "INPUT_TOTAL_BOUND")
    return rows


# ---------------------------------------------------------------------------------------------------
# The pointer machine's planned work. DG10: the practice study's DESIGN carries OLD-MACHINE work counts
# (`planned_slot_core_passes` 124510, `presentation_slots` 32280) that this machine does not have, so its
# own formula is registered here instead: one packet forward per presentation, and K shared
# message-passing rounds per packet regardless of the batch's depth (DG1).
# `relations` is the formula in machine-readable form: result = schedule_stat x multiplier. The result
# names are provisional; the OPEN decision `MAIN_COUNTERS` fixes the key set that the learner must match.
# ---------------------------------------------------------------------------------------------------
PLANNED_WORK_ROUNDS = 8
PLANNED_WORK = {
    "unit": "PACKET_FORWARD",
    "rounds": PLANNED_WORK_ROUNDS,
    "relations": (
        ("packet_forward_calls", "presentations", 1),
        ("core_forward_calls", "presentations", PLANNED_WORK_ROUNDS),
        ("core_forward_attempts", "presentations", PLANNED_WORK_ROUNDS),
        ("sample_core_passes", "presentations", PLANNED_WORK_ROUNDS),
        ("prediction_calls", "presentations", 1),
        ("private_loss_plan_calls", "presentations", 1),
        ("staged_batches", "main_updates", 1),
        ("backward_calls", "main_updates", 1),
        ("optimizer_updates", "main_updates", 1),
    ),
}

# OPEN: the pointer machine's own counter key set. `typed_practice_worker.py:361` compares the canonical
# bytes of the summed per-update deltas and `counter_delta` (`typed_course_worker.py:55-59`,
# "COUNTER_FIELDS") requires the two snapshots' key sets to match EXACTLY, so one extra or missing key
# fails MAIN_TRAINING_COUNTERS after the spend. The learner's `counters` dict and this function must be
# derived from one shared source of truth. Supply the names once lens B fixes the head set; do not guess.
MAIN_COUNTERS = None


def expected_main_delta(stats):
    """The planned work of the main-training phase, from the registered formula and the OPEN counter set."""
    require(MAIN_COUNTERS is not None, "MAIN_COUNTERS_OPEN")
    require(type(MAIN_COUNTERS) is tuple and len(set(MAIN_COUNTERS)) == len(MAIN_COUNTERS), "MAIN_COUNTERS")
    by_name = {name: stats[key] * multiplier for name, key, multiplier in PLANNED_WORK["relations"]}
    require(set(MAIN_COUNTERS) == set(by_name), "MAIN_COUNTERS")
    return {name: by_name[name] for name in MAIN_COUNTERS}


# ---------------------------------------------------------------------------------------------------
# The gate population. OPEN: the frozen per-question list after the registered removals.
# REMOVALS is an explicit, typed, CURRENTLY EMPTY placeholder so a later agent fills in the measured
# lists without touching the logic below. Rule names are fixed: `flag_rule` (FP2) and `rank_rule` (DG3).
# ---------------------------------------------------------------------------------------------------
REMOVAL_RULES = ("flag_rule", "rank_rule")
REMOVALS = {
    # FP2: held `parts` questions the registered input-blind flag rule already answers -> {"parts": [...]}.
    "flag_rule": {},
    # DG3: held `reach` questions the registered node-rank/order rule already answers -> {"reach": [...]}.
    "rank_rule": {},
}
# The verified eligible composition (measured 2026-09-19). 45 eligible = 10 DIRECT_READ + 29 RELATIONAL
# + 6 role_set; the 29 are correspondence 5, edge_account 5, reach 9, analogy 5, parts 5.
VERIFIED_ELIGIBLE_TOTAL = 45
VERIFIED_ELIGIBLE_RELATIONAL = 29
VERIFIED_RELATIONAL_BY_KIND = {"parts": 5, "edge_account": 5, "reach": 9, "correspondence": 5, "analogy": 5}
VERIFIED_RELATIONAL_BY_WORLD = {
    "world-98c6352de9137e679b7d2a460ab99be2791d9c719b0808b2fe3bbb09375534a9": 6,
    "world-28f61f2d7941a373f50285be7e57b1a9b8ec85bc0aff9e2d18c683e9f86b4547": 5,
    "world-6e1fcbdadc4a1aff1b5deddf2d84b9db1ca75b2ba9bbf98e2b202145a33d14be": 6,
    "world-22704554ac881d9846c94b37c5aabc5790edf38f7810692028f0b5e8ce8e4952": 5,
    "world-4090ec49174f1d031b16507663d875616c489382d0be1fdf7f4616aeb3dde9fc": 7,
}
# The known removals, as the interface spec and design v0.2 record them. NOT applied until REMOVALS
# carries them, and NOT necessarily complete -- see UNRECONCILED_REMOVAL_READINGS below.
VERIFIED_KNOWN_REMOVALS = {"flag_rule": {"parts": 3}, "rank_rule": {"reach": 2}}
# Measurements that arrived AFTER INTERFACE_SPEC_POINTER.md:46 was written (HEAD 7276f4f2) and that would
# grow the removals. They are recorded, NOT applied, and NOT reconciled into one list:
#   * DESIGN_DRAFT_v0.2.md:649-656 -- a zero-learning read of the input's own `contains` adjacency solves
#     5 of 5 eligible held `parts` and 5 of 5 `edge_account`, so the FP2 rule's 3 of 5 is not the widest
#     `parts` leak.
#   * HEAD 6cb0b348 -- a rank-only single-flag rule (R10) solves 4 of the 9 eligible held `reach`, with its
#     overlap against DG3's 2 of 9 UNMEASURED.
# If those hold, the RELATIONAL tier itself is narrower than 29, which changes what the owner confirmed by
# name and is therefore his decision, not this placeholder's. The `_removals()` shape check accepts only
# the two registered rule names, so nothing here can leak into the population by accident.
UNRECONCILED_REMOVAL_READINGS = {"parts_adjacency": 5, "edge_account_adjacency": 5, "reach_rank_only": 4}
# CNCM root, used only to locate the practice study's own gate reader lazily (see _practice_gates).
CNCM = Path(__file__).resolve().parents[4]
_GATES_MODULE = None


def _practice_gates():
    """The practice study's own eligible/shortcut derivation, loaded lazily and only when asked for.

    `records/` is analysis territory: it is outside the packaged source scope (`worker_contract.py:138-143`
    globs only `cncm/` and `cas_meta2/`), so this module is loaded on first use and never at import time.
    The AWS worker imports this contract and must not depend on a `records/` script being shipped.
    """
    global _GATES_MODULE
    if _GATES_MODULE is None:
        path = CNCM / "records" / "typed_practice_001" / "evaluate_gates.py"
        require(path.is_file(), "PRACTICE_GATES_MISSING")
        spec = importlib.util.spec_from_file_location("cncm_practice_gates", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        require(callable(getattr(module, "eligible_questions", None)), "PRACTICE_GATES_API")
        _GATES_MODULE = module
    return _GATES_MODULE


def _removals():
    """Validate the placeholder's shape and return it. Empty is valid; malformed is not."""
    require(type(REMOVALS) is dict and set(REMOVALS) == set(REMOVAL_RULES), "RELATIONAL_REMOVALS_SHAPE")
    for rule in REMOVAL_RULES:
        require(type(REMOVALS[rule]) is dict, "RELATIONAL_REMOVALS_SHAPE:" + rule)
        for kind, questions in REMOVALS[rule].items():
            require(kind in RELATIONAL and type(questions) is list
                    and all(type(question) is str for question in questions), "RELATIONAL_REMOVALS_SHAPE:" + rule)
    return REMOVALS


def relational_population(frozen):
    """The pointer study's gate population: eligible held RELATIONAL questions minus the registered removals.

    MECHANISM, NOT A FROZEN LITERAL.
      (a) take every eligible held-back question of the RELATIONAL kinds: the practice study's own hold-out
          (`held_back_questions`) minus the practice study's own registered input-blind shortcut questions,
          reused through `records/typed_practice_001/evaluate_gates.py:eligible_questions` rather than
          re-derived;
      (b) subtract every question solved by a registered FLAG rule (`REMOVALS["flag_rule"]`, review FP2) or
          a registered RANK/ORDER rule (`REMOVALS["rank_rule"]`, review DG3);
      (c) return the surviving question ids, their per-kind counts, their per-world counts, and a digest.

    THE VERIFIED INPUTS a later agent must reconcile against (measured 2026-09-19, recorded here rather
    than re-derived): 45 eligible held questions = 10 DIRECT_READ (definition 5 + context 5) + 29
    RELATIONAL + 6 role_set. The 29 RELATIONAL are correspondence 5, edge_account 5, reach 9, analogy 5,
    parts 5, and their held worlds are world-98c6352d 6, world-28f61f2d 5, world-6e1fcbda 6,
    world-22704554 5, world-4090ec49 7. Known removals: the FP2 flag rule solves 3 of the 5 eligible held
    `parts`; node-order dependence covers 2 of the 9 eligible held `reach`.

    While `REMOVALS` is empty the returned population is NOT the frozen one, and the function raises
    `RELATIONAL_POPULATION_UNRECONCILED` unless the eligible RELATIONAL total and its per-kind and
    per-world composition are exactly the verified values above, so the placeholder cannot be mistaken
    for a finished population.

    NOT THE LAST WORD ON THESE NUMBERS, and the guard is deliberately the only thing reconciling them.
    `DESIGN_DRAFT_v0.2.md:649-656` (section 6.4, "PENDING on the gate") measures that the input's own
    `contains` adjacency already answers 5 of 5 eligible held `parts` and 5 of 5 `edge_account` with no
    learned weights at all, and HEAD `6cb0b348` records a rank-only single-flag rule (R10) solving 4 of the
    9 eligible held `reach`, overlap against DG3 unmeasured. That would leave three kinds (reach, analogy,
    correspondence) and about 19 eligible questions -- a narrower RELATIONAL tier than the 29 measured
    here, which changes what the owner confirmed by name and therefore is NOT this module's decision.
   """
    rules = _removals()
    empty = not any(rules[rule] for rule in REMOVAL_RULES)
    held = held_back_questions(frozen)
    trained = set(split(frozen)[1])
    eligible, shortcut_hit, shortcut = _practice_gates().eligible_questions(frozen, trained, held)
    kind_of = {row["query"]["query_id"]: row["query"]["kind"] for row in frozen["registry"]}
    world_of = {row["query"]["query_id"]: row["source_world_id"] for row in frozen["registry"]}
    record_world = {row["record_id"]: row["source_world_id"] for row in frozen["registry"]}
    # A question is one unit of the gate and belongs to exactly one held world (as the practice reader
    # already assumes when it reads the kind off `records[0]`).
    require(all(len({record_world[record] for record in records}) == 1 and world_of[question] ==
                record_world[records[0]] for question, records in held.items()), "RELATIONAL_POPULATION_WORLD")
    require(set(eligible) <= set(held) and all(question in kind_of and question in world_of for question in eligible),
            "RELATIONAL_POPULATION_INPUT")

    eligible_relational = sorted(question for question in eligible if kind_of[question] in RELATIONAL)
    eligible_by_kind = {kind: sum(1 for q in eligible_relational if kind_of[q] == kind) for kind in RELATIONAL}
    eligible_by_world = dict(sorted(Counter(world_of[q] for q in eligible_relational).items()))
    counts = {tier: sum(1 for q in eligible if kind_of[q] in kinds) for tier, kinds in TIERS.items()}
    require(sum(eligible_by_world.values()) == len(eligible_relational) == sum(eligible_by_kind.values()),
            "RELATIONAL_POPULATION_COUNTS")
    require(not empty or (len(eligible_relational) == VERIFIED_ELIGIBLE_RELATIONAL
                          and eligible_by_kind == VERIFIED_RELATIONAL_BY_KIND
                          and eligible_by_world == VERIFIED_RELATIONAL_BY_WORLD
                          and sum(counts.values()) == VERIFIED_ELIGIBLE_TOTAL),
            "RELATIONAL_POPULATION_UNRECONCILED")

    removed = []
    for rule in REMOVAL_RULES:
        for kind in sorted(rules[rule]):
            listed = rules[rule][kind]
            require(set(listed) <= {q for q in eligible_relational if kind_of[q] == kind},
                    "RELATIONAL_REMOVALS_UNKNOWN:" + rule + ":" + kind)
            removed.extend(listed)
    require(len(removed) == len(set(removed)), "RELATIONAL_REMOVALS_OVERLAP")
    surviving = sorted(set(eligible_relational) - set(removed))

    return {
        "tier": "RELATIONAL",
        "tiers": list(RELATIONAL),
        "eligible_by_tier": dict(sorted(counts.items())),
        "eligible_questions": eligible_relational,
        "eligible_total": len(eligible_relational),
        "eligible_by_kind": eligible_by_kind,
        "eligible_by_world": eligible_by_world,
        "eligible_digest": digest(eligible_relational),
        "removed_questions": sorted(removed),
        "removed_by_rule": {rule: {kind: sorted(rules[rule][kind]) for kind in sorted(rules[rule])}
                            for rule in REMOVAL_RULES},
        "question_ids": surviving,
        "total": len(surviving),
        "by_kind": {kind: sum(1 for q in surviving if kind_of[q] == kind) for kind in RELATIONAL},
        "by_world": dict(sorted(Counter(world_of[q] for q in surviving).items())),
        "digest": digest(surviving),
        "removals_measured": not empty,
        "population_complete": not empty,
        "verified_inputs": {"eligible_total": VERIFIED_ELIGIBLE_TOTAL,
                            "eligible_relational": VERIFIED_ELIGIBLE_RELATIONAL,
                            "by_kind": deepcopy(VERIFIED_RELATIONAL_BY_KIND),
                            "by_world": deepcopy(VERIFIED_RELATIONAL_BY_WORLD),
                            "known_removals": deepcopy(VERIFIED_KNOWN_REMOVALS),
                            "unreconciled_removal_readings": deepcopy(UNRECONCILED_REMOVAL_READINGS)},
        "shortcut_question_ids": list(shortcut_hit),
        "shortcut_answers": dict(shortcut),
    }


# The 17 inherited machine fields that are genuinely machine-independent. `package` is deliberately NOT
# inherited: the pointer package ships the 18 practice checkpoints through MATERIAL, so the practice
# study's package description would be false here (DG10). `registered_learner_unchanged` and
# `initialization` are not inherited either -- both are false for a new machine and a new learner.
_INHERITED = ("d_model", "max_input_tokens", "prediction_depth", "depths", "optimizer_class", "optimizer_foreach",
              "optimizer_fused", "optimizer_config", "training_loss", "reporting_loss", "main_targets", "replay",
              "replay_counts", "source_attestation", "projection_scope", "region", "instance_type")

BOUNDARY = ("Typed pointer reading of ONE focus world as a small directed graph, on one teaching order. The "
            "held-back questions are about five course worlds the machine never read (same world sizes and "
            "question kinds as training); the development panel is out-of-distribution ten-node parts/reach. "
            "The primary label is keyed on the RELATIONAL tier, so gains on the DIRECT_READ kinds alone "
            "cannot produce it. No protected final-study, general CAS architecture, or full-machine claim.")

DESIGN = {**{key: deepcopy(matched.DESIGN[key]) for key in _INHERITED},
    "candidate": CANDIDATE,
    "purpose": "DOES_THE_POINTER_MACHINE_LEARN_RELATIONAL_ANSWERS_ON_WORLDS_IT_NEVER_READ",
    "owner_approval": ("2026-09-19 owner decisions, verbatim: \"Accept both, carry on.\" (both corrections -- the "
        "in-job checkpoint check costs about $0.38-0.63 per job, not \"no extra cost\", and pointer answers alone "
        "cannot work because the INPUT must change too, one world read as a graph instead of a blend of all 64), "
        "\"Approve the smoke job (Recommended)\" (a short AWS smoke job for S10, well under $1, before any paid "
        "launch) and \"Yes -- require the relational kinds.\" (the primary label is keyed on the RELATIONAL tier; "
        "the all-kinds result is a reported flag, never the label)."),
    "machine": "POINTER",
    "input_unit": "ONE_FOCUS_WORLD_READ_AS_A_DIRECTED_GRAPH",
    "answer_form": "POINTER_INTO_THE_QUESTION_INPUT",
    # INTERFACE_SPEC_POINTER.md:83-85 registers the node rank feature as INCLUDED (resolving DG3). The
    # registered value is kept here exactly as pinned; its status is recorded separately because HEAD
    # 6cb0b348 REOPENED the decision (a rank-only rule eats 4 of the 9 eligible held reach questions) and
    # pointer_inputs.py must not be built on either branch until lens A reports.
    "node_rank_feature": True,
    "node_rank_decision_status": "REGISTERED_INCLUDED_REOPENED_AT_6cb0b348_PENDING_LENS_A",
    "head_set": "OPEN_LENS_B_EXPRESSIVITY_TABLE",
    "core_rounds": PLANNED_WORK_ROUNDS,
    "planned_work": deepcopy(PLANNED_WORK),
    "tiers": {tier: list(kinds) for tier, kinds in TIERS.items()},
    "primary_label_tier": "RELATIONAL",
    "primary_label_rule": "RELATIONAL_TIER_GAIN_REQUIRED_TWO_KINDS_TWO_WORLDS_ALL_THREE_SEEDS",
    "flag_copy_alone_cannot_pass": True,
    "gate_population": "ELIGIBLE_HELD_RELATIONAL_QUESTIONS_MINUS_REGISTERED_FLAG_AND_RANK_RULE_REMOVALS",
    "gate_population_open": True,
    "checkpoint_check": "THREE_PRACTICE_CHECKPOINTS_PER_SEED_RESTORED_IN_PHASE_A_BEFORE_THE_POINTER_MODEL_IS_SEEDED",
    "initialization": "REGISTERED_RANDOM_PER_MODEL_SEED_AFTER_PHASE_A_RESTORES",
    "condition": CONDITION, "source_seed": SOURCE_SEED, "encoder_seed": ENCODER_SEED,
    "model_seeds": list(MODEL_SEEDS), "passes": PASSES, "holdout_unit": "FOCUS_WORLD",
    "holdout_rule": practice.DESIGN["holdout_rule"], "held_worlds": list(practice.HELD_WORLDS),
    "pass_checkpoints": list(PASS_CHECKPOINTS), "full_course_checkpoints": list(FULL_COURSE_CHECKPOINTS),
    "interference_updates": INTERFERENCE_UPDATES, "interference_batch": INTERFERENCE_BATCH,
    "interference_trained_records_only": True, "replay_updates": REPLAY_UPDATES,
    "learner_max_updates_ceiling": LEARNER_MAX_UPDATES_CEILING, "max_core_calls": MAX_CORE_CALLS,
    "worker_deadline_seconds": WORKER_DEADLINE_SECONDS, "max_wall_seconds": MAX_WALL_SECONDS,
    "instance_seconds_max": INSTANCE_SECONDS_MAX, "reservation_usd": RESERVATION_USD,
    "jobs": 1, "automatic_retries": 0, "launch_enabled": False, "partial_course_is_success": False,
    "registered_learner_unchanged": False,
    "package": ("PINNED_COURSE_TOKENIZER_SOURCES_THE_TWO_WHEELS_AND_THE_EIGHTEEN_PRACTICE_CHECKPOINTS_"
                "NO_PRIVATE_TARGET_BUNDLE"),
    "boundary": BOUNDARY,
    "learning_on_held_back_established": False}


def parse_job(job):
    require(type(job) is str, "JOB")
    match = re.fullmatch(JOB_PATTERN, job)
    require(match is not None, "JOB")
    return CONDITION, int(match.group(2))


def make_config(root, *, source_sha, job, bucket, model_seed):
    require(type(source_sha) is str and re.fullmatch(r"[0-9a-f]{40}", source_sha), "SOURCE_SHA")
    require(type(model_seed) is int and model_seed in MODEL_SEEDS, "MODEL_SEED")
    require(parse_job(job) == (CONDITION, model_seed) and re.fullmatch(JOB_PATTERN, job).group(1) == source_sha[:8],
            "JOB_PARAMETERS")
    require(type(bucket) is str and re.fullmatch(BUCKET_PATTERN, bucket), "BUCKET")
    frozen, _, development = load_material(root)
    _, stats = practice_schedule(frozen)
    held, _, excluded = split(frozen)
    retention = list(retention_packets(frozen))
    interference = interference_batches(frozen)
    rows = input_inventory(root)
    design = {**deepcopy(DESIGN), "model_seed": model_seed, "schedule": stats,
        "held_back_record_ids": held, "excluded_record_ids": excluded,
        "development_digest": development["development_digest"],
        "development_packets": len(development["packets"]), "retention_packets": len(retention),
        "retention_record_ids_digest": digest([key for key, _ in retention]),
        "interference_batches_digest": digest(interference)}
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
