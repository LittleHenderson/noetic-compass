#!/usr/bin/env python3
"""Verify one externally pinned signed root-CI receipt for a protected checkout.

The receipt is produced by the ``Customer Production Evidence`` workflow.  This
command verifies the artifact's recorded checksum, its external SHA-256 pin,
the pinned RS256 issuer/signature, its exact 120-minute validity window, the
complete embedded root-CI contract, and the expected master/deployment identity.
It performs no provider read, authority write, or acceptance publication.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import sys

import assemble_customer_production_acceptance_candidate as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKSUM_SUBJECT = (
    "customer-production-evidence/receipts/root-ci-protected-deploy.json"
)
CHECKSUM_RE = re.compile(
    rf"^(?P<sha256>[0-9a-f]{{64}})  {re.escape(CHECKSUM_SUBJECT)}\n$"
)
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
DEPLOY_ID_RE = re.compile(r"^dep-[a-z0-9]{1,64}$")
OBJECT_ID_RE = re.compile(r"^[0-9a-f]{40,64}$")
WORKFLOW_WINDOW_SECONDS = 20 * 60
DANGEROUS_GIT_ENVIRONMENT = frozenset(
    {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_REPLACE_REF_BASE",
        "GIT_NAMESPACE",
    }
)
SECURITY_CRITICAL_REPOSITORY_PATHS = (
    ".github/workflows/alert-delivery-drill.yml",
    ".production/customer-production-trusted-issuers.json",
    "scripts/assemble_customer_production_acceptance_candidate.py",
    "scripts/build_alert_delivery_gate_payload.py",
    "scripts/deliver_alert_delivery_drill.py",
    "scripts/deliver_production_runtime_alert.py",
    "scripts/verify_customer_production_acceptance.py",
    "scripts/verify_pinned_root_ci_receipt.py",
)


class ReceiptVerificationError(RuntimeError):
    """The artifact, signature, freshness, or current binding failed closed."""


def _sanitized_git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if name in DANGEROUS_GIT_ENVIRONMENT or name.startswith("GIT_CONFIG_"):
            environment.pop(name, None)
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    return environment


def _read_checksum(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ReceiptVerificationError("cannot read the root-CI checksum file") from exc
    if not raw or len(raw) > 256:
        raise ReceiptVerificationError("root-CI checksum file is empty or oversized")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ReceiptVerificationError("root-CI checksum file is not ASCII") from exc
    matched = CHECKSUM_RE.fullmatch(text)
    if matched is None:
        raise ReceiptVerificationError(
            "root-CI checksum file does not name the exact signed receipt"
        )
    return matched.group("sha256")


def _git_stdout(repo_root: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-C",
                str(repo_root),
                *arguments,
            ],
            check=True,
            capture_output=True,
            env=_sanitized_git_environment(),
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReceiptVerificationError(
            "cannot verify the security-critical Git checkout"
        ) from exc
    return result.stdout


def _git_text(repo_root: Path, *arguments: str) -> str:
    try:
        return _git_stdout(repo_root, *arguments).decode(
            "ascii", errors="strict"
        ).strip()
    except UnicodeDecodeError as exc:
        raise ReceiptVerificationError(
            "security-critical Git identity is not ASCII"
        ) from exc


def _verify_security_critical_checkout(
    repo_root: Path, expected_master_head: str
) -> None:
    replacement_refs = _git_stdout(
        repo_root,
        "for-each-ref",
        "--format=%(refname)",
        "refs/replace",
    ).strip()
    if replacement_refs:
        raise ReceiptVerificationError(
            "security-critical checkout contains forbidden replacement refs"
        )

    raw_grafts_path = _git_stdout(
        repo_root, "rev-parse", "--git-path", "info/grafts"
    ).rstrip(b"\r\n")
    try:
        grafts_path = Path(os.fsdecode(raw_grafts_path))
    except UnicodeError as exc:
        raise ReceiptVerificationError(
            "security-critical Git graft path is not decodable"
        ) from exc
    if not grafts_path.is_absolute():
        grafts_path = repo_root / grafts_path
    if os.path.lexists(grafts_path):
        raise ReceiptVerificationError(
            "security-critical checkout contains forbidden legacy grafts"
        )

    actual_head = _git_text(repo_root, "rev-parse", "HEAD")
    if actual_head != expected_master_head:
        raise ReceiptVerificationError(
            "checked-out commit does not match the expected protected master HEAD"
        )

    for repository_path in SECURITY_CRITICAL_REPOSITORY_PATHS:
        expected_blob = _git_text(
            repo_root, "rev-parse", f"{expected_master_head}:{repository_path}"
        )
        actual_blob = _git_text(
            repo_root,
            "hash-object",
            "--no-filters",
            "--",
            repository_path,
        )
        if (
            OBJECT_ID_RE.fullmatch(expected_blob) is None
            or OBJECT_ID_RE.fullmatch(actual_blob) is None
            or actual_blob != expected_blob
        ):
            raise ReceiptVerificationError(
                f"security-critical checkout file differs from HEAD: {repository_path}"
            )

    status = _git_stdout(
        repo_root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if status:
        raise ReceiptVerificationError(
            "checkout has tracked or untracked changes after repository tests"
        )


def _require_remaining_validity(
    receipt: candidate.PinnedReceipt,
    *,
    verification_time: datetime,
    minimum_remaining_seconds: int,
) -> None:
    if minimum_remaining_seconds < WORKFLOW_WINDOW_SECONDS:
        raise ReceiptVerificationError(
            "minimum remaining validity cannot be less than the 20-minute workflow window"
        )
    try:
        document = candidate._strict_document(receipt.raw, "root-CI signed receipt")
        expires = candidate._timestamp(
            document.get("expires_at_utc"), "root-CI receipt expires_at_utc"
        )
    except candidate.AssemblyError as exc:
        raise ReceiptVerificationError(str(exc)) from exc
    remaining_seconds = (expires - verification_time).total_seconds()
    if remaining_seconds <= minimum_remaining_seconds:
        raise ReceiptVerificationError(
            "root-CI receipt must remain valid for strictly more than "
            f"{minimum_remaining_seconds} seconds"
        )


def verify_pinned_root_ci_receipt(
    *,
    receipt_path: Path,
    checksum_path: Path,
    expected_receipt_sha256: str,
    expected_master_head: str,
    expected_deploy_id: str,
    repo_root: Path = REPO_ROOT,
    verification_time: datetime | None = None,
    minimum_remaining_seconds: int = WORKFLOW_WINDOW_SECONDS,
) -> candidate.PinnedReceipt:
    if candidate.SHA256_RE.fullmatch(expected_receipt_sha256) is None:
        raise ReceiptVerificationError(
            "root-CI receipt pin must be a lowercase SHA-256"
        )
    if SHA1_RE.fullmatch(expected_master_head) is None:
        raise ReceiptVerificationError("expected master HEAD must be 40 lowercase hex")
    if DEPLOY_ID_RE.fullmatch(expected_deploy_id) is None:
        raise ReceiptVerificationError("expected deploy ID is invalid")

    _verify_security_critical_checkout(repo_root, expected_master_head)

    artifact_checksum = _read_checksum(checksum_path)
    if artifact_checksum != expected_receipt_sha256:
        raise ReceiptVerificationError(
            "artifact checksum does not match the external root-CI receipt pin"
        )

    now_value = verification_time or datetime.now(timezone.utc)
    if now_value.tzinfo is None or now_value.utcoffset() is None:
        raise ReceiptVerificationError("verification time must be timezone-aware")
    now = now_value.astimezone(timezone.utc)
    try:
        pinned = candidate._load_pinned_root_receipt(
            receipt_path=receipt_path,
            expected_receipt_sha256=expected_receipt_sha256,
            expected_master_head=expected_master_head,
            expected_deploy_id=expected_deploy_id,
            verification_time=now,
            repo_root=repo_root,
        )
    except candidate.AssemblyError as exc:
        raise ReceiptVerificationError(str(exc)) from exc
    _require_remaining_validity(
        pinned,
        verification_time=now,
        minimum_remaining_seconds=minimum_remaining_seconds,
    )
    _verify_security_critical_checkout(repo_root, expected_master_head)
    return pinned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--checksum", type=Path, required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--expected-master-head", required=True)
    parser.add_argument("--expected-deploy-id", required=True)
    parser.add_argument(
        "--minimum-remaining-validity-seconds",
        type=int,
        default=WORKFLOW_WINDOW_SECONDS,
    )
    args = parser.parse_args(argv)
    try:
        verify_pinned_root_ci_receipt(
            receipt_path=args.receipt,
            checksum_path=args.checksum,
            expected_receipt_sha256=args.receipt_sha256,
            expected_master_head=args.expected_master_head,
            expected_deploy_id=args.expected_deploy_id,
            minimum_remaining_seconds=args.minimum_remaining_validity_seconds,
        )
    except ReceiptVerificationError as exc:
        print(f"root-CI receipt verification failed: {exc}", file=sys.stderr)
        return 1
    print(
        "PINNED_ROOT_CI_RECEIPT_VERIFIED: checksum, RS256 signature, freshness, "
        "protected master, and live deployment bindings are exact; acceptance "
        "remains OPEN.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
