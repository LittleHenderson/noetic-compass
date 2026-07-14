#!/usr/bin/env python3
"""Collect strict public-production hosted customer-journey evidence.

This command drives a real account-scoped customer journey against the public
API: provision two isolated tenants, grant the primary tenant a short-lived
manual-comped entitlement, authenticate, run the hosted Pythia audit, download
and verify its WORM-bound Evidence Packet, exercise an anonymous read-only
share through revocation, and prove the second tenant receives 404 for the
first tenant's audit and packet.

The output is secret-safe gate evidence. Raw account credentials, platform
secrets, billing secrets, bearer tokens, tenant identifiers, account IDs,
share IDs, and share tokens are never written or printed. This collector does
not publish acceptance authority; publication remains a separate CAS-guarded
operation.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


EVIDENCE_SCHEMA_VERSION = "cas_harness_customer_production_gate_evidence.v2"
SAFE_ARTIFACT_SCHEMA_VERSION = "cas_hosted_customer_journey_receipt.v1"
REPOSITORY = "LittleHenderson/noetic-compass"
PRODUCTION_APP_URL = "https://atlas.noeticcompass.com/audit-console"
PRODUCTION_API_ORIGIN = "https://noetic-compass-api.onrender.com"
PRODUCTION_SERVICE_ID = "srv-d82ph683kofs73d210e0"
AUTHORITY_URI = f"{PRODUCTION_API_ORIGIN}/internal/acceptance/customer-journey"
MODEL_ID = "EleutherAI/pythia-160m"
AUDIT_MODE = "BALANCED"
PLATFORM_SECRET_ENV = "NC_PLATFORM_TENANT_PROVISIONING_SECRET"
BILLING_SECRET_ENV = "NC_BILLING_ADMIN_SECRET"
MAX_RESPONSE_BYTES = 2_000_000
MIN_CONFIGURED_RETENTION_DAYS = 31
MIN_REMAINING_RETENTION = timedelta(days=30)
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DEPLOY_ID_RE = re.compile(r"^dep-[A-Za-z0-9]+$")
AUDIT_ID_RE = re.compile(r"^cas-audit-[0-9a-f]{16}$")


class JourneyFailure(RuntimeError):
    """A named customer-journey invariant failed."""

    def __init__(self, gate: str, detail: str) -> None:
        self.gate = gate
        super().__init__(f"{gate}: {detail}")


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: Mapping[str, str]
    body: bytes


Transport = Callable[..., HttpResult]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JourneyFailure("json", "response contains a duplicate JSON key")
        result[key] = value
    return result


def _decode_object(result: HttpResult, gate: str) -> Mapping[str, Any]:
    if len(result.body) > MAX_RESPONSE_BYTES:
        raise JourneyFailure(gate, "response exceeds the bounded size limit")
    try:
        value = json.loads(
            result.body.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
        )
    except JourneyFailure:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JourneyFailure(gate, "response is not valid UTF-8 JSON") from exc
    if not isinstance(value, Mapping):
        raise JourneyFailure(gate, "response JSON root is not an object")
    return value


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _subject_digest(kind: str, value: str) -> str:
    return _digest_bytes(f"{kind}:{value}".encode("utf-8"))


def _parse_timestamp(value: Any, gate: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise JourneyFailure(gate, "timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise JourneyFailure(gate, "timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise JourneyFailure(gate, "timestamp has no timezone")
    return parsed.astimezone(UTC)


def _stamp(value: datetime | Any, gate: str = "timestamp") -> str:
    parsed = value if isinstance(value, datetime) else _parse_timestamp(value, gate)
    if parsed.tzinfo is None:
        raise JourneyFailure(gate, "timestamp has no timezone")
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _required_string(value: Mapping[str, Any], key: str, gate: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise JourneyFailure(gate, f"response is missing {key}")
    return item.strip()


def _nested_mapping(value: Mapping[str, Any], *keys: str, gate: str) -> Mapping[str, Any]:
    current: Any = value
    for key in keys:
        if not isinstance(current, Mapping) or not isinstance(current.get(key), Mapping):
            raise JourneyFailure(gate, f"response is missing {'.'.join(keys)}")
        current = current[key]
    return current


def _default_transport(
    *,
    base_url: str,
    path: str,
    method: str,
    payload: Mapping[str, Any] | None,
    headers: Mapping[str, str],
    timeout: float,
) -> HttpResult:
    body = None if payload is None else _canonical_bytes(payload)
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "CAS-Harness-Customer-Journey/1.0",
        **headers,
    }
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - pinned origin
            response_body = response.read(MAX_RESPONSE_BYTES + 1)
            return HttpResult(
                status=int(response.status),
                headers={key.lower(): value for key, value in response.headers.items()},
                body=response_body,
            )
    except HTTPError as exc:
        return HttpResult(
            status=int(exc.code),
            headers={key.lower(): value for key, value in exc.headers.items()},
            body=exc.read(MAX_RESPONSE_BYTES + 1),
        )
    except (URLError, OSError, TimeoutError) as exc:
        raise JourneyFailure("network", "public API request failed") from exc


class JourneyCollector:
    def __init__(
        self,
        *,
        base_url: str,
        platform_secret: str,
        billing_secret: str,
        master_head_sha: str,
        deploy_id: str,
        transport: Transport = _default_transport,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        nonce: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.platform_secret = platform_secret
        self.billing_secret = billing_secret
        self.master_head_sha = master_head_sha
        self.deploy_id = deploy_id
        self.transport = transport
        self.clock = clock
        self.nonce = nonce or secrets.token_hex(12)
        self._active_tokens: list[str] = []
        self._validate_binding()

    def _validate_binding(self) -> None:
        parsed = urlparse(self.base_url)
        expected = urlparse(PRODUCTION_API_ORIGIN)
        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or parsed.netloc != expected.netloc
        ):
            raise JourneyFailure("binding", "API origin is not the pinned public production origin")
        if not self.platform_secret or not self.billing_secret:
            raise JourneyFailure("credentials", "required production operator credentials are unavailable")
        if SHA1_RE.fullmatch(self.master_head_sha) is None:
            raise JourneyFailure("binding", "master HEAD is invalid")
        if DEPLOY_ID_RE.fullmatch(self.deploy_id) is None:
            raise JourneyFailure("binding", "deploy ID is invalid")
        if re.fullmatch(r"[0-9a-f]{24}", self.nonce) is None:
            raise JourneyFailure("binding", "run nonce is invalid")

    def _call(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float = 60.0,
    ) -> HttpResult:
        result = self.transport(
            base_url=self.base_url,
            path=path,
            method=method,
            payload=payload,
            headers={} if headers is None else headers,
            timeout=timeout,
        )
        if len(result.body) > MAX_RESPONSE_BYTES:
            raise JourneyFailure("http", "response exceeds the bounded size limit")
        return result

    @staticmethod
    def _expect(result: HttpResult, statuses: set[int], gate: str) -> Mapping[str, Any]:
        if result.status not in statuses:
            raise JourneyFailure(gate, f"unexpected HTTP status {result.status}")
        return _decode_object(result, gate)

    def _provision(self, suffix: str) -> tuple[str, str, str, str]:
        tenant_id = f"cp-{self.nonce[:20]}-{suffix}"
        identity = f"cp-{self.nonce}-{suffix}@acceptance.invalid"
        credential = "casak_" + secrets.token_urlsafe(48)
        result = self._call(
            "/platform/tenants",
            method="POST",
            payload={
                "tenant_id": tenant_id,
                "email_or_username": identity,
                "api_credential": credential,
                "display_name": "Customer production acceptance probe",
            },
            headers={"X-Platform-Provisioning-Secret": self.platform_secret},
        )
        response = self._expect(result, {200}, f"provision-{suffix}")
        owner = response.get("owner")
        if not isinstance(owner, Mapping):
            raise JourneyFailure(f"provision-{suffix}", "owner response is missing")
        account_id = _required_string(owner, "account_id", f"provision-{suffix}")
        if owner.get("tenant_id") != tenant_id or owner.get("role") != "owner":
            raise JourneyFailure(f"provision-{suffix}", "owner binding is invalid")
        if "api_credential" in owner or credential in result.body.decode("utf-8", errors="ignore"):
            raise JourneyFailure(f"provision-{suffix}", "credential was echoed by the API")
        return tenant_id, identity, credential, account_id

    def _grant_comped(self, tenant_id: str, account_id: str) -> None:
        expires_at = self.clock() + timedelta(hours=2)
        result = self._call(
            "/platform/billing/manual-comped-subscription",
            method="POST",
            payload={
                "tenant_id": tenant_id,
                "billing_account_id": account_id,
                "expires_at": expires_at.isoformat(),
            },
            headers={"X-Billing-Admin-Secret": self.billing_secret},
        )
        response = self._expect(result, {200}, "manual-comped")
        if (
            response.get("tenant_id") != tenant_id
            or response.get("plan_id") != "professional_live"
            or response.get("status") != "active"
            or response.get("source") != "manual_comped"
        ):
            raise JourneyFailure("manual-comped", "entitlement response is invalid")
        if _parse_timestamp(response.get("expires_at"), "manual-comped") <= self.clock():
            raise JourneyFailure("manual-comped", "entitlement already expired")

    def _login(self, identity: str, credential: str, suffix: str) -> str:
        result = self._call(
            "/auth/token",
            method="POST",
            payload={"username": identity, "api_credential": credential},
        )
        response = self._expect(result, {200}, f"login-{suffix}")
        token = _required_string(response, "token", f"login-{suffix}")
        if token in result.body.decode("utf-8", errors="ignore").replace(token, "", 1):
            raise JourneyFailure(f"login-{suffix}", "token was duplicated in the response")
        self._active_tokens.append(token)
        return token

    @staticmethod
    def _auth(token: str) -> Mapping[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _assert_worm(
        self, packet: Mapping[str, Any], verification: Mapping[str, Any]
    ) -> None:
        anchor = _nested_mapping(packet, "hashes", "external_anchor", gate="worm")
        if (
            anchor.get("status") != "anchored"
            or anchor.get("mode") != "s3"
            or anchor.get("object_lock_mode") not in {"GOVERNANCE", "COMPLIANCE"}
        ):
            raise JourneyFailure("worm", "packet has no verified S3 Object Lock anchor")
        retention_days = anchor.get("retention_days")
        if (
            not isinstance(retention_days, int)
            or isinstance(retention_days, bool)
            or retention_days < MIN_CONFIGURED_RETENTION_DAYS
        ):
            raise JourneyFailure("worm", "configured Object Lock retention is too short")
        requested_at = _parse_timestamp(anchor.get("retention_requested_at"), "worm")
        retain_until = _parse_timestamp(anchor.get("object_lock_retain_until"), "worm")
        if retain_until < requested_at + timedelta(days=retention_days):
            raise JourneyFailure("worm", "Object Lock receipt is shorter than policy")
        if retain_until - self.clock() < MIN_REMAINING_RETENTION:
            raise JourneyFailure("worm", "Object Lock has less than 30 days remaining")
        if verification.get("overall") != "all_match":
            raise JourneyFailure("worm", "packet verification is not all_match")
        checks = verification.get("checks")
        if not isinstance(checks, list) or not any(
            isinstance(check, Mapping)
            and check.get("artifact") == "merged_packet_external_anchor"
            and check.get("match") is True
            for check in checks
        ):
            raise JourneyFailure("worm", "verification did not re-read the external anchor")

    def collect(self) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            return self._collect_once()
        finally:
            # A failed probe must not leave durable account sessions active. A
            # cleanup failure cannot replace the original fail-closed reason,
            # so this final boundary is deliberately best effort.
            self._logout_all(require_success=False)

    def _logout_all(self, *, require_success: bool) -> None:
        failures = 0
        while self._active_tokens:
            token = self._active_tokens.pop(0)
            try:
                result = self._call(
                    "/auth/logout", method="POST", headers=self._auth(token)
                )
                if result.status not in {200, 204}:
                    failures += 1
            except Exception:
                failures += 1
        if require_success and failures:
            raise JourneyFailure("logout", "probe sessions were not revoked")

    def _collect_once(self) -> tuple[dict[str, Any], dict[str, Any]]:
        tenant_a, identity_a, credential_a, account_a = self._provision("a")
        self._grant_comped(tenant_a, account_a)
        token_a = self._login(identity_a, credential_a, "a")
        auth_a = self._auth(token_a)

        create_result = self._call(
            "/api/cas-harness/audit/session",
            method="POST",
            payload={
                "model_id": MODEL_ID,
                "audit_mode": AUDIT_MODE,
                "prompt": f"Customer-production hosted journey {self.nonce}",
                "selected_modules": ["active_trace", "confidence_margin"],
            },
            headers=auth_a,
        )
        created = self._expect(create_result, {200, 201}, "audit-create")
        audit_id = _required_string(created, "audit_id", "audit-create")
        if AUDIT_ID_RE.fullmatch(audit_id) is None:
            raise JourneyFailure("audit-create", "audit ID is not production-shaped")

        run_result = self._call(
            f"/api/cas-harness/audit/session/{audit_id}/run",
            method="POST",
            headers=auth_a,
            timeout=600.0,
        )
        ran = self._expect(run_result, {200}, "audit-run")
        if str(ran.get("status") or "").upper() != "COMPLETE":
            raise JourneyFailure("audit-run", "audit did not complete")
        verdict = _required_string(ran, "verdict", "audit-run")
        if verdict not in {"ACCEPT", "FLAG_FOR_HUMAN_REVIEW", "SUPPRESS"}:
            raise JourneyFailure("audit-run", "audit verdict is invalid")
        if ran.get("model_id") != MODEL_ID or ran.get("audit_mode") != AUDIT_MODE:
            raise JourneyFailure("audit-run", "audit model or mode drifted")
        trace_id = _required_string(ran, "evidence_packet_trace_id", "audit-run")
        audit_completed = _stamp(ran.get("updated_at"), "audit-run")

        packet_result = self._call(f"/evidence/{trace_id}", headers=auth_a)
        packet = self._expect(packet_result, {200}, "packet-download")
        content_type = str(packet_result.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
        if content_type != "application/json" or packet.get("trace_id") != trace_id:
            raise JourneyFailure("packet-download", "packet identity or content type is invalid")
        packet_downloaded = _stamp(self.clock())
        packet_sha = _digest_bytes(packet_result.body)

        verify_result = self._call(
            f"/evidence/{trace_id}/verify",
            method="POST",
            headers=auth_a,
        )
        verification = self._expect(verify_result, {200}, "packet-verify")
        self._assert_worm(packet, verification)

        share_result = self._call(
            f"/evidence/{trace_id}/shares",
            method="POST",
            payload={"expires_at": (self.clock() + timedelta(days=1)).isoformat()},
            headers=auth_a,
        )
        share = self._expect(share_result, {201}, "share-create")
        share_id = _required_string(share, "share_id", "share-create")
        share_token = _required_string(share, "share_token", "share-create")
        expected_fetch_path = f"/evidence/shared/{share_id}"
        if share.get("trace_id") != trace_id or share.get("anonymous_fetch_path") != expected_fetch_path:
            raise JourneyFailure("share-create", "share binding is invalid")
        share_created = _stamp(share.get("created_at"), "share-create")
        share_expires = _stamp(share.get("expires_at"), "share-create")

        anonymous_result = self._call(
            expected_fetch_path,
            headers={"X-Evidence-Share-Token": share_token},
        )
        anonymous_packet = self._expect(anonymous_result, {200}, "share-fetch")
        if _canonical_bytes(anonymous_packet) != _canonical_bytes(packet):
            raise JourneyFailure("share-fetch", "anonymous packet differs from owner packet")
        share_fetched = _stamp(self.clock())

        tenant_b, identity_b, credential_b, _account_b = self._provision("b")
        token_b = self._login(identity_b, credential_b, "b")
        auth_b = self._auth(token_b)
        foreign_audit = self._call(
            f"/api/cas-harness/audit/session/{audit_id}/status", headers=auth_b
        )
        foreign_packet = self._call(f"/evidence/{trace_id}", headers=auth_b)
        if foreign_audit.status != 404 or foreign_packet.status != 404:
            raise JourneyFailure("tenant-isolation", "foreign tenant did not receive exact 404s")
        isolation_verified = _stamp(self.clock())

        revoke_result = self._call(
            f"/evidence/shares/{share_id}", method="DELETE", headers=auth_a
        )
        revoked_share = self._expect(revoke_result, {200, 204}, "share-revoke")
        revoked_at = _stamp(revoked_share.get("revoked_at"), "share-revoke")
        revoked_fetch = self._call(
            expected_fetch_path,
            headers={"X-Evidence-Share-Token": share_token},
        )
        if revoked_fetch.status not in {404, 410}:
            raise JourneyFailure("share-revoke", "revoked anonymous share remained readable")

        self._logout_all(require_success=True)
        observed_at = _stamp(self.clock())

        tenant_hash = _subject_digest("tenant", tenant_a)
        account_hash = _subject_digest("account", account_a)
        share_token_hash = _subject_digest("share-token", share_token)
        safe_artifact = {
            "schema_version": SAFE_ARTIFACT_SCHEMA_VERSION,
            "master_head_sha": self.master_head_sha,
            "deploy_id": self.deploy_id,
            "tenant_subject_sha256": tenant_hash,
            "account_subject_sha256": account_hash,
            "audit_id": audit_id,
            "trace_id_sha256": _subject_digest("trace", trace_id),
            "audit_create_http_status": create_result.status,
            "audit_run_http_status": run_result.status,
            "audit_completed_at_utc": audit_completed,
            "packet_http_status": packet_result.status,
            "packet_sha256": packet_sha,
            "packet_verification_overall": verification.get("overall"),
            "worm_receipt_bound": True,
            "share_create_http_status": share_result.status,
            "share_fetch_http_status": anonymous_result.status,
            "share_token_sha256": share_token_hash,
            "share_revoke_http_status": revoke_result.status,
            "share_revoked_fetch_http_status": revoked_fetch.status,
            "foreign_audit_http_status": foreign_audit.status,
            "foreign_packet_http_status": foreign_packet.status,
            "observed_at_utc": observed_at,
        }
        artifact_sha = _digest_bytes(_canonical_bytes(safe_artifact))
        evidence = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "gate": "hosted_customer_journey",
            "environment": "public-production",
            "repository": REPOSITORY,
            "master_head_sha": self.master_head_sha,
            "deploy_id": self.deploy_id,
            "event_at_utc": audit_completed,
            "observed_at_utc": observed_at,
            "artifact_uri": AUTHORITY_URI,
            "artifact_sha256": artifact_sha,
            "app_url": PRODUCTION_APP_URL,
            "api_base_url": PRODUCTION_API_ORIGIN,
            "service_id": PRODUCTION_SERVICE_ID,
            "customer_lane": "public-customer",
            "tenant_subject_sha256": tenant_hash,
            "account_subject_sha256": account_hash,
            "audit": {
                "audit_id": audit_id,
                "create_http_status": create_result.status,
                "terminal_status": "completed",
                "verdict": verdict,
                "model_id": MODEL_ID,
                "mode": AUDIT_MODE,
                "completed_at_utc": audit_completed,
            },
            "packet_download": {
                "audit_id": audit_id,
                "http_status": packet_result.status,
                "content_type": "application/json",
                "packet_sha256": packet_sha,
                "verification_overall": "all_match",
                "worm_receipt_bound": True,
                "downloaded_at_utc": packet_downloaded,
            },
            "share": {
                "create_http_status": share_result.status,
                "anonymous_fetch_http_status": anonymous_result.status,
                "scope": "read_only",
                "share_token_sha256": share_token_hash,
                "created_at_utc": share_created,
                "fetched_at_utc": share_fetched,
                "expires_at_utc": share_expires,
                "revoke_http_status": revoke_result.status,
                "revoked_at_utc": revoked_at,
                "revoked_fetch_http_status": revoked_fetch.status,
            },
            "tenant_isolation": {
                "foreign_audit_http_status": foreign_audit.status,
                "foreign_packet_http_status": foreign_packet.status,
                "verified_at_utc": isolation_verified,
            },
        }
        return evidence, safe_artifact


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(payload) + b"\n"
    handle = tempfile.NamedTemporaryFile(
        mode="wb", delete=False, dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temp_path = Path(handle.name)
    try:
        os.chmod(temp_path, 0o600)
        with handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=PRODUCTION_API_ORIGIN)
    parser.add_argument("--master-head", required=True)
    parser.add_argument("--deploy-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--safe-artifact-output", required=True, type=Path)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    platform_secret = os.environ.get(PLATFORM_SECRET_ENV, "")
    billing_secret = os.environ.get(BILLING_SECRET_ENV, "")
    try:
        collector = JourneyCollector(
            base_url=args.base_url,
            platform_secret=platform_secret,
            billing_secret=billing_secret,
            master_head_sha=args.master_head,
            deploy_id=args.deploy_id,
        )
        evidence, artifact = collector.collect()
        _atomic_write(args.safe_artifact_output, artifact)
        _atomic_write(args.output, evidence)
        print(
            json.dumps(
                {
                    "artifact_sha256": evidence["artifact_sha256"],
                    "audit_id": evidence["audit"]["audit_id"],
                    "evidence_sha256": _digest_bytes(_canonical_bytes(evidence)),
                    "gate": "hosted_customer_journey",
                    "status": "present",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    except JourneyFailure as exc:
        print(
            json.dumps(
                {"gate": exc.gate, "status": "OPEN", "error": str(exc)},
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
