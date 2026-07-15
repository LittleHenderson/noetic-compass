from __future__ import annotations

import json

import httpx
import pytest

from api.config import settings
from api.routes.evidence import _verify_packet_hashes, build_packet_for_trace
from api.services.cas_harness_harvest import iter_harvest_records
from api.services.cas_harness_live_worker_runner import (
    LiveAuditRunnerResult,
    LiveAuditRunnerUnavailable,
    _ablation_block_from_events,
    _code_commit_sha,
    _control_block_from_events,
    _post_worker_dump,
    _proof_chips_for_live_packet,
    live_worker_result_from_checkpoint,
    persist_live_worker_result,
    run_live_worker_audit,
)
from api.services.cas_harness_merged_evidence_packets import (
    reset_merged_fleet_evidence_packets_for_tests,
)


@pytest.fixture(autouse=True)
def _isolated_packet_store(tmp_path, monkeypatch):
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("CAS_HARNESS_HARVEST_STORE_DIR", str(tmp_path / "harvest"))
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", raising=False)
    monkeypatch.setattr(settings, "atlas_live_worker_token", "test-worker-secret")
    reset_merged_fleet_evidence_packets_for_tests()
    yield
    reset_merged_fleet_evidence_packets_for_tests()


@pytest.mark.asyncio
async def test_live_worker_runner_blocks_remote_url_without_service_token(monkeypatch):
    monkeypatch.setattr(settings, "atlas_live_worker_url", "https://worker.example")
    monkeypatch.setattr(settings, "atlas_live_worker_token", "")

    with pytest.raises(LiveAuditRunnerUnavailable, match="worker_token_required"):
        await run_live_worker_audit(
            audit_id="audit-insecure-worker",
            model_id="EleutherAI/pythia-160m",
            prompt="Do not send this prompt to an unprotected worker.",
            audit_mode="BALANCED",
            selected_modules=["active_trace"],
        )


@pytest.mark.parametrize(
    ("events", "error"),
    (
        ([{"type": "complete", "total_tokens": 0}], "did not begin"),
        (
            [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "is_real_model": False,
                    },
                }
            ],
            "did not prove real model weights",
        ),
        (
            [
                {
                    "type": "manifest",
                    "manifest": {"model_id": "EleutherAI/pythia-160m"},
                }
            ],
            "did not prove real model weights",
        ),
        (
            [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "attacker/mismatched-model",
                        "is_real_model": True,
                    },
                }
            ],
            "does not match requested target",
        ),
        (
            [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "is_real_model": True,
                    },
                },
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "attacker/conflicting-model",
                        "is_real_model": True,
                    },
                },
            ],
            "multiple manifest events",
        ),
    ),
    ids=("missing", "demo", "missing-real-flag", "wrong-model", "conflicting"),
)
@pytest.mark.asyncio
async def test_live_worker_runner_rejects_unbound_real_model_dumps_before_persistence(
    monkeypatch, tmp_path, events, error
):
    callbacks: list[str] = []

    async def fake_dump(_worker_base, _payload):
        return {
            "billing_measurement_receipt": {"schema_version": "untrusted"},
            "events": events,
        }

    monkeypatch.setattr(settings, "atlas_live_worker_url", "http://worker.test")
    monkeypatch.setattr(
        "api.services.cas_harness_live_worker_runner._post_worker_dump", fake_dump
    )

    with pytest.raises(LiveAuditRunnerUnavailable, match=error):
        await run_live_worker_audit(
            audit_id="cas-audit-hostile-manifest",
            model_id="EleutherAI/pythia-160m",
            prompt="Do not persist unbound output.",
            audit_mode="BALANCED",
            selected_modules=["active_trace"],
            billing_measurement_context={
                "tenant_id": "tenant-a",
                "billing_account_id": "acct-a",
                "run_id": "attempt-a",
            },
            on_billing_measurement_receipt=lambda _value: callbacks.append("billing"),
            on_provider_completed=lambda _value: callbacks.append("provider"),
            on_evidence_persisted=lambda _value: callbacks.append("evidence"),
        )

    assert callbacks == []
    assert list(iter_harvest_records()) == []
    assert list(tmp_path.rglob("*.json")) == []
    assert list(tmp_path.rglob("*.jsonl")) == []


def test_checkpoint_recovery_rejects_demo_manifest_before_persistence(tmp_path):
    packet = {
        "trace_id": "cas-checkpoint-demo-manifest",
        "model": {"model_key": "EleutherAI/pythia-160m"},
        "live_audit": {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "is_real_model": False,
                    },
                }
            ]
        },
    }
    checkpoint = {
        "schema_version": "cas_harness_provider_result_checkpoint.v1",
        "runner": "live_worker",
        "trace_id": "cas-checkpoint-demo-manifest",
        "evidence_packet": packet,
        "proof_chips": [],
        "verifier_decision": None,
        "message": "Untrusted checkpoint",
        "audit_scope": None,
    }

    with pytest.raises(LiveAuditRunnerUnavailable, match="real model weights"):
        live_worker_result_from_checkpoint(checkpoint)
    with pytest.raises(LiveAuditRunnerUnavailable, match="real model weights"):
        persist_live_worker_result(
            LiveAuditRunnerResult(
                trace_id="cas-checkpoint-demo-manifest",
                evidence_packet=packet,
                proof_chips=[],
                verifier_decision=None,
                message="Untrusted checkpoint",
                audit_scope=None,
            )
        )

    assert list(iter_harvest_records()) == []
    assert list(tmp_path.rglob("*.json")) == []
    assert list(tmp_path.rglob("*.jsonl")) == []


@pytest.mark.asyncio
async def test_billing_context_requires_and_delivers_one_worker_receipt(monkeypatch):
    receipt = {"schema_version": "signed-test-receipt"}
    seen: list[dict[str, object]] = []

    async def fake_dump(worker_base, payload):
        assert worker_base == "http://worker.test"
        assert payload["billing_measurement_context"] == {
            "tenant_id": "tenant-a",
            "billing_account_id": "acct-a",
            "run_id": "attempt-a",
        }
        return {
            "billing_measurement_receipt": receipt,
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "runtime": "real_pythia",
                        "is_real_model": True,
                    },
                },
                {
                    "type": "token",
                    "token_index": 0,
                    "token": " measured",
                    "confidence": 0.8,
                    "top_activated_neurons": [],
                    "mode7_attribution": [],
                },
                {"type": "complete", "total_tokens": 1},
            ],
        }

    monkeypatch.setattr(settings, "atlas_live_worker_url", "http://worker.test")
    monkeypatch.setattr(
        "api.services.cas_harness_live_worker_runner._post_worker_dump", fake_dump
    )

    await run_live_worker_audit(
        audit_id="cas-audit-metered",
        model_id="EleutherAI/pythia-160m",
        prompt="Meter this.",
        audit_mode="BALANCED",
        selected_modules=["active_trace"],
        billing_measurement_context={
            "tenant_id": "tenant-a",
            "billing_account_id": "acct-a",
            "run_id": "attempt-a",
        },
        on_billing_measurement_receipt=lambda value: seen.append(dict(value)),
    )

    assert seen == [receipt]


@pytest.mark.asyncio
async def test_billing_context_fails_closed_when_worker_omits_receipt(monkeypatch):
    async def fake_dump(_worker_base, _payload):
        return {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "is_real_model": True,
                    },
                }
            ]
        }

    monkeypatch.setattr(settings, "atlas_live_worker_url", "http://worker.test")
    monkeypatch.setattr(
        "api.services.cas_harness_live_worker_runner._post_worker_dump", fake_dump
    )
    with pytest.raises(LiveAuditRunnerUnavailable, match="was not returned"):
        await run_live_worker_audit(
            audit_id="cas-audit-unmetered",
            model_id="EleutherAI/pythia-160m",
            prompt="Do not guess usage.",
            audit_mode="BALANCED",
            selected_modules=["active_trace"],
            billing_measurement_context={
                "tenant_id": "tenant-a",
                "billing_account_id": "acct-a",
                "run_id": "attempt-a",
            },
            on_billing_measurement_receipt=lambda _value: None,
        )


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
                        "is_real_model": True,
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
    assert packet.provenance["code_commit_sha"] == _code_commit_sha()
    assert packet.provenance["code_commit_sha"] != "unknown"

    # Honest scope label: activations captured, but causal/control not yet run.
    assert packet.audit_scope["kind"] == "open_weight_live_trace"
    assert packet.audit_scope["internal_activation_access"] is True
    assert packet.audit_scope["verdict_disposition"] == "held_for_human_review"
    assert "causal/control not yet run" in packet.audit_scope["label"]

    harvest = list(iter_harvest_records())
    assert len(harvest) == 1
    assert harvest[0]["trace_id"] == result.trace_id
    assert harvest[0]["output"]["text"] == " Hello world"
    assert harvest[0]["join"] == {"key": "trace_id", "pairs_with": "native_nl.v1"}
    # The same-dump real manifest is retained in both packet and harvest.
    assert harvest[0]["model_io_is_demo_fallback"] is False

    assert chips == {
        "model_proof": "present",
        "cas_readout": "present",
        "causal_proof": "unavailable",
        "control_proof": "unavailable",
        "output_proof": "present",
        "packet_proof": "present",
    }


@pytest.mark.asyncio
async def test_live_worker_runner_forwards_key_and_checkpoints_in_order(monkeypatch):
    events: list[str] = []
    captured: dict[str, object] = {}

    async def fake_dump(worker_base, payload, *, provider_idempotency_key=None):
        events.append("provider_called")
        captured["worker_base"] = worker_base
        captured["provider_idempotency_key"] = provider_idempotency_key
        return {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "runtime": "real_pythia",
                        "is_real_model": True,
                    },
                },
                {"type": "token", "token_index": 0, "token": " result", "confidence": 0.8},
                {"type": "complete", "total_tokens": 1},
            ]
        }

    monkeypatch.setattr(settings, "atlas_live_worker_url", "http://worker.test")
    monkeypatch.setattr(
        "api.services.cas_harness_live_worker_runner._post_worker_dump", fake_dump
    )
    key = "cas-run-live-worker-stable"
    result = await run_live_worker_audit(
        audit_id="cas-audit-live-checkpoints",
        model_id="EleutherAI/pythia-160m",
        prompt="checkpoint the live worker",
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

    assert captured == {
        "worker_base": "http://worker.test",
        "provider_idempotency_key": key,
    }
    assert events == [
        "request_started",
        "provider_called",
        f"provider_completed:{result.trace_id}",
        f"evidence_persisted:{result.trace_id}",
    ]
    assert result.evidence_packet["live_audit"]["provider_idempotency"]["key"] == key
    assert (
        result.evidence_packet["live_audit"]["provider_idempotency"][
            "provider_enforcement"
        ]
        == "not_assumed"
    )


# ---------------------------------------------------------------------------
# Causal ablation consumption — the first causal proof, plumbed honestly.
# ---------------------------------------------------------------------------


def _real_ablation_event() -> dict:
    """A worker ablation_effect event flagged as a REAL measurement."""
    return {
        "type": "ablation_effect",
        "target": {"layer": 0, "unit": 0},
        "mode": "zero",
        "is_real_model": True,
        "baseline_top_token": " the",
        "ablated_top_token": " a",
        "baseline_top_token_id": 510,
        "ablated_top_token_id": 247,
        "logit_delta": -1.2345,
        "confidence_delta": -0.05,
        "top_token_changed": True,
        "detail": "Measured single-target ablation (zero) of layer 0 unit 0.",
    }


def _demo_ablation_event() -> dict:
    """A worker ablation_effect event flagged as demo (no real weights)."""
    return {
        "type": "ablation_effect",
        "target": {"layer": 0, "unit": 0},
        "mode": "zero",
        "is_real_model": False,
        "baseline_top_token": None,
        "ablated_top_token": None,
        "baseline_top_token_id": None,
        "ablated_top_token_id": None,
        "logit_delta": None,
        "confidence_delta": None,
        "top_token_changed": None,
        "detail": "Demo mode: no real weights loaded, so no causal ablation.",
    }


def _real_control_event() -> dict:
    """A worker ablation_control_effect event flagged as a REAL measurement."""
    return {
        "type": "ablation_control_effect",
        "target": {"layer": 0, "unit": 0},
        "mode": "zero",
        "is_real_model": True,
        "n_controls": 8,
        "control_units": [3, 11, 42, 100, 256, 500, 900, 1500],
        "target_abs_logit_delta": 1.4567,
        "control_mean_abs_logit_delta": 0.3210,
        "control_max_abs_logit_delta": 0.6789,
        "margin_over_control_max": 0.7778,
        "selectivity_passed": True,
        "seed": 42,
        "detail": "Single-unit selectivity control (zero) for layer 0 unit 0.",
    }


def _demo_control_event() -> dict:
    """A worker ablation_control_effect event flagged as demo (no real weights)."""
    return {
        "type": "ablation_control_effect",
        "target": {"layer": 0, "unit": 0},
        "mode": "zero",
        "is_real_model": False,
        "n_controls": 0,
        "control_units": None,
        "target_abs_logit_delta": None,
        "control_mean_abs_logit_delta": None,
        "control_max_abs_logit_delta": None,
        "margin_over_control_max": None,
        "selectivity_passed": None,
        "seed": None,
        "detail": "Demo mode: no real weights loaded, so no matched control.",
    }


@pytest.mark.asyncio
async def test_real_flagged_ablation_flips_causal_proof_present(monkeypatch):
    """A worker dump carrying a REAL ablation_effect event must produce
    packet['ablation'].status == 'present' (with measured deltas) AND flip the
    causal_proof chip to 'present'."""

    async def fake_dump(worker_base, payload):  # noqa: ARG001
        return {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "runtime": "real_pythia",
                        "is_real_model": True,
                    },
                },
                {
                    "type": "token",
                    "token_index": 0,
                    "token": " Hi",
                    "confidence": 0.9,
                    "top_activated_neurons": [],
                    "mode7_attribution": [],
                },
                _real_ablation_event(),
                {"type": "complete", "total_tokens": 1},
            ]
        }

    monkeypatch.setattr(settings, "atlas_live_worker_url", "http://worker.test")
    monkeypatch.setattr(
        "api.services.cas_harness_live_worker_runner._post_worker_dump",
        fake_dump,
    )

    result = await run_live_worker_audit(
        audit_id="cas-audit-abl-real",
        model_id="EleutherAI/pythia-160m",
        prompt="Audit this.",
        audit_mode="BALANCED",
        selected_modules=["active_trace"],
    )

    packet = build_packet_for_trace(result.trace_id)
    chips = {chip["id"]: chip["status"] for chip in result.proof_chips}

    # Ablation block present, carrying the REAL measured deltas.
    assert packet.ablation["status"] == "present"
    assert packet.ablation["is_real_model"] is True
    assert packet.ablation["logit_delta"] == pytest.approx(-1.2345)
    assert packet.ablation["top_token_changed"] is True
    assert packet.ablation["target"] == {"layer": 0, "unit": 0}

    # Honesty invariant: causal_proof flips to present ONLY here.
    assert chips["causal_proof"] == "present"
    # Matched controls remain unavailable — not faked.
    assert chips["control_proof"] == "unavailable"
    assert packet.matched_controls["status"] == "unavailable"

    # Audit scope + caveats reflect the real causal slice honestly.
    assert "real single-target causal ablation" in packet.audit_scope["label"]
    assert "causal/control not yet run" not in packet.audit_scope["label"]


@pytest.mark.asyncio
async def test_demo_flagged_ablation_keeps_causal_proof_unavailable(monkeypatch):
    """A demo-flagged ablation_effect event (is_real_model False) must NOT flip
    the causal_proof chip — status stays 'unavailable' and no deltas leak."""

    async def fake_dump(worker_base, payload):  # noqa: ARG001
        return {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "is_real_model": True,
                    },
                },
                {
                    "type": "token",
                    "token_index": 0,
                    "token": " Hi",
                    "confidence": 0.9,
                    "top_activated_neurons": [],
                    "mode7_attribution": [],
                },
                _demo_ablation_event(),
                {"type": "complete", "total_tokens": 1},
            ]
        }

    monkeypatch.setattr(settings, "atlas_live_worker_url", "http://worker.test")
    monkeypatch.setattr(
        "api.services.cas_harness_live_worker_runner._post_worker_dump",
        fake_dump,
    )

    result = await run_live_worker_audit(
        audit_id="cas-audit-abl-demo",
        model_id="EleutherAI/pythia-160m",
        prompt="Audit this.",
        audit_mode="BALANCED",
        selected_modules=["active_trace"],
    )

    packet = build_packet_for_trace(result.trace_id)
    chips = {chip["id"]: chip["status"] for chip in result.proof_chips}

    assert packet.ablation["status"] == "unavailable"
    assert packet.ablation.get("is_real_model") is False
    # No fabricated deltas in an unavailable block.
    assert "logit_delta" not in packet.ablation
    assert chips["causal_proof"] == "unavailable"
    assert "causal/control not yet run" in packet.audit_scope["label"]


def test_ablation_block_honesty_invariant():
    """Unit-level invariant: _ablation_block_from_events returns 'present' iff
    a real (is_real_model True) ablation_effect event exists; demo/absent →
    'unavailable'. And the proof-chip helper mirrors this exactly."""

    # Real → present, deltas carried.
    real_block = _ablation_block_from_events([_real_ablation_event()])
    assert real_block["status"] == "present"
    assert real_block["logit_delta"] == pytest.approx(-1.2345)

    # Demo → unavailable, no deltas.
    demo_block = _ablation_block_from_events([_demo_ablation_event()])
    assert demo_block["status"] == "unavailable"
    assert "logit_delta" not in demo_block

    # Absent → unavailable.
    absent_block = _ablation_block_from_events(
        [{"type": "token", "token_index": 0, "token": "x"}]
    )
    assert absent_block["status"] == "unavailable"

    # Chip mirror: present block → causal_proof present; otherwise unavailable.
    def _causal(block: dict) -> str:
        chips = _proof_chips_for_live_packet(
            {
                "trace_id": "t",
                "model": {"model_key": "EleutherAI/pythia-160m"},
                "output": {"text": "x"},
                "readout": {"status": "present"},
                "ablation": block,
            }
        )
        return next(c["status"] for c in chips if c["id"] == "causal_proof")

    assert _causal(real_block) == "present"
    assert _causal(demo_block) == "unavailable"
    assert _causal(absent_block) == "unavailable"


# ---------------------------------------------------------------------------
# Matched-control consumption — the first control proof, plumbed honestly.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_flagged_control_flips_control_proof_present(monkeypatch):
    """A worker dump carrying a REAL ablation_control_effect event must produce
    packet['matched_controls'].status == 'present' (with measured selectivity
    deltas) AND flip the control_proof chip to 'present'. The causal_proof chip
    also flips because a real ablation_effect event is present in the same dump."""

    async def fake_dump(worker_base, payload):  # noqa: ARG001
        return {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "runtime": "real_pythia",
                        "is_real_model": True,
                    },
                },
                {
                    "type": "token",
                    "token_index": 0,
                    "token": " Hi",
                    "confidence": 0.9,
                    "top_activated_neurons": [],
                    "mode7_attribution": [],
                },
                _real_ablation_event(),
                _real_control_event(),
                {"type": "complete", "total_tokens": 1},
            ]
        }

    monkeypatch.setattr(settings, "atlas_live_worker_url", "http://worker.test")
    monkeypatch.setattr(
        "api.services.cas_harness_live_worker_runner._post_worker_dump",
        fake_dump,
    )

    result = await run_live_worker_audit(
        audit_id="cas-audit-ctrl-real",
        model_id="EleutherAI/pythia-160m",
        prompt="Audit this.",
        audit_mode="BALANCED",
        selected_modules=["active_trace"],
    )

    packet = build_packet_for_trace(result.trace_id)
    chips = {chip["id"]: chip["status"] for chip in result.proof_chips}

    # Control block present, carrying the REAL measured selectivity deltas.
    assert packet.matched_controls["status"] == "present"
    assert packet.matched_controls["is_real_model"] is True
    assert packet.matched_controls["selectivity_passed"] is True
    assert packet.matched_controls["target_abs_logit_delta"] == pytest.approx(1.4567)
    assert packet.matched_controls["margin_over_control_max"] == pytest.approx(0.7778)
    assert packet.matched_controls["control_units"] == [3, 11, 42, 100, 256, 500, 900, 1500]
    assert packet.matched_controls["target"] == {"layer": 0, "unit": 0}

    # Both causal AND control proofs flip to present (both real events present).
    assert chips["causal_proof"] == "present"
    assert chips["control_proof"] == "present"

    # Scope label honestly mentions the single-unit matched-control selectivity.
    assert "real single-target causal ablation" in packet.audit_scope["label"]
    assert "matched-control selectivity" in packet.audit_scope["label"]


@pytest.mark.asyncio
async def test_demo_flagged_control_keeps_control_proof_unavailable(monkeypatch):
    """A demo-flagged ablation_control_effect event (is_real_model False) must NOT
    flip the control_proof chip — status stays 'unavailable' and no deltas leak,
    even though a real ablation_effect event flips causal_proof in the same dump."""

    async def fake_dump(worker_base, payload):  # noqa: ARG001
        return {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": "EleutherAI/pythia-160m",
                        "is_real_model": True,
                    },
                },
                {
                    "type": "token",
                    "token_index": 0,
                    "token": " Hi",
                    "confidence": 0.9,
                    "top_activated_neurons": [],
                    "mode7_attribution": [],
                },
                _real_ablation_event(),
                _demo_control_event(),
                {"type": "complete", "total_tokens": 1},
            ]
        }

    monkeypatch.setattr(settings, "atlas_live_worker_url", "http://worker.test")
    monkeypatch.setattr(
        "api.services.cas_harness_live_worker_runner._post_worker_dump",
        fake_dump,
    )

    result = await run_live_worker_audit(
        audit_id="cas-audit-ctrl-demo",
        model_id="EleutherAI/pythia-160m",
        prompt="Audit this.",
        audit_mode="BALANCED",
        selected_modules=["active_trace"],
    )

    packet = build_packet_for_trace(result.trace_id)
    chips = {chip["id"]: chip["status"] for chip in result.proof_chips}

    assert packet.matched_controls["status"] == "unavailable"
    assert packet.matched_controls.get("is_real_model") is False
    # No fabricated selectivity numbers in an unavailable block.
    assert "target_abs_logit_delta" not in packet.matched_controls
    # Causal proof still flips (real ablation), control proof does not (demo).
    assert chips["causal_proof"] == "present"
    assert chips["control_proof"] == "unavailable"


def test_control_block_honesty_invariant():
    """Unit-level invariant: _control_block_from_events returns 'present' iff a
    real (is_real_model True) ablation_control_effect event exists; demo/absent →
    'unavailable'. And the proof-chip helper mirrors this exactly."""

    # Real → present, selectivity deltas carried.
    real_block = _control_block_from_events([_real_control_event()])
    assert real_block["status"] == "present"
    assert real_block["selectivity_passed"] is True
    assert real_block["target_abs_logit_delta"] == pytest.approx(1.4567)

    # Demo → unavailable, no deltas.
    demo_block = _control_block_from_events([_demo_control_event()])
    assert demo_block["status"] == "unavailable"
    assert "target_abs_logit_delta" not in demo_block

    # Absent → unavailable.
    absent_block = _control_block_from_events(
        [{"type": "token", "token_index": 0, "token": "x"}]
    )
    assert absent_block["status"] == "unavailable"

    # Chip mirror: present block → control_proof present; otherwise unavailable.
    def _control(block: dict) -> str:
        chips = _proof_chips_for_live_packet(
            {
                "trace_id": "t",
                "model": {"model_key": "EleutherAI/pythia-160m"},
                "output": {"text": "x"},
                "readout": {"status": "present"},
                "matched_controls": block,
            }
        )
        return next(c["status"] for c in chips if c["id"] == "control_proof")

    assert _control(real_block) == "present"
    assert _control(demo_block) == "unavailable"
    assert _control(absent_block) == "unavailable"


# ---------------------------------------------------------------------------
# Graceful degradation — a worker that predates the causal-ablation probe must
# NOT break the live trace. The runner retries once with the ablation slice
# removed so real model I/O + harvest still land; causal_proof then stays
# 'unavailable' (event-derived), never fabricated. This is the exact state of
# the currently deployed m2-real-pythia worker, which 422s the unknown probe.
# ---------------------------------------------------------------------------


def _mock_async_client(monkeypatch, handler):
    """Point the runner's httpx.AsyncClient at a MockTransport handler."""
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(transport=transport, **kwargs),
    )


@pytest.mark.asyncio
async def test_post_worker_dump_sends_worker_token_header(monkeypatch):
    seen_headers: list[tuple[str | None, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(
            (
                request.headers.get("X-Atlas-Worker-Token"),
                request.headers.get("X-CAS-Provider-Idempotency-Key"),
            )
        )
        return httpx.Response(200, json={"events": [{"type": "complete", "total_tokens": 0}]})

    monkeypatch.setattr(settings, "atlas_live_worker_token", "worker-secret")
    _mock_async_client(monkeypatch, handler)

    body = await _post_worker_dump(
        "http://worker.test",
        {"prompt": "p", "model_id": "EleutherAI/pythia-160m", "probes": ["active_trace"]},
        provider_idempotency_key="cas-run-worker-header",
    )

    assert body == {"events": [{"type": "complete", "total_tokens": 0}]}
    assert seen_headers == [("worker-secret", "cas-run-worker-header")]


@pytest.mark.asyncio
async def test_post_worker_dump_retries_without_ablation_on_unsupported_probe(monkeypatch):
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        seen.append(payload)
        if "causal_ablation" in payload.get("probes", []):
            # Mirrors the deployed m2-real-pythia worker rejecting the unknown
            # probe value with a 422 that names `causal_ablation` as the input.
            return httpx.Response(
                422,
                json={
                    "detail": [
                        {
                            "type": "literal_error",
                            "loc": ["body", "probes", 4],
                            "input": "causal_ablation",
                        }
                    ]
                },
            )
        return httpx.Response(200, json={"events": [{"type": "complete", "total_tokens": 0}]})

    _mock_async_client(monkeypatch, handler)

    payload = {
        "prompt": "p",
        "model_id": "EleutherAI/pythia-160m",
        "probes": ["active_trace", "causal_ablation"],
        "ablation_target": {"layer": 0, "unit": 0, "mode": "zero"},
    }
    body = await _post_worker_dump("http://worker.test", payload)

    assert body == {"events": [{"type": "complete", "total_tokens": 0}]}
    # Exactly two attempts: with ablation (422) then without (200).
    assert len(seen) == 2
    assert "causal_ablation" in seen[0]["probes"]
    assert "ablation_target" in seen[0]
    # The retry drops both the probe and the now-meaningless target.
    assert "causal_ablation" not in seen[1]["probes"]
    assert "active_trace" in seen[1]["probes"]
    assert "ablation_target" not in seen[1]


@pytest.mark.asyncio
async def test_post_worker_dump_does_not_retry_unrelated_422(monkeypatch):
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        # A 422 with nothing to do with the ablation slice must surface, not be
        # silently downgraded — otherwise real validation errors get masked.
        return httpx.Response(
            422,
            json={"detail": [{"loc": ["body", "model_id"], "input": "bad-model"}]},
        )

    _mock_async_client(monkeypatch, handler)

    payload = {
        "prompt": "p",
        "model_id": "EleutherAI/pythia-160m",
        "probes": ["active_trace", "causal_ablation"],
        "ablation_target": {"layer": 0, "unit": 0, "mode": "zero"},
    }
    with pytest.raises(LiveAuditRunnerUnavailable):
        await _post_worker_dump("http://worker.test", payload)
    # No silent retry: only the single original attempt was made.
    assert len(seen) == 1
