"""An owner record's own words must bind the launcher, not just its hash.

Why this file exists. ``OWNER_AUTHORIZATION_READOUT_001.json`` states
``bounds.jobs: 1`` and lists "any further job or automatic retry beyond this
single readout" under ``explicitly_not_authorized``. Four separate jobs ran
against it - $28.00, none of which delivered a measurement - because the
launcher only ever checked that the file's sha256 equalled the value in the
authority. It never opened the record. A bound written in words that no program
reads is not a bound.

The gate is checked here against the REAL record directory, not only against
synthetic fixtures: it must refuse the record that was over-used and pass every
record that was not.

No AWS, no network, no reservation.
"""
import hashlib
import json

import pytest

from aws import graph_training_candidate_launch as candidate
from aws import graph_training_curriculum_launch as curriculum

RECORD_DIR = (curriculum.ROOT / "records/teaching_cycle_001/"
              "graph_first_candidate_001/training_mode_001/face_grounding_001")


def _record(name):
    raw = (RECORD_DIR / name).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def _owner_records():
    return sorted(path.name for path in
                  RECORD_DIR.glob("OWNER_AUTHORIZATION_*.json"))


def test_the_record_directory_still_holds_the_records_this_file_checks():
    names = _owner_records()
    assert "OWNER_AUTHORIZATION_READOUT_001.json" in names
    assert len([n for n in names if "CFC_PILOT" in n]) == 4


def test_the_gate_refuses_a_fifth_job_on_the_record_that_authorized_one():
    """The exact historical violation, read from the committed receipts."""
    record, sha = _record("OWNER_AUTHORIZATION_READOUT_001.json")
    assert record["bounds"]["jobs"] == 1
    used = candidate.owner_record_receipt_count(sha, RECORD_DIR)
    assert len(used) == 4, used
    with pytest.raises(Exception) as caught:
        candidate.require_owner_record_bounds(
            record, {"job": "cas-meta2-graph6read-99999999999999-deadbeef"},
            owner_sha256=sha, receipts_root=RECORD_DIR,
            job="cas-meta2-graph6read-99999999999999-deadbeef")
    assert "OWNER_RECORD_JOB_BUDGET_EXHAUSTED:4_used_of_1_allowed" in str(caught.value)


@pytest.mark.parametrize("name", [n for n in
                                  ("OWNER_AUTHORIZATION_CFC_PILOT_001.json",
                                   "OWNER_AUTHORIZATION_CFC_PILOT_002.json",
                                   "OWNER_AUTHORIZATION_CFC_PILOT_003.json",
                                   "OWNER_AUTHORIZATION_CFC_PILOT_004.json")])
def test_every_record_used_once_still_passes(name):
    """The gate must not condemn the workstream that did it right.

    The four pilot records carry no ``bounds`` block at all, so only the default
    one-job rule applies, and each was used exactly once. Re-running its own job
    is not a second job.
    """
    record, sha = _record(name)
    used = candidate.owner_record_receipt_count(sha, RECORD_DIR)
    assert len(used) == 1, used
    report = candidate.require_owner_record_bounds(
        record, {"job": used[0]}, owner_sha256=sha, receipts_root=RECORD_DIR,
        job=used[0])
    assert report["jobs_allowed"] == 1
    assert report["jobs_already_used"] == []


def test_a_bound_that_contradicts_the_authority_is_refused():
    record = {"bounds": {"reservation_usd": "7.00", "optimizer_updates": 0}}
    authority = {"job": "j", "reservation_usd": "9.00", "optimizer_updates": 0}
    with pytest.raises(Exception) as caught:
        candidate.require_owner_record_bounds(
            record, authority, owner_sha256="a" * 64, receipts_root=RECORD_DIR,
            job="j")
    assert "OWNER_RECORD_BOUND_CONTRADICTED:reservation_usd" in str(caught.value)


@pytest.mark.parametrize("bounds,code", [
    ({"automatic_retries": 1}, "OWNER_RECORD_AUTOMATIC_RETRIES_MUST_BE_ZERO"),
    ({"training": True}, "OWNER_RECORD_TRAINING_NOT_AUTHORIZED"),
    ({"jobs": 0}, "OWNER_RECORD_JOBS_BOUND"),
])
def test_the_refusals_a_record_can_state_about_itself(bounds, code):
    with pytest.raises(Exception) as caught:
        candidate.require_owner_record_bounds(
            {"bounds": bounds}, {"job": "j"}, owner_sha256="b" * 64,
            receipts_root=RECORD_DIR, job="j")
    assert code in str(caught.value)


def test_a_record_may_authorize_more_than_one_job_when_it_says_so(tmp_path):
    """The gate reads the number; it does not impose one."""
    sha = "c" * 64
    for index in (1, 2):
        receipt = tmp_path / ("receipt_job%d" % index)
        receipt.mkdir()
        (receipt / "intent.json").write_text(json.dumps(
            {"authority": {"owner_authorization_sha256": sha,
                           "job": "job%d" % index}}))
    assert len(candidate.owner_record_receipt_count(sha, tmp_path)) == 2
    report = candidate.require_owner_record_bounds(
        {"bounds": {"jobs": 3}}, {"job": "job3"}, owner_sha256=sha,
        receipts_root=tmp_path, job="job3")
    assert report["jobs_already_used"] == ["job1", "job2"]
    with pytest.raises(Exception) as caught:
        candidate.require_owner_record_bounds(
            {"bounds": {"jobs": 2}}, {"job": "job3"}, owner_sha256=sha,
            receipts_root=tmp_path, job="job3")
    assert "2_used_of_2_allowed" in str(caught.value)


def test_receipts_for_another_record_do_not_count(tmp_path):
    receipt = tmp_path / "receipt_other"
    receipt.mkdir()
    (receipt / "intent.json").write_text(json.dumps(
        {"authority": {"owner_authorization_sha256": "d" * 64, "job": "other"}}))
    assert candidate.owner_record_receipt_count("e" * 64, tmp_path) == []


def test_an_unreadable_receipt_is_skipped_not_fatal(tmp_path):
    """A half-written receipt must not be able to block a launch."""
    receipt = tmp_path / "receipt_broken"
    receipt.mkdir()
    (receipt / "intent.json").write_text("{not json")
    assert candidate.owner_record_receipt_count("f" * 64, tmp_path) == []


# --------------------------------------------------------------------------
# training: the record and the job must AGREE
# --------------------------------------------------------------------------

def _bounds(**overrides):
    bounds = {"jobs": 1}
    bounds.update(overrides)
    return {"bounds": bounds}


def test_a_training_record_authorises_a_training_job(tmp_path):
    """The rule that had to be fixed.

    The gate first said "no owner record may authorise training". That is right
    for the readout, whose whole point is zero optimizer updates, and wrong as a
    general rule: it refused CAS_RDCJT_001, a training candidate whose record
    correctly declares training true. It fired before the reservation so it cost
    nothing, but a gate that refuses a legitimate job is as broken as one that
    admits an illegitimate one.
    """
    report = candidate.require_owner_record_bounds(
        _bounds(training=True), {"job": "j", "training": True},
        owner_sha256="a" * 64, receipts_root=tmp_path, job="j")
    assert report["jobs_allowed"] == 1


def test_a_non_training_record_refuses_a_training_job(tmp_path):
    with pytest.raises(Exception) as caught:
        candidate.require_owner_record_bounds(
            _bounds(training=False), {"job": "j", "training": True},
            owner_sha256="a" * 64, receipts_root=tmp_path, job="j")
    assert "OWNER_RECORD_TRAINING_DISAGREES_WITH_AUTHORITY" in str(caught.value)


def test_a_training_record_refuses_a_job_that_does_not_declare_training(tmp_path):
    """Silence is not consent in this direction."""
    with pytest.raises(Exception) as caught:
        candidate.require_owner_record_bounds(
            _bounds(training=True), {"job": "j"},
            owner_sha256="a" * 64, receipts_root=tmp_path, job="j")
    assert "OWNER_RECORD_TRAINING_NOT_AUTHORIZED" in str(caught.value)


def test_the_readout_shape_still_passes(tmp_path):
    """record training false, authority with no training field: the readout."""
    report = candidate.require_owner_record_bounds(
        _bounds(training=False, optimizer_updates=0),
        {"job": "j", "optimizer_updates": 0},
        owner_sha256="a" * 64, receipts_root=tmp_path, job="j")
    assert "training" in report["bounds_checked"]
