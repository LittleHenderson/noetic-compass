"""Focused regressions for the CRITICAL-MASS 2x pointer version: R18's science, twice the training.

WHAT THIS FILE IS FOR. The new version of the pointer study trains 20 passes instead of R18's measured 10.
Exactly four things are allowed to move, and this file tests each one, plus the things that must NOT move:

  1. the training duration           -- PASSES is 20, and 20 is derived from a MEASUREMENT, not a guess;
  2. the evaluation schedule         -- pass 10 (R18's duration) AND pass 20 are both evaluated, and no
                                        checkpoint is selected over any other;
  3. the required output envelope    -- every pass 11-20 batches/updates file and the pass-20 evaluations
                                        are in the required artifact set;
  4. the resource envelope           -- wall/instance limits and the reservation fit a $20.00 all-services
                                        cap, with one machine, no automatic retry, and cleanup preserved.

Everything else -- the model and learner, the course, the batch order, the optimizer, the held-back worlds
and records, the 59-item hard development panel, the scoring and source logic -- is R18's and is asserted
here to be unchanged.

Pure: no torch, no GPU, no network, no AWS call, no ledger write. `budget.validate_plan` is the ledger's own
arithmetic and is called for its verdict, not to reserve anything.
"""
import builtins
import inspect
import sys
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

import pytest

# Self-contained import path, as `test_typed_pointer_study.py` does: do not depend on another test module.
for _extra in (Path(__file__).resolve().parents[1],
               Path(__file__).resolve().parents[1] / "research/CAS_META_2_COMPOSITION"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from aws import budget as ledger  # noqa: E402
from aws import typed_pointer_launch as launch  # noqa: E402
from cas_meta2.typed_teaching import pointer_contract as contract  # noqa: E402
from cas_meta2.typed_teaching import practice_contract as practice  # noqa: E402
from cncm import typed_pointer_worker as worker  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# The MEASUREMENT the 20 passes were set from: the DELIVERED R17 job, 10 passes, seed 20260917,
# `records/typed_pointer_001/receipt_analogy_on_20260917`. Raw fields, quoted exactly:
#   result.json elapsed_seconds                 10,516.263135700006 s
#   worker_report.json elapsed_seconds           9,895.504149891001 s
#   phase_timings measured training_seconds      7,197.795890278999 s over 1,470 updates
#   phase_timings measured evaluations 21        summing to 1,088.1962510759972 s
#   phase_timings measured phase_a_seconds       890.397366079 s over 3 checkpoints
#   phase_timings measured other                 719.1146424570053 s
#   measured non-worker overhead                 598.1888835440004 s
#   on-demand rate / ancillary                   2.5200000000 USD/h / 1.48 USD
R17_UPDATES = 1470
R17_TRAINING_SECONDS = 7197.795890278999
R17_EVALUATIONS = 21
R17_EVALUATION_SECONDS = 1088.1962510759972
R17_PHASE_A_SECONDS = 890.397366079
R17_PHASE_A_CHECKPOINTS = 3
R17_OTHER_SECONDS = 719.1146424570053
NON_WORKER_OVERHEAD_SECONDS = 598.1888835440004
HOURLY_USD = Decimal("2.5200000000")
ANCILLARY_USD = Decimal("1.48")
OTHER_SERVICES_ALLOWANCE_USD = Decimal("0.10")
ALL_SERVICES_CAP_USD = Decimal("20.00")
TEN_PASS_STRATIFIED_DIGEST = "1c67edd74bf670a1b2b17af63209bc33bc2a92bc3a796e2d66f285d10c7b5304"


@pytest.fixture(autouse=True)
def public_only(monkeypatch):
    """The same numeric/provider import guard the practice and pointer study files use."""
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


# ----------------------------------------------------------------------------------------------------------------
# 1. THE VERSION IDENTITY
# ----------------------------------------------------------------------------------------------------------------
def test_the_version_is_new_and_cannot_be_read_as_r18():
    assert contract.EXPERIMENT_VERSION == "cncm.typed-pointer-critical-mass-2x/1"
    assert contract.EXPERIMENT_VERSION != "R18"
    assert contract.VERSION_PASS_MULTIPLIER == 2
    # The identity travels with the design, which is what the worker config, the package manifest
    # (`typed_design`) and the worker report all carry.
    assert contract.DESIGN["experiment_version"] == contract.EXPERIMENT_VERSION
    assert contract.DESIGN["pass_multiplier_over_r18"] == 2
    assert contract.RUN_MODEL_SEED == contract.DESIGN["run_model_seed"] == 20260918
    assert contract.DESIGN["training_duration_change_only"].startswith("SAME_MODEL_DATA_BATCH_ORDER")
    assert launch.EXPERIMENT["version"] == contract.EXPERIMENT_VERSION
    # The R18 comparison point is still a named, checkable constant, so "twice R18" is not a bare word.
    assert contract.TEN_PASSES == 10 and practice.PASSES == 10


def test_r18s_constant_learning_rate_and_optimizer_are_preserved():
    assert contract.DESIGN["optimizer_config"] == practice.DESIGN["optimizer_config"]
    assert contract.DESIGN["optimizer_config"]["learning_rate"] == 0.003
    assert contract.DESIGN["learning_rate_schedule"] == "CONSTANT_AS_HELM_1_0"
    assert contract.DESIGN["planned_main_updates"] is None


# ----------------------------------------------------------------------------------------------------------------
# 2. THE TRAINING DURATION, AND THE MEASUREMENT THAT SET IT
# ----------------------------------------------------------------------------------------------------------------
def test_twenty_passes_are_the_measured_doubling_of_r18s_ten():
    assert contract.PASSES == 20 == contract.VERSION_PASS_MULTIPLIER * practice.PASSES
    assert contract.DESIGN["passes"] == 20
    # The update ceiling the contract has carried since the design phase still permits it: 20 x 147 + 16.
    assert contract.LEARNER_MAX_UPDATES_CEILING == contract.MAX_PASSES_PERMITTED * 147 + 16 == 3544
    assert 20 <= contract.MAX_PASSES_PERMITTED


def test_the_registered_duration_fits_the_envelope_the_measurement_projects():
    """A measurement, not a guess: R17's own seconds per update, projected over 20 passes."""
    seconds_per_update = R17_TRAINING_SECONDS / R17_UPDATES
    assert seconds_per_update == pytest.approx(4.896459789305442, rel=0, abs=1e-15)
    seconds_per_evaluation = R17_EVALUATION_SECONDS / R17_EVALUATIONS
    assert seconds_per_evaluation == pytest.approx(51.81886909885701, rel=0, abs=1e-12)
    main_updates = contract.PASSES * 147
    assert main_updates == 2940
    # The registered full plan's own evaluation count, read from the worker rather than restated here.
    evaluation_phases = (len(worker.FULL_PLAN["evaluation_phases"])
                         + len(worker.FULL_PLAN["ablation_phases"]))
    assert evaluation_phases == 23
    projected_worker_seconds = (R17_OTHER_SECONDS + main_updates * seconds_per_update
                                + evaluation_phases * seconds_per_evaluation + R17_PHASE_A_SECONDS)
    assert projected_worker_seconds == pytest.approx(17196.937778367716, rel=0, abs=1e-6)
    projected_instance_seconds = projected_worker_seconds + NON_WORKER_OVERHEAD_SECONDS
    assert projected_instance_seconds == pytest.approx(17795.126661911716, rel=0, abs=1e-6)
    # The run must FINISH inside the limits it declares, or the limit is theatre.
    assert projected_worker_seconds < contract.WORKER_DEADLINE_SECONDS == 23100
    assert projected_instance_seconds < contract.INSTANCE_SECONDS_MAX == 25200
    # The core-call budget, re-checked against the same measurement as the update budget was.
    assert contract.PASSES * 1176 * contract.PLANNED_WORK_ROUNDS == 188160
    assert contract.PASSES * 1176 * contract.PLANNED_WORK_ROUNDS < contract.MAX_CORE_CALLS == 600000


# ----------------------------------------------------------------------------------------------------------------
# 3. PASS 10 AND PASS 20 ARE BOTH EVALUATED; NOTHING IS SELECTED
# ----------------------------------------------------------------------------------------------------------------
def test_pass_ten_and_pass_twenty_are_both_evaluated_and_neither_is_selected():
    assert contract.PASS_CHECKPOINTS == (0, 1, 2, 4, 6, 8, 10, 20)
    assert 10 in contract.PASS_CHECKPOINTS and 20 in contract.PASS_CHECKPOINTS
    assert contract.FULL_COURSE_CHECKPOINTS == (0, 1, 10, 20)
    assert contract.DESIGN["pass_checkpoints"] == [0, 1, 2, 4, 6, 8, 10, 20]
    assert contract.DESIGN["full_course_checkpoints"] == [0, 1, 10, 20]
    assert contract.DESIGN["evaluated_at_both_durations"] is True
    assert contract.DESIGN["best_checkpoint_selection"] is False
    # The worker's registered plan evaluates exactly those checkpoints, at BOTH durations, and the
    # pass-20 evaluation is the full course (comparable with pass 10) plus the development panel.
    plan, claim_bearing = worker.schedule_plan()
    assert claim_bearing is True, "the 20-pass plan IS this version's registered full run"
    assert plan["passes"] == contract.PASSES == 20
    assert plan["updates"] is None and plan["evaluations"] == [0, 1, 2, 4, 6, 8, 10, 20]
    phases = set(plan["evaluation_phases"])
    assert {"course_p10", "course_p20", "development_p10", "development_p20"} <= phases
    # Both durations are scored on the full course: 10 was R18's full-course point, 20 is this version's.
    assert "course_p10" in phases and "course_p20" in phases
    # No "best" artifact and no selection phase exists anywhere in the plan.
    assert not any("best" in name for name in phases)
    assert not any("best" in name for name in worker.expected_artifact_names(plan))


def test_both_duration_checks_cover_the_course_held_back_slice_and_59_item_development_panel(material):
    frozen, _, development = material
    held, _, _ = contract.split(frozen)
    assert len(held) == 127
    assert len(contract.development_packets(development)) == 59
    phases = set(worker.FULL_PLAN["evaluation_phases"])
    for number in (10, 20):
        assert "course_p%02d" % number in phases
        assert "development_p%02d" % number in phases
    implementation = inspect.getsource(worker._main_training)
    assert '_evaluate(main, packets, name' in implementation
    assert '_split_score(scored, ctx["sides"])' in implementation


def test_only_seed_20260918_is_admitted_for_the_single_fresh_job():
    base = {"schema": launch.REQUEST_SCHEMA,
            "job": "cas-meta2-tpntr-20260924000000-aaaaaaaa-m-20260918",
            "source_sha": "a" * 40, "archive_sha256": "b" * 64,
            "manifest_sha256": "c" * 64, "launch_authorized": False}
    assert launch.validate_request(base) == base
    other_registered_seed = base["job"].replace("20260918", "20260917")
    assert contract.parse_job(other_registered_seed)[1] == 20260917
    with pytest.raises(ValueError, match="POINTER_REQUEST_MODEL_SEED"):
        launch.validate_request({**base, "job": other_registered_seed})


# ----------------------------------------------------------------------------------------------------------------
# 4. THE REQUIRED ARTIFACTS COVER PASSES 11-20
# ----------------------------------------------------------------------------------------------------------------
def test_required_artifacts_cover_every_pass_from_11_to_20():
    required = set(worker.EXPECTED_ARTIFACTS)
    for number in range(1, 21):
        assert "pass_%02d_batches.jsonl" % number in required
        assert "pass_%02d_updates.jsonl" % number in required
    for number in range(11, 21):
        assert "pass_%02d_batches.jsonl" % number in required, "pass 11-20 outputs are required"
    assert len(worker.FULL_PLAN["evaluation_phases"]) == 18
    assert worker.EVIDENCE_REQUIRED_COUNT == len(required) + 3
    # The launcher's pre-run evidence contract is the one the job record pins: it must require exactly the
    # names the registered plan produces, plus the terminal envelope and the artifact inventory.
    document = launch.evidence_contract()
    keys = set(launch.run_evidence.contract_keys(document))
    assert keys == ({"results/result.json", "results/result.json.sha256", "results/artifacts/manifest.json"}
                    | {"results/artifacts/" + name for name in required})
    assert document["required_count"] == len(keys) == worker.EVIDENCE_REQUIRED_COUNT
    assert document["cannot_shrink_after_a_failure"] is True
    assert document["worker_may_not_amend_required"] is True
    assert document["notes"][0].startswith("20 passes: ")
    # The ten-pass contract this version descends from required 102 keys; the difference is exactly the ten
    # new passes' two files each plus the pass-20 evaluation pair.
    assert len(keys) == 126 and len(keys) - 102 == 10 * 2 + 4


# ----------------------------------------------------------------------------------------------------------------
# 5. THE RESOURCE ENVELOPE FITS A USD 20.00 ALL-SERVICES CAP
# ----------------------------------------------------------------------------------------------------------------
def test_the_declared_envelope_fits_a_usd_20_all_services_cap():
    plan = launch.reservation_plan_for(launch.DESIGN)
    assert plan["instance_count"] == 1 and plan["automatic_retries"] == 0
    assert plan["runtime_seconds_max"] == contract.INSTANCE_SECONDS_MAX == 25200
    assert plan["instance_type"] == "g7.2xlarge" and plan["region"] == "us-west-2"
    # The ledger's plan carries the conservative 2-decimal rate; the pricing query observed the same number
    # to ten decimals ("2.5200000000"). Decimal equality is numeric, so the arithmetic below is exact either way.
    assert plan["on_demand_hourly_usd_max"] == "2.52" == str(HOURLY_USD.normalize())
    # The LEDGER'S OWN arithmetic decides the bound: reserved >= rate x runtime / 3600 + ancillary.
    bound = ledger.validate_plan(plan, contract.RESERVATION_USD)
    assert bound == HOURLY_USD * Decimal(25200) / Decimal(3600) + ANCILLARY_USD == Decimal("19.12")
    assert Decimal(contract.RESERVATION_USD) == Decimal("19.20") >= bound
    # All services, not just compute: the reservation plus the other-services allowance is under the cap.
    all_services = Decimal(contract.RESERVATION_USD) + OTHER_SERVICES_ALLOWANCE_USD
    assert all_services == Decimal("19.30") <= ALL_SERVICES_CAP_USD
    assert ALL_SERVICES_CAP_USD - all_services == Decimal("0.70")
    # And the worker's own owner-threshold check must be true of the projected instance time, or the run
    # would report itself outside the envelope the owner approved for this version.
    assert worker.OWNER_PROJECTION_THRESHOLD_SECONDS == contract.INSTANCE_SECONDS_MAX == 25200
    assert launch.BOUNDS == {"training": True, "jobs": 1, "automatic_retries": 0,
                             "reservation_usd": "19.20", "instance_type": "g7.2xlarge", "region": "us-west-2",
                             "instance_seconds_max": 25200, "max_wall_seconds": 23400,
                             "optimizer_updates_max": 2958}
    assert launch.BOUNDS["optimizer_updates_max"] == 20 * 147 + 16 + 2 == 2958


def test_a_bigger_or_retrying_plan_is_refused_by_the_ledger_rule():
    plan = launch.reservation_plan_for(launch.DESIGN)
    with pytest.raises(ValueError):
        ledger.validate_plan({**plan, "runtime_seconds_max": 43200}, contract.RESERVATION_USD)
    with pytest.raises(ValueError):
        ledger.validate_plan({**plan, "instance_count": 2}, contract.RESERVATION_USD)
    with pytest.raises(ValueError):
        ledger.validate_plan({**plan, "automatic_retries": 1}, contract.RESERVATION_USD)
    with pytest.raises(ValueError):
        ledger.validate_plan(plan, "19.11")          # one cent under the declared bound
    assert ledger.validate_plan(plan, "19.12") == Decimal("19.12")


def test_one_machine_no_retry_and_cleanup_are_preserved():
    assert launch.BOUNDS["jobs"] == 1
    assert launch.BOUNDS["automatic_retries"] == 0 == contract.DESIGN["automatic_retries"]
    assert launch.BOUNDS["training"] is True
    assert contract.DESIGN["jobs"] == 1
    # Cleanup is the inherited lifecycle's own stage, reached on every exit path, and this version
    # neither removes nor overrides it: the provider still inherits the cleanup method it runs.
    assert launch.TypedPointerProvider.cleanup.__qualname__.startswith("TypedMatchedProvider")
    assert launch.TypedPointerProvider.cleanup is not launch.TypedPointerProvider.__dict__.get("cleanup")


def test_the_timeout_order_is_strict_and_inside_the_new_envelope():
    ordered = [contract.WORKER_DEADLINE_SECONDS, contract.MAX_WALL_SECONDS, launch.OUTER_TIMEOUT_SECONDS,
               launch.BOOT_WATCHDOG_SECONDS, contract.INSTANCE_SECONDS_MAX]
    assert ordered == [23100, 23400, 24300, 24900, 25200]
    assert ordered == sorted(ordered) and len(set(ordered)) == len(ordered)
    # The launcher's own import-time ordering checks, plus the shared resource plan's inner limit.
    assert launch.shared.RESOURCE_PLAN["instance_seconds_max"] < launch.BOOT_WATCHDOG_SECONDS < \
        contract.INSTANCE_SECONDS_MAX
    # R18 kept 2,100 s between the worker deadline and the instance limit; this version keeps it too.
    assert contract.INSTANCE_SECONDS_MAX - contract.WORKER_DEADLINE_SECONDS == 2100
    # An hour-by-hour cost table, so the cap can be re-read without trusting this file's summary:
    #   23100 s -> $17.65   23400 s -> $17.86   24300 s -> $18.49   24900 s -> $18.91   25200 s -> $19.12
    for seconds, ceiling in ((23100, "17.65"), (23400, "17.86"), (24300, "18.49"), (24900, "18.91"),
                             (25200, "19.12")):
        cost = (HOURLY_USD * Decimal(seconds) / Decimal(3600) + ANCILLARY_USD
                ).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
        assert cost == Decimal(ceiling) <= ALL_SERVICES_CAP_USD


# ----------------------------------------------------------------------------------------------------------------
# 6. WHAT DID NOT MOVE: THE SCHEDULE, THE HOLDOUT, THE 59-ITEM PANEL
# ----------------------------------------------------------------------------------------------------------------
def test_the_batch_order_is_r18s_and_only_the_length_changes(material):
    frozen = material[0]
    ten, ten_stats = contract.pointer_schedule(frozen, passes=10)
    twenty, twenty_stats = contract.pointer_schedule(frozen, passes=20)
    assert ten_stats["updates_per_pass"] == twenty_stats["updates_per_pass"] == 147
    assert ten_stats["presentations_per_pass"] == twenty_stats["presentations_per_pass"] == 1176
    assert twenty_stats["main_updates"] == 2 * ten_stats["main_updates"] == 2940
    assert twenty_stats["passes"] == 20 and ten_stats["passes"] == 10
    # THE BATCH ORDER IS R18's. The ONE stratified pass is the same object in both schedules, and the pass
    # number is the only other input to a batch, so R18's whole ten-pass schedule IS the prefix of this
    # version's: same slots, same round/phase/depth, same record_ids, byte for byte.
    assert twenty[:len(ten)] == ten
    assert len(ten) == 1470 and len(twenty) == 2940
    # Pass 11 is the first pass R18 never ran: it exists here and is a whole, unique pass of its own.
    assert {batch["pass"] for batch in twenty[1470:1617]} == {11}
    assert twenty[1470]["record_ids"] == twenty[0]["record_ids"]
    assert len({batch["occurrence_ids"][0] for batch in twenty}) == 2940
    # The whole-schedule digest is a FUNCTION of the pass count, and it moved exactly as the contract's
    # import-time check requires: 20 passes is NOT the recorded ten-pass value.
    assert ten_stats["batches_digest"] == TEN_PASS_STRATIFIED_DIGEST
    assert twenty_stats["batches_digest"] == contract.STRATIFIED_BATCHES_DIGEST
    assert twenty_stats["batches_digest"] != TEN_PASS_STRATIFIED_DIGEST
    assert contract.STRATIFIED_BATCHES_DIGEST_AT_10_PASSES == TEN_PASS_STRATIFIED_DIGEST


def test_the_holdout_the_scorer_inputs_and_the_59_item_panel_are_unchanged(material):
    frozen, _, development = material
    held, trained, excluded = contract.split(frozen)
    assert (len(held), len(trained), len(excluded)) == (127, 358, 79)
    assert len(held) + len(trained) + len(excluded) == len(frozen["registry"]) == 564
    assert contract.held_worlds(frozen) == list(practice.HELD_WORLDS)
    assert len(contract.held_back_questions(frozen)) == 50
    # The 59-item hard development panel, the one the brief names: built by the matched study's own
    # function, reused by import, unchanged.
    packets = contract.development_packets(development)
    assert len(packets) == 59 == len(development["packets"])
    assert contract.development_packets is practice.development_packets
    # The interference rule is the practice study's own, reused by import, at 16 batches of 8.
    interference = contract.interference_batches(frozen)
    assert interference is not None and len(interference) == contract.INTERFERENCE_UPDATES == 16
    assert all(len(batch["record_ids"]) == contract.INTERFERENCE_BATCH == 8 for batch in interference)
    assert contract.interference_batches is practice.interference_batches
    # The tiers, the gate population rule and the passing bar are R18's.
    assert contract.RELATIONAL == ("parts", "edge_account", "reach", "correspondence", "analogy")
    assert contract.DIRECT_READ == ("definition", "context") and contract.TEXT == ("role_set",)
    assert contract.MIN_PASSING_B == 7 and contract.VERIFIED_POPULATION == 18
    assert contract.VERIFIED_POPULATION_DIGEST == \
        "4b1e3c1f0b8f8be339e281410dc830fac1834432e8d816d67dce58906e90036d"
