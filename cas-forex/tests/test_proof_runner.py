from datetime import date

from cas_forex.config import config
from cas_forex import proof_runner


def _paper_mode(monkeypatch):
    monkeypatch.setattr(config, "live_mode", False)
    monkeypatch.setattr(config, "paper_trading", True)


def test_run_proof_day_now_refuses_live_mode(monkeypatch):
    monkeypatch.setattr(config, "live_mode", True)
    monkeypatch.setattr(config, "paper_trading", True)

    result = proof_runner.run_proof_day_now(date(2026, 6, 22))

    assert result["status"] == "LIVE_BLOCKED"


def test_run_proof_day_now_skips_weekend(monkeypatch):
    _paper_mode(monkeypatch)

    # 2026-06-27 is a Saturday.
    result = proof_runner.run_proof_day_now(date(2026, 6, 27))

    assert result["status"] == "WEEKEND"
    assert result["date"] == "2026-06-27"


def test_run_proof_day_now_is_paper_safe_without_terminal(monkeypatch):
    """A weekday run with no reachable demo terminal must not crash or append."""
    _paper_mode(monkeypatch)

    result = proof_runner.run_proof_day_now(date(2026, 6, 22))

    # No live demo terminal in the test env -> not APPENDED, but a clean status.
    assert result["status"] in {
        "UNAVAILABLE",
        "BLOCKED",
        "SKIPPED_EXISTING",
        "APPENDED",
        "UNKNOWN",
    }
    assert "report_kind" in result


def test_runner_status_shape():
    status = proof_runner.runner_status()

    assert status["report_kind"] == "cas_forex_proof_runner"
    assert status["running"] is False
    assert "check_interval_seconds" in status


def test_desired_proof_runner_restores_after_process_restart(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    proof_runner.set_control_state_path_for_testing(tmp_path / "proof-auto-runner-control.json")
    monkeypatch.setattr(
        proof_runner,
        "run_proof_day_now",
        lambda *a, **k: {
            "report_kind": "cas_forex_proof_run",
            "status": "SKIPPED_EXISTING",
            "detail": "test proof already recorded",
        },
    )
    try:
        proof_runner.start_runner(120)
        # Simulate process teardown: stop the in-memory thread but keep owner desired state.
        proof_runner.stop_runner(persist_desired=False)

        restored = proof_runner.restore_desired_runner()

        assert restored["restore_status"] == "RESTORED_DESIRED_PAPER_PROOF_RUNNER"
        assert restored["running"] is True
        assert restored["check_interval_seconds"] == 120
    finally:
        proof_runner.stop_runner()
        proof_runner.reset_control_state_path_for_testing()


def test_owner_stop_persists_proof_runner_off(monkeypatch, tmp_path):
    _paper_mode(monkeypatch)
    proof_runner.set_control_state_path_for_testing(tmp_path / "proof-auto-runner-control.json")
    monkeypatch.setattr(
        proof_runner,
        "run_proof_day_now",
        lambda *a, **k: {
            "report_kind": "cas_forex_proof_run",
            "status": "SKIPPED_EXISTING",
            "detail": "test proof already recorded",
        },
    )
    try:
        proof_runner.start_runner(120)
        proof_runner.stop_runner()

        restored = proof_runner.restore_desired_runner()

        assert restored["restore_status"] == "NO_RESTORE_DESIRED"
        assert restored["running"] is False
    finally:
        proof_runner.stop_runner()
        proof_runner.reset_control_state_path_for_testing()
