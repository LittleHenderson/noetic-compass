"""AWS-only bridge specifications; no real checkpoint or training fixture."""
from dataclasses import replace
from types import SimpleNamespace
import pytest

from ..diagnostic_configuration import LEARNER_SHA256, SITE_SEMANTICS, CORE_ROUNDS, raw_capture
from .. import diagnostic_intervention as intervention
from .consumer_bridge import SITE, _prepare, consumer_schedule, verify_consumer_receipt


def captured():
    return raw_capture(checkpoint_sha256="a" * 64, input_sha256="b" * 64,
        source_sha256=LEARNER_SHA256, site=SITE, call_index=0, round_index=0,
        shape=(4, 64), dtype="float32", device="cpu",
        coordinate_meaning=SITE_SEMANTICS[SITE]["coordinate_meaning"], signed_values=[0.0] * 256)


def test_bridge_reuses_existing_noop_declaration_and_real_hook_seam():
    declaration, schedule = _prepare(captured(), hypothesis_id="SYNTHETIC", predicted_change="none")
    assert type(declaration) is intervention.Declaration and declaration.action == "NO_OP_CONTROL"
    assert (declaration.module_attribute, declaration.hook_kind) == ("core_block", "post")
    assert schedule["execution_authorized"] is False
    assert schedule["descendants_in_order"].index("_encode_query") < schedule["descendants_in_order"].index("node_head")


def test_node_state_is_refused_instead_of_stale_state_substitution():
    with pytest.raises(ValueError, match="CB1_CONSUMER_SITE_UNSUPPORTED"):
        consumer_schedule("graph.node_state", round_index=0)


def test_wrong_source_dimensions_and_call_identity_refuse():
    for value, error in [(replace(captured(), source_sha256="c" * 64), "SOURCE_SITE"),
                         (replace(captured(), shape=(4, 63)), "DIMENSIONS"),
                         (replace(captured(), call_index=1), "SINGLE_FORWARD")]:
        with pytest.raises(ValueError, match=error):
            _prepare(value, hypothesis_id="fixture", predicted_change="none")


def test_replacement_requires_finite_native_shape_without_bias_guess():
    declaration, _ = _prepare(captured(), native_values=[1.0] * 256, max_abs_delta=1.0, donor_provenance="STIMULUS_ONLY",
                               hypothesis_id="fixture", predicted_change="declared counterfactual")
    assert declaration.donor.values == (1.0,) * 256 and declaration.donor.provenance == "STIMULUS_ONLY"
    with pytest.raises(ValueError, match="DIMENSIONS"):
        _prepare(captured(), native_values=[1.0], hypothesis_id="fixture", predicted_change="none")
    with pytest.raises(ValueError, match="DONOR_VALUES"):
        _prepare(captured(), native_values=[float("nan")] * 256, max_abs_delta=1.0,
                 donor_provenance="STIMULUS_ONLY", hypothesis_id="fixture", predicted_change="none")


def test_replacement_has_explicit_enforced_native_delta_bound():
    with pytest.raises(ValueError, match="CB1_DELTA_LIMIT_REQUIRED"):
        _prepare(captured(), native_values=[1.0] * 256, hypothesis_id="fixture", predicted_change="none")
    with pytest.raises(ValueError, match="CB1_DELTA_LIMIT"):
        _prepare(captured(), native_values=[2.0] * 256, max_abs_delta=1.0,
                 donor_provenance="STIMULUS_ONLY", hypothesis_id="fixture", predicted_change="none")


def test_donor_provenance_is_explicit_and_oracle_claim_is_not_laundered():
    with pytest.raises(ValueError, match="CB1_DONOR_PROVENANCE_REQUIRED"):
        _prepare(captured(), native_values=[0.0] * 256, max_abs_delta=1.0,
                 hypothesis_id="fixture", predicted_change="none")
    declaration, _ = _prepare(captured(), native_values=[0.0] * 256, max_abs_delta=1.0,
        donor_provenance="GOLD_INFORMED", hypothesis_id="synthetic oracle", predicted_change="none")
    assert declaration.claim_ceiling == "ORACLE_ASSISTED_DIAGNOSIS_NOT_DEPLOYABLE"


def test_synthetic_noop_recomputes_descendants_and_removes_hook():
    import torch
    torch.manual_seed(11)
    module = SimpleNamespace(core_block=torch.nn.Linear(64, 64))
    # The existing helper expects a model with named_parameters/state_dict.
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.core_block = module.core_block; self.head = torch.nn.Linear(64, 2)
        def forward(self, value):
            for _ in range(CORE_ROUNDS):
                value = value + self.core_block(value)
            return self.head(value)
    model = Model(); values = torch.zeros(4, 64); expected = model(values).detach().clone()
    declaration, _ = _prepare(captured(), hypothesis_id="synthetic-noop", predicted_change="none")
    binding = intervention.caller_binding(model, torch, checkpoint_sha256="a" * 64,
                                         source_sha256=LEARNER_SHA256, restored_by="SYNTHETIC_FIXTURE_NOT_HELM")
    with intervention.apply(model, declaration, torch=torch, expected_forward_calls=1, binding=binding) as receipt:
        actual = model(values)
    assert torch.equal(expected, actual)
    assert verify_consumer_receipt(declaration, receipt)["status"] == "NO_OP_VERIFIED"
    assert not model.core_block._forward_hooks


def test_missed_forward_never_passes_consumer_gate():
    declaration, _ = _prepare(captured(), hypothesis_id="fixture", predicted_change="none")
    receipt = intervention.Receipt(intervention.RECEIPT_SCHEMA, intervention.declaration_digest(declaration),
        declaration.action, declaration.operation, SITE, "core_block", "post", 1, CORE_ROUNDS, 1)
    receipt.model_binding = "CALLER_VERIFIED"; receipt.hooks_removed = receipt.parameters_unchanged = True
    intervention.finalize(receipt)
    with pytest.raises(ValueError, match="CB1_CONSUMER_HITS"):
        verify_consumer_receipt(declaration, receipt)


def test_double_forward_never_passes_consumer_gate():
    declaration, _ = _prepare(captured(), hypothesis_id="fixture", predicted_change="none")
    receipt = intervention.Receipt(intervention.RECEIPT_SCHEMA, intervention.declaration_digest(declaration),
        declaration.action, declaration.operation, SITE, "core_block", "post", 1, CORE_ROUNDS, 1)
    receipt.model_binding = "CALLER_VERIFIED"; receipt.hooks_removed = receipt.parameters_unchanged = True
    receipt.hits = [{"round_index": i % CORE_ROUNDS, "targeted": i % CORE_ROUNDS == 0,
                     "shape": [4, 64], "untargeted_unchanged": True, "changed_count": 0}
                    for i in range(2 * CORE_ROUNDS)]
    intervention.finalize(receipt)
    with pytest.raises(ValueError, match="CB1_CONSUMER_HITS"):
        verify_consumer_receipt(declaration, receipt)
