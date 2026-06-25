"""Observational system-health composer for CAS Forex.

The operator runs multiple long-lived processes side by side: a uvicorn
API, the autowake supervisor, an MT5 terminal, and (optionally) the
notification dispatcher and strategy-dev queue evaluator. This module
provides a single primitive that summarises the whole stack's health at
a glance by READING ON-DISK EVIDENCE only — it never supervises,
restarts, or kills anything.

Framing (observational, never advisory):
    The summary describes WHAT IS — which processes have emitted recent
    signals, which evidence artifacts are fresh, how much disk is free,
    and how many error-style events the recent log window contains. It
    MUST NOT include imperative phrases ("you should restart", "kill
    the X", "force restart") — those are operator decisions, not the
    monitor's call. The forbidden-imperative regression guard in the
    test suite enforces this on every status branch.
"""

from __future__ import annotations

import glob
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessHealth:
    process_name: str
    expected: bool
    last_signal_at_iso: str | None
    seconds_since_signal: float | None
    likely_alive: bool
    status_label: str  # "alive" | "stale" | "missing" | "expected_off"


@dataclass(frozen=True)
class EvidenceFreshness:
    artifact_name: str
    latest_at_iso: str | None
    seconds_since_latest: float | None
    fresh: bool


@dataclass(frozen=True)
class DiskSpace:
    repo_root: str
    evidence_runs_bytes: int
    free_disk_bytes: int
    free_disk_pct: float


@dataclass(frozen=True)
class SystemHealthSnapshot:
    snapshot_at_iso: str
    processes: tuple[ProcessHealth, ...]
    evidence_freshness: tuple[EvidenceFreshness, ...]
    disk_space: DiskSpace | None
    recent_error_count: int
    plain_english_summary: str
    diagnostic_hints: tuple[str, ...]
    overall_status: str  # "healthy" | "degraded" | "stale" | "unknown"


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


DEFAULT_EXPECTED_PROCESSES: tuple[str, ...] = (
    "uvicorn-api",
    "autowake-supervisor",
    "mt5-terminal",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_iso(value: str | None) -> datetime | None:
    """Best-effort parser for ISO timestamps. Never raises."""
    if not value:
        return None
    try:
        # Allow trailing "Z"
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _seconds_between(now: datetime, then: datetime | None) -> float | None:
    if then is None:
        return None
    delta = now - then
    return float(delta.total_seconds())


# ---------------------------------------------------------------------------
# Pure composer
# ---------------------------------------------------------------------------


def compose_system_health(
    *,
    process_signals: Mapping[str, str | None],
    artifact_latests: Mapping[str, str | None],
    disk_space: DiskSpace | None = None,
    recent_error_count: int = 0,
    liveness_threshold_seconds: float = 600.0,
    freshness_thresholds: Mapping[str, float] | None = None,
    default_freshness_threshold_seconds: float = 1800.0,
    error_window_seconds: float = 3600.0,
    expected_processes: Sequence[str] = DEFAULT_EXPECTED_PROCESSES,
    now: datetime | None = None,
) -> SystemHealthSnapshot:
    """Compose an observational system-health snapshot.

    All inputs are pre-loaded values; this function performs no I/O. See
    ``load_system_health_inputs`` for the disk-reading counterpart.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    freshness_thresholds = dict(freshness_thresholds or {})
    expected_set = set(expected_processes)

    # ---- Processes
    processes: list[ProcessHealth] = []
    for name, iso in process_signals.items():
        expected = name in expected_set
        then = _parse_iso(iso)
        secs = _seconds_between(now, then)
        if iso is None or then is None:
            status_label = "missing" if expected else "expected_off"
            likely_alive = False
            secs = None
        else:
            if secs is not None and secs <= liveness_threshold_seconds:
                status_label = "alive"
                likely_alive = True
            else:
                status_label = "stale"
                likely_alive = False
        processes.append(
            ProcessHealth(
                process_name=name,
                expected=expected,
                last_signal_at_iso=iso,
                seconds_since_signal=secs,
                likely_alive=likely_alive,
                status_label=status_label,
            )
        )

    # If an expected process is not present in process_signals at all,
    # surface it as "missing" so the operator sees the gap.
    for name in expected_processes:
        if name not in process_signals:
            processes.append(
                ProcessHealth(
                    process_name=name,
                    expected=True,
                    last_signal_at_iso=None,
                    seconds_since_signal=None,
                    likely_alive=False,
                    status_label="missing",
                )
            )

    # ---- Evidence freshness
    artifacts: list[EvidenceFreshness] = []
    for name, iso in artifact_latests.items():
        then = _parse_iso(iso)
        secs = _seconds_between(now, then)
        threshold = freshness_thresholds.get(name, default_freshness_threshold_seconds)
        if iso is None or then is None or secs is None:
            fresh = False
            secs = None
        else:
            fresh = secs <= threshold
        artifacts.append(
            EvidenceFreshness(
                artifact_name=name,
                latest_at_iso=iso,
                seconds_since_latest=secs,
                fresh=fresh,
            )
        )

    # ---- Overall status
    expected_processes_view = [p for p in processes if p.expected]
    alive_count = sum(1 for p in expected_processes_view if p.status_label == "alive")
    stale_count = sum(1 for p in expected_processes_view if p.status_label == "stale")
    missing_count = sum(1 for p in expected_processes_view if p.status_label == "missing")
    expected_count = len(expected_processes_view)

    fresh_count = sum(1 for a in artifacts if a.fresh)
    total_artifacts = len(artifacts)

    disk_low = bool(disk_space is not None and disk_space.free_disk_pct < 5.0)

    all_signals_none = all(v is None for v in process_signals.values()) if process_signals else True
    no_artifacts_present = total_artifacts == 0 or all(a.latest_at_iso is None for a in artifacts)

    if all_signals_none and no_artifacts_present and disk_space is None:
        overall_status = "unknown"
    elif missing_count > 0:
        overall_status = "stale"
    elif stale_count > 0 or disk_low:
        overall_status = "degraded"
    elif (
        expected_count > 0
        and alive_count == expected_count
        and (total_artifacts == 0 or fresh_count == total_artifacts)
        and (disk_space is None or disk_space.free_disk_pct >= 5.0)
    ):
        overall_status = "healthy"
    else:
        # No expected processes alive yet, but we have *some* signal.
        overall_status = "unknown" if expected_count == 0 and not artifacts else "degraded"

    # ---- Diagnostic hints (factual, never imperative)
    hints: list[str] = []
    for p in processes:
        if p.expected and p.status_label == "missing":
            hints.append(f"expected process '{p.process_name}' has no recent signal on disk")
        elif p.expected and p.status_label == "stale":
            secs = p.seconds_since_signal
            secs_text = f"{int(secs)}s" if secs is not None else "unknown duration"
            hints.append(
                f"expected process '{p.process_name}' last signalled {secs_text} ago "
                f"(threshold {int(liveness_threshold_seconds)}s)"
            )
    for a in artifacts:
        if not a.fresh and a.latest_at_iso is not None:
            secs = a.seconds_since_latest
            secs_text = f"{int(secs)}s" if secs is not None else "unknown duration"
            hints.append(f"artifact '{a.artifact_name}' last fresh {secs_text} ago")
        elif a.latest_at_iso is None:
            hints.append(f"artifact '{a.artifact_name}' has no on-disk record")
    if disk_space is not None and disk_low:
        hints.append(
            f"disk free is {disk_space.free_disk_pct:.1f}% "
            f"({disk_space.free_disk_bytes // (1024 * 1024)} MiB) — below 5% threshold"
        )

    # ---- Plain-English summary (observational only)
    if disk_space is not None:
        disk_gb = disk_space.free_disk_bytes / (1024 ** 3)
        disk_line = f"Disk free: {disk_gb:.1f} GB ({disk_space.free_disk_pct:.1f}%)."
    else:
        disk_line = "Disk free: not measured."

    summary_lines = [
        f"System health: {overall_status}.",
        (
            f"Processes: {alive_count} alive, {stale_count} stale, "
            f"{missing_count} missing of {expected_count} expected."
        ),
        f"Evidence: {fresh_count}/{total_artifacts} artifacts fresh.",
        disk_line,
        f"Errors in last hour: {int(recent_error_count)}.",
    ]
    plain_english_summary = " ".join(summary_lines)

    return SystemHealthSnapshot(
        snapshot_at_iso=now.isoformat(),
        processes=tuple(processes),
        evidence_freshness=tuple(artifacts),
        disk_space=disk_space,
        recent_error_count=int(recent_error_count),
        plain_english_summary=plain_english_summary,
        diagnostic_hints=tuple(hints),
        overall_status=overall_status,
    )


# ---------------------------------------------------------------------------
# Disk loader (impure)
# ---------------------------------------------------------------------------


def _most_recent_mtime_iso(pattern: str) -> str | None:
    """Return the most recent mtime among glob matches as ISO, or None."""
    try:
        matches = glob.glob(pattern)
    except OSError:
        return None
    best: float | None = None
    for path in matches:
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if best is None or mtime > best:
            best = mtime
    if best is None:
        return None
    try:
        return datetime.fromtimestamp(best, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _directory_bytes(path: Path) -> int:
    total = 0
    try:
        for dirpath, _dirnames, filenames in os.walk(path):
            for fn in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, fn))
                except OSError:
                    continue
    except OSError:
        return total
    return total


def load_system_health_inputs(repo_root: Path | str) -> dict[str, Any]:
    """Read process signals + artifact latests + disk space from the repo.

    Process-signal globs:
      - ``uvicorn-api``: no on-disk signal; reported as None (operator runs
        uvicorn separately under their own supervisor — we cannot infer
        the uvicorn liveness from the evidence tree alone).
      - ``autowake-supervisor``: most recent
        ``evidence_runs/session_autowake_runner/session-autowake-*-report.json``
        mtime.
      - ``notification-dispatcher``: most recent
        ``evidence_runs/notification_dispatcher/*-report.json`` mtime if
        any, else None.
      - ``mt5-terminal``: most recent
        ``evidence_runs/mt5_terminal_api_verifier/mt5-terminal-api-verifier-*-report.json``
        mtime.

    Never raises; missing paths surface as None values.
    """
    root = Path(repo_root)
    evidence_root = root / "evidence_runs"

    process_signals: dict[str, str | None] = {
        "uvicorn-api": None,
        "autowake-supervisor": _most_recent_mtime_iso(
            str(evidence_root / "session_autowake_runner" / "session-autowake-*-report.json")
        ),
        "notification-dispatcher": _most_recent_mtime_iso(
            str(evidence_root / "notification_dispatcher" / "*-report.json")
        ),
        "mt5-terminal": _most_recent_mtime_iso(
            str(evidence_root / "mt5_terminal_api_verifier" / "mt5-terminal-api-verifier-*-report.json")
        ),
    }

    artifact_latests: dict[str, str | None] = {
        "agent-workflow-cycle": _most_recent_mtime_iso(
            str(evidence_root / "agent_workflow" / "*.json")
        ),
        "session-autowake": process_signals["autowake-supervisor"],
        "live-telemetry": _most_recent_mtime_iso(
            str(evidence_root / "live_telemetry" / "*.json")
        ),
        "mt5-probe": process_signals["mt5-terminal"],
    }

    disk_space: DiskSpace | None = None
    try:
        usage = shutil.disk_usage(str(root))
        ev_bytes = _directory_bytes(evidence_root) if evidence_root.exists() else 0
        free_pct = (usage.free / usage.total) * 100.0 if usage.total > 0 else 0.0
        disk_space = DiskSpace(
            repo_root=str(root),
            evidence_runs_bytes=int(ev_bytes),
            free_disk_bytes=int(usage.free),
            free_disk_pct=float(free_pct),
        )
    except OSError:
        disk_space = None

    return {
        "process_signals": process_signals,
        "artifact_latests": artifact_latests,
        "disk_space": disk_space,
        "recent_error_count": 0,
    }
