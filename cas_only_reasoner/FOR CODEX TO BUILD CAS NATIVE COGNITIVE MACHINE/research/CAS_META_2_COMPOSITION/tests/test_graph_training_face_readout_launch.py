"""Tests for the CFC-pilot readout binding (zero-update recovery of attempt 004).

No AWS, no torch, no model, no reservation. These check the plan, the bounds, the
request/authority gates, the provider's worker config and the package's input
files - the things that decide whether the paid job can only do the zero-update
readout it declares.
"""
import copy
import json
from pathlib import Path

import pytest

from aws import graph6_face_readout_launch as rl
from aws import graph_training_candidate_launch as candidate
from aws import graph_training_curriculum_launch as curriculum

JOB = "cas-meta2-graph6read-20260911140500-abc12345"
SOURCE_SHA = "1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d"
ARCHIVE_SHA = "a" * 64
MANIFEST_SHA = "b" * 64
OWNER_SHA = "c" * 64


# --------------------------------------------------------------------------
# plan and bounds
# --------------------------------------------------------------------------

def test_the_plan_reserves_nothing_and_reads_the_delivered_checkpoints():
    document = rl.plan_only()
    assert document["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert document["provider_calls"] == 0
    assert document["reservation_created"] is False
    facts = document["readout_facts"]
    assert facts["readout_of_job"] == \
        "cas-meta2-graph6face-20260911133305-9723735f"
    assert facts["optimizer_updates"] == 0 and facts["training"] is False
    assert [entry["condition"] for entry in facts["checkpoints"]] == \
        list(rl.FROZEN_CONDITIONS)
    for entry in facts["checkpoints"]:
        assert entry["sha256"] == rl.FROZEN_CHECKPOINTS[entry["condition"]]
        assert entry["bytes"] > 0
    assert facts["panel"] == {"primary_items": 192,
                              "by_layer": {"role_application": 96,
                                           "role_recognition": 96,
                                           "targeted_check": 24},
                              "diagnostics": 24}
    assert document["design"]["training"] is False
    assert document["design"]["launch_enabled"] is False


def test_the_declared_bounds_fit_the_shared_reservation():
    bounds = rl.validate_bounds()
    assert bounds["fits"] is True
    assert bounds["total_ceiling_seconds"] == \
        rl.FROZEN_MAX_WALL_SECONDS + rl.FROZEN_INSTALL_ALLOWANCE_SECONDS
    assert bounds["total_ceiling_seconds"] <= bounds["instance_ceiling_seconds"]

    with pytest.raises(ValueError) as error:
        rl.validate_bounds({"instance_seconds_max": 60})
    assert "READOUT_DESIGN_WALL_CLOCK_EXCEEDS_RESERVATION" in str(error.value)


def test_the_frozen_totals_are_the_ones_attempt_004_published():
    """Hard-coded on purpose: this is the gate the recovery is measured against."""
    assert rl.FROZEN_EXPECTED_TOTALS["cfc_stable_cues"]["role_application"] == \
        {"correct": 76, "total": 96}
    assert rl.FROZEN_EXPECTED_TOTALS["cfc_stable_cues"]["role_recognition"] == \
        {"correct": 55, "total": 96}
    assert rl.FROZEN_EXPECTED_TOTALS["cfc_neutral_cue"]["role_recognition"] == \
        {"correct": 56, "total": 96}
    assert rl.FROZEN_EXPECTED_TOTALS["mixed_order_stable_cues"]["role_recognition"] \
        == {"correct": 47, "total": 96}
    assert rl.FROZEN_EXPECTED_TOTALS["mixed_order_neutral_cue"]["role_recognition"] \
        == {"correct": 52, "total": 96}
    for name in rl.FROZEN_CONDITIONS:
        assert rl.FROZEN_EXPECTED_TOTALS[name]["targeted_check"]["total"] == 24
    assert rl.FROZEN_LOST_MEASUREMENTS_SHA256 == (
        "796658502cba1d3a03f026d3c7f5c97365de7bb35d7f312a5b105e0fa59dffee")


# --------------------------------------------------------------------------
# request and authority gates
# --------------------------------------------------------------------------

def _request(**overrides):
    document = {"schema": rl.REQUEST_SCHEMA, "job": JOB, "source_sha": SOURCE_SHA,
                "archive_sha256": ARCHIVE_SHA, "manifest_sha256": MANIFEST_SHA,
                "launch_authorized": False}
    document.update(overrides)
    return document


def _authority(**overrides):
    document = {"schema": rl.AUTHORITY_SCHEMA, "job": JOB, "source_sha": SOURCE_SHA,
                "archive_sha256": ARCHIVE_SHA, "manifest_sha256": MANIFEST_SHA,
                "owner_authorization_sha256": OWNER_SHA,
                "readout_of_job": rl.READOUT_OF_JOB,
                "conditions": list(rl.FROZEN_CONDITIONS),
                "checkpoints": {name: rl.FROZEN_CHECKPOINTS[name]
                                for name in rl.FROZEN_CONDITIONS},
                "expected_totals": {name: dict(values) for name, values
                                    in rl.FROZEN_EXPECTED_TOTALS.items()},
                "lost_measurements_sha256": rl.FROZEN_LOST_MEASUREMENTS_SHA256,
                "optimizer_updates": 0, "panel_items": 192,
                "seed": rl.FROZEN_SEED, "encoder_seed": rl.FROZEN_ENCODER_SEED,
                "learning_rate": rl.FROZEN_LEARNING_RATE,
                "max_wall_seconds": rl.FROZEN_MAX_WALL_SECONDS,
                "reservation_usd": rl.RESERVATION_USD}
    document.update(overrides)
    return document


def test_a_request_and_authority_for_this_readout_validate():
    assert rl.validate_request(_request())["job"] == JOB
    assert rl.validate_authority(_authority())["optimizer_updates"] == 0


def test_an_authorized_request_is_refused_because_this_binding_stays_inert():
    with pytest.raises(ValueError) as error:
        rl.validate_request(_request(launch_authorized=True))
    assert "READOUT_REQUEST_INERT" in str(error.value)


def test_the_job_name_is_pinned_to_this_readout():
    with pytest.raises(ValueError) as error:
        rl.validate_request(_request(job="cas-meta2-graph6face-20260911133305-9723735f"))
    assert "READOUT_REQUEST_JOB" in str(error.value)
    with pytest.raises(ValueError) as error:
        rl.validate_authority(_authority(job="anything-else"))
    assert "READOUT_AUTHORITY_JOB" in str(error.value)


def test_a_missing_or_extra_authority_field_is_refused():
    document = _authority()
    del document["expected_totals"]
    with pytest.raises(ValueError) as error:
        rl.validate_authority(document)
    assert "READOUT_AUTHORITY_FIELDS" in str(error.value)

    document = _authority()
    document["train_the_model"] = True
    with pytest.raises(ValueError) as error:
        rl.validate_authority(document)
    assert "READOUT_AUTHORITY_FIELDS" in str(error.value)


@pytest.mark.parametrize("field,value,code", [
    ("readout_of_job", "cas-meta2-graph6face-other", "READOUT_AUTHORITY_OF_JOB_FROZEN"),
    ("conditions", list(reversed(rl.FROZEN_CONDITIONS)),
     "READOUT_AUTHORITY_CONDITIONS_FROZEN"),
    ("optimizer_updates", 1, "READOUT_AUTHORITY_ZERO_UPDATES_FROZEN"),
    ("optimizer_updates", -1, "READOUT_AUTHORITY_ZERO_UPDATES_FROZEN"),
    ("panel_items", 96, "READOUT_AUTHORITY_PANEL_FROZEN"),
    ("seed", 1, "READOUT_AUTHORITY_SEED_FROZEN"),
    ("encoder_seed", 1, "READOUT_AUTHORITY_ENCODER_SEED_FROZEN"),
    ("learning_rate", 0.001, "READOUT_AUTHORITY_LR_FROZEN"),
    ("max_wall_seconds", 99999.0, "READOUT_AUTHORITY_WALL_FROZEN"),
    ("reservation_usd", "70.00", "READOUT_AUTHORITY_RESERVATION_FROZEN"),
    ("lost_measurements_sha256", "d" * 64,
     "READOUT_AUTHORITY_LOST_DIGEST_FROZEN"),
])
def test_every_frozen_authority_field_fails_closed_when_it_is_changed(field, value,
                                                                     code):
    with pytest.raises(ValueError) as error:
        rl.validate_authority(_authority(**{field: value}))
    assert code in str(error.value), (field, str(error.value))


def test_a_changed_checkpoint_hash_or_delivered_total_fails_closed():
    checkpoints = {name: rl.FROZEN_CHECKPOINTS[name] for name in rl.FROZEN_CONDITIONS}
    checkpoints["cfc_stable_cues"] = "e" * 64
    with pytest.raises(ValueError) as error:
        rl.validate_authority(_authority(checkpoints=checkpoints))
    assert "READOUT_AUTHORITY_CHECKPOINTS_FROZEN" in str(error.value)

    totals = copy.deepcopy(rl.FROZEN_EXPECTED_TOTALS)
    totals["cfc_stable_cues"]["role_application"]["correct"] = 96
    with pytest.raises(ValueError) as error:
        rl.validate_authority(_authority(expected_totals=totals))
    assert "READOUT_AUTHORITY_TOTALS_FROZEN" in str(error.value)
    # and the frozen constant itself is untouched by that attempt
    assert rl.FROZEN_EXPECTED_TOTALS["cfc_stable_cues"]["role_application"] == \
        {"correct": 76, "total": 96}


def test_owner_authorization_must_carry_the_owner_words(tmp_path):
    path = tmp_path / "owner.json"
    path.write_text(json.dumps({"schema":
                                "cas-cube-face-readout-owner-authorization/1"}))
    with pytest.raises(ValueError) as error:
        rl.validate_owner_authorization(path)
    assert "READOUT_OWNER_INSTRUCTION_REQUIRED" in str(error.value)

    path.write_text(json.dumps({"schema": "something-else",
                                "owner_instruction_raw": "GO"}))
    with pytest.raises(ValueError) as error:
        rl.validate_owner_authorization(path)
    assert "READOUT_OWNER_AUTHORIZATION_SCHEMA" in str(error.value)

    path.write_text(json.dumps(
        {"schema": "cas-cube-face-readout-owner-authorization/1",
         "owner_instruction_raw": "Yes - authorise the bounded zero-update readout"}))
    assert rl.validate_owner_authorization(path)["owner_instruction_raw"].startswith(
        "Yes")


# --------------------------------------------------------------------------
# provider config and package inputs
# --------------------------------------------------------------------------

def _provider():
    return rl.FaceReadoutProvider(
        job=JOB, source_sha=SOURCE_SHA, archive_sha256=ARCHIVE_SHA,
        manifest_sha256=MANIFEST_SHA, ledger_path=curriculum.LEDGER_PATH,
        clients={})


def test_the_provider_binds_a_zero_update_worker_config():
    provider = _provider()
    assert isinstance(provider, candidate.CandidateProvider)
    assert provider.worker_name == rl.WORKER_NAME
    assert provider.result_schema == rl.RESULT_SCHEMA
    assert "WORKER_FAILED" in provider.failure_statuses
    with pytest.raises(ValueError) as error:
        provider._worker_config("bucket-name")
    assert str(error.value).startswith("CANDIDATE_PROVIDER_AUTHORITY_HASH")

    provider.set_authority_sha256(OWNER_SHA)
    config = provider._worker_config("bucket-name")
    assert config["schema"] == "cas.cube-face-readout-config/1"
    assert config["condition_order"] == list(rl.FROZEN_CONDITIONS)
    assert config["optimizer_updates"] == 0
    assert config["checkpoint_dir"] == rl.FROZEN_CHECKPOINT_DIR
    assert config["authority_sha256"] == OWNER_SHA
    for name in rl.FROZEN_CONDITIONS:
        assert config["conditions"][name]["sha256"] == rl.FROZEN_CHECKPOINTS[name]
        assert config["conditions"][name]["checkpoint"] == \
            "checkpoint_%s.pt" % name
        assert config["expected_totals"][name]["targeted_check"]["total"] == 24
    assert config["lost_measurements_sha256"] == rl.FROZEN_LOST_MEASUREMENTS_SHA256


def test_the_package_carries_the_delivered_checkpoints_as_real_members():
    names = rl.package_data_files()
    for name in rl.FROZEN_CONDITIONS:
        assert (rl.FROZEN_CHECKPOINT_DIR + "/checkpoint_%s.pt" % name) in names
    assert names == tuple(sorted(names))
    for name in names:
        assert name.startswith(candidate.PILOT.rstrip("/") + "/"), name
        assert (candidate.ROOT / name.replace(candidate.PILOT, "", 1)).is_file() or \
            (Path(curriculum.ROOT) / name).is_file(), name
    assert len(names) == len(rl.FROZEN_CONDITIONS) + len(candidate.package_data_files())


def test_the_checkpoints_are_read_from_git_at_the_packaged_commit():
    """The builder reads every member from git, so the weights must be committed.

    This drives the builder's own accessor, not a hand-written git command: that
    accessor prepends the repository path prefix and disables line-ending
    translation, which is what makes a binary checkpoint round-trip byte-identically
    into the package. A checkpoint only present in the working tree would be absent
    from the package, and the deployed worker would fail closed on its own missing
    input.
    """
    import hashlib
    import subprocess

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(curriculum.ROOT),
                            capture_output=True, text=True).stdout.strip()
    assert commit
    for name in rl.FROZEN_CONDITIONS:
        member = rl.FROZEN_CHECKPOINT_DIR + "/checkpoint_%s.pt" % name
        raw = curriculum.git_bytes(curriculum.ROOT, commit, member)
        actual = hashlib.sha256(raw).hexdigest()
        assert actual == rl.FROZEN_CHECKPOINTS[name], (member, actual)


def test_the_rendered_worker_runs_the_readout_body_and_uploads_last():
    worker = rl.render_worker()
    assert "face_readout.run(CONFIG" in worker
    assert "gpu_adapter._cuda()" in worker
    assert "torch==2.11.0" in worker
    assert "subprocess.run([python, '-B', str(runner), str(root)]" in worker
    assert worker.index("Key=ARTIFACT_MANIFEST_KEY") < worker.index(
        "Key='results/result.json'")
    assert worker.index("'result.json.sha256'") < worker.index(
        "Key='results/result.json'")
    assert "WORKER_FAILED" in worker
    assert "REMOTE_FINISHED" in worker
    # the readout trains nothing, so the worker must not install or run a trainer
    assert "face_worker" not in worker
    assert "batch" not in worker.lower() or "batch_size" not in worker
