#!/usr/bin/env python3
"""Fail-closed checks for the repository's AWS deployment control.

This is the counterpart to ``scripts/verify_render_blueprint_control.py``. Production
moved from Render to AWS, so the AWS control manifest, not the Render blueprints, now
states where production runs.

Two modes:

* ``--offline`` (default in CI): standard library only. Validates the manifest's shape,
  its internal consistency, and the deployment invariants that must never silently
  change - the canary stays private, both databases stay non-public, no static AWS keys,
  every lane names an image tag, a health path, and a secret store. It also fails if the
  production runbook disagrees with the manifest about the production API origin.
* ``--live``: uses boto3 and requires AWS credentials. Compares the manifest against the
  real resources. This is the check that proves the declared state is the actual state;
  run it before any production claim.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

REPOSITORY = "LittleHenderson/noetic-compass"
MANIFEST_PATH = Path(".aws/deployment-control.json")
RUNBOOK_PATH = Path(
    "noetic-compass-scaffold/noetic-compass/docs/runbooks/customer_production_acceptance.md"
)
EXPECTED_ACCOUNT = "807562639912"
EXPECTED_REGION = "us-west-2"
EXPECTED_LANES = ["accounts-off", "customer-production", "accounts-canary", "atlas-viewer"]

# Values that must never be committed into a control manifest.
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"base64url:[A-Za-z0-9_-]{20,}"),
]
ORIGIN_PATTERN = re.compile(r"^https://[a-z0-9.-]+$")


class ControlError(RuntimeError):
    """A control invariant failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ControlError(message)


def load_manifest(repo_root: Path) -> dict[str, Any]:
    path = repo_root / MANIFEST_PATH
    _require(path.is_file(), f"Missing AWS control manifest: {MANIFEST_PATH.as_posix()}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ControlError(f"Cannot parse {MANIFEST_PATH.as_posix()}: {exc}") from exc
    _require(isinstance(manifest, dict), "AWS control manifest root must be an object")
    return manifest


def assert_no_secret_literals(text: str, label: str) -> None:
    for pattern in SECRET_PATTERNS:
        _require(
            pattern.search(text) is None,
            f"{label} contains what looks like a committed secret ({pattern.pattern})",
        )


def validate_manifest(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    expected_keys = {
        "schemaVersion", "repository", "provider", "account", "region", "migratedFrom",
        "migrationRecord", "authority", "imageRepository", "imageBuild", "lanes", "superseded",
    }
    _require(set(manifest) == expected_keys, "AWS control manifest has missing or unknown fields")
    _require(manifest["schemaVersion"] == 1, "AWS control manifest schemaVersion must be 1")
    _require(manifest["repository"] == REPOSITORY, "AWS control manifest repository drifted")
    _require(manifest["provider"] == "aws", "AWS control manifest provider must be aws")
    _require(manifest["account"] == EXPECTED_ACCOUNT, "AWS account drifted")
    _require(manifest["region"] == EXPECTED_REGION, "AWS region drifted")
    _require(manifest["migratedFrom"] == "render", "migratedFrom must record the Render origin")

    import os

    record = os.path.normpath(str(manifest["migrationRecord"]))
    _require(not record.startswith(".."), "migrationRecord must be repository-relative")

    lanes = manifest["lanes"]
    _require(isinstance(lanes, list), "lanes must be a list")
    names = [lane.get("name") for lane in lanes]
    _require(names == EXPECTED_LANES, f"lanes must be exactly {EXPECTED_LANES}, found {names}")

    for lane in lanes:
        label = f"lane {lane['name']}"
        for field in ("kind", "branch", "imageTag", "healthCheckPath", "publicIngress"):
            _require(field in lane, f"{label} is missing {field}")
        _require(lane["healthCheckPath"].startswith("/"), f"{label} healthCheckPath must be a path")
        if lane["kind"] != "s3-cloudfront":
            _require(bool(str(lane["imageTag"]).strip()), f"{label} must pin an imageTag")
        if lane["publicIngress"]:
            origin = lane.get("publicOrigin")
            _require(
                isinstance(origin, str) and ORIGIN_PATTERN.match(origin) is not None,
                f"{label} must declare an https publicOrigin when publicIngress is true",
            )
        else:
            _require(
                lane.get("publicOrigin") is None,
                f"{label} is not public and must not declare a publicOrigin",
            )
        if "database" in lane:
            db = lane["database"]
            _require(
                db.get("publiclyAccessible") is False,
                f"{label} database must not be publicly accessible",
            )
            _require(
                db.get("engine") == "postgres" and "majorVersion" in db,
                f"{label} database must declare a postgres engine and major version",
            )
        if lane["kind"] in ("ec2-cloudfront", "ec2-private"):
            _require(
                lane.get("staticAwsKeys") is False,
                f"{label} must not use static AWS keys; use an instance role",
            )
            _require(bool(lane.get("secretStore")), f"{label} must name a secret store path")

    by_name = {lane["name"]: lane for lane in lanes}
    canary = by_name["accounts-canary"]
    _require(
        canary["publicIngress"] is False,
        "accounts-canary must stay private; it was a private service on Render",
    )
    _require(
        canary.get("adminAccess") == "ssm-session-manager",
        "accounts-canary must document SSM Session Manager as its only access path",
    )
    customer = by_name["customer-production"]
    _require(
        customer.get("ingressLimitedTo") == "cloudfront-origin-facing",
        "customer-production ingress must be limited to CloudFront's origin-facing ranges",
    )

    authority = manifest["authority"]
    origin = authority["productionApiOrigin"]
    _require(ORIGIN_PATTERN.match(origin) is not None, "productionApiOrigin must be an https origin")
    _require(
        customer["publicOrigin"] == origin,
        "productionApiOrigin must equal the customer-production lane's publicOrigin",
    )
    _require(
        authority["originFrontDomain"] in {"d2zcr7t1an5spf.cloudfront.net"},
        "originFrontDomain must name the live CloudFront domain",
    )

    # The Atlas viewer consumes the production API. Its declared base must be the
    # production origin, so the console can never be wired to a stale or temporary host.
    atlas = by_name["atlas-viewer"]
    _require(bool(atlas.get("bucket")), "atlas-viewer must name its bucket")
    _require(bool(atlas.get("distributionId")), "atlas-viewer must name its distribution")
    atlas_base = str(atlas.get("apiBaseUrl", ""))
    _require(
        atlas_base.startswith(origin + "/") or atlas_base == origin,
        f"atlas-viewer apiBaseUrl must be under the production origin {origin}, found {atlas_base!r}",
    )
    _require(
        atlas.get("staticAwsKeys") is False,
        "atlas-viewer must not use static AWS keys; CloudFront reads the bucket by origin access control",
    )

    superseded = manifest["superseded"]
    _require(
        all(item.get("authoritative") is False for item in superseded),
        "every superseded provider entry must be marked authoritative: false",
    )
    _require(
        all(item.get("provider") == "render" for item in superseded),
        "superseded entries must name the provider they came from",
    )
    return lanes


def validate_runbook_agreement(repo_root: Path, manifest: Mapping[str, Any]) -> None:
    path = repo_root / RUNBOOK_PATH
    _require(path.is_file(), f"Missing production runbook: {RUNBOOK_PATH.as_posix()}")
    text = path.read_text(encoding="utf-8")
    origin = manifest["authority"]["productionApiOrigin"]
    _require(
        origin in text,
        f"{RUNBOOK_PATH.as_posix()} must state the declared production API origin {origin}",
    )
    # The runbook may record the Render lane historically, but only below a heading that
    # marks it superseded. Above that heading it must not present Render as production.
    cut = len(text)
    for heading in re.finditer(r"(?m)^#{2,}\s+.*$", text):
        if re.search(r"superseded|migration from render", heading.group(0), re.IGNORECASE):
            cut = heading.start()
            break
    current = text[:cut]
    _require(
        "cas-harness-customer-api.onrender.com" not in current,
        "the runbook must not present the Render host as current production authority",
    )


def offline(repo_root: Path) -> None:
    manifest = load_manifest(repo_root)
    assert_no_secret_literals(json.dumps(manifest, sort_keys=True), MANIFEST_PATH.as_posix())
    lanes = validate_manifest(manifest)
    validate_runbook_agreement(repo_root, manifest)
    print(
        f"offline AWS deployment control PASS: {len(lanes)} lanes, "
        f"production origin {manifest['authority']['productionApiOrigin']}, "
        f"{len(manifest['superseded'])} superseded provider entries"
    )


def live(repo_root: Path) -> None:
    import boto3  # imported lazily so offline mode needs no third-party packages

    manifest = load_manifest(repo_root)
    validate_manifest(manifest)
    region = manifest["region"]
    by_name = {lane["name"]: lane for lane in manifest["lanes"]}
    failures: list[str] = []

    apprunner = boto3.client("apprunner", region_name=region)
    summary = [
        s for s in apprunner.list_services()["ServiceSummaryList"]
        if s["ServiceArn"] == by_name["accounts-off"]["serviceArn"]
    ]
    if not summary:
        failures.append("accounts-off: App Runner service not found")
    else:
        detail = apprunner.describe_service(ServiceArn=summary[0]["ServiceArn"])["Service"]
        if detail["Status"] != "RUNNING":
            failures.append(f"accounts-off: status is {detail['Status']}, expected RUNNING")
        expected_host = by_name["accounts-off"]["publicOrigin"].removeprefix("https://")
        if detail.get("ServiceUrl") != expected_host:
            failures.append(
                f"accounts-off: ServiceUrl {detail.get('ServiceUrl')} != manifest {expected_host}"
            )

    ec2 = boto3.client("ec2", region_name=region)
    for name in ("customer-production", "accounts-canary"):
        lane = by_name[name]
        found = ec2.describe_instances(InstanceIds=[lane["instanceId"]])["Reservations"]
        if not found:
            failures.append(f"{name}: instance {lane['instanceId']} not found")
            continue
        inst = found[0]["Instances"][0]
        if inst["State"]["Name"] != "running":
            failures.append(f"{name}: instance state is {inst['State']['Name']}")
        if inst["InstanceType"] != lane["instanceType"]:
            failures.append(f"{name}: instance type {inst['InstanceType']} != {lane['instanceType']}")
        for group in inst["SecurityGroups"]:
            sg = ec2.describe_security_groups(GroupIds=[group["GroupId"]])["SecurityGroups"][0]
            rules = len(sg["IpPermissions"])
            if lane["publicIngress"] is False and rules != 0:
                failures.append(
                    f"{name}: {group['GroupId']} has {rules} inbound rules but the lane must be private"
                )

    rds = boto3.client("rds", region_name=region)
    for name in ("customer-production", "accounts-canary"):
        lane = by_name[name]
        ident = lane["database"]["identifier"]
        try:
            db = rds.describe_db_instances(DBInstanceIdentifier=ident)["DBInstances"][0]
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            failures.append(f"{name}: database {ident} not readable ({exc.__class__.__name__})")
            continue
        if db["DBInstanceStatus"] != "available":
            failures.append(f"{name}: database status {db['DBInstanceStatus']}")
        if db["PubliclyAccessible"]:
            failures.append(f"{name}: database {ident} is publicly accessible")
        if db["DBName"] != lane["database"]["databaseName"]:
            failures.append(f"{name}: database name {db['DBName']} != {lane['database']['databaseName']}")

    cf = boto3.client("cloudfront", region_name="us-east-1")
    try:
        dist = cf.get_distribution(Id=by_name["customer-production"]["distributionId"])["Distribution"]
        if not dist["DistributionConfig"]["Enabled"]:
            failures.append("customer-production: CloudFront distribution is disabled")
        if dist["DomainName"] != manifest["authority"]["originFrontDomain"]:
            failures.append("customer-production: CloudFront domain drifted from the manifest")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"customer-production: CloudFront not readable ({exc.__class__.__name__})")

    if failures:
        for item in failures:
            print(f"live AWS deployment control FAIL: {item}", file=sys.stderr)
        raise ControlError(f"{len(failures)} live control failure(s)")
    print(
        f"live AWS deployment control PASS: {len(manifest['lanes'])} lanes match the manifest "
        f"in {region} account {manifest['account']}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="repository-only checks")
    mode.add_argument("--live", action="store_true", help="compare against real AWS resources")
    parser.add_argument("--repo-root", default=".", help="repository root")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        if args.live:
            live(root)
        else:
            offline(root)
    except ControlError as exc:
        print(f"AWS deployment control FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
