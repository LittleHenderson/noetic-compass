"""Schema-level checks — these are the contract the API + UI rely on."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    CompleteEvent,
    CreateSessionRequest,
    ManifestEvent,
    Mode7Edge,
    NeuronActivation,
    NeuronCoversEvent,
    TokenEvent,
)
from app.runtime.model_loader import PYTHIA_160M_MANIFEST as MANIFEST


def test_manifest_event_round_trip():
    e = ManifestEvent(manifest=MANIFEST)
    j = e.model_dump_json()
    e2 = ManifestEvent.model_validate_json(j)
    assert e2.manifest.model_id == "EleutherAI/pythia-160m"
    assert e2.manifest.is_real_model is False  # m1 invariant
    assert e2.manifest.execution_kind == "demo_schema_only"
    assert "mlp_intermediate_post_activation" in e2.manifest.supported_hooks
    contract = e2.manifest.intervention_hook_contract
    assert contract.coordinate_space == "mlp_intermediate_post_activation"
    assert contract.module_path_template == (
        "gpt_neox.layers[{layer}].mlp.dense_4h_to_h"
    )
    assert contract.tensor_role == "forward_pre_hook.input[0]"
    assert contract.token_selection == "batch_0_last_sequence_position"
    assert contract.failure_policy == "fail_closed"


def test_token_event_accepts_optional_confidence():
    TokenEvent(token_index=0, token="hi")  # no activations or confidence is fine
    TokenEvent(
        token_index=1,
        token=" world",
        top_activated_neurons=[NeuronActivation(layer=0, index=0, activation=0.5)],
        mode7_attribution=[Mode7Edge(from_token_index=0, to_token_index=1, weight=0.5)],
        confidence=0.8,
    )


def test_token_event_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        TokenEvent(token_index=0, token="x", confidence=1.5)


def test_token_event_rejects_out_of_range_inversion_risk():
    with pytest.raises(ValidationError):
        TokenEvent(token_index=0, token="x", inversion_risk=1.5)


def test_mode7_weight_must_be_in_unit_interval():
    with pytest.raises(ValidationError):
        Mode7Edge(from_token_index=0, to_token_index=1, weight=1.5)


def test_complete_event_min():
    e = CompleteEvent(total_tokens=0)
    assert e.type == "complete"


def test_neuron_covers_event_default_empty():
    e = NeuronCoversEvent()
    assert e.per_class_neuron_covers == {}


def test_create_session_request_defaults():
    r = CreateSessionRequest(prompt="hi")
    assert r.model_id == "EleutherAI/pythia-160m"
    assert r.max_new_tokens == 24
    assert r.temperature == 0.0
    assert r.seed is None
    assert r.probes == []
    assert r.method_config == {}


def test_create_session_request_validates_prompt_length():
    with pytest.raises(ValidationError):
        CreateSessionRequest(prompt="")
