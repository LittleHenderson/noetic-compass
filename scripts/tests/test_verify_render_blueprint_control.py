from __future__ import annotations

import io
import json
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.verify_render_blueprint_control import (
    AUXILIARY_BLUEPRINT_PATHS,
    ControlError,
    EXPECTED_BLUEPRINTS,
    LIVE_REQUEST_ATTEMPTS,
    LIVE_REQUEST_TIMEOUT_SECONDS,
    LIVE_RETRY_BACKOFF_SECONDS,
    LIVE_TOTAL_TIMEOUT_SECONDS,
    PRODUCTION_PROVIDER_DASHBOARD_ENV_KEYS,
    _read_json,
    assert_no_secret_literals,
    assert_production_provider_env_declarations,
    assert_receipt_attestation_key_declaration,
    parse_service_env_blocks,
    parse_service_blocks,
    validate_auxiliary_blueprint_yaml,
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

    def test_receipt_attestation_key_must_be_unique_and_dashboard_managed(self) -> None:
        valid = """
services:
  - type: web
    name: api
    envVars:
      - key: NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY
        sync: false
"""
        assert_receipt_attestation_key_declaration(valid, "test.yaml")

        invalid_cases = (
            (valid.replace("sync: false", "value: committed-secret"), "server-only"),
            (valid.replace("sync: false", "generateValue: true"), "server-only"),
            (valid.replace("sync: false", "sync: true"), "server-only"),
            (valid.replace("      - key: NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY\n        sync: false\n", ""), "exactly one"),
            (valid + "\n      - key: NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY\n        sync: false\n", "exactly one"),
        )
        for text, error in invalid_cases:
            with self.subTest(error=error):
                with self.assertRaisesRegex(ControlError, error):
                    assert_receipt_attestation_key_declaration(text, "test.yaml")

    def test_production_provider_slots_must_be_complete_and_dashboard_managed(self) -> None:
        service_name = "noetic-compass-api"
        lines = [
            "services:",
            "  - type: web",
            f"    name: {service_name}",
            "    envVars:",
        ]
        for key in PRODUCTION_PROVIDER_DASHBOARD_ENV_KEYS:
            lines.extend((f"      - key: {key}", "        sync: false"))
        valid = "\n".join(lines) + "\n"
        assert_production_provider_env_declarations(valid, "test.yaml", service_name)
        self.assertEqual(
            len(parse_service_env_blocks(valid, service_name)),
            len(PRODUCTION_PROVIDER_DASHBOARD_ENV_KEYS),
        )

        missing = valid.replace(
            "      - key: NC_STRIPE_USAGE_PRICE_ID\n        sync: false\n", ""
        )
        with self.assertRaisesRegex(ControlError, "NC_STRIPE_USAGE_PRICE_ID"):
            assert_production_provider_env_declarations(
                missing, "test.yaml", service_name
            )

        committed = valid.replace(
            "      - key: NC_AIRTABLE_TOKEN\n        sync: false",
            "      - key: NC_AIRTABLE_TOKEN\n        value: committed-token",
        )
        with self.assertRaisesRegex(ControlError, "dashboard-managed"):
            assert_production_provider_env_declarations(
                committed, "test.yaml", service_name
            )

    def test_unlinked_env_group_cannot_satisfy_production_provider_slots(self) -> None:
        service_name = "noetic-compass-api"
        lines = [
            "services:",
            "  - type: web",
            f"    name: {service_name}",
            "    envVars:",
            "      - key: NC_JWT_SECRET",
            "        generateValue: true",
            "envVarGroups:",
            "  - name: unlinked-provider-slots",
            "    envVars:",
        ]
        for key in PRODUCTION_PROVIDER_DASHBOARD_ENV_KEYS:
            lines.extend((f"      - key: {key}", "        sync: false"))
        misplaced = "\n".join(lines) + "\n"

        with self.assertRaisesRegex(ControlError, "NC_STRIPE_SECRET_KEY"):
            assert_production_provider_env_declarations(
                misplaced, "test.yaml", service_name
            )

    def test_second_service_cannot_satisfy_production_provider_slots(self) -> None:
        service_name = "noetic-compass-api"
        lines = [
            "services:",
            "  - type: web",
            f"    name: {service_name}",
            "    envVars:",
            "      - key: NC_JWT_SECRET",
            "        generateValue: true",
            "  - type: web",
            "    name: unrelated-service",
            "    envVars:",
        ]
        for key in PRODUCTION_PROVIDER_DASHBOARD_ENV_KEYS:
            lines.extend((f"      - key: {key}", "        sync: false"))
        misplaced = "\n".join(lines) + "\n"

        with self.assertRaisesRegex(ControlError, "NC_STRIPE_SECRET_KEY"):
            assert_production_provider_env_declarations(
                misplaced, "test.yaml", service_name
            )


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
        self.assertTrue(
            all(
                call.args[1] == LIVE_REQUEST_TIMEOUT_SECONDS
                for call in read_json.call_args_list
            )
        )
        self.assertTrue(
            all(
                call.kwargs["attempts"] == LIVE_REQUEST_ATTEMPTS
                for call in read_json.call_args_list
            )
        )
        self.assertTrue(
            all(
                call.kwargs["backoff_seconds"] == LIVE_RETRY_BACKOFF_SECONDS
                for call in read_json.call_args_list
            )
        )
        deadlines = {call.kwargs["deadline"] for call in read_json.call_args_list}
        self.assertEqual(len(deadlines), 1)
        self.assertEqual(LIVE_TOTAL_TIMEOUT_SECONDS, 210.0)


class LiveReadRetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = urllib.request.Request("https://render.invalid/v1/blueprints/example")

    @patch("scripts.verify_render_blueprint_control.time.sleep")
    @patch("scripts.verify_render_blueprint_control.urllib.request.urlopen")
    def test_transient_timeout_recovers_with_bounded_backoff(self, urlopen, sleep) -> None:
        response = io.BytesIO(b'{"id":"example"}')
        urlopen.side_effect = [TimeoutError(), TimeoutError(), response]

        self.assertEqual(
            _read_json(self.request, 3.0, attempts=3, backoff_seconds=(0.25, 0.5)),
            {"id": "example"},
        )

        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.25, 0.5])

    @patch("scripts.verify_render_blueprint_control.time.sleep")
    @patch("scripts.verify_render_blueprint_control.urllib.request.urlopen")
    def test_transient_failure_exhaustion_fails_closed(self, urlopen, sleep) -> None:
        urlopen.side_effect = urllib.error.URLError(TimeoutError())

        with self.assertRaisesRegex(ControlError, "unavailable after 3 attempts"):
            _read_json(self.request, 3.0, attempts=3, backoff_seconds=(0.25, 0.5))

        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.25, 0.5])

    @patch("scripts.verify_render_blueprint_control.time.sleep")
    @patch("scripts.verify_render_blueprint_control.urllib.request.urlopen")
    def test_retryable_provider_status_recovers(self, urlopen, sleep) -> None:
        unavailable = urllib.error.HTTPError(
            self.request.full_url,
            503,
            "Service Unavailable",
            hdrs=None,
            fp=None,
        )
        urlopen.side_effect = [unavailable, io.BytesIO(b'{"id":"example"}')]

        self.assertEqual(
            _read_json(self.request, 3.0, attempts=2, backoff_seconds=(0.25,)),
            {"id": "example"},
        )

        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(0.25)

    @patch("scripts.verify_render_blueprint_control.time.sleep")
    @patch("scripts.verify_render_blueprint_control.urllib.request.urlopen")
    def test_authentication_failure_is_not_retried(self, urlopen, sleep) -> None:
        urlopen.side_effect = urllib.error.HTTPError(
            self.request.full_url,
            401,
            "Unauthorized",
            hdrs=None,
            fp=None,
        )

        with self.assertRaisesRegex(ControlError, "HTTP 401"):
            _read_json(self.request, 3.0, attempts=3, backoff_seconds=(0.25, 0.5))

        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @patch("scripts.verify_render_blueprint_control.time.sleep")
    @patch("scripts.verify_render_blueprint_control.urllib.request.urlopen")
    def test_invalid_response_is_not_retried(self, urlopen, sleep) -> None:
        urlopen.return_value = io.BytesIO(b'{"id":')

        with self.assertRaisesRegex(ControlError, "JSONDecodeError"):
            _read_json(self.request, 3.0, attempts=3, backoff_seconds=(0.25, 0.5))

        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @patch("scripts.verify_render_blueprint_control.time.sleep")
    @patch("scripts.verify_render_blueprint_control.urllib.request.urlopen")
    def test_non_object_response_is_not_retried(self, urlopen, sleep) -> None:
        urlopen.return_value = io.BytesIO(json.dumps(["unexpected"]).encode("utf-8"))

        with self.assertRaisesRegex(ControlError, "must be an object"):
            _read_json(self.request, 3.0, attempts=3, backoff_seconds=(0.25, 0.5))

        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @patch("scripts.verify_render_blueprint_control.urllib.request.urlopen")
    def test_shared_deadline_stops_retries(self, urlopen) -> None:
        now = [0.0]

        def timeout_at_end_of_attempt(request, *, timeout):  # noqa: ANN001
            now[0] += timeout
            raise TimeoutError()

        urlopen.side_effect = timeout_at_end_of_attempt

        with self.assertRaisesRegex(ControlError, "live-read window exhausted"):
            _read_json(
                self.request,
                30.0,
                attempts=3,
                backoff_seconds=(2.0, 5.0),
                deadline=31.0,
                clock=lambda: now[0],
                sleep=lambda delay: now.__setitem__(0, now[0] + delay),
            )

        self.assertEqual(urlopen.call_count, 1)


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


class AuxiliaryBlueprintPolicyTests(unittest.TestCase):
    def test_auxiliary_blueprint_requires_checks_pass(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            relative_path = "app/infra/render.yaml"
            path = repo_root / relative_path
            path.parent.mkdir(parents=True)
            path.write_text(
                "services:\n"
                "  - type: web\n"
                "    name: legacy-api\n"
                "    autoDeployTrigger: commit\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ControlError, "must be checksPass"):
                validate_auxiliary_blueprint_yaml(repo_root, relative_path)

            path.write_text(
                path.read_text(encoding="utf-8").replace("commit", "checksPass"),
                encoding="utf-8",
            )
            validate_auxiliary_blueprint_yaml(repo_root, relative_path)


class RepositoryIntegrationTests(unittest.TestCase):
    def test_checked_in_control_passes_offline(self) -> None:
        manifest = validate_offline(REPO_ROOT)
        self.assertEqual(len(manifest["blueprints"]), 2)
        self.assertEqual(len(AUXILIARY_BLUEPRINT_PATHS), 1)


if __name__ == "__main__":
    unittest.main()
