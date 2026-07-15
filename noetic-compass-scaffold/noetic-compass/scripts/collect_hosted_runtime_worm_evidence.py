#!/usr/bin/env python3
"""Collect runtime/WORM evidence from a short-lived hosted probe session.

This Render-Shell-only wrapper keeps the synthetic account credential and
bearer token inside one Python process.  It validates the exact fresh Render
deployment before creating one probe tenant, grants a two-hour manual-comped
entitlement, invokes the existing runtime/WORM collector in-process, confirms
logout, and only then writes the existing secret-safe evidence pair.

It does not publish acceptance authority, create a primary owner, call Stripe,
or change the customer-production verdict from OPEN.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re
import secrets
import sys
from typing import Any
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from . import collect_runtime_worm_evidence as runtime
except ImportError:
    try:
        from scripts import collect_runtime_worm_evidence as runtime
    except ImportError:  # Direct ``python scripts/...`` execution.
        import collect_runtime_worm_evidence as runtime


PLATFORM_SECRET_ENV = "NC_PLATFORM_TENANT_PROVISIONING_SECRET"
BILLING_SECRET_ENV = "NC_BILLING_ADMIN_SECRET"
PROBE_ENTITLEMENT_LIFETIME = timedelta(hours=2)
ACCOUNT_ID_RE = re.compile(r"^acct-[0-9a-f]{32}$")
PROVISIONING_ID_RE = re.compile(r"^tenantprov-[0-9a-f]{32}$")
PROVISIONING_RECEIPT_ID_RE = re.compile(r"^tenantprovrct-[0-9a-f]{32}$")


class HostedRuntimeWormCollector:
    """Orchestrate one bounded synthetic session around the proven collector."""

    def __init__(
        self,
        *,
        base_url: str,
        platform_secret: str,
        billing_secret: str,
        render_api_key: str,
        master_head_sha: str,
        deploy_id: str,
        deployed_at_utc: str,
        runtime_environment: Mapping[str, str] = os.environ,
        transport: runtime.Transport = runtime._default_transport,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        identity_nonce: str | None = None,
        runtime_nonce: str | None = None,
        runtime_collector_factory: Callable[..., Any] = runtime.RuntimeWormCollector,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.platform_secret = platform_secret
        self.billing_secret = billing_secret
        self.render_api_key = render_api_key
        self.master_head_sha = master_head_sha
        self.deploy_id = deploy_id
        self.deployed_at_utc = deployed_at_utc
        self.runtime_environment = runtime_environment
        self.transport = transport
        self.clock = clock
        self.identity_nonce = identity_nonce or secrets.token_hex(12)
        self.runtime_nonce = runtime_nonce or secrets.token_hex(12)
        self.runtime_collector_factory = runtime_collector_factory
        self._active_token: str | None = None
        self._sensitive_values: list[str] = [
            platform_secret,
            billing_secret,
            render_api_key,
        ]
        self._validate_binding()

    def _validate_binding(self) -> None:
        parsed = urlparse(self.base_url)
        expected = urlparse(runtime.PRODUCTION_API_ORIGIN)
        if (
            parsed != expected
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise runtime.RuntimeWormFailure(
                "binding", "base URL is not exact public production"
            )
        if runtime.SHA1_RE.fullmatch(self.master_head_sha) is None:
            raise runtime.RuntimeWormFailure(
                "binding", "master head is not a lowercase commit SHA"
            )
        if runtime.DEPLOY_ID_RE.fullmatch(self.deploy_id) is None:
            raise runtime.RuntimeWormFailure("binding", "deploy ID is invalid")
        if self.runtime_environment.get("RENDER_SERVICE_ID") != runtime.PRODUCTION_SERVICE_ID:
            raise runtime.RuntimeWormFailure(
                "binding", "collector is not running in the pinned production service"
            )
        if self.runtime_environment.get("RENDER_GIT_COMMIT") != self.master_head_sha:
            raise runtime.RuntimeWormFailure(
                "binding", "runtime commit does not match the supplied master HEAD"
            )
        if self.runtime_environment.get(runtime.API_TOKEN_ENV):
            raise runtime.RuntimeWormFailure(
                "authentication", "refusing an inherited account bearer token"
            )
        for name, value in (
            (PLATFORM_SECRET_ENV, self.platform_secret),
            (BILLING_SECRET_ENV, self.billing_secret),
            (runtime.RENDER_API_KEY_ENV, self.render_api_key),
        ):
            if not isinstance(value, str) or not value or len(value) > 8192:
                raise runtime.RuntimeWormFailure(
                    "authentication", f"required operator credential {name} is unavailable"
                )
        if any(character.isspace() for character in self.render_api_key):
            raise runtime.RuntimeWormFailure(
                "authentication", "Render API key is unavailable"
            )
        if (
            re.fullmatch(r"[0-9a-f]{24}", self.identity_nonce) is None
            or re.fullmatch(r"[0-9a-f]{24}", self.runtime_nonce) is None
            or self.identity_nonce == self.runtime_nonce
        ):
            raise runtime.RuntimeWormFailure(
                "binding", "probe nonces must be distinct lowercase 24-hex values"
            )
        self._now()

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise runtime.RuntimeWormFailure(
                "clock", "collector clock must be timezone-aware"
            )
        return value.astimezone(UTC)

    def _call(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float = 60.0,
    ) -> runtime.HttpResult:
        parsed = urlparse(path)
        if (
            not path.startswith("/")
            or path.startswith("//")
            or parsed.scheme
            or parsed.netloc
            or parsed.query
            or parsed.fragment
            or "\\" in path
        ):
            raise runtime.RuntimeWormFailure(
                "binding", "request path is not a query-free relative path"
            )
        return self.transport(
            base_url=self.base_url,
            path=path,
            method=method,
            payload=payload,
            headers={} if headers is None else headers,
            timeout=timeout,
        )

    def _call_retry_safe(self, path: str, **kwargs: Any) -> runtime.HttpResult:
        for attempt in range(2):
            try:
                result = self._call(path, **kwargs)
            except runtime.RuntimeWormFailure as exc:
                if exc.gate != "network" or attempt:
                    raise
                continue
            if result.status < 500 or attempt:
                return result
        raise runtime.RuntimeWormFailure(
            "network", "idempotent request could not be reconciled"
        )

    @staticmethod
    def _expect(
        result: runtime.HttpResult, statuses: set[int], gate: str
    ) -> Mapping[str, Any]:
        if result.status not in statuses:
            raise runtime.RuntimeWormFailure(
                gate, f"unexpected HTTP status {result.status}"
            )
        return runtime._decode_object(result, gate)

    def _preflight(self) -> None:
        runtime.read_exact_render_deployment(
            render_api_key=self.render_api_key,
            master_head_sha=self.master_head_sha,
            deploy_id=self.deploy_id,
            deployed_at_utc=self.deployed_at_utc,
            transport=self.transport,
            clock=self.clock,
        )

    def _provision(self) -> tuple[str, str, str, str]:
        tenant_id = f"cp-rw-{self.identity_nonce[:20]}"
        identity = f"cp-rw-{self.identity_nonce}@acceptance.invalid"
        credential = "casak_" + secrets.token_urlsafe(48)
        self._sensitive_values.extend((tenant_id, identity, credential))
        payload = {
            "tenant_id": tenant_id,
            "email_or_username": identity,
            "api_credential": credential,
            "display_name": "Runtime WORM acceptance probe",
        }
        result = self._call_retry_safe(
            "/platform/tenants",
            method="POST",
            payload=payload,
            headers={"X-Platform-Provisioning-Secret": self.platform_secret},
        )
        response = self._expect(result, {200}, "provision")
        owner = response.get("owner")
        if not isinstance(owner, Mapping):
            raise runtime.RuntimeWormFailure("provision", "owner response is missing")
        account_id = runtime._required_string(owner, "account_id", "provision")
        provisioning_id = runtime._required_string(
            response, "provisioning_id", "provision"
        )
        receipt_id = runtime._required_string(response, "receipt_id", "provision")
        completed_at = runtime._parse_timestamp(response.get("completed_at"), "provision")
        self._sensitive_values.extend((account_id, provisioning_id, receipt_id))
        if (
            ACCOUNT_ID_RE.fullmatch(account_id) is None
            or PROVISIONING_ID_RE.fullmatch(provisioning_id) is None
            or PROVISIONING_RECEIPT_ID_RE.fullmatch(receipt_id) is None
            or completed_at > self._now()
        ):
            raise runtime.RuntimeWormFailure(
                "provision", "provisioning receipt is invalid"
            )
        if (
            owner.get("tenant_id") != tenant_id
            or owner.get("email_or_username") != identity
            or owner.get("role") != "owner"
            or owner.get("status") != "active"
        ):
            raise runtime.RuntimeWormFailure("provision", "owner binding is invalid")
        if "api_credential" in owner or credential.encode("utf-8") in result.body:
            raise runtime.RuntimeWormFailure(
                "provision", "credential was echoed by the API"
            )
        return tenant_id, identity, credential, account_id

    def _grant_comped(self, tenant_id: str, account_id: str) -> None:
        expires_at = self._now() + PROBE_ENTITLEMENT_LIFETIME
        payload = {
            "tenant_id": tenant_id,
            "billing_account_id": account_id,
            "expires_at": expires_at.isoformat(),
        }
        # The entitlement store converges on the same final subscription, but
        # a replay creates another durable ledger revision. Do not retry an
        # ambiguous response; fail closed before login/audit instead.
        result = self._call(
            "/platform/billing/manual-comped-subscription",
            method="POST",
            payload=payload,
            headers={"X-Billing-Admin-Secret": self.billing_secret},
        )
        response = self._expect(result, {200}, "manual-comped")
        if (
            response.get("tenant_id") != tenant_id
            or response.get("plan_id") != "beta_comped"
            or response.get("status") != "active"
            or response.get("source") != "manual_comped"
            or runtime._parse_timestamp(response.get("expires_at"), "manual-comped")
            != expires_at
        ):
            raise runtime.RuntimeWormFailure(
                "manual-comped", "entitlement response is invalid"
            )

    def _login(self, identity: str, credential: str) -> str:
        result = self._call(
            "/auth/token",
            method="POST",
            payload={"username": identity, "api_credential": credential},
        )
        response = self._expect(result, {200}, "login")
        token = runtime._required_string(response, "token", "login")
        if len(token) > 8192 or any(character.isspace() for character in token):
            raise runtime.RuntimeWormFailure("login", "token shape is invalid")
        # Once a syntactically safe token is available, track it before any
        # remaining response validation so a malformed/duplicated response can
        # still be logged out by the outer cleanup boundary.
        self._active_token = token
        self._sensitive_values.append(token)
        if token in result.body.decode("utf-8", errors="ignore").replace(token, "", 1):
            raise runtime.RuntimeWormFailure("login", "token was duplicated in response")
        return token

    def _logout(self) -> int:
        token = self._active_token
        if not token:
            return 204
        result = self._call_retry_safe(
            "/auth/logout",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
        )
        if result.status not in {200, 204, 401}:
            raise runtime.RuntimeWormFailure(
                "logout", "probe session revocation could not be confirmed"
            )
        self._active_token = None
        return result.status

    def _best_effort_logout(self) -> None:
        try:
            self._logout()
        except BaseException:
            return

    def _assert_secret_safe(
        self, evidence: Mapping[str, Any], artifact: Mapping[str, Any]
    ) -> None:
        if runtime._semantic_contains_any(
            (evidence, artifact), tuple(self._sensitive_values)
        ):
            raise runtime.RuntimeWormFailure(
                "secret-safety", "raw hosted probe identifier reached output"
            )

    def collect(self) -> tuple[dict[str, Any], dict[str, Any], int]:
        self._preflight()
        tenant_id, identity, credential, account_id = self._provision()
        self._grant_comped(tenant_id, account_id)

        evidence: dict[str, Any] | None = None
        artifact: dict[str, Any] | None = None
        collection_error: BaseException | None = None
        cleanup_error: BaseException | None = None
        logout_status = 0
        try:
            token = self._login(identity, credential)
            collector = self.runtime_collector_factory(
                base_url=self.base_url,
                bearer_token=token,
                render_api_key=self.render_api_key,
                master_head_sha=self.master_head_sha,
                deploy_id=self.deploy_id,
                deployed_at_utc=self.deployed_at_utc,
                transport=self.transport,
                clock=self.clock,
                nonce=self.runtime_nonce,
            )
            evidence, artifact = collector.collect()
        except BaseException as exc:  # Preserve cancellation and the exact gate.
            collection_error = exc
        try:
            logout_status = self._logout()
        except BaseException as exc:
            cleanup_error = exc
            self._best_effort_logout()

        if collection_error is not None:
            if cleanup_error is not None and hasattr(collection_error, "add_note"):
                collection_error.add_note("probe session cleanup could not be confirmed")
            raise collection_error
        if cleanup_error is not None:
            if hasattr(cleanup_error, "add_note"):
                cleanup_error.add_note("probe session cleanup could not be confirmed")
            raise cleanup_error
        if evidence is None or artifact is None:
            raise runtime.RuntimeWormFailure(
                "runtime-worm", "collector produced no evidence"
            )
        self._assert_secret_safe(evidence, artifact)
        return evidence, artifact, logout_status


def _write_output_pair(
    *,
    evidence_path: Path,
    evidence: Mapping[str, Any],
    artifact_path: Path,
    artifact: Mapping[str, Any],
) -> None:
    """Publish two create-only files or remove every file created here."""

    if evidence_path.exists() or artifact_path.exists():
        raise runtime.RuntimeWormFailure(
            "output", "refusing to overwrite a pre-existing output"
        )
    nonce = secrets.token_hex(12)
    evidence_stage = evidence_path.parent / f".{evidence_path.name}.{nonce}.stage"
    artifact_stage = artifact_path.parent / f".{artifact_path.name}.{nonce}.stage"
    created_targets: list[Path] = []
    try:
        runtime._atomic_write(artifact_stage, artifact)
        runtime._atomic_write(evidence_stage, evidence)
        # Hard-link publication is atomic and create-only on the Render Linux
        # filesystem. If the second target cannot be linked, roll back the
        # first target instead of leaving a plausible one-sided evidence pair.
        os.link(artifact_stage, artifact_path)
        created_targets.append(artifact_path)
        os.link(evidence_stage, evidence_path)
        created_targets.append(evidence_path)
    except BaseException:
        for target in reversed(created_targets):
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    finally:
        for stage in (artifact_stage, evidence_stage):
            try:
                stage.unlink(missing_ok=True)
            except OSError:
                pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=runtime.PRODUCTION_API_ORIGIN)
    parser.add_argument("--master-head", required=True)
    parser.add_argument("--deploy-id", required=True)
    parser.add_argument("--deployed-at-utc", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--safe-artifact-output", required=True, type=Path)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.output.resolve() == args.safe_artifact_output.resolve():
            raise runtime.RuntimeWormFailure("output", "output paths must differ")
        if args.output.exists() or args.safe_artifact_output.exists():
            raise runtime.RuntimeWormFailure(
                "output", "refusing to overwrite a pre-existing output"
            )
        collector = HostedRuntimeWormCollector(
            base_url=args.base_url,
            platform_secret=os.environ.get(PLATFORM_SECRET_ENV, ""),
            billing_secret=os.environ.get(BILLING_SECRET_ENV, ""),
            render_api_key=os.environ.get(runtime.RENDER_API_KEY_ENV, ""),
            master_head_sha=args.master_head,
            deploy_id=args.deploy_id,
            deployed_at_utc=args.deployed_at_utc,
        )
        evidence, artifact, logout_status = collector.collect()
        _write_output_pair(
            evidence_path=args.output,
            evidence=evidence,
            artifact_path=args.safe_artifact_output,
            artifact=artifact,
        )
        print(
            json.dumps(
                {
                    "artifact_sha256": evidence["artifact_sha256"],
                    "authority_published": False,
                    "customer_production_status": "OPEN",
                    "evidence_sha256": runtime._digest_bytes(
                        runtime._canonical_bytes(evidence)
                    ),
                    "gate": "runtime_worm",
                    "logout_http_status": logout_status,
                    "status": "validated_hosted_draft",
                    "verdict": "FLAG_FOR_HUMAN_REVIEW",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    except runtime.RuntimeWormFailure as exc:
        cleanup_unconfirmed = (
            "probe session cleanup could not be confirmed"
            in tuple(getattr(exc, "__notes__", ()))
        )
        detail = str(exc)
        if cleanup_unconfirmed:
            detail += "; probe session cleanup could not be confirmed"
        print(
            json.dumps(
                {
                    "gate": exc.gate,
                    "status": "OPEN",
                    "error": detail,
                    "probe_session_cleanup_unconfirmed": cleanup_unconfirmed,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2
    except Exception as exc:
        cleanup_unconfirmed = (
            "probe session cleanup could not be confirmed"
            in tuple(getattr(exc, "__notes__", ()))
        )
        detail = "hosted runtime/WORM collection failed closed"
        if cleanup_unconfirmed:
            detail += "; probe session cleanup could not be confirmed"
        print(
            json.dumps(
                {
                    "gate": "internal",
                    "status": "OPEN",
                    "error": detail,
                    "probe_session_cleanup_unconfirmed": cleanup_unconfirmed,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
