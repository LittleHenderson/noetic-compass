"""CAS-HH-RDE-01-CB1 / A -- bounded binding edits in native coordinates (source-only, NOT RUN).

WHAT THIS MODULE IS. The third CB1-A file. A binding edit replaces one declared binding in a row's binding
set and turns the difference into ONE additive delta on the captured representation of that row:

    delta_z   = W @ ( vec(sum new terms) - vec(sum old terms) )        (the bias cancels: never added here)
    delta_raw = sigma * delta_z   when the reconstructor was fitted TRAIN_ZSCORE  (sigma only, never mean)
    h_edited  = h_original + delta_raw

The apparatus then hands the edit to the INCUMBENT typed intervention path unchanged: the plan is composed
into a `diagnostic_intervention.Donor` whose values are `h_original + delta_raw` for the declared row at the
declared site and round, and into a `SAME_INPUT_PATCH` declaration through `diagnostic_intervention.declare`.
That declaration is what the trusted caller passes to `diagnostic_intervention.apply`, which registers one
hook on one module of the caller-bound model, records every hit, removes the hook on every exit and refuses
an unverified model binding. Nothing here calls the model, patches the learner, or makes Codex's passive
`emit` callback writable.

THE SEAM. Codex's seam statement (PR #245 comment 5884514028): `graph.node_state` is arithmetic output and
the intervention deliberately refuses it; `graph.round_update` is the real `core_block` post-hook and every
downstream consumer (later rounds, query state, pointer query, node and reach heads) is recomputed on the
same fresh forward. That matches the learner lines cited in `diagnostic_intervention.HOOK_SITES` (the round
update is added to the hidden state at line 1200, all heads run later in the same `_graph` forward). It is
recorded here as SOURCE_CONSISTENT_NOT_EXECUTED: no forward has been run to confirm it.

FIRST PACKET SCOPE. `NO_CHANGE` (delta exactly zero, expected receipt status APPLIED_NO_CHANGE) and
`FILLER_REPLACEMENT` (one declared binding's filler replaced within one role, e.g. row A: (B, contains/out/1)
-> (D, contains/out/1), the section 3.1 endpoint edit). ROLE_REASSIGNMENT, TWO_ROLE_SWAP and ENDPOINT_SWAP
are named and refused until the first footprint is characterised (directive: "not every edit family at once").

SINGLE APPLICATION. One site, one round, one row, one forward: `verify_single_application` reads the
finalized receipt and refuses a second targeted hit (`DOUBLE_APPLICATION`), a hit whose measured change does
not match the planned delta, or a receipt without caller-verified model binding.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .. import diagnostic_intervention as di
from ..diagnostic_configuration import AUTHORITY, BASIS, CORE_ROUNDS, SITE_SEMANTICS, digest
from .reconstructor import Reconstructor, binding_tensor, design_digest
from .role_schemes import Binding, BindingSet, binding_set_digest

EDIT_SCHEMA = "helm.cube-binding.binding-edit/0.1"
PLAN_SCHEMA = "helm.cube-binding.edit-plan/0.1"
EDIT_KINDS = ("NO_CHANGE", "FILLER_REPLACEMENT", "ROLE_REASSIGNMENT", "TWO_ROLE_SWAP", "ENDPOINT_SWAP")
SUPPORTED_EDIT_KINDS = ("NO_CHANGE", "FILLER_REPLACEMENT")
EXPECTED_EFFECTS = ("NO_CHANGE", "PREDICTED_ANSWER_CHANGE", "PREDICTED_NO_ANSWER_CHANGE")
EDIT_SITE = "graph.round_update"
DESCENDANT_RECOMPUTATION = {
    "site": EDIT_SITE, "module": "core_block", "hook": "post",
    "recomputed_on_same_forward": ("graph.round_state (rounds after the edited one)", "graph.node_state",
                                   "graph.query_state", "graph.pointer_query", "head.node", "head.node_pointer", "head.reach"),
    "stale_cache_risk": "none inside one forward: no consumer reads a cached copy of the edited round update",
    "status": "SOURCE_CONSISTENT_NOT_EXECUTED", "source": "PR #245 comment 5884514028 (Codex seam statement)",
}
DELTA_TOLERANCE = 1e-4


class BindingEditRefused(ValueError):
    def __init__(self, code, detail=""):
        super().__init__(code if not detail else "%s: %s" % (code, detail))
        self.code = code


def _refuse(code, detail=""):
    raise BindingEditRefused(code, detail)


@dataclass(frozen=True)
class Edit:
    schema: str
    kind: str
    role_path: tuple
    old_filler: object
    new_filler: object
    occurrence: tuple


def declare_edit(kind, *, role_path=(), old_filler=None, new_filler=None, occurrence=()):
    if kind not in EDIT_KINDS:
        _refuse("EDIT_KIND", repr(kind))
    if kind not in SUPPORTED_EDIT_KINDS:
        _refuse("EDIT_KIND_NOT_IN_FIRST_PACKET", kind)
    if kind == "NO_CHANGE":
        if role_path or old_filler is not None or new_filler is not None or occurrence:
            _refuse("EDIT_FIELDS", "NO_CHANGE carries no target")
        return Edit(EDIT_SCHEMA, kind, (), None, None, ())
    if not role_path or type(old_filler) is not str or type(new_filler) is not str or not occurrence:
        _refuse("EDIT_FIELDS", "FILLER_REPLACEMENT needs role_path, old_filler, new_filler, occurrence")
    if old_filler == new_filler:
        _refuse("EDIT_FIELDS", "replacement with the same filler is NO_CHANGE, declare it as such")
    return Edit(EDIT_SCHEMA, kind, tuple(role_path), old_filler, new_filler, tuple(occurrence))


def edit_digest(edit):
    return digest({"schema": edit.schema, "kind": edit.kind, "role_path": list(edit.role_path),
                   "old_filler": edit.old_filler, "new_filler": edit.new_filler, "occurrence": list(edit.occurrence)})


def edit_bindings(old_set, edit):
    """The new binding set. Exactly one binding (by filler, role AND occurrence) is replaced; absent -> refuse."""
    if not isinstance(old_set, BindingSet):
        _refuse("BINDING_SET_TYPE", repr(type(old_set)))
    if edit.kind == "NO_CHANGE":
        return old_set
    target = Binding(edit.old_filler, edit.role_path, edit.occurrence)
    if target not in old_set.bindings:
        _refuse("EDIT_TARGET_ABSENT", repr(target))
    replaced = False
    bindings = []
    for b in old_set.bindings:
        if b == target and not replaced:
            bindings.append(Binding(edit.new_filler, b.role_path, b.occurrence))
            replaced = True
        else:
            bindings.append(b)
    ordered = tuple(sorted(bindings, key=lambda b: (b.role_path, b.filler, b.occurrence)))
    return BindingSet(old_set.schema, old_set.scheme_digest, old_set.scope, old_set.receiving, ordered, old_set.truncated)


def delta(rec, old_set, new_set, *, torch):
    """Native-coordinate delta, shape (d_h,). Bias never enters; TRAIN_ZSCORE rescales by sigma only."""
    if not isinstance(rec, Reconstructor):
        _refuse("RECONSTRUCTOR_TYPE", repr(type(rec)))
    if not rec.manifest:
        _refuse("RECONSTRUCTOR_UNFITTED", "edits need a fitted, frozen reconstructor")
    difference = binding_tensor(rec, new_set, torch=torch) - binding_tensor(rec, old_set, torch=torch)
    delta_z = rec.W @ difference
    out = rec.sigma * delta_z if rec.design.normalization == "TRAIN_ZSCORE" else delta_z
    if not bool(torch.isfinite(out).all()):
        _refuse("DELTA_NONFINITE")
    return out.detach()


@dataclass(frozen=True)
class Plan:
    schema: str
    site: str
    round_index: int
    row: int
    receiving_node: str
    edit_digest: str
    old_binding_digest: str
    new_binding_digest: str
    reconstructor_design_digest: str
    reconstructor_state_digest: str
    expected_effect: str
    hypothesis_id: str
    checkpoint_sha256: str
    input_sha256: str
    source_sha256: str
    max_delta_norm: float
    descendant_recomputation: dict
    authority: str = AUTHORITY
    basis: str = BASIS


def plan_digest(plan):
    body = dict(plan.__dict__)
    return digest(body)


def freeze_plan(*, rec, state_digest, old_set, new_set, edit, row, round_index, expected_effect, hypothesis_id,
                checkpoint_sha256, input_sha256, source_sha256, max_delta_norm, site=EDIT_SITE):
    """Frozen BEFORE the caller runs anything. One row, one round, one site; the bound on the delta norm
    is part of the plan so an oversized edit is refused instead of applied."""
    if site != EDIT_SITE:
        _refuse("EDIT_SITE", "first packet edits only %s (Codex seam); got %r" % (EDIT_SITE, site))
    if not SITE_SEMANTICS[site]["per_round"] or type(round_index) is not int or not 0 <= round_index < CORE_ROUNDS:
        _refuse("ROUND_INDEX", repr(round_index))
    if type(row) is not int or row < 0:
        _refuse("ROW", repr(row))
    if old_set.receiving is None or old_set.receiving != new_set.receiving:
        _refuse("RECEIVING_NODE", "old and new sets must belong to the same receiving row")
    if expected_effect not in EXPECTED_EFFECTS:
        _refuse("EXPECTED_EFFECT", repr(expected_effect))
    if edit.kind == "NO_CHANGE" and expected_effect != "NO_CHANGE":
        _refuse("EXPECTED_EFFECT", "NO_CHANGE edits expect NO_CHANGE")
    if edit.kind != "NO_CHANGE" and expected_effect == "NO_CHANGE":
        _refuse("EXPECTED_EFFECT", "an active edit must predict its effect")
    # Codex source finding (PR #245 comment 5884742440): `nan <= 0` and `inf <= 0` are both False, so type and
    # positivity alone let a non-finite bound through to the donor comparison, where `norm > nan` is False too.
    if (isinstance(max_delta_norm, bool) or not isinstance(max_delta_norm, (int, float))
            or not math.isfinite(float(max_delta_norm)) or max_delta_norm <= 0):
        _refuse("MAX_DELTA_NORM", "finite positive number required, got %r" % (max_delta_norm,))
    if type(state_digest) is not str or len(state_digest) != 64:
        _refuse("RECONSTRUCTOR_STATE_DIGEST", "the serialized state digest that will be retained is required")
    return Plan(PLAN_SCHEMA, site, round_index, row, old_set.receiving, edit_digest(edit), binding_set_digest(old_set),
                binding_set_digest(new_set), design_digest(rec.design), state_digest, expected_effect, hypothesis_id,
                checkpoint_sha256, input_sha256, source_sha256, float(max_delta_norm), dict(DESCENDANT_RECOMPUTATION))


def donor_for_plan(plan, delta_vector, original_row, *, torch, capture_digest, provenance="STIMULUS_ONLY"):
    """Compose `h_original + delta` into a typed donor for the incumbent SAME_INPUT_PATCH action.

    `original_row` is the captured value of the planned row at the planned site/round (from Codex's passive
    capture of the SAME input at the SAME checkpoint; `capture_digest` names it). `provenance` stays
    STIMULUS_ONLY unless the edit was chosen with gold knowledge, in which case the caller MUST say
    GOLD_INFORMED and the incumbent path caps the claim at ORACLE_ASSISTED_DIAGNOSIS_NOT_DEPLOYABLE."""
    if not torch.is_tensor(delta_vector) or not torch.is_tensor(original_row):
        _refuse("DELTA_TYPE", "tensors required")
    if delta_vector.shape != original_row.shape or delta_vector.dim() != 1:
        _refuse("DELTA_SHAPE", "%r vs %r" % (tuple(delta_vector.shape), tuple(original_row.shape)))
    norm = float(delta_vector.to(torch.float32).norm().item())
    if norm > plan.max_delta_norm:
        _refuse("DELTA_NORM_EXCEEDED", "%r > %r" % (norm, plan.max_delta_norm))
    if plan.expected_effect == "NO_CHANGE" and norm != 0.0:
        _refuse("NO_CHANGE_NOT_ZERO", repr(norm))
    patched = (original_row.to(torch.float32) + delta_vector.to(torch.float32)).to(original_row.dtype)
    return di.donor(input_sha256=plan.input_sha256, capture_digest=capture_digest, checkpoint_sha256=plan.checkpoint_sha256,
                    provenance=provenance, basis=SITE_SEMANTICS[plan.site]["basis"],
                    dtype=str(original_row.dtype).replace("torch.", ""), device=str(original_row.device),
                    values=patched.detach().to("cpu").reshape(-1).tolist())


def consumer_inputs_for_plan(plan, delta_vector, *, original_values, shape, torch, provenance="STIMULUS_ONLY"):
    """The keyword set Codex's `consumer_bridge.prepare_consumer_declaration` takes (CB1-C at `c9b0bfd3`).

    Codex's bridge replaces the WHOLE captured tensor of the site (all rows, all coordinates) from an
    externally anchored complete capture. `original_values` is that capture's row-major `signed_values`
    and `shape` its `(rows, width)`. This composes `h_original + delta` into the planned row only, leaves
    every other row byte-equal to the capture, and derives the finite `max_abs_delta` bound from the delta.
    A NO_CHANGE plan maps to the bridge's no-op path (`native_values=None`, incumbent NO_OP_CONTROL).
    Nothing here is executed; the returned dict is data for the bridge, which returns a declaration only."""
    if len(shape) != 2:
        _refuse("CAPTURE_SHAPE", "row-wise site capture (rows, width) required, got %r" % (tuple(shape),))
    rows, width = int(shape[0]), int(shape[1])
    if rows <= 0 or width <= 0 or len(original_values) != rows * width:
        _refuse("CAPTURE_SHAPE", "%d values for shape %r" % (len(original_values), tuple(shape)))
    if plan.row >= rows:
        _refuse("ROW", "plan row %d outside %d captured rows" % (plan.row, rows))
    if not torch.is_tensor(delta_vector):
        _refuse("DELTA_TYPE", repr(type(delta_vector)))
    base = dict(hypothesis_id=plan.hypothesis_id, predicted_change="%s:%s" % (plan.expected_effect, plan_digest(plan)[:16]))
    if plan.expected_effect == "NO_CHANGE":
        if float(delta_vector.to(torch.float32).norm().item()) != 0.0:
            _refuse("NO_CHANGE_NOT_ZERO")
        return dict(base, native_values=None, max_abs_delta=None, donor_provenance=None)
    if tuple(delta_vector.shape) != (width,):
        _refuse("DELTA_SHAPE", "expected (%d,), got %r" % (width, tuple(delta_vector.shape)))
    if provenance not in di.DONOR_PROVENANCE:
        _refuse("PROVENANCE", repr(provenance))
    norm = float(delta_vector.to(torch.float32).norm().item())
    if norm > plan.max_delta_norm:
        _refuse("DELTA_NORM_EXCEEDED", "%r > %r" % (norm, plan.max_delta_norm))
    values = [float(v) for v in original_values]
    start = plan.row * width
    original_row = torch.tensor(values[start:start + width], dtype=torch.float32)
    patched = (original_row + delta_vector.detach().to("cpu", torch.float32)).tolist()
    values[start:start + width] = patched
    max_abs = max(abs(new - old) for new, old in zip(patched, original_values[start:start + width]))
    max_abs_delta = max_abs * (1.0 + 1e-6) + 1e-12          # the bridge requires |new - old| <= bound, elementwise
    return dict(base, native_values=values, max_abs_delta=max_abs_delta, donor_provenance=provenance)


def declaration_for_plan(plan, donor, *, width):
    """The incumbent declaration: SAME_INPUT_PATCH on one row, all `width` coordinates, one round."""
    if type(width) is not int or width <= 0 or len(donor.values) != width:
        _refuse("WIDTH", "donor carries %d values for width %r" % (len(donor.values), width))
    return di.declare(action="SAME_INPUT_PATCH", site=plan.site, checkpoint_sha256=plan.checkpoint_sha256,
                      input_sha256=plan.input_sha256, source_sha256=plan.source_sha256, rows=(plan.row,),
                      coordinates=tuple(range(width)), round_index=plan.round_index, donor=donor,
                      hypothesis_id=plan.hypothesis_id, predicted_change="%s:%s" % (plan.expected_effect, plan_digest(plan)[:16]))


def verify_single_application(receipt, plan, delta_vector, *, torch):
    """Read a finalized incumbent receipt: exactly one targeted hit, at the planned round, with the planned
    change, on a caller-verified module, hooks removed, parameters unchanged. Anything else refuses."""
    if not isinstance(receipt, di.Receipt):
        _refuse("RECEIPT_TYPE", repr(type(receipt)))
    no_op = plan.expected_effect == "NO_CHANGE" and receipt.operation == "NO_OP_CONTROL"   # the bridge's no-op path
    if receipt.site != plan.site or (receipt.operation != "SAME_INPUT_PATCH" and not no_op):
        _refuse("RECEIPT_MISMATCH", "%s/%s" % (receipt.site, receipt.operation))
    targeted = receipt.targeted_hits()
    if len(targeted) > 1:
        _refuse("DOUBLE_APPLICATION", "%d targeted hits; one forward, one application" % len(targeted))
    if len(targeted) != 1:
        _refuse("NOT_APPLIED", "no targeted hit; status %s errors %r" % (receipt.status, receipt.errors))
    hit = targeted[0]
    if hit["round_index"] != plan.round_index:
        _refuse("ROUND_MISMATCH", "%r vs %r" % (hit["round_index"], plan.round_index))
    if receipt.model_binding != "CALLER_VERIFIED":
        _refuse("MODEL_BINDING_UNVERIFIED")
    if receipt.hooks_removed is not True or receipt.parameters_unchanged is not True:
        _refuse("STATE_NOT_RESTORED", "hooks_removed=%r parameters_unchanged=%r" % (receipt.hooks_removed, receipt.parameters_unchanged))
    if not hit["untargeted_unchanged"]:
        _refuse("COLLATERAL_ROWS_CHANGED")
    planned_norm = float(delta_vector.to(torch.float32).norm().item())
    if plan.expected_effect == "NO_CHANGE":
        wanted = "NO_OP_VERIFIED" if no_op else "APPLIED_NO_CHANGE"
        if receipt.status != wanted or hit["changed_count"] != 0:
            _refuse("NO_CHANGE_NOT_VERIFIED", "status %s changed %d" % (receipt.status, hit["changed_count"]))
    else:
        if receipt.status != "APPLIED":
            _refuse("NOT_APPLIED", receipt.status)
        if abs(hit["delta_norm"] - planned_norm) > DELTA_TOLERANCE * max(1.0, planned_norm):
            _refuse("DELTA_MISMATCH", "measured %r planned %r" % (hit["delta_norm"], planned_norm))
    return {"schema": "helm.cube-binding.application-check/0.1", "plan_digest": plan_digest(plan), "status": receipt.status,
            "call_index": hit["call_index"], "round_index": hit["round_index"], "measured_delta_norm": hit["delta_norm"],
            "planned_delta_norm": planned_norm, "claim_ceiling": receipt.claim_ceiling, "single_application": True}
