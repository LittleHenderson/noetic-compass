"""CB1-A torch cases for bounded binding edits through the INCUMBENT intervention path on a LABELLED FIXTURE
container (`FIXTURE_NOT_HELM`, the same shape as `test_diagnostic_intervention.Fixture`). Written, NOT RUN
locally. Proves: bias cancels, sigma-only rescaling, exact swap-back, single application via
`diagnostic_intervention.apply` at `graph.round_update`, double-application refusal, descendant recomputation
inside one forward (fixture), and the refusals. Nothing here is HELM."""
import os

import pytest
import torch

from .. import diagnostic_intervention as di
from ..diagnostic_configuration import CORE_ROUNDS, LEARNER_SHA256
from . import binding_edits as be
from . import reconstructor as rc
from . import role_schemes as rs

DEVICE = os.environ.get("HELM_DIAG_TEST_DEVICE", "cuda")
if DEVICE.startswith("cuda") and not torch.cuda.is_available():
    raise RuntimeError("GPU_REQUIRED: set HELM_DIAG_TEST_DEVICE only inside an admitted job")
CKPT, INPUT = "a" * 64, "1" * 64
WIDTH, NODES = 16, 4
FILLERS = ("A", "B", "C", "D")
ROUND = 3


class Fixture(torch.nn.Module):
    label = "FIXTURE_NOT_HELM"

    def __init__(self):
        super().__init__()
        self.core_block = torch.nn.Linear(WIDTH, WIDTH, bias=False)
        self.node_head = torch.nn.Sequential(torch.nn.Linear(WIDTH, 8), torch.nn.GELU(), torch.nn.Linear(8, 3))
        self.reach_option_head = torch.nn.Sequential(torch.nn.Linear(WIDTH, 2))
        self.pointer_key = torch.nn.Linear(WIDTH, WIDTH, bias=False)

    def forward(self, hidden, query):
        for _round in range(CORE_ROUNDS):
            hidden = hidden + 0.1 * torch.tanh(self.core_block(hidden))
        return self.node_head(hidden), self.pointer_key(query), self.reach_option_head(hidden.mean(dim=0, keepdim=True)).reshape(-1)


def _model():
    torch.manual_seed(7)
    return Fixture().to(DEVICE)


def _inputs():
    g = torch.Generator(device="cpu").manual_seed(11)
    return torch.randn(NODES, WIDTH, generator=g).to(DEVICE), torch.randn(WIDTH, generator=g).to(DEVICE)


def _binding(model):
    return di.caller_binding(model, torch, checkpoint_sha256=CKPT, source_sha256=LEARNER_SHA256, restored_by="FixtureLearner.restore")


def _refused(code, call, *args, **kwargs):
    with pytest.raises(be.BindingEditRefused) as info:
        call(*args, **kwargs)
    assert info.value.code == code, info.value


def _scheme():
    return rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=1)


def _rows(scheme, *pairs):
    return rs.row_binding_sets(scheme, rs.public_graph(scheme, [{"source_node_id": s, "predicate": "contains", "target_node_id": t} for s, t in pairs]))


def _fitted(scheme, normalization="NONE"):
    g = torch.Generator(device="cpu").manual_seed(2)
    rows = _rows(scheme, ("A", "B"), ("C", "D"), ("A", "C"))
    samples = [(row, torch.randn(WIDTH, generator=g).to(DEVICE)) for row in rows]
    design = rc.declare_design(scheme, kind="TPR", d_f=3, d_r=2, d_h=WIDTH, site=be.EDIT_SITE, seed=1, max_steps=10, normalization=normalization)
    return rc.fit(design, samples, torch=torch, device=DEVICE)


def _observe_row(model, row):
    """The passive stand-in: the captured original value of `row` at the edit site/round."""
    decl = di.declare(action="OBSERVE_ONLY", site=be.EDIT_SITE, checkpoint_sha256=CKPT, input_sha256=INPUT,
                      source_sha256=LEARNER_SHA256, rows=(row,), coordinates=tuple(range(WIDTH)), round_index=ROUND)
    hidden, query = _inputs()
    with di.apply(model, decl, torch=torch, expected_forward_calls=1, binding=_binding(model)) as receipt:
        original = model(hidden, query)
    assert receipt.status == "OBSERVED"
    hit = receipt.targeted_hits()[0]
    return torch.tensor(hit["before"], dtype=torch.float32, device=DEVICE), original


def _plan(rec, old, new, edit, expected, max_norm=1e6):
    _, state_digest = rc.serialize(rec)
    return be.freeze_plan(rec=rec, state_digest=state_digest, old_set=old, new_set=new, edit=edit, row=0, round_index=ROUND,
                          expected_effect=expected, hypothesis_id="H_CB1_FIXTURE", checkpoint_sha256=CKPT, input_sha256=INPUT,
                          source_sha256=LEARNER_SHA256, max_delta_norm=max_norm)


def test_bias_cancels_and_sigma_only_rescaling():
    scheme = _scheme()
    old = _rows(scheme, ("A", "B"), ("C", "D"))[0]
    edit = be.declare_edit("FILLER_REPLACEMENT", role_path=("contains", "out", "1"), old_filler="B", new_filler="D", occurrence=("A", "B"))
    new = be.edit_bindings(old, edit)
    assert new.multiplicity("D", ("contains", "out", "1")) == 1 and new.multiplicity("B", ("contains", "out", "1")) == 0
    for normalization in ("NONE", "TRAIN_ZSCORE"):
        rec = _fitted(scheme, normalization)
        d = be.delta(rec, old, new, torch=torch)
        via_reconstruct = rc.reconstruct(rec, new, torch=torch) - rc.reconstruct(rec, old, torch=torch)
        assert torch.allclose(d, via_reconstruct, atol=1e-5)          # bias (and mean) cancel
        dv = rc.binding_tensor(rec, new, torch=torch) - rc.binding_tensor(rec, old, torch=torch)
        expected = rec.W @ dv if normalization == "NONE" else rec.sigma * (rec.W @ dv)
        assert torch.allclose(d, expected, atol=1e-6)
        if normalization == "TRAIN_ZSCORE":
            assert not torch.allclose(d, rec.mean + rec.sigma * (rec.W @ dv), atol=1e-3)   # mean must NOT be added
        back = be.delta(rec, new, old, torch=torch)
        assert torch.allclose(d + back, torch.zeros_like(d), atol=1e-6)                     # exact swap-back
        assert torch.equal(be.delta(rec, old, old, torch=torch), torch.zeros_like(d))        # true no-op


def test_no_change_edit_applies_through_incumbent_path_as_applied_no_change():
    scheme = _scheme()
    rec = _fitted(scheme)
    old = _rows(scheme, ("A", "B"), ("C", "D"))[0]
    edit = be.declare_edit("NO_CHANGE")
    plan = _plan(rec, old, be.edit_bindings(old, edit), edit, "NO_CHANGE")
    model = _model()
    original_row, _ = _observe_row(model, 0)
    d = be.delta(rec, old, old, torch=torch)
    donor = be.donor_for_plan(plan, d, original_row, torch=torch, capture_digest="c" * 64)
    decl = be.declaration_for_plan(plan, donor, width=WIDTH)
    assert decl.action == "SAME_INPUT_PATCH" and decl.rows == (0,) and decl.round_index == ROUND
    hidden, query = _inputs()
    with di.apply(model, decl, torch=torch, expected_forward_calls=1, binding=_binding(model)) as receipt:
        model(hidden, query)
    assert receipt.status == "APPLIED_NO_CHANGE"
    check = be.verify_single_application(receipt, plan, d, torch=torch)
    assert check["single_application"] is True and check["measured_delta_norm"] == 0.0
    assert receipt.hooks_removed is True and receipt.parameters_unchanged is True


def test_filler_replacement_applies_once_with_the_planned_delta_and_descendants_recompute():
    scheme = _scheme()
    rec = _fitted(scheme)
    old = _rows(scheme, ("A", "B"), ("C", "D"))[0]
    edit = be.declare_edit("FILLER_REPLACEMENT", role_path=("contains", "out", "1"), old_filler="B", new_filler="D", occurrence=("A", "B"))
    new = be.edit_bindings(old, edit)
    plan = _plan(rec, old, new, edit, "PREDICTED_ANSWER_CHANGE")
    model = _model()
    original_row, original_out = _observe_row(model, 0)
    d = be.delta(rec, old, new, torch=torch)
    assert float(d.norm().item()) > 0
    donor = be.donor_for_plan(plan, d, original_row, torch=torch, capture_digest="c" * 64)
    decl = be.declaration_for_plan(plan, donor, width=WIDTH)
    hidden, query = _inputs()
    with di.apply(model, decl, torch=torch, expected_forward_calls=1, binding=_binding(model)) as receipt:
        edited_out = model(hidden, query)
    assert receipt.status == "APPLIED"
    hit = receipt.targeted_hits()[0]
    measured = torch.tensor(hit["after"], device=DEVICE) - torch.tensor(hit["before"], device=DEVICE)
    assert torch.allclose(measured, d, atol=1e-4)
    check = be.verify_single_application(receipt, plan, d, torch=torch)
    assert check["status"] == "APPLIED" and check["round_index"] == ROUND
    assert not torch.allclose(edited_out[0], original_out[0])          # node head recomputed on the same forward
    assert receipt.parameters_unchanged is True and receipt.hooks_removed is True
    assert decl.claim_ceiling == "WITHIN_CHECKPOINT_DIAGNOSTIC"
    gold_donor = be.donor_for_plan(plan, d, original_row, torch=torch, capture_digest="c" * 64, provenance="GOLD_INFORMED")
    assert be.declaration_for_plan(plan, gold_donor, width=WIDTH).claim_ceiling == "ORACLE_ASSISTED_DIAGNOSIS_NOT_DEPLOYABLE"


def test_double_application_and_unverified_binding_are_refused():
    scheme = _scheme()
    rec = _fitted(scheme)
    old = _rows(scheme, ("A", "B"), ("C", "D"))[0]
    edit = be.declare_edit("FILLER_REPLACEMENT", role_path=("contains", "out", "1"), old_filler="B", new_filler="D", occurrence=("A", "B"))
    plan = _plan(rec, old, be.edit_bindings(old, edit), edit, "PREDICTED_ANSWER_CHANGE")
    model = _model()
    original_row, _ = _observe_row(model, 0)
    d = be.delta(rec, old, be.edit_bindings(old, edit), torch=torch)
    decl = be.declaration_for_plan(plan, be.donor_for_plan(plan, d, original_row, torch=torch, capture_digest="c" * 64), width=WIDTH)
    hidden, query = _inputs()
    with di.apply(model, decl, torch=torch, expected_forward_calls=2, binding=_binding(model)) as twice:
        model(hidden, query)
        model(hidden, query)
    assert len(twice.targeted_hits()) == 2
    _refused("DOUBLE_APPLICATION", be.verify_single_application, twice, plan, d, torch=torch)
    with di.apply(model, decl, torch=torch, expected_forward_calls=1) as unbound:      # no caller binding
        model(hidden, query)
    _refused("MODEL_BINDING_UNVERIFIED", be.verify_single_application, unbound, plan, d, torch=torch)
    with di.apply(model, decl, torch=torch, expected_forward_calls=1, binding=_binding(model)) as none:
        pass                                                                            # no forward: no hit
    _refused("NOT_APPLIED", be.verify_single_application, none, plan, d, torch=torch)


def test_edit_and_plan_refusals():
    scheme = _scheme()
    rec = _fitted(scheme)
    old = _rows(scheme, ("A", "B"), ("C", "D"))[0]
    _refused("EDIT_KIND_NOT_IN_FIRST_PACKET", be.declare_edit, "TWO_ROLE_SWAP", role_path=("contains", "out", "1"), old_filler="B", new_filler="D", occurrence=("A", "B"))
    _refused("EDIT_KIND", be.declare_edit, "ANSWER_REWRITE")
    _refused("EDIT_FIELDS", be.declare_edit, "FILLER_REPLACEMENT", role_path=("contains", "out", "1"), old_filler="B", new_filler="B", occurrence=("A", "B"))
    absent = be.declare_edit("FILLER_REPLACEMENT", role_path=("contains", "out", "1"), old_filler="C", new_filler="D", occurrence=("A", "C"))
    _refused("EDIT_TARGET_ABSENT", be.edit_bindings, old, absent)
    edit = be.declare_edit("FILLER_REPLACEMENT", role_path=("contains", "out", "1"), old_filler="B", new_filler="D", occurrence=("A", "B"))
    new = be.edit_bindings(old, edit)
    unfitted = rc.initialise(rec.design, torch=torch, device=DEVICE)
    _refused("RECONSTRUCTOR_UNFITTED", be.delta, unfitted, old, new, torch=torch)
    _refused("EXPECTED_EFFECT", _plan, rec, old, new, edit, "NO_CHANGE")
    _refused("EXPECTED_EFFECT", _plan, rec, old, old, be.declare_edit("NO_CHANGE"), "PREDICTED_ANSWER_CHANGE")
    _, sd = rc.serialize(rec)
    _refused("EDIT_SITE", be.freeze_plan, rec=rec, state_digest=sd, old_set=old, new_set=new, edit=edit, row=0, round_index=ROUND,
             expected_effect="PREDICTED_ANSWER_CHANGE", hypothesis_id="H", checkpoint_sha256=CKPT, input_sha256=INPUT,
             source_sha256=LEARNER_SHA256, max_delta_norm=1.0, site="head.node")
    _refused("ROUND_INDEX", be.freeze_plan, rec=rec, state_digest=sd, old_set=old, new_set=new, edit=edit, row=0, round_index=CORE_ROUNDS,
             expected_effect="PREDICTED_ANSWER_CHANGE", hypothesis_id="H", checkpoint_sha256=CKPT, input_sha256=INPUT,
             source_sha256=LEARNER_SHA256, max_delta_norm=1.0)
    d = be.delta(rec, old, new, torch=torch)
    tiny = _plan(rec, old, new, edit, "PREDICTED_ANSWER_CHANGE", max_norm=1e-9)
    row_values = torch.zeros(WIDTH, device=DEVICE)
    _refused("DELTA_NORM_EXCEEDED", be.donor_for_plan, tiny, d, row_values, torch=torch, capture_digest="c" * 64)
    plan = _plan(rec, old, new, edit, "PREDICTED_ANSWER_CHANGE")
    _refused("DELTA_SHAPE", be.donor_for_plan, plan, d, torch.zeros(WIDTH + 1, device=DEVICE), torch=torch, capture_digest="c" * 64)
    no_change_plan = _plan(rec, old, old, be.declare_edit("NO_CHANGE"), "NO_CHANGE")
    _refused("NO_CHANGE_NOT_ZERO", be.donor_for_plan, no_change_plan, d, row_values, torch=torch, capture_digest="c" * 64)
    donor = be.donor_for_plan(plan, d, row_values, torch=torch, capture_digest="c" * 64)
    _refused("WIDTH", be.declaration_for_plan, plan, donor, width=WIDTH + 1)
    assert be.DESCENDANT_RECOMPUTATION["status"] == "SOURCE_CONSISTENT_NOT_EXECUTED"
