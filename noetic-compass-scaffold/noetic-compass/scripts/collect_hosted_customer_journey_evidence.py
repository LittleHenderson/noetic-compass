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
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


EVIDENCE_SCHEMA_VERSION = "cas_harness_customer_production_gate_evidence.v2"
SAFE_ARTIFACT_SCHEMA_VERSION = "cas_hosted_customer_journey_receipt.v3"
REPOSITORY = "LittleHenderson/noetic-compass"
PRODUCTION_APP_URL = "https://atlas.noeticcompass.com/audit-console"
PRODUCTION_API_ORIGIN = "https://cas-harness-customer-api.onrender.com"
PRODUCTION_SERVICE_ID = "srv-d9bijbjtqb8s73cn4n20"
RENDER_API_ORIGIN = "https://api.render.com"
AUTHORITY_URI = f"{PRODUCTION_API_ORIGIN}/internal/acceptance/customer-journey"
MODEL_ID = "EleutherAI/pythia-160m"
AUDIT_MODE = "BALANCED"
PLATFORM_SECRET_ENV = "NC_PLATFORM_TENANT_PROVISIONING_SECRET"
BILLING_SECRET_ENV = "NC_BILLING_ADMIN_SECRET"
RENDER_API_KEY_ENV = "RENDER_API_KEY"
MAX_RESPONSE_BYTES = 2_000_000
MIN_CONFIGURED_RETENTION_DAYS = 31
MIN_REMAINING_RETENTION = timedelta(days=30)
SHARE_LIFETIME = timedelta(minutes=15)
OBJECT_LOCK_VERIFICATION_SCHEMA = "cas_harness_object_lock_verification.v1"
OBJECT_LOCK_RETAIN_UNTIL_RULE = "observed_not_before_requested"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DEPLOY_ID_RE = re.compile(r"^dep-[A-Za-z0-9]+$")
AUDIT_ID_RE = re.compile(r"^cas-audit-[0-9a-f]{16}$")
TRACE_ID_RE = re.compile(r"^cas-live-[0-9a-f]{16}-[0-9a-f]{12}$")
SHARE_ID_RE = re.compile(r"^shr_[A-Za-z0-9_-]{20,64}$")
SHARE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{40,128}$")
ACCOUNT_ID_RE = re.compile(r"^acct-[0-9a-f]{32}$")
PROVISIONING_ID_RE = re.compile(r"^tenantprov-[0-9a-f]{32}$")
PROVISIONING_RECEIPT_ID_RE = re.compile(r"^tenantprovrct-[0-9a-f]{32}$")


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


def _reject_nonfinite_json(value: str) -> Any:
    raise JourneyFailure("json", f"response contains forbidden non-finite number {value}")


def _decode_object(result: HttpResult, gate: str) -> Mapping[str, Any]:
    if len(result.body) > MAX_RESPONSE_BYTES:
        raise JourneyFailure(gate, "response exceeds the bounded size limit")
    try:
        value = json.loads(
            result.body.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite_json,
        )
    except JourneyFailure:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise JourneyFailure(gate, "response is not valid UTF-8 JSON") from exc
    if not isinstance(value, Mapping):
        raise JourneyFailure(gate, "response JSON root is not an object")
    return value


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
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


class _NoRedirect(HTTPRedirectHandler):
    """Never forward bearer or operator headers to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


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
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310 - pinned origin
            final = urlparse(str(response.geturl()))
            expected = urlparse(base_url)
            if (
                final.scheme != "https"
                or final.username is not None
                or final.password is not None
                or final.netloc != expected.netloc
            ):
                raise JourneyFailure("redirect", "response origin drifted from production")
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
        runtime_environment: Mapping[str, str] = os.environ,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.platform_secret = platform_secret
        self.billing_secret = billing_secret
        self.master_head_sha = master_head_sha
        self.deploy_id = deploy_id
        self.transport = transport
        self.clock = clock
        self.nonce = nonce or secrets.token_hex(12)
        self.runtime_environment = runtime_environment
        render_api_key = self.runtime_environment.get(RENDER_API_KEY_ENV)
        self.render_api_key = (
            render_api_key if isinstance(render_api_key, str) else ""
        )
        self._active_tokens: list[str] = []
        self._active_shares: list[tuple[str, str]] = []
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
        if (
            not self.render_api_key
            or self.render_api_key != self.render_api_key.strip()
            or len(self.render_api_key) > 8192
            or any(character.isspace() for character in self.render_api_key)
        ):
            raise JourneyFailure(
                "render-deploy",
                "RENDER_API_KEY is required for exact live deploy proof",
            )
        if self.runtime_environment.get("RENDER_SERVICE_ID") != PRODUCTION_SERVICE_ID:
            raise JourneyFailure(
                "binding", "collector is not running in the pinned production service"
            )
        if self.runtime_environment.get("RENDER_GIT_COMMIT") != self.master_head_sha:
            raise JourneyFailure(
                "binding", "runtime commit does not match the supplied master HEAD"
            )
        self._now()

    def _now(self) -> datetime:
        value = self.clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise JourneyFailure("clock", "collector clock is not timezone aware")
        return value.astimezone(UTC)

    def _call(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float = 60.0,
    ) -> HttpResult:
        parsed_path = urlparse(path)
        if (
            not path.startswith("/")
            or path.startswith("//")
            or parsed_path.scheme
            or parsed_path.netloc
            or parsed_path.query
            or parsed_path.fragment
            or "\\" in path
        ):
            raise JourneyFailure("binding", "request path is not a query-free relative path")
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

    def _read_render_deploy(
        self,
    ) -> tuple[HttpResult, Mapping[str, Any], datetime, datetime, str]:
        """Read and validate the caller-selected immutable Render deployment."""

        result = self.transport(
            base_url=RENDER_API_ORIGIN,
            path=f"/v1/services/{PRODUCTION_SERVICE_ID}/deploys/{self.deploy_id}",
            method="GET",
            payload=None,
            headers={"Authorization": f"Bearer {self.render_api_key}"},
            timeout=30.0,
        )
        deploy = self._expect(result, {200}, "render-deploy")
        commit = deploy.get("commit")
        if (
            deploy.get("id") != self.deploy_id
            or deploy.get("status") != "live"
            or deploy.get("trigger") != "new_commit"
            or not isinstance(commit, Mapping)
            or commit.get("id") != self.master_head_sha
        ):
            raise JourneyFailure(
                "render-deploy",
                "exact deployment is not live at the pinned commit and trigger",
            )
        created = _parse_timestamp(deploy.get("createdAt"), "render-deploy")
        finished = _parse_timestamp(deploy.get("finishedAt"), "render-deploy")
        observed = self._now()
        if finished < created:
            raise JourneyFailure(
                "render-deploy", "deployment finished before it was created"
            )
        if finished > observed:
            raise JourneyFailure(
                "render-deploy", "deployment finish time is in the future"
            )
        deploy_sha = _digest_bytes(_canonical_bytes(deploy))
        return result, deploy, created, finished, deploy_sha

    def _call_retry_safe(self, path: str, **kwargs: Any) -> HttpResult:
        """Retry once only for operations whose server contract is idempotent.

        Login and share creation deliberately do not use this helper: each can
        mint a new bearer capability when its first response is ambiguous.
        """

        for attempt in range(2):
            try:
                result = self._call(path, **kwargs)
            except JourneyFailure as exc:
                if exc.gate != "network" or attempt:
                    raise
                continue
            if result.status < 500 or attempt:
                return result
        raise JourneyFailure("network", "idempotent request could not be reconciled")

    @staticmethod
    def _expect(result: HttpResult, statuses: set[int], gate: str) -> Mapping[str, Any]:
        if result.status not in statuses:
            raise JourneyFailure(gate, f"unexpected HTTP status {result.status}")
        content_type = (
            str(result.headers.get("content-type") or "")
            .split(";", 1)[0]
            .strip()
            .lower()
        )
        if content_type != "application/json":
            raise JourneyFailure(gate, "response content type is not application/json")
        return _decode_object(result, gate)

    def _provision(self, suffix: str) -> tuple[str, str, str, str]:
        tenant_id = f"cp-{self.nonce[:20]}-{suffix}"
        identity = f"cp-{self.nonce}-{suffix}@acceptance.invalid"
        credential = "casak_" + secrets.token_urlsafe(48)
        result = self._call_retry_safe(
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
        provisioning_id = _required_string(
            response, "provisioning_id", f"provision-{suffix}"
        )
        receipt_id = _required_string(response, "receipt_id", f"provision-{suffix}")
        completed_at = _parse_timestamp(
            response.get("completed_at"), f"provision-{suffix}"
        )
        if (
            ACCOUNT_ID_RE.fullmatch(account_id) is None
            or PROVISIONING_ID_RE.fullmatch(provisioning_id) is None
            or PROVISIONING_RECEIPT_ID_RE.fullmatch(receipt_id) is None
            or completed_at > self._now()
        ):
            raise JourneyFailure(f"provision-{suffix}", "provisioning receipt is invalid")
        if (
            owner.get("tenant_id") != tenant_id
            or owner.get("email_or_username") != identity
            or owner.get("role") != "owner"
            or owner.get("status") != "active"
        ):
            raise JourneyFailure(f"provision-{suffix}", "owner binding is invalid")
        if "api_credential" in owner or credential in result.body.decode("utf-8", errors="ignore"):
            raise JourneyFailure(f"provision-{suffix}", "credential was echoed by the API")
        return tenant_id, identity, credential, account_id

    def _grant_comped(self, tenant_id: str, account_id: str) -> None:
        expires_at = self._now() + timedelta(hours=2)
        result = self._call_retry_safe(
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
            or response.get("plan_id") != "beta_comped"
            or response.get("status") != "active"
            or response.get("source") != "manual_comped"
        ):
            raise JourneyFailure("manual-comped", "entitlement response is invalid")
        response_expiry = _parse_timestamp(response.get("expires_at"), "manual-comped")
        if response_expiry != expires_at or response_expiry <= self._now():
            raise JourneyFailure("manual-comped", "entitlement already expired")

    def _login(self, identity: str, credential: str, suffix: str) -> str:
        result = self._call(
            "/auth/token",
            method="POST",
            payload={"username": identity, "api_credential": credential},
        )
        response = self._expect(result, {200}, f"login-{suffix}")
        token = _required_string(response, "token", f"login-{suffix}")
        if len(token) > 8192 or any(character.isspace() for character in token):
            raise JourneyFailure(f"login-{suffix}", "token shape is invalid")
        if token in result.body.decode("utf-8", errors="ignore").replace(token, "", 1):
            raise JourneyFailure(f"login-{suffix}", "token was duplicated in the response")
        self._active_tokens.append(token)
        return token

    @staticmethod
    def _auth(token: str) -> Mapping[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _assert_worm(
        self,
        packet: Mapping[str, Any],
        verification: Mapping[str, Any],
        *,
        trace_id: str,
    ) -> Mapping[str, str]:
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
        now = self._now()
        if requested_at > now:
            raise JourneyFailure("worm", "Object Lock request timestamp is in the future")
        if retain_until < requested_at + timedelta(days=retention_days):
            raise JourneyFailure("worm", "Object Lock receipt is shorter than policy")
        if retain_until - now < MIN_REMAINING_RETENTION:
            raise JourneyFailure("worm", "Object Lock has less than 30 days remaining")
        bucket = _required_string(anchor, "bucket", "worm")
        key = _required_string(anchor, "key", "worm")
        version_id = _required_string(anchor, "version_id", "worm")
        manifest_sha = _required_string(anchor, "manifest_sha256", "worm")
        anchor_uri = _required_string(anchor, "anchor_uri", "worm")
        if SHA256_RE.fullmatch(manifest_sha) is None:
            raise JourneyFailure("worm", "anchor manifest digest is invalid")
        parsed_uri = urlparse(anchor_uri)
        try:
            query = parse_qs(parsed_uri.query, strict_parsing=True)
        except ValueError as exc:
            raise JourneyFailure("worm", "anchor URI query is invalid") from exc
        if (
            parsed_uri.scheme != "s3"
            or parsed_uri.username is not None
            or parsed_uri.password is not None
            or parsed_uri.netloc != bucket
            or unquote(parsed_uri.path.lstrip("/")) != key
            or query != {"versionId": [version_id]}
            or parsed_uri.fragment
        ):
            raise JourneyFailure("worm", "anchor URI is not bound to the exact S3 version")
        if verification.get("overall") != "all_match":
            raise JourneyFailure("worm", "packet verification is not all_match")
        if verification.get("trace_id") != trace_id:
            raise JourneyFailure("worm", "packet verification trace is cross-wired")
        checks = verification.get("checks")
        anchor_checks = (
            [
                check
                for check in checks
                if isinstance(check, Mapping)
                and check.get("artifact") == "merged_packet_external_anchor"
            ]
            if isinstance(checks, list)
            else []
        )
        if len(anchor_checks) != 1:
            raise JourneyFailure("worm", "verification has an ambiguous external-anchor check")
        check = anchor_checks[0]
        if (
            check.get("match") is not True
            or check.get("expected") != manifest_sha
            or check.get("actual") != manifest_sha
        ):
            raise JourneyFailure("worm", "verification did not re-read the external anchor")
        receipt = check.get("object_lock_verification")
        if not isinstance(receipt, Mapping):
            raise JourneyFailure("worm", "verification has no structured Object Lock receipt")
        expected = receipt.get("expected")
        observed = receipt.get("observed")
        if not isinstance(expected, Mapping) or not isinstance(observed, Mapping):
            raise JourneyFailure("worm", "Object Lock receipt bindings are missing")
        if (
            receipt.get("schema_version") != OBJECT_LOCK_VERIFICATION_SCHEMA
            or receipt.get("retain_until_rule") != OBJECT_LOCK_RETAIN_UNTIL_RULE
            or receipt.get("verified") is not True
            or receipt.get("failure_reasons") != []
            or SHA256_RE.fullmatch(str(receipt.get("issuer_attestation") or "")) is None
        ):
            raise JourneyFailure("worm", "structured Object Lock receipt is not verified")
        verified_at = _parse_timestamp(receipt.get("verified_at"), "worm")
        evaluated_at = _parse_timestamp(receipt.get("evaluated_at"), "worm")
        expected_requested_at = _parse_timestamp(expected.get("requested_at"), "worm")
        expected_retain_until = _parse_timestamp(expected.get("retain_until"), "worm")
        observed_retain_until = _parse_timestamp(observed.get("retain_until"), "worm")
        if (
            expected.get("bucket") != bucket
            or expected.get("key") != key
            or expected.get("version_id") != version_id
            or expected.get("content_sha256") != manifest_sha
            or expected.get("mode") != anchor.get("object_lock_mode")
            or expected.get("retention_days") != retention_days
            or expected_requested_at != requested_at
            or expected_retain_until != retain_until
            or observed.get("bucket") != bucket
            or observed.get("key") != key
            or observed.get("get_version_id") != version_id
            or observed.get("head_version_id") != version_id
            or observed.get("content_sha256") != manifest_sha
            or observed.get("mode") != anchor.get("object_lock_mode")
            or observed.get("reread_verified") is not True
            or observed_retain_until < expected_retain_until
            or verified_at > evaluated_at
            or evaluated_at > now
        ):
            raise JourneyFailure("worm", "structured Object Lock receipt is cross-wired")
        return {
            "anchor_receipt_sha256": _digest_bytes(_canonical_bytes(anchor)),
            "object_lock_verification_sha256": _digest_bytes(
                _canonical_bytes(receipt)
            ),
        }

    def _assert_packet_binding(
        self, packet: Mapping[str, Any], *, audit_id: str, trace_id: str
    ) -> None:
        packet_input = _nested_mapping(packet, "input", gate="packet-download")
        packet_model = _nested_mapping(packet, "model", gate="packet-download")
        live_audit = _nested_mapping(packet, "live_audit", gate="packet-download")
        provenance = _nested_mapping(packet, "provenance", gate="packet-download")
        if (
            packet.get("trace_id") != trace_id
            or packet_input.get("audit_id") != audit_id
            or packet_input.get("audit_mode") != AUDIT_MODE
            or packet_model.get("model_key") != MODEL_ID
            or packet_model.get("runtime") != "atlas_live_worker"
            or live_audit.get("audit_id") != audit_id
            or provenance.get("method_label") != "cas_harness_live_worker_v1"
        ):
            raise JourneyFailure(
                "packet-download", "packet is not bound to the hosted audit run"
            )

    @staticmethod
    def _assert_share_metadata(
        share: Mapping[str, Any],
        *,
        share_id: str,
        trace_id: str,
        expected_status: str,
        gate: str,
    ) -> tuple[datetime, datetime, datetime | None]:
        if (
            share.get("share_id") != share_id
            or share.get("trace_id") != trace_id
            or share.get("status") != expected_status
        ):
            raise JourneyFailure(gate, "share metadata binding is invalid")
        created = _parse_timestamp(share.get("created_at"), gate)
        expires = _parse_timestamp(share.get("expires_at"), gate)
        raw_revoked = share.get("revoked_at")
        revoked = (
            None if raw_revoked is None else _parse_timestamp(raw_revoked, gate)
        )
        if expires <= created:
            raise JourneyFailure(gate, "share expiry is not after creation")
        if expected_status == "active" and revoked is not None:
            raise JourneyFailure(gate, "active share already has a revocation time")
        if expected_status == "revoked" and (revoked is None or revoked < created):
            raise JourneyFailure(gate, "revoked share has an invalid revocation time")
        return created, expires, revoked

    def _revoke_owner_share(
        self,
        *,
        share_id: str,
        trace_id: str,
        token: str,
    ) -> tuple[HttpResult, HttpResult, datetime]:
        revoke_result = self._call_retry_safe(
            f"/evidence/shares/{share_id}",
            method="DELETE",
            headers=self._auth(token),
        )
        if revoke_result.status not in {200, 204}:
            raise JourneyFailure(
                "share-revoke", f"unexpected HTTP status {revoke_result.status}"
            )
        readback_result = self._call_retry_safe(
            f"/evidence/shares/{share_id}", headers=self._auth(token)
        )
        readback = self._expect(readback_result, {200}, "share-revoke-readback")
        _created, _expires, revoked = self._assert_share_metadata(
            readback,
            share_id=share_id,
            trace_id=trace_id,
            expected_status="revoked",
            gate="share-revoke-readback",
        )
        assert revoked is not None
        try:
            self._active_shares.remove((share_id, token))
        except ValueError:
            pass
        return revoke_result, readback_result, revoked

    def _revoke_all_shares(self) -> None:
        for share_id, token in tuple(self._active_shares):
            try:
                result = self._call_retry_safe(
                    f"/evidence/shares/{share_id}",
                    method="DELETE",
                    headers=self._auth(token),
                )
                if result.status in {200, 204, 404}:
                    self._active_shares.remove((share_id, token))
            except Exception:
                continue

    def collect(self) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            return self._collect_once()
        finally:
            # A failed probe must not leave durable account sessions active. A
            # cleanup failure cannot replace the original fail-closed reason,
            # so this final boundary is deliberately best effort.
            self._revoke_all_shares()
            self._logout_all(require_success=False)

    def _logout_all(self, *, require_success: bool) -> tuple[int, ...]:
        failures = 0
        statuses: list[int] = []
        for token in tuple(self._active_tokens):
            try:
                result = self._call_retry_safe(
                    "/auth/logout", method="POST", headers=self._auth(token)
                )
                statuses.append(result.status)
                # 401 is also a dead-session post-condition: it is what the
                # account chokepoint returns after a response-lost logout.
                if result.status not in {200, 204, 401}:
                    failures += 1
                else:
                    self._active_tokens.remove(token)
            except Exception:
                failures += 1
        if require_success and failures:
            raise JourneyFailure("logout", "probe sessions were not revoked")
        return tuple(statuses)

    def _collect_once(self) -> tuple[dict[str, Any], dict[str, Any]]:
        (
            render_preflight_result,
            render_preflight,
            render_created_dt,
            render_finished_dt,
            render_preflight_sha,
        ) = self._read_render_deploy()

        tenant_a, identity_a, credential_a, account_a = self._provision("a")
        self._grant_comped(tenant_a, account_a)
        token_a = self._login(identity_a, credential_a, "a")
        auth_a = self._auth(token_a)

        audit_payload = {
            "model_id": MODEL_ID,
            "audit_mode": AUDIT_MODE,
            "prompt": f"Customer-production hosted journey {self.nonce}",
            "selected_modules": ["active_trace", "confidence_margin"],
        }
        create_result = self._call_retry_safe(
            "/api/cas-harness/audit/session",
            method="POST",
            payload=audit_payload,
            headers=auth_a,
        )
        created = self._expect(create_result, {200, 201}, "audit-create")
        audit_id = _required_string(created, "audit_id", "audit-create")
        if (
            AUDIT_ID_RE.fullmatch(audit_id) is None
            or created.get("status") != "DRAFT"
            or created.get("model_id") != MODEL_ID
            or created.get("audit_mode") != AUDIT_MODE
            or created.get("selected_modules") != audit_payload["selected_modules"]
        ):
            raise JourneyFailure("audit-create", "audit ID is not production-shaped")

        # The server journals provider execution and treats this exact audit ID
        # as idempotent. One retry reconciles a proxy/network ambiguity without
        # creating a second logical provider run.
        run_result = self._call_retry_safe(
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
        if (
            ran.get("audit_id") != audit_id
            or ran.get("model_id") != MODEL_ID
            or ran.get("audit_mode") != AUDIT_MODE
        ):
            raise JourneyFailure("audit-run", "audit model or mode drifted")
        trace_id = _required_string(ran, "evidence_packet_trace_id", "audit-run")
        if TRACE_ID_RE.fullmatch(trace_id) is None:
            raise JourneyFailure("audit-run", "Evidence Packet trace ID is invalid")
        audit_completed_dt = _parse_timestamp(ran.get("updated_at"), "audit-run")
        audit_completed = _stamp(audit_completed_dt)

        packet_result = self._call_retry_safe(
            f"/evidence/{trace_id}", headers=auth_a
        )
        packet = self._expect(packet_result, {200}, "packet-download")
        self._assert_packet_binding(packet, audit_id=audit_id, trace_id=trace_id)
        packet_downloaded_dt = self._now()
        packet_downloaded = _stamp(packet_downloaded_dt)
        packet_sha = _digest_bytes(packet_result.body)
        packet_canonical_sha = _digest_bytes(_canonical_bytes(packet))

        verify_result = self._call_retry_safe(
            f"/evidence/{trace_id}/verify",
            method="POST",
            headers=auth_a,
        )
        verification = self._expect(verify_result, {200}, "packet-verify")
        worm_digests = self._assert_worm(
            packet, verification, trace_id=trace_id
        )

        share_expiry_requested = self._now().replace(microsecond=0) + SHARE_LIFETIME
        share_result = self._call(
            f"/evidence/{trace_id}/shares",
            method="POST",
            payload={"expires_at": share_expiry_requested.isoformat()},
            headers=auth_a,
        )
        share = self._expect(share_result, {201}, "share-create")
        share_id = _required_string(share, "share_id", "share-create")
        share_token = _required_string(share, "share_token", "share-create")
        if SHARE_ID_RE.fullmatch(share_id) is None:
            raise JourneyFailure("share-create", "share ID is invalid")
        self._active_shares.append((share_id, token_a))
        if SHARE_TOKEN_RE.fullmatch(share_token) is None:
            raise JourneyFailure("share-create", "share token is invalid")
        expected_fetch_path = f"/evidence/shared/{share_id}"
        if share.get("anonymous_fetch_path") != expected_fetch_path:
            raise JourneyFailure("share-create", "share binding is invalid")
        share_created_dt, share_expires_dt, _ = self._assert_share_metadata(
            share,
            share_id=share_id,
            trace_id=trace_id,
            expected_status="active",
            gate="share-create",
        )
        if share_expires_dt != share_expiry_requested:
            raise JourneyFailure("share-create", "share expiry drifted from the request")

        share_metadata_result = self._call_retry_safe(
            f"/evidence/shares/{share_id}", headers=auth_a
        )
        share_metadata = self._expect(
            share_metadata_result, {200}, "share-metadata-readback"
        )
        metadata_created, metadata_expires, _ = self._assert_share_metadata(
            share_metadata,
            share_id=share_id,
            trace_id=trace_id,
            expected_status="active",
            gate="share-metadata-readback",
        )
        if (
            metadata_created != share_created_dt
            or metadata_expires != share_expires_dt
            or "share_token" in share_metadata
            or share_token in share_metadata_result.body.decode("utf-8", errors="ignore")
        ):
            raise JourneyFailure(
                "share-metadata-readback", "share metadata readback is inconsistent"
            )

        anonymous_result = self._call_retry_safe(
            expected_fetch_path,
            headers={"X-Evidence-Share-Token": share_token},
        )
        anonymous_packet = self._expect(anonymous_result, {200}, "share-fetch")
        anonymous_packet_sha = _digest_bytes(_canonical_bytes(anonymous_packet))
        if anonymous_packet_sha != packet_canonical_sha:
            raise JourneyFailure("share-fetch", "anonymous packet differs from owner packet")
        share_fetched_dt = self._now()

        share_token_write = self._call_retry_safe(
            f"/evidence/shares/{share_id}",
            method="DELETE",
            headers={"X-Evidence-Share-Token": share_token},
        )
        if share_token_write.status != 401:
            raise JourneyFailure(
                "share-read-only", "share token reached an authenticated write surface"
            )

        tenant_b, identity_b, credential_b, _account_b = self._provision("b")
        token_b = self._login(identity_b, credential_b, "b")
        auth_b = self._auth(token_b)
        foreign_audit = self._call_retry_safe(
            f"/api/cas-harness/audit/session/{audit_id}/status", headers=auth_b
        )
        foreign_packet = self._call_retry_safe(
            f"/evidence/{trace_id}", headers=auth_b
        )
        foreign_share_create = self._call_retry_safe(
            f"/evidence/{trace_id}/shares",
            method="POST",
            payload={"expires_at": share_expiry_requested.isoformat()},
            headers=auth_b,
        )
        foreign_share_metadata = self._call_retry_safe(
            f"/evidence/shares/{share_id}", headers=auth_b
        )
        foreign_share_revoke = self._call_retry_safe(
            f"/evidence/shares/{share_id}", method="DELETE", headers=auth_b
        )
        if any(
            result.status != 404
            for result in (
                foreign_audit,
                foreign_packet,
                foreign_share_create,
                foreign_share_metadata,
                foreign_share_revoke,
            )
        ):
            raise JourneyFailure(
                "tenant-isolation", "foreign tenant did not receive exact 404s"
            )
        isolation_verified_dt = self._now()

        revoke_result, revoke_readback_result, revoked_at_dt = self._revoke_owner_share(
            share_id=share_id, trace_id=trace_id, token=token_a
        )
        if share_token in revoke_readback_result.body.decode("utf-8", errors="ignore"):
            raise JourneyFailure("share-revoke-readback", "share token was echoed")
        revoked_fetch = self._call_retry_safe(
            expected_fetch_path,
            headers={"X-Evidence-Share-Token": share_token},
        )
        if revoked_fetch.status not in {404, 410}:
            raise JourneyFailure("share-revoke", "revoked anonymous share remained readable")

        logout_statuses = self._logout_all(require_success=True)
        if len(logout_statuses) != 2:
            raise JourneyFailure("logout", "not all probe sessions were reconciled")

        (
            render_final_result,
            render_final,
            final_created_dt,
            final_finished_dt,
            render_final_sha,
        ) = self._read_render_deploy()
        if (
            render_final_sha != render_preflight_sha
            or final_created_dt != render_created_dt
            or final_finished_dt != render_finished_dt
            or render_final != render_preflight
        ):
            raise JourneyFailure(
                "render-deploy", "deployment provider readback mutated during collection"
            )
        observed_dt = self._now()

        critical_times = (
            packet_downloaded_dt,
            share_created_dt,
            share_fetched_dt,
            isolation_verified_dt,
            revoked_at_dt,
        )
        if (
            any(value < audit_completed_dt or value > observed_dt for value in critical_times)
            or not share_created_dt <= share_fetched_dt <= revoked_at_dt
            or share_expires_dt <= share_created_dt
        ):
            raise JourneyFailure("timestamp-order", "journey timestamps are not monotonic")

        share_created = _stamp(share_created_dt)
        share_fetched = _stamp(share_fetched_dt)
        share_expires = _stamp(share_expires_dt)
        isolation_verified = _stamp(isolation_verified_dt)
        revoked_at = _stamp(revoked_at_dt)
        observed_at = _stamp(observed_dt)

        tenant_hash = _subject_digest("tenant", tenant_a)
        account_hash = _subject_digest("account", account_a)
        share_token_hash = _subject_digest("share-token", share_token)
        safe_artifact = {
            "schema_version": SAFE_ARTIFACT_SCHEMA_VERSION,
            "master_head_sha": self.master_head_sha,
            "deploy_id": self.deploy_id,
            "render_service_id": PRODUCTION_SERVICE_ID,
            "render_deploy_commit_sha": self.master_head_sha,
            "render_deploy_status": "live",
            "render_deploy_trigger": "new_commit",
            "render_deploy_created_at_utc": _stamp(render_created_dt),
            "render_deploy_finished_at_utc": _stamp(render_finished_dt),
            "render_deploy_preflight_http_status": render_preflight_result.status,
            "render_deploy_preflight_sha256": render_preflight_sha,
            "render_deploy_final_http_status": render_final_result.status,
            "render_deploy_final_sha256": render_final_sha,
            "tenant_subject_sha256": tenant_hash,
            "account_subject_sha256": account_hash,
            "audit_id": audit_id,
            "trace_id_sha256": _subject_digest("trace", trace_id),
            "audit_create_http_status": create_result.status,
            "audit_run_http_status": run_result.status,
            "audit_completed_at_utc": audit_completed,
            "packet_http_status": packet_result.status,
            "packet_sha256": packet_sha,
            "packet_canonical_sha256": packet_canonical_sha,
            "packet_verification_overall": verification.get("overall"),
            "packet_verification_sha256": _digest_bytes(
                _canonical_bytes(verification)
            ),
            **worm_digests,
            "worm_receipt_bound": True,
            "share_create_http_status": share_result.status,
            "share_metadata_readback_http_status": share_metadata_result.status,
            "share_fetch_http_status": anonymous_result.status,
            "share_packet_canonical_sha256": anonymous_packet_sha,
            "share_token_write_http_status": share_token_write.status,
            "share_token_sha256": share_token_hash,
            "share_revoke_http_status": revoke_result.status,
            "share_revoke_readback_http_status": revoke_readback_result.status,
            "share_revoked_fetch_http_status": revoked_fetch.status,
            "foreign_audit_http_status": foreign_audit.status,
            "foreign_packet_http_status": foreign_packet.status,
            "foreign_share_create_http_status": foreign_share_create.status,
            "foreign_share_metadata_http_status": foreign_share_metadata.status,
            "foreign_share_revoke_http_status": foreign_share_revoke.status,
            "session_logout_http_statuses": list(logout_statuses),
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
        _validate_output_pair(evidence, safe_artifact)
        return evidence, safe_artifact


def _validate_output_pair(
    evidence: Mapping[str, Any], artifact: Mapping[str, Any]
) -> None:
    """Recompute the source-receipt binding before either file is persisted."""

    audit = evidence.get("audit")
    packet = evidence.get("packet_download")
    share = evidence.get("share")
    isolation = evidence.get("tenant_isolation")
    if not all(
        isinstance(value, Mapping) for value in (audit, packet, share, isolation)
    ):
        raise JourneyFailure("source-receipt", "evidence sections are missing")
    assert isinstance(audit, Mapping)
    assert isinstance(packet, Mapping)
    assert isinstance(share, Mapping)
    assert isinstance(isolation, Mapping)
    expected_artifact_hash = _digest_bytes(_canonical_bytes(artifact))
    if (
        artifact.get("schema_version") != SAFE_ARTIFACT_SCHEMA_VERSION
        or evidence.get("artifact_sha256") != expected_artifact_hash
        or artifact.get("master_head_sha") != evidence.get("master_head_sha")
        or artifact.get("deploy_id") != evidence.get("deploy_id")
        or artifact.get("render_service_id") != PRODUCTION_SERVICE_ID
        or artifact.get("render_deploy_commit_sha")
        != evidence.get("master_head_sha")
        or artifact.get("render_deploy_status") != "live"
        or artifact.get("render_deploy_trigger") != "new_commit"
        or artifact.get("render_deploy_preflight_http_status") != 200
        or artifact.get("render_deploy_final_http_status") != 200
        or artifact.get("render_deploy_preflight_sha256")
        != artifact.get("render_deploy_final_sha256")
        or artifact.get("tenant_subject_sha256")
        != evidence.get("tenant_subject_sha256")
        or artifact.get("account_subject_sha256")
        != evidence.get("account_subject_sha256")
        or artifact.get("audit_id") != audit.get("audit_id")
        or artifact.get("audit_create_http_status")
        != audit.get("create_http_status")
        or artifact.get("audit_completed_at_utc")
        != audit.get("completed_at_utc")
        or artifact.get("packet_http_status") != packet.get("http_status")
        or artifact.get("packet_sha256") != packet.get("packet_sha256")
        or artifact.get("packet_verification_overall")
        != packet.get("verification_overall")
        or artifact.get("worm_receipt_bound") is not True
        or packet.get("worm_receipt_bound") is not True
        or artifact.get("share_create_http_status")
        != share.get("create_http_status")
        or artifact.get("share_fetch_http_status")
        != share.get("anonymous_fetch_http_status")
        or artifact.get("share_token_sha256")
        != share.get("share_token_sha256")
        or artifact.get("share_revoke_http_status")
        != share.get("revoke_http_status")
        or artifact.get("share_revoked_fetch_http_status")
        != share.get("revoked_fetch_http_status")
        or artifact.get("foreign_audit_http_status")
        != isolation.get("foreign_audit_http_status")
        or artifact.get("foreign_packet_http_status")
        != isolation.get("foreign_packet_http_status")
        or artifact.get("observed_at_utc") != evidence.get("observed_at_utc")
    ):
        raise JourneyFailure("source-receipt", "evidence and source receipt diverged")
    for key in (
        "render_deploy_preflight_sha256",
        "render_deploy_final_sha256",
        "packet_canonical_sha256",
        "packet_verification_sha256",
        "anchor_receipt_sha256",
        "object_lock_verification_sha256",
        "share_packet_canonical_sha256",
    ):
        if SHA256_RE.fullmatch(str(artifact.get(key) or "")) is None:
            raise JourneyFailure("source-receipt", f"{key} is invalid")
    if artifact.get("packet_canonical_sha256") != artifact.get(
        "share_packet_canonical_sha256"
    ):
        raise JourneyFailure("source-receipt", "shared packet digest is cross-wired")
    render_created = _parse_timestamp(
        artifact.get("render_deploy_created_at_utc"), "source-receipt"
    )
    render_finished = _parse_timestamp(
        artifact.get("render_deploy_finished_at_utc"), "source-receipt"
    )
    observed = _parse_timestamp(evidence.get("observed_at_utc"), "source-receipt")
    if render_created > render_finished or render_finished > observed:
        raise JourneyFailure(
            "source-receipt", "Render deployment timing is not monotonic"
        )


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
        if args.output.resolve() == args.safe_artifact_output.resolve():
            raise JourneyFailure("output", "evidence and source-receipt paths must differ")
        collector = JourneyCollector(
            base_url=args.base_url,
            platform_secret=platform_secret,
            billing_secret=billing_secret,
            master_head_sha=args.master_head,
            deploy_id=args.deploy_id,
        )
        evidence, artifact = collector.collect()
        _validate_output_pair(evidence, artifact)
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
