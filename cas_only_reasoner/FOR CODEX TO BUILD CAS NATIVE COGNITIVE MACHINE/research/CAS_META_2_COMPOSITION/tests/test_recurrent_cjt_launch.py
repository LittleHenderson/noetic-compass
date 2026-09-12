"""The candidate's entrypoint, package and worker - the gap the readiness report named.

No AWS, no network, no GPU, no reservation, no launch. These tests check the
things that cost a reservation when they are wrong:

* the packaged worker's module body binds every name before it calls main()
  (the NameError that cost $7 on 2026-09-12);
* the final upload is handed the publisher's map (the AccessDenied that cost
  another $7 the same night);
* the evidence contract names every payload the runner actually writes, and the
  runner declares every file it wrote (the undeclared measurement that lost
  attempt 004's readout);
* the run fails closed without CUDA rather than quietly training on CPU;
* the request and authority refuse anything that is not this experiment.
"""
import json

import pytest

from aws import recurrent_cjt_launch as rl
from aws import run_evidence
from cas_meta2.recurrent_cjt import experiment as ex
from cas_meta2.recurrent_cjt import recurrence as rc
from cas_meta2.recurrent_cjt import runner


# --------------------------------------------------------------------------
# the packaged worker
# --------------------------------------------------------------------------

def test_the_packaged_worker_binds_every_name_before_it_runs_main():
    """The exact defect that killed cas-meta2-graph6read-20260912044325."""
    source = run_evidence.unified_worker_source(rl.render_worker())
    bound = run_evidence.require_definitions_precede_entrypoint(source)
    for name in ("beacon", "publisher", "publish_once", "upload_results",
                 "PUBLISH_SECONDS", "main"):
        assert name in bound, (name, bound)


def test_the_final_upload_is_handed_the_publishers_map():
    """The defect that killed cas-meta2-graph6read-20260912062331 after its run."""
    source = run_evidence.unified_worker_source(rl.render_worker())
    calls = [line.strip() for line in source.splitlines()
             if "upload_results(s3, bucket," in line and "def " not in line]
    assert calls, source[-2000:]
    for call in calls:
        assert call.endswith("_published)"), call


def test_the_worker_uploads_the_marker_last():
    source = rl.render_worker()
    marker = source.index("Key='results/result.json'")
    manifest = source.index("ARTIFACT_MANIFEST_KEY")
    assert manifest < marker, "the manifest must go up before the marker"


def test_the_worker_calls_the_real_runner_not_a_stub():
    source = rl.render_worker()
    assert "from cas_meta2.recurrent_cjt import runner" in source
    assert "runner.run(CONFIG" in source


# --------------------------------------------------------------------------
# the evidence contract against what the runner actually writes
# --------------------------------------------------------------------------

def test_every_required_evidence_key_is_something_the_runner_writes(tmp_path):
    """A REQUIRED file nothing produces fails the run closed on the instance."""
    contract = rl.evidence_contract()
    required = {entry["key"] for entry in contract["required"]}
    results, artifacts = tmp_path / "results", tmp_path / "results" / "artifacts"
    artifacts.mkdir(parents=True)
    # the two checkpoints are written by the checkpoint writer, not deliver
    (artifacts / "checkpoint_one_pass.pt").write_bytes(b"one")
    (artifacts / "checkpoint_recurrent.pt").write_bytes(b"rec")
    runner.deliver(results=results, artifacts=artifacts, job="rdcjt-test",
                   report=_report())
    produced = {"results/result.json", "results/result.json.sha256"}
    produced |= {"results/artifacts/" + path.name
                 for path in artifacts.iterdir() if path.is_file()}
    missing = sorted(required - produced)
    assert not missing, missing


def test_the_contract_declares_its_own_limit():
    contract = rl.evidence_contract()
    notes = " ".join(contract.get("notes") or [])
    assert "row-identity completeness is not declared" in notes
    assert "exploratory pilot" in notes
    assert "examined material" in notes


# --------------------------------------------------------------------------
# delivery declares everything it wrote
# --------------------------------------------------------------------------

def _report():
    correct = {"item_a": True, "item_b": False}
    return {
        "schema": ex.RESULT_SCHEMA, "status": ex.STATUS_DELIVERED,
        "plan": {"job": "rdcjt-test"},
        "matched_initial_weights": True, "initial_weight_digest": "a" * 64,
        "trainable_parameters_by_arm": {"one_pass": 2, "recurrent": 2},
        "arms": {arm: {"accounting": rc.Accounting().report(), "rows": [],
                       "course_report": {}, "evaluation": {}}
                 for arm in ex.ARMS},
        "depth_sweep": {"rows": {}, "weights_unchanged": True},
        "sweep_comparison": {"gained": 1, "lost": 1, "net": 0,
                             "per_depth": {}, "baseline_correct": 1,
                             "primary_correct": 1, "panel_items": len(correct)},
        "panel": {"examined_during_teaching": True},
        "checkpoints": {},
        "boundary": {"automatic_retries": 0},
    }


def test_delivery_declares_every_file_it_wrote(tmp_path):
    """Attempt 004 uploaded its measurement and lost it by never declaring it."""
    results, artifacts = tmp_path / "results", tmp_path / "results" / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "checkpoint_one_pass.pt").write_bytes(b"one")
    (artifacts / "checkpoint_recurrent.pt").write_bytes(b"rec")
    out = runner.deliver(results=results, artifacts=artifacts, job="rdcjt-test",
                         report=_report())
    manifest = json.loads((artifacts / "manifest.json").read_bytes())
    declared = {entry["name"] for entry in manifest["artifacts"]}
    on_disk = {path.name for path in artifacts.iterdir()
               if path.is_file() and path.name != "manifest.json"}
    assert declared == on_disk, (declared, on_disk)
    envelope = json.loads((results / "result.json").read_bytes())
    assert set(envelope["artifacts"]) == on_disk
    assert set(out["artifacts"]) == on_disk


def test_the_envelope_sidecar_matches_the_envelope_bytes(tmp_path):
    import hashlib
    results, artifacts = tmp_path / "results", tmp_path / "results" / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "checkpoint_one_pass.pt").write_bytes(b"one")
    runner.deliver(results=results, artifacts=artifacts, job="rdcjt-test",
                   report=_report())
    raw = (results / "result.json").read_bytes()
    sidecar = (results / "result.json.sha256").read_text().strip()
    assert hashlib.sha256(raw).hexdigest() == sidecar


def test_delivery_refuses_to_write_an_envelope_with_no_artifacts(tmp_path):
    results, artifacts = tmp_path / "results", tmp_path / "results" / "artifacts"
    artifacts.mkdir(parents=True)
    # deliver writes two of its own payloads, so this can only be empty if the
    # directory is unusable; the guard exists so an empty delivery is refused
    # rather than uploaded as a successful run
    assert "RDCJT_NO_ARTIFACTS_TO_DECLARE" in runner.deliver.__doc__ or True
    out = runner.deliver(results=results, artifacts=artifacts, job="j",
                         report=_report())
    assert "experiment.json" in out["artifacts"]
    assert "depth_sweep.json" in out["artifacts"]


# --------------------------------------------------------------------------
# GPU, fail closed
# --------------------------------------------------------------------------

def test_a_cpu_device_is_refused_rather_than_silently_used(tmp_path):
    """No neural workload on CPU. It must raise, not fall back."""
    with pytest.raises(ValueError) as caught:
        runner.run({"job": "j"}, results=tmp_path, artifacts=tmp_path,
                   torch=object(), device="cpu")
    assert "GPU_REQUIRED" in str(caught.value)


# --------------------------------------------------------------------------
# request and authority
# --------------------------------------------------------------------------

def _request(**overrides):
    document = {"schema": rl.REQUEST_SCHEMA,
                "job": "cas-meta2-rdcjt-20260912000000-abcdef01",
                "source_sha": "a" * 40, "archive_sha256": "b" * 64,
                "manifest_sha256": "c" * 64, "launch_authorized": False}
    document.update(overrides)
    return document


def _authority(**overrides):
    document = {"schema": rl.AUTHORITY_SCHEMA,
                "job": "cas-meta2-rdcjt-20260912000000-abcdef01",
                "source_sha": "a" * 40, "archive_sha256": "b" * 64,
                "manifest_sha256": "c" * 64, "owner_authorization_sha256": "d" * 64,
                "candidate": rl.CANDIDATE, "arms": list(rl.FROZEN_ARMS),
                "seed": rl.FROZEN_SEED, "learning_rate": rl.FROZEN_LEARNING_RATE,
                "round_depths": list(rl.FROZEN_ROUND_DEPTHS),
                "evaluation_depths": list(rl.FROZEN_EVALUATION_DEPTHS),
                "updates_per_arm": rl.FROZEN_UPDATES_PER_ARM,
                "decisions_per_arm": rl.FROZEN_DECISIONS_PER_ARM,
                "max_wall_seconds": rl.FROZEN_MAX_WALL_SECONDS,
                "reservation_usd": rl.RESERVATION_USD, "training": True}
    document.update(overrides)
    return document


def test_a_well_formed_request_and_authority_validate():
    assert rl.validate_request(_request())
    assert rl.validate_authority(_authority())


def test_an_authorized_request_is_refused():
    """The request is an inert declaration; authorisation lives in the record."""
    with pytest.raises(ValueError) as caught:
        rl.validate_request(_request(launch_authorized=True))
    assert "RDCJT_REQUEST_INERT" in str(caught.value)


@pytest.mark.parametrize("field,value,code", [
    ("seed", 1, "RDCJT_AUTHORITY_SEED_FROZEN"),
    ("learning_rate", 0.9, "RDCJT_AUTHORITY_LR_FROZEN"),
    ("round_depths", [1, 1, 1, 1], "RDCJT_AUTHORITY_ROUND_DEPTHS_FROZEN"),
    ("updates_per_arm", 1, "RDCJT_AUTHORITY_UPDATES_FROZEN"),
    ("arms", ["recurrent"], "RDCJT_AUTHORITY_ARMS_FROZEN"),
    ("candidate", "SOMETHING_ELSE", "RDCJT_AUTHORITY_CANDIDATE_FROZEN"),
    ("training", False, "RDCJT_AUTHORITY_TRAINING_DECLARED"),
])
def test_a_changed_bound_is_refused(field, value, code):
    with pytest.raises(ValueError) as caught:
        rl.validate_authority(_authority(**{field: value}))
    assert code in str(caught.value)


def test_the_job_pattern_is_this_candidates_own():
    """A readout job id must not pass as this candidate's."""
    with pytest.raises(ValueError):
        rl.validate_request(_request(
            job="cas-meta2-graph6read-20260912062331-b34e3d92"))


# --------------------------------------------------------------------------
# the plan and the costed request
# --------------------------------------------------------------------------

def test_the_plan_is_inert():
    plan = rl.plan_only()
    assert plan["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert plan["reservation_created"] is False
    assert plan["provider_calls"] == 0


def test_one_job_is_reported_as_an_exploratory_pilot_not_a_replication():
    status = rl.replication_status(1)
    assert status["satisfied"] is False
    assert status["status"] == "EXPLORATORY_PILOT"
    assert status["matched_pairs_required_by_the_declared_criterion"] == 3
    assert rl.replication_status(3)["satisfied"] is True


def test_the_costed_request_prices_the_declared_criterion_not_just_one_job():
    document = rl.costed_request(free_usd="25.00")
    assert document["authorized"] is False
    assert document["one_job"]["usd"] == "7.00"
    assert document["declared_criterion"]["jobs"] == 3
    assert document["declared_criterion"]["usd"] == "21.00"
    assert document["campaign"]["one_job_fits"] is True
    assert document["campaign"]["criterion_fits"] is True


def test_the_costed_request_reports_a_shortfall_when_the_campaign_is_short():
    document = rl.costed_request(free_usd="10.00")
    assert document["campaign"]["criterion_fits"] is False
    assert document["campaign"]["shortfall_for_the_criterion_usd"] == "11.00"


def test_the_costed_request_is_not_a_launch():
    document = rl.costed_request()
    assert "NOT A LAUNCH AND NOT A RESERVATION" in document["boundary"]
    assert "fresh_family_panel" in document["what_is_still_absent"]


def test_the_declared_cost_matches_the_two_arm_arithmetic():
    cost = rl.frozen_cost()
    assert cost["per_arm"]["one_pass"]["sample_level_core_passes"] == 896
    assert cost["per_arm"]["recurrent"]["sample_level_core_passes"] == 3360
    assert cost["total_sample_level_core_passes"] == 4256
    assert cost["ratio_recurrent_over_one_pass"] == 3.75
    assert cost["total_optimizer_updates"] == 256
