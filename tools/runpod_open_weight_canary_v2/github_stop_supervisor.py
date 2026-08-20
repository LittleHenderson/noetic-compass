"""Independent GitHub-hosted stop supervisor for the RunPod canary.

This module uses only the Python standard library.  It never deletes a Pod.
The normal path begins its STOP request 90 seconds before the exact UTC hard
deadline and then verifies a terminal provider state.  The emergency path
is intended for an ``if: always()`` workflow step and retries STOP even when
the normal supervisor failed.

The receipt is operational evidence, not a provider signature or a billing
settlement record.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


REST_BASE = "https://rest.runpod.io/v1"
EXCLUDED_POD_IDS = frozenset({"q2oqlooejhin7s", "hilj2rzs54gi06"})
POD_ID_PATTERN = re.compile(r"^[a-z0-9]{6,32}$")
POD_NAME_PATTERN = re.compile(r"^cas-open-weight-canary-v2-[a-z0-9-]+$")
SOURCE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
MAX_RECEIPT_BYTES = 1_000_000
POLL_SECONDS = 15
STOP_RETRY_DELAYS = (0, 2, 5, 10, 20, 30)
STOP_LEAD_SECONDS = 90


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("UTC timestamp must contain an offset")
    return parsed.astimezone(timezone.utc)


def _parse_provider_utc(value: str) -> datetime:
    legacy = re.fullmatch(
        r"(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) "
        r"(?P<offset>[+-]\d{4}) UTC",
        value,
    )
    if legacy:
        return datetime.strptime(
            f"{legacy.group('date')} {legacy.group('offset')}",
            "%Y-%m-%d %H:%M:%S.%f %z",
        ).astimezone(timezone.utc)
    return _parse_utc(value)


def _validate_identity(pod_id: str, pod_name: str, source_commit: str) -> None:
    if not POD_ID_PATTERN.fullmatch(pod_id):
        raise ValueError("pod id format mismatch")
    if pod_id in EXCLUDED_POD_IDS:
        raise ValueError("protected pod id is forbidden")
    if not POD_NAME_PATTERN.fullmatch(pod_name):
        raise ValueError("pod name format mismatch")
    if not SOURCE_SHA_PATTERN.fullmatch(source_commit):
        raise ValueError("source commit must be an exact 40-character Git SHA")


def _request_json(
    *, method: str, path: str, api_key: str, allow_empty: bool = False
) -> tuple[int, Any]:
    if not api_key or any(character in api_key for character in "\r\n"):
        raise ValueError("RunPod API key is absent or malformed")
    request = Request(
        REST_BASE + path,
        method=method,
        headers={
            "Authorization": "Bearer " + api_key,
            "User-Agent": "cas-open-weight-canary-v2-github-supervisor/1.0",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            status = int(response.status)
            raw = response.read(MAX_RECEIPT_BYTES + 1)
    except HTTPError as error:
        raise RuntimeError(f"RunPod returned HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError("RunPod request failed") from error
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ValueError("RunPod response exceeds the size limit")
    if not raw:
        if allow_empty:
            return status, None
        raise ValueError("RunPod returned an empty response")
    return status, json.loads(raw.decode("utf-8"))


def _get_pod(*, pod_id: str, api_key: str) -> dict[str, Any]:
    status, value = _request_json(
        method="GET",
        path=f"/pods/{quote(pod_id)}?includeMachine=true&includeNetworkVolume=true",
        api_key=api_key,
    )
    if status != 200 or not isinstance(value, dict):
        raise ValueError("RunPod GET response is not an admitted Pod object")
    return value


def _require_bound_target(
    value: dict[str, Any], *, pod_id: str, pod_name: str | None
) -> str:
    if value.get("id") != pod_id:
        raise ValueError("RunPod GET response does not match the bound Pod")
    if pod_name is not None and value.get("name") != pod_name:
        raise ValueError("RunPod GET response does not match the bound Pod name")
    status = value.get("desiredStatus")
    if status not in {"RUNNING", "EXITED", "TERMINATED"}:
        raise ValueError("RunPod desiredStatus is not admitted")
    return str(status)


def _require_bound_provider_start(value: dict[str, Any], expected: str) -> None:
    raw = value.get("lastStartedAt")
    if not isinstance(raw, str):
        raise ValueError("RunPod GET response omits lastStartedAt")
    if _parse_provider_utc(raw) != _parse_utc(expected):
        raise ValueError("RunPod GET response lastStartedAt differs from bound start")


def _post_stop_once(*, pod_id: str, api_key: str) -> int:
    status, _ = _request_json(
        method="POST",
        path=f"/pods/{quote(pod_id)}/stop",
        api_key=api_key,
        allow_empty=True,
    )
    if status != 200:
        raise RuntimeError(f"RunPod STOP returned HTTP {status}")
    return status


def _stop_with_retries(*, pod_id: str, api_key: str) -> tuple[int, int]:
    last_error: Exception | None = None
    for attempt, delay in enumerate(STOP_RETRY_DELAYS, start=1):
        if delay:
            time.sleep(delay)
        try:
            return _post_stop_once(pod_id=pod_id, api_key=api_key), attempt
        except Exception as error:  # bounded retry; the secret is never rendered
            last_error = error
    raise RuntimeError("all bounded RunPod STOP attempts failed") from last_error


def _wait_for_terminal(
    *, pod_id: str, api_key: str, timeout_seconds: int = 600
) -> tuple[str, int]:
    started = time.monotonic()
    polls = 0
    while time.monotonic() - started <= timeout_seconds:
        polls += 1
        try:
            value = _get_pod(pod_id=pod_id, api_key=api_key)
            status = _require_bound_target(value, pod_id=pod_id, pod_name=None)
            if status in {"EXITED", "TERMINATED"}:
                return status, polls
        except Exception:
            pass
        time.sleep(POLL_SECONDS)
    raise RuntimeError("RunPod did not reach a terminal state within the bounded poll window")


def _write_receipt_create_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _canonical_json_bytes(value)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _base_receipt(args: argparse.Namespace, *, mode: str) -> dict[str, Any]:
    return {
        "claim_boundary": (
            "GitHub-hosted operational stop evidence; not a RunPod signature or "
            "billing settlement record."
        ),
        "delete_attempted": False,
        "github_repository": os.environ.get("GITHUB_REPOSITORY"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "hard_stop_deadline_utc": args.deadline,
        "mode": mode,
        "pod_id": args.pod_id,
        "pod_name": args.pod_name,
        "provider_started_at_utc": args.provider_started_at,
        "schema_version": "cas_runpod_github_stop_supervisor.v2",
        "source_commit_sha": args.source_commit,
        "supervisor_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
    }


def arm_check(args: argparse.Namespace) -> int:
    _validate_identity(args.pod_id, args.pod_name, args.source_commit)
    if os.environ.get("GITHUB_SHA") != args.source_commit:
        raise ValueError("GitHub runner SHA does not match the bound source commit")
    deadline = _parse_utc(args.deadline)
    provider_started = _parse_utc(args.provider_started_at)
    if deadline != provider_started + timedelta(seconds=1800):
        raise ValueError("hard-stop deadline is not exactly provider start plus 1800 seconds")
    remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
    if remaining < 600 or remaining > 2_100:
        raise ValueError("hard-stop deadline must be 10 to 35 minutes after arm check")
    api_key = os.environ.get("RUNPOD_API_KEY", "")
    observed = _get_pod(pod_id=args.pod_id, api_key=api_key)
    observed_status = _require_bound_target(
        observed, pod_id=args.pod_id, pod_name=args.pod_name
    )
    _require_bound_provider_start(observed, args.provider_started_at)
    if observed_status != "RUNNING":
        raise ValueError("bound Pod is not RUNNING at supervisor arm check")
    receipt = _base_receipt(args, mode="PRE_DEADLINE_ARM_CHECK")
    receipt.update(
        {
            "observed_status": observed_status,
            "status": "ARMED_PROVIDER_GET_SUCCEEDED",
            "written_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    _write_receipt_create_new(Path(args.receipt), receipt)
    return 0


def run_supervisor(args: argparse.Namespace) -> int:
    _validate_identity(args.pod_id, args.pod_name, args.source_commit)
    github_sha = os.environ.get("GITHUB_SHA")
    if github_sha != args.source_commit:
        raise ValueError("GitHub runner SHA does not match the bound source commit")
    deadline = _parse_utc(args.deadline)
    provider_started = _parse_utc(args.provider_started_at)
    if deadline != provider_started + timedelta(seconds=1800):
        raise ValueError("hard-stop deadline is not exactly provider start plus 1800 seconds")
    now = datetime.now(timezone.utc)
    if deadline > now.replace(microsecond=0) and (deadline - now).total_seconds() > 2_100:
        raise ValueError("hard-stop deadline is more than 35 minutes away")
    stop_request_boundary = deadline - timedelta(seconds=STOP_LEAD_SECONDS)
    while datetime.now(timezone.utc) < stop_request_boundary:
        remaining = (stop_request_boundary - datetime.now(timezone.utc)).total_seconds()
        time.sleep(max(0.1, min(15.0, remaining)))

    api_key = os.environ.get("RUNPOD_API_KEY", "")
    before = _get_pod(pod_id=args.pod_id, api_key=api_key)
    # The exact name was provider-verified by the canonical arm receipt.  At
    # the pre-deadline STOP boundary, recovery is keyed only by the immutable
    # Pod ID so an editable-name drift cannot defeat cost containment.
    before_status = _require_bound_target(before, pod_id=args.pod_id, pod_name=None)
    _require_bound_provider_start(before, args.provider_started_at)
    stop_http_status: int | None = None
    stop_attempts = 0
    if before_status == "RUNNING":
        stop_http_status, stop_attempts = _stop_with_retries(
            pod_id=args.pod_id, api_key=api_key
        )
    terminal_status, terminal_polls = _wait_for_terminal(
        pod_id=args.pod_id, api_key=api_key
    )
    receipt = _base_receipt(args, mode="NORMAL_PRE_DEADLINE_STOP")
    receipt.update(
        {
            "observed_before_stop": before_status,
            "observed_terminal_status": terminal_status,
            "status": "STOPPED_OR_ALREADY_TERMINAL_CONFIRMED",
            "stop_lead_seconds": STOP_LEAD_SECONDS,
            "stop_attempts": stop_attempts,
            "stop_http_status": stop_http_status,
            "terminal_poll_count": terminal_polls,
            "written_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    _write_receipt_create_new(Path(args.receipt), receipt)
    return 0


def emergency_stop(args: argparse.Namespace) -> int:
    _validate_identity(args.pod_id, args.pod_name, args.source_commit)
    arm_receipt_path = Path(args.arm_receipt)
    arm_raw = arm_receipt_path.read_bytes()
    if len(arm_raw) > MAX_RECEIPT_BYTES:
        raise ValueError("arm receipt exceeds the size limit")
    arm_receipt = json.loads(arm_raw.decode("utf-8"))
    if not isinstance(arm_receipt, dict) or arm_raw != _canonical_json_bytes(arm_receipt):
        raise ValueError("emergency STOP requires a canonical arm receipt")
    required_arm_keys = {
        "claim_boundary",
        "delete_attempted",
        "github_repository",
        "github_run_attempt",
        "github_run_id",
        "github_sha",
        "hard_stop_deadline_utc",
        "mode",
        "observed_status",
        "pod_id",
        "pod_name",
        "provider_started_at_utc",
        "schema_version",
        "source_commit_sha",
        "status",
        "supervisor_source_sha256",
        "written_at_utc",
    }
    if set(arm_receipt) != required_arm_keys:
        raise ValueError("emergency STOP arm receipt keyset mismatch")
    exact_arm_bindings = {
        "claim_boundary": (
            "GitHub-hosted operational stop evidence; not a RunPod signature or "
            "billing settlement record."
        ),
        "delete_attempted": False,
        "github_repository": os.environ.get("GITHUB_REPOSITORY"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_sha": args.source_commit,
        "hard_stop_deadline_utc": args.deadline,
        "mode": "PRE_DEADLINE_ARM_CHECK",
        "observed_status": "RUNNING",
        "pod_id": args.pod_id,
        "pod_name": args.pod_name,
        "provider_started_at_utc": args.provider_started_at,
        "schema_version": "cas_runpod_github_stop_supervisor.v2",
        "source_commit_sha": args.source_commit,
        "status": "ARMED_PROVIDER_GET_SUCCEEDED",
        "supervisor_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
    }
    for key, expected in exact_arm_bindings.items():
        if arm_receipt.get(key) != expected:
            raise ValueError(f"emergency STOP arm receipt {key} mismatch")
    arm_written = _parse_utc(str(arm_receipt.get("written_at_utc")))
    arm_deadline = _parse_utc(args.deadline)
    provider_started = _parse_utc(args.provider_started_at)
    if arm_deadline != provider_started + timedelta(seconds=1800):
        raise ValueError("emergency STOP deadline/start binding mismatch")
    if not arm_deadline - timedelta(minutes=35) <= arm_written < arm_deadline:
        raise ValueError("emergency STOP arm receipt time is outside the bound window")
    api_key = os.environ.get("RUNPOD_API_KEY", "")
    emergency_observed = _get_pod(pod_id=args.pod_id, api_key=api_key)
    emergency_before_status = _require_bound_target(
        emergency_observed, pod_id=args.pod_id, pod_name=None
    )
    _require_bound_provider_start(emergency_observed, args.provider_started_at)
    stop_http_status: int | None = None
    stop_attempts = 0
    if emergency_before_status == "RUNNING":
        stop_http_status, stop_attempts = _stop_with_retries(
            pod_id=args.pod_id, api_key=api_key
        )
        terminal_status, terminal_polls = _wait_for_terminal(
            pod_id=args.pod_id, api_key=api_key
        )
    else:
        terminal_status = emergency_before_status
        terminal_polls = 0
    receipt = _base_receipt(args, mode="ALWAYS_RUN_EMERGENCY_STOP")
    receipt.update(
        {
            "observed_before_stop": emergency_before_status,
            "observed_terminal_status": terminal_status,
            "status": "EMERGENCY_STOPPED_OR_ALREADY_TERMINAL_CONFIRMED",
            "stop_attempts": stop_attempts,
            "stop_http_status": stop_http_status,
            "terminal_poll_count": terminal_polls,
            "written_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    receipt_path = Path(args.receipt)
    _write_receipt_create_new(receipt_path, receipt)
    return 0


def self_test() -> int:
    try:
        _validate_identity("q2oqlooejhin7s", "cas-open-weight-canary-v2-test", "0" * 40)
    except ValueError as error:
        if "protected" not in str(error):
            raise
    else:
        raise AssertionError("protected-pod self-test did not reject")
    encoded = _canonical_json_bytes({"b": 2, "a": 1})
    if encoded != b'{"a":1,"b":2}\n':
        raise AssertionError("canonical JSON self-test failed")
    print("SELF_TEST_PASS_NO_PROVIDER_CALL")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("arm-check", "run", "emergency-stop"):
        child = subparsers.add_parser(command)
        child.add_argument("--pod-id", required=True)
        child.add_argument("--pod-name", required=True)
        child.add_argument("--deadline", required=True)
        child.add_argument("--provider-started-at", required=True)
        child.add_argument("--source-commit", required=True)
        child.add_argument("--receipt", required=True)
        if command == "emergency-stop":
            child.add_argument("--arm-receipt", required=True)
    subparsers.add_parser("self-test")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "self-test":
        return self_test()
    if args.command == "arm-check":
        return arm_check(args)
    if args.command == "run":
        return run_supervisor(args)
    if args.command == "emergency-stop":
        return emergency_stop(args)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"SUPERVISOR_FAIL_CLOSED: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(2)
