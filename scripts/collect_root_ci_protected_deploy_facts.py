#!/usr/bin/env python3
"""Collect unsigned, fail-closed root-CI/deployment facts.

This collector intentionally emits only a
``cas_harness_customer_production_gate_evidence.v2`` payload.  It does not
create an authoritative receipt, sign bytes, update the production manifest,
or change a gate from ``OPEN`` to ``present``.  Authority remains the separate
responsibility of a pinned issuer and the acceptance verifier.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Mapping, Protocol
import urllib.error
import urllib.request

import verify_customer_production_acceptance as acceptance


REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_RESPONSE_BYTES = 2_000_000
DEFAULT_TIMEOUT_SECONDS = 15.0
DRAFT_NOTICE = (
    "DRAFT_UNSIGNED: collected root_ci_protected_deploy facts only; "
    "this is not a signed receipt and cannot mark the gate present or ACCEPT."
)

GITHUB_API = f"https://api.github.com/repos/{acceptance.REPOSITORY}"
RENDER_SERVICE_URL = (
    f"https://api.render.com/v1/services/{acceptance.PRODUCTION_SERVICE_ID}"
)
PRODUCTION_HEALTH_URL = f"{acceptance.PRODUCTION_API_ORIGIN}/health"

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_DEPLOY_RE = re.compile(r"^dep-[A-Za-z0-9]+$")
_DETAILS_RE = re.compile(
    rf"^{re.escape(acceptance.REPOSITORY_URL)}/actions/runs/([1-9][0-9]*)/job/([1-9][0-9]*)$"
)


class CollectorError(RuntimeError):
    """A source was unavailable, ambiguous, or inconsistent with policy."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


@dataclass(frozen=True)
class HttpDocument:
    url: str
    raw: bytes
    payload: Mapping[str, Any]
    headers: Mapping[str, str]


class JsonTransport(Protocol):
    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        label: str,
    ) -> HttpDocument: ...


def _strict_json(raw: bytes, label: str) -> Mapping[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, child in pairs:
            if key in value:
                raise CollectorError(f"{label} contains a duplicate JSON key")
            value[key] = child
        return value

    try:
        text = raw.decode("utf-8")
        payload = json.loads(text, object_pairs_hook=reject_duplicates)
    except CollectorError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorError(f"{label} did not return valid UTF-8 JSON") from exc
    if not isinstance(payload, Mapping):
        raise CollectorError(f"{label} JSON root must be an object")
    return payload


class HttpJsonClient:
    """Small JSON client with bounded reads, no redirects, and quiet errors."""

    def __init__(
        self,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
        opener: Any | None = None,
    ) -> None:
        if not 1.0 <= timeout_seconds <= 30.0:
            raise CollectorError("HTTP timeout must be between 1 and 30 seconds")
        if not 1 <= max_response_bytes <= MAX_RESPONSE_BYTES:
            raise CollectorError("HTTP response bound is invalid")
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.opener = opener or urllib.request.build_opener(_NoRedirect())

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        label: str,
    ) -> HttpDocument:
        request_headers = {
            "Accept": "application/json",
            "User-Agent": "cas-harness-root-ci-facts/1",
            **headers,
        }
        request = urllib.request.Request(url, headers=request_headers, method="GET")
        try:
            with self.opener.open(request, timeout=self.timeout_seconds) as response:
                response_status = getattr(response, "status", None)
                status = int(
                    response_status
                    if response_status is not None
                    else response.getcode()
                )
                if status != 200:
                    raise CollectorError(
                        f"{label} returned HTTP {status}; response body suppressed"
                    )
                final_url = str(response.geturl())
                if final_url != url:
                    raise CollectorError(f"{label} redirected; redirects are forbidden")
                content_type = str(response.headers.get("Content-Type", ""))
                media_type = content_type.split(";", 1)[0].strip().lower()
                if media_type != "application/json" and not media_type.endswith("+json"):
                    raise CollectorError(f"{label} did not return JSON content")
                raw = response.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise CollectorError(f"{label} exceeded the response size limit")
                response_headers = {
                    str(key).lower(): str(value)
                    for key, value in response.headers.items()
                }
        except CollectorError:
            raise
        except urllib.error.HTTPError as exc:
            raise CollectorError(
                f"{label} returned HTTP {exc.code}; response body suppressed"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise CollectorError(
                f"{label} request failed ({type(exc).__name__}); response body suppressed"
            ) from exc
        return HttpDocument(
            url=url,
            raw=raw,
            payload=_strict_json(raw, label),
            headers=response_headers,
        )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CollectorError(message)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CollectorError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CollectorError(f"{label} must be an array")
    return value


def _positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise CollectorError(f"{label} must be a positive integer")
    return value


def _parse_timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise CollectorError(f"{label} must be a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CollectorError(f"{label} is not a valid timestamp") from exc
    if parsed.tzinfo is None:
        raise CollectorError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _utc_seconds(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _require_single_page(document: HttpDocument, items: list[Any], label: str) -> None:
    link = document.headers.get("link", "")
    _require('rel="next"' not in link, f"{label} pagination is unsupported; refusing partial data")
    total = document.payload.get("total_count")
    if total is not None:
        _require(
            isinstance(total, int) and not isinstance(total, bool),
            f"{label}.total_count must be an integer",
        )
        _require(total == len(items), f"{label} response is incomplete")


def _git_head(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CollectorError("cannot resolve the local repository HEAD") from exc
    value = result.stdout.strip().lower()
    if _SHA1_RE.fullmatch(value) is None:
        raise CollectorError("local repository HEAD is not a full commit SHA")
    return value


def _find_misplaced_workflows(repo_root: Path) -> list[str]:
    ignored = {".git", "node_modules", ".pytest_cache", "__pycache__", ".venv"}
    misplaced: list[str] = []
    for current, directories, files in os.walk(repo_root):
        directories[:] = [name for name in directories if name not in ignored]
        current_path = Path(current)
        if current_path.name != "workflows" or current_path.parent.name != ".github":
            continue
        if current_path.resolve() == (repo_root / ".github" / "workflows").resolve():
            continue
        for name in files:
            if Path(name).suffix.lower() in {".yml", ".yaml"}:
                misplaced.append(str((current_path / name).relative_to(repo_root)))
    return sorted(misplaced)


def _validate_local_workflows(repo_root: Path) -> None:
    misplaced = _find_misplaced_workflows(repo_root)
    _require(
        not misplaced,
        "workflows must exist only below repository-root .github/workflows; "
        f"misplaced: {', '.join(misplaced)}",
    )
    for name, contract in acceptance.WORKFLOW_CONTRACTS.items():
        path = repo_root / contract["workflow_path"]
        _require(path.is_file(), f"required workflow is missing: {contract['workflow_path']}")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CollectorError(
                f"cannot read required workflow: {contract['workflow_path']}"
            ) from exc
        job_pattern = re.compile(rf"(?m)^  {re.escape(contract['job_key'])}:\s*$")
        _require(
            job_pattern.search(text) is not None,
            f"{contract['workflow_path']} is missing job key {contract['job_key']}",
        )
        _require(
            re.search(rf"(?m)^\s{{4}}name:\s*{re.escape(name)}\s*$", text)
            is not None,
            f"{contract['workflow_path']} is missing required check name {name}",
        )


def _github_headers(token: str) -> dict[str, str]:
    _require(bool(token.strip()), "GITHUB_TOKEN or GH_TOKEN is required")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _render_headers(api_key: str) -> dict[str, str]:
    _require(bool(api_key.strip()), "RENDER_API_KEY is required")
    return {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}


def _workflow_index(document: HttpDocument) -> dict[str, Mapping[str, Any]]:
    workflows = _list(document.payload.get("workflows"), "GitHub workflows")
    _require_single_page(document, workflows, "GitHub workflows")
    by_name: dict[str, Mapping[str, Any]] = {}
    for item in workflows:
        workflow = _mapping(item, "GitHub workflow")
        name = workflow.get("name")
        if isinstance(name, str) and name in acceptance.REQUIRED_CHECKS:
            # Aggregate check names are job names, not workflow names.
            raise CollectorError("GitHub workflow identity is ambiguous")
        workflow_name = workflow.get("name")
        if isinstance(workflow_name, str):
            _require(workflow_name not in by_name, "GitHub workflow names are duplicated")
            by_name[workflow_name] = workflow
    return by_name


def _validate_repository(payload: Mapping[str, Any]) -> None:
    expected = {
        "id": acceptance.REPOSITORY_ID,
        "node_id": acceptance.REPOSITORY_NODE_ID,
        "full_name": acceptance.REPOSITORY,
        "html_url": acceptance.REPOSITORY_URL,
        "url": acceptance.REPOSITORY_API_URL,
        "default_branch": "master",
    }
    for field, value in expected.items():
        _require(payload.get(field) == value, f"GitHub repository {field} drifted")


def _validate_protection(payload: Mapping[str, Any]) -> None:
    required = _mapping(payload.get("required_status_checks"), "branch required checks")
    _require(required.get("strict") is True, "protected master is not strict")
    contexts = _list(required.get("contexts"), "branch required check contexts")
    _require(
        len(contexts) == len(set(contexts))
        and set(contexts) == set(acceptance.REQUIRED_CHECKS),
        "protected master required-check contexts drifted",
    )
    checks = _list(required.get("checks"), "branch required check apps")
    actual_checks: set[tuple[Any, Any]] = set()
    for item in checks:
        check = _mapping(item, "branch required check app")
        actual_checks.add((check.get("context"), check.get("app_id")))
    expected_checks = {
        (name, acceptance.GITHUB_ACTIONS_APP["id"])
        for name in acceptance.REQUIRED_CHECKS
    }
    _require(
        len(checks) == len(expected_checks) and actual_checks == expected_checks,
        "protected master required-check apps drifted",
    )
    controls = {
        "enforce_admins": True,
        "required_linear_history": True,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "required_conversation_resolution": True,
    }
    for field, expected in controls.items():
        value = _mapping(payload.get(field), f"branch protection {field}").get("enabled")
        _require(value is expected, f"branch protection {field} drifted")


def collect_root_ci_protected_deploy_facts(
    *,
    expected_master_head: str,
    expected_deploy_id: str,
    repo_root: Path,
    transport: JsonTransport,
    github_token: str,
    render_api_key: str,
    now: datetime | None = None,
    repository_head: str | None = None,
    deploy_wait_seconds: int = 0,
    deploy_poll_seconds: int = 10,
    sleeper: Any = time.sleep,
) -> dict[str, Any]:
    """Collect one verifier-compatible unsigned gate payload."""

    _require(
        _SHA1_RE.fullmatch(expected_master_head) is not None,
        "expected master HEAD must be a lowercase 40-character SHA",
    )
    _require(
        _DEPLOY_RE.fullmatch(expected_deploy_id) is not None,
        "expected deploy ID must use the dep- identifier form",
    )
    _require(
        isinstance(deploy_wait_seconds, int)
        and not isinstance(deploy_wait_seconds, bool)
        and 0 <= deploy_wait_seconds <= 900,
        "deploy wait must be an integer between 0 and 900 seconds",
    )
    _require(
        isinstance(deploy_poll_seconds, int)
        and not isinstance(deploy_poll_seconds, bool)
        and 1 <= deploy_poll_seconds <= 60,
        "deploy poll interval must be an integer between 1 and 60 seconds",
    )
    repo_root = repo_root.resolve()
    _require(repo_root.is_dir(), "repository root is unavailable")
    actual_head = repository_head or _git_head(repo_root)
    _require(actual_head == expected_master_head, "local HEAD does not match expected master HEAD")
    _validate_local_workflows(repo_root)

    github_headers = _github_headers(github_token)
    render_headers = _render_headers(render_api_key)

    repository_document = transport.get_json(
        GITHUB_API, headers=github_headers, label="GitHub repository"
    )
    _validate_repository(repository_document.payload)

    protection_document = transport.get_json(
        f"{GITHUB_API}/branches/master/protection",
        headers=github_headers,
        label="GitHub branch protection",
    )
    _validate_protection(protection_document.payload)

    workflows_document = transport.get_json(
        f"{GITHUB_API}/actions/workflows?per_page=100",
        headers=github_headers,
        label="GitHub workflows",
    )
    workflow_by_name = _workflow_index(workflows_document)
    for contract in acceptance.WORKFLOW_CONTRACTS.values():
        workflow = workflow_by_name.get(contract["workflow_name"])
        _require(workflow is not None, f"workflow {contract['workflow_name']} is unavailable")
        assert workflow is not None
        _require(workflow.get("id") == contract["workflow_id"], "workflow ID drifted")
        _require(workflow.get("path") == contract["workflow_path"], "workflow path drifted")
        _require(workflow.get("state") == "active", "required workflow is not active")

    check_runs_url = f"{GITHUB_API}/commits/{expected_master_head}/check-runs?per_page=100"
    check_runs_document = transport.get_json(
        check_runs_url,
        headers=github_headers,
        label="GitHub check runs",
    )
    check_runs = _list(check_runs_document.payload.get("check_runs"), "GitHub check runs")
    _require_single_page(check_runs_document, check_runs, "GitHub check runs")
    by_name: dict[str, list[Mapping[str, Any]]] = {
        name: [] for name in acceptance.REQUIRED_CHECKS
    }
    for item in check_runs:
        check = _mapping(item, "GitHub check run")
        name = check.get("name")
        if isinstance(name, str) and name in by_name:
            by_name[name].append(check)

    evidence_checks: list[dict[str, Any]] = []
    run_event_times: list[datetime] = []
    completed_times: list[datetime] = []
    seen_run_ids: set[int] = set()
    for name in acceptance.REQUIRED_CHECKS:
        matches = by_name[name]
        _require(len(matches) == 1, f"required check {name} is missing or ambiguous")
        check = matches[0]
        check_run_id = _positive_int(check.get("id"), f"{name} check-run ID")
        _require(check.get("status") == "completed", f"required check {name} is incomplete")
        _require(check.get("conclusion") == "success", f"required check {name} did not pass")
        app = _mapping(check.get("app"), f"{name} GitHub App")
        for field, value in acceptance.GITHUB_ACTIONS_APP.items():
            _require(app.get(field) == value, f"required check {name} app identity drifted")
        suite = _mapping(check.get("check_suite"), f"{name} check suite")
        check_suite_id = _positive_int(suite.get("id"), f"{name} check-suite ID")
        details_url = check.get("details_url")
        match = _DETAILS_RE.fullmatch(str(details_url))
        _require(match is not None, f"required check {name} details URL is invalid")
        assert match is not None
        run_id = int(match.group(1))
        _require(int(match.group(2)) == check_run_id, f"required check {name} job URL is mismatched")
        _require(run_id not in seen_run_ids, "required workflow run IDs must be unique")
        seen_run_ids.add(run_id)

        run_url = f"{GITHUB_API}/actions/runs/{run_id}"
        run_document = transport.get_json(
            run_url,
            headers=github_headers,
            label=f"GitHub workflow run {name}",
        )
        run = run_document.payload
        contract = acceptance.WORKFLOW_CONTRACTS[name]
        expected_run = {
            "id": run_id,
            "workflow_id": contract["workflow_id"],
            "name": contract["workflow_name"],
            "path": contract["workflow_path"],
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "master",
            "head_sha": expected_master_head,
            "check_suite_id": check_suite_id,
            "html_url": f"{acceptance.REPOSITORY_URL}/actions/runs/{run_id}",
        }
        for field, value in expected_run.items():
            _require(run.get(field) == value, f"{name} workflow run {field} drifted")
        run_attempt = _positive_int(run.get("run_attempt"), f"{name} run attempt")
        run_event_times.append(_parse_timestamp(run.get("created_at"), f"{name} created_at"))

        jobs_document = transport.get_json(
            f"{run_url}/jobs?per_page=100",
            headers=github_headers,
            label=f"GitHub workflow jobs {name}",
        )
        jobs = _list(jobs_document.payload.get("jobs"), f"{name} workflow jobs")
        _require_single_page(jobs_document, jobs, f"{name} workflow jobs")
        matching_jobs = [
            _mapping(job, f"{name} workflow job")
            for job in jobs
            if isinstance(job, Mapping) and job.get("id") == check_run_id
        ]
        _require(len(matching_jobs) == 1, f"{name} exact workflow job is missing or ambiguous")
        job = matching_jobs[0]
        _require(job.get("name") == name, f"{name} workflow job name drifted")
        _require(job.get("status") == "completed", f"{name} workflow job is incomplete")
        _require(job.get("conclusion") == "success", f"{name} workflow job did not pass")
        _require(job.get("html_url") == details_url, f"{name} workflow job URL drifted")
        completed = _parse_timestamp(check.get("completed_at"), f"{name} completed_at")
        job_completed = _parse_timestamp(job.get("completed_at"), f"{name} job completed_at")
        _require(job_completed == completed, f"{name} job and check completion times disagree")
        completed_times.append(completed)

        evidence_checks.append(
            {
                "name": name,
                **contract,
                "run_id": run_id,
                "run_attempt": run_attempt,
                "event": "push",
                "status": "completed",
                "conclusion": "success",
                "head_branch": "master",
                "head_sha": expected_master_head,
                "check_run_id": check_run_id,
                "check_suite_id": check_suite_id,
                "app_id": app["id"],
                "app_node_id": app["node_id"],
                "app_slug": app["slug"],
                "details_url": details_url,
                "completed_at_utc": _utc_seconds(completed),
            }
        )

    service_document = transport.get_json(
        RENDER_SERVICE_URL,
        headers=render_headers,
        label="Render production service",
    )
    service = service_document.payload
    expected_service = {
        "id": acceptance.PRODUCTION_SERVICE_ID,
        "name": acceptance.PRODUCTION_SERVICE_NAME,
        "type": "web_service",
        "repo": acceptance.REPOSITORY_URL,
        "branch": "master",
        "autoDeployTrigger": "checksPass",
    }
    for field, value in expected_service.items():
        _require(service.get(field) == value, f"Render service {field} drifted")
    service_details = _mapping(service.get("serviceDetails"), "Render serviceDetails")
    _require(
        service_details.get("healthCheckPath") == "/health",
        "Render production healthCheckPath drifted",
    )

    deploy_url = f"{RENDER_SERVICE_URL}/deploys/{expected_deploy_id}"
    pending_statuses = {
        "created",
        "build_in_progress",
        "update_in_progress",
        "pre_deploy_in_progress",
    }
    remaining_wait = deploy_wait_seconds
    deploy_document: HttpDocument | None = None
    deploy: Mapping[str, Any] | None = None
    while True:
        candidate_document = transport.get_json(
            deploy_url,
            headers=render_headers,
            label="Render production deployment",
        )
        candidate = candidate_document.payload
        _require(candidate.get("id") == expected_deploy_id, "Render deployment ID drifted")
        _require(
            candidate.get("trigger") == "new_commit",
            "Render deployment was not triggered by a new commit",
        )
        commit = _mapping(candidate.get("commit"), "Render deployment commit")
        _require(commit.get("id") == expected_master_head, "Render deployment commit drifted")
        status = candidate.get("status")
        if status == "live":
            deploy_document = candidate_document
            deploy = candidate
            break
        _require(status in pending_statuses, "Render deployment entered a non-live terminal or unknown status")
        if remaining_wait <= 0:
            raise CollectorError("exact Render deployment did not become live before the wait expired")
        sleep_seconds = min(deploy_poll_seconds, remaining_wait)
        sleeper(sleep_seconds)
        remaining_wait -= sleep_seconds
    assert deploy_document is not None and deploy is not None
    deploy_created = _parse_timestamp(deploy.get("createdAt"), "Render deploy createdAt")
    deploy_finished = _parse_timestamp(deploy.get("finishedAt"), "Render deploy finishedAt")
    _require(deploy_finished >= deploy_created, "Render deployment finished before it started")
    _require(
        deploy_created >= max(completed_times),
        "Render deployment started before all required checks completed",
    )

    health_document = transport.get_json(
        PRODUCTION_HEALTH_URL,
        headers={},
        label="production /health",
    )
    health = health_document.payload
    _require(health.get("status") == "ok", "production /health is not ok")
    _require(health.get("engine") == "cas-engine", "production /health engine drifted")

    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    event = min(run_event_times)
    _require(event <= min(completed_times), "workflow completion precedes the push event")
    _require(deploy_finished <= observed, "deployment completion is in the future")
    _require(
        observed - event
        <= timedelta(
            minutes=acceptance.FRESHNESS_POLICY[
                "root_ci_protected_deploy_max_age_minutes"
            ]
        ),
        "root-CI/deployment facts are stale",
    )

    payload: dict[str, Any] = {
        "schema_version": acceptance.EVIDENCE_SCHEMA_VERSION,
        "gate": "root_ci_protected_deploy",
        "environment": "public-production",
        "repository": acceptance.REPOSITORY,
        "master_head_sha": expected_master_head,
        "deploy_id": expected_deploy_id,
        "event_at_utc": _utc_seconds(event),
        "observed_at_utc": _utc_seconds(observed),
        "artifact_uri": deploy_url,
        "artifact_sha256": hashlib.sha256(deploy_document.raw).hexdigest(),
        "github_repository": {
            "id": acceptance.REPOSITORY_ID,
            "node_id": acceptance.REPOSITORY_NODE_ID,
            "full_name": acceptance.REPOSITORY,
            "html_url": acceptance.REPOSITORY_URL,
            "api_url": acceptance.REPOSITORY_API_URL,
        },
        "branch": "master",
        "workflow_directory": ".github/workflows",
        "misplaced_workflow_count": 0,
        "github_app": dict(acceptance.GITHUB_ACTIONS_APP),
        "branch_protection": {
            "strict": True,
            "required_checks": list(acceptance.REQUIRED_CHECKS),
            "source": "github-api",
            "observed_at_utc": _utc_seconds(observed),
        },
        "checks": evidence_checks,
        "deployment": {
            "provider": "Render",
            "service_id": acceptance.PRODUCTION_SERVICE_ID,
            "service_name": acceptance.PRODUCTION_SERVICE_NAME,
            "service_type": "web_service",
            "repository": acceptance.REPOSITORY_URL,
            "branch": "master",
            "deploy_id": expected_deploy_id,
            "status": "live",
            "commit_sha": expected_master_head,
            "auto_deploy_trigger": "checksPass",
            "health_check_path": "/health",
            "deployed_at_utc": _utc_seconds(deploy_finished),
        },
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    for forbidden in ("signature_base64url", '"authority"', '"issuer"', '"key_id"'):
        _require(forbidden not in serialized, "collector attempted to emit authority fields")
    _require('"ACCEPT"' not in serialized and '"present"' not in serialized, "collector attempted to emit a gate decision")
    for secret in (github_token, render_api_key):
        if len(secret) >= 8:
            _require(secret not in serialized, "collector attempted to emit a credential")
    return payload


def _write_payload(payload: Mapping[str, Any], output: Path | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output is None:
        sys.stdout.write(rendered)
        return
    output = output.resolve()
    _require(output.parent.is_dir(), "output parent directory does not exist")
    try:
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
    except FileExistsError as exc:
        raise CollectorError("refusing to overwrite an existing draft payload") from exc
    except OSError as exc:
        raise CollectorError("cannot write the draft payload") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-master-head", required=True)
    parser.add_argument("--expected-deploy-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="per-request timeout, constrained to 1..30 seconds",
    )
    parser.add_argument(
        "--deploy-wait-seconds",
        type=int,
        default=0,
        help="wait up to 900 seconds for the exact deploy ID to become live",
    )
    parser.add_argument(
        "--deploy-poll-seconds",
        type=int,
        default=10,
        help="poll interval for the exact deploy ID, constrained to 1..60 seconds",
    )
    args = parser.parse_args(argv)
    try:
        client = HttpJsonClient(timeout_seconds=args.timeout_seconds)
        payload = collect_root_ci_protected_deploy_facts(
            expected_master_head=args.expected_master_head,
            expected_deploy_id=args.expected_deploy_id,
            repo_root=args.repo_root,
            transport=client,
            github_token=os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GH_TOKEN", ""),
            render_api_key=os.environ.get("RENDER_API_KEY", ""),
            deploy_wait_seconds=args.deploy_wait_seconds,
            deploy_poll_seconds=args.deploy_poll_seconds,
        )
        _write_payload(payload, args.output)
    except CollectorError as exc:
        print(f"root-CI fact collection failed: {exc}", file=sys.stderr)
        return 1
    print(DRAFT_NOTICE, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
