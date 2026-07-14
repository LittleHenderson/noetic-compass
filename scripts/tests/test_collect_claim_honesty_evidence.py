from __future__ import annotations

import hashlib
import io
import json
import unittest
from datetime import datetime, timezone

from scripts import collect_claim_honesty_evidence as collector


NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
STAMP = "2026-07-14T12:00:00Z"
HEADINGS = {
    "product_app": "Atlas",
    "audit_console": "Audit Console",
    "landing": "Noetic Compass",
    "legal": "Legal",
    "privacy": "Privacy",
    "terms": "Terms",
}


class FakeResponse:
    def __init__(
        self,
        *,
        status: int,
        body: bytes,
        url: str,
        content_type: str = "text/html; charset=utf-8",
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


def _html(kind: str, text: str | None = None) -> bytes:
    paragraph = text or (
        "This public route describes scoped research evidence and explicit "
        "human-review boundaries for the service without making guarantees."
    )
    return (
        f"<!doctype html><html><body><main><h1>{HEADINGS[kind]}</h1>"
        f"<p>{paragraph}</p></main></body></html>"
    ).encode("utf-8")


def _completed_fetch(kind: str, body: bytes) -> collector.SurfaceFetch:
    return collector.SurfaceFetch(
        kind=kind,
        url=collector.PINNED_SURFACE_MAP[kind],
        verified_at_utc=STAMP,
        http_status=200,
        final_url_matches_requested=True,
        content_type="text/html; charset=utf-8",
        declared_content_length=len(body),
        byte_length=len(body),
        raw_content_sha256=hashlib.sha256(body).hexdigest(),
        raw=body,
    )


def _analysis(kind: str, text: str) -> collector.SurfaceAnalysis:
    return collector.analyze_surface(_completed_fetch(kind, _html(kind, text)))


class SurfaceUrlPolicyTests(unittest.TestCase):
    def test_exact_six_pinned_urls_are_valid(self) -> None:
        self.assertEqual(len(collector.PINNED_SURFACES), 6)
        for kind, url in collector.PINNED_SURFACES:
            self.assertEqual(collector.validate_surface_url(kind, url), url)

    def test_query_string_is_rejected(self) -> None:
        with self.assertRaisesRegex(collector.CollectorError, "query or fragment"):
            collector.validate_surface_url(
                "legal", "https://cascompass.ai/legal?preview=true"
            )

    def test_embedded_credentials_are_rejected_without_echoing_them(self) -> None:
        value = "https://user:do-not-print@cascompass.ai/legal"
        with self.assertRaises(collector.CollectorError) as context:
            collector.validate_surface_url("legal", value)
        self.assertNotIn("do-not-print", str(context.exception))

    def test_unpinned_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(collector.CollectorError, "not the pinned"):
            collector.validate_surface_url("legal", "https://cascompass.ai/login")


class BoundedFetchTests(unittest.TestCase):
    def test_get_records_exact_status_and_raw_byte_digest(self) -> None:
        kind = "legal"
        url = collector.PINNED_SURFACE_MAP[kind]
        body = _html(kind)
        response = FakeResponse(
            status=200,
            body=body,
            url=url,
            declared_length=str(len(body)),
        )
        opener = FakeOpener(response)

        result = collector.fetch_surface(
            kind, url, opener=opener, clock=lambda: NOW
        )

        self.assertEqual(result.http_status, 200)
        self.assertEqual(result.byte_length, len(body))
        self.assertEqual(result.raw_content_sha256, hashlib.sha256(body).hexdigest())
        self.assertEqual(result.errors, [])
        self.assertTrue(response.closed)
        self.assertEqual(len(opener.requests), 1)
        self.assertEqual(opener.requests[0].get_method(), "GET")  # type: ignore[attr-defined]

    def test_redirect_status_is_hashed_but_rejected(self) -> None:
        kind = "legal"
        url = collector.PINNED_SURFACE_MAP[kind]
        body = b"redirect rejected"
        response = FakeResponse(status=302, body=body, url=url)

        result = collector.fetch_surface(
            kind, url, opener=FakeOpener(response), clock=lambda: NOW
        )

        self.assertEqual(result.http_status, 302)
        self.assertEqual(result.raw_content_sha256, hashlib.sha256(body).hexdigest())
        self.assertIn("redirect_response_rejected", result.errors)
        self.assertIn("http_status_not_200", result.errors)

    def test_not_found_status_keeps_exact_error_body_digest(self) -> None:
        kind = "privacy"
        url = collector.PINNED_SURFACE_MAP[kind]
        body = b"not found"
        response = FakeResponse(status=404, body=body, url=url)

        result = collector.fetch_surface(
            kind, url, opener=FakeOpener(response), clock=lambda: NOW
        )

        self.assertEqual(result.http_status, 404)
        self.assertEqual(result.raw_content_sha256, hashlib.sha256(body).hexdigest())
        self.assertIn("http_status_not_200", result.errors)

    def test_final_url_mismatch_is_rejected(self) -> None:
        kind = "legal"
        url = collector.PINNED_SURFACE_MAP[kind]
        response = FakeResponse(
            status=200,
            body=_html(kind),
            url="https://cascompass.ai/login",
        )
        result = collector.fetch_surface(
            kind, url, opener=FakeOpener(response), clock=lambda: NOW
        )
        self.assertIn("redirect_or_final_url_mismatch", result.errors)

    def test_declared_oversize_response_is_not_partially_hashed(self) -> None:
        kind = "legal"
        url = collector.PINNED_SURFACE_MAP[kind]
        response = FakeResponse(
            status=200,
            body=b"elevenbytes",
            url=url,
            declared_length="11",
        )
        result = collector.fetch_surface(
            kind,
            url,
            opener=FakeOpener(response),
            clock=lambda: NOW,
            max_response_bytes=10,
        )
        self.assertIn("response_too_large", result.errors)
        self.assertIsNone(result.raw_content_sha256)
        self.assertIsNone(result.byte_length)

    def test_streamed_oversize_response_is_not_partially_hashed(self) -> None:
        kind = "legal"
        url = collector.PINNED_SURFACE_MAP[kind]
        response = FakeResponse(status=200, body=b"elevenbytes", url=url)
        result = collector.fetch_surface(
            kind,
            url,
            opener=FakeOpener(response),
            clock=lambda: NOW,
            max_response_bytes=10,
        )
        self.assertIn("response_too_large", result.errors)
        self.assertIsNone(result.raw_content_sha256)


class RouteCoverageTests(unittest.TestCase):
    def test_static_route_text_and_heading_establish_coverage(self) -> None:
        analysis = collector.analyze_surface(
            _completed_fetch("legal", _html("legal"))
        )
        self.assertTrue(analysis.coverage_established)
        self.assertTrue(analysis.route_identity_established)
        self.assertEqual(analysis.visibility_basis, "static_same_route_html")

    def test_javascript_only_shell_fails_closed(self) -> None:
        body = (
            b"<html><body><div id='root'></div>"
            b"<script src='/assets/app.js'></script></body></html>"
        )
        analysis = collector.analyze_surface(_completed_fetch("legal", body))
        self.assertFalse(analysis.coverage_established)
        self.assertTrue(analysis.client_rendered_shell_detected)
        self.assertIn(
            "client_rendered_route_coverage_not_established", analysis.errors
        )

    def test_client_routed_page_fails_even_with_plausible_static_heading(self) -> None:
        body = (
            "<html><body><div id='root'><main><h1>Legal</h1><p>"
            "This static fallback contains many plausible words about legal "
            "notices, privacy, terms, evaluation scope, evidence boundaries, "
            "service operation, public access, and responsible human review."
            "</p></main></div><script src='/assets/app.js'></script></body></html>"
        ).encode("utf-8")
        analysis = collector.analyze_surface(_completed_fetch("legal", body))
        self.assertTrue(analysis.route_identity_established)
        self.assertFalse(analysis.coverage_established)
        self.assertIn(
            "client_rendered_route_coverage_not_established", analysis.errors
        )

    def test_http_200_generic_login_cannot_satisfy_legal_route(self) -> None:
        body = (
            "<html><body><div id='root'><main><h1>Log in to Noetic Compass</h1>"
            "<p>Sign in to continue to your account and manage your workspace. "
            "Use your organization credentials to access all available tools, "
            "settings, projects, and account features from this application.</p>"
            "<footer><h2>Legal</h2><a>Privacy</a><a>Terms</a></footer>"
            "</main></div><script src='/assets/app.js'></script></body></html>"
        ).encode("utf-8")
        analysis = collector.analyze_surface(_completed_fetch("legal", body))
        self.assertFalse(analysis.coverage_established)
        self.assertFalse(analysis.route_identity_established)
        self.assertIn("requested_route_identity_not_established", analysis.errors)

    def test_hidden_claims_are_not_counted_as_visible_route_text(self) -> None:
        body = (
            "<html><body><main><h1>Legal</h1><p hidden>"
            + ("guaranteed compliance " * 20)
            + "</p><p>Short note.</p></main></body></html>"
        ).encode("utf-8")
        analysis = collector.analyze_surface(_completed_fetch("legal", body))
        self.assertFalse(analysis.coverage_established)
        self.assertLess(analysis.visible_text_characters, 32)


class DeterministicClaimScanTests(unittest.TestCase):
    def test_positive_claim_patterns_are_reported_by_category(self) -> None:
        text = (
            "We are SOC 2 certified and guarantee every AI model is always safe. "
            "Patent pending. This service measures how AI thinks in production."
        )
        analysis = _analysis("landing", text)
        self.assertTrue(analysis.coverage_established)

        findings = collector.scan_visible_text([analysis])
        categories = {item["category"] for item in findings}

        self.assertIn("misleading_claim", categories)
        self.assertIn("unsupported_compliance_claim", categories)
        self.assertIn("unsupported_universality_claim", categories)
        self.assertIn("unsupported_ip_claim", categories)
        self.assertTrue(all("matched_text" not in item for item in findings))

    def test_explicit_negations_are_not_reported_as_positive_claims(self) -> None:
        text = (
            "This service is not SOC 2 certified, does not guarantee universal "
            "accuracy, and is not regulatory approval. WORM retention does not "
            "upgrade a verdict or produce a product decision."
        )
        analysis = _analysis("legal", text)
        self.assertTrue(analysis.coverage_established)
        self.assertEqual(collector.scan_visible_text([analysis]), [])

    def test_status_vocabulary_requires_exact_spelling_and_case(self) -> None:
        drift = _analysis(
            "legal",
            "Customer-production status: Accept. This explanatory sentence "
            "provides enough visible words for deterministic route coverage.",
        )
        exact = _analysis(
            "legal",
            "Customer-production status: OPEN. This explanatory sentence "
            "provides enough visible words for deterministic route coverage.",
        )
        self.assertTrue(
            any(
                item["category"] == "status_vocabulary"
                for item in collector.scan_visible_text([drift])
            )
        )
        self.assertFalse(
            any(
                item["category"] == "status_vocabulary"
                for item in collector.scan_visible_text([exact])
            )
        )


class DraftReportContractTests(unittest.TestCase):
    def test_clean_machine_scan_stays_unsigned_and_open(self) -> None:
        bodies = {kind: _html(kind) for kind, _url in collector.PINNED_SURFACES}

        def fetcher(kind: str, _url: str) -> collector.SurfaceFetch:
            return _completed_fetch(kind, bodies[kind])

        report = collector.collect_claim_honesty_report(
            fetcher=fetcher, clock=lambda: NOW
        )
        draft = report["draft_payload"]

        self.assertTrue(draft["coverage_complete"])
        self.assertTrue(draft["machine_scan_passed"])
        self.assertEqual(draft["gate_status"], "OPEN")
        self.assertTrue(draft["draft_only"])
        self.assertFalse(draft["authoritative"])
        self.assertFalse(draft["eligible_for_acceptance"])
        self.assertEqual(len(draft["scanned_surfaces"]), 6)
        self.assertIn(
            "unsigned_draft_requires_independent_human_review", report["blockers"]
        )

        serialized = json.dumps(report, sort_keys=True, separators=(",", ":"))
        self.assertNotIn('"approvals"', serialized)
        self.assertNotIn('"present"', serialized)
        self.assertNotIn('"ACCEPT"', serialized)

    def test_any_coverage_gap_prevents_machine_pass(self) -> None:
        bodies = {kind: _html(kind) for kind, _url in collector.PINNED_SURFACES}
        bodies["privacy"] = b"<html><body><div id='root'></div></body></html>"

        def fetcher(kind: str, _url: str) -> collector.SurfaceFetch:
            return _completed_fetch(kind, bodies[kind])

        report = collector.collect_claim_honesty_report(
            fetcher=fetcher, clock=lambda: NOW
        )
        self.assertFalse(report["draft_payload"]["coverage_complete"])
        self.assertFalse(report["draft_payload"]["machine_scan_passed"])


if __name__ == "__main__":
    unittest.main()
