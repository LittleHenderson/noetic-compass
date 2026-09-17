"""Pure delivery/admission regressions; no numerical runtime is executed."""
from copy import deepcopy
from hashlib import sha256
import ast
import importlib.abc
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from cncm import typed_course_worker as worker

ROOT = Path(__file__).resolve().parents[1]


def test_artifact_contract_flat_unique_and_complete():
    names = worker.EXPECTED_ARTIFACTS
    assert len(names) == 344 == len(set(names))
    assert all(Path(name).name == name and "/" not in name for name in names)
    assert "manifest.json" not in names
    assert all("batch_%03d.json" % n in names and "update_%03d.json" % n in names for n in range(160))
    assert {"initial.pt", "prelast.pt", "final.pt", "replay_report.json"} <= set(names)


def test_counter_delta_does_not_recount_restored_history():
    assert worker.counter_delta({"updates": 160, "calls": 180}, {"updates": 159, "calls": 172}) == {"updates": 1, "calls": 8}


@pytest.mark.parametrize("after,before", [({"x": True}, {"x": 0}), ({"x": 1.0}, {"x": 0}),
    ({"x": 1}, {"x": -1}), ({"x": 0}, {"x": 1}), ({"x": 1}, {"y": 0})])
def test_counter_aliases_and_regressions_refused(after, before):
    with pytest.raises(ValueError):
        worker.counter_delta(after, before)


def training_delta():
    return {"slot_forwards": 4613, "core_forward_calls": 17178, "core_forward_attempts": 17178,
        "sample_core_passes": 17178, "prediction_calls": 1152, "staged_batches": 160,
        "private_loss_plan_calls": 1152, "backward_attempts": 160, "backward_calls": 160,
        "optimizer_step_attempts": 160, "optimizer_updates": 160}


def test_exact_main_contract():
    assert worker.validate_training_delta(training_delta()) == training_delta()


@pytest.mark.parametrize("key", list(training_delta()))
def test_partial_main_is_not_success(key):
    delta = training_delta()
    delta[key] -= 1
    with pytest.raises(ValueError, match="MAIN_TRAINING_COUNTERS"):
        worker.validate_training_delta(delta)


def test_seal_exact_bytes_and_no_overwrite(tmp_path):
    raw = b'{"only":"public"}\n'
    path = tmp_path / "batch.json"
    receipt = worker._write_bytes(path, raw)
    assert receipt == {"name": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    with pytest.raises(FileExistsError):
        worker._write_bytes(path, b"changed")
    assert path.read_bytes() == raw


def test_scoring_rejects_stale_seal_before_private_import(tmp_path):
    path = tmp_path / "predictions.json"
    receipt = worker._write(path, {"predictions": []})
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="SCORING_SEAL_CHANGED"):
        worker._score_seal(path, receipt, {}, started=worker.time.monotonic())


def test_failure_delivery_preserves_partial_files(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    worker._write(artifacts / "batch_000.json", {"public": True})
    report = {"job": "example", "source_sha": "a" * 40, "status": "TYPED_COURSE_FAILED",
              "failure": {"schema": worker.FAILURE_SCHEMA, "type": "ValueError", "detail": "refused"}}
    result = worker.deliver(tmp_path, artifacts, report, failed=True)
    assert result["status"] == "TYPED_COURSE_FAILED"
    for row in result["artifacts"]:
        raw = (artifacts / row["name"]).read_bytes()
        assert len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"]
    assert (tmp_path / "result.json.sha256").read_text().strip() == sha256((tmp_path / "result.json").read_bytes()).hexdigest()
    assert result["summary"]["learning_advantage_established"] is False


def test_success_delivery_requires_every_batch(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    with pytest.raises(ValueError, match="REQUIRED_ARTIFACTS"):
        worker.deliver(tmp_path, artifacts, {"job": "example"}, failed=False)


def test_real_material_windows_refusal_is_delivered_before_numerical_import(tmp_path, monkeypatch):
    from cas_meta2.teaching_cycle import gpu_adapter
    forbidden = {"torch", "numpy", "cas_cjt", "casformer", "boto3", "requests"}
    attempted = []
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in forbidden:
                attempted.append(fullname)
                raise AssertionError("numerical/provider import attempted")
    guard = Guard()
    monkeypatch.setattr(gpu_adapter.platform, "system", lambda: "Windows")
    config = worker.contract.make_config(ROOT, source_sha="a" * 40,
        job="cas-meta2-typedcourse-20260917000000-aaaaaaaa", bucket="typed-pure-test")
    sys.meta_path.insert(0, guard)
    try:
        with pytest.raises(ValueError, match="^TEACHING_GPU:LINUX_WORKER_REQUIRED$"):
            worker.run(config, ROOT, tmp_path, tmp_path / "artifacts")
    finally:
        sys.meta_path.remove(guard)
    receipt = json.loads((tmp_path / "result.json").read_bytes())
    assert receipt["failure"] == {"schema": worker.FAILURE_SCHEMA, "type": "ValueError",
                                  "detail": "TEACHING_GPU:LINUX_WORKER_REQUIRED"}
    assert receipt["status"] == "TYPED_COURSE_FAILED" and attempted == []
    assert not forbidden.intersection(sys.modules)
    report = json.loads((tmp_path / "artifacts/worker_report.json").read_bytes())
    assert report["phase"] == "preflight"
    progress = [json.loads(p.read_bytes()) for p in sorted((tmp_path / "evidence").glob("typed_progress_*.json"))]
    assert [row["typed_course_phase"] for row in progress] == ["preflight", "failed/preflight"]
    assert progress[-1]["completed_main_updates"] == 0


def test_fresh_builder_seeds_before_registered_construction():
    tree = ast.parse(Path(worker.__file__).read_text(encoding="utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_fresh_framework")
    text = ast.unparse(function)
    assert text.index("torch.manual_seed") < text.index("return build_graph_training_framework")
    assert text.index("torch.cuda.manual_seed_all") < text.index("return build_graph_training_framework")
    assert "encoder={'d_model': 64}" in text


def test_no_eager_numerical_or_private_import():
    tree = ast.parse(Path(worker.__file__).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names] + [getattr(node, "module", "") or ""]
            assert not any(name.split(".")[0] in {"torch", "numpy", "boto3", "checker", "loss_plan"} for name in names)


def test_progress_is_complete_before_atomic_publication_and_never_overwritten(tmp_path, monkeypatch):
    results = tmp_path / "results"; results.mkdir()
    original_rename = Path.rename
    observed = []
    def watched_rename(staged, destination):
        assert not staged.is_relative_to(results)
        assert not destination.exists()
        raw = staged.read_bytes(); row = json.loads(raw)
        assert row["index"] == len(observed)
        assert row["typed_course_phase"] in {"initial_predictions", "main_training"}
        observed.append((destination, raw))
        return original_rename(staged, destination)
    monkeypatch.setattr(Path, "rename", watched_rename)
    writer = worker._ProgressWriter(results, worker.time.monotonic())
    writer.emit("initial_predictions", completed_packets=50, total_packets=564)
    writer.emit("main_training", completed_main_updates=10, total_main_updates=160, raw_batch_loss=0.75)
    assert len(observed) == 2
    assert [p.name for p, _ in observed] == ["typed_progress_0000.json", "typed_progress_0001.json"]
    for path, raw in observed:
        assert path.read_bytes() == raw and json.loads(raw)["elapsed_seconds"] >= 0
    writer.index = 0
    with pytest.raises(ValueError, match="PROGRESS_ALREADY_EXISTS"):
        writer.emit("would_replace_prior_record")
    assert observed[0][0].read_bytes() == observed[0][1]
    assert not list(tmp_path.glob(".typed-progress-*"))


def test_failed_progress_rename_exposes_no_partial_file(tmp_path, monkeypatch):
    results = tmp_path / "results"; results.mkdir()
    def refuse(staged, destination):
        assert not staged.is_relative_to(results) and json.loads(staged.read_bytes())
        raise OSError("SYNTHETIC_RENAME_FAILURE")
    monkeypatch.setattr(Path, "rename", refuse)
    writer = worker._ProgressWriter(results, worker.time.monotonic())
    with pytest.raises(OSError, match="SYNTHETIC_RENAME_FAILURE"):
        writer.emit("initial_predictions", completed_packets=50, total_packets=564)
    assert not list((results / "evidence").iterdir()) and writer.index == 0
    assert not list(tmp_path.glob(".typed-progress-*"))


def test_scoring_progress_counts_only_checked_sealed_rows(tmp_path, monkeypatch):
    import cas_meta2.typed_teaching as package
    checked = []
    def check(public, query, answer):
        checked.append(query["index"])
        return {"correct": False}
    checker = SimpleNamespace(check_answer=check)
    monkeypatch.setitem(sys.modules, "cas_meta2.typed_teaching.checker", checker)
    monkeypatch.setattr(package, "checker", checker, raising=False)
    keys = ["id%03d" % i for i in range(101)]
    predictions = [{"record_id": key, "prediction_id": key + "-prediction", "answer": {}} for key in keys]
    packets = {key: {"source": {}, "record": {"query": {"index": i}}} for i, key in enumerate(keys)}
    path = tmp_path / "sealed.json"
    pin = worker._sealed_predictions(path, predictions, phase="initial", expected_ids=keys)
    progress = []
    def capture(phase, **counts):
        assert phase == "initial_scoring" and counts["completed_packets"] == len(checked)
        progress.append(counts)
    result = worker._score_seal(path, pin, packets, started=worker.time.monotonic(), progress=capture)
    assert [row["completed_packets"] for row in progress] == [0, 50, 100, 101]
    assert all(row["total_packets"] == 101 for row in progress)
    assert checked == list(range(101)) and result["total"] == 101 and result["correct"] == 0


def test_partial_checkpoint_is_atomic_bound_and_does_not_replace_required_artifacts(tmp_path, monkeypatch):
    results = tmp_path / "results"; results.mkdir()
    raw = b"EXPLICIT PURE CHECKPOINT STUB, NOT A NUMERICAL MODEL"
    exported = []
    class Learner:
        def export_checkpoint(self, path):
            assert not path.is_relative_to(results) and not path.exists()
            path.write_bytes(raw); exported.append(path)
            return {"path": str(path.resolve()), "bytes": len(raw), "sha256": sha256(raw).hexdigest(),
                    "run_identity_digest": "a"*64, "metadata": {"cursor": 20}}
    original_rename = Path.rename
    publications = []
    def watched_rename(staged, destination):
        assert not staged.is_relative_to(results) and not destination.exists()
        publications.append((destination.name, staged.read_bytes()))
        return original_rename(staged, destination)
    monkeypatch.setattr(Path, "rename", watched_rename)
    before_rng = worker.random.getstate()
    metadata = worker._partial_checkpoint(Learner(), results, 20)
    assert worker.random.getstate() == before_rng
    assert len(exported) == 1 and [name for name, _ in publications] == ["main_checkpoint_0020.pt", "main_checkpoint_0020.json"]
    checkpoint = results / "evidence/main_checkpoint_0020.pt"
    assert checkpoint.read_bytes() == raw and metadata["checkpoint"]["path"] == str(checkpoint.resolve())
    assert metadata["checkpoint"]["sha256"] == sha256(raw).hexdigest()
    assert metadata["completed_main_updates"] == 20 and metadata["main_course_complete"] is False
    assert json.loads((results / "evidence/main_checkpoint_0020.json").read_bytes()) == metadata
    with pytest.raises(ValueError, match="PARTIAL_CHECKPOINT_ALREADY_EXISTS"):
        worker._partial_checkpoint(Learner(), results, 20)
    assert checkpoint.read_bytes() == raw and len(exported) == 1
    assert len(worker.EXPECTED_ARTIFACTS) == 344
    assert not any("main_checkpoint_" in name for name in worker.EXPECTED_ARTIFACTS)
    assert not list(tmp_path.glob(".typed-checkpoint-*"))


def test_progress_and_partial_checkpoint_cadence_does_not_add_training_calls():
    tree = ast.parse(Path(worker.__file__).read_text(encoding="utf-8"))
    run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
    calls = [n for n in ast.walk(run) if isinstance(n, ast.Call)]
    assert len([n for n in calls if ast.unparse(n.func) == "main.train_sealed_batch"]) == 1
    partial = next(n for n in ast.walk(run) if isinstance(n, ast.If) and "range(20, 160, 20)" in ast.unparse(n.test))
    assert [ast.unparse(n.func) for n in ast.walk(partial) if isinstance(n, ast.Call)].count("_partial_checkpoint") == 1
    assert set(range(20, 160, 20)) == {20, 40, 60, 80, 100, 120, 140}
    assert "main.cursor % 10 == 0" in ast.unparse(run)
    assert "len(rows) % 50 == 0 or len(rows) == len(packets)" in ast.unparse(run)
