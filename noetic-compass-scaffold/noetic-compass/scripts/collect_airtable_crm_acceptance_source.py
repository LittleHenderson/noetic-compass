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
    CRM_PRIVACY_NOTICE_URL,
    CRM_SCHEMA_VERSION,
    CRMVerificationReceipt,
    JsonlFileLeadStore,
    Lead,
)


SOURCE_SCHEMA_VERSION = "cas_harness_airtable_crm_acceptance_source.v1"
FRAGMENT_SCHEMA_VERSION = "cas_harness_support_crm_acceptance_fragment.v1"
REPOSITORY = "LittleHenderson/noetic-compass"
PRODUCTION_API_ORIGIN = "https://noetic-compass-api.onrender.com"
PRODUCTION_SERVICE_ID = "srv-d82ph683kofs73d210e0"
PUBLIC_LEAD_PATH = "/api/crm/public/leads"
CANONICAL_AIRTABLE_API_BASE_URL = "https://api.airtable.com/v0"
MAX_RESPONSE_BYTES = 1_000_000
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TAGGED_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
DEPLOY_ID_RE = re.compile(r"^dep-[A-Za-z0-9]+$")
LEAD_ID_RE = re.compile(r"^lead-[0-9a-f]{16}$")
AIRTABLE_RECORD_ID_RE = re.compile(r"^rec[A-Za-z0-9]{14,125}$")
NOTICE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
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
        "consent_recorded_at_utc",
        "consent_schema_version",
        "message",
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


def _subject_digest(kind: str, value: str) -> str:
    return _digest_bytes(f"{kind}:{value}".encode("utf-8"))


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
    payload: Mapping[str, Any],
    timeout: float,
) -> HttpResult:
    body = _canonical_bytes(payload)
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "CAS-Harness-Airtable-CRM-Acceptance/1.0",
        },
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


def _default_lead_reader(path: str, lead_id: str) -> Lead | None:
    return JsonlFileLeadStore(path).get(lead_id)


class AirtableCRMSourceCollector:
    def __init__(
        self,
        *,
        base_url: str,
        master_head_sha: str,
        deploy_id: str,
        privacy_notice_version: str,
        runtime_environment: Mapping[str, str] = os.environ,
        transport: Transport = _default_transport,
        lead_reader: LeadReader = _default_lead_reader,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        nonce: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.master_head_sha = master_head_sha
        self.deploy_id = deploy_id
        self.privacy_notice_version = privacy_notice_version
        self.runtime_environment = runtime_environment
        self.transport = transport
        self.lead_reader = lead_reader
        self.clock = clock
        self.nonce = nonce or secrets.token_hex(12)
        self.lead_store_path = ""
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
        if NOTICE_VERSION_RE.fullmatch(self.privacy_notice_version) is None:
            raise CRMCollectionFailure("consent", "privacy notice version is invalid")
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
        if (
            env.get("NC_AIRTABLE_API_BASE_URL", CANONICAL_AIRTABLE_API_BASE_URL)
            .strip()
            .rstrip("/")
            != CANONICAL_AIRTABLE_API_BASE_URL
        ):
            raise CRMCollectionFailure("provider", "Airtable API origin is not canonical")
        required_provider_fields = (
            "NC_AIRTABLE_TOKEN",
            "NC_AIRTABLE_BASE_ID",
            "NC_AIRTABLE_TABLE_NAME",
            "NC_AIRTABLE_DEDUP_FIELD",
            "NC_AIRTABLE_OWNER_FIELD",
            "NC_AIRTABLE_OWNER_VALUE",
            "NC_AIRTABLE_LIFECYCLE_FIELD",
        )
        if any(not env.get(name, "").strip() for name in required_provider_fields):
            raise CRMCollectionFailure("provider", "Airtable provider contract is incomplete")
        self.lead_store_path = env.get("NC_CRM_LEAD_STORE_PATH", "").strip()
        if not self.lead_store_path or not Path(self.lead_store_path).is_absolute():
            raise CRMCollectionFailure(
                "persistence", "NC_CRM_LEAD_STORE_PATH must be an absolute durable path"
            )
        self._now()

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

    def collect(self) -> tuple[dict[str, Any], dict[str, Any]]:
        synthetic_email = f"crm-acceptance-{self.nonce}@acceptance.invalid"
        payload = {
            "email": synthetic_email,
            "interest": "cas_harness",
            "source": "customer_production_acceptance_probe",
            "metadata": {"probe": "support_crm"},
            "consent_to_contact": True,
            "privacy_notice_version": self.privacy_notice_version,
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
            or response.get("privacy_notice_version") != self.privacy_notice_version
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
            or persisted.privacy_notice_version != self.privacy_notice_version
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
        consent_time = _parse_timestamp(
            persisted.consent_recorded_at_utc, "consent-recorded"
        )
        verified_time = _parse_timestamp(receipt.verified_at, "airtable-verified")
        observed_time = self._now()
        if not consent_time <= verified_time <= observed_time:
            raise CRMCollectionFailure(
                "timestamp-order", "consent, readback, and observation are not monotonic"
            )

        observed_at = _stamp(observed_time)
        lead_hash = _subject_digest("crm-lead", lead_id)
        trace_hash = _subject_digest("crm-request-trace", persisted.trace_id)
        record_hash = _subject_digest("airtable-record", external_id)
        source_receipt = {
            "schema_version": SOURCE_SCHEMA_VERSION,
            "environment": "public-production",
            "repository": REPOSITORY,
            "master_head_sha": self.master_head_sha,
            "deploy_id": self.deploy_id,
            "service_id": PRODUCTION_SERVICE_ID,
            "provider": "airtable",
            "capture_http_status": result.status,
            "lead_id_sha256": lead_hash,
            "trace_id_sha256": trace_hash,
            "airtable_record_id_sha256": record_hash,
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
            "privacy_notice_url": persisted.privacy_notice_url,
            "privacy_notice_version": persisted.privacy_notice_version,
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
            "event_at_utc": receipt.verified_at,
            "observed_at_utc": observed_at,
            "source_receipt_sha256": source_receipt_sha,
            "missing_required_evidence": ["resolved_support_ticket_sla"],
            "crm_lead": {
                "system": "airtable",
                "provider": "airtable",
                "lead_id_sha256": lead_hash,
                "airtable_record_id_sha256": record_hash,
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
                "consent_schema_version": persisted.consent_schema_version,
                "recorded_at_utc": persisted.consent_recorded_at_utc,
            },
        }
        _validate_output_pair(source_receipt, fragment)
        return source_receipt, fragment


def _validate_output_pair(
    source_receipt: Mapping[str, Any], fragment: Mapping[str, Any]
) -> None:
    source_hash = _digest_bytes(_canonical_bytes(source_receipt))
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
        or lead.get("lead_id_sha256") != source_receipt.get("lead_id_sha256")
        or lead.get("airtable_record_id_sha256")
        != source_receipt.get("airtable_record_id_sha256")
        or lead.get("adapter_response_digest")
        != source_receipt.get("adapter_response_digest")
        or lead.get("verified_at_utc") != source_receipt.get("verified_at_utc")
        or consent.get("recorded_at_utc")
        != source_receipt.get("consent_recorded_at_utc")
        or consent.get("privacy_notice_version")
        != source_receipt.get("privacy_notice_version")
    ):
        raise CRMCollectionFailure("output", "source receipt and fragment diverged")
    for key in (
        "lead_id_sha256",
        "airtable_record_id_sha256",
        "source_receipt_sha256",
    ):
        if SHA256_RE.fullmatch(str(lead.get(key) or "")) is None:
            raise CRMCollectionFailure("output", f"{key} is invalid")
    if SHA256_RE.fullmatch(str(source_receipt.get("trace_id_sha256") or "")) is None:
        raise CRMCollectionFailure("output", "trace_id_sha256 is invalid")
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
    parser.add_argument("--privacy-notice-version", required=True)
    parser.add_argument("--source-receipt-output", type=Path, required=True)
    parser.add_argument("--fragment-output", type=Path, required=True)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.source_receipt_output.resolve() == args.fragment_output.resolve():
            raise CRMCollectionFailure("output", "output paths must differ")
        collector = AirtableCRMSourceCollector(
            base_url=args.base_url,
            master_head_sha=args.master_head,
            deploy_id=args.deploy_id,
            privacy_notice_version=args.privacy_notice_version,
        )
        source_receipt, fragment = collector.collect()
        _validate_output_pair(source_receipt, fragment)
        _atomic_write(args.source_receipt_output, source_receipt)
        _atomic_write(args.fragment_output, fragment)
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


if __name__ == "__main__":
    raise SystemExit(run())
