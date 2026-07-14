#!/usr/bin/env python3
"""Fail-closed checks for the repository's Render Blueprint deployment control.

The offline policy check intentionally uses only Python's standard library. It
does not try to replace Render's full Blueprint schema validator; it validates
the small set of deployment fields that prevent a Blueprint sync or service
deploy from bypassing the repository's aggregate CI gates.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Mapping


REPOSITORY = "LittleHenderson/noetic-compass"
REPOSITORY_URL = f"https://github.com/{REPOSITORY}"
MANIFEST_PATH = Path(".render/blueprint-control.json")
REQUIRED_AGGREGATE_CHECKS = ["cas-ci-gate", "cas-postgres-live-gate"]
ATTESTATION_FIELDS = ["blueprint_source_sha", "service_source_sha"]
SHA_FORMAT = r"^[0-9a-f]{40}$"
EXPECTED_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "environment": "production",
        "id": "exs-d82lpanaqgkc7399m1g0",
        "path": "render.yaml",
        "sourceBranch": "master",
        "autoSyncRequired": False,
        "services": [
            {
                "id": "srv-d82ph683kofs73d210e0",
                "name": "noetic-compass-api",
                "type": "web_service",
                "branch": "master",
                "region": "oregon",
                "autoDeployTrigger": "checksPass",
                "healthCheckPath": "/health",
            }
        ],
    },
    {
        "environment": "accounts-canary",
        "id": "exs-d9aknt8458ps73ftpkc0",
        "path": "render.canary.yaml",
        "sourceBranch": "master",
        "autoSyncRequired": False,
        "services": [
            {
                "id": "srv-d9akoolaeets73bp3e7g",
                "name": "cas-harness-api-accounts-canary",
                "type": "private_service",
                "branch": "release/accounts-canary-20260713",
                "region": "oregon",
                "autoDeployTrigger": "checksPass",
            }
        ],
    },
]

_SERVICE_ITEM = re.compile(r"^(?P<indent> *)-\s+type:\s*(?P<value>[^#]+?)\s*(?:#.*)?$")
_ENV_ITEM = re.compile(r"^(?P<indent> *)-\s+key:\s*(?P<value>[^#]+?)\s*(?:#.*)?$")
_DIRECT_FIELD = re.compile(
    r"^(?P<indent> *)(?P<key>[A-Za-z][A-Za-z0-9_]*):(?:\s*(?P<value>.*?))?\s*$"
)
_SECRET_ENV_NAME = re.compile(
    r"(?:SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE_KEY|ACCESS_KEY|CREDENTIAL|PEPPER|DATABASE_URL|WEBHOOK)",
    re.IGNORECASE,
)
_HIGH_RISK_LITERAL_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
_BLUEPRINT_SERVICE_TYPES = {
    "web_service": "web",
    "private_service": "pserv",
}
OBJECT_LOCK_RECEIPT_ATTESTATION_ENV = "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY"


class ControlError(RuntimeError):
    """A repository or live Blueprint control is missing or unsafe."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ControlError(message)


def _scalar(value: str) -> str:
    value = value.strip()
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value


def _direct_fields(lines: list[str], start: int, item_indent: int) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent <= item_indent:
            break
        if current_indent != item_indent + 2:
            continue
        match = _DIRECT_FIELD.match(line)
        if match:
            fields[match.group("key")] = _scalar(match.group("value") or "")
    return fields


def parse_service_blocks(text: str) -> list[dict[str, str]]:
    """Return direct fields for each Render service list item."""

    _require("\t" not in text, "Blueprint YAML must use spaces, not tabs")
    lines = text.splitlines()
    services: list[dict[str, str]] = []
    for index, line in enumerate(lines):
        match = _SERVICE_ITEM.match(line)
        if not match:
            continue
        item_indent = len(match.group("indent"))
        fields = {"type": _scalar(match.group("value"))}
        fields.update(_direct_fields(lines, index, item_indent))
        _require(bool(fields.get("name")), "Every Blueprint service must have a name")
        services.append(fields)
    return services


def parse_env_blocks(text: str) -> list[dict[str, str]]:
    """Return direct fields for each envVars item."""

    lines = text.splitlines()
    env_vars: list[dict[str, str]] = []
    for index, line in enumerate(lines):
        match = _ENV_ITEM.match(line)
        if not match:
            continue
        item_indent = len(match.group("indent"))
        fields = {"key": _scalar(match.group("value"))}
        fields.update(_direct_fields(lines, index, item_indent))
        env_vars.append(fields)
    return env_vars


def assert_no_secret_literals(text: str, label: str) -> None:
    for pattern in _HIGH_RISK_LITERAL_PATTERNS:
        _require(
            pattern.search(text) is None,
            f"{label} contains a value that looks like a committed credential",
        )

    for env_var in parse_env_blocks(text):
        key = env_var["key"]
        if not _SECRET_ENV_NAME.search(key):
            continue
        _require(
            "value" not in env_var,
            f"{label}: sensitive env var {key} must not have a literal value",
        )
        is_dashboard_managed = env_var.get("sync", "").lower() == "false"
        is_generated = env_var.get("generateValue", "").lower() == "true"
        is_reference = "fromDatabase" in env_var or "fromService" in env_var
        _require(
            is_dashboard_managed or is_generated or is_reference,
            f"{label}: sensitive env var {key} must be sync:false, generated, or referenced",
        )


def assert_receipt_attestation_key_declaration(text: str, label: str) -> None:
    """Require one dashboard-managed stable receipt authority per Blueprint."""

    matches = [
        env_var
        for env_var in parse_env_blocks(text)
        if env_var.get("key") == OBJECT_LOCK_RECEIPT_ATTESTATION_ENV
    ]
    _require(
        len(matches) == 1,
        f"{label}: must declare exactly one {OBJECT_LOCK_RECEIPT_ATTESTATION_ENV}",
    )
    declaration = matches[0]
    _require(
        set(declaration) == {"key", "sync"}
        and declaration.get("sync", "").lower() == "false",
        f"{label}: {OBJECT_LOCK_RECEIPT_ATTESTATION_ENV} must be server-only sync:false",
    )


def _load_manifest(repo_root: Path) -> dict[str, Any]:
    path = repo_root / MANIFEST_PATH
    _require(path.is_file(), f"Missing control manifest: {MANIFEST_PATH.as_posix()}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ControlError(f"Cannot read control manifest: {exc}") from exc
    _require(isinstance(manifest, dict), "Control manifest root must be an object")
    assert_no_secret_literals(json.dumps(manifest, sort_keys=True), str(MANIFEST_PATH))
    return manifest


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    expected_keys = {
        "schemaVersion",
        "repository",
        "requiredAggregateChecks",
        "attestations",
        "blueprints",
    }
    _require(set(manifest) == expected_keys, "Control manifest has missing or unknown fields")
    _require(manifest.get("schemaVersion") == 2, "Control manifest schemaVersion must be 2")
    _require(manifest.get("repository") == REPOSITORY, "Control manifest repository drifted")
    _require(
        manifest.get("requiredAggregateChecks") == REQUIRED_AGGREGATE_CHECKS,
        "Control manifest must require cas-ci-gate and cas-postgres-live-gate",
    )
    _require(
        manifest.get("attestations")
        == {
            "requiredFields": ATTESTATION_FIELDS,
            "shaFormat": SHA_FORMAT,
            "requirePostSyncEvidence": True,
        },
        "Attestations must record separate exact Blueprint and service source SHAs",
    )
    _require(
        manifest.get("blueprints") == EXPECTED_BLUEPRINTS,
        "Blueprint IDs, paths, source branches, or service mappings drifted",
    )


def _safe_repo_path(repo_root: Path, relative: str) -> Path:
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ControlError(f"Blueprint path escapes repository root: {relative}") from exc
    return candidate


def validate_blueprint_yaml(repo_root: Path, blueprint: Mapping[str, Any]) -> None:
    relative_path = str(blueprint["path"])
    path = _safe_repo_path(repo_root, relative_path)
    _require(path.is_file(), f"Missing Blueprint file: {relative_path}")
    text = path.read_text(encoding="utf-8")

    _require(
        "Blueprint Auto Sync MUST stay disabled" in text,
        f"{relative_path} is missing the Auto Sync safety warning",
    )
    _require(
        "exact Blueprint source SHA" in text,
        f"{relative_path} is missing the exact-SHA sync warning",
    )
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        _require(
            re.match(r"^\s*(?:-\s+)?commit\s*:", line, re.IGNORECASE) is None,
            f"{relative_path} must not pin a service to commit; CI gates linked branches",
        )
        _require(
            re.match(r"^\s*autoDeploy\s*:", line) is None,
            f"{relative_path} must use autoDeployTrigger, not deprecated autoDeploy",
        )

    assert_no_secret_literals(text, relative_path)
    assert_receipt_attestation_key_declaration(text, relative_path)
    actual_services = parse_service_blocks(text)
    actual_by_name = {service["name"]: service for service in actual_services}
    expected_services = blueprint["services"]
    expected_names = {service["name"] for service in expected_services}
    _require(
        set(actual_by_name) == expected_names,
        f"{relative_path} service list does not match the control manifest",
    )

    for expected in expected_services:
        actual = actual_by_name[expected["name"]]
        _require(
            actual.get("type") == _BLUEPRINT_SERVICE_TYPES[expected["type"]],
            f"{relative_path}:{expected['name']} service type drifted",
        )
        _require(
            actual.get("repo") == REPOSITORY_URL,
            f"{relative_path}:{expected['name']} must use {REPOSITORY_URL}",
        )
        for field in ("branch", "region", "autoDeployTrigger", "healthCheckPath"):
            if field not in expected:
                continue
            _require(
                actual.get(field) == expected[field],
                f"{relative_path}:{expected['name']} {field} must be {expected[field]}",
            )


def validate_workflow_locations(repo_root: Path) -> None:
    ignored = {".git", "node_modules", ".pytest_cache", "__pycache__"}
    misplaced: list[str] = []

    def ignore_error(_: OSError) -> None:
        return None

    for current, directories, files in os.walk(repo_root, onerror=ignore_error):
        directories[:] = [name for name in directories if name not in ignored]
        current_path = Path(current)
        if current_path.name != "workflows" or current_path.parent.name != ".github":
            continue
        if current_path.resolve() == (repo_root / ".github/workflows").resolve():
            continue
        for name in files:
            if Path(name).suffix.lower() in {".yml", ".yaml"}:
                misplaced.append(str((current_path / name).relative_to(repo_root)))

    _require(
        not misplaced,
        "GitHub Actions workflows must exist only under repository-root "
        f".github/workflows; misplaced: {', '.join(sorted(misplaced))}",
    )


def validate_ci_integration(repo_root: Path) -> None:
    ci_path = repo_root / ".github/workflows/ci.yml"
    control_path = repo_root / ".github/workflows/render-blueprint-control.yml"
    runtime_monitor_path = repo_root / ".github/workflows/production-runtime-monitor.yml"
    _require(ci_path.is_file(), "Missing root CAS CI workflow")
    _require(control_path.is_file(), "Missing root Render Blueprint control workflow")
    _require(
        runtime_monitor_path.is_file(),
        "Missing root CAS production runtime monitor workflow",
    )
    ci_text = ci_path.read_text(encoding="utf-8")
    control_text = control_path.read_text(encoding="utf-8")
    runtime_monitor_text = runtime_monitor_path.read_text(encoding="utf-8")

    _require("blueprint_control:" in ci_text, "CAS CI is missing blueprint_control job")
    _require(
        "python scripts/verify_render_blueprint_control.py --offline" in ci_text,
        "CAS CI does not run the offline Blueprint control verifier",
    )
    _require(
        "needs.blueprint_control.result" in ci_text,
        "cas-ci-gate does not aggregate the Blueprint control result",
    )
    _require("pull_request:" in control_text, "Control workflow must run for pull requests")
    _require("schedule:" in control_text, "Control workflow must schedule live drift checks")
    _require("pull_request_target:" not in control_text, "Fork-safe workflow must not use pull_request_target")
    _require(
        "python scripts/verify_render_blueprint_control.py --live" in control_text,
        "Control workflow is missing the live Auto Sync drift check",
    )
    _require(
        "github.repository == 'LittleHenderson/noetic-compass'" in control_text
        and "github.ref == 'refs/heads/master'" in control_text
        and "github.event_name != 'pull_request'" in control_text,
        "Live Blueprint check must be restricted to protected upstream master events",
    )
    _require(
        "schedule:" in runtime_monitor_text
        and "workflow_dispatch:" in runtime_monitor_text,
        "Production runtime monitor must be scheduled and manually dispatchable",
    )
    _require(
        "python scripts/verify_production_runtime_readiness.py --readiness"
        in runtime_monitor_text,
        "Production runtime monitor is missing API dependency readiness",
    )
    _require(
        "python scripts/verify_production_runtime_readiness.py --worker-realmode"
        in runtime_monitor_text,
        "Production runtime monitor is missing worker realmode proof",
    )
    _require(
        "python scripts/verify_render_blueprint_control.py --live"
        in runtime_monitor_text,
        "Production runtime monitor is missing live Blueprint drift control",
    )
    _require(
        "name: cas-production-runtime-monitor-gate" in runtime_monitor_text,
        "Production runtime monitor aggregate check name drifted",
    )
    for result_name in (
        "needs.api_dependency_readiness.result",
        "needs.worker_realmode.result",
        "needs.blueprint_drift.result",
    ):
        _require(
            result_name in runtime_monitor_text,
            f"Production runtime monitor gate does not aggregate {result_name}",
        )


def validate_offline(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    manifest = _load_manifest(repo_root)
    validate_manifest(manifest)
    for blueprint in manifest["blueprints"]:
        validate_blueprint_yaml(repo_root, blueprint)
    validate_workflow_locations(repo_root)
    validate_ci_integration(repo_root)
    return manifest


def validate_live_payload(payload: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    _require(payload.get("id") == expected["id"], f"Unexpected Blueprint ID for {expected['environment']}")
    _require(
        payload.get("autoSync") is expected["autoSyncRequired"],
        f"{expected['environment']} Blueprint Auto Sync drifted from false",
    )
    _require(payload.get("path") == expected["path"], f"{expected['environment']} Blueprint path drifted")
    _require(
        payload.get("branch") == expected["sourceBranch"],
        f"{expected['environment']} Blueprint source branch drifted",
    )
    _require(
        str(payload.get("repo", "")).rstrip("/") == REPOSITORY_URL,
        f"{expected['environment']} Blueprint repository drifted",
    )


def validate_live_service_payload(
    payload: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    environment: str,
) -> None:
    """Validate one stable Render service without exposing its raw payload."""

    label = f"{environment} service {expected['name']}"
    _require(payload.get("id") == expected["id"], f"{label} stable ID drifted")
    _require(payload.get("name") == expected["name"], f"{label} name drifted")
    _require(payload.get("type") == expected["type"], f"{label} type drifted")
    _require(
        str(payload.get("repo", "")).rstrip("/") == REPOSITORY_URL,
        f"{label} repository drifted",
    )
    _require(payload.get("branch") == expected["branch"], f"{label} branch drifted")
    _require(
        payload.get("autoDeployTrigger") == expected["autoDeployTrigger"],
        f"{label} autoDeployTrigger drifted from {expected['autoDeployTrigger']}",
    )

    details = payload.get("serviceDetails")
    _require(isinstance(details, Mapping), f"{label} serviceDetails are unavailable")
    _require(details.get("region") == expected["region"], f"{label} region drifted")
    if "healthCheckPath" in expected:
        _require(
            details.get("healthCheckPath") == expected["healthCheckPath"],
            f"{label} healthCheckPath drifted from {expected['healthCheckPath']}",
        )
    else:
        _require(
            details.get("healthCheckPath") in (None, ""),
            f"{label} unexpectedly exposes a healthCheckPath",
        )


def _read_json(request: urllib.request.Request, timeout: float) -> Mapping[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise ControlError(f"Render API returned HTTP {exc.code}; response body suppressed") from exc
    except urllib.error.URLError as exc:
        raise ControlError(f"Render API request failed: {exc.reason}") from exc
    except (TimeoutError, json.JSONDecodeError) as exc:
        raise ControlError(f"Render API response was unavailable or invalid: {type(exc).__name__}") from exc
    _require(isinstance(payload, dict), "Render API response must be an object")
    return payload


def validate_live(
    manifest: Mapping[str, Any],
    api_key: str,
    *,
    api_base: str = "https://api.render.com/v1",
    timeout: float = 15.0,
) -> None:
    _require(bool(api_key.strip()), "RENDER_API_KEY is required for --live")
    for blueprint in manifest["blueprints"]:
        blueprint_id = urllib.parse.quote(str(blueprint["id"]), safe="")
        request = urllib.request.Request(
            f"{api_base.rstrip('/')}/blueprints/{blueprint_id}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "noetic-compass-blueprint-control/1",
            },
            method="GET",
        )
        payload = _read_json(request, timeout)
        validate_live_payload(payload, blueprint)
        print(
            f"live Blueprint control PASS: {blueprint['environment']} "
            f"({blueprint['id']}) autoSync=false"
        )
        for service in blueprint["services"]:
            service_id = urllib.parse.quote(str(service["id"]), safe="")
            service_request = urllib.request.Request(
                f"{api_base.rstrip('/')}/services/{service_id}",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "noetic-compass-blueprint-control/1",
                },
                method="GET",
            )
            service_payload = _read_json(service_request, timeout)
            validate_live_service_payload(
                service_payload,
                service,
                environment=str(blueprint["environment"]),
            )
            health_suffix = (
                f", healthCheckPath={service['healthCheckPath']}"
                if "healthCheckPath" in service
                else ""
            )
            print(
                f"live Render service control PASS: {blueprint['environment']} "
                f"{service['name']} ({service['id']}), branch={service['branch']}, "
                f"autoDeployTrigger={service['autoDeployTrigger']}{health_suffix}"
            )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="run repository-only checks (default)")
    mode.add_argument("--live", action="store_true", help="also verify live Render Blueprint settings")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the script's parent repository)",
    )
    parser.add_argument(
        "--api-base",
        default="https://api.render.com/v1",
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = validate_offline(args.repo_root)
        print(
            "offline Blueprint control PASS: "
            f"{len(manifest['blueprints'])} Blueprints, "
            f"required checks {', '.join(REQUIRED_AGGREGATE_CHECKS)}"
        )
        if args.live:
            validate_live(
                manifest,
                os.environ.get("RENDER_API_KEY", ""),
                api_base=args.api_base,
            )
    except (ControlError, OSError) as exc:
        print(f"Blueprint control FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
