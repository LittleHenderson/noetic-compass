"""Pure admission and gate-population regressions for the pointer study (owner-approved 2026-09-19).

The pointer study reuses the practice study's course, hold-out, schedule and random start, so the tests
that protect it are identity tests against the practice values, plus the new machine's own rules: the
63-character bucket, the eighteen checkpoint pins, the pointer planned-work formula, the new job pattern,
and the RELATIONAL gate population with its deliberately empty removal placeholder.

Pure: no torch, no GPU, no network, no AWS call. The numeric-import guard below is the same one the
practice test file uses, so this file imports and runs with no numeric runtime installed.
"""
import builtins
import json
from pathlib import Path
import re
import sys

import pytest

# Self-contained import path: do not depend on another test module having run first.
for _extra in (Path(__file__).resolve().parents[1], Path(__file__).resolve().parents[1] / "research/CAS_META_2_COMPOSITION"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from cas_meta2.typed_teaching import pointer_contract as contract
from cas_meta2.typed_teaching import practice_contract as practice

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "a" * 40
SEED = 20260917
JOB = "cas-meta2-tpntr-20260919000000-aaaaaaaa-m-%d"
PRACTICE_JOB = "cas-meta2-tprac-20260919000000-aaaaaaaa-m-20260917"
BUCKET_PATTERN = r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]"
PINS_PATH = ROOT / "records/typed_pointer_001/pre_design/contract_pins/checkpoint_pins.json"
PINS_BYTES = 15259777
HELD_DIGEST = "668e6ce73c426d1fcf8f2391e1a08d90c045ffb37fba95fc64e2658f5369ab1d"
EXCLUDED_DIGEST = "b82108e14554a9fe746a7cfcb1e2cb181a99a3019dc39a3596805f10934c2621"
BATCHES_DIGEST = "daf95831dd6f054f0395e9a868c513650982bd1912247adc698ca067433bc857"
SOURCE_SCHEDULE_DIGEST = "1772c0a53933aa92ea7dfb6b2ce53dcd1089cb3634b089427caba3369977d275"
# The verified eligible RELATIONAL composition (INTERFACE_SPEC_POINTER section 1).
ELIGIBLE_BY_KIND = {"parts": 5, "edge_account": 5, "reach": 9, "correspondence": 5, "analogy": 5}
ELIGIBLE_BY_WORLD = {
    "world-98c6352de9137e679b7d2a460ab99be2791d9c719b0808b2fe3bbb09375534a9": 6,
    "world-28f61f2d7941a373f50285be7e57b1a9b8ec85bc0aff9e2d18c683e9f86b4547": 5,
    "world-6e1fcbdadc4a1aff1b5deddf2d84b9db1ca75b2ba9bbf98e2b202145a33d14be": 6,
    "world-22704554ac881d9846c94b37c5aabc5790edf38f7810692028f0b5e8ce8e4952": 5,
    "world-4090ec49174f1d031b16507663d875616c489382d0be1fdf7f4616aeb3dde9fc": 7,
}


@pytest.fixture(autouse=True)
def public_only(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "numpy", "boto3", "botocore", "cas_cjt", "casformer"}:
            raise AssertionError("NUMERIC_PROVIDER_IMPORT:" + name)
        if name.endswith(("graph_teaching.final_panel", "graph_teaching.reference")):
            raise AssertionError("FINAL_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)


@pytest.fixture(scope="module")
def material():
    return contract.load_material(ROOT)


@pytest.fixture(scope="module")
def population(material):
    """Computed once: the practice gate derivation it reuses takes about 73 seconds."""
    return contract.relational_population(material[0])


class _FakeGates:
    """Stands in for records/typed_practice_001/evaluate_gates.py so the population logic can be driven
    with a chosen eligible set without re-running the 73-second practice derivation."""

    def __init__(self, eligible):
        self.eligible = eligible

    def eligible_questions(self, frozen, trained, questions):
        return sorted(self.eligible), [], {}


def test_holdout_and_schedule_are_byte_identical_to_the_practice_study(material):
    # P1: the pointer contract's hold-out objects ARE the practice study's objects, unchanged by import.
    for name in ("split", "held_worlds", "held_back_questions", "practice_schedule", "interference_batches",
                 "retention_packets", "development_packets", "load_material", "public_packets"):
        assert getattr(contract, name) is getattr(practice, name)
    assert contract.input_inventory is not practice.input_inventory      # the one deliberate wrapper
    frozen = material[0]
    held, trained, excluded = contract.split(frozen)
    assert (len(held), len(trained), len(excluded)) == (127, 358, 79)
    assert len(contract.held_back_questions(frozen)) == 50
    _, stats = contract.practice_schedule(frozen)
    assert stats["held_back_record_ids_digest"] == HELD_DIGEST
    assert stats["excluded_record_ids_digest"] == EXCLUDED_DIGEST
    assert stats["batches_digest"] == BATCHES_DIGEST
    assert stats["source_schedule_digest"] == SOURCE_SCHEDULE_DIGEST
    assert stats["held_back_records"] == len(held) == 127 and stats["trained_records"] == len(trained) == 358
    assert stats["main_updates"] == 1470 and stats["presentations"] == 8180
    assert contract.PASSES == practice.PASSES == 10 and contract.MODEL_SEEDS == practice.MODEL_SEEDS


def test_job_and_bucket_are_within_the_bucket_rule_for_all_three_seeds():
    # P2: 63 characters is the maximum the bucket pattern allows (RK4).
    assert contract.STUDY_TOKEN == "tpntr" and contract.BUCKET_SUFFIX == "-807562639912"
    for seed in contract.MODEL_SEEDS:
        job = JOB % seed
        bucket = job + contract.BUCKET_SUFFIX
        assert re.fullmatch(contract.JOB_PATTERN, job) is not None
        assert contract.parse_job(job) == (contract.CONDITION, seed)
        assert re.fullmatch(contract.BUCKET_PATTERN, bucket) is not None
        assert len(bucket) == 63 and len(bucket) <= 63


def test_a_six_character_study_token_would_break_the_bucket():
    # The rule cannot silently regress: one more token character is 64 and is refused.
    job = JOB.replace(contract.STUDY_TOKEN, "tpoint") % SEED
    bucket = job + contract.BUCKET_SUFFIX
    assert len(bucket) == 64
    assert re.fullmatch(BUCKET_PATTERN, bucket) is None
    with pytest.raises(ValueError):
        contract.parse_job(job)


def test_material_carries_the_eighteen_checkpoint_pins():
    # P3: the 18 checkpoint rows, exactly `bytes` + `sha256`, equal to checkpoint_pins.json.
    pins = json.loads(PINS_PATH.read_bytes())
    assert pins["totals"] == {"files": 18, "bytes": PINS_BYTES, "pt_files": 9, "pt_bytes": 15053349,
                              "json_files": 9}
    rows = pins["material"]
    assert len(rows) == contract.CHECKPOINT_PINS_COUNT == 18
    assert set(contract.CHECKPOINT_PINS) == set(rows)
    assert set(rows) <= set(contract.MATERIAL) and len(contract.MATERIAL) == len(practice.MATERIAL) + 18
    for path, pin in rows.items():
        assert set(contract.MATERIAL[path]) == {"bytes", "sha256"}
        assert contract.MATERIAL[path] == {"bytes": pin["bytes"], "sha256": pin["sha256"]}
    for path, row in contract.MATERIAL.items():
        assert set(row) == {"bytes", "sha256"} and type(row["bytes"]) is int and len(row["sha256"]) == 64
    assert sum(row["bytes"] for row in rows.values()) == PINS_BYTES
    assert sum(pin["bytes"] for pin in contract.CHECKPOINT_PINS.values()) == PINS_BYTES
    assert sum(1 for path in rows if path.endswith(".pt")) == 9
    assert all(pin["sha256"] == contract.MATERIAL[path]["sha256"] for path, pin in rows.items())


def test_input_inventory_stays_within_the_row_and_byte_bounds():
    # P3: the wrapper appends the 18 rows, keeps the inventory sorted, and re-checks the total bound.
    rows = contract.input_inventory(ROOT)
    paths = [row["path"] for row in rows]
    assert paths == sorted(paths) and len(set(paths)) == len(rows)
    assert len(rows) <= 2000 and sum(row["bytes"] for row in rows) <= 96 * 1024 ** 2
    assert all(set(row) == {"path", "bytes", "sha256"} for row in rows)
    by_path = {row["path"]: row for row in rows}
    for path, pin in contract.CHECKPOINT_PINS.items():
        assert by_path[path]["bytes"] == pin["bytes"] and by_path[path]["sha256"] == pin["sha256"]
    # The wrapper only ADDS the 18 rows: the three practice material rows are carried through unchanged.
    for path, pin in practice.MATERIAL.items():
        assert by_path[path]["bytes"] == pin["bytes"] and by_path[path]["sha256"] == pin["sha256"]
    assert len(rows) >= len(practice.MATERIAL) + len(contract.CHECKPOINT_PINS)


def test_planned_work_formula_is_self_consistent_against_the_real_schedule(material):
    # P11: the formula the new DESIGN states is checked against the PRACTICE study's own schedule.
    _, stats = practice.practice_schedule(material[0])
    work = contract.DESIGN["planned_work"]
    assert work["unit"] == "PACKET_FORWARD" and type(work["relations"]) is tuple
    assert work["rounds"] == contract.PLANNED_WORK_ROUNDS == 8
    computed = {}
    for name, key, multiplier in work["relations"]:
        assert key in stats and (multiplier == 1 or multiplier == work["rounds"])
        computed[name] = stats[key] * multiplier
    assert computed["packet_forward_calls"] == stats["presentations"] == 8180
    assert (computed["core_forward_calls"] == computed["core_forward_attempts"]
            == computed["sample_core_passes"] == stats["presentations"] * 8 == 65440)
    assert computed["prediction_calls"] == computed["private_loss_plan_calls"] == 8180
    assert (computed["staged_batches"] == computed["backward_calls"]
            == computed["optimizer_updates"] == stats["main_updates"] == 1470)
    # The old machine's per-slot counts are NOT this machine's planned work (DG10, GOTCHA 20).
    assert stats["planned_slot_core_passes"] == 124510 and stats["presentation_slots"] == 32280
    assert computed["core_forward_calls"] != stats["planned_slot_core_passes"]
    assert computed["packet_forward_calls"] != stats["presentation_slots"]
    assert not any(key in contract.DESIGN for key in ("planned_slot_core_passes", "presentation_slots",
                                                      "training_slot_calls", "training_core_forward_calls", "schedule"))
    # DG10: the two fields that are false for a new machine and a new learner are not inherited.
    assert practice.DESIGN["registered_learner_unchanged"] is True
    assert contract.DESIGN["registered_learner_unchanged"] is False
    assert contract.DESIGN["initialization"] != practice.DESIGN["initialization"]
    assert contract.DESIGN["candidate"] == contract.CANDIDATE and contract.DESIGN["jobs"] == 1
    assert contract.DESIGN["primary_label_tier"] == "RELATIONAL"
    assert contract.DESIGN["tiers"]["RELATIONAL"] == list(contract.RELATIONAL)
    assert set(contract.DESIGN["tiers"]) == set(contract.TIERS)
    # The rank feature is registered as INCLUDED and its reopened status is recorded beside it, so neither
    # reading is presented as settled (HEAD 6cb0b348 reopened the decision).
    assert contract.DESIGN["node_rank_feature"] is True
    assert contract.DESIGN["node_rank_decision_status"] == "REGISTERED_INCLUDED_REOPENED_AT_6cb0b348_PENDING_LENS_A"
    assert contract.DESIGN["owner_approval"].count("2026-09-19") == 1
    for phrase in ("Accept both, carry on.", "Approve the smoke job (Recommended)",
                   "require the relational kinds."):
        assert phrase in contract.DESIGN["owner_approval"]
    # The planned-work formula is OPEN only in its counter key set, which fails closed.
    assert contract.MAIN_COUNTERS is None
    with pytest.raises(ValueError, match="MAIN_COUNTERS_OPEN"):
        contract.expected_main_delta(stats)


def test_parse_job_accepts_only_the_pointer_pattern():
    job = JOB % SEED
    assert contract.parse_job(job) == (contract.CONDITION, SEED)
    assert contract.CANDIDATE == "CNCM_TYPED_POINTER_LEARNING_001"
    assert contract.CONFIG_SCHEMA == "cncm.typed-pointer-worker-config/0.1"
    with pytest.raises(ValueError, match="JOB"):
        contract.parse_job(PRACTICE_JOB)                      # the practice study's own pattern
    for bad in (JOB.replace(contract.STUDY_TOKEN, "tpoint") % SEED, job.replace("-m-", "-a-"),
                job.replace("20260917", "20260920"), job + "-retry", 20260917):
        with pytest.raises(ValueError):
            contract.parse_job(bad)


def test_make_config_refuses_a_sixty_four_character_bucket():
    # The bucket is checked before any material is loaded, so this costs nothing.
    with pytest.raises(ValueError, match="BUCKET"):
        contract.make_config(ROOT, source_sha=SOURCE, job=JOB % SEED,
                             bucket=(JOB.replace(contract.STUDY_TOKEN, "tpoint") % SEED) + contract.BUCKET_SUFFIX,
                             model_seed=SEED)
    with pytest.raises(ValueError, match="MODEL_SEED"):
        contract.make_config(ROOT, source_sha=SOURCE, job=JOB % SEED, bucket=JOB % SEED, model_seed=True)


def test_relational_population_returns_the_29_eligible_relational_questions(population):
    assert population["tier"] == "RELATIONAL" and population["tiers"] == list(contract.RELATIONAL)
    assert population["eligible_total"] == len(population["eligible_questions"]) == 29
    assert population["eligible_by_kind"] == ELIGIBLE_BY_KIND
    assert population["eligible_by_world"] == ELIGIBLE_BY_WORLD
    assert sum(population["eligible_by_world"].values()) == 29
    assert population["eligible_by_tier"] == {"DIRECT_READ": 10, "RELATIONAL": 29, "TEXT": 6}
    assert sum(population["eligible_by_tier"].values()) == 45
    # Nothing is removed yet, and the population says so rather than looking finished.
    assert population["removals_measured"] is False and population["population_complete"] is False
    assert contract.REMOVALS == {"flag_rule": {}, "rank_rule": {}}
    # The later, unreconciled removal readings are recorded and NOT applied: the placeholder accepts only
    # the two registered rule names, so nothing can leak into the population by accident.
    assert contract.UNRECONCILED_REMOVAL_READINGS == {"parts_adjacency": 5, "edge_account_adjacency": 5,
                                                      "reach_rank_only": 4}
    assert not set(contract.REMOVAL_RULES) & set(contract.UNRECONCILED_REMOVAL_READINGS)
    assert population["removed_questions"] == []
    assert population["removed_by_rule"] == {"flag_rule": {}, "rank_rule": {}}
    assert population["question_ids"] == population["eligible_questions"] and population["total"] == 29
    assert population["by_kind"] == ELIGIBLE_BY_KIND and population["by_world"] == ELIGIBLE_BY_WORLD
    assert population["digest"] == population["eligible_digest"] == contract.digest(population["question_ids"])
    assert population["verified_inputs"] == {"eligible_total": 45, "eligible_relational": 29,
        "by_kind": ELIGIBLE_BY_KIND, "by_world": ELIGIBLE_BY_WORLD,
        "known_removals": {"flag_rule": {"parts": 3}, "rank_rule": {"reach": 2}},
        "unreconciled_removal_readings": {"parts_adjacency": 5, "edge_account_adjacency": 5,
                                          "reach_rank_only": 4}}
    assert all(kind in contract.RELATIONAL for kind in population["eligible_by_kind"])
    assert len(population["shortcut_question_ids"]) == 5


def test_relational_population_guard_fires_while_removals_are_empty(material, population, monkeypatch):
    # The guard: while the removal placeholder is empty, the eligible RELATIONAL total must be the
    # verified 29, or the placeholder may not be read as a finished population.
    assert contract.REMOVALS == {"flag_rule": {}, "rank_rule": {}}
    one_short = population["eligible_questions"][:-1]
    assert len(one_short) == 28
    monkeypatch.setattr(contract, "_practice_gates", lambda: _FakeGates(one_short))
    with pytest.raises(ValueError, match="RELATIONAL_POPULATION_UNRECONCILED"):
        contract.relational_population(material[0])


def test_filling_the_removals_subtracts_exactly_the_measured_lists(material, population, monkeypatch):
    # The mechanism: a later agent fills in the measured lists and the logic does not move.
    frozen = material[0]
    eligible = population["eligible_questions"]
    kind_of = {row["query"]["query_id"]: row["query"]["kind"] for row in frozen["registry"]}
    parts = [q for q in eligible if kind_of[q] == "parts"][:3]
    reach = [q for q in eligible if kind_of[q] == "reach"][:2]
    assert len(parts) == 3 and len(reach) == 2
    monkeypatch.setattr(contract, "_practice_gates", lambda: _FakeGates(eligible))
    monkeypatch.setattr(contract, "REMOVALS", {"flag_rule": {"parts": parts}, "rank_rule": {"reach": reach}})
    filled = contract.relational_population(frozen)
    assert filled["removals_measured"] is True and filled["population_complete"] is True
    assert filled["removed_questions"] == sorted(parts + reach)
    assert filled["question_ids"] == sorted(set(eligible) - set(parts) - set(reach))
    assert filled["total"] == 24 and filled["by_kind"]["parts"] == 2 and filled["by_kind"]["reach"] == 7
    assert filled["eligible_total"] == 29 and filled["digest"] != filled["eligible_digest"]
    # A malformed placeholder and an unknown question id both fail closed.
    monkeypatch.setattr(contract, "REMOVALS", {"flag_rule": {"definition": ["q"]}, "rank_rule": {}})
    with pytest.raises(ValueError, match="RELATIONAL_REMOVALS_SHAPE"):
        contract.relational_population(frozen)
    monkeypatch.setattr(contract, "REMOVALS", {"flag_rule": {"parts": ["not-a-held-question"]}, "rank_rule": {}})
    with pytest.raises(ValueError, match="RELATIONAL_REMOVALS_UNKNOWN"):
        contract.relational_population(frozen)
