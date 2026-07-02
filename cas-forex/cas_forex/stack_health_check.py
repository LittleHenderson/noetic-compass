"""One-screen stack-health composer for CAS Forex.

The operator runs many narrow status endpoints today (operator briefing,
system health, autonomous-loop health, MT5 terminal verifier, readiness
gates, live telemetry). Asking "is everything OK?" forces the operator
to check 5+ surfaces. This module composes their results into a single
:class:`StackHealthReport` covering six structural checks:

* ``uvicorn-api``
* ``autowake-supervisor``
* ``mt5-terminal``
* ``autonomous-loop``
* ``readiness-gates``
* ``live-telemetry``

Framing (observational + factual remediation only):
    The report describes WHAT IS — which inputs were received, which
    expected processes have evidence, whether MT5 is verified, whether
    readiness gates pass. ``next_actions`` only contains factual
    remediation strings ("start uvicorn ...", "launch autowake ...") —
    they describe the missing surface, not trade advisory. The forbidden-
    phrase regression guard in the tests enforces this on every status
    branch.

The composer is pure (no I/O); :func:`load_stack_health_inputs` is the
separate disk + HTTP shim for production callers. Missing inputs become
``UNKNOWN`` checks; the report never fabricates a number or status.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional


__all__ = [
    "CheckResult",
    "StackHealthReport",
    "compose_stack_health_report",
    "load_stack_health_inputs",
]


# Status vocabulary
STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_MISSING = "MISSING"
STATUS_UNKNOWN = "UNKNOWN"


# Ordered list of structural check names — composition order matters.
CHECK_NAMES: tuple[str, ...] = (
    "uvicorn-api",
    "autowake-supervisor",
    "mt5-terminal",
    "autonomous-loop",
    "readiness-gates",
    "live-telemetry",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str  # "OK" | "DEGRADED" | "MISSING" | "UNKNOWN"
    headline: str
    detail: str
    remediation: Optional[str]


@dataclass(frozen=True)
class StackHealthReport:
    generated_at_iso: str
    checks: tuple[CheckResult, ...]
    overall_status: str  # "OK" | "DEGRADED" | "MISSING" | "UNKNOWN"
    ok_count: int
    degraded_count: int
    missing_count: int
    unknown_count: int
    plain_english_summary: str
    next_actions: tuple[str, ...]


# ---------------------------------------------------------------------------
# Per-check helpers
# ---------------------------------------------------------------------------


def _check_uvicorn_api(operator_briefing: Optional[Mapping[str, Any]]) -> CheckResult:
    if operator_briefing is not None:
        return CheckResult(
            name="uvicorn-api",
            status=STATUS_OK,
            headline="API reachable (operator briefing composed).",
            detail=(
                "An operator-briefing payload was returned, which means the "
                "uvicorn API process responded to a status request."
            ),
            remediation=None,
        )
    return CheckResult(
        name="uvicorn-api",
        status=STATUS_MISSING,
        headline="API not reachable (no operator briefing returned).",
        detail=(
            "No operator briefing was returned. The uvicorn API process is "
            "likely not running on the configured port."
        ),
        remediation=(
            "Start uvicorn: py -3.12 -m uvicorn api.server:app --host "
            "127.0.0.1 --port 8765"
        ),
    )


def _find_process_status(
    system_health: Optional[Mapping[str, Any]], process_name: str
) -> Optional[str]:
    """Return the system_health status_label for ``process_name`` or None."""
    if not isinstance(system_health, Mapping):
        return None
    procs = system_health.get("processes")
    if not isinstance(procs, (list, tuple)):
        return None
    for p in procs:
        if not isinstance(p, Mapping):
            continue
        if p.get("process_name") == process_name:
            label = p.get("status_label")
            if isinstance(label, str):
                return label
    return None


def _check_autowake_supervisor(
    system_health: Optional[Mapping[str, Any]],
) -> CheckResult:
    label = _find_process_status(system_health, "autowake-supervisor")
    if label is None:
        return CheckResult(
            name="autowake-supervisor",
            status=STATUS_UNKNOWN,
            headline="Autowake supervisor status unknown.",
            detail=(
                "No system-health signal was supplied for the autowake "
                "supervisor, so its liveness cannot be inferred."
            ),
            remediation=None,
        )
    if label == "alive":
        return CheckResult(
            name="autowake-supervisor",
            status=STATUS_OK,
            headline="Autowake supervisor is alive.",
            detail=(
                "The session-autowake report was written recently, so the "
                "supervisor process appears to be ticking."
            ),
            remediation=None,
        )
    if label == "stale":
        return CheckResult(
            name="autowake-supervisor",
            status=STATUS_DEGRADED,
            headline="Autowake supervisor signal is stale.",
            detail=(
                "A session-autowake report exists but it is older than the "
                "liveness threshold; the supervisor may have stopped ticking."
            ),
            remediation=(
                "Launch autowake supervisor: py -3.12 "
                "scripts/run_autowake_supervisor.py "
                "--tick-interval-seconds 300 --execute-cycle --summary-only"
            ),
        )
    # Treat "missing" or any other label as MISSING.
    return CheckResult(
        name="autowake-supervisor",
        status=STATUS_MISSING,
        headline="Autowake supervisor has no recent signal.",
        detail=(
            "No recent session-autowake report was found on disk. The "
            "autowake supervisor is not running, or has never been started."
        ),
        remediation=(
            "Launch autowake supervisor: py -3.12 "
            "scripts/run_autowake_supervisor.py "
            "--tick-interval-seconds 300 --execute-cycle --summary-only"
        ),
    )


def _extract_mt5_flags(
    mt5_probe: Optional[Mapping[str, Any]],
) -> tuple[bool, bool, bool]:
    """Return (probe_present, terminal_connected, broker_api_verified)."""
    if not isinstance(mt5_probe, Mapping):
        return False, False, False
    summary = mt5_probe.get("summary") if isinstance(mt5_probe.get("summary"), Mapping) else None
    terminal_connected = False
    broker_api_verified = False
    if isinstance(summary, Mapping):
        terminal_connected = bool(summary.get("terminal_connected"))
        broker_api_verified = bool(
            summary.get("broker_api_verified")
            or summary.get("broker_source_verified")
        )
    if not terminal_connected:
        terminal_connected = bool(
            mt5_probe.get("terminal_connected") or mt5_probe.get("connected")
        )
    if not broker_api_verified:
        broker_api_verified = bool(
            mt5_probe.get("broker_api_verified")
            or mt5_probe.get("broker_source_verified")
        )
    probe_status = str(
        mt5_probe.get("status")
        or mt5_probe.get("probe_status")
        or mt5_probe.get("receipt_validation_status")
        or ""
    ).upper()
    if probe_status == "BROKER_API_VERIFIED":
        terminal_connected = True
        broker_api_verified = True
    return True, terminal_connected, broker_api_verified


def _check_mt5_terminal(mt5_probe: Optional[Mapping[str, Any]]) -> CheckResult:
    probe_present, terminal_connected, broker_api_verified = _extract_mt5_flags(mt5_probe)
    if not probe_present:
        return CheckResult(
            name="mt5-terminal",
            status=STATUS_UNKNOWN,
            headline="MT5 terminal status unknown (no probe).",
            detail=(
                "No MT5 terminal-API verifier probe was supplied, so the "
                "terminal-connection state cannot be inferred."
            ),
            remediation=None,
        )
    if broker_api_verified:
        return CheckResult(
            name="mt5-terminal",
            status=STATUS_OK,
            headline="MT5 terminal connected and broker API verified.",
            detail=(
                "The mt5_terminal_api_verifier probe reports both "
                "terminal_connected=True and broker_api_verified=True."
            ),
            remediation=None,
        )
    if terminal_connected:
        return CheckResult(
            name="mt5-terminal",
            status=STATUS_DEGRADED,
            headline="MT5 terminal connected, broker API not verified.",
            detail=(
                "Terminal is reachable but the broker-side API verification "
                "did not succeed; symbol or account context may be wrong."
            ),
            remediation=(
                "Restart MT5 terminal with Hugosway-Demo logged in and "
                "AutoTrading enabled"
            ),
        )
    return CheckResult(
        name="mt5-terminal",
        status=STATUS_MISSING,
        headline="MT5 terminal not connected.",
        detail=(
            "The mt5_terminal_api_verifier probe reports terminal_connected=False; "
            "the MT5 terminal process is not running or not logged in."
        ),
        remediation=(
            "Restart MT5 terminal with Hugosway-Demo logged in and "
            "AutoTrading enabled"
        ),
    )


def _check_autonomous_loop(loop_health: Optional[Mapping[str, Any]]) -> CheckResult:
    if not isinstance(loop_health, Mapping):
        return CheckResult(
            name="autonomous-loop",
            status=STATUS_UNKNOWN,
            headline="Autonomous loop status unknown.",
            detail="No loop-health summary was supplied.",
            remediation=None,
        )
    status = str(loop_health.get("overall_status") or "").lower()
    cycles_today = loop_health.get("cycles_today")
    secs = loop_health.get("seconds_since_last_cycle")
    if status == "running":
        return CheckResult(
            name="autonomous-loop",
            status=STATUS_OK,
            headline="Autonomous loop is running.",
            detail=(
                f"Loop reports overall_status='running' with "
                f"{cycles_today if cycles_today is not None else 0} cycle(s) "
                "recorded today."
            ),
            remediation=None,
        )
    if status == "stalled":
        secs_text = (
            f"{int(secs)}s" if isinstance(secs, (int, float)) else "unknown duration"
        )
        return CheckResult(
            name="autonomous-loop",
            status=STATUS_DEGRADED,
            headline="Autonomous loop is stalled.",
            detail=(
                f"Loop reports overall_status='stalled'; last cycle was "
                f"{secs_text} ago."
            ),
            remediation=(
                "Launch autowake supervisor: py -3.12 "
                "scripts/run_autowake_supervisor.py "
                "--tick-interval-seconds 300 --execute-cycle --summary-only"
            ),
        )
    if status == "never_started":
        return CheckResult(
            name="autonomous-loop",
            status=STATUS_MISSING,
            headline="Autonomous loop has never started.",
            detail=(
                "No cycle reports have been written on disk; the autonomous "
                "loop has not produced any evidence yet."
            ),
            remediation=(
                "Launch autowake supervisor: py -3.12 "
                "scripts/run_autowake_supervisor.py "
                "--tick-interval-seconds 300 --execute-cycle --summary-only"
            ),
        )
    return CheckResult(
        name="autonomous-loop",
        status=STATUS_UNKNOWN,
        headline=f"Autonomous loop status is '{status or 'unknown'}'.",
        detail=(
            "Loop-health summary does not report a recognized overall_status; "
            "treat as unknown."
        ),
        remediation=None,
    )


def _check_readiness_gates(
    readiness: Optional[Mapping[str, Any]],
) -> CheckResult:
    if not isinstance(readiness, Mapping):
        return CheckResult(
            name="readiness-gates",
            status=STATUS_UNKNOWN,
            headline="Readiness gates status unknown.",
            detail="No live-readiness report was supplied.",
            remediation=None,
        )
    try:
        passed = int(readiness.get("checks_passed") or 0)
        total = int(readiness.get("checks_total") or 0)
    except (TypeError, ValueError):
        passed, total = 0, 0
    if total <= 0:
        return CheckResult(
            name="readiness-gates",
            status=STATUS_UNKNOWN,
            headline="Readiness report has no gate counts.",
            detail=(
                "A readiness payload was supplied but it carries no "
                "checks_total — gates cannot be evaluated."
            ),
            remediation=None,
        )
    caveat = (
        " Note: readiness gates being open is not required for the "
        "paper/demo lane; OK here means there are no surprises."
    )
    if passed == total:
        return CheckResult(
            name="readiness-gates",
            status=STATUS_OK,
            headline=f"Readiness gates {passed}/{total} passing.",
            detail=(
                f"All {total} live-readiness checks are PASSED." + caveat
            ),
            remediation=None,
        )
    return CheckResult(
        name="readiness-gates",
        status=STATUS_DEGRADED,
        headline=f"Readiness gates {passed}/{total} passing.",
        detail=(
            f"{total - passed} of {total} live-readiness checks are not "
            "passing." + caveat
        ),
        remediation=(
            f"Inspect failing readiness gates: GET /api/forex/readiness/live "
            f"({passed}/{total} passing)"
        ),
    )


def _check_live_telemetry(
    live_telemetry: Optional[Mapping[str, Any]],
) -> CheckResult:
    if not isinstance(live_telemetry, Mapping):
        return CheckResult(
            name="live-telemetry",
            status=STATUS_UNKNOWN,
            headline="Live telemetry status unknown.",
            detail=(
                "No live-telemetry payload was supplied, so the telemetry "
                "feed cannot be evaluated."
            ),
            remediation=None,
        )
    return CheckResult(
        name="live-telemetry",
        status=STATUS_OK,
        headline="Live telemetry feed responding.",
        detail=(
            "A live-telemetry payload was returned by the API; the feed is "
            "wired and producing a structured response."
        ),
        remediation=None,
    )


# ---------------------------------------------------------------------------
# Public composer
# ---------------------------------------------------------------------------


def _coerce_now(now: Optional[datetime]) -> datetime:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now


def _classify_overall(checks: tuple[CheckResult, ...]) -> str:
    if any(c.status == STATUS_MISSING for c in checks):
        return STATUS_MISSING
    if any(c.status == STATUS_DEGRADED for c in checks):
        return STATUS_DEGRADED
    if all(c.status == STATUS_UNKNOWN for c in checks):
        return STATUS_UNKNOWN
    if all(c.status == STATUS_OK for c in checks):
        return STATUS_OK
    # mix of OK and UNKNOWN, no MISSING/DEGRADED -> degraded view? No,
    # call that DEGRADED because something is partially unobservable.
    # Spec says: OK only when all OK; UNKNOWN only when ALL UNKNOWN.
    # MISSING when any MISSING. DEGRADED when any DEGRADED (no MISSING).
    # Fallthrough = DEGRADED.
    return STATUS_DEGRADED


def _build_plain_english(
    checks: tuple[CheckResult, ...],
    overall: str,
    ok_count: int,
    degraded_count: int,
    missing_count: int,
    unknown_count: int,
) -> str:
    total = len(checks)
    parts: list[str] = []
    parts.append(
        f"Stack: {ok_count}/{total} checks OK, "
        f"{degraded_count} DEGRADED, {missing_count} MISSING, "
        f"{unknown_count} UNKNOWN."
    )
    # Mention the first MISSING and first DEGRADED check explicitly with
    # a factual headline (never advisory).
    for c in checks:
        if c.status == STATUS_MISSING:
            parts.append(c.headline)
            break
    for c in checks:
        if c.status == STATUS_DEGRADED:
            parts.append(c.headline)
            break
    if overall == STATUS_OK:
        parts.append("All structural checks report OK.")
    elif overall == STATUS_UNKNOWN:
        parts.append("No inputs were supplied; status is unknown.")
    return " ".join(parts)


def _build_next_actions(checks: tuple[CheckResult, ...]) -> tuple[str, ...]:
    # MISSING first (in check order), then DEGRADED (in check order).
    actions: list[str] = []
    seen: set[str] = set()
    for c in checks:
        if c.status == STATUS_MISSING and c.remediation:
            if c.remediation not in seen:
                actions.append(c.remediation)
                seen.add(c.remediation)
    for c in checks:
        if c.status == STATUS_DEGRADED and c.remediation:
            if c.remediation not in seen:
                actions.append(c.remediation)
                seen.add(c.remediation)
    return tuple(actions)


def compose_stack_health_report(
    *,
    system_health: Optional[Mapping[str, Any]] = None,
    operator_briefing: Optional[Mapping[str, Any]] = None,
    loop_health: Optional[Mapping[str, Any]] = None,
    mt5_probe: Optional[Mapping[str, Any]] = None,
    readiness: Optional[Mapping[str, Any]] = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
) -> StackHealthReport:
    """Compose a one-screen stack-health report from already-parsed inputs.

    All inputs are dicts (or ``None``). The composer performs no I/O.
    Missing inputs surface as ``UNKNOWN`` checks; the report never
    fabricates a number or a status. See :func:`load_stack_health_inputs`
    for a disk + HTTP loader counterpart.
    """
    now_utc = _coerce_now(now)

    # Special case: when EVERY input is None we cannot determine
    # anything — including whether the uvicorn API is down vs. simply
    # not probed. Surface as UNKNOWN across the board, not MISSING.
    all_inputs_none = all(
        x is None
        for x in (
            system_health,
            operator_briefing,
            loop_health,
            mt5_probe,
            readiness,
            live_telemetry,
        )
    )
    if all_inputs_none:
        unknown_check = lambda name: CheckResult(  # noqa: E731
            name=name,
            status=STATUS_UNKNOWN,
            headline=f"{name} status unknown (no input supplied).",
            detail=(
                "No inputs were supplied to the stack-health composer; "
                "no on-disk or HTTP signal was available."
            ),
            remediation=None,
        )
        checks = tuple(unknown_check(n) for n in CHECK_NAMES)
    else:
        checks = (
            _check_uvicorn_api(operator_briefing),
            _check_autowake_supervisor(system_health),
            _check_mt5_terminal(mt5_probe),
            _check_autonomous_loop(loop_health),
            _check_readiness_gates(readiness),
            _check_live_telemetry(live_telemetry),
        )
    ok_count = sum(1 for c in checks if c.status == STATUS_OK)
    degraded_count = sum(1 for c in checks if c.status == STATUS_DEGRADED)
    missing_count = sum(1 for c in checks if c.status == STATUS_MISSING)
    unknown_count = sum(1 for c in checks if c.status == STATUS_UNKNOWN)
    overall = _classify_overall(checks)
    summary = _build_plain_english(
        checks, overall, ok_count, degraded_count, missing_count, unknown_count
    )
    next_actions = _build_next_actions(checks)
    return StackHealthReport(
        generated_at_iso=now_utc.isoformat(),
        checks=checks,
        overall_status=overall,
        ok_count=ok_count,
        degraded_count=degraded_count,
        missing_count=missing_count,
        unknown_count=unknown_count,
        plain_english_summary=summary,
        next_actions=next_actions,
    )


# ---------------------------------------------------------------------------
# Disk + HTTP loader (impure)
# ---------------------------------------------------------------------------


def _http_get_json(
    url: str, *, timeout_seconds: float = 2.0
) -> Optional[Mapping[str, Any]]:
    """GET ``url`` and parse JSON. Returns None on any failure."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout, OSError, ValueError):
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if isinstance(data, Mapping):
        return data
    return None


def load_stack_health_inputs(
    repo_root: Path | str,
    api_base: str = "http://127.0.0.1:8765",
) -> dict[str, Any]:
    """Compose the inputs needed for :func:`compose_stack_health_report`.

    The loader never raises. Each underlying lookup is wrapped so a
    missing or unreachable source becomes ``None`` for that key.

    Reads:
      * ``operator_briefing`` — first tries HTTP GET ``{api_base}/api/forex/operator-briefing``;
        falls back to :func:`load_operator_briefing_inputs` composed locally.
      * ``system_health`` — :func:`load_system_health_inputs` + composer.
      * ``loop_health`` — :func:`load_loop_health_inputs` + summariser.
      * ``mt5_probe`` — HTTP GET ``{api_base}/api/forex/mt/probe/latest``.
      * ``readiness`` — HTTP GET ``{api_base}/api/forex/readiness/live``.
      * ``live_telemetry`` — HTTP GET ``{api_base}/api/forex/live-telemetry``.
    """
    root = Path(repo_root)
    api_base = api_base.rstrip("/")

    operator_briefing: Optional[Mapping[str, Any]] = None
    try:
        operator_briefing = _http_get_json(f"{api_base}/api/forex/operator-briefing")
    except Exception:  # pragma: no cover - defensive
        operator_briefing = None
    if operator_briefing is None:
        try:
            from cas_forex.operator_briefing import (
                compose_operator_briefing,
                load_operator_briefing_inputs,
            )
            from dataclasses import asdict as _asdict

            inputs = load_operator_briefing_inputs(root)
            operator_briefing = _asdict(compose_operator_briefing(**inputs))
        except Exception:
            operator_briefing = None

    system_health: Optional[Mapping[str, Any]] = None
    try:
        from cas_forex.system_health_monitor import (
            compose_system_health,
            load_system_health_inputs,
        )
        from dataclasses import asdict as _asdict

        sh_inputs = load_system_health_inputs(root)
        system_health = _asdict(compose_system_health(**sh_inputs))
    except Exception:
        system_health = None

    loop_health: Optional[Mapping[str, Any]] = None
    try:
        from cas_forex.autonomous_loop_health import (
            load_loop_health_inputs,
            summarize_autonomous_loop_health,
        )
        from dataclasses import asdict as _asdict

        lh_inputs = load_loop_health_inputs(root)
        loop_health = _asdict(summarize_autonomous_loop_health(**lh_inputs))
    except Exception:
        loop_health = None

    mt5_probe = _http_get_json(f"{api_base}/api/forex/mt/probe/latest")
    readiness = _http_get_json(f"{api_base}/api/forex/readiness/live")
    live_telemetry = _http_get_json(f"{api_base}/api/forex/live-telemetry")

    return {
        "system_health": system_health,
        "operator_briefing": operator_briefing,
        "loop_health": loop_health,
        "mt5_probe": mt5_probe,
        "readiness": readiness,
        "live_telemetry": live_telemetry,
    }
