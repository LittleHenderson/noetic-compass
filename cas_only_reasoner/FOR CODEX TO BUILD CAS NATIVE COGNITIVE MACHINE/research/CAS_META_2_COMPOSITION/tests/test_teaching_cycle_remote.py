"""Guest orchestration with simulated processes and an in-memory transport only."""
from copy import deepcopy
from hashlib import sha256
import io
import json
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

from aws import teaching_cycle_remote as guest, teaching_cycle_plan as plan

JOB = "cas-meta2-teaching-20260908000000-abcdef12"


class FakeClock:
    def __init__(self):
        self.value = 1000.0

    def time(self):
        return self.value

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


def h(value):
    return sha256(value.encode()).hexdigest()


def public_bytes():
    rows = [{"problem": "Requested source: blue square.", "observations": [
        {"slot": slot, "tag": tag, "values": [slot] * 8}
        for slot, tag in enumerate(("blue square", "red circle", "green triangle"))]} for _ in range(64)]
    return guest.canonical({split: rows for split in guest.SPLITS}) + b"\n"


def campaign(config, root, *, complete=True):
    report = {"schema": "cas-teaching-four-arm-campaign/1", "run_id": config["run_id"],
        "source_sha256": config["bindings"]["source_sha256"], "manifest_sha256": config["bindings"]["manifest_sha256"],
        "all_allocations_finished": complete, "held_out_opened": False, "accepted_weights_updated": False, "arms": {}}
    for arm in guest.ARMS:
        family, curriculum = arm.split(".")
        refs = []
        for transaction, suffix in ((1, "initial"), (5, "selected")):
            path = root / "campaign" / arm / "journal" / f"txn-{transaction:08d}/candidate.pt"
            path.parent.mkdir(parents=True)
            raw = ("synthetic bytes " + arm + suffix).encode()
            path.write_bytes(raw)
            refs.append({"path": str(path), "sha256": sha256(raw).hexdigest(), "transaction": transaction,
                "state_sha256": h(family + "initialstate") if suffix == "initial" else h(arm + "state4"),
                "receipt_sha256": h(arm + suffix + "receipt")})
        report["arms"][arm] = {"run_id": config["run_id"] + "." + curriculum + "." + family,
            "curriculum": curriculum, "execution_mode": "cuda", "allocation_finished": complete,
            "max_epochs": 16, "cursor": {"epoch": 16 if complete else 1, "batch": 0, "stage": 0},
            "observed_optimizer_steps": 896 if complete else 56, "observed_teaching_examples": 28672 if complete else 1792,
            "initial_checkpoint": refs[0], "selected_checkpoint": refs[1],
            "development_curve": [{"kind": "development", "epoch": epoch, "eligible": epoch >= 4,
                "attempted": 64 if epoch >= 4 else 0, "correct": 64 if epoch == 4 else 40,
                "checkpoint_sha256": h(arm + "state" + str(epoch))} for epoch in range(1, 17)]}
    return report


class FakeChild:
    def __init__(self, owner, pid, duration, code):
        self.owner, self.pid, self.finish, self.code = owner, pid, owner.clock.time() + duration, code
        self.stopped = False

    def poll(self):
        callback = getattr(self.owner, "on_poll", None)
        if callback is not None:
            callback(self)
        return self.code if self.owner.clock.time() >= self.finish or self.stopped else None

    def wait(self, timeout):
        assert self.poll() is not None
        self.owner.events.append(("observed_exit", self.pid, self.code))
        return self.code


class FakeProcesses:
    def __init__(self, config, clock):
        self.config, self.clock = config, clock
        self.events, self.commands, self.children = [], [], []
        self.complete, self.exit_code, self.duration, self.same_pid = True, {}, {}, False

    def start(self, command, *, cwd, env, stdout_path, stderr_path):
        phase, output = command[4], Path(command[command.index("--output") + 1])
        label = output.name
        assert (Path(cwd) / "driver" / f"{label}.intent.json").is_file()
        assert not output.exists()
        self.commands.append(command)
        self.events.append(("start", label))
        output.mkdir()
        Path(stdout_path).write_bytes(b"synthetic process stdout\n")
        Path(stderr_path).write_bytes(b"")
        assert env["CAS_META2_RUN_TEACHING_CYCLE"] == "1"
        if phase == "train":
            assert "--public-sets" not in command
            self.summary = campaign(self.config, output, complete=self.complete)
            guest.write(output / "campaign_summary.json", self.summary)
        else:
            assert "--public-sets" in command and "--campaign-summary-sha256" in command
            artifacts = {}
            for arm in guest.ARMS:
                for version, key in (("untrained", "initial_checkpoint"), ("trained", "selected_checkpoint")):
                    for split in guest.SPLITS:
                        name = f"{arm}.{version}.{split}.json"
                        artifacts[name] = guest.write(output / name, {"predictions": [0] * 64,
                            "checkpoint": self.summary["arms"][arm][key], "synthetic_fixture": True})
            guest.write(output / "prediction_seal.json", {"schema": "cas-teaching-blind-prediction-seal/1",
                "source_sha256": self.config["bindings"]["source_sha256"], "artifacts": artifacts,
                "private_targets_opened": False, "native_execution": "UNEXECUTED"})
        child = FakeChild(self, 101 if self.same_pid else 101 + len(self.children), self.duration.get(label, 1), self.exit_code.get(label, 0))
        self.children.append(child)
        return child

    def stop(self, child):
        child.stopped, child.code = True, -9
        self.events.append(("stopped", child.pid))
        return child.wait(timeout=10)


class FakeTransport:
    def __init__(self, config, processes):
        self.config, self.processes = config, processes
        self.events, self.uploads, self.empty_polls = [], {}, 0
        self.release_change, self.failure = None, None
        self.public = public_bytes()

    def upload(self, path, key, maximum, deadline):
        self.events.append(("upload", key))
        if self.failure == key:
            raise RuntimeError("synthetic upload failure")
        raw = Path(path).read_bytes()
        assert len(raw) <= maximum
        self.uploads[key] = raw
        if key == "results/train_ready.json":
            ready = guest.parse(raw)
            assert ("observed_exit", ready["train_exit"]["pid"], 0) in self.processes.events

    def download(self, key, destination, maximum, deadline):
        self.events.append(("download", key))
        raw = b"synthetic source archive, extractor replaced explicitly in this fixture" if key == "input/source.zip" else self.public
        assert len(raw) <= maximum and not Path(destination).exists()
        Path(destination).write_bytes(raw)

    def fetch_optional(self, key, maximum, deadline):
        self.events.append(("poll", key))
        assert "results/train_ready.json" in self.uploads
        if self.empty_polls:
            self.empty_polls -= 1
            return None
        ready_raw = self.uploads["results/train_ready.json"]
        ready = guest.parse(ready_raw)
        release = {"schema": "cas-teaching-public-release/1", **{key: ready[key] for key in
            ("job", "run_id", "source_sha256", "manifest_sha256", "material_sha256")},
            "training_ready_sha256": sha256(ready_raw).hexdigest(), "campaign_summary_sha256": ready["campaign_summary"]["sha256"],
            "automatic_retries": 0, "public_sets": {"key": "input/public.json", "sha256": sha256(self.public).hexdigest(), "bytes": len(self.public)}}
        if self.release_change:
            self.release_change(release)
        return guest.canonical(release) + b"\n"


@pytest.fixture
def setup(tmp_path, monkeypatch):
    bindings = {name: h(name) for name in guest.BINDINGS}
    bindings.update(plan.FROZEN_BINDINGS)
    bindings["guest_driver_sha256"] = guest.file_hash(guest.__file__)["sha256"]
    bindings["public_sets_sha256"] = sha256(public_bytes()).hexdigest()
    resource = plan.resource_plan()
    config = {"schema": guest.SCHEMA, "job": JOB, "run_id": JOB, "bindings": bindings,
        "request_sha256": h("request"), "resource_plan_sha256": sha256(guest.canonical(resource)).hexdigest(),
        "resource_plan": resource, "bucket": JOB + "-807562639912", "prefix": "", "launch_started_unix": 1000.0, "deadline_unix": 8200.0}
    config_pin = sha256(guest.canonical(config)).hexdigest()
    permit = {"schema": guest.PERMIT_SCHEMA, "job": JOB, "run_id": JOB, "config_sha256": config_pin,
        "request_sha256": config["request_sha256"], "instance_id": "i-0123456789abcdef0", "deadline_unix": 8200.0,
        "shutdown_schedule_arn": "arn:aws:scheduler:us-west-2:807562639912:schedule/default/" + JOB,
        "shutdown_schedule_confirmed": True, "automatic_retries": 0}
    clock = FakeClock()
    processes = FakeProcesses(config, clock)
    transport = FakeTransport(config, processes)

    def fake_extract(archive, destination, pins):
        assert Path(archive).is_file() and not destination.exists() and pins == bindings
        destination.mkdir()
        return {"explicit_synthetic_extraction": True}

    monkeypatch.setattr(guest, "extract_training", fake_extract)
    return SimpleNamespace(config=config, config_sha256=config_pin, permit=permit, root=tmp_path / "job",
        clock=clock, processes=processes, transport=transport)


def execute(setup, **kwargs):
    return guest.execute(setup.config, setup.root, config_sha256=setup.config_sha256, permit=setup.permit,
        python="/fake/venv/python", transport=setup.transport, processes=setup.processes, clock=setup.clock, **kwargs)


def test_full_driver_trains_once_waits_then_two_fresh_readers_and_finishes_last(setup):
    setup.transport.empty_polls = 2
    result = execute(setup)
    assert result["status"] == "COMPLETE"
    assert len(setup.processes.commands) == 3
    assert [command[4] for command in setup.processes.commands] == ["train", "predict", "predict"]
    assert len({process["pid"] for process in result["processes"]}) == 3
    assert setup.transport.events[-1] == ("upload", "results/complete.json")
    events = setup.transport.events
    assert events.index(("upload", "results/train_ready.json")) < events.index(("download", "input/public.json"))
    assert result["resources"]["uploaded_bytes"] == sum(map(len, setup.transport.uploads.values()))
    assert result["resources"]["s3_api_attempts_upper_bound"] == sum(1 if kind == "upload" else 2 for kind, _ in events)
    assert result["resources"]["shared_deadline_unix"] == 8200.0
    with ZipFile(io.BytesIO(setup.transport.uploads["results/artifacts.zip"])) as archive:
        names = archive.namelist()
        assert "train/campaign_summary.json" in names and "predict1/prediction_seal.json" in names and "predict2/prediction_seal.json" in names
        assert "input/source.zip" in names and "input/public.json" in names
        assert not any("evaluator_private" in name or name.startswith("bundle/") for name in names)


def test_incomplete_training_preserves_prefix_without_public_release(setup):
    setup.processes.complete = False
    result = execute(setup)
    assert result["status"] == "TEACHING_INCOMPLETE" and result["artifact"]
    assert len(setup.processes.commands) == 1 and result["prediction_seals"] == []
    assert not any(kind == "poll" or key == "input/public.json" for kind, key in setup.transport.events)
    assert "results/train_ready.json" not in setup.transport.uploads
    assert setup.transport.events[-1][1] == "results/complete.json"
    with ZipFile(io.BytesIO(setup.transport.uploads["results/artifacts.zip"])) as archive:
        assert "train/campaign_summary.json" in archive.namelist()
        assert any(name.endswith("candidate.pt") for name in archive.namelist())


@pytest.mark.parametrize("phase,count", [("train", 1), ("predict1", 2), ("predict2", 3)])
def test_nonzero_process_never_retries_and_still_packages(setup, phase, count):
    setup.processes.exit_code[phase] = 7
    result = execute(setup)
    assert result["status"] == "BLOCKED" and result["artifact"]
    assert len(setup.processes.commands) == count
    assert result["processes"][-1]["exit_code"] == 7
    assert setup.transport.events[-1][1] == "results/complete.json"


@pytest.mark.parametrize("field", ["training_ready_sha256", "campaign_summary_sha256", "source_sha256", "job"])
def test_wrong_public_release_stops_before_final_download(setup, field):
    setup.transport.release_change = lambda release: release.update({field: "wrong"})
    result = execute(setup)
    assert result["status"] == "BLOCKED" and len(setup.processes.commands) == 1
    assert ("download", "input/public.json") not in setup.transport.events


def test_wrong_public_file_pin_stops_before_prediction(setup):
    setup.transport.public = public_bytes() + b" "
    result = execute(setup)
    assert result["status"] == "BLOCKED" and len(setup.processes.commands) == 1


def test_same_pid_is_not_promoted_as_fresh_reader(setup):
    setup.processes.same_pid = True
    result = execute(setup)
    assert result["status"] == "BLOCKED" and len(setup.processes.commands) == 2
    assert "FRESH_PROCESS_REQUIRED" in result["reason"]["message"]


def test_timeout_kills_observes_exit_and_does_not_retry(setup, monkeypatch):
    # Advance fake time by minutes per poll; do not spend thousands of real
    # filesystem scans simulating a long remote process.
    original_sleep = setup.clock.sleep
    monkeypatch.setattr(setup.clock, "sleep", lambda seconds: original_sleep(seconds * 100))
    setup.processes.duration["train"] = 5000
    result = execute(setup)
    assert result["status"] == "BLOCKED" and result["artifact"]
    assert len(setup.processes.commands) == 1 and setup.processes.children[0].stopped
    assert result["processes"][0]["exit_code"] == -9
    assert result["resources"]["remaining_seconds"] > 0


@pytest.mark.parametrize("change", ["permit", "driver", "bucket", "deadline", "resource"])
def test_identity_rejections_have_no_transport_or_process_effect(setup, change):
    if change == "permit":
        setup.permit["shutdown_schedule_confirmed"] = False
    elif change == "driver":
        setup.config["bindings"]["guest_driver_sha256"] = h("wrong driver")
    elif change == "bucket":
        setup.config["bucket"] = "another-bucket"
    elif change == "deadline":
        setup.config["deadline_unix"] = 9000
    else:
        setup.config["resource_plan"]["runtime_seconds_max"] = 9999
    with pytest.raises(guest.GuestError):
        execute(setup)
    assert not setup.root.exists() and not setup.transport.events and not setup.processes.commands


def test_active_checkpoint_rename_race_is_tolerated_but_quiescent_scan_is_strict(setup, tmp_path, monkeypatch):
    path = tmp_path / "candidate.pt"
    path.write_bytes(b"synthetic")
    original = guest.info

    def vanished(target, *args, **kwargs):
        if target == path:
            raise FileNotFoundError("synthetic atomic staging rename")
        return original(target, *args, **kwargs)

    monkeypatch.setattr(guest, "info", vanished)
    budget = guest.Budget(setup.config, setup.clock)
    budget.scan(tmp_path, active=True)
    with pytest.raises(FileNotFoundError):
        budget.scan(tmp_path)


def test_shared_transfer_and_request_bounds_never_reset_between_phases(setup):
    budget = guest.Budget(setup.config, setup.clock)
    for _ in range(448):
        budget.operation()
    with pytest.raises(guest.GuestError, match="S3_REQUEST_BOUND"):
        budget.operation(True)
    budget.transfer(guest.ARTIFACT_MAX - 1)
    budget.transfer(1)
    with pytest.raises(guest.GuestError, match="TRANSFER_BYTE_BOUND"):
        budget.transfer(1)


def test_bootstrap_evidence_copy_is_exact_allowlist(setup, tmp_path):
    bootstrap = tmp_path / "bootstrap"
    bootstrap.mkdir()
    for name in guest.BOOTSTRAP_FILES:
        (bootstrap / name).write_bytes(("fake " + name).encode())
    (bootstrap / "private_targets.json").write_bytes(b"must not copy")
    result = execute(setup, bootstrap_evidence=bootstrap)
    assert result["status"] == "COMPLETE"
    with ZipFile(io.BytesIO(setup.transport.uploads["results/artifacts.zip"])) as archive:
        assert {name.split("/", 1)[1] for name in archive.namelist() if name.startswith("bootstrap_evidence/")} == set(guest.BOOTSTRAP_FILES)


def envelope(transport, key):
    raw = transport.uploads[key]
    return {"raw_utf8": raw.decode(), "sha256": sha256(raw).hexdigest(), "bytes": len(raw), "key": key}


def test_actual_guest_receipts_pass_real_parent_contracts(setup, tmp_path):
    from aws import teaching_cycle_launch as parent
    result = execute(setup)
    assert result["status"] == "COMPLETE"
    context = {"job": JOB, "run_id": JOB, "bindings": setup.config["bindings"], "resource_plan": setup.config["resource_plan"]}
    pids = set()
    training = {"ready": envelope(setup.transport, "results/train_ready.json"),
                "campaign": envelope(setup.transport, "results/train/campaign_summary.json")}
    _, summary = parent._training(training, context, pids)
    context.update(training_ready_sha256=training["ready"]["sha256"], campaign_summary_sha256=training["campaign"]["sha256"])
    context["prediction_seals"] = []
    for index in (1, 2):
        prediction = {"ready": envelope(setup.transport, f"results/prediction{index}_ready.json"),
                      "seal": envelope(setup.transport, f"results/predict{index}/prediction_seal.json")}
        ref, _ = parent._prediction(prediction, context, index, pids, summary)
        context["prediction_seals"].append(ref)
    destination = tmp_path / "collected"
    destination.mkdir()
    archive = destination / "artifacts.zip"
    raw = setup.transport.uploads["results/artifacts.zip"]
    archive.write_bytes(raw)
    collected = parent._collection({"complete": envelope(setup.transport, "results/complete.json"),
        "archive": {"path": str(archive), "key": "results/artifacts.zip", "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}}, context, destination)
    assert collected["local_bytes_verified"] is True and collected["contents_independently_scored"] is False
    assert pids == {101, 102, 103}


def test_source_module_has_no_repository_or_neural_import():
    import ast
    tree = ast.parse(Path(guest.__file__).read_text())
    forbidden = {"aws", "cas_meta2", "torch", "numpy", "boto3", "botocore", "sqlite3", "_sqlite3"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not {name.name.split(".")[0] for name in node.names} & forbidden
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden


def frozen_archive():
    path = Path(__file__).resolve().parents[1] / "records/teaching_cycle_001/bundle_002/training.zip"
    assert guest.file_hash(path)["sha256"] == plan.FROZEN_BINDINGS["archive_sha256"]
    return path


def test_standalone_extractor_admits_actual_frozen_bytes_without_importing_them(tmp_path):
    destination = tmp_path / "bundle"
    manifest = guest.extract_training(frozen_archive(), destination, plan.FROZEN_BINDINGS)
    assert {path.relative_to(destination).as_posix() for path in destination.rglob("*") if path.is_file()} == guest.MEMBERS
    assert manifest["source_sha256"] == plan.FROZEN_BINDINGS["source_sha256"]
    assert guest.file_hash(destination / guest.WHEEL)["sha256"] == guest.WHEEL_SHA


@pytest.mark.parametrize("identity", ["archive_sha256", "manifest_sha256", "source_sha256"])
def test_standalone_extractor_rejects_wrong_pins_before_creating_bundle(tmp_path, identity):
    bindings = {**plan.FROZEN_BINDINGS, identity: h("wrong identity")}
    destination = tmp_path / "bundle"
    with pytest.raises(guest.GuestError):
        guest.extract_training(frozen_archive(), destination, bindings)
    assert not destination.exists()


def test_extra_teacher_file_is_rejected_even_with_resealed_archive_pin(tmp_path):
    archive_path = tmp_path / "extra.zip"
    with ZipFile(frozen_archive()) as original, ZipFile(archive_path, "w", ZIP_DEFLATED) as changed:
        for member in original.infolist():
            changed.writestr(member, original.read(member))
        changed.writestr("evaluator_private/test_fresh.json", b"[]")
    bindings = {**plan.FROZEN_BINDINGS, "archive_sha256": guest.file_hash(archive_path)["sha256"]}
    with pytest.raises(guest.GuestError, match="BUNDLE_INVENTORY"):
        guest.extract_training(archive_path, tmp_path / "bundle", bindings)
    assert not (tmp_path / "bundle").exists()


def test_s3_absent_404_is_distinct_from_denied_403(monkeypatch):
    responses = [SimpleNamespace(returncode=255, stdout=b"", stderr=b"An error occurred (404)"),
                 SimpleNamespace(returncode=255, stdout=b"", stderr=b"An error occurred (403)")]
    calls = []

    def fake_command(command, **kwargs):
        calls.append((command, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(guest.subprocess, "run", fake_command)
    adapter = guest.S3CLI(JOB + "-807562639912", clock=FakeClock())
    assert adapter.fetch_optional("input/public_release.json", guest.PUBLIC_MAX, 8200) is None
    with pytest.raises(guest.GuestError, match="S3_CLI_FAILED"):
        adapter.fetch_optional("input/public_release.json", guest.PUBLIC_MAX, 8200)
    assert len(calls) == 2
    assert all(options["env"]["AWS_MAX_ATTEMPTS"] == "1" for _, options in calls)


def first_event(setup):
    return {"sequence": 1, "intent_sha256": h("synthetic intent"), "receipt": {
        "schema": "cas-teaching-binding-cuda/1", "execution_mode": "cuda",
        "run_id": setup.config["run_id"] + ".aligned.cas", "optimizer_steps": 1,
        "cumulative_optimizer_steps": 1, "accepted_weights_updated": False}}


def test_missing_or_partially_written_event_is_not_first_update(setup):
    assert guest.first_update_marker(setup.root, setup.config) is None
    event_path = setup.root / "train/campaign/cas.aligned/events/step-00000001.result.json"
    event_path.parent.mkdir(parents=True)
    event_path.write_bytes(b'{"sequence":1,"receipt":')
    assert guest.first_update_marker(setup.root, setup.config) is None
    raw = guest.canonical(first_event(setup)) + b"\n"
    event_path.write_bytes(raw)
    marker = guest.first_update_marker(setup.root, setup.config)
    assert marker["event"] == {"key": "train/campaign/cas.aligned/events/step-00000001.result.json",
        "raw_utf8": raw.decode(), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
    assert marker["boundary"] == "WORKER_REPORTED_NOT_INDEPENDENT_LEARNING_PROOF"


@pytest.mark.parametrize("field,value", [("execution_mode", "simulated"), ("run_id", "wrong-run"),
    ("optimizer_steps", True), ("cumulative_optimizer_steps", 0),
    ("cumulative_optimizer_steps", True), ("accepted_weights_updated", True)])
def test_first_update_requires_real_shaped_cuda_receipt_not_a_flag_alone(setup, field, value):
    event = first_event(setup)
    event["receipt"][field] = value
    path = setup.root / "train/campaign/cas.aligned/events/step-00000001.result.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(guest.canonical(event))
    assert guest.first_update_marker(setup.root, setup.config) is None


def install_progress_writer(setup):
    setup.processes.duration["train"] = 5
    polls = [0]
    path = setup.root / "train/campaign/cas.aligned/events/step-00000001.result.json"

    def on_poll(child):
        if setup.processes.commands[-1][4] != "train":
            return
        polls[0] += 1
        if polls[0] == 2:
            path.parent.mkdir(parents=True)
            path.write_bytes(b'{"sequence":1,')
        if polls[0] == 3:
            path.write_bytes(guest.canonical(first_event(setup)) + b"\n")

    setup.processes.on_poll = on_poll


def test_first_valid_update_uploaded_once_before_train_seal_and_counted(setup):
    install_progress_writer(setup)
    result = execute(setup)
    assert result["status"] == "COMPLETE"
    updates = [event for event in setup.transport.events if event == ("upload", "results/first_update.json")]
    assert len(updates) == 1
    assert setup.transport.events.index(updates[0]) < setup.transport.events.index(("upload", "results/train_ready.json"))
    marker = guest.parse(setup.transport.uploads["results/first_update.json"])
    raw = (setup.root / "driver/first_update.result.json").read_bytes()
    assert raw.decode() == marker["event"]["raw_utf8"]
    assert sha256(raw).hexdigest() == marker["event"]["sha256"]
    assert result["resources"]["uploaded_bytes"] == sum(map(len, setup.transport.uploads.values()))
    assert result["resources"]["s3_api_attempts_upper_bound"] == sum(1 if kind == "upload" else 2 for kind, _ in setup.transport.events)


def test_optional_progress_upload_failure_does_not_retry_or_stop_training(setup):
    install_progress_writer(setup)
    setup.transport.failure = "results/first_update.json"
    result = execute(setup)
    assert result["status"] == "COMPLETE" and result["first_update_error"]["automatic_retries"] == 0
    assert setup.transport.events.count(("upload", "results/first_update.json")) == 1
    assert len(setup.processes.commands) == 3
    assert (setup.root / "driver/first_update.result.json").is_file()
