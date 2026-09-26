"""Tests for the production hostname cutover.

The properties asserted here are the ones that would break or mislead in production:

* ``CallerReference`` is never changed — AWS rejects an update that alters it, so a run that
  changed it would fail outright.
* Existing aliases and unrelated settings survive; the hostname is merged in, not swapped in.
* The update uses the current ETag, so a concurrent configuration change is not clobbered.
* A rollback record of the pre-change configuration is written before anything changes.
* Re-running is safe and reports rather than rewrites.
* A wildcard DNS answer cannot pass as the intended destination. Vercel answers for every name
  in the zone, so resolution alone proves nothing.
"""

from __future__ import annotations

import importlib.util
import json
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

CALLER_REFERENCE = "original-caller-reference-abc123"
EXISTING_ALIAS = "atlas.noeticcompass.com"


def distribution_config(**overrides):
    config = {
        "CallerReference": CALLER_REFERENCE,
        "Comment": "existing comment",
        "Enabled": True,
        "Aliases": {"Quantity": 1, "Items": [EXISTING_ALIAS]},
        "ViewerCertificate": {"CloudFrontDefaultCertificate": True},
        "DefaultRootObject": "",
        "PriceClass": "PriceClass_100",
        "Origins": {"Quantity": 1, "Items": [{"Id": "origin"}]},
        "DefaultCacheBehavior": {"TargetOriginId": "origin"},
        "CustomErrorResponses": {"Quantity": 0},
    }
    config.update(overrides)
    return config


class FakeCloudFront:
    def __init__(self, config=None, status="Deployed"):
        self.config = config or distribution_config()
        self.status = status
        self.updates = []

    def get_distribution(self, Id):  # noqa: N803 - matches the boto3 keyword
        return {
            "Distribution": {"DistributionConfig": json.loads(json.dumps(self.config)),
                             "Status": self.status, "Id": Id},
            "ETag": "etag-current",
        }

    def update_distribution(self, DistributionConfig, Id, IfMatch):  # noqa: N803
        self.updates.append({"config": DistributionConfig, "id": Id, "if_match": IfMatch})
        self.config = DistributionConfig


class FakeAcm:
    def __init__(self, status="ISSUED", names=None):
        self.status = status
        self.names = names or [cutover.HOSTNAME]

    def describe_certificate(self, CertificateArn):  # noqa: N803
        return {"Certificate": {"Status": self.status, "DomainName": self.names[0],
                                "SubjectAlternativeNames": self.names}}


class FakeS3:
    def __init__(self):
        self.puts = []

    def put_object(self, Bucket, Key, Body):  # noqa: N803
        self.puts.append({"bucket": Bucket, "key": Key, "body": Body})


def with_clients(cf, acm=None, s3=None):
    def fake_client(service, region):
        if service == "cloudfront":
            return cf
        if service == "acm":
            return acm or FakeAcm()
        if service == "s3":
            return s3 or FakeS3()
        raise AssertionError(f"unexpected client {service}")

    return mock.patch.object(cutover, "_client", fake_client)


class AttachAliasTests(unittest.TestCase):
    def test_caller_reference_is_never_changed(self) -> None:
        cf = FakeCloudFront()
        with with_clients(cf):
            self.assertTrue(cutover.attach_alias())
        self.assertEqual(cf.updates[0]["config"]["CallerReference"], CALLER_REFERENCE)

    def test_existing_aliases_are_preserved_and_merged(self) -> None:
        cf = FakeCloudFront()
        with with_clients(cf):
            cutover.attach_alias()
        aliases = cf.updates[0]["config"]["Aliases"]
        self.assertEqual(aliases["Quantity"], 2)
        self.assertIn(EXISTING_ALIAS, aliases["Items"])
        self.assertIn(cutover.HOSTNAME, aliases["Items"])

    def test_unrelated_settings_survive(self) -> None:
        cf = FakeCloudFront()
        with with_clients(cf):
            cutover.attach_alias()
        updated = cf.updates[0]["config"]
        self.assertEqual(updated["Comment"], "existing comment")
        self.assertEqual(updated["PriceClass"], "PriceClass_100")
        self.assertTrue(updated["Enabled"])

    def test_update_uses_the_current_etag(self) -> None:
        cf = FakeCloudFront()
        with with_clients(cf):
            cutover.attach_alias()
        self.assertEqual(cf.updates[0]["if_match"], "etag-current")

    def test_rollback_record_is_written_before_the_change(self) -> None:
        cf = FakeCloudFront()
        s3 = FakeS3()
        with with_clients(cf, s3=s3):
            cutover.attach_alias()
        self.assertEqual(len(s3.puts), 1)
        saved = json.loads(s3.puts[0]["body"])
        self.assertEqual(saved["CallerReference"], CALLER_REFERENCE)
        self.assertEqual(saved["Aliases"]["Items"], [EXISTING_ALIAS])

    def test_repeat_run_is_a_no_op(self) -> None:
        cf = FakeCloudFront()
        with with_clients(cf):
            cutover.attach_alias()
        first_updates = len(cf.updates)
        with with_clients(cf):
            changed = cutover.attach_alias()
        self.assertFalse(changed)
        self.assertEqual(len(cf.updates), first_updates)


class CertificateGateTests(unittest.TestCase):
    def test_pending_certificate_blocks_the_run(self) -> None:
        with with_clients(FakeCloudFront(), acm=FakeAcm(status="PENDING_VALIDATION")):
            self.assertFalse(cutover.certificate_issued())

    def test_certificate_that_does_not_cover_the_hostname_blocks_the_run(self) -> None:
        with with_clients(FakeCloudFront(), acm=FakeAcm(names=["other.example.com"])):
            self.assertFalse(cutover.certificate_issued())

    def test_main_attaches_nothing_when_the_certificate_is_pending(self) -> None:
        cf = FakeCloudFront()
        with with_clients(cf, acm=FakeAcm(status="PENDING_VALIDATION")):
            result = cutover.main(["--attach"])
        self.assertEqual(result, 2)
        self.assertEqual(cf.updates, [])


class DnsVerificationTests(unittest.TestCase):
    def _opener(self, answers):
        class Response:
            def __init__(self, payload):
                self._payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return json.dumps({"Answer": answers}).encode()

        def open_(_request, timeout=None):  # noqa: ARG001
            return Response(answers)

        return open_

    def test_returns_cname_targets(self) -> None:
        opener = self._opener([{"type": 5, "data": "d2zcr7t1an5spf.cloudfront.net."}])
        self.assertEqual(cutover.resolve_cname(cutover.HOSTNAME, opener=opener),
                         ["d2zcr7t1an5spf.cloudfront.net"])

    def test_wildcard_answer_without_a_cname_is_not_accepted(self) -> None:
        # Vercel answers an A record for every name in the zone. No CNAME in the answer means
        # the record was not created, whatever the resolver returned.
        opener = self._opener([{"type": 1, "data": "216.150.1.65"}])
        self.assertEqual(cutover.resolve_cname(cutover.HOSTNAME, opener=opener), [])

    def test_verify_fails_when_the_cname_points_elsewhere(self) -> None:
        with mock.patch.object(cutover, "resolve_cname", return_value=["somewhere.else.example.com"]):
            with mock.patch.object(cutover, "tls_covers_hostname", return_value=False):
                with mock.patch.object(cutover, "http", side_effect=lambda *a, **k: (0, "")):
                    self.assertFalse(cutover.verify(bootstrap_owner=False))

    def test_verify_passes_when_every_check_holds(self) -> None:
        responses = {
            ("/health", "GET"): (200, "{}"),
            ("/deployment", "GET"): (200, '{"configured": true}'),
            ("/accounts/credential/rotate", "POST"): (401, "{}"),
            ("/auth/token", "POST"): (200, '{"token": "t"}'),
            ("/api/cas-harness/audit/sessions", "GET"): (200, '{"sessions": []}'),
        }
        with mock.patch.object(cutover, "resolve_cname", return_value=["d2zcr7t1an5spf.cloudfront.net"]):
            with mock.patch.object(cutover, "tls_covers_hostname", return_value=True):
                with mock.patch.object(cutover, "http",
                                       side_effect=lambda path, method="GET", **k: responses[(path, method)]):
                    with mock.patch.object(cutover, "_client", lambda s, r: type(
                            "S", (), {"get_parameter": lambda self, **k: {"Parameter": {"Value": "cred"}}})()):
                        self.assertTrue(cutover.verify(bootstrap_owner=False))


if __name__ == "__main__":
    unittest.main()
