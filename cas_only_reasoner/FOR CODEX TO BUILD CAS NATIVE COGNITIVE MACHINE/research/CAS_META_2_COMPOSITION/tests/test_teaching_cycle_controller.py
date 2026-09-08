from copy import deepcopy
import pytest

from cas_meta2.codec import canonical_sha256
from cas_meta2.teaching_cycle.controller import Allocation, ExposureLedger, TeachingError
from cas_meta2.teaching_cycle.data import build_dataset
from cas_meta2.teaching_cycle.guided_application import make_cycle


@pytest.fixture(scope="module")
def case():
    return build_dataset()["splits"]["train"][0]


def ledger(curriculum="aligned", mode="simulated"):
    return ExposureLedger(run_id="pure-test", curriculum=curriculum,
        scope_names=["binding_query.weight"], initial_checkpoint="0" * 64,
        train_cases=[build_dataset()["splits"]["train"][0]],
        development_cases=build_dataset()["splits"]["development"],
        allocation=Allocation(2, 12, 1, 2, .9, 1, 1), execution_mode=mode)


def receipt(log, records):
    return {"run_id": log.run_id, "execution_mode": log.execution_mode,
        "scope_sha256": log.scope_sha256, "before_checkpoint_sha256": log.checkpoint,
        "training_cases_sha256": log.training_cases_sha256,
        "after_checkpoint_sha256": canonical_sha256([log.checkpoint, len(log.batches)]),
        "optimizer_steps": 1, "batch_size": len(records),
        "input_sha256": canonical_sha256([r["public"] for r in records]),
        "target_sha256": canonical_sha256([r["target_binding"] for r in records]),
        "loss": .5, "gradient_parameter_names": ["binding_query.weight"],
        "changed_parameter_names": ["binding_query.weight"],
        "device": "cuda:0", "gpu_name": "SIMULATED_TEST_DEVICE_NOT_A_PROVIDER_RECEIPT"}


def cycle(log, case, number):
    for record in make_cycle(case, assistance=log.assistance(), curriculum=log.curriculum):
        log.record_batch([str(number)], [record], receipt(log, [record]))


def dev(log, **kwargs):
    inputs = {"split": "development", "checkpoint_sha256": log.checkpoint,
              "input_sha256": log.development_input_sha256,
              "predictions": [c["target_binding"] for c in log.development_cases]}
    return log.observe_development(**{**inputs, **kwargs})


def test_default_allocation_is_substantial_not_unlimited():
    assert Allocation().minimum_full_cycles == 1024
    assert Allocation().maximum_cycles == 4096


def test_documents_and_partial_cycle_do_not_count(case):
    log = ledger()
    records = make_cycle(case)
    assert log.report()["optimizer_steps"] == 0
    for row in records[:6]:
        log.record_batch(["first"], [row], receipt(log, [row]))
    assert log.complete() == 0
    assert sum(log.report()["stage_exposures"].values()) == 6
    log.record_batch(["first"], [records[6]], receipt(log, [records[6]]))
    assert log.complete() == 1
    assert log.report()["verified_neural_cycles"] == 0
    assert log.report()["claimed_cuda_cycles"] == 0
    assert log.report()["status"] == "SIMULATED_ONLY_NOT_DELIVERED"


@pytest.mark.parametrize("field,value,error", [
    ("input_sha256", "a" * 64, "DELIVERED_INPUT_MISMATCH"),
    ("target_sha256", "a" * 64, "DELIVERED_TARGET_MISMATCH"),
    ("scope_sha256", "a" * 64, "RECEIPT_SCOPE_MISMATCH"),
    ("before_checkpoint_sha256", "a" * 64, "CHECKPOINT_CHAIN_BROKEN"),
    ("changed_parameter_names", ["accepted.cjt.weight"], "PARAMETER_SCOPE_ESCAPE"),
    ("optimizer_steps", 0, "OPTIMIZER_STEP_REQUIRED"),
    ("loss", float("nan"), "LOSS_NOT_FINITE"),
    ("execution_mode", "cuda", "RECEIPT_MODE_MISMATCH"),
])
def test_bad_receipt_is_atomic(case, field, value, error):
    log = ledger()
    row = make_cycle(case)[0]
    rec = receipt(log, [row])
    rec[field] = value
    with pytest.raises(TeachingError, match=error):
        log.record_batch(["first"], [row], rec)
    assert log.cycles == {} and log.batches == [] and log.checkpoint == "0" * 64


def test_no_skips_replays_or_heldout(case):
    log = ledger()
    rows = make_cycle(case)
    with pytest.raises(TeachingError, match="INCOMPLETE_CYCLE_START"):
        log.record_batch(["first"], [rows[1]], receipt(log, [rows[1]]))
    log.record_batch(["first"], [rows[0]], receipt(log, [rows[0]]))
    with pytest.raises(TeachingError, match="STAGE_ORDER_OR_REPLAY"):
        log.record_batch(["first"], [rows[0]], receipt(log, [rows[0]]))
    heldout = {**rows[1], "split": "test_fresh"}
    with pytest.raises(TeachingError, match="HELD_OUT_TEACHING_REJECTED"):
        log.record_batch(["first"], [heldout], receipt(log, [heldout]))


def test_guidance_fades_only_after_minimum_and_repeated_checks(case):
    log = ledger()
    with pytest.raises(TeachingError, match="MINIMUM_TEACHING"):
        dev(log)
    for index in range(2):
        cycle(log, case, index)
    dev(log)
    assert log.assistance() == "full"
    with pytest.raises(TeachingError, match="MINIMUM_TEACHING"):
        dev(log)
    cycle(log, case, 2)
    dev(log)
    assert log.assistance() == "faded"
    for index in (3, 4):
        cycle(log, case, index)
        dev(log)
    assert log.assistance() == "none"
    assert all(row["readiness_not_mastery"] for row in log.development)
    with pytest.raises(TeachingError, match="FINAL_TEST_FEEDBACK_REJECTED"):
        dev(log, split="test_fresh")


def test_ordinary_blocks_are_not_aligned_cycles(case):
    log = ledger(curriculum="ordinary")
    cycle(log, case, 1)
    assert log.report()["completed_full_aligned_cycles"] == 0
    assert log.report()["completed_ordinary_blocks"] == 1


def test_no_parameter_change_is_reported_not_turned_into_learning(case):
    log = ledger()
    row = make_cycle(case)[0]
    rec = receipt(log, [row])
    rec.update(after_checkpoint_sha256=log.checkpoint, changed_parameter_names=[],
               gradient_parameter_names=[])
    log.record_batch(["first"], [row], rec)
    assert log.report()["batches_with_parameter_change"] == 0


def test_t4_and_cpu_receipts_rejected(case):
    log = ledger(mode="cuda")
    row = make_cycle(case)[0]
    rec = receipt(log, [row])
    for change in ({"device": "cpu"}, {"gpu_name": "Tesla T4"}):
        with pytest.raises(TeachingError):
            log.record_batch(["first"], [row], {**rec, **change})


def test_allocation_exhaustion_preserves_progress(case):
    log = ledger()
    for index in range(12):
        cycle(log, case, index)
    row = make_cycle(case)[0]
    before = deepcopy(log.report())
    with pytest.raises(TeachingError, match="TEACHING_ALLOCATION_EXHAUSTED"):
        log.record_batch(["too-many"], [row], receipt(log, [row]))
    assert log.report() == before


@pytest.mark.parametrize("change", ["family_id", "public", "alignment", "target_binding"])
def test_stage_label_is_not_proof_of_registered_lesson(case, change):
    log = ledger()
    row = deepcopy(make_cycle(case)[0])
    if change == "public":
        row["public"]["problem"] += " altered meaning"
    elif change == "target_binding":
        row[change] = (row[change] + 1) % 3
    elif change == "alignment":
        row[change] = []
    else:
        row[change] = "unknown"
    with pytest.raises(TeachingError, match="UNREGISTERED_OR_CHANGED_LESSON"):
        log.record_batch(["first"], [row], receipt(log, [row]))
    assert log.cycles == {}


def test_one_repeated_case_cannot_satisfy_full_variety_requirement(case):
    cases = build_dataset()["splits"]["train"][:2]
    log = ExposureLedger(run_id="pure-test", curriculum="aligned",
        scope_names=["binding_query.weight"], initial_checkpoint="0" * 64,
        train_cases=cases, development_cases=build_dataset()["splits"]["development"],
        allocation=Allocation(2, 12, 1, 2, .9, 2, 1), execution_mode="simulated")
    cycle(log, case, 0)
    cycle(log, case, 1)
    with pytest.raises(TeachingError, match="MINIMUM_TEACHING_VARIETY"):
        dev(log)


def test_one_prediction_cannot_stand_for_64_development_cases(case):
    log = ledger()
    with pytest.raises(TeachingError, match="DEVELOPMENT_PREDICTIONS_INVALID"):
        dev(log, predictions=[0])


def test_detached_training_has_exposure_but_cannot_trigger_readiness(case):
    log = ledger()
    for index in range(2):
        for row in make_cycle(case):
            rec = receipt(log, [row])
            rec.update(gradient_parameter_names=[], changed_parameter_names=[],
                       after_checkpoint_sha256=log.checkpoint)
            log.record_batch([str(index)], [row], rec)
    assert log.complete() == 2
    assert log.report()["families_in_complete_gradient_bearing_batches"] == 0
    with pytest.raises(TeachingError, match="BINDING_GRADIENT_DELIVERY_INCOMPLETE"):
        dev(log)


def test_minimum_cycles_per_family_is_enforced(case):
    log = ExposureLedger(run_id="pure-test", curriculum="aligned",
        scope_names=["binding_query.weight"], initial_checkpoint="0" * 64,
        train_cases=[case], development_cases=build_dataset()["splits"]["development"],
        allocation=Allocation(2, 12, 1, 2, .9, 1, 4), execution_mode="simulated")
    cycle(log, case, 0)
    cycle(log, case, 1)
    with pytest.raises(TeachingError, match="MINIMUM_PER_FAMILY_TEACHING"):
        dev(log)
