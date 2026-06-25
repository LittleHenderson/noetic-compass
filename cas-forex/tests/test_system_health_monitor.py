"""Tests for the pure system-health composer.

The composer summarises live processes, evidence freshness, disk space,
and recent error count. It MUST stay observational — no imperative
phrases anywhere in summary or hints.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cas_forex.system_health_monitor import (
    DiskSpace,
    SystemHealthSnapshot,
    compose_system_health,
)


FORBIDDEN_IMPERATIVES: tuple[str, ...] = (
    "you should restart",
    "consider restarting",
    "kill the",
    "should be killed",
    "force restart",
)


def _iso(ts: datetime) -> str:
    return ts.isoformat()


def _now() -> datetime:
    return datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)


def _assert_no_imperatives(snap: SystemHealthSnapshot) -> None:
    blob = " ".join([snap.plain_english_summary, *snap.diagnostic_hints]).lower()
    for phrase in FORBIDDEN_IMPERATIVES:
        assert phrase not in blob, f"forbidden imperative phrase present: {phrase!r}"


# ---------------------------------------------------------------------------
# 1. Unknown when everything is None
# ---------------------------------------------------------------------------


def test_all_none_yields_unknown() -> None:
    snap = compose_system_health(
        process_signals={
            "uvicorn-api": None,
            "autowake-supervisor": None,
            "mt5-terminal": None,
        },
        artifact_latests={
            "agent-workflow-cycle": None,
            "session-autowake": None,
        },
        disk_space=None,
        recent_error_count=0,
        now=_now(),
    )
    assert snap.overall_status == "unknown"
    _assert_no_imperatives(snap)


# ---------------------------------------------------------------------------
# 2. Healthy when everything is fresh + disk OK
# ---------------------------------------------------------------------------


def test_all_alive_fresh_disk_ok_yields_healthy() -> None:
    now = _now()
    recent = _iso(now - timedelta(seconds=60))
    snap = compose_system_health(
        process_signals={
            "uvicorn-api": recent,
            "autowake-supervisor": recent,
            "mt5-terminal": recent,
        },
        artifact_latests={
            "agent-workflow-cycle": recent,
            "live-telemetry": recent,
        },
        disk_space=DiskSpace(
            repo_root="/tmp/repo",
            evidence_runs_bytes=1_000_000,
            free_disk_bytes=200 * (1024 ** 3),
            free_disk_pct=50.0,
        ),
        recent_error_count=0,
        now=now,
    )
    assert snap.overall_status == "healthy"
    assert all(p.likely_alive for p in snap.processes if p.expected)
    assert all(a.fresh for a in snap.evidence_freshness)
    _assert_no_imperatives(snap)


# ---------------------------------------------------------------------------
# 3. Stale expected process -> degraded
# ---------------------------------------------------------------------------


def test_one_stale_expected_process_yields_degraded() -> None:
    now = _now()
    snap = compose_system_health(
        process_signals={
            "uvicorn-api": _iso(now - timedelta(seconds=60)),
            "autowake-supervisor": _iso(now - timedelta(seconds=5000)),  # stale
            "mt5-terminal": _iso(now - timedelta(seconds=60)),
        },
        artifact_latests={},
        disk_space=DiskSpace(
            repo_root="/tmp/repo",
            evidence_runs_bytes=0,
            free_disk_bytes=100 * (1024 ** 3),
            free_disk_pct=40.0,
        ),
        now=now,
    )
    assert snap.overall_status == "degraded"
    stale = [p for p in snap.processes if p.process_name == "autowake-supervisor"][0]
    assert stale.status_label == "stale"
    assert any("autowake-supervisor" in h for h in snap.diagnostic_hints)
    _assert_no_imperatives(snap)


# ---------------------------------------------------------------------------
# 4. Missing expected process -> stale
# ---------------------------------------------------------------------------


def test_one_missing_expected_process_yields_stale() -> None:
    now = _now()
    snap = compose_system_health(
        process_signals={
            "uvicorn-api": _iso(now - timedelta(seconds=60)),
            "autowake-supervisor": None,
            "mt5-terminal": _iso(now - timedelta(seconds=60)),
        },
        artifact_latests={},
        disk_space=None,
        now=now,
    )
    assert snap.overall_status == "stale"
    missing = [p for p in snap.processes if p.process_name == "autowake-supervisor"][0]
    assert missing.status_label == "missing"
    assert any("autowake-supervisor" in h for h in snap.diagnostic_hints)
    _assert_no_imperatives(snap)


# ---------------------------------------------------------------------------
# 5. Low disk -> degraded + hint
# ---------------------------------------------------------------------------


def test_low_disk_yields_degraded_with_hint() -> None:
    now = _now()
    recent = _iso(now - timedelta(seconds=60))
    snap = compose_system_health(
        process_signals={
            "uvicorn-api": recent,
            "autowake-supervisor": recent,
            "mt5-terminal": recent,
        },
        artifact_latests={},
        disk_space=DiskSpace(
            repo_root="/tmp/repo",
            evidence_runs_bytes=0,
            free_disk_bytes=2 * (1024 ** 3),
            free_disk_pct=2.5,
        ),
        now=now,
    )
    assert snap.overall_status == "degraded"
    assert any("below 5%" in h for h in snap.diagnostic_hints)
    _assert_no_imperatives(snap)


# ---------------------------------------------------------------------------
# 6. Per-process status labels: alive/stale/missing/expected_off
# ---------------------------------------------------------------------------


def test_per_process_status_labels() -> None:
    now = _now()
    snap = compose_system_health(
        process_signals={
            "uvicorn-api": _iso(now - timedelta(seconds=10)),       # alive
            "autowake-supervisor": _iso(now - timedelta(seconds=9999)),  # stale
            "mt5-terminal": None,                                    # missing (expected)
            "notification-dispatcher": None,                         # expected_off (not in expected set)
        },
        artifact_latests={},
        now=now,
    )
    by_name = {p.process_name: p for p in snap.processes}
    assert by_name["uvicorn-api"].status_label == "alive"
    assert by_name["uvicorn-api"].likely_alive is True
    assert by_name["autowake-supervisor"].status_label == "stale"
    assert by_name["autowake-supervisor"].likely_alive is False
    assert by_name["mt5-terminal"].status_label == "missing"
    assert by_name["notification-dispatcher"].status_label == "expected_off"
    assert by_name["notification-dispatcher"].expected is False
    _assert_no_imperatives(snap)


# ---------------------------------------------------------------------------
# 7. Per-artifact freshness correctness
# ---------------------------------------------------------------------------


def test_artifact_freshness_correctness() -> None:
    now = _now()
    snap = compose_system_health(
        process_signals={"uvicorn-api": _iso(now), "autowake-supervisor": _iso(now), "mt5-terminal": _iso(now)},
        artifact_latests={
            "fresh-one": _iso(now - timedelta(seconds=100)),
            "stale-one": _iso(now - timedelta(seconds=99999)),
            "missing-one": None,
        },
        default_freshness_threshold_seconds=1800.0,
        now=now,
    )
    by_name = {a.artifact_name: a for a in snap.evidence_freshness}
    assert by_name["fresh-one"].fresh is True
    assert by_name["stale-one"].fresh is False
    assert by_name["missing-one"].fresh is False
    assert by_name["missing-one"].latest_at_iso is None
    _assert_no_imperatives(snap)


# ---------------------------------------------------------------------------
# 8. Error count surfaced
# ---------------------------------------------------------------------------


def test_error_count_surfaced() -> None:
    now = _now()
    snap = compose_system_health(
        process_signals={"uvicorn-api": _iso(now), "autowake-supervisor": _iso(now), "mt5-terminal": _iso(now)},
        artifact_latests={},
        recent_error_count=17,
        now=now,
    )
    assert snap.recent_error_count == 17
    assert "Errors in last hour: 17" in snap.plain_english_summary
    _assert_no_imperatives(snap)


# ---------------------------------------------------------------------------
# 9. notification-dispatcher absent does not degrade overall
# ---------------------------------------------------------------------------


def test_notification_dispatcher_absent_does_not_degrade() -> None:
    now = _now()
    recent = _iso(now - timedelta(seconds=60))
    snap = compose_system_health(
        process_signals={
            "uvicorn-api": recent,
            "autowake-supervisor": recent,
            "mt5-terminal": recent,
            "notification-dispatcher": None,
        },
        artifact_latests={},
        disk_space=DiskSpace(
            repo_root="/tmp/repo",
            evidence_runs_bytes=0,
            free_disk_bytes=100 * (1024 ** 3),
            free_disk_pct=40.0,
        ),
        now=now,
    )
    assert snap.overall_status == "healthy"
    nd = [p for p in snap.processes if p.process_name == "notification-dispatcher"][0]
    assert nd.status_label == "expected_off"
    _assert_no_imperatives(snap)


# ---------------------------------------------------------------------------
# 10. Custom expected_processes override
# ---------------------------------------------------------------------------


def test_custom_expected_processes_override() -> None:
    now = _now()
    recent = _iso(now - timedelta(seconds=60))
    snap = compose_system_health(
        process_signals={
            "uvicorn-api": recent,
            "autowake-supervisor": recent,
            "mt5-terminal": None,
            "notification-dispatcher": recent,
        },
        artifact_latests={},
        expected_processes=("uvicorn-api", "autowake-supervisor", "notification-dispatcher"),
        disk_space=DiskSpace(
            repo_root="/tmp/repo",
            evidence_runs_bytes=0,
            free_disk_bytes=50 * (1024 ** 3),
            free_disk_pct=30.0,
        ),
        now=now,
    )
    by_name = {p.process_name: p for p in snap.processes}
    assert by_name["notification-dispatcher"].expected is True
    assert by_name["notification-dispatcher"].status_label == "alive"
    assert by_name["mt5-terminal"].expected is False
    assert by_name["mt5-terminal"].status_label == "expected_off"
    assert snap.overall_status == "healthy"
    _assert_no_imperatives(snap)


# ---------------------------------------------------------------------------
# 11. Per-artifact freshness threshold override
# ---------------------------------------------------------------------------


def test_per_artifact_freshness_threshold_override() -> None:
    now = _now()
    snap = compose_system_health(
        process_signals={"uvicorn-api": _iso(now), "autowake-supervisor": _iso(now), "mt5-terminal": _iso(now)},
        artifact_latests={
            "tight-clock": _iso(now - timedelta(seconds=200)),
            "loose-clock": _iso(now - timedelta(seconds=200)),
        },
        freshness_thresholds={
            "tight-clock": 60.0,
            "loose-clock": 3600.0,
        },
        now=now,
    )
    by_name = {a.artifact_name: a for a in snap.evidence_freshness}
    assert by_name["tight-clock"].fresh is False  # 200s > 60s
    assert by_name["loose-clock"].fresh is True   # 200s < 3600s
    _assert_no_imperatives(snap)


# ---------------------------------------------------------------------------
# 12. Forbidden imperative phrases across status branches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scenario",
    [
        "unknown",
        "healthy",
        "degraded_stale",
        "degraded_low_disk",
        "stale_missing",
    ],
)
def test_no_forbidden_imperatives_across_status_branches(scenario: str) -> None:
    now = _now()
    recent = _iso(now - timedelta(seconds=60))
    if scenario == "unknown":
        snap = compose_system_health(
            process_signals={"uvicorn-api": None, "autowake-supervisor": None, "mt5-terminal": None},
            artifact_latests={},
            disk_space=None,
            now=now,
        )
        assert snap.overall_status == "unknown"
    elif scenario == "healthy":
        snap = compose_system_health(
            process_signals={"uvicorn-api": recent, "autowake-supervisor": recent, "mt5-terminal": recent},
            artifact_latests={"art": recent},
            disk_space=DiskSpace("/r", 0, 100 * (1024 ** 3), 40.0),
            now=now,
        )
        assert snap.overall_status == "healthy"
    elif scenario == "degraded_stale":
        snap = compose_system_health(
            process_signals={
                "uvicorn-api": recent,
                "autowake-supervisor": _iso(now - timedelta(seconds=99999)),
                "mt5-terminal": recent,
            },
            artifact_latests={},
            disk_space=DiskSpace("/r", 0, 100 * (1024 ** 3), 40.0),
            now=now,
        )
        assert snap.overall_status == "degraded"
    elif scenario == "degraded_low_disk":
        snap = compose_system_health(
            process_signals={"uvicorn-api": recent, "autowake-supervisor": recent, "mt5-terminal": recent},
            artifact_latests={},
            disk_space=DiskSpace("/r", 0, 1 * (1024 ** 3), 1.0),
            now=now,
        )
        assert snap.overall_status == "degraded"
    elif scenario == "stale_missing":
        snap = compose_system_health(
            process_signals={"uvicorn-api": recent, "autowake-supervisor": None, "mt5-terminal": recent},
            artifact_latests={},
            disk_space=None,
            now=now,
        )
        assert snap.overall_status == "stale"

    _assert_no_imperatives(snap)
