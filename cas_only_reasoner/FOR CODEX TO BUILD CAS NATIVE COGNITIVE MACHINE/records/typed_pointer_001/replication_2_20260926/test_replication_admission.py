"""Focused public admission checks, executed on bounded AWS CPU only."""
import importlib.util
from copy import deepcopy
from pathlib import Path
import pytest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import campaign_operator

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("replication_admission", HERE / "prepare_replication.py")
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)
PLAN_HASH = writer.digest((HERE / "PLAN.json").read_bytes())

@pytest.mark.parametrize("seed", [20260917, 20260919])
def test_registered_seed_keeps_source_science_package_and_all_128_requirements(seed):
    plan = writer.load_plan(PLAN_HASH)
    records = writer.build_records(plan, PLAN_HASH, seed)
    request = writer.json.loads(records["request.json"])
    authority = writer.json.loads(records["authority.json"])
    study = writer.json.loads(records["study.json"])
    reference = writer.json.loads((writer.REFERENCE / "authority.json").read_bytes())["worker_config"]
    writer.assert_only_seed_difference(authority["worker_config"], reference, seed)
    design = authority["worker_config"]["design"]
    assert request["source_sha"] == writer.SOURCE
    assert request["archive_sha256"] == writer.ARCHIVE_SHA
    assert request["manifest_sha256"] == writer.MANIFEST_SHA
    assert design["model_seed"] == seed and design["run_model_seed"] == 20260918
    assert design["planned_main_updates"] is None and design["learning_rate_schedule"] == "CONSTANT_AS_HELM_1_0"
    assert design["passes"] == 20 and design["schedule"]["main_updates"] == 2940
    assert design["worker_deadline_seconds"] == 23100
    assert study["required_artifacts"] == 128 and study["automatic_retries"] == 0
    assert study["effective_model_seed"] == seed
    assert writer.launch.contract.RUN_MODEL_SEED == 20260918

@pytest.mark.parametrize("seed", [20260918, 42, True])
def test_unapproved_replication_seed_rejected(seed):
    with pytest.raises(ValueError, match="UNAUTHORIZED_SEED"):
        with writer.seed_context(seed):
            pytest.fail("unapproved seed reached admission")

def test_selected_seed_rejects_a_different_job_seed():
    plan = writer.load_plan(PLAN_HASH)
    row = plan["jobs"][1]
    request = {"schema": writer.launch.REQUEST_SCHEMA, "job": row["job"], "source_sha": writer.SOURCE,
               "archive_sha256": writer.ARCHIVE_SHA, "manifest_sha256": writer.MANIFEST_SHA, "launch_authorized": False}
    with writer.seed_context(20260917), pytest.raises(ValueError, match="POINTER_REQUEST_MODEL_SEED"):
        writer.launch.validate_request(request)

def test_scientific_design_difference_rejected():
    reference = writer.json.loads((writer.REFERENCE / "authority.json").read_bytes())["worker_config"]
    candidate = deepcopy(reference)
    row = writer.load_plan(PLAN_HASH)["jobs"][0]
    candidate["job"] = row["job"]
    candidate["bucket"] = row["job"] + "-" + writer.launch.shared.RESOURCE_PLAN["account"]
    candidate["design"]["model_seed"] = 20260917
    candidate["design"]["optimizer_config"]["learning_rate"] = 0.004
    with pytest.raises(ValueError, match="SCIENTIFIC_DESIGN_CHANGED"):
        writer.assert_only_seed_difference(candidate, reference, 20260917)

def test_authority_cannot_disagree_with_seed_in_job():
    records = writer.build_records(writer.load_plan(PLAN_HASH), PLAN_HASH, 20260917)
    authority = writer.json.loads(records["authority.json"])
    authority["worker_config"]["design"]["model_seed"] = 20260919
    with writer.seed_context(20260917), pytest.raises(ValueError, match="POINTER_AUTHORITY_CONFIG"):
        writer.launch.validate_authority(authority)

def test_seed_context_restores_original_after_failure():
    design = writer.canonical(writer.launch.contract.DESIGN)
    with pytest.raises(RuntimeError, match="sentinel"):
        with writer.seed_context(20260917):
            raise RuntimeError("sentinel")
    assert writer.launch.contract.RUN_MODEL_SEED == 20260918
    assert writer.canonical(writer.launch.contract.DESIGN) == design

def test_reference_request_still_uses_original_default_gate():
    reference = writer.json.loads((writer.REFERENCE / "request.json").read_bytes())
    writer.launch.validate_request(reference)
    assert writer.launch.contract.RUN_MODEL_SEED == 20260918

def test_wrong_plan_hash_rejected_before_any_record():
    with pytest.raises(ValueError, match="PLAN_HASH"):
        writer.load_plan("0" * 64)

def test_both_seed_plans_fixed_before_results_and_separate_receipts():
    plan = writer.load_plan(PLAN_HASH)
    assert plan["frozen_before_new_results"] is True
    assert [x["seed"] for x in plan["jobs"]] == [20260917, 20260919]
    assert len({x["job"] for x in plan["jobs"]}) == 2
    assert len({x["receipt_dir"] for x in plan["jobs"]}) == 2
    assert plan["primary"]["per_seed_delta"] == "pass20 correct minus the same seed pass10 correct"
    assert plan["monitor"]["may_launch_retry_or_alter_job"] is False

@pytest.mark.parametrize("fault", [None, "failed", "missing_artifact", "wrong_seed", "incomplete_passes"])
def test_second_seed_gate_requires_operational_success_not_good_scores(fault):
    row = writer.load_plan(PLAN_HASH)["jobs"][0]
    result = {"job":row["job"], "completed_deliverable":True, "status":"AWS_CANDIDATE_FINISHED",
              "cleanup":{"complete":True,"failures":[]}}
    receiver = {"job":row["job"],"collection":"COMPLETE_VERIFIED","required_count":128,"failures":[],
                "byte_integrity":{"state":"COMPLETE_VERIFIED","verified_count":128,"required_count":128,
                                  "missing":[],"mismatched":[],"unavailable":[]}}
    worker = {"job":row["job"],"status":"TYPED_POINTER_DELIVERED", "summary":{
        "status":"COMPLETE_TYPED_POINTER_ARM","source_sha":writer.SOURCE,"model_seed":row["seed"],
        "main_training_delta":{"optimizer_updates":2940},
        "pass_summaries":[{"pass":i,"updates":147} for i in range(1,21)],
        "runtime":{"torch_version":"2.11.0+cu128","cuda_version":"12.8","gpu_name":"RTX PRO 4500"}}}
    if fault == "failed": result["completed_deliverable"] = False
    if fault == "missing_artifact": receiver["byte_integrity"]["verified_count"] = 127
    if fault == "wrong_seed": worker["summary"]["model_seed"] = 20260918
    if fault == "incomplete_passes": worker["summary"]["pass_summaries"].pop()
    if fault:
        with pytest.raises(ValueError): campaign_operator.successful_terminal(result,receiver,worker,row)
    else:
        assert campaign_operator.successful_terminal(result,receiver,worker,row)
