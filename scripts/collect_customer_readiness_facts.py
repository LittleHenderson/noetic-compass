#!/usr/bin/env python3
"""Collect credential-free customer-readiness facts without creating evidence.

This collector is deliberately incapable of exercising a customer journey.  It
reads three pinned public-production JSON surfaces plus exact repository source
files, records byte hashes and configured-versus-observed facts, and emits an
unsigned OPEN draft.  It never creates an account, audit, share, checkout, or
provider event and can never satisfy a customer-production acceptance gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


REPORT_SCHEMA_VERSION = "cas_harness_customer_readiness_machine_report.v1"
DRAFT_SCHEMA_VERSION = "cas_harness_customer_readiness_machine_draft.v1"
PRODUCTION_API_ORIGIN = "https://cas-harness-customer-api.onrender.com"
PINNED_SURFACES: tuple[tuple[str, str], ...] = (
    ("health", f"{PRODUCTION_API_ORIGIN}/health"),
    ("readiness", f"{PRODUCTION_API_ORIGIN}/health/ready"),
    ("openapi", f"{PRODUCTION_API_ORIGIN}/openapi.json"),
)
PINNED_SURFACE_MAP = dict(PINNED_SURFACES)
EXPECTED_HTTP_STATUSES: Mapping[str, frozenset[int]] = {
    "health": frozenset({200}),
    "readiness": frozenset({200, 503}),
    "openapi": frozenset({200}),
}
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RESPONSE_BYTES = 2_000_000
MAX_RESPONSE_BYTES = 4_000_000

RENDER_PATH = Path("render.customer.yaml")
CONFIG_PATH = Path("noetic-compass-scaffold/noetic-compass/api/config.py")
PUBLIC_SERVICE_NAME = "cas-harness-customer-api"
PUBLIC_SERVICE_SCALARS: Mapping[str, str] = {
    "repo": "https://github.com/LittleHenderson/noetic-compass",
    "branch": "master",
    "rootDir": "noetic-compass-scaffold/noetic-compass",
    "autoDeployTrigger": "checksPass",
    "healthCheckPath": "/health",
}
FEATURE_ENV_KEYS: Mapping[str, str] = {
    "accounts": "NC_ACCOUNTS_ENABLED",
    "quotas": "NC_QUOTAS_ENABLED",
    "billing_entitlements": "NC_BILLING_ENTITLEMENTS_ENABLED",
    "billing_reconciliation": "NC_BILLING_RECONCILIATION_ENABLED",
    "object_store": "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED",
    "shares": "NC_EVIDENCE_SHARES_ENABLED",
}
DATABASE_ENV_KEY = "NC_DATABASE_URL"
CUSTOMER_DATABASE_NAME = "cas-harness-customer-postgres"
BILLING_PROVIDER_ENV_KEY = "NC_BILLING_PROVIDER"
STRIPE_SLOT_KEYS: tuple[str, ...] = (
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
)
SOURCE_CONFIG_FIELDS: Mapping[str, str] = {
    "postgres_database_url": "database_url",
    "accounts": "accounts_enabled",
    "quotas": "quotas_enabled",
    "billing_entitlements": "billing_entitlements_enabled",
    "billing_reconciliation": "billing_reconciliation_enabled",
    "billing_provider": "billing_provider",
    "stripe_secret": "stripe_secret_key",
    "stripe_webhook_secret": "stripe_webhook_secret",
    "stripe_professional_price": "stripe_professional_price_id",
    "stripe_enterprise_price": "stripe_enterprise_price_id",
    "billing_provider_reference_hash_key": "billing_provider_reference_hash_key",
    "billing_usage_meter_event_name": "billing_usage_meter_event_name",
    "billing_usage_meter_version": "billing_usage_meter_version",
    "billing_usage_currency": "billing_usage_currency",
    "stripe_usage_price": "stripe_usage_price_id",
    "stripe_livemode": "stripe_livemode",
    "billing_customer_receipt_allowed_hosts": "billing_customer_receipt_allowed_hosts",
    "object_store": "evidence_packet_object_store_enabled",
    "shares": "evidence_shares_enabled",
}

# OpenAPI route declarations prove only that code is deployed.  They do not
# prove that feature flags, credentials, persistence, or provider integrations
# are live, nor that any lifecycle was exercised successfully.
ROUTE_CAPABILITIES: Mapping[str, tuple[tuple[str, str], ...]] = {
    "account_lifecycle": (
        ("/accounts/bootstrap", "post"),
        ("/accounts/invite/redeem", "post"),
        ("/accounts/invite", "post"),
        ("/platform/tenants", "post"),
    ),
    "hosted_audit": (
        ("/api/cas-harness/audit/session", "post"),
        ("/api/cas-harness/audit/session/{audit_id}/status", "get"),
        ("/api/cas-harness/audit/session/{audit_id}/run", "post"),
    ),
    "evidence_packet": (
        ("/evidence/{trace_id}", "get"),
        ("/evidence/{trace_id}/verify", "post"),
        ("/evidence/{trace_id}/anchor", "post"),
    ),
    "read_only_shares": (
        ("/evidence/{trace_id}/shares", "post"),
        ("/evidence/shares/{share_id}", "get"),
        ("/evidence/shares/{share_id}", "delete"),
        ("/evidence/shared/{share_id}", "get"),
    ),
    "stripe_billing": (
        ("/billing/plans", "get"),
        ("/billing/entitlement", "get"),
        ("/billing/checkout", "post"),
        ("/billing/portal", "post"),
        ("/billing/webhook/stripe", "post"),
    ),
}


class CollectorError(RuntimeError):
    """The collection boundary or exact source configuration is invalid."""


class ResponseTooLarge(RuntimeError):
    """A response cannot be hashed exactly within the configured bound."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


@dataclass
class SurfaceFetch:
    kind: str
    url: str
    observed_at_utc: str
    http_status: int | None = None
    final_url_matches_requested: bool | None = None
    content_type: str | None = None
    declared_content_length: int | None = None
    byte_length: int | None = None
    raw_content_sha256: str | None = None
    raw: bytes | None = field(default=None, repr=False)
    errors: list[str] = field(default_factory=list)

    def public_record(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "url": self.url,
            "http_status": self.http_status,
            "final_url_matches_requested": self.final_url_matches_requested,
            "content_type": self.content_type,
            "declared_content_length": self.declared_content_length,
            "byte_length": self.byte_length,
            "raw_content_sha256": self.raw_content_sha256,
            "observed_at_utc": self.observed_at_utc,
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class RepositorySnapshot:
    render_sha256: str
    config_sha256: str
    service: Mapping[str, str]
    env: Mapping[str, Mapping[str, Any]]
    source_fields: Mapping[str, bool]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _collector_sha256() -> str:
    try:
        return _sha256(Path(__file__).read_bytes())
    except OSError:
        return "unavailable"


def _normalized_origin(url: str) -> str | None:
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return None
    port_text = f":{port}" if port is not None else ""
    return f"https://{parsed.hostname.lower()}{port_text}"


def validate_surface_url(kind: str, url: str) -> str:
    expected = PINNED_SURFACE_MAP.get(kind)
    if expected is None:
        raise CollectorError(f"unknown surface kind: {kind}")
    if _normalized_origin(url) is None:
        raise CollectorError(
            "surface URL must be credential-free HTTPS without query or fragment"
        )
    if url != expected:
        raise CollectorError(f"surface URL is not the pinned {kind} route")
    return url


def _parse_content_length(headers: Any) -> tuple[int | None, bool]:
    value = headers.get("Content-Length") if headers is not None else None
    if value is None:
        return None, True
    try:
        parsed = int(str(value), 10)
    except (TypeError, ValueError):
        return None, False
    return parsed, parsed >= 0


def _read_response_bounded(response: Any, maximum: int) -> bytes:
    raw = response.read(maximum + 1)
    if not isinstance(raw, bytes):
        raise CollectorError("response body was not bytes")
    if len(raw) > maximum:
        raise ResponseTooLarge("response exceeds byte limit")
    return raw


def fetch_surface(
    kind: str,
    url: str,
    *,
    opener: Any | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    clock: Callable[[], datetime] = _utc_now,
) -> SurfaceFetch:
    validate_surface_url(kind, url)
    if not (0 < timeout_seconds <= MAX_TIMEOUT_SECONDS):
        raise CollectorError("timeout must be greater than zero and at most 30 seconds")
    if not (0 < max_response_bytes <= MAX_RESPONSE_BYTES):
        raise CollectorError("response bound must be between 1 and 4000000 bytes")

    result = SurfaceFetch(kind=kind, url=url, observed_at_utc="")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": "cas-customer-readiness-machine-collector/1",
        },
        method="GET",
    )
    active_opener = opener or urllib.request.build_opener(_NoRedirect)
    response: Any | None = None
    try:
        try:
            response = active_opener.open(request, timeout=timeout_seconds)
        except urllib.error.HTTPError as exc:
            response = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            result.errors.append(f"network_error:{type(exc).__name__}")
            return result

        status_value = getattr(response, "status", getattr(response, "code", None))
        try:
            result.http_status = int(status_value)
        except (TypeError, ValueError):
            result.errors.append("http_status_unavailable")

        final_url = response.geturl() if hasattr(response, "geturl") else None
        result.final_url_matches_requested = final_url == url
        if result.final_url_matches_requested is not True:
            result.errors.append("redirect_or_final_url_mismatch")

        headers = getattr(response, "headers", None)
        content_type = headers.get("Content-Type") if headers is not None else None
        result.content_type = str(content_type).strip() if content_type else None
        if not result.content_type or not result.content_type.lower().startswith(
            "application/json"
        ):
            result.errors.append("content_type_not_json")

        declared_length, valid_length = _parse_content_length(headers)
        result.declared_content_length = declared_length
        if not valid_length:
            result.errors.append("invalid_content_length")
        if declared_length is not None and declared_length > max_response_bytes:
            result.errors.append("response_too_large")
        else:
            try:
                raw = _read_response_bounded(response, max_response_bytes)
            except ResponseTooLarge:
                result.errors.append("response_too_large")
            except CollectorError:
                result.errors.append("response_body_invalid")
            except (TimeoutError, OSError) as exc:
                result.errors.append(f"body_read_error:{type(exc).__name__}")
            else:
                result.raw = raw
                result.byte_length = len(raw)
                result.raw_content_sha256 = _sha256(raw)

        if result.http_status is not None and 300 <= result.http_status <= 399:
            result.errors.append("redirect_response_rejected")
        if result.http_status not in EXPECTED_HTTP_STATUSES[kind]:
            result.errors.append("unexpected_http_status")
        return result
    finally:
        result.observed_at_utc = _format_utc(clock())
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def _strict_json_object(raw: bytes) -> dict[str, Any]:
    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CollectorError("JSON response contains a duplicate key")
            result[key] = value
        return result

    try:
        decoded = raw.decode("utf-8", errors="strict")
        parsed = json.loads(decoded, object_pairs_hook=pairs_hook)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorError("JSON response is invalid") from exc
    if not isinstance(parsed, dict):
        raise CollectorError("JSON response root must be an object")
    return parsed


def _yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_render_public_service(raw: bytes) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    """Parse the narrow Render service contract without a YAML dependency."""

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CollectorError("render.customer.yaml must be UTF-8") from exc
    lines = text.splitlines()
    starts = [
        (index, len(match.group("indent")))
        for index, line in enumerate(lines)
        if (match := re.fullmatch(r"(?P<indent> *)- type: .+", line))
    ]
    candidates: list[tuple[list[str], int]] = []
    for start, service_indent in starts:
        end = len(lines)
        for index in range(start + 1, len(lines)):
            stripped = lines[index].lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(lines[index]) - len(stripped)
            if indent < service_indent or (
                indent == service_indent and stripped.startswith("- ")
            ):
                end = index
                break
        block = lines[start:end]
        field_prefix = " " * (service_indent + 2)
        names = [
            _yaml_scalar(match.group(1))
            for line in block
            if (match := re.fullmatch(rf"{re.escape(field_prefix)}name: (.+)", line))
        ]
        if names == [PUBLIC_SERVICE_NAME]:
            candidates.append((block, service_indent))
    if len(candidates) != 1:
        raise CollectorError(
            "render.customer.yaml must contain exactly one pinned customer service"
        )
    block, service_indent = candidates[0]
    field_prefix = " " * (service_indent + 2)
    env_item_prefix = " " * (service_indent + 4)
    env_value_prefix = " " * (service_indent + 6)
    env_nested_prefix = " " * (service_indent + 8)

    service: dict[str, str] = {"name": PUBLIC_SERVICE_NAME}
    for key, expected in PUBLIC_SERVICE_SCALARS.items():
        values = [
            _yaml_scalar(match.group(1))
            for line in block
            if (
                match := re.fullmatch(
                    rf"{re.escape(field_prefix)}{re.escape(key)}: (.+)", line
                )
            )
        ]
        if values != [expected]:
            raise CollectorError(f"public Render service {key} drifted from its pinned value")
        service[key] = values[0]

    key_lines: list[tuple[int, str]] = []
    for index, line in enumerate(block):
        match = re.fullmatch(
            rf"{re.escape(env_item_prefix)}- key: ([A-Z][A-Z0-9_]*)",
            line,
        )
        if match:
            key_lines.append((index, match.group(1)))
    env: dict[str, dict[str, Any]] = {}
    for offset, (start, key) in enumerate(key_lines):
        if key in env:
            raise CollectorError(f"public Render service contains duplicate env key {key}")
        end = key_lines[offset + 1][0] if offset + 1 < len(key_lines) else len(block)
        item = block[start + 1 : end]
        literal_values = [
            _yaml_scalar(match.group(1))
            for line in item
            if (
                match := re.fullmatch(
                    rf"{re.escape(env_value_prefix)}value: (.+)", line
                )
            )
        ]
        sync_values = [
            _yaml_scalar(match.group(1)).lower()
            for line in item
            if (
                match := re.fullmatch(
                    rf"{re.escape(env_value_prefix)}sync: (.+)", line
                )
            )
        ]
        from_database = any(
            re.fullmatch(
                rf"{re.escape(env_value_prefix)}fromDatabase:\s*", line
            )
            for line in item
        )
        database_names = [
            _yaml_scalar(match.group(1))
            for line in item
            if (
                match := re.fullmatch(
                    rf"{re.escape(env_nested_prefix)}name: (.+)", line
                )
            )
        ]
        database_properties = [
            _yaml_scalar(match.group(1))
            for line in item
            if (
                match := re.fullmatch(
                    rf"{re.escape(env_nested_prefix)}property: (.+)", line
                )
            )
        ]
        if len(literal_values) == 1 and not sync_values:
            env[key] = {"mode": "literal", "repository_value": literal_values[0]}
        elif sync_values == ["false"] and not literal_values:
            env[key] = {
                "mode": "dashboard_managed_slot",
                "repository_value": None,
            }
        elif (
            from_database
            and database_names == [CUSTOMER_DATABASE_NAME]
            and database_properties == ["connectionString"]
            and not literal_values
            and not sync_values
        ):
            env[key] = {
                "mode": "blueprint_database_binding",
                "repository_value": None,
                "database_name": CUSTOMER_DATABASE_NAME,
                "property": "connectionString",
            }
        else:
            # Other Blueprint constructs are irrelevant unless one of the required
            # keys uses them; retaining an opaque mode avoids pretending to parse them.
            env[key] = {"mode": "other", "repository_value": None}

    required_keys = set(FEATURE_ENV_KEYS.values()) | {
        DATABASE_ENV_KEY,
        BILLING_PROVIDER_ENV_KEY,
    }
    missing = sorted(required_keys - env.keys())
    if missing:
        raise CollectorError("public Render service is missing required readiness env keys")
    return service, env


def parse_source_configuration_fields(raw: bytes) -> dict[str, bool]:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CollectorError("api/config.py must be UTF-8") from exc
    fields: dict[str, bool] = {}
    for capability, identifier in SOURCE_CONFIG_FIELDS.items():
        matches = re.findall(rf"^    {re.escape(identifier)}\s*:", text, flags=re.MULTILINE)
        if len(matches) != 1:
            raise CollectorError(
                f"api/config.py must declare {identifier} exactly once"
            )
        fields[capability] = True
    return fields


def load_repository_snapshot(repository_root: Path) -> RepositorySnapshot:
    root = repository_root.resolve()
    try:
        render_raw = (root / RENDER_PATH).read_bytes()
        config_raw = (root / CONFIG_PATH).read_bytes()
    except OSError as exc:
        raise CollectorError("required repository source file is unavailable") from exc
    service, env = parse_render_public_service(render_raw)
    source_fields = parse_source_configuration_fields(config_raw)
    return RepositorySnapshot(
        render_sha256=_sha256(render_raw),
        config_sha256=_sha256(config_raw),
        service=service,
        env=env,
        source_fields=source_fields,
    )


def _literal_bool(snapshot: RepositorySnapshot, key: str) -> bool:
    declaration = snapshot.env[key]
    value = declaration.get("repository_value")
    if declaration.get("mode") != "literal" or value not in {"true", "false"}:
        raise CollectorError(f"{key} must be an exact literal true or false")
    return value == "true"


def _parse_fetched_document(fetch: SurfaceFetch) -> tuple[dict[str, Any] | None, str | None]:
    if fetch.raw is None:
        return None, "response_bytes_unavailable"
    try:
        return _strict_json_object(fetch.raw), None
    except CollectorError:
        return None, "invalid_json_object"


def _extract_route_capabilities(
    openapi: Mapping[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    paths = openapi.get("paths") if isinstance(openapi, Mapping) else None
    path_map = paths if isinstance(paths, Mapping) else {}
    result: dict[str, list[dict[str, Any]]] = {}
    for capability, requirements in ROUTE_CAPABILITIES.items():
        records: list[dict[str, Any]] = []
        for path, method in requirements:
            path_item = path_map.get(path)
            declared = isinstance(path_item, Mapping) and isinstance(
                path_item.get(method), Mapping
            )
            records.append(
                {"path": path, "method": method.upper(), "route_declared": declared}
            )
        result[capability] = records
    return result


def _database_observation(readiness: Mapping[str, Any] | None) -> dict[str, Any]:
    checks = readiness.get("checks") if isinstance(readiness, Mapping) else None
    database = checks.get("database") if isinstance(checks, Mapping) else None
    status = database.get("status") if isinstance(database, Mapping) else None
    if status == "not_configured":
        return {
            "database_status": status,
            "database_configured": False,
            "database_reachable": False,
            "postgres_confirmed": False,
        }
    if status == "ok":
        return {
            "database_status": status,
            "database_configured": True,
            "database_reachable": True,
            "postgres_confirmed": None,
        }
    if status == "error":
        return {
            "database_status": status,
            "database_configured": True,
            "database_reachable": False,
            "postgres_confirmed": None,
        }
    return {
        "database_status": "unavailable",
        "database_configured": None,
        "database_reachable": None,
        "postgres_confirmed": None,
    }


def _feature_fact(
    snapshot: RepositorySnapshot,
    feature: str,
) -> dict[str, Any]:
    key = FEATURE_ENV_KEYS[feature]
    return {
        "repository_env_key": key,
        "repository_declared_enabled": _literal_bool(snapshot, key),
        "public_runtime_live_enablement": None,
        "public_runtime_observation_basis": (
            "unavailable_on_credential_free_public_status_surfaces"
        ),
    }


def collect_customer_readiness_report(
    *,
    repository_root: Path | None = None,
    fetcher: Callable[[str, str], SurfaceFetch] | None = None,
    clock: Callable[[], datetime] = _utc_now,
    opener: Any | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> dict[str, Any]:
    root = repository_root or Path(__file__).resolve().parents[1]
    snapshot = load_repository_snapshot(root)
    provider = snapshot.env[BILLING_PROVIDER_ENV_KEY]
    if provider.get("mode") != "literal" or not isinstance(
        provider.get("repository_value"), str
    ):
        raise CollectorError("NC_BILLING_PROVIDER must be an exact literal")
    database_declaration = snapshot.env[DATABASE_ENV_KEY]
    if (
        database_declaration.get("mode") != "blueprint_database_binding"
        or database_declaration.get("database_name") != CUSTOMER_DATABASE_NAME
        or database_declaration.get("property") != "connectionString"
    ):
        raise CollectorError(
            "NC_DATABASE_URL must bind the dedicated customer Blueprint database"
        )
    declared_stripe_slots = [key for key in STRIPE_SLOT_KEYS if key in snapshot.env]
    provider_value = str(provider["repository_value"]).lower()
    if provider_value == "null":
        if declared_stripe_slots:
            raise CollectorError(
                "Stripe provider slots must be absent while NC_BILLING_PROVIDER is null"
            )
    elif provider_value == "stripe":
        if declared_stripe_slots != list(STRIPE_SLOT_KEYS) or any(
            snapshot.env[key].get("mode") != "dashboard_managed_slot"
            for key in STRIPE_SLOT_KEYS
        ):
            raise CollectorError(
                "Stripe provider mode requires every dashboard-managed source slot"
            )

    if fetcher is None:
        active_opener = opener or urllib.request.build_opener(_NoRedirect)

        def fetcher(kind: str, url: str) -> SurfaceFetch:
            return fetch_surface(
                kind,
                url,
                opener=active_opener,
                timeout_seconds=timeout_seconds,
                max_response_bytes=max_response_bytes,
                clock=clock,
            )

    fetches = [fetcher(kind, url) for kind, url in PINNED_SURFACES]
    documents: dict[str, dict[str, Any] | None] = {}
    parse_errors: dict[str, str] = {}
    for fetch in fetches:
        document, error = _parse_fetched_document(fetch)
        documents[fetch.kind] = document
        if error is not None:
            parse_errors[fetch.kind] = error

    route_capabilities = _extract_route_capabilities(documents.get("openapi"))
    database = _database_observation(documents.get("readiness"))
    health = documents.get("health")
    readiness = documents.get("readiness")
    api_liveness = (
        fetches[0].http_status == 200
        and isinstance(health, Mapping)
        and health.get("status") == "ok"
    )
    readiness_ready = (
        readiness.get("ready") if isinstance(readiness, Mapping) else None
    )
    if not isinstance(readiness_ready, bool):
        readiness_ready = None

    configured_vs_observed: dict[str, Any] = {
        "postgres": {
            "repository_env_key": DATABASE_ENV_KEY,
            "repository_value_mode": "blueprint_database_binding",
            "repository_value_available": False,
            "repository_database_name": CUSTOMER_DATABASE_NAME,
            "repository_database_property": "connectionString",
            **database,
            "observation_basis": "sanitized_public_health_ready_database_check",
        },
        "accounts": _feature_fact(snapshot, "accounts"),
        "quotas": _feature_fact(snapshot, "quotas"),
        "object_store": _feature_fact(snapshot, "object_store"),
        "shares": _feature_fact(snapshot, "shares"),
        "billing_entitlements": _feature_fact(snapshot, "billing_entitlements"),
        "billing_reconciliation": _feature_fact(snapshot, "billing_reconciliation"),
        "stripe": {
            "repository_provider_env_key": BILLING_PROVIDER_ENV_KEY,
            "repository_provider_value": provider["repository_value"],
            "repository_dashboard_managed_slots": declared_stripe_slots,
            "repository_slot_posture": (
                "absent_while_provider_null"
                if provider_value == "null"
                else "declared_for_stripe_provider"
            ),
            "repository_slot_values_available": False,
            "public_runtime_live_enablement": None,
            "public_runtime_observation_basis": (
                "unavailable_on_credential_free_public_status_surfaces"
            ),
        },
    }

    blockers: list[str] = [
        "authority:unsigned_machine_draft",
        "hosted_customer_journey:tenant_audit_packet_worm_share_and_isolation_lifecycle_not_collected",
        "accounts_billing:account_lifecycle_quota_and_idempotency_not_collected",
        "accounts_billing:live_stripe_subscription_invoice_webhook_and_meter_reconciliation_not_collected",
    ]
    for fetch in fetches:
        blockers.extend(f"surface:{fetch.kind}:{error}" for error in fetch.errors)
    blockers.extend(
        f"surface:{kind}:{error}" for kind, error in parse_errors.items()
    )

    if database["database_status"] == "not_configured":
        blockers.append("public_production:postgres:not_configured")
    elif database["database_status"] == "error":
        blockers.extend(
            (
                "public_production:database:unreachable",
                "public_production:postgres:provider_unconfirmed",
            )
        )
    elif database["database_status"] == "ok":
        blockers.append("public_production:postgres:provider_unconfirmed")
    else:
        blockers.append("public_production:postgres:status_unavailable")

    for feature in FEATURE_ENV_KEYS:
        if not configured_vs_observed[feature]["repository_declared_enabled"]:
            blockers.append(f"repository_configuration:{feature}:disabled")
        blockers.append(
            f"public_production:{feature}:live_enablement_unavailable_on_credential_free_surfaces"
        )
    if str(provider["repository_value"]).lower() != "stripe":
        blockers.append("repository_configuration:stripe:provider_is_not_stripe")
    blockers.append(
        "public_production:stripe:live_configuration_unavailable_on_credential_free_surfaces"
    )
    for capability, records in route_capabilities.items():
        if not all(record["route_declared"] for record in records):
            blockers.append(f"source_capability:{capability}:route_unavailable")

    collection_complete = not parse_errors and all(not fetch.errors for fetch in fetches)
    public_prerequisites_established = bool(
        collection_complete
        and api_liveness is True
        and readiness_ready is True
        and database["postgres_confirmed"] is True
        and all(
            configured_vs_observed[feature]["repository_declared_enabled"] is True
            and configured_vs_observed[feature]["public_runtime_live_enablement"]
            is True
            for feature in FEATURE_ENV_KEYS
        )
        and str(provider["repository_value"]).lower() == "stripe"
        and configured_vs_observed["stripe"]["public_runtime_live_enablement"]
        is True
        and all(
            record["route_declared"] is True
            for records in route_capabilities.values()
            for record in records
        )
    )
    generated_at = _format_utc(clock())
    draft_payload: dict[str, Any] = {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "environment": "public-production",
        "gate_statuses": {
            "hosted_customer_journey": "OPEN",
            "accounts_billing": "OPEN",
        },
        "draft_only": True,
        "authoritative": False,
        "eligible_for_acceptance": False,
        "generated_at_utc": generated_at,
        "collection_boundary": {
            "collector_sha256": _collector_sha256(),
            "request_method": "GET",
            "redirects_allowed": False,
            "maximum_response_bytes": max_response_bytes,
            "credentials_sent": False,
            "mutation_requests_sent": False,
            "accounts_created": False,
            "audits_created": False,
            "shares_created_or_fetched": False,
            "checkouts_or_portal_sessions_created": False,
            "provider_events_created_or_fabricated": False,
            "authority_records_created": False,
        },
        "public_surfaces": [fetch.public_record() for fetch in fetches],
        "public_runtime": {
            "api_liveness_observed": api_liveness,
            "readiness_ready": readiness_ready,
            **database,
        },
        "repository_sources": [
            {"path": RENDER_PATH.as_posix(), "sha256": snapshot.render_sha256},
            {"path": CONFIG_PATH.as_posix(), "sha256": snapshot.config_sha256},
        ],
        "public_service_configuration": dict(snapshot.service),
        "configured_vs_observed": configured_vs_observed,
        "source_capability": {
            "source_capability_does_not_establish_live_enablement": True,
            "configuration_fields_declared": dict(snapshot.source_fields),
            "deployed_openapi_routes": route_capabilities,
        },
        "collection_complete": collection_complete,
        "public_prerequisites_established": public_prerequisites_established,
    }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "draft_payload": draft_payload,
        "blockers": sorted(set(blockers)),
    }


def _write_report(report: Mapping[str, Any], output: Path | None, pretty: bool) -> None:
    serialized = json.dumps(
        report,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        sort_keys=True,
    )
    if output is None:
        print(serialized)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(serialized + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write JSON here instead of stdout")
    parser.add_argument("--pretty", action="store_true", help="pretty-print the JSON")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="per-request timeout, greater than zero and at most 30",
    )
    parser.add_argument(
        "--max-response-bytes",
        type=int,
        default=DEFAULT_MAX_RESPONSE_BYTES,
        help="per-response bound, greater than zero and at most 4000000",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = collect_customer_readiness_report(
            timeout_seconds=args.timeout_seconds,
            max_response_bytes=args.max_response_bytes,
        )
        _write_report(report, args.output, args.pretty)
    except (CollectorError, OSError) as exc:
        print(f"customer-readiness collector failed: {type(exc).__name__}", file=sys.stderr)
        return 2
    return 0 if report["draft_payload"]["public_prerequisites_established"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
