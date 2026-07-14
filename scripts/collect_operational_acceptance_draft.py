#!/usr/bin/env python3
"""Collect read-only machine facts for four OPEN operational launch gates.

This collector deliberately does *not* produce customer-production acceptance
evidence.  It inspects pinned public surfaces, the deployed OpenAPI document,
one checked-in incident record, and (when exact IDs are supplied) one GitHub
runtime-monitor run and its deduplicated alert issue.  The resulting document
is always unsigned, non-authoritative, and ``OPEN``.

The purpose is to make missing evidence explicit without turning route
presence, a local JSON file, a bot-authored issue, or an unverified ``ACK``
comment into approval.  It performs no customer, provider, issue, or account
writes and never records a GitHub token or response body.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


REPORT_SCHEMA_VERSION = "cas_harness_operational_acceptance_machine_draft.v1"
REPOSITORY = "LittleHenderson/noetic-compass"
REPOSITORY_ID = 1203465584
REPOSITORY_API_ORIGIN = "https://api.github.com"
PRODUCTION_APP_ORIGIN = "https://atlas.noeticcompass.com"
PRODUCTION_API_ORIGIN = "https://noetic-compass-api.onrender.com"
LANDING_ORIGIN = "https://cascompass.ai"
PRODUCTION_SERVICE_ID = "srv-d82ph683kofs73d210e0"
RUNTIME_MONITOR_WORKFLOW_PATH = ".github/workflows/production-runtime-monitor.yml"
ALERT_ISSUE_TITLE = "CAS production runtime monitor is failing"
ALERT_ISSUE_LABEL = "cas-production-runtime-alert"
ALERT_JOB_NAMES = frozenset(
    {
        "production-api-dependency-readiness",
        "production-worker-realmode",
        "production-render-blueprint-drift",
        "cas-production-runtime-monitor-gate",
        "cas-production-runtime-alert-delivery",
    }
)
GATES = (
    "hosted_customer_journey",
    "support_crm",
    "incident_tabletop",
    "alert_delivery",
)

PINNED_SURFACES: tuple[tuple[str, str], ...] = (
    ("audit_console", f"{PRODUCTION_APP_ORIGIN}/audit-console"),
    ("api_health", f"{PRODUCTION_API_ORIGIN}/health"),
    ("api_openapi", f"{PRODUCTION_API_ORIGIN}/openapi.json"),
    ("public_support", f"{LANDING_ORIGIN}/contact"),
)

HOSTED_JOURNEY_OPERATIONS: tuple[tuple[str, str], ...] = (
    ("post", "/api/cas-harness/audit/session"),
    ("get", "/api/cas-harness/audit/session/{audit_id}/status"),
    ("get", "/evidence/{trace_id}"),
    ("post", "/evidence/{trace_id}/verify"),
    ("post", "/evidence/{trace_id}/shares"),
    ("get", "/evidence/shared/{share_id}"),
    ("delete", "/evidence/shares/{share_id}"),
)
CRM_OPERATIONS: tuple[tuple[str, str], ...] = (
    ("post", "/api/crm/public/leads"),
    ("get", "/api/crm/leads/{lead_id}"),
    ("patch", "/api/crm/leads/{lead_id}/pipeline-status"),
)
SUPPORT_TICKET_OPERATIONS: tuple[tuple[str, str], ...] = (
    ("post", "/api/support/tickets"),
    ("get", "/api/support/tickets/{ticket_id}"),
)
LIVE_AUTHORITY_OPERATIONS: Mapping[str, tuple[str, str]] = {
    "hosted_customer_journey": ("get", "/internal/acceptance/customer-journey"),
    "support_crm": ("get", "/internal/acceptance/support-crm"),
    "incident_tabletop": ("get", "/internal/acceptance/incident-tabletop"),
    "alert_delivery": ("get", "/internal/acceptance/alert-delivery"),
}

DEFAULT_INCIDENT_PATH = (
    Path("noetic-compass-scaffold")
    / "noetic-compass"
    / "docs"
    / "working"
    / "incident_response"
    / "IR-2026-07-13-001.json"
)
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RESPONSE_BYTES = 2_000_000
MAX_RESPONSE_BYTES = 2_000_000
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
DEPLOY_ID_RE = re.compile(r"^dep-[a-z0-9]{8,64}$")
ACK_RE = re.compile(r"^ACK(?:\s|$)", re.IGNORECASE)
ESCALATION_RE = re.compile(
    r"^(?:ESCALATE|ESCALATION)(?:\s|$).*\bsecondary[_ -]on[_ -]call\b",
    re.IGNORECASE,
)


class CollectorError(RuntimeError):
    """The collector configuration or a pinned response is unsafe."""


class ResponseTooLarge(CollectorError):
    """A response cannot be hashed exactly within the configured limit."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


@dataclass
class FetchResult:
    name: str
    url: str
    fetched_at_utc: str
    http_status: int | None = None
    content_type: str | None = None
    byte_length: int | None = None
    content_sha256: str | None = None
    error: str | None = None
    raw: bytes | None = field(default=None, repr=False)
    pagination_incomplete: bool = False


Fetcher = Callable[[str, str], FetchResult]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_pinned_url(url: str) -> urllib.parse.SplitResult:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise CollectorError("every collector URL must use absolute HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise CollectorError("credentialized URLs are prohibited")
    if parsed.fragment:
        raise CollectorError("URL fragments are prohibited")
    origin = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port is not None:
        origin = f"{origin}:{parsed.port}"
    allowed_origins = {
        PRODUCTION_APP_ORIGIN,
        PRODUCTION_API_ORIGIN,
        LANDING_ORIGIN,
        REPOSITORY_API_ORIGIN,
    }
    if origin not in allowed_origins:
        raise CollectorError("collector URL origin is not pinned")
    if parsed.query:
        if origin != REPOSITORY_API_ORIGIN or parsed.query != "per_page=100":
            raise CollectorError("only the pinned GitHub pagination query is allowed")
    return parsed


def _read_bounded(response: Any, max_response_bytes: int) -> bytes:
    declared = response.headers.get("Content-Length")
    if declared:
        try:
            declared_length = int(declared)
        except ValueError as exc:
            raise CollectorError("response Content-Length is invalid") from exc
        if declared_length < 0 or declared_length > max_response_bytes:
            raise ResponseTooLarge("response exceeds the configured byte limit")
    raw = response.read(max_response_bytes + 1)
    if len(raw) > max_response_bytes:
        raise ResponseTooLarge("response exceeds the configured byte limit")
    return raw


def fetch_pinned(
    name: str,
    url: str,
    *,
    opener: Any,
    github_token: str | None,
    timeout_seconds: float,
    max_response_bytes: int,
    clock: Callable[[], datetime] = _utc_now,
) -> FetchResult:
    parsed = _validate_pinned_url(url)
    headers = {
        "Accept": "application/vnd.github+json" if parsed.hostname == "api.github.com" else "*/*",
        "User-Agent": "cas-harness-operational-acceptance-collector/1",
    }
    if parsed.hostname == "api.github.com":
        if not github_token:
            return FetchResult(
                name=name,
                url=url,
                fetched_at_utc=_format_utc(clock()),
                error="github_token_unavailable",
            )
        headers["Authorization"] = f"Bearer {github_token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers, method="GET")
    fetched_at = _format_utc(clock())
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            raw = _read_bounded(response, max_response_bytes)
            status = int(response.getcode())
            link = response.headers.get("Link", "")
            return FetchResult(
                name=name,
                url=url,
                fetched_at_utc=fetched_at,
                http_status=status,
                content_type=response.headers.get_content_type(),
                byte_length=len(raw),
                content_sha256=hashlib.sha256(raw).hexdigest(),
                raw=raw,
                pagination_incomplete='rel="next"' in link,
            )
    except urllib.error.HTTPError as exc:
        raw = _read_bounded(exc, max_response_bytes)
        if 300 <= int(exc.code) < 400:
            error = "redirect_refused"
        else:
            error = f"http_{int(exc.code)}"
        return FetchResult(
            name=name,
            url=url,
            fetched_at_utc=fetched_at,
            http_status=int(exc.code),
            content_type=exc.headers.get_content_type() if exc.headers else None,
            byte_length=len(raw),
            content_sha256=hashlib.sha256(raw).hexdigest(),
            error=error,
            raw=raw,
        )
    except ResponseTooLarge:
        raise
    except (urllib.error.URLError, TimeoutError, OSError):
        return FetchResult(
            name=name,
            url=url,
            fetched_at_utc=fetched_at,
            error="request_failed",
        )


def _fetch_summary(result: FetchResult) -> dict[str, Any]:
    return {
        "name": result.name,
        "url": result.url,
        "fetched_at_utc": result.fetched_at_utc,
        "http_status": result.http_status,
        "content_type": result.content_type,
        "byte_length": result.byte_length,
        "content_sha256": result.content_sha256,
        "error": result.error,
        "pagination_incomplete": result.pagination_incomplete,
    }


def _json_body(result: FetchResult) -> Any | None:
    if result.http_status != 200 or result.raw is None:
        return None
    try:
        return json.loads(result.raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _operation_presence(
    openapi: Mapping[str, Any] | None,
    operations: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    paths = openapi.get("paths") if isinstance(openapi, Mapping) else None
    if not isinstance(paths, Mapping):
        paths = {}
    results: list[dict[str, Any]] = []
    for method, path in operations:
        item = paths.get(path)
        found = isinstance(item, Mapping) and isinstance(item.get(method), Mapping)
        results.append({"method": method.upper(), "path": path, "found": found})
    return results


def _collector_sha256() -> str:
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except OSError:
        return "unavailable"


def _git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    value = result.stdout.strip().lower()
    return value if SHA1_RE.fullmatch(value) else "unavailable"


def _incident_summary(path: Path) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return (
            {
                "path": path.as_posix(),
                "loaded": False,
                "content_sha256": None,
            },
            ["checked_in_incident_record_unavailable"],
        )
    if not isinstance(document, Mapping):
        return (
            {
                "path": path.as_posix(),
                "loaded": False,
                "content_sha256": hashlib.sha256(raw).hexdigest(),
            },
            ["checked_in_incident_record_not_an_object"],
        )
    roles = document.get("roles")
    assigned_roles = 0
    required_roles = 0
    if isinstance(roles, Mapping):
        required_roles = len(roles)
        assigned_roles = sum(
            isinstance(value, str) and not value.strip().startswith("[ASSIGN")
            for value in roles.values()
        )
    actions = document.get("open_actions")
    action_rows = actions if isinstance(actions, list) else []
    open_action_count = sum(
        not isinstance(row, Mapping) or row.get("status") != "CLOSED"
        for row in action_rows
    )
    tabletop = document.get("tabletop")
    tabletop_status = (
        tabletop.get("exercise_status") if isinstance(tabletop, Mapping) else None
    )
    status = document.get("status")
    if status != "CLOSED":
        blockers.append("incident_record_not_closed")
    if open_action_count != 0:
        blockers.append("incident_open_actions_remain")
    if assigned_roles != required_roles or required_roles == 0:
        blockers.append("incident_roles_not_fully_assigned")
    if tabletop_status != "completed":
        blockers.append("tabletop_participant_run_not_completed")
    return (
        {
            "path": path.as_posix(),
            "loaded": True,
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "incident_id": document.get("incident_id"),
            "status": status,
            "compromise_status": document.get("compromise_status"),
            "required_role_count": required_roles,
            "assigned_role_count": assigned_roles,
            "open_action_count": open_action_count,
            "tabletop_exercise_status": tabletop_status,
        },
        blockers,
    )


def _github_urls(run_id: int, issue_number: int) -> dict[str, str]:
    base = f"{REPOSITORY_API_ORIGIN}/repos/{REPOSITORY}"
    return {
        "run": f"{base}/actions/runs/{run_id}",
        "jobs": f"{base}/actions/runs/{run_id}/jobs?per_page=100",
        "issue": f"{base}/issues/{issue_number}",
        "comments": f"{base}/issues/{issue_number}/comments?per_page=100",
    }


def _safe_comment_candidates(comments: Any) -> dict[str, Any]:
    acknowledgement: list[dict[str, Any]] = []
    escalation: list[dict[str, Any]] = []
    if not isinstance(comments, list):
        return {
            "ack_candidate_count": 0,
            "ack_candidates": [],
            "escalation_candidate_count": 0,
            "escalation_candidates": [],
        }
    for row in comments:
        if not isinstance(row, Mapping):
            continue
        body = row.get("body")
        author = row.get("user")
        login = author.get("login") if isinstance(author, Mapping) else None
        if not isinstance(body, str) or not isinstance(login, str):
            continue
        normalized_login = login.lower()
        if normalized_login in {"github-actions", "github-actions[bot]"} or normalized_login.endswith("[bot]"):
            continue
        candidate = {
            "comment_id": row.get("id"),
            "created_at_utc": row.get("created_at"),
            "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "author_login_sha256": hashlib.sha256(login.encode("utf-8")).hexdigest(),
            "role_assignment_verified": False,
        }
        if ACK_RE.search(body.strip()):
            acknowledgement.append(candidate)
        if ESCALATION_RE.search(body.strip()):
            escalation.append(candidate)
    return {
        "ack_candidate_count": len(acknowledgement),
        "ack_candidates": acknowledgement,
        "escalation_candidate_count": len(escalation),
        "escalation_candidates": escalation,
    }


def _alert_summary(
    *,
    fetcher: Fetcher,
    target_master_head: str,
    run_id: int | None,
    issue_number: int | None,
) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    if run_id is None or issue_number is None:
        if run_id is None:
            blockers.append("exact_runtime_monitor_run_not_selected")
        if issue_number is None:
            blockers.append("exact_alert_issue_not_selected")
        blockers.extend(
            [
                "incident_channel_delivery_not_verified",
                "primary_on_call_delivery_receipt_missing",
                "incident_commander_acknowledgement_not_verified",
                "secondary_on_call_escalation_receipt_missing",
            ]
        )
        return (
            {
                "selected_run_id": run_id,
                "selected_issue_number": issue_number,
                "github_facts_collected": False,
                "incident_channel_machine_delivery_verified": False,
                "human_acknowledgement_verified": False,
                "secondary_escalation_verified": False,
            },
            blockers,
        )

    urls = _github_urls(run_id, issue_number)
    fetched = {key: fetcher(f"github_{key}", url) for key, url in urls.items()}
    documents = {key: _json_body(value) for key, value in fetched.items()}
    for key, result in fetched.items():
        if result.http_status != 200 or documents[key] is None:
            blockers.append(f"github_{key}_readback_failed")
        if result.pagination_incomplete:
            blockers.append(f"github_{key}_pagination_incomplete")

    run = documents["run"] if isinstance(documents["run"], Mapping) else {}
    jobs_doc = documents["jobs"] if isinstance(documents["jobs"], Mapping) else {}
    issue = documents["issue"] if isinstance(documents["issue"], Mapping) else {}
    comments = documents["comments"] if isinstance(documents["comments"], list) else []

    repository = run.get("repository")
    repository_id = repository.get("id") if isinstance(repository, Mapping) else None
    if run.get("id") != run_id:
        blockers.append("runtime_monitor_run_id_mismatch")
    if run.get("path") != RUNTIME_MONITOR_WORKFLOW_PATH:
        blockers.append("runtime_monitor_workflow_path_mismatch")
    if run.get("head_sha") != target_master_head:
        blockers.append("runtime_monitor_head_sha_mismatch")
    if run.get("status") != "completed":
        blockers.append("runtime_monitor_run_not_completed")
    if run.get("conclusion") != "failure":
        blockers.append("runtime_monitor_run_is_not_a_p1_failure_drill")
    if repository_id != REPOSITORY_ID:
        blockers.append("runtime_monitor_repository_identity_mismatch")

    jobs = jobs_doc.get("jobs") if isinstance(jobs_doc, Mapping) else None
    job_rows = jobs if isinstance(jobs, list) else []
    jobs_by_name = {
        row.get("name"): row
        for row in job_rows
        if isinstance(row, Mapping) and isinstance(row.get("name"), str)
    }
    missing_jobs = sorted(ALERT_JOB_NAMES - jobs_by_name.keys())
    if missing_jobs:
        blockers.append("runtime_monitor_required_jobs_missing")
    delivery_job = jobs_by_name.get("cas-production-runtime-alert-delivery")
    if not isinstance(delivery_job, Mapping) or delivery_job.get("conclusion") != "success":
        blockers.append("runtime_monitor_alert_delivery_job_not_successful")

    labels_value = issue.get("labels")
    labels = labels_value if isinstance(labels_value, list) else []
    label_names = {
        row.get("name")
        for row in labels
        if isinstance(row, Mapping)
    }
    issue_identity_valid = (
        issue.get("number") == issue_number
        and issue.get("title") == ALERT_ISSUE_TITLE
        and ALERT_ISSUE_LABEL in label_names
    )
    if not issue_identity_valid:
        blockers.append("deduplicated_alert_issue_identity_mismatch")

    expected_run_url = f"https://github.com/{REPOSITORY}/actions/runs/{run_id}"
    delivery_times: list[str] = []
    issue_body = issue.get("body")
    if isinstance(issue_body, str) and expected_run_url in issue_body:
        created_at = issue.get("created_at")
        if isinstance(created_at, str):
            delivery_times.append(created_at)
    for row in comments:
        if not isinstance(row, Mapping):
            continue
        body = row.get("body")
        author = row.get("user")
        login = author.get("login") if isinstance(author, Mapping) else None
        if (
            isinstance(body, str)
            and expected_run_url in body
            and login in {"github-actions", "github-actions[bot]"}
            and isinstance(row.get("created_at"), str)
        ):
            delivery_times.append(str(row.get("created_at")))
    incident_channel_verified = (
        issue_identity_valid
        and not missing_jobs
        and isinstance(delivery_job, Mapping)
        and delivery_job.get("conclusion") == "success"
        and bool(delivery_times)
    )
    if not incident_channel_verified:
        blockers.append("incident_channel_delivery_not_verified")

    candidates = _safe_comment_candidates(comments)
    # Text alone cannot establish the actor's assigned incident role, delivery
    # to a distinct primary on-call destination, or provider escalation.
    blockers.extend(
        [
            "primary_on_call_delivery_receipt_missing",
            "incident_commander_acknowledgement_not_verified",
            "secondary_on_call_escalation_receipt_missing",
        ]
    )
    return (
        {
            "selected_run_id": run_id,
            "selected_issue_number": issue_number,
            "github_facts_collected": all(
                value.http_status == 200 and documents[key] is not None
                for key, value in fetched.items()
            ),
            "fetches": [_fetch_summary(fetched[key]) for key in sorted(fetched)],
            "run": {
                "id": run.get("id"),
                "head_sha": run.get("head_sha"),
                "path": run.get("path"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "created_at_utc": run.get("created_at"),
                "updated_at_utc": run.get("updated_at"),
                "repository_id": repository_id,
                "required_job_names": sorted(ALERT_JOB_NAMES),
                "observed_job_conclusions": {
                    name: row.get("conclusion")
                    for name, row in sorted(jobs_by_name.items())
                    if name in ALERT_JOB_NAMES
                },
            },
            "issue": {
                "number": issue.get("number"),
                "state": issue.get("state"),
                "created_at_utc": issue.get("created_at"),
                "updated_at_utc": issue.get("updated_at"),
                "exact_title_and_label": issue_identity_valid,
                "selected_run_delivery_times_utc": sorted(set(delivery_times)),
            },
            "incident_channel_machine_delivery_verified": incident_channel_verified,
            "primary_on_call_delivery_verified": False,
            "comment_candidates": candidates,
            "human_acknowledgement_verified": False,
            "secondary_escalation_verified": False,
        },
        list(dict.fromkeys(blockers)),
    )


def collect_operational_report(
    *,
    target_master_head: str,
    target_deploy_id: str | None,
    run_id: int | None = None,
    issue_number: int | None = None,
    incident_path: Path = DEFAULT_INCIDENT_PATH,
    fetcher: Fetcher | None = None,
    opener: Any | None = None,
    github_token: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    clock: Callable[[], datetime] = _utc_now,
) -> dict[str, Any]:
    if SHA1_RE.fullmatch(target_master_head) is None:
        raise CollectorError("target master head must be a lowercase 40-character SHA")
    if target_deploy_id is not None and DEPLOY_ID_RE.fullmatch(target_deploy_id) is None:
        raise CollectorError("target deploy ID has an invalid shape")
    if (run_id is None) != (issue_number is None):
        raise CollectorError("runtime monitor run and alert issue IDs must be supplied together")
    if run_id is not None and run_id <= 0:
        raise CollectorError("runtime monitor run ID must be positive")
    if issue_number is not None and issue_number <= 0:
        raise CollectorError("alert issue number must be positive")
    if not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise CollectorError("timeout is outside the allowed range")
    if not 0 < max_response_bytes <= MAX_RESPONSE_BYTES:
        raise CollectorError("response byte limit is outside the allowed range")

    if fetcher is None:
        active_opener = opener or urllib.request.build_opener(_NoRedirect)

        def fetcher(name: str, url: str) -> FetchResult:
            return fetch_pinned(
                name,
                url,
                opener=active_opener,
                github_token=github_token,
                timeout_seconds=timeout_seconds,
                max_response_bytes=max_response_bytes,
                clock=clock,
            )

    surfaces = {name: fetcher(name, url) for name, url in PINNED_SURFACES}
    openapi_doc = _json_body(surfaces["api_openapi"])
    openapi = openapi_doc if isinstance(openapi_doc, Mapping) else None

    hosted_ops = _operation_presence(openapi, HOSTED_JOURNEY_OPERATIONS)
    hosted_authority_ops = _operation_presence(
        openapi, (LIVE_AUTHORITY_OPERATIONS["hosted_customer_journey"],)
    )
    hosted_machine_blockers: list[str] = []
    if surfaces["audit_console"].http_status != 200:
        hosted_machine_blockers.append("public_audit_console_not_http_200")
    if surfaces["api_health"].http_status != 200:
        hosted_machine_blockers.append("production_api_health_not_http_200")
    if openapi is None:
        hosted_machine_blockers.append("production_openapi_unavailable_or_invalid")
    if not all(row["found"] for row in hosted_ops):
        hosted_machine_blockers.append("hosted_journey_source_operations_missing")
    if not all(row["found"] for row in hosted_authority_ops):
        hosted_machine_blockers.append(
            "live_authority_endpoint_missing_and_no_signed_receipt_inspected"
        )
    if target_deploy_id is None:
        hosted_machine_blockers.append("exact_public_deploy_id_not_selected")

    hosted_active_blockers = [
        "public_customer_account_and_tenant_session_not_executed",
        "hosted_audit_terminal_verdict_not_observed",
        "packet_download_hash_verification_and_worm_binding_not_observed",
        "read_only_share_create_fetch_revoke_lifecycle_not_observed",
        "cross_tenant_audit_and_packet_404_checks_not_observed",
    ]

    crm_ops = _operation_presence(openapi, CRM_OPERATIONS)
    support_ops = _operation_presence(openapi, SUPPORT_TICKET_OPERATIONS)
    support_authority_ops = _operation_presence(
        openapi, (LIVE_AUTHORITY_OPERATIONS["support_crm"],)
    )
    support_machine_blockers: list[str] = []
    if surfaces["public_support"].http_status != 200:
        support_machine_blockers.append("public_contact_page_not_http_200")
    if openapi is None:
        support_machine_blockers.append("production_openapi_unavailable_or_invalid")
    if not all(row["found"] for row in crm_ops):
        support_machine_blockers.append("crm_source_operations_missing")
    if not all(row["found"] for row in support_ops):
        support_machine_blockers.append("support_ticket_source_operations_missing")
    if not all(row["found"] for row in support_authority_ops):
        support_machine_blockers.append(
            "live_authority_endpoint_missing_and_no_signed_receipt_inspected"
        )
    if target_deploy_id is None:
        support_machine_blockers.append("exact_public_deploy_id_not_selected")
    support_active_blockers = [
        "real_support_ticket_persistence_routing_and_resolution_not_observed",
        "first_response_sla_and_operator_acknowledgement_not_observed",
        "external_crm_readback_deduplication_and_owner_assignment_not_observed",
        "consent_source_attribution_and_privacy_notice_linkage_not_observed",
    ]

    incident, incident_machine_blockers = _incident_summary(incident_path)
    incident_authority_ops = _operation_presence(
        openapi, (LIVE_AUTHORITY_OPERATIONS["incident_tabletop"],)
    )
    if not all(row["found"] for row in incident_authority_ops):
        incident_machine_blockers.append(
            "live_authority_endpoint_missing_and_no_signed_receipt_inspected"
        )
    if target_deploy_id is None:
        incident_machine_blockers.append("exact_public_deploy_id_not_selected")
    incident_active_blockers = [
        "provider_audit_log_review_and_credential_rotation_closure_missing",
        "recovery_and_unique_worm_write_verification_missing",
        "immutable_postmortem_publication_and_hash_missing",
        "cross_functional_tabletop_participant_attestations_missing",
        "tabletop_scenario_results_and_corrective_action_closure_missing",
    ]

    alert, alert_machine_blockers = _alert_summary(
        fetcher=fetcher,
        target_master_head=target_master_head,
        run_id=run_id,
        issue_number=issue_number,
    )
    alert_authority_ops = _operation_presence(
        openapi, (LIVE_AUTHORITY_OPERATIONS["alert_delivery"],)
    )
    if not all(row["found"] for row in alert_authority_ops):
        alert_machine_blockers.append(
            "live_authority_endpoint_missing_and_no_signed_receipt_inspected"
        )
    if target_deploy_id is None:
        alert_machine_blockers.append("exact_public_deploy_id_not_selected")
    alert_active_blockers = [
        "distinct_primary_on_call_delivery_receipt_requires_configured_on_call_provider",
        "incident_commander_acknowledgement_within_600_seconds_requires_assigned_human_role",
        "secondary_on_call_escalation_receipt_requires_configured_escalation_path",
    ]

    def gate(
        machine_facts: Mapping[str, Any],
        machine_blockers: Sequence[str],
        active_blockers: Sequence[str],
    ) -> dict[str, Any]:
        return {
            "status": "OPEN",
            "authoritative": False,
            "machine_prerequisites_passed": not machine_blockers,
            "machine_facts": dict(machine_facts),
            "machine_blockers": list(dict.fromkeys(machine_blockers)),
            "active_or_human_evidence_missing": list(active_blockers),
        }

    gates = {
        "hosted_customer_journey": gate(
            {
                "app_url": f"{PRODUCTION_APP_ORIGIN}/audit-console",
                "api_base_url": PRODUCTION_API_ORIGIN,
                "service_id": PRODUCTION_SERVICE_ID,
                "required_openapi_operations": hosted_ops,
                "live_authority_openapi_operation": hosted_authority_ops[0],
            },
            hosted_machine_blockers,
            hosted_active_blockers,
        ),
        "support_crm": gate(
            {
                "public_support_url": f"{LANDING_ORIGIN}/contact",
                "api_base_url": PRODUCTION_API_ORIGIN,
                "service_id": PRODUCTION_SERVICE_ID,
                "crm_openapi_operations": crm_ops,
                "support_ticket_openapi_operations": support_ops,
                "live_authority_openapi_operation": support_authority_ops[0],
            },
            support_machine_blockers,
            support_active_blockers,
        ),
        "incident_tabletop": gate(
            {
                "api_base_url": PRODUCTION_API_ORIGIN,
                "service_id": PRODUCTION_SERVICE_ID,
                "checked_in_incident_record": incident,
                "live_authority_openapi_operation": incident_authority_ops[0],
                "local_record_is_not_authority": True,
            },
            incident_machine_blockers,
            incident_active_blockers,
        ),
        "alert_delivery": gate(
            {
                "api_base_url": PRODUCTION_API_ORIGIN,
                "service_id": PRODUCTION_SERVICE_ID,
                "github_alert": alert,
                "live_authority_openapi_operation": alert_authority_ops[0],
                "bot_issue_is_not_human_acknowledgement": True,
            },
            alert_machine_blockers,
            alert_active_blockers,
        ),
    }
    machine_passed = all(
        gate_report["machine_prerequisites_passed"] for gate_report in gates.values()
    )
    generated = _format_utc(clock())
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at_utc": generated,
        "collector_sha256": _collector_sha256(),
        "repository": REPOSITORY,
        "source_head_sha": _git_head(),
        "target_master_head_sha": target_master_head,
        "target_deploy_id": target_deploy_id,
        "environment": "public-production",
        "customer_production_status": "OPEN",
        "authoritative": False,
        "signed": False,
        "can_promote_manifest_gate": False,
        "collection_mode": "read_only_no_customer_or_provider_mutations",
        "public_surface_fetches": [
            _fetch_summary(surfaces[name]) for name, _url in PINNED_SURFACES
        ],
        "gates": gates,
        "summary": {
            "gate_count": len(GATES),
            "open_gates": list(GATES),
            "machine_prerequisites_passed": machine_passed,
            "acceptance_evidence_complete": False,
            "human_approvals_recorded": False,
        },
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-master-head",
        help="Exact protected master SHA inspected by the selected runtime-monitor run.",
    )
    parser.add_argument(
        "--target-deploy-id",
        help="Exact public Render deploy ID being assessed.",
    )
    parser.add_argument("--runtime-monitor-run-id", type=int)
    parser.add_argument("--alert-issue-number", type=int)
    parser.add_argument("--incident-path", type=Path, default=DEFAULT_INCIDENT_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--max-response-bytes", type=int, default=DEFAULT_MAX_RESPONSE_BYTES
    )
    parser.add_argument(
        "--github-token-env",
        default="GITHUB_TOKEN",
        help="Environment variable containing a read-only GitHub token; never written to output.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    target_master_head = (args.target_master_head or _git_head()).lower()
    github_token = os.environ.get(args.github_token_env) or (
        os.environ.get("GH_TOKEN") if args.github_token_env == "GITHUB_TOKEN" else None
    )
    try:
        report = collect_operational_report(
            target_master_head=target_master_head,
            target_deploy_id=args.target_deploy_id,
            run_id=args.runtime_monitor_run_id,
            issue_number=args.alert_issue_number,
            incident_path=args.incident_path,
            github_token=github_token,
            timeout_seconds=args.timeout_seconds,
            max_response_bytes=args.max_response_bytes,
        )
    except CollectorError as exc:
        print(f"Operational acceptance collection failed: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(
        report,
        indent=2 if args.pretty else None,
        sort_keys=True,
        separators=None if args.pretty else (",", ":"),
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if report["summary"]["machine_prerequisites_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
