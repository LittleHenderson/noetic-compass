"""Pure tests for the confirmation experiment: the frozen candidate repeated
for predeclared seeds on newly generated panels. Fake git objects, fake client
stacks, and pure-Python datasets only — no AWS, network, tensor, or GPU work."""
import io
import json
import pytest
from pathlib import Path
from types import SimpleNamespace

from aws import budget
from aws import graph_training_confirmation_launch as launch
from cas_meta2.graph_teaching import competence, lessons, trainer
from tools import graph_training_confirmation_panel_check as panel_check

JOB = "cas-meta2-confirmation-20260909230000-abcdef01"


def valid_request():
    return {"schema": launch.REQUEST_SCHEMA, "job": JOB, "source_sha": "a" * 40,
            "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
            "launch_authorized": False}


def valid_authority():
    return {"schema": launch.AUTHORITY_SCHEMA, "job": JOB, "source_sha": "a" * 40,
            "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
            "owner_authorization_sha256": "0" * 64,
            "learning_rate": 0.003, "max_optimizer_steps": 64,
            "max_wall_seconds": 600.0, "seeds": list(launch.FROZEN_SEEDS),
            "reservation_usd": "4.00"}


def test_plan_only_is_inert_and_names_the_predeclared_seeds():
    result = launch.plan_only()
    assert result["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert result["reservation_created"] is False
    assert result["provider_calls"] == 0
    frozen = result["scope"]["frozen_budget"]
    assert frozen["arms"] == ["cas"]
    assert frozen["seeds"] == [20260910, 20260911, 20260912]
    assert frozen["max_optimizer_steps"] == 64
    assert frozen["reservation_usd"] == "4.00"


def test_reservation_plan_covers_declared_cost_bound():
    budget.validate_plan(launch.reservation_plan(), "4.00")


def test_authority_freezes_budget_and_seeds():
    for key, value in (("learning_rate", 0.1), ("max_optimizer_steps", 128),
                       ("max_wall_seconds", 1200.0)):
        authority = valid_authority()
        authority[key] = value
        with pytest.raises(ValueError, match=key):
            launch.validate_authority(authority)
    authority = valid_authority()
    authority["seeds"] = [20260910, 20260911, 20260913]
    with pytest.raises(ValueError, match="SEEDS_FROZEN"):
        launch.validate_authority(authority)
    authority = valid_authority()
    authority["reservation_usd"] = "8.00"
    with pytest.raises(ValueError, match="RESERVATION"):
        launch.validate_authority(authority)


def test_worker_repeats_the_frozen_sequence_per_predeclared_seed():
    text = launch.render_worker()
    assert "for seed in seeds:" in text
    assert "torch.manual_seed(seed)" in text
    assert "trainer.training_records(seed)" in text
    assert "adapter.public_records(r, 'cas')" in text
    assert "competence.launch(" in text
    assert "competence.confirmation_outcome(runs)" in text
    assert "max_optimizer_steps=64" in text and "max_wall_seconds=600.0" in text
    assert "learning_rate=0.003" in text
    assert "INNER_RUNNER_EXIT_" in text
    assert "torch==2.11.0" in text
    assert "gpu_adapter._cuda()" in text
    assert "for arm in ('cas', 'generic')" not in text
    assert "{job}" not in text and "{{" not in text
    # the rendered worker and its inner runner are valid Python
    compile(text, "worker.py", "exec")
    namespace = {}
    exec(compile(text, "worker.py", "exec"), namespace)
    compile(namespace["INNER_RUNNER"], "inner_runner.py", "exec")


def test_worker_does_not_change_the_learning_scope_or_the_module():
    text = launch.render_worker()
    for forbidden in ("requires_grad_", "scope_parameters", "plasticity",
                      "d_model=128", "learning_rate=0.01"):
        assert forbidden not in text


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
    return launch.ConfirmationProvider(job=JOB, source_sha="a" * 40,
                                       archive_sha256="b" * 64,
                                       manifest_sha256="c" * 64,
                                       ledger_path=ledger_path, clients=clients,
                                       client_error=FakeClientError)


def test_cleanup_already_absent_tolerance(tmp_path):
    provider = make_provider(tmp_path / "ledger.json", fake_clients())
    provider._resources["bucket"] = "job-bucket"
    status = provider.cleanup(JOB)
    assert status["complete"] is True
    assert status["instances_termination_pending"] == []
    assert status["security_group_deleted"] is True
    assert status["roles_removed"] is True
    assert status["bucket_deleted"] is True


def test_wait_requires_the_confirmation_result_identity(tmp_path):
    clients = fake_clients()
    state = {"calls": 0}

    def get_object(**kwargs):
        state["calls"] += 1
        raw = json.dumps({"schema": launch.RESULT_SCHEMA, "job": JOB,
                          "runs": []}).encode()
        return {"Body": io.BytesIO(raw)}

    clients["s3"] = SimpleNamespace(get_object=get_object)
    provider = make_provider(tmp_path / "ledger.json", clients)
    provider._instance_id = "i-0123456789abcdef0"
    provider._resources["bucket"] = "job-bucket"
    outcome = provider.wait(JOB, timeout=60, poll_interval=0.01)
    assert outcome["worker_status"] == "REMOTE_FINISHED"
    assert provider._result["schema"] == launch.RESULT_SCHEMA


def test_wait_rejects_a_foreign_result_schema(tmp_path):
    clients = fake_clients()

    def get_object(**kwargs):
        raw = json.dumps({"schema": "cas-graph-training-competence-result/1"}).encode()
        return {"Body": io.BytesIO(raw)}

    clients["s3"] = SimpleNamespace(get_object=get_object)
    provider = make_provider(tmp_path / "ledger.json", clients)
    provider._instance_id = "i-0123456789abcdef0"
    provider._resources["bucket"] = "job-bucket"
    with pytest.raises(ValueError, match="CONFIRMATION_RESULT_IDENTITY"):
        provider.wait(JOB, timeout=5, poll_interval=0.01)


def test_user_data_explicitly_enables_the_teaching_cycle_gate():
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
                "competence.py"],
            launch.PILOT + "cas_meta2/teaching_cycle": ["gpu_adapter.py"],
        }[directory]
        return [directory + "/" + name for name in members]


def test_package_build_is_source_only_and_names_the_seeds(tmp_path, monkeypatch):
    fake_git = FakeGit(launch.ROOT)
    root = tmp_path / "root"
    (root / "records").mkdir(parents=True)
    monkeypatch.setattr(launch, "ROOT", root)
    output = root / "records" / "confirmation_package_001"
    receipt = launch.build_package(output, source_sha="f" * 40,
                                   git_bytes_fn=fake_git.show,
                                   git_paths_fn=fake_git.ls_tree)
    assert receipt["status"] == "SOURCE_ONLY_NO_LAUNCH"
    assert receipt["manifest"]["launch_enabled"] is False
    assert receipt["manifest"]["arms"] == ["cas"]
    assert receipt["manifest"]["seeds"] == [20260910, 20260911, 20260912]
    import zipfile
    with zipfile.ZipFile(output / "source.zip") as archive:
        names = archive.namelist()
        assert launch.MANIFEST_NAME in names and launch.WORKER_NAME in names
        manifest = json.loads(archive.read(launch.MANIFEST_NAME))
        assert manifest["frozen_budget"]["seeds"] == [20260910, 20260911, 20260912]
    with pytest.raises(ValueError, match="PACKAGE_NEW_SCOPED_OUTPUT_REQUIRED"):
        launch.build_package(output, source_sha="f" * 40,
                             git_bytes_fn=fake_git.show,
                             git_paths_fn=fake_git.ls_tree)


def _run(seed, correct, attempted, margin=0.5, familiar=(24, 30)):
    return {"schema": competence.SCHEMA, "run_id": "job.%d" % seed, "seed": seed,
            "fit_criterion": {"met": margin > competence.FIT_MARGIN,
                              "margin": margin},
            "stage3": {"ran": True, "sealed_total_correct": correct,
                       "sealed_total_attempted": attempted,
                       "familiar": {"correct": familiar[0],
                                    "attempted": familiar[1]}},
            "outcome": ("LEARNED_AND_TRANSFERRED"
                        if correct >= competence.TRANSFER_THRESHOLD
                        else "LEARNED_NO_TRANSFER")}


def test_panel_normalized_threshold_never_softens_the_registered_bar():
    assert competence.panel_normalized_threshold(12) == 6
    assert competence.panel_normalized_threshold(11) == 6
    assert competence.panel_normalized_threshold(13) == 7
    with pytest.raises(ValueError, match="PANEL_SIZE_REQUIRED"):
        competence.panel_normalized_threshold(0)


def test_confirmation_outcome_replicates_on_the_registered_absolute_rule():
    runs = [_run(20260910, 7, 11), _run(20260911, 6, 11), _run(20260912, 4, 13)]
    report = competence.confirmation_outcome(runs)
    assert report["outcome"] == "REPLICATED"
    assert report["fit_seeds"] == 3 and report["transfer_seeds"] == 2
    assert report["transfer_seeds_panel_normalized"] == 2
    assert report["outcome_panel_normalized"] == "REPLICATED"
    assert report["transfer_threshold"] == 6
    assert [row["registered_met"] for row in report["per_seed"]] == [True, True, False]
    assert report["per_seed"][2]["panel_normalized_threshold"] == 7
    assert report["per_seed"][2]["panel_normalized_met"] is False


def test_confirmation_outcome_reports_a_disconfirming_run():
    runs = [_run(20260910, 3, 11, margin=0.001), _run(20260911, 4, 11, margin=0.001),
            _run(20260912, 5, 13, margin=0.5)]
    report = competence.confirmation_outcome(runs)
    assert report["outcome"] == "NOT_REPLICATED"
    assert report["outcome_panel_normalized"] == "NOT_REPLICATED"
    assert report["fit_seeds"] == 1 and report["transfer_seeds"] == 0


def test_confirmation_outcome_records_a_stage1_stop_without_inventing_a_panel():
    runs = [{"seed": 20260910, "outcome": "STAGE1_CHECK_FAILED",
             "fit_criterion": None, "stage3": None}]
    report = competence.confirmation_outcome(runs)
    assert report["outcome"] == "NOT_REPLICATED"
    row = report["per_seed"][0]
    assert row["sealed_ran"] is False and row["registered_met"] is False
    assert row["sealed_total_attempted"] is None
    assert row["panel_normalized_threshold"] is None


def test_new_sealed_panels_exclude_the_previously_examined_panel():
    report = panel_check.build_report()
    assert report["neural_work"] is False and report["gpu_used"] is False
    assert report["examined_panel_count"] == 12
    assert report["all_sealed_panels_disjoint_from_examined_panel"] is True
    assert report["no_familiar_overlap_with_examined_panel"] is True
    for row in report["per_seed"]:
        assert row["sealed_overlap_with_examined_panel"] == []
        assert row["familiar_overlap_with_examined_panel"] == []
        assert row["sealed_count"] >= competence.TRANSFER_THRESHOLD
        assert row["familiar_count"] >= 1


def test_predeclared_seeds_are_not_the_examined_dataset_seed():
    assert panel_check.PREVIOUS_DATASET_SEED not in competence.CONFIRM_SEEDS
    for seed in competence.CONFIRM_SEEDS:
        assert trainer.training_records(seed)


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
    authority["owner_authorization_sha256"] = launch.digest(b'{"owner": "confirmation"}\n')
    owner = tmp_path / "OWNER_AUTHORIZATION_CONFIRMATION_001.json"
    owner.write_bytes(b'{"owner": "confirmation"}\n')
    result = launch.execute(valid_request(), authority, provider, ledger_path=ledger,
                            receipt_dir=tmp_path / "receipt",
                            owner_authorization_path=owner)
    assert result["status"] == "AWS_CONFIRMATION_FINISHED"
    assert provider.calls == ["preflight", "reserve", "launch", "wait", "collect",
                              "cleanup"]
    assert result["claims"] == {"specialist_claimed": False,
                                "composition_claimed": False,
                                "final_targets_read": False}


def test_execute_owner_record_mismatch_refuses(tmp_path, monkeypatch):
    ledger = _ledger(tmp_path)
    monkeypatch.setattr(launch, "LEDGER_PATH", ledger)
    provider = FakeProvider(ledger)
    owner = tmp_path / "OWNER_AUTHORIZATION_CONFIRMATION_001.json"
    owner.write_bytes(b'{"owner": "other"}\n')
    with pytest.raises(ValueError, match="OWNER_AUTHORIZATION_RECORD_MISMATCH"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger,
                       owner_authorization_path=owner)
    assert provider.calls == []


def test_execute_refuses_a_second_reservation_for_the_same_job(tmp_path, monkeypatch):
    ledger = _ledger(tmp_path)
    monkeypatch.setattr(launch, "LEDGER_PATH", ledger)
    provider = FakeProvider(ledger)
    authority = valid_authority()
    authority["owner_authorization_sha256"] = launch.digest(b'{"owner": "confirmation"}\n')
    owner = tmp_path / "OWNER_AUTHORIZATION_CONFIRMATION_001.json"
    owner.write_bytes(b'{"owner": "confirmation"}\n')
    launch.execute(valid_request(), authority, provider, ledger_path=ledger,
                   receipt_dir=tmp_path / "receipt",
                   owner_authorization_path=owner)
    second = FakeProvider(ledger)
    with pytest.raises(ValueError, match="JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY"):
        launch.execute(valid_request(), authority, second, ledger_path=ledger,
                       receipt_dir=tmp_path / "receipt2",
                       owner_authorization_path=owner)
    assert second.calls == []
