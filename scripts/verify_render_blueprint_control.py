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
import queue
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


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
    {
        "environment": "customer-production",
        "id": "exs-d9biqt37uimc73ajh99g",
        "path": "render.customer.yaml",
        "sourceBranch": "master",
        "autoSyncRequired": False,
        "project": {
            "id": "prj-d9biitbtqb8s73cn3le0",
            "name": "cas-harness-customer",
        },
        "providerEnvironment": {
            "id": "evm-d9biitbtqb8s73cn3leg",
            "name": "production",
            "projectId": "prj-d9biitbtqb8s73cn3le0",
            "databasesIds": ["dpg-d9biitbtqb8s73cn3mgg-a"],
            "serviceIds": ["srv-d9bijbjtqb8s73cn4n20"],
            "protectedStatus": "protected",
            "networkIsolationEnabled": True,
        },
        "databases": [
            {
                "id": "dpg-d9biitbtqb8s73cn3mgg-a",
                "name": "cas-harness-customer-postgres",
                "databaseName": "cas_harness_customer",
                "databaseUser": "cas_harness_customer",
                "plan": "basic_256mb",
                "region": "oregon",
                "version": "16",
                "diskSizeGB": 5,
                "diskAutoscalingEnabled": True,
                # Render's live Postgres API serializes the Blueprint's
                # `ipAllowList: []` (no public database ingress) as null.
                "ipAllowList": None,
            }
        ],
        "services": [
            {
                "id": "srv-d9bijbjtqb8s73cn4n20",
                "name": "cas-harness-customer-api",
                "type": "web_service",
                "branch": "master",
                "region": "oregon",
                "autoDeployTrigger": "checksPass",
                "healthCheckPath": "/health",
                "url": "https://cas-harness-customer-api.onrender.com",
                "disk": {
                    "id": "dsk-d9bijbjtqb8s73cn4o60",
                    "name": "cas-harness-customer-support",
                    "mountPath": "/var/customer-support",
                    "sizeGB": 1,
                },
            }
        ],
    },
]
EXPECTED_PENDING_BLUEPRINTS: list[dict[str, Any]] = []
EXPECTED_CUSTOMER_BLUEPRINT = EXPECTED_BLUEPRINTS[2]
AUXILIARY_BLUEPRINT_PATHS = (
    "noetic-compass-scaffold/noetic-compass/infra/render.yaml",
)
CUSTOMER_BLUEPRINT_PATH = "render.customer.yaml"
CUSTOMER_SERVICE_NAME = "cas-harness-customer-api"
CUSTOMER_DATABASE_NAME = "cas-harness-customer-postgres"
CUSTOMER_GENERATED_SECRET_ENV_KEYS = frozenset(
    {
        "NC_JWT_SECRET",
        "NC_ACCOUNT_CREDENTIAL_PEPPER",
        "NC_ACCOUNT_BOOTSTRAP_SECRET",
        "NC_PLATFORM_TENANT_PROVISIONING_SECRET",
        "NC_BILLING_ADMIN_SECRET",
        "NC_EVIDENCE_SHARE_TOKEN_PEPPER",
        "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY",
    }
)
CUSTOMER_AIRTABLE_DASHBOARD_ENV_KEYS = frozenset(
    {
        "NC_AIRTABLE_TOKEN",
        "NC_AIRTABLE_BASE_ID",
        "NC_AIRTABLE_TABLE_NAME",
        "NC_AIRTABLE_DEDUP_FIELD",
        "NC_AIRTABLE_OWNER_FIELD",
        "NC_AIRTABLE_OWNER_VALUE",
        "NC_AIRTABLE_LIFECYCLE_FIELD",
    }
)
CUSTOMER_INJECTED_PROVIDER_ENV_KEYS = frozenset(
    {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "ATLAS_LIVE_WORKER_URL",
        "ATLAS_LIVE_WORKER_TOKEN",
        "NC_HUMAN_ATTESTATION_PSEUDONYM_ACTIVE_KEY_ID",
        "NC_HUMAN_ATTESTATION_PSEUDONYM_KEYRING_JSON",
    }
) | CUSTOMER_AIRTABLE_DASHBOARD_ENV_KEYS
CUSTOMER_LITERAL_ENV_VALUES = {
    "NC_DEBUG": "false",
    "NC_DEPLOYMENT_PROFILE": "customer-production",
    "NC_JWT_ALGORITHM": "HS256",
    "NC_JWT_EXPIRY_MINUTES": "60",
    "NC_STATE_LEDGER_ENABLED": "true",
    "NC_STATE_LEDGER_READ_AUTHORITY": "true",
    "NC_ACCOUNTS_ENABLED": "true",
    "NC_ACCOUNTS_BOOTSTRAP_TENANT_ID": "primary",
    "NC_ACCOUNTS_ALLOW_SINGLE_HOST_SQLITE": "false",
    "NC_QUOTAS_ENABLED": "true",
    "NC_BILLING_ENTITLEMENTS_ENABLED": "true",
    "NC_BILLING_PROVIDER": "null",
    "NC_BILLING_RECONCILIATION_ENABLED": "false",
    "NC_BILLING_WORKER_MEASUREMENT_ENABLED": "false",
    "NC_BILLING_USAGE_DISPATCH_ENABLED": "false",
    "NC_FLEET_SERVICE_AUTH_ENABLED": "false",
    "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED": "true",
    "CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR": (
        "/var/customer-support/evidence_packets"
    ),
    "NC_EVIDENCE_SHARES_ENABLED": "true",
    "CAS_HARNESS_EVIDENCE_ANCHOR_MODE": "s3",
    "CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET": "cas-harness-runpod-92754088",
    "CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX": (
        "cas-harness/customer-production/evidence-anchors"
    ),
    "CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION": "us-west-2",
    "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE": "GOVERNANCE",
    "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS": "31",
    "NC_CRM_PROVIDER": "airtable",
    "NC_AIRTABLE_API_BASE_URL": "https://api.airtable.com/v0",
    "NC_CRM_LEAD_STORE_BACKEND": "state_store",
    "NC_CRM_LEAD_STORE_PATH": "/var/customer-support/leads.jsonl",
    "NC_CRM_PRIVACY_NOTICE_PUBLICATION_STATUS": "OPEN",
    "NC_CRM_PRIVACY_NOTICE_VERSION": "draft-2026-07-14",
    "NC_CRM_PRIVACY_NOTICE_CONTENT_SHA256": (
        "e94df1615dde4122836b47a74e32d45c79b63c1603db3bd1aee01f62d7ddae28"
    ),
    "NC_CRM_PUBLIC_LEAD_RATE_LIMIT_MAX": "5",
    "NC_CRM_PUBLIC_LEAD_RATE_LIMIT_WINDOW_SECONDS": "3600",
    "NC_SUPPORT_TICKET_STORE_BACKEND": "state_store",
    "NC_SUPPORT_TICKET_STORE_PATH": (
        "/var/customer-support/support_tickets.jsonl"
    ),
    "NC_SUPPORT_ACK_SLA_SECONDS": "86400",
    "NC_SUPPORT_PUBLIC_TICKET_RATE_LIMIT_MAX": "5",
    "NC_SUPPORT_PUBLIC_TICKET_RATE_LIMIT_WINDOW_SECONDS": "3600",
    "ATLAS_ALLOWED_ORIGINS": (
        "https://atlas.noeticcompass.com,"
        "https://atlas-viewer-app.onrender.com,"
        "https://cascompass.ai,https://www.cascompass.ai"
    ),
    "NC_CORS_ORIGIN_REGEX": "^$",
    "NC_DEFAULT_LLM_PROVIDER": "mock",
    "NC_MOCK_LLM": "true",
    "NC_RATE_LIMIT_TIER": "enterprise",
    "NC_RATE_LIMIT_RPM": "120",
}
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
PRODUCTION_PROVIDER_DASHBOARD_ENV_KEYS = (
    # Stripe subscriptions and usage/invoice reconciliation.
    "NC_STRIPE_SECRET_KEY",
    "NC_STRIPE_WEBHOOK_SECRET",
    "NC_STRIPE_PROFESSIONAL_PRICE_ID",
    "NC_STRIPE_ENTERPRISE_PRICE_ID",
    "NC_STRIPE_CHECKOUT_SUCCESS_URL",
    "NC_STRIPE_CHECKOUT_CANCEL_URL",
    "NC_STRIPE_PORTAL_RETURN_URL",
    "NC_BILLING_PROVIDER_REFERENCE_HASH_KEY",
    "NC_BILLING_USAGE_METER_EVENT_NAME",
    "NC_BILLING_USAGE_METER_VERSION",
    "NC_BILLING_USAGE_CURRENCY",
    "NC_STRIPE_USAGE_PRICE_ID",
    "NC_STRIPE_LIVEMODE",
    "NC_BILLING_CUSTOMER_RECEIPT_ALLOWED_HOSTS",
    "NC_BILLING_WORKER_RECEIPT_HMAC_KEY",
    "NC_BILLING_WORKER_RECEIPT_KEY_ID",
    "NC_BILLING_WORKER_RECEIPT_ISSUER",
    "NC_BILLING_WORKER_PROVIDER_ID",
    "NC_BILLING_WORKER_ID",
    # Airtable CRM.
    "NC_CRM_PROVIDER",
    "NC_AIRTABLE_TOKEN",
    "NC_AIRTABLE_BASE_ID",
    "NC_AIRTABLE_TABLE_NAME",
    "NC_AIRTABLE_API_BASE_URL",
    "NC_AIRTABLE_DEDUP_FIELD",
    "NC_AIRTABLE_OWNER_FIELD",
    "NC_AIRTABLE_OWNER_VALUE",
    "NC_AIRTABLE_LIFECYCLE_FIELD",
    # AWS S3 Object Lock.
    "CAS_HARNESS_EVIDENCE_ANCHOR_MODE",
    "CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET",
    "CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX",
    "CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION",
    "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE",
    "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS",
    "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
)
LIVE_REQUEST_TIMEOUT_SECONDS = 30.0
LIVE_REQUEST_ATTEMPTS = 3
LIVE_RETRY_BACKOFF_SECONDS = (2.0, 5.0)
LIVE_TOTAL_TIMEOUT_SECONDS = 210.0
LIVE_RESPONSE_MAX_BYTES = 1_048_576
_RETRYABLE_RENDER_HTTP_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class ControlError(RuntimeError):
    """A repository or live Blueprint control is missing or unsafe."""


class _RejectRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep the Render Bearer token on the exact requested origin."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Mapping[str, str],
        newurl: str,
    ) -> None:
        if fp is not None:
            fp.close()
        raise urllib.error.HTTPError(
            req.full_url,
            code,
            "Render API redirect rejected",
            headers,
            None,
        )


_RENDER_API_OPENER = urllib.request.build_opener(_RejectRedirectHandler())


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


def parse_service_env_blocks(text: str, service_name: str) -> list[dict[str, str]]:
    """Return only the direct envVars items attached to one named service."""

    _require("\t" not in text, "Blueprint YAML must use spaces, not tabs")
    lines = text.splitlines()
    service_ranges: list[tuple[int, int, int]] = []
    for index, line in enumerate(lines):
        match = _SERVICE_ITEM.match(line)
        if not match:
            continue
        item_indent = len(match.group("indent"))
        fields = {"type": _scalar(match.group("value"))}
        fields.update(_direct_fields(lines, index, item_indent))
        if fields.get("name") != service_name:
            continue
        end = len(lines)
        for offset in range(index + 1, len(lines)):
            candidate = lines[offset]
            stripped = candidate.strip()
            if not stripped or stripped.startswith("#"):
                continue
            current_indent = len(candidate) - len(candidate.lstrip(" "))
            if current_indent <= item_indent:
                end = offset
                break
        service_ranges.append((index, end, item_indent))

    _require(
        len(service_ranges) == 1,
        f"Blueprint must declare exactly one service named {service_name}",
    )
    start, end, item_indent = service_ranges[0]
    env_block_starts: list[int] = []
    for index in range(start + 1, end):
        line = lines[index]
        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent != item_indent + 2:
            continue
        match = _DIRECT_FIELD.match(line)
        if match and match.group("key") == "envVars" and not _scalar(
            match.group("value") or ""
        ):
            env_block_starts.append(index)

    _require(
        len(env_block_starts) == 1,
        f"Blueprint service {service_name} must declare exactly one envVars block",
    )
    env_start = env_block_starts[0]
    env_indent = item_indent + 2
    env_end = end
    for index in range(env_start + 1, end):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent <= env_indent:
            env_end = index
            break

    env_vars: list[dict[str, str]] = []
    for index in range(env_start + 1, env_end):
        match = _ENV_ITEM.match(lines[index])
        if not match or len(match.group("indent")) != env_indent + 2:
            continue
        item_indent = len(match.group("indent"))
        fields = {"key": _scalar(match.group("value"))}
        fields.update(_direct_fields(lines[:env_end], index, item_indent))
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


def assert_receipt_attestation_key_declaration(
    text: str,
    label: str,
    *,
    generated: bool = False,
) -> None:
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
    expected = (
        {"key", "generateValue"} if generated else {"key", "sync"}
    )
    field = "generateValue" if generated else "sync"
    _require(
        set(declaration) == expected
        and declaration.get(field, "").lower() == ("true" if generated else "false"),
        f"{label}: {OBJECT_LOCK_RECEIPT_ATTESTATION_ENV} must be server-only "
        + ("generateValue:true" if generated else "sync:false"),
    )


def assert_production_provider_env_declarations(
    text: str,
    label: str,
    service_name: str,
) -> None:
    """Require every provider setting on the production service to be a safe slot."""

    env_vars = parse_service_env_blocks(text, service_name)
    by_key: dict[str, list[dict[str, str]]] = {}
    for env_var in env_vars:
        by_key.setdefault(env_var.get("key", ""), []).append(env_var)
    for key in PRODUCTION_PROVIDER_DASHBOARD_ENV_KEYS:
        matches = by_key.get(key, [])
        _require(
            len(matches) == 1,
            f"{label}:{service_name} must declare exactly one {key}",
        )
        declaration = matches[0]
        _require(
            set(declaration) == {"key", "sync"}
            and declaration.get("sync", "").lower() == "false",
            f"{label}:{service_name} {key} must be a dashboard-managed sync:false slot",
        )


def assert_customer_blueprint_contract(text: str, label: str) -> None:
    """Pin the pre-provision customer lane to its fail-closed effect posture."""

    service = parse_service_blocks(text)[0]
    for field, expected in {
        "runtime": "docker",
        "rootDir": "noetic-compass-scaffold/noetic-compass",
        "dockerfilePath": "./Dockerfile.api",
        "dockerContext": ".",
        "plan": "starter",
        "numInstances": "1",
    }.items():
        _require(
            service.get(field) == expected,
            f"{label}:{CUSTOMER_SERVICE_NAME} {field} must be {expected}",
        )

    database_block = re.search(
        r"(?ms)^        databases:\s*$\n(?P<body>.*?)(?=^        services:\s*$)",
        text,
    )
    _require(
        database_block is not None,
        f"{label} must declare one dedicated {CUSTOMER_DATABASE_NAME}",
    )
    database_lines = {
        line.strip()
        for line in database_block.group("body").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    _require(
        database_lines
        == {
            f"- name: {CUSTOMER_DATABASE_NAME}",
            "plan: basic-256mb",
            "region: oregon",
            'postgresMajorVersion: "16"',
            "databaseName: cas_harness_customer",
            "user: cas_harness_customer",
            "diskSizeGB: 5",
            "storageAutoscalingEnabled: true",
            "ipAllowList: []",
        },
        f"{label} dedicated customer Postgres contract drifted",
    )

    disk_block = re.search(
        r"(?ms)^            disk:\s*$\n(?P<body>.*?)(?=^            envVars:\s*$)",
        text,
    )
    _require(
        disk_block is not None
        and [
            line.strip()
            for line in disk_block.group("body").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        == [
            "name: cas-harness-customer-support",
            "mountPath: /var/customer-support",
            "sizeGB: 1",
        ],
        f"{label}:{CUSTOMER_SERVICE_NAME} dedicated support disk drifted",
    )

    env_vars = parse_service_env_blocks(text, CUSTOMER_SERVICE_NAME)
    by_key: dict[str, dict[str, str]] = {}
    for declaration in env_vars:
        key = declaration.get("key", "")
        _require(bool(key), f"{label}:{CUSTOMER_SERVICE_NAME} has an empty env key")
        _require(
            key not in by_key,
            f"{label}:{CUSTOMER_SERVICE_NAME} declares duplicate env key {key}",
        )
        by_key[key] = declaration

    expected_env_keys = (
        set(CUSTOMER_LITERAL_ENV_VALUES)
        | CUSTOMER_GENERATED_SECRET_ENV_KEYS
        | CUSTOMER_INJECTED_PROVIDER_ENV_KEYS
        | {"NC_DATABASE_URL"}
    )
    _require(
        set(by_key) == expected_env_keys,
        f"{label}:{CUSTOMER_SERVICE_NAME} env key inventory drifted; "
        f"missing={sorted(expected_env_keys - set(by_key))}, "
        f"extra={sorted(set(by_key) - expected_env_keys)}",
    )

    for key, expected in CUSTOMER_LITERAL_ENV_VALUES.items():
        _require(
            by_key.get(key) == {"key": key, "value": expected},
            f"{label}:{CUSTOMER_SERVICE_NAME} {key} must be literal {expected}",
        )
    for key in CUSTOMER_GENERATED_SECRET_ENV_KEYS:
        _require(
            by_key.get(key) == {"key": key, "generateValue": "true"},
            f"{label}:{CUSTOMER_SERVICE_NAME} {key} must be independently generated",
        )
    for key in CUSTOMER_INJECTED_PROVIDER_ENV_KEYS:
        _require(
            by_key.get(key) == {"key": key, "sync": "false"},
            f"{label}:{CUSTOMER_SERVICE_NAME} {key} must be provider-injected sync:false",
        )

    actual_sync_false = {
        key
        for key, declaration in by_key.items()
        if declaration.get("sync", "").lower() == "false"
    }
    _require(
        actual_sync_false == CUSTOMER_INJECTED_PROVIDER_ENV_KEYS,
        f"{label}:{CUSTOMER_SERVICE_NAME} sync:false is limited to required provider inputs",
    )
    actual_generated = {
        key
        for key, declaration in by_key.items()
        if declaration.get("generateValue", "").lower() == "true"
    }
    _require(
        actual_generated == CUSTOMER_GENERATED_SECRET_ENV_KEYS,
        f"{label}:{CUSTOMER_SERVICE_NAME} generated authority inventory drifted",
    )
    database_declaration = by_key.get("NC_DATABASE_URL")
    _require(
        database_declaration == {"key": "NC_DATABASE_URL", "fromDatabase": ""},
        f"{label}:{CUSTOMER_SERVICE_NAME} NC_DATABASE_URL must reference Render Postgres",
    )
    database_reference = re.compile(
        r"(?m)^(?P<indent> *)- key: NC_DATABASE_URL\s*$\n"
        r"(?P=indent)  fromDatabase:\s*$\n"
        rf"(?P=indent)    name: {re.escape(CUSTOMER_DATABASE_NAME)}\s*$\n"
        r"(?P=indent)    property: connectionString\s*$"
    )
    _require(
        database_reference.search(text) is not None,
        f"{label}:{CUSTOMER_SERVICE_NAME} must reference only {CUSTOMER_DATABASE_NAME}",
    )

    for required_fragment in (
        "  - name: cas-harness-customer",
        "      - name: production",
        "          isolation: enabled",
        "          protection: enabled",
    ):
        _require(
            required_fragment in text,
            f"{label} is missing protected isolated customer environment metadata",
        )


def validate_customer_blueprint_yaml(repo_root: Path) -> None:
    path = _safe_repo_path(repo_root, CUSTOMER_BLUEPRINT_PATH)
    _require(path.is_file(), f"Missing customer Blueprint file: {CUSTOMER_BLUEPRINT_PATH}")
    text = path.read_text(encoding="utf-8")
    validate_blueprint_yaml(
        repo_root,
        EXPECTED_CUSTOMER_BLUEPRINT,
        receipt_key_generated=True,
    )
    assert_customer_blueprint_contract(text, CUSTOMER_BLUEPRINT_PATH)


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
        "pendingBlueprints",
    }
    _require(set(manifest) == expected_keys, "Control manifest has missing or unknown fields")
    _require(manifest.get("schemaVersion") == 3, "Control manifest schemaVersion must be 3")
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
    _require(
        manifest.get("pendingBlueprints") == EXPECTED_PENDING_BLUEPRINTS,
        "Pending Blueprint paths or pre-provider identity contracts drifted",
    )


def _safe_repo_path(repo_root: Path, relative: str) -> Path:
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ControlError(f"Blueprint path escapes repository root: {relative}") from exc
    return candidate


def validate_blueprint_yaml(
    repo_root: Path,
    blueprint: Mapping[str, Any],
    *,
    receipt_key_generated: bool = False,
) -> None:
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
    assert_receipt_attestation_key_declaration(
        text,
        relative_path,
        generated=receipt_key_generated,
    )
    expected_services = blueprint["services"]
    if blueprint.get("environment") == "production":
        _require(
            len(expected_services) == 1,
            f"{relative_path} production Blueprint must pin exactly one service",
        )
        assert_production_provider_env_declarations(
            text,
            relative_path,
            str(expected_services[0]["name"]),
        )
    actual_services = parse_service_blocks(text)
    actual_by_name = {service["name"]: service for service in actual_services}
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


def validate_auxiliary_blueprint_yaml(repo_root: Path, relative_path: str) -> None:
    """Keep non-live/legacy Render files from reintroducing commit-trigger deploys."""

    path = _safe_repo_path(repo_root, relative_path)
    _require(path.is_file(), f"Missing auxiliary Blueprint file: {relative_path}")
    text = path.read_text(encoding="utf-8")
    assert_no_secret_literals(text, relative_path)
    triggers: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        match = re.match(r"^\s*autoDeployTrigger:\s*(?P<value>[^#]+?)\s*$", line)
        if match:
            triggers.append(_scalar(match.group("value")))
        _require(
            re.match(r"^\s*autoDeploy\s*:", line) is None,
            f"{relative_path} must use autoDeployTrigger, not deprecated autoDeploy",
        )
        _require(
            re.match(r"^\s*(?:-\s+)?commit\s*:", line, re.IGNORECASE) is None,
            f"{relative_path} must not pin a service commit",
        )
    _require(triggers, f"{relative_path} must declare autoDeployTrigger for its services")
    _require(
        all(trigger == "checksPass" for trigger in triggers),
        f"{relative_path} autoDeployTrigger must be checksPass for every service",
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
        if blueprint["environment"] == "customer-production":
            validate_customer_blueprint_yaml(repo_root)
        else:
            validate_blueprint_yaml(repo_root, blueprint)
    for relative_path in AUXILIARY_BLUEPRINT_PATHS:
        validate_auxiliary_blueprint_yaml(repo_root, relative_path)
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
    if "databases" in expected:
        resources = payload.get("resources")
        _require(
            isinstance(resources, list),
            f"{expected['environment']} Blueprint resources are unavailable",
        )
        actual_resources = {
            (item.get("id"), item.get("name"), item.get("type"))
            for item in resources
            if isinstance(item, Mapping)
        }
        expected_resources = {
            (service["id"], service["name"], service["type"])
            for service in expected["services"]
        } | {
            (database["id"], database["name"], "postgres")
            for database in expected["databases"]
        }
        _require(
            actual_resources == expected_resources,
            f"{expected['environment']} Blueprint resource identities drifted",
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
    if "disk" in expected:
        disk = details.get("disk")
        _require(
            isinstance(disk, Mapping)
            and all(disk.get(key) == value for key, value in expected["disk"].items()),
            f"{label} persistent disk identity or attachment drifted",
        )
    if "url" in expected:
        _require(
            details.get("url") == expected["url"],
            f"{label} external URL drifted from its identity-locked origin",
        )


def validate_live_database_payload(
    payload: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    environment: str,
) -> None:
    """Validate non-secret Postgres identity and configuration fields."""

    label = f"{environment} Postgres {expected['name']}"
    for key in (
        "id",
        "name",
        "databaseName",
        "databaseUser",
        "plan",
        "region",
        "version",
        "diskSizeGB",
        "diskAutoscalingEnabled",
        "ipAllowList",
    ):
        _require(key in payload, f"{label} {key} is unavailable")
        _require(payload.get(key) == expected[key], f"{label} {key} drifted")


def validate_live_project_payload(
    payload: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    environment: str,
) -> None:
    """Validate the Render project container without reading member identity."""

    label = f"{environment} project {expected['name']}"
    for key in ("id", "name"):
        _require(payload.get(key) == expected[key], f"{label} {key} drifted")


def validate_live_environment_payload(
    payload: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    environment: str,
) -> None:
    """Validate protected membership and network isolation for one environment."""

    label = f"{environment} provider environment {expected['name']}"
    for key in (
        "id",
        "name",
        "projectId",
        "protectedStatus",
        "networkIsolationEnabled",
    ):
        _require(payload.get(key) == expected[key], f"{label} {key} drifted")
    for key in ("databasesIds", "serviceIds"):
        actual = payload.get(key)
        _require(isinstance(actual, list), f"{label} {key} are unavailable")
        _require(
            set(actual) == set(expected[key]) and len(actual) == len(expected[key]),
            f"{label} {key} membership drifted",
        )


def validate_live_disk_payload(
    payload: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    environment: str,
    service_id: str,
) -> None:
    """Validate the customer disk independently of its service projection."""

    label = f"{environment} disk {expected['name']}"
    for key in ("id", "name", "mountPath", "sizeGB"):
        _require(payload.get(key) == expected[key], f"{label} {key} drifted")
    _require(payload.get("serviceId") == service_id, f"{label} service binding drifted")


def _open_and_parse_render_response(
    request: urllib.request.Request,
    timeout: float,
) -> Any:
    """Read one bounded response without following redirects."""

    with _RENDER_API_OPENER.open(request, timeout=timeout) as response:
        body = response.read(LIVE_RESPONSE_MAX_BYTES + 1)
    _require(
        len(body) <= LIVE_RESPONSE_MAX_BYTES,
        "Render API response exceeded the maximum allowed size",
    )
    return json.loads(body)


def _run_with_wall_clock_timeout(
    operation: Callable[[], Any],
    timeout: float,
) -> Any:
    """Bound connect, body read, and parsing even when socket reads keep trickling."""

    outcome: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

    def run() -> None:
        try:
            value = operation()
        except Exception as exc:  # propagated unchanged on the calling thread
            outcome.put((False, exc))
        else:
            outcome.put((True, value))

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise TimeoutError()

    succeeded, value = outcome.get_nowait()
    if not succeeded:
        raise value
    return value


def _read_json(
    request: urllib.request.Request,
    timeout: float,
    *,
    attempts: int = LIVE_REQUEST_ATTEMPTS,
    backoff_seconds: Sequence[float] = LIVE_RETRY_BACKOFF_SECONDS,
    deadline: float | None = None,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> Mapping[str, Any]:
    """Read one Render object with bounded retries for transient failures only."""

    clock_fn = clock or time.monotonic
    sleep_fn = sleep or time.sleep
    _require(timeout > 0, "Render API request timeout must be positive")
    _require(attempts >= 1, "Render API request attempts must be positive")
    _require(
        len(backoff_seconds) >= attempts - 1
        and all(delay >= 0 for delay in backoff_seconds[: attempts - 1]),
        "Render API retry backoff must cover every retry with non-negative delays",
    )

    for attempt in range(1, attempts + 1):
        attempt_timeout = timeout
        if deadline is not None:
            remaining = deadline - clock_fn()
            if remaining <= 0:
                raise ControlError(
                    "Render API live-read window exhausted before a valid response"
                )
            attempt_timeout = min(timeout, remaining)

        failure = ""
        cause: BaseException | None = None
        try:
            payload = _run_with_wall_clock_timeout(
                lambda: _open_and_parse_render_response(
                    request,
                    timeout=attempt_timeout,
                ),
                attempt_timeout,
            )
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            if status not in _RETRYABLE_RENDER_HTTP_STATUSES:
                raise ControlError(
                    f"Render API returned HTTP {status}; response body suppressed"
                ) from exc
            failure = f"HTTP {status}"
            cause = exc
        except urllib.error.URLError as exc:
            failure = f"network error ({type(exc.reason).__name__})"
            cause = exc
        except TimeoutError as exc:
            failure = type(exc).__name__
            cause = exc
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ControlError(
                "Render API response was unavailable or invalid: "
                f"{type(exc).__name__}"
            ) from exc
        else:
            if deadline is not None and clock_fn() >= deadline:
                raise ControlError(
                    "Render API live-read window exhausted after response processing"
                )
            _require(isinstance(payload, dict), "Render API response must be an object")
            return payload

        if attempt == attempts:
            raise ControlError(
                f"Render API remained unavailable after {attempts} attempts; "
                f"last failure: {failure}"
            ) from cause

        delay = float(backoff_seconds[attempt - 1])
        if deadline is not None and deadline - clock_fn() <= delay:
            raise ControlError(
                f"Render API live-read window exhausted after {attempt} attempt(s); "
                f"last failure: {failure}"
            ) from cause
        sleep_fn(delay)

    raise AssertionError("unreachable")


def validate_live(
    manifest: Mapping[str, Any],
    api_key: str,
    *,
    api_base: str = "https://api.render.com/v1",
    timeout: float = LIVE_REQUEST_TIMEOUT_SECONDS,
    attempts: int = LIVE_REQUEST_ATTEMPTS,
    backoff_seconds: Sequence[float] = LIVE_RETRY_BACKOFF_SECONDS,
    total_timeout: float = LIVE_TOTAL_TIMEOUT_SECONDS,
) -> None:
    _require(bool(api_key.strip()), "RENDER_API_KEY is required for --live")
    _require(total_timeout > 0, "Render API total live-read timeout must be positive")
    deadline = time.monotonic() + total_timeout
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
        payload = _read_json(
            request,
            timeout,
            attempts=attempts,
            backoff_seconds=backoff_seconds,
            deadline=deadline,
        )
        validate_live_payload(payload, blueprint)
        print(
            f"live Blueprint control PASS: {blueprint['environment']} "
            f"({blueprint['id']}) autoSync=false"
        )
        project = blueprint.get("project")
        if isinstance(project, Mapping):
            project_id = urllib.parse.quote(str(project["id"]), safe="")
            project_request = urllib.request.Request(
                f"{api_base.rstrip('/')}/projects/{project_id}",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "noetic-compass-blueprint-control/1",
                },
                method="GET",
            )
            project_payload = _read_json(
                project_request,
                timeout,
                attempts=attempts,
                backoff_seconds=backoff_seconds,
                deadline=deadline,
            )
            validate_live_project_payload(
                project_payload,
                project,
                environment=str(blueprint["environment"]),
            )
            print(
                f"live Render project control PASS: {blueprint['environment']} "
                f"{project['name']} ({project['id']})"
            )
        provider_environment = blueprint.get("providerEnvironment")
        if isinstance(provider_environment, Mapping):
            environment_id = urllib.parse.quote(
                str(provider_environment["id"]), safe=""
            )
            environment_request = urllib.request.Request(
                f"{api_base.rstrip('/')}/environments/{environment_id}",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "noetic-compass-blueprint-control/1",
                },
                method="GET",
            )
            environment_payload = _read_json(
                environment_request,
                timeout,
                attempts=attempts,
                backoff_seconds=backoff_seconds,
                deadline=deadline,
            )
            validate_live_environment_payload(
                environment_payload,
                provider_environment,
                environment=str(blueprint["environment"]),
            )
            print(
                f"live Render environment control PASS: {blueprint['environment']} "
                f"{provider_environment['name']} ({provider_environment['id']})"
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
            service_payload = _read_json(
                service_request,
                timeout,
                attempts=attempts,
                backoff_seconds=backoff_seconds,
                deadline=deadline,
            )
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
            disk = service.get("disk")
            if isinstance(disk, Mapping):
                disk_id = urllib.parse.quote(str(disk["id"]), safe="")
                disk_request = urllib.request.Request(
                    f"{api_base.rstrip('/')}/disks/{disk_id}",
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {api_key}",
                        "User-Agent": "noetic-compass-blueprint-control/1",
                    },
                    method="GET",
                )
                disk_payload = _read_json(
                    disk_request,
                    timeout,
                    attempts=attempts,
                    backoff_seconds=backoff_seconds,
                    deadline=deadline,
                )
                validate_live_disk_payload(
                    disk_payload,
                    disk,
                    environment=str(blueprint["environment"]),
                    service_id=str(service["id"]),
                )
                print(
                    f"live Render disk control PASS: {blueprint['environment']} "
                    f"{disk['name']} ({disk['id']})"
                )
        for database in blueprint.get("databases", []):
            database_id = urllib.parse.quote(str(database["id"]), safe="")
            database_request = urllib.request.Request(
                f"{api_base.rstrip('/')}/postgres/{database_id}",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "noetic-compass-blueprint-control/1",
                },
                method="GET",
            )
            database_payload = _read_json(
                database_request,
                timeout,
                attempts=attempts,
                backoff_seconds=backoff_seconds,
                deadline=deadline,
            )
            validate_live_database_payload(
                database_payload,
                database,
                environment=str(blueprint["environment"]),
            )
            print(
                f"live Render Postgres control PASS: {blueprint['environment']} "
                f"{database['name']} ({database['id']})"
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
            f"{len(manifest['blueprints'])} identity-locked Blueprints, "
            f"{len(manifest['pendingBlueprints'])} pending identity lock, "
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
