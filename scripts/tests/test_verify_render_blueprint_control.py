from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.verify_render_blueprint_control import (
    ControlError,
    EXPECTED_BLUEPRINTS,
    assert_no_secret_literals,
    parse_service_blocks,
    validate_live_payload,
    validate_offline,
    validate_workflow_locations,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class BlueprintYamlPolicyTests(unittest.TestCase):
    def test_service_parser_ignores_nested_names(self) -> None:
        text = """
services:
  - type: web
    name: api
    repo: https://github.com/example/repo
    branch: master
    region: oregon
    autoDeployTrigger: checksPass
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: database-name-must-not-replace-service-name
          property: connectionString
"""
        self.assertEqual(
            parse_service_blocks(text),
            [
                {
                    "type": "web",
                    "name": "api",
                    "repo": "https://github.com/example/repo",
                    "branch": "master",
                    "region": "oregon",
                    "autoDeployTrigger": "checksPass",
                    "envVars": "",
                }
            ],
        )

    def test_sensitive_env_literal_is_rejected(self) -> None:
        text = """
services:
  - type: web
    name: api
    envVars:
      - key: API_TOKEN
        value: definitely-not-allowed
"""
        with self.assertRaisesRegex(ControlError, "must not have a literal value"):
            assert_no_secret_literals(text, "test.yaml")

    def test_dashboard_managed_sensitive_env_is_allowed(self) -> None:
        text = """
services:
  - type: web
    name: api
    envVars:
      - key: API_TOKEN
        sync: false
"""
        assert_no_secret_literals(text, "test.yaml")


class LiveBlueprintPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.expected = EXPECTED_BLUEPRINTS[0]
        self.payload = {
            "id": self.expected["id"],
            "autoSync": False,
            "path": self.expected["path"],
            "branch": self.expected["sourceBranch"],
            "repo": "https://github.com/LittleHenderson/noetic-compass",
        }

    def test_disabled_auto_sync_passes(self) -> None:
        validate_live_payload(self.payload, self.expected)

    def test_enabled_auto_sync_fails_closed(self) -> None:
        self.payload["autoSync"] = True
        with self.assertRaisesRegex(ControlError, "Auto Sync drifted"):
            validate_live_payload(self.payload, self.expected)


class WorkflowLocationPolicyTests(unittest.TestCase):
    def test_workflow_below_repository_root_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            root_workflows = repo_root / ".github/workflows"
            root_workflows.mkdir(parents=True)
            (root_workflows / "ci.yml").write_text("name: root\n", encoding="utf-8")
            nested_workflows = repo_root / "app/.github/workflows"
            nested_workflows.mkdir(parents=True)
            (nested_workflows / "deploy.yml").write_text("name: misplaced\n", encoding="utf-8")

            with self.assertRaisesRegex(ControlError, "repository-root"):
                validate_workflow_locations(repo_root)


class RepositoryIntegrationTests(unittest.TestCase):
    def test_checked_in_control_passes_offline(self) -> None:
        manifest = validate_offline(REPO_ROOT)
        self.assertEqual(len(manifest["blueprints"]), 2)


if __name__ == "__main__":
    unittest.main()
