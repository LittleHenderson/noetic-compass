from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import collect_operational_acceptance_draft as collector


NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
STAMP = "2026-07-14T12:00:00Z"
MASTER = "f475bff625dc3f2191d12022d9bb73091f635585"
DEPLOY = "dep-d9avd7eq1p3s73crb8o0"
RUN_ID = 29317935223
ISSUE_NUMBER = 154


class FakeHeaders(dict[str, str]):
    def get_content_type(self) -> str:
        return self.get("Content-Type", "application/octet-stream").split(";", 1)[0]


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        content_type: str = "application/json",
        content_length: str | None = None,
        link: str | None = None,
    ) -> None:
        self._body = io.BytesIO(body)
        self._status = status
        self.headers = FakeHeaders({"Content-Type": content_type})
        if content_length is not None:
            self.headers["Content-Length"] = content_length
        if link is not None:
            self.headers["Link"] = link

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def getcode(self) -> int:
        return self._status

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)


class FakeOpener:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requests: list[object] = []

    def open(self, request: object, timeout: float) -> FakeResponse:
        self.requests.append(request)
        return self.response


def _json_fetch(name: str, url: str, value: object, status: int = 200) -> collector.FetchResult:
    raw = json.dumps(value, sort_keys=True).encode("utf-8")
    return collector.FetchResult(
        name=name,
        url=url,
        fetched_at_utc=STAMP,
        http_status=status,
        content_type="application/json",
        byte_length=len(raw),
        content_sha256=hashlib.sha256(raw).hexdigest(),
        raw=raw,
    )


def _bytes_fetch(
    name: str,
    url: str,
    body: bytes = b"ok",
    *,
    status: int = 200,
    content_type: str = "text/html",
) -> collector.FetchResult:
    return collector.FetchResult(
        name=name,
        url=url,
        fetched_at_utc=STAMP,
        http_status=status,
        content_type=content_type,
        byte_length=len(body),
        content_sha256=hashlib.sha256(body).hexdigest(),
        raw=body,
        error=None if status == 200 else f"http_{status}",
    )


def _openapi(*, include_support: bool = False) -> dict[str, object]:
    paths: dict[str, object] = {}
    for method, path in (*collector.HOSTED_JOURNEY_OPERATIONS, *collector.CRM_OPERATIONS):
        paths.setdefault(path, {})[method] = {"operationId": f"{method}-{path}"}  # type: ignore[index]
    if include_support:
        for method, path in collector.SUPPORT_TICKET_OPERATIONS:
            paths.setdefault(path, {})[method] = {"operationId": f"{method}-{path}"}  # type: ignore[index]
    return {"openapi": "3.1.0", "paths": paths}


def _incident(*, closed: bool = False) -> dict[str, object]:
    status = "CLOSED" if closed else "OPEN"
    return {
        "incident_id": "IR-2026-07-13-001",
        "status": status,
        "compromise_status": "not_established",
        "roles": {
            "incident_commander": "assigned" if closed else "[ASSIGN]",
            "security": "assigned" if closed else "[ASSIGN]",
        },
        "open_actions": []
        if closed
        else [{"id": "IR-ACT-001", "status": "OPEN"}],
        "tabletop": {"exercise_status": "completed" if closed else "participant_run_pending"},
    }


def _public_fetcher(*, contact_status: int = 404, include_support: bool = False):
    openapi = _openapi(include_support=include_support)

    def fetch(name: str, url: str) -> collector.FetchResult:
        if name == "api_openapi":
            return _json_fetch(name, url, openapi)
        if name == "public_support":
            return _bytes_fetch(name, url, status=contact_status)
        return _bytes_fetch(name, url)

    return fetch


def _github_documents() -> dict[str, object]:
    run_url = f"https://github.com/{collector.REPOSITORY}/actions/runs/{RUN_ID}"
    return {
        "run": {
            "id": RUN_ID,
            "path": collector.RUNTIME_MONITOR_WORKFLOW_PATH,
            "head_sha": MASTER,
            "status": "completed",
            "conclusion": "failure",
            "created_at": "2026-07-14T11:40:00Z",
            "updated_at": "2026-07-14T11:41:00Z",
            "repository": {"id": collector.REPOSITORY_ID},
        },
        "jobs": {
            "jobs": [
                {
                    "name": name,
                    "conclusion": (
                        "success"
                        if name == "cas-production-runtime-alert-delivery"
                        else "failure"
                    ),
                }
                for name in sorted(collector.ALERT_JOB_NAMES)
            ]
        },
        "issue": {
            "number": ISSUE_NUMBER,
            "title": collector.ALERT_ISSUE_TITLE,
            "state": "open",
            "created_at": "2026-07-14T11:40:20Z",
            "updated_at": "2026-07-14T11:41:00Z",
            "labels": [{"name": collector.ALERT_ISSUE_LABEL}],
            "body": f"Automated alert. Run: {run_url}",
        },
        "comments": [
            {
                "id": 1,
                "body": f"Automated alert. Run: {run_url}",
                "created_at": "2026-07-14T11:40:30Z",
                "user": {"login": "github-actions"},
            },
            {
                "id": 2,
                "body": "ACK diagnosis includes a secret-looking word but no secret value",
                "created_at": "2026-07-14T11:41:00Z",
                "user": {"login": "operator-example"},
            },
            {
                "id": 3,
                "body": "ESCALATE secondary_on_call",
                "created_at": "2026-07-14T11:42:00Z",
                "user": {"login": "operator-example"},
            },
        ],
    }


class OperationalAcceptanceCollectorTests(unittest.TestCase):
    def test_root_ci_runs_this_collector_contract(self) -> None:
        workflow_path = (
            Path(__file__).resolve().parents[2]
            / ".github"
            / "workflows"
            / "ci.yml"
        )
        workflow = workflow_path.read_text(encoding="utf-8")
        self.assertIn("Run the operational acceptance draft collector tests", workflow)
        self.assertIn("-p 'test_collect_operational_acceptance_draft.py'", workflow)

    def test_url_policy_rejects_credentials_fragments_and_unpinned_origins(self) -> None:
        bad = (
            "https://user:secret@api.github.com/repos/x",
            "https://example.com/",
            "https://cascompass.ai/contact#fragment",
            "http://cascompass.ai/contact",
            "https://api.github.com/repos/x?per_page=99",
        )
        for url in bad:
            with self.subTest(url=url):
                with self.assertRaises(collector.CollectorError):
                    collector._validate_pinned_url(url)

    def test_github_fetch_fails_closed_without_token_before_network(self) -> None:
        opener = FakeOpener(FakeResponse(b"{}"))
        result = collector.fetch_pinned(
            "github_run",
            f"{collector.REPOSITORY_API_ORIGIN}/repos/{collector.REPOSITORY}/actions/runs/1",
            opener=opener,
            github_token=None,
            timeout_seconds=1,
            max_response_bytes=100,
            clock=lambda: NOW,
        )
        self.assertEqual(result.error, "github_token_unavailable")
        self.assertEqual(opener.requests, [])

    def test_fetch_hashes_exact_bytes_and_refuses_oversize(self) -> None:
        body = b'{"ok":true}'
        opener = FakeOpener(FakeResponse(body))
        result = collector.fetch_pinned(
            "api_health",
            f"{collector.PRODUCTION_API_ORIGIN}/health",
            opener=opener,
            github_token=None,
            timeout_seconds=1,
            max_response_bytes=100,
            clock=lambda: NOW,
        )
        self.assertEqual(result.content_sha256, hashlib.sha256(body).hexdigest())
        self.assertNotIn("raw", collector._fetch_summary(result))

        oversized = FakeOpener(FakeResponse(b"x", content_length="101"))
        with self.assertRaises(collector.ResponseTooLarge):
            collector.fetch_pinned(
                "api_health",
                f"{collector.PRODUCTION_API_ORIGIN}/health",
                opener=oversized,
                github_token=None,
                timeout_seconds=1,
                max_response_bytes=100,
                clock=lambda: NOW,
            )

    def test_current_shape_stays_open_and_names_all_four_gate_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            incident_path = Path(temp) / "incident.json"
            incident_path.write_text(json.dumps(_incident()), encoding="utf-8")
            report = collector.collect_operational_report(
                target_master_head=MASTER,
                target_deploy_id=DEPLOY,
                incident_path=incident_path,
                fetcher=_public_fetcher(contact_status=404, include_support=False),
                clock=lambda: NOW,
            )

        self.assertEqual(report["customer_production_status"], "OPEN")
        self.assertFalse(report["authoritative"])
        self.assertFalse(report["signed"])
        self.assertFalse(report["can_promote_manifest_gate"])
        self.assertEqual(set(report["gates"]), set(collector.GATES))
        self.assertFalse(report["summary"]["acceptance_evidence_complete"])
        self.assertIn(
            "public_contact_page_not_http_200",
            report["gates"]["support_crm"]["machine_blockers"],
        )
        self.assertIn(
            "support_ticket_source_operations_missing",
            report["gates"]["support_crm"]["machine_blockers"],
        )
        self.assertIn(
            "incident_record_not_closed",
            report["gates"]["incident_tabletop"]["machine_blockers"],
        )
        self.assertIn(
            "exact_runtime_monitor_run_not_selected",
            report["gates"]["alert_delivery"]["machine_blockers"],
        )
        hosted = report["gates"]["hosted_customer_journey"]
        self.assertFalse(hosted["machine_prerequisites_passed"])
        self.assertIn(
            "live_authority_endpoint_missing_and_no_signed_receipt_inspected",
            hosted["machine_blockers"],
        )
        self.assertTrue(
            all(
                row["found"]
                for row in hosted["machine_facts"]["required_openapi_operations"]
            )
        )
        self.assertTrue(
            hosted["active_or_human_evidence_missing"]
        )

    def test_alert_issue_proves_only_machine_incident_channel_delivery(self) -> None:
        documents = _github_documents()
        urls = collector._github_urls(RUN_ID, ISSUE_NUMBER)
        by_url = {
            urls[key]: _json_fetch(f"github_{key}", urls[key], value)
            for key, value in documents.items()
        }
        public = _public_fetcher(contact_status=200, include_support=True)

        def fetch(name: str, url: str) -> collector.FetchResult:
            return by_url.get(url) or public(name, url)

        with tempfile.TemporaryDirectory() as temp:
            incident_path = Path(temp) / "incident.json"
            incident_path.write_text(json.dumps(_incident(closed=True)), encoding="utf-8")
            report = collector.collect_operational_report(
                target_master_head=MASTER,
                target_deploy_id=DEPLOY,
                run_id=RUN_ID,
                issue_number=ISSUE_NUMBER,
                incident_path=incident_path,
                fetcher=fetch,
                clock=lambda: NOW,
            )

        alert = report["gates"]["alert_delivery"]
        facts = alert["machine_facts"]["github_alert"]
        self.assertTrue(facts["incident_channel_machine_delivery_verified"])
        self.assertEqual(facts["comment_candidates"]["ack_candidate_count"], 1)
        self.assertEqual(facts["comment_candidates"]["escalation_candidate_count"], 1)
        self.assertFalse(facts["human_acknowledgement_verified"])
        self.assertFalse(facts["secondary_escalation_verified"])
        self.assertIn(
            "incident_commander_acknowledgement_not_verified",
            alert["machine_blockers"],
        )
        rendered = json.dumps(report)
        self.assertNotIn("ACK diagnosis", rendered)
        self.assertNotIn("ESCALATE secondary_on_call", rendered)
        self.assertNotIn("operator-example", rendered)

    def test_github_head_or_pagination_mismatch_fails_closed(self) -> None:
        documents = _github_documents()
        documents["run"]["head_sha"] = "0" * 40  # type: ignore[index]
        urls = collector._github_urls(RUN_ID, ISSUE_NUMBER)
        fetched = {
            key: _json_fetch(f"github_{key}", urls[key], value)
            for key, value in documents.items()
        }
        fetched["comments"].pagination_incomplete = True

        def fetch(name: str, url: str) -> collector.FetchResult:
            for key, pinned in urls.items():
                if url == pinned:
                    return fetched[key]
            return _public_fetcher(contact_status=200, include_support=True)(name, url)

        alert, blockers = collector._alert_summary(
            fetcher=fetch,
            target_master_head=MASTER,
            run_id=RUN_ID,
            issue_number=ISSUE_NUMBER,
        )
        self.assertTrue(alert["github_facts_collected"])
        self.assertIn("runtime_monitor_head_sha_mismatch", blockers)
        self.assertIn("github_comments_pagination_incomplete", blockers)

    def test_invalid_target_bindings_and_partial_alert_selection_are_rejected(self) -> None:
        with self.assertRaises(collector.CollectorError):
            collector.collect_operational_report(
                target_master_head="F" * 40,
                target_deploy_id=DEPLOY,
                fetcher=_public_fetcher(),
            )
        with self.assertRaises(collector.CollectorError):
            collector.collect_operational_report(
                target_master_head=MASTER,
                target_deploy_id="latest",
                fetcher=_public_fetcher(),
            )
        with self.assertRaises(collector.CollectorError):
            collector.collect_operational_report(
                target_master_head=MASTER,
                target_deploy_id=DEPLOY,
                run_id=RUN_ID,
                issue_number=None,
                fetcher=_public_fetcher(),
            )

    def test_report_has_no_acceptance_shaped_evidence_or_secret_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            incident_path = Path(temp) / "incident.json"
            incident_path.write_text(json.dumps(_incident()), encoding="utf-8")
            report = collector.collect_operational_report(
                target_master_head=MASTER,
                target_deploy_id=DEPLOY,
                incident_path=incident_path,
                fetcher=_public_fetcher(),
                clock=lambda: NOW,
            )
        rendered = json.dumps(report, sort_keys=True)
        self.assertNotIn('"status": "present"', rendered)
        self.assertNotIn('"customer_production_status": "ACCEPT"', rendered)
        for prohibited in ("token", "password", "cookie", "authorization", "private_key"):
            self.assertNotIn(f'"{prohibited}"', rendered.lower())


if __name__ == "__main__":
    unittest.main()
