"""Evidence Packet AI Explainer — verdict-fidelity + tenant-ownership honesty tests.

Authoritative design: docs/design/cas_harness_evidence_packet_ai_explainer_spec.md
(§2 guardrails, §6 citations, §7 contract, §8 backend, §10 honesty test cases).

This file covers the two non-negotiable cores of the "Explain this packet" backend:

* **Tenant ownership (G3)** — a trace the caller's tenant does not own returns 404, and the
  redacted projection is NEVER built (the projection builder is asserted un-called). Account-mode
  integration via a real ``SqliteStateStore`` + ownership ledger, mirroring
  ``tests/test_evidence_ownership.py`` / ``tests/test_accounts_invites.py``.

* **Verdict fidelity (G1) + IP containment (G2), fail-closed** — exercised at the service layer
  (``explain_evidence``) with a mocked Gemini connector and a stub projection module:
    - verdict-echo guard: a corrupted model ``verdict_echo`` != EP verdict is DISCARDED (degraded,
      raw verdict only, never the inflated reading);
    - no-upgrade: a FLAG_FOR_HUMAN_REVIEW packet never yields pass/accept/approved language;
    - no-suppress-softening: a SUPPRESS packet is never described as acceptable/minor;
    - scope-carried: a scoped-validation ACCEPT is never rendered as a customer-production ACCEPT
      (the scope qualifier survives into the output);
    - deny-list: a methodology leak in the model output fails closed.

Run ONLY this file:
    python -m pytest tests/test_ep_explainer_endpoint.py -q
"""

from __future__ import annotations

import sys
import uuid
from types import ModuleType, SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.config import settings
from api.llm_connectors.base import LLMResponse
from api.services.accounts.store import AccountStore
from api.services.evidence_ownership import record_evidence_ownership
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.sessions import SessionStore
from api.services import explainer as explainer_service

_PROJECTION_MODULE = "api.services.cas_harness_evidence_projection"


# ===========================================================================
# Helpers — fake projection module + fake Gemini connector.
# ===========================================================================


def _install_fake_projection(monkeypatch, recorder: dict | None = None):
    """Install a stub ``cas_harness_evidence_projection`` module exposing ``build_packet_projection``.

    The real module is owned by another agent and may be absent on this branch; the service imports
    it lazily by name, so we inject a stub into ``sys.modules`` for the duration of the test. When a
    ``recorder`` dict is passed, the stub records whether it was called and with what — used by the
    ownership-404 test to PROVE the projection is never built for a non-owned trace.
    """
    module = ModuleType(_PROJECTION_MODULE)

    def build_packet_projection(ep):  # noqa: ANN001 — mirrors the real signature ep -> dict
        if recorder is not None:
            recorder["called"] = True
            recorder["ep"] = ep
        # Allow-list-shaped projection (spec §4): verdict + scope + customer-facing chips only.
        projection = {
            "verdict": ep.get("verdict") if isinstance(ep, dict) else None,
            "proof_chips": ep.get("proof_chips") if isinstance(ep, dict) else [],
        }
        for key in ("decision_scope", "validation_scope", "is_customer_production"):
            if isinstance(ep, dict) and key in ep:
                projection[key] = ep[key]
        return projection

    module.build_packet_projection = build_packet_projection  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, _PROJECTION_MODULE, module)
    return module


class _FakeConnector:
    """Mock GoogleConnector that returns a scripted text and records the prompts it received."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.prompt = ""
        self.system_prompt = ""

    async def generate(self, prompt: str, system_prompt: str = "", **kwargs):  # noqa: ANN003
        self.prompt = prompt
        self.system_prompt = system_prompt
        return LLMResponse(text=self._text, model="gemini-test")


@pytest.fixture(autouse=True)
def _google_key(monkeypatch):
    """Service requires a key OR an injected connector. We always inject a connector, but set a key
    too so the dark-default branch is not accidentally taken in the connector-injected tests."""
    monkeypatch.setattr(settings, "google_api_key", "test-key")


# ===========================================================================
# (G1/G2) SERVICE-LAYER FAIL-CLOSED — explain_evidence with a mocked connector.
# ===========================================================================


@pytest.mark.asyncio
async def test_faithful_flag_packet_passes_through(monkeypatch):
    """Happy path: a faithful FLAG echo + cited segments survives and is returned verbatim."""
    _install_fake_projection(monkeypatch)
    ep = {
        "trace_id": "t-flag-ok",
        "verdict": "FLAG_FOR_HUMAN_REVIEW",
        "decision_scope": "stage9_40e_validation_packet",
        "proof_chips": [{"id": "causal_proof", "status": "verified"}],
    }
    model_json = (
        '{"verdict_echo": "FLAG_FOR_HUMAN_REVIEW", '
        '"segments": [{"text": "A human must review this audit.", "refs": ["verdict"]}], '
        '"investigate_next": [{"text": "Reproduce the flagged input.", "refs": ["proof_chips.0.status"]}]}'
    )
    conn = _FakeConnector(model_json)

    result = await explainer_service.explain_evidence(ep, trace_id="t-flag-ok", connector=conn)

    assert result.verdict_echo == "FLAG_FOR_HUMAN_REVIEW"
    assert result.used_gemini is True
    assert len(result.segments) == 1
    assert result.segments[0].refs == ("verdict",)
    assert result.safety_mode == "packet_projection_only"
    assert "authoritative record" in result.disclaimer
    # The strict system prompt and the redacted projection both reached the model.
    assert "VERDICT FIDELITY" in conn.system_prompt
    assert "PACKET PROJECTION" in conn.prompt


@pytest.mark.asyncio
async def test_verdict_echo_guard_discards_inflated_echo(monkeypatch):
    """Verdict-echo guard (spec §10.7): a model that echoes ACCEPT for a FLAG packet is DISCARDED.

    The degraded result carries ONLY the packet's real verdict (FLAG_FOR_HUMAN_REVIEW) with no
    segments — the inflated reading is never rendered.
    """
    _install_fake_projection(monkeypatch)
    ep = {"trace_id": "t-corrupt", "verdict": "FLAG_FOR_HUMAN_REVIEW", "proof_chips": []}
    # Corrupted/inflated echo + pass language that must NEVER be surfaced.
    model_json = (
        '{"verdict_echo": "ACCEPT", '
        '"segments": [{"text": "Your audit passed and is approved.", "refs": ["verdict"]}], '
        '"investigate_next": []}'
    )
    conn = _FakeConnector(model_json)

    result = await explainer_service.explain_evidence(ep, trace_id="t-corrupt", connector=conn)

    # Fail closed: the API surfaces the packet's real verdict, discards the segments entirely.
    assert result.verdict_echo == "FLAG_FOR_HUMAN_REVIEW"
    assert result.segments == ()
    assert result.investigate_next == ()
    # The inflated "ACCEPT" / "passed" / "approved" text never appears in any returned field.
    blob = " ".join(seg.text for seg in result.segments)
    assert "ACCEPT" not in blob
    assert "approved" not in blob.lower()


@pytest.mark.asyncio
async def test_no_upgrade_flag_packet_has_no_pass_language(monkeypatch):
    """No-upgrade (spec §10.1): a FLAG packet's faithful output carries no pass/accept/approved text."""
    _install_fake_projection(monkeypatch)
    ep = {"trace_id": "t-flag", "verdict": "FLAG_FOR_HUMAN_REVIEW", "proof_chips": []}
    model_json = (
        '{"verdict_echo": "FLAG_FOR_HUMAN_REVIEW", '
        '"segments": [{"text": "This returned FLAG_FOR_HUMAN_REVIEW; a person must review it.", '
        '"refs": ["verdict"]}], "investigate_next": []}'
    )
    conn = _FakeConnector(model_json)

    result = await explainer_service.explain_evidence(ep, trace_id="t-flag", connector=conn)

    assert result.verdict_echo == "FLAG_FOR_HUMAN_REVIEW"
    text = " ".join(seg.text for seg in result.segments).lower()
    for banned in ("passed", "approved", " accept", "certified", "cleared"):
        assert banned not in text


@pytest.mark.asyncio
async def test_no_suppress_softening(monkeypatch):
    """No-suppress-softening (spec §10.2): a SUPPRESS packet's verdict is echoed exactly, not softened."""
    _install_fake_projection(monkeypatch)
    ep = {"trace_id": "t-suppress", "verdict": "SUPPRESS", "proof_chips": []}
    model_json = (
        '{"verdict_echo": "SUPPRESS", '
        '"segments": [{"text": "This audit returned SUPPRESS.", "refs": ["verdict"]}], '
        '"investigate_next": []}'
    )
    conn = _FakeConnector(model_json)

    result = await explainer_service.explain_evidence(ep, trace_id="t-suppress", connector=conn)

    assert result.verdict_echo == "SUPPRESS"
    text = " ".join(seg.text for seg in result.segments).lower()
    for banned in ("acceptable", "minor", "no big deal", "fine", "harmless"):
        assert banned not in text


@pytest.mark.asyncio
async def test_softened_suppress_echo_is_discarded(monkeypatch):
    """A model that re-labels SUPPRESS as ACCEPT (softening) trips the verdict-echo guard."""
    _install_fake_projection(monkeypatch)
    ep = {"trace_id": "t-suppress-soft", "verdict": "SUPPRESS", "proof_chips": []}
    model_json = (
        '{"verdict_echo": "ACCEPT", '
        '"segments": [{"text": "This is only a minor, acceptable issue.", "refs": ["verdict"]}], '
        '"investigate_next": []}'
    )
    conn = _FakeConnector(model_json)

    result = await explainer_service.explain_evidence(ep, trace_id="t-suppress-soft", connector=conn)

    # Discarded: the real verdict is carried, the softening text is gone.
    assert result.verdict_echo == "SUPPRESS"
    assert result.segments == ()


@pytest.mark.asyncio
async def test_scope_carried_scoped_validation_not_production(monkeypatch):
    """Scope-carried (spec §10.3): a scoped-validation ACCEPT is never a customer-production ACCEPT.

    The packet's scope qualifier (``decision_scope=stage9_40e_validation_packet``,
    ``is_customer_production=False``) reaches the model in the projection, and the faithful output
    keeps the scope wording. The verdict echo is the literal ACCEPT, but the scope is explicit.
    """
    _install_fake_projection(monkeypatch)
    ep = {
        "trace_id": "t-scoped",
        "verdict": "ACCEPT",
        "decision_scope": "stage9_40e_validation_packet",
        "is_customer_production": False,
        "proof_chips": [],
    }
    model_json = (
        '{"verdict_echo": "ACCEPT", '
        '"segments": [{"text": "This is a SCOPED-VALIDATION ACCEPT over fixed validation cases '
        '(decision_scope stage9_40e_validation_packet), not a customer-production ACCEPT.", '
        '"refs": ["verdict", "decision_scope"]}], '
        '"investigate_next": []}'
    )
    conn = _FakeConnector(model_json)

    result = await explainer_service.explain_evidence(ep, trace_id="t-scoped", connector=conn)

    assert result.verdict_echo == "ACCEPT"
    # The scope qualifier was sent to the model (projection carried it).
    assert "stage9_40e_validation_packet" in conn.prompt
    assert "is_customer_production" in conn.prompt
    # And it survived into the rendered reading.
    text = " ".join(seg.text for seg in result.segments)
    assert "scoped" in text.lower() or "validation" in text.lower()
    assert "decision_scope" in result.segments[0].refs


@pytest.mark.asyncio
async def test_deny_list_leak_fails_closed(monkeypatch):
    """Deny-list (spec §10.5): a methodology token in the model output fails closed (degraded)."""
    _install_fake_projection(monkeypatch)
    ep = {"trace_id": "t-leak", "verdict": "FLAG_FOR_HUMAN_REVIEW", "proof_chips": []}
    model_json = (
        '{"verdict_echo": "FLAG_FOR_HUMAN_REVIEW", '
        '"segments": [{"text": "The NCCS weights and dial values drove this.", "refs": ["verdict"]}], '
        '"investigate_next": []}'
    )
    conn = _FakeConnector(model_json)

    result = await explainer_service.explain_evidence(ep, trace_id="t-leak", connector=conn)

    # Degraded: methodology never surfaces.
    assert result.verdict_echo == "FLAG_FOR_HUMAN_REVIEW"
    assert result.segments == ()


@pytest.mark.asyncio
async def test_uncited_segments_are_dropped(monkeypatch):
    """Every-segment-cited (spec §10.4): a segment with empty refs is dropped; cited ones survive."""
    _install_fake_projection(monkeypatch)
    ep = {"trace_id": "t-uncited", "verdict": "FLAG_FOR_HUMAN_REVIEW", "proof_chips": []}
    model_json = (
        '{"verdict_echo": "FLAG_FOR_HUMAN_REVIEW", '
        '"segments": ['
        '{"text": "Uncited claim that must be dropped.", "refs": []}, '
        '{"text": "Cited claim that survives.", "refs": ["verdict"]}'
        '], "investigate_next": []}'
    )
    conn = _FakeConnector(model_json)

    result = await explainer_service.explain_evidence(ep, trace_id="t-uncited", connector=conn)

    assert len(result.segments) == 1
    assert result.segments[0].text == "Cited claim that survives."
    assert all(seg.refs for seg in result.segments)


@pytest.mark.asyncio
async def test_dark_default_no_key_degrades(monkeypatch):
    """Dark default (spec §10.9): no key + no connector -> degraded raw-verdict-only, no Gemini call."""
    _install_fake_projection(monkeypatch)
    monkeypatch.setattr(settings, "google_api_key", "")
    ep = {"trace_id": "t-dark", "verdict": "SUPPRESS", "proof_chips": []}

    result = await explainer_service.explain_evidence(ep, trace_id="t-dark")

    assert result.used_gemini is False
    assert result.verdict_echo == "SUPPRESS"
    assert result.segments == ()


# ===========================================================================
# (G3) ROUTE-LAYER TENANT OWNERSHIP — account-mode integration, real store.
# ===========================================================================


@pytest.fixture
def tenant_iso_client(tmp_path, monkeypatch):
    """A TestClient with accounts_enabled=True, durable account/session stores AND a state ledger on
    app.state, all sharing ONE SqliteStateStore backend. Mirrors test_evidence_ownership.py.

    Yields ``(client, account_store, backend)``.
    """
    from api.main import app

    backend = SqliteStateStore(tmp_path / f"{uuid.uuid4().hex}.db")
    acct_store = AccountStore(backend)
    session_store = SessionStore(backend)

    with TestClient(app) as client:
        monkeypatch.setattr(settings, "accounts_enabled", True)
        prev_ledger = getattr(app.state, "state_ledger", None)
        app.state.account_store = acct_store
        app.state.session_store = session_store
        app.state.state_ledger = SimpleNamespace(store=backend)
        try:
            yield client, acct_store, backend
        finally:
            app.state.account_store = None
            app.state.session_store = None
            app.state.state_ledger = prev_ledger
            backend.close()


def _provision_login(client, store, *, code, identity, role, tenant_id):
    """Create+redeem an invite and log in; returns the account-mode bearer headers + account."""
    invite = store.create_invite(code=code, role=role, tenant_id=tenant_id)
    account = store.redeem_invite(code=invite.code, email_or_username=identity)
    resp = client.post("/auth/token", json={"username": identity})
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}, account


# A real, registry-discoverable Stage 9 40E trace (FLAG_FOR_HUMAN_REVIEW); reused from the evidence
# ownership tests so the route resolves a genuine on-disk packet.
_STAGE9_FLAG_TRACE_ID = "pythia-160m-stage9-40e-readout-20260531"


def test_route_requires_auth(client):
    """JWT-protected like /explainer/chat: no token -> 401 (the middleware gates it)."""
    resp = client.post(f"/explainer/evidence/{_STAGE9_FLAG_TRACE_ID}")
    assert resp.status_code == 401


def test_ownership_404_projection_never_built(tenant_iso_client, monkeypatch):
    """G3 (spec §10.6): a trace tenant B does not own -> 404, and the projection is NEVER built.

    Tenant A owns the trace; tenant B asks to explain it. The stub projection records whether it was
    called; the assertion proves it was not — no projection is built for a non-owned trace.
    """
    client, store, backend = tenant_iso_client
    recorder: dict = {}
    _install_fake_projection(monkeypatch, recorder)

    # Tenant A owns the Stage 9 trace.
    _, account_a = _provision_login(
        client, store, code="ep-a-1", identity="a@example.com", role="member", tenant_id="tenant-A"
    )
    record_evidence_ownership(
        backend, tenant_id="tenant-A", account_id=account_a.account_id, trace_id=_STAGE9_FLAG_TRACE_ID
    )

    # Tenant B logs in but owns nothing.
    headers_b, _ = _provision_login(
        client, store, code="ep-b-1", identity="b@example.com", role="operator", tenant_id="tenant-B"
    )

    resp = client.post(f"/explainer/evidence/{_STAGE9_FLAG_TRACE_ID}", headers=headers_b)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "trace_id not found"
    # The load-bearing assertion: no projection was built for the non-owned trace.
    assert recorder.get("called") is not True


def test_ownership_owner_reaches_handler_flag_carried(tenant_iso_client, monkeypatch):
    """The owning tenant reaches the handler; the real FLAG packet's verdict is carried end-to-end.

    The Gemini connector is mocked at the service boundary (no key needed). The owner gets a 200
    whose ``verdict_echo`` is the packet's real FLAG_FOR_HUMAN_REVIEW, with the §7 contract shape.
    """
    client, store, backend = tenant_iso_client
    _install_fake_projection(monkeypatch)

    # Mock the connector the service would construct, so no real Gemini/key is used and the echo is
    # faithful to the on-disk packet's verdict.
    model_json = (
        '{"verdict_echo": "FLAG_FOR_HUMAN_REVIEW", '
        '"segments": [{"text": "A human must review this audit.", "refs": ["verdict"]}], '
        '"investigate_next": [{"text": "Reproduce the flagged input.", "refs": ["proof_chips"]}]}'
    )
    monkeypatch.setattr(settings, "google_api_key", "test-key")
    monkeypatch.setattr(
        explainer_service, "GoogleConnector", lambda *a, **k: _FakeConnector(model_json)
    )

    headers_a, account_a = _provision_login(
        client, store, code="ep-own-1", identity="owner@example.com", role="member",
        tenant_id="tenant-OWN",
    )
    record_evidence_ownership(
        backend, tenant_id="tenant-OWN", account_id=account_a.account_id,
        trace_id=_STAGE9_FLAG_TRACE_ID,
    )

    resp = client.post(f"/explainer/evidence/{_STAGE9_FLAG_TRACE_ID}", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["trace_id"] == _STAGE9_FLAG_TRACE_ID
    assert body["verdict_echo"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["safety_mode"] == "packet_projection_only"
    assert "authoritative record" in body["disclaimer"]
    # §7 contract shape: every segment carries non-empty refs.
    assert body["segments"] and all(seg["refs"] for seg in body["segments"])
    # No pass/accept language anywhere in the rendered reading.
    rendered = " ".join(seg["text"] for seg in body["segments"]).lower()
    assert "passed" not in rendered and "approved" not in rendered


def test_account_mode_no_identity_is_401(tenant_iso_client):
    """Account mode + no bearer token -> the middleware 401s before the ownership guard runs."""
    client, _store, _backend = tenant_iso_client
    resp = client.post(f"/explainer/evidence/{_STAGE9_FLAG_TRACE_ID}")
    assert resp.status_code == 401


def test_owned_but_missing_trace_is_404(tenant_iso_client, monkeypatch):
    """Owner of a recorded trace_id that resolves to no on-disk packet -> 404 (no 500)."""
    client, store, backend = tenant_iso_client
    recorder: dict = {}
    _install_fake_projection(monkeypatch, recorder)

    bogus_trace = "owned-but-no-packet-xyz-42"
    headers_a, account_a = _provision_login(
        client, store, code="ep-miss-1", identity="miss@example.com", role="member",
        tenant_id="tenant-MISS",
    )
    record_evidence_ownership(
        backend, tenant_id="tenant-MISS", account_id=account_a.account_id, trace_id=bogus_trace
    )

    resp = client.post(f"/explainer/evidence/{bogus_trace}", headers=headers_a)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "trace_id not found"
    # Ownership passed but the packet does not exist, so the projection was still never built.
    assert recorder.get("called") is not True
