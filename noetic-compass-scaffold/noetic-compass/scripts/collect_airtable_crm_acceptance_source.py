#!/usr/bin/env python3
"""Collect a secret-safe Airtable CRM source receipt from public production.

Run this command from the Render production shell. It submits one synthetic
public lead through the real public endpoint, then reopens the durable lead
ledger and requires the Airtable adapter's strict upsert/direct-read/list-read
receipt. Output contains only hashes and non-PII facts.

This is deliberately a *source* collector, not a ``support_crm`` authority
publisher. The emitted acceptance fragment stays ``OPEN`` because the separate
resolved support-ticket/SLA proof is absent.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

# Render Shell may execute this copied file directly, which otherwise puts only
# ``/app/scripts`` on ``sys.path`` instead of the trusted application root.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.services.crm import (
    CRM_CONSENT_SCHEMA_VERSION,
    CRM_CURRENT_OPEN_DRAFT_CONTENT_SHA256,
    CRM_PRIVACY_NOTICE_PRESENT_STATUS,
    CRM_PRIVACY_NOTICE_URL,
    CRM_SCHEMA_VERSION,
    CRMPrivacyNoticeConfigError,
    CRMPrivacyNoticeContract,
    CRMVerificationReceipt,
    Lead,
)
from api.services.crm.state_store import (
    CRM_LEAD_JSONL_MIGRATION_ID,
    StateStoreLeadStore,
)
from api.services.customer_production_pseudonyms import (
    AIRTABLE_RECORD_DOMAIN,
    CRM_LEAD_DOMAIN,
    SUBJECT_PATTERN,
    SUPPORT_CRM_REQUEST_TRACE_DOMAIN,
    CustomerProductionPseudonymizer,
    parse_customer_production_pseudonym_keyring,
    validate_public_pseudonym_metadata,
)
from api.services.production.state_substrate import StateStore
from api.services.revisioned_contact_store import (
    CONTACT_MIGRATION_KIND,
    CONTACT_MIGRATION_SCHEMA_VERSION,
    CONTACT_STATE_TENANT,
)


SOURCE_SCHEMA_VERSION = "cas_harness_airtable_crm_acceptance_source.v3"
FRAGMENT_SCHEMA_VERSION = "cas_harness_support_crm_acceptance_fragment.v3"
PRIVATE_LEAD_SELECTOR_SCHEMA_VERSION = (
    "cas_harness_support_crm_lead_selector.v1"
)
REPOSITORY = "LittleHenderson/noetic-compass"
REPOSITORY_URL = "https://github.com/LittleHenderson/noetic-compass"
PRODUCTION_API_ORIGIN = "https://api.noeticcompass.com"
PRODUCTION_SERVICE_ID = "i-0bd0a082507a51ae3"
PRODUCTION_SERVICE_NAME = "cas-harness-customer-api"
RENDER_API_ORIGIN = "https://api.render.com"
PUBLIC_LEAD_PATH = "/api/crm/public/leads"
CANONICAL_AIRTABLE_API_BASE_URL = "https://api.airtable.com/v0"
PRODUCTION_AIRTABLE_BASE_ID = "appXBoYskbfjNaFTs"
PRODUCTION_AIRTABLE_TABLE_NAME = "Leads"
PRODUCTION_AIRTABLE_DEDUP_FIELD = "Dedup Key"
PRODUCTION_AIRTABLE_OWNER_FIELD = "Owner"
PRODUCTION_AIRTABLE_OWNER_VALUE = "CAS Harness"
PRODUCTION_AIRTABLE_LIFECYCLE_FIELD = "Pipeline Status"
PRODUCTION_DISK_ID = "vol-056e0897eb5b72c4c"
PRODUCTION_DISK_NAME = "customer-support"
PRODUCTION_DISK_MOUNT_PATH = "/var/customer-support"
PRODUCTION_LEAD_STORE_PATH = "/var/customer-support/leads.jsonl"
AIRTABLE_CONSENT_FIELD_CONTRACT = {
    "consent_to_contact_field": "Consent to Contact",
    "consent_recorded_at_field": "Consent Recorded At UTC",
    "consent_schema_version_field": "Consent Schema Version",
    "privacy_notice_url_field": "Privacy Notice URL",
    "privacy_notice_version_field": "Privacy Notice Version",
    "privacy_notice_content_sha256_field": "Privacy Notice Content SHA-256",
    "privacy_notice_publication_status_field": "Privacy Notice Publication Status",
}
MAX_RESPONSE_BYTES = 1_000_000
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TAGGED_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
DEPLOY_ID_RE = re.compile(r"^dep-[A-Za-z0-9]+$")
LEAD_ID_RE = re.compile(r"^lead-[0-9a-f]{16}$")
AIRTABLE_RECORD_ID_RE = re.compile(r"^rec[A-Za-z0-9]{14,125}$")
PUBLIC_RESPONSE_KEYS = frozenset(
    {
        "lead_id",
        "captured",
        "sync_status",
        "synced",
        "schema_version",
        "consent_to_contact",
        "privacy_notice_url",
        "privacy_notice_version",
        "privacy_notice_content_sha256",
        "privacy_notice_publication_status",
        "consent_recorded_at_utc",
        "consent_schema_version",
        "message",
    }
)
SOURCE_RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "environment",
        "repository",
        "master_head_sha",
        "deploy_id",
        "service_id",
        "render_service_name",
        "render_repository",
        "render_branch",
        "render_auto_deploy_trigger",
        "render_service_response_sha256",
        "render_deploy_status",
        "render_deploy_commit_sha",
        "render_deploy_trigger",
        "render_deploy_finished_at_utc",
        "render_deploy_response_sha256",
        "pseudonymization_scheme",
        "pseudonym_key_id",
        "lead_subject",
        "airtable_record_subject",
        "lead_store_backend",
        "state_store_backend",
        "state_store_read_authority",
        "lead_migration_marker_verified",
        "lead_head_revision_verified",
        "provider",
        "airtable_api_base",
        "airtable_base_id",
        "airtable_table_name",
        "airtable_dedup_field",
        "airtable_owner_field",
        "airtable_owner_value",
        "airtable_lifecycle_field",
        "airtable_consent_to_contact_field",
        "airtable_consent_recorded_at_field",
        "airtable_consent_schema_version_field",
        "airtable_privacy_notice_url_field",
        "airtable_privacy_notice_version_field",
        "airtable_privacy_notice_content_sha256_field",
        "airtable_privacy_notice_publication_status_field",
        "airtable_contract_sha256",
        "privacy_notice_publication_status",
        "privacy_notice_url",
        "privacy_notice_version",
        "privacy_notice_content_sha256",
        "privacy_notice_http_status",
        "privacy_notice_content_type",
        "privacy_notice_verified_at_utc",
        "capture_http_status",
        "trace_subject",
        "adapter_response_digest",
        "lead_schema_version",
        "lead_record_version",
        "persisted",
        "readback_verified",
        "deduplicated",
        "owner_assigned",
        "lifecycle_stage",
        "verified_at_utc",
        "consent_to_contact",
        "consent_schema_version",
        "consent_recorded_at_utc",
        "source_attribution_recorded",
        "observed_at_utc",
    }
)


class CRMCollectionFailure(RuntimeError):
    """One named, secret-safe collector invariant failed."""

    def __init__(self, gate: str, detail: str) -> None:
        self.gate = gate
        super().__init__(f"{gate}: {detail}")


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: Mapping[str, str]
    body: bytes


Transport = Callable[..., HttpResult]
LeadReader = Callable[[str, str], Lead | None]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CRMCollectionFailure("json", "response contains a duplicate JSON key")
        value[key] = item
    return value


def _reject_nonfinite(value: str) -> Any:
    raise CRMCollectionFailure("json", f"response contains forbidden number {value}")


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _decode_object(result: HttpResult, gate: str) -> Mapping[str, Any]:
    if len(result.body) > MAX_RESPONSE_BYTES:
        raise CRMCollectionFailure(gate, "response exceeds the bounded size limit")
    try:
        parsed = json.loads(
            result.body.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except CRMCollectionFailure:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise CRMCollectionFailure(gate, "response is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise CRMCollectionFailure(gate, "response JSON root is not an object")
    return parsed


def _parse_timestamp(value: object, gate: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise CRMCollectionFailure(gate, "timestamp is missing")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise CRMCollectionFailure(
            gate, "timestamp must be canonical whole-second UTC"
        ) from exc
    return parsed


def _parse_provider_timestamp(value: object, gate: str) -> datetime:
    """Parse a provider RFC3339 timestamp while preserving a UTC comparison."""

    if not isinstance(value, str) or not value.endswith("Z"):
        raise CRMCollectionFailure(gate, "provider timestamp is missing or non-UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CRMCollectionFailure(gate, "provider timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise CRMCollectionFailure(gate, "provider timestamp has no timezone")
    return parsed.astimezone(UTC)


def _stamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise CRMCollectionFailure("clock", "collector clock has no timezone")
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


class _NoRedirect(HTTPRedirectHandler):
    """Reject redirects so request data cannot be replayed to another origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _default_transport(
    *,
    base_url: str,
    path: str,
    method: str,
    payload: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float,
) -> HttpResult:
    body = None if payload is None else _canonical_bytes(payload)
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "CAS-Harness-Airtable-CRM-Acceptance/2.0",
        **dict(headers or {}),
    }
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=request_headers,
        method=method,
    )
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310 - pinned origin
            final = urlparse(str(response.geturl()))
            expected = urlparse(base_url)
            if (
                final.scheme != "https"
                or final.username is not None
                or final.password is not None
                or final.netloc != expected.netloc
                or final.path != path
                or final.query
                or final.fragment
            ):
                raise CRMCollectionFailure("redirect", "response URL drifted from production")
            return HttpResult(
                status=int(response.status),
                headers={key.lower(): value for key, value in response.headers.items()},
                body=response.read(MAX_RESPONSE_BYTES + 1),
            )
    except HTTPError as exc:
        return HttpResult(
            status=int(exc.code),
            headers={key.lower(): value for key, value in exc.headers.items()},
            body=exc.read(MAX_RESPONSE_BYTES + 1),
        )
    except (URLError, OSError, TimeoutError) as exc:
        raise CRMCollectionFailure("network", "public CRM request failed") from exc


def _verified_state_store_lead_reader(store: StateStore) -> LeadReader:
    """Build a reader that proves the migration marker plus head/revision path."""

    leads = StateStoreLeadStore(store)

    def read(_migration_path: str, lead_id: str) -> Lead | None:
        marker = store.get(
            CONTACT_STATE_TENANT,
            CONTACT_MIGRATION_KIND,
            CRM_LEAD_JSONL_MIGRATION_ID,
        )
        payload = None if marker is None else marker.payload
        if (
            marker is None
            or marker.version != 1
            or marker.tenant_id != CONTACT_STATE_TENANT
            or marker.kind != CONTACT_MIGRATION_KIND
            or marker.record_id != CRM_LEAD_JSONL_MIGRATION_ID
            or marker.source != "contact_jsonl_migration"
            or marker.trace_id is not None
            or not isinstance(payload, Mapping)
            or payload.get("schema_version")
            != CONTACT_MIGRATION_SCHEMA_VERSION
            or payload.get("domain") != "crm_lead"
            or type(payload.get("source_present")) is not bool
            or any(
                type(payload.get(field)) is not int
                or int(payload.get(field, -1)) < 0
                for field in (
                    "line_count",
                    "revision_count",
                    "head_count",
                )
            )
            or any(
                SHA256_RE.fullmatch(str(payload.get(field) or "")) is None
                for field in ("source_sha256", "records_sha256")
            )
        ):
            raise CRMCollectionFailure(
                "persistence", "CRM migration marker is absent or invalid"
            )
        lead = leads.get(lead_id)
        if lead is None:
            return None
        revisions = [
            item for item in leads.list_revisions(lead_id) if item.version == lead.version
        ]
        if len(revisions) != 1 or revisions[0].to_dict() != lead.to_dict():
            raise CRMCollectionFailure(
                "persistence", "CRM head and immutable revision diverged"
            )
        return lead

    return read


class AirtableCRMSourceCollector:
    def __init__(
        self,
        *,
        base_url: str,
        master_head_sha: str,
        deploy_id: str,
        runtime_environment: Mapping[str, str] = os.environ,
        transport: Transport = _default_transport,
        lead_reader: LeadReader,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        nonce: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.master_head_sha = master_head_sha
        self.deploy_id = deploy_id
        self.runtime_environment = runtime_environment
        self.transport = transport
        self.lead_reader = lead_reader
        self.clock = clock
        self.nonce = nonce or secrets.token_hex(12)
        self.lead_store_path = ""
        self.render_api_key = ""
        self.pseudonymizer: CustomerProductionPseudonymizer
        self.privacy_notice_contract: CRMPrivacyNoticeContract
        self.airtable_contract: dict[str, str]
        self._validate_binding()

    def _now(self) -> datetime:
        value = self.clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise CRMCollectionFailure("clock", "collector clock is not timezone aware")
        return value.astimezone(UTC)

    def _validate_binding(self) -> None:
        parsed = urlparse(self.base_url)
        expected = urlparse(PRODUCTION_API_ORIGIN)
        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.netloc != expected.netloc
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise CRMCollectionFailure(
                "binding", "API origin is not the pinned public production origin"
            )
        if SHA1_RE.fullmatch(self.master_head_sha) is None:
            raise CRMCollectionFailure("binding", "master HEAD is invalid")
        if DEPLOY_ID_RE.fullmatch(self.deploy_id) is None:
            raise CRMCollectionFailure("binding", "deploy ID is invalid")
        if re.fullmatch(r"[0-9a-f]{24}", self.nonce) is None:
            raise CRMCollectionFailure("binding", "run nonce is invalid")
        env = self.runtime_environment
        if env.get("RENDER_SERVICE_ID") != PRODUCTION_SERVICE_ID:
            raise CRMCollectionFailure(
                "binding", "collector is not running in the pinned production service"
            )
        if env.get("RENDER_GIT_COMMIT") != self.master_head_sha:
            raise CRMCollectionFailure(
                "binding", "runtime commit does not match the supplied master HEAD"
            )
        if env.get("NC_CRM_PROVIDER", "").strip().lower() != "airtable":
            raise CRMCollectionFailure("provider", "NC_CRM_PROVIDER is not exact airtable")
        if not env.get("NC_AIRTABLE_TOKEN", "").strip():
            raise CRMCollectionFailure("provider", "Airtable provider token is absent")
        exact_provider_contract = {
            "api_base_url": CANONICAL_AIRTABLE_API_BASE_URL,
            "base_id": PRODUCTION_AIRTABLE_BASE_ID,
            "table_name": PRODUCTION_AIRTABLE_TABLE_NAME,
            "dedup_field": PRODUCTION_AIRTABLE_DEDUP_FIELD,
            "owner_field": PRODUCTION_AIRTABLE_OWNER_FIELD,
            "owner_value": PRODUCTION_AIRTABLE_OWNER_VALUE,
            "lifecycle_field": PRODUCTION_AIRTABLE_LIFECYCLE_FIELD,
        }
        environment_names = {
            "api_base_url": "NC_AIRTABLE_API_BASE_URL",
            "base_id": "NC_AIRTABLE_BASE_ID",
            "table_name": "NC_AIRTABLE_TABLE_NAME",
            "dedup_field": "NC_AIRTABLE_DEDUP_FIELD",
            "owner_field": "NC_AIRTABLE_OWNER_FIELD",
            "owner_value": "NC_AIRTABLE_OWNER_VALUE",
            "lifecycle_field": "NC_AIRTABLE_LIFECYCLE_FIELD",
        }
        for key, expected_value in exact_provider_contract.items():
            actual = env.get(environment_names[key], "").strip()
            if key == "api_base_url":
                actual = actual.rstrip("/")
            if actual != expected_value:
                raise CRMCollectionFailure(
                    "provider",
                    f"{environment_names[key]} does not match the exact production contract",
                )
        self.airtable_contract = {
            **exact_provider_contract,
            **AIRTABLE_CONSENT_FIELD_CONTRACT,
        }
        self.lead_store_path = env.get("NC_CRM_LEAD_STORE_PATH", "").strip()
        if env.get("NC_CRM_LEAD_STORE_BACKEND", "").strip().lower() != "state_store":
            raise CRMCollectionFailure(
                "persistence",
                "NC_CRM_LEAD_STORE_BACKEND must be exact state_store",
            )
        if env.get("NC_STATE_LEDGER_ENABLED", "").strip().lower() != "true":
            raise CRMCollectionFailure(
                "persistence", "NC_STATE_LEDGER_ENABLED must be exact true"
            )
        if env.get("NC_STATE_LEDGER_READ_AUTHORITY", "").strip().lower() != "true":
            raise CRMCollectionFailure(
                "persistence", "NC_STATE_LEDGER_READ_AUTHORITY must be exact true"
            )
        database_url = env.get("NC_DATABASE_URL", "").strip().lower()
        if not database_url.startswith(("postgres://", "postgresql://")):
            raise CRMCollectionFailure(
                "persistence", "CRM read authority requires shared Postgres"
            )
        try:
            active_key_id = env.get(
                "NC_CUSTOMER_PRODUCTION_PSEUDONYM_ACTIVE_KEY_ID", ""
            )
            self.pseudonymizer = CustomerProductionPseudonymizer(
                parse_customer_production_pseudonym_keyring(
                    env.get("NC_CUSTOMER_PRODUCTION_PSEUDONYM_KEYRING_JSON", ""),
                    active_key_id=active_key_id,
                ),
                active_key_id=active_key_id,
            )
        except (TypeError, ValueError) as exc:
            raise CRMCollectionFailure(
                "pseudonymization",
                "customer-production pseudonym keyring is unavailable",
            ) from exc
        self.render_api_key = env.get("RENDER_API_KEY", "").strip()
        if not self.render_api_key:
            raise CRMCollectionFailure(
                "render-deploy", "RENDER_API_KEY is required for exact live deploy proof"
            )
        try:
            self.privacy_notice_contract = CRMPrivacyNoticeContract(
                publication_status=env.get(
                    "NC_CRM_PRIVACY_NOTICE_PUBLICATION_STATUS", ""
                ),
                version=env.get("NC_CRM_PRIVACY_NOTICE_VERSION", ""),
                content_sha256=env.get(
                    "NC_CRM_PRIVACY_NOTICE_CONTENT_SHA256", ""
                ),
            ).validated()
        except CRMPrivacyNoticeConfigError as exc:
            raise CRMCollectionFailure("privacy-publication", str(exc)) from exc
        self._now()

    @staticmethod
    def _json_response(result: HttpResult, gate: str) -> Mapping[str, Any]:
        if result.status != 200:
            raise CRMCollectionFailure(gate, f"provider returned HTTP {result.status}")
        content_type = str(result.headers.get("content-type", "")).split(";", 1)[0]
        if content_type.strip().lower() != "application/json":
            raise CRMCollectionFailure(gate, "provider response is not application/json")
        return _decode_object(result, gate)

    def _collect_render_facts(self) -> dict[str, object]:
        headers = {
            "Authorization": f"Bearer {self.render_api_key}",
            "Accept": "application/json",
        }
        service_result = self.transport(
            base_url=RENDER_API_ORIGIN,
            path=f"/v1/services/{PRODUCTION_SERVICE_ID}",
            method="GET",
            headers=headers,
            timeout=30.0,
        )
        service = self._json_response(service_result, "render-service")
        exact_service = {
            "id": PRODUCTION_SERVICE_ID,
            "name": PRODUCTION_SERVICE_NAME,
            "type": "web_service",
            "repo": REPOSITORY_URL,
            "branch": "master",
            "autoDeployTrigger": "checksPass",
        }
        if any(service.get(key) != value for key, value in exact_service.items()):
            raise CRMCollectionFailure(
                "render-service", "production Render service contract drifted"
            )
        details = service.get("serviceDetails")
        disk = details.get("disk") if isinstance(details, Mapping) else None
        if not isinstance(disk, Mapping):
            raise CRMCollectionFailure("persistence", "Render persistent disk is absent")
        if (
            disk.get("id") != PRODUCTION_DISK_ID
            or disk.get("name") != PRODUCTION_DISK_NAME
            or disk.get("mountPath") != PRODUCTION_DISK_MOUNT_PATH
            or type(disk.get("sizeGB")) is not int
            or int(disk["sizeGB"]) < 1
        ):
            raise CRMCollectionFailure(
                "persistence", "Render persistent-disk contract drifted"
            )

        deploy_result = self.transport(
            base_url=RENDER_API_ORIGIN,
            path=(
                f"/v1/services/{PRODUCTION_SERVICE_ID}/deploys/{self.deploy_id}"
            ),
            method="GET",
            headers=headers,
            timeout=30.0,
        )
        deploy = self._json_response(deploy_result, "render-deploy")
        commit = deploy.get("commit")
        if (
            deploy.get("id") != self.deploy_id
            or deploy.get("status") != "live"
            or not isinstance(commit, Mapping)
            or commit.get("id") != self.master_head_sha
        ):
            raise CRMCollectionFailure(
                "render-deploy",
                "supplied deploy is not the live production deploy at the exact commit",
            )
        trigger = deploy.get("trigger")
        if not isinstance(trigger, str) or not trigger.strip() or len(trigger) > 80:
            raise CRMCollectionFailure("render-deploy", "Render deploy trigger is invalid")
        finished = _parse_provider_timestamp(deploy.get("finishedAt"), "render-deploy")
        if finished > self._now():
            raise CRMCollectionFailure("render-deploy", "Render deploy finished in the future")
        return {
            "render_service_name": PRODUCTION_SERVICE_NAME,
            "render_repository": REPOSITORY_URL,
            "render_branch": "master",
            "render_auto_deploy_trigger": "checksPass",
            "render_service_response_sha256": _digest_bytes(service_result.body),
            "render_deploy_status": "live",
            "render_deploy_commit_sha": self.master_head_sha,
            "render_deploy_trigger": trigger,
            "render_deploy_finished_at_utc": _stamp(finished),
            "render_deploy_response_sha256": _digest_bytes(deploy_result.body),
        }

    def _collect_privacy_notice_facts(self) -> dict[str, object]:
        result = self.transport(
            base_url="https://cascompass.ai",
            path="/privacy",
            method="GET",
            headers={"Accept": "text/html"},
            timeout=30.0,
        )
        if result.status != 200:
            raise CRMCollectionFailure(
                "privacy-publication",
                f"privacy notice returned HTTP {result.status}",
            )
        content_type = str(result.headers.get("content-type", "")).split(";", 1)[0]
        if content_type.strip().lower() != "text/html":
            raise CRMCollectionFailure(
                "privacy-publication", "privacy notice is not text/html"
            )
        digest = _digest_bytes(result.body)
        notice = self.privacy_notice_contract
        if digest != notice.content_sha256:
            raise CRMCollectionFailure(
                "privacy-publication",
                "live privacy notice bytes do not match the server-owned content digest",
            )
        if not notice.permits_contact_capture:
            raise CRMCollectionFailure(
                "privacy-publication",
                f"live privacy notice publication remains {notice.publication_status}",
            )
        lowered = result.body.lower()
        if (
            digest == CRM_CURRENT_OPEN_DRAFT_CONTENT_SHA256
            or b"privacy publication status: open" in lowered
            or b"flag_for_human_review" in lowered
            or b"draft notice" in lowered
        ):
            raise CRMCollectionFailure(
                "privacy-publication",
                "live privacy notice still contains the exact OPEN/draft markers",
            )
        return {
            "privacy_notice_publication_status": notice.publication_status,
            "privacy_notice_url": notice.url,
            "privacy_notice_version": notice.version,
            "privacy_notice_content_sha256": notice.content_sha256,
            "privacy_notice_http_status": result.status,
            "privacy_notice_content_type": "text/html",
            "privacy_notice_verified_at_utc": _stamp(self._now()),
        }

    def _post_public_lead(self, payload: Mapping[str, Any]) -> HttpResult:
        result = self.transport(
            base_url=self.base_url,
            path=PUBLIC_LEAD_PATH,
            method="POST",
            payload=payload,
            timeout=60.0,
        )
        if len(result.body) > MAX_RESPONSE_BYTES:
            raise CRMCollectionFailure("public-lead", "response exceeds the bounded size limit")
        return result

    @staticmethod
    def _require_receipt(lead: Lead) -> CRMVerificationReceipt:
        receipt = lead.verification_receipt
        if receipt is None:
            raise CRMCollectionFailure("airtable-readback", "verification receipt is absent")
        if (
            receipt.provider != "airtable"
            or receipt.readback_verified is not True
            or receipt.deduplicated is not True
            or receipt.owner_assigned is not True
            or receipt.lifecycle_stage != lead.pipeline_status
            or TAGGED_SHA256_RE.fullmatch(receipt.response_digest) is None
        ):
            raise CRMCollectionFailure(
                "airtable-readback", "verification receipt is incomplete or cross-wired"
            )
        return receipt

    def collect(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        render_facts = self._collect_render_facts()
        privacy_facts = self._collect_privacy_notice_facts()
        synthetic_email = f"crm-acceptance-{self.nonce}@acceptance.invalid"
        payload = {
            "email": synthetic_email,
            "interest": "cas_harness",
            "source": "customer_production_acceptance_probe",
            "metadata": {"probe": "support_crm"},
            "consent_to_contact": True,
        }
        result = self._post_public_lead(payload)
        if result.status != 200:
            raise CRMCollectionFailure(
                "public-lead", f"public lead capture returned HTTP {result.status}"
            )
        content_type = str(result.headers.get("content-type", "")).split(";", 1)[0]
        if content_type.strip().lower() != "application/json":
            raise CRMCollectionFailure("public-lead", "response is not application/json")
        response = _decode_object(result, "public-lead")
        if set(response) != PUBLIC_RESPONSE_KEYS:
            raise CRMCollectionFailure(
                "public-lead", "capture response fields drifted from the exact contract"
            )
        lead_id = response.get("lead_id")
        if not isinstance(lead_id, str) or LEAD_ID_RE.fullmatch(lead_id) is None:
            raise CRMCollectionFailure("public-lead", "response lead ID is invalid")
        if (
            response.get("captured") is not True
            or response.get("synced") is not True
            or response.get("sync_status") != "synced"
            or response.get("schema_version") != CRM_SCHEMA_VERSION
            or response.get("consent_to_contact") is not True
            or response.get("privacy_notice_url") != CRM_PRIVACY_NOTICE_URL
            or response.get("privacy_notice_version")
            != self.privacy_notice_contract.version
            or response.get("privacy_notice_content_sha256")
            != self.privacy_notice_contract.content_sha256
            or response.get("privacy_notice_publication_status")
            != CRM_PRIVACY_NOTICE_PRESENT_STATUS
            or response.get("consent_schema_version") != CRM_CONSENT_SCHEMA_VERSION
        ):
            raise CRMCollectionFailure(
                "public-lead", "capture response did not prove synced consent-bound intake"
            )

        persisted = self.lead_reader(self.lead_store_path, lead_id)
        if persisted is None:
            raise CRMCollectionFailure("persistence", "captured lead was not durable on readback")
        if (
            persisted.lead_id != lead_id
            or persisted.email != synthetic_email
            or persisted.source != "customer_production_acceptance_probe"
            or not isinstance(persisted.trace_id, str)
            or not persisted.trace_id.strip()
            or persisted.sync_status != "synced"
            or persisted.schema_version != CRM_SCHEMA_VERSION
            or persisted.version < 2
            or persisted.consent_to_contact is not True
            or persisted.privacy_notice_url != CRM_PRIVACY_NOTICE_URL
            or persisted.privacy_notice_version
            != self.privacy_notice_contract.version
            or persisted.privacy_notice_content_sha256
            != self.privacy_notice_contract.content_sha256
            or persisted.privacy_notice_publication_status
            != CRM_PRIVACY_NOTICE_PRESENT_STATUS
            or persisted.consent_schema_version != CRM_CONSENT_SCHEMA_VERSION
            or persisted.consent_recorded_at_utc
            != response.get("consent_recorded_at_utc")
        ):
            raise CRMCollectionFailure(
                "persistence", "durable lead readback is stale or cross-wired"
            )
        external_id = persisted.external_id
        if (
            not isinstance(external_id, str)
            or AIRTABLE_RECORD_ID_RE.fullmatch(external_id) is None
        ):
            raise CRMCollectionFailure("airtable-readback", "Airtable record ID is invalid")
        receipt = self._require_receipt(persisted)
        deployed_time = _parse_timestamp(
            render_facts["render_deploy_finished_at_utc"], "render-deployed"
        )
        privacy_time = _parse_timestamp(
            privacy_facts["privacy_notice_verified_at_utc"], "privacy-verified"
        )
        consent_time = _parse_timestamp(
            persisted.consent_recorded_at_utc, "consent-recorded"
        )
        verified_time = _parse_timestamp(receipt.verified_at, "airtable-verified")
        observed_time = self._now()
        if not (
            deployed_time
            <= privacy_time
            <= consent_time
            <= verified_time
            <= observed_time
        ):
            raise CRMCollectionFailure(
                "timestamp-order",
                "deploy, privacy, consent, readback, and observation are not monotonic",
            )

        observed_at = _stamp(observed_time)
        pseudonym_metadata = self.pseudonymizer.metadata()
        lead_subject = self.pseudonymizer.subject(
            domain=CRM_LEAD_DOMAIN,
            tenant_scope=CONTACT_STATE_TENANT,
            value=lead_id,
        )
        record_subject = self.pseudonymizer.subject(
            domain=AIRTABLE_RECORD_DOMAIN,
            tenant_scope=CONTACT_STATE_TENANT,
            value=external_id,
        )
        trace_subject = self.pseudonymizer.subject(
            domain=SUPPORT_CRM_REQUEST_TRACE_DOMAIN,
            tenant_scope=CONTACT_STATE_TENANT,
            value=persisted.trace_id,
        )
        airtable_contract_sha = _digest_bytes(_canonical_bytes(self.airtable_contract))
        source_receipt = {
            "schema_version": SOURCE_SCHEMA_VERSION,
            "environment": "public-production",
            "repository": REPOSITORY,
            "master_head_sha": self.master_head_sha,
            "deploy_id": self.deploy_id,
            "service_id": PRODUCTION_SERVICE_ID,
            **render_facts,
            **pseudonym_metadata,
            "lead_subject": lead_subject,
            "airtable_record_subject": record_subject,
            "lead_store_backend": "state_store",
            "state_store_backend": "postgres",
            "state_store_read_authority": True,
            "lead_migration_marker_verified": True,
            "lead_head_revision_verified": True,
            "provider": "airtable",
            "airtable_api_base": self.airtable_contract["api_base_url"],
            "airtable_base_id": self.airtable_contract["base_id"],
            "airtable_table_name": self.airtable_contract["table_name"],
            "airtable_dedup_field": self.airtable_contract["dedup_field"],
            "airtable_owner_field": self.airtable_contract["owner_field"],
            "airtable_owner_value": self.airtable_contract["owner_value"],
            "airtable_lifecycle_field": self.airtable_contract["lifecycle_field"],
            "airtable_consent_to_contact_field": self.airtable_contract[
                "consent_to_contact_field"
            ],
            "airtable_consent_recorded_at_field": self.airtable_contract[
                "consent_recorded_at_field"
            ],
            "airtable_consent_schema_version_field": self.airtable_contract[
                "consent_schema_version_field"
            ],
            "airtable_privacy_notice_url_field": self.airtable_contract[
                "privacy_notice_url_field"
            ],
            "airtable_privacy_notice_version_field": self.airtable_contract[
                "privacy_notice_version_field"
            ],
            "airtable_privacy_notice_content_sha256_field": self.airtable_contract[
                "privacy_notice_content_sha256_field"
            ],
            "airtable_privacy_notice_publication_status_field": self.airtable_contract[
                "privacy_notice_publication_status_field"
            ],
            "airtable_contract_sha256": airtable_contract_sha,
            **privacy_facts,
            "capture_http_status": result.status,
            "trace_subject": trace_subject,
            "adapter_response_digest": receipt.response_digest,
            "lead_schema_version": persisted.schema_version,
            "lead_record_version": persisted.version,
            "persisted": True,
            "readback_verified": True,
            "deduplicated": True,
            "owner_assigned": True,
            "lifecycle_stage": persisted.pipeline_status,
            "verified_at_utc": receipt.verified_at,
            "consent_to_contact": True,
            "consent_schema_version": persisted.consent_schema_version,
            "consent_recorded_at_utc": persisted.consent_recorded_at_utc,
            "source_attribution_recorded": True,
            "observed_at_utc": observed_at,
        }
        source_receipt_sha = _digest_bytes(_canonical_bytes(source_receipt))
        fragment = {
            "schema_version": FRAGMENT_SCHEMA_VERSION,
            "gate": "support_crm",
            "status": "OPEN",
            "environment": "public-production",
            "repository": REPOSITORY,
            "master_head_sha": self.master_head_sha,
            "deploy_id": self.deploy_id,
            "service_id": PRODUCTION_SERVICE_ID,
            **pseudonym_metadata,
            "event_at_utc": receipt.verified_at,
            "observed_at_utc": observed_at,
            "source_receipt_sha256": source_receipt_sha,
            "source_receipt": deepcopy(source_receipt),
            "missing_required_evidence": ["resolved_support_ticket_sla"],
            "crm_lead": {
                "system": "airtable",
                "provider": "airtable",
                "lead_subject": lead_subject,
                "airtable_record_subject": record_subject,
                "adapter_response_digest": receipt.response_digest,
                "source_receipt_sha256": source_receipt_sha,
                "persisted": True,
                "readback_verified": True,
                "deduplicated": True,
                "owner_assigned": True,
                "lifecycle_stage": persisted.pipeline_status,
                "verified_at_utc": receipt.verified_at,
            },
            "consent": {
                "capture_consent_recorded": True,
                "consent_to_contact": True,
                "source_attribution_recorded": True,
                "privacy_notice_linked": True,
                "privacy_notice_url": persisted.privacy_notice_url,
                "privacy_notice_version": persisted.privacy_notice_version,
                "privacy_notice_content_sha256": (
                    persisted.privacy_notice_content_sha256
                ),
                "privacy_notice_publication_status": (
                    persisted.privacy_notice_publication_status
                ),
                "consent_schema_version": persisted.consent_schema_version,
                "recorded_at_utc": persisted.consent_recorded_at_utc,
            },
        }
        private_selector = {
            "schema_version": PRIVATE_LEAD_SELECTOR_SCHEMA_VERSION,
            "gate": "support_crm",
            "crm_lead_id": lead_id,
        }
        _validate_output_pair(source_receipt, fragment)
        rendered_public = json.dumps(
            [source_receipt, fragment], ensure_ascii=True, sort_keys=True
        )
        if persisted.trace_id in rendered_public:
            raise CRMCollectionFailure(
                "privacy", "public output contains the private request trace ID"
            )
        _validate_private_lead_selector(private_selector)
        return source_receipt, fragment, private_selector


def _validate_output_pair(
    source_receipt: Mapping[str, Any], fragment: Mapping[str, Any]
) -> None:
    embedded = fragment.get("source_receipt")
    if not isinstance(embedded, Mapping):
        raise CRMCollectionFailure("output", "embedded source receipt is missing")
    if set(source_receipt) != SOURCE_RECEIPT_KEYS or set(embedded) != SOURCE_RECEIPT_KEYS:
        raise CRMCollectionFailure("output", "source receipt fields drifted")
    source_bytes = _canonical_bytes(source_receipt)
    embedded_bytes = _canonical_bytes(embedded)
    if embedded_bytes != source_bytes:
        raise CRMCollectionFailure("output", "embedded source receipt diverged")
    if any(
        fragment.get(field) != source_receipt.get(field)
        for field in ("pseudonymization_scheme", "pseudonym_key_id")
    ):
        raise CRMCollectionFailure(
            "output", "source receipt and fragment pseudonym metadata diverged"
        )
    try:
        validate_public_pseudonym_metadata(source_receipt)
        validate_public_pseudonym_metadata(fragment)
    except ValueError as exc:
        raise CRMCollectionFailure(
            "output", "source receipt or fragment pseudonym metadata is invalid"
        ) from exc
    source_hash = _digest_bytes(embedded_bytes)
    lead = fragment.get("crm_lead")
    consent = fragment.get("consent")
    if not isinstance(lead, Mapping) or not isinstance(consent, Mapping):
        raise CRMCollectionFailure("output", "acceptance fragment sections are missing")
    if (
        source_receipt.get("schema_version") != SOURCE_SCHEMA_VERSION
        or fragment.get("schema_version") != FRAGMENT_SCHEMA_VERSION
        or fragment.get("gate") != "support_crm"
        or fragment.get("status") != "OPEN"
        or fragment.get("missing_required_evidence") != ["resolved_support_ticket_sla"]
        or fragment.get("source_receipt_sha256") != source_hash
        or lead.get("source_receipt_sha256") != source_hash
        or lead.get("lead_subject") != source_receipt.get("lead_subject")
        or lead.get("airtable_record_subject")
        != source_receipt.get("airtable_record_subject")
        or lead.get("adapter_response_digest")
        != source_receipt.get("adapter_response_digest")
        or lead.get("verified_at_utc") != source_receipt.get("verified_at_utc")
        or consent.get("recorded_at_utc")
        != source_receipt.get("consent_recorded_at_utc")
        or consent.get("privacy_notice_version")
        != source_receipt.get("privacy_notice_version")
        or consent.get("privacy_notice_content_sha256")
        != source_receipt.get("privacy_notice_content_sha256")
        or consent.get("privacy_notice_publication_status")
        != source_receipt.get("privacy_notice_publication_status")
    ):
        raise CRMCollectionFailure("output", "source receipt and fragment diverged")
    exact_source_contract = {
        "environment": "public-production",
        "repository": REPOSITORY,
        "service_id": PRODUCTION_SERVICE_ID,
        "render_service_name": PRODUCTION_SERVICE_NAME,
        "render_repository": REPOSITORY_URL,
        "render_branch": "master",
        "render_auto_deploy_trigger": "checksPass",
        "render_deploy_status": "live",
        "render_deploy_commit_sha": source_receipt.get("master_head_sha"),
        "lead_store_backend": "state_store",
        "state_store_backend": "postgres",
        "state_store_read_authority": True,
        "lead_migration_marker_verified": True,
        "lead_head_revision_verified": True,
        "provider": "airtable",
        "airtable_api_base": CANONICAL_AIRTABLE_API_BASE_URL,
        "airtable_base_id": PRODUCTION_AIRTABLE_BASE_ID,
        "airtable_table_name": PRODUCTION_AIRTABLE_TABLE_NAME,
        "airtable_dedup_field": PRODUCTION_AIRTABLE_DEDUP_FIELD,
        "airtable_owner_field": PRODUCTION_AIRTABLE_OWNER_FIELD,
        "airtable_owner_value": PRODUCTION_AIRTABLE_OWNER_VALUE,
        "airtable_lifecycle_field": PRODUCTION_AIRTABLE_LIFECYCLE_FIELD,
        "privacy_notice_publication_status": CRM_PRIVACY_NOTICE_PRESENT_STATUS,
        "privacy_notice_url": CRM_PRIVACY_NOTICE_URL,
        "privacy_notice_http_status": 200,
        "privacy_notice_content_type": "text/html",
    }
    if any(source_receipt.get(key) != value for key, value in exact_source_contract.items()):
        raise CRMCollectionFailure("output", "source receipt production contract drifted")
    if source_receipt.get("deploy_id") != fragment.get("deploy_id"):
        raise CRMCollectionFailure("output", "source deploy ID diverged")
    if (
        source_receipt.get("master_head_sha") != fragment.get("master_head_sha")
        or SHA1_RE.fullmatch(str(source_receipt.get("master_head_sha") or "")) is None
    ):
        raise CRMCollectionFailure("output", "source master commit diverged")
    airtable_contract = {
        "api_base_url": source_receipt.get("airtable_api_base"),
        "base_id": source_receipt.get("airtable_base_id"),
        "table_name": source_receipt.get("airtable_table_name"),
        "dedup_field": source_receipt.get("airtable_dedup_field"),
        "owner_field": source_receipt.get("airtable_owner_field"),
        "owner_value": source_receipt.get("airtable_owner_value"),
        "lifecycle_field": source_receipt.get("airtable_lifecycle_field"),
        "consent_to_contact_field": source_receipt.get(
            "airtable_consent_to_contact_field"
        ),
        "consent_recorded_at_field": source_receipt.get(
            "airtable_consent_recorded_at_field"
        ),
        "consent_schema_version_field": source_receipt.get(
            "airtable_consent_schema_version_field"
        ),
        "privacy_notice_url_field": source_receipt.get(
            "airtable_privacy_notice_url_field"
        ),
        "privacy_notice_version_field": source_receipt.get(
            "airtable_privacy_notice_version_field"
        ),
        "privacy_notice_content_sha256_field": source_receipt.get(
            "airtable_privacy_notice_content_sha256_field"
        ),
        "privacy_notice_publication_status_field": source_receipt.get(
            "airtable_privacy_notice_publication_status_field"
        ),
    }
    expected_airtable_contract = {
        "api_base_url": CANONICAL_AIRTABLE_API_BASE_URL,
        "base_id": PRODUCTION_AIRTABLE_BASE_ID,
        "table_name": PRODUCTION_AIRTABLE_TABLE_NAME,
        "dedup_field": PRODUCTION_AIRTABLE_DEDUP_FIELD,
        "owner_field": PRODUCTION_AIRTABLE_OWNER_FIELD,
        "owner_value": PRODUCTION_AIRTABLE_OWNER_VALUE,
        "lifecycle_field": PRODUCTION_AIRTABLE_LIFECYCLE_FIELD,
        **AIRTABLE_CONSENT_FIELD_CONTRACT,
    }
    if airtable_contract != expected_airtable_contract:
        raise CRMCollectionFailure("output", "Airtable field/owner contract drifted")
    if source_receipt.get("airtable_contract_sha256") != _digest_bytes(
        _canonical_bytes(expected_airtable_contract)
    ):
        raise CRMCollectionFailure("output", "Airtable contract digest diverged")
    for key in ("lead_subject", "airtable_record_subject"):
        if re.fullmatch(r"hmac-sha256:[0-9a-f]{64}", str(lead.get(key) or "")) is None:
            raise CRMCollectionFailure("output", f"{key} is invalid")
    if SHA256_RE.fullmatch(str(lead.get("source_receipt_sha256") or "")) is None:
        raise CRMCollectionFailure("output", "source_receipt_sha256 is invalid")
    if "trace_id_sha256" in source_receipt:
        raise CRMCollectionFailure(
            "output", "legacy unkeyed trace digest is forbidden"
        )
    if SUBJECT_PATTERN.fullmatch(str(source_receipt.get("trace_subject") or "")) is None:
        raise CRMCollectionFailure("output", "trace_subject is invalid")
    for key in (
        "render_service_response_sha256",
        "render_deploy_response_sha256",
        "airtable_contract_sha256",
        "privacy_notice_content_sha256",
    ):
        if SHA256_RE.fullmatch(str(source_receipt.get(key) or "")) is None:
            raise CRMCollectionFailure("output", f"{key} is invalid")
    if TAGGED_SHA256_RE.fullmatch(str(lead.get("adapter_response_digest") or "")) is None:
        raise CRMCollectionFailure("output", "adapter_response_digest is invalid")
    rendered = json.dumps([source_receipt, fragment], ensure_ascii=True, sort_keys=True)
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", rendered):
        raise CRMCollectionFailure("output", "output contains an email address")
    if any(
        forbidden in rendered.lower()
        for forbidden in ("nc_airtable_token", "authorization", "bearer ", "api_key")
    ):
        raise CRMCollectionFailure("output", "output contains credential-shaped material")


def _validate_private_lead_selector(selector: Mapping[str, Any]) -> None:
    if (
        set(selector) != {"schema_version", "gate", "crm_lead_id"}
        or selector.get("schema_version") != PRIVATE_LEAD_SELECTOR_SCHEMA_VERSION
        or selector.get("gate") != "support_crm"
        or not isinstance(selector.get("crm_lead_id"), str)
        or LEAD_ID_RE.fullmatch(str(selector.get("crm_lead_id"))) is None
    ):
        raise CRMCollectionFailure("private-selector", "private lead selector is invalid")


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temp_path = Path(handle.name)
    try:
        os.chmod(temp_path, 0o600)
        with handle:
            handle.write(_canonical_bytes(payload) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=PRODUCTION_API_ORIGIN)
    parser.add_argument("--master-head", required=True)
    parser.add_argument("--deploy-id", required=True)
    parser.add_argument("--source-receipt-output", type=Path, required=True)
    parser.add_argument("--fragment-output", type=Path, required=True)
    parser.add_argument("--private-lead-selector-output", type=Path, required=True)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    state_store = None
    try:
        if len(
            {
                args.source_receipt_output.resolve(),
                args.fragment_output.resolve(),
                args.private_lead_selector_output.resolve(),
            }
        ) != 3:
            raise CRMCollectionFailure("output", "output paths must differ")
        from api.config import Settings
        from api.state_ledger_bootstrap import _build_state_store

        state_store = _build_state_store(Settings())
        collector = AirtableCRMSourceCollector(
            base_url=args.base_url,
            master_head_sha=args.master_head,
            deploy_id=args.deploy_id,
            lead_reader=_verified_state_store_lead_reader(state_store),
        )
        source_receipt, fragment, private_selector = collector.collect()
        _validate_output_pair(source_receipt, fragment)
        _validate_private_lead_selector(private_selector)
        _atomic_write(args.source_receipt_output, source_receipt)
        _atomic_write(args.fragment_output, fragment)
        _atomic_write(args.private_lead_selector_output, private_selector)
        print(
            json.dumps(
                {
                    "gate": "support_crm",
                    "status": "OPEN",
                    "source_receipt_sha256": fragment["source_receipt_sha256"],
                    "missing_required_evidence": fragment["missing_required_evidence"],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    except CRMCollectionFailure as exc:
        print(
            json.dumps(
                {"gate": exc.gate, "status": "OPEN", "error": str(exc)},
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2
    except Exception as exc:  # pragma: no cover - final secret-safe boundary
        print(
            json.dumps(
                {
                    "gate": "collector",
                    "status": "OPEN",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 3
    finally:
        if state_store is not None:
            try:
                state_store.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(run())
