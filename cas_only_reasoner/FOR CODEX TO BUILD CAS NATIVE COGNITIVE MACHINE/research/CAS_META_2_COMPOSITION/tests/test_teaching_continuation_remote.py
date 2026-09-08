"""Pure continuation process/transport fixtures; no model or cloud execution."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile
import pytest
from aws import teaching_continuation_remote as remote, teaching_cycle_remote as base
from aws import teaching_continuation_plan as plan, teaching_continuation_bootstrap as bootstrap

def helper(name):
    spec = importlib.util.spec_from_file_location("_remote_" + name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

old = helper("test_teaching_cycle_remote")
pt = helper("test_teaching_continuation_plan")

class Processes(old.FakeProcesses):
    def start(self, command, *, cwd, env, stdout_path, stderr_path):
        output = Path(command[command.index("--output") + 1])
        label = "train" if output.name == "train_continued_001" else output.name
        assert (Path(cwd) / "driver" / (label + ".intent.json")).is_file()
        assert not output.exists()
        self.commands.append(command)
        self.events.append(("start", label))
        output.mkdir()
        Path(stdout_path).write_bytes(b"synthetic process only\n")
        Path(stderr_path).write_bytes(b"")
        if label == "restore":
            assert "--prior-archive" in command and "--run-id" in command
            b, c = self.config["bindings"], self.config["continuation"]
            proof = {"schema": "cas-teaching-gpu-restore/1", "status": "RESTORED_NO_TRAINING",
                "job": self.config["job"], "run_id": self.config["run_id"], "source_sha256": b["source_sha256"],
                "bundle_manifest_sha256": b["manifest_sha256"], "material_sha256": b["material_receipt_sha256"],
                "prior_archive_sha256": c["prior_state_archive_sha256"], "prior_manifest_sha256": c["prior_state_manifest_sha256"],
                "summary_sha256": c["prior_summary_sha256"], "probe_sha256": c["restore_probe_sha256"],
                "input_tree_unchanged": True, "optimizer_steps_performed": 0, "predictions_run": False}
            if getattr(self, "bad_restore", False):
                proof["optimizer_steps_performed"] = 1
            tree = {"files": len(self.manifest["members"]), "bytes": self.manifest["expanded_bytes"],
                    "sha256": plan.canonical_sha256(self.manifest["members"])}
            proof.update(source_archive_sha256=b["archive_sha256"], validator_sha256=c["prior_package_validator_sha256"],
                actual_restore="FOUR_ARMS_RESTORED", pid=200, wall_seconds=1.0,
                instance={"instanceId": "i-0123456789abcdef0", "accountId": "807562639912", "region": "us-west-2", "instanceType": "g7.2xlarge"},
                environment={"torch": "2.11.0+cu128", "cuda": "12.8", "gpu": "NVIDIA RTX PRO 4500", "device": "cuda:0"},
                prior_tree_before=tree, prior_tree_after=tree, arms={})
            for arm, prior in self.manifest["arms"].items():
                proof["arms"][arm] = {**prior, "optimizer_state_sha256": "7" * 64, "saved_optimizer_state_sha256": "7" * 64,
                    "scope_sha256": "8" * 64, "record_registry_sha256": "9" * 64,
                    "training_cases_sha256": b["training_cases_sha256"], "initial_state_sha256": old.h(arm.split(".")[0] + "initialstate"),
                    "optimizer_steps_performed": 0, "predictions_run": False, "optimizer_tensors_device_checked": 9}
            base.write(output / "restore_receipt.json", proof)
        elif label == "train":
            assert self.transport.train_released
            assert "--resume-summary" in command and "--public-sets" not in command
            assert command[command.index("--run-id") + 1] == remote.LOGICAL_RUN
            # Synthetic checkpoint metadata only; actual runtime proof has its own suite.
            self.summary = old.campaign(self.config, Path(cwd) / "train", complete=self.complete)
            for arm, row in self.summary["arms"].items():
                for key in ("initial_checkpoint", "selected_checkpoint"):
                    ref = row[key]
                    ref["path"] = remote.CAMPAIGN_ROOT + f"/{arm}/journal/txn-{ref['transaction']:08d}/candidate.pt"
            self.summary.update(resumed_summary_sha256=self.config["continuation"]["prior_summary_sha256"],
                campaign_root=remote.CAMPAIGN_ROOT)
            base.write(output / "campaign_summary.json", self.summary)
            if getattr(self, "change_prior", False):
                (Path(cwd) / "train/campaign_summary.json").write_bytes(b"changed")
        else:
            assert self.transport.public_released and "--campaign-summary" in command
            assert Path(command[command.index("--campaign-summary") + 1]) == Path(cwd) / remote.LATEST_SUMMARY
            artifacts = {}
            for arm in base.ARMS:
                for version in ("untrained", "trained"):
                    for split in base.SPLITS:
                        name = f"{arm}.{version}.{split}.json"
                        artifacts[name] = base.write(output / name, {"predictions": [0] * 64, "synthetic": True})
            base.write(output / "prediction_seal.json", {"schema": "cas-teaching-blind-prediction-seal/1",
                "source_sha256": self.config["bindings"]["source_sha256"], "artifacts": artifacts, "private_targets_opened": False,
                "native_execution": "UNEXECUTED"})
        child = old.FakeChild(self, 200 if self.same_pid else 200 + len(self.children),
            self.duration.get(label, 1), self.exit_code.get(label, 0))
        self.children.append(child)
        return child

class Transport(old.FakeTransport):
    def __init__(self, config, processes, files):
        super().__init__(config, processes)
        self.files = files
        self.train_released = self.public_released = False
        self.bad_release = None
    def download(self, key, destination, maximum, deadline):
        self.events.append(("download", key))
        raw = self.public if key == "input/public.json" else self.files[key]
        assert len(raw) <= maximum and not Path(destination).exists()
        Path(destination).write_bytes(raw)
    def fetch_optional(self, key, maximum, deadline):
        self.events.append(("poll", key))
        ready_key = "results/restore_ready.json" if key == "input/train_release.json" else "results/train_ready.json"
        assert ready_key in self.uploads
        raw_ready = self.uploads[ready_key]
        ready = base.parse(raw_ready)
        release = {"schema": "cas-teaching-continuation-train-release/1" if key == "input/train_release.json" else "cas-teaching-public-release/1",
            **{k: ready[k] for k in ("job", "run_id", "source_sha256", "manifest_sha256", "material_sha256", "continuation_sha256")},
            "automatic_retries": 0}
        if key == "input/train_release.json":
            release.update(restore_ready_sha256=sha256(raw_ready).hexdigest(),
                restore_receipt_sha256=ready["restore_receipt"]["sha256"])
            self.train_released = True
        else:
            release.update(restore_ready_sha256=ready["restore_ready_sha256"],
                restore_receipt_sha256=ready["restore_receipt_sha256"],
                training_ready_sha256=sha256(raw_ready).hexdigest(),
                campaign_summary_sha256=ready["campaign_summary"]["sha256"],
                public_sets={"key": "input/public.json", "sha256": sha256(self.public).hexdigest(), "bytes": len(self.public)})
            self.public_released = True
        if self.bad_release:
            release[self.bad_release] = "f" * 64
        return base.canonical(release) + b"\n"

@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path / "job"
    monkeypatch.setattr(remote, "CAMPAIGN_ROOT", (root / "train/campaign").as_posix())
    support = tmp_path / "support"
    support.mkdir()
    for name, source in (("base_remote.py", Path(base.__file__)),
                         ("continuation_package.py", Path(remote.__file__).resolve().parents[1] / "cas_meta2/teaching_cycle/continuation_package.py"),
                         ("restore_probe.py", Path(remote.__file__).with_name("teaching_cycle_restore_probe.py"))):
        (support / name).write_bytes(source.read_bytes())
    b, c = pt.bindings(), pt.continuation()
    b["guest_driver_sha256"] = base.file_hash(remote.__file__)["sha256"]
    b["public_sets_sha256"] = sha256(old.public_bytes()).hexdigest()
    c.update(original_campaign_root=remote.CAMPAIGN_ROOT,
        base_guest_driver_sha256=remote.BASE_SHA,
        prior_package_validator_sha256=base.file_hash(support / "continuation_package.py")["sha256"],
        restore_probe_sha256=base.file_hash(support / "restore_probe.py")["sha256"])
    files = {"train/campaign_summary.json": b'{"synthetic":"prior summary"}\n',
             "train/campaign/cas.aligned/journal/txn-00000000/prior.raw": b"synthetic prior bytes"}
    manifest = {"original_campaign_root": remote.CAMPAIGN_ROOT,
        "members": {k: {"sha256": sha256(v).hexdigest(), "bytes": len(v)} for k, v in files.items()},
        "expanded_bytes": sum(map(len, files.values())),
        "arms": {arm: {"committed_optimizer_steps": 56} for arm in base.ARMS}}
    manifest_raw = base.canonical(manifest) + b"\n"
    zipped = io.BytesIO()
    with ZipFile(zipped, "w") as z:
        for k, v in files.items():
            z.writestr(k, v)
        z.writestr("manifest.json", manifest_raw)
    prior_raw = zipped.getvalue()
    c.update(prior_state_archive_sha256=sha256(prior_raw).hexdigest(),
        prior_state_manifest_sha256=sha256(manifest_raw).hexdigest(),
        prior_summary_sha256=sha256(files["train/campaign_summary.json"]).hexdigest(),
        prior_state_archive_bytes=len(prior_raw), prior_state_expanded_bytes=manifest["expanded_bytes"] + len(manifest_raw))
    resource = plan.resource_plan()
    config = {"schema": remote.SCHEMA, "job": old.JOB, "run_id": remote.LOGICAL_RUN,
        "bindings": b, "continuation": c, "resource_plan": resource,
        "resource_plan_sha256": plan.canonical_sha256(resource), "request_sha256": "a" * 64,
        "bucket": old.JOB + "-807562639912", "prefix": "", "launch_started_unix": 1000.0, "deadline_unix": 8200.0}
    config_sha = sha256(base.canonical(config) + b"\n").hexdigest()
    permit = {"schema": base.PERMIT_SCHEMA, "job": old.JOB, "run_id": remote.LOGICAL_RUN,
        "config_sha256": config_sha, "request_sha256": config["request_sha256"], "deadline_unix": 8200.0,
        "instance_id": "i-0123456789abcdef0", "shutdown_schedule_confirmed": True, "automatic_retries": 0,
        "shutdown_schedule_arn": "arn:aws:scheduler:us-west-2:807562639912:schedule/default/" + old.JOB}
    clock = old.FakeClock()
    processes = Processes(config, clock)
    processes.manifest = manifest
    transport = Transport(config, processes, {"input/source.zip": b"synthetic source",
        "input/prior_state.zip": prior_raw, "input/prior_state_manifest.json": manifest_raw})
    processes.transport = transport
    actual_base, actual_validator = remote.load_support(support, c)
    monkeypatch.setattr(actual_base, "extract_training", lambda archive, target, pins: target.mkdir())
    monkeypatch.setattr(remote, "load_support", lambda directory, pins: (actual_base, actual_validator))
    validator = SimpleNamespace(validate_package=lambda *args, **kwargs: manifest)
    return SimpleNamespace(config=config, permit=permit, config_sha=config_sha, root=root, support=support,
        clock=clock, processes=processes, transport=transport, validator=validator, manifest=manifest, files=files)

def execute(s):
    return remote.execute(s.config, s.root, config_sha256=s.config_sha, permit=s.permit, python="/fake/python",
        transport=s.transport, processes=s.processes, clock=s.clock, support_dir=s.support, validator_override=s.validator)

def test_restore_gate_then_train_then_two_fresh_predictions(setup):
    result = execute(setup)
    assert result["status"] == "COMPLETE", result
    assert len(result["processes"]) == 4
    assert len({row["pid"] for row in result["processes"]}) == 4
    events = setup.transport.events
    assert events.index(("upload", "results/restore_ready.json")) < events.index(("poll", "input/train_release.json"))
    assert events.index(("upload", "results/train_ready.json")) < events.index(("download", "input/public.json"))
    assert events[-1] == ("upload", "results/complete.json")
    assert result["resources"]["uploaded_bytes"] == sum(map(len, setup.transport.uploads.values()))
    assert result["resources"]["s3_api_attempts_upper_bound"] == sum(1 if kind == "upload" else 2 for kind, _ in events)
    with ZipFile(io.BytesIO(setup.transport.uploads["results/artifacts.zip"])) as zipped:
        assert zipped.read("train/campaign_summary.json") == setup.files["train/campaign_summary.json"]
        assert "train_continued_001/campaign_summary.json" in zipped.namelist()
        assert "input/prior_state.zip" in zipped.namelist()
        assert "restore/restore_receipt.json" in zipped.namelist()

def test_incomplete_preserves_history_and_never_requests_public(setup):
    setup.processes.complete = False
    result = execute(setup)
    assert result["status"] == "TEACHING_INCOMPLETE", result
    assert len(result["processes"]) == 2 and result["artifact"]
    assert not setup.transport.public_released
    assert not any(key == "input/public.json" for _, key in setup.transport.events)

@pytest.mark.parametrize("phase, count", [("restore", 1), ("train", 2), ("predict1", 3), ("predict2", 4)])
def test_failed_process_is_not_retried_and_results_retained(setup, phase, count):
    setup.processes.exit_code[phase] = 3
    result = execute(setup)
    assert result["status"] == "BLOCKED" and result["artifact"], result
    assert len(result["processes"]) == count

def test_invalid_restore_never_trains(setup):
    setup.processes.bad_restore = True
    result = execute(setup)
    assert result["status"] == "BLOCKED" and len(result["processes"]) == 1
    assert not setup.transport.train_released

@pytest.mark.parametrize("field", ["restore_ready_sha256", "restore_receipt_sha256", "continuation_sha256", "run_id"])
def test_parent_release_identity_must_match(setup, field):
    setup.transport.bad_release = field
    result = execute(setup)
    assert result["status"] == "BLOCKED" and len(result["processes"]) == 1

def test_rewritten_prior_history_is_not_accepted(setup):
    setup.processes.change_prior = True
    result = execute(setup)
    assert result["status"] == "BLOCKED" and "PRIOR_HISTORY_CHANGED" in result["reason"]["message"]
    assert not setup.transport.public_released

@pytest.mark.parametrize("phase, cap", [("restore", 180), ("train", 4800), ("predict1", 300)])
def test_each_process_uses_its_original_hard_cap(setup, phase, cap):
    setup.processes.duration[phase] = cap + 20
    setup.clock.sleep = lambda seconds: setattr(setup.clock, "value", setup.clock.value + min(60, cap / 10))
    result = execute(setup)
    assert result["status"] == "BLOCKED" and "PROCESS" in result["reason"]["message"]
    assert setup.clock.time() < 8200
    assert any(row["failure"] for row in result["processes"])

def test_old_events_are_not_new_progress(setup):
    path = setup.root / "train/campaign/cas.aligned/events"
    path.mkdir(parents=True)
    (path / "step-00000001.result.json").write_bytes(b"{}")
    assert remote.new_progress(setup.root, setup.config, setup.manifest, base) is None
    event = {"sequence": 57, "intent_sha256": "a" * 64, "receipt": {
        "schema": "cas-teaching-binding-cuda/1", "run_id": remote.LOGICAL_RUN + ".aligned.cas",
        "execution_mode": "cuda", "accepted_weights_updated": False, "optimizer_steps": 1, "cumulative_optimizer_steps": 57}}
    target = path / "step-00000057.result.json"
    target.write_bytes(b"{")
    assert remote.new_progress(setup.root, setup.config, setup.manifest, base) is None
    target.write_bytes(base.canonical(event) + b"\n")
    marker = remote.new_progress(setup.root, setup.config, setup.manifest, base)
    assert marker["prior_optimizer_steps"] == 56
    from aws.teaching_continuation_provider import validate_first_update
    raw = base.canonical(marker) + b"\n"
    context = {**setup.config, "prior_arms": setup.manifest["arms"]}
    report = validate_first_update({"raw_utf8": raw.decode(), "sha256": sha256(raw).hexdigest(),
        "bytes": len(raw), "key": "results/new_update.json"}, context)
    assert report["cumulative_optimizer_steps"] == 57

def test_bootstrap_support_is_pinned_and_after_permit_gate():
    c = pt.continuation()
    script = bootstrap.render_bootstrap(bucket=old.JOB + "-807562639912", job=old.JOB,
        source_sha256="a" * 64, driver_sha256="b" * 64, config_sha256="c" * 64,
        deadline_unix=2000000000, continuation=c)
    assert len(script.encode()) <= 16384
    for name, key in bootstrap.SUPPORT_KEYS.items():
        assert script.index("get_object input/permit.json") < script.index("get_object input/" + name)
        assert c[key] + "  " + name in script
    assert script.index("get_object input/restore_probe.py") < script.index("remote.py --config")

def test_actual_guest_receipts_pass_real_parent_phase_and_collection_checks(setup, monkeypatch):
    from aws import teaching_continuation_launch as parent
    monkeypatch.setattr(plan, "ORIGINAL_CAMPAIGN_ROOT", remote.CAMPAIGN_ROOT)
    result = execute(setup)
    assert result["status"] == "COMPLETE", result
    def envelope(key):
        raw = setup.transport.uploads[key]
        return {"key": key, "raw_utf8": raw.decode(), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
    context = {**setup.config, "launch": {"instance_id": setup.permit["instance_id"]},
        "prior_arms": setup.manifest["arms"], "prior_tree_expected": {
            "files": len(setup.manifest["members"]), "bytes": setup.manifest["expanded_bytes"],
            "sha256": plan.canonical_sha256(setup.manifest["members"])}}
    pids = set()
    proof = parent._restore({"ready": envelope("results/restore_ready.json"),
        "probe": envelope("results/restore/restore_receipt.json")}, context, pids)
    context.update(restore_ready_sha256=result["restore_ready_sha256"], restore_receipt_sha256=result["restore_receipt_sha256"],
        restore_initial_states={arm: row["initial_state_sha256"] for arm, row in proof["arms"].items()})
    campaign = parent._training({"ready": envelope("results/train_ready.json"),
        "campaign": envelope("results/" + remote.LATEST_SUMMARY)}, context, pids)
    context.update(training_ready_sha256=result["training_ready_sha256"], campaign_summary_sha256=result["campaign_summary_sha256"], prediction_seals=[])
    for index in (1, 2):
        seal, _ = parent._prediction({"ready": envelope(f"results/prediction{index}_ready.json"),
            "seal": envelope(f"results/predict{index}/prediction_seal.json")}, context, index, pids, campaign)
        context["prediction_seals"].append(seal)
    collected = parent._collection({"complete": envelope("results/complete.json"),
        "archive": {**result["artifact"], "path": str(setup.root / "artifacts.zip")}}, context, setup.root)
    assert collected["local_bytes_verified"] and len(pids) == 4

def test_low_remaining_time_matches_parent_wait_and_worker_finishes_before_it(setup):
    setup.root.mkdir()
    (setup.root / "driver").mkdir()
    (setup.root / "train").mkdir()
    setup.transport.train_released = True
    setup.clock.value = 3200.0  # Exactly 5,000 seconds remain in this same job.
    budget = base.Budget(setup.config, setup.clock)
    parent_wait_seconds = budget.remaining() - 900
    receipt = remote.run_process(setup.root, "train", setup.config, setup.permit,
        "/fake/python", setup.support, base, budget, setup.processes)
    intent = base.parse(base.read(setup.root / "driver/train.intent.json"))
    assert parent_wait_seconds == intent["timeout_seconds"] == 4100
    command = receipt["command"]
    assert command[command.index("--worker-seconds") + 1] == "4070"
    assert receipt["exit_code"] == 0 and setup.clock.time() <= 3200 + parent_wait_seconds
