"""Tests for the AWS deploy identity reader.

The whole value of this module is that it fails closed, so the tests concentrate on the ways a
deployment could disagree with itself: a registry digest that differs from the running digest,
a running commit that differs from the protected commit, an unconfigured endpoint, a build that
did not succeed, and a response that is malformed or oversized.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "aws_deploy_identity.py"

spec = importlib.util.spec_from_file_location("aws_deploy_identity", MODULE_PATH)
assert spec and spec.loader
aws = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = aws
spec.loader.exec_module(aws)

DIGEST = "sha256:" + "a" * 64
OTHER_DIGEST = "sha256:" + "b" * 64
COMMIT = "c" * 40
OTHER_COMMIT = "d" * 40

RUNNING = {
    "provider": "aws",
    "service_id": "i-0bd0a082507a51ae3",
    "service_name": "cas-harness-customer-api",
    "image_digest": DIGEST,
    "build_id": "nc-api-image-build:1234",
    "commit_sha": COMMIT,
    "region": "us-west-2",
    "configured": True,
}
BUILD = {"id": "nc-api-image-build:1234", "buildStatus": "SUCCEEDED", "startTime": "2026-09-25T23:21:51Z"}


class _Response(io.BytesIO):
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_: object) -> bool:
        return False


def opener_returning(payload: object, *, raw: bytes | None = None):
    body = raw if raw is not None else json.dumps(payload).encode()

    def _open(_request, timeout=None):  # noqa: ARG001
        return _Response(body)

    return _open


class FakeEcr:
    def __init__(self, digest: str) -> None:
        self._digest = digest

    def describe_images(self, **_: object) -> dict:
        return {"imageDetails": [{"imageDigest": self._digest}]}


class FakeCodeBuild:
    def __init__(self, status: str = "SUCCEEDED", start: str | None = "2026-09-25T23:21:51Z") -> None:
        self._status = status
        self._start = start

    def batch_get_builds(self, **_: object) -> dict:
        record = {"id": "nc-api-image-build:1234", "buildStatus": self._status}
        if self._start is not None:
            record["startTime"] = self._start
        return {"builds": [record]}


class FetchRunningIdentityTests(unittest.TestCase):
    def test_reads_a_well_formed_identity(self) -> None:
        payload = aws.fetch_running_identity(
            "https://example.test/deployment", opener=opener_returning(RUNNING)
        )
        self.assertEqual(payload["image_digest"], DIGEST)

    def test_rejects_an_unconfigured_deployment(self) -> None:
        body = dict(RUNNING, configured=False)
        with self.assertRaises(aws.DeployIdentityError) as ctx:
            aws.fetch_running_identity("https://example.test/deployment", opener=opener_returning(body))
        self.assertIn("not fully configured", str(ctx.exception))

    def test_rejects_a_missing_field(self) -> None:
        body = dict(RUNNING)
        del body["image_digest"]
        with self.assertRaises(aws.DeployIdentityError):
            aws.fetch_running_identity("https://example.test/deployment", opener=opener_returning(body))

    def test_rejects_a_malformed_digest(self) -> None:
        body = dict(RUNNING, image_digest="not-a-digest")
        with self.assertRaises(aws.DeployIdentityError):
            aws.fetch_running_identity("https://example.test/deployment", opener=opener_returning(body))

    def test_rejects_a_non_aws_provider(self) -> None:
        body = dict(RUNNING, provider="render")
        with self.assertRaises(aws.DeployIdentityError):
            aws.fetch_running_identity("https://example.test/deployment", opener=opener_returning(body))

    def test_rejects_invalid_json(self) -> None:
        with self.assertRaises(aws.DeployIdentityError):
            aws.fetch_running_identity(
                "https://example.test/deployment", opener=opener_returning(None, raw=b"<html>")
            )

    def test_rejects_an_oversized_response(self) -> None:
        big = json.dumps(dict(RUNNING, padding="x" * (aws.MAX_RESPONSE_BYTES + 10))).encode()
        with self.assertRaises(aws.DeployIdentityError) as ctx:
            aws.fetch_running_identity("https://example.test/deployment", opener=opener_returning(None, raw=big))
        self.assertIn("size limit", str(ctx.exception))

    def test_requires_https(self) -> None:
        with self.assertRaises(aws.DeployIdentityError):
            aws.fetch_running_identity("http://example.test/deployment", opener=opener_returning(RUNNING))


class RegistryAndBuildTests(unittest.TestCase):
    def test_registry_digest_returns_the_tag_digest(self) -> None:
        self.assertEqual(aws.registry_digest(FakeEcr(DIGEST), "repo", "v1"), DIGEST)

    def test_registry_requires_exactly_one_image(self) -> None:
        class Empty:
            def describe_images(self, **_: object) -> dict:
                return {"imageDetails": []}

        with self.assertRaises(aws.DeployIdentityError):
            aws.registry_digest(Empty(), "repo", "v1")

    def test_build_record_requires_success(self) -> None:
        with self.assertRaises(aws.DeployIdentityError) as ctx:
            aws.build_record(FakeCodeBuild(status="FAILED"), "nc-api-image-build:1234")
        self.assertIn("did not succeed", str(ctx.exception))

    def test_build_record_accepts_a_successful_build(self) -> None:
        record = aws.build_record(FakeCodeBuild(), "nc-api-image-build:1234")
        self.assertEqual(record["buildStatus"], "SUCCEEDED")


class VerifyDeploymentTests(unittest.TestCase):
    def _verify(self, **overrides):
        kwargs = {
            "running": RUNNING,
            "registry_image_digest": DIGEST,
            "expected_commit": COMMIT,
            "build": BUILD,
            "deployment_url": "https://api.noeticcompass.com/deployment",
        }
        kwargs.update(overrides)
        return aws.verify_deployment(**kwargs)

    def test_agreement_produces_facts(self) -> None:
        facts = self._verify()
        self.assertEqual(facts.image_digest, DIGEST)
        self.assertEqual(facts.commit_sha, COMMIT)
        record = facts.as_record()
        self.assertEqual(record["service_id"], "i-0bd0a082507a51ae3")
        self.assertEqual(record["build_started_at"], "2026-09-25T23:21:51Z")

    def test_digest_mismatch_fails(self) -> None:
        with self.assertRaises(aws.DeployIdentityError) as ctx:
            self._verify(registry_image_digest=OTHER_DIGEST)
        self.assertIn("does not match the registry digest", str(ctx.exception))

    def test_commit_mismatch_fails(self) -> None:
        # This is the exact condition the gate exists to catch: CI signed off one commit and a
        # different one is serving traffic.
        with self.assertRaises(aws.DeployIdentityError) as ctx:
            self._verify(expected_commit=OTHER_COMMIT)
        self.assertIn("does not match the protected master commit", str(ctx.exception))

    def test_malformed_expected_commit_fails_before_comparison(self) -> None:
        with self.assertRaises(aws.DeployIdentityError):
            self._verify(expected_commit="HEAD")

    def test_build_without_a_start_time_fails(self) -> None:
        with self.assertRaises(aws.DeployIdentityError) as ctx:
            self._verify(build={"id": "nc-api-image-build:1234", "buildStatus": "SUCCEEDED"})
        self.assertIn("no start time", str(ctx.exception))

    def test_build_id_mismatch_fails(self) -> None:
        with self.assertRaises(aws.DeployIdentityError) as ctx:
            self._verify(build={"id": "some-other-build", "buildStatus": "SUCCEEDED", "startTime": "x"})
        self.assertIn("does not match the recorded build", str(ctx.exception))

    def test_missing_build_record_still_verifies_the_rest(self) -> None:
        facts = self._verify(build=None)
        self.assertIsNone(facts.build_started_at)


if __name__ == "__main__":
    unittest.main()
