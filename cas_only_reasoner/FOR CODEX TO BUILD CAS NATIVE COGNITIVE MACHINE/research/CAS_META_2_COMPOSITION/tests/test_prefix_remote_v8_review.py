"""Independent pure remote regressions and parent/worker interface checks.

All budget data is synthetic and local to tmp_path. No ledger, model, provider,
subprocess, reservation, launch or metadata request is used by these tests.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "prefix_remote_v8_review", ROOT / "aws/prefix_remote_v8.py")
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def _pure_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = _pure_module("prefix_parent_interface_review", "aws/launch_prefix_diagnostic_v8.py")
g = _pure_module("prefix_gpu_interface_review", "cas_meta2/diagnostic_v8/gpu.py")


@pytest.fixture
def handoff(tmp_path, monkeypatch):
    """Exercise the real producer with fixture-only receipts, never real money."""
    source_archive = ROOT / "records/child_call_v8_diagnostic_001/source_001/source.zip"
    with ZipFile(source_archive) as archive:
        old = json.loads(archive.read("launch_manifest.json"))
    source = {"package_layout": {key: old[key] for key in (
        "pilot_dir", "meta1_dir", "meta_runtime_dir", "dependency_lock", "wheel_paths")}}
    request = {"job": "cas-meta2-20260906000000-c0ffee01", "parent_source_sha": "a" * 40,
               "resource_plan": p.resource_plan(), "source_archive": str(source_archive)}
    now = datetime(2026, 9, 6, tzinfo=timezone.utc)
    deadline = now + timedelta(seconds=3480)
    entry = {"job": request["job"], "source_sha": p.WORKER_SOURCE_SHA,
             "archive_sha256": p.SOURCE_ARCHIVE_SHA, "reserved_usd": "4.00",
             "reserved_utc": now.isoformat(), "status": "SYNTHETIC_TEST_ONLY",
             "plan": request["resource_plan"],
             "plan_sha256": p.digest(p.encoded(request["resource_plan"]))}
    ledger = {"schema": "SYNTHETIC_TEST_ONLY", "revision": 1,
              "owner_task_cap_usd": "400.00", "no_automatic_refund": True,
              "total_reserved_usd": "4.00", "remaining_unreserved_usd": "396.00",
              "reservations": [entry]}
    ledger_file = tmp_path / "synthetic_ledger.json"
    ledger_file.write_bytes(p.encoded(ledger))
    reservation = {"reservation": entry, "ledger_path": str(ledger_file),
                   "ledger_sha256": p.digest(ledger_file.read_bytes()), "revision": 1,
                   "total_reserved_usd": "4.00", "remaining_unreserved_usd": "396.00"}
    receipt_file = tmp_path / "synthetic_reservation.json"
    receipt_file.write_bytes(p.encoded(reservation))
    # checked_permit models Linux guest paths; do not change the host platform.
    monkeypatch.setattr(r, "REMOTE_ROOT", PurePosixPath("/opt/cas-meta2-prefix"))
    monkeypatch.setattr(r.time, "time", lambda: now.timestamp())
    config = p.remote_config(request, source)
    permit = p.worker_permit(request, source, reservation, ledger,
                             "i-0123456789abcdef0", deadline)
    return {"request": request, "config": config, "permit": permit,
            "deadline": deadline.timestamp(), "ledger": ledger_file, "receipt": receipt_file}


def _reseal_worker_plan(permit):
    permit["worker_plan_sha256"] = p.digest(p.encoded(permit["worker_plan"]))


def test_real_parent_permit_passes_remote_and_frozen_worker_bounds(handoff):
    config, permit = handoff["config"], handoff["permit"]
    assert r.validate_config(config) is config
    assert r.checked_permit(config, permit) == handoff["deadline"]
    plan = permit["worker_plan"]
    assert g.plan_bounds(plan, config["job"], r.BUNDLE_SHA) is plan
    assert p.encoded(plan) == r.canonical(plan) == g.canonical(plan)
    assert p.digest(p.encoded(plan)) == permit["worker_plan_sha256"]
    assert plan["source_sha"] == p.WORKER_SOURCE_SHA == r.SOURCE_SHA
    assert plan["bundle_manifest_sha256"] == p.BUNDLE_MANIFEST_SHA == r.BUNDLE_SHA
    expected = {
        "source_manifest": ("package/prefix_source_manifest.json", r.MANIFEST_SHA),
        "source_archive": ("source.zip", r.SOURCE_ARCHIVE_SHA),
        "reservation_receipt": ("launch/reservation_receipt.json", r.file_hash(handoff["receipt"])),
        "ledger_snapshot": ("launch/ledger_snapshot.json", r.file_hash(handoff["ledger"])),
    }
    for key, (suffix, digest) in expected.items():
        assert plan[key] == {"path": "/opt/cas-meta2-prefix/" + suffix, "sha256": digest}
    assert plan["max_seconds"] == 1800 and plan["tasks_per_checkpoint"] == 120
    assert plan["batch_size"] == 16 and plan["checkpoints"] == list(g.KEYS)
    assert plan["resource_plan"] == config["resource_plan"]


def test_parent_permit_changed_job_is_rejected(handoff):
    permit = deepcopy(handoff["permit"])
    permit["job"] = "cas-meta2-20260906000000-c0ffee02"
    with pytest.raises(ValueError, match="PREFIX_CLOUD_PERMISSION_MISMATCH"):
        r.checked_permit(handoff["config"], permit)


def test_parent_permit_unsealed_worker_change_is_rejected(handoff):
    permit = deepcopy(handoff["permit"])
    permit["worker_plan"]["batch_size"] = 8
    with pytest.raises(ValueError, match="PREFIX_WORKER_PLAN_HASH"):
        r.checked_permit(handoff["config"], permit)


@pytest.mark.parametrize("key", ["source_manifest", "source_archive", "reservation_receipt", "ledger_snapshot"])
def test_parent_permit_changed_remote_path_is_rejected_after_resealing(handoff, key):
    permit = deepcopy(handoff["permit"])
    permit["worker_plan"][key]["path"] = "/opt/cas-meta2-prefix/wrong.json"
    _reseal_worker_plan(permit)
    with pytest.raises(ValueError, match="PREFIX_REMOTE_PLAN_PATH_OR_BYTES"):
        r.checked_permit(handoff["config"], permit)


def test_parent_permit_changed_receipt_bytes_are_rejected(handoff):
    permit = deepcopy(handoff["permit"])
    permit["reservation_receipt"]["revision"] = 2
    with pytest.raises(ValueError, match="PREFIX_REMOTE_PLAN_PATH_OR_BYTES"):
        r.checked_permit(handoff["config"], permit)


def test_frozen_worker_rejects_resealed_batch_change(handoff):
    permit = deepcopy(handoff["permit"])
    permit["worker_plan"]["batch_size"] = 8
    _reseal_worker_plan(permit)
    # The remote layer checks its scope; the frozen worker owns this extra bound.
    assert r.checked_permit(handoff["config"], permit) == handoff["deadline"]
    with pytest.raises(ValueError, match="V8_DIAGNOSTIC_BOUNDS_CHANGED"):
        g.plan_bounds(permit["worker_plan"], handoff["config"]["job"], r.BUNDLE_SHA)


def test_worker_stage_counts_its_logs_outside_output_root(tmp_path, monkeypatch):
    """Simulate a large log without allocating it or starting any subprocess."""
    stage = tmp_path / "stage"
    runs = tmp_path / "runs"
    runs.mkdir()
    original_stat = Path.stat

    def fake_log_size(path, *args, **kwargs):
        value = original_stat(path, *args, **kwargs)
        if path == stage / "stdout.txt":
            fields = list(value)
            fields[6] = 501 * 1024**2
            return os.stat_result(fields)
        return value

    class FinishedAfterOneCheck:
        pid = 987654
        returncode = None
        polls = 0

        def poll(self):
            self.polls += 1
            if self.polls >= 2:
                self.returncode = 0
            return self.returncode

    monkeypatch.setattr(Path, "stat", fake_log_size)
    monkeypatch.setattr(r.subprocess, "Popen", lambda *a, **k: FinishedAfterOneCheck())
    monkeypatch.setattr(r.time, "sleep", lambda _: None)
    with pytest.raises(ValueError, match="PREFIX_CHILD_PROCESS_FAILED"):
        r.stage_process(["synthetic-only"], stage, env={}, cwd=tmp_path,
                        seconds=30, deadline=r.time.time() + 30, output_root=runs)
    receipt = json.loads((stage / "receipt.json").read_bytes())
    assert receipt["failure"]["message"] == "PREFIX_STAGE_ARTIFACT_BOUND"
    assert receipt["outputs"]["stdout.txt"]["bytes"] == 501 * 1024**2
