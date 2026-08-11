from __future__ import annotations

from pathlib import Path

from api import data


def test_backsolve_summary_returns_unavailable_for_oversized_dashboard_report(
    monkeypatch,
    tmp_path: Path,
) -> None:
    evidence_root = tmp_path / "evidence_runs"
    backsolve_dir = evidence_root / "leverage_income_backsolve"
    backsolve_dir.mkdir(parents=True)
    report_path = backsolve_dir / "leverage-income-backsolve-20260706000100-report.json"
    report_path.write_text('{"run_id": "oversized"}', encoding="utf-8")
    monkeypatch.setattr(data, "EVIDENCE_ROOT", evidence_root)
    monkeypatch.setattr(data, "BACKSOLVE_DASHBOARD_MAX_BYTES", 4)

    summary = data.backsolve_summary()

    assert summary["status"] == "unavailable"
    assert summary["viable_scenarios"] == 0
    assert summary["deployment_status"] == "NOT LICENSED"
    assert "too large" in summary["detail"]
    assert summary["source_path"] == str(report_path)
