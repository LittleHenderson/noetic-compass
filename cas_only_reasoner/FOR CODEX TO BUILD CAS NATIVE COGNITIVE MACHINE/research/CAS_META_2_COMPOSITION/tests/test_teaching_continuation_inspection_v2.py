"""Synthetic journals only: no tensors, AWS, or final-test targets."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

from cas_meta2.teaching_cycle import continuation_package_v2 as package
from cas_meta2.teaching_cycle import runner, worker_contract
from tools import inspect_teaching_continuation_v2 as tool

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prior_v2_fixture_helpers",
    ROOT / "tests/test_teaching_continuation_package.py")
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def publish(packet):
    root = packet["root"]
    source = root / "extracted"
    archive = root / "collected.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as target:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                target.write(path, path.relative_to(source).as_posix())
    current_sha = digest(source / package.SUMMARY_PATH)
    retained_sha = digest(source / package.RETAINED_SUMMARY_PATH)
    complete = {"schema": "cas-teaching-guest-complete/1", "status": "TEACHING_INCOMPLETE",
        "job": "synthetic-continuation-second-job", "run_id": packet["run_id"],
        "source_sha256": packet["bindings"]["source_sha256"],
        "manifest_sha256": packet["bindings"]["manifest_sha256"],
        "material_sha256": packet["bindings"]["material_receipt_sha256"],
        "campaign_summary_sha256": current_sha, "latest_summary_path": package.SUMMARY_PATH,
        "original_summary_path": package.RETAINED_SUMMARY_PATH,
        "restore_receipt_sha256": "a" * 64, "restore_ready_sha256": "b" * 64,
        "artifact": {"key": "results/artifacts.zip", "sha256": digest(archive), "bytes": archive.stat().st_size}}
    parent = {"schema": "cas-teaching-continuation-parent-lifecycle/1", "status": "TEACHING_INCOMPLETE",
        "job": complete["job"], "run_id": packet["run_id"], "bindings": packet["bindings"],
        "continuation": packet["continuation"],
        "archive": {**complete["artifact"], "local_bytes_verified": True}}
    paths = {name: root / (name + ".json") for name in ("parent", "complete", "evaluation")}
    paths["parent"].write_bytes(package.canonical(parent))
    paths["complete"].write_bytes(package.canonical(complete))
    pins = {"parent_sha256": digest(paths["parent"]), "complete_sha256": digest(paths["complete"]),
            "archive_sha256": digest(archive)}
    evaluated = {"schema": "cas-teaching-continuation-collected-evaluation/1",
        "status": "PARTIAL_EXPOSURE_ONLY", "guest_status": "TEACHING_INCOMPLETE",
        "job": parent["job"], "run_id": parent["run_id"], **pins,
        "private_targets_opened": False, "final_scores": None,
        "continuation_evidence": {"status": "PINNED_RESTORE_RECEIPT_AND_PRIOR_BYTES_VERIFIED",
            "restore_receipt_sha256": complete["restore_receipt_sha256"],
            "restore_ready_sha256": complete["restore_ready_sha256"],
            "prior_members_unchanged": packet["prior_members"]}}
    paths["evaluation"].write_bytes(package.canonical(evaluated))
    current = json.loads((source / package.SUMMARY_PATH).read_bytes())
    payloads = [p for p in source.rglob("*") if p.is_file()
        and (p.relative_to(source).as_posix().startswith("train/campaign/")
             or p.relative_to(source).as_posix() in (package.SUMMARY_PATH, package.RETAINED_SUMMARY_PATH))]
    frozen = {**pins, "evaluation_sha256": digest(paths["evaluation"]),
        "summary_sha256": current_sha, "retained_summary_sha256": retained_sha,
        "logical_run_id": packet["run_id"], "job": parent["job"],
        "payload_members": len(payloads), "payload_bytes": sum(p.stat().st_size for p in payloads),
        "steps": {a: r["observed_optimizer_steps"] for a, r in current["arms"].items()}}
    args = {"parent_result": paths["parent"], "complete_marker": paths["complete"], "archive": archive,
        "extracted_root": source, **pins, "evaluation_report": paths["evaluation"],
        "evaluation_sha256": frozen["evaluation_sha256"]}
    return args, frozen


@pytest.fixture(scope="module")
def seed(tmp_path_factory):
    originals = old.originals.__wrapped__(tmp_path_factory)
    prior = old.built.__wrapped__(originals, tmp_path_factory)
    root = tmp_path_factory.mktemp("synthetic_continuation_v2")
    extracted = root / "extracted"
    shutil.copytree(originals["extracted_root"], extracted)
    shutil.copyfile(prior["root"] / "prior_state.zip", extracted / "input/prior_state.zip")
    shutil.copyfile(prior["root"] / "manifest.json", extracted / "input/prior_state_manifest.json")
    parent = json.loads(Path(originals["parent_result"]).read_bytes())
    bindings = parent["bindings"]
    _, _, bundle = worker_contract.archive_payloads(extracted / "input/source.zip",
        bindings["archive_sha256"], bindings["manifest_sha256"])
    campaign = json.loads((extracted / package.RETAINED_SUMMARY_PATH).read_bytes())
    arms, clock = {}, [0]
    registry_sha256 = old.fixture.tool._registry_digest(bundle["training_cases"])
    saved_clock = runner.time.monotonic
    runner.time.monotonic = lambda: clock[0]
    try:
        for arm in runner.ARMS:
            family, curriculum = arm.split(".")
            learner = old.fixture.FakeLearner(campaign["run_id"] + "." + curriculum + "." + family,
                bundle["training_cases"], family=family, clock=clock,
                registry_sha256=registry_sha256)
            session = runner.TrainingSession(learner, bundle["training_cases"], bundle["development_cases"],
                curriculum, extracted / "train/campaign" / arm, bundle["manifest"]["source_sha256"],
                runner.Allocation(**bundle["manifest"]["profile"]["allocation"]), execution_mode="cuda")
            assert learner.counter == 1
            session.advance_epoch(batch_size=32, stop_at=clock[0] + 1)
            arms[arm] = session.report()
            for field in ("initial_checkpoint", "selected_checkpoint", "last_checkpoint"):
                ref = arms[arm][field]
                if ref is not None:
                    ref["path"] = package.ORIGINAL_ROOT + f"/{arm}/journal/txn-{ref['transaction']:08d}/candidate.pt"
    finally:
        runner.time.monotonic = saved_clock
    current = {**campaign, "arms": arms,
               "resumed_summary_sha256": digest(extracted / package.RETAINED_SUMMARY_PATH)}
    (extracted / "train_continued_001").mkdir()
    (extracted / package.SUMMARY_PATH).write_bytes(package.canonical(current))
    return {"root": root, "bindings": bindings, "run_id": campaign["run_id"],
        "prior_members": len(prior["manifest"]["members"]),
        "continuation": {"prior_package_validator_sha256": digest(old.package.__file__),
            "prior_state_archive_sha256": prior["receipt"]["archive"]["sha256"],
            "prior_state_manifest_sha256": prior["receipt"]["manifest"]["sha256"],
            "prior_summary_sha256": digest(extracted / package.RETAINED_SUMMARY_PATH)}}


@pytest.fixture
def packet(seed, tmp_path):
    shutil.copytree(seed["root"] / "extracted", tmp_path / "extracted")
    return {**seed, "root": tmp_path}


def inspect(packet, monkeypatch):
    args, frozen = publish(packet)
    monkeypatch.setattr(tool, "FROZEN_EVIDENCE", frozen)
    return tool.inspect_continuation(**args)


def test_replays_latest_state_read_only_without_creating_constructor(packet, monkeypatch):
    args, frozen = publish(packet)
    monkeypatch.setattr(tool, "FROZEN_EVIDENCE", frozen)
    before = old.fixture.identities(packet["root"])
    monkeypatch.setattr(old.fixture.journal.CheckpointJournal, "__init__",
                        lambda *a, **k: pytest.fail("creating constructor"))
    monkeypatch.setattr(old.fixture.journal, "_write_new", lambda *a: pytest.fail("input write"))
    original_open = Path.open
    def read_only(path, mode="r", *a, **k):
        assert not any(flag in mode for flag in "wax+")
        return original_open(path, mode, *a, **k)
    monkeypatch.setattr(Path, "open", read_only)
    result = tool.inspect_continuation(**args)
    assert result["structurally_resumable"] is True
    assert result["schema"] == "cas-teaching-continuation-inspection/2"
    assert all(a["committed_optimizer_steps"] == 2 for a in result["arms"].values())
    assert all(p["strict_unchanged_prefix"] for p in result["history_prefixes"].values())
    assert result["summary_path"] == package.SUMMARY_PATH
    assert result["retained_summary_sha256"] == frozen["retained_summary_sha256"]
    assert result["private_targets_opened"] is result["new_reservation"] is False
    assert result["actual_gpu_restore"] == result["optimizer_restore"] == "UNEXECUTED"
    assert old.fixture.identities(packet["root"]) == before


@pytest.mark.parametrize("key", ["parent_sha256", "complete_sha256", "archive_sha256", "evaluation_sha256"])
def test_production_input_pins_cannot_be_replaced(packet, monkeypatch, key):
    args, frozen = publish(packet)
    monkeypatch.setattr(tool, "FROZEN_EVIDENCE", frozen)
    with pytest.raises(ValueError, match="EXACT_CONTINUATION001_EVIDENCE"):
        tool.inspect_continuation(**{**args, key: "f" * 64})


def test_new_summary_cannot_resume_older_or_unrelated_summary(packet, monkeypatch):
    path = packet["root"] / "extracted" / package.SUMMARY_PATH
    value = json.loads(path.read_bytes())
    value["resumed_summary_sha256"] = "f" * 64
    path.write_bytes(package.canonical(value))
    with pytest.raises(ValueError, match="LATEST_SUMMARY_LINEAGE"):
        inspect(packet, monkeypatch)


def test_retained_checkpoint_bytes_cannot_be_changed(packet, monkeypatch):
    path = packet["root"] / "extracted/train/campaign/cas.aligned/journal/txn-00000001/candidate.pt"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="PREVIOUS_MEMBER_CHANGED"):
        inspect(packet, monkeypatch)


def test_latest_event_cannot_be_resealed_without_journal(packet, monkeypatch):
    path = packet["root"] / "extracted/train/campaign/cas.aligned/events/step-00000002.result.json"
    value = json.loads(path.read_bytes())
    value["receipt"]["loss"] = .9
    path.write_bytes(old.fixture.encoded(value))
    with pytest.raises(ValueError, match="EVENT_DIGEST_MISMATCH"):
        inspect(packet, monkeypatch)


def test_latest_checkpoint_bytes_cannot_be_resealed_without_receipt(packet, monkeypatch):
    path = packet["root"] / "extracted/train/campaign/cas.aligned/journal/txn-00000003/candidate.pt"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        inspect(packet, monkeypatch)


def test_extra_uncommitted_tail_cannot_be_admitted(packet, monkeypatch):
    path = packet["root"] / "extracted/train/campaign/cas.aligned/events/step-00000003.intent.json"
    path.write_bytes(b'{"partial":')
    result = inspect(packet, monkeypatch)
    assert result["structurally_resumable"] is False
    assert result["arms"]["cas.aligned"]["blocker"] == "UNCOMMITTED_TEACHING_TAIL"


def test_added_staging_blocks_reuse(packet, monkeypatch):
    root = packet["root"] / "extracted/train/campaign/cas.aligned/journal/.staging-fake"
    root.mkdir()
    (root / "candidate.pt").write_bytes(b"fake")
    with pytest.raises(ValueError, match="LATEST_SUMMARY_STATE_MISMATCH"):
        inspect(packet, monkeypatch)


def test_latest_summary_cannot_hide_wrong_committed_count(packet, monkeypatch):
    path = packet["root"] / "extracted" / package.SUMMARY_PATH
    value = json.loads(path.read_bytes())
    value["arms"]["cas.aligned"]["observed_optimizer_steps"] += 1
    path.write_bytes(package.canonical(value))
    with pytest.raises(ValueError, match="LATEST_SUMMARY_STATE_MISMATCH"):
        inspect(packet, monkeypatch)


@pytest.mark.parametrize("field,value", [("private_targets_opened", True), ("status", "TWO_READERS_SCORED"),
                                        ("final_scores", {}), ("guest_status", "COMPLETE")])
def test_evaluation_boundary_is_required(packet, monkeypatch, field, value):
    args, frozen = publish(packet)
    path = args["evaluation_report"]
    report = json.loads(path.read_bytes())
    report[field] = value
    path.write_bytes(package.canonical(report))
    args["evaluation_sha256"] = frozen["evaluation_sha256"] = digest(path)
    monkeypatch.setattr(tool, "FROZEN_EVIDENCE", frozen)
    with pytest.raises(ValueError, match="VALIDATED_PARTIAL_EVALUATION"):
        tool.inspect_continuation(**args)


def test_unknown_summary_root_is_rejected(packet, monkeypatch):
    path = packet["root"] / "extracted/train_continued_009"
    path.mkdir()
    (path / "campaign_summary.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="ARCHIVE_PATH_INVALID"):
        inspect(packet, monkeypatch)


def test_no_neural_modules_loaded():
    assert not tool.FORBIDDEN.intersection(sys.modules)
