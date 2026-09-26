"""Tests for scripts/verify_aws_deployment_control.py.

The point of these tests is that the deployment invariants fail closed. A canary that
quietly becomes public, a database that quietly becomes reachable from the internet, or a
manifest that quietly disagrees with the production runbook must all stop the check.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "verify_aws_deployment_control.py"

spec = importlib.util.spec_from_file_location("verify_aws_deployment_control", MODULE_PATH)
assert spec and spec.loader
control = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = control
spec.loader.exec_module(control)


def manifest() -> dict:
    return json.loads((REPO_ROOT / control.MANIFEST_PATH).read_text(encoding="utf-8"))


def lane(document: dict, name: str) -> dict:
    return next(item for item in document["lanes"] if item["name"] == name)


class OfflineControlTests(unittest.TestCase):
    def test_repository_manifest_passes(self) -> None:
        control.offline(REPO_ROOT)

    def test_canary_must_stay_private(self) -> None:
        document = manifest()
        canary = lane(document, "accounts-canary")
        canary["publicIngress"] = True
        canary["publicOrigin"] = "https://canary.example.com"
        with self.assertRaises(control.ControlError) as ctx:
            control.validate_manifest(document)
        self.assertIn("accounts-canary", str(ctx.exception))

    def test_canary_must_not_declare_a_public_origin_while_private(self) -> None:
        document = manifest()
        lane(document, "accounts-canary")["publicOrigin"] = "https://canary.example.com"
        with self.assertRaises(control.ControlError):
            control.validate_manifest(document)

    def test_database_must_not_be_publicly_accessible(self) -> None:
        document = manifest()
        lane(document, "customer-production")["database"]["publiclyAccessible"] = True
        with self.assertRaises(control.ControlError) as ctx:
            control.validate_manifest(document)
        self.assertIn("publicly accessible", str(ctx.exception))

    def test_static_aws_keys_are_refused(self) -> None:
        document = manifest()
        lane(document, "customer-production")["staticAwsKeys"] = True
        with self.assertRaises(control.ControlError):
            control.validate_manifest(document)

    def test_production_origin_must_match_the_customer_lane(self) -> None:
        document = manifest()
        document["authority"]["productionApiOrigin"] = "https://somewhere-else.example.com"
        with self.assertRaises(control.ControlError) as ctx:
            control.validate_manifest(document)
        self.assertIn("productionApiOrigin", str(ctx.exception))

    def test_lane_set_is_fixed(self) -> None:
        document = manifest()
        document["lanes"] = document["lanes"][:2]
        with self.assertRaises(control.ControlError):
            control.validate_manifest(document)

    def test_superseded_entries_must_not_claim_authority(self) -> None:
        document = manifest()
        document["superseded"][0]["authoritative"] = True
        with self.assertRaises(control.ControlError):
            control.validate_manifest(document)

    def test_unknown_top_level_field_is_refused(self) -> None:
        document = manifest()
        document["surprise"] = "value"
        with self.assertRaises(control.ControlError):
            control.validate_manifest(document)

    def test_health_check_path_must_be_a_path(self) -> None:
        document = manifest()
        lane(document, "accounts-off")["healthCheckPath"] = "health"
        with self.assertRaises(control.ControlError):
            control.validate_manifest(document)

    def test_image_tag_is_required(self) -> None:
        document = manifest()
        lane(document, "accounts-off")["imageTag"] = "  "
        with self.assertRaises(control.ControlError):
            control.validate_manifest(document)

    def test_secret_literals_are_refused(self) -> None:
        with self.assertRaises(control.ControlError):
            control.assert_no_secret_literals('{"key": "base64url:AbCdEfGhIjKlMnOpQrStUvWx"}', "test")
        with self.assertRaises(control.ControlError):
            control.assert_no_secret_literals('{"aws": "AKIAIOSFODNN7EXAMPLE"}', "test")

    def test_runbook_must_agree_with_the_manifest_origin(self) -> None:
        document = manifest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".aws").mkdir()
            (root / ".aws" / "deployment-control.json").write_text(
                json.dumps(document), encoding="utf-8"
            )
            (root / control.RUNBOOK_PATH).parent.mkdir(parents=True, exist_ok=True)
            (root / control.RUNBOOK_PATH).write_text(
                "# Runbook\n\nAPI origin `https://wrong.example.com`.\n", encoding="utf-8"
            )
            with self.assertRaises(control.ControlError):
                control.validate_runbook_agreement(root, document)


if __name__ == "__main__":
    unittest.main()
