"""Verify the deployed Atlas LIVE worker is in real-model mode.

Hits the noetic-compass-api Atlas LIVE health surfaces and (optionally)
the worker directly, then prints a green/red checklist. Exits 0 when
every check passes, 1 otherwise.

The point: a single command answers "is the deployed RunPod actually
running Pythia-160M right now, or has it fallen back to fake?" without
opening the cockpit and parsing SSE events.

Examples
--------

    # Most common: just hit the production API.
    python scripts/verify_atlas_live.py

    # Stage / custom API host:
    python scripts/verify_atlas_live.py \\
        --api-url https://noetic-compass-api-staging.onrender.com

    # Also probe the worker directly (debugging proxy issues):
    python scripts/verify_atlas_live.py \\
        --worker-url https://pythia-worker.runpod.net \\
        --api-key "$ATLAS_LIVE_WORKER_API_KEY"
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

import httpx


EXPECTED_MODEL_ID = "EleutherAI/pythia-160m"
DEFAULT_API_URL = "https://noetic-compass-api.onrender.com"
DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def _check(name: str, passed: bool, detail: str = "") -> CheckResult:
    return CheckResult(name=name, passed=passed, detail=detail)


def _print_check(result: CheckResult) -> None:
    mark = "✓" if result.passed else "✗"
    line = f"  [{mark}] {result.name}"
    if result.detail:
        line = f"{line} — {result.detail}"
    print(line)


def _http_get(url: str, headers: dict[str, str] | None = None) -> tuple[int, Any, str]:
    """GET helper returning (status_code, parsed_json_or_None, error_str)."""
    try:
        resp = httpx.get(url, headers=headers or {}, timeout=DEFAULT_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        return 0, None, f"transport error: {exc}"
    try:
        body = resp.json()
    except ValueError:
        body = None
    return resp.status_code, body, ""


def check_api(api_url: str) -> list[CheckResult]:
    """Run the API-side checklist."""
    api_url = api_url.rstrip("/")
    results: list[CheckResult] = []

    # 1. API reachable + worker URL configured (via /atlas/live/health).
    health_url = f"{api_url}/atlas/live/health"
    status, body, err = _http_get(health_url)
    if err:
        results.append(_check("API reachable", False, err))
        results.append(_check("Worker URL configured", False, "skipped — API unreachable"))
        results.append(_check("Worker reachable (via API)", False, "skipped — API unreachable"))
        results.append(_check("is_real_model = true", False, "skipped"))
        results.append(_check("model_loaded = true", False, "skipped"))
        results.append(_check("load_error = null", False, "skipped"))
        results.append(_check("fake_runtime_env = false", False, "skipped"))
        results.append(_check(f"model_id == {EXPECTED_MODEL_ID}", False, "skipped"))
        return results

    results.append(_check("API reachable", True, f"GET {health_url} -> HTTP {status}"))

    if status == 503:
        detail = ""
        if isinstance(body, dict):
            detail = str(body.get("detail", ""))
        if detail == "atlas_live_disabled":
            results.append(_check("Worker URL configured", False, "API returned atlas_live_disabled"))
            results.append(_check("Worker reachable (via API)", False, "skipped — worker URL unset"))
        else:
            # 503 but not the disabled marker -> worker unreachable from API.
            results.append(_check("Worker URL configured", True, "configured (no atlas_live_disabled)"))
            results.append(_check("Worker reachable (via API)", False, f"API returned 503: {detail or 'no detail'}"))
        results.append(_check("is_real_model = true", False, "skipped — worker unreachable"))
        results.append(_check("model_loaded = true", False, "skipped"))
        results.append(_check("load_error = null", False, "skipped"))
        results.append(_check("fake_runtime_env = false", False, "skipped"))
        results.append(_check(f"model_id == {EXPECTED_MODEL_ID}", False, "skipped"))
        return results

    if status != 200 or not isinstance(body, dict):
        results.append(_check("Worker URL configured", False, f"unexpected HTTP {status}"))
        results.append(_check("Worker reachable (via API)", False, "skipped"))
        results.append(_check("is_real_model = true", False, "skipped"))
        results.append(_check("model_loaded = true", False, "skipped"))
        results.append(_check("load_error = null", False, "skipped"))
        results.append(_check("fake_runtime_env = false", False, "skipped"))
        results.append(_check(f"model_id == {EXPECTED_MODEL_ID}", False, "skipped"))
        return results

    results.append(_check("Worker URL configured", True, "/atlas/live/health -> 200"))
    results.append(_check("Worker reachable (via API)", True, "/atlas/live/health -> 200"))

    # 2. Realmode probe. Real-mode means ALL FOUR conditions hold:
    #    is_real_model=true (worker's own real-mode assertion),
    #    model_loaded=true (Pythia weights actually in memory),
    #    load_error=null (no prior load failure recorded),
    #    fake_runtime_env=false (LIVE_TRACE_DEMO_MODE not set),
    #    plus model_id == EleutherAI/pythia-160m. Earlier wiring of this
    #    script only checked is_real_model, which can be true on a cold
    #    worker that has never loaded weights — that lets a fake-but-not-
    #    forced state silently certify "LIVE". Each condition is reported
    #    separately so operators see which one fails.
    realmode_url = f"{api_url}/atlas/live/health/realmode"
    rstatus, rbody, rerr = _http_get(realmode_url)
    if rerr or rstatus != 200 or not isinstance(rbody, dict):
        results.append(_check("is_real_model = true", False, rerr or f"HTTP {rstatus}"))
        results.append(_check("model_loaded = true", False, "skipped"))
        results.append(_check("load_error = null", False, "skipped"))
        results.append(_check("fake_runtime_env = false", False, "skipped"))
        results.append(_check(f"model_id == {EXPECTED_MODEL_ID}", False, "skipped"))
        return results

    is_real = bool(rbody.get("is_real_model"))
    results.append(_check("is_real_model = true", is_real, f"is_real_model={rbody.get('is_real_model')!r}"))

    model_loaded = bool(rbody.get("model_loaded"))
    results.append(
        _check(
            "model_loaded = true",
            model_loaded,
            f"model_loaded={rbody.get('model_loaded')!r}",
        )
    )

    load_error = rbody.get("load_error")
    results.append(
        _check(
            "load_error = null",
            load_error is None,
            f"load_error={load_error!r}",
        )
    )

    fake_env = bool(rbody.get("fake_runtime_env"))
    results.append(
        _check(
            "fake_runtime_env = false",
            not fake_env,
            f"fake_runtime_env={rbody.get('fake_runtime_env')!r}",
        )
    )

    model_id = str(rbody.get("model_id", ""))
    results.append(
        _check(
            f"model_id == {EXPECTED_MODEL_ID}",
            model_id == EXPECTED_MODEL_ID,
            f"model_id={model_id!r}",
        )
    )
    return results


def check_worker(worker_url: str, api_key: str | None) -> list[CheckResult]:
    """Run the worker-direct checklist."""
    worker_url = worker_url.rstrip("/")
    results: list[CheckResult] = []
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None

    realmode_url = f"{worker_url}/health/realmode"
    status, body, err = _http_get(realmode_url, headers=headers)
    if err or status != 200 or not isinstance(body, dict):
        detail = err or f"HTTP {status}"
        results.append(_check("Worker reachable (direct)", False, detail))
        results.append(_check("Worker is_real_model = true", False, "skipped"))
        results.append(_check("Worker model_loaded = true", False, "skipped"))
        results.append(_check("Worker load_error = null", False, "skipped"))
        results.append(_check("Worker fake_runtime_env = false", False, "skipped"))
        results.append(_check(f"Worker model_id == {EXPECTED_MODEL_ID}", False, "skipped"))
        return results

    results.append(_check("Worker reachable (direct)", True, f"GET {realmode_url} -> HTTP 200"))

    is_real = bool(body.get("is_real_model"))
    results.append(
        _check(
            "Worker is_real_model = true",
            is_real,
            f"is_real_model={body.get('is_real_model')!r}",
        )
    )

    model_loaded = bool(body.get("model_loaded"))
    results.append(
        _check(
            "Worker model_loaded = true",
            model_loaded,
            f"model_loaded={body.get('model_loaded')!r}",
        )
    )

    load_error = body.get("load_error")
    results.append(
        _check(
            "Worker load_error = null",
            load_error is None,
            f"load_error={load_error!r}",
        )
    )

    fake_env = bool(body.get("fake_runtime_env"))
    results.append(
        _check(
            "Worker fake_runtime_env = false",
            not fake_env,
            f"fake_runtime_env={body.get('fake_runtime_env')!r}",
        )
    )

    model_id = str(body.get("model_id", ""))
    results.append(
        _check(
            f"Worker model_id == {EXPECTED_MODEL_ID}",
            model_id == EXPECTED_MODEL_ID,
            f"model_id={model_id!r}",
        )
    )
    return results


def run_verification(
    api_url: str,
    worker_url: str | None = None,
    api_key: str | None = None,
) -> int:
    """Run the full verification and return the exit code (0 = all green)."""
    print(f"Verifying Atlas LIVE deployment via {api_url}")
    print()
    print("API checks:")
    api_results = check_api(api_url)
    for r in api_results:
        _print_check(r)

    worker_results: list[CheckResult] = []
    if worker_url:
        print()
        print(f"Worker-direct checks ({worker_url}):")
        worker_results = check_worker(worker_url, api_key)
        for r in worker_results:
            _print_check(r)

    all_results = api_results + worker_results
    passed = sum(1 for r in all_results if r.passed)
    total = len(all_results)
    print()
    if passed == total:
        print(f"PASS — {passed}/{total} checks green")
        return 0
    print(f"FAIL — {passed}/{total} checks green; {total - passed} red")
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_atlas_live.py",
        description=(
            "Verify the deployed Atlas LIVE worker is in real-model mode "
            "(Pythia-160M) and not falling back to fake."
        ),
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"Noetic Compass API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--worker-url",
        default=None,
        help="Optional: hit the worker directly too (for debugging).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional: bearer token for the worker-direct probe.",
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
