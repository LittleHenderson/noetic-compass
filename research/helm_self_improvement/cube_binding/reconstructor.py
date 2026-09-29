"""CAS-HH-RDE-01-CB1 / A -- explicit, site-shaped tensor-product reconstructor (source-only, NOT RUN).

WHAT THIS MODULE IS. The second CB1-A file. A small DISCOVER-inspired reconstructor (McCoy, Soulos, Linzen,
Smolensky, arXiv:2608.29530v1, sections 2.3 and 3.2) fitted to ADMITTED captured hidden states of ONE site of
ONE frozen checkpoint:

    z_hat = W @ vec( sum_b outer(filler_embedding[b.filler], role_embedding[b.role_path]) ) + bias

Dimensions (all explicit, all pinned in the design record):
    filler_embedding : (n_f, d_f)      role_embedding : (n_r, d_r)
    W                : (d_h, d_f*d_r)  bias           : (d_h,)
    vec ordering     : FILLER_MAJOR -- vec(outer(f, r))[i*d_r + j] = f[i] * r[j]   (torch reshape(-1) of (d_f, d_r))
    dtype float32 on the caller's device; the same ordering is used by fit, reconstruct, serialize and
    `binding_edits.delta`, and it is written into every serialized record.

TWO KINDS. `TPR` is the compositional hypothesis above. `ATOMIC_PAIR` is the paper's non-systematic control:
the same role paths, but every (filler, role) pair is one unanalysable symbol with its own vector in
R^(d_f*d_r); a pair never seen in fitting is refused (`PAIR_UNKNOWN`), because that control has no way to
compose it. Its parameter count is reported next to the TPR's so the comparison is capacity-conscious.

WHAT THE FIT OPTIMISES. Activation reconstruction error only (mean squared error against the captured
vector) plus the declared L2 penalty on W. Samples are (binding_set, target_vector) pairs and nothing
else: a sample carrying an answer, label, score or split field is refused (`FIT_INPUT_FORBIDDEN`). The
HELM checkpoint is never a parameter here: `helm_optimizer_updates` is 0 by construction, and the analysis
update count (`analysis_optimizer_updates`) is the bounded step count actually taken.

NORMALISATION. Optional TRAIN_ZSCORE: mean and sigma computed on the TRAINING targets only, zero-variance
coordinates get sigma = 1 and are listed, nonfinite statistics refuse. `reconstruct` returns native
coordinates (mean + sigma * z_hat). `binding_edits.delta` rescales by sigma only.

WHAT IT PROVES. Nothing about HELM until it is fitted on real, admitted captures inside an admitted job.
A low residual on a labelled synthetic TPR system proves the apparatus, not natural structure.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field

from ..diagnostic_configuration import AUTHORITY, canonical, digest
from .role_schemes import BindingSet, RoleSchemeRefused, Scheme, scheme_digest

DESIGN_SCHEMA = "helm.cube-binding.reconstructor-design/0.1"
STATE_SCHEMA = "helm.cube-binding.reconstructor-state/0.1"
MANIFEST_SCHEMA = "helm.cube-binding.fit-manifest/0.1"
BUDGET_SCHEMA = "helm.cube-binding.fit-budget/0.1"
KINDS = ("TPR", "ATOMIC_PAIR")
NORMALIZATIONS = ("NONE", "TRAIN_ZSCORE")
VEC_ORDER = "FILLER_MAJOR"           # vec(outer(f, r))[i*d_r + j] = f[i]*r[j]
FIT_LOSS = "ACTIVATION_RECONSTRUCTION_MSE_PLUS_L2_ON_W"
DTYPE = "float32"
MAX_STEPS_LIMIT = 20000
MAX_DIM = 4096
FORBIDDEN_SAMPLE_FIELDS = ("answer", "correct", "label", "score", "gold", "split", "on_correct_path", "target_index")


class ReconstructorRefused(ValueError):
    def __init__(self, code, detail=""):
        super().__init__(code if not detail else "%s: %s" % (code, detail))
        self.code = code


def _refuse(code, detail=""):
    raise ReconstructorRefused(code, detail)


def _dim(value, code, limit=MAX_DIM):
    if type(value) is not int or not 1 <= value <= limit:
        _refuse(code, "1..%d, got %r" % (limit, value))
    return value


@dataclass(frozen=True)
class Design:
    schema: str
    kind: str
    scheme_digest: str
    filler_vocabulary: tuple
    role_vocabulary: tuple
    d_f: int
    d_r: int
    d_h: int
    vec_order: str
    dtype: str
    seed: int
    learning_rate: float
    l2_lambda: float
    max_steps: int
    normalization: str
    site: str
    fit_loss: str = FIT_LOSS
    authority: str = AUTHORITY

    @property
    def n_f(self):
        return len(self.filler_vocabulary)

    @property
    def n_r(self):
        return len(self.role_vocabulary)


def design_digest(design):
    body = {k: (list(v) if isinstance(v, tuple) else v) for k, v in design.__dict__.items()}
    body["role_vocabulary"] = [list(r) for r in design.role_vocabulary]
    return digest(body)


def declare_design(scheme, *, kind, d_f, d_r, d_h, site, seed, learning_rate=1e-2, l2_lambda=1e-4, max_steps=200,
                   normalization="NONE"):
    if not isinstance(scheme, Scheme):
        _refuse("SCHEME_TYPE", repr(type(scheme)))
    if kind not in KINDS:
        _refuse("KIND", repr(kind))
    if normalization not in NORMALIZATIONS:
        _refuse("NORMALIZATION", repr(normalization))
    if type(site) is not str or not site:
        _refuse("SITE", "the capture site the fit belongs to must be named")
    if type(seed) is not int:
        _refuse("SEED", repr(seed))
    if type(max_steps) is not int or not 1 <= max_steps <= MAX_STEPS_LIMIT:
        _refuse("MAX_STEPS", "1..%d" % MAX_STEPS_LIMIT)
    for name, value in (("learning_rate", learning_rate), ("l2_lambda", l2_lambda)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
            _refuse("FIT_HYPERPARAMETER", "%s=%r" % (name, value))
    return Design(DESIGN_SCHEMA, kind, scheme_digest(scheme), scheme.filler_vocabulary, scheme.role_vocabulary,
                  _dim(d_f, "D_F"), _dim(d_r, "D_R"), _dim(d_h, "D_H"), VEC_ORDER, DTYPE, seed, float(learning_rate),
                  float(l2_lambda), max_steps, normalization, site)


def parameter_count(design):
    """Effective trainable parameters. The TPR/ATOMIC_PAIR difference is the whole point of the control."""
    dfr = design.d_f * design.d_r
    shared = design.d_h * dfr + design.d_h
    if design.kind == "TPR":
        return {"factors": design.n_f * design.d_f + design.n_r * design.d_r, "W_and_bias": shared,
                "total": design.n_f * design.d_f + design.n_r * design.d_r + shared, "pairs_possible": design.n_f * design.n_r}
    pairs = design.n_f * design.n_r
    return {"pair_symbols": pairs * dfr, "W_and_bias": shared, "total": pairs * dfr + shared, "pairs_possible": pairs}


# ---------------------------------------------------------------------------------------------------------
# Fit resource boundary (owner packet PRIMARY-CB1-INTEGRATE-01, 2026-09-29). Every call to `fit` needs an
# explicit FitBudget. The checks below are COOPERATIVE Python checks: they refuse before allocation when the
# declared limits would be exceeded, and they stop the loop at the deadline or on cancellation. They are NOT a
# hard process-memory or wall-clock limit; the hard limit is the outside runtime named in
# `outside_runtime_limit` (the admitted job's own wall/memory bounds), which the budget record only points at.
# ---------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class FitBudget:
    schema: str
    max_samples: int             # pre-allocation: number of (binding_set, target) samples
    max_parameters: int          # pre-allocation: parameter_count(design)["total"]
    max_tensor_elements: int     # pre-allocation: estimated float32 elements held during the fit
    deadline_seconds: float      # cooperative wall-clock deadline, checked before every optimizer step
    outside_runtime_limit: str   # the hard limit this budget lives under (job wall/memory), named, never claimed here
    python_checks_are_hard_memory_limits: bool = False


def declare_budget(*, max_samples, max_parameters, max_tensor_elements, deadline_seconds, outside_runtime_limit):
    for name, value in (("max_samples", max_samples), ("max_parameters", max_parameters),
                        ("max_tensor_elements", max_tensor_elements)):
        if type(value) is not int or value < 1:
            _refuse("FIT_BUDGET", "%s must be a positive int, got %r" % (name, value))
    if (isinstance(deadline_seconds, bool) or not isinstance(deadline_seconds, (int, float))
            or not math.isfinite(float(deadline_seconds)) or deadline_seconds <= 0):
        _refuse("FIT_BUDGET", "deadline_seconds must be a finite positive number, got %r" % (deadline_seconds,))
    if type(outside_runtime_limit) is not str or not outside_runtime_limit.strip():
        _refuse("FIT_BUDGET", "name the outside runtime limit (the admitted job's wall/memory bound)")
    return FitBudget(BUDGET_SCHEMA, max_samples, max_parameters, max_tensor_elements, float(deadline_seconds),
                     outside_runtime_limit)


def preallocation_estimate(design, sample_count):
    """Float32 elements the fit will hold, estimated BEFORE any tensor exists: targets and predictions
    (2 * samples * d_h), parameters and their gradients (2 * total), one binding tensor (d_f * d_r).
    An estimate of what this code allocates, not a measurement of process memory."""
    if type(sample_count) is not int or sample_count < 0:
        _refuse("FIT_BUDGET", "sample_count must be a non-negative int")
    params = parameter_count(design)["total"]
    elements = 2 * sample_count * design.d_h + 2 * params + design.d_f * design.d_r
    return {"samples": sample_count, "parameters": params, "tensor_elements": elements,
            "bytes_estimate_float32": elements * 4}


@dataclass
class Reconstructor:
    design: Design
    torch_dtype: object
    device: str
    filler_embedding: object      # (n_f, d_f)          TPR only
    role_embedding: object        # (n_r, d_r)          TPR only
    pair_symbols: object          # (n_f*n_r, d_f*d_r)  ATOMIC_PAIR only; row = f_index*n_r + r_index
    pair_seen: object             # python set of pair rows present in fitting (ATOMIC_PAIR)
    W: object                     # (d_h, d_f*d_r)
    bias: object                  # (d_h,)
    mean: object                  # (d_h,) or None
    sigma: object                 # (d_h,) or None
    zero_variance_dims: tuple = ()
    manifest: dict = field(default_factory=dict)


def _pair_row(rec, f_index, r_index):
    return f_index * rec.design.n_r + r_index


def initialise(design, *, torch, device):
    """Seeded initial state; nothing fitted yet."""
    generator = torch.Generator(device="cpu").manual_seed(design.seed)
    dfr = design.d_f * design.d_r
    dtype = torch.float32

    def rand(*shape):
        return (torch.randn(*shape, generator=generator, dtype=dtype) * 0.1).to(device)

    rec = Reconstructor(design, dtype, str(device), None, None, None, set(), rand(design.d_h, dfr),
                        torch.zeros(design.d_h, dtype=dtype, device=device), None, None)
    if design.kind == "TPR":
        rec.filler_embedding, rec.role_embedding = rand(design.n_f, design.d_f), rand(design.n_r, design.d_r)
    else:
        rec.pair_symbols = rand(design.n_f * design.n_r, dfr)
    return rec


def _check_binding_set(rec, binding_set):
    if not isinstance(binding_set, BindingSet):
        _refuse("BINDING_SET_TYPE", repr(type(binding_set)))
    if binding_set.scheme_digest != rec.design.scheme_digest:
        _refuse("SCHEME_MISMATCH", "binding set was built under a different scheme")


def _indices(rec, binding_set):
    design = rec.design
    out = []
    for filler, role in binding_set.records():
        try:
            f_index = design.filler_vocabulary.index(filler)
        except ValueError:
            _refuse("FILLER_UNKNOWN", repr(filler))
        try:
            r_index = design.role_vocabulary.index(tuple(role))
        except ValueError:
            _refuse("ROLE_UNKNOWN", repr(role))
        out.append((f_index, r_index))
    return out


def binding_tensor(rec, binding_set, *, torch):
    """vec(sum_b outer(f_b, r_b)) in FILLER_MAJOR order, shape (d_f*d_r,). Occurrences add: a filler bound
    twice in the same role contributes twice (multiplicity preserved)."""
    _check_binding_set(rec, binding_set)
    design = rec.design
    total = torch.zeros(design.d_f * design.d_r, dtype=rec.torch_dtype, device=rec.device)
    for f_index, r_index in _indices(rec, binding_set):
        if design.kind == "TPR":
            total = total + torch.outer(rec.filler_embedding[f_index], rec.role_embedding[r_index]).reshape(-1)
        else:
            row = _pair_row(rec, f_index, r_index)
            if row not in rec.pair_seen and rec.manifest:      # after fitting, unseen pairs are unknown
                _refuse("PAIR_UNKNOWN", "atomic control cannot compose an unseen (filler, role) pair")
            total = total + rec.pair_symbols[row]
    return total


def reconstruct(rec, binding_set, *, torch):
    """Native coordinates, shape (d_h,): W @ v + bias, de-normalised once (bias once per reconstruction)."""
    z_hat = rec.W @ binding_tensor(rec, binding_set, torch=torch) + rec.bias
    if rec.design.normalization == "TRAIN_ZSCORE":
        return rec.mean + rec.sigma * z_hat
    return z_hat


def _check_target(rec, target, *, torch):
    if not torch.is_tensor(target):
        _refuse("TARGET_TYPE", repr(type(target)))
    if tuple(target.shape) != (rec.design.d_h,):
        _refuse("TARGET_SHAPE", "expected (%d,), got %r" % (rec.design.d_h, tuple(target.shape)))
    if str(target.dtype) != "torch.float32":
        _refuse("TARGET_DTYPE", str(target.dtype))
    if not bool(torch.isfinite(target).all()):
        _refuse("TARGET_NONFINITE")
    return target.detach().to(rec.device)


def _samples(rec, samples, *, torch):
    out = []
    for sample in samples:
        if isinstance(sample, dict):
            bad = sorted(k for k in sample if k in FORBIDDEN_SAMPLE_FIELDS)
            if bad:
                _refuse("FIT_INPUT_FORBIDDEN", ",".join(bad))
            if set(sample) != {"bindings", "target"}:
                _refuse("FIT_INPUT_SHAPE", "a sample is {bindings, target} and nothing else")
            binding_set, target = sample["bindings"], sample["target"]
        else:
            if len(sample) != 2:
                _refuse("FIT_INPUT_SHAPE", "a sample is (binding_set, target) and nothing else")
            binding_set, target = sample
        _check_binding_set(rec, binding_set)
        out.append((binding_set, _check_target(rec, target, torch=torch)))
    if not out:
        _refuse("FIT_INPUT_EMPTY")
    return out


def fit(design, samples, *, torch, device, budget, holdout_pairs=(), cancel=None, clock=time.monotonic):
    """Bounded gradient fit of activation reconstruction only. `holdout_pairs` are (filler, role_path)
    combinations that must NOT appear in the training samples (analysis holdout, paper section 8).

    `budget` (a FitBudget) is mandatory: sample, parameter and tensor limits are checked BEFORE any tensor is
    allocated; the deadline and the optional `cancel()` callable are checked before every optimizer step.
    A refusal at any of these points returns nothing: no partial reconstructor is handed back. `clock` is
    injectable for deterministic tests. These are cooperative checks under the outside runtime limit the
    budget names; they are not a hard process limit."""
    if not isinstance(budget, FitBudget):
        _refuse("FIT_BUDGET_REQUIRED", "fit needs an explicit FitBudget from declare_budget")
    samples = list(samples)
    estimate = preallocation_estimate(design, len(samples))
    if estimate["samples"] > budget.max_samples:
        _refuse("FIT_SAMPLE_LIMIT", "%d > %d" % (estimate["samples"], budget.max_samples))
    if estimate["parameters"] > budget.max_parameters:
        _refuse("FIT_PARAMETER_LIMIT", "%d > %d" % (estimate["parameters"], budget.max_parameters))
    if estimate["tensor_elements"] > budget.max_tensor_elements:
        _refuse("FIT_TENSOR_LIMIT", "%d > %d" % (estimate["tensor_elements"], budget.max_tensor_elements))
    if cancel is not None and not callable(cancel):
        _refuse("FIT_BUDGET", "cancel must be callable")
    started = clock()
    rec = initialise(design, torch=torch, device=device)
    data = _samples(rec, samples, torch=torch)
    held = {(f, tuple(r)) for f, r in holdout_pairs}
    for binding_set, _ in data:
        leak = held & set(binding_set.records())
        if leak:
            _refuse("HOLDOUT_LEAK", repr(sorted(leak)[:3]))
    if design.kind == "ATOMIC_PAIR":
        for binding_set, _ in data:
            for f_index, r_index in _indices(rec, binding_set):
                rec.pair_seen.add(_pair_row(rec, f_index, r_index))
    targets = torch.stack([t for _, t in data])
    if design.normalization == "TRAIN_ZSCORE":
        mean = targets.mean(dim=0)
        sigma = targets.std(dim=0, correction=0)
        zero = [int(i) for i in torch.nonzero(sigma == 0).reshape(-1).tolist()]
        sigma = torch.where(sigma == 0, torch.ones_like(sigma), sigma)
        if not bool(torch.isfinite(mean).all()) or not bool(torch.isfinite(sigma).all()):
            _refuse("NORMALIZATION_NONFINITE")
        rec.mean, rec.sigma, rec.zero_variance_dims = mean, sigma, tuple(zero)
        fit_targets = (targets - mean) / sigma
    else:
        fit_targets = targets
    params = [rec.W, rec.bias] + ([rec.filler_embedding, rec.role_embedding] if design.kind == "TPR" else [rec.pair_symbols])
    for p in params:
        p.requires_grad_(True)
    optimizer = torch.optim.Adam(params, lr=design.learning_rate)
    first_loss = last_loss = None
    steps = 0
    for _step in range(design.max_steps):                       # bounded in the loop itself
        elapsed = clock() - started
        if elapsed > budget.deadline_seconds:
            _refuse("FIT_DEADLINE_EXCEEDED", "%.3fs > %.3fs after %d steps" % (elapsed, budget.deadline_seconds, steps))
        if cancel is not None and cancel():
            _refuse("FIT_CANCELLED", "after %d steps" % steps)
        optimizer.zero_grad()
        preds = torch.stack([rec.W @ binding_tensor(rec, b, torch=torch) + rec.bias for b, _ in data])
        mse = ((preds - fit_targets) ** 2).mean()
        loss = mse + design.l2_lambda * (rec.W ** 2).sum()
        if not bool(torch.isfinite(loss)):
            _refuse("FIT_NONFINITE", "step %d" % steps)
        loss.backward()
        optimizer.step()
        steps += 1
        value = float(loss.item())
        first_loss = value if first_loss is None else first_loss
        last_loss = value
    for p in params:
        p.requires_grad_(False)
    rec.manifest = {"schema": MANIFEST_SCHEMA, "design_digest": design_digest(design), "samples": len(data),
                    "analysis_optimizer_updates": steps, "helm_optimizer_updates": 0, "fit_loss": FIT_LOSS,
                    "first_loss": first_loss, "last_loss": last_loss, "parameters": parameter_count(design),
                    "holdout_pairs": sorted([f, list(r)] for f, r in held), "zero_variance_dims": list(rec.zero_variance_dims),
                    "device": rec.device, "dtype": DTYPE, "vec_order": VEC_ORDER, "target_weights": "FROZEN_NOT_A_PARAMETER",
                    "budget": {"schema": budget.schema, "max_samples": budget.max_samples,
                               "max_parameters": budget.max_parameters, "max_tensor_elements": budget.max_tensor_elements,
                               "deadline_seconds": budget.deadline_seconds, "elapsed_seconds": float(clock() - started),
                               "preallocation_estimate": estimate, "outside_runtime_limit": budget.outside_runtime_limit,
                               "python_checks_are_hard_memory_limits": False}}
    return rec


def residuals(rec, samples, *, torch):
    """Per-sample reconstruction error in native coordinates: (||z_hat - z||, ||z||). No answers involved."""
    out = []
    for binding_set, target in _samples(rec, samples, torch=torch):
        diff = reconstruct(rec, binding_set, torch=torch) - target
        out.append({"residual_norm": float(diff.norm().item()), "target_norm": float(target.norm().item())})
    return out


def agreement_record(*, original_answer, reconstructed_answer, gold_answer=None):
    """CB18: agreement with the original model and correctness under the evaluator are different columns.
    `gold_answer` may only be supplied by the evaluator side; None keeps correctness UNKNOWN."""
    return {"agrees_with_original": original_answer == reconstructed_answer,
            "original_correct": None if gold_answer is None else original_answer == gold_answer,
            "reconstructed_correct": None if gold_answer is None else reconstructed_answer == gold_answer,
            "changed_wrong_to_different_wrong": (None if gold_answer is None else
                                                (original_answer != gold_answer and reconstructed_answer != gold_answer
                                                 and original_answer != reconstructed_answer))}


def _tensor_list(t):
    return None if t is None else t.detach().to("cpu").reshape(-1).tolist()


def serialize(rec):
    design = rec.design
    body = {"schema": STATE_SCHEMA, "design": json.loads(canonical({k: (list(v) if isinstance(v, tuple) else v)
                                                                    for k, v in design.__dict__.items()})),
            "design_digest": design_digest(design), "vec_order": VEC_ORDER, "dtype": DTYPE,
            "shapes": {"W": [design.d_h, design.d_f * design.d_r], "bias": [design.d_h],
                       "filler_embedding": [design.n_f, design.d_f] if design.kind == "TPR" else None,
                       "role_embedding": [design.n_r, design.d_r] if design.kind == "TPR" else None,
                       "pair_symbols": [design.n_f * design.n_r, design.d_f * design.d_r] if design.kind != "TPR" else None},
            "W": _tensor_list(rec.W), "bias": _tensor_list(rec.bias),
            "filler_embedding": _tensor_list(rec.filler_embedding), "role_embedding": _tensor_list(rec.role_embedding),
            "pair_symbols": _tensor_list(rec.pair_symbols), "pair_seen": sorted(rec.pair_seen),
            "mean": _tensor_list(rec.mean), "sigma": _tensor_list(rec.sigma), "zero_variance_dims": list(rec.zero_variance_dims),
            "manifest": rec.manifest}
    body["design"]["role_vocabulary"] = [list(r) for r in design.role_vocabulary]
    text = canonical(body)
    return text, digest(body)


def deserialize(text, *, torch, device, retained_state_digest):
    """Reload needs the externally retained digest of the serialized state; the text cannot vouch for itself."""
    body = json.loads(text)
    if digest(body) != retained_state_digest:
        _refuse("STATE_DIGEST_MISMATCH", "serialized reconstructor is not the retained one")
    if body.get("schema") != STATE_SCHEMA or body.get("vec_order") != VEC_ORDER:
        _refuse("STATE_SCHEMA", "%r / %r" % (body.get("schema"), body.get("vec_order")))
    d = dict(body["design"])
    d["filler_vocabulary"] = tuple(d["filler_vocabulary"])
    d["role_vocabulary"] = tuple(tuple(r) for r in d["role_vocabulary"])
    design = Design(**d)
    if design_digest(design) != body.get("design_digest"):
        _refuse("STATE_DESIGN_MISMATCH")

    def tensor(values, shape):
        if values is None:
            return None
        t = torch.tensor(values, dtype=torch.float32, device=device)
        if t.numel() != math.prod(shape):
            _refuse("STATE_SHAPE", "%r for %r" % (t.numel(), shape))
        return t.reshape(*shape)

    shapes = body["shapes"]
    rec = Reconstructor(design, torch.float32, str(device),
                        tensor(body["filler_embedding"], shapes["filler_embedding"] or [0]),
                        tensor(body["role_embedding"], shapes["role_embedding"] or [0]),
                        tensor(body["pair_symbols"], shapes["pair_symbols"] or [0]), set(body["pair_seen"]),
                        tensor(body["W"], shapes["W"]), tensor(body["bias"], shapes["bias"]),
                        tensor(body["mean"], [design.d_h]), tensor(body["sigma"], [design.d_h]),
                        tuple(body["zero_variance_dims"]), dict(body["manifest"]))
    return rec
