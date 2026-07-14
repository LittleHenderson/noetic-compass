"""Validate and publish one customer-production authority document.

The public acceptance routes are intentionally read-only.  This command is the
authenticated operational write path: it runs inside the production service
environment, connects directly to the configured shared Postgres StateStore,
and uses the same fail-closed validator and compare-and-swap head update as the
serving API.

It never collects evidence, creates approvals, signs receipts, or changes the
customer-production manifest.  Operators must supply independently collected
evidence and pin every mutable identity on the command line.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, TextIO

# Render Shell operators may invoke this copied script by absolute path instead
# of as a module.  In that mode Python only adds ``/app/scripts`` to sys.path,
# so explicitly add the trusted application root before importing ``api``.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.acceptance_authority_contract import (
    ACCEPTANCE_AUTHORITY_PATH_BY_GATE,
    PRODUCTION_API_ORIGIN,
)
from api.services.customer_production_acceptance_authority import (
    MAX_EVIDENCE_BYTES,
    PRODUCTION_SERVICE_NAME,
    PRODUCTION_SERVICE_ID,
    REPOSITORY,
    AcceptanceAuthorityConflict,
    AcceptanceAuthorityInvalid,
    AcceptanceAuthorityNotFound,
    AcceptanceAuthorityUnavailable,
    CustomerProductionAcceptanceAuthorityStore,
    canonicalize_acceptance_evidence,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_DEPLOY_ID_RE = re.compile(r"^dep-[A-Za-z0-9]+$")
_POSTGRES_SCHEMES = ("postgres://", "postgresql://", "postgresql+asyncpg://")


class PublisherInputError(ValueError):
    """Safe operator-facing input or production-binding error."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


class PublicationReadbackError(RuntimeError):
    """A mutation may have committed, but exact post-write state is unknown."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PublisherInputError(
                "duplicate_json_key", "evidence JSON contains a duplicate key"
            )
        result[key] = value
    return result


def _read_evidence(path: Path) -> Mapping[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PublisherInputError(
            "evidence_unreadable", "evidence file could not be read"
        ) from exc
    if len(raw) > MAX_EVIDENCE_BYTES:
        raise PublisherInputError(
            "evidence_too_large", "evidence file exceeds the authority size limit"
        )
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except PublisherInputError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublisherInputError(
            "evidence_invalid_json", "evidence file is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(value, Mapping):
        raise PublisherInputError(
            "evidence_root_invalid", "evidence JSON root must be an object"
        )
    return value


def _prepare_evidence(
    *,
    gate: str,
    evidence_path: Path,
    expected_master_head: str,
    expected_deploy_id: str,
    expected_evidence_sha256: str | None,
    now: datetime | None,
) -> tuple[Mapping[str, Any], bytes, str]:
    if _SHA1_RE.fullmatch(expected_master_head) is None:
        raise PublisherInputError(
            "expected_master_head_invalid",
            "expected master head must be a lowercase 40-character commit SHA",
        )
    if _DEPLOY_ID_RE.fullmatch(expected_deploy_id) is None:
        raise PublisherInputError(
            "expected_deploy_id_invalid", "expected deploy ID is invalid"
        )
    if expected_evidence_sha256 is not None and (
        _SHA256_RE.fullmatch(expected_evidence_sha256) is None
    ):
        raise PublisherInputError(
            "expected_evidence_sha256_invalid",
            "expected evidence SHA-256 must be 64 lowercase hexadecimal characters",
        )

    evidence = _read_evidence(evidence_path)
    if evidence.get("master_head_sha") != expected_master_head:
        raise PublisherInputError(
            "master_head_mismatch",
            "evidence master head does not match the pinned command value",
        )
    if evidence.get("deploy_id") != expected_deploy_id:
        raise PublisherInputError(
            "deploy_id_mismatch",
            "evidence deploy ID does not match the pinned command value",
        )

    canonical = canonicalize_acceptance_evidence(gate, evidence, now=now)
    digest = hashlib.sha256(canonical).hexdigest()
    if expected_evidence_sha256 is not None and digest != expected_evidence_sha256:
        raise PublisherInputError(
            "evidence_sha256_mismatch",
            "canonical evidence SHA-256 does not match the pinned command value",
        )
    return evidence, canonical, digest


def _assert_production_binding(
    settings: Any,
    *,
    expected_master_head: str,
    environ: Mapping[str, str],
) -> None:
    if bool(getattr(settings, "debug", True)):
        raise PublisherInputError(
            "debug_runtime_forbidden", "publication requires a non-debug runtime"
        )
    if not bool(getattr(settings, "state_ledger_enabled", False)):
        raise PublisherInputError(
            "state_ledger_disabled",
            "publication requires the production shared state ledger",
        )
    database_url = str(getattr(settings, "database_url", "") or "")
    if not database_url.startswith(_POSTGRES_SCHEMES):
        raise PublisherInputError(
            "shared_postgres_required",
            "publication requires the configured shared Postgres StateStore",
        )
    if environ.get("RENDER_SERVICE_ID") != PRODUCTION_SERVICE_ID:
        raise PublisherInputError(
            "render_service_mismatch",
            "runtime is not the pinned public production API service",
        )
    if environ.get("RENDER_GIT_COMMIT") != expected_master_head:
        raise PublisherInputError(
            "runtime_commit_mismatch",
            "runtime commit does not match the pinned protected master head",
        )
    expected_runtime = {
        "RENDER": "true",
        "IS_PULL_REQUEST": "false",
        "RENDER_GIT_BRANCH": "master",
        "RENDER_GIT_REPO_SLUG": REPOSITORY,
        "RENDER_SERVICE_NAME": PRODUCTION_SERVICE_NAME,
        "RENDER_SERVICE_TYPE": "web",
        "RENDER_EXTERNAL_URL": PRODUCTION_API_ORIGIN,
    }
    for key, expected in expected_runtime.items():
        if environ.get(key) != expected:
            raise PublisherInputError(
                "render_runtime_identity_mismatch",
                "runtime identity does not match the pinned public production service",
            )


@contextmanager
def _production_authority(
    *,
    expected_master_head: str,
    environ: Mapping[str, str],
    include_immutable_backend: bool = False,
) -> Iterator[CustomerProductionAcceptanceAuthorityStore]:
    # Imports stay inside the production-only path so ``validate`` never opens a
    # database connection or initializes an object-store client.
    from api.config import Settings
    from api.state_ledger_bootstrap import _build_state_store

    settings = Settings()
    _assert_production_binding(
        settings,
        expected_master_head=expected_master_head,
        environ=environ,
    )
    if include_immutable_backend and settings.evidence_packet_object_store_enabled:
        settings.validate_object_lock_receipt_attestation()

    state_store = None
    try:
        state_store = _build_state_store(settings)
        immutable_repository = None
        if include_immutable_backend and settings.evidence_packet_object_store_enabled:
            from api.services.cas_harness_evidence_object_store import (
                build_s3_evidence_packet_repository,
            )

            immutable_repository = build_s3_evidence_packet_repository(state_store)
        yield CustomerProductionAcceptanceAuthorityStore(
            state_store,
            immutable_backend=(
                immutable_repository.backend
                if immutable_repository is not None
                else None
            ),
            retention_policy=(
                immutable_repository.policy
                if immutable_repository is not None
                else None
            ),
        )
    finally:
        if state_store is not None:
            try:
                state_store.close()
            except Exception:
                # A close failure after an exact readback cannot undo the
                # committed CAS write. Never mask the verified operation or
                # print a driver exception that might contain a DSN.
                pass


def _emit(stream: TextIO, payload: Mapping[str, Any]) -> None:
    stream.write(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    gates = sorted(ACCEPTANCE_AUTHORITY_PATH_BY_GATE)

    validate = subparsers.add_parser(
        "validate", help="validate and hash evidence without opening production state"
    )
    validate.add_argument("--gate", required=True, choices=gates)
    validate.add_argument("--evidence", required=True, type=Path)
    validate.add_argument("--expected-master-head", required=True)
    validate.add_argument("--expected-deploy-id", required=True)
    validate.add_argument("--expected-evidence-sha256")

    head = subparsers.add_parser(
        "head", help="read the current version of one production authority head"
    )
    head.add_argument("--gate", required=True, choices=gates)
    head.add_argument("--expected-master-head", required=True)

    publish = subparsers.add_parser(
        "publish", help="CAS-publish canonical evidence and verify exact readback"
    )
    publish.add_argument("--gate", required=True, choices=gates)
    publish.add_argument("--evidence", required=True, type=Path)
    publish.add_argument("--expected-master-head", required=True)
    publish.add_argument("--expected-deploy-id", required=True)
    publish.add_argument("--expected-evidence-sha256", required=True)
    publish.add_argument("--expected-head-version", required=True, type=int)
    publish.add_argument("--authorization-artifact-uri", required=True)
    publish.add_argument("--authorization-artifact-sha256", required=True)
    publish.add_argument("--operation-reason", required=True)
    publish.add_argument(
        "--expected-previous-evidence-sha256",
        help="required when expected-head-version is greater than zero",
    )

    deactivate = subparsers.add_parser(
        "deactivate",
        help="CAS-tombstone one active authority head and verify it serves 404",
    )
    deactivate.add_argument("--gate", required=True, choices=gates)
    deactivate.add_argument("--expected-master-head", required=True)
    deactivate.add_argument("--expected-evidence-sha256", required=True)
    deactivate.add_argument("--expected-head-version", required=True, type=int)
    deactivate.add_argument("--authorization-artifact-uri", required=True)
    deactivate.add_argument("--authorization-artifact-sha256", required=True)
    deactivate.add_argument("--operation-reason", required=True)
    return parser


def run(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    now: datetime | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    args = _build_parser().parse_args(argv)
    runtime_environ = os.environ if environ is None else environ

    try:
        if args.command == "validate":
            _, _, digest = _prepare_evidence(
                gate=args.gate,
                evidence_path=args.evidence,
                expected_master_head=args.expected_master_head,
                expected_deploy_id=args.expected_deploy_id,
                expected_evidence_sha256=args.expected_evidence_sha256,
                now=now,
            )
            _emit(
                stdout,
                {
                    "evidence_sha256": digest,
                    "gate": args.gate,
                    "status": "valid",
                },
            )
            return 0

        if args.command == "head":
            if _SHA1_RE.fullmatch(args.expected_master_head) is None:
                raise PublisherInputError(
                    "expected_master_head_invalid",
                    "expected master head must be a lowercase 40-character commit SHA",
                )
            with _production_authority(
                expected_master_head=args.expected_master_head,
                environ=runtime_environ,
            ) as authority:
                current = authority.current_head(args.gate)
            _emit(
                stdout,
                {
                    "active": False if current is None else current.active,
                    "evidence_sha256": None if current is None else current.sha256,
                    "gate": args.gate,
                    "head_version": 0 if current is None else current.head_version,
                    "operation_record_id": (
                        None if current is None else current.operation_record_id
                    ),
                    "operation_sha256": (
                        None if current is None else current.operation_sha256
                    ),
                    "status": "observed",
                },
            )
            return 0

        if args.command == "deactivate":
            if _SHA1_RE.fullmatch(args.expected_master_head) is None:
                raise PublisherInputError(
                    "expected_master_head_invalid",
                    "expected master head must be a lowercase 40-character commit SHA",
                )
            if args.expected_head_version <= 0:
                raise PublisherInputError(
                    "expected_head_version_invalid",
                    "deactivation requires a positive expected head version",
                )
            if _SHA256_RE.fullmatch(args.expected_evidence_sha256) is None:
                raise PublisherInputError(
                    "expected_evidence_sha256_invalid",
                    "expected evidence SHA-256 must be 64 lowercase hexadecimal characters",
                )
            with _production_authority(
                expected_master_head=args.expected_master_head,
                environ=runtime_environ,
            ) as authority:
                try:
                    deactivated = authority.deactivate(
                        args.gate,
                    expected_head_version=args.expected_head_version,
                    expected_evidence_sha256=args.expected_evidence_sha256,
                    authorization_artifact_uri=args.authorization_artifact_uri,
                    authorization_artifact_sha256=(
                        args.authorization_artifact_sha256
                    ),
                    operation_reason=args.operation_reason,
                    now=now,
                    )
                except AcceptanceAuthorityUnavailable as exc:
                    # The database may have committed immediately before the
                    # connection failed, so mutation state is not knowable
                    # without an independent head read.
                    raise PublicationReadbackError from exc
                try:
                    observed = authority.current_head(args.gate)
                    if (
                        observed is None
                        or observed.active
                        or observed.sha256 != deactivated.sha256
                        or observed.head_version != deactivated.head_version
                        or observed.operation_record_id
                        != deactivated.operation_record_id
                        or observed.operation_sha256
                        != deactivated.operation_sha256
                    ):
                        raise PublicationReadbackError
                    try:
                        authority.load(args.gate, now=now)
                    except AcceptanceAuthorityNotFound:
                        pass
                    else:
                        raise PublicationReadbackError
                except (AcceptanceAuthorityInvalid, AcceptanceAuthorityUnavailable) as exc:
                    raise PublicationReadbackError from exc
            _emit(
                stdout,
                {
                    "already_inactive": deactivated.already_inactive,
                    "evidence_sha256": deactivated.sha256,
                    "gate": deactivated.gate,
                    "head_version": deactivated.head_version,
                    "operation_record_id": deactivated.operation_record_id,
                    "operation_sha256": deactivated.operation_sha256,
                    "readback_verified": True,
                    "status": "inactive",
                },
            )
            return 0

        if args.expected_head_version < 0:
            raise PublisherInputError(
                "expected_head_version_invalid",
                "expected head version must be a non-negative integer",
            )
        previous_sha = args.expected_previous_evidence_sha256
        if args.expected_head_version == 0:
            if previous_sha is not None:
                raise PublisherInputError(
                    "expected_previous_evidence_sha256_unexpected",
                    "previous evidence SHA-256 must be omitted for an absent head",
                )
        elif previous_sha is None or _SHA256_RE.fullmatch(previous_sha) is None:
            raise PublisherInputError(
                "expected_previous_evidence_sha256_required",
                "a valid previous evidence SHA-256 is required for an existing head",
            )
        evidence, canonical, digest = _prepare_evidence(
            gate=args.gate,
            evidence_path=args.evidence,
            expected_master_head=args.expected_master_head,
            expected_deploy_id=args.expected_deploy_id,
            expected_evidence_sha256=args.expected_evidence_sha256,
            now=now,
        )
        with _production_authority(
            expected_master_head=args.expected_master_head,
            environ=runtime_environ,
            include_immutable_backend=True,
        ) as authority:
            try:
                published = authority.publish(
                    args.gate,
                    evidence,
                    expected_head_version=args.expected_head_version,
                    expected_previous_sha256=previous_sha,
                    authorization_artifact_uri=args.authorization_artifact_uri,
                    authorization_artifact_sha256=(
                        args.authorization_artifact_sha256
                    ),
                    operation_reason=args.operation_reason,
                    now=now,
                )
            except AcceptanceAuthorityUnavailable as exc:
                # A failed return does not prove the transaction rolled back.
                raise PublicationReadbackError from exc
            try:
                loaded = authority.load(args.gate, now=now)
                observed = authority.current_head(args.gate)
            except (
                AcceptanceAuthorityInvalid,
                AcceptanceAuthorityNotFound,
                AcceptanceAuthorityUnavailable,
            ) as exc:
                raise PublicationReadbackError from exc
            if (
                loaded.sha256 != digest
                or loaded.body != canonical
                or observed is None
                or not observed.active
                or observed.head_version != published.head_version
                or observed.operation_record_id != published.operation_record_id
                or observed.operation_sha256 != published.operation_sha256
            ):
                raise PublicationReadbackError
        _emit(
            stdout,
            {
                "evidence_sha256": published.sha256,
                "gate": published.gate,
                "head_version": published.head_version,
                "operation_record_id": published.operation_record_id,
                "operation_sha256": published.operation_sha256,
                "readback_verified": True,
                "status": "published",
                "storage_mode": published.storage_mode,
            },
        )
        return 0
    except PublicationReadbackError:
        _emit(
            stderr,
            {
                "code": "mutation_readback_failed",
                "detail": "mutation may have committed; recover by reading the exact head",
                "publication_state": "unknown",
                "status": "error",
            },
        )
        return 4
    except PublisherInputError as exc:
        _emit(
            stderr,
            {"code": exc.code, "detail": str(exc), "status": "error"},
        )
        return 2
    except AcceptanceAuthorityInvalid as exc:
        _emit(
            stderr,
            {"code": "evidence_invalid", "detail": str(exc), "status": "error"},
        )
        return 2
    except AcceptanceAuthorityConflict:
        _emit(
            stderr,
            {
                "code": "head_version_conflict",
                "detail": "authority head changed; re-read before the operation",
                "status": "error",
            },
        )
        return 3
    except AcceptanceAuthorityUnavailable:
        _emit(
            stderr,
            {
                "code": "authority_unavailable",
                "detail": "authority persistence or readback is unavailable",
                "status": "error",
            },
        )
        return 4
    except Exception as exc:  # pragma: no cover - final secret-safe boundary
        _emit(
            stderr,
            {
                "code": "unexpected_failure",
                "error_type": type(exc).__name__,
                "status": "error",
            },
        )
        return 5


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
