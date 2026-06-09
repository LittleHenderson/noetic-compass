"""Hosted account-mode smoke for CAS Harness deployments.

This script is intentionally an external black-box smoke: it calls the hosted
HTTP API only. It does not import backend internals and it does not fabricate a
first operator/admin account. Supply a pre-provisioned operator/admin/owner
account-mode token, or credentials for an existing operator/admin/owner account.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OPERATOR_ROLES = {"operator", "admin", "owner"}


class SmokeFailure(RuntimeError):
    pass


@dataclass
class Response:
    status: int
    body: Any
    text: str
    url: str


class Client:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        data = None
        req_headers = {"Accept": "application/json"}
        if headers:
            req_headers.update(headers)
        if token:
            req_headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        req = Request(url, data=data, headers=req_headers, method=method.upper())
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return Response(resp.status, _json_or_text(raw), raw, url)
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            return Response(exc.code, _json_or_text(raw), raw, url)
        except URLError as exc:
            raise SmokeFailure(f"HTTP request failed for {method} {url}: {exc}") from exc


def _json_or_text(raw: str) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _token_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        raise SmokeFailure("Bearer token is not JWT-shaped; expected three dot-separated parts.")
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode((payload + padding).encode("ascii"))
        data = json.loads(decoded.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - this is diagnostic parsing only.
        raise SmokeFailure(f"Could not decode JWT payload: {exc}") from exc
    if not isinstance(data, dict):
        raise SmokeFailure("Decoded JWT payload is not an object.")
    return data


def _expect(resp: Response, status: int, label: str) -> Any:
    if resp.status != status:
        raise SmokeFailure(f"{label} expected HTTP {status}, got {resp.status}: {resp.text}")
    return resp.body


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{int(time.time())}-{uuid.uuid4().hex[:8]}@example.invalid"


def _login(client: Client, *, username: str, mint_secret: str) -> str:
    resp = client.request(
        "POST",
        "/auth/token",
        body={"username": username, "mint_secret": mint_secret},
        headers={"X-Auth-Mint-Secret": mint_secret},
    )
    body = _expect(resp, 200, f"login for {username}")
    token = str(body.get("token") or "")
    if not token:
        raise SmokeFailure(f"login for {username} returned no token: {body}")
    return token


def _operator_token(args: argparse.Namespace, client: Client) -> str:
    if args.bearer_token:
        return args.bearer_token.strip()
    if args.operator_username and args.mint_secret:
        return _login(client, username=args.operator_username, mint_secret=args.mint_secret)
    raise SmokeFailure(
        "No operator/admin bootstrap path is exposed by the hosted API. "
        "Supply --bearer-token for a pre-provisioned operator/admin/owner account-mode token, "
        "or --operator-username plus --mint-secret for an existing operator/admin/owner account."
    )


def _check_operator_claims(token: str) -> dict[str, Any]:
    claims = _token_payload(token)
    role = str(claims.get("role") or "")
    if role not in OPERATOR_ROLES:
        raise SmokeFailure(
            f"Supplied operator token role must be one of {sorted(OPERATOR_ROLES)}, got {role!r}."
        )
    for claim in ("jti", "account_id", "tenant_id"):
        if not claims.get(claim):
            raise SmokeFailure(
                f"Supplied operator token is missing {claim!r}; hosted account-mode smoke "
                "requires a durable account-mode token, not a legacy shared-secret token."
            )
    return claims


def _create_invite(
    client: Client,
    *,
    operator_token: str,
    role: str,
    email: str,
    tenant_id: str,
) -> str:
    resp = client.request(
        "POST",
        "/accounts/invite",
        token=operator_token,
        body={
            "role": role,
            "target_email": email,
            "tenant_id": tenant_id,
            "max_uses": 1,
        },
    )
    if resp.status == 503:
        raise SmokeFailure(
            "Accounts endpoint returned 503 during invite creation. "
            "Hosted deployment is not running with NC_ACCOUNTS_ENABLED=true and a durable store."
        )
    if resp.status in (401, 403):
        raise SmokeFailure(
            f"Operator/admin token was refused by invite creation ({resp.status}): {resp.text}"
        )
    body = _expect(resp, 200, f"create {role} invite for {email}")
    code = str(body.get("code") or "")
    if not code:
        raise SmokeFailure(f"invite response did not include a code: {body}")
    return code


def _redeem(client: Client, *, code: str, email: str) -> dict[str, Any]:
    body = _expect(
        client.request(
            "POST",
            "/accounts/invite/redeem",
            body={"code": code, "email_or_username": email, "display_name": "Hosted Smoke"},
        ),
        200,
        f"redeem invite for {email}",
    )
    if body.get("email_or_username") != email.lower():
        raise SmokeFailure(f"redeem returned unexpected identity for {email}: {body}")
    if body.get("status") != "active":
        raise SmokeFailure(f"redeemed account is not active: {body}")
    return body


def _create_redeem_login(
    client: Client,
    *,
    operator_token: str,
    mint_secret: str,
    role: str,
    email: str,
    tenant_id: str,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    code = _create_invite(
        client,
        operator_token=operator_token,
        role=role,
        email=email,
        tenant_id=tenant_id,
    )
    account = _redeem(client, code=code, email=email)
    token = _login(client, username=email, mint_secret=mint_secret)
    claims = _token_payload(token)
    if not claims.get("jti"):
        raise SmokeFailure(f"login for {email} minted a token without durable jti: {claims}")
    if claims.get("tenant_id") != tenant_id:
        raise SmokeFailure(f"login for {email} returned wrong tenant: {claims}")
    if claims.get("role") != role:
        raise SmokeFailure(f"login for {email} returned wrong role: {claims}")
    return token, claims, account


def _protected_probe(client: Client, token: str) -> Response:
    return client.request("GET", "/api/cas-harness/audit/sessions", token=token)


def _check_logout(client: Client, token: str) -> None:
    _expect(_protected_probe(client, token), 200, "pre-logout protected request")
    body = _expect(client.request("POST", "/auth/logout", token=token), 200, "logout")
    if body != {"revoked": True}:
        raise SmokeFailure(f"logout response was not {{'revoked': True}}: {body}")
    after = _protected_probe(client, token)
    if after.status != 401:
        raise SmokeFailure(f"revoked logout token should be rejected with 401, got {after.status}: {after.text}")


def _check_admin_revoke(client: Client, *, operator_token: str, member_token: str, member_jti: str) -> None:
    _expect(_protected_probe(client, member_token), 200, "pre-admin-revoke protected request")
    resp = client.request("POST", f"/auth/sessions/{member_jti}/revoke", token=operator_token)
    if resp.status == 404:
        print("SKIP admin revoke: /auth/sessions/{jti}/revoke is not present on this deployment.")
        return
    body = _expect(resp, 200, "admin revoke")
    if body != {"revoked": True}:
        raise SmokeFailure(f"admin revoke response was not {{'revoked': True}}: {body}")
    after = _protected_probe(client, member_token)
    if after.status != 401:
        raise SmokeFailure(f"admin-revoked token should be rejected with 401, got {after.status}: {after.text}")


def _check_disable(
    client: Client,
    *,
    args: argparse.Namespace,
    operator_token: str,
    victim_token: str,
    victim_account: dict[str, Any],
) -> str | None:
    if not args.disable_account_endpoint:
        message = (
            "Disabled-account recheck BLOCKED: no hosted admin-disable endpoint was supplied. "
            "Pass --disable-account-endpoint with {account_id} or use "
            "--allow-missing-disabled-account-check to run the rest as a scaffold."
        )
        if args.allow_missing_disabled_account_check:
            print(f"SKIP {message}")
            return None
        return message

    path = args.disable_account_endpoint.format(
        account_id=victim_account.get("account_id"),
        email=victim_account.get("email_or_username"),
    )
    body = json.loads(args.disable_account_json) if args.disable_account_json else None
    resp = client.request(args.disable_account_method, path, token=operator_token, body=body)
    if resp.status == 404:
        return f"Configured admin-disable endpoint returned 404: {path}"
    if resp.status not in args.disable_success_status:
        return (
            f"Configured admin-disable endpoint expected one of {args.disable_success_status}, "
            f"got {resp.status}: {resp.text}"
        )
    after = _protected_probe(client, victim_token)
    if after.status != 401:
        return f"disabled account token should be rejected with 401, got {after.status}: {after.text}"
    return None


def _check_audit_evidence(
    client: Client,
    *,
    args: argparse.Namespace,
    operator_token: str,
    mint_secret: str,
    tenant_id: str,
    cross_tenant_id: str,
) -> None:
    member_email = args.audit_email or _unique_email("hosted-audit-member")
    cross_email = args.cross_tenant_email or _unique_email("hosted-cross-member")
    same_tenant_operator_email = args.same_tenant_operator_email or _unique_email("hosted-anchor-operator")
    member_token, _member_claims, _member_account = _create_redeem_login(
        client,
        operator_token=operator_token,
        mint_secret=mint_secret,
        role="member",
        email=member_email,
        tenant_id=tenant_id,
    )
    cross_token, _cross_claims, _cross_account = _create_redeem_login(
        client,
        operator_token=operator_token,
        mint_secret=mint_secret,
        role="member",
        email=cross_email,
        tenant_id=cross_tenant_id,
    )

    created = _expect(
        client.request(
            "POST",
            "/api/cas-harness/audit/session",
            token=member_token,
            body={
                "model_id": args.audit_model_id,
                "audit_mode": "BALANCED",
                "prompt": "Hosted account-mode smoke: produce evidence ownership if the runner is available.",
                "selected_modules": ["active_trace", "confidence_margin"],
            },
        ),
        200,
        "create account-mode audit session",
    )
    audit_id = str(created.get("audit_id") or "")
    if not audit_id:
        raise SmokeFailure(f"audit create response did not include audit_id: {created}")
    ran = _expect(
        client.request("POST", f"/api/cas-harness/audit/session/{audit_id}/run", token=member_token),
        200,
        "run account-mode audit session",
    )
    trace_id = str(ran.get("evidence_packet_trace_id") or "")
    if not trace_id:
        raise SmokeFailure(f"audit run produced no evidence_packet_trace_id: {ran}")

    _expect(client.request("GET", f"/evidence/{trace_id}", token=member_token), 200, "evidence own read")
    cross = client.request("GET", f"/evidence/{trace_id}", token=cross_token)
    if cross.status != 404:
        raise SmokeFailure(f"cross-tenant evidence read should be 404, got {cross.status}: {cross.text}")

    if args.check_anchor:
        same_tenant_operator_token, _claims, _account = _create_redeem_login(
            client,
            operator_token=operator_token,
            mint_secret=mint_secret,
            role="operator",
            email=same_tenant_operator_email,
            tenant_id=tenant_id,
        )
        member_anchor = client.request("POST", f"/evidence/{trace_id}/anchor", token=member_token)
        if member_anchor.status != 403:
            raise SmokeFailure(
                f"member anchor should be denied with 403 in account mode, got {member_anchor.status}: {member_anchor.text}"
            )
        operator_anchor = client.request(
            "POST",
            f"/evidence/{trace_id}/anchor",
            token=same_tenant_operator_token,
            query={"require_object_lock": "false"},
        )
        if operator_anchor.status not in (200, 404, 409):
            raise SmokeFailure(
                "same-tenant operator anchor should pass RBAC and then return route-level 200/404/409, "
                f"got {operator_anchor.status}: {operator_anchor.text}"
            )
        print(f"anchor RBAC scaffold observed operator status {operator_anchor.status} for trace {trace_id}")


def _dry_run(args: argparse.Namespace) -> None:
    plan = {
        "base_url": args.base_url,
        "uses_operator_bearer_token": bool(args.bearer_token),
        "uses_operator_credentials": bool(args.operator_username and args.mint_secret),
        "requires_member_login_mint_secret": True,
        "core_checks": [
            "operator/admin/owner token has durable jti/account_id/tenant_id",
            "POST /accounts/invite",
            "POST /accounts/invite/redeem",
            "POST /auth/token for redeemed member",
            "POST /auth/logout then protected request returns 401",
            "POST /auth/sessions/{jti}/revoke then protected request returns 401 if endpoint exists",
        ],
        "disabled_account_check": args.disable_account_endpoint
        or "BLOCKED unless --allow-missing-disabled-account-check is set",
        "audit_evidence_checks": bool(args.check_audit_evidence),
        "anchor_checks": bool(args.check_anchor),
    }
    print(json.dumps(plan, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Hosted CAS Harness account-mode smoke. Requires a deployment with "
            "NC_ACCOUNTS_ENABLED=true and a pre-provisioned operator/admin/owner account."
        )
    )
    parser.add_argument("--base-url", required=True, help="Hosted API base URL, e.g. https://api.example.com")
    parser.add_argument("--bearer-token", help="Pre-provisioned operator/admin/owner account-mode bearer token")
    parser.add_argument("--operator-username", help="Existing operator/admin/owner username/email for /auth/token")
    parser.add_argument("--mint-secret", help="NC_AUTH_MINT_SECRET credential used by /auth/token")
    parser.add_argument("--tenant-id", default=f"hosted-smoke-{uuid.uuid4().hex[:8]}")
    parser.add_argument("--cross-tenant-id", default=f"hosted-smoke-cross-{uuid.uuid4().hex[:8]}")
    parser.add_argument("--logout-email")
    parser.add_argument("--revoke-email")
    parser.add_argument("--disable-email")
    parser.add_argument("--audit-email")
    parser.add_argument("--cross-tenant-email")
    parser.add_argument("--same-tenant-operator-email")
    parser.add_argument("--audit-model-id", default="EleutherAI/pythia-160m")
    parser.add_argument("--check-audit-evidence", action="store_true", help="Run audit/evidence own and cross-tenant checks")
    parser.add_argument("--check-anchor", action="store_true", help="Also scaffold evidence anchor RBAC checks")
    parser.add_argument("--disable-account-endpoint", help="Admin-disable path template, e.g. /accounts/{account_id}/disable")
    parser.add_argument("--disable-account-method", default="POST")
    parser.add_argument("--disable-account-json", default="", help="Optional JSON body for the disable endpoint")
    parser.add_argument(
        "--disable-success-status",
        type=int,
        nargs="+",
        default=[200, 204],
        help="HTTP status codes accepted from the disable endpoint",
    )
    parser.add_argument(
        "--allow-missing-disabled-account-check",
        action="store_true",
        help="Do not fail solely because no hosted admin-disable endpoint exists; reports a scaffold skip instead.",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--dry-run", action="store_true", help="Print planned checks without making HTTP requests")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.dry_run:
        _dry_run(args)
        return 0
    client = Client(args.base_url, args.timeout)
    if not args.mint_secret:
        raise SmokeFailure(
            "--mint-secret is required for invite/redeem/login smoke because redeemed accounts "
            "must log in through /auth/token."
        )

    operator_token = _operator_token(args, client)
    operator_claims = _check_operator_claims(operator_token)
    print(
        "operator token OK: "
        f"role={operator_claims.get('role')} tenant={operator_claims.get('tenant_id')} "
        f"jti={operator_claims.get('jti')}"
    )

    logout_token, logout_claims, _logout_account = _create_redeem_login(
        client,
        operator_token=operator_token,
        mint_secret=args.mint_secret,
        role="member",
        email=args.logout_email or _unique_email("hosted-logout-member"),
        tenant_id=args.tenant_id,
    )
    print(f"invite/redeem/login OK for logout member jti={logout_claims.get('jti')}")
    _check_logout(client, logout_token)
    print("logout revocation OK")

    revoke_token, revoke_claims, _revoke_account = _create_redeem_login(
        client,
        operator_token=operator_token,
        mint_secret=args.mint_secret,
        role="member",
        email=args.revoke_email or _unique_email("hosted-revoke-member"),
        tenant_id=args.tenant_id,
    )
    print(f"invite/redeem/login OK for admin-revoke member jti={revoke_claims.get('jti')}")
    _check_admin_revoke(
        client,
        operator_token=operator_token,
        member_token=revoke_token,
        member_jti=str(revoke_claims["jti"]),
    )
    print("admin revoke OK or explicitly skipped when endpoint absent")

    disable_token, _disable_claims, disable_account = _create_redeem_login(
        client,
        operator_token=operator_token,
        mint_secret=args.mint_secret,
        role="member",
        email=args.disable_email or _unique_email("hosted-disable-member"),
        tenant_id=args.tenant_id,
    )
    disabled_blocker = _check_disable(
        client,
        args=args,
        operator_token=operator_token,
        victim_token=disable_token,
        victim_account=disable_account,
    )

    if args.check_audit_evidence:
        _check_audit_evidence(
            client,
            args=args,
            operator_token=operator_token,
            mint_secret=args.mint_secret,
            tenant_id=args.tenant_id,
            cross_tenant_id=args.cross_tenant_id,
        )
        print("audit/evidence ownership checks OK")
    else:
        print("SKIP audit/evidence ownership checks: pass --check-audit-evidence to run them.")

    if disabled_blocker:
        raise SmokeFailure(disabled_blocker)
    print("HOSTED ACCOUNT-MODE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeFailure as exc:
        print(f"HOSTED ACCOUNT-MODE SMOKE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
