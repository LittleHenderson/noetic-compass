"""Prospective launcher-only regressions; never contact AWS or run CAS.

These checks are separate from the frozen 57-case CAS scientific suite.
All SDK credentials below are deliberately inert test strings.
"""
import ast
import base64
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse


spec = importlib.util.spec_from_file_location("cas_launch_transport_subject", Path(__file__).with_name("launch.py"))
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


def bootstrap_source():
    text = launch.userdata(
        {"payload_sha256": "0" * 64, "job_id": "offline-job", "account_id": "000000000000", "region": "us-west-2"},
        "https://offline.invalid/download?secret=do-not-print",
        "https://offline.invalid/failure?secret=do-not-print",
        "https://offline.invalid/evidence?secret=do-not-print",
    )
    return base64.b64decode(re.search(r"b64decode\('([^']+)'\)", text).group(1)).decode()


class LaunchTransportTests(unittest.TestCase):
    def test_get_and_emergency_put_presign_the_explicit_regional_endpoint(self):
        import boto3
        from botocore.config import Config
        session = boto3.Session(aws_access_key_id="OFFLINE_TEST_KEY", aws_secret_access_key="OFFLINE_TEST_SECRET", region_name="us-west-2")
        with patch("botocore.endpoint.Endpoint.make_request", side_effect=AssertionError("NETWORK_FORBIDDEN")):
            client = launch.service_client(session, Config(retries={"total_max_attempts": 1}), "s3", "us-west-2")
            self.assertEqual(client.meta.endpoint_url, "https://s3.us-west-2.amazonaws.com")
            for operation in ("get_object", "put_object"):
                url = client.generate_presigned_url(operation, Params={"Bucket": "offline-test-bucket", "Key": "job/file"}, ExpiresIn=60)
                parts = urllib.parse.urlsplit(url)
                self.assertEqual(parts.hostname, "s3.us-west-2.amazonaws.com")
                self.assertEqual(parts.path, "/offline-test-bucket/job/file")
                query = urllib.parse.parse_qs(parts.query)
                self.assertEqual(query["X-Amz-Algorithm"], ["AWS4-HMAC-SHA256"])
                self.assertIn("/us-west-2/s3/aws4_request", query["X-Amz-Credential"][0])

    def test_non_s3_clients_keep_normal_service_endpoints(self):
        from botocore.config import Config
        class RecordingSession:
            def client(self, name, **options):
                return name, options
        config = Config(retries={"total_max_attempts": 1})
        name, options = launch.service_client(RecordingSession(), config, "ec2", "us-west-2")
        self.assertEqual(name, "ec2")
        self.assertEqual(options, {"region_name": "us-west-2", "config": config})

    def test_safe_error_record_drops_messages_urls_and_unknown_codes(self):
        tree = ast.parse(bootstrap_source())
        safe_nodes = [node for node in tree.body if isinstance(node, ast.Import) or isinstance(node, ast.FunctionDef) and node.name == "safe_failure"]
        namespace = {}
        exec(compile(ast.Module(body=safe_nodes, type_ignores=[]), "<safe-error-test>", "exec"), namespace)
        for code, expected in (("SignatureDoesNotMatch", "SignatureDoesNotMatch"), ("secret-do-not-print", None)):
            error = urllib.error.HTTPError("https://secret.invalid/?token=do-not-print", 403, "secret-message", {}, io.BytesIO(("<Error><Code>" + code + "</Code><Message>secret-do-not-print</Message></Error>").encode()))
            result = namespace["safe_failure"](error)
            self.assertEqual(result, {"status": "BOOTSTRAP_OR_WORKER_FAILED", "error_type": "HTTPError", "http_status": 403, "code": expected})
        self.assertIsNone(namespace["safe_failure"](ValueError("secret-do-not-print"))["code"])
        self.assertEqual(namespace["safe_failure"](ValueError("PAYLOAD_IDENTITY"))["code"], "PAYLOAD_IDENTITY")

    def test_download_failure_prints_safe_json_before_failed_emergency_upload(self):
        tree = ast.parse(bootstrap_source())
        with tempfile.TemporaryDirectory(prefix="cas-bootstrap-error-test-") as directory:
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "root" for target in node.targets):
                    node.value.args[0] = ast.Constant(str(Path(directory) / "job"))
            ast.fix_missing_locations(tree)
            output = io.StringIO()
            calls = []
            def fail_transport(request, **options):
                calls.append(request)
                if len(calls) == 1:
                    raise urllib.error.HTTPError("https://secret.invalid/?token=do-not-print", 403, "secret-message", {}, io.BytesIO(b"<Error><Code>SignatureDoesNotMatch</Code></Error>"))
                record = json.loads(output.getvalue())
                self.assertEqual(record["code"], "SignatureDoesNotMatch")
                self.assertEqual(record["http_status"], 403)
                raise urllib.error.URLError("secret-upload-error")
            with patch("urllib.request.urlopen", side_effect=fail_transport), contextlib.redirect_stdout(output):
                with self.assertRaises(SystemExit) as stopped:
                    exec(compile(tree, "<offline-bootstrap-test>", "exec"), {})
            self.assertEqual(stopped.exception.code, 1)
            self.assertEqual(len(calls), 2)
            self.assertNotIn("secret", output.getvalue())
            self.assertNotIn("https://", output.getvalue())


if __name__ == "__main__":
    unittest.main()
