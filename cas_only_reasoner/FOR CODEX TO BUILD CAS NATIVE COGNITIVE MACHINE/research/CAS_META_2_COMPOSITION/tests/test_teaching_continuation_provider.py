"""Real-shaped AWS fakes only; no canonical budget or provider access."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from aws import teaching_continuation_provider as subject, teaching_continuation_plan as plan
from aws import teaching_cycle_remote as base, teaching_continuation_remote as remote

def helper(name):
    spec = importlib.util.spec_from_file_location("_provider_" + name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
old = helper("test_teaching_cycle_provider")
pt = helper("test_teaching_continuation_plan")

class Cloud(old.Cloud):
    def call(self, service, method, args):
        if method == "put_object" and hasattr(args["Body"], "read"):
            args = {**args, "Body": args["Body"].read()}
        return super().call(service, method, args)

@pytest.fixture
def setup(tmp_path, monkeypatch):
    cloud, now = Cloud(), [1000.0]
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    ledger, pricing, prior, manifest = [tmp_path / n for n in ("ledger.json", "pricing.json", "prior.zip", "prior.json")]
    ledger.write_bytes(b"{}\n")
    prior.write_bytes(b"synthetic prior zip")
    manifest.write_bytes(b"{}\n")
    prices = pt.prices()
    price_doc = {"schema": subject.continuation_checks.SCHEMA, "raw_prices": prices,
        "cost_worksheet": plan.worksheet(prices),
        "source_sha256": sha256(Path(subject.continuation_checks.__file__).read_bytes()).hexdigest(),
        "base_preflight_sha256": sha256(Path(subject.checks.__file__).read_bytes()).hexdigest(),
        "plan_sha256": sha256(Path(plan.__file__).read_bytes()).hexdigest()}
    pricing.write_bytes(subject.canonical(price_doc))
    pins, c = pt.bindings(), pt.continuation()
    dependencies = {"explicit synthetic dependency map": "a" * 64}
    monkeypatch.setattr(subject, "source_dependencies", lambda: dependencies)
    monkeypatch.setattr(subject.generic.budget, "validate_state", lambda value: value)
    pins.update(provider_source_sha256=sha256(Path(subject.__file__).read_bytes()).hexdigest(),
        provider_dependencies_sha256=plan.canonical_sha256(dependencies),
        guest_driver_sha256=sha256(Path(remote.__file__).read_bytes()).hexdigest(),
        bootstrap_sha256=sha256(Path(subject.bootstrap.__file__).read_bytes()).hexdigest(),
        pricing_receipt_sha256=sha256(pricing.read_bytes()).hexdigest())
    c.update(prior_state_archive_sha256=sha256(prior.read_bytes()).hexdigest(),
        prior_state_manifest_sha256=sha256(manifest.read_bytes()).hexdigest(),
        prior_state_archive_bytes=prior.stat().st_size, prior_state_expanded_bytes=4,
        prior_package_validator_sha256=sha256(Path(subject.prior_package.__file__).read_bytes()).hexdigest(),
        restore_probe_sha256=sha256(Path(subject.ROOT / "aws/teaching_cycle_restore_probe.py").read_bytes()).hexdigest(),
        continuation_plan_sha256=sha256(Path(plan.__file__).read_bytes()).hexdigest())
    request = plan.build_request(job=old.JOB, logical_run_id=plan.LOGICAL_RUN_ID,
        bindings=pins, continuation=c, ledger=pt.ledger())
    arms = {arm: {"committed_optimizer_steps": 56} for arm in base.ARMS}
    monkeypatch.setattr(subject.prior_package, "validate_package",
        lambda *args, **kwargs: {"expanded_bytes": 1, "arms": arms})
    context = {"request": request, "job": old.JOB, "run_id": plan.LOGICAL_RUN_ID, "bindings": pins, "continuation": c,
        "resource_plan": request["resource_plan"], "request_sha256": plan.canonical_sha256(request),
        "receipt_dir": str(evidence), "ledger_path": str(ledger), "started_unix": 1000.0, "deadline_unix": 8200.0,
        "prior_state_archive_path": str(prior), "prior_state_manifest_path": str(manifest), "prior_arms": arms}
    reservations = []
    def reserve(*args):
        reservations.append(args)
        return {"reservation": {"job": old.JOB}, "simulated": True}
    def observer(clients):
        return {**price_doc, "account_id": clients["sts"].get_caller_identity()["Account"],
            "region": "us-west-2", "instance_type": "g7.2xlarge", "read_only": True, "conflicting_resources": []}
    provider = subject.TeachingContinuationProvider(
        clients={name: cloud.client(name) for name in ("sts", "s3", "ec2", "iam", "scheduler")},
        source_archive=subject.ROOT / "records/teaching_cycle_001/bundle_002/training.zip",
        guest_driver=remote.__file__, pricing_receipt_path=pricing, ledger_path=ledger,
        clock=lambda: now[0], sleeper=lambda sec: now.__setitem__(0, now[0] + sec),
        budget_module=SimpleNamespace(reserve_budget=reserve), observer=observer, monotonic_clock=lambda: now[0])
    return provider, context, cloud, reservations, now

def start(s):
    p,c,cloud,reservations,now=s
    p.preflight(c)
    p.reserve(c)
    c["launch"]=p.launch(c)
    return s

def test_new_cloud_instance_preserves_logical_run_and_release_order(setup):
    p,c,cloud,reservations,now=start(setup)
    config=json.loads(cloud.objects["input/config.json"])
    permit=json.loads(cloud.objects["input/permit.json"])
    remote.validate_config(config,sha256(cloud.objects["input/config.json"]).hexdigest(),permit,base)
    assert config["job"] != config["run_id"] == plan.LOGICAL_RUN_ID
    assert len(reservations)==1
    calls=[(m,a) for _,m,a in cloud.calls]
    assert len([m for m,_ in calls if m=="run_instances"])==1
    assert calls.index(next(row for row in calls if row[0]=="get_schedule")) < calls.index(next(row for row in calls if row[0]=="put_object" and row[1]["Key"]=="input/permit.json"))
    assert not any(key in cloud.objects for key in ("input/train_release.json","input/public.json"))
    assert cloud.objects["input/prior_state.zip"]==Path(c["prior_state_archive_path"]).read_bytes()
    policy=[json.loads(a["PolicyDocument"]) for m,a in calls if m=="put_role_policy" and a["RoleName"].endswith("-worker")][0]
    get=next(row for row in policy["Statement"] if row["Action"]==["s3:GetObject"])
    assert any(path.endswith("/input/train_release.json") for path in get["Resource"])
    assert any(path.endswith("/input/prior_state.zip") for path in get["Resource"])

@pytest.mark.parametrize("key",["provider_source_sha256","provider_dependencies_sha256","guest_driver_sha256"])
def test_local_pin_refusal_precedes_any_cloud_call(setup,key):
    p,c,cloud,_,_=setup
    c["bindings"][key]="f"*64
    c["request"]["bindings"][key]="f"*64
    c["request_sha256"]=plan.canonical_sha256(c["request"])
    with pytest.raises(ValueError):
        p.preflight(c)
    assert not cloud.calls

def test_bad_schedule_cannot_release_worker(setup):
    p,c,cloud,_,_=setup
    cloud.bad_schedule=True
    with pytest.raises(ValueError,match="SCHEDULE_READBACK"):
        start(setup)
    assert "input/permit.json" not in cloud.objects

def release_doc(c):
    return {"schema":"cas-teaching-continuation-train-release/1","job":c["job"],"run_id":c["run_id"],
        "continuation_sha256":plan.canonical_sha256(c["continuation"]),
        "restore_ready_sha256":c.get("restore_ready_sha256"),"restore_receipt_sha256":c.get("restore_receipt_sha256"),
        "automatic_retries":0}

def test_training_release_requires_independent_restore_and_is_one_shot(setup):
    p,c,cloud,_,_=start(setup)
    with pytest.raises(ValueError,match="CONTINUATION_RELEASE"):
        p.release_training(c,release_doc(c))
    c.update(restore_ready_sha256="a"*64,restore_receipt_sha256="b"*64)
    result=p.release_training(c,release_doc(c))
    assert result["uploaded"] and result["release_sha256"]==sha256(cloud.objects["input/train_release.json"]).hexdigest()
    with pytest.raises(ValueError,match="ONE_RESTORE"):
        p.release_training(c,release_doc(c))

def test_waits_fetch_the_actual_continuation_keys(setup):
    p,c,cloud,_,_=start(setup)
    cloud.objects.update({"results/restore_ready.json":b"{}\n","results/restore/restore_receipt.json":b"{}\n"})
    assert p.wait_restore(c,100)["probe"]["key"]=="results/restore/restore_receipt.json"
    cloud.objects.update({"results/train_ready.json":b"{}\n","results/train_continued_001/campaign_summary.json":b"{}\n"})
    assert p.wait_training(c,100)["campaign"]["key"]=="results/train_continued_001/campaign_summary.json"

def test_progress_poll_reads_new_key_once_and_rejects_old_history(setup,capsys):
    p,c,cloud,_,_=start(setup)
    event={"sequence":57,"intent_sha256":"a"*64,"receipt":{"schema":"cas-teaching-binding-cuda/1",
        "run_id":c["run_id"]+".aligned.cas","execution_mode":"cuda","accepted_weights_updated":False,
        "optimizer_steps":1,"cumulative_optimizer_steps":57}}
    raw=subject.canonical(event)
    marker={"schema":"cas-teaching-continuation-progress/1","job":c["job"],"run_id":c["run_id"],
        "request_sha256":c["request_sha256"],"source_sha256":c["bindings"]["source_sha256"],
        "manifest_sha256":c["bindings"]["manifest_sha256"],"arm":"cas.aligned","prior_optimizer_steps":56,
        "event":{"key":"train/campaign/cas.aligned/events/step-00000057.result.json","raw_utf8":raw.decode(),
            "sha256":sha256(raw).hexdigest(),"bytes":len(raw)},
        "boundary":"WORKER_REPORTED_NEW_CUDA_UPDATE_NOT_INDEPENDENT_LEARNING_PROOF"}
    cloud.objects["results/new_update.json"]=subject.canonical(marker)
    p._observe_first_update()
    p._observe_first_update()
    assert Path(c["receipt_dir"],"new_update.json").read_bytes()==cloud.objects["results/new_update.json"]
    assert len([a for _,m,a in cloud.calls if m=="get_object" and a["Key"]=="results/new_update.json"])==1
    assert "cumulative_optimizer_steps" in capsys.readouterr().out
    marker["prior_optimizer_steps"]=0
    changed=subject.canonical(marker)
    with pytest.raises(ValueError,match="PRIOR_UPDATE_COUNT"):
        subject.validate_first_update({"raw_utf8":changed.decode(),"sha256":sha256(changed).hexdigest(),
            "bytes":len(changed),"key":"results/new_update.json"},c)

def test_cleanup_retains_result_copy_and_never_relaunches(setup):
    p,c,cloud,_,_=start(setup)
    cloud.objects["results/artifacts.zip"]=b"synthetic durable evidence"
    result=p.cleanup(c,retain_cloud_copy=True)
    assert result["compute_closed"] and result["cloud_copy_deleted"] is False
    assert cloud.objects["results/artifacts.zip"]==b"synthetic durable evidence"
    assert len([1 for _,m,_ in cloud.calls if m=="run_instances"])==1

def test_no_second_launch(setup):
    p,c,*_=start(setup)
    with pytest.raises(ValueError,match="ONE_RESERVED"):
        p.launch(c)

