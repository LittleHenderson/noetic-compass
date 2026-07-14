#!/usr/bin/env python3
"""Sign one collected root-CI payload without changing any acceptance gate.

The private key is accepted only through ``CUSTOMER_PRODUCTION_SIGNING_KEY_PEM``.
The script verifies that the matching public key and exact subject grant are
already pinned in the checked-out trusted-issuer registry, validates the v2
payload with the production verifier, and emits one RS256 receipt.  It never
edits a manifest or dispatches the final acceptance workflow.
"""

from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

import collect_root_ci_protected_deploy_facts as collector
import verify_customer_production_acceptance as acceptance


try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
except ImportError:  # pragma: no cover - exercised by the workflow dependency check
    hashes = serialization = padding = rsa = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[1]
ISSUER = "github-customer-production"
KEY_ID = "gh-env-2026-07-14-01"
SUBJECT_URI = (
    f"{acceptance.REPOSITORY_URL}/releases/download/"
    "customer-production-evidence/root-ci-protected-deploy.json"
)
PRIVATE_KEY_ENV = "CUSTOMER_PRODUCTION_SIGNING_KEY_PEM"
DEFAULT_EXPIRY_MINUTES = 120


class SigningError(RuntimeError):
    """The draft, issuer authority, or private key failed closed."""


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _canonical_subject_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _utc_seconds(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _payload_time(value: Any, label: str) -> datetime:
    errors: list[str] = []
    parsed = acceptance._timestamp(value, label, errors)
    if parsed is None:
        raise SigningError(errors[0] if errors else f"{label} is invalid")
    return parsed


def _load_private_key(private_key_pem: str):
    if serialization is None or rsa is None:
        raise SigningError("cryptography is required for receipt signing")
    if not private_key_pem.strip():
        raise SigningError(f"{PRIVATE_KEY_ENV} is required")
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"), password=None
        )
    except (TypeError, ValueError) as exc:
        raise SigningError("the signing key is not a valid unencrypted PEM key") from exc
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise SigningError("the signing key must be RSA")
    public_numbers = private_key.public_key().public_numbers()
    if private_key.key_size < 2048 or public_numbers.e != 65537:
        raise SigningError("the signing key must be RSA-2048+ with exponent 65537")
    return private_key


def sign_root_ci_protected_deploy_receipt(
    *,
    payload: Mapping[str, Any],
    subject_bytes: bytes,
    expected_master_head: str,
    expected_deploy_id: str,
    private_key_pem: str,
    trusted_issuers: Mapping[tuple[str, str], Mapping[str, Any]],
    now: datetime | None = None,
    expiry_minutes: int = DEFAULT_EXPIRY_MINUTES,
    issuer: str = ISSUER,
    key_id: str = KEY_ID,
) -> dict[str, Any]:
    if not 1 <= expiry_minutes <= 1440:
        raise SigningError("receipt expiry must be between 1 and 1440 minutes")
    try:
        subject_payload = collector._strict_json(subject_bytes, "release subject")
    except collector.CollectorError as exc:
        raise SigningError("release subject is not strict JSON") from exc
    if dict(subject_payload) != dict(payload):
        raise SigningError("release subject does not match the draft payload")
    if subject_bytes != _canonical_subject_bytes(payload):
        raise SigningError("release subject is not the canonical collector encoding")
    issued = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(
        microsecond=0
    )
    context = acceptance.ValidationContext(
        repo_root=REPO_ROOT,
        evidence_root=REPO_ROOT,
        verification_time=issued,
        generated_at=issued,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
        repository_commit=expected_master_head,
        live=False,
        trusted_issuers=dict(trusted_issuers),
        registry_sha256="0" * 64,
    )
    acceptance._validate_root_ci(payload, context)
    if context.errors:
        raise SigningError(
            "root-CI source payload failed production validation: "
            + "; ".join(context.errors)
        )

    evidence = deepcopy(dict(payload))
    subject_sha256 = hashlib.sha256(subject_bytes).hexdigest()
    evidence["artifact_uri"] = SUBJECT_URI
    evidence["artifact_sha256"] = subject_sha256
    context.errors.clear()
    acceptance._validate_root_ci(evidence, context)
    if context.errors:
        raise SigningError(
            "root-CI v2 payload failed production validation: "
            + "; ".join(context.errors)
        )
    observed = _payload_time(evidence.get("observed_at_utc"), "observed_at_utc")
    if issued < observed:
        raise SigningError("receipt issuance cannot precede evidence observation")

    identity = (issuer, key_id)
    authority = trusted_issuers.get(identity)
    if authority is None:
        raise SigningError("issuer/key_id is not pinned in the trusted registry")
    if ("root_ci_protected_deploy", SUBJECT_URI) not in authority.get(
        "allowed_subjects", frozenset()
    ):
        raise SigningError("issuer lacks the exact root-CI subject grant")
    valid_from = authority.get("valid_from")
    valid_until = authority.get("valid_until")
    if not isinstance(valid_from, datetime) or not isinstance(valid_until, datetime):
        raise SigningError("issuer validity bounds are unavailable")
    expires = issued + timedelta(minutes=expiry_minutes)
    if not valid_from <= issued <= valid_until or expires > valid_until:
        raise SigningError("receipt time is outside the issuer validity window")

    private_key = _load_private_key(private_key_pem)
    public_numbers = private_key.public_key().public_numbers()
    if public_numbers.n != authority.get("n") or public_numbers.e != authority.get("e"):
        raise SigningError("private key does not match the pinned issuer public key")

    unsigned: dict[str, Any] = {
        "schema_version": acceptance.RECEIPT_SCHEMA_VERSION,
        "issuer": issuer,
        "key_id": key_id,
        "gate": "root_ci_protected_deploy",
        "environment": "public-production",
        "repository": acceptance.REPOSITORY,
        "master_head_sha": expected_master_head,
        "deploy_id": expected_deploy_id,
        "issued_at_utc": _utc_seconds(issued),
        "expires_at_utc": _utc_seconds(expires),
        "subject_uri": SUBJECT_URI,
        "subject_sha256": subject_sha256,
        "evidence": evidence,
    }
    assert hashes is not None and padding is not None
    signature = private_key.sign(
        _canonical_bytes(unsigned), padding.PKCS1v15(), hashes.SHA256()
    )
    receipt = dict(unsigned)
    receipt["signature_base64url"] = base64.urlsafe_b64encode(signature).decode(
        "ascii"
    ).rstrip("=")
    if not acceptance._rsa_verify_rs256(
        _canonical_bytes(unsigned),
        receipt["signature_base64url"],
        public_numbers.n,
        public_numbers.e,
    ):
        raise SigningError("receipt signature self-verification failed")
    rendered = json.dumps(receipt, sort_keys=True)
    if private_key_pem.strip() in rendered:
        raise SigningError("refusing output that contains private key material")
    return receipt


def _read_bounded(path: Path, label: str) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SigningError(f"cannot read {label}") from exc
    if not raw or len(raw) > acceptance.MAX_EVIDENCE_BYTES:
        raise SigningError(f"{label} is empty or exceeds the size limit")
    return raw


def _write_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path = path.resolve()
    if not path.parent.is_dir():
        raise SigningError("receipt output parent does not exist")
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
    except FileExistsError as exc:
        raise SigningError("refusing to overwrite an existing receipt") from exc
    except OSError as exc:
        raise SigningError("cannot write the receipt") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--subject-file", type=Path, required=True)
    parser.add_argument("--expected-master-head", required=True)
    parser.add_argument("--expected-deploy-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--expiry-minutes", type=int, default=DEFAULT_EXPIRY_MINUTES
    )
    args = parser.parse_args(argv)
    try:
        payload_raw = _read_bounded(args.payload, "draft payload")
        payload = collector._strict_json(payload_raw, "draft payload")
        subject_bytes = _read_bounded(args.subject_file, "release subject")
        trusted_issuers, _ = acceptance._load_trusted_issuer_registry(REPO_ROOT)
        receipt = sign_root_ci_protected_deploy_receipt(
            payload=payload,
            subject_bytes=subject_bytes,
            expected_master_head=args.expected_master_head,
            expected_deploy_id=args.expected_deploy_id,
            private_key_pem=os.environ.get(PRIVATE_KEY_ENV, ""),
            trusted_issuers=trusted_issuers,
            expiry_minutes=args.expiry_minutes,
        )
        _write_exclusive(args.output, receipt)
    except (SigningError, acceptance.ManifestLoadError, collector.CollectorError) as exc:
        print(f"root-CI receipt signing failed: {exc}", file=sys.stderr)
        return 1
    print(
        "SIGNED_RECEIPT_CREATED: root_ci_protected_deploy only; "
        "the manifest remains OPEN and final ACCEPT was not dispatched.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
