from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import collect_root_ci_protected_deploy_facts as collector
import verify_customer_production_acceptance as acceptance


MASTER_SHA = "2" * 40
DEPLOY_ID = "dep-rootcifacts001"
NOW = datetime(2026, 7, 14, 8, 0, 0, tzinfo=timezone.utc)
GITHUB_TOKEN = "github-test-token-never-output"
RENDER_KEY = "render-test-key-never-output"


class FakeTransport:
    def __init__(self, documents: dict[str, collector.HttpDocument]) -> None:
        self.documents = documents
        self.requests: list[tuple[str, dict[str, str], str]] = []

    def get_json(self, url: str, *, headers, label: str) -> collector.HttpDocument:
        self.requests.append((url, dict(headers), label))
        if url not in self.documents:
            raise AssertionError(f"unexpected URL: {url}")
        return self.documents[url]


class SequencedDeployTransport(FakeTransport):
    def __init__(
        self,
        documents: dict[str, collector.HttpDocument],
        deploy_url: str,
        deploy_payloads: list[dict],
    ) -> None:
        super().__init__(documents)
        self.deploy_url = deploy_url
        self.deploy_payloads = list(deploy_payloads)

    def get_json(self, url: str, *, headers, label: str) -> collector.HttpDocument:
        if url != self.deploy_url:
            return super().get_json(url, headers=headers, label=label)
        self.requests.append((url, dict(headers), label))
        if not self.deploy_payloads:
            raise AssertionError("exact deploy was polled too many times")
        return _document(url, self.deploy_payloads.pop(0))


def _document(url: str, payload: dict, *, headers: dict[str, str] | None = None) -> collector.HttpDocument:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return collector.HttpDocument(
        url=url,
        raw=raw,
        payload=payload,
        headers=headers or {},
    )


def _write_workflows(root: Path) -> None:
    for name, contract in acceptance.WORKFLOW_CONTRACTS.items():
        path = root / contract["workflow_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                (
                    f"name: {contract['workflow_name']}",
                    "jobs:",
                    f"  {contract['job_key']}:",
                    f"    name: {name}",
                    "    runs-on: ubuntu-latest",
                    "",
                )
            ),
            encoding="utf-8",
        )


def _fixture(root: Path) -> tuple[FakeTransport, dict[str, collector.HttpDocument]]:
    _write_workflows(root)
    documents: dict[str, collector.HttpDocument] = {}

    documents[collector.GITHUB_API] = _document(
        collector.GITHUB_API,
        {
            "id": acceptance.REPOSITORY_ID,
            "node_id": acceptance.REPOSITORY_NODE_ID,
            "full_name": acceptance.REPOSITORY,
            "html_url": acceptance.REPOSITORY_URL,
            "url": acceptance.REPOSITORY_API_URL,
            "default_branch": "master",
            "ignored_secret": "must-not-escape",
        },
    )
    protection_url = f"{collector.GITHUB_API}/branches/master/protection"
    documents[protection_url] = _document(
        protection_url,
        {
            "required_status_checks": {
                "strict": True,
                "contexts": list(acceptance.REQUIRED_CHECKS),
                "checks": [
                    {"context": name, "app_id": acceptance.GITHUB_ACTIONS_APP["id"]}
                    for name in acceptance.REQUIRED_CHECKS
                ],
            },
            "enforce_admins": {"enabled": True},
            "required_linear_history": {"enabled": True},
            "allow_force_pushes": {"enabled": False},
            "allow_deletions": {"enabled": False},
            "required_conversation_resolution": {"enabled": True},
        },
    )
    workflows_url = f"{collector.GITHUB_API}/actions/workflows?per_page=100"
    workflows = [
        {
            "id": contract["workflow_id"],
            "name": contract["workflow_name"],
            "path": contract["workflow_path"],
            "state": "active",
        }
        for contract in acceptance.WORKFLOW_CONTRACTS.values()
    ]
    documents[workflows_url] = _document(
        workflows_url,
        {"total_count": len(workflows), "workflows": workflows},
    )

    check_runs_url = f"{collector.GITHUB_API}/commits/{MASTER_SHA}/check-runs?per_page=100"
    check_runs: list[dict] = []
    for index, name in enumerate(acceptance.REQUIRED_CHECKS, start=1):
        contract = acceptance.WORKFLOW_CONTRACTS[name]
        run_id = 31000000000 + index
        job_id = 41000000000 + index
        suite_id = 51000000000 + index
        details_url = f"{acceptance.REPOSITORY_URL}/actions/runs/{run_id}/job/{job_id}"
        completed = f"2026-07-14T07:2{index}:00Z"
        check_runs.append(
            {
                "id": job_id,
                "name": name,
                "status": "completed",
                "conclusion": "success",
                "details_url": details_url,
                "completed_at": completed,
                "check_suite": {"id": suite_id},
                "app": dict(acceptance.GITHUB_ACTIONS_APP),
            }
        )
        run_url = f"{collector.GITHUB_API}/actions/runs/{run_id}"
        documents[run_url] = _document(
            run_url,
            {
                "id": run_id,
                "workflow_id": contract["workflow_id"],
                "name": contract["workflow_name"],
                "path": contract["workflow_path"],
                "event": "push",
                "run_attempt": 1,
                "status": "completed",
                "conclusion": "success",
                "head_branch": "master",
                "head_sha": MASTER_SHA,
                "check_suite_id": suite_id,
                "html_url": f"{acceptance.REPOSITORY_URL}/actions/runs/{run_id}",
                "created_at": "2026-07-14T07:20:00Z",
            },
        )
        jobs_url = f"{run_url}/jobs?per_page=100"
        jobs = [
            {
                "id": job_id,
                "name": name,
                "status": "completed",
                "conclusion": "success",
                "html_url": details_url,
                "completed_at": completed,
            }
        ]
        documents[jobs_url] = _document(
            jobs_url,
            {"total_count": len(jobs), "jobs": jobs},
        )
    documents[check_runs_url] = _document(
        check_runs_url,
        {"total_count": len(check_runs), "check_runs": check_runs},
    )

    documents[collector.RENDER_SERVICE_URL] = _document(
        collector.RENDER_SERVICE_URL,
        {
            "id": acceptance.PRODUCTION_SERVICE_ID,
            "name": acceptance.PRODUCTION_SERVICE_NAME,
            "type": "web_service",
            "repo": acceptance.REPOSITORY_URL,
            "branch": "master",
            "autoDeployTrigger": "checksPass",
            "serviceDetails": {"healthCheckPath": "/health"},
            "envSpecificDetails": {"secret": "must-not-escape"},
        },
    )
    deploy_url = f"{collector.RENDER_SERVICE_URL}/deploys/{DEPLOY_ID}"
    documents[deploy_url] = _document(
        deploy_url,
        {
            "id": DEPLOY_ID,
            "status": "live",
            "trigger": "new_commit",
            "commit": {"id": MASTER_SHA},
            "createdAt": "2026-07-14T07:30:00.123456Z",
            "finishedAt": "2026-07-14T07:35:00.654321Z",
            "secret": "must-not-escape",
        },
    )
    documents[collector.PRODUCTION_HEALTH_URL] = _document(
        collector.PRODUCTION_HEALTH_URL,
        {"status": "ok", "engine": "cas-engine", "version": "0.1.0"},
    )
    return FakeTransport(documents), documents


def _collect(root: Path, transport: FakeTransport) -> dict:
    return collector.collect_root_ci_protected_deploy_facts(
        expected_master_head=MASTER_SHA,
        expected_deploy_id=DEPLOY_ID,
        repo_root=root,
        transport=transport,
        github_token=GITHUB_TOKEN,
        render_api_key=RENDER_KEY,
        now=NOW,
        repository_head=MASTER_SHA,
    )


class CollectorTests(unittest.TestCase):
    def test_valid_sources_emit_verifier_compatible_unsigned_v2_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport, documents = _fixture(root)
            payload = _collect(root, transport)

        self.assertEqual(payload["schema_version"], acceptance.EVIDENCE_SCHEMA_VERSION)
        self.assertEqual(payload["gate"], "root_ci_protected_deploy")
        self.assertEqual(payload["misplaced_workflow_count"], 0)
        self.assertEqual(payload["deployment"]["commit_sha"], MASTER_SHA)
        deploy_url = f"{collector.RENDER_SERVICE_URL}/deploys/{DEPLOY_ID}"
        self.assertEqual(payload["artifact_uri"], deploy_url)
        self.assertEqual(
            payload["artifact_sha256"],
            hashlib.sha256(documents[deploy_url].raw).hexdigest(),
        )
        rendered = json.dumps(payload, sort_keys=True)
        for forbidden in (
            GITHUB_TOKEN,
            RENDER_KEY,
            "must-not-escape",
            "signature_base64url",
            '"issuer"',
            '"key_id"',
            '"ACCEPT"',
            '"present"',
        ):
            self.assertNotIn(forbidden, rendered)

        context = acceptance.ValidationContext(
            repo_root=ROOT,
            evidence_root=ROOT,
            verification_time=NOW,
            generated_at=NOW,
            expected_master_head=MASTER_SHA,
            expected_deploy_id=DEPLOY_ID,
            repository_commit=MASTER_SHA,
            live=False,
            trusted_issuers={},
            registry_sha256="0" * 64,
        )
        acceptance._validate_root_ci(payload, context)
        self.assertEqual(context.errors, [])

    def test_hostile_source_drift_fails_closed(self) -> None:
        cases = {
            "repository identity": lambda docs: docs[collector.GITHUB_API].payload.__setitem__("id", 1),
            "non-strict protection": lambda docs: docs[f"{collector.GITHUB_API}/branches/master/protection"].payload["required_status_checks"].__setitem__("strict", False),
            "extra required check": lambda docs: docs[f"{collector.GITHUB_API}/branches/master/protection"].payload["required_status_checks"]["contexts"].append("attacker-green"),
            "wrong check app": lambda docs: docs[f"{collector.GITHUB_API}/commits/{MASTER_SHA}/check-runs?per_page=100"].payload["check_runs"][0]["app"].__setitem__("id", 1),
            "duplicate required check app": lambda docs: docs[f"{collector.GITHUB_API}/branches/master/protection"].payload["required_status_checks"]["checks"].append(deepcopy(docs[f"{collector.GITHUB_API}/branches/master/protection"].payload["required_status_checks"]["checks"][0])),
            "manual deploy": lambda docs: docs[f"{collector.RENDER_SERVICE_URL}/deploys/{DEPLOY_ID}"].payload.__setitem__("trigger", "manual"),
            "wrong deploy commit": lambda docs: docs[f"{collector.RENDER_SERVICE_URL}/deploys/{DEPLOY_ID}"].payload["commit"].__setitem__("id", "3" * 40),
            "deploy not live": lambda docs: docs[f"{collector.RENDER_SERVICE_URL}/deploys/{DEPLOY_ID}"].payload.__setitem__("status", "build_in_progress"),
            "commit trigger policy": lambda docs: docs[collector.RENDER_SERVICE_URL].payload.__setitem__("autoDeployTrigger", "commit"),
            "wrong health path": lambda docs: docs[collector.RENDER_SERVICE_URL].payload["serviceDetails"].__setitem__("healthCheckPath", "/"),
            "degraded health": lambda docs: docs[collector.PRODUCTION_HEALTH_URL].payload.__setitem__("status", "degraded"),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                transport, documents = _fixture(root)
                mutate(documents)
                with self.assertRaises(collector.CollectorError):
                    _collect(root, transport)

    def test_run_and_job_identity_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport, documents = _fixture(root)
            name = acceptance.REQUIRED_CHECKS[0]
            check_url = f"{collector.GITHUB_API}/commits/{MASTER_SHA}/check-runs?per_page=100"
            check = documents[check_url].payload["check_runs"][0]
            run_id = int(check["details_url"].split("/runs/")[1].split("/")[0])
            run_url = f"{collector.GITHUB_API}/actions/runs/{run_id}"
            documents[run_url].payload["head_sha"] = "4" * 40
            with self.assertRaisesRegex(collector.CollectorError, "head_sha"):
                _collect(root, transport)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport, documents = _fixture(root)
            check_url = f"{collector.GITHUB_API}/commits/{MASTER_SHA}/check-runs?per_page=100"
            check = documents[check_url].payload["check_runs"][0]
            run_id = int(check["details_url"].split("/runs/")[1].split("/")[0])
            jobs_url = f"{collector.GITHUB_API}/actions/runs/{run_id}/jobs?per_page=100"
            documents[jobs_url].payload["jobs"][0]["conclusion"] = "failure"
            with self.assertRaisesRegex(collector.CollectorError, "did not pass"):
                _collect(root, transport)

    def test_duplicate_check_and_partial_pagination_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport, documents = _fixture(root)
            check_url = f"{collector.GITHUB_API}/commits/{MASTER_SHA}/check-runs?per_page=100"
            duplicate = deepcopy(documents[check_url].payload["check_runs"][0])
            duplicate["id"] += 99
            documents[check_url].payload["check_runs"].append(duplicate)
            documents[check_url].payload["total_count"] += 1
            with self.assertRaisesRegex(collector.CollectorError, "ambiguous"):
                _collect(root, transport)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport, documents = _fixture(root)
            workflows_url = f"{collector.GITHUB_API}/actions/workflows?per_page=100"
            documents[workflows_url] = collector.HttpDocument(
                url=workflows_url,
                raw=documents[workflows_url].raw,
                payload=documents[workflows_url].payload,
                headers={"link": '<https://api.github.test/next>; rel="next"'},
            )
            with self.assertRaisesRegex(collector.CollectorError, "pagination"):
                _collect(root, transport)

    def test_deploy_cannot_start_before_required_checks_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport, documents = _fixture(root)
            deploy_url = f"{collector.RENDER_SERVICE_URL}/deploys/{DEPLOY_ID}"
            documents[deploy_url].payload["createdAt"] = "2026-07-14T07:20:30Z"
            with self.assertRaisesRegex(collector.CollectorError, "before all required checks"):
                _collect(root, transport)

    def test_wait_polls_only_the_exact_deploy_until_it_is_live(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, documents = _fixture(root)
            deploy_url = f"{collector.RENDER_SERVICE_URL}/deploys/{DEPLOY_ID}"
            live = deepcopy(documents[deploy_url].payload)
            pending = deepcopy(live)
            pending["status"] = "build_in_progress"
            transport = SequencedDeployTransport(
                documents,
                deploy_url,
                [pending, live],
            )
            sleeps: list[int] = []
            payload = collector.collect_root_ci_protected_deploy_facts(
                expected_master_head=MASTER_SHA,
                expected_deploy_id=DEPLOY_ID,
                repo_root=root,
                transport=transport,
                github_token=GITHUB_TOKEN,
                render_api_key=RENDER_KEY,
                now=NOW,
                repository_head=MASTER_SHA,
                deploy_wait_seconds=10,
                deploy_poll_seconds=1,
                sleeper=sleeps.append,
            )

        self.assertEqual(payload["deploy_id"], DEPLOY_ID)
        self.assertEqual(sleeps, [1])
        deploy_requests = [url for url, _, _ in transport.requests if "/deploys/" in url]
        self.assertEqual(deploy_requests, [deploy_url, deploy_url])

    def test_wait_never_tolerates_terminal_or_unknown_deploy_status(self) -> None:
        for status in ("build_failed", "canceled", "attacker_green"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _, documents = _fixture(root)
                deploy_url = f"{collector.RENDER_SERVICE_URL}/deploys/{DEPLOY_ID}"
                failed = deepcopy(documents[deploy_url].payload)
                failed["status"] = status
                transport = SequencedDeployTransport(documents, deploy_url, [failed])
                with self.assertRaisesRegex(collector.CollectorError, "terminal or unknown"):
                    collector.collect_root_ci_protected_deploy_facts(
                        expected_master_head=MASTER_SHA,
                        expected_deploy_id=DEPLOY_ID,
                        repo_root=root,
                        transport=transport,
                        github_token=GITHUB_TOKEN,
                        render_api_key=RENDER_KEY,
                        now=NOW,
                        repository_head=MASTER_SHA,
                        deploy_wait_seconds=10,
                        deploy_poll_seconds=1,
                        sleeper=lambda _: None,
                    )

    def test_misplaced_workflow_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport, _ = _fixture(root)
            misplaced = root / "nested" / ".github" / "workflows" / "bad.yml"
            misplaced.parent.mkdir(parents=True)
            misplaced.write_text("name: bad\n", encoding="utf-8")
            with self.assertRaisesRegex(collector.CollectorError, "misplaced"):
                _collect(root, transport)

    def test_stale_facts_and_local_head_mismatch_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport, _ = _fixture(root)
            with self.assertRaisesRegex(collector.CollectorError, "local HEAD"):
                collector.collect_root_ci_protected_deploy_facts(
                    expected_master_head=MASTER_SHA,
                    expected_deploy_id=DEPLOY_ID,
                    repo_root=root,
                    transport=transport,
                    github_token=GITHUB_TOKEN,
                    render_api_key=RENDER_KEY,
                    now=NOW,
                    repository_head="5" * 40,
                )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport, _ = _fixture(root)
            with self.assertRaisesRegex(collector.CollectorError, "stale"):
                collector.collect_root_ci_protected_deploy_facts(
                    expected_master_head=MASTER_SHA,
                    expected_deploy_id=DEPLOY_ID,
                    repo_root=root,
                    transport=transport,
                    github_token=GITHUB_TOKEN,
                    render_api_key=RENDER_KEY,
                    now=datetime(2026, 7, 16, tzinfo=timezone.utc),
                    repository_head=MASTER_SHA,
                )


class _FakeHeaders(dict):
    def items(self):
        return super().items()


class _FakeResponse:
    def __init__(self, raw: bytes, *, url: str, status: int = 200, content_type: str = "application/json") -> None:
        self._stream = io.BytesIO(raw)
        self._url = url
        self.status = status
        self.headers = _FakeHeaders({"Content-Type": content_type})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return self._url

    def read(self, amount: int) -> bytes:
        return self._stream.read(amount)


class _FakeOpener:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error

    def open(self, request, timeout):
        if self.error is not None:
            raise self.error
        return self.response


class HttpClientTests(unittest.TestCase):
    def test_redirect_and_oversize_are_rejected(self) -> None:
        requested = "https://api.example.test/value"
        redirected = _FakeResponse(b"{}", url="https://attacker.test/value")
        client = collector.HttpJsonClient(opener=_FakeOpener(redirected))
        with self.assertRaisesRegex(collector.CollectorError, "redirected"):
            client.get_json(requested, headers={}, label="source")

        oversized = _FakeResponse(b"{" + (b"x" * 32), url=requested)
        client = collector.HttpJsonClient(max_response_bytes=8, opener=_FakeOpener(oversized))
        with self.assertRaisesRegex(collector.CollectorError, "size limit"):
            client.get_json(requested, headers={}, label="source")

    def test_http_error_body_and_duplicate_json_values_are_suppressed(self) -> None:
        requested = "https://api.example.test/value"
        error = urllib.error.HTTPError(
            requested,
            403,
            "forbidden-secret-body",
            {},
            io.BytesIO(b"credential=must-not-escape"),
        )
        client = collector.HttpJsonClient(opener=_FakeOpener(error=error))
        with self.assertRaises(collector.CollectorError) as exc_info:
            client.get_json(requested, headers={"Authorization": "secret"}, label="source")
        self.assertNotIn("must-not-escape", str(exc_info.exception))
        self.assertNotIn("forbidden-secret-body", str(exc_info.exception))

        duplicate = _FakeResponse(b'{"a":1,"a":2}', url=requested)
        client = collector.HttpJsonClient(opener=_FakeOpener(duplicate))
        with self.assertRaisesRegex(collector.CollectorError, "duplicate JSON key"):
            client.get_json(requested, headers={}, label="source")


if __name__ == "__main__":
    unittest.main()
