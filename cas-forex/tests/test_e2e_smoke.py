"""Tests for cas_forex.e2e_smoke — active endpoint smoke check."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import pytest

from cas_forex.e2e_smoke import (
    BUILT_IN_ENDPOINTS,
    E2ESmokeReport,
    EndpointCheckResult,
    run_endpoint_smoke,
)


# ---------------------------------------------------------------------------
# Fake transports
# ---------------------------------------------------------------------------


@dataclass
class _FakeResponse:
    status_code: int
    body: Any

    def json(self) -> Any:
        return self.body


def _valid_body_for(path: str) -> Mapping[str, Any]:
    """Return a JSON body that satisfies required keys for the catalog spec
    matching ``path``. Falls back to an empty dict if the spec has no
    required keys (or the path isn't in the catalog)."""
    for spec in BUILT_IN_ENDPOINTS:
        if spec["path"] == path:
            req = spec.get("required_keys") or ()
            return {k: _sample_for_key(k) for k in req}
    return {}


def _sample_for_key(key: str) -> Any:
    if key in {"checks_passed", "checks_total", "open_position_count",
              "count", "record_count"}:
        return 0
    if key in {"checks", "decisions", "records", "next_actions",
              "open_positions", "subscriptions", "sections", "chain"}:
        return []
    if key in {"totals", "data_freshness", "processes",
              "evidence_freshness", "symbols", "canonical_timeframes"}:
        return {}
    return "ok"


def _all_ok_transport(method: str, url: str, *, json=None, timeout=None):
    # Extract the path from the full URL (strip api_base)
    for prefix in ("http://", "https://"):
        if url.startswith(prefix):
            rest = url[len(prefix):]
            slash = rest.find("/")
            path = rest[slash:] if slash >= 0 else "/"
            break
    else:
        path = url
    return _FakeResponse(status_code=200, body=_valid_body_for(path))


def _all_500_transport(method: str, url: str, *, json=None, timeout=None):
    return _FakeResponse(status_code=500, body={"error": "boom"})


# ---------------------------------------------------------------------------
# Test 1 — empty catalog yields empty report
# ---------------------------------------------------------------------------


def test_run_endpoint_smoke_empty_catalog_yields_zero_results() -> None:
    report = run_endpoint_smoke(
        transport=_all_ok_transport,
        endpoints=[],
    )
    assert isinstance(report, E2ESmokeReport)
    assert report.total_checks == 0
    assert report.passed == 0
    assert report.failed == 0
    assert report.skipped == 0
    assert report.results == ()
    assert report.failures == ()


# ---------------------------------------------------------------------------
# Test 2 — all-OK transport: every endpoint passes
# ---------------------------------------------------------------------------


def test_run_endpoint_smoke_all_ok_transport_passes_all() -> None:
    report = run_endpoint_smoke(transport=_all_ok_transport)
    assert report.total_checks == len(BUILT_IN_ENDPOINTS)
    assert report.passed == report.total_checks
    assert report.failed == 0
    assert report.failures == ()
    for r in report.results:
        assert r.success is True, f"{r.path} failed: {r.error_message}"
        assert r.schema_check == "OK"
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Test 3 — single 500 in mixed transport: that one failed, others passed
# ---------------------------------------------------------------------------


def test_run_endpoint_smoke_one_500_others_pass() -> None:
    fail_path = "/api/forex/health"

    def mixed_transport(method, url, *, json=None, timeout=None):
        if url.endswith(fail_path):
            return _FakeResponse(status_code=500, body={"error": "boom"})
        return _all_ok_transport(method, url, json=json, timeout=timeout)

    report = run_endpoint_smoke(transport=mixed_transport)
    fails = [r for r in report.results if not r.success]
    assert len(fails) == 1
    assert fails[0].path == fail_path
    assert fails[0].status_code == 500
    assert fails[0].success is False
    assert report.passed == report.total_checks - 1
    assert report.failed == 1


# ---------------------------------------------------------------------------
# Test 4 — missing required key
# ---------------------------------------------------------------------------


def test_run_endpoint_smoke_missing_required_key_marks_failure() -> None:
    target = "/api/forex/health"  # requires status, version

    def transport(method, url, *, json=None, timeout=None):
        if url.endswith(target):
            # Missing 'version'.
            return _FakeResponse(status_code=200, body={"status": "ok"})
        return _all_ok_transport(method, url, json=json, timeout=timeout)

    report = run_endpoint_smoke(transport=transport)
    [hit] = [r for r in report.results if r.path == target]
    assert hit.success is False
    assert hit.schema_check == "MISSING_KEY:version"
    assert hit.status_code == 200
    assert "version" in (hit.error_message or "")


# ---------------------------------------------------------------------------
# Test 5 — connection error -> status_code=None, error_message populated
# ---------------------------------------------------------------------------


def test_run_endpoint_smoke_connection_error_documented() -> None:
    class _ConnErr(Exception):
        pass

    def transport(method, url, *, json=None, timeout=None):
        raise _ConnErr("connection refused")

    report = run_endpoint_smoke(transport=transport)
    assert report.failed == report.total_checks
    for r in report.results:
        assert r.status_code is None
        assert r.success is False
        assert r.error_message is not None
        assert "connection refused" in r.error_message


# ---------------------------------------------------------------------------
# Test 6 — extra endpoints injected
# ---------------------------------------------------------------------------


def test_run_endpoint_smoke_extra_endpoints_included() -> None:
    extra = [
        {
            "method": "GET",
            "path": "/api/forex/custom/extra",
            "name": "Custom extra",
            "category": "custom",
            "required_keys": ("custom_status",),
        }
    ]

    def transport(method, url, *, json=None, timeout=None):
        if url.endswith("/api/forex/custom/extra"):
            return _FakeResponse(
                status_code=200, body={"custom_status": "green"}
            )
        return _all_ok_transport(method, url, json=json, timeout=timeout)

    report = run_endpoint_smoke(transport=transport, extra_endpoints=extra)
    assert any(r.path == "/api/forex/custom/extra" for r in report.results)
    [hit] = [r for r in report.results if r.path == "/api/forex/custom/extra"]
    assert hit.success is True
    assert hit.category == "custom"
    assert report.total_checks == len(BUILT_IN_ENDPOINTS) + 1


# ---------------------------------------------------------------------------
# Test 7 — skip_post default filters POST endpoints
# ---------------------------------------------------------------------------


def test_run_endpoint_smoke_skip_post_default_filters_post_endpoints() -> None:
    post_extra = [
        {
            "method": "POST",
            "path": "/api/forex/custom/mutate",
            "name": "Mutator",
            "category": "actions",
            "required_keys": (),
        }
    ]
    report = run_endpoint_smoke(
        transport=_all_ok_transport,
        extra_endpoints=post_extra,
    )
    assert not any(r.method == "POST" for r in report.results)
    # Built-in catalog has zero POSTs by design too.
    assert all(r.method != "POST" for r in report.results)

    # With skip_post=False, POST appears.
    report2 = run_endpoint_smoke(
        transport=_all_ok_transport,
        extra_endpoints=post_extra,
        skip_post=False,
    )
    assert any(r.method == "POST" for r in report2.results)


# ---------------------------------------------------------------------------
# Test 8 — elapsed time aggregated correctly
# ---------------------------------------------------------------------------


def test_run_endpoint_smoke_elapsed_time_aggregated() -> None:
    report = run_endpoint_smoke(transport=_all_ok_transport)
    assert report.elapsed_ms >= 0.0
    # Per-result elapsed should sum to <= aggregate (sequential), with some
    # bookkeeping slack tolerated.
    per_call_total = sum(r.elapsed_ms for r in report.results)
    # Aggregate must be at least the sum of per-call times minus epsilon.
    # We add a generous +50ms slack for measurement noise on Windows perf
    # counters.
    assert report.elapsed_ms + 50.0 >= per_call_total


# ---------------------------------------------------------------------------
# Test 9 — plain_english_summary must never include trade-advisory phrases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden",
    [
        "buy now",
        "should you trade",
        "good entry",
        "consider closing",
        "should you sell",
    ],
)
def test_plain_english_summary_avoids_trade_advisory(forbidden: str) -> None:
    # Run under various transport conditions to exercise multiple branches.
    for transport in (_all_ok_transport, _all_500_transport):
        report = run_endpoint_smoke(transport=transport)
        assert forbidden not in report.plain_english_summary.lower()

    # Also the empty-catalog branch.
    empty_report = run_endpoint_smoke(
        transport=_all_ok_transport,
        endpoints=[],
    )
    assert forbidden not in empty_report.plain_english_summary.lower()


# ---------------------------------------------------------------------------
# Test 10 — failures list contains only failed entries
# ---------------------------------------------------------------------------


def test_failures_contains_only_failed_entries() -> None:
    fail_paths = {"/api/forex/health", "/api/forex/dashboard"}

    def transport(method, url, *, json=None, timeout=None):
        for fp in fail_paths:
            if url.endswith(fp):
                return _FakeResponse(status_code=500, body={"err": "x"})
        return _all_ok_transport(method, url, json=json, timeout=timeout)

    report = run_endpoint_smoke(transport=transport)
    assert len(report.failures) == len(fail_paths)
    assert all(not f.success for f in report.failures)
    assert {f.path for f in report.failures} == fail_paths
    for r in report.results:
        if r.success:
            assert r not in report.failures


# ---------------------------------------------------------------------------
# Test 11 — built-in catalog size >= 15
# ---------------------------------------------------------------------------


def test_built_in_endpoint_catalog_has_at_least_15_entries() -> None:
    assert len(BUILT_IN_ENDPOINTS) >= 15
    # Schema sanity: every entry has method + path + name + category.
    for spec in BUILT_IN_ENDPOINTS:
        assert "method" in spec
        assert "path" in spec
        assert "name" in spec
        assert "category" in spec


# ---------------------------------------------------------------------------
# Bonus: now override surfaces deterministic timestamp.
# ---------------------------------------------------------------------------


def test_run_endpoint_smoke_honors_now_override() -> None:
    fixed = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    report = run_endpoint_smoke(
        transport=_all_ok_transport,
        now=fixed,
    )
    assert report.generated_at_iso == fixed.isoformat()
