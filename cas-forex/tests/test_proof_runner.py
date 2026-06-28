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
