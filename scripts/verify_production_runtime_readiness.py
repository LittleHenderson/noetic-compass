#!/usr/bin/env python3
"""Fail closed when the public CAS production runtime is not actually ready.

The monitor uses only public, metadata-only endpoints.  It never runs model
inference, writes an Evidence Packet, or requires a RunPod account credential.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterable, Mapping


DEFAULT_API_BASE_URL = "https://cas-harness-customer-api.onrender.com"
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_RESPONSE_BYTES = 1_000_000
EXPECTED_MODEL_ID = "EleutherAI/pythia-160m"
REALMODE_PASS = "REAL_PYTHIA_WEIGHTS_LOADED"
REQUIRED_PRODUCTION_DEPENDENCIES = ("live_worker", "s3_worm")
SAFE_DEPENDENCY_REASONS = frozenset(
    {
        "authentication_failed",
        "authority_check_failed",
        "authority_denied",
        "bucket_unavailable",
        "credentials_unavailable",
        "invalid_response",
        "invalid_worker_configuration",
        "invalid_worker_url",
        "object_lock_disabled",
        "object_lock_policy_invalid",
        "object_lock_retention_below_minimum",
        "realmode_contract_failed",
        "s3_client_unavailable",
        "s3_configuration_incomplete",
        "s3_configuration_invalid",
        "timeout",
        "unreachable",
        "unsupported_anchor_mode",
        "versioning_disabled",
        "worker_token_required",
    }
)


class RuntimeMonitorError(RuntimeError):
    """The public runtime failed a production dependency contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeMonitorError(message)


def validate_api_base_url(value: str) -> str:
    base = value.strip().rstrip("/")
    try:
        parsed = urllib.parse.urlsplit(base)
    except ValueError as exc:
        raise RuntimeMonitorError("API base URL is invalid") from exc
    _require(
        parsed.scheme in {"http", "https"},
        "API base URL must use http or https",
    )
    _require(bool(parsed.hostname), "API base URL must include a hostname")
    _require(
        parsed.username is None and parsed.password is None,
        "API base URL must not embed credentials",
    )
    _require(
        not parsed.query and not parsed.fragment,
        "API base URL must not include query or fragment",
    )
    return base


def _decode_json_body(response: Any) -> Mapping[str, Any] | None:
    body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeMonitorError("runtime response exceeded the size limit")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def request_json(
    base_url: str,
    path: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[int, Mapping[str, Any] | None]:
    request = urllib.request.Request(
        f"{validate_api_base_url(base_url)}{path}",
        headers={
            "Accept": "application/json",
            "User-Agent": "cas-production-runtime-monitor/1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), _decode_json_body(response)
    except urllib.error.HTTPError as exc:
        return int(exc.code), _decode_json_body(exc)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeMonitorError(
            f"runtime request failed: {type(exc).__name__}"
        ) from exc


def validate_readiness_payload(status: int, payload: Mapping[str, Any] | None) -> None:
    """Require the public API and both production dependencies to be ready."""

    _require(payload is not None, f"/health/ready returned invalid JSON (HTTP {status})")
    checks = payload.get("checks")
    _require(isinstance(checks, Mapping), "/health/ready checks are missing")

    failures: list[str] = []
    for name in REQUIRED_PRODUCTION_DEPENDENCIES:
        check = checks.get(name)
        if not isinstance(check, Mapping):
            failures.append(f"{name}=missing")
            continue
        if check.get("configured") is not True:
            failures.append(f"{name}=not_configured")
        elif check.get("required") is not True:
            failures.append(f"{name}=not_required")
        elif check.get("status") != "ok":
            reason = check.get("reason")
            safe_reason = (
                reason
                if isinstance(reason, str) and reason in SAFE_DEPENDENCY_REASONS
                else "error"
            )
            failures.append(f"{name}={safe_reason}")
        elif check.get("authority") != "verified":
            failures.append(f"{name}=authority_unverified")

    _require(not failures, "production dependencies unavailable: " + ", ".join(failures))
    _require(status == 200, f"/health/ready returned HTTP {status}")
    _require(payload.get("ready") is True, "/health/ready did not report ready=true")
    _require(payload.get("status") == "ok", "/health/ready did not report status=ok")


def validate_realmode_payload(status: int, payload: Mapping[str, Any] | None) -> None:
    """Require strict real-Pythia metadata from the public API worker proxy."""

    _require(status == 200, f"worker realmode proxy returned HTTP {status}")
    _require(payload is not None, "worker realmode proxy returned invalid JSON")
    required = {
        "verdict": payload.get("verdict") == REALMODE_PASS,
        "is_real_model": payload.get("is_real_model") is True,
        "fake_runtime_env": payload.get("fake_runtime_env") is False,
        "model_loaded": payload.get("model_loaded") is True,
        "load_error": payload.get("load_error") is None,
        "manifest_is_real_model": payload.get("manifest_is_real_model") is True,
        "model_id": payload.get("model_id") == EXPECTED_MODEL_ID,
    }
    failed = [name for name, passed in required.items() if not passed]
    _require(not failed, "worker realmode contract failed: " + ", ".join(failed))


def run_monitor(
    base_url: str,
    *,
    check_readiness: bool,
    check_worker_realmode: bool,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    if check_readiness:
        status, payload = request_json(base_url, "/health/ready", timeout=timeout)
        validate_readiness_payload(status, payload)
        print("production API dependency readiness PASS")
    if check_worker_realmode:
        status, payload = request_json(
            base_url,
            "/atlas/live/health/realmode",
            timeout=timeout,
        )
        validate_realmode_payload(status, payload)
        print("production worker realmode PASS")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-base-url",
        default=os.environ.get("CAS_PRODUCTION_API_BASE_URL", "")
        or DEFAULT_API_BASE_URL,
        help="Public API base URL (defaults to production Render API)",
    )
    parser.add_argument(
        "--readiness",
        action="store_true",
        help="check /health/ready and require worker + S3 WORM authority",
    )
    parser.add_argument(
        "--worker-realmode",
        action="store_true",
        help="check strict worker real-weight metadata through the API proxy",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="request timeout in seconds",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    check_readiness = bool(args.readiness)
    check_worker = bool(args.worker_realmode)
    if not check_readiness and not check_worker:
        check_readiness = True
        check_worker = True
    try:
        _require(args.timeout > 0, "timeout must be positive")
        run_monitor(
            args.api_base_url,
            check_readiness=check_readiness,
            check_worker_realmode=check_worker,
            timeout=args.timeout,
        )
    except RuntimeMonitorError as exc:
        print(f"production runtime monitor FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
