"""Synthetic continuation packets; no real final targets, models or AWS calls.

Frozen scorer tests fake the separately tested continuation-evidence seam.
Evidence-gate tests use its real restore admission with only prior-package byte
validation faked; that validator has its own byte-preservation test suite.
"""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

from aws import teaching_continuation_plan_v2 as plan, teaching_continuation_launch_v2 as launch
from cas_meta2.teaching_cycle import continuation_package_v2 as package, evaluation as scorer
from tools import evaluate_teaching_continuation_v2 as tool

ROOT = Path(__file__).resolve().parents[1]


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = load("test_teaching_cycle_collected_evaluation.py", "old_collected_fixture")
helpers = load("test_teaching_continuation_second_launch.py", "restore_receipt_fixture")
encode = old.encode
JOB = "cas-meta2-teaching-20260908090000-abcd1234"


def write(root, name, raw):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return sha256(raw).hexdigest()


def no_private(path):
    assert "evaluator_private" not in path.parts, "PRIVATE_TARGET_READ_BEFORE_ADMISSION"
    return path.read_bytes()


def source_bundle(files, source_sha256):
    """Synthetic source-only ZIP. No lessons, neural code or real final data."""
    manifest = {"schema": "cas-meta2-teaching-cycle-training-bundle/1",
        "source_sha256": source_sha256,
        "files": {name: {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
                  for name, raw in files.items()}}
    raw_manifest = encode(manifest)
    stream = io.BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", raw_manifest)
        for name, raw in files.items():
            archive.writestr(name, raw)
    return stream.getvalue(), sha256(raw_manifest).hexdigest()


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    b = {key: "1" * 64 for key in ("source_sha256", "manifest_sha256", "archive_sha256",
        "material_receipt_sha256", "training_cases_sha256", "development_cases_sha256")}
    b["parent_driver_sha256"] = sha256(Path(launch.__file__).read_bytes()).hexdigest()
    c = {key: "2" * 64 for key in ("prior_state_archive_sha256", "prior_state_manifest_sha256",
        "prior_summary_sha256", "prior_parent_result_sha256", "prior_complete_sha256",
        "prior_inspection_sha256", "prior_result_archive_sha256", "profile_sha256")}
    c["continuation_plan_sha256"] = sha256(Path(plan.__file__).read_bytes()).hexdigest()
    validator_raw = Path(package.__file__).read_bytes()
    c["prior_package_validator_sha256"] = sha256(validator_raw).hexdigest()
    for name, key, owner, raw in (("remote.py", "guest_driver_sha256", b, b"synthetic remote"),
        ("base_remote.py", "base_guest_driver_sha256", c, b"synthetic base"),
        ("restore_probe.py", "restore_probe_sha256", c, b"synthetic probe"),
        ("continuation_package.py", "prior_package_validator_sha256", c, validator_raw)):
        owner[key] = write(tmp_path, "driver/" + name, raw)
    members = {"train/campaign_summary.json": b"original synthetic summary",
               "train_continued_001/campaign_summary.json": b"first continuation synthetic summary",
               "train/campaign/cas.aligned/old.pt": b"opaque synthetic old checkpoint"}
    prior = {"members": {}, "expanded_bytes": sum(map(len, members.values())), "arms": helpers.prior_arms()}
    for name, raw in members.items():
        prior["members"][name] = {"sha256": write(tmp_path, name, raw), "bytes": len(raw)}
    archive_bytes, manifest_bytes = b"fake package seam", encode(prior)
    c["prior_state_archive_sha256"] = write(tmp_path, "input/prior_state.zip", archive_bytes)
    c["prior_state_manifest_sha256"] = write(tmp_path, "input/prior_state_manifest.json", manifest_bytes)
    c["prior_state_archive_bytes"] = len(archive_bytes)
    c["prior_state_expanded_bytes"] = prior["expanded_bytes"] + len(manifest_bytes)
    def validated(archive, manifest, **kwargs):
        assert sha256(Path(archive).read_bytes()).hexdigest() == kwargs["archive_sha256"]
        assert sha256(Path(manifest).read_bytes()).hexdigest() == kwargs["manifest_sha256"]
        assert kwargs["expected_bindings"]["logical_run_id"] == plan.LOGICAL_RUN_ID
        return deepcopy(prior)
    monkeypatch.setattr(package, "validate_package", validated)
    context = {"job": JOB, "run_id": plan.LOGICAL_RUN_ID, "bindings": b, "continuation": c,
        "prior_arms": prior["arms"], "resource_plan": plan.resource_plan(),
        "prior_tree_expected": {"files": len(prior["members"]), "bytes": prior["expanded_bytes"],
                                "sha256": plan.canonical_sha256(prior["members"])},
        "launch": {"instance_id": "i-123456789abcdef01"}}
    provider = helpers.FakeProvider(None)
    provider.mark = lambda *args: None
    restored = provider.wait_restore(context, timeout=6300)
    for name, value in (("driver/restore_ready.json", restored["ready"]),
                        ("restore/restore_receipt.json", restored["probe"])):
        write(tmp_path, name, value["raw_utf8"].encode())
    parent = {"job": JOB, "run_id": plan.LOGICAL_RUN_ID, "request_sha256": "a" * 64,
        "bindings": b, "continuation": c, "restore_ready_sha256": restored["ready"]["sha256"],
        "restore_receipt_sha256": restored["probe"]["sha256"]}
    complete = {"status": "TEACHING_INCOMPLETE", "continuation_sha256": plan.canonical_sha256(c),
        "latest_summary_path": "train_continued_002/campaign_summary.json", "original_summary_path": "train_continued_001/campaign_summary.json",
        "restore_ready_sha256": parent["restore_ready_sha256"], "restore_receipt_sha256": parent["restore_receipt_sha256"]}
    write(tmp_path, "driver/identity.json", encode({"job": JOB, "run_id": parent["run_id"],
        "request_sha256": parent["request_sha256"], "prior": c, "permit": context["launch"]}))
    release = {"schema": "cas-teaching-continuation-train-release/1", "job": JOB, "run_id": parent["run_id"],
        "source_sha256": b["source_sha256"], "manifest_sha256": b["manifest_sha256"],
        "material_sha256": b["material_receipt_sha256"], "continuation_sha256": plan.canonical_sha256(c),
        "restore_ready_sha256": parent["restore_ready_sha256"],
        "restore_receipt_sha256": parent["restore_receipt_sha256"], "automatic_retries": 0}
    write(tmp_path, "input/train_release.json", encode(release))
    return {"root": tmp_path, "parent": parent, "complete": complete, "prior": prior}


def admit_evidence(evidence):
    return tool._continuation_evidence(evidence["parent"], evidence["complete"], evidence["root"], scorer._Reader(no_private))


def test_real_restore_admission_reconstructs_expected_prior_tree(evidence):
    result = admit_evidence(evidence)
    assert result["status"] == "PINNED_RESTORE_RECEIPT_AND_PRIOR_BYTES_VERIFIED"
    assert result["restored_steps"] == {arm: 774 if arm == "generic.ordinary" else 784 for arm in scorer.ARMS}
    assert result["actual_gpu_restore"] == "WORKER_RECORDED_PARENT_ADMITTED_NOT_RERUN_BY_EVALUATOR"


@pytest.mark.parametrize("target", ["prior", "first_continuation", "driver", "release", "restore", "identity"])
def test_tampered_continuation_evidence_blocks_admission(evidence, target):
    names = {"prior": "train/campaign_summary.json", "first_continuation": "train_continued_001/campaign_summary.json", "driver": "driver/remote.py",
        "release": "input/train_release.json", "restore": "restore/restore_receipt.json", "identity": "driver/identity.json"}
    path = evidence["root"] / names[target]
    if target in ("release", "identity"):
        value = json.loads(path.read_bytes())
        value["run_id"] = "wrong-logical-run"
        path.write_bytes(encode(value))
    else:
        path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises((ValueError, AssertionError)):
        admit_evidence(evidence)


def test_latest_and_original_summary_paths_cannot_swap(evidence):
    evidence["complete"]["latest_summary_path"] = "train/campaign_summary.json"
    with pytest.raises(ValueError, match="COMPLETE_BINDING"):
        admit_evidence(evidence)


def test_partial_without_restore_never_claims_restore(evidence):
    evidence["complete"].update(status="BLOCKED", restore_receipt_sha256=None)
    result = admit_evidence(evidence)
    assert result["actual_gpu_restore"] == "UNPROVEN"


@pytest.fixture
def collected(tmp_path, monkeypatch):
    value = old.collected.__wrapped__(tmp_path)
    helper_files = {name: (ROOT / name).read_bytes() for name in tool.SCORER_BUNDLE_DEPENDENCIES}
    source, manifest_pin = source_bundle(helper_files, value["packet"]["expected_source_sha256"])
    value["files"]["input/source.zip"] = source
    value["packet"]["expected_bundle_manifest_sha256"] = manifest_pin
    campaign = json.loads(value["files"].pop("train/campaign_summary.json"))
    campaign.update(run_id=plan.LOGICAL_RUN_ID, campaign_root=plan.ORIGINAL_CAMPAIGN_ROOT,
                    resumed_summary_sha256="a" * 64, manifest_sha256=manifest_pin)
    for row in campaign["arms"].values():
        row.update(max_epochs=16, observed_optimizer_steps=896)
    value["files"]["train_continued_002/campaign_summary.json"] = encode(campaign)
    value["files"]["train/campaign_summary.json"] = b"original summary preserved by separately tested gate"
    value["files"]["train_continued_001/campaign_summary.json"] = b"first continuation summary preserved by separately tested gate"
    # Frozen plan identities and actual restore admission are tested separately.
    monkeypatch.setattr(plan, "validate_bindings", lambda value: value)
    monkeypatch.setattr(plan, "validate_continuation", lambda value: value)
    monkeypatch.setattr(tool, "_continuation_evidence", lambda *args: {
        "status": "SYNTHETIC_GATE_SEAM_ONLY", "restored_steps": {
            arm: 774 if arm == "generic.ordinary" else 784 for arm in scorer.ARMS}})
    return value


def publish(value, partial=False):
    # Reuse only the old synthetic external packet construction, then bind the
    # new parent/complete schemas and original logical identity explicitly.
    files = value["files"]
    latest = files["train_continued_002/campaign_summary.json"]
    retained = files["train/campaign_summary.json"]
    files["train/campaign_summary.json"] = latest
    args = old.publish(value, partial=partial)
    files["train/campaign_summary.json"] = retained
    with ZipFile(args["archive"], "w", compression=ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            if not partial or not name.startswith(("predict1/", "predict2/")):
                archive.writestr(name, raw)
    digest = sha256(args["archive"].read_bytes()).hexdigest()
    parent = json.loads(args["parent_result"].read_bytes())
    complete = json.loads(args["complete_marker"].read_bytes())
    parent.update(schema="cas-teaching-continuation-parent-lifecycle/1", job=JOB, run_id=plan.LOGICAL_RUN_ID,
        status="TEACHING_INCOMPLETE" if partial else "TEACHING_CONTINUATION_COLLECTED_NOT_SCORED",
        continuation={"prior_summary_sha256": "a" * 64})
    complete.update(job=JOB, run_id=plan.LOGICAL_RUN_ID)
    for document in (parent["archive"], complete["artifact"]):
        document.update(sha256=digest, bytes=args["archive"].stat().st_size)
    args["parent_result"].write_bytes(encode(parent))
    args["complete_marker"].write_bytes(encode(complete))
    args.update(parent_sha256=sha256(args["parent_result"].read_bytes()).hexdigest(), archive_sha256=digest,
                complete_sha256=sha256(args["complete_marker"].read_bytes()).hexdigest())
    return args


def test_both_frozen_prediction_packets_admitted_before_synthetic_gold(collected):
    seen = set()
    def read(path):
        if "evaluator_private" in path.parts:
            assert all((f"predict{i}", name) in seen for i in (1, 2) for name in scorer.PREDICTION_NAMES)
        seen.add((path.parent.name, path.name))
        return path.read_bytes()
    result = tool.evaluate_collected(**publish(collected), reader=read)
    assert result["report"]["status"] == "TWO_READERS_SCORED"
    assert result["report"]["run_id"] == plan.LOGICAL_RUN_ID
    assert result["report"]["scorer_source_files"]["status"] == "SUPPLIED_SOURCE_FILE_PINS_CHECKED"
    assert result["report"]["scorer_source_files"]["file_count"] == 6
    for receipt in result["report"]["scores"]:
        scored = json.loads(Path(receipt["path"]).read_bytes())
        assert scored["identities"]["source_files"] == result["report"]["scorer_source_files"]


@pytest.mark.parametrize("field,value", [("run_id", "new-wrong-run"),
    ("resumed_summary_sha256", "b" * 64), ("campaign_root", "/tmp/changed"), ("all_allocations_finished", False)])
def test_full_summary_continuation_identity_checked_before_gold(collected, field, value):
    name = "train_continued_002/campaign_summary.json"
    document = json.loads(collected["files"][name])
    document[field] = value
    collected["files"][name] = encode(document)
    with pytest.raises(ValueError):
        tool.evaluate_collected(**publish(collected), reader=no_private)


def test_partial_counts_distinguish_restored_from_additional_updates(collected):
    name = "train_continued_002/campaign_summary.json"
    document = json.loads(collected["files"][name])
    document["all_allocations_finished"] = False
    for row in document["arms"].values():
        row.update(allocation_finished=False, observed_optimizer_steps=800)
    collected["files"][name] = encode(document)
    result = tool.evaluate_collected(**publish(collected, partial=True), reader=no_private)
    assert result["report"]["private_targets_opened"] is False and result["report"]["final_scores"] is None
    assert all(row["restored_optimizer_steps"] == (774 if arm == "generic.ordinary" else 784)
               and row["additional_optimizer_steps"] == (26 if arm == "generic.ordinary" else 16)
               for arm, row in result["report"]["exposure"].items())


def test_second_packet_corruption_prevents_first_private_score(collected):
    collected["files"]["predict2/cas.aligned.trained.test_fresh.json"] += b" "
    with pytest.raises(ValueError, match="FILE_HASH_MISMATCH"):
        tool.evaluate_collected(**publish(collected), reader=no_private)


@pytest.mark.parametrize("change,reason", [("different_prediction", "FRESH_READER_PREDICTIONS_CHANGED"),
                                          ("reused_pid", "FRESH_READER_PID_REUSED")])
def test_resealed_second_reader_disagreement_refuses_both_private_scores(collected, change, reason):
    old.alter_second(collected, **{change: True})
    with pytest.raises(ValueError, match=reason):
        tool.evaluate_collected(**publish(collected), reader=no_private)


@pytest.mark.parametrize("field,value", [("observed_optimizer_steps", 783), ("observed_optimizer_steps", 897),
    ("observed_optimizer_steps", True), ("observed_optimizer_steps", 800.0), ("max_epochs", 17)])
def test_partial_step_rewind_or_allocation_expansion_refuses_without_private(collected, field, value):
    name = "train_continued_002/campaign_summary.json"
    campaign = json.loads(collected["files"][name])
    campaign["arms"]["cas.aligned"][field] = value
    collected["files"][name] = encode(campaign)
    with pytest.raises(ValueError, match="CONTINUED_ALLOCATION_COUNT_INVALID"):
        tool.evaluate_collected(**publish(collected, partial=True), reader=no_private)


def test_all_three_summary_paths_are_preserved_without_using_old_summary_as_current(collected):
    args = publish(collected)
    before = {name: collected["files"][name] for name in (
        "train/campaign_summary.json", "train_continued_001/campaign_summary.json", "train_continued_002/campaign_summary.json")}
    result = tool.evaluate_collected(**args)
    extracted = Path(result["report"]["extraction"]["root"])
    assert all((extracted / name).read_bytes() == raw for name, raw in before.items())
    assert result["report"]["schema"] == "cas-teaching-continuation-collected-evaluation/2"


@pytest.mark.parametrize("member", ["../escape", "train_continued_002/../escape", "restore/NUL.txt", "input\\escape"])
def test_new_archive_paths_do_not_relax_extraction_safety(tmp_path, member):
    archive = tmp_path / "bad.zip"
    with ZipFile(archive, "w") as stream:
        stream.writestr(member, b"x")
    if "\\" in member:
        # Windows ZipFile normalizes this on write; preserve the intentionally
        # invalid raw member name in both ZIP headers for the parser test.
        archive.write_bytes(archive.read_bytes().replace(member.replace("\\", "/").encode(), member.encode()))
    with pytest.raises(ValueError, match="ARCHIVE_PATH"):
        tool.extract_verified(archive, tmp_path / "output", sha256(archive.read_bytes()).hexdigest())


@pytest.mark.parametrize("name", tool.SCORER_BUNDLE_DEPENDENCIES)
def test_active_helper_byte_drift_rejected_before_synthetic_private_read(collected, name):
    target = ROOT / name
    seen = []
    def read(path):
        assert "evaluator_private" not in path.parts
        seen.append(path)
        raw = path.read_bytes()
        return bytes((raw[0] ^ 1,)) + raw[1:] if path == target else raw
    with pytest.raises(ValueError, match="SOURCE_FILE_MISMATCH"):
        tool.evaluate_collected(**publish(collected), reader=read)
    assert target in seen


def test_source_pins_are_rechecked_after_both_public_admissions_before_scoring(collected):
    target = ROOT / "cas_meta2/codec.py"
    source_reads = 0
    def read(path):
        nonlocal source_reads
        assert "evaluator_private" not in path.parts
        raw = path.read_bytes()
        if path == target:
            source_reads += 1
            # Initial source admission, reader 1 and reader 2 admissions passed.
            # The first score_packet must check the same pins a fourth time.
            if source_reads == 4:
                return bytes((raw[0] ^ 1,)) + raw[1:]
        return raw
    with pytest.raises(ValueError, match="SOURCE_FILE_MISMATCH"):
        tool.evaluate_collected(**publish(collected), reader=read)
    assert source_reads == 4


def test_loaded_helper_from_a_different_path_is_rejected(collected, monkeypatch):
    monkeypatch.setattr(sys.modules["cas_meta2.codec"], "__file__",
                        str(collected["root"] / "different-source/codec.py"))
    with pytest.raises(ValueError, match="SCORER_ACTIVE_MODULE_PATH_MISMATCH"):
        tool.evaluate_collected(**publish(collected), reader=no_private)


@pytest.mark.parametrize("change,reason", [
    ("member", "SCORER_SOURCE_BUNDLE_MEMBER_CHANGED"),
    ("missing", "SCORER_SOURCE_DEPENDENCY_MISSING"),
    ("manifest", "SCORER_SOURCE_MANIFEST_PIN_MISMATCH"),
    ("duplicate", "SCORER_SOURCE_DUPLICATE_MEMBER"),
])
def test_source_bundle_tampering_is_rejected_before_synthetic_private_read(collected, change, reason):
    with ZipFile(io.BytesIO(collected["files"]["input/source.zip"])) as original:
        files = {item.filename: original.read(item) for item in original.infolist()}
    target = "cas_meta2/codec.py"
    if change == "member":
        files[target] += b"\n# changed synthetic fixture\n"
    elif change == "missing":
        del files[target]
    elif change == "manifest":
        files["manifest.json"] += b" "
    stream = io.BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
        if change == "duplicate":
            with pytest.warns(UserWarning, match="Duplicate name"):
                archive.writestr(target, files[target])
    collected["files"]["input/source.zip"] = stream.getvalue()
    with pytest.raises(ValueError, match=reason):
        tool.evaluate_collected(**publish(collected), reader=no_private)


def test_partial_report_also_records_pinned_local_scorer_helpers_without_private_reads(collected):
    result = tool.evaluate_collected(**publish(collected, partial=True), reader=no_private)
    assert result["report"]["status"] == "PARTIAL_EXPOSURE_ONLY"
    assert result["report"]["scorer_source_files"]["file_count"] == 6
    assert result["report"]["private_targets_opened"] is False
    assert result["report"]["final_scores"] is None
