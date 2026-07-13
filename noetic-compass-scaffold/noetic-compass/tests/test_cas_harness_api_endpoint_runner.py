from __future__ import annotations

import json

import pytest

from api.errors import LLMError
from api.llm_connectors.base import LLMResponse
from api.routes.evidence import _verify_packet_hashes, build_packet_for_trace
from api.services.cas_harness_api_endpoint_runner import (
    ApiEndpointRunnerUnavailable,
    _code_commit_sha,
    run_api_endpoint_audit,
)
from api.services.cas_harness_harvest import iter_harvest_records
from api.services.cas_harness_merged_evidence_packets import (
    reset_merged_fleet_evidence_packets_for_tests,
)


@pytest.fixture(autouse=True)
def _isolated_packet_store(tmp_path, monkeypatch):
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("CAS_HARNESS_HARVEST_STORE_DIR", str(tmp_path / "harvest"))
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", raising=False)
    reset_merged_fleet_evidence_packets_for_tests()
    yield
    reset_merged_fleet_evidence_packets_for_tests()


@pytest.mark.asyncio
async def test_api_runner_writes_output_only_packet_and_harvest_record():
    result = await run_api_endpoint_audit(
        audit_id="cas-audit-api001",
        provider="mock",
        model_id="mock-cas-v1",
        prompt="Audit this closed model.",
        audit_mode="BALANCED",
        selected_modules=["active_trace"],
        endpoint_url="https://api.example.com/v1/chat",
    )

    packet = build_packet_for_trace(result.trace_id)
    verify = _verify_packet_hashes(packet)
    chips = {chip["id"]: chip["status"] for chip in result.proof_chips}

    assert packet.trace_id == result.trace_id
    assert packet.trace_id.startswith("cas-api-api001-")
    assert packet.input["text"] == "Audit this closed model."
    assert packet.output["text"]  # mock connector returns CAS-formatted text
    # A closed API exposes no activations: readout/ablation/controls unavailable.
    assert packet.readout["status"] == "unavailable"
    assert packet.ablation["status"] == "unavailable"
    assert packet.matched_controls["status"] == "unavailable"
    assert packet.live_audit["provider"] == "mock"
    assert verify.overall == "all_match"
    assert packet.provenance["code_commit_sha"] == _code_commit_sha()

    # Honest scope label so the UI never implies internal access on a closed API.
    assert packet.audit_scope["kind"] == "output_only_api_harvest"
    assert packet.audit_scope["internal_activation_access"] is False
    assert packet.audit_scope["verdict_disposition"] == "held_for_human_review"
    assert "Output-only harvest" in packet.audit_scope["label"]

    # Honest proof-chip posture: model + output present, the three activation-
    # dependent proofs unavailable. This keeps the verdict gate at human review.
    assert chips == {
        "model_proof": "present",
        "cas_readout": "unavailable",
        "causal_proof": "unavailable",
        "control_proof": "unavailable",
        "output_proof": "present",
        "packet_proof": "present",
    }

    harvest = list(iter_harvest_records())
    assert len(harvest) == 1
    assert harvest[0]["trace_id"] == result.trace_id
    assert harvest[0]["output"]["text"] == packet.output["text"]
    assert harvest[0]["join"] == {"key": "trace_id", "pairs_with": "native_nl.v1"}
    # Mock output is synthetic — it must be flagged demo fallback so it never
    # silently enters a training corpus as real model signal.
    assert harvest[0]["model_io_is_demo_fallback"] is True
    assert harvest[0]["policy"]["foreign_output_retained"] is True


@pytest.mark.asyncio
async def test_api_runner_rejects_unknown_provider():
    with pytest.raises(ApiEndpointRunnerUnavailable):
        await run_api_endpoint_audit(
            audit_id="cas-audit-api002",
            provider="not_a_provider",
            model_id="whatever",
            prompt="Audit this.",
            audit_mode="BALANCED",
            selected_modules=["active_trace"],
        )


@pytest.mark.asyncio
async def test_api_runner_threads_byok_key_to_connector_without_persisting(monkeypatch):
    # Bring-your-own-key: the customer's ephemeral secret must reach the
    # connector for this one call but never land in the packet or harvest.
    from api.llm_connectors.mock_connector import MockLLMConnector

    captured: dict[str, object] = {}

    def fake_get_connector(provider, model=None, *, api_key_override=None):
        captured["provider"] = provider
        captured["model"] = model
        captured["api_key_override"] = api_key_override
        return MockLLMConnector()

    monkeypatch.setattr(
        "api.services.cas_harness_api_endpoint_runner.get_connector",
        fake_get_connector,
    )

    secret = "sk-customer-byok-do-not-store-9z9z9z"
    result = await run_api_endpoint_audit(
        audit_id="cas-audit-byok01",
        provider="openai",
        model_id="gpt-4",
        prompt="Audit this closed model with my own key.",
        audit_mode="BALANCED",
        selected_modules=["active_trace"],
        endpoint_url="https://api.example.com/v1/chat",
        api_key=secret,
    )

    # The ephemeral key reached the connector for this single call.
    assert captured["api_key_override"] == secret
    assert captured["provider"] == "openai"

    packet = build_packet_for_trace(result.trace_id)
    # Credential MODE is recorded; the secret itself is not.
    assert packet.model["manifest"]["credential_mode"] == "customer_ephemeral_key"
    assert packet.live_audit["credential_mode"] == "customer_ephemeral_key"

    # The secret must appear nowhere in the persisted packet or harvest corpus.
    assert secret not in json.dumps(packet.model_dump(mode="json"))
    harvest = list(iter_harvest_records())
    assert len(harvest) == 1
    assert secret not in json.dumps(harvest[0])


@pytest.mark.asyncio
async def test_api_runner_surfaces_connector_failure_as_unavailable(monkeypatch):
    def boom(provider, model=None, *, api_key_override=None):
        raise LLMError("Anthropic API key not configured", provider="anthropic")

    monkeypatch.setattr(
        "api.services.cas_harness_api_endpoint_runner.get_connector", boom
    )
    with pytest.raises(ApiEndpointRunnerUnavailable):
        await run_api_endpoint_audit(
            audit_id="cas-audit-api003",
            provider="anthropic",
            model_id="claude-sonnet-4-6",
            prompt="Audit this.",
            audit_mode="BALANCED",
            selected_modules=["active_trace"],
        )


@pytest.mark.asyncio
async def test_api_runner_checkpoints_boundaries_and_forwards_stable_key(monkeypatch):
    events: list[str] = []
    captured: dict[str, object] = {}

    class CapturingConnector:
        async def generate(self, prompt, system_prompt="", **kwargs):
            events.append("provider_called")
            captured.update(kwargs)
            return LLMResponse(text="checkpointed output", model="provider-model")

    monkeypatch.setattr(
        "api.services.cas_harness_api_endpoint_runner.get_connector",
        lambda *_args, **_kwargs: CapturingConnector(),
    )
    key = "cas-run-stable-provider-operation"
    result = await run_api_endpoint_audit(
        audit_id="cas-audit-provider-checkpoints",
        provider="openai",
        model_id="gpt-provider",
        prompt="checkpoint every provider boundary",
        audit_mode="BALANCED",
        selected_modules=["active_trace"],
        provider_idempotency_key=key,
        on_request_started=lambda: events.append("request_started"),
        on_provider_completed=lambda checkpoint: events.append(
            f"provider_completed:{checkpoint['trace_id']}"
        ),
        on_evidence_persisted=lambda trace_id: events.append(
            f"evidence_persisted:{trace_id}"
        ),
    )

    assert captured == {"idempotency_key": key, "retry_attempts": 1}
    assert events == [
        "request_started",
        "provider_called",
        f"provider_completed:{result.trace_id}",
        f"evidence_persisted:{result.trace_id}",
    ]
    assert result.evidence_packet["live_audit"]["provider_idempotency"] == {
        "key": key,
        "scope": "logical_cas_audit_run",
        "provider_enforcement": "not_assumed",
    }
