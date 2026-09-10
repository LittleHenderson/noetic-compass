"""Pure tests for the GRAPH6_CURRICULUM_002 launcher, including in-job
checkpoint collection: fake git objects and fake client stacks only. No AWS,
network, tensor, or GPU work."""
import io
import json
import pytest
from pathlib import Path
from types import SimpleNamespace

from aws import budget
from aws import graph_training_curriculum_launch as launch

JOB = "cas-meta2-graph6curr-20260910033000-a387d882"


def valid_request():
    return {"schema": launch.REQUEST_SCHEMA, "job": JOB, "source_sha": "a" * 40,
            "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
            "launch_authorized": False}


def valid_authority():
    return {"schema": launch.AUTHORITY_SCHEMA, "job": JOB, "source_sha": "a" * 40,
            "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
            "owner_authorization_sha256": "0" * 64,
            "pair_seeds": list(launch.FROZEN_PAIR_SEEDS),
            "conditions": list(launch.FROZEN_CONDITIONS),
            "checkpoints": list(launch.FROZEN_CHECKPOINTS),
            "updates_per_learner": launch.FROZEN_UPDATES_PER_LEARNER,
            "total_optimizer_steps": launch.FROZEN_TOTAL_UPDATES,
            "panel_seed": launch.FROZEN_PANEL_SEED,
            "learning_rate": 0.003,
            "max_wall_seconds_per_learner": launch.FROZEN_MAX_WALL_SECONDS_PER_LEARNER,
            "reservation_usd": "7.00"}


def test_plan_only_is_inert_and_declares_the_whole_design():
    result = launch.plan_only()
    assert result["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert result["reservation_created"] is False
    assert result["provider_calls"] == 0
    frozen = result["scope"]["frozen_budget"]
    assert frozen["pair_seeds"] == [20260913, 20260914, 20260915]
    assert frozen["conditions"] == ["control", "varied"]
    assert frozen["checkpoints"] == [64, 256]
    assert frozen["updates_per_learner"] == 256
    assert frozen["learners"] == 6
    assert frozen["total_optimizer_steps"] == 1536
    assert frozen["panel_seed"] == 20260930
    assert frozen["encoder_seed"] == 20260909
    assert frozen["reservation_usd"] == "7.00"
    assert result["scope"]["instance_seconds_max"] == 7200
    assert result["scope"]["worker_seconds_max"] == 3600


def test_reservation_plan_covers_the_declared_total_cost_bound():
    budget.validate_plan(launch.reservation_plan(), "7.00")


def test_authority_freezes_the_design():
    for key, value, code in (("pair_seeds", [1, 2, 3], "PAIR_SEEDS_FROZEN"),
                             ("conditions", ["varied"], "CONDITIONS_FROZEN"),
                             ("checkpoints", [64], "CHECKPOINTS_FROZEN"),
                             ("updates_per_learner", 128, "UPDATES_FROZEN"),
                             ("total_optimizer_steps", 768, "TOTAL_STEPS_FROZEN"),
                             ("panel_seed", 1, "PANEL_SEED_FROZEN"),
                             ("learning_rate", 0.1, "learning_rate"),
                             ("max_wall_seconds_per_learner", 1.0, "max_wall_seconds"),
                             ("reservation_usd", "6.00", "RESERVATION")):
        authority = valid_authority()
        authority[key] = value
        with pytest.raises(ValueError, match=code):
            launch.validate_authority(authority)


def test_worker_runs_the_whole_comparison_in_one_job():
    text = launch.render_worker()
    assert "trainer.training_records(20260909)" in text
    assert "build_encoder(torch, publics, d_model=64, seed=20260909," in text
    assert "final_panel.build_final_panel()" in text
    assert "curriculum_experiment.launch(" in text
    assert "checkpoint_dir" in text
    assert "results/artifacts/" in text
    assert "INNER_RUNNER_EXIT_" in text
    assert "torch==2.11.0" in text
    assert "gpu_adapter._cuda()" in text
    assert "for arm in ('cas', 'generic')" not in text
    assert "{job}" not in text and "{{" not in text
    compile(text, "worker.py", "exec")
    namespace = {}
    exec(compile(text, "worker.py", "exec"), namespace)
    compile(namespace["INNER_RUNNER"], "inner_runner.py", "exec")


def test_worker_never_lets_the_final_panel_touch_the_tokenizer():
    text = launch.render_worker()
    assert text.index("build_encoder(") < text.index("final_panel.build_final_panel()")
    assert "publics = [adapter.public_records(r, 'cas')['public'] for r in records]" in text
    assert "build_encoder(torch, panel" not in text


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
                          describe_security_groups=lambda **k: {"SecurityGroups": [],
                                                                "NextToken": None},
                          delete_security_group=lambda GroupId: None)
    scheduler = SimpleNamespace(get_schedule=raiser("ResourceNotFoundException"))
    iam = SimpleNamespace(get_role=raiser("NoSuchEntity"),
                          get_instance_profile=raiser("NoSuchEntity"),
                          remove_role_from_instance_profile=raiser("NoSuchEntity"),
                          delete_role_policy=raiser("NoSuchEntity"))
    s3 = SimpleNamespace(list_objects_v2=raiser("NoSuchBucket"))
    return {"ec2": ec2, "s3": s3, "iam": iam, "scheduler": scheduler}


def make_provider(ledger_path, clients):
    return launch.CurriculumProvider(
        job=JOB, source_sha="a" * 40, archive_sha256="b" * 64,
        manifest_sha256="c" * 64, ledger_path=ledger_path, clients=clients,
        client_error=FakeClientError)


def test_cleanup_tolerates_already_absent_resources(tmp_path):
    provider = make_provider(tmp_path / "ledger.json", fake_clients())
    provider._resources["bucket"] = "job-bucket"
    status = provider.cleanup(JOB)
    assert status["complete"] is True
    assert status["instances_termination_pending"] == []
    assert status["security_group_deleted"] is True
    assert status["roles_removed"] is True
    assert status["bucket_deleted"] is True


def test_wait_accepts_only_the_curriculum_result_identity(tmp_path):
    clients = fake_clients()

    def get_object(**kwargs):
        raw = json.dumps({"schema": launch.RESULT_SCHEMA, "job": JOB}).encode()
        return {"Body": io.BytesIO(raw)}

    clients["s3"] = SimpleNamespace(get_object=get_object)
    provider = make_provider(tmp_path / "ledger.json", clients)
    provider._instance_id = "i-0123456789abcdef0"
    provider._resources["bucket"] = "job-bucket"
    outcome = provider.wait(JOB, timeout=60, poll_interval=0.01)
    assert outcome["worker_status"] == "REMOTE_FINISHED"


def test_wait_rejects_a_foreign_result_schema(tmp_path):
    clients = fake_clients()

    def get_object(**kwargs):
        return {"Body": io.BytesIO(json.dumps(
            {"schema": "cas-graph-training-graph6-confirmation-result/1"}).encode())}

    clients["s3"] = SimpleNamespace(get_object=get_object)
    provider = make_provider(tmp_path / "ledger.json", clients)
    provider._instance_id = "i-0123456789abcdef0"
    provider._resources["bucket"] = "job-bucket"
    with pytest.raises(ValueError, match="CURRICULUM_RESULT_IDENTITY"):
        provider.wait(JOB, timeout=5, poll_interval=0.01)


class FakeS3:
    """Minimal in-memory S3 for collect()."""

    def __init__(self, objects):
        self.objects = objects
        self.requested = []

    def get_object(self, Bucket, Key):
        self.requested.append(Key)
        if Key not in self.objects:
            raise FakeClientError("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[Key])}


def _collect_fixture(tmp_path, artifact_body=b"checkpoint-bytes"):
    import hashlib
    result = json.dumps({"schema": launch.RESULT_SCHEMA, "job": JOB,
                         "artifacts": []}).encode()
    sidecar = hashlib.sha256(result).hexdigest().encode()
    manifest = json.dumps({"artifacts": [
        {"name": "varied_seed20260913_step064.pt", "bytes": len(artifact_body),
         "sha256": hashlib.sha256(artifact_body).hexdigest(), "step": 64,
         "condition": "varied", "learner_seed": 20260913}]}).encode()
    clients = fake_clients()
    clients["s3"] = FakeS3({
        "results/result.json.sha256": sidecar,
        launch.ARTIFACT_MANIFEST_KEY: manifest,
        launch.ARTIFACT_PREFIX + "varied_seed20260913_step064.pt": artifact_body})
    provider = make_provider(tmp_path / "ledger.json", clients)
    provider._instance_id = "i-0123456789abcdef0"
    provider._resources["bucket"] = "job-bucket"
    provider._result_raw = result
    (tmp_path / "receipt").mkdir()
    provider.configure_evidence(tmp_path / "receipt")
    return provider, clients


def test_collect_downloads_and_verifies_checkpoint_artifacts(tmp_path):
    provider, clients = _collect_fixture(tmp_path)
    collected = provider.collect(JOB)
    assert collected["artifact_count"] == 1
    assert collected["artifact_bytes"] == len(b"checkpoint-bytes")
    saved = Path(collected["artifacts"][0]["path"])
    assert saved.is_file() and saved.read_bytes() == b"checkpoint-bytes"
    assert (tmp_path / "receipt" / "artifact_manifest.json").is_file()
    assert (tmp_path / "receipt" / "curriculum_result.json").is_file()


def test_collect_rejects_a_corrupted_artifact(tmp_path):
    provider, _ = _collect_fixture(tmp_path, artifact_body=b"checkpoint-bytes")
    provider.clients["s3"].objects[
        launch.ARTIFACT_PREFIX + "varied_seed20260913_step064.pt"] = b"tampered"
    with pytest.raises(ValueError, match="CURRICULUM_ARTIFACT_BYTES|CURRICULUM_ARTIFACT_SHA"):
        provider.collect(JOB)


def test_collect_requires_a_non_empty_artifact_manifest(tmp_path):
    provider, clients = _collect_fixture(tmp_path)
    clients["s3"].objects[launch.ARTIFACT_MANIFEST_KEY] = json.dumps(
        {"artifacts": []}).encode()
    with pytest.raises(ValueError, match="CURRICULUM_ARTIFACT_MANIFEST_REQUIRED"):
        provider.collect(JOB)


def test_user_data_enables_the_teaching_cycle_gate():
    provider = make_provider("ledger.json", fake_clients())
    text = provider._user_data("job-bucket")
    assert "export CAS_META2_RUN_TEACHING_CYCLE=1" in text
    assert launch.WORKER_NAME in text


def test_main_passes_the_real_client_error_class():
    import inspect
    source = inspect.getsource(launch.main)
    assert "from botocore.exceptions import ClientError" in source
    assert "client_error=ClientError" in source


class FakeGit:
    def __init__(self, real_root):
        self.real_root = real_root

    def show(self, root, commit, path):
        if path in launch.WHEELS:
            wheel_dir = (self.real_root.parent / "CAS_CJT_TRANSFORMER_v0_2"
                         / "artifacts/release_reproduction/dist")
            return (wheel_dir / Path(path).name).read_bytes()
        return b"file:" + path.encode()

    def ls_tree(self, root, commit, directory):
        members = {
            launch.PILOT + "cas_meta2/graph_teaching": [
                "__init__.py", "graph.py", "reference.py", "lessons.py",
                "adapter.py", "real_framework.py", "trainer.py", "diagnostic.py",
                "competence.py", "fresh_panel.py", "confirmation.py",
                "curriculum.py", "final_panel.py", "curriculum_experiment.py"],
            launch.PILOT + "cas_meta2/teaching_cycle": ["gpu_adapter.py"],
        }[directory]
        return [directory + "/" + name for name in members]


def test_package_build_is_source_only_and_declares_the_design(tmp_path, monkeypatch):
    fake_git = FakeGit(launch.ROOT)
    root = tmp_path / "root"
    (root / "records").mkdir(parents=True)
    monkeypatch.setattr(launch, "ROOT", root)
    output = root / "records" / "graph6_curriculum_package_001"
    receipt = launch.build_package(output, source_sha="f" * 40,
                                   git_bytes_fn=fake_git.show,
                                   git_paths_fn=fake_git.ls_tree)
    assert receipt["status"] == "SOURCE_ONLY_NO_LAUNCH"
    manifest = receipt["manifest"]
    assert manifest["launch_enabled"] is False
    assert manifest["pair_seeds"] == [20260913, 20260914, 20260915]
    assert manifest["conditions"] == ["control", "varied"]
    assert manifest["checkpoints"] == [64, 256]
    assert manifest["total_optimizer_steps"] == 1536
    assert manifest["panel_seed"] == 20260930
    import zipfile
    with zipfile.ZipFile(output / "source.zip") as archive:
        names = archive.namelist()
        assert launch.MANIFEST_NAME in names and launch.WORKER_NAME in names
        assert any(name.endswith("graph_teaching/curriculum.py") for name in names)
        assert any(name.endswith("graph_teaching/final_panel.py") for name in names)
        assert any(name.endswith("graph_teaching/curriculum_experiment.py")
                   for name in names)
    with pytest.raises(ValueError, match="PACKAGE_NEW_SCOPED_OUTPUT_REQUIRED"):
        launch.build_package(output, source_sha="f" * 40,
                             git_bytes_fn=fake_git.show,
                             git_paths_fn=fake_git.ls_tree)


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
        return {"result_sha256": "d" * 64, "artifact_count": 18}

    def cleanup(self, job):
        self.calls.append("cleanup")
        return {"complete": True, "instance_ids": [], "instances": {},
                "security_group_deleted": True, "schedule_removed": True,
                "roles_removed": True, "bucket_deleted": True,
                "results_deleted": True, "failures": []}


def _ledger(tmp_path):
    ledger = tmp_path / "ledger.json"
    prior = (launch.ROOT.parent / "CAS_META_1_LEARNED_SELECTION"
             / "records/aws_budget_ledger.json")
    approval = launch.ROOT / "records/budget/OWNER_APPROVAL_SOURCE.json"
    budget.initialize_ledger(prior, approval, ledger)
    return ledger


def test_execute_lifecycle_order_and_claims(tmp_path, monkeypatch):
    ledger = _ledger(tmp_path)
    monkeypatch.setattr(launch, "LEDGER_PATH", ledger)
    provider = FakeProvider(ledger)
    authority = valid_authority()
    authority["owner_authorization_sha256"] = launch.digest(b'{"owner": "curriculum"}\n')
    owner = tmp_path / "OWNER_AUTHORIZATION_GRAPH6_CURRICULUM_002.json"
    owner.write_bytes(b'{"owner": "curriculum"}\n')
    result = launch.execute(valid_request(), authority, provider, ledger_path=ledger,
                            receipt_dir=tmp_path / "receipt",
                            owner_authorization_path=owner)
    assert result["status"] == "AWS_CURRICULUM_FINISHED"
    assert provider.calls == ["preflight", "reserve", "launch", "wait", "collect",
                              "cleanup"]
    assert result["claims"] == {"specialist_claimed": False,
                                "composition_claimed": False,
                                "final_targets_read": False}


def test_execute_owner_record_mismatch_refuses(tmp_path, monkeypatch):
    ledger = _ledger(tmp_path)
    monkeypatch.setattr(launch, "LEDGER_PATH", ledger)
    provider = FakeProvider(ledger)
    owner = tmp_path / "OWNER_AUTHORIZATION_GRAPH6_CURRICULUM_002.json"
    owner.write_bytes(b'{"owner": "other"}\n')
    with pytest.raises(ValueError, match="OWNER_AUTHORIZATION_RECORD_MISMATCH"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger,
                       owner_authorization_path=owner)
    assert provider.calls == []


def test_execute_refuses_a_second_reservation_for_the_same_job(tmp_path, monkeypatch):
    ledger = _ledger(tmp_path)
    monkeypatch.setattr(launch, "LEDGER_PATH", ledger)
    authority = valid_authority()
    authority["owner_authorization_sha256"] = launch.digest(b'{"owner": "curriculum"}\n')
    owner = tmp_path / "OWNER_AUTHORIZATION_GRAPH6_CURRICULUM_002.json"
    owner.write_bytes(b'{"owner": "curriculum"}\n')
    launch.execute(valid_request(), authority, FakeProvider(ledger), ledger_path=ledger,
                   receipt_dir=tmp_path / "receipt", owner_authorization_path=owner)
    second = FakeProvider(ledger)
    with pytest.raises(ValueError, match="JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY"):
        launch.execute(valid_request(), authority, second, ledger_path=ledger,
                       receipt_dir=tmp_path / "receipt2", owner_authorization_path=owner)
    assert second.calls == []
