from __future__ import annotations

import io
import json
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


@contextmanager
def _running_http_server(handler):  # noqa: ANN001
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


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
    @patch("scripts.verify_render_blueprint_control._open_and_parse_render_response")
    def test_transient_timeout_recovers_with_bounded_backoff(self, open_response, sleep) -> None:
        open_response.side_effect = [TimeoutError(), TimeoutError(), {"id": "example"}]

        self.assertEqual(
            _read_json(self.request, 3.0, attempts=3, backoff_seconds=(0.25, 0.5)),
            {"id": "example"},
        )

        self.assertEqual(open_response.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.25, 0.5])

    @patch("scripts.verify_render_blueprint_control.time.sleep")
    @patch("scripts.verify_render_blueprint_control._open_and_parse_render_response")
    def test_transient_failure_exhaustion_fails_closed(self, open_response, sleep) -> None:
        open_response.side_effect = urllib.error.URLError(TimeoutError())

        with self.assertRaisesRegex(ControlError, "unavailable after 3 attempts"):
            _read_json(self.request, 3.0, attempts=3, backoff_seconds=(0.25, 0.5))

        self.assertEqual(open_response.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.25, 0.5])

    @patch("scripts.verify_render_blueprint_control.time.sleep")
    @patch("scripts.verify_render_blueprint_control._open_and_parse_render_response")
    def test_retryable_provider_statuses_recover(self, open_response, sleep) -> None:
        for status in (408, 429, 500, 502, 503, 504):
            with self.subTest(status=status):
                open_response.reset_mock()
                sleep.reset_mock()
                open_response.side_effect = [
                    urllib.error.HTTPError(
                        self.request.full_url,
                        status,
                        "Transient provider failure",
                        hdrs=None,
                        fp=None,
                    ),
                    {"id": "example"},
                ]

                self.assertEqual(
                    _read_json(
                        self.request,
                        3.0,
                        attempts=2,
                        backoff_seconds=(0.25,),
                    ),
                    {"id": "example"},
                )

                self.assertEqual(open_response.call_count, 2)
                sleep.assert_called_once_with(0.25)

    @patch("scripts.verify_render_blueprint_control.time.sleep")
    @patch("scripts.verify_render_blueprint_control._open_and_parse_render_response")
    def test_authentication_failure_is_not_retried(self, open_response, sleep) -> None:
        open_response.side_effect = urllib.error.HTTPError(
            self.request.full_url,
            401,
            "Unauthorized",
            hdrs=None,
            fp=None,
        )

        with self.assertRaisesRegex(ControlError, "HTTP 401"):
            _read_json(self.request, 3.0, attempts=3, backoff_seconds=(0.25, 0.5))

        self.assertEqual(open_response.call_count, 1)
        sleep.assert_not_called()

    @patch("scripts.verify_render_blueprint_control.time.sleep")
    @patch("scripts.verify_render_blueprint_control._RENDER_API_OPENER.open")
    def test_invalid_response_is_not_retried(self, opener, sleep) -> None:
        cases = (
            (b'{"id":', "JSONDecodeError"),
            (b"\xff", "UnicodeDecodeError"),
        )
        for body, error in cases:
            with self.subTest(error=error):
                opener.reset_mock()
                opener.return_value = io.BytesIO(body)

                with self.assertRaisesRegex(ControlError, error):
                    _read_json(
                        self.request,
                        3.0,
                        attempts=3,
                        backoff_seconds=(0.25, 0.5),
                    )

                self.assertEqual(opener.call_count, 1)
        sleep.assert_not_called()

    @patch("scripts.verify_render_blueprint_control.time.sleep")
    @patch("scripts.verify_render_blueprint_control._open_and_parse_render_response")
    def test_non_object_response_is_not_retried(self, open_response, sleep) -> None:
        open_response.return_value = json.loads('["unexpected"]')

        with self.assertRaisesRegex(ControlError, "must be an object"):
            _read_json(self.request, 3.0, attempts=3, backoff_seconds=(0.25, 0.5))

        self.assertEqual(open_response.call_count, 1)
        sleep.assert_not_called()

    @patch("scripts.verify_render_blueprint_control._open_and_parse_render_response")
    def test_shared_deadline_stops_retries(self, open_response) -> None:
        now = [0.0]

        def timeout_at_end_of_attempt(request, *, timeout):  # noqa: ANN001
            now[0] += timeout
            raise TimeoutError()

        open_response.side_effect = timeout_at_end_of_attempt

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

        self.assertEqual(open_response.call_count, 1)

    @patch("scripts.verify_render_blueprint_control._open_and_parse_render_response")
    def test_delayed_success_after_shared_deadline_fails_closed(self, open_response) -> None:
        now = [0.0]

        def delayed_success(request, timeout):  # noqa: ANN001
            now[0] = 31.0
            return {"id": "too-late"}

        open_response.side_effect = delayed_success

        with self.assertRaisesRegex(ControlError, "after response processing"):
            _read_json(
                self.request,
                30.0,
                attempts=1,
                deadline=30.0,
                clock=lambda: now[0],
            )

        self.assertEqual(open_response.call_count, 1)

    @patch("scripts.verify_render_blueprint_control._open_and_parse_render_response")
    def test_attempt_watchdog_bounds_body_read_and_parse(self, open_response) -> None:
        started = threading.Event()
        release = threading.Event()

        def blocked_response(request, timeout):  # noqa: ANN001
            started.set()
            release.wait(timeout=2.0)
            return {"id": "too-late"}

        open_response.side_effect = blocked_response
        started_at = time.monotonic()
        try:
            with self.assertRaisesRegex(ControlError, "unavailable after 1 attempts"):
                _read_json(self.request, 0.05, attempts=1)
        finally:
            release.set()

        elapsed = time.monotonic() - started_at
        self.assertTrue(started.wait(timeout=0.5))
        self.assertLess(elapsed, 0.5)

    def test_cross_origin_redirect_is_rejected_without_token_forwarding(self) -> None:
        source_authorization: list[str | None] = []
        destination_authorization: list[str | None] = []

        class DestinationHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                destination_authorization.append(self.headers.get("Authorization"))
                body = b'{"id":"redirected"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args) -> None:  # noqa: A002, ANN001
                return None

        with _running_http_server(DestinationHandler) as destination:
            destination_url = (
                f"http://127.0.0.1:{destination.server_address[1]}/redirect-target"
            )

            class SourceHandler(BaseHTTPRequestHandler):
                def do_GET(self) -> None:
                    source_authorization.append(self.headers.get("Authorization"))
                    self.send_response(302)
                    self.send_header("Location", destination_url)
                    self.end_headers()

                def log_message(self, format, *args) -> None:  # noqa: A002, ANN001
                    return None

            with _running_http_server(SourceHandler) as source:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{source.server_address[1]}/source",
                    headers={"Authorization": "Bearer must-not-forward"},
                )
                with self.assertRaisesRegex(ControlError, "HTTP 302"):
                    _read_json(request, 2.0, attempts=1)

        self.assertEqual(source_authorization, ["Bearer must-not-forward"])
        self.assertEqual(destination_authorization, [])


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
