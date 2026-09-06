"""Synthetic capture failures; no subprocess or provider is actually started."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def harness(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / "tools/check_br_snapshot_v8.py"
    spec = importlib.util.spec_from_file_location("br_capture_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path
    module.checks.RECORDS = tmp_path / "captures"
    module.checks.RECORDS.mkdir()
    budget = tmp_path / "records/budget/campaign_ledger.json"
    budget.parent.mkdir(parents=True)
    budget.write_text('{"synthetic_test_ledger": true}')
    request = tmp_path / "records/child_call_v8_launch_connection_001/launch_request.json"
    request.parent.mkdir(parents=True)
    request.write_text('{"parent_file_sha256": {}}')
    monkeypatch.setattr(module.importlib.util, "find_spec", lambda _: SimpleNamespace(origin=str(tmp_path / "pytest/__init__.py")))
    def fake_process(command, *, cwd, stdout, stderr):
        stdout.write(b"synthetic child output retained\n")
        stderr.write(b"synthetic diagnostic retained\n")
        return SimpleNamespace(pid=17, wait=lambda **_: 0)
    monkeypatch.setattr(module.subprocess, "Popen", fake_process)
    return module, budget


@pytest.mark.parametrize("failed_check", ["frozen_sources", "budget"])
def test_postcheck_failure_receipts_raw_logs(tmp_path, monkeypatch, failed_check):
    module, budget = harness(tmp_path, monkeypatch)
    calls = 0
    def source_check():
        nonlocal calls
        calls += 1
        if calls == 2:
            if failed_check == "frozen_sources":
                raise ValueError("synthetic protected source changed")
            budget.unlink()  # Only this test's disposable synthetic ledger.
        return {"synthetic_source": "unchanged"}
    monkeypatch.setattr(module.checks, "sources", source_check)
    output = module.checks.RECORDS / "new_capture"
    assert module.capture(output) == 1
    receipt = json.loads((output / "receipt.json").read_bytes())
    assert failed_check in receipt["postcheck_errors"]
    assert receipt["exit_code"] == 0  # Synthetic child success is not capture success.
    assert (output / "stdout.txt").read_bytes() == b"synthetic child output retained\n"
    assert (output / "stderr.txt").read_bytes() == b"synthetic diagnostic retained\n"
    assert receipt["source_unchanged"] is (failed_check != "frozen_sources")
    assert receipt["budget_unchanged"] is (failed_check != "budget")
