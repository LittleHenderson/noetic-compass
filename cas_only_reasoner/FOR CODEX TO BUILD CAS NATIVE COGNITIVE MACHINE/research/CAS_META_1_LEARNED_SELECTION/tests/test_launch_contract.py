"""Pure launcher checks: no AWS client, torch, GPU, or paid action."""
import hashlib
import ast
import importlib.util
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("meta1_aws_launch", ROOT / "aws" / "launch.py")
launch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launch)
PLAN = json.loads((ROOT / "aws" / "launch_plan.json").read_text())
SOURCE = "a" * 40
BASELINE = "0917267b1354e5d036263eaa6ba9a7197eafb776"


def archive_fixture(tmp_path, *, extra=None, manifest_change=None, lock=None):
    payload = {
        "research/pilot/cas_meta1/train.py": b"# not executed\n",
        "research/pilot/data/train.jsonl": b"{}\n",
        "research/pilot/requirements-gpu.txt": b"numpy==2.3.5\n",
        "wheels/base1.whl": b"wheel1",
        "wheels/base2.whl": b"wheel2",
    }
    if lock is not None: payload["research/pilot/requirements-gpu.txt"] = lock
    manifest = {"schema_version":1,"source_sha":SOURCE,"baseline_sha":BASELINE,
                "pilot_dir":"research/pilot","data_dir":"research/pilot/data",
                "dependency_lock":"research/pilot/requirements-gpu.txt",
                "wheel_paths":["wheels/base1.whl","wheels/base2.whl"],
                "files_sha256":{n:hashlib.sha256(v).hexdigest() for n,v in payload.items()}}
    if manifest_change: manifest_change(manifest)
    path = tmp_path / "payload.zip"
    with zipfile.ZipFile(path,"w") as z:
        for name,data in payload.items(): z.writestr(name,data)
        z.writestr("launch_manifest.json",json.dumps(manifest))
        if extra: z.writestr(*extra)
    return path, launch.digest(path)


def test_default_plan_does_not_import_boto_or_train(capsys):
    assert launch.main([]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["aws_actions_performed"] is False
    assert output["archive_verified"] is False
    assert output["plan"]["local_neural_execution"] is False


@pytest.mark.parametrize("cap", [None,"", "NaN", "Infinity", "-2", "0", "2", "3", "abc"])
def test_missing_or_different_cap_refuses(cap):
    with pytest.raises(launch.LaunchRefused): launch.validate_approval(cap,PLAN)


def test_exact_approval_only():
    launch.validate_approval("100.00",PLAN)
    with pytest.raises(launch.LaunchRefused):
        launch.validate_approval("100",{**PLAN,"automatic_retries":1})


@pytest.mark.parametrize("key,value",[("region","us-east-1"),("instance_type","g5.xlarge"),("artifact_bytes_max",2147483648),("ebs_encrypted",False),("s3_retention_days",30)])
def test_plan_expansion_needs_new_authority(key,value):
    with pytest.raises(launch.LaunchRefused): launch.validate_approval("100",{**PLAN,key:value})


def test_execute_without_cap_stops_before_cloud(capsys):
    assert launch.main(["--execute"]) == 2
    assert "EXPLICIT_100_USD_TASK_APPROVAL_REQUIRED" in capsys.readouterr().out


def test_valid_archive(tmp_path):
    path,sha = archive_fixture(tmp_path)
    manifest = launch.validate_archive(path,sha,SOURCE,PLAN)
    assert manifest["baseline_sha"] == BASELINE


def test_wrong_archive_digest(tmp_path):
    path,_ = archive_fixture(tmp_path)
    with pytest.raises(launch.LaunchRefused,match="ARCHIVE_SHA_MISMATCH"):
        launch.validate_archive(path,"0"*64,SOURCE,PLAN)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/absolute", "a\\b", "a/../b", "a//b"])
def test_archive_path_refusal(name):
    with pytest.raises(launch.LaunchRefused): launch.safe_relative(name)


def test_unmanifested_archive_entry(tmp_path):
    path,sha = archive_fixture(tmp_path,extra=("extra.txt",b"not declared"))
    with pytest.raises(launch.LaunchRefused,match="COVERAGE"):
        launch.validate_archive(path,sha,SOURCE,PLAN)


def test_nonaccepted_baseline(tmp_path):
    path,sha = archive_fixture(tmp_path,manifest_change=lambda m:m.update(baseline_sha="c"*40))
    with pytest.raises(launch.LaunchRefused,match="BASELINE"):
        launch.validate_archive(path,sha,SOURCE,PLAN)


def test_matching_baseline_prefix_is_not_full_identity(tmp_path):
    path,sha = archive_fixture(tmp_path,manifest_change=lambda m:m.update(baseline_sha="0917267b"+"b"*32))
    with pytest.raises(launch.LaunchRefused,match="BASELINE"):
        launch.validate_archive(path,sha,SOURCE,PLAN)


def test_wrong_source_sha(tmp_path):
    path,sha = archive_fixture(tmp_path)
    with pytest.raises(launch.LaunchRefused,match="SOURCE"):
        launch.validate_archive(path,sha,"d"*40,PLAN)


def test_size_ceiling(tmp_path):
    path,sha = archive_fixture(tmp_path)
    with pytest.raises(launch.LaunchRefused,match="SIZE_CEILING"):
        launch.validate_archive(path,sha,SOURCE,{**PLAN,"archive_expanded_bytes_max":1})


def test_symlink_archive_rejected(tmp_path):
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    path,sha = archive_fixture(tmp_path,extra=(info,b"target"))
    with pytest.raises(launch.LaunchRefused,match="SYMLINK"):
        launch.validate_archive(path,sha,SOURCE,PLAN)


@pytest.mark.parametrize("lock",[b"numpy>=2\n",b"-r elsewhere.txt\n",b"--extra-index-url https://example.com\n",b"torch==2.11.0+cpu\n",b"torch==2.11.0\n"])
def test_gpu_lock_cannot_redirect_or_replace_torch(tmp_path,lock):
    path,sha = archive_fixture(tmp_path,lock=lock)
    with pytest.raises(launch.LaunchRefused,match="EXACT_PINS"):
        launch.validate_archive(path,sha,SOURCE,PLAN)


def test_owned_instance_only():
    launch.check_tag([{"Key":"cas_meta_job","Value":"this-job"}],"this-job")
    with pytest.raises(launch.LaunchRefused): launch.check_tag([],"this-job")
    with pytest.raises(launch.LaunchRefused): launch.check_tag([{"Key":"cas_meta_job","Value":"another"}],"this-job")


def test_remote_script_is_syntactically_valid_and_cuda_only():
    config = {**PLAN,"bucket":"cas-meta1-test","job":"cas-meta1-test","archive_sha256":"f"*64,"manifest":{}}
    source = launch.remote_program(config)
    compile(source,"<remote-only>","exec") # syntax only, deliberately never exec
    assert "torch.cuda.is_available()" in source
    assert "torch.__version__=='2.11.0+cu128'" in source
    assert source.index("CLOUD_DEADLINE_NOT_CONFIRMED") < source.index("pip','install")
    assert "cas_meta1.train" in source
    assert "CAS_META1_SOURCE_SHA" in source
    assert source.index("CUBLAS_WORKSPACE_CONFIG") < source.index("torch.cuda.is_available()")
    assert source.index("PYTHONDONTWRITEBYTECODE") < source.index("torch.cuda.is_available()")
    assert "'CAS_META1_RUN_GPU_TESTS'" in source
    assert "{'tests':4,'failures':0,'errors':0,'skipped':0}" in source
    assert source.index("GPU_CONTRACT_TESTS_MUST_REPORT_EXACTLY_FOUR_PASSED") < source.index("cas_meta1.train")
    assert "package / m['pilot_dir'] / 'runs' / 'cloud_job'" in source
    bootstrap = launch.user_data(config)
    assert len(bootstrap.encode()) <= 16384
    assert "shutdown -h now" in bootstrap
    assert "(3,11)" in bootstrap


def test_frozen_runtime_paths_not_installed_from_source():
    source = launch.remote_program({})
    assert "'--no-deps'" in source
    assert "pip','install','-e'" not in source


class FakeEC2:
    def __init__(self,instances): self.instances = instances
    def describe_instances(self,**arguments):
        self.arguments = arguments
        return {"Reservations":[{"Instances":self.instances}]}


def test_lost_launch_response_recovers_only_exact_tag_and_token():
    instance = {"InstanceId":"i-new","Tags":[{"Key":"cas_meta_job","Value":"job"}],"ClientToken":"job"}
    provider = FakeEC2([instance])
    assert launch.reconcile_instance(provider,"job") == instance
    assert provider.arguments["Filters"] == [{"Name":"tag:cas_meta_job","Values":["job"]},{"Name":"client-token","Values":["job"]}]


@pytest.mark.parametrize("instances",[[],[{},{}],[{"Tags":[{"Key":"cas_meta_job","Value":"job"}],"ClientToken":"other"}]])
def test_uncertain_launch_never_claims_no_instance(instances):
    with pytest.raises(launch.LaunchRefused,match="TERMINATION_UNCONFIRMED"):
        launch.reconcile_instance(FakeEC2(instances),"job")


@pytest.mark.parametrize("field,bad",[("State","DISABLED"),("ScheduleExpression","at(wrong)"),("ScheduleExpressionTimezone","PST"),("FlexibleTimeWindow",{"Mode":"FLEXIBLE"}),("ActionAfterCompletion","NONE")])
def test_schedule_full_confirmation(field,bad):
    target = {"Arn":"terminate","RoleArn":"newrole","Input":"newinstance","RetryPolicy":{"MaximumRetryAttempts":0,"MaximumEventAgeInSeconds":60}}
    actual = {"State":"ENABLED","ScheduleExpression":"at(exact)","ScheduleExpressionTimezone":"UTC","FlexibleTimeWindow":{"Mode":"OFF"},"ActionAfterCompletion":"DELETE","Target":target}
    launch.verify_schedule(actual,target,"at(exact)")
    with pytest.raises(launch.LaunchRefused): launch.verify_schedule({**actual,field:bad},target,"at(exact)")


def test_schedule_cannot_change_target_action_or_retry():
    target = {"Arn":"terminate","RoleArn":"newrole","Input":"newinstance","RetryPolicy":{"MaximumRetryAttempts":0,"MaximumEventAgeInSeconds":60}}
    actual = {"State":"ENABLED","ScheduleExpression":"at(exact)","ScheduleExpressionTimezone":"UTC","FlexibleTimeWindow":{"Mode":"OFF"},"ActionAfterCompletion":"DELETE","Target":{**target,"Arn":"other"}}
    with pytest.raises(launch.LaunchRefused): launch.verify_schedule(actual,target,"at(exact)")


def test_oversize_output_preserves_failure_packet_checkpoint_and_log_tail(tmp_path):
    artifacts = tmp_path/"results"; artifacts.mkdir()
    (artifacts/"checkpoint.pt").write_bytes(b"fixture weights")
    (artifacts/"training.log").write_bytes(b"x"*(8*1024*1024)+b"FINAL ERROR")
    bundle = tmp_path/"bounded.zip"
    record = launch.build_evidence_bundle(artifacts,bundle,8*1024*1024,{"returncode":0,"job":"fixture"})
    assert record["returncode"] == 1 and record["partial_evidence"]
    assert record["omitted_full_file_count"] == 1
    assert len(record["original_file_index_sha256"]) == 64
    assert bundle.stat().st_size < 8*1024*1024
    with zipfile.ZipFile(bundle) as z:
        assert z.read("checkpoint.pt") == b"fixture weights"
        assert z.read("failure_log_tails/training.log").endswith(b"FINAL ERROR")
        assert json.loads(z.read("artifact_collection_receipt.json"))["returncode"] == 1


def test_small_output_is_fully_preserved(tmp_path):
    artifacts = tmp_path/"results"; artifacts.mkdir()
    (artifacts/"result.json").write_text("{}")
    record = launch.build_evidence_bundle(artifacts,tmp_path/"full.zip",8*1024*1024,{"returncode":0})
    assert record["returncode"] == 0 and not record["partial_evidence"]
    assert record["omitted_full_file_count"] == 0


def test_task_budget_reservation_is_durable_and_never_automatically_refunded(tmp_path):
    ledger = tmp_path/"ledger.json"
    result = launch.reserve_budget(ledger,"cas-meta1-test1",SOURCE,"f"*64,PLAN)
    assert result["total_reserved_usd"] == "2"
    assert json.loads(ledger.read_text())["reservations"][0]["reserved_usd"] == "2.00"
    assert not ledger.with_suffix(".json.lock").exists()
    with pytest.raises(launch.LaunchRefused,match="ALREADY_RESERVED"):
        launch.reserve_budget(ledger,"cas-meta1-test1",SOURCE,"f"*64,PLAN)
    second = launch.reserve_budget(ledger,"cas-meta1-test2",SOURCE,"f"*64,PLAN)
    assert second["total_reserved_usd"] == "4"


def test_task_budget_stops_after_fifty_two_dollar_reservations(tmp_path):
    ledger = tmp_path/"ledger.json"
    for i in range(50): launch.reserve_budget(ledger,f"cas-meta1-test{i}",SOURCE,"f"*64,PLAN)
    before = ledger.read_bytes()
    with pytest.raises(launch.LaunchRefused,match="BUDGET_EXHAUSTED"):
        launch.reserve_budget(ledger,"cas-meta1-excess",SOURCE,"f"*64,PLAN)
    assert ledger.read_bytes() == before


def test_budget_lock_refuses_concurrent_or_crashed_owner(tmp_path):
    ledger = tmp_path/"ledger.json"
    lock = ledger.with_suffix(".json.lock"); lock.write_text("existing lock")
    with pytest.raises(launch.LaunchRefused,match="LOCKED"):
        launch.reserve_budget(ledger,"cas-meta1-blocked",SOURCE,"f"*64,PLAN)
    assert lock.read_text() == "existing lock" and not ledger.exists()


def test_budget_wrong_amount_is_not_accepted(tmp_path):
    ledger = tmp_path/"ledger.json"
    ledger.write_text(json.dumps({"schema_version":1,"owner_task_cap_usd":"100.00","reservations":[{"job":"cas-meta1-existing","reserved_usd":"0.00"}]}))
    with pytest.raises(launch.LaunchRefused,match="INVALID_BUDGET"):
        launch.reserve_budget(ledger,"cas-meta1-new",SOURCE,"f"*64,PLAN)


def test_local_launcher_must_match_pinned_archive():
    hashes = {"research/pilot/aws/"+p.name:launch.digest(p) for p in (Path(launch.__file__),launch.PLAN_FILE)}
    manifest = {"pilot_dir":"research/pilot","files_sha256":hashes}
    assert launch.verify_launcher_identity(manifest) == hashes
    hashes["research/pilot/aws/launch.py"] = "0"*64
    with pytest.raises(launch.LaunchRefused,match="LAUNCHER_ARCHIVE"):
        launch.verify_launcher_identity(manifest)


def test_size_sampler_tolerates_disappearing_sqlite_files():
    def missing(): raise FileNotFoundError("closed database WAL")
    gone = SimpleNamespace(is_file=lambda:True,stat=missing)
    present = SimpleNamespace(is_file=lambda:True,stat=lambda:SimpleNamespace(st_size=12))
    root = SimpleNamespace(rglob=lambda pattern:[gone,present])
    assert launch.sample_artifact_bytes(root) == 12


def test_monitor_error_stops_child_before_artifact_packaging(tmp_path):
    # Execute only the bookkeeping function with a fake child, never remote/GPU code.
    tree = ast.parse(launch.remote_program({}))
    function = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == "bounded_process")
    class FakeChild:
        returncode = None
        def poll(self): return self.returncode
        def terminate(self): self.terminated = True; self.returncode = -15
        def wait(self,timeout): self.waited = True; return self.returncode
        def kill(self): raise AssertionError("termination should succeed")
    child = FakeChild()
    def broken_monitor(root): raise OSError("monitor read failure")
    namespace = {"time":SimpleNamespace(time=lambda:0,sleep=lambda seconds:None),
                 "subprocess":SimpleNamespace(Popen=lambda *a,**k:child,STDOUT=-2,TimeoutExpired=TimeoutError),
                 "sample_artifact_bytes":broken_monitor,"artifact_root":tmp_path,
                 "CONFIG":{"artifact_bytes_max":1073741824}}
    exec(compile(ast.Module(body=[function],type_ignores=[]),"<bookkeeping-only>","exec"),namespace)
    with pytest.raises(OSError,match="monitor read failure"):
        namespace["bounded_process"](["fake"],tmp_path/"fake.log",env={},cwd=tmp_path,seconds=60,deadline=3600)
    assert child.terminated and child.waited
