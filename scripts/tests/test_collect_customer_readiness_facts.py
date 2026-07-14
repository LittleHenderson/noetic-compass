from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import collect_customer_readiness_facts as collector


NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
STAMP = "2026-07-14T12:00:00Z"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class FakeResponse:
    def __init__(
        self,
        *,
        status: int,
        body: bytes,
        url: str,
        content_type: str = "application/json; charset=utf-8",
        declared_length: str | None = None,
    ) -> None:
        self.status = status
        self.code = status
        self._body = io.BytesIO(body)
        self._url = url
        self.closed = False
        self.headers = {"Content-Type": content_type}
        if declared_length is not None:
            self.headers["Content-Length"] = declared_length

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)

    def geturl(self) -> str:
        return self._url

    def close(self) -> None:
        self.closed = True


class FakeOpener:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requests: list[object] = []

    def open(self, request: object, timeout: float) -> FakeResponse:
        self.requests.append(request)
        return self.response


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _openapi_document(*, omit: tuple[str, str] | None = None) -> dict[str, object]:
    paths: dict[str, dict[str, object]] = {}
    for requirements in collector.ROUTE_CAPABILITIES.values():
        for path, method in requirements:
            if omit == (path, method):
                continue
            paths.setdefault(path, {})[method] = {"responses": {"200": {}}}
    return {"openapi": "3.1.0", "paths": paths}


def _surface_bodies(
    *,
    database_status: str = "not_configured",
    omit_route: tuple[str, str] | None = None,
) -> dict[str, bytes]:
    return {
        "health": _json_bytes({"status": "ok"}),
        "readiness": _json_bytes(
            {
                "status": "ok",
                "ready": True,
                "checks": {
                    "api": {"status": "ok"},
                    "database": {"status": database_status},
                },
            }
        ),
        "openapi": _json_bytes(_openapi_document(omit=omit_route)),
    }


def _completed_fetch(
    kind: str,
    body: bytes,
    *,
    status: int = 200,
) -> collector.SurfaceFetch:
    return collector.SurfaceFetch(
        kind=kind,
        url=collector.PINNED_SURFACE_MAP[kind],
        observed_at_utc=STAMP,
        http_status=status,
        final_url_matches_requested=True,
        content_type="application/json",
        declared_content_length=len(body),
        byte_length=len(body),
        raw_content_sha256=hashlib.sha256(body).hexdigest(),
        raw=body,
    )


def _source_config_text() -> str:
    identifiers = list(collector.SOURCE_CONFIG_FIELDS.values())
    return "\n".join(f"    {identifier}: object" for identifier in identifiers) + "\n"


def _render_text(*, enabled: bool, provider: str) -> str:
    literal = "true" if enabled else "false"
    lines = [
        "services:",
        "  - type: web",
        "    name: noetic-compass-api",
        "    repo: https://github.com/LittleHenderson/noetic-compass",
        "    branch: master",
        "    rootDir: noetic-compass-scaffold/noetic-compass",
        "    autoDeployTrigger: checksPass",
        "    healthCheckPath: /health",
        "    envVars:",
    ]
    for key in collector.FEATURE_ENV_KEYS.values():
        lines.extend((f"      - key: {key}", f'        value: "{literal}"'))
    lines.extend(
        (
            f"      - key: {collector.BILLING_PROVIDER_ENV_KEY}",
            f'        value: "{provider}"',
            f"      - key: {collector.DATABASE_ENV_KEY}",
            "        sync: false",
        )
    )
    for key in collector.STRIPE_SLOT_KEYS:
        lines.extend((f"      - key: {key}", "        sync: false"))
    return "\n".join(lines) + "\n"


def _write_test_repository(root: Path, *, enabled: bool, provider: str) -> None:
    (root / collector.CONFIG_PATH).parent.mkdir(parents=True)
    (root / collector.RENDER_PATH).write_text(
        _render_text(enabled=enabled, provider=provider), encoding="utf-8"
    )
    (root / collector.CONFIG_PATH).write_text(_source_config_text(), encoding="utf-8")


class SurfaceUrlPolicyTests(unittest.TestCase):
    def test_only_three_nonmutating_public_urls_are_pinned(self) -> None:
        self.assertEqual(
            collector.PINNED_SURFACES,
            (
                (
                    "health",
                    "https://noetic-compass-api.onrender.com/health",
                ),
                (
                    "readiness",
                    "https://noetic-compass-api.onrender.com/health/ready",
                ),
                (
                    "openapi",
                    "https://noetic-compass-api.onrender.com/openapi.json",
                ),
            ),
        )
        for kind, url in collector.PINNED_SURFACES:
            self.assertEqual(collector.validate_surface_url(kind, url), url)
        serialized = json.dumps(collector.PINNED_SURFACES)
        self.assertNotIn("/accounts/", serialized)
        self.assertNotIn("/billing/", serialized)
        self.assertNotIn("/evidence/", serialized)

    def test_query_fragment_and_credentials_are_rejected(self) -> None:
        with self.assertRaises(collector.CollectorError):
            collector.validate_surface_url(
                "health",
                "https://noetic-compass-api.onrender.com/health?probe=1",
            )
        with self.assertRaises(collector.CollectorError) as context:
            collector.validate_surface_url(
                "health",
                "https://user:do-not-print@noetic-compass-api.onrender.com/health",
            )
        self.assertNotIn("do-not-print", str(context.exception))

    def test_unpinned_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(collector.CollectorError, "not the pinned"):
            collector.validate_surface_url(
                "openapi", "https://noetic-compass-api.onrender.com/docs"
            )


class BoundedFetchTests(unittest.TestCase):
    def test_get_has_no_credential_headers_and_hashes_exact_bytes(self) -> None:
        kind = "health"
        url = collector.PINNED_SURFACE_MAP[kind]
        body = _json_bytes({"status": "ok"})
        response = FakeResponse(
            status=200,
            body=body,
            url=url,
            declared_length=str(len(body)),
        )
        opener = FakeOpener(response)

        result = collector.fetch_surface(kind, url, opener=opener, clock=lambda: NOW)

        self.assertEqual(result.http_status, 200)
        self.assertEqual(result.raw_content_sha256, hashlib.sha256(body).hexdigest())
        self.assertEqual(result.errors, [])
        self.assertTrue(response.closed)
        request = opener.requests[0]
        self.assertEqual(request.get_method(), "GET")  # type: ignore[attr-defined]
        headers = {key.lower(): value for key, value in request.header_items()}  # type: ignore[attr-defined]
        self.assertNotIn("authorization", headers)
        self.assertNotIn("cookie", headers)
        self.assertEqual(headers["accept-encoding"], "identity")

    def test_readiness_503_is_expected_and_exact_body_is_hashed(self) -> None:
        kind = "readiness"
        url = collector.PINNED_SURFACE_MAP[kind]
        body = _json_bytes({"status": "degraded", "ready": False})
        result = collector.fetch_surface(
            kind,
            url,
            opener=FakeOpener(FakeResponse(status=503, body=body, url=url)),
            clock=lambda: NOW,
        )
        self.assertEqual(result.raw_content_sha256, hashlib.sha256(body).hexdigest())
        self.assertNotIn("unexpected_http_status", result.errors)

    def test_redirect_is_hashed_and_rejected(self) -> None:
        kind = "openapi"
        url = collector.PINNED_SURFACE_MAP[kind]
        body = b"{}"
        result = collector.fetch_surface(
            kind,
            url,
            opener=FakeOpener(FakeResponse(status=302, body=body, url=url)),
            clock=lambda: NOW,
        )
        self.assertEqual(result.raw_content_sha256, hashlib.sha256(body).hexdigest())
        self.assertIn("redirect_response_rejected", result.errors)
        self.assertIn("unexpected_http_status", result.errors)

    def test_oversize_body_is_never_partially_hashed(self) -> None:
        kind = "health"
        url = collector.PINNED_SURFACE_MAP[kind]
        result = collector.fetch_surface(
            kind,
            url,
            opener=FakeOpener(FakeResponse(status=200, body=b"123456", url=url)),
            clock=lambda: NOW,
            max_response_bytes=5,
        )
        self.assertIn("response_too_large", result.errors)
        self.assertIsNone(result.raw_content_sha256)


class StrictInputTests(unittest.TestCase):
    def test_duplicate_json_key_fails_closed(self) -> None:
        with self.assertRaisesRegex(collector.CollectorError, "duplicate key"):
            collector._strict_json_object(b'{"status":"ok","status":"bad"}')

    def test_current_public_blueprint_is_dark_and_exactly_hashed(self) -> None:
        snapshot = collector.load_repository_snapshot(REPOSITORY_ROOT)
        for key in collector.FEATURE_ENV_KEYS.values():
            self.assertEqual(snapshot.env[key]["mode"], "literal")
            self.assertEqual(snapshot.env[key]["repository_value"], "false")
        self.assertEqual(
            snapshot.env[collector.BILLING_PROVIDER_ENV_KEY]["repository_value"],
            "null",
        )
        self.assertEqual(
            snapshot.env[collector.DATABASE_ENV_KEY]["mode"],
            "dashboard_managed_slot",
        )
        self.assertEqual(
            snapshot.render_sha256,
            hashlib.sha256((REPOSITORY_ROOT / collector.RENDER_PATH).read_bytes()).hexdigest(),
        )

    def test_duplicate_render_env_key_fails_closed(self) -> None:
        raw = _render_text(enabled=False, provider="null")
        duplicate = (
            f"      - key: {collector.FEATURE_ENV_KEYS['accounts']}\n"
            '        value: "false"\n'
        )
        with self.assertRaisesRegex(collector.CollectorError, "duplicate env key"):
            collector.parse_render_public_service((raw + duplicate).encode("utf-8"))

    def test_missing_source_configuration_field_fails_closed(self) -> None:
        incomplete = _source_config_text().replace("    quotas_enabled: object\n", "")
        with self.assertRaisesRegex(collector.CollectorError, "quotas_enabled"):
            collector.parse_source_configuration_fields(incomplete.encode("utf-8"))


class DraftReportContractTests(unittest.TestCase):
    def _report(
        self,
        *,
        repository_root: Path = REPOSITORY_ROOT,
        database_status: str = "not_configured",
        omit_route: tuple[str, str] | None = None,
    ) -> tuple[dict[str, object], list[tuple[str, str]]]:
        bodies = _surface_bodies(
            database_status=database_status,
            omit_route=omit_route,
        )
        calls: list[tuple[str, str]] = []

        def fetcher(kind: str, url: str) -> collector.SurfaceFetch:
            calls.append((kind, url))
            return _completed_fetch(kind, bodies[kind])

        report = collector.collect_customer_readiness_report(
            repository_root=repository_root,
            fetcher=fetcher,
            clock=lambda: NOW,
        )
        return report, calls

    def test_dark_production_report_is_complete_but_open_and_non_authoritative(self) -> None:
        report, calls = self._report()
        draft = report["draft_payload"]

        self.assertEqual(calls, list(collector.PINNED_SURFACES))
        self.assertTrue(draft["collection_complete"])
        self.assertFalse(draft["public_prerequisites_established"])
        self.assertEqual(
            draft["gate_statuses"],
            {
                "hosted_customer_journey": "OPEN",
                "accounts_billing": "OPEN",
            },
        )
        self.assertTrue(draft["draft_only"])
        self.assertFalse(draft["authoritative"])
        self.assertFalse(draft["eligible_for_acceptance"])
        self.assertFalse(draft["configured_vs_observed"]["accounts"]["repository_declared_enabled"])
        self.assertFalse(draft["configured_vs_observed"]["postgres"]["database_configured"])
        self.assertEqual(
            draft["configured_vs_observed"]["stripe"]["repository_provider_value"],
            "null",
        )
        self.assertIn("public_production:postgres:not_configured", report["blockers"])
        self.assertIn("repository_configuration:accounts:disabled", report["blockers"])
        self.assertIn(
            "repository_configuration:stripe:provider_is_not_stripe",
            report["blockers"],
        )
        for records in draft["source_capability"]["deployed_openapi_routes"].values():
            self.assertTrue(all(record["route_declared"] for record in records))

        safety = draft["collection_boundary"]
        self.assertEqual(safety["request_method"], "GET")
        self.assertFalse(safety["credentials_sent"])
        self.assertFalse(safety["accounts_created"])
        self.assertFalse(safety["provider_events_created_or_fabricated"])

        serialized = json.dumps(report, sort_keys=True, separators=(",", ":"))
        self.assertNotIn('"approvals"', serialized)
        self.assertNotIn('"present"', serialized)
        self.assertNotIn('"ACCEPT"', serialized)

    def test_route_declaration_is_capability_not_enablement(self) -> None:
        missing = ("/billing/checkout", "post")
        report, _calls = self._report(omit_route=missing)
        draft = report["draft_payload"]
        self.assertTrue(
            draft["source_capability"][
                "source_capability_does_not_establish_live_enablement"
            ]
        )
        self.assertIn(
            "source_capability:stripe_billing:route_unavailable", report["blockers"]
        )
        self.assertIsNone(
            draft["configured_vs_observed"]["stripe"]["public_runtime_live_enablement"]
        )

    def test_even_enabled_source_declarations_and_reachable_database_stay_open(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_test_repository(root, enabled=True, provider="stripe")
            report, _calls = self._report(
                repository_root=root,
                database_status="ok",
            )

        draft = report["draft_payload"]
        self.assertEqual(draft["gate_statuses"]["accounts_billing"], "OPEN")
        self.assertFalse(draft["authoritative"])
        self.assertFalse(draft["public_prerequisites_established"])
        self.assertTrue(draft["configured_vs_observed"]["accounts"]["repository_declared_enabled"])
        self.assertTrue(draft["configured_vs_observed"]["postgres"]["database_reachable"])
        self.assertIsNone(draft["configured_vs_observed"]["postgres"]["postgres_confirmed"])
        self.assertIn(
            "accounts_billing:live_stripe_subscription_invoice_webhook_and_meter_reconciliation_not_collected",
            report["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
