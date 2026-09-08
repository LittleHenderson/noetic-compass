"""Collected ZIP tests use synthetic byte checkpoints, not learning evidence."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import stat
import zipfile

import pytest

from cas_meta2.teaching_cycle import evaluation as scorer

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = load(ROOT / "tools/evaluate_teaching_launch.py", "synthetic_collected_tool")
fixtures = load(ROOT / "tests/test_teaching_cycle_evaluation.py", "synthetic_score_fixture")


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


@pytest.fixture
def collected(tmp_path):
    packet = fixtures.packet.__wrapped__(tmp_path)
    files = {"input/source.zip": b"Synthetic source archive, not a runnable model bundle."}
    campaign = json.loads(packet["campaign_summary_path"].read_bytes())
    campaign["run_id"] = "synthetic-collected"
    files["train/campaign_summary.json"] = encode(campaign)
    for path in packet["campaign_root"].rglob("*"):
        if path.is_file():
            files["train/campaign/" + path.relative_to(packet["campaign_root"]).as_posix()] = path.read_bytes()
    publics = {split: json.loads((packet["material_root"] / f"evaluation_public/{split}.json").read_bytes()) for split in scorer.SPLITS}
    files["input/public.json"] = encode(publics)
    for index in (1, 2):
        artifacts = {}
        for name in scorer.PREDICTION_NAMES:
            document = json.loads((packet["prediction_root"] / name).read_bytes())
            document["pid"] = 123 + index
            raw = encode(document)
            files[f"predict{index}/{name}"] = raw
            artifacts[name] = {"path": "/synthetic/" + name, "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
        files[f"predict{index}/prediction_seal.json"] = encode({"schema": "cas-teaching-blind-prediction-seal/1",
            "source_sha256": packet["expected_source_sha256"], "artifacts": artifacts,
            "private_targets_opened": False, "native_execution": "UNEXECUTED"})
    return {"packet": packet, "files": files, "root": tmp_path}


def publish(collected, *, partial=False):
    root, packet, files = collected["root"], collected["packet"], collected["files"]
    archive = root / "collected.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for name, raw in files.items():
            if not partial or not name.startswith(("predict1/", "predict2/")):
                output.writestr(name, raw)
    archive_hash = sha256(archive.read_bytes()).hexdigest()
    bindings = {"source_sha256": packet["expected_source_sha256"], "manifest_sha256": packet["expected_bundle_manifest_sha256"],
                "material_receipt_sha256": packet["expected_material_sha256"],
                "scorer_sha256": sha256(Path(scorer.__file__).read_bytes()).hexdigest(),
                "archive_sha256": sha256(files.get("input/source.zip", b"unavailable pinned source")).hexdigest(),
                "public_sets_sha256": sha256(files["input/public.json"]).hexdigest()}
    seals = [{"run_index": index, "key": f"results/predict{index}/prediction_seal.json",
              "sha256": sha256(files[f"predict{index}/prediction_seal.json"]).hexdigest(),
              "bytes": len(files[f"predict{index}/prediction_seal.json"])} for index in (1, 2)]
    artifact = {"key": "results/artifacts.zip", "sha256": archive_hash, "bytes": archive.stat().st_size}
    complete = {"schema": "cas-teaching-guest-complete/1", "job": "synthetic-collected", "run_id": "synthetic-collected",
                "source_sha256": bindings["source_sha256"], "manifest_sha256": bindings["manifest_sha256"],
                "material_sha256": bindings["material_receipt_sha256"], "status": "TEACHING_INCOMPLETE" if partial else "COMPLETE",
                "artifact": artifact, "training_ready_sha256": "6" * 64,
                "campaign_summary_sha256": sha256(files["train/campaign_summary.json"]).hexdigest() if "train/campaign_summary.json" in files else None,
                "prediction_seals": [] if partial else seals}
    parent = {"schema": "cas-teaching-cycle-parent-lifecycle/2", "job": "synthetic-collected", "bindings": bindings,
              "status": "TEACHING_INCOMPLETE" if partial else "TEACHING_CYCLE_COLLECTED_NOT_SCORED",
              "archive": {**artifact, "local_bytes_verified": True}, "training_ready_sha256": complete["training_ready_sha256"],
              "campaign_summary_sha256": complete["campaign_summary_sha256"], "prediction_seals": complete["prediction_seals"]}
    parent_path, complete_path = root / "parent.json", root / "complete.json"
    parent_path.write_bytes(encode(parent))
    complete_path.write_bytes(encode(complete))
    return {"parent_result": parent_path, "parent_sha256": sha256(parent_path.read_bytes()).hexdigest(),
            "archive": archive, "archive_sha256": archive_hash, "complete_marker": complete_path,
            "complete_sha256": sha256(complete_path.read_bytes()).hexdigest(), "material_root": packet["material_root"],
            "output": root / "evaluation"}


def test_two_complete_packets_compared_before_any_private_target_read(collected):
    args = publish(collected)
    seen = set()
    def guarded(path):
        if "evaluator_private" in path.parts:
            for index in (1, 2):
                assert {(f"predict{index}", name) for name in scorer.PREDICTION_NAMES} <= seen
        seen.add((path.parent.name, path.name))
        return path.read_bytes()
    result = tool.evaluate_collected(**args, reader=guarded)
    assert result["report"]["status"] == "TWO_READERS_SCORED"
    assert result["report"]["reader_comparison"]["prediction_files_compared"] == 24
    assert result["report"]["reader_comparison"]["predictions_equal"] is True
    assert result["report"]["native_execution"] == "UNEXECUTED"
    assert result["report"]["retention_after_intervening_learning"] == "UNEXECUTED"
    assert args["archive"].is_file()


def alter_second(collected, *, different_prediction=False, reused_pid=False):
    name = "cas.aligned.trained.test_fresh.json"
    document = json.loads(collected["files"]["predict2/" + name])
    if different_prediction:
        document["predictions"][0] = (document["predictions"][0] + 1) % 3
    if reused_pid:
        for member in scorer.PREDICTION_NAMES:
            row = json.loads(collected["files"]["predict2/" + member])
            row["pid"] = 124
            collected["files"]["predict2/" + member] = encode(row)
    else:
        collected["files"]["predict2/" + name] = encode(document)
    seal = json.loads(collected["files"]["predict2/prediction_seal.json"])
    for member in scorer.PREDICTION_NAMES:
        raw = collected["files"]["predict2/" + member]
        seal["artifacts"][member].update(sha256=sha256(raw).hexdigest(), bytes=len(raw))
    collected["files"]["predict2/prediction_seal.json"] = encode(seal)


@pytest.mark.parametrize("change,reason", [("different_prediction", "FRESH_READER_PREDICTIONS_CHANGED"),
                                          ("reused_pid", "FRESH_READER_PID_REUSED")])
def test_second_reader_disagreement_is_rejected_before_private(collected, change, reason):
    alter_second(collected, **{change: True})
    args = publish(collected)
    def no_private(path):
        assert "evaluator_private" not in path.parts
        return path.read_bytes()
    with pytest.raises(ValueError, match=reason):
        tool.evaluate_collected(**args, reader=no_private)


def test_corrupt_second_seal_blocks_first_reader_private_scoring(collected):
    collected["files"]["predict2/cas.aligned.trained.test_fresh.json"] += b" "
    args = publish(collected)
    def no_private(path):
        assert "evaluator_private" not in path.parts
        return path.read_bytes()
    with pytest.raises(ValueError, match="FILE_HASH_MISMATCH"):
        tool.evaluate_collected(**args, reader=no_private)


def test_partial_training_reports_exposure_without_gold_or_final_scores(collected):
    args = publish(collected, partial=True)
    def no_private(path):
        assert "evaluator_private" not in path.parts
        return path.read_bytes()
    result = tool.evaluate_collected(**args, reader=no_private)
    assert result["report"]["status"] == "PARTIAL_EXPOSURE_ONLY"
    assert result["report"]["private_targets_opened"] is False
    assert result["report"]["final_scores"] is None
    assert set(result["report"]["exposure"]) == set(scorer.ARMS)


@pytest.mark.parametrize("member", ["../escape", "/absolute", "train/../escape", "train\\escape", "train/NUL.txt", "train/trailing."])
def test_archive_traversal_and_windows_aliases_rejected_before_extraction(tmp_path, member):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(member, b"x")
    if "\\" in member:
        archive.write_bytes(archive.read_bytes().replace(member.replace("\\", "/").encode(), member.encode()))
    with pytest.raises(ValueError, match="ARCHIVE_PATH_REJECTED"):
        tool.extract_verified(archive, tmp_path / "out", sha256(archive.read_bytes()).hexdigest())
    assert not (tmp_path / "out").exists() and archive.is_file()


@pytest.mark.parametrize("kind", ["case", "duplicate", "symlink", "file_directory"])
def test_archive_collisions_and_links_fail_closed(tmp_path, kind):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("train/file", b"x")
        if kind == "symlink":
            info = zipfile.ZipInfo("train/link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            output.writestr(info, b"file")
        elif kind == "file_directory":
            output.writestr("train/file/child", b"x")
        elif kind == "duplicate":
            with pytest.warns(UserWarning):
                output.writestr("train/file", b"x")
        else:
            output.writestr("train/FILE", b"x")
    with pytest.raises(ValueError):
        tool.extract_verified(archive, tmp_path / "out", sha256(archive.read_bytes()).hexdigest())
    assert not (tmp_path / "out").exists()


def test_expanded_limit_is_enforced_without_allocating_large_files(tmp_path, monkeypatch):
    archive = tmp_path / "large.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        output.writestr("train/payload", b"x" * 1000)
    monkeypatch.setattr(tool, "LIMIT", 500)
    with pytest.raises(ValueError, match="EXPANDED_ARCHIVE_BYTE_LIMIT"):
        tool.extract_verified(archive, tmp_path / "out", sha256(archive.read_bytes()).hexdigest())


@pytest.mark.parametrize("pin", ["parent_sha256", "archive_sha256", "complete_sha256"])
def test_external_pin_changes_refused_before_private(collected, pin):
    args = publish(collected)
    args[pin] = "9" * 64
    with pytest.raises(ValueError):
        tool.evaluate_collected(**args, reader=lambda path: (_ for _ in ()).throw(AssertionError())
                                if "evaluator_private" in path.parts else path.read_bytes())


def test_early_infrastructure_failure_allows_missing_source_but_claims_no_teaching(collected):
    collected["files"] = {name: raw for name, raw in collected["files"].items()
                           if name != "input/source.zip" and not name.startswith("train/")}
    collected["files"]["driver/failure.json"] = encode({"status": "SOURCE_DOWNLOAD_FAILED"})
    args = publish(collected, partial=True)
    for path_key, pin_key in (("parent_result", "parent_sha256"), ("complete_marker", "complete_sha256")):
        path = args[path_key]
        document = json.loads(path.read_bytes())
        document["status"] = "TEACHING_CYCLE_BLOCKED" if path_key == "parent_result" else "BLOCKED"
        path.write_bytes(encode(document))
        args[pin_key] = sha256(path.read_bytes()).hexdigest()
    def no_private(path):
        assert "evaluator_private" not in path.parts
        return path.read_bytes()
    result = tool.evaluate_collected(**args, reader=no_private)["report"]
    assert result["status"] == "INFRASTRUCTURE_FAILURE_ONLY"
    assert result["source_copy_available"] is False
    assert result["exposure"] is None and result["final_scores"] is None
