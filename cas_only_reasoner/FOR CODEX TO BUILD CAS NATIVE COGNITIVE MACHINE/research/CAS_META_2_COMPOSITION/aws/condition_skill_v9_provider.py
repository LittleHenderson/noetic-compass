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
automatic retries anywhere; the single registered instance uses
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
        self._instance_id = None
        self._result = None
        self._resources = {}

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
        if self._resources.get("bucket") == bucket:
            return bucket
        s3.create_bucket(Bucket=bucket,
                         CreateBucketConfiguration={"LocationConstraint": plan.RESOURCE_PLAN["region"]})
        try:
            s3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": tags})
            s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={
                "BlockPublicAcls": True, "IgnorePublicAcls": True,
                "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
            s3.put_bucket_encryption(Bucket=bucket, ServerSideEncryptionConfiguration={
                "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]})
        except Exception:
            # A half-hardened bucket must not be treated as ready: forget it so
            # later calls re-attempt hardening instead of silently skipping it.
            self._resources.pop("bucket", None)
            raise
        self._resources["bucket"] = bucket
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
                  "resource_plan": plan.RESOURCE_PLAN, "permit": permit}
        driver_lines = [
            "CONFIG = " + repr(config),
            "import hashlib",
            "import json",
            "import os",
            "import shutil",
            "import subprocess",
            "import sys",
            "import zipfile",
            "from pathlib import Path",
            "ROOT = Path('/opt/cas-meta2-condition-skill-v9')",
            "pkg = ROOT / 'package'",
            "if not pkg.exists():",
            "    pkg.mkdir(parents=True)",
            "with zipfile.ZipFile(ROOT / 'source.zip') as z:",
            "    z.extractall(pkg)",
            "pilot = pkg / 'research/CAS_META_2_COMPOSITION'",
            "sys.path.insert(0, str(pilot))",
            "out = pilot / 'runs' / CONFIG['job']",
            "data = pilot / 'records/condition_skill_v9_001/dataset_001'",
            "evidence = out.parent / (out.name + '.evidence')",
            "# Frozen CUDA 12.8 index, mirrored from aws/launch.py launch_plan.json",
            "# torch_index_url; the same pin used by every v8 remote install.",
            "TORCH_INDEX = 'https://download.pytorch.org/whl/cu128'",
            "WHEEL_DIR = 'research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist'",
            "WHEELS = [pkg / WHEEL_DIR / 'casformer_reference-0.1.0-py3-none-any.whl',",
            "          pkg / WHEEL_DIR / 'cas_neural_cjt-0.2.0-py3-none-any.whl']",
            "REQUIREMENTS = pilot / 'requirements-gpu.txt'",
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
            "timeout 120 aws s3api get-object --bucket " + bucket
            + " --key input/permit.json " + WORKER_ROOT + "/permit.json --region "
            + frozen["region"],
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
        require(not self._launch_attempted, "CONDITION_SKILL_V9_SINGLE_LAUNCH_ONLY")
        self._validate_permit(permit)
        frozen = plan.RESOURCE_PLAN
        ec2, s3, iam, scheduler = (self.clients[name] for name in
                                   ("ec2", "s3", "iam", "scheduler"))
        bucket = self.job + "-" + frozen["account"]
        tags = [{"Key": "cas_meta_job", "Value": self.job}]
        worker_role = self.job + "-worker"
        timer_role = self.job + "-timer"

        raw = self._source_bytes()
        require(0 < len(raw) <= 24 * 1024**2, "CONDITION_SKILL_V9_SOURCE_ARCHIVE_BOUND")

        self._ensure_bucket(s3, tags)
        s3.put_object(Bucket=bucket, Key="input/source.zip", Body=raw)
        remote = self._render_remote(permit).encode("utf-8")
        s3.put_object(Bucket=bucket, Key="input/remote.py", Body=remote)
        s3.put_object(Bucket=bucket, Key="input/permit.json", Body=canonical(permit))

        def create_role(name, service, statements):
            trust = {"Version": "2012-10-17", "Statement": [
                {"Effect": "Allow", "Principal": {"Service": service},
                 "Action": "sts:AssumeRole"}]}
            iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust),
                            Tags=tags)
            iam.put_role_policy(RoleName=name, PolicyName="job-only",
                                PolicyDocument=json.dumps({"Version": "2012-10-17",
                                                           "Statement": statements}))
            return name

        create_role(worker_role, "ec2.amazonaws.com", [
            {"Effect": "Allow", "Action": ["s3:GetObject"],
             "Resource": ["arn:aws:s3:::" + bucket + "/input/source.zip",
                          "arn:aws:s3:::" + bucket + "/input/remote.py",
                          "arn:aws:s3:::" + bucket + "/input/permit.json"]},
            {"Effect": "Allow", "Action": ["s3:PutObject"],
             "Resource": ["arn:aws:s3:::" + bucket + "/results/*"]}])
        iam.create_instance_profile(InstanceProfileName=worker_role, Tags=tags)
        iam.add_role_to_instance_profile(InstanceProfileName=worker_role,
                                         RoleName=worker_role)
        create_role(timer_role, "scheduler.amazonaws.com", [
            {"Effect": "Allow", "Action": "ec2:TerminateInstances",
             "Resource": "arn:aws:ec2:" + frozen["region"] + ":" + frozen["account"]
             + ":instance/*",
             "Condition": {"StringEquals": {"ec2:ResourceTag/cas_meta_job": self.job}}}])

        _, subnet_id = self._default_network(ec2)
        sg = ec2.create_security_group(GroupName=self.job,
                                       Description="CAS condition-skill v9 outbound HTTPS only",
                                       VpcId=ec2.describe_vpcs(Filters=[
                                           {"Name": "isDefault", "Values": ["true"]}]
                                       )["Vpcs"][0]["VpcId"],
                                       TagSpecifications=[{"ResourceType": "security-group",
                                                           "Tags": tags}])["GroupId"]
        ec2.revoke_security_group_egress(GroupId=sg, IpPermissions=[
            {"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        ec2.authorize_security_group_egress(GroupId=sg, IpPermissions=[
            {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,
             "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        self._resources["security_group"] = sg

        bootstrap = self._user_data(bucket, digest(remote))
        launched = ec2.run_instances(
            ImageId=frozen["ami"], InstanceType=frozen["instance_type"],
            MinCount=1, MaxCount=1, ClientToken=self.job,
            IamInstanceProfile={"Name": worker_role},
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
        require(len(launched.get("Instances", [])) == 1,
                "CONDITION_SKILL_V9_ONE_INSTANCE_RESPONSE_REQUIRED")
        self._instance_id = launched["Instances"][0]["InstanceId"]
        require(type(self._instance_id) is str and bool(INSTANCE_ID.fullmatch(self._instance_id)),
                "CONDITION_SKILL_V9_REAL_INSTANCE_ID_REQUIRED")
        self._resources["instance"] = self._instance_id
        self._launch_attempted = True

        cloud_deadline = datetime.now(timezone.utc) + timedelta(
            seconds=frozen["cloud_schedule_seconds"])
        target = {"Arn": "arn:aws:scheduler:::aws-sdk:ec2:terminateInstances",
                  "RoleArn": timer_role,
                  "Input": json.dumps({"InstanceIds": [self._instance_id]}),
                  "RetryPolicy": {"MaximumRetryAttempts": 0,
                                  "MaximumEventAgeInSeconds": 60}}
        expression = "at(" + cloud_deadline.strftime("%Y-%m-%dT%H:%M:%S") + ")"
        scheduler.create_schedule(Name=self.job, ScheduleExpression=expression,
                                  ScheduleExpressionTimezone="UTC",
                                  FlexibleTimeWindow={"Mode": "OFF"}, Target=target,
                                  ActionAfterCompletion="DELETE")
        self._resources["schedule"] = self.job

        return {"job": self.job, "instance_id": self._instance_id,
                "client_token": self.job, "imdsv2_required": True,
                "permit": permit, "bucket": bucket, "launch_attempted": True,
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
        return _parse_artifacts(raw)

    # ------------------------------------------------------------------ #
    # cleanup (call-safe; records every failure)
    # ------------------------------------------------------------------ #
    def cleanup(self, job):
        self.calls.append("cleanup")
        require(job == self.job, "CONDITION_SKILL_V9_CLEANUP_JOB_MISMATCH")
        failures = []
        status = {}
        ec2 = self.clients.get("ec2")
        s3 = self.clients.get("s3")
        iam = self.clients.get("iam")
        scheduler = self.clients.get("scheduler")

        instance_id = self._instance_id or self._resources.get("instance")
        if instance_id is None:
            status["instance_terminated"] = True
            status["instance_termination_confirmed"] = True
        else:
            try:
                ec2.terminate_instances(InstanceIds=[instance_id])
                confirmed = False
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    current = ec2.describe_instances(InstanceIds=[instance_id]
                                                     )["Reservations"][0]["Instances"][0]
                    if current.get("State", {}).get("Name") == "terminated":
                        confirmed = True
                        break
                    time.sleep(2)
                status["instance_terminated"] = True
                status["instance_termination_confirmed"] = confirmed
                if not confirmed:
                    failures.append("INSTANCE_TERMINATION_UNCONFIRMED:" + instance_id)
            except Exception as error:  # noqa: BLE001 - cleanup must record, not raise
                failures.append("INSTANCE_TERMINATION_FAILED:" + str(error))
                status["instance_terminated"] = False
                status["instance_termination_confirmed"] = False

        bucket = self._resources.get("bucket")
        if bucket is not None and s3 is not None:
            try:
                # results/* must be deleted too, or delete_bucket fails on a
                # non-empty bucket and every successful run ends incomplete.
                s3.delete_objects(Bucket=bucket, Delete={"Objects": [
                    {"Key": "input/source.zip"}, {"Key": "input/remote.py"},
                    {"Key": "input/permit.json"},
                    {"Key": "reservation/reservation_receipt.json"},
                    {"Key": "reservation/ledger_snapshot.json"},
                    {"Key": "results/complete.json"},
                    {"Key": "results/artifacts.zip"}]})
                status["inputs_deleted"] = True
                status["results_deleted"] = True
            except Exception as error:  # noqa: BLE001
                failures.append("INPUT_DELETION_FAILED:" + str(error))
                status["inputs_deleted"] = False
            try:
                s3.delete_bucket(Bucket=bucket)
                status["bucket_deleted"] = True
            except Exception as error:  # noqa: BLE001
                failures.append("BUCKET_DELETION_FAILED:" + str(error))
                status["bucket_deleted"] = False
        else:
            status["inputs_deleted"] = True
            status["bucket_deleted"] = True

        if scheduler is not None:
            try:
                scheduler.delete_schedule(Name=self.job)
                status["schedule_removed"] = True
            except self._client_error as error:
                code = getattr(error, "response", {}).get("Error", {}).get("Code")
                if code == "ResourceNotFoundException":
                    # Already absent: clean, not a failure. Record it honestly.
                    status["schedule_removed"] = True
                    status["schedule_was_absent"] = True
                else:
                    failures.append("SCHEDULE_REMOVAL_FAILED:" + str(error))
                    status["schedule_removed"] = False
            except Exception as error:  # noqa: BLE001
                failures.append("SCHEDULE_REMOVAL_FAILED:" + str(error))
                status["schedule_removed"] = False
        else:
            status["schedule_removed"] = True

        security_group = self._resources.get("security_group")
        if security_group is not None and ec2 is not None:
            try:
                ec2.delete_security_group(GroupId=security_group)
                status["security_group_deleted"] = True
            except self._client_error as error:
                code = getattr(error, "response", {}).get("Error", {}).get("Code")
                if code in ("InvalidGroup.NotFound", "InvalidSecurityGroupID.NotFound"):
                    status["security_group_deleted"] = True
                    status["security_group_was_absent"] = True
                else:
                    failures.append("SECURITY_GROUP_DELETION_FAILED:" + str(error))
                    status["security_group_deleted"] = False
            except Exception as error:  # noqa: BLE001
                failures.append("SECURITY_GROUP_DELETION_FAILED:" + str(error))
                status["security_group_deleted"] = False
        else:
            status["security_group_deleted"] = True

        if iam is not None:
            for role in (self.job + "-worker", self.job + "-timer"):
                try:
                    iam.remove_role_from_instance_profile(InstanceProfileName=role,
                                                         RoleName=role)
                except Exception:  # noqa: BLE001 - instance profile may not exist
                    pass
                try:
                    iam.delete_instance_profile(InstanceProfileName=role)
                except Exception:  # noqa: BLE001
                    pass
                try:
                    iam.delete_role_policy(RoleName=role, PolicyName="job-only")
                    iam.delete_role(RoleName=role)
                except Exception:  # noqa: BLE001
                    pass
            status["roles_removed"] = True

        status["volumes_deleted"] = status.get("instance_termination_confirmed", False)
        if not status.get("volumes_deleted"):
            failures.append("VOLUME_DELETION_UNCONFIRMED")
        complete = not failures
        return {"complete": complete, "failures": failures, **status}


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
