"""External-CRM sync seam — the only place a lead can earn the word ``synced``.

This is the boundary between "captured on our side" and "landed in the external CRM of record"
(Airtable / HubSpot / …). It mirrors the honesty discipline of
``api/services/production/billing.py``'s ``PaymentProvider``: the seam is an ABC the real
integrations implement, and the shipped default is a **stub that advertises its own no-op** — it
never moves a lead into an external system and never claims it did.

The load-bearing rule (from :mod:`.models`)
-------------------------------------------
Only a real provider that actually wrote to the external CRM may return a
:class:`~api.services.crm.models.CRMSyncResult` with ``synced=True`` — and that result structurally
*must* carry a real ``external_id`` and ``is_real=True`` (``CRMSyncResult.__post_init__`` refuses
anything less). The :class:`NullCRMProvider` therefore **cannot** produce a synced landing even by
mistake: it returns ``synced=False, is_real=False``. So a deployment running the dark default leaves
every lead at ``captured`` → ``sync_pending`` ("attempted, nothing left the building"), which is the
honest state when no external CRM is wired.

Why the factory fails loud
--------------------------
:func:`build_crm_provider` returns the null provider for the default ``crm_provider="null"``.
Configured Airtable is accepted only with its complete identity/ownership field contract;
half-configuration raises. An unimplemented provider such as ``"hubspot"`` also raises rather than
silently handing back a stub. A loud startup failure the operator can see and fix is the honest
outcome (same discipline as ``install_state_ledger``).
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from api.services.crm.models import (
    CRMSyncResult,
    CRMVerificationReceipt,
    Lead,
    _now_iso,
    _verification_now_iso,
    normalize_email,
)


_CANONICAL_AIRTABLE_API_BASE_URL = "https://api.airtable.com/v0"
_MAX_AIRTABLE_RESPONSE_BYTES = 2_000_000


class _DuplicateJSONKeyError(ValueError):
    """Internal marker for an ambiguous provider JSON object."""


class _NonStandardJSONConstantError(ValueError):
    """Internal marker for NaN/Infinity values, which are not valid JSON."""


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKeyError
        result[key] = value
    return result


def _reject_nonstandard_json_constant(_value: str) -> object:
    raise _NonStandardJSONConstantError


class _RejectRedirects(HTTPRedirectHandler):
    """Keep the Airtable bearer token on the one configured canonical origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


_AIRTABLE_NO_REDIRECT_OPENER = build_opener(_RejectRedirects())


def _open_canonical_airtable(request: Request, timeout: int):
    """Open one Airtable request without following credential-bearing redirects."""

    return _AIRTABLE_NO_REDIRECT_OPENER.open(request, timeout=timeout)


class CRMConfigError(ValueError):
    """Raised when the CRM is configured to use a provider that is not available/implemented.

    Asking for a real external CRM we have not built yet must fail loudly at construction, never
    degrade to a silent no-op that looks like a working sync.
    """


class CRMProviderError(RuntimeError):
    """Normalized, secret-safe external CRM failure.

    Raw response bodies, URLs, credentials, request payloads, and transport ``reason`` strings are
    intentionally excluded. ``CRMService`` may persist this string without accidentally copying a
    provider secret or lead PII into the local append-only ledger.
    """

    def __init__(
        self,
        *,
        provider: str,
        stage: str,
        category: str,
        status: int | None = None,
    ) -> None:
        self.provider = provider
        self.stage = stage
        self.category = category
        self.status = status
        status_suffix = "" if status is None else f", status={status}"
        super().__init__(
            f"{provider} CRM request failed (stage={stage}, category={category}{status_suffix})"
        )


def normalize_crm_provider_error(provider: str, exc: Exception) -> str:
    """Return a bounded error note that is safe to persist.

    Known provider errors are already normalized. Unknown exception type and message are both
    discarded because either may contain an Authorization label, URL, response body, or submitted
    customer data.
    """

    if isinstance(exc, CRMProviderError):
        return str(exc)
    safe_provider = (
        provider if provider.replace("-", "").replace("_", "").isalnum() else "unknown"
    )
    return f"{safe_provider} CRM request failed (stage=sync, category=unexpected_error)"


def airtable_email_dedup_key(email: str) -> str:
    """Return a stable pseudonymous Airtable merge key for a normalized email address.

    The external CRM still receives the contact email in its dedicated ``Email`` field. The merge
    key itself never embeds that address, which keeps list-filter URLs and provider diagnostics
    free of contact PII and avoids formula-injection input at the deduplication boundary.
    """

    normalized = normalize_email(email)
    digest = hashlib.sha256(
        b"noetic-crm-airtable-email-dedup-v1\x00" + normalized.encode("utf-8")
    ).hexdigest()
    return f"nc-email-sha256-v1:{digest}"


class CRMSyncProvider(ABC):
    """The seam a real external-CRM integration implements.

    A concrete provider's :meth:`sync_lead` does the real network write to Airtable/HubSpot/… and
    returns a :class:`CRMSyncResult` carrying the external record id on success. ``provider_name``
    and ``is_real`` let the orchestrating service annotate a *failed* attempt honestly (real
    provider that errored → ``sync_failed``) without having to know the concrete type — see
    :meth:`~api.services.crm.service.CRMService.capture`.
    """

    #: Stable identifier of this provider ("null" | "airtable" | "hubspot" | …).
    provider_name: str = "abstract"

    #: Whether this provider actually talks to an external CRM. The null stub sets this False so a
    #: failure on it maps to ``sync_pending`` (a no-op cannot "fail"), while a real provider's
    #: failure maps to ``sync_failed``.
    is_real: bool = False

    @abstractmethod
    def sync_lead(self, lead: Lead) -> CRMSyncResult:
        """Attempt to land ``lead`` in the external CRM and report the honest outcome."""
        ...


class NullCRMProvider(CRMSyncProvider):
    """The dark default. Never contacts an external CRM; never claims a landing.

    This is the CRM analog of ``billing.py``'s ``StubPaymentProvider``: it exists so lead capture
    works end-to-end (and is unit-testable) with zero external configuration, and it is structurally
    incapable of dishonesty — it returns ``synced=False, is_real=False`` with no ``external_id``, so
    the lead settles at ``sync_pending``. A deployment that wants leads to actually reach an external
    CRM must configure a real provider; until then, the honest posture is "captured locally, nothing
    synced", and that is exactly what this returns.
    """

    provider_name = "null"
    is_real = False

    def sync_lead(self, lead: Lead) -> CRMSyncResult:
        return CRMSyncResult(
            provider=self.provider_name,
            synced=False,
            is_real=False,
            external_id=None,
            synced_at=_now_iso(),
            note=(
                "null CRM provider: lead captured locally, no external CRM configured, so nothing "
                "was synced. Configure NC_CRM_PROVIDER (airtable|hubspot) with credentials to land "
                "leads in an external CRM of record."
            ),
        )


class AirtableCRMProvider(CRMSyncProvider):
    """Airtable upsert provider with idempotent identity and independent readback.

    One PATCH ``performUpsert`` merges on a configured text field containing a pseudonymous hash
    of the normalized email. Success is not inferred from that write response: the provider then
    GETs the returned record directly and performs a filtered list GET for the dedup key. Only an
    exact field match plus exactly one list result for the same record earns ``synced``.
    """

    provider_name = "airtable"
    is_real = True

    def __init__(
        self,
        *,
        token: str,
        base_id: str,
        table_name: str,
        api_base_url: str = "https://api.airtable.com/v0",
        dedup_field: str = "Dedup Key",
        owner_field: str = "Owner",
        owner_value: str = "",
        lifecycle_field: str = "Pipeline Status",
        http_open: Callable[..., object] = _open_canonical_airtable,
    ) -> None:
        token = token.strip()
        base_id = base_id.strip()
        table_name = table_name.strip()
        api_base_url = api_base_url.strip().rstrip("/") or _CANONICAL_AIRTABLE_API_BASE_URL
        dedup_field = dedup_field.strip()
        owner_field = owner_field.strip()
        owner_value = owner_value.strip()
        lifecycle_field = lifecycle_field.strip()
        missing = [
            name
            for name, value in (
                ("NC_AIRTABLE_TOKEN", token),
                ("NC_AIRTABLE_BASE_ID", base_id),
                ("NC_AIRTABLE_TABLE_NAME", table_name),
                ("NC_AIRTABLE_DEDUP_FIELD", dedup_field),
                ("NC_AIRTABLE_OWNER_FIELD", owner_field),
                ("NC_AIRTABLE_OWNER_VALUE", owner_value),
                ("NC_AIRTABLE_LIFECYCLE_FIELD", lifecycle_field),
            )
            if not value
        ]
        if missing:
            raise CRMConfigError(
                "CRM provider 'airtable' requires " + ", ".join(missing) + "; refusing to start "
                "because a half-configured Airtable provider would capture leads locally but sync "
                "nothing."
            )
        if api_base_url != _CANONICAL_AIRTABLE_API_BASE_URL:
            raise CRMConfigError(
                "NC_AIRTABLE_API_BASE_URL must be exactly "
                f"{_CANONICAL_AIRTABLE_API_BASE_URL}; refusing to send the Airtable bearer "
                "credential to a non-canonical origin"
            )
        for setting_name, field_name in (
            ("NC_AIRTABLE_DEDUP_FIELD", dedup_field),
            ("NC_AIRTABLE_OWNER_FIELD", owner_field),
            ("NC_AIRTABLE_LIFECYCLE_FIELD", lifecycle_field),
        ):
            if (
                len(field_name) > 255
                or any(character in field_name for character in "{}")
                or any(ord(character) < 32 for character in field_name)
            ):
                raise CRMConfigError(
                    f"{setting_name} must be a non-empty Airtable field name without braces or "
                    "line breaks"
                )
        configured_fields = [
            dedup_field.casefold(),
            owner_field.casefold(),
            lifecycle_field.casefold(),
        ]
        if len(set(configured_fields)) != len(configured_fields):
            raise CRMConfigError(
                "NC_AIRTABLE_DEDUP_FIELD, NC_AIRTABLE_OWNER_FIELD, and "
                "NC_AIRTABLE_LIFECYCLE_FIELD must name distinct Airtable fields"
            )
        fixed_fields = {
            "lead id",
            "email",
            "name",
            "organization",
            "message",
            "interest",
            "source",
            "trace id",
            "schema version",
            "metadata json",
            "consent to contact",
            "consent recorded at utc",
            "consent schema version",
            "privacy notice url",
            "privacy notice version",
        }
        if dedup_field.casefold() in fixed_fields or owner_field.casefold() in fixed_fields:
            raise CRMConfigError(
                "Airtable dedup and owner fields must not reuse a built-in lead field name"
            )
        if lifecycle_field.casefold() in fixed_fields:
            raise CRMConfigError(
                "NC_AIRTABLE_LIFECYCLE_FIELD must not reuse a built-in lead field name"
            )
        self._token = token
        self._base_id = base_id
        self._table_name = table_name
        self._api_base_url = api_base_url
        self._dedup_field = dedup_field
        self._owner_field = owner_field
        self._owner_value = owner_value
        self._lifecycle_field = lifecycle_field
        self._http_open = http_open

    @property
    def create_record_url(self) -> str:
        """Backward-compatible table endpoint name (writes now use PATCH upsert)."""

        base_id = quote(self._base_id, safe="")
        table_name = quote(self._table_name, safe="")
        return f"{self._api_base_url}/{base_id}/{table_name}"

    @property
    def records_url(self) -> str:
        return self.create_record_url

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request_json(self, request: Request, *, stage: str) -> dict[str, object]:
        try:
            with self._http_open(request, timeout=15) as response:  # type: ignore[attr-defined]
                raw_bytes = response.read(_MAX_AIRTABLE_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            # Drain a bounded amount when possible, but never include provider content in the error.
            try:
                exc.read(8192)
            except Exception:  # noqa: BLE001 - the body is intentionally discarded either way
                pass
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category="http_error",
                status=exc.code,
            ) from None
        except (URLError, TimeoutError, OSError):
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category="transport_error",
            ) from None
        except CRMProviderError:
            raise
        except Exception:  # noqa: BLE001 - normalize arbitrary client exceptions safely
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category="transport_error",
            ) from None

        if not isinstance(raw_bytes, bytes):
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category="invalid_response_type",
            )
        if len(raw_bytes) > _MAX_AIRTABLE_RESPONSE_BYTES:
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category="response_too_large",
            )
        try:
            decoded = raw_bytes.decode("utf-8")
            data = json.loads(
                decoded,
                object_pairs_hook=_unique_json_object,
                parse_constant=_reject_nonstandard_json_constant,
            )
        except _DuplicateJSONKeyError:
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category="duplicate_json_key",
            ) from None
        except (UnicodeDecodeError, json.JSONDecodeError, _NonStandardJSONConstantError):
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category="invalid_json",
            ) from None
        if not isinstance(data, dict):
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category="invalid_response_shape",
            )
        return data

    def _lead_fields(self, lead: Lead, dedup_key: str) -> dict[str, object]:
        fields: dict[str, object] = {
            self._dedup_field: dedup_key,
            self._owner_field: self._owner_value,
            self._lifecycle_field: lead.pipeline_status,
            "Lead ID": lead.lead_id,
            "Email": lead.email,
            "Schema Version": lead.schema_version,
            "Consent to Contact": lead.consent_to_contact,
            "Consent Recorded At UTC": lead.consent_recorded_at_utc,
            "Consent Schema Version": lead.consent_schema_version,
            "Privacy Notice URL": lead.privacy_notice_url,
            "Privacy Notice Version": lead.privacy_notice_version,
            "Metadata JSON": json.dumps(
                dict(lead.metadata), sort_keys=True, separators=(",", ":")
            ),
        }
        # Empty strings are intentional updates: a repeat submission that clears a value must not
        # silently retain stale PII from the prior Airtable record.
        fields.update(
            {
                "Name": lead.name,
                "Organization": lead.organization,
                "Message": lead.message,
                "Interest": lead.interest,
                "Source": lead.source,
                "Trace ID": lead.trace_id or "",
            }
        )
        return fields

    def _record_from_response(
        self,
        data: Mapping[str, object],
        *,
        stage: str,
        wrapped: bool,
    ) -> dict[str, object]:
        if wrapped:
            records = data.get("records")
            if (
                not isinstance(records, list)
                or len(records) != 1
                or not isinstance(records[0], dict)
            ):
                raise CRMProviderError(
                    provider=self.provider_name,
                    stage=stage,
                    category="invalid_response_shape",
                )
            return records[0]
        return dict(data)

    def _record_id(self, record: Mapping[str, object], *, stage: str) -> str:
        external_id = record.get("id")
        if (
            not isinstance(external_id, str)
            or not external_id.strip()
            or len(external_id) > 128
            or any(character.isspace() for character in external_id)
        ):
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category="missing_record_id",
            )
        return external_id

    def _verify_record(
        self,
        record: Mapping[str, object],
        *,
        external_id: str,
        expected_fields: Mapping[str, object],
        stage: str,
    ) -> None:
        if self._record_id(record, stage=stage) != external_id:
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category="record_id_mismatch",
            )
        fields = record.get("fields")
        if not isinstance(fields, dict):
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category="missing_fields",
            )
        for field_name, expected_value in expected_fields.items():
            actual_value = fields.get(field_name)
            # Airtable omits cleared fields from read responses. Missing and an explicit empty
            # string are equivalent only when the exact requested value was empty.
            if actual_value == expected_value or (
                expected_value == "" and field_name not in fields
            ):
                continue
            if field_name == self._owner_field:
                category = "owner_mismatch"
            elif field_name == self._lifecycle_field:
                category = "lifecycle_mismatch"
            elif field_name == self._dedup_field:
                category = "dedup_key_mismatch"
            else:
                category = "stale_readback"
            raise CRMProviderError(
                provider=self.provider_name,
                stage=stage,
                category=category,
            )

    @staticmethod
    def _response_digest(*responses: Mapping[str, object]) -> str:
        canonical = json.dumps(
            list(responses),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest = hashlib.sha256(
            b"noetic-crm-airtable-verification-v1\x00" + canonical
        ).hexdigest()
        return f"sha256:{digest}"

    def sync_lead(self, lead: Lead) -> CRMSyncResult:
        dedup_key = airtable_email_dedup_key(lead.email)
        expected_fields = self._lead_fields(lead, dedup_key)
        payload: dict[str, object] = {
            "performUpsert": {"fieldsToMergeOn": [self._dedup_field]},
            "records": [
                {
                    "fields": expected_fields,
                }
            ],
        }
        upsert_request = Request(
            self.records_url,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers=self._headers(),
            method="PATCH",
        )
        upsert_data = self._request_json(upsert_request, stage="upsert")
        upsert_record = self._record_from_response(upsert_data, stage="upsert", wrapped=True)
        external_id = self._record_id(upsert_record, stage="upsert")

        record_url = f"{self.records_url}/{quote(external_id, safe='')}"
        record_request = Request(record_url, headers=self._headers(), method="GET")
        record_data = self._request_json(record_request, stage="record_readback")
        self._verify_record(
            record_data,
            external_id=external_id,
            expected_fields=expected_fields,
            stage="record_readback",
        )

        formula = f"{{{self._dedup_field}}}='{dedup_key}'"
        list_query = urlencode(
            {"filterByFormula": formula, "maxRecords": 2, "pageSize": 2}
        )
        list_url = f"{self.records_url}?{list_query}"
        list_request = Request(list_url, headers=self._headers(), method="GET")
        list_data = self._request_json(list_request, stage="dedup_list_readback")
        records = list_data.get("records")
        if (
            not isinstance(records, list)
            or len(records) != 1
            or not isinstance(records[0], dict)
            or "offset" in list_data
        ):
            raise CRMProviderError(
                provider=self.provider_name,
                stage="dedup_list_readback",
                category="ambiguous_deduplication",
            )
        self._verify_record(
            records[0],
            external_id=external_id,
            expected_fields=expected_fields,
            stage="dedup_list_readback",
        )

        verified_at = _verification_now_iso()
        receipt = CRMVerificationReceipt(
            provider=self.provider_name,
            readback_verified=True,
            deduplicated=True,
            owner_assigned=True,
            lifecycle_stage=lead.pipeline_status,
            verified_at=verified_at,
            response_digest=self._response_digest(upsert_data, record_data, list_data),
        )

        return CRMSyncResult(
            provider=self.provider_name,
            synced=True,
            is_real=True,
            external_id=external_id,
            synced_at=verified_at,
            note="lead upserted and independently verified in Airtable",
            verification_receipt=receipt,
        )


def build_crm_provider(settings) -> CRMSyncProvider:
    """Construct the configured sync provider, or fail loud for one we have not built.

    * ``"null"`` (the default) -> :class:`NullCRMProvider`: dark, no external landing, honest.
    * ``"airtable"`` -> :class:`AirtableCRMProvider`: real external landing, only when token/base,
      table, dedup, owner, and lifecycle settings are present.
    * ``"hubspot"`` -> :class:`CRMConfigError`. The seam is declared but the real integration is not
      implemented; refusing here keeps an operator from believing leads are syncing when no provider
      exists to sync them.

    Any other value is an outright misconfiguration and also raises.
    """
    provider = (getattr(settings, "crm_provider", "null") or "null").strip().lower()
    if provider == "null":
        return NullCRMProvider()
    if provider == "airtable":
        return AirtableCRMProvider(
            token=getattr(settings, "crm_airtable_token", ""),
            base_id=getattr(settings, "crm_airtable_base_id", ""),
            table_name=getattr(settings, "crm_airtable_table_name", "Leads"),
            api_base_url=getattr(
                settings,
                "crm_airtable_api_base_url",
                _CANONICAL_AIRTABLE_API_BASE_URL,
            ),
            dedup_field=getattr(settings, "crm_airtable_dedup_field", "Dedup Key"),
            owner_field=getattr(settings, "crm_airtable_owner_field", "Owner"),
            owner_value=getattr(settings, "crm_airtable_owner_value", ""),
            lifecycle_field=getattr(
                settings, "crm_airtable_lifecycle_field", "Pipeline Status"
            ),
        )
    if provider == "hubspot":
        raise CRMConfigError(
            f"CRM provider {provider!r} is declared but not yet implemented. The sync seam exists "
            f"(api/services/crm/sync.py) but no real {provider} integration has been built, so it "
            f"cannot land leads. Refusing to start with a provider that would silently sync "
            f"nothing. Use NC_CRM_PROVIDER=null (capture-only) until the integration ships."
        )
    raise CRMConfigError(
        f"unknown CRM provider {provider!r}; valid values are 'null' (default, capture-only), "
        f"'airtable' (implemented, requires credentials), or 'hubspot' (not yet implemented)."
    )
