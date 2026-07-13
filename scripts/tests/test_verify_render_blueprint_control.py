from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.verify_render_blueprint_control import (
    ControlError,
    EXPECTED_BLUEPRINTS,
    assert_no_secret_literals,
    parse_service_blocks,
    validate_live,
    validate_live_payload,
    validate_live_service_payload,
    validate_offline,
    validate_workflow_locations,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _blueprint_payload(expected: dict[str, object]) -> dict[str, object]:
    return {
        "id": expected["id"],
        "autoSync": False,
        "path": expected["path"],
        "branch": expected["sourceBranch"],
        "repo": "https://github.com/LittleHenderson/noetic-compass",
    }


def _service_payload(expected: dict[str, object]) -> dict[str, object]:
    details = {"region": expected["region"]}
    if "healthCheckPath" in expected:
        details["healthCheckPath"] = expected["healthCheckPath"]
    return {
        "id": expected["id"],
        "name": expected["name"],
        "type": expected["type"],
        "repo": "https://github.com/LittleHenderson/noetic-compass",
        "branch": expected["branch"],
        "autoDeployTrigger": expected["autoDeployTrigger"],
        "serviceDetails": details,
    }


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
        self.payload = _blueprint_payload(self.expected)

    def test_disabled_auto_sync_passes(self) -> None:
        validate_live_payload(self.payload, self.expected)

    def test_enabled_auto_sync_fails_closed(self) -> None:
        self.payload["autoSync"] = True
        with self.assertRaisesRegex(ControlError, "Auto Sync drifted"):
            validate_live_payload(self.payload, self.expected)


class LiveServicePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.expected = EXPECTED_BLUEPRINTS[0]["services"][0]

    def test_expected_production_service_passes(self) -> None:
        validate_live_service_payload(
            _service_payload(self.expected),
            self.expected,
            environment="production",
        )

    def test_expected_private_canary_passes_without_http_health_path(self) -> None:
        expected = EXPECTED_BLUEPRINTS[1]["services"][0]
        validate_live_service_payload(
            _service_payload(expected),
            expected,
            environment="accounts-canary",
        )

    def test_top_level_service_drift_fails_closed(self) -> None:
        cases = (
            ("id", "srv-unexpected", "stable ID drifted"),
            ("name", "renamed-service", "name drifted"),
            ("type", "private_service", "type drifted"),
            ("repo", "https://github.com/example/other", "repository drifted"),
            ("branch", "unsafe-branch", "branch drifted"),
            ("autoDeployTrigger", "off", "autoDeployTrigger drifted"),
        )
        for field, value, error in cases:
            with self.subTest(field=field):
                payload = _service_payload(self.expected)
                payload[field] = value
                with self.assertRaisesRegex(ControlError, error):
                    validate_live_service_payload(
                        payload,
                        self.expected,
                        environment="production",
                    )

    def test_nested_service_drift_fails_closed(self) -> None:
        cases = (
            ("region", "frankfurt", "region drifted"),
            ("healthCheckPath", "/health/ready", "healthCheckPath drifted"),
        )
        for field, value, error in cases:
            with self.subTest(field=field):
                payload = _service_payload(self.expected)
                payload["serviceDetails"][field] = value
                with self.assertRaisesRegex(ControlError, error):
                    validate_live_service_payload(
                        payload,
                        self.expected,
                        environment="production",
                    )


class LiveRequestCoverageTests(unittest.TestCase):
    @patch("scripts.verify_render_blueprint_control._read_json")
    def test_live_queries_every_stable_service_without_printing_key(self, read_json) -> None:
        responses: list[dict[str, object]] = []
        expected_urls: list[str] = []
        for blueprint in EXPECTED_BLUEPRINTS:
            responses.append(_blueprint_payload(blueprint))
            expected_urls.append(f"https://render.invalid/v1/blueprints/{blueprint['id']}")
            for service in blueprint["services"]:
                responses.append(_service_payload(service))
                expected_urls.append(f"https://render.invalid/v1/services/{service['id']}")
        read_json.side_effect = responses

        output = io.StringIO()
        api_key = "unit-test-render-secret"
        with redirect_stdout(output):
            validate_live(
                {"blueprints": EXPECTED_BLUEPRINTS},
                api_key,
                api_base="https://render.invalid/v1",
            )

        actual_urls = [call.args[0].full_url for call in read_json.call_args_list]
        self.assertEqual(actual_urls, expected_urls)
        self.assertNotIn(api_key, output.getvalue())
        self.assertEqual(output.getvalue().count("live Render service control PASS"), 2)


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
