from __future__ import annotations

import pytest

from api.config import settings
from api.routes.evidence import _verify_packet_hashes, build_packet_for_trace
from api.services.cas_harness_live_worker_runner import run_live_worker_audit
from api.services.cas_harness_merged_evidence_packets import (
    reset_merged_fleet_evidence_packets_for_tests,
)


@pytest.fixture(autouse=True)
def _isolated_packet_store(tmp_path, monkeypatch):
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", raising=False)
    reset_merged_fleet_evidence_packets_for_tests()
    yield
    reset_merged_fleet_evidence_packets_for_tests()


@pytest.mark.asyncio
async def test_live_worker_runner_writes_packet_loadable_harvest_record(monkeypatch):
    async def fake_dump(worker_base, payload):
        assert worker_base == "http://worker.test"
        assert payload["model_id"] == "EleutherAI/pythia-160m"
        return {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "runtime": "real_pythia",
                    },
                },
                {
                    "type": "token",
                    "token_index": 0,
                    "token": " Hello",
                    "confidence": 0.7,
                    "top_activated_neurons": [{"layer": 1, "index": 2, "activation": 0.3}],
                    "mode7_attribution": [],
                },
                {
                    "type": "token",
                    "token_index": 1,
                    "token": " world",
                    "confidence": 0.8,
                    "top_activated_neurons": [],
                    "mode7_attribution": [],
                },
                {
                    "type": "neuron_covers",
                    "per_class_neuron_covers": {"F1": [{"label": "L1N2"}]},
                },
                {"type": "complete", "total_tokens": 2},
            ]
        }

    monkeypatch.setattr(settings, "atlas_live_worker_url", "http://worker.test")
    monkeypatch.setattr(
        "api.services.cas_harness_live_worker_runner._post_worker_dump",
        fake_dump,
    )

    result = await run_live_worker_audit(
        audit_id="cas-audit-live001",
        model_id="EleutherAI/pythia-160m",
        prompt="Audit this.",
        audit_mode="BALANCED",
        selected_modules=["active_trace"],
    )

    packet = build_packet_for_trace(result.trace_id)
    verify = _verify_packet_hashes(packet)
    chips = {chip["id"]: chip["status"] for chip in result.proof_chips}

    assert packet.trace_id == result.trace_id
    assert packet.input["text"] == "Audit this."
    assert packet.output["text"] == " Hello world"
    assert packet.readout["confidence"] == pytest.approx(0.75)
    assert packet.live_audit["event_counts"] == {
        "manifest": 1,
        "token": 2,
        "neuron_covers": 1,
        "complete": 1,
    }
    assert verify.overall == "all_match"
    assert chips == {
        "model_proof": "present",
        "cas_readout": "present",
        "causal_proof": "unavailable",
        "control_proof": "unavailable",
        "output_proof": "present",
        "packet_proof": "present",
    }
