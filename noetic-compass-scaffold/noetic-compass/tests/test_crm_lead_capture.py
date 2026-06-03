"""Honesty + traceability tests for the CRM lead-capture workstream (``api/services/crm/``).

The load-bearing property under test mirrors the rest of the platform's declared-vs-verified
discipline, applied to go-to-market: **a lead captured on our side is never reported as synced to
the external CRM unless a real provider actually landed it.** These tests would fail loudly if the
dark default ever laundered a local capture into a ``synced`` status, if a sync failure ever lost a
captured lead, or if the durable store ever forgot a lead it claimed to persist.

Layered like ``test_production_billing.py``: most assertions are import-isolated (no app), exercising
the models / store / sync / service directly. A small set of route tests drives the FastAPI app to
prove the public capture endpoint is open, the sales views are authed, and traceability survives the
HTTP round-trip.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from api.middleware.auth import create_token
from api.services.crm import (
    AirtableCRMProvider,
    CRMConfigError,
    CRMService,
    CRMStateError,
    CRMSyncProvider,
    CRMSyncResult,
    InMemoryLeadStore,
    JsonlFileLeadStore,
    Lead,
    PublicLeadAbuseGuard,
    LeadSubmission,
    LeadValidationError,
    NullCRMProvider,
    build_crm_provider,
    build_crm_service,
    build_dark_crm_service,
    normalize_email,
)
from api.services.crm.models import _now_iso


_MISSING = object()


@pytest.fixture(autouse=True)
def _isolate_public_lead_abuse_guard(client):
    """Keep route tests deterministic despite the process-local public lead limiter."""
    old_guard = getattr(client.app.state, "crm_public_abuse_guard", _MISSING)
    client.app.state.crm_public_abuse_guard = PublicLeadAbuseGuard(
        max_submissions=1000,
        window_seconds=3600,
    )
    yield
    if old_guard is _MISSING:
        delattr(client.app.state, "crm_public_abuse_guard")
    else:
        client.app.state.crm_public_abuse_guard = old_guard


# ---------------------------------------------------------------------------
# Test doubles: providers the shipped code does not contain (real-ish + raising)
# ---------------------------------------------------------------------------


class _LandingProvider(CRMSyncProvider):
    """A fake REAL provider that actually 'lands' the lead with an external id."""

    provider_name = "fake-landing"
    is_real = True

    def sync_lead(self, lead: Lead) -> CRMSyncResult:
        return CRMSyncResult(
            provider=self.provider_name,
            synced=True,
            is_real=True,
            external_id=f"rec-{lead.lead_id[-8:]}",
            synced_at=_now_iso(),
            note="fake landed",
        )


class _RaisingProvider(CRMSyncProvider):
    """A fake REAL provider whose network write blows up — must not lose the captured lead."""

    provider_name = "fake-raising"
    is_real = True

    def sync_lead(self, lead: Lead) -> CRMSyncResult:
        raise RuntimeError("external CRM exploded")


def _submission(email: str = "lead@example.com", **overrides: str) -> LeadSubmission:
    base = {
        "email": email,
        "name": "Ada Lovelace",
        "organization": "Analytical Engines Ltd",
        "message": "Interested in the CAS Harness.",
        "interest": "cas_harness",
    }
    base.update(overrides)
    return LeadSubmission(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# models — submission validation + the email normalizer
# ---------------------------------------------------------------------------


def test_normalize_email_trims_and_lowercases() -> None:
    assert normalize_email("  Foo@Bar.COM ") == "foo@bar.com"


def test_validated_accepts_a_usable_address() -> None:
    validated = _submission("Ada@Example.com").validated()
    # validated() trims but preserves case; normalization to lower happens at Lead construction.
    assert validated.email == "Ada@Example.com"


@pytest.mark.parametrize("bad", ["nope", "a@b", "@b.com", "a@.com", "a@b.", "  @x.com"])
def test_validated_refuses_uncontactable_addresses(bad: str) -> None:
    with pytest.raises(LeadValidationError):
        _submission(bad).validated()


def test_validated_coerces_metadata_to_str() -> None:
    sub = LeadSubmission(email="a@b.com", metadata={"utm": "spring", "n": 5})  # type: ignore[dict-item]
    cleaned = sub.validated()
    assert cleaned.metadata == {"utm": "spring", "n": "5"}


# ---------------------------------------------------------------------------
# models — THE honesty guard on CRMSyncResult
# ---------------------------------------------------------------------------


def test_sync_result_cannot_claim_synced_without_external_id() -> None:
    """A synced landing MUST carry the CRM's record id as evidence."""
    with pytest.raises(CRMStateError, match="external_id"):
        CRMSyncResult(provider="airtable", synced=True, is_real=True, external_id=None)


def test_sync_result_stub_cannot_report_a_real_landing() -> None:
    """synced=True with is_real=False is dishonesty-by-construction and is refused."""
    with pytest.raises(CRMStateError, match="is_real"):
        CRMSyncResult(provider="null", synced=True, is_real=False, external_id="rec-1")


def test_sync_result_real_landing_is_allowed() -> None:
    result = CRMSyncResult(provider="airtable", synced=True, is_real=True, external_id="rec-1")
    assert result.synced and result.is_real and result.external_id == "rec-1"


# ---------------------------------------------------------------------------
# models — Lead.from_submission + with_sync_result status mapping
# ---------------------------------------------------------------------------


def test_from_submission_captures_with_provenance() -> None:
    lead = Lead.from_submission(
        _submission("Ada@Example.com").validated(),
        source="public_web_form",
        trace_id="req-123",
        parent_ids=(),
    )
    assert lead.sync_status == "captured"
    assert lead.email == "ada@example.com"  # normalized at construction
    assert lead.source == "public_web_form"
    assert lead.trace_id == "req-123"
    assert lead.external_id is None
    assert lead.version == 1


def test_with_sync_result_dark_null_is_sync_pending() -> None:
    """The dark/null provider's no-op lands the lead at sync_pending — nothing left the building."""
    captured = Lead.from_submission(_submission().validated(), source="t", trace_id=None)
    annotated = captured.with_sync_result(NullCRMProvider().sync_lead(captured))
    assert annotated.sync_status == "sync_pending"
    assert annotated.external_id is None
    assert annotated.version == 2  # immutably bumped


def test_with_sync_result_real_landing_is_synced_with_external_id() -> None:
    captured = Lead.from_submission(_submission().validated(), source="t", trace_id=None)
    annotated = captured.with_sync_result(_LandingProvider().sync_lead(captured))
    assert annotated.sync_status == "synced"
    assert annotated.external_id is not None and annotated.external_id.startswith("rec-")


def test_with_sync_result_real_failure_is_sync_failed() -> None:
    captured = Lead.from_submission(_submission().validated(), source="t", trace_id=None)
    failed = CRMSyncResult(provider="airtable", synced=False, is_real=True, external_id=None)
    annotated = captured.with_sync_result(failed)
    assert annotated.sync_status == "sync_failed"
    assert annotated.external_id is None


def test_lead_dict_round_trips() -> None:
    lead = Lead.from_submission(
        _submission().validated(), source="t", trace_id="req-1", parent_ids=("lead-prev",)
    )
    again = Lead.from_dict(lead.to_dict())
    assert again == lead


# ---------------------------------------------------------------------------
# store — in-memory: version-regression guard, lookup by email
# ---------------------------------------------------------------------------


def test_in_memory_store_keeps_the_newer_version() -> None:
    """A stale lower-version write must never roll back a captured lead's status."""
    store = InMemoryLeadStore()
    captured = Lead.from_submission(_submission().validated(), source="t", trace_id=None)  # v1
    synced = captured.with_sync_result(NullCRMProvider().sync_lead(captured))  # v2 sync_pending
    store.save(synced)
    store.save(captured)  # stale v1 — must be rejected
    held = store.get(captured.lead_id)
    assert held is not None and held.version == 2 and held.sync_status == "sync_pending"


def test_in_memory_find_by_email_is_normalized() -> None:
    store = InMemoryLeadStore()
    lead = Lead.from_submission(_submission("Ada@Example.com").validated(), source="t", trace_id=None)
    store.save(lead)
    assert [l.lead_id for l in store.find_by_email("  ADA@example.COM ")] == [lead.lead_id]


# ---------------------------------------------------------------------------
# store — durable JSONL: survives a restart, append-only lineage
# ---------------------------------------------------------------------------


def test_jsonl_store_is_durable_across_reinstantiation(tmp_path) -> None:
    """The whole point of the durable store: a captured lead comes back after a 'restart'."""
    path = tmp_path / "leads.jsonl"
    store = JsonlFileLeadStore(path)
    captured = Lead.from_submission(_submission().validated(), source="t", trace_id=None)  # v1
    store.save(captured)
    store.save(captured.with_sync_result(NullCRMProvider().sync_lead(captured)))  # v2

    # A fresh store on the same path == a restarted process replaying the file.
    reopened = JsonlFileLeadStore(path)
    got = reopened.get(captured.lead_id)
    assert got is not None and got.version == 2 and got.sync_status == "sync_pending"


def test_jsonl_store_is_append_only(tmp_path) -> None:
    """Capture + sync annotation are two distinct lines — the lineage is recoverable from disk."""
    path = tmp_path / "leads.jsonl"
    store = JsonlFileLeadStore(path)
    captured = Lead.from_submission(_submission().validated(), source="t", trace_id=None)
    store.save(captured)
    store.save(captured.with_sync_result(NullCRMProvider().sync_lead(captured)))
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2  # nothing overwritten


# ---------------------------------------------------------------------------
# sync — the dark default + the fail-loud factory
# ---------------------------------------------------------------------------


def test_null_provider_never_reports_a_landing() -> None:
    result = NullCRMProvider().sync_lead(
        Lead.from_submission(_submission().validated(), source="t", trace_id=None)
    )
    assert result.synced is False and result.is_real is False and result.external_id is None


class _Settings:
    def __init__(
        self,
        provider: str,
        *,
        airtable_token: str = "",
        airtable_base_id: str = "",
        airtable_table_name: str = "Leads",
        airtable_api_base_url: str = "https://api.airtable.com/v0",
    ) -> None:
        self.crm_provider = provider
        self.crm_airtable_token = airtable_token
        self.crm_airtable_base_id = airtable_base_id
        self.crm_airtable_table_name = airtable_table_name
        self.crm_airtable_api_base_url = airtable_api_base_url


def test_build_provider_default_is_null() -> None:
    assert isinstance(build_crm_provider(_Settings("null")), NullCRMProvider)


def test_build_provider_fails_loud_for_airtable_without_credentials() -> None:
    """Airtable is implemented, but half-configured sync must fail at startup."""
    with pytest.raises(CRMConfigError, match="NC_AIRTABLE_TOKEN"):
        build_crm_provider(_Settings("airtable"))


def test_build_provider_airtable_with_credentials() -> None:
    provider = build_crm_provider(
        _Settings(
            "airtable",
            airtable_token="pat-secret",
            airtable_base_id="app123",
            airtable_table_name="Leads",
        )
    )
    assert isinstance(provider, AirtableCRMProvider)


def test_airtable_provider_posts_record_and_reports_external_id() -> None:
    """A lead earns synced only when Airtable returns a real record id."""
    captured_requests = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"records":[{"id":"recAirtable123","fields":{}}]}'

    def fake_open(request, timeout):
        captured_requests.append((request, timeout))
        return _Response()

    provider = AirtableCRMProvider(
        token="pat-secret",
        base_id="app123",
        table_name="Leads Table",
        http_open=fake_open,
    )
    lead = Lead.from_submission(
        _submission(metadata={"campaign": "alpha"}).validated(),
        source="public_web_form",
        trace_id="req-airtable",
    )

    result = provider.sync_lead(lead)

    assert result.synced is True
    assert result.is_real is True
    assert result.external_id == "recAirtable123"
    request, timeout = captured_requests[0]
    assert timeout == 15
    assert request.full_url.endswith("/app123/Leads%20Table")
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer pat-secret"
    payload = json.loads(request.data.decode("utf-8"))
    fields = payload["records"][0]["fields"]
    assert fields["Email"] == "lead@example.com"
    assert fields["Lead ID"] == lead.lead_id
    assert fields["Trace ID"] == "req-airtable"
    assert fields["Metadata JSON"] == '{"campaign":"alpha"}'


def test_airtable_provider_requires_record_id() -> None:
    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"records":[{"fields":{}}]}'

    provider = AirtableCRMProvider(
        token="pat-secret",
        base_id="app123",
        table_name="Leads",
        http_open=lambda request, timeout: _Response(),
    )
    lead = Lead.from_submission(_submission().validated(), source="public_web_form", trace_id=None)
    with pytest.raises(RuntimeError, match="record id"):
        provider.sync_lead(lead)


@pytest.mark.parametrize("provider", ["hubspot"])
def test_build_provider_fails_loud_for_unimplemented(provider: str) -> None:
    """Asking for a real CRM we have not built must raise, not silently no-op."""
    with pytest.raises(CRMConfigError, match="not yet implemented"):
        build_crm_provider(_Settings(provider))


def test_build_provider_rejects_unknown() -> None:
    with pytest.raises(CRMConfigError, match="unknown CRM provider"):
        build_crm_provider(_Settings("salesforce"))


# ---------------------------------------------------------------------------
# service — capture-before-sync, failure never loses the lead, lineage
# ---------------------------------------------------------------------------


def test_capture_with_dark_service_is_pending_not_synced() -> None:
    service = build_dark_crm_service()
    lead = service.capture(_submission(), source="web", trace_id="req-1")
    assert lead.sync_status == "sync_pending"
    assert lead.sync_status != "synced"
    # The captured lead is retrievable and traceable back to the request that created it.
    fetched = service.get_lead(lead.lead_id)
    assert fetched is not None and fetched.trace_id == "req-1"


def test_capture_rejects_unusable_email() -> None:
    service = build_dark_crm_service()
    with pytest.raises(LeadValidationError):
        service.capture(_submission("nope"), source="web", trace_id=None)
    assert service.list_leads() == []  # nothing junk was persisted


def test_capture_survives_a_provider_that_raises() -> None:
    """A provider blowing up must leave the lead CAPTURED and annotated sync_failed, not lost."""
    service = CRMService(InMemoryLeadStore(), _RaisingProvider())
    lead = service.capture(_submission(), source="web", trace_id="req-x")
    assert lead.sync_status == "sync_failed"
    assert service.get_lead(lead.lead_id) is not None  # the lead was NOT lost


def test_capture_with_real_provider_is_synced() -> None:
    service = CRMService(InMemoryLeadStore(), _LandingProvider())
    lead = service.capture(_submission(), source="web", trace_id=None)
    assert lead.sync_status == "synced" and lead.external_id is not None


def test_repeat_submission_is_linked_to_its_predecessor() -> None:
    """Lineage: the same email submitting twice links the second lead to the first."""
    service = build_dark_crm_service()
    first = service.capture(_submission("repeat@example.com"), source="web", trace_id=None)
    second = service.capture(_submission("repeat@example.com"), source="web", trace_id=None)
    assert second.parent_ids == (first.lead_id,)


def test_build_crm_service_default_is_dark() -> None:
    """Default settings => in-memory store + null provider (dark, capture-only)."""
    service = build_crm_service(_Settings("null"))
    assert isinstance(service.provider, NullCRMProvider)
    assert isinstance(service.store, InMemoryLeadStore)


# ---------------------------------------------------------------------------
# routes — public capture is open + authed; traceability survives HTTP
# ---------------------------------------------------------------------------


def _auth_headers() -> dict[str, str]:
    # Unique api_key per call => fresh rate-limit bucket + monthly counter, immune to the
    # suite-wide community-tier pollution other HTTP tests cause.
    token = create_token(sub="crm-test", api_key=f"crm-test-{uuid4().hex}")
    return {"Authorization": f"Bearer {token}"}


def test_public_capture_needs_no_auth_and_does_not_overclaim(client) -> None:
    email = f"public-{uuid4().hex}@example.com"
    resp = client.post("/api/crm/public/leads", json={"email": email, "name": "Web Lead"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["captured"] is True
    assert body["synced"] is False  # dark default never claims an external landing
    assert body["sync_status"] in ("captured", "sync_pending")
    assert "lead_id" in body


def test_public_capture_rejects_bad_email(client) -> None:
    resp = client.post("/api/crm/public/leads", json={"email": "not-an-email"})
    assert resp.status_code == 422


def test_public_capture_honeypot_rejects_before_capture(client) -> None:
    """Bots filling the hidden website field are rejected before any lead is persisted."""
    email = f"honeypot-{uuid4().hex}@example.com"
    resp = client.post(
        "/api/crm/public/leads",
        json={
            "email": email,
            "name": "Bot Lead",
            "website": "https://spam.example",
        },
    )
    assert resp.status_code == 400
    listing = client.get("/api/crm/leads", headers=_auth_headers())
    assert email not in {lead["email"] for lead in listing.json()["leads"]}


def test_public_capture_rate_limit_is_separate_from_api_key_limiter(client) -> None:
    """The public endpoint is anonymous, so it has its own per-client limiter."""
    client.app.state.crm_public_abuse_guard = PublicLeadAbuseGuard(
        max_submissions=1,
        window_seconds=60,
        now=lambda: 1000.0,
    )
    first = client.post(
        "/api/crm/public/leads",
        json={"email": f"first-{uuid4().hex}@example.com"},
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/api/crm/public/leads",
        json={"email": f"second-{uuid4().hex}@example.com"},
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "60"


def test_public_capture_records_trace_id(client) -> None:
    """The captured lead carries the request id as its trace_id — origin is recoverable."""
    email = f"trace-{uuid4().hex}@example.com"
    resp = client.post(
        "/api/crm/public/leads",
        json={"email": email},
        headers={"X-Request-ID": "req-traceable-1"},
    )
    lead_id = resp.json()["lead_id"]
    fetched = client.get(f"/api/crm/leads/{lead_id}", headers=_auth_headers())
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["trace_id"] == "req-traceable-1"


def test_sales_views_require_auth(client) -> None:
    assert client.get("/api/crm/leads").status_code == 401
    assert client.get("/api/crm/leads/whatever").status_code == 401


def test_authed_list_and_get_404(client) -> None:
    headers = _auth_headers()
    email = f"list-{uuid4().hex}@example.com"
    created = client.post("/api/crm/public/leads", json={"email": email})
    lead_id = created.json()["lead_id"]

    listing = client.get("/api/crm/leads", headers=headers)
    assert listing.status_code == 200
    assert lead_id in {lead["lead_id"] for lead in listing.json()["leads"]}

    assert client.get(f"/api/crm/leads/{uuid4().hex}", headers=headers).status_code == 404
