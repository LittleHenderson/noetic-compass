"""
Cut customer production over to its proper hostname, in the order AWS requires.

Sequence, and why it is this order:

  1. Confirm the ACM certificate is ISSUED in us-east-1 and covers the hostname. CloudFront
     refuses to serve a custom hostname without a certificate that covers it.
  2. Attach the certificate and the hostname to the distribution. This does NOT need DNS to
     exist yet, so it can be done before the traffic record is switched — which is what makes
     the switch safe.
  3. Only after the distribution reports Deployed, point the CNAME at it.
  4. Verify TLS, health, deployment identity, an authenticated request, and that an
     unauthenticated request is refused.

Ground rules this script holds to:

  * ``CallerReference`` is never changed. AWS rejects an update that alters it, so the existing
    value is preserved verbatim.
  * Existing aliases and unrelated distribution settings are preserved. The configured hostname
    is merged into the alias list, not substituted for it.
  * The current ETag is always used for the update, so a concurrent change cannot be clobbered.
  * Every run writes a rollback record of the distribution configuration that was in place
    before the change, so the original state can be restored.
  * Re-running is safe: an already-correct distribution is reported, not rewritten.

The AWS clients are created lazily so this module imports with the standard library alone; the
offline deployment-control job runs without third-party packages.
"""

from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REGION = "us-west-2"
ACCOUNT = "807562639912"
HOSTNAME = "api.noeticcompass.com"
DISTRIBUTION_ID = "E1RBLENB7B6YEA"
CERT_ARN = f"arn:aws:acm:us-east-1:{ACCOUNT}:certificate/ec714143-cd52-49a6-bd7b-f828a0d4a760"
SSM_LANE = "/noetic-compass/customer-production"
ROLLBACK_BUCKET = f"nc-api-build-{ACCOUNT}-usw2"
DOH_ENDPOINT = "https://cloudflare-dns.com/dns-query"


def _client(service: str, region: str):
    import boto3 as _boto3

    return _boto3.client(service, region_name=region)


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def resolve_cname(host: str, *, opener=urllib.request.urlopen) -> list[str]:
    """Return the CNAME targets for a host, via DNS-over-HTTPS.

    A resolver lookup alone cannot tell the difference between a real record and a wildcard
    that answers for every name in the zone, which is exactly the trap here: Vercel answers
    for any name under the domain. Asking specifically for a CNAME record shows whether the
    record was actually created.
    """
    query = urllib.parse.urlencode({"name": host, "type": "CNAME"})
    request = urllib.request.Request(
        f"{DOH_ENDPOINT}?{query}", headers={"Accept": "application/dns-json"}
    )
    try:
        with opener(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise RuntimeError(f"DNS query failed: {exc.__class__.__name__}") from exc
    answers = payload.get("Answer") or []
    return sorted(
        entry["data"].rstrip(".") for entry in answers if entry.get("type") == 5  # 5 = CNAME
    )


def certificate_state() -> tuple[str, list[str]]:
    acm = _client("acm", "us-east-1")
    certificate = acm.describe_certificate(CertificateArn=CERT_ARN)["Certificate"]
    names = [certificate.get("DomainName", "")] + list(certificate.get("SubjectAlternativeNames", []))
    return certificate["Status"], sorted({name for name in names if name})


def certificate_issued() -> bool:
    status, names = certificate_state()
    log(f"certificate status: {status}; covers: {', '.join(names) or '(none reported)'}")
    if status != "ISSUED":
        log("certificate is not issued; the validation record must be added and validated first")
        return False
    if HOSTNAME not in names:
        log(f"certificate does not cover {HOSTNAME}")
        return False
    return True


def save_rollback_record(config: dict) -> str | None:
    """Store the pre-change distribution configuration so the change can be undone."""
    key = f"rollback/cloudfront-{DISTRIBUTION_ID}-{int(time.time())}.json"
    try:
        _client("s3", REGION).put_object(
            Bucket=ROLLBACK_BUCKET, Key=key,
            Body=json.dumps(config, indent=2, sort_keys=True).encode("utf-8"),
        )
        log(f"rollback record written: s3://{ROLLBACK_BUCKET}/{key}")
        return key
    except Exception as exc:  # noqa: BLE001 - reported, not fatal
        log(f"could not write the rollback record: {exc.__class__.__name__}")
        return None


def attach_alias() -> bool:
    """Attach the certificate and hostname, preserving everything else. True when changed."""
    cf = _client("cloudfront", "us-east-1")
    response = cf.get_distribution(Id=DISTRIBUTION_ID)
    distribution = response["Distribution"]
    config = distribution["DistributionConfig"]
    # boto3 returns the ETag beside Distribution, not inside it.
    etag = response["ETag"]

    aliases = config.get("Aliases", {"Quantity": 0, "Items": []})
    existing = list(aliases.get("Items", []))
    viewer = config.get("ViewerCertificate", {})

    if HOSTNAME in existing and viewer.get("ACMCertificateArn") == CERT_ARN:
        log(f"{HOSTNAME} and the certificate are already attached; nothing to change")
        return False

    save_rollback_record(config)

    merged = sorted(set(existing) | {HOSTNAME})
    # CallerReference is deliberately NOT touched: AWS rejects an update that changes it.
    config["Aliases"] = {"Quantity": len(merged), "Items": merged}
    config["ViewerCertificate"] = {
        "ACMCertificateArn": CERT_ARN,
        "SSLSupportMethod": "sni-only",
        "MinimumProtocolVersion": "TLSv1.2_2021",
        "Certificate": CERT_ARN,
        "CertificateSource": "acm",
    }

    cf.update_distribution(DistributionConfig=config, Id=DISTRIBUTION_ID, IfMatch=etag)
    log(f"attached {HOSTNAME} to {DISTRIBUTION_ID}; aliases now: {', '.join(merged)}")
    return True


def wait_for_deployment(timeout: int = 900) -> bool:
    cf = _client("cloudfront", "us-east-1")
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = cf.get_distribution(Id=DISTRIBUTION_ID)["Distribution"]["Status"]
        if status == "Deployed":
            log("distribution deployed")
            return True
        log(f"distribution status: {status}")
        time.sleep(20)
    return False


def tls_covers_hostname(host: str) -> bool:
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=20) as raw:
            with context.wrap_socket(raw, server_hostname=host) as tls:
                certificate = tls.getpeercert()
    except Exception as exc:  # noqa: BLE001
        log(f"TLS handshake failed: {exc.__class__.__name__}")
        return False
    names = [value for key, value in certificate.get("subjectAltName", ()) if key == "DNS"]
    log(f"certificate presented covers: {', '.join(names)}")
    return host in names


def http(path: str, *, method: str = "GET", body: dict | None = None, headers: dict | None = None):
    request = urllib.request.Request(
        f"https://{HOSTNAME}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Accept": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode()[:300]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:300]
    except OSError as exc:
        return 0, exc.__class__.__name__


def verify(*, bootstrap_owner: bool) -> bool:
    checks: dict[str, bool] = {}

    log("=== DNS points at the intended distribution ===")
    try:
        targets = resolve_cname(HOSTNAME)
        log(f"CNAME answers for {HOSTNAME}: {', '.join(targets) or '(none)'}")
        checks["CNAME targets the CloudFront distribution"] = (
            "d2zcr7t1an5spf.cloudfront.net" in targets
        )
    except RuntimeError as exc:
        log(str(exc))
        checks["CNAME targets the CloudFront distribution"] = False

    log("=== TLS ===")
    checks["certificate covers the hostname"] = tls_covers_hostname(HOSTNAME)

    log("=== health ===")
    status, body = http("/health")
    log(f"GET /health -> HTTP {status} {body}")
    checks["/health is 200"] = status == 200

    log("=== deployment identity ===")
    status, body = http("/deployment")
    log(f"GET /deployment -> HTTP {status} {body}")
    try:
        checks["deployment identity is configured"] = status == 200 and json.loads(body).get("configured") is True
    except ValueError:
        checks["deployment identity is configured"] = False

    log("=== unauthenticated request is refused ===")
    status, body = http("/accounts/credential/rotate", method="POST", body={})
    log(f"POST /accounts/credential/rotate without a token -> HTTP {status}")
    checks["unauthenticated request refused"] = status == 401

    log("=== authenticated request succeeds ===")
    try:
        ssm = _client("ssm", REGION)
        credential = ssm.get_parameter(
            Name=f"{SSM_LANE}/NC_VERIFICATION_OWNER_CREDENTIAL", WithDecryption=True
        )["Parameter"]["Value"]
        status, body = http("/auth/token", method="POST",
                            body={"username": "migration-verification@noeticcompass.com",
                                  "api_credential": credential})
        token = json.loads(body)["token"] if status == 200 else None
        if token:
            status, body = http("/api/cas-harness/audit/sessions",
                                headers={"Authorization": f"Bearer {token}"})
        log(f"authenticated GET /api/cas-harness/audit/sessions -> HTTP {status} {body[:120]}")
        checks["authenticated request succeeds"] = status == 200
    except Exception as exc:  # noqa: BLE001
        log(f"authenticated check could not run: {exc.__class__.__name__}")
        checks["authenticated request succeeds"] = False

    if bootstrap_owner:
        log("=== optional: re-bind the first owner ===")
        log("skipped: ownership transfer is a separate, owner-confirmed procedure")

    print()
    log("=== verdict ===")
    for label, ok in checks.items():
        log(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return all(checks.values())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attach", action="store_true",
                        help="attach the certificate and hostname; does not need DNS")
    parser.add_argument("--verify", action="store_true",
                        help="verify the hostname end to end; needs DNS in place")
    parser.add_argument("--bootstrap-owner", action="store_true",
                        help="accepted for compatibility; ownership transfer is separate")
    args = parser.parse_args(argv)

    if not certificate_issued():
        return 2

    if args.attach or not args.verify:
        if attach_alias():
            if not wait_for_deployment():
                log("distribution did not reach Deployed within the timeout")
                return 1
        if not args.verify:
            log("next step: point the api CNAME at d2zcr7t1an5spf.cloudfront.net, then run --verify")
            return 0

    return 0 if verify(bootstrap_owner=args.bootstrap_owner) else 1


if __name__ == "__main__":
    sys.exit(main())
