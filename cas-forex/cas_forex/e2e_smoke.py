"""Active end-to-end endpoint smoke check for CAS Forex.

The operator has dozens of API endpoints. Static health composers
(:mod:`cas_forex.stack_health_check`) report on-disk evidence freshness
and process presence, but they do NOT actually hit the HTTP surface.
This module CALLS each endpoint, validates response shape, and reports
pass/fail per endpoint.

Framing — observational only:
    The smoke surfaces failures (HTTP errors, missing schema keys,
    connection refusals). It does NOT advise trades, suggest entries,
    or recommend closing positions. The plain-English summary describes
    surface health only. A regression test enforces this.

The default transport uses :mod:`urllib.request` — no new dependencies.
For tests, a fake transport callable can be injected:

    def fake_transport(method, url, *, json=None, timeout=None):
        return FakeResponse(status=200, body={"status": "ok"})

Schema-check leniency:
    Each catalog entry declares the REQUIRED top-level keys. Missing
    optional keys are tolerated. A missing required key yields
    ``schema_check="MISSING_KEY:<name>"`` and ``success=False``.
"""

from __future__ import annotations

import json as _json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence


__all__ = [
    "EndpointCheckResult",
    "E2ESmokeReport",
    "BUILT_IN_ENDPOINTS",
    "run_endpoint_smoke",
    "default_urllib_transport",
]


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EndpointCheckResult:
    method: str
    path: str
    name: str
    category: str
    status_code: Optional[int]
    success: bool
    elapsed_ms: float
    schema_check: str
    error_message: Optional[str]


@dataclass(frozen=True)
class E2ESmokeReport:
    generated_at_iso: str
    api_base: str
    total_checks: int
    passed: int
    failed: int
    skipped: int
    elapsed_ms: float
    plain_english_summary: str
    failures: tuple[EndpointCheckResult, ...]
    results: tuple[EndpointCheckResult, ...]


# ---------------------------------------------------------------------------
# Built-in endpoint catalog
# ---------------------------------------------------------------------------
#
# Each entry:
#   method:           HTTP verb ("GET" / "POST" / "DELETE")
#   path:             Path appended to api_base (may contain ?query=...)
#   name:             Human-readable name
#   category:         Grouping for summary
#   required_keys:    Tuple of required top-level response keys
#                     (empty tuple ⇒ only 2xx required)

BUILT_IN_ENDPOINTS: tuple[Mapping[str, Any], ...] = (
    {
        "method": "GET",
        "path": "/api/forex/health",
        "name": "Health probe",
        "category": "health",
        "required_keys": ("status", "version"),
    },
    {
        "method": "GET",
        "path": "/api/forex/dashboard",
        "name": "Dashboard composite",
        "category": "dashboard",
        "required_keys": (),
    },
    {
        "method": "GET",
        "path": "/api/forex/readiness/live",
        "name": "Live readiness",
        "category": "readiness",
        "required_keys": ("overall_status", "checks_passed", "checks_total"),
    },
    {
        "method": "GET",
        "path": "/api/forex/operator-briefing",
        "name": "Operator briefing",
        "category": "observability",
        "required_keys": ("loop_health_status", "plain_english_briefing"),
    },
    {
        "method": "GET",
        "path": "/api/forex/autonomous-loop/health",
        "name": "Autonomous-loop health",
        "category": "observability",
        "required_keys": ("overall_status", "plain_english_summary"),
    },
    {
        "method": "GET",
        "path": "/api/forex/agent-decision/latest",
        "name": "Latest agent decision",
        "category": "agent-decision",
        "required_keys": ("overall_status", "plain_english_summary", "chain"),
    },
    {
        "method": "GET",
        "path": "/api/forex/agent-decision/history?limit=5",
        "name": "Agent-decision history",
        "category": "agent-decision",
        "required_keys": ("count", "decisions"),
    },
    {
        "method": "GET",
        "path": "/api/forex/live-telemetry",
        "name": "Live telemetry snapshot",
        "category": "telemetry",
        "required_keys": ("open_positions", "totals", "data_freshness"),
    },
    {
        "method": "GET",
        "path": "/api/forex/timeframes",
        "name": "Available timeframes",
        "category": "configuration",
        "required_keys": ("symbols",),
    },
    {
        "method": "GET",
        "path": "/api/forex/timeframes/canonical",
        "name": "Canonical timeframes",
        "category": "configuration",
        "required_keys": ("canonical_timeframes",),
    },
    {
        "method": "GET",
        "path": "/api/forex/risk-monitoring/portfolio",
        "name": "Portfolio risk monitoring",
        "category": "risk",
        "required_keys": ("open_position_count", "plain_english_summary"),
    },
    {
        "method": "GET",
        "path": "/api/forex/system-health/snapshot",
        "name": "System-health snapshot",
        "category": "health",
        "required_keys": ("overall_status", "processes", "evidence_freshness"),
    },
    {
        "method": "GET",
        "path": "/api/forex/stack-health/check",
        "name": "Stack-health composite",
        "category": "health",
        "required_keys": ("overall_status", "checks", "next_actions"),
    },
    {
        "method": "GET",
        "path": "/api/forex/strategy-comparison/ranked?limit=5",
        "name": "Strategy comparison ranked",
        "category": "strategy",
        "required_keys": ("record_count", "records"),
    },
    {
        "method": "GET",
        "path": "/api/forex/daily-report/today",
        "name": "Daily report (today)",
        "category": "reporting",
        "required_keys": ("report_date", "overall_headline", "sections"),
    },
    {
        "method": "GET",
        "path": "/api/forex/notifications/subscriptions",
        "name": "Notification subscriptions",
        "category": "subscriptions",
        "required_keys": ("subscriptions",),
    },
    {
        "method": "GET",
        "path": "/api/forex/webhook-notifications/subscriptions",
        "name": "Webhook subscriptions",
        "category": "subscriptions",
        "required_keys": ("subscriptions",),
    },
)


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class _UrllibResponse:
    """Tiny response-like wrapper produced by the default transport."""

    __slots__ = ("status_code", "_body_bytes")

    def __init__(self, status_code: int, body_bytes: bytes) -> None:
        self.status_code = status_code
        self._body_bytes = body_bytes

    def json(self) -> Any:
        if not self._body_bytes:
            return None
        return _json.loads(self._body_bytes.decode("utf-8"))


def default_urllib_transport(
    method: str,
    url: str,
    *,
    json: Optional[Mapping[str, Any]] = None,
    timeout: Optional[float] = None,
) -> _UrllibResponse:
    """Default transport using stdlib urllib (no external deps)."""

    data: Optional[bytes] = None
    headers = {"Accept": "application/json"}
    if json is not None:
        data = _json.dumps(json).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec: B310
            body_bytes = resp.read()
            return _UrllibResponse(resp.getcode(), body_bytes)
    except urllib.error.HTTPError as exc:
        body_bytes = b""
        try:
            body_bytes = exc.read() or b""
        except Exception:  # pragma: no cover - defensive
            body_bytes = b""
        return _UrllibResponse(exc.code, body_bytes)


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------


def _check_one_endpoint(
    spec: Mapping[str, Any],
    *,
    api_base: str,
    transport: Callable[..., Any],
    timeout_seconds: float,
) -> EndpointCheckResult:
    method = str(spec.get("method", "GET")).upper()
    path = str(spec["path"])
    name = str(spec.get("name", path))
    category = str(spec.get("category", "uncategorized"))
    required_keys: tuple[str, ...] = tuple(spec.get("required_keys") or ())

    url = api_base.rstrip("/") + path

    start = time.perf_counter()
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    schema_check = "SKIP"
    success = False

    try:
        resp = transport(method, url, json=None, timeout=timeout_seconds)
        status_code = getattr(resp, "status_code", None)
        if status_code is None or not (200 <= status_code < 300):
            error_message = f"non-2xx status: {status_code}"
            schema_check = "SKIP"
            success = False
        else:
            # Parse body if any required keys
            if required_keys:
                try:
                    body = resp.json()
                except Exception as exc:  # noqa: BLE001
                    error_message = f"response not JSON: {exc}"
                    schema_check = "SKIP"
                    success = False
                else:
                    if not isinstance(body, Mapping):
                        error_message = (
                            f"response not a JSON object: {type(body).__name__}"
                        )
                        schema_check = "SKIP"
                        success = False
                    else:
                        missing = next(
                            (k for k in required_keys if k not in body), None
                        )
                        if missing is not None:
                            schema_check = f"MISSING_KEY:{missing}"
                            success = False
                            error_message = (
                                f"required key '{missing}' missing in response"
                            )
                        else:
                            schema_check = "OK"
                            success = True
            else:
                schema_check = "OK"
                success = True
    except Exception as exc:  # noqa: BLE001
        # Connection error / timeout / DNS / etc.
        error_message = f"{type(exc).__name__}: {exc}"
        status_code = None
        schema_check = "SKIP"
        success = False

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return EndpointCheckResult(
        method=method,
        path=path,
        name=name,
        category=category,
        status_code=status_code,
        success=success,
        elapsed_ms=round(elapsed_ms, 3),
        schema_check=schema_check,
        error_message=error_message,
    )


# ---------------------------------------------------------------------------
# Forbidden trade-advisory phrases (regression guard)
# ---------------------------------------------------------------------------

_FORBIDDEN_PHRASES: tuple[str, ...] = (
    "buy now",
    "should you trade",
    "good entry",
    "consider closing",
    "should you sell",
)


def _build_plain_english_summary(
    *,
    total: int,
    passed: int,
    failed: int,
    skipped: int,
    failures: Sequence[EndpointCheckResult],
) -> str:
    if total == 0:
        return (
            "Endpoint smoke ran with 0 endpoints in the catalog. "
            "Nothing was called; this is an observational status only."
        )
    lines: list[str] = []
    if failed == 0:
        lines.append(
            f"Endpoint smoke checked {total} surfaces and all {passed} responded "
            "with the expected shape."
        )
    else:
        lines.append(
            f"Endpoint smoke checked {total} surfaces: {passed} responded with "
            f"the expected shape, {failed} did not."
        )
        # List up to 5 failures by name in summary (observational only).
        head = ", ".join(f.name for f in failures[:5])
        if head:
            lines.append(f"Failing surfaces: {head}.")
    if skipped:
        lines.append(f"{skipped} surface(s) were skipped.")
    lines.append(
        "This report describes surface health only; it does not advise trades."
    )
    summary = " ".join(lines)
    # Belt-and-suspenders: scrub forbidden phrases if any slipped in.
    lowered = summary.lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in lowered:
            # Replace with neutral wording rather than fail silently.
            summary = summary.replace(phrase, "[redacted]")
            lowered = summary.lower()
    return summary


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_endpoint_smoke(
    *,
    api_base: str = "http://127.0.0.1:8765",
    transport: Optional[Callable[..., Any]] = None,
    timeout_seconds: float = 10.0,
    skip_post: bool = True,
    extra_endpoints: Optional[Sequence[Mapping[str, Any]]] = None,
    now: Optional[datetime] = None,
    endpoints: Optional[Sequence[Mapping[str, Any]]] = None,
) -> E2ESmokeReport:
    """Run the full endpoint smoke and return an :class:`E2ESmokeReport`.

    Parameters
    ----------
    api_base:
        Base URL for all relative paths in the catalog.
    transport:
        Optional callable with signature
        ``transport(method, url, *, json=None, timeout=None) -> response-like``.
        The response must expose ``status_code`` and ``json()``. If ``None``,
        :func:`default_urllib_transport` is used.
    timeout_seconds:
        Per-request timeout passed to the transport.
    skip_post:
        When ``True`` (default), POST endpoints in the catalog are not called.
        Smoke is observational by default; mutating endpoints opt-in.
    extra_endpoints:
        Additional endpoint specs appended to the catalog (after filtering).
    now:
        Override for ``generated_at_iso``.
    endpoints:
        Override the entire catalog. When provided, ``BUILT_IN_ENDPOINTS`` is
        NOT used; ``extra_endpoints`` is still appended.
    """

    if transport is None:
        transport = default_urllib_transport

    catalog: list[Mapping[str, Any]] = list(
        BUILT_IN_ENDPOINTS if endpoints is None else endpoints
    )
    if extra_endpoints:
        catalog.extend(extra_endpoints)

    if skip_post:
        catalog = [
            spec for spec in catalog
            if str(spec.get("method", "GET")).upper() != "POST"
        ]

    run_start = time.perf_counter()
    results: list[EndpointCheckResult] = []
    for spec in catalog:
        results.append(
            _check_one_endpoint(
                spec,
                api_base=api_base,
                transport=transport,
                timeout_seconds=timeout_seconds,
            )
        )
    elapsed_ms = (time.perf_counter() - run_start) * 1000.0

    passed = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    skipped = 0  # Reserved for future: per-spec skip flag.
    failures = tuple(r for r in results if not r.success)

    summary = _build_plain_english_summary(
        total=len(results),
        passed=passed,
        failed=failed,
        skipped=skipped,
        failures=failures,
    )

    now_dt = now if now is not None else datetime.now(timezone.utc)
    return E2ESmokeReport(
        generated_at_iso=now_dt.isoformat(),
        api_base=api_base,
        total_checks=len(results),
        passed=passed,
        failed=failed,
        skipped=skipped,
        elapsed_ms=round(elapsed_ms, 3),
        plain_english_summary=summary,
        failures=failures,
        results=tuple(results),
    )


def report_to_dict(report: E2ESmokeReport) -> dict[str, Any]:
    """Serialize an :class:`E2ESmokeReport` to a plain dict (JSON-friendly)."""

    return {
        "generated_at_iso": report.generated_at_iso,
        "api_base": report.api_base,
        "total_checks": report.total_checks,
        "passed": report.passed,
        "failed": report.failed,
        "skipped": report.skipped,
        "elapsed_ms": report.elapsed_ms,
        "plain_english_summary": report.plain_english_summary,
        "failures": [asdict(r) for r in report.failures],
        "results": [asdict(r) for r in report.results],
    }
