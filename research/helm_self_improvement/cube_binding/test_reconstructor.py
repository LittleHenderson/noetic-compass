"""CB1-A torch cases for the tensor-product reconstructor on LABELLED SYNTHETIC systems. Written, NOT RUN
locally (no torch here; the namespace conftest requires the admitted AWS venue). A labelled synthetic TPR
proves the apparatus (vec order, dimensions, bounded fit, holdout custody, normalisation, reload), never
natural HELM structure. Device: `HELM_DIAG_TEST_DEVICE` (default `cuda`, GPU_REQUIRED otherwise)."""
import os

import pytest
import torch

from . import reconstructor as rc
from . import role_schemes as rs

DEVICE = os.environ.get("HELM_DIAG_TEST_DEVICE", "cuda")
if DEVICE.startswith("cuda") and not torch.cuda.is_available():
    raise RuntimeError("GPU_REQUIRED: set HELM_DIAG_TEST_DEVICE only inside an admitted job")
FILLERS = ("A", "B", "C", "D", "E")
D_F, D_R, D_H = 3, 2, 8


def _refused(code, call, *args, **kwargs):
    with pytest.raises(rc.ReconstructorRefused) as info:
        call(*args, **kwargs)
    assert info.value.code == code, info.value


def _scheme():
    return rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=1)


def _edges(*pairs):
    return [{"source_node_id": s, "predicate": "contains", "target_node_id": t} for s, t in pairs]


def _rows(scheme, *pairs):
    return rs.row_binding_sets(scheme, rs.public_graph(scheme, _edges(*pairs)))


def _design(scheme, kind="TPR", **kw):
    args = dict(kind=kind, d_f=D_F, d_r=D_R, d_h=D_H, site="graph.round_update", seed=3, max_steps=150, learning_rate=2e-2)
    args.update(kw)
    return rc.declare_design(scheme, **args)


def _ground_truth(scheme):
    """A labelled synthetic TPR system: hidden factors the fit is allowed to rediscover."""
    g = torch.Generator(device="cpu").manual_seed(5)
    f = torch.randn(len(scheme.filler_vocabulary), D_F, generator=g)
    r = torch.randn(len(scheme.role_vocabulary), D_R, generator=g)
    W = torch.randn(D_H, D_F * D_R, generator=g)
    b = torch.randn(D_H, generator=g)
    return f.to(DEVICE), r.to(DEVICE), W.to(DEVICE), b.to(DEVICE)


def _target(scheme, truth, binding_set):
    f, r, W, b = truth
    v = torch.zeros(D_F * D_R, device=DEVICE)
    for filler, role in binding_set.records():
        v = v + torch.outer(f[scheme.filler_vocabulary.index(filler)], r[scheme.role_vocabulary.index(tuple(role))]).reshape(-1)
    return (W @ v + b).to(torch.float32)


def _samples(scheme, truth, rows):
    return [(row, _target(scheme, truth, row)) for row in rows]


def test_vec_order_is_filler_major_and_multiplicity_adds():
    scheme = _scheme()
    rec = rc.initialise(_design(scheme), torch=torch, device=DEVICE)
    row_a = _rows(scheme, ("A", "B"))[0]
    single = rc.binding_tensor(rec, row_a, torch=torch)
    expected = torch.zeros(D_F * D_R, device=DEVICE)
    for filler, role in row_a.records():
        f = rec.filler_embedding[scheme.filler_vocabulary.index(filler)]
        r = rec.role_embedding[scheme.role_vocabulary.index(tuple(role))]
        for i in range(D_F):
            for j in range(D_R):
                expected[i * D_R + j] += f[i] * r[j]
    assert torch.allclose(single, expected, atol=1e-6)
    # the same filler twice in one role (two occurrences) contributes twice
    deep = rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=2)
    two = _rows(deep, ("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"))[0]
    rec2 = rc.initialise(_design(deep), torch=torch, device=DEVICE)
    assert two.multiplicity("D", ("contains", "out", "2")) == 2
    d_only = rs.BindingSet(two.schema, two.scheme_digest, two.scope, "A", tuple(b for b in two.bindings if b.filler == "D"), 0)
    one_d = rs.BindingSet(two.schema, two.scheme_digest, two.scope, "A", (d_only.bindings[0],), 0)
    assert torch.allclose(rc.binding_tensor(rec2, d_only, torch=torch), 2 * rc.binding_tensor(rec2, one_d, torch=torch), atol=1e-6)


def test_dimensions_and_parameter_counts_are_explicit():
    scheme = _scheme()
    tpr, atomic = _design(scheme), _design(scheme, kind="ATOMIC_PAIR")
    rec = rc.initialise(tpr, torch=torch, device=DEVICE)
    assert tuple(rec.W.shape) == (D_H, D_F * D_R) and tuple(rec.bias.shape) == (D_H,)
    assert tuple(rec.filler_embedding.shape) == (len(FILLERS), D_F) and tuple(rec.role_embedding.shape) == (len(scheme.role_vocabulary), D_R)
    n_f, n_r = len(FILLERS), len(scheme.role_vocabulary)
    assert rc.parameter_count(tpr)["total"] == n_f * D_F + n_r * D_R + D_H * D_F * D_R + D_H
    assert rc.parameter_count(atomic)["total"] == n_f * n_r * D_F * D_R + D_H * D_F * D_R + D_H
    assert rc.parameter_count(atomic)["total"] > rc.parameter_count(tpr)["total"]
    assert tpr.vec_order == "FILLER_MAJOR" and tpr.dtype == "float32" and tpr.fit_loss == rc.FIT_LOSS
    _refused("D_H", rc.declare_design, scheme, kind="TPR", d_f=D_F, d_r=D_R, d_h=0, site="graph.round_update", seed=1)
    _refused("MAX_STEPS", rc.declare_design, scheme, kind="TPR", d_f=D_F, d_r=D_R, d_h=D_H, site="graph.round_update", seed=1, max_steps=10 ** 9)
    _refused("KIND", rc.declare_design, scheme, kind="RNN", d_f=D_F, d_r=D_R, d_h=D_H, site="graph.round_update", seed=1)


def test_bounded_fit_on_labelled_tpr_reduces_reconstruction_error_and_counts_updates():
    scheme = _scheme()
    truth = _ground_truth(scheme)
    rows = _rows(scheme, ("A", "B"), ("A", "C"), ("B", "D"), ("C", "E"))
    rec = rc.fit(_design(scheme), _samples(scheme, truth, rows), torch=torch, device=DEVICE)
    m = rec.manifest
    assert m["analysis_optimizer_updates"] == 150 and m["helm_optimizer_updates"] == 0
    assert m["last_loss"] < m["first_loss"]
    assert m["target_weights"] == "FROZEN_NOT_A_PARAMETER" and m["fit_loss"] == rc.FIT_LOSS
    res = rc.residuals(rec, _samples(scheme, truth, rows), torch=torch)
    assert len(res) == len(rows) and all(r["residual_norm"] >= 0 for r in res)
    assert not any(p.requires_grad for p in (rec.W, rec.bias, rec.filler_embedding, rec.role_embedding))
    short = rc.fit(_design(scheme, max_steps=5), _samples(scheme, truth, rows), torch=torch, device=DEVICE)
    assert short.manifest["analysis_optimizer_updates"] == 5


def test_holdout_leak_is_refused_and_unseen_pair_semantics_differ_by_kind():
    scheme = _scheme()
    truth = _ground_truth(scheme)
    rows = _rows(scheme, ("A", "B"), ("C", "D"))
    held = (("D", ("contains", "out", "1")),)
    _refused("HOLDOUT_LEAK", rc.fit, _design(scheme, max_steps=5), _samples(scheme, truth, rows), torch=torch, device=DEVICE, holdout_pairs=held)
    clean_rows = _rows(scheme, ("A", "B"), ("C", "E"))    # D bound nowhere
    tpr = rc.fit(_design(scheme, max_steps=20), _samples(scheme, truth, clean_rows), torch=torch, device=DEVICE, holdout_pairs=held)
    atomic = rc.fit(_design(scheme, kind="ATOMIC_PAIR", max_steps=20), _samples(scheme, truth, clean_rows), torch=torch, device=DEVICE, holdout_pairs=held)
    unseen = _rows(scheme, ("A", "D"))[0]                  # receiving A with (D, out/1): an analysis-held-out combination
    assert tuple(rc.reconstruct(tpr, unseen, torch=torch).shape) == (D_H,)
    _refused("PAIR_UNKNOWN", rc.reconstruct, atomic, unseen, torch=torch)
    assert atomic.manifest["parameters"]["total"] > tpr.manifest["parameters"]["total"]


def test_fit_inputs_carry_no_answers_and_wrong_targets_refuse():
    scheme = _scheme()
    truth = _ground_truth(scheme)
    row = _rows(scheme, ("A", "B"))[0]
    good = _target(scheme, truth, row)
    design = _design(scheme, max_steps=2)
    _refused("FIT_INPUT_FORBIDDEN", rc.fit, design, [{"bindings": row, "target": good, "answer": "B"}], torch=torch, device=DEVICE)
    _refused("FIT_INPUT_SHAPE", rc.fit, design, [(row, good, "label")], torch=torch, device=DEVICE)
    _refused("TARGET_SHAPE", rc.fit, design, [(row, good.reshape(1, -1))], torch=torch, device=DEVICE)
    _refused("TARGET_DTYPE", rc.fit, design, [(row, good.to(torch.float64))], torch=torch, device=DEVICE)
    bad = good.clone()
    bad[0] = float("nan")
    _refused("TARGET_NONFINITE", rc.fit, design, [(row, bad)], torch=torch, device=DEVICE)
    other = rs.declare_scheme("RELATION_ENDPOINT", filler_vocabulary=FILLERS, max_path_length=2)
    _refused("SCHEME_MISMATCH", rc.fit, design, [(_rows(other, ("A", "B"))[0], good)], torch=torch, device=DEVICE)
    _refused("FIT_INPUT_EMPTY", rc.fit, design, [], torch=torch, device=DEVICE)


def test_train_only_zscore_normalisation_zero_variance_and_native_reconstruction():
    scheme = _scheme()
    truth = _ground_truth(scheme)
    rows = _rows(scheme, ("A", "B"), ("A", "C"), ("B", "D"))
    samples = []
    for row, target in _samples(scheme, truth, rows):
        t = target.clone()
        t[0] = 0.5                                         # one constant coordinate across the training set
        samples.append((row, t))
    rec = rc.fit(_design(scheme, max_steps=10, normalization="TRAIN_ZSCORE"), samples, torch=torch, device=DEVICE)
    assert rec.zero_variance_dims == (0,) and float(rec.sigma[0].item()) == 1.0
    stacked = torch.stack([t for _, t in samples])
    assert torch.allclose(rec.mean, stacked.mean(dim=0), atol=1e-6)
    z_hat = rec.W @ rc.binding_tensor(rec, rows[0], torch=torch) + rec.bias
    assert torch.allclose(rc.reconstruct(rec, rows[0], torch=torch), rec.mean + rec.sigma * z_hat, atol=1e-6)


def test_serialization_round_trip_requires_retained_digest():
    scheme = _scheme()
    truth = _ground_truth(scheme)
    rows = _rows(scheme, ("A", "B"), ("C", "D"))
    rec = rc.fit(_design(scheme, max_steps=10, normalization="TRAIN_ZSCORE"), _samples(scheme, truth, rows), torch=torch, device=DEVICE)
    text, state_digest = rc.serialize(rec)
    back = rc.deserialize(text, torch=torch, device=DEVICE, retained_state_digest=state_digest)
    assert torch.allclose(rc.reconstruct(back, rows[0], torch=torch), rc.reconstruct(rec, rows[0], torch=torch), atol=1e-6)
    assert back.manifest == rec.manifest and back.design == rec.design
    _refused("STATE_DIGEST_MISMATCH", rc.deserialize, text, torch=torch, device=DEVICE, retained_state_digest="0" * 64)
    atomic = rc.fit(_design(scheme, kind="ATOMIC_PAIR", max_steps=3), _samples(scheme, truth, rows), torch=torch, device=DEVICE)
    a_text, a_digest = rc.serialize(atomic)
    a_back = rc.deserialize(a_text, torch=torch, device=DEVICE, retained_state_digest=a_digest)
    assert a_back.pair_seen == atomic.pair_seen and a_back.filler_embedding is None


def test_agreement_and_correctness_are_separate_columns():
    r = rc.agreement_record(original_answer="B", reconstructed_answer="C", gold_answer="D")
    assert r == {"agrees_with_original": False, "original_correct": False, "reconstructed_correct": False,
                 "changed_wrong_to_different_wrong": True}
    r2 = rc.agreement_record(original_answer="B", reconstructed_answer="B")
    assert r2["agrees_with_original"] is True and r2["original_correct"] is None and r2["reconstructed_correct"] is None
