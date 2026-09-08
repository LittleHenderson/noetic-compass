"""Synthetic byte checkpoints only; no model, tensor restore or provider calls."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

from cas_meta2.teaching_cycle import journal, runner, worker_contract
from tools import inspect_teaching_continuation as tool

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("continuation_synthetic_learner", ROOT / "tests/test_teaching_cycle_runner.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def encoded(value):
    return journal._encode(value)


class FakeLearner(fixtures.FakeLearner):
    """CUDA-shaped fixture records, not an actual CUDA learner."""
    execution_mode = "cuda"

    def __init__(self, *args, registry_sha256, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry_sha256 = registry_sha256

    def state_identity(self):
        return {**super().state_identity(), "record_registry_sha256": self.registry_sha256}

    def teach(self, records):
        result = super().teach(records)
        result.update(scope_names=["binding_query.weight"], execution_mode="cuda", device="cuda:0",
                      gpu_name="SYNTHETIC_GPU_NO_EXECUTION", synthetic_fixture_only=True)
        return result


@pytest.fixture(scope="module")
def original(tmp_path_factory):
    root = tmp_path_factory.mktemp("synthetic_continuation_original")
    extracted = root / "extracted"
    (extracted / "input").mkdir(parents=True)
    (extracted / "train/campaign").mkdir(parents=True)
    bundle_root = ROOT / "records/teaching_cycle_001/bundle_002"
    archive = bundle_root / "training.zip"
    manifest_pin = sha256((bundle_root / "manifest.json").read_bytes()).hexdigest()
    archive_pin = sha256(archive.read_bytes()).hexdigest()
    _, _, bundle = worker_contract.archive_payloads(archive, archive_pin, manifest_pin)
    registry_sha256 = tool._registry_digest(bundle["training_cases"])
    shutil.copyfile(archive, extracted / "input/source.zip")
    run_id = "synthetic-continuation"
    arms = {}
    clock = [0]
    old_clock = runner.time.monotonic
    runner.time.monotonic = lambda: clock[0]
    try:
        for arm in runner.ARMS:
            family, curriculum = arm.split(".")
            learner = FakeLearner(run_id + "." + curriculum + "." + family,
                                  bundle["training_cases"], family=family, clock=clock, registry_sha256=registry_sha256)
            session = runner.TrainingSession(learner, bundle["training_cases"], bundle["development_cases"],
                curriculum, extracted / "train/campaign" / arm, bundle["manifest"]["source_sha256"],
                runner.Allocation(**bundle["manifest"]["profile"]["allocation"]), execution_mode="cuda")
            # One step is deliberately incomplete and is not a learning result.
            session.advance_epoch(batch_size=32, stop_at=clock[0] + 1)
            arms[arm] = session.report()
            for field in ("initial_checkpoint", "selected_checkpoint", "last_checkpoint"):
                reference = arms[arm][field]
                if reference is not None:
                    reference["path"] = (f"/srv/original-teaching/train/campaign/{arm}/journal/"
                                         f"txn-{reference['transaction']:08d}/candidate.pt")
    finally:
        runner.time.monotonic = old_clock
    campaign = {"schema": "cas-teaching-four-arm-campaign/1", "run_id": run_id,
        "campaign_root": "/srv/original-teaching/train/campaign", "all_allocations_finished": False,
        "source_sha256": bundle["manifest"]["source_sha256"], "manifest_sha256": manifest_pin, "arms": arms}
    (extracted / "train/campaign_summary.json").write_bytes(encoded(campaign))
    return {"root": root, "bindings": {"source_sha256": campaign["source_sha256"],
        "manifest_sha256": manifest_pin, "archive_sha256": archive_pin,
        "material_receipt_sha256": "3" * 64}, "run_id": run_id}


@pytest.fixture
def packet(tmp_path, original):
    shutil.copytree(original["root"] / "extracted", tmp_path / "extracted")
    return {**original, "root": tmp_path}


def publish(packet):
    root, bindings = packet["root"], packet["bindings"]
    archive = root / "collected.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as stream:
        for path in (root / "extracted").rglob("*"):
            if path.is_file():
                stream.write(path, path.relative_to(root / "extracted").as_posix())
    archive_pin = sha256(archive.read_bytes()).hexdigest()
    summary = root / "extracted/train/campaign_summary.json"
    complete = {"schema": "cas-teaching-guest-complete/1", "status": "TEACHING_INCOMPLETE",
        "job": packet["run_id"], "run_id": packet["run_id"], "source_sha256": bindings["source_sha256"],
        "manifest_sha256": bindings["manifest_sha256"], "material_sha256": bindings["material_receipt_sha256"],
        "campaign_summary_sha256": sha256(summary.read_bytes()).hexdigest() if summary.is_file() else None,
        "artifact": {"key": "results/artifacts.zip", "sha256": archive_pin, "bytes": archive.stat().st_size}}
    parent = {"schema": "cas-teaching-cycle-parent-lifecycle/2", "status": "TEACHING_INCOMPLETE",
        "job": packet["run_id"], "bindings": bindings,
        "archive": {**complete["artifact"], "local_bytes_verified": True}}
    parent_path, complete_path = root / "parent.json", root / "complete.json"
    parent_path.write_bytes(encoded(parent))
    complete_path.write_bytes(encoded(complete))
    return {"parent_result": parent_path, "complete_marker": complete_path, "archive": archive,
        "extracted_root": root / "extracted", "parent_sha256": sha256(parent_path.read_bytes()).hexdigest(),
        "complete_sha256": sha256(complete_path.read_bytes()).hexdigest(), "archive_sha256": archive_pin}


def identities(root):
    return {path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


def test_registry_matches_unchanged_adapter_without_model_import(original):
    from cas_meta2.teaching_cycle.gpu_adapter import validate_training_plan
    archive = original["root"] / "extracted/input/source.zip"
    _, _, bundle = worker_contract.archive_payloads(archive, original["bindings"]["archive_sha256"],
                                                  original["bindings"]["manifest_sha256"])
    _, expected = validate_training_plan(bundle["training_cases"], bundle["manifest"]["training_cases_sha256"])
    assert tool._registry_digest(bundle["training_cases"]) == expected["record_registry_sha256"]


def test_read_only_inspection_replays_exactly_to_tensor_boundary(packet, monkeypatch):
    args = publish(packet)
    before = identities(packet["root"])
    monkeypatch.setattr(journal.CheckpointJournal, "__init__", lambda *a, **k: pytest.fail("creating constructor called"))
    monkeypatch.setattr(journal, "_write_new", lambda *a: pytest.fail("input write attempted"))
    ordinary_open = Path.open
    def read_only(path, mode="r", *args, **kwargs):
        assert not any(flag in mode for flag in "wax+")
        return ordinary_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", read_only)
    report = tool.inspect_continuation(**args)
    assert report["status"] == "STRUCTURALLY_RESUMABLE_GPU_RESTORE_UNTESTED"
    assert report["structurally_resumable"] is True
    assert report["required_original_campaign_root"] == "/srv/original-teaching/train/campaign"
    assert report["actual_gpu_restore"] == report["actual_restart"] == "UNEXECUTED"
    assert report["private_targets_opened"] is report["new_reservation"] is False
    for arm in report["arms"].values():
        assert arm["committed_cursor"] == {"epoch": 0, "batch": 0, "stage": 1}
        assert arm["committed_optimizer_steps"] == 1 and arm["committed_teaching_examples"] == 32
        assert arm["unfinished_cycles"] == 4096 and arm["uncommitted_tail"] == []
        assert arm["committed_transactions"] == 2
        assert arm["committed_exposure"]["verified_neural_cycles"] == 0
    assert identities(packet["root"]) == before


@pytest.mark.parametrize("pin", ["parent_sha256", "complete_sha256", "archive_sha256"])
def test_external_pins_are_required(packet, pin):
    args = publish(packet)
    args[pin] = "9" * 64
    with pytest.raises(ValueError):
        tool.inspect_continuation(**args)


def test_extracted_tamper_rejected_even_when_size_is_unchanged(packet):
    args = publish(packet)
    path = packet["root"] / "extracted/train/campaign/cas.aligned/journal/txn-00000002/candidate.pt"
    raw = path.read_bytes()
    path.write_bytes(b"x" + raw[1:])
    with pytest.raises(ValueError, match="EXTRACTED_BYTES_MISMATCH"):
        tool.inspect_continuation(**args)


@pytest.mark.parametrize("entry", ["candidate.pt", "metadata.json", "receipt.json"])
def test_resealed_archive_cannot_hide_old_committed_corruption(packet, entry):
    path = packet["root"] / "extracted/train/campaign/cas.aligned/journal/txn-00000001" / entry
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        tool.inspect_continuation(**publish(packet))


def test_missing_old_transaction_cannot_fall_back_to_latest(packet):
    directory = packet["root"] / "extracted/train/campaign/cas.aligned/journal/txn-00000001"
    # Exactly three synthetic fixture files, never a real teaching directory.
    assert directory.resolve().is_relative_to(packet["root"].resolve())
    for name in ("candidate.pt", "metadata.json", "receipt.json"):
        (directory / name).unlink()
    directory.rmdir()
    with pytest.raises(ValueError, match="TRANSACTION_CHAIN_GAP"):
        tool.inspect_continuation(**publish(packet))


def test_uncommitted_tail_remains_visible_and_blocks_restart(packet):
    events = packet["root"] / "extracted/train/campaign/cas.aligned/events"
    raw = json.loads((events / "step-00000001.intent.json").read_bytes())
    raw["sequence"] = 2
    (events / "step-00000002.intent.json").write_bytes(encoded(raw))
    report = tool.inspect_continuation(**publish(packet))
    assert report["status"] == "CONTINUATION_BLOCKED"
    assert report["arms"]["cas.aligned"]["blocker"] == "UNCOMMITTED_TEACHING_TAIL"
    assert report["arms"]["cas.aligned"]["uncommitted_tail"][0]["sequence"] == 2
    assert report["arms"]["cas.aligned"]["committed_optimizer_steps"] == 1


@pytest.mark.parametrize("kind", ["intent", "result"])
def test_partial_json_uncommitted_tail_is_reported_without_trusting_it(packet, kind):
    path = packet["root"] / f"extracted/train/campaign/cas.aligned/events/step-00000002.{kind}.json"
    path.write_bytes(b'{"partial":')
    report = tool.inspect_continuation(**publish(packet))
    arm = report["arms"]["cas.aligned"]
    assert report["structurally_resumable"] is False
    assert arm["blocker"] == "UNCOMMITTED_TEACHING_TAIL"
    assert arm["uncommitted_tail"][0]["parse_status"] == "UNCOMMITTED_NOT_PARSED_OR_TRUSTED"
    assert arm["committed_optimizer_steps"] == 1


def test_resealed_collected_archive_does_not_reseal_committed_events(packet):
    path = packet["root"] / "extracted/train/campaign/cas.aligned/events/step-00000001.result.json"
    event = json.loads(path.read_bytes())
    event["receipt"]["batch_size"] = 31
    path.write_bytes(encoded(event))
    with pytest.raises(ValueError, match="EVENT_DIGEST_MISMATCH"):
        tool.inspect_continuation(**publish(packet))


def test_checkpoint_cannot_change_frozen_resume_batch_size(packet):
    directory = packet["root"] / "extracted/train/campaign/cas.aligned/journal/txn-00000002"
    metadata = json.loads((directory / "metadata.json").read_bytes())
    metadata["batch_size"] = 16
    raw = encoded(metadata)
    (directory / "metadata.json").write_bytes(raw)
    receipt = json.loads((directory / "receipt.json").read_bytes())
    receipt.update(metadata_sha256=sha256(raw).hexdigest(), metadata_bytes=len(raw))
    (directory / "receipt.json").write_bytes(encoded(receipt))
    with pytest.raises(ValueError, match="RESUME_BATCH_SIZE_MISMATCH"):
        tool.inspect_continuation(**publish(packet))


def test_missing_scope_receipts_are_an_explicit_gap_not_a_restore_claim(packet):
    args = publish(packet)
    # Direct arm seam: all external file checks are covered separately above.
    root = packet["root"] / "extracted"
    campaign = json.loads((root / "train/campaign_summary.json").read_bytes())
    _, _, bundle = worker_contract.archive_payloads(root / "input/source.zip", packet["bindings"]["archive_sha256"], packet["bindings"]["manifest_sha256"])
    result = tool._inspect_arm("cas.aligned", campaign["arms"]["cas.aligned"], campaign, bundle, root / "train/campaign", {},
                               tool._registry_digest(bundle["training_cases"]))
    assert result["structural_resume_checks_passed"] is False
    assert result["blocker"] == "SCOPE_NAMES_UNAVAILABLE_WITHOUT_TENSOR_RESTORE"


def test_retained_journal_byte_cap_is_checked_without_large_allocations(packet, monkeypatch):
    original_latest = journal.CheckpointJournal.latest
    def excessive(view):
        result = original_latest(view)
        result["retained_bytes"] = journal.TOTAL_BYTES + 1
        return result
    monkeypatch.setattr(journal.CheckpointJournal, "latest", excessive)
    path = packet["root"] / "extracted/train/campaign/cas.aligned/journal"
    with pytest.raises(ValueError, match="JOURNAL_RETAINED_BYTE_LIMIT"):
        tool._journal_view(path)


def test_declared_non_cuda_mode_is_not_admitted_as_this_gpu_campaign(packet, monkeypatch):
    args = publish(packet)
    original_view = tool._journal_view
    def relabel(root):
        view, latest = original_view(root)
        view.identity = {**view.identity, "execution_mode": "simulated"}
        return view, latest
    monkeypatch.setattr(tool, "_journal_view", relabel)
    with pytest.raises(ValueError, match="ARM_PLAN_IDENTITY_MISMATCH"):
        tool.inspect_continuation(**args)


@pytest.mark.parametrize("change", ["registry", "extra_key"])
def test_real_constructor_identity_cannot_be_replaced_with_stored_claims(packet, monkeypatch, change):
    args = publish(packet)
    original_view = tool._journal_view
    def relabel(root):
        view, latest = original_view(root)
        view.identity = {**view.identity, **({"record_registry_sha256": "2" * 64} if change == "registry" else {"extra": True})}
        return view, latest
    monkeypatch.setattr(tool, "_journal_view", relabel)
    with pytest.raises(ValueError, match="ARM_PLAN_IDENTITY_MISMATCH"):
        tool.inspect_continuation(**args)


def test_last_checkpoint_path_must_map_to_original_linux_campaign(packet):
    path = packet["root"] / "extracted/train/campaign_summary.json"
    campaign = json.loads(path.read_bytes())
    campaign["arms"]["cas.aligned"]["last_checkpoint"]["path"] = "/unrelated/candidate.pt"
    path.write_bytes(encoded(campaign))
    with pytest.raises(ValueError, match="LAST_CHECKPOINT_REFERENCE_MISMATCH"):
        tool.inspect_continuation(**publish(packet))


def test_initial_checkpoint_reference_must_match_transaction_one(packet):
    path = packet["root"] / "extracted/train/campaign_summary.json"
    campaign = json.loads(path.read_bytes())
    campaign["arms"]["cas.aligned"]["initial_checkpoint"]["state_sha256"] = "9" * 64
    path.write_bytes(encoded(campaign))
    with pytest.raises(ValueError, match="INITIAL_CHECKPOINT_REFERENCE_MISMATCH"):
        tool.inspect_continuation(**publish(packet))


def test_same_size_input_change_during_inspection_is_caught_at_end(packet, monkeypatch):
    args = publish(packet)
    original_arm = tool._inspect_arm
    def mutate_after(arm, *values):
        result = original_arm(arm, *values)
        if arm == "cas.aligned":
            path = Path(result["checkpoint_file"])
            raw = path.read_bytes()
            path.write_bytes(b"x" + raw[1:])
        return result
    monkeypatch.setattr(tool, "_inspect_arm", mutate_after)
    with pytest.raises(ValueError, match="EXTRACTED_BYTES_MISMATCH"):
        tool.inspect_continuation(**args)


def test_staging_files_are_not_committed_or_discarded(packet):
    staging = packet["root"] / "extracted/train/campaign/cas.aligned/journal/.staging-synthetic"
    staging.mkdir()
    (staging / "candidate.pt").write_bytes(b"synthetic unfinished state")
    report = tool.inspect_continuation(**publish(packet))
    assert report["arms"]["cas.aligned"]["incomplete_staging"]
    assert report["arms"]["cas.aligned"]["committed_transactions"] == 2
    assert staging.is_dir()


def test_no_summary_is_blocked_not_invented(packet):
    (packet["root"] / "extracted/train/campaign_summary.json").unlink()
    report = tool.inspect_continuation(**publish(packet))
    assert report["status"] == "BLOCKED_NO_CAMPAIGN_SUMMARY"
    assert report["arms"] == {} and report["structurally_resumable"] is False


@pytest.mark.parametrize("change,reason", [("path", "ORIGINAL_ABSOLUTE_CAMPAIGN_PATH_REQUIRED"),
                                           ("source", "BUNDLE_SOURCE_BINDING_MISMATCH")])
def test_summary_cannot_change_original_path_or_bundle_source(packet, change, reason):
    path = packet["root"] / "extracted/train/campaign_summary.json"
    campaign = json.loads(path.read_bytes())
    if change == "path":
        campaign["campaign_root"] = "../somewhere"
    else:
        packet["bindings"] = deepcopy(packet["bindings"])
        packet["bindings"]["source_sha256"] = "9" * 64
        campaign["source_sha256"] = "9" * 64
    path.write_bytes(encoded(campaign))
    with pytest.raises(ValueError, match=reason):
        tool.inspect_continuation(**publish(packet))


def test_output_must_be_fresh_and_inside_teaching_records(tmp_path, monkeypatch):
    records = tmp_path / "records"
    records.mkdir()
    monkeypatch.setattr(tool, "RECORDS", records)
    report = {"actual_gpu_restore": "UNEXECUTED"}
    with pytest.raises(ValueError, match="FRESH_TEACHING_RECORD_PATH_REQUIRED"):
        tool.write_report(report, tmp_path / "elsewhere.json")
    with pytest.raises(ValueError, match="FRESH_TEACHING_RECORD_PATH_REQUIRED"):
        tool.write_report(report, records / ".." / "escape.json")
    output = records / "inspection.json"
    receipt = tool.write_report(report, output)
    assert receipt["sha256"] == sha256(output.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="FRESH_TEACHING_RECORD_PATH_REQUIRED"):
        tool.write_report(report, output)


def test_links_and_unlisted_files_refused(packet):
    args = publish(packet)
    (packet["root"] / "extracted/driver").mkdir()
    (packet["root"] / "extracted/driver/unlisted.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="EXTRACTED_INVENTORY_MISMATCH"):
        tool.inspect_continuation(**args)
