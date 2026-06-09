"""Hosted quota smoke for CAS Harness deployments.

The quota gate is a black-box HTTP behavior: when NC_QUOTAS_ENABLED=true and
the tenant is over cap, CAS Harness audit-session creation must return HTTP
429 with detail.error == "quota_exceeded".
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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
        headers: dict[str, str] | None = None,
    ) -> Response:
        url = f"{self.base_url}{path}"
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


def _login(client: Client, *, username: str, mint_secret: str) -> str:
    resp = client.request(
        "POST",
        "/auth/token",
        body={"username": username, "mint_secret": mint_secret},
        headers={"X-Auth-Mint-Secret": mint_secret},
    )
    if resp.status != 200:
        raise SmokeFailure(f"login expected HTTP 200, got {resp.status}: {resp.text}")
    token = str((resp.body or {}).get("token") or "")
    if not token:
        raise SmokeFailure(f"login returned no token: {resp.body}")
    return token


def _bearer(args: argparse.Namespace, client: Client) -> str:
    if args.bearer_token:
        return args.bearer_token.strip()
    if args.username and args.mint_secret:
        return _login(client, username=args.username, mint_secret=args.mint_secret)
    raise SmokeFailure(
        "Supply --bearer-token for an account-mode member/operator token, "
        "or --username plus --mint-secret for an existing account."
    )


def _audit_payload(iteration: int, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "model_id": args.model_id,
        "audit_mode": "BALANCED",
        "prompt": f"Hosted quota smoke request {iteration}: verify 429 quota_exceeded behavior.",
        "selected_modules": ["cognitive_bias", "provenance_trace"],
        "license_key": "hosted-quota-smoke",
    }


def _detail_error(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    detail = body.get("detail")
    if isinstance(detail, dict):
        value = detail.get("error")
        return str(value) if value is not None else None
    return None


def _dry_run(args: argparse.Namespace) -> None:
    plan = {
        "base_url": args.base_url,
        "uses_bearer_token": bool(args.bearer_token),
        "uses_credentials": bool(args.username and args.mint_secret),
        "endpoint": "POST /api/cas-harness/audit/session",
        "max_attempts": args.max_attempts,
        "pass_condition": 'HTTP 429 with JSON body detail.error == "quota_exceeded"',
        "failure_if": [
            "token has no durable jti",
            "audit creation returns auth/setup errors",
            "no quota_exceeded 429 appears before max attempts",
        ],
    }
    print(json.dumps(plan, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Hosted CAS Harness quota smoke. Requires NC_ACCOUNTS_ENABLED=true, "
            "NC_QUOTAS_ENABLED=true, and an account-mode token for the tenant to meter."
        )
    )
    parser.add_argument("--base-url", required=True, help="Hosted API base URL")
    parser.add_argument("--bearer-token", help="Account-mode bearer token to meter")
    parser.add_argument("--username", help="Existing account username/email for /auth/token")
    parser.add_argument("--mint-secret", help="NC_AUTH_MINT_SECRET credential used by /auth/token")
    parser.add_argument("--model-id", default="openai:gpt-4.1-mini")
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=105,
        help="Maximum audit-session create attempts before declaring quota enforcement absent",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--dry-run", action="store_true", help="Print planned checks without making HTTP requests")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.dry_run:
        _dry_run(args)
        return 0
    if args.max_attempts < 1:
        raise SmokeFailure("--max-attempts must be >= 1")

    client = Client(args.base_url, args.timeout)
    token = _bearer(args, client)
    claims = _token_payload(token)
    if not claims.get("jti"):
        raise SmokeFailure(
            "Quota smoke requires a durable account-mode token with jti; "
            "legacy shared-secret tokens are not valid for quota enforcement."
        )
    print(
        "quota token OK: "
        f"tenant={claims.get('tenant_id')} role={claims.get('role')} jti={claims.get('jti')}"
    )

    successes = 0
    for attempt in range(1, args.max_attempts + 1):
        resp = client.request(
            "POST",
            "/api/cas-harness/audit/session",
            token=token,
            body=_audit_payload(attempt, args),
        )
        if resp.status == 429:
            error = _detail_error(resp.body)
            if error != "quota_exceeded":
                raise SmokeFailure(
                    f"HTTP 429 did not carry detail.error == 'quota_exceeded': {resp.text}"
                )
            print(f"quota 429 OK after {attempt} attempt(s): {json.dumps(resp.body, sort_keys=True)}")
            print("HOSTED QUOTA SMOKE PASSED")
            return 0
        if resp.status == 200:
            successes += 1
            print(f"attempt {attempt}: audit session created; quota not exhausted yet")
            continue
        if resp.status in (401, 403):
            raise SmokeFailure(f"account-mode token refused before quota check ({resp.status}): {resp.text}")
        if resp.status == 503:
            raise SmokeFailure(
                "audit creation returned 503 before quota_exceeded. "
                "The hosted deployment may be missing account/quota startup wiring or a required audit preflight: "
                f"{resp.text}"
            )
        raise SmokeFailure(f"unexpected status before quota_exceeded ({resp.status}): {resp.text}")

    raise SmokeFailure(
        f"No quota_exceeded 429 after {args.max_attempts} attempts ({successes} successful creates). "
        "Either NC_QUOTAS_ENABLED is off, quota route wiring is absent, the tenant cap is higher than "
        "--max-attempts, or the deployed quota branch is not present."
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeFailure as exc:
        print(f"HOSTED QUOTA SMOKE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
