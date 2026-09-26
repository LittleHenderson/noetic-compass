"""Tests for the production hostname cutover.

The property that matters most is that the script is inert until DNS exists. It must never
attach an alias or touch CloudFront on the strength of a name that merely resolves — Vercel
answers for every name in the zone, so resolution alone proves nothing.
"""

from __future__ import annotations

import importlib.util
import socket
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "cutover_production_hostname.py"

spec = importlib.util.spec_from_file_location("cutover_production_hostname", MODULE_PATH)
assert spec and spec.loader
cutover = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cutover
spec.loader.exec_module(cutover)


class InertWithoutDnsTests(unittest.TestCase):
    def test_unresolvable_name_changes_nothing(self) -> None:
        with mock.patch.object(socket, "getaddrinfo", side_effect=socket.gaierror("no such host")):
            with mock.patch.object(cutover, "attach_alias") as attach:
                result = cutover.main([])
        self.assertEqual(result, 2)
        attach.assert_not_called()

    def test_pending_certificate_changes_nothing(self) -> None:
        fake = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("216.150.1.65", 443))]
        with mock.patch.object(socket, "getaddrinfo", return_value=fake):
            with mock.patch.object(cutover, "cert_issued", return_value=False):
                with mock.patch.object(cutover, "attach_alias") as attach:
                    result = cutover.main([])
        self.assertEqual(result, 2)
        attach.assert_not_called()

    def test_ready_dns_and_issued_certificate_proceed_to_attach(self) -> None:
        fake = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("13.32.0.1", 443))]
        with mock.patch.object(socket, "getaddrinfo", return_value=fake):
            with mock.patch.object(cutover, "cert_issued", return_value=True):
                with mock.patch.object(cutover, "attach_alias", return_value=True) as attach:
                    with mock.patch.object(cutover, "wait_for_deployment", return_value=True):
                        with mock.patch.object(cutover, "verify", return_value=True):
                            result = cutover.main([])
        self.assertEqual(result, 0)
        attach.assert_called_once()

    def test_verify_reports_failure_when_the_gate_is_open(self) -> None:
        responses = {"/health": (200, "{}"), "/deployment": (200, '{"configured": true}'), "/accounts/me": (200, "{}")}
        with mock.patch.object(cutover, "tls_subject", return_value=[cutover.HOSTNAME]):
            with mock.patch.object(cutover, "http", side_effect=lambda path, **_: responses[path]):
                self.assertFalse(cutover.verify(bootstrap_owner=False))

    def test_verify_passes_when_everything_answers_correctly(self) -> None:
        responses = {
            "/health": (200, '{"status":"ok"}'),
            "/deployment": (200, '{"configured": true}'),
            "/accounts/me": (401, '{"detail":"missing"}'),
        }
        with mock.patch.object(cutover, "tls_subject", return_value=["other.test", cutover.HOSTNAME]):
            with mock.patch.object(cutover, "http", side_effect=lambda path, **_: responses[path]):
                self.assertTrue(cutover.verify(bootstrap_owner=False))

    def test_verify_rejects_a_certificate_that_does_not_cover_the_hostname(self) -> None:
        with mock.patch.object(cutover, "tls_subject", return_value=["wrong.test"]):
            self.assertFalse(cutover.verify(bootstrap_owner=False))


if __name__ == "__main__":
    unittest.main()
