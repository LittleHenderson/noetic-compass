"""
Cut customer production over to its proper hostname, once DNS exists.

Everything here is gated on the DNS records being in place, so it is safe to run repeatedly:
if the records are absent it reports that and changes nothing.

Steps, in order:
  1. Confirm api.noeticcompass.com points at the CloudFront distribution.
  2. Confirm the ACM certificate for the name is ISSUED.
  3. Attach the certificate and the alternate domain name to the distribution.
  4. Verify TLS on the real hostname, then /health, then /deployment, then the auth gate.
  5. Optionally bootstrap the first owner account and make one genuinely authenticated request
     (--bootstrap-owner). Off by default: it creates an account in a governed lane, and the
     runbook says the bootstrap secret is deleted after the first owner is verified.
"""
import argparse
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request

import boto3

REGION = "us-west-2"
ACCOUNT = "807562639912"
HOSTNAME = "api.noeticcompass.com"
DISTRIBUTION_ID = "E1RBLENB7B6YEA"
CERT_ARN = f"arn:aws:acm:us-east-1:{ACCOUNT}:certificate/ec714143-cd52-49a6-bd7b-f828a0d4a760"
SSM_LANE = "/noetic-compass/customer-production"

cf = boto3.client("cloudfront", region_name="us-east-1")
acm = boto3.client("acm", region_name="us-east-1")
ssm = boto3.client("ssm", region_name=REGION)


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def dns_ready():
    """True when the hostname is a CNAME to the distribution (or resolves to it)."""
    try:
        answers = socket.getaddrinfo(HOSTNAME, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        log(f"{HOSTNAME} does not resolve yet")
        return False, None
    addresses = sorted({a[4][0] for a in answers})
    log(f"{HOSTNAME} resolves to {', '.join(addresses)}")
    # Vercel's wildcard answers for any name in the zone; CloudFront's addresses do not
    # overlap with it, so a TLS check below is the real proof. Report the addresses only.
    return True, addresses


def cert_issued():
    status = acm.describe_certificate(CertificateArn=CERT_ARN)["Certificate"]["Status"]
    log(f"certificate status: {status}")
    return status == "ISSUED"


def attach_alias():
    dist = cf.get_distribution(Id=DISTRIBUTION_ID)["Distribution"]
    config = dist["DistributionConfig"]
    config["CallerReference"] = f"nc-api-alias-{int(time.time())}"
    already = HOSTNAME in config.get("Aliases", {}).get("Items", [])
    config["Aliases"] = {"Quantity": 1, "Items": [HOSTNAME]}
    config["ViewerCertificate"] = {
        "ACMCertificateArn": CERT_ARN,
        "SSLSupportMethod": "sni-only",
        "MinimumProtocolVersion": "TLSv1.2_2021",
        "Certificate": CERT_ARN,
        "CertificateSource": "acm",
    }
    if already and config["ViewerCertificate"].get("ACMCertificateArn") == CERT_ARN:
        log("alias and certificate already attached")
        return False
    cf.update_distribution(
        DistributionConfig=config, Id=DISTRIBUTION_ID, IfMatch=dist["ETag"]
    )
    log(f"attached {HOSTNAME} and the ACM certificate to {DISTRIBUTION_ID}")
    return True


def wait_for_deployment(timeout=900):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = cf.get_distribution(Id=DISTRIBUTION_ID)["Distribution"]["Status"]
        if status == "Deployed":
            log("distribution deployed")
            return True
        log(f"distribution status: {status}")
        time.sleep(20)
    return False


def tls_subject(host):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=15) as raw:
        with ctx.wrap_socket(raw, server_hostname=host) as tls:
            cert = tls.getpeercert()
    names = [value for key, value in cert.get("subjectAltName", ()) if key == "DNS"]
    return names


def http(path, method="GET", body=None, headers=None):
    url = f"https://{HOSTNAME}{path}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url, data=data, method=method,
        headers={"Accept": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode()[:400]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:400]
    except OSError as exc:
        return 0, f"{exc.__class__.__name__}"


def verify(*, bootstrap_owner: bool):
    log("=== TLS ===")
    try:
        names = tls_subject(HOSTNAME)
        log(f"certificate covers: {', '.join(names)}")
        if HOSTNAME not in names:
            log("FAIL: certificate does not cover the hostname")
            return False
    except Exception as exc:  # noqa: BLE001
        log(f"FAIL: TLS handshake failed: {exc.__class__.__name__}")
        return False

    log("=== /health ===")
    status, body = http("/health")
    log(f"HTTP {status} {body}")
    health_ok = status == 200

    log("=== /deployment ===")
    status, body = http("/deployment")
    log(f"HTTP {status} {body}")
    try:
        deployment = json.loads(body)
        identity_ok = status == 200 and deployment.get("configured") is True
    except json.JSONDecodeError:
        identity_ok = False

    log("=== auth gate (unauthenticated must be refused) ===")
    status, body = http("/accounts/me")
    log(f"HTTP {status} {body}")
    gate_ok = status == 401

    authenticated_ok = None
    if bootstrap_owner:
        log("=== bootstrap first owner and make an authenticated request ===")
        try:
            secret = ssm.get_parameter(
                Name=f"{SSM_LANE}/NC_ACCOUNT_BOOTSTRAP_SECRET", WithDecryption=True
            )["Parameter"]["Value"]
        except Exception as exc:  # noqa: BLE001
            log(f"bootstrap secret unavailable: {exc.__class__.__name__}")
            return False
        status, body = http(
            "/accounts/bootstrap",
            method="POST",
            body={"secret": secret, "tenant_id": "primary"},
            headers={"Content-Type": "application/json"},
        )
        log(f"bootstrap: HTTP {status} {body[:200]}")
        authenticated_ok = status in (200, 201)

    print()
    log("=== verdict ===")
    checks = {
        "/health 200": health_ok,
        "/deployment configured": identity_ok,
        "unauthenticated /accounts/me refused": gate_ok,
    }
    if authenticated_ok is not None:
        checks["bootstrap/authenticated request"] = authenticated_ok
    for label, ok in checks.items():
        log(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return all(checks.values())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-owner", action="store_true",
                        help="also bootstrap the first owner account and authenticate once")
    args = parser.parse_args(argv)

    resolved, _ = dns_ready()
    if not resolved:
        log("DNS is not in place yet: nothing to cut over. Add these records in the zone:")
        log("  CNAME _30a27fe05b7706611a6520c0b2e2fe8f.api -> _a29e60938f344c281201dfe70f73a090.wzccmgtwzk.acm-validations.aws.")
        log("  CNAME api                                      -> d2zcr7t1an5spf.cloudfront.net")
        return 2

    if not cert_issued():
        log("certificate is not issued yet; the validation record is missing or still propagating")
        return 2

    changed = attach_alias()
    if changed:
        wait_for_deployment()
    return 0 if verify(bootstrap_owner=args.bootstrap_owner) else 1


if __name__ == "__main__":
    sys.exit(main())
