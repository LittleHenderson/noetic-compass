"""Verify that Atlas LIVE is serving actual Pythia-160M weights.

This script is deliberately stricter than a liveness check. It only exits
0 when the API/worker realmode endpoint proves all required conditions:

* fake_runtime_env is false
* model_loaded is true
* load_error is null
* manifest_is_real_model is true
* verdict is REAL_PYTHIA_WEIGHTS_LOADED
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

import httpx


EXPECTED_MODEL_ID = "EleutherAI/pythia-160m"
REALMODE_PASS = "REAL_PYTHIA_WEIGHTS_LOADED"
DEFAULT_API_URL = "https://cas-harness-customer-api.onrender.com"
DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def _check(name: str, passed: bool, detail: str = "") -> CheckResult:
    return CheckResult(name=name, passed=passed, detail=detail)


def _print_check(result: CheckResult) -> None:
    mark = "PASS" if result.passed else "FAIL"
    line = f"  [{mark}] {result.name}"
    if result.detail:
        line = f"{line}: {result.detail}"
    print(line)


def _http_get(url: str, headers: dict[str, str] | None = None) -> tuple[int, Any, str]:
    try:
        resp = httpx.get(url, headers=headers or {}, timeout=DEFAULT_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        return 0, None, f"transport error: {exc}"
    try:
        body = resp.json()
    except ValueError:
        body = None
    return resp.status_code, body, ""


def _skipped_realmode_checks(prefix: str, reason: str) -> list[CheckResult]:
    return [
        _check(f"{prefix} verdict == {REALMODE_PASS}", False, reason),
        _check(f"{prefix} is_real_model = true", False, "skipped"),
        _check(f"{prefix} fake_runtime_env = false", False, "skipped"),
        _check(f"{prefix} model_loaded = true", False, "skipped"),
        _check(f"{prefix} load_error = null", False, "skipped"),
        _check(f"{prefix} manifest_is_real_model = true", False, "skipped"),
        _check(f"{prefix} model_id == {EXPECTED_MODEL_ID}", False, "skipped"),
    ]


def _check_realmode_payload(prefix: str, payload: dict[str, Any]) -> list[CheckResult]:
    verdict = payload.get("verdict")
    is_real_model = payload.get("is_real_model")
    fake_runtime_env = payload.get("fake_runtime_env")
    model_loaded = payload.get("model_loaded")
    load_error = payload.get("load_error")
    manifest_is_real_model = payload.get("manifest_is_real_model")
    model_id = payload.get("model_id")

    return [
        _check(
            f"{prefix} verdict == {REALMODE_PASS}",
            verdict == REALMODE_PASS,
            f"verdict={verdict!r}",
        ),
        _check(
            f"{prefix} is_real_model = true",
            is_real_model is True,
            f"is_real_model={is_real_model!r}",
        ),
        _check(
            f"{prefix} fake_runtime_env = false",
            fake_runtime_env is False,
            f"fake_runtime_env={fake_runtime_env!r}",
        ),
        _check(
            f"{prefix} model_loaded = true",
            model_loaded is True,
            f"model_loaded={model_loaded!r}",
        ),
        _check(
            f"{prefix} load_error = null",
            load_error is None,
            f"load_error={load_error!r}",
        ),
        _check(
            f"{prefix} manifest_is_real_model = true",
            manifest_is_real_model is True,
            f"manifest_is_real_model={manifest_is_real_model!r}",
        ),
        _check(
            f"{prefix} model_id == {EXPECTED_MODEL_ID}",
            model_id == EXPECTED_MODEL_ID,
            f"model_id={model_id!r}",
        ),
    ]


def check_api(api_url: str) -> list[CheckResult]:
    api_url = api_url.rstrip("/")
    health_url = f"{api_url}/atlas/live/health"
    status, body, err = _http_get(health_url)
    results: list[CheckResult] = []

    if err:
        results.append(_check("API reachable", False, err))
        results.append(_check("Worker URL configured", False, "skipped"))
        results.append(_check("Worker reachable via API", False, "skipped"))
        results.extend(_skipped_realmode_checks("API realmode", "skipped"))
        return results

    results.append(_check("API reachable", True, f"GET {health_url} -> HTTP {status}"))

    if status == 503:
        detail = body.get("detail") if isinstance(body, dict) else None
        if detail == "atlas_live_disabled":
            results.append(_check("Worker URL configured", False, "atlas_live_disabled"))
            results.append(_check("Worker reachable via API", False, "worker URL unset"))
        else:
            results.append(_check("Worker URL configured", True, "configured"))
            results.append(
                _check(
                    "Worker reachable via API",
                    False,
                    f"API returned 503: {detail or 'no detail'}",
                )
            )
        results.extend(_skipped_realmode_checks("API realmode", "worker unreachable"))
        return results

    if status != 200 or not isinstance(body, dict):
        results.append(_check("Worker URL configured", False, f"unexpected HTTP {status}"))
        results.append(_check("Worker reachable via API", False, "skipped"))
        results.extend(_skipped_realmode_checks("API realmode", "health check failed"))
        return results

    results.append(_check("Worker URL configured", True, "/atlas/live/health -> 200"))
    results.append(_check("Worker reachable via API", True, "/atlas/live/health -> 200"))

    realmode_url = f"{api_url}/atlas/live/health/realmode"
    real_status, real_body, real_err = _http_get(realmode_url)
    if real_err or real_status != 200 or not isinstance(real_body, dict):
        detail = real_err or f"HTTP {real_status}"
        results.extend(_skipped_realmode_checks("API realmode", detail))
        return results

    results.extend(_check_realmode_payload("API realmode", real_body))
    return results


def check_worker(worker_url: str, api_key: str | None) -> list[CheckResult]:
    worker_url = worker_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    realmode_url = f"{worker_url}/health/realmode"
    status, body, err = _http_get(realmode_url, headers=headers)

    if err or status != 200 or not isinstance(body, dict):
        detail = err or f"HTTP {status}"
        return [_check("Worker direct reachable", False, detail)] + _skipped_realmode_checks(
            "Worker direct realmode",
            detail,
        )

    return [_check("Worker direct reachable", True, f"GET {realmode_url} -> HTTP 200")] + (
        _check_realmode_payload("Worker direct realmode", body)
    )


def run_verification(
    api_url: str,
    worker_url: str | None = None,
    api_key: str | None = None,
) -> int:
    print(f"Verifying Atlas LIVE via API: {api_url}")
    print()
    print("API checks:")
    api_results = check_api(api_url)
    for result in api_results:
        _print_check(result)

    worker_results: list[CheckResult] = []
    if worker_url:
        print()
        print(f"Worker-direct checks: {worker_url}")
        worker_results = check_worker(worker_url, api_key)
        for result in worker_results:
            _print_check(result)

    all_results = api_results + worker_results
    passed = sum(1 for result in all_results if result.passed)
    total = len(all_results)
    print()
    if passed == total:
        print(f"PASS: {passed}/{total} checks green")
        return 0
    print(f"FAIL: {passed}/{total} checks green; {total - passed} red")
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_atlas_live.py",
        description="Verify Atlas LIVE realmode proof for Pythia-160M.",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"Noetic Compass API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--worker-url",
        default=None,
        help="Optional worker URL for direct /health/realmode verification.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional bearer token for worker-direct verification.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return run_verification(
        api_url=args.api_url,
        worker_url=args.worker_url,
        api_key=args.api_key,
    )


if __name__ == "__main__":
    sys.exit(main())
