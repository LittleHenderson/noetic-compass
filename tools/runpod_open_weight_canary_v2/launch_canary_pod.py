"""Live launch driver for the one authorized canary Pod.

This is the ONLY entry point in the repository that can spend money. It wires
the frozen create-once library (`execute_create_once`) to real collaborators:

    transport   RunPodHttpsTransport            (frozen library class)
    guardian    BridgeGuardian                  (authorization consumption +
                                                 live inventory + GitHub stop
                                                 dispatch on bind)
    local_arm   WatchdogLocalArm                (spawns the frozen PowerShell
                                                 watchdog for the exact Pod)
    validator   RunnerAndWatchdogValidator      (frozen library class; both
                                                 consumer contracts)
    secret      SecretGuard([api key])          (frozen library class)

Two subcommands:

  authorize   Build the one-use `cas_runpod_create_authorization.v1` document,
              print its SHA-256, and exit. NOTHING is sent anywhere. The owner
              reads the terms and the hash; the launch consumes it within its
              15-minute validity window.
  launch      Execute the one create transaction. Refuses unless BOTH
              `--i-confirm-one-paid-create` is present AND a valid, current
              authorization document is supplied. `execute_create_once` never
              retries a create; a replayed authorization refuses durably in
              both the launcher marker AND the bridge marker.

Spend bounds carried in code, not convention: `maximum_spend_usd` is pinned
"0.50" by the frozen library (`_validate_configuration_literals`), the
authorization pins `maximum_wall_seconds` 1800, the watchdog refuses an
observed rate above 0.50/hr, and the guardian receipt pins the 30-minute
deadline arithmetic.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from create_provider_launch_receipt import (
    AUTHORIZATION_CLAIM,
    AUTHORIZATION_SCHEMA,
    ArmContext,
    LaunchConfiguration,
    ProtocolFailure,
    RunPodHttpsTransport,
    RunnerAndWatchdogValidator,
    SecretGuard,
    build_create_request,
    canonical_json_bytes,
    execute_create_once,
    sha256_bytes,
    _format_utc,
    _self_hashed,
)
from precreate_guardian_bridge import BridgeGuardian

REPOSITORY = "LittleHenderson/noetic-compass"
IMAGE_NAME = "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404"
OCI_IMAGE_DIGEST = (
    "sha256:4d1721e62b56d345c83b4fd6090664be6daf9312caab5b2e76f23d8231941851"
)
WATCHDOG_PATH = Path(__file__).resolve().parent / "watchdog_armed.ps1"
_POD_NAME = re.compile(r"^cas-open-weight-canary-v2-[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{32}$")


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value.strip():
        raise SystemExit(f"MISSING_REQUIRED_ENVIRONMENT_{name}")
    return value.strip()


def _fresh_pod_name() -> str:
    stamp = _format_utc(datetime.now(timezone.utc))
    slug = re.sub(r"[^a-z0-9]", "", stamp.lower())
    return f"cas-open-weight-canary-v2-{slug}-{secrets.token_hex(16)}"


def _configuration(args: argparse.Namespace, pod_name: str) -> LaunchConfiguration:
    state = Path(args.state_directory)
    state.mkdir(parents=True, exist_ok=True)
    public_key_path = Path(args.public_key_path)
    public_key = public_key_path.read_text(encoding="utf-8").strip()
    return LaunchConfiguration(
        pod_name=pod_name,
        source_commit_sha256=args.source_commit,
        oci_image_digest=OCI_IMAGE_DIGEST,
        image_name=IMAGE_NAME,
        public_key=public_key,
        authorization_path=Path(args.authorization),
        expected_authorization_sha256=args.authorization_sha256 or "",
        state_directory=state,
        provider_receipt_path=state / "provider-launch-receipt.json",
        failure_evidence_path=state / "provider-launch-failure.json",
        public_key_path=public_key_path,
        observed_hourly_rate=args.observed_hourly_rate,
    )


def _authorize(args: argparse.Namespace) -> int:
    pod_name = args.pod_name or _fresh_pod_name()
    if not _POD_NAME.fullmatch(pod_name):
        raise SystemExit("POD_NAME_MALFORMED")
    configuration = _configuration(args, pod_name)
    request_raw = canonical_json_bytes(build_create_request(configuration))
    issued = datetime.now(timezone.utc)
    document = _self_hashed(
        {
            "authorization_id": "canary-" + secrets.token_hex(16),
            "claim_boundary": AUTHORIZATION_CLAIM,
            "expires_at_utc": _format_utc(issued + timedelta(minutes=15)),
            "issued_at_utc": _format_utc(issued),
            "maximum_spend_usd": "0.50",
            "maximum_wall_seconds": 1800,
            "oci_image_digest": OCI_IMAGE_DIGEST,
            "one_use": True,
            "operation": "CREATE_EXACTLY_ONE_NEW_RUNPOD_POD",
            "pod_name": pod_name,
            "provider": "RUNPOD",
            "request_body_sha256": sha256_bytes(request_raw),
            "schema_version": AUTHORIZATION_SCHEMA,
            "source_commit_sha256": args.source_commit,
            "status": "AUTHORIZED_FOR_ONE_NEW_RUNPOD_CANARY",
        },
        "authorization_sha256",
    )
    raw = canonical_json_bytes(document)
    path = Path(args.authorization)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as handle:  # never overwrite an authorization
        handle.write(raw)
    print(f"AUTHORIZATION_WRITTEN path={path}")
    print(f"AUTHORIZATION_SHA256 {sha256_bytes(raw)}")
    print(f"POD_NAME {pod_name}")
    print(f"REQUEST_BODY_SHA256 {document['request_body_sha256']}")
    print(f"EXPIRES_AT_UTC {document['expires_at_utc']}")
    print("TERMS one pod, SECURE cloud A40, <=0.50 USD, 1800 s wall, one attempt")
    return 0


class WatchdogLocalArm:
    """Spawn the frozen local watchdog, detached, for the exact created Pod."""

    def __init__(self, *, state_directory: Path, spawner=None) -> None:
        self._state = state_directory
        self._spawn = spawner if spawner is not None else self._spawn_detached

    @staticmethod
    def _spawn_detached(argv: list[str]) -> None:
        flags = 0
        if os.name == "nt":  # detach so the watchdog outlives this process
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008
        subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )

    def arm(self, context: ArmContext) -> None:
        import shutil

        executable = shutil.which("pwsh") or shutil.which("powershell")
        if executable is None:
            raise ProtocolFailure("LOCAL_WATCHDOG_POWERSHELL_UNAVAILABLE")
        receipt_directory = self._state / "watchdog-receipts"
        receipt_directory.mkdir(parents=True, exist_ok=True)
        self._spawn(
            [
                executable,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(WATCHDOG_PATH),
                "-PodId",
                context.pod_id,
                "-PodName",
                context.pod_name,
                "-RunStartedAtUtc",
                context.provider_started_at_utc,
                "-HardStopDeadlineUtc",
                context.hard_stop_deadline_utc,
                "-SourceCommitSha256",
                context.source_commit_sha256,
                "-OciImageDigest",
                context.oci_image_digest,
                "-ExpectedImageName",
                context.image_name,
                "-ObservedHourlyRate",
                "0.44",
                "-ReceiptDirectory",
                str(receipt_directory),
                "-ProviderLaunchReceiptPath",
                str(context.provider_receipt_path),
                "-ProviderLaunchReceiptSha256",
                context.provider_receipt_sha256.upper(),
            ]
        )


def _launch(args: argparse.Namespace) -> int:
    if not args.i_confirm_one_paid_create:
        print("REFUSED_WITHOUT_EXPLICIT_CONFIRMATION_FLAG")
        return 4
    if not args.authorization_sha256:
        print("REFUSED_WITHOUT_AUTHORIZATION_SHA256")
        return 4
    authorization_raw = Path(args.authorization).read_bytes()
    document = json.loads(authorization_raw)
    pod_name = str(document.get("pod_name", ""))
    if not _POD_NAME.fullmatch(pod_name):
        print("AUTHORIZATION_POD_NAME_MALFORMED")
        return 4
    configuration = _configuration(args, pod_name)
    api_key = _required_env("RUNPOD_API_KEY")
    outcome = execute_create_once(
        configuration,
        transport=RunPodHttpsTransport(api_key),
        guardian=BridgeGuardian(
            state_directory=configuration.state_directory / "bridge-guardian",
            repository=REPOSITORY,
        ),
        local_arm=WatchdogLocalArm(state_directory=configuration.state_directory),
        validator=RunnerAndWatchdogValidator(),
        secret_guard=SecretGuard([api_key]),
    )
    print(f"OUTCOME status={outcome.status}")
    print(f"OUTCOME pod_id={outcome.pod_id}")
    print(f"OUTCOME receipt={configuration.provider_receipt_path}")
    return 0 if outcome.status == "EXACT_CREATE_RESPONSE_STARTED_POD_OBSERVED" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--authorization", required=True)
    common.add_argument("--authorization-sha256", default="")
    common.add_argument("--source-commit", required=True)
    common.add_argument("--state-directory", required=True)
    common.add_argument("--public-key-path", required=True)
    common.add_argument("--observed-hourly-rate", default="0.44")

    authorize = sub.add_parser("authorize", parents=[common])
    authorize.add_argument("--pod-name", default="")

    launch = sub.add_parser("launch", parents=[common])
    launch.add_argument("--i-confirm-one-paid-create", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "authorize":
            return _authorize(args)
        return _launch(args)
    except ProtocolFailure as failure:
        print(f"LAUNCH_FAIL_CLOSED:{failure}")
        return 3
    except SystemExit:
        raise
    except Exception as error:  # noqa: BLE001 - class name only, never a value
        print(f"LAUNCH_FAIL_CLOSED:{type(error).__name__}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
