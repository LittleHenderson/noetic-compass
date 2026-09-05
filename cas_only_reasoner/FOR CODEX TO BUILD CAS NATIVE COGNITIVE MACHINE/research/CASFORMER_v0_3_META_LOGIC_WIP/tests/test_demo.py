from hashlib import sha256
import json
import shutil
import sqlite3
import subprocess
import sys

import pytest

from cas_meta.demo import ROOT, run_demo, semantic_projection
from cas_meta.fixture import create_native, open_native, run_reference


def cli(*arguments):
    return subprocess.run([sys.executable, "-m", "cas_meta.demo", *map(str, arguments)],
                          cwd=ROOT, capture_output=True, text=True, check=False)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def native_head(path):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return connection.execute("SELECT * FROM active_head").fetchall()
    finally:
        connection.close()


@pytest.fixture(scope="module")
def prepared_cli(tmp_path_factory):
    # Only the public CLI prepares native state. No runtime fixture secretly
    # initializes the database needed by the resume subprocess.
    output = tmp_path_factory.mktemp("public-prepare") / "bundle"
    completed = cli("--prepare", output)
    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt == read_json(output / "creation_receipt.json")
    assert receipt["native_trace_count"] == receipt["native_head"]["state_version"] == 4
    assert receipt["spent"] == 288 and receipt["remaining"] == 224
    assert not (output / "worker_result.json").exists()
    assert sha256((output / "checkpoint.json").read_bytes()).hexdigest() == receipt["checkpoint_digest"]
    for name in ("compiled.db", "checkpoint.json", "creation_receipt.json"):
        assert (output / name).read_bytes() == (output / "paused" / name).read_bytes()
    return output


def copy_paused(prepared, target):
    shutil.copytree(prepared / "paused", target)
    return read_json(target / "creation_receipt.json")


def test_actual_fresh_process_resume_and_semantic_equivalence(tmp_path):
    result = run_demo(tmp_path / "demo")
    assert result["fresh_process_restart"]
    assert result["native_trace_count"] == 5
    assert result["accepted_effects"] == 4
    assert result["meta_event_count"] == 20
    assert result["budget_reserved_policy_units"] == 360
    assert result["semantic_projection_equal"]
    assert result["fixed_weights"]
    output = tmp_path / "demo"
    assert read_json(output / "paused" / "checkpoint.json")["head"]["state_version"] == 4
    assert read_json(output / "final_checkpoint.json")["head"]["state_version"] == 5
    replay = tmp_path / "replay-preserved-pause"
    receipt = copy_paused(output, replay)
    completed = cli("--resume", replay, "--expected-digest", receipt["checkpoint_digest"])
    assert completed.returncode == 0, completed.stderr
    assert read_json(replay / "worker_result.json")["native_head_before"]["state_version"] == 4


def test_documented_prepare_then_fresh_resume_preserves_continuation(prepared_cli, tmp_path):
    output = tmp_path / "independent-resume"
    receipt = copy_paused(prepared_cli, output)
    checkpoint = read_json(output / "checkpoint.json")
    completed = cli("--resume", output, "--expected-digest", receipt["checkpoint_digest"])
    assert completed.returncode == 0, completed.stderr
    worker = read_json(output / "worker_result.json")
    assert worker["restored_frames"] == checkpoint["frames"]
    assert [f["pc"] for f in worker["restored_frames"]] == [1, 1, 1]
    assert worker["native_head_before"] == checkpoint["head"]
    assert worker["native_head_after"]["state_version"] == 5
    assert (worker["spent_before"], worker["spent"]) == (288, 360)
    assert (worker["remaining_before"], worker["remaining_after"]) == (224, 152)
    assert worker["model_digest_before"] == worker["model_digest_after"] == receipt["model_digest"]
    assert worker["prior_native_projection_unchanged"] and worker["prior_meta_events_unchanged"]
    events = read_json(output / "meta_trace.json")
    assert events[:len(checkpoint["events"])] == checkpoint["events"]
    assert [e["cjt_id"] for e in events if e["kind"] == "NATIVE"] == ["A", "B", "C", "R", "C"]
    assert worker["repair_closed"] and worker["done"]
    resumed = open_native(output / "compiled.db")
    reference = create_native(tmp_path / "uninterrupted.db")
    try:
        run_reference(reference)
        assert semantic_projection(resumed) == semantic_projection(reference)
        assert resumed.state == reference.state
    finally:
        resumed.close()
        reference.close()


def test_wrong_digest_cli_rejects_without_changing_native_head(prepared_cli, tmp_path):
    output = tmp_path / "wrong-receipt"
    copy_paused(prepared_cli, output)
    before = native_head(output / "compiled.db")
    completed = cli("--resume", output, "--expected-digest", "0" * 64)
    assert completed.returncode != 0
    assert "CHECKPOINT_RECEIPT_MISMATCH" in completed.stderr
    assert native_head(output / "compiled.db") == before
    assert not (output / "worker_result.json").exists()


def test_completed_database_rejects_original_checkpoint_on_cli(prepared_cli, tmp_path):
    output = tmp_path / "already-consumed"
    receipt = copy_paused(prepared_cli, output)
    args = ("--resume", output, "--expected-digest", receipt["checkpoint_digest"])
    completed = cli(*args)
    assert completed.returncode == 0, completed.stderr
    before = native_head(output / "compiled.db")
    worker_bytes = (output / "worker_result.json").read_bytes()
    repeated = cli(*args)
    assert repeated.returncode != 0
    assert "NATIVE_HEAD_MISMATCH" in repeated.stderr
    assert native_head(output / "compiled.db") == before
    assert (output / "worker_result.json").read_bytes() == worker_bytes


@pytest.mark.parametrize("missing", ["compiled.db", "checkpoint.json"])
def test_cli_names_missing_dependency_without_recreating_it(prepared_cli, tmp_path, missing):
    output = tmp_path / "missing-dependency"
    receipt = copy_paused(prepared_cli, output)
    (output / missing).unlink()  # Only this test's newly copied disposable file.
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    completed = cli("--resume", output, "--expected-digest", receipt["checkpoint_digest"])
    assert completed.returncode != 0
    assert "MISSING_CHECKPOINT_DEPENDENCY:" + missing in completed.stderr
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


def test_each_new_cli_checkpoint_has_its_own_run_identity(prepared_cli, tmp_path):
    second = tmp_path / "another-run"
    completed = cli("--prepare", second)
    assert completed.returncode == 0, completed.stderr
    first_cp = read_json(prepared_cli / "checkpoint.json")
    second_cp = read_json(second / "checkpoint.json")
    assert first_cp["binding"]["run_id"] != second_cp["binding"]["run_id"]
    assert first_cp["head"] == second_cp["head"]
    for key in ("program_digest", "model_digest"):
        assert first_cp["binding"][key] == second_cp["binding"][key]
    assert read_json(prepared_cli / "creation_receipt.json")["checkpoint_digest"] != json.loads(completed.stdout)["checkpoint_digest"]


def test_prepare_cli_never_overwrites_existing_bundle(prepared_cli):
    before = (prepared_cli / "checkpoint.json").read_bytes()
    completed = cli("--prepare", prepared_cli)
    assert completed.returncode != 0
    assert (prepared_cli / "checkpoint.json").read_bytes() == before
