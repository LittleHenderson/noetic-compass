"""Pure tests for the graph-training AWS launcher: fake git objects and fake
client stacks only. No AWS, network, tensor, or provider work."""
import json
import pytest
from pathlib import Path
from types import SimpleNamespace

from aws import graph_training_launch as launch
from aws import budget

JOB = "cas-meta2-teaching-graph-20260909011302-e654ae56"


def valid_request():
    return {"schema": launch.REQUEST_SCHEMA, "job": JOB, "source_sha": "a" * 40,
            "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
            "launch_authorized": False}


def valid_authority():
    return {"schema": launch.AUTHORITY_SCHEMA, "job": JOB, "source_sha": "a" * 40,
            "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
            "owner_authorization_sha256": "0" * 64,
            "learning_rate": 0.003, "max_optimizer_steps": 64,
            "max_wall_seconds": 600.0, "reservation_usd": "4.00"}


def test_plan_only_is_inert():
    result = launch.plan_only()
    assert result["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert result["reservation_created"] is False
    assert result["provider_calls"] == 0
    assert result["scope"]["frozen_budget"]["total_optimizer_steps"] == 128


def test_frozen_budget_binds_both_arms():
    scope = launch.scope()
    frozen = scope["frozen_budget"]
    assert frozen["arms"] == ["cas", "generic"]
    assert frozen["max_optimizer_steps"] == 64
    assert frozen["max_wall_seconds"] == 600.0
    assert frozen["total_optimizer_steps"] == 128
    assert frozen["total_wall_seconds"] == 1200.0


def test_authority_rejects_budget_mutations():
    authority = valid_authority()
    authority["learning_rate"] = 0.1
    with pytest.raises(ValueError, match="learning_rate"):
        launch.validate_authority(authority)
    authority = valid_authority()
    authority["max_optimizer_steps"] = 48
    with pytest.raises(ValueError, match="max_optimizer_steps"):
        launch.validate_authority(authority)


class FakeClientError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


def fake_clients():
    def raiser(code):
        def _raise(**kwargs):
            raise FakeClientError(code)
        return _raise

    ec2 = SimpleNamespace(describe_instances=raiser("InvalidInstanceID.NotFound"),
                          describe_security_groups=lambda **k: {"SecurityGroups": [], "NextToken": None},
                          delete_security_group=lambda GroupId: None)
    scheduler = SimpleNamespace(get_schedule=raiser("ResourceNotFoundException"))
    iam = SimpleNamespace(get_role=raiser("NoSuchEntity"),
                          get_instance_profile=raiser("NoSuchEntity"),
                          remove_role_from_instance_profile=raiser("NoSuchEntity"),
                          delete_role_policy=raiser("NoSuchEntity"))
    s3 = SimpleNamespace(list_objects_v2=raiser("NoSuchBucket"))
    return {"ec2": ec2, "s3": s3, "iam": iam, "scheduler": scheduler}


def make_provider(ledger_path, clients):
    return launch.GraphTrainingProvider(job=JOB, source_sha="a" * 40,
                                        archive_sha256="b" * 64,
                                        manifest_sha256="c" * 64,
                                        ledger_path=ledger_path, clients=clients,
                                        client_error=FakeClientError)


def test_cleanup_already_absent_tolerance_and_termination_wait(tmp_path):
    clients = fake_clients()
    provider = make_provider(tmp_path / "ledger.json", clients)
    provider._resources["bucket"] = "job-bucket"
    status = provider.cleanup(JOB)
    assert status["complete"] is True
    assert status["instances_termination_pending"] == []
    assert status["security_group_deleted"] is True
    assert status["roles_removed"] is True
    assert status["bucket_deleted"] is True


def test_cleanup_detaches_role_before_deleting(tmp_path):
    calls = []
    clients = fake_clients()
    clients["iam"] = SimpleNamespace(
        get_role=lambda **k: {}, get_instance_profile=lambda **k: {},
        remove_role_from_instance_profile=lambda **k: calls.append("detach"),
        delete_role_policy=lambda **k: calls.append("policy"),
        delete_role=lambda **k: calls.append("role"),
        delete_instance_profile=lambda **k: calls.append("profile"))
    provider = make_provider(tmp_path / "ledger.json", clients)
    provider._resources["bucket"] = "job-bucket"
    status = provider.cleanup(JOB)
    assert calls[:2] == ["detach", "policy"]
    assert "role" in calls and "profile" in calls
    assert status["complete"] is True


def test_worker_script_preserves_inner_errors_and_runs_both_arms():
    text = launch.render_worker()
    assert "for arm in ('cas', 'generic')" in text
    assert "capture_output=True" in text
    assert "INNER_RUNNER_EXIT_" in text
    assert "torch==2.11.0" in text
    assert "evaluate_sealed" in text
    assert "from cas_meta2.teaching_cycle import gpu_adapter" in text
    assert "gpu_adapter._cuda()" in text
    assert "{job}" not in text and "{{" not in text


def test_package_build_zip_readback_and_manifest(tmp_path, monkeypatch):
    real_root = launch.ROOT
    fake_git = FakeGit(real_root)
    root = tmp_path / "root"
    (root / "records").mkdir(parents=True)
    monkeypatch.setattr(launch, "ROOT", root)
    output = root / "records" / "package_001"
    receipt = launch.build_package(output, source_sha="f" * 40,
                                   git_bytes_fn=fake_git.show,
                                   git_paths_fn=fake_git.ls_tree)
    assert receipt["status"] == "SOURCE_ONLY_NO_LAUNCH"
    assert receipt["manifest"]["launch_enabled"] is False
    import zipfile
    with zipfile.ZipFile(output / "source.zip") as archive:
        names = archive.namelist()
        assert launch.MANIFEST_NAME in names and launch.WORKER_NAME in names
        assert any(name.startswith("research/CAS_META_2_COMPOSITION/cas_meta2/graph_teaching/")
                   for name in names)
        manifest = json.loads(archive.read(launch.MANIFEST_NAME))
        assert manifest["frozen_budget"]["total_optimizer_steps"] == 128
    # byte-identical rebuild refuses a non-fresh output directory
    with pytest.raises(ValueError, match="PACKAGE_NEW_SCOPED_OUTPUT_REQUIRED"):
        launch.build_package(output, source_sha="f" * 40,
                             git_bytes_fn=fake_git.show,
                             git_paths_fn=fake_git.ls_tree)


class FakeGit:
    def __init__(self, real_root):
        self.real_root = real_root

    def show(self, root, commit, path):
        if path in launch.WHEELS:
            wheel_dir = (self.real_root.parent / "CAS_CJT_TRANSFORMER_v0_2"
                         / "artifacts/release_reproduction/dist")
            raw = (wheel_dir / Path(path).name).read_bytes()
        else:
            raw = b"file:" + path.encode()
        return raw

    def ls_tree(self, root, commit, directory):
        members = {
            launch.PILOT + "cas_meta2/graph_teaching": [
                "__init__.py", "graph.py", "reference.py", "lessons.py",
                "adapter.py", "real_framework.py", "trainer.py"],
            launch.PILOT + "cas_meta2/teaching_cycle": ["gpu_adapter.py"],
        }[directory]
        return [directory + "/" + name for name in members]


def test_provider_preflight_with_fake_clients():
    clients = fake_clients()
    clients["sts"] = SimpleNamespace(get_caller_identity=lambda: {"Account": "807562639912"})
    clients["ec2"] = SimpleNamespace(
        describe_images=lambda **k: {"Images": [{"State": "available"}]},
        describe_instance_types=lambda **k: {"InstanceTypes": [
            {"InstanceType": "g7.2xlarge",
             "GpuInfo": {"Gpus": [{"Name": "RTX PRO 4500", "Count": 1}]}}]},
        describe_instances=lambda **k: {"NextToken": None, "Reservations": []})
    clients["pricing"] = SimpleNamespace(get_products=lambda **k: {
        "NextToken": None, "PriceList": [json.dumps(
            {"terms": {"OnDemand": {"x": {"priceDimensions": {"d": {
                "pricePerUnit": {"USD": "2.52"}, "unit": "Hrs"}}}}}})]})
    provider = make_provider("ledger.json", clients)
    facts = provider.preflight()
    assert facts["account"] == "807562639912"
    assert facts["gpu_name_contains"] == "RTX PRO 4500"
    assert facts["conflicting_resources"] == []


def test_wait_tolerates_no_such_key_until_result_appears(tmp_path):
    """The paid-run defect: a NoSuchKey poll escaped the wait loop because the
    real botocore ClientError was not the tolerated class. With the correct
    class wired, NoSuchKey keeps polling and only other codes propagate."""
    import io
    clients = fake_clients()
    state = {"calls": 0}

    def get_object(**kwargs):
        state["calls"] += 1
        if state["calls"] < 3:
            raise FakeClientError("NoSuchKey")
        raw = b'{"schema": "cas-graph-training-result/1", "job": "x", "status": "OK", "arms": []}'
        return {"Body": io.BytesIO(raw)}

    clients["s3"] = SimpleNamespace(get_object=get_object)
    clients["ec2"] = SimpleNamespace(describe_instances=lambda **k: {
        "Reservations": [{"Instances": [{"State": {"Name": "running"}}]}]})
    provider = make_provider(tmp_path / "ledger.json", clients)
    provider._instance_id = "i-0123456789abcdef0"
    provider._resources["bucket"] = "job-bucket"
    outcome = provider.wait(JOB, timeout=60, poll_interval=0.01)
    assert outcome["worker_status"] == "REMOTE_FINISHED"
    assert state["calls"] == 3


def test_wait_propagates_non_missing_errors(tmp_path):
    clients = fake_clients()
    clients["s3"] = SimpleNamespace(
        get_object=lambda **k: (_ for _ in ()).throw(FakeClientError("AccessDenied")))
    provider = make_provider(tmp_path / "ledger.json", clients)
    provider._instance_id = "i-0123456789abcdef0"
    provider._resources["bucket"] = "job-bucket"
    with pytest.raises(FakeClientError):
        provider.wait(JOB, timeout=5, poll_interval=0.01)


def test_cleanup_tolerates_schedule_and_timer_role_absence(tmp_path):
    """ResourceNotFoundException on the schedule and NoSuchEntity on the timer
    role are already-absent, not failures (the paid run mislabeled them only
    because the real error class was unwired)."""
    clients = fake_clients()
    provider = make_provider(tmp_path / "ledger.json", clients)
    provider._resources["bucket"] = "job-bucket"
    status = provider.cleanup(JOB)
    assert status["schedule_removed"] is True
    assert status["roles_removed"] is True
    assert status["complete"] is True


def test_main_passes_the_real_client_error_class():
    """The launcher entrypoint must wire botocore's ClientError, not the
    default fake, so real SDK errors hit the tolerance paths."""
    import inspect
    source = inspect.getsource(launch.main)
    assert "from botocore.exceptions import ClientError" in source
    assert "client_error=ClientError" in source


class FakeProvider:
    def __init__(self, ledger_path):
        self.ledger_path = ledger_path
        self.calls = []

    def configure_evidence(self, directory):
        self.evidence = directory

    def preflight(self):
        self.calls.append("preflight")
        return {"account": "807562639912", "region": "us-west-2",
                "ami": launch.RESOURCE_PLAN["ami"],
                "instance_type": "g7.2xlarge", "instance_count": 1,
                "gpu_name_contains": "RTX PRO 4500", "visible_gpu_count": 1,
                "t4_rejected": True, "rate_ceiling_usd": "2.52",
                "conflicting_resources": []}

    def reserve(self, amount):
        self.calls.append("reserve")
        receipt = budget.reserve_budget(JOB, "a" * 40, "b" * 64, amount,
                                        launch.reservation_plan(), self.ledger_path)
        return {**receipt, "aws_side_reservation": {"status": "RECORDED"}}

    def launch(self, job, permit):
        self.calls.append("launch")
        return {"job": job, "instance_id": "i-0123456789abcdef0"}

    def wait(self, job, timeout):
        self.calls.append("wait")
        return {"worker_status": "REMOTE_FINISHED"}

    def collect(self, job):
        self.calls.append("collect")
        return {"result_sha256": "d" * 64}

    def cleanup(self, job):
        self.calls.append("cleanup")
        return {"complete": True, "instance_ids": [], "instances": {},
                "security_group_deleted": True, "schedule_removed": True,
                "roles_removed": True, "bucket_deleted": True,
                "results_deleted": True, "failures": []}


def test_execute_lifecycle_order_and_claims(tmp_path):
    ledger = tmp_path / "ledger.json"
    launch.LEDGER_PATH = ledger
    prior = launch.ROOT.parent / "CAS_META_1_LEARNED_SELECTION" / "records/aws_budget_ledger.json"
    approval = launch.ROOT / "records/budget/OWNER_APPROVAL_SOURCE.json"
    budget.initialize_ledger(prior, approval, ledger)
    provider = FakeProvider(ledger)
    authority = valid_authority()
    authority["owner_authorization_sha256"] = launch.digest(
        b'{"owner": "graph-test"}\n')
    owner = tmp_path / "OWNER_AUTHORIZATION_AWS.json"
    owner.write_bytes(b'{"owner": "graph-test"}\n')
    result = launch.execute(valid_request(), authority, provider, ledger_path=ledger,
                            receipt_dir=tmp_path / "receipt",
                            owner_authorization_path=owner)
    assert result["status"] == "AWS_GRAPH_TRAINING_FINISHED"
    assert provider.calls == ["preflight", "reserve", "launch", "wait", "collect",
                              "cleanup"]
    assert result["claims"] == {"specialist_claimed": False,
                                "composition_claimed": False,
                                "final_targets_read": False}
    launch.LEDGER_PATH = launch.ROOT / "records/budget/campaign_ledger.json"


def test_execute_owner_record_mismatch_refuses(tmp_path):
    ledger = tmp_path / "ledger.json"
    prior = launch.ROOT.parent / "CAS_META_1_LEARNED_SELECTION" / "records/aws_budget_ledger.json"
    approval = launch.ROOT / "records/budget/OWNER_APPROVAL_SOURCE.json"
    budget.initialize_ledger(prior, approval, ledger)
    provider = FakeProvider(ledger)
    owner = tmp_path / "OWNER_AUTHORIZATION_AWS.json"
    owner.write_bytes(b'{"owner": "other"}\n')
    with pytest.raises(ValueError, match="OWNER_AUTHORIZATION_RECORD_MISMATCH"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger,
                       owner_authorization_path=owner)
    assert provider.calls == []
