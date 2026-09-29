"""Torch cases for the intervention bridge on a LABELED FIXTURE container. Written, NOT RUN locally.

The fixture (`FIXTURE_NOT_HELM`) has the container attributes the hookable sites name (`core_block`,
`node_head`, `reach_option_head`, `pointer_key`) and a forward that calls `core_block` CORE_ROUNDS times,
then the heads once. It is not HELM and proves plumbing only (HH10/HH11/HH06/HH02/HH15/HH16); a real
witness needs the runner job with the guarded learner. Device: `HELM_DIAG_TEST_DEVICE` (default `cuda`);
a missing CUDA device fails with GPU_REQUIRED rather than falling back to CPU.
"""
import json
import os

import pytest
import torch

from . import diagnostic_intervention as di
from .diagnostic_configuration import CORE_ROUNDS, LEARNER_SHA256, SITE_SEMANTICS

DEVICE = os.environ.get("HELM_DIAG_TEST_DEVICE", "cuda")
if DEVICE.startswith("cuda") and not torch.cuda.is_available():
    raise RuntimeError("GPU_REQUIRED: set HELM_DIAG_TEST_DEVICE only inside an admitted job")
CKPT = "a" * 64
INPUT = "1" * 64
WIDTH, NODES = 16, 5
FIXTURE_LABEL = "FIXTURE_NOT_HELM"


class Fixture(torch.nn.Module):
    label = FIXTURE_LABEL

    def __init__(self):
        super().__init__()
        self.core_block = torch.nn.Linear(WIDTH, WIDTH, bias=False)
        self.node_head = torch.nn.Sequential(torch.nn.Linear(WIDTH, 8), torch.nn.GELU(), torch.nn.Linear(8, 3))
        self.reach_option_head = torch.nn.Sequential(torch.nn.Linear(WIDTH, 2))
        self.pointer_key = torch.nn.Linear(WIDTH, WIDTH, bias=False)
        self.raise_after_rounds = False

    def forward(self, hidden, query):
        for _round in range(CORE_ROUNDS):
            hidden = hidden + 0.1 * torch.tanh(self.core_block(hidden))
        if self.raise_after_rounds:
            raise RuntimeError("FIXTURE_INJECTED_FAILURE")
        node_rows = self.node_head(hidden)
        pointer_query = self.pointer_key(query)
        reach = self.reach_option_head(hidden.mean(dim=0, keepdim=True)).reshape(-1)
        return node_rows, pointer_query, reach


def _model():
    torch.manual_seed(7)
    return Fixture().to(DEVICE)


def _inputs():
    generator = torch.Generator(device="cpu").manual_seed(11)
    hidden = torch.randn(NODES, WIDTH, generator=generator).to(DEVICE)
    query = torch.randn(WIDTH, generator=generator).to(DEVICE)
    return hidden, query


def _declare(action="SUPPRESS", **overrides):
    fields = dict(action=action, site="graph.round_input", checkpoint_sha256=CKPT, input_sha256=INPUT,
                  source_sha256=LEARNER_SHA256, rows=(1, 3), coordinates=(2, 5, 9), round_index=3,
                  gain=1.0 if action in ("SUPPRESS",) else None, hypothesis_id="H1",
                  predicted_change="reach margin falls")
    fields.update(overrides)
    return di.declare(**fields)


def _refused(code, function, *args, **kwargs):
    with pytest.raises(di.InterventionRefused) as info:
        function(*args, **kwargs)
    assert info.value.code == code, (info.value.code, code)


def _binding(model):
    return di.caller_binding(model, torch, checkpoint_sha256=CKPT, source_sha256=LEARNER_SHA256, restored_by="fixture-loader")


def _baseline(model):
    hidden, query = _inputs()
    with torch.no_grad():
        return [t.detach().clone() for t in model(hidden, query)]


def test_hh02_bind_refuses_foreign_objects_and_reads_widths_from_the_modules():
    model = _model()
    bound = di.bind_sites(model, torch)
    assert set(bound) == set(di.HOOK_SITES)
    assert bound["graph.round_input"]["widths"] == {"in_features": WIDTH, "out_features": WIDTH}
    assert bound["head.reach"]["widths"]["out_features"] == 2
    _refused("MODEL_TYPE", di.bind_sites, object(), torch)

    class Foreign(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.core_block = torch.nn.Linear(WIDTH, WIDTH)
            self.node_head = "not a module"
    _refused("SITE_MODULE_MISSING", di.bind_sites, Foreign().to(DEVICE), torch, sites=("head.reach",))
    _refused("SITE_MODULE_TYPE", di.bind_sites, Foreign().to(DEVICE), torch, sites=("head.node",))


def test_declaration_refusals_close_the_grammar():
    _refused("SITE_NOT_HOOKABLE", _declare, site="head.node_pointer", round_index=None)
    _refused("SITE_UNKNOWN", _declare, site="mlp.3")
    _refused("ROUND_INDEX", _declare, round_index=CORE_ROUNDS)
    _refused("ROUND_INDEX", _declare, site="head.reach", rows=(0,), round_index=0)
    _refused("GAIN_RANGE", _declare, gain=0.0)
    _refused("GAIN_RANGE", _declare, gain=1.5)
    _refused("GAIN", _declare, gain=float("nan"))
    _refused("SOURCE_NOT_ADMITTED", _declare, source_sha256="9" * 64)
    _refused("ROWS", _declare, rows=(1, 1))
    _refused("COORDINATES", _declare, coordinates=())
    _refused("ACTION_UNKNOWN", _declare, action="AMPLIFY_ALL")
    _refused("CONTROL_FIELDS", _declare, control_seed=3)
    _refused("GAIN_UNEXPECTED", _declare, action="OBSERVE_ONLY", gain=0.5)
    _refused("RECEIPT_BYTES_EXCEEDED", _declare, max_receipt_bytes=8)
    assert di.suppression_factor(1.0) == 0.0 and di.suppression_factor(0.25) == 0.75 and di.suppression_factor(2.0) == 0.0
    assert set(di.HOOK_SITES) | set(di.NOT_HOOKABLE) == set(SITE_SEMANTICS)


def test_hh13_donor_assumptions_are_explicit_and_cross_checkpoint_or_wrong_basis_is_refused():
    good = di.donor(input_sha256="2" * 64, capture_digest="3" * 64, checkpoint_sha256=CKPT, provenance="STIMULUS_ONLY",
                    basis="NODE_ROW_BLOCK_INPUT", dtype="float32", device=str(torch.device(DEVICE)), values=[0.5] * 6)
    patch = _declare("SAME_INPUT_PATCH", donor=good)
    assert patch.claim_ceiling == "WITHIN_CHECKPOINT_DIAGNOSTIC"
    gold = di.donor(input_sha256="2" * 64, capture_digest="3" * 64, checkpoint_sha256=CKPT, provenance="GOLD_INFORMED",
                    basis="NODE_ROW_BLOCK_INPUT", dtype="float32", device=str(torch.device(DEVICE)), values=[0.5] * 6)
    assert _declare("SAME_INPUT_PATCH", donor=gold).claim_ceiling == "ORACLE_ASSISTED_DIAGNOSIS_NOT_DEPLOYABLE"
    _refused("DONOR_CHECKPOINT_MISMATCH", _declare, "SAME_INPUT_PATCH",
             donor=di.donor(input_sha256="2" * 64, capture_digest="3" * 64, checkpoint_sha256="b" * 64,
                            provenance="STIMULUS_ONLY", basis="NODE_ROW_BLOCK_INPUT", dtype="float32",
                            device="cuda:0", values=[0.5] * 6))
    _refused("DONOR_BASIS_MISMATCH", _declare, "SAME_INPUT_PATCH",
             donor=di.donor(input_sha256="2" * 64, capture_digest="3" * 64, checkpoint_sha256=CKPT,
                            provenance="STIMULUS_ONLY", basis="NODE_ROW_STATE", dtype="float32",
                            device="cuda:0", values=[0.5] * 6))
    _refused("DONOR_VALUE_COUNT", _declare, "SAME_INPUT_PATCH",
             donor=di.donor(input_sha256="2" * 64, capture_digest="3" * 64, checkpoint_sha256=CKPT,
                            provenance="STIMULUS_ONLY", basis="NODE_ROW_BLOCK_INPUT", dtype="float32",
                            device="cuda:0", values=[0.5] * 5))
    _refused("DONOR_PROVENANCE", di.donor, input_sha256="2" * 64, capture_digest="3" * 64, checkpoint_sha256=CKPT,
             provenance="GUESSED", basis="NODE_ROW_BLOCK_INPUT", dtype="float32", device="cuda:0", values=[0.5])
    _refused("DONOR_REQUIRED", _declare, "SAME_INPUT_PATCH")


def test_hh03_observe_only_never_returns_a_tensor_and_leaves_output_state_and_hooks_untouched():
    model = _model()
    baseline = _baseline(model)
    declaration = _declare("OBSERVE_ONLY", coordinates=(), gain=None)
    hidden, query = _inputs()
    with di.apply(model, declaration, torch=torch, expected_forward_calls=1) as receipt:
        with torch.no_grad():
            observed = model(hidden, query)
    assert all(torch.equal(a, b) for a, b in zip(baseline, observed))
    assert receipt.status == "OBSERVED" and receipt.applied is None
    assert len(receipt.hits) == CORE_ROUNDS and len(receipt.targeted_hits()) == 1
    targeted = receipt.targeted_hits()[0]
    assert targeted["round_index"] == 3 and len(targeted["before"]) == 2 * WIDTH and targeted["after"] is None
    assert receipt.hooks_removed is True and receipt.parameters_unchanged is True
    assert not model.core_block._forward_pre_hooks and not model.core_block._forward_hooks
    assert receipt.stored_floats * di.FLOAT_BYTES <= declaration.max_receipt_bytes


def test_hh04_observe_only_with_fewer_forwards_than_expected_is_incomplete_not_zero_valued():
    model = _model()
    declaration = _declare("OBSERVE_ONLY", coordinates=(2,), gain=None)
    with di.apply(model, declaration, torch=torch, expected_forward_calls=2) as receipt:
        hidden, query = _inputs()
        with torch.no_grad():
            model(hidden, query)
    assert receipt.status == "OBSERVED_INCOMPLETE" and len(receipt.hits) == CORE_ROUNDS < receipt.expected_hits


def test_hh10_no_op_control_goes_through_the_edit_path_and_leaves_everything_bitwise_equal():
    model = _model()
    baseline = _baseline(model)
    declaration = _declare("NO_OP_CONTROL", gain=None)
    assert declaration.gain == 0.0
    hidden, query = _inputs()
    with di.apply(model, declaration, torch=torch, expected_forward_calls=1) as receipt:
        with torch.no_grad():
            sham = model(hidden, query)
    assert all(torch.equal(a, b) for a, b in zip(baseline, sham))
    assert receipt.status == "NO_OP_VERIFIED" and receipt.applied is True
    targeted = receipt.targeted_hits()[0]
    assert targeted["changed_count"] == 0 and targeted["untargeted_unchanged"] and targeted["before"] == targeted["after"]
    assert receipt.parameters_unchanged is True and receipt.hooks_removed is True


def test_hh11_suppress_changes_only_the_declared_entries_at_the_declared_round_by_the_harness_factor():
    model = _model()
    baseline = _baseline(model)
    declaration = _declare("SUPPRESS", gain=0.5)
    hidden, query = _inputs()
    seen = {}

    def spy(_module, args):
        seen.setdefault("inputs", []).append(args[0].detach().clone())
    spy_handle = model.core_block.register_forward_pre_hook(spy)
    try:
        with di.apply(model, declaration, torch=torch, expected_forward_calls=1) as receipt:
            with torch.no_grad():
                changed = model(hidden, query)
    finally:
        spy_handle.remove()
    assert receipt.status == "APPLIED" and receipt.applied is True
    assert len(receipt.hits) == CORE_ROUNDS and len(receipt.targeted_hits()) == 1
    hit = receipt.targeted_hits()[0]
    assert hit["round_index"] == 3 and hit["changed_count"] == 6 and hit["untargeted_unchanged"] is True
    before = torch.tensor(hit["before"]).reshape(2, 3)
    after = torch.tensor(hit["after"]).reshape(2, 3)
    assert torch.allclose(after, before * di.suppression_factor(0.5))
    assert not all(torch.equal(a, b) for a, b in zip(baseline, changed))
    # the spy registered BEFORE the adapter saw the unmodified input; the adapter's hook ran after it
    assert len(seen["inputs"]) == CORE_ROUNDS
    assert receipt.parameters_unchanged is True and receipt.hooks_removed is True
    assert not model.core_block._forward_pre_hooks


def test_hh11_suppress_on_all_zero_targets_is_applied_no_change_not_applied_success():
    model = _model()
    declaration = _declare("SUPPRESS", gain=1.0, site="head.reach", rows=(0,), coordinates=(0, 1), round_index=None)
    with torch.no_grad():
        model.reach_option_head[0].weight.zero_()
        model.reach_option_head[0].bias.zero_()
    hidden, query = _inputs()
    with di.apply(model, declaration, torch=torch, expected_forward_calls=1, binding=_binding(model)) as receipt:
        with torch.no_grad():
            model(hidden, query)
    assert receipt.status == "APPLIED_NO_CHANGE" and receipt.applied is True
    assert receipt.targeted_hits()[0]["changed_count"] == 0
    assert receipt.model_binding == "CALLER_VERIFIED" and receipt.restored_by == "fixture-loader"
    assert di.require_applied(receipt) is receipt


def test_hh11_same_input_patch_lands_donor_values_exactly_and_refuses_device_or_dtype_drift():
    model = _model()
    device = str(torch.device(DEVICE) if torch.device(DEVICE).index is not None or DEVICE == "cpu"
                 else torch.device(DEVICE, 0))
    values = [0.25, -0.5, 1.0, 2.0, -3.0, 0.0]
    good = di.donor(input_sha256="2" * 64, capture_digest="3" * 64, checkpoint_sha256=CKPT, provenance="STIMULUS_ONLY",
                    basis="NODE_ROW_BLOCK_INPUT", dtype="float32", device=device, values=values)
    declaration = _declare("SAME_INPUT_PATCH", donor=good)
    hidden, query = _inputs()
    with di.apply(model, declaration, torch=torch, expected_forward_calls=1) as receipt:
        with torch.no_grad():
            model(hidden, query)
    assert receipt.status == "APPLIED"
    assert receipt.targeted_hits()[0]["after"] == values
    wrong_device = di.donor(input_sha256="2" * 64, capture_digest="3" * 64, checkpoint_sha256=CKPT,
                            provenance="STIMULUS_ONLY", basis="NODE_ROW_BLOCK_INPUT", dtype="float32",
                            device="cpu" if device != "cpu" else "cuda:0", values=values)
    bad = _declare("SAME_INPUT_PATCH", donor=wrong_device)
    with pytest.raises(di.InterventionRefused) as info:
        with di.apply(model, bad, torch=torch, expected_forward_calls=1) as receipt:
            with torch.no_grad():
                model(hidden, query)
    assert info.value.code == "DONOR_DEVICE_MISMATCH"
    assert receipt.status == "NOT_APPLIED" and receipt.applied is False and receipt.hooks_removed is True
    assert not model.core_block._forward_pre_hooks
    _refused("INTERVENTION_NOT_APPLIED", di.require_applied, receipt)


def test_hh12_matched_control_has_same_count_rows_round_gain_and_disjoint_coordinates():
    active = _declare("SUPPRESS", gain=0.75)
    control = di.matched_control(active, width=WIDTH, seed=2026)
    assert di.verify_matched(control, active) == {"matched": True, "count": 3, "seed": 2026}
    assert control.operation == "SUPPRESS" and control.gain == 0.75 and control.rows == active.rows
    assert not set(control.coordinates) & set(active.coordinates)
    assert di.matched_control(active, width=WIDTH, seed=2026).coordinates == control.coordinates
    _refused("CONTROL_NOT_MATCHED", di.verify_matched, control, _declare("SUPPRESS", gain=0.5))
    _refused("CONTROL_POOL", di.matched_control, _declare("SUPPRESS", coordinates=tuple(range(WIDTH - 2))),
             width=WIDTH, seed=1)
    model = _model()
    hidden, query = _inputs()
    with di.apply(model, control, torch=torch, expected_forward_calls=1) as receipt:
        with torch.no_grad():
            model(hidden, query)
    assert receipt.status == "APPLIED" and receipt.action == "MATCHED_CONTROL" and receipt.operation == "SUPPRESS"
    assert receipt.targeted_hits()[0]["changed_count"] == 6


def test_hh11_active_target_out_of_range_raises_inside_the_forward_and_is_not_applied():
    model = _model()
    declaration = _declare("SUPPRESS", gain=1.0, rows=(NODES + 4,))
    hidden, query = _inputs()
    with pytest.raises(di.InterventionRefused) as info:
        with di.apply(model, declaration, torch=torch, expected_forward_calls=1) as receipt:
            with torch.no_grad():
                model(hidden, query)
    assert info.value.code == "TARGET_OUT_OF_RANGE"
    assert receipt.status == "NOT_APPLIED" and receipt.errors and receipt.hooks_removed is True
    assert receipt.parameters_unchanged is True and not model.core_block._forward_pre_hooks


def test_hh11_zero_forwards_is_not_applied_never_a_silent_success():
    model = _model()
    with di.apply(model, _declare("SUPPRESS"), torch=torch, expected_forward_calls=1) as receipt:
        pass
    assert receipt.status == "NOT_APPLIED" and receipt.applied is False and not receipt.hits
    with di.apply(model, _declare("NO_OP_CONTROL", gain=None), torch=torch, expected_forward_calls=1) as sham:
        pass
    assert sham.status == "NO_OP_FAILED"


def test_hh06_exception_inside_the_forward_still_removes_hooks_and_finalizes_the_receipt():
    model = _model()
    model.raise_after_rounds = True
    hidden, query = _inputs()
    with pytest.raises(RuntimeError, match="FIXTURE_INJECTED_FAILURE"):
        with di.apply(model, _declare("SUPPRESS", site="head.node", rows=(0,), coordinates=(1,), round_index=None),
                      torch=torch, expected_forward_calls=1) as receipt:
            with torch.no_grad():
                model(hidden, query)
    assert receipt.status == "NOT_APPLIED" and not receipt.hits and receipt.hooks_removed is True
    assert not model.node_head._forward_hooks and receipt.parameters_unchanged is True


def test_hh06_receipt_byte_bound_is_enforced_at_declaration_and_at_storage():
    _refused("RECEIPT_BYTES_EXCEEDED", _declare, "OBSERVE_ONLY", coordinates=(), gain=None, rows=tuple(range(NODES)),
             max_receipt_bytes=NODES * 2 * di.FLOAT_BYTES - 1)
    model = _model()
    declaration = _declare("OBSERVE_ONLY", coordinates=(0, 1), gain=None, rows=(0,), max_receipt_bytes=2 * 2 * di.FLOAT_BYTES)
    hidden, query = _inputs()
    # the declared bound holds exactly two targeted hits (before values only); the third forward overflows it
    with di.apply(model, declaration, torch=torch, expected_forward_calls=3) as receipt:
        with torch.no_grad():
            model(hidden, query)
            model(hidden, query)
            model(hidden, query)
    assert receipt.status == "OBSERVED_INCOMPLETE" and len(receipt.hits) == 3 * CORE_ROUNDS
    assert any("RECEIPT_BYTES_EXCEEDED" in row for row in receipt.errors)
    assert receipt.targeted_hits()[2]["before"] is None and receipt.stored_floats == 4


def test_hh16_receipt_json_round_trips_binds_its_declaration_and_detects_tampering():
    model = _model()
    declaration = _declare("SUPPRESS", gain=1.0)
    hidden, query = _inputs()
    with di.apply(model, declaration, torch=torch, expected_forward_calls=1) as receipt:
        with torch.no_grad():
            model(hidden, query)
    text = di.receipt_to_json(receipt)
    import hashlib
    anchor = hashlib.sha256(text.encode()).hexdigest()
    _refused("EXTERNAL_ANCHOR_REQUIRED", di.verify_receipt, text, declaration, retained_receipt_sha256=None)
    body = di.verify_receipt(text, declaration, retained_receipt_sha256=anchor)
    assert body["status"] == "APPLIED" and body["actor"] == di.ACTOR and body["authority"] == "OBSERVATION_ONLY_NO_PROMOTION"
    _refused("RECEIPT_ANCHOR_MISMATCH", di.verify_receipt, text, declaration, retained_receipt_sha256="0" * 64)
    _refused("RECEIPT_DECLARATION_MISMATCH", di.verify_receipt, text, _declare("SUPPRESS", gain=0.5), retained_receipt_sha256=anchor)
    tampered = json.dumps(dict(json.loads(text), status="APPLIED_NO_CHANGE"))
    _refused("RECEIPT_TAMPERED", di.verify_receipt, tampered, declaration,
             retained_receipt_sha256=hashlib.sha256(tampered.encode()).hexdigest())


def test_hh15_expected_hits_from_the_emitter_rule_make_an_unexpected_reach_hit_not_applied():
    from .diagnostic_configuration import expected_hits_for
    model = _model()
    declaration = _declare("SUPPRESS", gain=1.0, site="head.reach", rows=(0,), coordinates=(0,), round_index=None)
    hidden, query = _inputs()
    # a Parts packet never reaches head.reach (emitter rule: 0 expected); the fixture calls it anyway -> over-count
    with di.apply(model, declaration, torch=torch, expected_forward_calls=1,
                  expected_hits=expected_hits_for("head.reach", "parts")) as receipt:
        with torch.no_grad():
            model(hidden, query)
    assert receipt.expected_hits == 0 and len(receipt.hits) == 1 and receipt.status == "NOT_APPLIED"
    with di.apply(model, declaration, torch=torch, expected_forward_calls=1,
                  expected_hits=expected_hits_for("head.reach", "reach")) as receipt:
        with torch.no_grad():
            model(hidden, query)
    assert receipt.expected_hits == 1 and receipt.status == "APPLIED"


def test_hh15_declaration_strings_never_authenticate_the_module_only_the_caller_binding_does():
    model = _model()
    declaration = _declare("SUPPRESS", gain=1.0)
    hidden, query = _inputs()
    with di.apply(model, declaration, torch=torch, expected_forward_calls=1) as receipt:
        with torch.no_grad():
            model(hidden, query)
    assert receipt.status == "APPLIED" and receipt.model_binding == "UNVERIFIED_SELF_REPORTED"
    _refused("MODEL_BINDING_UNVERIFIED", di.require_applied, receipt)
    other = _model()
    with torch.no_grad():
        other.core_block.weight.add_(0.5)
    stale = _binding(other)
    with pytest.raises(di.InterventionRefused) as info:
        with di.apply(model, declaration, torch=torch, expected_forward_calls=1, binding=stale):
            pass
    assert info.value.code == "MODEL_BINDING_MISMATCH"
    assert not model.core_block._forward_pre_hooks
    wrong_checkpoint = dict(_binding(model), checkpoint_sha256="b" * 64)
    with pytest.raises(di.InterventionRefused) as info:
        with di.apply(model, declaration, torch=torch, expected_forward_calls=1, binding=wrong_checkpoint):
            pass
    assert info.value.code == "MODEL_BINDING_MISMATCH"
    _refused("MODEL_BINDING_INVALID", lambda: di.verify_caller_binding(model, torch, declaration, {"schema": "other"}))
    _refused("BINDING_RESTORER", di.caller_binding, model, torch, checkpoint_sha256=CKPT, source_sha256=LEARNER_SHA256, restored_by="")
    with di.apply(model, declaration, torch=torch, expected_forward_calls=1, binding=_binding(model)) as bound:
        with torch.no_grad():
            model(hidden, query)
    assert bound.model_binding == "CALLER_VERIFIED" and di.require_applied(bound) is bound


class FixtureLearner:
    """A labeled stand-in for the guarded-restored learner: `.module`, class-level `_graph`, `predict`. NOT HELM."""
    label = FIXTURE_LABEL

    def __init__(self, module):
        self.module, self._pending = module, None

    def _graph(self, packet):
        return None

    def predict(self, packet, depth):
        hidden, query = _inputs()
        with torch.no_grad():
            return self.module(hidden, query)


def test_trusted_caller_connection_is_disabled_by_default_and_binds_checkpoint_input_and_module(tmp_path):
    import hashlib
    from .diagnostic_configuration import _emitter_canonical, digest as cfg_digest, detect_from_observation, freeze_configuration
    from .test_diagnostic_configuration import _emitted_receipt
    copy = tmp_path / "parent_copy.pt"
    copy.write_bytes(b"FIXTURE_NOT_A_REAL_CHECKPOINT")
    ckpt = hashlib.sha256(copy.read_bytes()).hexdigest()
    fixture_source = hashlib.sha256(open(__file__, "rb").read()).hexdigest()
    packet = {"record_id": "fixture-1", "source": {"kind": "fixture"}, "record": {"x": 1}}
    input_sha = hashlib.sha256(_emitter_canonical(packet)).hexdigest()
    learner = FixtureLearner(_model())
    declaration = di.declare(action="SUPPRESS", site="head.reach", checkpoint_sha256=ckpt, input_sha256=input_sha,
                             source_sha256=fixture_source, rows=(0,), coordinates=(0,), gain=1.0, hypothesis_id="H1",
                             predicted_change="reach margin falls", allowed_sources=(fixture_source,))
    # the pinned learner source is the default: a fixture learner is refused unless its own hash is named explicitly
    _refused("UNSUPPORTED_LEARNER_SOURCE", lambda: di.trusted_intervention_caller(
        learner=learner, packet=packet, kind="reach", checkpoint_path=copy, expected_checkpoint_sha256=ckpt,
        declaration=declaration, torch=torch))
    disabled = di.trusted_intervention_caller(learner=learner, packet=packet, kind="reach", checkpoint_path=copy,
                                              expected_checkpoint_sha256=ckpt, declaration=declaration, torch=torch,
                                              expected_learner_sha256=fixture_source)
    assert disabled["status"] == di.CONNECTION_DISABLED and disabled["hooks_registered"] is False and disabled["forwards"] == 0
    assert disabled["checks"]["learner_source_is_pinned"] is False and disabled["checks"]["checkpoint_bytes"] is True
    assert disabled["binding"]["schema"] == "helm.harness.caller-binding/0.1" and disabled["expected_hits"] == 1
    assert not learner.module.reach_option_head._forward_hooks
    wrong_copy = tmp_path / "other.pt"
    wrong_copy.write_bytes(b"DIFFERENT")
    _refused("WRONG_CHECKPOINT_BYTES", lambda: di.trusted_intervention_caller(
        learner=learner, packet=packet, kind="reach", checkpoint_path=wrong_copy, expected_checkpoint_sha256=ckpt,
        declaration=declaration, torch=torch, expected_learner_sha256=fixture_source))
    _refused("UNADMITTED_INPUT", lambda: di.trusted_intervention_caller(
        learner=learner, packet=dict(packet, record={"x": 2}), kind="reach", checkpoint_path=copy,
        expected_checkpoint_sha256=ckpt, declaration=declaration, torch=torch, expected_learner_sha256=fixture_source))
    _refused("PROTOCOL_CHECKS_FAILED", lambda: di.trusted_intervention_caller(
        learner=learner, packet=packet, kind="reach", checkpoint_path=copy, expected_checkpoint_sha256=ckpt,
        declaration=declaration, torch=torch, expected_learner_sha256=fixture_source, enabled=True, protocol=None))
    receipt = _emitted_receipt(kind="reach", checkpoint_sha256=ckpt, input_sha256=input_sha)
    # the emitted receipt names the pinned learner source; scope must match the declaration's source pin too
    configuration = freeze_configuration(detect_from_observation(receipt, site="head.reach", row=0, k=1, split="DISCOVERY",
                                                                 family="F", retained_receipt_sha256=receipt["receipt_sha256"]))
    control = di.matched_control(declaration, width=2, seed=3)
    protocol = di.protocol_checks(declaration=declaration, passive_receipt=receipt,
                                  retained_passive_receipt_sha256=receipt["receipt_sha256"], configuration=configuration,
                                  control=control, witness_protocol_digest=cfg_digest(di.witness_protocol()), learner_pending=None)
    # the passive receipt carries source 0f424d86... (the real pin) while this fixture declaration pins its own file
    assert protocol["checks"]["passive_receipt_captured_same_scope"] is False and protocol["all_passed"] is False
    _refused("PROTOCOL_CHECKS_FAILED", lambda: di.trusted_intervention_caller(
        learner=learner, packet=packet, kind="reach", checkpoint_path=copy, expected_checkpoint_sha256=ckpt,
        declaration=declaration, torch=torch, expected_learner_sha256=fixture_source, enabled=True, protocol=protocol))
    forged = dict(protocol, all_passed=True)
    enabled = di.trusted_intervention_caller(learner=learner, packet=packet, kind="reach", checkpoint_path=copy,
                                             expected_checkpoint_sha256=ckpt, declaration=declaration, torch=torch,
                                             expected_learner_sha256=fixture_source, enabled=True, protocol=forged)
    # a forged protocol record is a caller decision this fixture cannot police; what the connection DOES guarantee:
    assert enabled["forwards"] == 1 and enabled["status"] == "APPLIED" and enabled["receipt"].model_binding == "CALLER_VERIFIED"
    assert enabled["receipt"].restored_by == "PointerCourseLearner.restore_checkpoint" and enabled["hooks_registered"] is True
    assert not learner.module.reach_option_head._forward_hooks and enabled["prediction"] is not None
