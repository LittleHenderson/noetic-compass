"""AWS launch adapter (provider) for the condition-skill v9 learning pilot.

This module is the single owner of the v9 reservation path. It is NOT wired
into any existing lifecycle entrypoint that already owns a reservation (for
example ``launch_child_qualification_v8``); doing so would reserve twice under
the shared campaign ledger. The v9 provider reserves exactly once, through the
canonical helper ``aws.budget.reserve_budget``, and the v9 launch lifecycle
(``aws.condition_skill_v9_launch``) is the only caller of this provider.

``reserve()`` is a strict two-phase operation. Phase 1 appends the canonical
campaign-ledger entry through ``aws.budget`` under its lock and is the first
and authoritative step; Phase 2 records the reservation on the AWS side
(on-demand: a receipt object in the job bucket, never an EC2 capacity
reservation) and only runs after the append succeeded. If the AWS-side step
fails, the append-only history already recorded the attempt, so there is no
refund and no retry: the failure is reported in the returned receipt.
``reserve()`` never delegates to another lifecycle entrypoint that owns its own
reservation (for example ``launch_child_qualification_v8._run_authorized``).

The AWS SDK (boto3/botocore) is imported LAZILY, only inside ``build()`` and
the client construction path. The guarded pure checker and every test inject a
fake client stack (by monkeypatching the module's import helper ``_import_boto3``
or passing ``boto3_module=``/``clients=``) and never import the real SDK.

Cleanup is call-safe: it is safe to call ``cleanup()`` before, during, or after
a launch, and it records every failure instead of raising mid-way. There are no
automatic workload retries; bounded read-only readiness observations are not
new workload attempts. The single registered instance uses
``ClientToken=job``. The provider records what it observes in the launch-side
receipt (the returned ``InstanceId`` plus ``ClientToken=job`` and the IMDSv2
``HttpTokens: required`` request); it does not claim to prove in-guest identity
by itself.
"""
from __future__ import annotations

import io
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import re
import stat
import time
from zipfile import ZipFile

from aws import budget
from aws import condition_skill_v9_resource_plan as plan
from aws import condition_skill_v9_launch as launch
from aws import condition_skill_v9_remote as remote_worker

SCHEMA = "cas-meta2-condition-skill-v9-provider/9"
REMOTE_CONFIG_SCHEMA = "cas-meta2-condition-skill-v9-remote-config/9"
JOB_PATTERN = plan.JOB_PATTERN
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
INSTANCE_ID = re.compile(r"i-[0-9a-f]{17}\Z")
VCPU_QUOTA_CODE = "L-DB2E81BA"
WORKER_ROOT = "/opt/cas-meta2-condition-skill-v9"
IAM_READY_ATTEMPTS = 16
OBSERVATION_DELAY_SECONDS = 2
RESULT_RETENTION_DAYS = 7


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def digest(raw):
    return sha256(raw).hexdigest()


class _DefaultClientError(Exception):
    """Fallback for error-path handling when no botocore ClientError is injected."""

    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.response = {"Error": {"Code": code, "Message": message}}


def _import_boto3():
    """Lazy, guarded AWS SDK import. Tests monkeypatch this exact function.

    Returns ``(boto3, Config, ClientError)``. Nothing in this module imports
    boto3 or botocore at import time; the pure checker and tests never reach
    this function, and monkeypatch it to inject a fake stack instead.
    """
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    return boto3, Config, ClientError


def _resolve_identity(arguments, *, job, source_sha, archive_sha256,
                      manifest_sha256, dataset_manifest_sha256):
    """Resolve the job identity either from an injection seam or the request file.

    In the real flow the request file (and its sha256) are already read and
    hash-verified by ``launch.main()``; ``build()`` re-reads and re-verifies
    them here so the provider can reserve for the exact bound job without the
    launch lifecycle passing the job into ``reserve()``.
    """
    provided = (job, source_sha, archive_sha256, manifest_sha256, dataset_manifest_sha256)
    if all(value is not None for value in provided):
        require(type(job) is str and re.fullmatch(JOB_PATTERN, job) is not None,
                "CONDITION_SKILL_V9_JOB")
        require(type(source_sha) is str and bool(HEX40.fullmatch(source_sha)),
                "CONDITION_SKILL_V9_SOURCE_SHA")
        require(type(archive_sha256) is str and bool(HEX64.fullmatch(archive_sha256)),
                "CONDITION_SKILL_V9_ARCHIVE_SHA")
        require(type(manifest_sha256) is str and bool(HEX64.fullmatch(manifest_sha256)),
                "CONDITION_SKILL_V9_MANIFEST_SHA")
        require(type(dataset_manifest_sha256) is str
                and dataset_manifest_sha256 == plan.DATASET_MANIFEST_SHA256,
                "CONDITION_SKILL_V9_DATASET_MANIFEST")
        return {"job": job, "source_sha": source_sha, "archive_sha256": archive_sha256,
                "manifest_sha256": manifest_sha256,
                "dataset_manifest_sha256": dataset_manifest_sha256}
    require(all(value is None for value in provided),
            "CONDITION_SKILL_V9_PARTIAL_IDENTITY_INJECTION")
    require(getattr(arguments, "request", None) and getattr(arguments, "request_sha256", None),
            "CONDITION_SKILL_V9_REQUEST_INPUTS_REQUIRED")
    raw = Path(arguments.request).read_bytes()
    require(digest(raw) == arguments.request_sha256, "CONDITION_SKILL_V9_REQUEST_HASH_MISMATCH")
    request = json.loads(raw)
    plan.validate_launch_request(request)
    return {"job": request["job"], "source_sha": request["source_sha"],
            "archive_sha256": request["archive_sha256"],
            "manifest_sha256": request["manifest_sha256"],
            "dataset_manifest_sha256": request["dataset_manifest_sha256"]}


def build(arguments, boto3_module=None, *, job=None, source_sha=None,
          archive_sha256=None, manifest_sha256=None, dataset_manifest_sha256=None,
          ledger_path=None, clients=None, source_archive=None, client_error=None):
    """Build a provider instance from launch arguments plus injection seams.

    ``arguments`` is an argparse namespace with at least ``.profile`` (default
    ``"default"``). All identity fields, the ledger path, the client stack, the
    source archive, and the botocore ClientError class are injectable so tests
    never import or install the real AWS SDK.
    """
    profile = getattr(arguments, "profile", "default")
    identity = _resolve_identity(arguments, job=job, source_sha=source_sha,
                                 archive_sha256=archive_sha256,
                                 manifest_sha256=manifest_sha256,
                                 dataset_manifest_sha256=dataset_manifest_sha256)
    if clients is None:
        if boto3_module is None:
            boto3_module, Config, client_error = _import_boto3()
        else:
            Config = getattr(boto3_module, "Config", None)
            client_error = getattr(boto3_module, "ClientError", None)
            require(Config is not None and client_error is not None,
                    "CONDITION_SKILL_V9_INJECTED_SDK_MISSING_BOTOCORE")
        config = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0})
        session = boto3_module.Session(profile_name=profile,
                                       region_name=plan.RESOURCE_PLAN["region"])
        clients = {name: session.client(name, config=config) for name in
                   ("sts", "ec2", "iam", "s3", "scheduler", "service-quotas")}
        clients["pricing"] = session.client("pricing", region_name="us-east-1",
                                            config=config)
    return ConditionSkillV9Provider(
        job=identity["job"], source_sha=identity["source_sha"],
        archive_sha256=identity["archive_sha256"],
        manifest_sha256=identity["manifest_sha256"],
        dataset_manifest_sha256=identity["dataset_manifest_sha256"],
        ledger_path=ledger_path if ledger_path is not None else launch.LEDGER_PATH,
        clients=clients, source_archive=source_archive, client_error=client_error,
    )


def _locate_source_archive(archive_sha256):
    """Find the already-built source package by its archive hash, under records/.

    The package builder writes a receipt with ``archive_sha256`` and the
    ``archive`` path; nothing is rebuilt here. The launch lifecycle must still
    verify the bytes against ``archive_sha256`` before upload.
    """
    require(type(archive_sha256) is str and bool(HEX64.fullmatch(archive_sha256)),
            "CONDITION_SKILL_V9_ARCHIVE_SHA")
    for receipt in sorted((launch.ROOT / "records").rglob("receipt.json")):
        try:
            document = json.loads(receipt.read_bytes())
        except (OSError, ValueError):
            continue
        if document.get("archive_sha256") == archive_sha256 and document.get("archive"):
            archive = Path(document["archive"])
            if archive.is_file():
                return archive
    raise ValueError("CONDITION_SKILL_V9_SOURCE_ARCHIVE_NOT_FOUND")


class ConditionSkillV9Provider:
    """Injected provider implementing the v9 launch lifecycle interface."""

    def __init__(self, *, job, source_sha, archive_sha256, manifest_sha256,
                 dataset_manifest_sha256, ledger_path, clients, source_archive=None,
                 client_error=None, budget_module=budget, launch_module=launch):
        self.job = job
        self.source_sha = source_sha
        self.archive_sha256 = archive_sha256
        self.manifest_sha256 = manifest_sha256
        self.dataset_manifest_sha256 = dataset_manifest_sha256
        self.ledger_path = ledger_path
        self.region = plan.RESOURCE_PLAN["region"]
        self.clients = clients
        self.source_archive = source_archive
        self.budget = budget_module
        self.launch_module = launch_module
        self._client_error = client_error or _DefaultClientError
        self.calls = []
        self._reserved = False
        self._launch_attempted = False
        self._launch_called = False
        self._instance_id = None
        self._result = None
        self._resources = {}
        self._evidence = None
        self._event_number = 0
        self._result_raw = None
        self._durable_results = False
        self._durable_files = {}
        self._source_copy = None
        self._bucket_ready = False
        self._run_state = "NOT_ATTEMPTED"
        self._instance_ids = []

    def configure_evidence(self, directory):
        """Must be configured before side effects; no in-memory-only paid run."""
        directory = self.launch_module.evidence_directory(directory)
        require(directory.is_dir() and self._evidence is None,
                "CONDITION_SKILL_V9_FRESH_EVIDENCE_REQUIRED")
        self._evidence = directory
        self._event("provider_configured", "OBSERVED")

    def _event(self, operation, state, **details):
        require(self._evidence is not None, "CONDITION_SKILL_V9_EVIDENCE_REQUIRED")
        self._event_number += 1
        return self.launch_module.write_evidence(
            self._evidence / ("provider_%04d.json" % self._event_number),
            canonical({"schema": SCHEMA, "job": self.job, "source_sha": self.source_sha,
                       "operation": operation, "state": state,
                       "observed_utc": datetime.now(timezone.utc).isoformat(),
                       "resources": dict(self._resources), **details}))

    def _effect(self, operation, callback, **arguments):
        # Intents do not copy user data, credentials, or arbitrary SDK bodies.
        self._event(operation, "REQUESTED")
        try:
            result = callback(**arguments)
        except BaseException as error:
            self._event(operation, "FAILED", error=type(error).__name__ + ":" + str(error)[:2000])
            raise
        self._event(operation, "RETURNED",
                    request_id=result.get("ResponseMetadata", {}).get("RequestId"))
        return result

    @staticmethod
    def _error_code(error):
        return getattr(error, "response", {}).get("Error", {}).get("Code")

    def _wait_for_iam(self, worker, timer, worker_arn, timer_arn, profile_arn):
        """Bounded IAM readback, explicitly not proof of EC2 propagation."""
        iam = self.clients["iam"]
        deadline = time.monotonic() + 60
        for attempt in range(IAM_READY_ATTEMPTS):
            try:
                roles = [iam.get_role(RoleName=name)["Role"] for name in (worker, timer)]
                profile = iam.get_instance_profile(InstanceProfileName=worker)["InstanceProfile"]
                require([role.get("Arn") for role in roles] == [worker_arn, timer_arn]
                        and profile.get("Arn") == profile_arn,
                        "CONDITION_SKILL_V9_IAM_READBACK_IDENTITY")
                attached = [role.get("Arn") for role in profile.get("Roles", [])]
                ready = attached == [worker_arn]
                self._event("iam_readback", "OBSERVED", attempt=attempt + 1,
                            profile_arn=profile_arn, attached_roles=attached, ready=ready,
                            ec2_propagation_proved=False)
                if ready:
                    return {"profile_arn": profile_arn, "worker_role_arn": worker_arn,
                            "timer_role_arn": timer_arn, "attempts": attempt + 1,
                            "ec2_propagation_proved": False}
            except self._client_error as error:
                if self._error_code(error) != "NoSuchEntity":
                    raise
                self._event("iam_readback", "NOT_READY", attempt=attempt + 1,
                            error_code="NoSuchEntity")
            if time.monotonic() >= deadline:
                break
            time.sleep(OBSERVATION_DELAY_SECONDS)
        raise ValueError("CONDITION_SKILL_V9_IAM_READBACK_TIMEOUT")

    def _discover_instances(self):
        """Recover one ambiguous request by its stable token AND exact job tag."""
        arguments = {"Filters": [
            {"Name": "client-token", "Values": [self.job]},
            {"Name": "tag:cas_meta_job", "Values": [self.job]}]}
        instances = []
        tokens = set()
        while True:
            response = self.clients["ec2"].describe_instances(**arguments)
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    require(instance.get("ClientToken") == self.job and
                            {t["Key"]: t["Value"] for t in instance.get("Tags", [])}.get("cas_meta_job") == self.job,
                            "CONDITION_SKILL_V9_RECOVERY_IDENTITY")
                    require(bool(INSTANCE_ID.fullmatch(instance.get("InstanceId", ""))),
                            "CONDITION_SKILL_V9_RECOVERY_INSTANCE_ID")
                    instances.append(instance)
            if not response.get("NextToken"):
                break
            require(response["NextToken"] not in tokens and len(tokens) < 32,
                    "CONDITION_SKILL_V9_RECOVERY_PAGINATION")
            tokens.add(response["NextToken"])
            arguments["NextToken"] = response["NextToken"]
            require(len(instances) <= 100, "CONDITION_SKILL_V9_RECOVERY_BOUND")
        self._instance_ids = sorted(set(self._instance_ids + [i["InstanceId"] for i in instances]))
        self._event("instance_recovery", "OBSERVED", instance_ids=self._instance_ids,
                    states={i["InstanceId"]: i.get("State", {}).get("Name") for i in instances})
        return instances

    def reservation_plan(self):
        """Exact task/resource binding for the canonical budget helper."""
        return self.launch_module.reservation_plan()

    # ------------------------------------------------------------------ #
    # read-only preflight
    # ------------------------------------------------------------------ #
    def preflight(self):
        self.calls.append("preflight")
        frozen = plan.RESOURCE_PLAN
        ec2, sts, pricing, quotas = (self.clients[name] for name in
                                     ("ec2", "sts", "pricing", "service-quotas"))

        identity = sts.get_caller_identity()
        require(type(identity.get("Account")) is str and identity["Account"] == frozen["account"],
                "CONDITION_SKILL_V9_PREFLIGHT_ACCOUNT")
        require(self.region == frozen["region"], "CONDITION_SKILL_V9_PREFLIGHT_REGION")

        images = ec2.describe_images(ImageIds=[frozen["ami"]]).get("Images", [])
        require(len(images) == 1 and images[0].get("State") == "available"
                and images[0].get("Architecture") == "x86_64"
                and images[0].get("OwnerId") == "898082745236",
                "CONDITION_SKILL_V9_PREFLIGHT_AMI")

        descriptions = ec2.describe_instance_types(
            InstanceTypes=[frozen["instance_type"]]).get("InstanceTypes", [])
        require(len(descriptions) == 1
                and descriptions[0].get("InstanceType") == frozen["instance_type"],
                "CONDITION_SKILL_V9_PREFLIGHT_INSTANCE_TYPE")
        gpus = descriptions[0].get("GpuInfo", {}).get("Gpus", [])
        require(len(gpus) == 1, "CONDITION_SKILL_V9_PREFLIGHT_GPU_COUNT")
        gpu_name = gpus[0].get("Name", "")
        require(re.search(r"t4", gpu_name, re.IGNORECASE) is None,
                "CONDITION_SKILL_V9_PREFLIGHT_T4")
        require(frozen["gpu_name_contains"] in gpu_name, "CONDITION_SKILL_V9_PREFLIGHT_GPU_NAME")
        visible_gpu_count = sum(gpu.get("Count", 1) for gpu in gpus)
        require(visible_gpu_count == frozen["visible_gpu_count"],
                "CONDITION_SKILL_V9_PREFLIGHT_VISIBLE_GPU_COUNT")

        offerings = ec2.describe_instance_type_offerings(LocationType="region", Filters=[
            {"Name": "instance-type", "Values": [frozen["instance_type"]]}]
        ).get("InstanceTypeOfferings", [])
        require(len(offerings) >= 1, "CONDITION_SKILL_V9_PREFLIGHT_OFFERINGS")

        fields = {"instanceType": frozen["instance_type"], "location": "US West (Oregon)",
                  "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA",
                  "capacitystatus": "Used", "marketoption": "OnDemand",
                  "operation": "RunInstances"}
        price = pricing.get_products(ServiceCode="AmazonEC2", Filters=[
            {"Type": "TERM_MATCH", "Field": key, "Value": value}
            for key, value in fields.items()])
        require(not price.get("NextToken"), "CONDITION_SKILL_V9_PREFLIGHT_PAGINATED_PRICE")
        rates = [Decimal(dimension["pricePerUnit"]["USD"])
                 for raw in price.get("PriceList", [])
                 for term in json.loads(raw).get("terms", {}).get("OnDemand", {}).values()
                 for dimension in term.get("priceDimensions", {}).values()
                 if dimension.get("unit") == "Hrs"]
        require(rates and all(rate.is_finite() and rate >= 0 for rate in rates)
                and max(rates) <= Decimal(frozen["on_demand_rate_ceiling_usd"]),
                "CONDITION_SKILL_V9_PREFLIGHT_RATE_CEILING")

        vcpus = descriptions[0].get("VCpuInfo", {}).get("DefaultVCpus", 0)
        require(vcpus == 8, "CONDITION_SKILL_V9_PREFLIGHT_VCPU")
        quota = quotas.get_service_quota(ServiceCode="ec2", QuotaCode=VCPU_QUOTA_CODE)
        value = quota.get("Quota", {}).get("Value")
        require(type(value) in (int, float) and value >= vcpus,
                "CONDITION_SKILL_V9_PREFLIGHT_QUOTA")

        active = ec2.describe_instances(Filters=[
            {"Name": "tag-key", "Values": ["cas_meta_job"]},
            {"Name": "instance-state-name",
             "Values": ["pending", "running", "stopping", "shutting-down"]}])
        require(not active.get("NextToken"), "CONDITION_SKILL_V9_PREFLIGHT_PAGINATED_CONFLICTS")
        conflicting = [instance.get("InstanceId")
                       for reservation in active.get("Reservations", [])
                       for instance in reservation.get("Instances", [])]
        require(not conflicting, "CONDITION_SKILL_V9_PREFLIGHT_CONFLICTING_RESOURCES")

        return {"account": identity["Account"], "region": self.region,
                "ami": frozen["ami"], "instance_type": frozen["instance_type"],
                "instance_count": 1, "gpu_name_contains": frozen["gpu_name_contains"],
                "visible_gpu_count": visible_gpu_count, "t4_rejected": True,
                "rate_ceiling_usd": frozen["on_demand_rate_ceiling_usd"],
                "conflicting_resources": []}

    # ------------------------------------------------------------------ #
    # reservation (the only paid mutation before launch; exactly once)
    # ------------------------------------------------------------------ #
    def reserve(self, amount):
        """Two-phase reservation: canonical ledger append FIRST, AWS-side after.

        Phase 1 appends the campaign-ledger entry through ``aws.budget`` under
        its lock. It is the single source of truth and must precede any AWS-side
        step; it refuses a duplicate job id itself
        (JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY). Phase 2 records the
        reservation on the AWS side (on-demand: a receipt object in the job
        bucket, never an EC2 capacity reservation). If Phase 2 fails, the
        append-only history already recorded the attempt, so there is no refund
        and no retry: the failure is reported in the returned receipt. This
        method never delegates to another lifecycle entrypoint that owns its own
        reservation (e.g. launch_child_qualification_v8._run_authorized).
        """
        self.calls.append("reserve")
        self._event("budget_reservation", "REQUESTED", amount=amount)
        require(not self._reserved, "CONDITION_SKILL_V9_RESERVATION_ALREADY_ATTEMPTED")
        require(type(amount) is str and amount == plan.RESOURCE_PLAN["reservation_usd"],
                "CONDITION_SKILL_V9_RESERVATION_AMOUNT_FROZEN")
        # Phase 1: canonical ledger append (first, under aws/budget.py's lock).
        # This also refuses a job that already has a ledger reservation.
        receipt = self.budget.reserve_budget(self.job, self.source_sha, self.archive_sha256,
                                             amount, self.reservation_plan(), self.ledger_path)
        self._reserved = True
        # Phase 2: AWS-side reservation record, only after the append succeeded.
        # A failure here is reported, never refunded or retried.
        return {**receipt, "aws_side_reservation": self._record_aws_side_reservation(receipt)}

    def _bucket_name(self):
        return self.job + "-" + plan.RESOURCE_PLAN["account"]

    def _ensure_bucket(self, s3, tags=None):
        """Create and harden the job bucket; never memoize a half-hardened one."""
        tags = tags or [{"Key": "cas_meta_job", "Value": self.job}]
        bucket = self._bucket_name()
        if self._bucket_ready:
            return bucket
        if "bucket" not in self._resources:
            self._resources["bucket"] = bucket
            self._effect("create_bucket", s3.create_bucket, Bucket=bucket,
                         CreateBucketConfiguration={"LocationConstraint": plan.RESOURCE_PLAN["region"]})
        try:
            s3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": tags})
            s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={
                "BlockPublicAcls": True, "IgnorePublicAcls": True,
                "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
            s3.put_bucket_encryption(Bucket=bucket, ServerSideEncryptionConfiguration={
                "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]})
            # Failed collection keeps bounded cloud evidence instead of deleting
            # the only copy of a checkpoint. This does not authorize a new run.
            lifecycle = {"Rules": [{"ID": "bounded-job-evidence", "Status": "Enabled",
                "Filter": {"Prefix": ""}, "Expiration": {"Days": RESULT_RETENTION_DAYS},
                "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1}}]}
            s3.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration=lifecycle)
            observed = s3.get_bucket_lifecycle_configuration(Bucket=bucket)
            require(observed.get("Rules") == lifecycle["Rules"],
                    "CONDITION_SKILL_V9_RETENTION_READBACK")
        except Exception:
            # A half-hardened bucket must not be treated as ready: forget it so
            # later calls re-attempt hardening instead of silently skipping it.
            self._bucket_ready = False
            raise
        self._resources["bucket"] = bucket
        self._bucket_ready = True
        return bucket

    def _record_aws_side_reservation(self, receipt):
        """Persist the reservation receipt + ledger snapshot to the job bucket.

        This is the AWS-side reservation record, created strictly after the
        canonical ledger append. On-demand pilot: no EC2 capacity reservation
        is created. Any failure is returned as a status dict (never raised), so
        the append-only ledger entry is never refunded or retried.
        """
        s3 = self.clients.get("s3")
        if s3 is None:
            return {"status": "NOT_RECORDED", "reason": "NO_S3_CLIENT"}
        bucket = self._bucket_name()
        try:
            self._ensure_bucket(s3)
            s3.put_object(Bucket=bucket, Key="reservation/reservation_receipt.json",
                          Body=canonical(receipt))
            snapshot = budget.validate_state(budget.decoded(Path(self.ledger_path).read_bytes()))
            s3.put_object(Bucket=bucket, Key="reservation/ledger_snapshot.json",
                          Body=canonical(snapshot))
            return {"status": "RECORDED", "bucket": bucket,
                    "key": "reservation/reservation_receipt.json"}
        except Exception as error:  # noqa: BLE001 - report, never refund/retry
            return {"status": "FAILED", "bucket": bucket,
                    "failure": type(error).__name__ + ":" + str(error)[:2000]}

    # ------------------------------------------------------------------ #
    # launch
    # ------------------------------------------------------------------ #
    def _validate_permit(self, permit):
        require(type(permit) is dict, "CONDITION_SKILL_V9_PERMIT_REQUIRED")
        require(permit.get("job") == self.job
                and permit.get("source_sha") == self.source_sha
                and permit.get("archive_sha256") == self.archive_sha256
                and permit.get("manifest_sha256") == self.manifest_sha256
                and permit.get("dataset_manifest_sha256") == self.dataset_manifest_sha256,
                "CONDITION_SKILL_V9_PERMIT_IDENTITY_MISMATCH")
        reservation = permit.get("reservation")
        require(type(reservation) is dict
                and reservation.get("reservation", {}).get("job") == self.job
                and reservation.get("reservation", {}).get("status") == budget.STATUS,
                "CONDITION_SKILL_V9_PERMIT_RESERVATION_MISMATCH")
        require(permit.get("resource_plan") == plan.RESOURCE_PLAN,
                "CONDITION_SKILL_V9_PERMIT_RESOURCE_PLAN_MISMATCH")
        self.launch_module.validate_preflight(permit.get("preflight"))

    def _source_bytes(self):
        if self.source_archive is None:
            raw = _locate_source_archive(self.archive_sha256).read_bytes()
        elif isinstance(self.source_archive, (bytes, bytearray, memoryview)):
            raw = bytes(self.source_archive)
        else:
            raw = Path(self.source_archive).read_bytes()
        require(digest(raw) == self.archive_sha256, "CONDITION_SKILL_V9_SOURCE_ARCHIVE_HASH_MISMATCH")
        return raw

    def _render_remote(self, permit):
        """Render a self-contained remote driver script with the bound config.

        The driver extracts the package, creates (or discovers) the isolated task
        venv at ``WORKER_ROOT/venv``, installs the frozen torch cu128 build, the
        two frozen trainer wheels, and the pinned requirements (each fail-closed),
        then runs ``aws.condition_skill_v9_remote.orchestrate`` with the venv
        Python. Afterwards it packages the allowlisted trainer evidence into
        ``results/artifacts.zip`` and uploads ``results/complete.json`` with the
        real artifact sha256/bytes so ``wait()``/``collect()`` can verify the run.
        The driver imports only stdlib until after the install step; boto3 is
        imported only for the final S3 uploads (instance-role creds via IMDSv2).
        """
        config = {"schema": REMOTE_CONFIG_SCHEMA, "job": self.job,
                  "bucket": self._resources["bucket"], "region": self.region,
                  "account_id": plan.RESOURCE_PLAN["account"],
                  "source_sha": self.source_sha, "archive_sha256": self.archive_sha256,
                  "manifest_sha256": self.manifest_sha256,
                  "dataset_manifest_sha256": self.dataset_manifest_sha256,
                  "resource_plan": plan.RESOURCE_PLAN}
        driver_lines = [
            "CONFIG = " + repr(config),
            "import hashlib",
            "import json",
            "import os",
            "import shutil",
            "import subprocess",
            "import sys",
            "import zipfile",
            "import time",
            "from pathlib import Path",
            "ROOT = Path('/opt/cas-meta2-condition-skill-v9')",
            "# The release is deliberately absent from CONFIG and the source package.",
            "release = json.loads((ROOT / 'permit.json').read_bytes())",
            "for key in ('job', 'source_sha', 'archive_sha256', 'manifest_sha256', 'dataset_manifest_sha256'):",
            "    if release.get(key) != CONFIG[key]: raise ValueError('WORKER_RELEASE_IDENTITY')",
            "gate = release.get('worker_release', {})",
            "if gate.get('schedule_confirmed') is not True or not gate.get('instance_id'):",
            "    raise ValueError('WORKER_RELEASE_REQUIRES_CONFIRMED_SCHEDULE')",
            "if gate.get('deadline_epoch', 0) - time.time() < 900:",
            "    raise ValueError('WORKER_RELEASE_DEADLINE_TOO_CLOSE')",
            "pkg = ROOT / 'package'",
            "bootstrap = ROOT / 'bootstrap'",
            "bootstrap.mkdir()",
            "with zipfile.ZipFile(ROOT / 'source.zip') as z:",
            "    if len(z.infolist()) > 4096: raise ValueError('BOOTSTRAP_MEMBER_BOUND')",
            "    for member in z.infolist():",
            "        parts = member.filename.split('/')",
            "        if member.is_dir() or any(p in ('', '.', '..') for p in parts) or ':' in member.filename or '\\\\' in member.filename:",
            "            raise ValueError('BOOTSTRAP_MEMBER_PATH')",
            "    z.extractall(bootstrap)",
            "pilot = pkg / 'research/CAS_META_2_COMPOSITION'",
            "sys.path.insert(0, str(bootstrap / 'research/CAS_META_2_COMPOSITION'))",
            "out = pilot / 'runs' / CONFIG['job']",
            "data = pilot / 'records/condition_skill_v9_001/dataset_001'",
            "evidence = out.parent / (out.name + '.evidence')",
            "# Frozen CUDA 12.8 index, mirrored from aws/launch.py launch_plan.json",
            "# torch_index_url; the same pin used by every v8 remote install.",
            "TORCH_INDEX = 'https://download.pytorch.org/whl/cu128'",
            "WHEEL_DIR = 'research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist'",
            "WHEELS = [bootstrap / WHEEL_DIR / 'casformer_reference-0.1.0-py3-none-any.whl',",
            "          bootstrap / WHEEL_DIR / 'cas_neural_cjt-0.2.0-py3-none-any.whl']",
            "REQUIREMENTS = bootstrap / 'research/CAS_META_2_COMPOSITION/requirements-gpu.txt'",
            "",
            "def run_checked(argv):",
            "    subprocess.run(argv, check=True)",
            "",
            "orchestrate = None",
            "allowed_trainer_output = None",
            "failure = None",
            "receipt = None",
            "python = os.environ.get('CAS_META2_VENV_PYTHON')",
            "try:",
            "    from aws.condition_skill_v9_remote import orchestrate, allowed_trainer_output",
            "    if not python:",
            "        venv = ROOT / 'venv'",
            "        venv_py = venv / 'bin' / 'python'",
            "        if not venv_py.exists():",
            "            base = next((c for c in ('python3.12', 'python3.11', 'python3') if shutil.which(c)), None)",
            "            if base is None:",
            "                raise SystemExit('SUPPORTED_PYTHON_REQUIRED')",
            "            run_checked([base, '-m', 'venv', str(venv)])",
            "        python = str(venv_py)",
            "    run_checked([python, '-m', 'pip', 'install', '--disable-pip-version-check',",
            "                 'torch==2.11.0', '--index-url', TORCH_INDEX,",
            "                 '--report', str(ROOT / 'torch_install.json')])",
            "    run_checked([python, '-m', 'pip', 'install', '--disable-pip-version-check',",
            "                 '--no-deps', str(WHEELS[0]), str(WHEELS[1]),",
            "                 '--report', str(ROOT / 'wheel_install.json')])",
            "    # requirements-gpu.txt pins numpy/jsonschema/pytest and carries no torch pin",
            "    # (torch is installed above from the cu128 index), so it is installed verbatim.",
            "    run_checked([python, '-m', 'pip', 'install', '--disable-pip-version-check',",
            "                 '-r', str(REQUIREMENTS),",
            "                 '--report', str(ROOT / 'dependency_install.json')])",
            "    if gate['deadline_epoch'] - time.time() < 900:",
            "        raise ValueError('WORKER_RELEASE_DEADLINE_TOO_CLOSE_AFTER_INSTALL')",
            "    receipt = orchestrate(str(ROOT / 'source.zip'), str(pkg), str(out), str(data),",
            "        CONFIG['job'], expected_sha256=CONFIG['archive_sha256'],",
            "        expected_source_sha=CONFIG['source_sha'],",
            "        expected_manifest_sha256=CONFIG['manifest_sha256'],",
            "        python_executable=python, timeout=600)",
            "except BaseException as error:",
            "    failure = {'type': type(error).__name__, 'message': str(error)[:2000]}",
            "",
            "def make_artifacts():",
            "    names = []",
            "    seen = set()",
            "    for directory in (evidence, out):",
            "        if not directory.is_dir():",
            "            continue",
            "        for name in sorted(os.listdir(str(directory))):",
            "            path = directory / name",
            "            if not path.is_file():",
            "                continue",
            "            if allowed_trainer_output is not None and not allowed_trainer_output(name):",
            "                continue",
            "            if name in seen:",
            "                continue",
            "            seen.add(name)",
            "            names.append((name, path))",
            "    target = ROOT / 'artifacts.zip'",
            "    with zipfile.ZipFile(str(target), 'w', compression=zipfile.ZIP_DEFLATED) as zf:",
            "        for name, path in names:",
            "            zf.write(str(path), arcname=name)",
            "    return target.read_bytes()",
            "",
            "status = 'REMOTE_FAILED' if failure is not None else receipt.get('status', 'REMOTE_FAILED')",
            "artifacts = make_artifacts()",
            "artifact_sha = hashlib.sha256(artifacts).hexdigest()",
            "artifact_bytes = len(artifacts)",
            "import boto3",
            "s3 = boto3.client('s3', region_name=CONFIG['region'])",
            "s3.put_object(Bucket=CONFIG['bucket'], Key='results/artifacts.zip', Body=artifacts)",
            "complete = {'job': CONFIG['job'], 'status': status,",
            "            'sha256': artifact_sha, 'bytes': artifact_bytes,",
            "            'experiment': CONFIG['resource_plan']['experiment'],",
            "            'returncode': 0 if status == 'REMOTE_FINISHED' else 1}",
            "if failure is not None:",
            "    complete['failure'] = failure",
            "s3.put_object(Bucket=CONFIG['bucket'], Key='results/complete.json',",
            "              Body=json.dumps(complete))",
        ]
        return "\n".join(driver_lines)

    def _user_data(self, bucket, remote_sha256):
        frozen = plan.RESOURCE_PLAN
        text = "\n".join([
            "#!/bin/bash", "set -eu", "umask 077",
            "export PYTHONDONTWRITEBYTECODE=1 AWS_MAX_ATTEMPTS=1 AWS_PAGER=''",
            "export CAS_META2_GUEST_DEADLINE_EPOCH=$(( $(date +%s) + "
            + str(frozen["guest_shutdown_seconds"]) + " ))",
            "( sleep " + str(frozen["guest_shutdown_seconds"])
            + "; shutdown -h now ) >/dev/null 2>&1 &",
            "mkdir -p " + WORKER_ROOT,
            "exec > " + WORKER_ROOT + "/bootstrap.log 2>&1",
            "command -v aws >/dev/null || { echo AWS_CLI_REQUIRED; exit 1; }",
            "timeout 120 aws s3api get-object --bucket " + bucket
            + " --key input/source.zip " + WORKER_ROOT + "/source.zip --region "
            + frozen["region"],
            "echo '" + self.archive_sha256 + "  " + WORKER_ROOT
            + "/source.zip' | sha256sum -c -",
            "timeout 120 aws s3api get-object --bucket " + bucket
            + " --key input/remote.py " + WORKER_ROOT + "/remote.py --region "
            + frozen["region"],
            "echo '" + remote_sha256 + "  " + WORKER_ROOT
            + "/remote.py' | sha256sum -c -",
            "RELEASE_DEADLINE=$(( $(date +%s) + 180 ))",
            "until timeout 10 aws s3api get-object --bucket " + bucket
            + " --key input/permit.json " + WORKER_ROOT + "/permit.json --region "
            + frozen["region"] + "; do",
            "  test $(date +%s) -lt $RELEASE_DEADLINE || { echo WORKER_RELEASE_TIMEOUT; exit 1; }",
            "  sleep 2",
            "done",
            "PY=''",
            "for p in python3.12 python3.11 python3; do",
            "  if command -v \"$p\" >/dev/null 2>&1; then PY=\"$p\"; break; fi",
            "done",
            "test -n \"$PY\" || { echo SUPPORTED_PYTHON_REQUIRED; exit 1; }",
            "\"$PY\" -B " + WORKER_ROOT + "/remote.py",
            "",
        ])
        require(len(text.encode("utf-8")) <= 16384, "CONDITION_SKILL_V9_USER_DATA_BOUND")
        return text

    def _default_network(self, ec2):
        vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}]
                                 ).get("Vpcs", [])
        require(len(vpcs) == 1, "CONDITION_SKILL_V9_DEFAULT_VPC_REQUIRED")
        vpc_id = vpcs[0]["VpcId"]
        subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]},
                                                {"Name": "default-for-az", "Values": ["true"]}]
                                       ).get("Subnets", [])
        require(subnets, "CONDITION_SKILL_V9_DEFAULT_SUBNET_REQUIRED")
        return vpc_id, subnets[0]["SubnetId"]

    def launch(self, job, permit):
        self.calls.append("launch")
        require(job == self.job, "CONDITION_SKILL_V9_LAUNCH_JOB_MISMATCH")
        require(self._reserved, "CONDITION_SKILL_V9_LAUNCH_REQUIRES_RESERVATION")
        require(not self._launch_called, "CONDITION_SKILL_V9_SINGLE_LAUNCH_ONLY")
        self._validate_permit(permit)
        self._launch_called = True
        frozen = plan.RESOURCE_PLAN
        ec2, s3, iam, scheduler = (self.clients[name] for name in
                                   ("ec2", "s3", "iam", "scheduler"))
        bucket = self.job + "-" + frozen["account"]
        tags = [{"Key": "cas_meta_job", "Value": self.job}]
        worker_role = self.job + "-worker"
        timer_role = self.job + "-timer"

        raw = self._source_bytes()
        require(0 < len(raw) <= 24 * 1024**2, "CONDITION_SKILL_V9_SOURCE_ARCHIVE_BOUND")
        self._source_copy = self.launch_module.write_evidence(self._evidence / "source.zip", raw)
        self._event("source_archive_copy", "DURABLE_VERIFIED", archive=self._source_copy)

        self._ensure_bucket(s3, tags)
        self._effect("upload_source", s3.put_object, Bucket=bucket, Key="input/source.zip", Body=raw)
        remote = self._render_remote(permit).encode("utf-8")
        self._effect("upload_bootstrap", s3.put_object, Bucket=bucket, Key="input/remote.py", Body=remote)

        def create_role(name, service, statements):
            trust = {"Version": "2012-10-17", "Statement": [
                {"Effect": "Allow", "Principal": {"Service": service},
                 "Action": "sts:AssumeRole"}]}
            self._resources[name.rsplit("-", 1)[-1] + "_role"] = name
            response = self._effect("create_role", iam.create_role, RoleName=name,
                                   AssumeRolePolicyDocument=json.dumps(trust), Tags=tags)
            arn = response.get("Role", {}).get("Arn")
            require(arn == "arn:aws:iam::" + frozen["account"] + ":role/" + name,
                    "CONDITION_SKILL_V9_ROLE_ARN")
            self._effect("put_role_policy", iam.put_role_policy, RoleName=name, PolicyName="job-only",
                                PolicyDocument=json.dumps({"Version": "2012-10-17",
                                                           "Statement": statements}))
            return arn

        worker_arn = create_role(worker_role, "ec2.amazonaws.com", [
            {"Effect": "Allow", "Action": ["s3:GetObject"],
             "Resource": ["arn:aws:s3:::" + bucket + "/input/source.zip",
                          "arn:aws:s3:::" + bucket + "/input/remote.py",
                          "arn:aws:s3:::" + bucket + "/input/permit.json"]},
            {"Effect": "Allow", "Action": ["s3:PutObject"],
             "Resource": ["arn:aws:s3:::" + bucket + "/results/*"]}])
        self._resources["instance_profile"] = worker_role
        profile = self._effect("create_instance_profile", iam.create_instance_profile,
                               InstanceProfileName=worker_role, Tags=tags)["InstanceProfile"]
        profile_arn = profile.get("Arn")
        require(profile_arn == "arn:aws:iam::" + frozen["account"] + ":instance-profile/" + worker_role,
                "CONDITION_SKILL_V9_PROFILE_ARN")
        self._effect("add_role_to_instance_profile", iam.add_role_to_instance_profile,
                     InstanceProfileName=worker_role,
                                         RoleName=worker_role)
        timer_arn = create_role(timer_role, "scheduler.amazonaws.com", [
            {"Effect": "Allow", "Action": "ec2:TerminateInstances",
             "Resource": "arn:aws:ec2:" + frozen["region"] + ":" + frozen["account"]
             + ":instance/*",
             "Condition": {"StringEquals": {"ec2:ResourceTag/cas_meta_job": self.job}}}])
        iam_readback = self._wait_for_iam(worker_role, timer_role, worker_arn, timer_arn, profile_arn)

        _, subnet_id = self._default_network(ec2)
        group = self._effect("create_security_group", ec2.create_security_group, GroupName=self.job,
                                       Description="CAS condition-skill v9 outbound HTTPS only",
                                       VpcId=ec2.describe_vpcs(Filters=[
                                           {"Name": "isDefault", "Values": ["true"]}]
                                       )["Vpcs"][0]["VpcId"],
                                       TagSpecifications=[{"ResourceType": "security-group",
                                                           "Tags": tags}])
        sg = group["GroupId"]
        self._resources["security_group"] = sg
        self._effect("revoke_security_group_egress", ec2.revoke_security_group_egress, GroupId=sg, IpPermissions=[
            {"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        self._effect("authorize_security_group_egress", ec2.authorize_security_group_egress, GroupId=sg, IpPermissions=[
            {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,
             "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        self._resources["security_group"] = sg

        bootstrap = self._user_data(bucket, digest(remote))
        self._launch_attempted = True
        self._run_state = "REQUESTED_UNKNOWN"
        launch_started = datetime.now(timezone.utc)
        try:
            launched = self._effect("run_instances", ec2.run_instances,
            ImageId=frozen["ami"], InstanceType=frozen["instance_type"],
            MinCount=1, MaxCount=1, ClientToken=self.job,
            IamInstanceProfile={"Arn": profile_arn},
            InstanceInitiatedShutdownBehavior="terminate",
            MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"},
            NetworkInterfaces=[{"DeviceIndex": 0, "SubnetId": subnet_id, "Groups": [sg],
                                "AssociatePublicIpAddress": True,
                                "DeleteOnTermination": True}],
            BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {
                "VolumeSize": frozen["ebs"]["size_gib"], "VolumeType": "gp3",
                "Iops": frozen["ebs"]["iops"],
                "Throughput": frozen["ebs"]["throughput_mib_s"],
                "Encrypted": True, "DeleteOnTermination": True}}],
            TagSpecifications=[{"ResourceType": "instance", "Tags": tags},
                               {"ResourceType": "volume", "Tags": tags}],
            UserData=bootstrap)
        except BaseException as error:
            if self._error_code(error) in ("InvalidParameterValue", "InvalidParameterCombination",
                    "UnauthorizedOperation", "AuthFailure", "InsufficientInstanceCapacity",
                    "InstanceLimitExceeded", "Unsupported"):
                self._run_state = "REJECTED"
            # Never issue RunInstances again, including after transport timeout.
            # Discovery is read-only and keeps an unresolved response explicit.
            try:
                self._discover_instances()
            except Exception as recovery_error:
                self._event("instance_recovery", "FAILED", error=str(recovery_error)[:2000])
            raise
        require(len(launched.get("Instances", [])) == 1,
                "CONDITION_SKILL_V9_ONE_INSTANCE_RESPONSE_REQUIRED")
        self._instance_id = launched["Instances"][0]["InstanceId"]
        require(type(self._instance_id) is str and bool(INSTANCE_ID.fullmatch(self._instance_id)),
                "CONDITION_SKILL_V9_REAL_INSTANCE_ID_REQUIRED")
        self._resources["instance"] = self._instance_id
        self._instance_ids = [self._instance_id]
        self._run_state = "INSTANCE_OBSERVED"
        self._event("instance_identity", "OBSERVED", instance_id=self._instance_id,
                    client_token=self.job)

        cloud_deadline = launch_started + timedelta(
            seconds=frozen["cloud_schedule_seconds"])
        target = {"Arn": "arn:aws:scheduler:::aws-sdk:ec2:terminateInstances",
                  "RoleArn": timer_arn,
                  "Input": json.dumps({"InstanceIds": [self._instance_id]}),
                  "RetryPolicy": {"MaximumRetryAttempts": 0,
                                  "MaximumEventAgeInSeconds": 60}}
        expression = "at(" + cloud_deadline.strftime("%Y-%m-%dT%H:%M:%S") + ")"
        self._resources["schedule"] = self.job
        self._effect("create_schedule", scheduler.create_schedule,
                                  Name=self.job, ScheduleExpression=expression,
                                  ScheduleExpressionTimezone="UTC",
                                  FlexibleTimeWindow={"Mode": "OFF"}, Target=target,
                                  ActionAfterCompletion="DELETE")
        response = scheduler.get_schedule(Name=self.job)
        observed = {key: response.get(key) for key in ("Arn", "State", "Target",
            "ScheduleExpression", "ScheduleExpressionTimezone", "FlexibleTimeWindow", "ActionAfterCompletion")}
        require(observed.get("Arn") == "arn:aws:scheduler:" + self.region + ":" + frozen["account"]
                + ":schedule/default/" + self.job
                and observed.get("State") == "ENABLED" and observed.get("Target") == target
                and observed.get("ScheduleExpression") == expression
                and observed.get("ScheduleExpressionTimezone") == "UTC"
                and observed.get("FlexibleTimeWindow") == {"Mode": "OFF"}
                and observed.get("ActionAfterCompletion") == "DELETE",
                "CONDITION_SKILL_V9_SCHEDULE_READBACK")
        self._event("shutdown_schedule", "CONFIRMED", schedule=observed)
        released = {**permit, "worker_release": {"instance_id": self._instance_id,
                    "schedule_confirmed": True, "schedule_arn": observed.get("Arn"),
                    "schedule_sha256": digest(canonical(observed)),
                    "deadline_epoch": int(cloud_deadline.timestamp())}}
        self._effect("release_worker", s3.put_object, Bucket=bucket,
                     Key="input/permit.json", Body=canonical(released))

        return {"job": self.job, "instance_id": self._instance_id,
                "client_token": self.job, "imdsv2_required": True,
                "permit": released, "iam_readback": iam_readback,
                "shutdown_schedule": observed, "bucket": bucket, "launch_attempted": True,
                "automatic_retries": 0,
                "identity_note": ("Launch-side receipt records the observed InstanceId "
                                  "and ClientToken=job with IMDSv2 HttpTokens=required; "
                                  "in-guest identity is not independently proven here.")}

    # ------------------------------------------------------------------ #
    # wait / collect
    # ------------------------------------------------------------------ #
    def _read_body(self, body, maximum):
        total = 0
        blocks = []
        while True:
            block = body.read(min(1024**2, maximum - total + 1))
            if not block:
                break
            total += len(block)
            require(total <= maximum, "CONDITION_SKILL_V9_S3_BODY_BOUND")
            blocks.append(block)
        return b"".join(blocks)

    def wait(self, job, timeout, *, poll_interval=5.0):
        self.calls.append("wait")
        require(job == self.job, "CONDITION_SKILL_V9_WAIT_JOB_MISMATCH")
        require(self._instance_id is not None, "CONDITION_SKILL_V9_WAIT_REQUIRES_LAUNCH")
        require(type(timeout) in (int, float) and 0 < timeout
                <= plan.RESOURCE_PLAN["instance_seconds_max"],
                "CONDITION_SKILL_V9_WAIT_TIMEOUT_BOUND")
        ec2, s3 = self.clients["ec2"], self.clients["s3"]
        bucket = self._resources["bucket"]
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                response = s3.get_object(Bucket=bucket, Key="results/complete.json")
                raw = self._read_body(response["Body"], 1024**2)
                result = json.loads(raw)
                require(result.get("job") == self.job,
                        "CONDITION_SKILL_V9_RESULT_IDENTITY")
                require(type(result.get("status")) is str and result["status"] in
                        ("REMOTE_FINISHED", "REMOTE_FAILED"),
                        "CONDITION_SKILL_V9_RESULT_STATUS")
                self._result = result
                self._result_raw = raw
                return {"worker_status": result["status"]}
            except self._client_error as error:
                code = getattr(error, "response", {}).get("Error", {}).get("Code")
                if code not in ("NoSuchKey", "404"):
                    raise
            current = ec2.describe_instances(InstanceIds=[self._instance_id]
                                             )["Reservations"][0]["Instances"][0]
            state = current.get("State", {}).get("Name")
            if state in ("terminated", "shutting-down"):
                return {"worker_status": "REMOTE_FAILED", "instance_state": state}
            time.sleep(poll_interval)
        return {"worker_status": "REMOTE_TIMED_OUT"}

    def collect(self, job):
        self.calls.append("collect")
        require(job == self.job, "CONDITION_SKILL_V9_COLLECT_JOB_MISMATCH")
        require(self._instance_id is not None, "CONDITION_SKILL_V9_COLLECT_REQUIRES_LAUNCH")
        s3 = self.clients["s3"]
        bucket = self._resources["bucket"]
        result = self._result
        require(result is not None, "CONDITION_SKILL_V9_COLLECT_REQUIRES_RESULT")
        require(type(result.get("sha256")) is str and bool(HEX64.fullmatch(result["sha256"])),
                "CONDITION_SKILL_V9_RESULT_ARTIFACT_SHA")
        require(type(result.get("bytes")) is int and 0 < result["bytes"] <= 256 * 1024**2,
                "CONDITION_SKILL_V9_RESULT_ARTIFACT_BYTES")
        head = s3.head_object(Bucket=bucket, Key="results/artifacts.zip")
        require(head.get("ContentLength") == result["bytes"],
                "CONDITION_SKILL_V9_RESULT_SIZE_MISMATCH")
        response = s3.get_object(Bucket=bucket, Key="results/artifacts.zip")
        raw = self._read_body(response["Body"], result["bytes"])
        require(digest(raw) == result["sha256"], "CONDITION_SKILL_V9_ARTIFACT_HASH_MISMATCH")
        archive = self.launch_module.write_evidence(self._evidence / "cloud_artifacts.zip", raw)
        completion = self.launch_module.write_evidence(self._evidence / "cloud_complete.json",
                                self._result_raw if self._result_raw is not None else canonical(result))
        self._event("cloud_artifact_copy", "DURABLE_VERIFIED", archive=archive, completion=completion)
        self._durable_files = {"cloud_artifacts.zip": archive, "cloud_complete.json": completion}
        self._durable_results = True
        return {"archive": archive, "completion": completion, "files": _parse_artifacts(raw)}

    # ------------------------------------------------------------------ #
    # cleanup (call-safe; records every failure)
    # ------------------------------------------------------------------ #
    def cleanup(self, job):
        """Record observations; retain uncollected results under seven-day expiry.

        A missing local instance id is not proof an instance was terminated.
        Ambiguous RunInstances responses are discovered by stable token and tag,
        never by issuing another launch. Unknown compute keeps its shutdown
        schedule and supporting roles instead of dismantling its only backstop.
        """
        self.calls.append("cleanup")
        require(job == self.job, "CONDITION_SKILL_V9_CLEANUP_JOB_MISMATCH")
        failures, status = [], {"instance_ids": [], "instances": {}}
        ec2, s3, iam, scheduler = (self.clients.get(name) for name in ("ec2", "s3", "iam", "scheduler"))

        def failed(label, error):
            failures.append(label + ":" + type(error).__name__ + ":" + str(error)[:1500])

        def observe(label, callback, absent):
            try:
                value = callback()
                return value, False
            except self._client_error as error:
                if self._error_code(error) in absent:
                    return None, True
                raise

        def confirm_absent(label, callback, absent, empty=lambda value: False):
            for attempt in range(16):
                value, missing = observe(label, callback, absent)
                if missing or empty(value):
                    return "CONFIRMED_ABSENT"
                if attempt != 15:
                    time.sleep(OBSERVATION_DELAY_SECONDS)
            raise ValueError(label + "_ABSENCE_UNCONFIRMED")

        try:
            self._event("cleanup", "REQUESTED", launch_state=self._run_state)
        except Exception as error:
            failed("CLEANUP_JOURNAL_FAILED", error)
        if self._launch_attempted and not self._instance_ids:
            try:
                self._discover_instances()
            except Exception as error:
                failed("INSTANCE_DISCOVERY_FAILED", error)
        status["instance_ids"] = list(self._instance_ids)
        compute_closed = not self._instance_ids and self._run_state in ("NOT_ATTEMPTED", "REJECTED")
        if compute_closed:
            status["instance_state"] = "NOT_CREATED" if not self._launch_attempted else "REJECTED_NO_INSTANCE_OBSERVED"
        elif not self._instance_ids:
            status["instance_state"] = "UNKNOWN"
            failures.append("AMBIGUOUS_RUN_INSTANCES_UNRESOLVED")
        for instance_id in self._instance_ids:
            try:
                current = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
                require(current.get("ClientToken") == self.job and
                        {t["Key"]: t["Value"] for t in current.get("Tags", [])}.get("cas_meta_job") == self.job,
                        "CONDITION_SKILL_V9_CLEANUP_INSTANCE_IDENTITY")
                if current.get("State", {}).get("Name") != "terminated":
                    ec2.terminate_instances(InstanceIds=[instance_id])
                confirmed = False
                for attempt in range(60):
                    current = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
                    if current.get("State", {}).get("Name") == "terminated":
                        confirmed = True
                        break
                    time.sleep(OBSERVATION_DELAY_SECONDS)
                require(confirmed, "INSTANCE_TERMINATION_UNCONFIRMED")
                status["instances"][instance_id] = "CONFIRMED_TERMINATED"
            except Exception as error:
                failed("INSTANCE_TERMINATION_FAILED", error)
                status["instances"][instance_id] = "UNKNOWN"
        if self._instance_ids:
            compute_closed = all(value == "CONFIRMED_TERMINATED" for value in status["instances"].values())
            status["instance_state"] = "CONFIRMED_TERMINATED" if compute_closed else "UNKNOWN"
        status["instance_terminated"] = bool(self._instance_ids) and compute_closed
        status["instance_termination_confirmed"] = status["instance_terminated"]
        status["compute_closed"] = compute_closed

        try:
            require(compute_closed, "COMPUTE_STILL_UNRESOLVED")
            status["volume_state"] = confirm_absent("VOLUMES",
                lambda: ec2.describe_volumes(Filters=[{"Name": "tag:cas_meta_job", "Values": [self.job]}]),
                (), empty=lambda value: value.get("Volumes") == [] and not value.get("NextToken"))
        except Exception as error:
            failed("VOLUME_DELETION_UNCONFIRMED", error)
            status["volume_state"] = "UNKNOWN"
        # This boolean means observed absent, not inferred from an instance flag.
        status["volumes_deleted"] = status["volume_state"] == "CONFIRMED_ABSENT"

        if compute_closed:
            try:
                _, missing = observe("schedule", lambda: scheduler.get_schedule(Name=self.job),
                                     ("ResourceNotFoundException",))
                if not missing:
                    scheduler.delete_schedule(Name=self.job)
                status["schedule_state"] = confirm_absent("SCHEDULE",
                    lambda: scheduler.get_schedule(Name=self.job), ("ResourceNotFoundException",))
            except Exception as error:
                failed("SCHEDULE_REMOVAL_FAILED", error)
                status["schedule_state"] = "UNKNOWN"
        else:
            status["schedule_state"] = "RETAINED_FOR_UNKNOWN_COMPUTE"
        status["schedule_removed"] = status["schedule_state"] == "CONFIRMED_ABSENT"

        # Roles and the profile are named before their create request, so partial
        # setup is discoverable even when the create response was lost.
        status["iam_resources"] = {}
        if compute_closed:
            profile_name = self.job + "-worker"
            try:
                profile, missing = observe("profile",
                    lambda: iam.get_instance_profile(InstanceProfileName=profile_name), ("NoSuchEntity",))
                if not missing:
                    roles = profile["InstanceProfile"].get("Roles", [])
                    require(all(role.get("RoleName") == profile_name for role in roles),
                            "UNEXPECTED_PROFILE_ROLE")
                    for role in roles:
                        iam.remove_role_from_instance_profile(InstanceProfileName=profile_name,
                                                             RoleName=role["RoleName"])
                    iam.delete_instance_profile(InstanceProfileName=profile_name)
                status["iam_resources"][profile_name + "/profile"] = confirm_absent("PROFILE",
                    lambda: iam.get_instance_profile(InstanceProfileName=profile_name), ("NoSuchEntity",))
            except Exception as error:
                failed("INSTANCE_PROFILE_REMOVAL_FAILED", error)
                status["iam_resources"][profile_name + "/profile"] = "UNKNOWN"
            for role_name in (self.job + "-worker", self.job + "-timer"):
                try:
                    _, missing = observe("role", lambda: iam.get_role(RoleName=role_name), ("NoSuchEntity",))
                    if not missing:
                        observe("role_policy", lambda: iam.delete_role_policy(
                            RoleName=role_name, PolicyName="job-only"), ("NoSuchEntity",))
                        iam.delete_role(RoleName=role_name)
                    status["iam_resources"][role_name] = confirm_absent("ROLE",
                        lambda: iam.get_role(RoleName=role_name), ("NoSuchEntity",))
                except Exception as error:
                    failed("ROLE_REMOVAL_FAILED", error)
                    status["iam_resources"][role_name] = "UNKNOWN"
        else:
            status["iam_resources"]["state"] = "RETAINED_FOR_UNKNOWN_COMPUTE"
        status["roles_removed"] = bool(status["iam_resources"]) and all(
            value == "CONFIRMED_ABSENT" for value in status["iam_resources"].values())

        group = self._resources.get("security_group")
        try:
            require(compute_closed, "COMPUTE_STILL_UNRESOLVED")
            groups = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [self.job]}])
            require(not groups.get("NextToken"), "SECURITY_GROUP_OBSERVATION_TRUNCATED")
            for candidate in groups.get("SecurityGroups", []):
                require(candidate.get("GroupName") == self.job and
                        {t["Key"]: t["Value"] for t in candidate.get("Tags", [])}.get("cas_meta_job") == self.job,
                        "SECURITY_GROUP_OWNERSHIP")
                ec2.delete_security_group(GroupId=candidate["GroupId"])
            status["security_group_state"] = confirm_absent("SECURITY_GROUP",
                lambda: ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [self.job]}]),
                ("InvalidGroup.NotFound", "InvalidSecurityGroupID.NotFound"),
                empty=lambda value: value.get("SecurityGroups") == [] and not value.get("NextToken"))
        except Exception as error:
            failed("SECURITY_GROUP_DELETION_FAILED", error)
            status["security_group_state"] = "UNKNOWN"
        status["security_group_deleted"] = status["security_group_state"] == "CONFIRMED_ABSENT"

        bucket = self._resources.get("bucket")
        status["results_deleted"] = False
        status["bucket_deleted"] = False
        status["inputs_deleted"] = False
        if bucket is None:
            status["bucket_state"] = "NOT_CREATED"
        else:
            try:
                listing, missing = observe("bucket", lambda: s3.list_objects_v2(Bucket=bucket),
                                           ("NoSuchBucket", "404"))
                if missing:
                    status["bucket_state"] = "CONFIRMED_ABSENT"
                    status["inputs_deleted"] = True
                else:
                    require(not listing.get("IsTruncated") and not listing.get("NextContinuationToken"),
                            "BUCKET_CONTENTS_TRUNCATED")
                    keys = [item["Key"] for item in listing.get("Contents", [])]
                    require(len(keys) <= 100, "BUCKET_CONTENTS_BOUND")
                    if "input/source.zip" in keys:
                        require(self._source_copy is not None, "LOCAL_SOURCE_COPY_REQUIRED")
                        source_path = self.launch_module.evidence_directory(self._source_copy["path"])
                        require(source_path.stat().st_nlink == 1 and
                                digest(source_path.read_bytes()) == self._source_copy["sha256"],
                                "LOCAL_SOURCE_CHANGED_BEFORE_CLOUD_DELETE")
                    disposable = [key for key in keys if key.startswith(("input/", "reservation/"))]
                    # Recheck local copies immediately before deleting any result.
                    if self._durable_results:
                        for filename in ("cloud_artifacts.zip", "cloud_complete.json"):
                            expected = self._durable_files[filename]
                            path = self.launch_module.evidence_directory(expected["path"])
                            require(path.stat().st_nlink == 1 and path.stat().st_size == expected["bytes"]
                                    and digest(path.read_bytes()) == expected["sha256"],
                                    "LOCAL_EVIDENCE_CHANGED_BEFORE_CLOUD_DELETE")
                        disposable += [key for key in keys if key in ("results/artifacts.zip", "results/complete.json")]
                    if disposable:
                        deleted = s3.delete_objects(Bucket=bucket, Delete={"Objects": [
                            {"Key": key} for key in disposable]})
                        require(not deleted.get("Errors"), "S3_PARTIAL_DELETION_FAILED")
                    status["inputs_deleted"] = True
                    status["results_deleted"] = self._durable_results and any(
                        key.startswith("results/") for key in disposable)
                    remaining = s3.list_objects_v2(Bucket=bucket)
                    require(not remaining.get("IsTruncated"), "BUCKET_RECHECK_TRUNCATED")
                    if not remaining.get("Contents") and compute_closed:
                        s3.delete_bucket(Bucket=bucket)
                        confirm_absent("BUCKET", lambda: s3.list_objects_v2(Bucket=bucket), ("NoSuchBucket", "404"))
                        status["bucket_deleted"] = True
                        status["bucket_state"] = "CONFIRMED_ABSENT"
                    else:
                        policy = s3.get_bucket_lifecycle_configuration(Bucket=bucket)
                        require(any(rule.get("Status") == "Enabled" and rule.get("Filter") == {"Prefix": ""}
                                    and rule.get("Expiration") == {"Days": RESULT_RETENTION_DAYS}
                                    for rule in policy.get("Rules", [])), "RESULT_RETENTION_UNCONFIRMED")
                        status["bucket_state"] = "RETAINED_BOUNDED_EVIDENCE"
                        status["retained_bucket"] = bucket
                        status["retention_days"] = RESULT_RETENTION_DAYS
                        status["retained_keys"] = [item["Key"] for item in remaining.get("Contents", [])]
            except Exception as error:
                failed("EVIDENCE_CLEANUP_FAILED", error)
                status["bucket_state"] = "UNKNOWN_PRESERVED"
        status["complete"] = not failures and compute_closed
        status["failures"] = failures
        try:
            self._event("cleanup", "OBSERVED", cleanup=status)
        except Exception as error:
            failed("CLEANUP_JOURNAL_FAILED", error)
            status["complete"] = False
        return status

def _parse_artifacts(raw):
    """Parse the collected artifacts zip into {name: {sha256, bytes}} objects.

    Every member must be an allowlisted trainer output; anything else fails.
    """
    require(0 < len(raw) <= 256 * 1024**2, "CONDITION_SKILL_V9_ARTIFACTS_BOUND")
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        require(0 < len(infos) <= remote_worker.OUTPUT_FILES_MAX,
                "CONDITION_SKILL_V9_ARTIFACT_COUNT_BOUND")
        objects = {}
        total = 0
        for info in infos:
            name = info.filename
            require(type(name) is str and name and "\\" not in name and ":" not in name
                    and not any(part in ("", ".", "..") for part in name.split("/"))
                    and not info.is_dir()
                    and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
                    and not info.flag_bits & 1,
                    "CONDITION_SKILL_V9_ARTIFACT_MEMBER_UNSAFE")
            require(remote_worker.allowed_trainer_output(name),
                    "CONDITION_SKILL_V9_UNALLOWED_ARTIFACT:" + name)
            require(name not in objects, "CONDITION_SKILL_V9_DUPLICATE_ARTIFACT:" + name)
            member = archive.read(info)
            require(len(member) == info.file_size
                    and len(member) <= remote_worker.TRAINER_OUTPUT_BYTES_MAX,
                    "CONDITION_SKILL_V9_ARTIFACT_MEMBER_SIZE:" + name)
            total += len(member)
            require(total <= remote_worker.TRAINER_OUTPUT_BYTES_MAX,
                    "CONDITION_SKILL_V9_ARTIFACT_TOTAL_BOUND")
            objects[name] = {"sha256": digest(member), "bytes": len(member)}
    return objects
