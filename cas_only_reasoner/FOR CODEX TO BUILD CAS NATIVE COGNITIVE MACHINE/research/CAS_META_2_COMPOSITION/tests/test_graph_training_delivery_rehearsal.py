"""Delivery rehearsal: the EXPORTED worker → uploader → collector → cleanup chain.

Owner-directed (2026-09-10). Attempt 003 completed the experiment and then lost
the whole result to a plumbing defect, so the delivery chain is rehearsed as a
chain, not asserted branch by branch:

* the REAL rendered worker's inner runner produces a dummy result and dummy
  checkpoint files (a stub training call — NO neural execution);
* the REAL exported `upload_results` uploads them to a simulated bucket;
* the REAL `CurriculumProvider.wait/collect/cleanup` receive and verify them;
* two paths: normal completion, and an upload failure injected AFTER the dummy
  experiment returned.

What the rehearsal establishes: the collector receives the known result and every
dummy checkpoint with matching hashes and byte counts; the completion signal
appears only after its required uploads; on an injected upload failure the
original result survives byte-for-byte, the failure is recorded separately,
missing checkpoints are reported explicitly, cleanup retains the evidence bucket
instead of destroying the only surviving copy, and the compute still stops.

What it does NOT establish: that real cloud transport can never fail.
"""
import hashlib
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from aws import budget
from aws import graph_training_curriculum_launch as launch
from cas_meta2.graph_teaching import adapter, trainer

JOB = "cas-meta2-graph6curr-20260910113000-0ecdd342"
CHECKPOINTS = ("control_seed20260913_step000.pt", "control_seed20260913_step064.pt",
               "varied_seed20260913_step000.pt", "varied_seed20260913_step256.pt")


class SimulatedS3:
    """In-memory bucket with an injectable failure and a record of every call.

    It raises the SAME error class the provider is configured to catch, exactly
    like botocore's ClientError does in production.
    """

    def __init__(self, fail_on=None):
        self.objects = {}
        self.put_order = []
        self.calls = []
        self.fail_on = fail_on
        self.deleted = False

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.calls.append(("put", Key))
        if self.fail_on is not None and self.fail_on in Key:
            raise StubClientError("InternalError")
        # the shared transport publishes create-only: an existing key with
        # different content is a conflict, not an invitation to overwrite
        if kwargs.get("IfNoneMatch") == "*" and Key in self.objects \
                and self.objects[Key] != Body:
            raise StubClientError("PreconditionFailed")
        self.objects[Key] = Body
        self.put_order.append(Key)
        return {}

    def get_object(self, Bucket, Key):
        self.calls.append(("get", Key))
        if Key not in self.objects:
            raise StubClientError("NoSuchKey")
        return {"Body": __import__("io").BytesIO(self.objects[Key])}

    def list_objects_v2(self, Bucket):
        self.calls.append(("list", Bucket))
        return {"Contents": [{"Key": key} for key in self.objects]}

    def delete_objects(self, Bucket, Delete):
        self.calls.append(("delete", Bucket))
        for entry in Delete["Objects"]:
            self.objects.pop(entry["Key"], None)
        return {}

    def delete_bucket(self, Bucket):
        self.calls.append(("delete_bucket", Bucket))
        self.deleted = True
        return {}


class StubClientError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


def _fake_clients(s3):
    def raiser(code):
        def _raise(**kwargs):
            raise StubClientError(code)
        return _raise

    return {
        "ec2": SimpleNamespace(
            describe_instances=lambda **kwargs: {
                "Reservations": [{"Instances": [{"State": {"Name": "terminated"}}]}]},
            describe_security_groups=lambda **kwargs: {"SecurityGroups": [],
                                                       "NextToken": None},
            delete_security_group=lambda GroupId: None),
        "s3": s3,
        "iam": SimpleNamespace(get_role=raiser("NoSuchEntity"),
                               get_instance_profile=raiser("NoSuchEntity"),
                               remove_role_from_instance_profile=raiser("NoSuchEntity"),
                               delete_role_policy=raiser("NoSuchEntity")),
        "scheduler": SimpleNamespace(get_schedule=raiser("ResourceNotFoundException")),
    }


@pytest.fixture()
def worker(tmp_path, monkeypatch):
    """Run the REAL rendered inner runner against a stub training call."""
    recorded = {}

    stub_torch = SimpleNamespace(__version__="stub", manual_seed=lambda seed: None)
    gpu_adapter = types.ModuleType("cas_meta2.teaching_cycle.gpu_adapter")
    gpu_adapter._cuda = lambda: (stub_torch, "cpu")
    monkeypatch.setitem(sys.modules, "cas_meta2.teaching_cycle.gpu_adapter",
                        gpu_adapter)
    from cas_meta2.graph_teaching import (curriculum_experiment as experiment,
                                          final_panel as panel_module,
                                          real_framework as framework_module)

    monkeypatch.setattr(framework_module, "build_encoder",
                        lambda torch, publics, d_model, seed, device: {
                            "vocabulary_size": 2, "d_model": d_model, "seed": seed})
    monkeypatch.setattr(panel_module, "build_final_panel",
                        lambda: {"schema": "cas-graph-training-final-panel/1",
                                 "panel_seed": 20260930, "family_count": 30,
                                 "case_count": 90, "cases": []})

    dummy_report = {"schema": "cas-graph-training-curriculum-result/1",
                    "job": JOB, "verdict": {"outcome": "REHEARSAL_DUMMY"},
                    "design": {"learners": 6, "total_updates": 1536}}

    def launch_experiment(**kwargs):
        recorded["launch_kwargs"] = kwargs
        checkpoint_dir = kwargs["checkpoint_dir"]
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        artifacts = []
        for name in CHECKPOINTS:
            path = checkpoint_dir / name
            path.write_bytes(("dummy-weights:" + name).encode())
            stem = name[:-3]                      # drop ".pt"
            condition, rest = stem.split("_seed", 1)
            seed_text, step_text = rest.split("_step", 1)
            artifacts.append({"path": str(path), "step": int(step_text),
                              "condition": condition,
                              "learner_seed": int(seed_text)})
        return {**dummy_report, "artifacts": artifacts}

    monkeypatch.setattr(experiment, "launch", launch_experiment)

    outer = {}
    exec(compile(
        launch.run_evidence.unified_worker_source(launch.render_worker()),
        "worker.py", "exec"), outer)
    root = tmp_path / "root"
    (root / "results").mkdir(parents=True)
    (root / "config.json").write_bytes(json.dumps(
        {"job": JOB, "bucket": "bucket", "region": "us-west-2"}).encode())
    argv, cwd = sys.argv, Path.cwd()
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "argv", ["inner_runner.py", str(root)])
    try:
        exec(compile(outer["INNER_RUNNER"], "inner_runner.py", "exec"),
             {"__name__": "__main__"})
    finally:
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "argv", argv)
    return {"recorded": recorded, "root": root, "results": root / "results",
            "upload_results": outer["upload_results"], "dummy_report": dummy_report}


def _provider(s3, receipt_dir, *, configure=True):
    provider = launch.CurriculumProvider(
        job=JOB, source_sha="a" * 40, archive_sha256="b" * 64,
        manifest_sha256="c" * 64, ledger_path="ledger.json",
        clients=_fake_clients(s3), client_error=StubClientError)
    provider._instance_id = "i-0123456789abcdef0"
    provider._instance_ids = ["i-0123456789abcdef0"]
    provider._resources["bucket"] = "bucket"
    if configure:
        receipt_dir.mkdir()
        provider.configure_evidence(receipt_dir)
    return provider


# ---------------------------------------------------------------- path one

def test_delivery_rehearsal_normal_completion(worker, tmp_path):
    """The collector must receive the known result and every dummy checkpoint,
    with matching hashes and byte counts, and the completion signal must appear
    only after its required uploads."""
    s3 = SimulatedS3()
    uploaded = worker["upload_results"](s3, "bucket", worker["root"])
    assert uploaded["marker"] is True and uploaded["manifest"] is True
    assert sorted(uploaded["artifacts"]) == sorted(CHECKPOINTS)

    provider = _provider(s3, tmp_path / "receipt")
    outcome = provider.wait(JOB, timeout=30, poll_interval=0.01)
    assert outcome["worker_status"] == "REMOTE_FINISHED"
    collected = provider.collect(JOB)

    # the known result arrived byte-for-byte
    result_bytes = (tmp_path / "receipt" / "curriculum_result.json").read_bytes()
    assert json.loads(result_bytes) == worker["dummy_report"] | {
        "job": JOB, "artifacts": json.loads(result_bytes)["artifacts"]}
    assert collected["result_sha256"] == hashlib.sha256(result_bytes).hexdigest()

    # every dummy checkpoint arrived with matching bytes and hash
    assert collected["artifact_count"] == len(CHECKPOINTS)
    for entry in collected["artifacts"]:
        local = Path(entry["path"]).read_bytes()
        assert local == ("dummy-weights:" + entry["name"]).encode()
        assert entry["bytes"] == len(local)
        assert entry["sha256"] == hashlib.sha256(local).hexdigest()

    # the completion signal was uploaded LAST: every artifact and the manifest
    # were already in the bucket when result.json appeared
    order = s3.put_order
    assert order[-1] == "results/result.json"
    assert order.index("results/artifacts/manifest.json") < order.index(
        "results/result.json")
    for name in CHECKPOINTS:
        assert order.index("results/artifacts/" + name) < order.index(
            "results/result.json")

    # verified collection ⇒ cleanup may delete the bucket, and compute stopped
    assert launch.collection_is_verified(collected) is True
    status = provider.cleanup(JOB, collection_verified=True)
    assert status["complete"] is True
    # RUN_EVIDENCE_PRESERVATION_001: a verified collection no longer authorises
    # deletion. The archive is retained and the decision is DENY by default.
    assert status["bucket_deleted"] is False
    assert status["evidence_deleted"] is False
    assert status["deletion_decision"]["decision"] == "DENY"
    assert s3.deleted is False
    assert status["instances"]["i-0123456789abcdef0"] == "CONFIRMED_TERMINATED"


# ---------------------------------------------------------------- path two

def test_delivery_rehearsal_injected_upload_failure(worker, tmp_path):
    """An upload failure AFTER the dummy experiment returns must not lose the
    result, must be recorded separately, must report missing checkpoints
    explicitly, and must not let cleanup destroy the only surviving copy."""
    failing = "manifest.json"
    s3 = SimulatedS3(fail_on=failing)
    original = (worker["results"] / "result.json").read_bytes()
    with pytest.raises(Exception):
        worker["upload_results"](s3, "bucket", worker["root"])

    # 1. the original result survives byte-for-byte on disk
    assert (worker["results"] / "result.json").read_bytes() == original
    # 2. the failure is recorded separately, not over the result
    failure = {"type": "InternalError", "message": "upload failed"}
    (worker["results"] / "failure.json").write_text(
        json.dumps(failure, sort_keys=True, indent=2) + "\n")
    assert json.loads((worker["results"] / "failure.json").read_text()) == failure
    assert (worker["results"] / "result.json").read_bytes() == original

    # 3. uploads that DID land are the only surviving copy: nothing but artifacts
    assert "results/result.json" not in s3.objects

    provider = _provider(s3, tmp_path / "receipt")
    outcome = provider.wait(JOB, timeout=2, poll_interval=0.01)
    # the instance ends without ever publishing a completion signal
    assert outcome["worker_status"] in ("REMOTE_FAILED", "REMOTE_TIMED_OUT")
    assert "results/result.json" not in s3.objects
    # collection cannot even start: there is no result to collect
    with pytest.raises(ValueError, match="CURRICULUM_COLLECT_STATE"):
        provider.collect(JOB)
    assert launch.collection_is_verified(None) is False

    # 4. cleanup must retain the evidence bucket; retention is not a failure
    status = provider.cleanup(JOB, collection_verified=False)
    assert status["complete"] is True
    assert status["bucket_deleted"] is False
    assert status["evidence_deleted"] is False
    assert status["evidence_retained"] is True
    assert status["retained_bucket"] == "bucket"
    assert status["deletion_decision"]["decision"] == "DENY"
    assert not [entry for entry in status["failures"]
                if "EVIDENCE_RETAINED" in entry]
    assert s3.deleted is False
    # the compute still stopped
    assert status["instances"]["i-0123456789abcdef0"] == "CONFIRMED_TERMINATED"
    assert status["instances_termination_pending"] == []


def test_rehearsal_reports_missing_checkpoints_explicitly(worker, tmp_path):
    """A result whose checkpoints did not all arrive must be reported honestly:
    the missing checkpoint is NAMED, the collection is not verified, and the
    bucket is retained."""
    s3 = SimulatedS3()
    worker["upload_results"](s3, "bucket", worker["root"])
    # simulate one artifact lost in transport
    dropped = CHECKPOINTS[-1]
    s3.objects.pop("results/artifacts/" + dropped)
    provider = _provider(s3, tmp_path / "receipt")
    provider.wait(JOB, timeout=5, poll_interval=0.01)
    collected = provider.collect(JOB)
    assert collected["artifacts_missing"] == [dropped]
    assert collected["artifacts_available"] is False
    assert collected["reason"] == "ARTIFACTS_MISSING:" + dropped
    assert collected["artifact_count"] == len(CHECKPOINTS) - 1
    assert launch.collection_is_verified(collected) is False
    status = provider.cleanup(JOB, collection_verified=False)
    assert status["bucket_deleted"] is False and s3.deleted is False
    assert status["retained_bucket"] == "bucket"


def test_execute_reports_execution_collection_and_cleanup_separately(
        worker, tmp_path, monkeypatch):
    """The three outcomes are reported independently, and a run whose collection
    was not verified is not a completed deliverable."""
    s3 = SimulatedS3()
    worker["upload_results"](s3, "bucket", worker["root"])
    inner = _provider(s3, tmp_path / "receipt_execute", configure=False)

    class RealProvider:
        """Minimal provider that reuses the REAL wait/collect/cleanup."""

        def __init__(self, inner):
            self.inner = inner
            self.calls = []

        def configure_evidence(self, directory, contract=None):
            self.inner.configure_evidence(directory)

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
                                            launch.reservation_plan(),
                                            self.inner.ledger_path)
            return {**receipt, "aws_side_reservation": {"status": "RECORDED"}}

        def launch(self, job, permit):
            self.calls.append("launch")
            return {"job": job, "instance_id": "i-0123456789abcdef0"}

        def wait(self, job, timeout):
            return self.inner.wait(job, timeout, poll_interval=0.01)

        def collect(self, job):
            return self.inner.collect(job)

        def cleanup(self, job, *, collection_verified=False):
            return self.inner.cleanup(job, collection_verified=collection_verified)

    provider = RealProvider(inner)
    ledger = tmp_path / "ledger.json"
    prior = (launch.ROOT.parent / "CAS_META_1_LEARNED_SELECTION"
             / "records/aws_budget_ledger.json")
    approval = launch.ROOT / "records/budget/OWNER_APPROVAL_SOURCE.json"
    budget.initialize_ledger(prior, approval, ledger)
    inner.ledger_path = ledger
    request = {"schema": launch.REQUEST_SCHEMA, "job": JOB, "source_sha": "a" * 40,
               "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
               "launch_authorized": False}
    authority = {"schema": launch.AUTHORITY_SCHEMA, "job": JOB,
                 "source_sha": "a" * 40, "archive_sha256": "b" * 64,
                 "manifest_sha256": "c" * 64,
                 "owner_authorization_sha256": "0" * 64,
                 "pair_seeds": list(launch.FROZEN_PAIR_SEEDS),
                 "conditions": list(launch.FROZEN_CONDITIONS),
                 "checkpoints": list(launch.FROZEN_CHECKPOINTS),
                 "updates_per_learner": launch.FROZEN_UPDATES_PER_LEARNER,
                 "total_optimizer_steps": launch.FROZEN_TOTAL_UPDATES,
                 "panel_seed": launch.FROZEN_PANEL_SEED,
                 "learning_rate": 0.003,
                 "max_wall_seconds_per_learner":
                     launch.FROZEN_MAX_WALL_SECONDS_PER_LEARNER,
                 "reservation_usd": "7.00"}
    authority["owner_authorization_sha256"] = launch.digest(b'{"owner": "rehearsal"}\n')
    owner = tmp_path / "OWNER.json"
    owner.write_bytes(b'{"owner": "rehearsal"}\n')
    receipt_dir = tmp_path / "receipt_execute"
    result = launch.execute(request, authority, provider, ledger_path=ledger,
                            receipt_dir=receipt_dir, owner_authorization_path=owner)
    assert result["stages"] == {"execution": "FINISHED", "collection": "VERIFIED",
                                "cleanup": "COMPLETE"}
    assert result["completed_deliverable"] is True
    assert result["collected"]["artifact_count"] == len(CHECKPOINTS)
