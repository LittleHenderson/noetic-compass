"""Tests for the deployment identity endpoint.

The endpoint exists so the root-CI deploy evidence collector can ask a running service which
artifact, build, and commit it is. Two properties matter and both are asserted here: it
reports exactly what the environment says, and it fails visibly (nulls, configured=false)
rather than guessing when the deployment did not inject the identifiers.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from api.main import app

VARS = {
    "NC_DEPLOYMENT_PROVIDER": "aws",
    "NC_DEPLOYMENT_SERVICE_ID": "i-0bd0a082507a51ae3",
    "NC_DEPLOYMENT_SERVICE_NAME": "cas-harness-customer-api",
    "NC_DEPLOYMENT_IMAGE_DIGEST": "sha256:" + "a" * 64,
    "NC_DEPLOYMENT_BUILD_ID": "nc-api-image-build:1234",
    "NC_BUILD_COMMIT_SHA": "b" * 40,
    "NC_DEPLOYMENT_REGION": "us-west-2",
}


class DeploymentIdentityTests(unittest.TestCase):
    def test_reports_the_injected_identity(self) -> None:
        with mock.patch.dict(os.environ, VARS, clear=False):
            with TestClient(app) as client:
                response = client.get("/deployment")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["configured"])
        for name, expected in (
            ("provider", VARS["NC_DEPLOYMENT_PROVIDER"]),
            ("service_id", VARS["NC_DEPLOYMENT_SERVICE_ID"]),
            ("image_digest", VARS["NC_DEPLOYMENT_IMAGE_DIGEST"]),
            ("build_id", VARS["NC_DEPLOYMENT_BUILD_ID"]),
            ("commit_sha", VARS["NC_BUILD_COMMIT_SHA"]),
            ("region", VARS["NC_DEPLOYMENT_REGION"]),
        ):
            self.assertEqual(body[name], expected, name)

    def test_reports_nulls_and_unconfigured_when_nothing_is_injected(self) -> None:
        cleared = {key: "" for key in VARS}
        with mock.patch.dict(os.environ, cleared, clear=False):
            with TestClient(app) as client:
                response = client.get("/deployment")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["configured"])
        for name in ("provider", "service_id", "image_digest", "commit_sha"):
            self.assertIsNone(body[name], name)

    def test_is_reachable_without_a_token(self) -> None:
        # The evidence collector holds no application credential, so this route must not
        # require one. A 401 here would silently break deploy evidence collection.
        with TestClient(app) as client:
            response = client.get("/deployment")
        self.assertNotEqual(response.status_code, 401)

    def test_never_returns_credential_material(self) -> None:
        with mock.patch.dict(
            os.environ,
            {**VARS, "NC_JWT_SECRET": "super-secret-value", "NC_DATABASE_URL": "postgresql://u:p@h/db"},
            clear=False,
        ):
            with TestClient(app) as client:
                response = client.get("/deployment")
        text = response.text
        self.assertNotIn("super-secret-value", text)
        self.assertNotIn("postgresql://", text)


if __name__ == "__main__":
    unittest.main()
