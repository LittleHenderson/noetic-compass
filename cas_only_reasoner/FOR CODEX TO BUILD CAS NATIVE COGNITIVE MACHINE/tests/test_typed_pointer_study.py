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
    # The rank feature is EXCLUDED, decided 2026-09-19 once both lenses had reported: adopting it would take
    # the population from 18 to 13 and raise the required share from 7/18 to 7/13, and rank IS the node alias
    # (244 of 244 refs), so the order-dependent questions are removed instead.
    assert contract.DESIGN["node_rank_feature"] is False
    assert contract.DESIGN["node_rank_decision_status"] == (
        "EXCLUDED_2026_09_19_ORDER_DEPENDENT_QUESTIONS_REMOVED_INSTEAD")
    assert contract.DESIGN["owner_approval"].count("2026-09-19") == 1
    for phrase in ("Accept both, carry on.", "Approve the smoke job (Recommended)",
                   "require the relational kinds."):
        assert phrase in contract.DESIGN["owner_approval"]
    # The planned-work formula is OPEN only in its counter key set, which fails closed.
    assert contract.MAIN_COUNTERS is None
    with pytest.raises(ValueError, match="MAIN_COUNTERS_OPEN"):
        contract.expected_main_delta(stats)


# ---------------------------------------------------------------------------------------------------
# STRATIFICATION (owner decision 2026-09-19: the option labelled "Stratify AND train longer
# (Recommended)"). The single pass now carries one record of EVERY kind in every update. These four
# tests are the mechanism: the fidelity property is still exact on the unstratified branch, the
# stratified branch really does cover all eight kinds in all 147 updates, its cost is the measured
# 1176 presentations per pass, and its digest is pinned so a later drift is visible rather than
# discovered after a spend. The as-is absence counts this decision answers are in
# records/typed_pointer_001/pre_design/REVIEW_SYNTHESIS.md section 4.7 and in the contract's DESIGN.
# ---------------------------------------------------------------------------------------------------
STRATIFIED_BATCHES_DIGEST = "1c67edd74bf670a1b2b17af63209bc33bc2a92bc3a796e2d66f285d10c7b5304"
STRATIFIED_PASS_DIGEST = "80ae7121ff75f687e9c6c88593e2ed7d3f6024173d3577243ed05049c8859056"
# REVIEW_SYNTHESIS.md section 4.7, measured by pre_design/lb11_economics.py: the as-is MIXED pass of
# 147 updates leaves each kind ABSENT from this many of them. Stratifying drives all eight to zero.
AS_IS_ABSENT_UPDATES = {"role_set": 115, "analogy": 112, "context": 107, "definition": 105,
                        "edge_account": 95, "correspondence": 67, "parts": 63, "reach": 40}
AS_IS_UPDATES_PER_PASS = 147
AS_IS_PRESENTATIONS_PER_PASS = 818
STRATIFIED_PRESENTATIONS_PER_PASS = 1176


def test_the_non_stratified_branch_keeps_the_practice_fidelity_property_exactly(material):
    # The owner's decision must not cost the comparison the two studies rest on: with `stratified=False`
    # the 10-pass schedule IS the practice study's own, byte for byte.
    batches, stats = contract.pointer_schedule(material[0], contract.practice.PASSES, stratified=False)
    assert stats["batches_digest"] == BATCHES_DIGEST
    assert stats["batches_digest"] == contract.DESIGN["schedule_unstratified_batches_digest"]
    assert stats["updates_per_pass"] == AS_IS_UPDATES_PER_PASS == 147
    assert stats["presentations_per_pass"] == AS_IS_PRESENTATIONS_PER_PASS == 818
    # And it is the practice function's own output, not merely an equal digest: same batches, same stats.
    practice_batches, practice_stats = contract.practice_schedule(material[0])
    assert batches == practice_batches
    assert stats == practice_stats
    # The flag is refused when it is not a bool, so neither branch can be selected by accident.
    assert contract.STRATIFIED is True and contract.DESIGN["schedule_stratified"] is True
    for bad in ("yes", 1, 0, []):
        with pytest.raises(ValueError, match="POINTER_STRATIFIED_FLAG"):
            contract.pointer_schedule(material[0], 1, stratified=bad)


def test_the_stratified_default_puts_every_kind_in_every_update_at_the_same_update_count(material):
    # The default branch, and the whole point of the owner's decision: with 147 updates per pass as
    # before, each kind is absent from ZERO of them instead of from 40..115 of them.
    batches, stats = contract.pointer_schedule(material[0])
    assert contract.STRATIFIED is True and contract.DESIGN["schedule_stratified_decision"] == \
        "OWNER_DECISION_STRATIFY_AND_TRAIN_LONGER_RECOMMENDED"
    assert stats["updates_per_pass"] == AS_IS_UPDATES_PER_PASS == 147
    assert stats["passes"] == contract.PASSES == 10 and stats["main_updates"] == 1470
    first = [batch for batch in batches if batch["pass"] == 1]
    assert len(first) == 147
    kinds_of = {row["record_id"]: row["query"]["kind"] for row in material[0]["registry"]}
    absence = {kind: 0 for kind in contract.KINDS}
    for batch in first:
        present = {kinds_of[key] for key in batch["record_ids"]}
        assert present == set(contract.KINDS)
        assert len(present) == len(contract.KINDS) == 8
        for kind in contract.KINDS:
            if kind not in present:
                absence[kind] += 1
    assert absence == {kind: 0 for kind in contract.KINDS}
    # The as-is counts this decision answers, recorded rather than re-derived (REVIEW_SYNTHESIS 4.7),
    # are all non-zero and all larger than the stratified branch's zeros.
    assert contract.DESIGN["schedule_stratified_absent_updates_as_is"] == AS_IS_ABSENT_UPDATES
    assert set(AS_IS_ABSENT_UPDATES) == set(contract.KINDS)
    assert all(count > 0 for count in AS_IS_ABSENT_UPDATES.values())
    assert sum(AS_IS_ABSENT_UPDATES.values()) == 704
    # The pass-level composition is pinned, and every record still comes from the trained pool.
    keep_set = set(contract.split(material[0])[1])
    assert all(key in keep_set for batch in batches for key in batch["record_ids"])
    one_pass = contract._stratified_pass(material[0], contract.matched.schedule(material[0], contract.CONDITION)[0],
                                         keep_set)
    assert contract.digest(one_pass) == contract.STRATIFIED_PASS_DIGEST == STRATIFIED_PASS_DIGEST
    assert [len(batch["record_ids"]) for batch in one_pass] == [8] * 147


def test_the_stratified_cost_is_the_measured_1176_presentations_and_the_digest_is_pinned(material):
    # +43.8 % presentations for the same update count: 818 -> 1176 per pass, and a digest of its own.
    batches, stats = contract.pointer_schedule(material[0])
    assert stats["presentations_per_pass"] == STRATIFIED_PRESENTATIONS_PER_PASS == 1176
    assert stats["presentations"] == 11760
    assert AS_IS_PRESENTATIONS_PER_PASS + 358 == STRATIFIED_PRESENTATIONS_PER_PASS
    increase = STRATIFIED_PRESENTATIONS_PER_PASS / AS_IS_PRESENTATIONS_PER_PASS - 1
    assert 0.437 < increase < 0.439                    # 43.8 %, not rounded into 44 % or 0.44
    assert stats["updates_per_pass"] == AS_IS_UPDATES_PER_PASS     # the update count does NOT move
    # The stratified digest differs from the practice one, and both are pinned exactly.
    assert stats["batches_digest"] != BATCHES_DIGEST
    assert stats["batches_digest"] == STRATIFIED_BATCHES_DIGEST
    assert stats["batches_digest"] == contract.STRATIFIED_BATCHES_DIGEST
    assert stats["batches_digest"] == contract.DESIGN["schedule_stratified_batches_digest"]
    assert contract.DESIGN["schedule_stratified_presentations_per_pass"] == 1176
    assert contract.DESIGN["schedule_stratified_updates_per_pass"] == 147
    # A different pass count still differs, and the ceiling still binds at 24 passes.
    other, other_stats = contract.pointer_schedule(material[0], 7)
    assert other_stats["batches_digest"] not in (BATCHES_DIGEST, STRATIFIED_BATCHES_DIGEST)
    assert other_stats["main_updates"] == 7 * 147 == 1029
    with pytest.raises(ValueError, match="POINTER_PASSES_BOUND"):
        contract.pointer_schedule(material[0], contract.MAX_PASSES_PERMITTED + 1)


def test_every_stratified_batch_carries_exactly_eight_records_and_eight_kinds(material):
    # Not one batch of pass 1 is short of a kind: 8 records, 8 distinct kinds, in all 147 updates.
    batches, stats = contract.pointer_schedule(material[0])
    kinds_of = {row["record_id"]: row["query"]["kind"] for row in material[0]["registry"]}
    for batch in [b for b in batches if b["pass"] == 1]:
        assert len(batch["record_ids"]) == 8
        kinds = {kinds_of[key] for key in batch["record_ids"]}
        assert len(kinds) == 8 and kinds == set(contract.KINDS)
        # One record per kind, so no kind is doubled to fill the batch.
        assert len(batch["record_ids"]) == len(set(batch["record_ids"]))
        # The ids are this study's own and are unique inside the batch (the OCCURRENCE_UNIQUE contract).
        assert len(batch["occurrence_ids"]) == len(set(batch["occurrence_ids"])) == 8
        assert len(batch["presentation_ids"]) == len(set(batch["presentation_ids"])) == 8
        assert all(key.startswith("typed-occurrence-") for key in batch["occurrence_ids"])
        assert all("pointer-stratified-" in key for key in batch["presentation_ids"])
        # The structure the owner required be kept from the base slot IS the base slot's.
        assert type(batch["round"]) is int and type(batch["phase"]) is str
        assert type(batch["depth"]) is int and batch["depth"] > 0
        assert type(batch["source_cursor"]) is int and 0 <= batch["source_cursor"] < 160
    assert stats["presentations_per_pass"] == 8 * 147 == 1176
    assert stats["updates_per_pass"] == len([b for b in batches if b["pass"] == 1]) == 147


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


def test_relational_population_is_the_frozen_18_after_the_eleven_removals(population):
    assert population["tier"] == "RELATIONAL" and population["tiers"] == list(contract.RELATIONAL)
    assert population["eligible_total"] == len(population["eligible_questions"]) == 29
    assert population["eligible_by_kind"] == ELIGIBLE_BY_KIND
    assert population["eligible_by_world"] == ELIGIBLE_BY_WORLD
    assert sum(population["eligible_by_world"].values()) == 29
    assert population["eligible_by_tier"] == {"DIRECT_READ": 10, "RELATIONAL": 29, "TEXT": 6}
    assert sum(population["eligible_by_tier"].values()) == 45
    # FROZEN 2026-09-19: eleven removals across four classes, and the population says it is finished.
    assert population["removals_measured"] is True and population["population_complete"] is True
    assert len(population["removed_questions"]) == 11
    assert population["total"] == contract.VERIFIED_POPULATION == 18
    assert population["by_kind"] == contract.VERIFIED_POPULATION_BY_KIND
    # `by_kind` covers all five RELATIONAL kinds, so `correspondence` is present with a count of zero:
    # every one of its five questions left the gate as the architectural-inexpressibility class.
    assert population["by_kind"] == {"parts": 2, "edge_account": 5, "reach": 6,
                                     "correspondence": 0, "analogy": 5}
    assert sum(population["by_kind"].values()) == 18
    assert population["digest"] == contract.VERIFIED_POPULATION_DIGEST
    assert population["digest"] != population["eligible_digest"]
    # The four classes, and the one that is NOT a shortcut must be labelled as such.
    assert set(contract.REMOVAL_RULES) == {"flag_rule", "order_rule", "present_rule", "inexpressible"}
    assert set(population["removed_by_rule"]) == set(contract.REMOVAL_RULES)
    assert len(population["removed_by_rule"]["flag_rule"]["parts"]) == 3
    assert len(population["removed_by_rule"]["order_rule"]["reach"]) == 2
    assert len(population["removed_by_rule"]["present_rule"]["reach"]) == 1
    assert len(population["removed_by_rule"]["inexpressible"]["correspondence"]) == 5
    # The rank-last pointing questions are NOT removed, because the rank feature is excluded.
    assert contract.DESIGN["node_rank_feature"] is False
    assert "rank_rule" not in contract.REMOVAL_RULES
    assert population["verified_inputs"]["unreconciled_removal_readings"][
        "rank_last_pointing_not_removed"] == 5
    assert all(kind in contract.RELATIONAL for kind in population["eligible_by_kind"])
    assert len(population["shortcut_question_ids"]) == 5
    # Required share, restated where a reader changing the population will see it.
    assert contract.MIN_PASSING_B == 7 and 2 ** -contract.MIN_PASSING_B <= 0.01


def test_population_guard_fires_when_the_composition_drifts_and_removals_are_empty(material, population,
                                                                                  monkeypatch):
    # The guard exists to stop an UNFILLED placeholder being read as a finished population. Filled, it is
    # bypassed; emptied again, it fires if the eligible composition drifts from the verified values.
    monkeypatch.setattr(contract, "REMOVALS", {rule: {} for rule in contract.REMOVAL_RULES})
    one_short = population["eligible_questions"][:-1]
    assert len(one_short) == 28
    monkeypatch.setattr(contract, "_practice_gates", lambda: _FakeGates(one_short))
    with pytest.raises(ValueError, match="RELATIONAL_POPULATION_UNRECONCILED"):
        contract.relational_population(material[0])


def test_removals_subtract_exactly_the_listed_questions_and_fail_closed(material, population, monkeypatch):
    # The mechanism: what the lists carry is exactly what leaves, and a malformed or unknown entry fails closed.
    frozen = material[0]
    eligible = population["eligible_questions"]
    kind_of = {row["query"]["query_id"]: row["query"]["kind"] for row in frozen["registry"]}
    parts = [q for q in eligible if kind_of[q] == "parts"][:3]
    reach = [q for q in eligible if kind_of[q] == "reach"][:2]
    assert len(parts) == 3 and len(reach) == 2
    monkeypatch.setattr(contract, "_practice_gates", lambda: _FakeGates(eligible))
    monkeypatch.setattr(contract, "REMOVALS", {"flag_rule": {"parts": parts},
                                               "order_rule": {"reach": reach},
                                               "present_rule": {}, "inexpressible": {}})
    filled = contract.relational_population(frozen)
    assert filled["removals_measured"] is True and filled["population_complete"] is True
    assert filled["removed_questions"] == sorted(parts + reach)
    assert filled["question_ids"] == sorted(set(eligible) - set(parts) - set(reach))
    assert filled["total"] == 24 and filled["by_kind"]["parts"] == 2 and filled["by_kind"]["reach"] == 7
    assert filled["eligible_total"] == 29 and filled["digest"] != filled["eligible_digest"]
    # A malformed placeholder and an unknown question id both fail closed.
    monkeypatch.setattr(contract, "REMOVALS", {"flag_rule": {"definition": ["q"]}, "order_rule": {},
                                               "present_rule": {}, "inexpressible": {}})
    with pytest.raises(ValueError, match="RELATIONAL_REMOVALS_SHAPE"):
        contract.relational_population(frozen)
    monkeypatch.setattr(contract, "REMOVALS", {"flag_rule": {"parts": ["not-a-held-question"]},
                                               "order_rule": {}, "present_rule": {}, "inexpressible": {}})
    with pytest.raises(ValueError, match="RELATIONAL_REMOVALS_UNKNOWN"):
        contract.relational_population(frozen)


# ---------------------------------------------------------------------------------------------------
# P9, P10, the read-cost bound and the digest pin, for the pure public-input reader.
#
# The imports, constants and helpers live HERE, below the tests that were already in this file, so nothing
# above this line changed. Everything below reads public data only: the bank's worlds and each registry
# row's PUBLIC QUERY. `supports`, `cue`, `instruction`, `role_catalog` and every answer or target are never
# read by the reader, and test P10 proves it structurally rather than by inspection.
# ---------------------------------------------------------------------------------------------------
import statistics                                                                    # noqa: E402
import time                                                                         # noqa: E402

from cas_meta2.typed_teaching import answers as _answers                             # noqa: E402
from cas_meta2.typed_teaching import course as _course                              # noqa: E402
from cas_meta2.typed_teaching import pointer_inputs as reader                       # noqa: E402
from cas_meta2.typed_teaching import slots as _slots                                # noqa: E402
from cas_meta2.typed_teaching import source as _source                              # noqa: E402

# The pinned cache digest, measured at HEAD 607a3f15 over the frozen course: 136 declaration strings and
# 36 role_set excerpts, tokenizer digest 5ce5aa8b26334eb517c820ebae66216fe20439d1f91ede0ada6e64cc03edf798.
CACHE_DIGEST = "720cb915ba3961b3855c1df5be13b4f4e12885bd4ac93b24ea0c25645365e481"
CACHE_DECLARATIONS = 136
CACHE_EXCERPTS = 36
CACHE_VOCABULARY = 3829
# `input_digest` over all 564 records, aggregated as `digest({record_id: input_digest(reading)})`, on each
# branch of the register design constant. Both are recorded because both branches are implemented and
# selected live from `pointer_contract.DESIGN["node_rank_feature"]`, whose decision is REOPENED pending
# lens A (`DESIGN["node_rank_decision_status"]`).
ALL_RECORDS_DIGEST = "d6ca34f4449dbdce392461e1313a71c04dd8959d2d0f764aa28b0af26ebd8a72"
ALL_RECORDS_DIGEST_RANK_OUT = "ef989528913b6a676c9a2c7e495ea5a3f7b5bfc3f52dc072a05becc2a77c20d0"
# BOTH constants were re-derived on 2026-09-19, for two separate reasons, and the record of the old values is
# kept because a digest that moved without explanation is indistinguishable from a regression:
#   * the rank feature was EXCLUDED (pointer_contract.DESIGN["node_rank_feature"] is now False), so the default
#     branch became the rank-OUT one;
#   * `is_primary_label` and its rank were REMOVED from the reading, because design v0.2 section 5.1 and the
#     protocol section 5.3 both require it: LK5 measured `primary_labels == participants` in 64 of 64 worlds,
#     re-verified here directly against the frozen course.
# Previous values: rank-OUT was 8ffa39390b5927c341975e22470e898971d70ba50bb7228dbefe8cb918a3f48c and the
# rank-IN value was f2652b55f3525d4ab49b57130d638b890f574cb550bbb738001fbe2fe58ba5d4.
# Measured at HEAD 607a3f15 on this machine, system Python 3.14.0 / pytest 9.0.2: worst packet
# 0.000972 s in one run and 0.001024 s in another, both the 64-world `analogy` kind (64 world graphs, a
# 56,567-byte canonical reading); the whole 564-record sweep needs 0.427 s / 0.445 s for reading AND
# digesting. The bound is the guard against the `tokenization.py:151` per-call rebuild, measured at
# 0.0111 s per call: one rebuild per declaration string would make a 64-world packet take about 2.8 s, and
# 8,180 presentations of that would exceed the 12,300 s worker deadline by more than an order of magnitude.
MAX_PACKET_SECONDS = 0.005
SWEEP_SECONDS = 60.0
READ_SECONDS_MEASURED = 0.001024
# Every key name the reader may emit, and every string value it may emit. A label word, a node ref, an
# answer field or a support text can only reach the reading by appearing in one of these two sets.
READING_KEYS = frozenset({
    "schema", "record_id", "query_id", "focus_world_id", "node_rank_feature", "query", "focus_world",
    "worlds", "node_flags", "excerpt", "kind", "kind_name", "rule", "rule_name", "whole", "part",
    "target_world_id", "world_count", "world_id", "is_focus", "is_target", "node_count", "contains",
    "declaration_ids", "nodes", "domain", "function", "setting", "rank", "is_declared_whole",
    "is_participant", "is_primary_label", "is_whole_argument", "is_part_argument"})
SLOT_READING_KEYS = frozenset({
    "slot_id", "field", "group", "world_id", "is_target_world", "role_ids", "node_ranks", "nodes",
    "symbol_count"})
# `target_world_id` is NOT in this list: it is a MANDATED public query argument (`answers._ARGUMENTS`,
# answers.py:37) that INTERFACE_SPEC_POINTER.md:77 requires the reading to carry as the correspondence
# target world. The prohibition is on the answer/target sidecar, never on this argument.
FORBIDDEN_NAMES = ("supports", "cue", "instruction", "role_catalog", "answer", "prediction", "correct",
                   "receipt")


def _rows_by_kind(frozen):
    """One registry row per kind. Only the PUBLIC QUERY and the record id are read off a row."""
    rows = {}
    for row in frozen["registry"]:
        rows.setdefault(row["query"]["kind"], row)
    return rows


def _light_packet(row, frozen):
    """A packet carrying EXACTLY the keys the reader reads, and none of the forbidden ones.

    `course.model_packet` builds a record with `supports`, `cue`, `instruction` and `role_catalog` in it
    (course.py:300-301). Handing the reader this packet instead proves the exclusion at the API level: if
    the reader needed any of those fields it would fail here, and P10 asserts the two packets give the
    identical reading.
    """
    return {"source": {"focus_world_id": row["source_world_id"], "worlds": frozen["bank"]["worlds"]},
            "record": {"record_id": row["record_id"], "query": row["query"]}}


def _walk(value, keys, values):
    """Collect every dict key and every string value in a reading, requiring plain non-bool int leaves."""
    if type(value) is dict:
        for key, item in value.items():
            assert type(key) is str
            keys.add(key)
            _walk(item, keys, values)
    elif type(value) is list:
        for item in value:
            _walk(item, keys, values)
    elif type(value) is str:
        values.add(value)
    else:
        assert type(value) is int or type(value) is type(None), "READING_LEAF_TYPE:%r" % (type(value),)


def _sweep(frozen):
    """`{record_id: input_digest(reading)}` over all 564 records, from light packets."""
    return {row["record_id"]: reader.input_digest(reader.read_packet(_light_packet(row, frozen)))
            for row in frozen["registry"]}


def test_p9_input_reader_is_pure_deterministic_and_cached_once(material):
    # P9: the same packet read twice gives identical canonical bytes; the cache is built ONCE and its every
    # entry equals a direct `FrameTokenizer.encode_text` call; reading never mutates the packet.
    frozen, tokenizer = material[0], material[1]
    cache = reader.label_cache(ROOT)
    assert cache["cache_digest"] == reader.LABEL_CACHE_DIGEST_PIN == CACHE_DIGEST
    assert cache["declaration_count"] == CACHE_DECLARATIONS and cache["excerpt_count"] == CACHE_EXCERPTS
    assert cache["vocabulary_size"] == CACHE_VOCABULARY and cache["word_start"] == 258
    assert cache["tokenizer_digest"] == tokenizer.digest
    assert len(cache["declaration_ids"]) == CACHE_DECLARATIONS
    assert len(cache["excerpt_ids"]) == CACHE_EXCERPTS
    # Built ONCE: a second call for the same root reuses the record and returns an equal cache. This is the
    # RK3 resolution -- `tokenization.py:151` rebuilds a 3571-entry lookup on every call, and this module must
    # not repeat that bug.
    builds = reader._CACHE_STATE["builds"]
    assert type(builds) is int and builds >= 1
    assert reader.label_cache(ROOT) == cache
    assert reader._CACHE_STATE["builds"] == builds
    # Every cached entry equals a direct encode_text call, so the reusable lookup is semantics-identical.
    entries = {**cache["declaration_ids"], **cache["excerpt_ids"]}
    assert len(entries) == CACHE_DECLARATIONS + CACHE_EXCERPTS
    for text, ids in entries.items():
        assert type(text) is str and ids and tokenizer.encode_text(text) == ids
    for row in _rows_by_kind(frozen).values():
        packet = _light_packet(row, frozen)
        before = _source.canonical(packet)
        first = reader.read_packet(packet)
        second = reader.read_packet(packet)
        assert _source.canonical(first) == _source.canonical(second)
        assert reader.input_digest(first) == reader.input_digest(second)
        the_bytes = _source.canonical(first)
        assert the_bytes == _source.canonical(json.loads(the_bytes))       # canonical-serialisable
        assert _source.canonical(packet) == before                        # reading does not mutate the packet
        assert first["record_id"] == row["record_id"] and first["query_id"] == row["query"]["query_id"]
    with pytest.raises(ValueError):
        reader.input_digest({"schema": "not-the-reading-schema"})


def test_p10_inputs_exclude_answers_and_label_words_and_include_the_reach_rule(material):
    # P10: the reading excludes supports/cue/instruction and every node label word, includes the reach rule,
    # and never needs the answer-bearing fields to exist at all.
    frozen = material[0]
    bank = frozen["bank"]["worlds"]
    bank_ids = {world["world_id"] for world in bank}
    labels = {node["label"] for world in bank for node in world["nodes"]}
    held = set(practice.HELD_WORLDS)
    held_labels = {node["label"] for world in bank if world["world_id"] in held for node in world["nodes"]}
    assert len(labels) == 230 and len(held_labels) == 20
    rows = _rows_by_kind(frozen)
    assert set(rows) == set(contract.TIERS["DIRECT_READ"] + contract.TIERS["RELATIONAL"] + contract.TIERS["TEXT"])
    for kind, row in sorted(rows.items()):
        packet = _light_packet(row, frozen)
        # The reader must not even need the answer-bearing keys to be present.
        assert not (set(FORBIDDEN_NAMES) & set(packet["record"]))
        reading = reader.read_packet(packet)
        # The full packet, built by the course's own public view, gives the identical reading.
        full = _course.model_packet(frozen, row["record_id"])
        assert _source.canonical(reader.read_packet(full)) == _source.canonical(reading)
        keys, values = set(), set()
        _walk(reading, keys, values)
        # The ONLY key names outside the fixed schema are the 64 bank world ids, because `worlds` is keyed by
        # `world_id` exactly as INTERFACE_SPEC_POINTER.md:77 pins it.
        assert keys <= READING_KEYS | bank_ids, "READING_KEY:%r" % (keys - READING_KEYS - bank_ids)
        allowed = bank_ids | set(reader.KIND_IDS) | set(reader.RULE_IDS)
        allowed |= {reader.READING_SCHEMA, row["record_id"], row["query"]["query_id"]}
        assert values <= allowed, "READING_VALUE:%r" % (values - allowed)
        blob = _source.canonical(reading)
        for name in FORBIDDEN_NAMES:
            assert name not in blob, "FORBIDDEN_NAME:" + name
        assert not any(label in blob for label in labels), "NODE_LABEL_WORD"
        assert not any(label in blob for label in held_labels), "HELD_WORLD_LABEL_WORD"
        assert "/n" not in blob, "NODE_REF"
        # The rank feature branch is recorded, and it is read LIVE from the contract.
        assert reading["node_rank_feature"] == int(contract.DESIGN["node_rank_feature"] is True)
        assert all(("rank" in node) is contract.DESIGN["node_rank_feature"] for node in reading["node_flags"])
        assert [node.get("rank") for node in reading["node_flags"]] == (
            list(range(len(reading["node_flags"]))) if contract.DESIGN["node_rank_feature"]
            else [None] * len(reading["node_flags"]))
    # The reach rule IS an input: the two admitted reach rules get different learned ids, and the
    # development panel -- which no course record uses -- is readable and uses the other one.
    reach_rows = [row for row in frozen["registry"] if row["query"]["kind"] == "reach"]
    # `answers.RULES` ("reach", answers.py:32-33) admits exactly these two, in this order.
    assert _answers.RULES["reach"] == ("first_direct_constituent_lexical_v1",
                                       "bfs_immediate_predecessor_lexical_v1")
    assert {row["query"]["rule"] for row in reach_rows} == set(_answers.RULES["reach"])
    ids = {row["query"]["rule"]: reader.read_packet(_light_packet(row, frozen))["query"]["rule"]
           for row in reach_rows}
    assert len(ids) == 2 and len(set(ids.values())) == 2
    development = contract.development_packets(material[2])
    dev_kinds, dev_rules = set(), set()
    for record_id in sorted(development):
        dev_reading = reader.read_packet(development[record_id])
        dev_kinds.add(dev_reading["query"]["kind_name"])
        if dev_reading["query"]["kind_name"] == "reach":
            dev_rules.add(dev_reading["query"]["rule_name"])
    assert dev_kinds == {"parts", "reach"} and dev_rules == {"first_direct_constituent_lexical_v1"}
    assert dev_rules < set(_answers.RULES["reach"])


def test_p9_slot_readings_line_up_with_the_existing_slot_plan(material):
    # The per-slot readings use the EXISTING slot plan: one entry per slot, in slot order, and the slot's own
    # coordinate refs are spent to recover ranks rather than copied into the reading.
    frozen = material[0]
    for kind, row in sorted(_rows_by_kind(frozen).items()):
        full = _course.model_packet(frozen, row["record_id"])
        reading = reader.read_packet(full)
        plan = _slots.compile_slots(full)
        rows = reader.slot_readings(reading, plan["slots"])
        assert len(rows) == len(plan["slots"]) and len(rows) > 0
        assert [entry["field"] for entry in rows] == [slot["field"] for slot in plan["slots"]]
        assert [entry["slot_id"] for entry in rows] == [slot["slot_id"] for slot in plan["slots"]]
        assert _source.canonical(rows) == _source.canonical(reader.slot_readings(reading, plan))
        for entry, slot in zip(rows, plan["slots"]):
            assert entry["world_id"] == slot["scope_world_id"]
            assert entry["symbol_count"] == len(slot["symbols"])
            assert entry["world_id"] in reading["worlds"]
            assert set(entry) == SLOT_READING_KEYS
            if slot["field"] == "role":
                assert entry["role_ids"] == slot["coordinates"] and not entry["node_ranks"]
            elif slot["field"] in ("participant", "node", "edge", "mapping_target"):
                assert len(entry["node_ranks"]) == len(slot["coordinates"])
                graph = reading["worlds"][entry["world_id"]]
                assert all(0 <= rank < graph["node_count"] for rank in entry["node_ranks"])
                assert entry["nodes"] == [graph["nodes"][rank] for rank in entry["node_ranks"]]
            else:
                assert slot["coordinates"] == [] and not entry["node_ranks"] and not entry["role_ids"]
        blob = _source.canonical(rows)
        assert "/n" not in blob and all(label not in blob for label in
                                        {node["label"] for world in frozen["bank"]["worlds"]
                                         for node in world["nodes"]})


def test_p9_reader_cost_cannot_silently_regress(material):
    # The reader must stay far under the worker deadline. A regression that rebuilt the tokenizer lookup per
    # call (`tokenization.py:151`, 0.0111 s per call) would show up here immediately.
    frozen = material[0]
    reader.label_cache(ROOT)
    builds = reader._CACHE_STATE["builds"]
    worst, measured = None, {}
    for kind, row in sorted(_rows_by_kind(frozen).items()):
        packet = _light_packet(row, frozen)
        reader.read_packet(packet)
        samples = []
        for _ in range(25):
            started = time.perf_counter()
            reader.read_packet(packet)
            samples.append(time.perf_counter() - started)
        measured[kind] = statistics.median(samples)
        if worst is None or measured[kind] > worst[1]:
            worst = (kind, measured[kind])
    assert worst[1] < MAX_PACKET_SECONDS, "READ_TIME:%s:%r measured at HEAD %r" % (worst[0], worst[1],
                                                                                  READ_SECONDS_MEASURED)
    # The whole 564-record sweep, reading AND digesting every record, stays well inside its bound, and the
    # cache is not rebuilt for any of them.
    started = time.perf_counter()
    digests = _sweep(frozen)
    elapsed = time.perf_counter() - started
    assert len(digests) == 564 and elapsed < SWEEP_SECONDS, "SWEEP_TIME:%r" % (elapsed,)
    assert reader._CACHE_STATE["builds"] == builds
    print("reader: worst %s %.6f s/packet; all 564 read+digest in %.3f s" % (worst[0], worst[1], elapsed))


def test_p9_input_digest_over_all_564_records_is_reproducible(material, monkeypatch):
    # The digest is stable across processes and machines, and BOTH branches of the register design constant
    # are implemented: flipping `pointer_contract.DESIGN["node_rank_feature"]` is the whole change.
    # Since 2026-09-19 the DEFAULT is the rank-OUT branch, because the rank feature was excluded.
    frozen = material[0]
    assert contract.DESIGN["node_rank_feature"] is False
    assert contract.DESIGN["node_rank_decision_status"] == (
        "EXCLUDED_2026_09_19_ORDER_DEPENDENT_QUESTIONS_REMOVED_INSTEAD")
    first = _sweep(frozen)
    assert len(first) == 564
    assert _source.digest(first) == ALL_RECORDS_DIGEST_RANK_OUT
    assert _source.digest(_sweep(frozen)) == ALL_RECORDS_DIGEST_RANK_OUT        # reproducible
    without_rank = reader.read_packet(_light_packet(next(iter(frozen["registry"])), frozen))
    assert without_rank["node_rank_feature"] == 0
    assert all("rank" not in node for node in without_rank["node_flags"])
    monkeypatch.setitem(contract.DESIGN, "node_rank_feature", True)
    with_rank = _sweep(frozen)
    assert _source.digest(with_rank) == ALL_RECORDS_DIGEST
    assert with_rank != first
    sample = reader.read_packet(_light_packet(next(iter(frozen["registry"])), frozen))
    assert sample["node_rank_feature"] == 1
    assert all("rank" in node for node in sample["node_flags"])
    # Same content on both branches apart from the feature: the digests differ, the keys do not.
    assert set(sample) == set(without_rank)
    assert set(with_rank) == set(first)
