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
from typing import Any, Callable, Mapping, Protocol
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
RENDER_ACTIVE_DEPLOYS_URL = f"{RENDER_SERVICE_URL}/deploys?status=live&limit=2"
RENDER_LATEST_DEPLOY_URL = f"{RENDER_SERVICE_URL}/deploys?limit=1"
ROOT_CI_SCHEMA_VERSION = acceptance.ROOT_CI_SCHEMA_VERSION
ROOT_CI_OBSERVATION_SEMANTICS = acceptance.ROOT_CI_OBSERVATION_SEMANTICS

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
    payload: Any
    headers: Mapping[str, str]


class JsonTransport(Protocol):
    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        label: str,
    ) -> HttpDocument: ...

    def get_json_array(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        label: str,
    ) -> HttpDocument: ...


def _strict_json_value(raw: bytes, label: str) -> Any:
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
    return payload


def _strict_json(raw: bytes, label: str) -> Mapping[str, Any]:
    payload = _strict_json_value(raw, label)
    if not isinstance(payload, Mapping):
        raise CollectorError(f"{label} JSON root must be an object")
    return payload


def _strict_json_array(raw: bytes, label: str) -> list[Any]:
    payload = _strict_json_value(raw, label)
    if not isinstance(payload, list):
        raise CollectorError(f"{label} JSON root must be an array")
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
        return self._get_json(
            url,
            headers=headers,
            label=label,
            parser=_strict_json,
        )

    def get_json_array(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        label: str,
    ) -> HttpDocument:
        return self._get_json(
            url,
            headers=headers,
            label=label,
            parser=_strict_json_array,
        )

    def _get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        label: str,
        parser: Callable[[bytes, str], Any],
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
            payload=parser(raw, label),
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


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _read_clock(clock: Callable[[], datetime], label: str) -> datetime:
    value = clock()
    _require(isinstance(value, datetime), f"{label} clock did not return a datetime")
    _require(value.tzinfo is not None, f"{label} clock must include a timezone")
    return value.astimezone(timezone.utc)


def _require_single_page(document: HttpDocument, items: list[Any], label: str) -> None:
    link = document.headers.get("link", "")
    _require('rel="next"' not in link, f"{label} pagination is unsupported; refusing partial data")
    payload = _mapping(document.payload, label)
    total = payload.get("total_count")
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
    payload = _mapping(document.payload, "GitHub workflows response")
    workflows = _list(payload.get("workflows"), "GitHub workflows")
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


def _validate_workflow_registry(document: HttpDocument) -> None:
    workflow_by_name = _workflow_index(document)
    for contract in acceptance.WORKFLOW_CONTRACTS.values():
        workflow = workflow_by_name.get(contract["workflow_name"])
        _require(
            workflow is not None,
            f"workflow {contract['workflow_name']} is unavailable",
        )
        assert workflow is not None
        _require(workflow.get("id") == contract["workflow_id"], "workflow ID drifted")
        _require(workflow.get("path") == contract["workflow_path"], "workflow path drifted")
        _require(workflow.get("state") == "active", "required workflow is not active")


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


def _validate_master_branch(
    payload: Mapping[str, Any], expected_master_head: str
) -> None:
    _require(payload.get("name") == "master", "GitHub master branch name drifted")
    _require(payload.get("protected") is True, "GitHub master is not protected")
    _require(
        payload.get("protection_url")
        == f"{GITHUB_API}/branches/master/protection",
        "GitHub master protection URL drifted",
    )
    commit = _mapping(payload.get("commit"), "GitHub master commit")
    _require(
        commit.get("sha") == expected_master_head,
        "GitHub current master HEAD does not match expected master HEAD",
    )


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


def _validate_render_service(payload: Mapping[str, Any]) -> None:
    expected_service = {
        "id": acceptance.PRODUCTION_SERVICE_ID,
        "name": acceptance.PRODUCTION_SERVICE_NAME,
        "type": "web_service",
        "repo": acceptance.REPOSITORY_URL,
        "branch": "master",
        "autoDeployTrigger": "checksPass",
    }
    for field, value in expected_service.items():
        _require(payload.get(field) == value, f"Render service {field} drifted")
    service_details = _mapping(payload.get("serviceDetails"), "Render serviceDetails")
    _require(
        service_details.get("healthCheckPath") == "/health",
        "Render production healthCheckPath drifted",
    )


def _validate_render_deploy_identity(
    payload: Mapping[str, Any],
    *,
    expected_master_head: str,
    expected_deploy_id: str,
    require_live: bool,
) -> None:
    _require(payload.get("id") == expected_deploy_id, "Render deployment ID drifted")
    _require(
        payload.get("trigger") == "new_commit",
        "Render deployment was not triggered by a new commit",
    )
    commit = _mapping(payload.get("commit"), "Render deployment commit")
    _require(commit.get("id") == expected_master_head, "Render deployment commit drifted")
    if require_live:
        _require(payload.get("status") == "live", "exact Render deployment is not live")


def _validate_current_active_deploy(
    document: HttpDocument,
    *,
    expected_master_head: str,
    expected_deploy_id: str,
) -> Mapping[str, Any]:
    items = _list(document.payload, "Render active deployments")
    _require(
        len(items) == 1,
        "Render current live deployment is missing or ambiguous",
    )
    wrapper = _mapping(items[0], "Render active deployment wrapper")
    _require(
        set(wrapper) == {"deploy", "cursor"},
        "Render active deployment wrapper schema drifted",
    )
    _require(
        isinstance(wrapper.get("cursor"), str) and bool(wrapper.get("cursor")),
        "Render active deployment cursor is invalid",
    )
    deploy = _mapping(wrapper.get("deploy"), "Render current live deployment")
    _validate_render_deploy_identity(
        deploy,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
        require_live=True,
    )
    return deploy


def collect_root_ci_protected_deploy_facts(
    *,
    expected_master_head: str,
    expected_deploy_id: str,
    repo_root: Path,
    transport: JsonTransport,
    github_token: str,
    render_api_key: str,
    now: datetime | None = None,
    clock: Callable[[], datetime] | None = None,
    repository_head: str | None = None,
    deploy_wait_seconds: int = 0,
    deploy_poll_seconds: int = 10,
    sleeper: Any = time.sleep,
) -> dict[str, Any]:
    """Collect one verifier-compatible unsigned gate payload.

    The protected checks and ``new_commit`` deployment are immutable release
    provenance.  Freshness comes from a new final observation cycle that starts
    only after that exact deploy is live, then proves the expected SHA is still
    current on GitHub and the exact deploy is still Render's sole active live
    deploy.  Full provider records are compared before and after the health
    read so a stable release can be observed again without no-op redeploy churn.
    """

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
    _require(
        not (now is not None and clock is not None),
        "supply either now or clock, not both",
    )
    if clock is None:
        if now is None:
            evidence_clock = lambda: datetime.now(timezone.utc)
        else:
            evidence_clock = lambda: now
    else:
        evidence_clock = clock
    repo_root = repo_root.resolve()
    _require(repo_root.is_dir(), "repository root is unavailable")
    actual_head = repository_head or _git_head(repo_root)
    _require(actual_head == expected_master_head, "local HEAD does not match expected master HEAD")

    github_headers = _github_headers(github_token)
    render_headers = _render_headers(render_api_key)

    deploy_url = f"{RENDER_SERVICE_URL}/deploys/{expected_deploy_id}"
    pending_statuses = {
        "created",
        "queued",
        "build_in_progress",
        "update_in_progress",
        "pre_deploy_in_progress",
    }
    remaining_wait = deploy_wait_seconds
    deploy: Mapping[str, Any] | None = None
    deploy_initial_document: HttpDocument | None = None
    while True:
        candidate_document = transport.get_json(
            deploy_url,
            headers=render_headers,
            label="Render production deployment",
        )
        candidate = _mapping(candidate_document.payload, "Render production deployment")
        _validate_render_deploy_identity(
            candidate,
            expected_master_head=expected_master_head,
            expected_deploy_id=expected_deploy_id,
            require_live=False,
        )
        status = candidate.get("status")
        if status == "live":
            deploy = candidate
            deploy_initial_document = candidate_document
            break
        _require(status in pending_statuses, "Render deployment entered a non-live terminal or unknown status")
        if remaining_wait <= 0:
            raise CollectorError("exact Render deployment did not become live before the wait expired")
        sleep_seconds = min(deploy_poll_seconds, remaining_wait)
        sleeper(sleep_seconds)
        remaining_wait -= sleep_seconds
    assert deploy is not None
    assert deploy_initial_document is not None
    deploy_created = _parse_timestamp(deploy.get("createdAt"), "Render deploy createdAt")
    deploy_finished = _parse_timestamp(deploy.get("finishedAt"), "Render deploy finishedAt")
    _require(deploy_finished >= deploy_created, "Render deployment finished before it started")

    # The fresh cycle begins only after a deployment that finished during an
    # optional wait has become immutable historical provenance.
    event = _read_clock(evidence_clock, "observation start")
    _require(
        deploy_finished <= event,
        "Render deployment completion is after the fresh observation start",
    )
    _validate_local_workflows(repo_root)

    service_preflight_document = transport.get_json(
        RENDER_SERVICE_URL,
        headers=render_headers,
        label="Render production service preflight",
    )
    service_preflight = _mapping(
        service_preflight_document.payload, "Render production service preflight"
    )
    _validate_render_service(service_preflight)
    deploy_preflight_document = transport.get_json(
        deploy_url,
        headers=render_headers,
        label="Render production deployment preflight",
    )
    deploy_preflight = _mapping(
        deploy_preflight_document.payload, "Render production deployment preflight"
    )
    _validate_render_deploy_identity(
        deploy_preflight,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
        require_live=True,
    )
    active_preflight_document = transport.get_json_array(
        RENDER_ACTIVE_DEPLOYS_URL,
        headers=render_headers,
        label="Render current live deployment preflight",
    )
    _validate_current_active_deploy(
        active_preflight_document,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
    )
    latest_preflight_document = transport.get_json_array(
        RENDER_LATEST_DEPLOY_URL,
        headers=render_headers,
        label="Render latest deployment preflight",
    )
    _validate_current_active_deploy(
        latest_preflight_document,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
    )
    render_preflight_verified = _read_clock(
        evidence_clock, "Render preflight observation"
    )

    repository_preflight_document = transport.get_json(
        GITHUB_API, headers=github_headers, label="GitHub repository preflight"
    )
    repository_preflight = _mapping(
        repository_preflight_document.payload, "GitHub repository preflight"
    )
    _validate_repository(repository_preflight)

    master_url = f"{GITHUB_API}/branches/master"
    master_preflight_document = transport.get_json(
        master_url,
        headers=github_headers,
        label="GitHub current master preflight",
    )
    master_preflight = _mapping(
        master_preflight_document.payload, "GitHub current master preflight"
    )
    _validate_master_branch(master_preflight, expected_master_head)

    protection_preflight_document = transport.get_json(
        f"{GITHUB_API}/branches/master/protection",
        headers=github_headers,
        label="GitHub branch protection preflight",
    )
    protection_preflight = _mapping(
        protection_preflight_document.payload, "GitHub branch protection preflight"
    )
    _validate_protection(protection_preflight)

    workflows_preflight_document = transport.get_json(
        f"{GITHUB_API}/actions/workflows?per_page=100",
        headers=github_headers,
        label="GitHub workflows preflight",
    )
    _validate_workflow_registry(workflows_preflight_document)

    check_runs_url = f"{GITHUB_API}/commits/{expected_master_head}/check-runs?per_page=100"
    check_runs_document = transport.get_json(
        check_runs_url,
        headers=github_headers,
        label="GitHub check runs",
    )
    check_runs_payload = _mapping(
        check_runs_document.payload, "GitHub check runs response"
    )
    check_runs = _list(check_runs_payload.get("check_runs"), "GitHub check runs")
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
        run = _mapping(run_document.payload, f"GitHub workflow run {name}")
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
        run_created = _parse_timestamp(run.get("created_at"), f"{name} created_at")

        jobs_document = transport.get_json(
            f"{run_url}/jobs?per_page=100",
            headers=github_headers,
            label=f"GitHub workflow jobs {name}",
        )
        jobs_payload = _mapping(
            jobs_document.payload, f"{name} workflow jobs response"
        )
        jobs = _list(jobs_payload.get("jobs"), f"{name} workflow jobs")
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
        _require(run_created <= completed, f"{name} completed before its workflow run was created")
        _require(completed <= event, f"{name} completed after the fresh observation started")
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
                "run_created_at_utc": _utc_seconds(run_created),
                "completed_at_utc": _utc_seconds(completed),
            }
        )

    _require(
        deploy_created >= max(completed_times),
        "Render deployment started before all required checks completed",
    )
    github_controls_verified = _read_clock(
        evidence_clock, "GitHub controls observation"
    )

    health_document = transport.get_json(
        PRODUCTION_HEALTH_URL,
        headers={},
        label="production /health",
    )
    health = _mapping(health_document.payload, "production /health")
    _require(health.get("status") == "ok", "production /health is not ok")
    _require(health.get("engine") == "cas-engine", "production /health engine drifted")
    health_verified = _read_clock(evidence_clock, "production health observation")

    master_final_document = transport.get_json(
        master_url,
        headers=github_headers,
        label="GitHub current master final",
    )
    master_final = _mapping(
        master_final_document.payload, "GitHub current master final"
    )
    _validate_master_branch(master_final, expected_master_head)
    github_master_verified = _read_clock(
        evidence_clock, "GitHub final master observation"
    )

    repository_final_document = transport.get_json(
        GITHUB_API, headers=github_headers, label="GitHub repository final"
    )
    repository_final = _mapping(
        repository_final_document.payload, "GitHub repository final"
    )
    _validate_repository(repository_final)
    protection_final_document = transport.get_json(
        f"{GITHUB_API}/branches/master/protection",
        headers=github_headers,
        label="GitHub branch protection final",
    )
    protection_final = _mapping(
        protection_final_document.payload, "GitHub branch protection final"
    )
    _validate_protection(protection_final)
    workflows_final_document = transport.get_json(
        f"{GITHUB_API}/actions/workflows?per_page=100",
        headers=github_headers,
        label="GitHub workflows final",
    )
    _validate_workflow_registry(workflows_final_document)
    github_controls_final_verified = _read_clock(
        evidence_clock, "GitHub final controls observation"
    )

    service_final_document = transport.get_json(
        RENDER_SERVICE_URL,
        headers=render_headers,
        label="Render production service final",
    )
    service_final = _mapping(
        service_final_document.payload, "Render production service final"
    )
    _validate_render_service(service_final)
    deploy_final_document = transport.get_json(
        deploy_url,
        headers=render_headers,
        label="Render production deployment final",
    )
    deploy_final = _mapping(
        deploy_final_document.payload, "Render production deployment final"
    )
    _validate_render_deploy_identity(
        deploy_final,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
        require_live=True,
    )
    active_final_document = transport.get_json_array(
        RENDER_ACTIVE_DEPLOYS_URL,
        headers=render_headers,
        label="Render current live deployment final",
    )
    _validate_current_active_deploy(
        active_final_document,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
    )
    latest_final_document = transport.get_json_array(
        RENDER_LATEST_DEPLOY_URL,
        headers=render_headers,
        label="Render latest deployment final",
    )
    _validate_current_active_deploy(
        latest_final_document,
        expected_master_head=expected_master_head,
        expected_deploy_id=expected_deploy_id,
    )
    render_final_verified = _read_clock(
        evidence_clock, "Render final observation"
    )
    observed = _read_clock(evidence_clock, "observation completion")

    observation_times = (
        event,
        render_preflight_verified,
        github_controls_verified,
        health_verified,
        github_master_verified,
        github_controls_final_verified,
        render_final_verified,
        observed,
    )
    _require(
        all(left <= right for left, right in zip(observation_times, observation_times[1:])),
        "fresh observation clock moved backwards",
    )
    _require(
        observed - event
        <= timedelta(
            minutes=acceptance.FRESHNESS_POLICY[
                "root_ci_protected_deploy_max_age_minutes"
            ]
        ),
        "root-CI observation cycle is stale",
    )
    _require(
        _canonical_bytes(master_preflight) == _canonical_bytes(master_final),
        "GitHub current master record changed during collection",
    )
    _require(
        _canonical_bytes(repository_preflight)
        == _canonical_bytes(repository_final),
        "GitHub repository record changed during collection",
    )
    _require(
        _canonical_bytes(protection_preflight)
        == _canonical_bytes(protection_final),
        "GitHub branch protection record changed during collection",
    )
    _require(
        _canonical_bytes(workflows_preflight_document.payload)
        == _canonical_bytes(workflows_final_document.payload),
        "GitHub workflow registry changed during collection",
    )
    _require(
        _canonical_bytes(service_preflight) == _canonical_bytes(service_final),
        "Render service record changed during collection",
    )
    _require(
        _canonical_bytes(deploy) == _canonical_bytes(deploy_preflight),
        "Render deployment record changed between initial and preflight collection",
    )
    _require(
        _canonical_bytes(deploy_preflight) == _canonical_bytes(deploy_final),
        "Render deployment record changed during collection",
    )
    _require(
        _canonical_bytes(active_preflight_document.payload)
        == _canonical_bytes(active_final_document.payload),
        "Render current live deployment changed during collection",
    )
    _require(
        _canonical_bytes(latest_preflight_document.payload)
        == _canonical_bytes(latest_final_document.payload),
        "Render latest deployment changed during collection",
    )

    payload: dict[str, Any] = {
        "schema_version": acceptance.EVIDENCE_SCHEMA_VERSION,
        "root_ci_schema_version": ROOT_CI_SCHEMA_VERSION,
        "gate": "root_ci_protected_deploy",
        "environment": "public-production",
        "repository": acceptance.REPOSITORY,
        "master_head_sha": expected_master_head,
        "deploy_id": expected_deploy_id,
        "event_at_utc": _utc_seconds(event),
        "observed_at_utc": _utc_seconds(observed),
        "artifact_uri": deploy_url,
        "artifact_sha256": hashlib.sha256(deploy_final_document.raw).hexdigest(),
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
            "observed_at_utc": _utc_seconds(github_controls_final_verified),
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
            "created_at_utc": _utc_seconds(deploy_created),
            "deployed_at_utc": _utc_seconds(deploy_finished),
        },
        "observation": {
            "semantics": ROOT_CI_OBSERVATION_SEMANTICS,
            "started_at_utc": _utc_seconds(event),
            "render_preflight_verified_at_utc": _utc_seconds(
                render_preflight_verified
            ),
            "github_controls_verified_at_utc": _utc_seconds(
                github_controls_verified
            ),
            "health_verified_at_utc": _utc_seconds(health_verified),
            "github_master_verified_at_utc": _utc_seconds(
                github_master_verified
            ),
            "github_controls_final_verified_at_utc": _utc_seconds(
                github_controls_final_verified
            ),
            "render_final_verified_at_utc": _utc_seconds(render_final_verified),
            "completed_at_utc": _utc_seconds(observed),
            "github_master_preflight_sha256": _sha256(master_preflight),
            "github_master_final_sha256": _sha256(master_final),
            "github_repository_preflight_sha256": _sha256(
                repository_preflight
            ),
            "github_repository_final_sha256": _sha256(repository_final),
            "github_protection_preflight_sha256": _sha256(
                protection_preflight
            ),
            "github_protection_final_sha256": _sha256(protection_final),
            "github_workflows_preflight_sha256": _sha256(
                workflows_preflight_document.payload
            ),
            "github_workflows_final_sha256": _sha256(
                workflows_final_document.payload
            ),
            "render_service_preflight_sha256": _sha256(service_preflight),
            "render_service_final_sha256": _sha256(service_final),
            "render_deploy_initial_sha256": _sha256(deploy),
            "render_deploy_preflight_sha256": _sha256(deploy_preflight),
            "render_deploy_final_sha256": _sha256(deploy_final),
            "render_active_preflight_sha256": _sha256(
                active_preflight_document.payload
            ),
            "render_active_final_sha256": _sha256(
                active_final_document.payload
            ),
            "render_latest_preflight_sha256": _sha256(
                latest_preflight_document.payload
            ),
            "render_latest_final_sha256": _sha256(
                latest_final_document.payload
            ),
            "current_master_head_sha": expected_master_head,
            "current_active_deploy_id": expected_deploy_id,
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
