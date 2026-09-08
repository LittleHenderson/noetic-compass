"""Pure worker checks: fake IMDS, fake checkpoints and fake learners only.

These tests do not import a neural library, execute CUDA, contact a provider,
or establish a real model restart. File fixtures are local and disposable.
"""
from copy import deepcopy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import urllib.request
from zipfile import ZipFile

import pytest

from cas_meta2.codec import canonical_sha256
from cas_meta2.teaching_cycle import worker


SOURCE = "a" * 64
MANIFEST = "b" * 64
ARMS = ("cas.aligned", "cas.ordinary", "generic.aligned", "generic.ordinary")
SPLITS = ("test_fresh", "test_context", "test_names")
INSTANCE = {"instanceId": "i-0123456789abcdef0", "accountId": "807562639912",
            "region": "us-west-2", "instanceType": "g7.2xlarge", "imageId": "ami-fake"}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def observe(fetch, expected=None):
    expected = expected or INSTANCE
    return worker.observe_instance(*(expected[k] for k in
        ("instanceId", "accountId", "region", "instanceType")), fetch=fetch)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"nested":{"a":1,"a":2}}',
                                      b'{"n":NaN}', b'{"n":Infinity}', b'{"n":-Infinity}',
                                      b'{"n":1e999}', b'{"n":[-1e999]}'])
def test_json_rejects_duplicate_and_nonfinite_values(raw):
    with pytest.raises(ValueError):
        worker._json(raw)


def test_external_json_pin_is_checked_before_parsing(tmp_path, monkeypatch):
    path = tmp_path / "public.json"
    path.write_bytes(b"not json")
    monkeypatch.setattr(worker, "_json", lambda raw: pytest.fail("wrong pin reached JSON parser"))
    with pytest.raises(ValueError, match="EXTERNAL_FILE_PIN_MISMATCH"):
        worker.read_pinned_json(path, "0" * 64)


@pytest.mark.parametrize("pin", [None, "", "A" * 64, "x" * 64, "a" * 63, 12])
def test_external_json_requires_exact_pin_before_read(pin, monkeypatch):
    monkeypatch.setattr(worker, "_read", lambda *args: pytest.fail("invalid pin reached file read"))
    with pytest.raises(ValueError, match="EXTERNAL_FILE_PIN_REQUIRED"):
        worker.read_pinned_json("unused.json", pin)


def test_external_json_pin_accepts_exact_bytes(tmp_path):
    path = tmp_path / "public.json"
    raw = b'{"condition":true}\n'
    path.write_bytes(raw)
    assert worker.read_pinned_json(path, sha256(raw).hexdigest()) == {"condition": True}


def test_instance_observation_is_bound_but_not_provider_proof():
    raw = encoded(INSTANCE)
    result = observe(lambda: raw)
    assert all(result[key] == value for key, value in INSTANCE.items())
    assert result["document_sha256"] == sha256(raw).hexdigest()
    assert result["source"] == "EC2_IMDSv2_OBSERVATION"
    assert result["provider_identity_proved"] is False


@pytest.mark.parametrize("field,value", [("instanceId", "i-fffffffffffffffff"),
    ("accountId", "000000000000"), ("region", "us-east-1"), ("instanceType", "g4dn.xlarge")])
def test_each_instance_identity_mismatch_is_rejected(field, value):
    doc = {**INSTANCE, field: value}
    with pytest.raises(ValueError, match="INSTANCE_IDENTITY_MISMATCH"):
        observe(lambda: encoded(doc))


@pytest.mark.parametrize("instance_id", ["i-1234567", "i-123456789", "i-1234567890abcdef",
    "i-1234567890abcdef01", "i-0123456789ABCDEf0", "not-an-instance"])
def test_invalid_expected_instance_never_fetches(instance_id):
    with pytest.raises(ValueError, match="EXPECTED_INSTANCE_REQUIRED"):
        observe(lambda: pytest.fail("invalid expected ID fetched metadata"),
                {**INSTANCE, "instanceId": instance_id})


@pytest.mark.parametrize("account", ["", "123", "a" * 12])
def test_invalid_expected_account_never_fetches(account):
    with pytest.raises(ValueError, match="EXPECTED_ACCOUNT_INVALID"):
        observe(lambda: pytest.fail("invalid account fetched metadata"), {**INSTANCE, "accountId": account})


@pytest.mark.parametrize("raw", ["not bytes", b"x" * 16385, b"[]", b"null"])
def test_malformed_instance_document_is_rejected(raw):
    with pytest.raises(ValueError):
        observe(lambda: raw)


class FakeResponse(io.BytesIO):
    def __init__(self, raw, bounds):
        super().__init__(raw)
        self.bounds = bounds

    def read(self, size=-1):
        self.bounds.append(size)
        return super().read(size)


def metadata_opener(monkeypatch, token=b"fake-token-for-unit-test", document=None):
    calls, handlers, bounds = [], [], []
    payloads = [token, encoded(INSTANCE) if document is None else document]

    def build(*provided):
        handlers.extend(provided)

        def opened(request, timeout):
            calls.append((request, timeout))
            return FakeResponse(payloads[len(calls) - 1], bounds)
        return SimpleNamespace(open=opened)

    monkeypatch.setattr(urllib.request, "build_opener", build)
    return calls, handlers, bounds


def test_imdsv2_uses_fixed_host_bounded_reads_no_proxy_and_no_redirect(monkeypatch):
    calls, handlers, bounds = metadata_opener(monkeypatch)
    assert worker._metadata_fetch() == encoded(INSTANCE)
    assert bounds == [2049, 16385]
    assert [(req.full_url, req.get_method(), timeout) for req, timeout in calls] == [
        ("http://169.254.169.254/latest/api/token", "PUT", 3),
        ("http://169.254.169.254/latest/dynamic/instance-identity/document", "GET", 3)]
    assert dict((k.lower(), v) for k, v in calls[0][0].header_items()) == {
        "x-aws-ec2-metadata-token-ttl-seconds": "60"}
    assert dict((k.lower(), v) for k, v in calls[1][0].header_items()) == {
        "x-aws-ec2-metadata-token": "fake-token-for-unit-test"}
    assert handlers[0].proxies == {}
    with pytest.raises(ValueError, match="METADATA_REDIRECT_REJECTED"):
        handlers[1].redirect_request(None, None, None, None, None, "http://example.invalid")


@pytest.mark.parametrize("token", [b"", b"x" * 2049, b"has\nnewline", b"has\rreturn"])
def test_bad_imds_token_prevents_document_fetch_without_echoing_token(monkeypatch, token):
    calls, _, _ = metadata_opener(monkeypatch, token)
    with pytest.raises(ValueError, match="METADATA_TOKEN_INVALID") as caught:
        worker._metadata_fetch()
    assert len(calls) == 1
    if token:
        assert token.decode() not in str(caught.value)


def test_oversized_imds_document_is_rejected(monkeypatch):
    metadata_opener(monkeypatch, document=b"x" * 16385)
    with pytest.raises(ValueError, match="INSTANCE_DOCUMENT_BOUND"):
        worker._metadata_fetch()


def test_file_reads_reject_hardlinks_and_bounds(tmp_path):
    original, linked = tmp_path / "original", tmp_path / "linked"
    original.write_bytes(b"1234")
    with pytest.raises(ValueError, match="FILE_BOUND"):
        worker._read(original, maximum=3)
    os.link(original, linked)
    with pytest.raises(ValueError, match="FILE_BOUND"):
        worker._read(linked)


@pytest.mark.parametrize("operation", ["read", "write"])
def test_linked_parent_is_rejected_before_io(tmp_path, monkeypatch, operation):
    path = tmp_path / "unread.json"
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p == tmp_path or original(p))
    with pytest.raises(ValueError, match="LINK_PATH_REJECTED"):
        worker._read(path) if operation == "read" else worker._write(path, {})
    assert not path.exists()


def test_write_is_exclusive_and_receipt_matches_saved_bytes(tmp_path):
    path = tmp_path / "receipt.json"
    receipt = worker._write(path, {"z": 2, "a": 1})
    raw = path.read_bytes()
    assert raw == b'{"a":1,"z":2}\n'
    assert receipt == {"path": str(path.absolute()), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
    with pytest.raises(FileExistsError):
        worker._write(path, {"a": 3})
    assert path.read_bytes() == raw


def isolate_loaded_modules(monkeypatch, root, names):
    for name in list(sys.modules):
        if name == "cas_meta2" or name.startswith("cas_meta2."):
            monkeypatch.delitem(sys.modules, name)
    for name, package in names.items():
        path = root.joinpath(*name.split("."))
        path = path / "__init__.py" if package else path.with_suffix(".py")
        module = SimpleNamespace(__file__=str(path))
        if package:
            module.__path__ = [str(path.parent)]
        monkeypatch.setitem(sys.modules, name, module)


def test_loaded_worker_paths_must_come_from_bundle(tmp_path, monkeypatch):
    isolate_loaded_modules(monkeypatch, tmp_path, {"cas_meta2": True,
        "cas_meta2.teaching_cycle": True, "cas_meta2.teaching_cycle.worker": False})
    worker.verify_loaded_sources(tmp_path)
    monkeypatch.setitem(sys.modules, "cas_meta2.codec", SimpleNamespace(__file__=str(tmp_path / "outside.py")))
    with pytest.raises(ValueError, match="LOADED_SOURCE_OUTSIDE_BUNDLE:cas_meta2.codec"):
        worker.verify_loaded_sources(tmp_path)


@pytest.mark.parametrize("name", ["data", "package"])
def test_teacher_modules_rejected_even_at_matching_bundle_path(tmp_path, monkeypatch, name):
    isolate_loaded_modules(monkeypatch, tmp_path, {"cas_meta2.teaching_cycle." + name: False})
    with pytest.raises(ValueError, match="TEACHER_MODULE_LOADED"):
        worker.verify_loaded_sources(tmp_path)


def test_loaded_module_without_file_is_rejected(tmp_path, monkeypatch):
    isolate_loaded_modules(monkeypatch, tmp_path, {})
    monkeypatch.setitem(sys.modules, "cas_meta2.codec", SimpleNamespace())
    with pytest.raises(ValueError, match="LOADED_SOURCE_OUTSIDE_BUNDLE"):
        worker.verify_loaded_sources(tmp_path)


@pytest.fixture
def installed_reference(tmp_path, monkeypatch):
    root, installed = tmp_path / "bundle", tmp_path / "site-packages"
    wheel = root / "wheels/casformer_reference-0.1.0-py3-none-any.whl"
    wheel.parent.mkdir(parents=True)
    payloads = {"casformer/__init__.py": b"# fake frozen package\n",
                "casformer/core.py": b"# fake reference module\n"}
    with ZipFile(wheel, "w") as archive:
        for name, raw in payloads.items():
            archive.writestr(name, raw)
            path = installed / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    monkeypatch.setattr(worker.importlib.util, "find_spec",
                        lambda name: SimpleNamespace(origin=str(installed / "casformer/__init__.py")))
    return root, installed, wheel


def test_installed_reference_compares_bytes_without_import(installed_reference):
    root, _, wheel = installed_reference
    assert worker.verify_installed_reference(root) == {
        "module_files_checked": 2, "wheel_sha256": sha256(wheel.read_bytes()).hexdigest()}
    assert "casformer" not in sys.modules


def test_installed_reference_extra_python_file_rejected(installed_reference):
    root, installed, _ = installed_reference
    (installed / "casformer/extra.py").write_bytes(b"# unexpected\n")
    with pytest.raises(ValueError, match="INSTALLED_REFERENCE_INVENTORY_CHANGED"):
        worker.verify_installed_reference(root)


def test_installed_reference_changed_bytes_rejected(installed_reference):
    root, installed, _ = installed_reference
    (installed / "casformer/core.py").write_bytes(b"# changed\n")
    with pytest.raises(ValueError, match="INSTALLED_REFERENCE_BYTES_CHANGED"):
        worker.verify_installed_reference(root)


def test_missing_installed_reference_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(worker.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(ValueError, match="FROZEN_REFERENCE_NOT_INSTALLED"):
        worker.verify_installed_reference(tmp_path)


class FakeLearner:
    def __init__(self, run_id, references):
        self.run_id, self.references = run_id, references
        self.restores, self.seen = [], []
        self.state = "uninitialized"
        self.result = None
        self.mutate = False

    def restore_checkpoint(self, path, digest):
        reference = self.references[str(path)]
        assert digest == reference["sha256"]
        self.restores.append((str(path), digest))
        self.state = reference["state_sha256"]

    def state_identity(self):
        return {"checkpoint_sha256": self.state, "run_id": self.run_id}

    def predict(self, rows):
        assert all(set(public) == {"problem", "observations"} for public in rows)
        self.seen.append(deepcopy(rows))
        if self.mutate:
            self.state = "unexpected-weight-update"
        return [index % 3 for index in range(len(rows))] if self.result is None else self.result


@pytest.fixture
def prediction_setup(tmp_path):
    checkpoints, output = tmp_path / "campaign", tmp_path / "predictions"
    checkpoints.mkdir()
    output.mkdir()
    learners, reports = {}, {}
    for arm in ARMS:
        references = {}
        report = {"run_id": "fake-test." + arm, "allocation_finished": True}
        for key in ("initial_checkpoint", "selected_checkpoint"):
            path = checkpoints / f"{arm}.{key}.fake"
            raw = (arm + key).encode()
            path.write_bytes(raw)
            reference = {"path": str(path), "sha256": sha256(raw).hexdigest(),
                         "state_sha256": sha256(b"state:" + raw).hexdigest()}
            references[str(path)] = report[key] = reference
        learners[arm] = FakeLearner(report["run_id"], references)
        reports[arm] = report
    campaign = {"all_allocations_finished": True, "arms": reports,
        "source_sha256": SOURCE, "manifest_sha256": MANIFEST, "run_id": "fake-test",
        "campaign_root": str(checkpoints), "worker_pid": os.getpid() + 10000}
    public = {split: [{"problem": f"Choose an observation for {split} case {case}.",
        "observations": [{"slot": slot, "tag": "observed-" + str(slot), "values": [case + slot] * 8}
                         for slot in range(3)]} for case in range(64)] for split in SPLITS}
    return learners, campaign, public, output


def test_blind_predictions_restore_both_checkpoints_and_seal_exact_receipts(prediction_setup):
    learners, campaign, public, output = prediction_setup
    receipt = worker.predict_sealed(learners, campaign, public, output, SOURCE)
    seal_path = output / "prediction_seal.json"
    seal = json.loads(seal_path.read_bytes())
    assert receipt["sha256"] == sha256(seal_path.read_bytes()).hexdigest()
    assert len(seal["artifacts"]) == 24
    assert seal["private_targets_opened"] is False
    assert seal["native_execution"] == "UNEXECUTED"
    assert set(p.name for p in output.iterdir()) == {*seal["artifacts"], "prediction_seal.json"}
    for name, saved in seal["artifacts"].items():
        raw = (output / name).read_bytes()
        result = json.loads(raw)
        assert saved["sha256"] == sha256(raw).hexdigest() and saved["bytes"] == len(raw)
        assert result["source_sha256"] == SOURCE
        assert result["public_sha256"] == canonical_sha256(public[result["split"]])
        assert result["private_targets_opened"] is False
        assert result["predictions"] == [index % 3 for index in range(64)]
    for arm, learner in learners.items():
        assert len(learner.restores) == 2 and len(learner.seen) == 6
        assert [path for path, _ in learner.restores] == [campaign["arms"][arm][key]["path"]
            for key in ("initial_checkpoint", "selected_checkpoint")]


@pytest.mark.parametrize("where", ["all", "arm"])
@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_incomplete_or_truthy_allocations_never_predict(prediction_setup, where, value):
    learners, campaign, public, output = prediction_setup
    if where == "all":
        campaign["all_allocations_finished"] = value
    else:
        campaign["arms"][ARMS[0]]["allocation_finished"] = value
    with pytest.raises(ValueError):
        worker.predict_sealed(learners, campaign, public, output, SOURCE)
    assert not (output / "prediction_seal.json").exists()
    assert not any(learner.seen for learner in learners.values())


@pytest.mark.parametrize("bad", [[True] * 64, [0] * 63, [3] * 64, [0.0] * 64])
def test_invalid_predictions_never_receive_seal(prediction_setup, bad):
    learners, campaign, public, output = prediction_setup
    learners[ARMS[0]].result = bad
    with pytest.raises(ValueError, match="FINAL_PREDICTIONS_INVALID"):
        worker.predict_sealed(learners, campaign, public, output, SOURCE)
    assert not (output / "prediction_seal.json").exists()


@pytest.mark.parametrize("change", ["split", "count", "target", "worked", "bind"])
def test_invalid_or_answer_bearing_public_input_fails_before_restore(prediction_setup, change):
    learners, campaign, public, output = prediction_setup
    if change == "split":
        public["private"] = public.pop("test_names")
    elif change == "count":
        public["test_fresh"].pop()
    elif change == "target":
        public["test_fresh"][0]["target"] = 0
    else:
        public["test_fresh"][0]["problem"] = "Worked example" if change == "worked" else "BIND0"
    with pytest.raises(ValueError):
        worker.predict_sealed(learners, campaign, public, output, SOURCE)
    assert not any(learner.restores for learner in learners.values())
    assert not (output / "prediction_seal.json").exists()


@pytest.mark.parametrize("arm", ["unexpected", "../outside", "cas.aligned/child"])
def test_nonregistered_arm_names_fail_before_restore(prediction_setup, arm):
    learners, campaign, public, output = prediction_setup
    learners[arm] = learners.pop(ARMS[0])
    campaign["arms"][arm] = campaign["arms"].pop(ARMS[0])
    with pytest.raises(ValueError, match="FOUR_REGISTERED_ARMS_REQUIRED"):
        worker.predict_sealed(learners, campaign, public, output, SOURCE)
    assert not any(learner.restores for learner in learners.values())
    assert not list(output.iterdir())


def test_prediction_weight_mutation_has_no_seal(prediction_setup):
    learners, campaign, public, output = prediction_setup
    learners[ARMS[0]].mutate = True
    with pytest.raises(ValueError, match="STATE|MUTAT"):
        worker.predict_sealed(learners, campaign, public, output, SOURCE)
    assert not (output / "prediction_seal.json").exists()


def test_changed_checkpoint_file_fails_before_restore(prediction_setup):
    learners, campaign, public, output = prediction_setup
    Path(campaign["arms"][ARMS[0]]["initial_checkpoint"]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="PREDICTION_CHECKPOINT_FILE_MISMATCH"):
        worker.predict_sealed(learners, campaign, public, output, SOURCE)
    assert not any(learner.restores for learner in learners.values())


def test_checkpoint_outside_campaign_fails_before_restore(prediction_setup):
    learners, campaign, public, output = prediction_setup
    campaign["arms"][ARMS[0]]["initial_checkpoint"]["path"] = str(output / "wrong.fake")
    with pytest.raises(ValueError, match="CHECKPOINT_OUTSIDE_CAMPAIGN"):
        worker.predict_sealed(learners, campaign, public, output, SOURCE)
    assert not any(learner.restores for learner in learners.values())


def test_wrong_restored_state_has_no_prediction_or_seal(prediction_setup):
    learners, campaign, public, output = prediction_setup
    learners[ARMS[0]].state_identity = lambda: {"checkpoint_sha256": "wrong"}
    with pytest.raises(ValueError, match="PREDICTION_CHECKPOINT_STATE_MISMATCH"):
        worker.predict_sealed(learners, campaign, public, output, SOURCE)
    assert not any(learner.seen for learner in learners.values())
    assert not (output / "prediction_seal.json").exists()


def test_elapsed_prediction_deadline_prevents_seal(prediction_setup, monkeypatch):
    learners, campaign, public, output = prediction_setup
    monkeypatch.setattr(worker.time, "monotonic", lambda: 10.0)
    with pytest.raises(ValueError, match="PREDICTION_DEADLINE_REACHED"):
        worker.predict_sealed(learners, campaign, public, output, SOURCE, stop_at=9.0)
    assert not any(learner.seen for learner in learners.values())
    assert not (output / "prediction_seal.json").exists()


@pytest.mark.parametrize("slow_call", [1, 24])
def test_post_prediction_deadline_rejects_slow_call_before_artifact_or_seal(prediction_setup, monkeypatch, slow_call):
    learners, campaign, public, output = prediction_setup
    clock = {"now": 0.0, "calls": 0}
    monkeypatch.setattr(worker.time, "monotonic", lambda: clock["now"])
    for learner in learners.values():
        original = learner.predict

        def slow_prediction(rows, original=original):
            result = original(rows)
            clock["calls"] += 1
            if clock["calls"] == slow_call:
                clock["now"] = 10.0
            return result

        learner.predict = slow_prediction
    with pytest.raises(ValueError, match="PREDICTION_DEADLINE_REACHED"):
        worker.predict_sealed(learners, campaign, public, output, SOURCE, stop_at=9.0)
    assert clock["calls"] == slow_call
    assert len(list(output.iterdir())) == slow_call - 1
    assert not (output / "prediction_seal.json").exists()


def test_deadline_after_last_artifact_still_prevents_final_seal(prediction_setup, monkeypatch):
    learners, campaign, public, output = prediction_setup
    clock = {"now": 0.0, "writes": 0}
    original_write = worker._write
    monkeypatch.setattr(worker.time, "monotonic", lambda: clock["now"])

    def write_then_expire(path, value):
        receipt = original_write(path, value)
        clock["writes"] += 1
        if clock["writes"] == 24:
            clock["now"] = 10.0
        return receipt

    monkeypatch.setattr(worker, "_write", write_then_expire)
    with pytest.raises(ValueError, match="PREDICTION_DEADLINE_REACHED"):
        worker.predict_sealed(learners, campaign, public, output, SOURCE, stop_at=9.0)
    assert len(list(output.iterdir())) == 24
    assert not (output / "prediction_seal.json").exists()


@pytest.mark.parametrize("pin", [None, "not-a-pin", "A" * 64])
def test_prediction_requires_source_identity_before_restore(prediction_setup, pin):
    learners, campaign, public, output = prediction_setup
    with pytest.raises(ValueError, match="PREDICTION_SOURCE_PIN_REQUIRED"):
        worker.predict_sealed(learners, campaign, public, output, pin)
    assert not any(learner.restores for learner in learners.values())


@pytest.fixture
def main_setup(tmp_path, monkeypatch):
    # Patch boundaries directly: no real IMDS, model library, model or trainer.
    from cas_meta2.teaching_cycle import gpu_adapter, runner, worker_contract
    bundle, output = tmp_path / "bundle", tmp_path / "output"
    bundle.mkdir()
    events = []
    data = {"manifest_sha256": MANIFEST, "manifest": {"source_sha256": SOURCE,
        "training_cases_sha256": "c" * 64,
        "profile": {"allocation": {}, "seed": 7, "batch_size": 32}},
        "training_cases": ["fake training case"], "development_cases": ["fake development case"]}
    monkeypatch.setattr(worker, "__file__", str(bundle / "cas_meta2/teaching_cycle/worker.py"))
    monkeypatch.setattr(worker.platform, "system", lambda: "Linux")
    flags = {name: getattr(sys.flags, name) for name in dir(sys.flags) if not name.startswith("_")}
    monkeypatch.setattr(worker.sys, "flags", SimpleNamespace(**{**flags, "isolated": 1}))
    monkeypatch.setattr(worker.sys, "dont_write_bytecode", True)
    monkeypatch.setattr(worker.sys, "version_info", (3, 12, 0, "final", 0))
    monkeypatch.setattr(worker.sys, "path", list(sys.path))
    monkeypatch.setenv("CAS_META2_RUN_TEACHING_CYCLE", "1")

    def observed(name, result):
        def call(*args, **kwargs):
            events.append((name, args, kwargs))
            return result
        return call

    monkeypatch.setattr(worker_contract, "load_bundle", observed("bundle", data))
    monkeypatch.setattr(worker, "verify_loaded_sources", observed("sources", None))
    monkeypatch.setattr(worker, "observe_instance", observed("instance", {"fake_instance": True}))
    monkeypatch.setattr(worker, "verify_installed_reference", observed("reference", {"fake_reference": True}))
    fake_torch = SimpleNamespace(__version__="2.11.0+cu128", version=SimpleNamespace(cuda="12.8"),
        cuda=SimpleNamespace(get_device_name=lambda device: "NVIDIA RTX PRO 4500 Blackwell Server Edition"))
    monkeypatch.setattr(gpu_adapter, "_cuda", observed("cuda", (fake_torch, "fake-device")))
    monkeypatch.setattr(worker, "_learners", observed("learners", ({}, {"fake_matching": True})))
    monkeypatch.setattr(runner, "run_campaign", observed("campaign", {
        "all_allocations_finished": False, "arms": {}, "fake_execution": True}))
    args = ["train", "--bundle", str(bundle), "--manifest-sha256", MANIFEST,
        "--output", str(output), "--run-id", "fake-test", "--expected-instance-id", INSTANCE["instanceId"]]
    return SimpleNamespace(bundle=bundle, output=output, args=args, events=events,
        data=data, torch=fake_torch, gpu=gpu_adapter, contract=worker_contract, runner=runner)


def names(setup):
    return [event[0] for event in setup.events]


def fake_final_inputs(setup, tmp_path, campaign=None, public=None):
    campaign = campaign or {"source_sha256": SOURCE, "manifest_sha256": MANIFEST,
        "run_id": "fake-test", "all_allocations_finished": True}
    public = {} if public is None else public
    args = [*setup.args]
    args[0] = "predict"
    for option, value in (("campaign-summary", campaign), ("public-sets", public)):
        path = tmp_path / (option + ".json")
        raw = encoded(value)
        path.write_bytes(raw)
        args += ["--" + option, str(path), "--" + option + "-sha256", sha256(raw).hexdigest()]
    return args


@pytest.mark.parametrize("guard,expected", [("linux", "ISOLATED_LINUX_WORKER_REQUIRED"),
    ("isolated", "ISOLATED_LINUX_WORKER_REQUIRED"), ("bytecode", "ISOLATED_LINUX_WORKER_REQUIRED"),
    ("enable", "EXPLICIT_ENABLE_REQUIRED"), ("entrypoint", "ENTRYPOINT_OUTSIDE_BUNDLE")])
def test_main_environment_and_entrypoint_rejections_precede_bundle(main_setup, monkeypatch, guard, expected):
    if guard == "linux":
        monkeypatch.setattr(worker.platform, "system", lambda: "Windows")
    elif guard == "isolated":
        monkeypatch.setattr(worker.sys.flags, "isolated", 0)
    elif guard == "bytecode":
        monkeypatch.setattr(worker.sys, "dont_write_bytecode", False)
    elif guard == "enable":
        monkeypatch.delenv("CAS_META2_RUN_TEACHING_CYCLE")
    else:
        monkeypatch.setattr(worker, "__file__", str(main_setup.bundle / "outside.py"))
    with pytest.raises(ValueError, match=expected):
        worker.main(main_setup.args)
    assert not main_setup.events


@pytest.mark.parametrize("extra,expected", [(["--worker-seconds", "0"], "WORKER_TIME_BOUND"),
    (["--worker-seconds", "6001"], "WORKER_TIME_BOUND"),
    (["--run-id", "../wrong"], "RUN_ID_INVALID")])
def test_main_bad_bounds_precede_bundle(main_setup, extra, expected):
    with pytest.raises(ValueError, match=expected):
        worker.main(main_setup.args + extra)
    assert not main_setup.events


def test_main_wrong_bundle_pin_never_reaches_instance_or_gpu(main_setup, monkeypatch):
    def rejected(*args):
        raise ValueError("fake bundle pin rejection")
    monkeypatch.setattr(main_setup.contract, "load_bundle", rejected)
    with pytest.raises(ValueError, match="fake bundle pin rejection"):
        worker.main(main_setup.args)
    assert not main_setup.events
    assert not main_setup.output.exists()


@pytest.mark.parametrize("flag", ["public-sets", "public-sets-sha256", "campaign-summary", "campaign-summary-sha256"])
def test_main_train_rejects_any_final_input_before_instance_or_gpu(main_setup, flag):
    with pytest.raises(ValueError, match="TRAIN_PHASE_FINAL_INPUT_REJECTED"):
        worker.main(main_setup.args + ["--" + flag, "unused"])
    assert names(main_setup) == ["bundle", "sources"]
    assert not main_setup.output.exists()


@pytest.mark.parametrize("flag", ["campaign-summary-sha256", "public-sets-sha256"])
def test_main_wrong_final_pin_fails_before_instance_or_gpu(main_setup, tmp_path, flag):
    args = fake_final_inputs(main_setup, tmp_path)
    args[args.index("--" + flag) + 1] = "0" * 64
    with pytest.raises(ValueError, match="EXTERNAL_FILE_PIN_MISMATCH"):
        worker.main(args)
    assert names(main_setup) == ["bundle", "sources"]
    assert not main_setup.output.exists()


@pytest.mark.parametrize("field,value", [("source_sha256", "e" * 64), ("manifest_sha256", "f" * 64),
    ("run_id", "another-run"), ("all_allocations_finished", False)])
def test_main_final_campaign_identity_and_completion_precede_gpu(main_setup, tmp_path, field, value):
    campaign = {"source_sha256": SOURCE, "manifest_sha256": MANIFEST,
        "run_id": "fake-test", "all_allocations_finished": True, field: value}
    with pytest.raises(ValueError, match="PREDICTION_SOURCE_MISMATCH|FINAL_PREDICTION_ALLOCATION_INCOMPLETE"):
        worker.main(fake_final_inputs(main_setup, tmp_path, campaign))
    assert names(main_setup) == ["bundle", "sources"]


@pytest.mark.parametrize("boundary", ["observe_instance", "verify_installed_reference"])
def test_main_machine_and_reference_failures_precede_gpu(main_setup, monkeypatch, boundary):
    def rejected(*args):
        raise ValueError("fake identity rejection")
    monkeypatch.setattr(worker, boundary, rejected)
    with pytest.raises(ValueError, match="fake identity rejection"):
        worker.main(main_setup.args)
    assert "cuda" not in names(main_setup) and "learners" not in names(main_setup)
    assert not main_setup.output.exists()


@pytest.mark.parametrize("change,reason", [("torch", "REGISTERED_NEURAL_ENVIRONMENT_REQUIRED"),
    ("cuda", "REGISTERED_NEURAL_ENVIRONMENT_REQUIRED"), ("gpu", "REGISTERED_GPU_REQUIRED")])
def test_main_registered_environment_checked_before_learner(main_setup, change, reason):
    if change == "torch":
        main_setup.torch.__version__ = "wrong"
    elif change == "cuda":
        main_setup.torch.version.cuda = "wrong"
    else:
        main_setup.torch.cuda.get_device_name = lambda device: "T4"
    with pytest.raises(ValueError, match=reason):
        worker.main(main_setup.args)
    assert "cuda" in names(main_setup) and "learners" not in names(main_setup)
    assert not (main_setup.output / "campaign_summary.json").exists()


@pytest.mark.parametrize("kind", ["existing", "inside-bundle"])
def test_main_requires_fresh_output_outside_bundle_before_gpu(main_setup, kind):
    args = list(main_setup.args)
    if kind == "existing":
        main_setup.output.mkdir()
    else:
        args[args.index("--output") + 1] = str(main_setup.bundle / "output")
    with pytest.raises(ValueError, match="FRESH_OUTPUT_OUTSIDE_BUNDLE_REQUIRED"):
        worker.main(args)
    assert "cuda" not in names(main_setup) and "learners" not in names(main_setup)


def test_main_fake_training_binds_identity_and_passes_only_training_development(main_setup):
    assert worker.main(main_setup.args) == 0
    order = names(main_setup)
    assert order.index("bundle") < order.index("instance") < order.index("reference") < order.index("cuda")
    assert order.index("cuda") < order.index("learners") < order.index("campaign")
    call = next(event for event in main_setup.events if event[0] == "campaign")
    assert call[1][1:3] == (main_setup.data["training_cases"], main_setup.data["development_cases"])
    assert call[1][3] == main_setup.output / "campaign"
    assert call[1][4] == SOURCE
    report = json.loads((main_setup.output / "campaign_summary.json").read_bytes())
    assert report["source_sha256"] == SOURCE and report["manifest_sha256"] == MANIFEST
    assert report["run_id"] == "fake-test" and report["fake_execution"] is True
    assert report["all_allocations_finished"] is False
    assert "private_targets" not in encoded(report).decode()


@pytest.mark.parametrize("flag", ["resume-summary", "resume-summary-sha256"])
def test_main_resume_requires_both_file_and_pin_before_gpu(main_setup, flag):
    with pytest.raises(ValueError, match="RESUME_PIN_REQUIRED"):
        worker.main(main_setup.args + ["--" + flag, "unused"])
    assert names(main_setup) == ["bundle", "sources"]


@pytest.mark.parametrize("field,value", [("source_sha256", "e" * 64), ("manifest_sha256", "f" * 64),
    ("run_id", "different"), ("all_allocations_finished", True)])
def test_main_resume_identity_checked_before_gpu(main_setup, tmp_path, field, value):
    summary = {"source_sha256": SOURCE, "manifest_sha256": MANIFEST,
        "run_id": "fake-test", "all_allocations_finished": False, field: value}
    path = tmp_path / "resume.json"
    raw = encoded(summary)
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="RESUME_IDENTITY_MISMATCH"):
        worker.main(main_setup.args + ["--resume-summary", str(path),
            "--resume-summary-sha256", sha256(raw).hexdigest()])
    assert names(main_setup) == ["bundle", "sources"]


def test_main_resume_keeps_existing_campaign_and_uses_fresh_receipt_output(main_setup, tmp_path):
    old_campaign = tmp_path / "previous-campaign"
    old_campaign.mkdir()
    sentinel = old_campaign / "existing-evidence"
    sentinel.write_bytes(b"retained")
    summary = {"source_sha256": SOURCE, "manifest_sha256": MANIFEST,
        "run_id": "fake-test", "all_allocations_finished": False, "campaign_root": str(old_campaign)}
    path = tmp_path / "resume.json"
    raw = encoded(summary)
    path.write_bytes(raw)
    pin = sha256(raw).hexdigest()
    assert worker.main(main_setup.args + ["--resume-summary", str(path), "--resume-summary-sha256", pin]) == 0
    call = next(event for event in main_setup.events if event[0] == "campaign")
    assert call[1][3] == old_campaign
    report = json.loads((main_setup.output / "campaign_summary.json").read_bytes())
    assert report["campaign_root"] == str(old_campaign)
    assert report["resumed_summary_sha256"] == pin
    assert sentinel.read_bytes() == b"retained"


class IntegrationRuleLearner:
    """A rule with a saved counter, not a model or a learning result."""
    execution_mode = "simulated"

    def __init__(self, run_id, cases, family):
        self.run_id, self.family, self.counter = run_id, family, 0
        self.training_sha = canonical_sha256(sorted(cases, key=lambda case: case["family_id"]))

    def state_identity(self):
        return {"run_id": self.run_id, "checkpoint_sha256": canonical_sha256([self.family, self.counter]),
            "scope_names": ["binding_query.weight"], "training_cases_sha256": self.training_sha,
            "record_registry_sha256": "d" * 64}

    def teach(self, records):
        before = self.state_identity()["checkpoint_sha256"]
        self.counter += 1
        return {"run_id": self.run_id, "execution_mode": "simulated",
            "scope_sha256": canonical_sha256(["binding_query.weight"]), "training_cases_sha256": self.training_sha,
            "before_checkpoint_sha256": before, "after_checkpoint_sha256": self.state_identity()["checkpoint_sha256"],
            "optimizer_steps": 1, "batch_size": len(records), "loss": 0.5,
            "input_sha256": canonical_sha256([row["public"] for row in records]),
            "target_sha256": canonical_sha256([row["target_binding"] for row in records]),
            "gradient_parameter_names": ["binding_query.weight"],
            "changed_parameter_names": ["binding_query.weight"], "provider_identity_proved": False}

    def predict(self, rows):
        from cas_meta2.teaching_cycle.lesson_contract import recover_binding
        return [recover_binding(row) for row in rows]

    def save_checkpoint(self, path):
        raw = encoded({"run_id": self.run_id, "family": self.family, "counter": self.counter})
        with path.open("xb") as stream:
            stream.write(raw)
        return {"path": str(path), "sha256": sha256(raw).hexdigest(), "tensor_execution": False}

    def restore_checkpoint(self, path, digest):
        raw = Path(path).read_bytes()
        assert sha256(raw).hexdigest() == digest
        state = json.loads(raw)
        assert state["run_id"] == self.run_id and state["family"] == self.family
        self.counter = state["counter"]


def test_actual_runner_journal_worker_export_and_scorer_contract_with_rule_only(tmp_path):
    from cas_meta2.teaching_cycle import evaluation, runner
    from cas_meta2.teaching_cycle.controller import Allocation
    from cas_meta2.teaching_cycle.data import build_dataset
    from cas_meta2.teaching_cycle.lesson_contract import make_public

    dataset = build_dataset()
    training, development = dataset["splits"]["train"][:4], dataset["splits"]["development"][:2]
    # Small synthetic allocation deliberately differs from the real frozen profile.
    allocation = Allocation(minimum_full_cycles=4, maximum_cycles=4, development_interval=4,
        consistent_checks=1, readiness_accuracy=0.9, minimum_unique_families=4,
        minimum_cycles_per_family=1, development_cases_count=2)
    learners = {arm: IntegrationRuleLearner("integration." + arm, training, arm.split(".")[0]) for arm in ARMS}
    campaign_root = tmp_path / "campaign"
    report = runner.run_campaign(learners, training, development, campaign_root, SOURCE, 120,
                                 allocation=allocation, batch_size=4)
    assert report["all_allocations_finished"] is True
    for arm in ARMS:
        assert report["arms"][arm]["selected_checkpoint"]["transaction"] == 2
        assert report["arms"][arm]["execution_mode"] == "simulated"
        assert report["arms"][arm]["exposure"]["verified_neural_cycles"] == 0
    report.update(source_sha256=SOURCE, manifest_sha256=MANIFEST, run_id="integration",
                  campaign_root=str(campaign_root), worker_pid=os.getpid())
    campaign_path = tmp_path / "campaign_summary.json"
    campaign_receipt = worker._write(campaign_path, report)

    material = tmp_path / "material"
    material.mkdir()
    artifacts = {}
    for split in SPLITS:
        cases = dataset["splits"][split]
        for folder, values in (("evaluation_public", [make_public(case) for case in cases]),
            ("evaluator_private", [{"family_id": case["family_id"], "binding": case["target_binding"],
                "selected_values": next(row["values"] for row in case["observations"]
                    if row["slot"] == case["target_binding"])} for case in cases])):
            path = material / folder / f"{split}.json"
            path.parent.mkdir(exist_ok=True)
            receipt = worker._write(path, values)
            artifacts[f"{folder}/{split}.json"] = {key: receipt[key] for key in ("sha256", "bytes")}
    material_receipt = worker._write(material / "preparation_receipt.json", {
        "schema": "cas-teaching-preparation/1", "status": "PREPARED_NOT_TRAINED",
        "dataset_sha256": canonical_sha256(dataset), "counts": dataset["counts"], "artifacts": artifacts})
    public_path = tmp_path / "public_sets.json"
    seen = []

    def public_only(path):
        assert "evaluator_private" not in path.parts
        seen.append(path)
        return path.read_bytes()

    exported = evaluation.export_public(material, material_receipt["sha256"], public_path, reader=public_only)
    assert exported["counts"] == {split: 64 for split in SPLITS}
    public_sets = worker.read_pinned_json(public_path, exported["sha256"])
    assert set(public_sets) == set(SPLITS)
    prediction_root = tmp_path / "predictions"
    prediction_root.mkdir()
    # Fresh objects must restore each saved counter. This is not a fresh-process claim.
    restored = {arm: IntegrationRuleLearner("integration." + arm, training, arm.split(".")[0]) for arm in ARMS}
    seal = worker.predict_sealed(restored, report, public_sets, prediction_root, SOURCE)
    reads = []

    def checked_reader(path):
        if "evaluator_private" in path.parts:
            assert evaluation.PREDICTION_NAMES <= {item.name for item in reads}
            for arm in ARMS:
                assert any(arm in item.parts and "txn-00000002" in item.parts and item.name == "candidate.pt"
                           for item in reads)
        reads.append(path)
        return path.read_bytes()

    result = evaluation.score_packet(prediction_root, material, campaign_path, campaign_root,
        expected_seal_sha256=seal["sha256"], expected_campaign_sha256=campaign_receipt["sha256"],
        expected_material_sha256=material_receipt["sha256"], expected_source_sha256=SOURCE,
        expected_bundle_manifest_sha256=MANIFEST, reader=checked_reader)
    assert result["prediction_files_validated_before_private_reads"] == 24
    assert sum("evaluator_private" in path.parts for path in reads) == 3
    for arm in ARMS:
        for split in SPLITS:
            assert result["comparison"][arm][split] == {"before_correct": 64, "after_correct": 64,
                "attempted_each": 64, "change_correct": 0}
        assert result["identities"]["checkpoints"][arm]["committed_transactions_checked"] == 2
    assert result["complete_native_task_correctness"] == "UNMEASURED"
    assert result["provider_identity_proved"] is False
