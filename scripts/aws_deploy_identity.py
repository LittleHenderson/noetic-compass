#!/usr/bin/env python3
"""Read and verify the AWS deployment identity.

This is the AWS half of the root-CI deploy evidence: the part that answers "is the commit CI
signed off the one actually serving traffic?". On Render the platform answered it directly —
a service id and a ``dep-`` deploy id. On AWS nothing answers it, so it is assembled from four
independent sources and they must agree:

  1. the running process      ``GET /deployment`` on the production origin
  2. the registry             the ECR image digest for the deployed tag
  3. the build record         the CodeBuild build that produced that image
  4. the repository           the protected ``master`` commit the caller expects

A mismatch is a failure, never a warning. The point of the check is that a released commit and
a running commit cannot silently differ.

This module is deliberately independent of the older Render collector: it holds no provider
credentials, performs no GitHub calls, and returns a plain record. The collector calls it for
the deployment half and keeps its own payload shape.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
REGION_RE = re.compile(r"^[a-z]{2}-[a-z]+-\d$")
MAX_RESPONSE_BYTES = 64 * 1024
DEFAULT_TIMEOUT_SECONDS = 20.0

# Fields the running service must report for the identity to count as configured.
REQUIRED_REPORTED_FIELDS = (
    "provider",
    "service_id",
    "service_name",
    "image_digest",
    "build_id",
    "commit_sha",
    "region",
)


class DeployIdentityError(RuntimeError):
    """A deployment identity check failed. Never downgraded to a warning."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DeployIdentityError(message)


def fetch_running_identity(
    deployment_url: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Read what the running service says it is.

    Strict by construction: bounded read, JSON object required, unknown shapes rejected.
    """
    _require(deployment_url.startswith("https://"), "deployment URL must be https")
    request = urllib.request.Request(
        deployment_url, headers={"Accept": "application/json", "Cache-Control": "no-store"}
    )
    try:
        with opener(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:  # pragma: no cover - transport detail
        raise DeployIdentityError(f"deployment endpoint returned HTTP {exc.code}") from exc
    except OSError as exc:  # pragma: no cover - transport detail
        raise DeployIdentityError(f"deployment endpoint unreachable: {exc.__class__.__name__}") from exc

    _require(len(raw) <= MAX_RESPONSE_BYTES, "deployment response exceeded the size limit")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DeployIdentityError("deployment response was not valid JSON") from exc
    _require(isinstance(payload, dict), "deployment response must be a JSON object")

    _require(payload.get("configured") is True, "deployment identity is not fully configured")
    for field in REQUIRED_REPORTED_FIELDS:
        value = payload.get(field)
        _require(
            isinstance(value, str) and value.strip() != "",
            f"deployment identity field {field!r} is missing or empty",
        )
    _require(payload["provider"] == "aws", "deployment provider is not aws")
    _require(
        DIGEST_RE.fullmatch(payload["image_digest"]) is not None,
        "reported image digest is not a sha256 digest",
    )
    _require(
        COMMIT_RE.fullmatch(payload["commit_sha"]) is not None,
        "reported commit is not a 40-character lowercase SHA",
    )
    _require(REGION_RE.fullmatch(payload["region"]) is not None, "reported region is malformed")
    return payload


def registry_digest(ecr: Any, repository: str, tag: str) -> str:
    """Return the digest the registry holds for a tag."""
    _require(bool(repository), "repository name is required")
    _require(bool(tag), "image tag is required")
    details = ecr.describe_images(repositoryName=repository, imageIds=[{"imageTag": tag}])
    images = details.get("imageDetails") or []
    _require(len(images) == 1, f"expected exactly one image for tag {tag!r}")
    digest = images[0].get("imageDigest")
    _require(
        isinstance(digest, str) and DIGEST_RE.fullmatch(digest) is not None,
        "registry returned a malformed image digest",
    )
    return digest


def build_record(codebuild: Any, build_id: str) -> Mapping[str, Any]:
    """Return the build record for a build id, requiring a successful build."""
    _require(bool(build_id), "build id is required")
    builds = codebuild.batch_get_builds(ids=[build_id]).get("builds") or []
    _require(len(builds) == 1, f"expected exactly one build for id {build_id!r}")
    build = builds[0]
    _require(
        build.get("buildStatus") == "SUCCEEDED",
        f"build {build_id!r} did not succeed (status {build.get('buildStatus')!r})",
    )
    return build


@dataclass(frozen=True)
class DeployFacts:
    """The verified deployment facts, as a plain record the collector can embed."""

    provider: str
    service_id: str
    service_name: str
    region: str
    image_digest: str
    build_id: str
    build_started_at: str | None
    commit_sha: str
    deployment_url: str

    def as_record(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "service_id": self.service_id,
            "service_name": self.service_name,
            "region": self.region,
            "image_digest": self.image_digest,
            "build_id": self.build_id,
            "build_started_at": self.build_started_at,
            "commit_sha": self.commit_sha,
            "deployment_url": self.deployment_url,
        }


def verify_deployment(
    *,
    running: Mapping[str, Any],
    registry_image_digest: str,
    expected_commit: str,
    build: Mapping[str, Any] | None,
    deployment_url: str,
) -> DeployFacts:
    """Check the four sources agree, or fail closed."""
    _require(
        COMMIT_RE.fullmatch(expected_commit) is not None,
        "expected commit must be a 40-character lowercase SHA",
    )
    _require(
        running.get("image_digest") == registry_image_digest,
        "the running image digest does not match the registry digest for the deployed tag",
    )
    _require(
        running.get("commit_sha") == expected_commit,
        "the running commit does not match the protected master commit",
    )
    if build is not None:
        started = build.get("startTime")
        _require(
            started is not None,
            "the build record has no start time, so provenance cannot be ordered",
        )
        build_id_reported = running.get("build_id")
        _require(
            build.get("id") == build_id_reported or build.get("arn", "").endswith(build_id_reported),
            "the running build id does not match the recorded build",
        )
    else:
        started = None

    return DeployFacts(
        provider=str(running["provider"]),
        service_id=str(running["service_id"]),
        service_name=str(running["service_name"]),
        region=str(running["region"]),
        image_digest=str(running["image_digest"]),
        build_id=str(running["build_id"]),
        build_started_at=str(started) if started is not None else None,
        commit_sha=str(running["commit_sha"]),
        deployment_url=deployment_url,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment-url", required=True)
    parser.add_argument("--repository", required=True, help="ECR repository name")
    parser.add_argument("--tag", required=True, help="deployed image tag")
    parser.add_argument("--expected-commit", required=True, help="protected master SHA")
    parser.add_argument("--region", default="us-west-2")
    args = parser.parse_args(argv)

    try:
        import boto3

        running = fetch_running_identity(args.deployment_url)
        digest = registry_digest(boto3.client("ecr", region_name=args.region), args.repository, args.tag)
        build = build_record(boto3.client("codebuild", region_name=args.region), running["build_id"])
        facts = verify_deployment(
            running=running,
            registry_image_digest=digest,
            expected_commit=args.expected_commit,
            build=build,
            deployment_url=args.deployment_url,
        )
    except DeployIdentityError as exc:
        print(f"deploy identity FAIL: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(facts.as_record(), indent=2, sort_keys=True))
    print("deploy identity PASS: running artifact, registry, build and protected commit agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
