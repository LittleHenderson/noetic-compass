"""Pure META3 launch/collection contracts. Fixtures are not native evidence."""
import ast
from copy import deepcopy
from hashlib import sha256
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("meta3_launch_tested", ROOT / "aws/launch.py")
launch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launch)


@pytest.fixture(autouse=True)
def isolated_execution_lock(tmp_path, monkeypatch):
    # Tests must never acquire the real campaign lock or touch its ledger.
    monkeypatch.setattr(launch, "EXECUTION_LOCK_FILE", tmp_path / "meta3-execution.lock")


def plan():
    return json.loads(launch.PLAN_FILE.read_bytes())


def config():
    return {**plan(), "job": "cas-meta3-fixture-only", "bucket": "cas-meta3-fixture-only-807562639912",
            "archive_sha256": "a" * 64, "manifest": {"entrypoint": launch.frozen.ENTRYPOINT,
            "source_sha": "b" * 40, "baseline_sha": launch.ACCEPTED_BASELINE,
            "pilot_dir": launch.frozen.PILOT, "meta2_dir": launch.frozen.META2,
            "meta1_dir": launch.frozen.META1, "meta_runtime_dir": launch.frozen.META_RUNTIME,
            "files_sha256": {}}}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def synthetic_roots(tmp_path):
    """Byte-contract mock only: its placeholder DBs are not native databases."""
    job = config()["job"]
    demo, native = tmp_path / "demo", tmp_path / "native"
    demo.mkdir()
    native.mkdir()
    names = ("package.json", "registry.db", "trusted_compatibility.json", "rejection_receipt.json",
        "link_receipt.json", "identity_probe_receipt.json", "reference_result.json",
        "reference_verdict.json", "candidate_result.json", "candidate_verdict.json",
        "call_mapping_receipt.json", "writer.stdout.log", "writer.stderr.log",
        "reader.stdout.log", "reader.stderr.log")
    for name in names:
        (demo / name).write_bytes(b"MOCK ONLY")
    for role, pid in (("writer", 123), ("reader", 456)):
        (demo / (role + "_receipt.json")).write_bytes(encoded({
            "job": job, "qualification_status": "UNQUALIFIED", "learning_performed": False,
            "pid": pid, "process_nonce": role, "registry_closed": True}))
        (demo / (role + "_process.json")).write_bytes(encoded({"stage": role, "returncode": 0, "pid": pid}))
    for folder in ("reference", "candidate", "fresh_reader_identity"):
        target = native / folder
        target.mkdir()
        (target / "native.db").write_bytes(b"MOCK NOT A NATIVE DATABASE")
    absolute = {"demo": "/opt/cas-meta3/package/research/CAS_META_3_PROCEDURAL_MEMORY/runs/cloud_job/demo",
                "native": "/opt/cas-meta3/package/research/CAS_META_2_COMPOSITION/records/meta3_" + job}
    entries = []
    for kind, base in (("demo", demo), ("native", native)):
        for path in sorted(base.rglob("*")):
            if path.is_file():
                raw = path.read_bytes()
                entries.append({"root": kind, "path": path.relative_to(base).as_posix(),
                                "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    index = {"schema": "cas-meta3-file-index/0.1", "roots": absolute, "entries": entries,
             "entries_sha256": sha256(encoded(entries).rstrip(b"\n")).hexdigest()}
    index_raw = encoded(index)
    (demo / "file_index.json").write_bytes(index_raw)
    receipt = {"schema": "cas-meta3-native-reuse/0.1", "status": "CAS_META_3_NATIVE_REUSE_DEMONSTRATED",
        "completed": True, "job": job, "qualification_status": "UNQUALIFIED", "learning_performed": False,
        "automatic_retries": 0, "reference_native_runs": 3, "candidate_native_runs": 3,
        "identity_probe_native_ticks": 0, "max_wall_seconds": 1200,
        "output": absolute["demo"], "native_output": absolute["native"],
        "file_index_sha256": sha256(index_raw).hexdigest()}
    (demo / "memory_demo_receipt.json").write_bytes(encoded(receipt))
    cloud = tmp_path / "cloud_job"
    cloud.mkdir()
    # The separate demo directory is collected under its explicit archive prefix.
    roots = [("cloud_job/demo", demo, True), ("meta2_native/meta3_" + job, native, True)]
    return job, demo, native, roots


def staged_fixture(tmp_path):
    job, demo, native, roots = synthetic_roots(tmp_path)
    stage = tmp_path / "staging"
    launch.collect_roots(roots, stage, 8 * 1024 * 1024)
    names = {path.relative_to(stage).as_posix() for path in stage.rglob("*") if path.is_file()}
    return job, stage, names


def test_exact_shared_plan_without_neural_or_provider_execution():
    launch.validate_approval("400.00", plan())
    assert plan()["runtime_seconds_max"] == 7200
    assert plan()["compute_seconds_max"] == 6600
    assert plan()["demo_seconds_max"] == 1200
    assert plan()["per_launch_reserved_cap_usd"] == "7.00"


@pytest.mark.parametrize("change", [
    {"instance_type": "g4dn.xlarge"}, {"instance_count": 2}, {"runtime_seconds_max": 7201},
    {"compute_seconds_max": 6601}, {"automatic_retries": 1}, {"demo_seconds_max": 1201},
    {"entrypoint": "cas_meta2.campaign"}, {"learning_performed": True},
    {"qualification_status": "QUALIFIED"}, {"instance_count": True}, {"artifact_objects_max": 4},
])
def test_resource_scope_changes_fail_closed(change):
    with pytest.raises(launch.LaunchRefused):
        launch.validate_approval("400.00", {**plan(), **change})


def test_missing_owner_ledger_blocks_before_provider_import():
    args = SimpleNamespace(approved_cap_usd="400.00")
    with patch.object(launch, "verify_launcher_identity", return_value={}), patch.object(
        launch.budget, "read_ledger", side_effect=launch.budget.BudgetRefused("OWNER_APPROVAL_MISSING")):
        with pytest.raises(launch.budget.BudgetRefused, match="OWNER_APPROVAL_MISSING"):
            launch.execute(args, plan(), {})


def test_only_existing_canonical_ledger_is_used():
    assert launch.budget.CANONICAL_LEDGER == launch.frozen.META2_ROOT / "records/budget/campaign_ledger.json"
    with patch.object(launch.budget, "reserve_budget", return_value={"mock": True}) as call:
        assert launch.reserve_budget(config()["job"], "b" * 40, "a" * 64, plan()) == {"mock": True}
        call.assert_called_once_with(config()["job"], "b" * 40, "a" * 64, "7.00", plan())


def test_plan_default_does_not_execute(capsys):
    with patch.object(launch, "execute", side_effect=AssertionError("PAID_PATH")):
        assert launch.main([]) == 0
    assert json.loads(capsys.readouterr().out)["aws_actions_performed"] is False


def test_cleanup_functions_are_unchanged_shared_objects():
    for name in ("check_tag", "confirm_deleted_volumes", "remove_owned_auxiliary_resources",
                 "reconcile_instance", "verify_schedule", "terminate_owned_instance", "build_evidence_bundle"):
        assert getattr(launch, name) is getattr(launch.shared, name)


def test_old_validator_and_entrypoint_are_never_reassigned_or_called():
    source = Path(launch.__file__).read_text()
    ast.parse(source)
    assert "shared.validate_archive" not in source
    assert "shared.execute" not in source
    assert "shared.remote_program" not in source
    assert "experiment_record" not in source
    assert "cas_meta2.campaign" not in source
    assert "ledger_path=" not in source and "initialize_ledger(" not in source


def test_all_dependency_hashes_are_checked_before_any_import():
    with patch.object(launch.frozen, "verify_dependencies", side_effect=ValueError("CHANGED")), patch.object(
        launch.frozen.importlib.util, "spec_from_file_location", side_effect=AssertionError("IMPORT_TOO_EARLY")):
        with pytest.raises(ValueError, match="CHANGED"):
            launch.frozen.load_helpers()


@pytest.mark.parametrize("name", list(launch.frozen.PINNED_FILES))
def test_each_dependency_tamper_is_rejected_in_fixture_copy(tmp_path, name):
    for relative in launch.frozen.PINNED_FILES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((launch.frozen.META2_ROOT / relative).read_bytes())
    (tmp_path / name).write_bytes(b"not the frozen helper")
    with pytest.raises(ValueError, match="IMMUTABLE_META2_DEPENDENCY_CHANGED"):
        launch.frozen.verify_dependencies(tmp_path)


def test_remote_fixed_command_eight_gpu_gates_and_new_output_roots():
    code = launch.remote_program(config())
    compile(code, "<remote-not-executed>", "exec")
    assert "'cas_meta3.native_demo'" in code
    assert "'--native-output',str(native_root)" in code
    assert "effective_demo_seconds = min(CONFIG['demo_seconds_max'],CONFIG['compute_seconds_max'],int(deadline-time.time()-180))" in code
    assert "seconds=effective_demo_seconds,deadline=deadline" in code
    assert "env['CAS_META3_RUN_GPU_DEMO'] = '1'" in code
    assert "env['CAS_META3_AWS_JOB_ID'] = CONFIG['job']" in code
    assert "env['CAS_META2_AWS_JOB_ID'] = CONFIG['job']" in code
    assert "cwd=package/m['meta2_dir'],seconds=600" in code
    assert "tests/test_execution_contract.py" in code and "tests/test_policy_gpu.py" in code
    assert "test_learning_v2_gpu" not in code and "campaign_v2" not in code
    assert "native_root = package / m['meta2_dir'] / 'records' / ('meta3_' + CONFIG['job'])" in code
    assert "meta2_native/meta3_" in code and "meta1_runs" in code
    assert code.index("cloud_deadline_confirmed") < code.index("'torch==2.11.0'")
    assert code.index("env.pop('CAS_META2_RUN_GPU_TESTS')") < code.index("env['CAS_META3_RUN_GPU_DEMO']")


def test_early_guest_cutoff_and_group_cleanup_are_preserved():
    script = launch.user_data(config())
    assert len(script.encode()) < 16384 and "( sleep 7100;" in script
    assert "sha256sum -c -" in script and "trap " in script
    code = launch.remote_program(config())
    assert "start_new_session=True" in code and "os.killpg(process.pid,signal.SIGTERM)" in code
    assert "os.killpg(process.pid,signal.SIGKILL)" in code
    source = Path(launch.__file__).read_text()
    assert source.index("verify_schedule(confirmed,target,expression)") < source.index('Key="input/permit.json"')
    assert source.index("budget_reservation = reserve_budget(") < source.index("s3.create_bucket(")
    assert source.index("verify_downloaded_packet(artifact,result") < source.index("artifact_verified = True")


def test_dual_root_collection_preserves_all_bytes_and_trusted_sidecars(tmp_path):
    job, stage, names = staged_fixture(tmp_path)
    report = launch.verify_demo_evidence(lambda name: (stage / name).read_bytes(), names, job)
    assert report["qualification_status"] == "UNQUALIFIED" and report["learning_performed"] is False
    assert report["memory_demo_receipt_sha256"] == sha256((stage / "cloud_job/demo/memory_demo_receipt.json").read_bytes()).hexdigest()
    assert report["native_prefix"] == "meta2_native/meta3_" + job + "/"
    assert report["indexed_files"] == len(names) - 3


@pytest.mark.parametrize("missing", [
    "cloud_job/demo/registry.db", "cloud_job/demo/writer.stderr.log",
    "meta2_native/meta3_cas-meta3-fixture-only/reference/native.db",
    "meta2_native/meta3_cas-meta3-fixture-only/candidate/native.db",
    "meta2_native/meta3_cas-meta3-fixture-only/fresh_reader_identity/native.db",
])
def test_missing_native_or_memory_evidence_cannot_be_success(tmp_path, missing):
    job, stage, names = staged_fixture(tmp_path)
    names.remove(missing)
    with pytest.raises(RuntimeError, match="MANDATORY"):
        launch.verify_demo_evidence(lambda name: (stage / name).read_bytes(), names, job)


def test_rehashed_receipt_cannot_promote_or_claim_learning(tmp_path):
    job, stage, names = staged_fixture(tmp_path)
    path = stage / "cloud_job/demo/memory_demo_receipt.json"
    doc = json.loads(path.read_bytes())
    doc["learning_performed"] = True
    path.write_bytes(encoded(doc))
    with pytest.raises(RuntimeError, match="SCOPE_OR_COUNTS"):
        launch.verify_demo_evidence(lambda name: (stage / name).read_bytes(), names, job)


def test_dual_root_added_file_or_changed_byte_rejected(tmp_path):
    job, stage, names = staged_fixture(tmp_path)
    target = stage / "cloud_job/demo/registry.db"
    target.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="MEMBER_HASH"):
        launch.verify_demo_evidence(lambda name: (stage / name).read_bytes(), names, job)


def test_required_root_absence_and_expanded_limit_fail(tmp_path):
    with pytest.raises(RuntimeError, match="REQUIRED_ARTIFACT_ROOT_MISSING"):
        launch.collect_roots([("native", tmp_path / "missing", True)], tmp_path / "missing_stage", 8 * 1024 * 1024)
    source = tmp_path / "source"
    source.mkdir()
    (source / "x").write_bytes(b"1234")
    with pytest.raises(RuntimeError, match="EXPANDED_CEILING"):
        launch.collect_roots([("native", source, True)], tmp_path / "small_stage", 4194305)


def test_unsafe_artifact_label_rejected(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(RuntimeError, match="UNSAFE_ARTIFACT_ROOT_LABEL"):
        launch.collect_roots([("../outside", source, True)], tmp_path / "stage", 8 * 1024 * 1024)


def test_download_binding_is_checked_before_returning_verified(tmp_path):
    job, stage, names = staged_fixture(tmp_path)
    report = launch.verify_demo_evidence(lambda name: (stage / name).read_bytes(), names, job)
    binding = {**report, "job": job, "source_sha": "b" * 40}
    job_record = {"job": job, "source_sha": "b" * 40, "returncode": 0, "entrypoint": launch.frozen.ENTRYPOINT,
                  "native_demo_binding": binding}
    archive = tmp_path / "packet.zip"
    collection = launch.build_evidence_bundle(stage, archive, 8 * 1024 * 1024, job_record, 8 * 1024 * 1024)
    result = {"bytes": archive.stat().st_size, "sha256": sha256(archive.read_bytes()).hexdigest(),
              "returncode": 0, "entrypoint": launch.frozen.ENTRYPOINT, "native_demo_binding": binding}
    assert launch.verify_downloaded_packet(archive, result, job, "b" * 40, plan()) == collection
    wrong = {**result, "native_demo_binding": {**binding, "file_index_sha256": "f" * 64}}
    with pytest.raises(launch.LaunchRefused, match="TRUSTED_DEMO_SIDECAR"):
        launch.verify_downloaded_packet(archive, wrong, job, "b" * 40, plan())


def test_execution_lock_blocks_a_second_owner_and_releases_only_its_bytes():
    path = launch.EXECUTION_LOCK_FILE
    with launch.campaign_execution_lock() as owner:
        original = path.read_bytes()
        assert owner["scope"] == launch.EXECUTION_LOCK_SCOPE
        assert "not a cross-host or cross-version mutex" in owner["scope"]
        with pytest.raises(launch.LaunchRefused, match="ALREADY_LOCKED"):
            with launch.campaign_execution_lock():
                raise AssertionError("SECOND_OWNER_ENTERED")
        assert path.read_bytes() == original
    assert not path.exists()


def test_execution_lock_refuses_a_stale_or_replaced_lock_without_deleting_it():
    path = launch.EXECUTION_LOCK_FILE
    with pytest.raises(launch.LaunchRefused, match="OWNERSHIP_CHANGED_NOT_REMOVED"):
        with launch.campaign_execution_lock():
            path.write_bytes(b"another owner; fixture only")
    assert path.read_bytes() == b"another owner; fixture only"
    with pytest.raises(launch.LaunchRefused, match="NO_AUTOMATIC_STALE_CLEAR"):
        with launch.campaign_execution_lock():
            raise AssertionError("STALE_LOCK_WAS_CLEARED")
    assert path.read_bytes() == b"another owner; fixture only"


def test_execution_lock_spans_the_actual_execute_body_and_exception_cleanup():
    observed = []
    def body(args, chosen_plan, manifest, owner):
        assert launch.EXECUTION_LOCK_FILE.exists()
        assert json.loads(launch.EXECUTION_LOCK_FILE.read_bytes())["token"] == owner["token"]
        observed.append("preflight")
        try:
            raise RuntimeError("FAKE_PROVIDER_FAILURE")
        finally:
            assert launch.EXECUTION_LOCK_FILE.exists()
            observed.append("cleanup")
    with patch.object(launch, "_execute_locked", side_effect=body):
        with pytest.raises(RuntimeError, match="FAKE_PROVIDER_FAILURE"):
            launch.execute(SimpleNamespace(approved_cap_usd="400.00"), plan(), {})
    assert observed == ["preflight", "cleanup"]
    assert not launch.EXECUTION_LOCK_FILE.exists()


def test_lock_contention_precedes_provider_preflight_and_budget_reads():
    with launch.campaign_execution_lock(), patch.object(
        launch, "_execute_locked", side_effect=AssertionError("PROVIDER_OR_BUDGET_PATH_ENTERED")):
        with pytest.raises(launch.LaunchRefused, match="ALREADY_LOCKED"):
            launch.execute(SimpleNamespace(approved_cap_usd="400.00"), plan(), {})


def test_execution_lock_is_visible_to_a_genuinely_fresh_process():
    # This child imports pure launcher code only. It never calls execute/budget/provider APIs.
    code = """
import importlib.abc, importlib.util, pathlib, sys
class NoNeuralImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','tensorflow','jax','numpy','boto3','botocore'}:
            raise RuntimeError('FORBIDDEN_IMPORT:' + fullname)
sys.meta_path.insert(0, NoNeuralImports())
spec = importlib.util.spec_from_file_location('pure_lock_child', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.EXECUTION_LOCK_FILE = pathlib.Path(sys.argv[2])
try:
    with module.campaign_execution_lock():
        raise RuntimeError('LOCK_WAS_NOT_SHARED')
except module.LaunchRefused as exc:
    assert str(exc) == 'META3_EXECUTION_ALREADY_LOCKED_NO_AUTOMATIC_STALE_CLEAR'
    print('FRESH_PROCESS_LOCK_CONTENTION_CONFIRMED_PURE_ONLY')
"""
    with launch.campaign_execution_lock():
        original = launch.EXECUTION_LOCK_FILE.read_bytes()
        result = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT / "aws/launch.py"),
                                 str(launch.EXECUTION_LOCK_FILE)], capture_output=True, text=True,
                                timeout=30, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stdout.strip() == "FRESH_PROCESS_LOCK_CONTENTION_CONFIRMED_PURE_ONLY"
        assert launch.EXECUTION_LOCK_FILE.read_bytes() == original


class FakeClientError(Exception):
    def __init__(self, code):
        self.response = {"Error": {"Code": code}}
        super().__init__(code)


class FakeAuxiliaryAWS:
    """Stateful fake provider: successful creation followed by a lost response.

    No methods below access AWS. They exercise the actual execute/cleanup code,
    including the unchanged shared cleanup helper, against synthetic resources.
    """
    def __init__(self, target, receipt_path, *, deny_ownership=False):
        self.target, self.receipt_path = target, receipt_path
        self.deny_ownership = deny_ownership
        self.account = plan()["account_id"]
        self.roles, self.profiles, self.groups, self.buckets = {}, {}, {}, {}
        self.deleted, self.created, self.lookups = [], [], []

    def client(self, name, **kwargs):
        return self

    def before_create(self, key, kind):
        # The persisted receipt must already identify the attempted resource.
        saved = json.loads(self.receipt_path.read_bytes())
        intent = saved["resource_intents"][key]
        assert intent["kind"] == kind and intent["status"] == "CREATE_ATTEMPTED"
        assert key not in saved["resources"]
        assert Path(saved["execution_lock"]["path"]).exists()
        self.created.append((kind, intent["name"]))

    def after_create(self, kind, row):
        if kind == self.target:
            if self.deny_ownership:
                row["Tags"] = [{"Key": "cas_meta_job", "Value": "someone-else"}]
            raise TimeoutError("FAKE_CREATE_RESPONSE_LOST:" + kind)

    def get_caller_identity(self):
        return {"Account": self.account, "Arn": "arn:aws:iam::" + self.account + ":user/fixture-only"}

    def describe_subnets(self, **kwargs):
        return {"Subnets": [{"VpcId": "vpc-abc"}]}

    def describe_images(self, **kwargs):
        return {"Images": [{"State": "available", "RootDeviceName": "/dev/sda1", "OwnerId": "898082745236"}]}

    def get_service_quota(self, **kwargs):
        return {"Quota": {"Value": 8}}

    def describe_instances(self, **kwargs):
        return {"Reservations": []}

    def get_products(self, **kwargs):
        return {"PriceList": [json.dumps({"terms": {"OnDemand": {"fixture": {"priceDimensions": {
            "fixture": {"unit": "Hrs", "pricePerUnit": {"USD": "2.52"}}}}}}})]}

    def create_bucket(self, Bucket, **kwargs):
        self.before_create("bucket", "bucket")
        row = {"Tags": []}
        self.buckets[Bucket] = row
        self.after_create("bucket", row)
        return {}

    def put_bucket_tagging(self, Bucket, Tagging):
        self.buckets[Bucket]["Tags"] = deepcopy(Tagging["TagSet"])

    def put_public_access_block(self, **kwargs):
        return {}

    def put_bucket_encryption(self, **kwargs):
        return {}

    def put_bucket_lifecycle_configuration(self, **kwargs):
        return {}

    def get_bucket_tagging(self, Bucket, **kwargs):
        self.lookups.append(("bucket", Bucket, kwargs))
        tags = self.buckets[Bucket]["Tags"]
        if not tags:
            raise FakeClientError("NoSuchTagSet")
        return {"TagSet": deepcopy(tags)}

    def head_object(self, **kwargs):
        raise FakeClientError("NoSuchKey")

    def list_objects_v2(self, **kwargs):
        return {"Contents": []}

    def create_role(self, RoleName, Tags, **kwargs):
        self.before_create(RoleName, "role")
        row = {"RoleName": RoleName, "Arn": f"arn:aws:iam::{self.account}:role/{RoleName}", "Tags": deepcopy(Tags)}
        self.roles[RoleName] = row
        self.after_create("role", row)
        return {"Role": deepcopy(row)}

    def get_role(self, RoleName):
        self.lookups.append(("role", RoleName))
        return {"Role": deepcopy(self.roles[RoleName])}

    def put_role_policy(self, **kwargs):
        return {}

    def delete_role_policy(self, **kwargs):
        return {}

    def delete_role(self, RoleName):
        self.deleted.append(("role", RoleName))
        del self.roles[RoleName]

    def create_instance_profile(self, InstanceProfileName, Tags):
        self.before_create("instance_profile", "instance_profile")
        row = {"InstanceProfileName": InstanceProfileName,
               "Arn": f"arn:aws:iam::{self.account}:instance-profile/{InstanceProfileName}",
               "Tags": deepcopy(Tags), "Roles": []}
        self.profiles[InstanceProfileName] = row
        self.after_create("instance_profile", row)
        return {"InstanceProfile": deepcopy(row)}

    def get_instance_profile(self, InstanceProfileName):
        self.lookups.append(("instance_profile", InstanceProfileName))
        return {"InstanceProfile": deepcopy(self.profiles[InstanceProfileName])}

    def add_role_to_instance_profile(self, InstanceProfileName, RoleName):
        self.profiles[InstanceProfileName]["Roles"] = [{"RoleName": RoleName}]

    def remove_role_from_instance_profile(self, InstanceProfileName, RoleName):
        self.profiles[InstanceProfileName]["Roles"] = []

    def delete_instance_profile(self, InstanceProfileName):
        self.deleted.append(("instance_profile", InstanceProfileName))
        del self.profiles[InstanceProfileName]

    def create_security_group(self, GroupName, VpcId, TagSpecifications, **kwargs):
        self.before_create("security_group", "security_group")
        row = {"GroupName": GroupName, "VpcId": VpcId, "OwnerId": self.account, "GroupId": "sg-abc",
               "Tags": deepcopy(TagSpecifications[0]["Tags"])}
        self.groups["sg-abc"] = row
        self.after_create("security_group", row)
        return {"GroupId": "sg-abc"}

    def describe_security_groups(self, **kwargs):
        self.lookups.append(("security_group", deepcopy(kwargs)))
        return {"SecurityGroups": deepcopy(list(self.groups.values()))}

    def delete_security_group(self, GroupId):
        self.deleted.append(("security_group", GroupId))
        del self.groups[GroupId]


def execute_fake_lost_create(tmp_path, monkeypatch, kind, *, deny_ownership=False):
    """Run the real local controller with every external boundary replaced."""
    monkeypatch.setattr(launch, "PILOT_ROOT", tmp_path)
    output = tmp_path / "fake_receipts"
    fake = FakeAuxiliaryAWS(kind, output / "launch_receipt.json", deny_ownership=deny_ownership)
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(Session=lambda **kwargs: fake))
    monkeypatch.setitem(sys.modules, "botocore.config", SimpleNamespace(Config=lambda **kwargs: kwargs))
    monkeypatch.setitem(sys.modules, "botocore.exceptions", SimpleNamespace(ClientError=FakeClientError))
    monkeypatch.setattr(launch, "verify_launcher_identity", lambda manifest: {"fixture_only": True})
    monkeypatch.setattr(launch.budget, "read_ledger", lambda: {"remaining_unreserved_usd": "7.00"})
    monkeypatch.setattr(launch, "reserve_budget", lambda *args: {"fixture_only": True, "no_ledger_write": True})
    args = SimpleNamespace(approved_cap_usd="400.00", profile="fixture-only", subnet_id="subnet-abc",
                           receipt_dir=str(output), archive="never-uploaded.zip", source_sha="b" * 40,
                           sha256="a" * 64)
    result = launch.execute(args, plan(), {})
    assert result == json.loads((output / "launch_receipt.json").read_bytes())
    assert not launch.EXECUTION_LOCK_FILE.exists()
    return result, fake


@pytest.mark.parametrize("kind", ["role", "instance_profile", "security_group"])
def test_lost_auxiliary_create_response_recovers_exact_owned_identity_and_cleans_it(tmp_path, monkeypatch, kind):
    result, fake = execute_fake_lost_create(tmp_path, monkeypatch, kind)
    job = result["job"]
    key = job + "-worker" if kind == "role" else kind
    assert result["resource_intents"][key]["status"] == "OWNERSHIP_RECOVERED"
    assert key in result["resources"]
    assert result["cleanup_errors"] == []
    assert any(deleted_kind == kind for deleted_kind, _ in fake.deleted)
    assert result["termination_confirmed"] is True
    assert result["status"] == "AWS_JOB_BLOCKED_OR_FAILED"  # No actual run, never a success claim.
    assert any(event["event"] == "AUXILIARY_IDENTITY_RECOVERED" for event in result["events"])
    assert "NOT_CONFIRMED" not in result["s3_retention"]


def test_lost_bucket_create_without_atomic_tags_is_named_but_not_self_authorized(tmp_path, monkeypatch):
    result, fake = execute_fake_lost_create(tmp_path, monkeypatch, "bucket")
    expected = result["job"] + "-" + plan()["account_id"]
    intent = result["resource_intents"]["bucket"]
    assert intent["name"] == expected and intent["status"] == "OWNERSHIP_UNCONFIRMED"
    assert "bucket" not in result["resources"] and expected in fake.buckets
    assert fake.buckets[expected]["Tags"] == [] and fake.deleted == []
    assert fake.lookups == [("bucket", expected, {"ExpectedBucketOwner": plan()["account_id"]})]
    assert result["status"] == "CLEANUP_REQUIRES_ATTENTION"
    assert result["s3_retention"].startswith("NOT_CONFIRMED")


@pytest.mark.parametrize("kind", ["role", "instance_profile", "security_group", "bucket"])
def test_uncertain_resource_with_foreign_tag_is_never_admitted_for_deletion(tmp_path, monkeypatch, kind):
    result, fake = execute_fake_lost_create(tmp_path, monkeypatch, kind, deny_ownership=True)
    key = result["job"] + "-worker" if kind == "role" else kind
    assert result["resource_intents"][key]["status"] == "OWNERSHIP_UNCONFIRMED"
    assert key not in result["resources"]
    assert not any(deleted_kind == kind for deleted_kind, _ in fake.deleted)
    assert result["status"] == "CLEANUP_REQUIRES_ATTENTION"
    assert any(error.startswith("AUXILIARY_OWNERSHIP_UNCONFIRMED:") for error in result["cleanup_errors"])


def test_recovery_refuses_rewritten_resource_intent_before_provider_calls():
    job = "cas-meta3-fixture-only"
    result = {"job": job, "plan": plan(), "resources": {}, "cleanup_errors": [],
              "resource_intents": {"bucket": {"kind": "bucket", "name": "unrelated-bucket",
                  "job": job, "account_id": plan()["account_id"], "status": "CREATE_FAILED_OR_UNCERTAIN"}}}
    no_provider = SimpleNamespace(get_bucket_tagging=lambda **kwargs: (_ for _ in ()).throw(AssertionError("UNRELATED_LOOKUP")))
    events = []
    launch.reconcile_auxiliary_intents(no_provider, no_provider, no_provider, result, job,
                                      lambda event, **details: events.append(event))
    assert result["resources"] == {}
    assert result["resource_intents"]["bucket"]["status"] == "OWNERSHIP_UNCONFIRMED"
    assert "AUXILIARY_INTENT_SCOPE_MISMATCH" in result["cleanup_errors"][0]
    assert events == ["AUXILIARY_UNCONFIRMED_NOT_DELETED"]
