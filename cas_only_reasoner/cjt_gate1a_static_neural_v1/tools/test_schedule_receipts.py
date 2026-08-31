"""test_schedule_receipts.py -- the section-5 run-schedule receipt tests."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
from exec.schedule import RunSchedule, ScheduleViolation  # noqa: E402

SCHED = RunSchedule.load(PKG / "RUN_SCHEDULE_MANIFEST_CANDIDATE.json")
LAYER, COMMIT, REV, IMG = 12, "ab" * 20, "cd" * 20, "sha256:" + "12" * 32


def good_receipts():
    return [{"arm": a, "seed": s, "status": "SUCCESS",
             "update_count": SCHED.updates_per_run, "selected_layer": LAYER,
             "checkpoint_sha256": "ee" * 32, "cache_manifest_sha256": "ff" * 32,
             "model_revision_sha": REV, "container_image_digest": IMG,
             "package_commit_sha": COMMIT}
            for (a, s) in SCHED.expected_claim_bearing()]


def validate(receipts):
    return SCHED.validate_claim_bearing_receipts(
        receipts, selected_layer=LAYER, expected_commit=COMMIT,
        expected_model_revision=REV, expected_container_digest=IMG)


def expect_refused(name, receipts):
    try:
        validate(receipts)
    except ScheduleViolation:
        print(f"PASS {name}")
        return
    raise AssertionError(f"{name}: bad receipt set ACCEPTED")


def main():
    assert SCHED.expected_total_runs() == 29 and len(validate(good_receipts())) == 24
    print("PASS schedule-derived receipt set (24 claim-bearing from the signed "
          "schedule, 29 total runs -- never a hardcoded count)")
    r = good_receipts(); r[3] = None
    expect_refused("test_none_receipts_refused", r)
    r = good_receipts(); r.append(copy.deepcopy(r[0]))
    expect_refused("test_duplicate_arm_seed_refused", r)
    expect_refused("test_missing_arm_seed_refused", good_receipts()[:-1])
    r = good_receipts(); r.append({**r[0], "arm": "S9"})
    expect_refused("test_extra_arm_seed_refused", r)
    r = good_receipts(); r[5]["status"] = "FAILED"
    expect_refused("test_failed_run_receipt_refused", r)
    r = good_receipts(); r[6]["update_count"] = SCHED.updates_per_run - 1
    expect_refused("test_wrong_update_count_refused", r)
    r = good_receipts(); r[7]["selected_layer"] = 24
    expect_refused("test_wrong_layer_refused", r)
    r = good_receipts(); r[8]["checkpoint_sha256"] = "short"
    expect_refused("test_wrong_checkpoint_digest_refused", r)
    r = good_receipts(); r[9]["cache_manifest_sha256"] = None
    expect_refused("test_wrong_cache_digest_refused", r)
    r = good_receipts(); r[10]["model_revision_sha"] = "0" * 40
    expect_refused("wrong_model_identity_refused", r)
    r = good_receipts(); r[11]["package_commit_sha"] = "0" * 40
    expect_refused("wrong_package_commit_refused", r)
    got = validate(good_receipts())
    assert set(got) == set(SCHED.expected_claim_bearing())
    print("PASS test_schedule_receipt_set_exactly_matches")
    print("ALL SCHEDULE-RECEIPT TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
