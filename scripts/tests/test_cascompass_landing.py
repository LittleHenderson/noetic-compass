from __future__ import annotations

import hashlib
import re
import tomllib
import unittest
from pathlib import Path

from scripts import collect_claim_honesty_evidence as collector


REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_ROOT = REPO_ROOT / "cascompass-landing"
PINNED_FILES = {
    "landing": SITE_ROOT / "index.html",
    "legal": SITE_ROOT / "legal.html",
    "privacy": SITE_ROOT / "privacy.html",
    "terms": SITE_ROOT / "terms.html",
}
CLEAN_ROUTES = {
    "/legal": "/legal.html",
    "/privacy": "/privacy.html",
    "/terms": "/terms.html",
    "/contact": "/contact.html",
}


def _source_analysis(kind: str, path: Path) -> collector.SurfaceAnalysis:
    raw = path.read_bytes()
    return collector.analyze_surface(
        collector.SurfaceFetch(
            kind=kind,
            url=collector.PINNED_SURFACE_MAP[kind],
            verified_at_utc="2026-07-14T00:00:00Z",
            http_status=200,
            final_url_matches_requested=True,
            content_type="text/html; charset=utf-8",
            declared_content_length=len(raw),
            byte_length=len(raw),
            raw_content_sha256=hashlib.sha256(raw).hexdigest(),
            raw=raw,
        )
    )


class LandingSourceTests(unittest.TestCase):
    def test_public_pages_are_real_utf8_static_documents(self) -> None:
        expected = {
            "index.html",
            "legal.html",
            "privacy.html",
            "terms.html",
            "contact.html",
        }
        self.assertTrue(expected.issubset({path.name for path in SITE_ROOT.iterdir()}))
        for name in expected:
            document = (SITE_ROOT / name).read_text(encoding="utf-8")
            self.assertTrue(document.startswith("<!doctype html>"), name)
            self.assertEqual(document.count("<h1"), 1, name)
            if name != "contact.html":
                self.assertNotIn("<script", document.lower(), name)
            self.assertIn('href="/site.css"', document, name)

    def test_pinned_pages_establish_static_route_coverage(self) -> None:
        analyses = [
            _source_analysis(kind, path) for kind, path in PINNED_FILES.items()
        ]
        for analysis in analyses:
            self.assertTrue(analysis.coverage_established, analysis.errors)
            self.assertTrue(analysis.route_identity_established, analysis.errors)
            self.assertEqual(analysis.visibility_basis, "static_same_route_html")

    def test_deterministic_claim_rules_find_no_positive_claims(self) -> None:
        analyses = [
            _source_analysis(kind, path) for kind, path in PINNED_FILES.items()
        ]
        self.assertEqual(collector.scan_visible_text(analyses), [])

    def test_removed_landing_claims_cannot_regress(self) -> None:
        index = (SITE_ROOT / "index.html").read_text(encoding="utf-8")
        all_html = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(SITE_ROOT.glob("*.html"))
        )
        self.assertNotRegex(index, re.compile(r"measure\s+how\s+AI\s+thinks", re.I))
        self.assertNotRegex(all_html, re.compile(r"patents?\s+pending", re.I))
        self.assertNotRegex(all_html, re.compile(r"\b(?:all|every)\s+AI\s+models?\b", re.I))
        self.assertNotRegex(all_html, re.compile(r"\b(?:SOC\s*2|HIPAA|FedRAMP|ISO\s*27001)\b", re.I))

    def test_legal_status_vocabulary_and_review_boundary_are_explicit(self) -> None:
        legal = (SITE_ROOT / "legal.html").read_text(encoding="utf-8")
        for term in collector.EXACT_STATUS_TERMS:
            self.assertIn(term, legal)
        self.assertIn("qualified counsel", legal)
        self.assertIn("do not mark customer-production ACCEPT", legal)

    def test_contact_page_uses_only_the_project_address(self) -> None:
        contact = (SITE_ROOT / "contact.html").read_text(encoding="utf-8")
        addresses = set(re.findall(r"mailto:([^?\"']+)", contact))
        self.assertEqual(addresses, {"hello@cascompass.ai"})
        self.assertIn("Do not include passwords", contact)

    def test_internal_navigation_uses_clean_known_routes(self) -> None:
        allowed = {
            "/",
            "/legal",
            "/privacy",
            "/terms",
            "/contact",
            "/site.css",
            "/contact.js",
        }
        for path in sorted(SITE_ROOT.glob("*.html")):
            document = path.read_text(encoding="utf-8")
            internal = set(re.findall(r'(?:href|src)="(/[^"]*)"', document))
            self.assertTrue(internal.issubset(allowed), (path.name, internal))
            self.assertFalse(any(value.endswith(".html") for value in internal))


class NetlifyContractTests(unittest.TestCase):
    def test_clean_routes_are_internal_200_rewrites(self) -> None:
        config = tomllib.loads(
            (SITE_ROOT / "netlify.toml").read_text(encoding="utf-8")
        )
        redirects = {
            item["from"]: item for item in config.get("redirects", [])
        }
        self.assertEqual(set(redirects), set(CLEAN_ROUTES))
        for route, target in CLEAN_ROUTES.items():
            self.assertEqual(redirects[route]["to"], target)
            self.assertEqual(redirects[route]["status"], 200)
            self.assertIs(redirects[route]["force"], True)

    def test_deploy_config_is_portable_and_fail_closed(self) -> None:
        raw = (SITE_ROOT / "netlify.toml").read_text(encoding="utf-8")
        config = tomllib.loads(raw)
        self.assertEqual(config["build"]["base"], ".")
        self.assertEqual(config["build"]["publish"], ".")
        self.assertNotRegex(raw, re.compile(r"[A-Z]:\\", re.I))

        publish_header_lines = [
            line.rstrip()
            for line in (SITE_ROOT / "_headers").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(publish_header_lines[0], "/*")
        headers: dict[str, str] = {}
        for line in publish_header_lines[1:]:
            self.assertTrue(line.startswith("  "), line)
            name, separator, value = line.strip().partition(": ")
            self.assertEqual(separator, ": ", line)
            self.assertNotIn(name, headers)
            headers[name] = value

        # `netlify deploy --dir cascompass-landing` reads the special file from
        # the published bytes, not the nested project configuration. Keep both
        # supported deploy modes on exactly the same response-header policy.
        self.assertEqual(headers, config["headers"][0]["values"])
        self.assertEqual(
            set(headers),
            {
                "Cache-Control",
                "Content-Security-Policy",
                "Cross-Origin-Opener-Policy",
                "Permissions-Policy",
                "Referrer-Policy",
                "X-Content-Type-Options",
                "X-Frame-Options",
            },
        )
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIn(
            "https://noetic-compass-api.onrender.com",
            headers["Content-Security-Policy"],
        )
        self.assertEqual(headers["Cross-Origin-Opener-Policy"], "same-origin")
        self.assertEqual(
            headers["Permissions-Policy"],
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        self.assertEqual(
            headers["Referrer-Policy"], "strict-origin-when-cross-origin"
        )
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")

    def test_contact_form_posts_only_to_the_pinned_support_intake(self) -> None:
        contact = (SITE_ROOT / "contact.html").read_text(encoding="utf-8")
        script = (SITE_ROOT / "contact.js").read_text(encoding="utf-8")
        self.assertIn('id="support-form"', contact)
        self.assertIn('name="consent_to_contact"', contact)
        self.assertIn('src="/contact.js"', contact)
        self.assertIn(
            "https://noetic-compass-api.onrender.com/api/support/public/tickets",
            script,
        )
        self.assertIn(r"Submitting your support request\u2026", script)
        for mojibake in ("â€¦", "Ã¢", "Â"):
            self.assertNotIn(mojibake, script)
        self.assertIn("textContent", script)
        self.assertNotIn("innerHTML", script)


if __name__ == "__main__":
    unittest.main()
