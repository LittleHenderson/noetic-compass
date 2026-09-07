"""Pure tests for the condition-skill v9 AWS launch adapter (provider).

No real boto3/botocore is installed or imported. The module's import helper
``aws.condition_skill_v9_provider._import_boto3`` is monkeypatched to return a
fake client stack, and every budget operation runs against private temporary
ledgers built with the canonical ``aws.budget`` helper (never the real campaign
ledger).
"""
import argparse
import ast
import io
import json
from hashlib import sha256
from pathlib import Path
import sys
import zipfile

import pytest

from aws import budget
from aws import condition_skill_v9_launch as launch
from aws import condition_skill_v9_provider as provider
from aws import condition_skill_v9_resource_plan as plan


JOB = "cas-meta2-20260907160000-abcdef12"
INSTANCE = "i-0123456789abcdef0"
SOURCE_SHA = "a" * 40
SOURCE_BYTES = b"condition-skill-v9-source-payload-v9"
ARCHIVE_SHA = sha256(SOURCE_BYTES).hexdigest()
MANIFEST_SHA = "c" * 64


# --------------------------------------------------------------------------- #
# ledger fixture (private temporary ledger via the canonical budget helper)
# --------------------------------------------------------------------------- #
def make_ledger(tmp_path):
    path = tmp_path / "campaign_ledger.json"
    prior = tmp_path / "prior.json"
    approval = tmp_path / "approval.json"
    prior.write_bytes((launch.ROOT.parent / "CAS_META_1_LEARNED_SELECTION" /
                       "records/aws_budget_ledger.json").read_bytes())
    approval.write_bytes((launch.ROOT / "records/budget/OWNER_APPROVAL_SOURCE.json").read_bytes())
    budget.initialize_ledger(prior, approval, path)
    return path


def reservation_plan():
    return launch.reservation_plan()


# --------------------------------------------------------------------------- #
# fake AWS SDK stack
# --------------------------------------------------------------------------- #
class FakeConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeClientError(Exception):
    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.response = {"Error": {"Code": code, "Message": message}}


class FakeSTS:
    def __init__(self):
        self.calls = []
        self.account = "807562639912"

    def get_caller_identity(self):
        self.calls.append("get_caller_identity")
        return {"Account": self.account, "Arn": "arn:aws:iam::807562639912:user/test",
                "UserId": "AIDAEXAMPLE"}


class FakeEC2:
    def __init__(self):
        self.calls = []
        self.image = {"ImageId": "ami-0fbbd0facbc9e3cff", "State": "available",
                      "Architecture": "x86_64", "OwnerId": "898082745236"}
        self.gpu_name = "NVIDIA RTX PRO 4500"
        self.vcpus = 8
        self.conflicts = []
        self.instance_state = "running"
        self.terminated_called = False
        self.vpc_id = "vpc-0123456789abcdef0"
        self.subnet_id = "subnet-0123456789abcdef0"
        self.terminate_raises = None

    def describe_images(self, **kwargs):
        self.calls.append(("describe_images", kwargs))
        return {"Images": [self.image]}

    def describe_instance_types(self, **kwargs):
        self.calls.append(("describe_instance_types", kwargs))
        return {"InstanceTypes": [{"InstanceType": "g7.2xlarge",
                                   "GpuInfo": {"Gpus": [{"Name": self.gpu_name,
                                                         "Manufacturer": "NVIDIA",
                                                         "Count": 1}]},
                                   "VCpuInfo": {"DefaultVCpus": self.vcpus}}]}

    def describe_instance_type_offerings(self, **kwargs):
        self.calls.append(("describe_instance_type_offerings", kwargs))
        return {"InstanceTypeOfferings": [{"InstanceType": "g7.2xlarge",
                                           "LocationType": "region",
                                           "Location": "us-west-2"}]}

    def describe_instances(self, **kwargs):
        self.calls.append(("describe_instances", kwargs))
        if "Filters" in kwargs:
            return {"Reservations": [{"Instances": [{"InstanceId": iid}
                                                    for iid in self.conflicts]}] if self.conflicts else []}
        state = "terminated" if self.terminated_called else self.instance_state
        return {"Reservations": [{"Instances": [{"InstanceId": INSTANCE,
                                                 "State": {"Name": state}}]}]}

    def describe_vpcs(self, **kwargs):
        self.calls.append(("describe_vpcs", kwargs))
        return {"Vpcs": [{"VpcId": self.vpc_id, "IsDefault": True}]}

    def describe_subnets(self, **kwargs):
        self.calls.append(("describe_subnets", kwargs))
        return {"Subnets": [{"SubnetId": self.subnet_id, "DefaultForAz": True}]}

    def create_security_group(self, **kwargs):
        self.calls.append(("create_security_group", kwargs))
        return {"GroupId": "sg-0123456789abcdef0"}

    def revoke_security_group_egress(self, **kwargs):
        self.calls.append(("revoke_security_group_egress", kwargs))
        return {}

    def authorize_security_group_egress(self, **kwargs):
        self.calls.append(("authorize_security_group_egress", kwargs))
        return {}

    def delete_security_group(self, **kwargs):
        self.calls.append(("delete_security_group", kwargs))
        return {}

    def run_instances(self, **kwargs):
        self.calls.append(("run_instances", kwargs))
        return {"Instances": [{"InstanceId": INSTANCE}]}

    def terminate_instances(self, **kwargs):
        self.calls.append(("terminate_instances", kwargs))
        if self.terminate_raises is not None:
            raise self.terminate_raises
        self.terminated_called = True
        return {"TerminatingInstances": [{"InstanceId": kwargs["InstanceIds"][0]}]}


class FakeIAM:
    def __init__(self):
        self.calls = []

    def _record(self, name, kwargs):
        self.calls.append((name, kwargs))
        return {}

    def create_role(self, **kwargs):
        return self._record("create_role", kwargs)

    def put_role_policy(self, **kwargs):
        return self._record("put_role_policy", kwargs)

    def create_instance_profile(self, **kwargs):
        return self._record("create_instance_profile", kwargs)

    def add_role_to_instance_profile(self, **kwargs):
        return self._record("add_role_to_instance_profile", kwargs)

    def remove_role_from_instance_profile(self, **kwargs):
        return self._record("remove_role_from_instance_profile", kwargs)

    def delete_instance_profile(self, **kwargs):
        return self._record("delete_instance_profile", kwargs)

    def delete_role_policy(self, **kwargs):
        return self._record("delete_role_policy", kwargs)

    def delete_role(self, **kwargs):
        return self._record("delete_role", kwargs)


class FakeS3:
    def __init__(self):
        self.calls = []
        self.objects = {}
        self.head_lengths = {}
        self.missing = set()

    def create_bucket(self, **kwargs):
        self.calls.append(("create_bucket", kwargs))
        return {}

    def put_bucket_tagging(self, **kwargs):
        self.calls.append(("put_bucket_tagging", kwargs))
        return {}

    def put_public_access_block(self, **kwargs):
        self.calls.append(("put_public_access_block", kwargs))
        return {}

    def put_bucket_encryption(self, **kwargs):
        self.calls.append(("put_bucket_encryption", kwargs))
        return {}

    def put_object(self, **kwargs):
        self.calls.append(("put_object", kwargs))
        self.objects[kwargs["Key"]] = kwargs["Body"]
        return {}

    def get_object(self, **kwargs):
        self.calls.append(("get_object", kwargs))
        key = kwargs["Key"]
        if key in self.missing or key not in self.objects:
            raise FakeClientError("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[key])}

    def head_object(self, **kwargs):
        self.calls.append(("head_object", kwargs))
        key = kwargs["Key"]
        return {"ContentLength": self.head_lengths.get(key, len(self.objects.get(key, b"")))}

    def delete_objects(self, **kwargs):
        self.calls.append(("delete_objects", kwargs))
        return {}

    def delete_bucket(self, **kwargs):
        self.calls.append(("delete_bucket", kwargs))
        return {}


class FakeScheduler:
    def __init__(self):
        self.calls = []

    def create_schedule(self, **kwargs):
        self.calls.append(("create_schedule", kwargs))
        return {}

    def delete_schedule(self, **kwargs):
        self.calls.append(("delete_schedule", kwargs))
        return {}


class FakeQuotas:
    def __init__(self):
        self.calls = []
        self.value = 8

    def get_service_quota(self, **kwargs):
        self.calls.append(("get_service_quota", kwargs))
        return {"Quota": {"Value": self.value}}


class FakePricing:
    def __init__(self):
        self.calls = []
        self.usd = "2.52"

    def get_products(self, **kwargs):
        self.calls.append(("get_products", kwargs))
        product = {"terms": {"OnDemand": {"ABC": {"priceDimensions": {
            "ABC": {"unit": "Hrs", "pricePerUnit": {"USD": self.usd}}}}}}}
        return {"PriceList": [json.dumps(product)]}


class FakeSession:
    def __init__(self, clients, profile_name=None, region_name=None):
        self.clients = clients
        self.profile_name = profile_name
        self.region_name = region_name
        self.made = []

    def client(self, name, config=None, region_name=None):
        self.made.append((name, config, region_name))
        return self.clients[name]


class FakeBoto3:
    def __init__(self, clients):
        self.clients = clients
        self.Config = FakeConfig
        self.ClientError = FakeClientError
        self.sessions = []

    def Session(self, profile_name=None, region_name=None):
        session = FakeSession(self.clients, profile_name, region_name)
        self.sessions.append(session)
        return session


class FakeStack:
    def __init__(self):
        self.sts = FakeSTS()
        self.ec2 = FakeEC2()
        self.iam = FakeIAM()
        self.s3 = FakeS3()
        self.scheduler = FakeScheduler()
        self.quotas = FakeQuotas()
        self.pricing = FakePricing()
        self.clients = {"sts": self.sts, "ec2": self.ec2, "iam": self.iam,
                        "s3": self.s3, "scheduler": self.scheduler,
                        "service-quotas": self.quotas, "pricing": self.pricing}
        self.boto3 = FakeBoto3(self.clients)


def patch_import(monkeypatch, stack):
    monkeypatch.setattr(provider, "_import_boto3",
                        lambda: (stack.boto3, FakeConfig, FakeClientError))


def build_provider(stack, tmp_path, monkeypatch, **overrides):
    patch_import(monkeypatch, stack)
    args = argparse.Namespace(profile="default")
    kwargs = dict(job=JOB, source_sha=SOURCE_SHA, archive_sha256=ARCHIVE_SHA,
                  manifest_sha256=MANIFEST_SHA,
                  dataset_manifest_sha256=plan.DATASET_MANIFEST_SHA256,
                  ledger_path=make_ledger(tmp_path), source_archive=SOURCE_BYTES)
    kwargs.update(overrides)
    return provider.build(args, **kwargs)


def make_artifacts():
    members = {"result.json": b'{"status": "REMOTE_FINISHED"}',
               "config.json": b'{"seed": 7}'}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, raw in members.items():
            archive.writestr(name, raw)
    return buffer.getvalue(), members


def load_worker_result(stack, artifacts):
    result = {"job": JOB, "status": "REMOTE_FINISHED",
              "sha256": sha256(artifacts).hexdigest(), "bytes": len(artifacts),
              "experiment": plan.RESOURCE_PLAN["experiment"], "returncode": 0}
    stack.s3.objects["results/complete.json"] = json.dumps(result).encode()
    stack.s3.objects["results/artifacts.zip"] = artifacts
    stack.s3.head_lengths["results/artifacts.zip"] = len(artifacts)
    return result


def valid_permit(receipt, facts):
    return {"job": JOB, "source_sha": SOURCE_SHA, "archive_sha256": ARCHIVE_SHA,
            "manifest_sha256": MANIFEST_SHA,
            "dataset_manifest_sha256": plan.DATASET_MANIFEST_SHA256,
            "reservation": receipt, "preflight": facts,
            "resource_plan": plan.RESOURCE_PLAN}


# --------------------------------------------------------------------------- #
# lazy imports / import hygiene
# --------------------------------------------------------------------------- #
def test_no_boto3_or_botocore_import_at_module_level():
    source = Path(provider.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in ("boto3", "botocore"), alias.name
        elif isinstance(node, ast.ImportFrom):
            assert node.module is None or node.module.split(".")[0] not in ("boto3", "botocore")


def test_importing_module_does_not_pull_aws_sdk():
    # The provider (and its pure dependencies) never import the AWS SDK at import time.
    assert "boto3" not in sys.modules
    assert "botocore" not in sys.modules


# --------------------------------------------------------------------------- #
# build / identity resolution
# --------------------------------------------------------------------------- #
def test_build_reads_hash_bound_request(tmp_path, monkeypatch):
    stack = FakeStack()
    patch_import(monkeypatch, stack)
    request = {"schema": plan.REQUEST_SCHEMA, "job": JOB, "source_sha": SOURCE_SHA,
               "archive_sha256": ARCHIVE_SHA, "manifest_sha256": MANIFEST_SHA,
               "dataset_manifest_sha256": plan.DATASET_MANIFEST_SHA256,
               "seed": 7, "training": True, "native_execution": False,
               "automatic_retries": 0, "reservation_usd": "4.00",
               "launch_authorized": False, "new_reservation": False}
    raw = json.dumps(request, sort_keys=True).encode()
    request_path = tmp_path / "request.json"
    request_path.write_bytes(raw)
    args = argparse.Namespace(profile="default", request=str(request_path),
                              request_sha256=sha256(raw).hexdigest())
    built = provider.build(args, ledger_path=make_ledger(tmp_path),
                           source_archive=SOURCE_BYTES)
    assert built.job == JOB
    assert built.source_sha == SOURCE_SHA
    assert built.archive_sha256 == ARCHIVE_SHA
    assert built.manifest_sha256 == MANIFEST_SHA


def test_build_rejects_wrong_request_hash(tmp_path, monkeypatch):
    stack = FakeStack()
    patch_import(monkeypatch, stack)
    request_path = tmp_path / "request.json"
    request_path.write_bytes(b'{"schema": "wrong"}')
    args = argparse.Namespace(profile="default", request=str(request_path),
                              request_sha256="0" * 64)
    with pytest.raises(ValueError, match="CONDITION_SKILL_V9_REQUEST_HASH_MISMATCH"):
        provider.build(args)


def test_build_accepts_clients_injection(tmp_path):
    stack = FakeStack()
    args = argparse.Namespace()
    built = provider.build(args, clients=stack.clients, job=JOB, source_sha=SOURCE_SHA,
                           archive_sha256=ARCHIVE_SHA, manifest_sha256=MANIFEST_SHA,
                           dataset_manifest_sha256=plan.DATASET_MANIFEST_SHA256,
                           ledger_path=make_ledger(tmp_path), source_archive=SOURCE_BYTES)
    assert built.clients is stack.clients


# --------------------------------------------------------------------------- #
# preflight fact validation
# --------------------------------------------------------------------------- #
def test_preflight_returns_frozen_facts(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    facts = built.preflight()
    assert facts == {"account": "807562639912", "region": "us-west-2",
                     "ami": "ami-0fbbd0facbc9e3cff", "instance_type": "g7.2xlarge",
                     "instance_count": 1, "gpu_name_contains": "RTX PRO 4500",
                     "visible_gpu_count": 1, "t4_rejected": True,
                     "rate_ceiling_usd": "2.52", "conflicting_resources": []}
    assert "get_caller_identity" in stack.sts.calls
    assert any(name == "describe_images" for name, _ in stack.ec2.calls)
    assert any(name == "get_products" for name, _ in stack.pricing.calls)


@pytest.mark.parametrize("mutate,code", [
    (lambda s: setattr(s.sts, "account", "000000000000"),
     "CONDITION_SKILL_V9_PREFLIGHT_ACCOUNT"),
    (lambda s: setattr(s.ec2, "image", {**s.ec2.image, "State": "deregistered"}),
     "CONDITION_SKILL_V9_PREFLIGHT_AMI"),
    (lambda s: setattr(s.ec2, "gpu_name", "NVIDIA T4"), "CONDITION_SKILL_V9_PREFLIGHT_T4"),
    (lambda s: setattr(s.ec2, "gpu_name", "NVIDIA L4"), "CONDITION_SKILL_V9_PREFLIGHT_GPU_NAME"),
    (lambda s: setattr(s.pricing, "usd", "3.00"),
     "CONDITION_SKILL_V9_PREFLIGHT_RATE_CEILING"),
    (lambda s: setattr(s.ec2, "conflicts", ["i-11111111111111111"]),
     "CONDITION_SKILL_V9_PREFLIGHT_CONFLICTING_RESOURCES"),
    (lambda s: setattr(s.quotas, "value", 0), "CONDITION_SKILL_V9_PREFLIGHT_QUOTA"),
])
def test_preflight_rejects_mismatches(tmp_path, monkeypatch, mutate, code):
    stack = FakeStack()
    mutate(stack)
    built = build_provider(stack, tmp_path, monkeypatch)
    with pytest.raises(ValueError, match=code):
        built.preflight()


# --------------------------------------------------------------------------- #
# reservation: exactly-once, refusal, frozen amount
# --------------------------------------------------------------------------- #
def test_reserve_is_exactly_once(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    receipt = built.reserve("4.00")
    assert receipt["reservation"]["status"] == budget.STATUS
    assert receipt["reservation"]["job"] == JOB
    assert receipt["reservation"]["reserved_usd"] == "4.00"
    assert receipt["aws_side_reservation"]["status"] == "RECORDED"
    with pytest.raises(ValueError, match="CONDITION_SKILL_V9_RESERVATION_ALREADY_ATTEMPTED"):
        built.reserve("4.00")


def test_reserve_refuses_existing_job_in_ledger(tmp_path, monkeypatch):
    stack = FakeStack()
    ledger = make_ledger(tmp_path)
    budget.reserve_budget(JOB, SOURCE_SHA, ARCHIVE_SHA, "4.00",
                          reservation_plan(), ledger)
    built = build_provider(stack, tmp_path, monkeypatch, ledger_path=ledger)
    with pytest.raises(ValueError, match="JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY"):
        built.reserve("4.00")


def test_reserve_amount_is_frozen(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="CONDITION_SKILL_V9_RESERVATION_AMOUNT_FROZEN"):
        built.reserve("5.00")


def test_reserve_records_call_and_updates_private_ledger(tmp_path, monkeypatch):
    stack = FakeStack()
    ledger = make_ledger(tmp_path)
    built = build_provider(stack, tmp_path, monkeypatch, ledger_path=ledger)
    built.reserve("4.00")
    assert built.calls == ["reserve"]
    state = budget.read_ledger(ledger)
    assert state["reservations"][-1]["job"] == JOB
    assert state["reservations"][-1]["status"] == budget.STATUS


def test_reserve_records_aws_side_reservation_after_ledger(tmp_path, monkeypatch):
    stack = FakeStack()
    ledger = make_ledger(tmp_path)
    built = build_provider(stack, tmp_path, monkeypatch, ledger_path=ledger)
    receipt = built.reserve("4.00")
    # Phase 2 record exists in the job bucket and is bound to the ledger entry.
    assert receipt["aws_side_reservation"]["status"] == "RECORDED"
    assert "reservation/reservation_receipt.json" in stack.s3.objects
    assert "reservation/ledger_snapshot.json" in stack.s3.objects
    stored = json.loads(stack.s3.objects["reservation/reservation_receipt.json"].decode())
    assert stored["reservation"]["job"] == JOB
    assert stored["reservation"]["status"] == budget.STATUS


def test_reserve_reports_aws_side_failure_without_refund_or_retry(tmp_path, monkeypatch):
    stack = FakeStack()
    ledger = make_ledger(tmp_path)
    built = build_provider(stack, tmp_path, monkeypatch, ledger_path=ledger)
    stack.s3.put_object = lambda **kw: (_ for _ in ()).throw(RuntimeError("s3-down"))
    receipt = built.reserve("4.00")
    # The ledger append already happened and must not be refunded or retried.
    assert receipt["reservation"]["status"] == budget.STATUS
    assert budget.read_ledger(ledger)["reservations"][-1]["job"] == JOB
    # The AWS-side failure is reported, not swallowed and not raised.
    assert receipt["aws_side_reservation"]["status"] == "FAILED"
    assert "s3-down" in receipt["aws_side_reservation"]["failure"]
    assert built.calls == ["reserve"]


def test_provider_never_imports_other_reservation_owners():
    tree = ast.parse(Path(provider.__file__).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "launch_child_qualification_v8" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert "launch_child_qualification_v8" not in module


# --------------------------------------------------------------------------- #
# launch / wait / collect / cleanup call sequences
# --------------------------------------------------------------------------- #
def test_full_call_sequence_and_shapes(tmp_path, monkeypatch):
    stack = FakeStack()
    artifacts, members = make_artifacts()
    load_worker_result(stack, artifacts)
    built = build_provider(stack, tmp_path, monkeypatch)

    facts = built.preflight()
    receipt = built.reserve("4.00")
    launched = built.launch(JOB, valid_permit(receipt, facts))
    waited = built.wait(JOB, timeout=3600)
    collected = built.collect(JOB)
    cleaned = built.cleanup(JOB)

    assert built.calls == ["preflight", "reserve", "launch", "wait", "collect", "cleanup"]
    assert launched["instance_id"] == INSTANCE
    assert launched["client_token"] == JOB
    assert launched["automatic_retries"] == 0
    assert waited == {"worker_status": "REMOTE_FINISHED"}
    expected = {name: {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
                for name, raw in members.items()}
    assert collected == expected
    assert cleaned["complete"] is True
    assert cleaned["failures"] == []
    assert cleaned["instance_terminated"] is True


def test_launch_registers_single_instance_with_client_token(tmp_path, monkeypatch):
    stack = FakeStack()
    artifacts, _ = make_artifacts()
    load_worker_result(stack, artifacts)
    built = build_provider(stack, tmp_path, monkeypatch)
    facts = built.preflight()
    receipt = built.reserve("4.00")
    built.launch(JOB, valid_permit(receipt, facts))
    run_calls = [kwargs for name, kwargs in stack.ec2.calls if name == "run_instances"]
    assert len(run_calls) == 1
    kwargs = run_calls[0]
    assert kwargs["ClientToken"] == JOB
    assert kwargs["MinCount"] == 1 and kwargs["MaxCount"] == 1
    assert kwargs["InstanceType"] == "g7.2xlarge"
    assert kwargs["ImageId"] == "ami-0fbbd0facbc9e3cff"
    assert kwargs["MetadataOptions"] == {"HttpTokens": "required", "HttpEndpoint": "enabled"}
    assert kwargs["InstanceInitiatedShutdownBehavior"] == "terminate"


def test_launch_requires_reservation_first(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    facts = built.preflight()
    with pytest.raises(ValueError, match="CONDITION_SKILL_V9_LAUNCH_REQUIRES_RESERVATION"):
        built.launch(JOB, valid_permit({"reservation": {"job": JOB, "status": budget.STATUS}},
                                       facts))


def test_launch_rejects_permit_identity_mismatch(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    facts = built.preflight()
    receipt = built.reserve("4.00")
    permit = valid_permit(receipt, facts)
    permit["source_sha"] = "b" * 40
    with pytest.raises(ValueError, match="CONDITION_SKILL_V9_PERMIT_IDENTITY_MISMATCH"):
        built.launch(JOB, permit)


def ready(built):
    """Run preflight + reserve and return the facts and receipt for a permit."""
    facts = built.preflight()
    receipt = built.reserve("4.00")
    return facts, receipt


def test_wait_returns_worker_status_after_polling(tmp_path, monkeypatch):
    stack = FakeStack()
    artifacts, _ = make_artifacts()
    load_worker_result(stack, artifacts)
    built = build_provider(stack, tmp_path, monkeypatch)
    facts, receipt = ready(built)
    built.launch(JOB, valid_permit(receipt, facts))
    waited = built.wait(JOB, timeout=3600)
    assert waited == {"worker_status": "REMOTE_FINISHED"}


def test_wait_times_out_without_worker_result(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    facts, receipt = ready(built)
    built.launch(JOB, valid_permit(receipt, facts))
    # Nothing uploaded to S3; get_object keeps raising NoSuchKey.
    waited = built.wait(JOB, timeout=0.3, poll_interval=0.01)
    assert waited == {"worker_status": "REMOTE_TIMED_OUT"}


def test_cleanup_records_every_failure(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    facts, receipt = ready(built)
    built.launch(JOB, valid_permit(receipt, facts))
    stack.ec2.terminate_raises = RuntimeError("boom")
    stack.s3.delete_objects = lambda **kw: (_ for _ in ()).throw(RuntimeError("s3-broken"))
    cleaned = built.cleanup(JOB)
    assert cleaned["complete"] is False
    assert any("INSTANCE_TERMINATION_FAILED" in failure for failure in cleaned["failures"])
    assert any("INPUT_DELETION_FAILED" in failure for failure in cleaned["failures"])
    assert cleaned["instance_terminated"] is False


def test_cleanup_is_call_safe_before_launch(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    cleaned = built.cleanup(JOB)
    assert cleaned["complete"] is True
    assert cleaned["failures"] == []
    assert cleaned["instance_terminated"] is True


def test_cleanup_deletes_results_before_bucket(tmp_path, monkeypatch):
    # A real S3 refuses to delete a non-empty bucket. The cleanup must request
    # deletion of results/* keys, or every successful run would end incomplete.
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    facts, receipt = ready(built)
    built.launch(JOB, valid_permit(receipt, facts))

    deleted_keys = []

    def tracking_delete_objects(**kwargs):
        deleted_keys.extend(item["Key"] for item in kwargs["Delete"]["Objects"])
        return {}

    def strict_delete_bucket(**kwargs):
        remaining = set(stack.s3.objects) - set(deleted_keys)
        if remaining:
            raise FakeClientError("BucketNotEmpty")
        return {}

    stack.s3.delete_objects = tracking_delete_objects
    stack.s3.delete_bucket = strict_delete_bucket
    cleaned = built.cleanup(JOB)
    assert cleaned["complete"] is True
    assert "results/complete.json" in deleted_keys
    assert "results/artifacts.zip" in deleted_keys
    assert cleaned["results_deleted"] is True
    assert cleaned["bucket_deleted"] is True


def test_ensure_bucket_does_not_memoize_half_hardened(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)

    def broken_tagging(**kwargs):
        raise FakeClientError("AccessDenied")

    stack.s3.put_bucket_tagging = broken_tagging
    with pytest.raises(FakeClientError):
        built._ensure_bucket(stack.s3)
    assert built._resources.get("bucket") is None
    # After the failure is repaired, a later call succeeds and memoizes.
    stack.s3.put_bucket_tagging = lambda **kwargs: {}
    assert built._ensure_bucket(stack.s3) == built._bucket_name()
    assert built._resources.get("bucket") == built._bucket_name()


def test_collect_requires_wait_result(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    facts, receipt = ready(built)
    built.launch(JOB, valid_permit(receipt, facts))
    with pytest.raises(ValueError, match="CONDITION_SKILL_V9_COLLECT_REQUIRES_RESULT"):
        built.collect(JOB)


# --------------------------------------------------------------------------- #
# rendered remote driver / user-data bootstrap
# --------------------------------------------------------------------------- #
def test_render_remote_driver_installs_venv_and_uploads_real_artifacts(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    built._resources["bucket"] = built._bucket_name()
    driver = built._render_remote({})
    compile(driver, "<remote>", "exec")
    # venv creation + CAS_META2_VENV_PYTHON discovery over discovered binaries
    assert "CAS_META2_VENV_PYTHON" in driver
    assert "'-m', 'venv'" in driver
    assert "'python3.12'" in driver and "'python3.11'" in driver and "'python3'" in driver
    # frozen torch cu128 install from the pinned index
    assert "'torch==2.11.0'" in driver
    assert "'--index-url', TORCH_INDEX" in driver
    assert "'https://download.pytorch.org/whl/cu128'" in driver
    # the two frozen wheels shipped in the package
    assert "'casformer_reference-0.1.0-py3-none-any.whl'" in driver
    assert "'cas_neural_cjt-0.2.0-py3-none-any.whl'" in driver
    assert "'research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist'" in driver
    # requirements-gpu.txt install path
    assert "'-r', str(REQUIREMENTS)" in driver
    # artifacts.zip built with a real sha256, then complete.json with real sha256/bytes
    assert "hashlib.sha256(artifacts).hexdigest()" in driver
    assert "artifacts = make_artifacts()" in driver
    assert "Key='results/artifacts.zip'" in driver
    assert "Key='results/complete.json'" in driver
    # failure path still uploads complete.json and attempts artifacts.zip
    assert "except BaseException as error:" in driver
    assert "'message': str(error)[:2000]" in driver
    assert "complete['failure'] = failure" in driver
    # no placeholder sha256 remains
    assert "'sha256': ''" not in driver


def test_user_data_within_bound_and_contains_hash_checks(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    text = built._user_data(built._bucket_name(), "d" * 64)
    assert len(text.encode("utf-8")) <= 16384
    assert "sha256sum -c -" in text
    assert ARCHIVE_SHA in text


def test_cleanup_treats_absent_schedule_as_clean(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    facts, receipt = ready(built)
    built.launch(JOB, valid_permit(receipt, facts))

    def absent_schedule(**kwargs):
        raise FakeClientError("ResourceNotFoundException")

    stack.scheduler.delete_schedule = absent_schedule
    cleaned = built.cleanup(JOB)
    assert cleaned["complete"] is True
    assert cleaned["schedule_removed"] is True
    assert cleaned.get("schedule_was_absent") is True
    assert cleaned["failures"] == []


def test_cleanup_deletes_security_group(tmp_path, monkeypatch):
    stack = FakeStack()
    built = build_provider(stack, tmp_path, monkeypatch)
    facts, receipt = ready(built)
    built.launch(JOB, valid_permit(receipt, facts))
    cleaned = built.cleanup(JOB)
    assert cleaned["security_group_deleted"] is True
    deleted = [call for call in stack.ec2.calls if call[0] == "delete_security_group"]
    assert deleted
