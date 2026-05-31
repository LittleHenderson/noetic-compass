from __future__ import annotations

import pytest

from api.errors import LLMError
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
async def test_api_runner_surfaces_connector_failure_as_unavailable(monkeypatch):
    def boom(provider, model=None):
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
