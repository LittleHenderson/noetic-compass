"""CAS-HH-RDE-01 / A -- bounded within-checkpoint intervention bridge for HELM container sites.

WHAT THIS MODULE IS. The intervention half of Claude's leased adapter. It adapts the Harness's
`capture_probes`/`EraserIntervention` pattern (Pythia: forward hook on each layer's MLP, last-token
coordinate suppression with `factor = max(0, 1 - max(0, gain))`, hooks always removed) to the HELM container
modules that the contract sites name. The hooks are ordinary torch hook handles on ONE module of ONE model
object, registered inside a context manager and removed on every exit path; nothing is patched globally and
the learner file is never edited.

WHICH SITES ARE REACHABLE THIS WAY (HH15). Only sites computed BY A MODULE CALL are hookable without a
learner change: `graph.round_input` (pre-hook on `model.core_block`, whose input is exactly `hidden_input`,
`pointer_learner.py:1191-1199`), `graph.round_update` (post-hook, its output), `graph.pointer_query`
(`model.pointer_key`, line 1313), `head.node` (`model.node_head`, line 1347) and `head.reach`
(`model.reach_option_head`, line 1512). `head.node_pointer` is `states.matmul(pointer_query)` (line 1417),
a tensor operation, so it is recorded NOT_HOOKABLE and refused rather than approximated. The learner's
passive `observe` callback cannot intervene: `_rounds` ignores its return.

THE GRAMMAR. OBSERVE_ONLY (records, never returns a tensor), NO_OP_CONTROL (sham edit through the SAME
clone-write-return path, must leave the tensor bitwise equal), one active action -- SUPPRESS (Harness gain
semantics on declared rows x coordinates at one declared round) or SAME_INPUT_PATCH (declared donor values
from the SAME checkpoint, same basis, explicit dtype/device) -- and MATCHED_CONTROL (same site, rows, round,
gain and coordinate COUNT, disjoint coordinates chosen by a recorded seed). A gold-informed donor caps the
claim at ORACLE_ASSISTED_DIAGNOSIS_NOT_DEPLOYABLE.

WHAT THE RECEIPT PROVES (HH10/HH11). Every hook call is a hit row: call index, round index, shape, whether it
was the targeted call, before/after values of the targeted entries, changed count, max |delta|, delta norm,
and that untargeted entries are unchanged. `finalize` turns hits into one status: APPLIED, APPLIED_NO_CHANGE
(hit, but every targeted value was already 0 or the donor equalled it), NOT_APPLIED (no targeted hit, or an
error), NO_OP_VERIFIED / NO_OP_FAILED, OBSERVED / OBSERVED_INCOMPLETE. A failed active action raises inside
the forward; it is never reported as a successful no-op. Hook removal and parameter preservation are checked
in `finally` and written into the receipt.

Authority: `OBSERVATION_ONLY_NO_PROMOTION`. Basis: `WITHIN_CHECKPOINT_ONLY`. Actor recorded on every
declaration and receipt: this is an externally directed diagnostic, not native HELM reasoning.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field

from .diagnostic_configuration import (AUTHORITY, BASIS, CORE_ROUNDS, LEARNER_SHA256, SITE_SEMANTICS,
                                       canonical, digest, _hex64)

DECLARATION_SCHEMA = "helm.harness.intervention-declaration/0.1"
RECEIPT_SCHEMA = "helm.harness.intervention-receipt/0.1"
ACTOR = "EXTERNAL_LEAD_CLAUDE"
ACTIONS = ("OBSERVE_ONLY", "NO_OP_CONTROL", "SUPPRESS", "SAME_INPUT_PATCH", "MATCHED_CONTROL")
ACTIVE_ACTIONS = ("SUPPRESS", "SAME_INPUT_PATCH")
DONOR_PROVENANCE = ("STIMULUS_ONLY", "GOLD_INFORMED")
CLAIM_CEILINGS = ("WITHIN_CHECKPOINT_DIAGNOSTIC", "ORACLE_ASSISTED_DIAGNOSIS_NOT_DEPLOYABLE")
STATUSES = ("OBSERVED", "OBSERVED_INCOMPLETE", "NO_OP_VERIFIED", "NO_OP_FAILED", "APPLIED",
            "APPLIED_NO_CHANGE", "NOT_APPLIED")
MODEL_BINDINGS = ("CALLER_VERIFIED", "UNVERIFIED_SELF_REPORTED")
DEFAULT_MAX_RECEIPT_BYTES = 8 * 1024 * 1024
FLOAT_BYTES = 4

# site -> (container attribute, hook kind). The attribute names are the container's own (`_build_container`,
# `pointer_learner.py:777-856`); widths are read from the bound module, never restated here.
HOOK_SITES = {
    "graph.round_input": ("core_block", "pre"),
    "graph.round_update": ("core_block", "post"),
    "graph.pointer_query": ("pointer_key", "post"),
    "head.node": ("node_head", "post"),
    "head.reach": ("reach_option_head", "post"),
}
NOT_HOOKABLE = {
    "head.node_pointer": "states.matmul(pointer_query) at pointer_learner.py:1417 is a tensor op, not a module call",
    "graph.initial_state": "hidden = _rms_unit(node_encode(raw)) at line 1160: node_encode output is pre-normalisation",
    "graph.round_state": "hidden update at line 1200 is arithmetic, not a module call",
    "graph.node_state": "final hidden (line 1303) is the round-state tensor, not a module output",
    "graph.query_state": "query_value adds node states after query_norm (lines 1361-1376); the module output is only `base`",
    "input.mapping": "not a tensor", "answer.scores": "not a module output", "answer.decisions": "not a tensor",
    "answer.assembly": "not a tensor",
}
assert set(HOOK_SITES) | set(NOT_HOOKABLE) == set(SITE_SEMANTICS)
assert not (set(HOOK_SITES) & set(NOT_HOOKABLE))


class InterventionRefused(ValueError):
    def __init__(self, code, detail=""):
        super().__init__(code if not detail else "%s: %s" % (code, detail))
        self.code = code


def _refuse(code, detail=""):
    raise InterventionRefused(code, detail)


def suppression_factor(gain):
    """The Harness eraser's own formula (`probe_runner.py:211`): `max(0.0, 1.0 - max(0.0, float(gain)))`."""
    return max(0.0, 1.0 - max(0.0, float(gain)))


def _index_tuple(values, code, allow_empty=False):
    values = tuple(values)
    if not values and not allow_empty:
        _refuse(code, "empty")
    if any(type(v) is not int or v < 0 for v in values) or len(set(values)) != len(values):
        _refuse(code, "non-negative distinct ints required, got %r" % (values,))
    return values


@dataclass(frozen=True)
class Donor:
    input_sha256: str
    capture_digest: str
    checkpoint_sha256: str
    provenance: str
    basis: str
    dtype: str
    device: str
    values: tuple            # len(rows) * len(coordinates), row-major over the declared rows/coordinates


def donor(*, input_sha256, capture_digest, checkpoint_sha256, provenance, basis, dtype, device, values):
    for name, value in (("input_sha256", input_sha256), ("capture_digest", capture_digest),
                        ("checkpoint_sha256", checkpoint_sha256)):
        _hex64(value, "DONOR_IDENTITY:" + name)
    if provenance not in DONOR_PROVENANCE:
        _refuse("DONOR_PROVENANCE", repr(provenance))
    if type(basis) is not str or type(dtype) is not str or type(device) is not str:
        _refuse("DONOR_ASSUMPTIONS", "basis, dtype and device must be explicit strings")
    values = tuple(values)
    if not values or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v))
                         for v in values):
        _refuse("DONOR_VALUES", "finite floats required")
    return Donor(input_sha256, capture_digest, checkpoint_sha256, provenance, basis, dtype, device,
                 tuple(float(v) for v in values))


@dataclass(frozen=True)
class Declaration:
    schema: str
    action: str
    site: str
    module_attribute: str
    hook_kind: str
    round_index: object
    rows: tuple
    coordinates: tuple
    gain: object
    donor: object
    control_of: object
    control_action: object
    control_seed: object
    checkpoint_sha256: str
    input_sha256: str
    source_sha256: str
    hypothesis_id: str
    predicted_change: str
    claim_ceiling: str
    max_receipt_bytes: int
    actor: str
    authority: str
    basis: str

    @property
    def operation(self):
        return self.control_action if self.action == "MATCHED_CONTROL" else self.action


def declaration_digest(declaration):
    return digest(asdict(declaration))


def declare(*, action, site, checkpoint_sha256, input_sha256, source_sha256, rows, coordinates=(), round_index=None,
            gain=None, donor=None, control_of=None, control_action=None, control_seed=None, hypothesis_id="H0",
            predicted_change="UNSPECIFIED", allowed_sources=(LEARNER_SHA256,),
            max_receipt_bytes=DEFAULT_MAX_RECEIPT_BYTES):
    """Every assumption explicit; refused at declaration when it can be, at hit time otherwise."""
    if action not in ACTIONS:
        _refuse("ACTION_UNKNOWN", repr(action))
    if site not in SITE_SEMANTICS:
        _refuse("SITE_UNKNOWN", repr(site))
    if site not in HOOK_SITES:
        _refuse("SITE_NOT_HOOKABLE", "%s: %s" % (site, NOT_HOOKABLE[site]))
    module_attribute, hook_kind = HOOK_SITES[site]
    for name, value in (("checkpoint_sha256", checkpoint_sha256), ("input_sha256", input_sha256),
                        ("source_sha256", source_sha256)):
        _hex64(value, "DECLARATION_IDENTITY:" + name)
    if source_sha256 not in tuple(allowed_sources):
        _refuse("SOURCE_NOT_ADMITTED", source_sha256)
    if SITE_SEMANTICS[site]["per_round"]:
        if type(round_index) is not int or not 0 <= round_index < CORE_ROUNDS:
            _refuse("ROUND_INDEX", "%s needs 0..%d, got %r" % (site, CORE_ROUNDS - 1, round_index))
    elif round_index is not None:
        _refuse("ROUND_INDEX", "%s is not a per-round site" % site)
    rows = _index_tuple(rows, "ROWS")
    coordinates = _index_tuple(coordinates, "COORDINATES", allow_empty=(action == "OBSERVE_ONLY"))
    if action != "OBSERVE_ONLY" and not coordinates:
        _refuse("COORDINATES", "empty")
    if type(max_receipt_bytes) is not int or max_receipt_bytes <= 0:
        _refuse("RECEIPT_BYTES", repr(max_receipt_bytes))
    needed = 2 * len(rows) * max(len(coordinates), 1) * FLOAT_BYTES
    if needed > max_receipt_bytes:
        _refuse("RECEIPT_BYTES_EXCEEDED", "%d > %d" % (needed, max_receipt_bytes))
    claim_ceiling = "WITHIN_CHECKPOINT_DIAGNOSTIC"
    operation = control_action if action == "MATCHED_CONTROL" else action
    if action == "MATCHED_CONTROL":
        if control_action not in ACTIVE_ACTIONS:
            _refuse("CONTROL_ACTION", repr(control_action))
        _hex64(control_of, "CONTROL_OF")
        if type(control_seed) is not int:
            _refuse("CONTROL_SEED", repr(control_seed))
    elif control_of is not None or control_action is not None or control_seed is not None:
        _refuse("CONTROL_FIELDS", "only MATCHED_CONTROL carries control_of/control_action/control_seed")
    if operation == "SUPPRESS":
        if gain is None or isinstance(gain, bool) or not isinstance(gain, (int, float)) or not math.isfinite(float(gain)):
            _refuse("GAIN", repr(gain))
        gain = float(gain)
        if not 0.0 < gain <= 1.0:
            _refuse("GAIN_RANGE", "suppression gain must be in (0, 1], got %r" % gain)
        if donor is not None:
            _refuse("DONOR_UNEXPECTED", "SUPPRESS takes no donor")
    elif operation == "SAME_INPUT_PATCH":
        if gain is not None:
            _refuse("GAIN_UNEXPECTED", "SAME_INPUT_PATCH takes no gain")
        if not isinstance(donor, Donor):
            _refuse("DONOR_REQUIRED")
        if donor.checkpoint_sha256 != checkpoint_sha256:
            _refuse("DONOR_CHECKPOINT_MISMATCH", "cross-checkpoint donors need their own compatibility hypothesis")
        if donor.basis != SITE_SEMANTICS[site]["basis"]:
            _refuse("DONOR_BASIS_MISMATCH", "%s vs %s" % (donor.basis, SITE_SEMANTICS[site]["basis"]))
        if len(donor.values) != len(rows) * len(coordinates):
            _refuse("DONOR_VALUE_COUNT", "%d values for %d rows x %d coordinates"
                    % (len(donor.values), len(rows), len(coordinates)))
        if donor.provenance == "GOLD_INFORMED":
            claim_ceiling = "ORACLE_ASSISTED_DIAGNOSIS_NOT_DEPLOYABLE"
    else:
        if gain is not None and action != "NO_OP_CONTROL":
            _refuse("GAIN_UNEXPECTED", "%s takes no gain" % action)
        if action == "NO_OP_CONTROL" and gain not in (None, 0.0, 0):
            _refuse("GAIN_UNEXPECTED", "NO_OP_CONTROL gain is 0.0 by definition")
        gain = 0.0 if action == "NO_OP_CONTROL" else None
        if donor is not None:
            _refuse("DONOR_UNEXPECTED", "%s takes no donor" % action)
    if type(hypothesis_id) is not str or not hypothesis_id or type(predicted_change) is not str or not predicted_change:
        _refuse("HYPOTHESIS", "hypothesis_id and predicted_change are required strings")
    return Declaration(DECLARATION_SCHEMA, action, site, module_attribute, hook_kind, round_index, rows, coordinates,
                       gain, donor, control_of, control_action, control_seed, checkpoint_sha256, input_sha256,
                       source_sha256, hypothesis_id, predicted_change, claim_ceiling, max_receipt_bytes, ACTOR,
                       AUTHORITY, BASIS)


def matched_control(active, *, width, seed, control_donor=None):
    """Same site, rows, round, gain and coordinate COUNT; disjoint coordinates from a recorded seed."""
    if active.action not in ACTIVE_ACTIONS:
        _refuse("CONTROL_ACTION", "matched control needs an active declaration, got %s" % active.action)
    if type(width) is not int or width <= 0:
        _refuse("CONTROL_WIDTH", repr(width))
    if any(c >= width for c in active.coordinates):
        _refuse("COORDINATES", "active coordinates exceed width %d" % width)
    pool = [c for c in range(width) if c not in active.coordinates]
    if len(pool) < len(active.coordinates):
        _refuse("CONTROL_POOL", "not enough untargeted coordinates for a disjoint control")
    chosen = tuple(sorted(random.Random(seed).sample(pool, len(active.coordinates))))
    donor_for_control = None
    if active.action == "SAME_INPUT_PATCH":
        if control_donor is None:
            _refuse("DONOR_REQUIRED", "a patch control needs its own declared control donor")
        donor_for_control = control_donor
    return declare(action="MATCHED_CONTROL", site=active.site, checkpoint_sha256=active.checkpoint_sha256,
                   input_sha256=active.input_sha256, source_sha256=active.source_sha256, rows=active.rows,
                   coordinates=chosen, round_index=active.round_index, gain=active.gain, donor=donor_for_control,
                   control_of=declaration_digest(active), control_action=active.action, control_seed=seed,
                   hypothesis_id=active.hypothesis_id, predicted_change="MATCHED_CONTROL_NO_SPECIFIC_EFFECT",
                   allowed_sources=(active.source_sha256,), max_receipt_bytes=active.max_receipt_bytes)


def verify_matched(control, active):
    if control.action != "MATCHED_CONTROL" or control.control_of != declaration_digest(active):
        _refuse("CONTROL_NOT_MATCHED", "control_of does not name this active declaration")
    same = (control.site, control.rows, control.round_index, control.gain, control.control_action) == (
        active.site, active.rows, active.round_index, active.gain, active.action)
    if not same or len(control.coordinates) != len(active.coordinates):
        _refuse("CONTROL_NOT_MATCHED", "site/rows/round/gain/count differ")
    if set(control.coordinates) & set(active.coordinates):
        _refuse("CONTROL_NOT_MATCHED", "control coordinates overlap the target")
    return {"matched": True, "count": len(control.coordinates), "seed": control.control_seed}


# ---------------------------------------------------------------------------------------------------------
# Binding to the container (HH02)
# ---------------------------------------------------------------------------------------------------------

def _linear_widths(torch, module):
    linears = [m for m in module.modules() if isinstance(m, torch.nn.Linear)]
    if not linears:
        return None
    return {"in_features": int(linears[0].in_features), "out_features": int(linears[-1].out_features)}


def bind_sites(model, torch, sites=tuple(HOOK_SITES)):
    """Refuse a foreign object: each hookable site's attribute must exist and be a torch module."""
    if not isinstance(model, torch.nn.Module):
        _refuse("MODEL_TYPE", repr(type(model)))
    bound = {}
    for site in sites:
        if site not in HOOK_SITES:
            _refuse("SITE_NOT_HOOKABLE", site)
        attribute, kind = HOOK_SITES[site]
        module = getattr(model, attribute, None)
        if module is None:
            _refuse("SITE_MODULE_MISSING", "%s -> model.%s" % (site, attribute))
        if not isinstance(module, torch.nn.Module):
            _refuse("SITE_MODULE_TYPE", "%s -> model.%s is %r" % (site, attribute, type(module)))
        bound[site] = {"attribute": attribute, "hook": kind, "module": module, "type": type(module).__name__,
                       "widths": _linear_widths(torch, module)}
    return bound


def caller_binding(model, torch, *, checkpoint_sha256, source_sha256, restored_by):
    """Built by the GUARDED CALLER right after the guarded restore, never from a declaration's strings.

    The declaration's own checkpoint/source hashes do not authenticate the `nn.Module` handed to `apply`; this
    record ties that exact object's parameter bytes (`state_digest`) to the checkpoint and source the caller
    restored under its own admission, and names the restorer.
    """
    _hex64(checkpoint_sha256, "BINDING_CHECKPOINT")
    _hex64(source_sha256, "BINDING_SOURCE")
    if type(restored_by) is not str or not restored_by:
        _refuse("BINDING_RESTORER", "name the guarded loader, e.g. PointerCourseLearner.restore_checkpoint")
    return {"schema": "helm.harness.caller-binding/0.1", "model_state_digest": state_digest(model, torch),
            "checkpoint_sha256": checkpoint_sha256, "source_sha256": source_sha256, "restored_by": restored_by}


def verify_caller_binding(model, torch, declaration, binding):
    if type(binding) is not dict or binding.get("schema") != "helm.harness.caller-binding/0.1":
        _refuse("MODEL_BINDING_INVALID", "caller_binding record required")
    if (binding.get("checkpoint_sha256"), binding.get("source_sha256")) != (declaration.checkpoint_sha256, declaration.source_sha256):
        _refuse("MODEL_BINDING_MISMATCH", "declaration names a different checkpoint or source than the caller restored")
    if binding.get("model_state_digest") != state_digest(model, torch):
        _refuse("MODEL_BINDING_MISMATCH", "the module's parameter bytes are not the ones the caller bound")
    return "CALLER_VERIFIED"


def state_digest(model, torch):
    hasher = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        hasher.update(name.encode())
        hasher.update(str(tuple(tensor.shape)).encode())
        hasher.update(str(tensor.dtype).encode())
        flat = tensor.detach().to("cpu").contiguous().reshape(-1)
        hasher.update(flat.view(torch.uint8).numpy().tobytes() if flat.numel() else b"")
    return hasher.hexdigest()


# ---------------------------------------------------------------------------------------------------------
# Receipts (HH10, HH11)
# ---------------------------------------------------------------------------------------------------------

@dataclass
class Receipt:
    schema: str
    declaration_digest: str
    action: str
    operation: str
    site: str
    module_attribute: str
    hook_kind: str
    expected_forward_calls: int
    expected_hits: int
    expected_targeted_hits: int
    hits: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    stored_floats: int = 0
    module_type: object = None
    module_widths: object = None
    hooks_removed: object = None
    parameters_unchanged: object = None
    state_digest_before: object = None
    state_digest_after: object = None
    status: object = None
    applied: object = None
    claim_ceiling: object = None
    model_binding: str = "UNVERIFIED_SELF_REPORTED"
    restored_by: object = None
    actor: str = ACTOR
    authority: str = AUTHORITY
    basis: str = BASIS

    def targeted_hits(self):
        return [hit for hit in self.hits if hit["targeted"]]


def receipt_to_json(receipt):
    body = asdict(receipt)
    body["receipt_digest"] = digest(body)
    return canonical(body) + "\n"


def verify_receipt(text, declaration=None, *, retained_receipt_sha256=None):
    """Self-carried digest = transport integrity only; an externally retained sha256 of the text adds more."""
    if retained_receipt_sha256 is not None and hashlib.sha256(text.encode()).hexdigest() != retained_receipt_sha256:
        _refuse("RECEIPT_ANCHOR_MISMATCH", "externally retained digest differs")
    body = json.loads(text)
    expected = body.pop("receipt_digest", None)
    if expected != digest(body):
        _refuse("RECEIPT_TAMPERED")
    if declaration is not None and body["declaration_digest"] != declaration_digest(declaration):
        _refuse("RECEIPT_DECLARATION_MISMATCH")
    if body["status"] not in STATUSES:
        _refuse("RECEIPT_STATUS", repr(body["status"]))
    return body


def finalize(receipt):
    """One status from the hits; a declared action with no targeted hit is NOT_APPLIED, never success."""
    targeted = receipt.targeted_hits()
    complete = (len(receipt.hits) == receipt.expected_hits and len(targeted) == receipt.expected_targeted_hits
                and not receipt.errors and receipt.hooks_removed is True and receipt.parameters_unchanged is True)
    if receipt.operation == "OBSERVE_ONLY":
        receipt.status = "OBSERVED" if complete else "OBSERVED_INCOMPLETE"
        receipt.applied = None
    elif receipt.operation == "NO_OP_CONTROL":
        equal = all(hit["untargeted_unchanged"] and hit["changed_count"] == 0 for hit in targeted)
        receipt.status = "NO_OP_VERIFIED" if complete and targeted and equal else "NO_OP_FAILED"
        receipt.applied = receipt.status == "NO_OP_VERIFIED"
    else:
        if not complete or not targeted or not all(hit["untargeted_unchanged"] for hit in targeted):
            receipt.status, receipt.applied = "NOT_APPLIED", False
        elif all(hit["changed_count"] == 0 for hit in targeted):
            receipt.status, receipt.applied = "APPLIED_NO_CHANGE", True
        else:
            receipt.status, receipt.applied = "APPLIED", True
    return receipt


def _as_rows(torch, tensor):
    if not torch.is_tensor(tensor):
        _refuse("HIT_NOT_TENSOR", repr(type(tensor)))
    if tensor.dim() == 1:
        return tensor.reshape(1, -1)
    if tensor.dim() == 2:
        return tensor
    _refuse("HIT_SHAPE", "expected 1-D or 2-D site tensor, got %r" % (tuple(tensor.shape),))


def _visit(torch, declaration, receipt, tensor):
    """One hook call. Returns None (passive or untargeted call) or the modified tensor (sham/active)."""
    call_index = len(receipt.hits)
    per_round = SITE_SEMANTICS[declaration.site]["per_round"]
    round_index = call_index % CORE_ROUNDS if per_round else None
    view = _as_rows(torch, tensor)
    hit = {"call_index": call_index, "round_index": round_index, "shape": list(tensor.shape),
           "dtype": str(tensor.dtype).replace("torch.", ""), "device": str(tensor.device),
           "targeted": (round_index == declaration.round_index) if per_round else True,
           "changed_count": 0, "untargeted_unchanged": True, "max_abs_delta": 0.0, "delta_norm": 0.0,
           "target_norm_before": None, "before": None, "after": None}
    receipt.hits.append(hit)
    if not hit["targeted"]:
        return None
    rows, coords = declaration.rows, declaration.coordinates
    if max(rows) >= view.shape[0] or (coords and max(coords) >= view.shape[1]):
        _refuse("TARGET_OUT_OF_RANGE", "rows %r coords %r for shape %r" % (rows, coords, tuple(view.shape)))
    row_index = torch.tensor(rows, dtype=torch.int64, device=tensor.device).reshape(-1, 1)
    if declaration.operation == "OBSERVE_ONLY":
        if coords:
            col_index = torch.tensor(coords, dtype=torch.int64, device=tensor.device).reshape(1, -1)
            block = view[row_index, col_index]
        else:
            block = view[row_index.reshape(-1)]
        values = block.detach().to("cpu", torch.float32).reshape(-1).tolist()
        _store(receipt, declaration, hit, "before", values)
        return None
    col_index = torch.tensor(coords, dtype=torch.int64, device=tensor.device).reshape(1, -1)
    before = view[row_index, col_index].detach().clone()
    hit["target_norm_before"] = float(before.to(torch.float32).norm().item())
    modified = tensor.clone()
    modified_view = modified.reshape(1, -1) if tensor.dim() == 1 else modified
    if declaration.operation == "NO_OP_CONTROL":
        modified_view[row_index, col_index] = modified_view[row_index, col_index] * 1.0
    elif declaration.operation == "SUPPRESS":
        modified_view[row_index, col_index] = modified_view[row_index, col_index] * suppression_factor(declaration.gain)
    elif declaration.operation == "SAME_INPUT_PATCH":
        donor_values = declaration.donor
        if donor_values.dtype != hit["dtype"]:
            _refuse("DONOR_DTYPE_MISMATCH", "%s vs %s" % (donor_values.dtype, hit["dtype"]))
        if donor_values.device != hit["device"]:
            _refuse("DONOR_DEVICE_MISMATCH", "%s vs %s" % (donor_values.device, hit["device"]))
        patch = torch.tensor(donor_values.values, dtype=tensor.dtype, device=tensor.device).reshape(len(rows), len(coords))
        modified_view[row_index, col_index] = patch
    else:  # pragma: no cover -- declare() closes the action set
        _refuse("ACTION_UNKNOWN", declaration.operation)
    after = modified_view[row_index, col_index].detach()
    mask = torch.zeros(view.shape, dtype=torch.bool, device=tensor.device)
    mask[row_index, col_index] = True
    hit["untargeted_unchanged"] = bool(torch.equal(modified_view[~mask], view.detach()[~mask]))
    delta = (after.to(torch.float32) - before.to(torch.float32))
    hit["changed_count"] = int((after != before).sum().item())
    hit["max_abs_delta"] = float(delta.abs().max().item()) if delta.numel() else 0.0
    hit["delta_norm"] = float(delta.norm().item())
    _store(receipt, declaration, hit, "before", before.to("cpu", torch.float32).reshape(-1).tolist())
    _store(receipt, declaration, hit, "after", after.to("cpu", torch.float32).reshape(-1).tolist())
    return modified


def _store(receipt, declaration, hit, key, values):
    if (receipt.stored_floats + len(values)) * FLOAT_BYTES > declaration.max_receipt_bytes:
        _refuse("RECEIPT_BYTES_EXCEEDED", "%d floats stored" % receipt.stored_floats)
    receipt.stored_floats += len(values)
    hit[key] = [float(v) for v in values]


@contextmanager
def apply(model, declaration, *, torch, expected_forward_calls, expected_hits=None, binding=None):
    """Register one hook, yield the receipt, always remove the hook and check state, then finalize.

    `binding` is the guarded caller's `caller_binding` record. Without it the receipt is marked
    `UNVERIFIED_SELF_REPORTED`: the hooks still run and the hits are still recorded, but `require_applied`
    (the scoring gate) and `evidence_record` refuse it. The declaration's checkpoint/source strings never
    authenticate the module by themselves and never confer authority or success.

    `expected_hits` overrides the default `forwards x (CORE_ROUNDS or 1)`; take it from
    `diagnostic_configuration.expected_hits_for(site, kind)` so a Parts packet expects 0 `head.reach` hits.
    Interplay with Codex's passive emitter (`observation_sites.instrumented_graph`): its `graph.round_input`
    emit fires BEFORE `model.core_block(hidden_input)`, so a passive capture at that site records the
    UNMODIFIED input; this receipt is the record of the modification, and the `graph.round_update` capture
    shows its effect. The emitter's `capture_helm` binds `learner._graph` for one packet forward and disables
    `stage_batch`; these hooks touch neither.

    Passive operations (OBSERVE_ONLY) catch their own errors, record them, and return None so the learner
    finishes with an incomplete receipt. Sham and active operations raise through the forward: a failed
    edit aborts the branch and is reported NOT_APPLIED / NO_OP_FAILED, never as success.
    """
    if not isinstance(declaration, Declaration):
        _refuse("DECLARATION_TYPE", repr(type(declaration)))
    if type(expected_forward_calls) is not int or expected_forward_calls < 0:
        _refuse("EXPECTED_FORWARD_CALLS", repr(expected_forward_calls))
    bound = bind_sites(model, torch, sites=(declaration.site,))[declaration.site]
    module = bound["module"]
    per_round = SITE_SEMANTICS[declaration.site]["per_round"]
    if expected_hits is None:
        expected_hits = expected_forward_calls * (CORE_ROUNDS if per_round else 1)
    elif type(expected_hits) is not int or expected_hits < 0:
        _refuse("EXPECTED_HITS", repr(expected_hits))
    expected_targeted = expected_forward_calls if expected_hits else 0
    receipt = Receipt(RECEIPT_SCHEMA, declaration_digest(declaration), declaration.action, declaration.operation,
                      declaration.site, declaration.module_attribute, declaration.hook_kind, expected_forward_calls,
                      expected_hits, expected_targeted, module_type=bound["type"], module_widths=bound["widths"],
                      claim_ceiling=declaration.claim_ceiling)
    if binding is not None:
        receipt.model_binding = verify_caller_binding(model, torch, declaration, binding)
        receipt.restored_by = binding["restored_by"]
    receipt.state_digest_before = state_digest(model, torch)
    pre_count, post_count = len(module._forward_pre_hooks), len(module._forward_hooks)
    passive = declaration.operation == "OBSERVE_ONLY"

    def run(tensor):
        try:
            return _visit(torch, declaration, receipt, tensor)
        except Exception as error:
            receipt.errors.append("%s: %s" % (type(error).__name__, error))
            if passive:
                return None
            raise

    if declaration.hook_kind == "pre":
        def pre_hook(_module, args):
            if not args:
                receipt.errors.append("HIT_NO_ARGS")
                return None
            result = run(args[0])
            return None if result is None else (result,) + tuple(args[1:])
        handle = module.register_forward_pre_hook(pre_hook)
    else:
        def post_hook(_module, _args, output):
            return run(output)
        handle = module.register_forward_hook(post_hook)
    try:
        yield receipt
    finally:
        try:
            handle.remove()
        finally:
            receipt.hooks_removed = (len(module._forward_pre_hooks), len(module._forward_hooks)) == (pre_count, post_count)
            receipt.state_digest_after = state_digest(model, torch)
            receipt.parameters_unchanged = receipt.state_digest_after == receipt.state_digest_before
            finalize(receipt)


def require_applied(receipt):
    """Gate before task scoring: only APPLIED or APPLIED_NO_CHANGE on a caller-verified module may be scored."""
    if receipt.status not in ("APPLIED", "APPLIED_NO_CHANGE"):
        _refuse("INTERVENTION_NOT_APPLIED", "status %r, errors %r" % (receipt.status, receipt.errors))
    if receipt.model_binding != "CALLER_VERIFIED":
        _refuse("MODEL_BINDING_UNVERIFIED", "the module was not bound by the guarded caller; strings alone do not authenticate it")
    return receipt


# ---------------------------------------------------------------------------------------------------------
# One controlled witness protocol (planning record, source-bound; not a job admission)
# ---------------------------------------------------------------------------------------------------------

WITNESS_SCHEMA = "helm.harness.witness-protocol/0.1"


def witness_protocol():
    """The first engineering witness: injected-fault plumbing check plus one frozen hypothesis, with controls.

    Everything here is bound to `c45f775f` sites and container attributes; the checkpoint, inputs and job are
    Codex's admission. Conditions run on ONE checkpoint, ONE packet forward each, zero optimizer updates. The
    injected condition is labeled INJECTED and proves only that the apparatus detects a change it caused.
    """
    return {
        "schema": WITNESS_SCHEMA, "task": "CAS-HH-RDE-01", "label": "FIRST_ENGINEERING_WITNESS",
        "source": {"scientific_source": "c45f775f225dd06cc20cdf313f0a0398486e0d61", "learner_sha256": LEARNER_SHA256,
                   "site_module": HOOK_SITES["graph.round_input"], "site_anchor": SITE_SEMANTICS["graph.round_input"]["anchor"]},
        "checkpoint": {"identity": "TO_BE_SUPPLIED_BY_CODEX_ADMISSION", "kind": "preserved development-selected checkpoint",
                       "count": 1, "optimizer_updates": 0},
        "inputs": {"kind": "SYNTHETIC_FIXTURE_PARTS_REACH", "discovery": 2, "confirmation": 2, "split_by": "graph structure family",
                   "model_visible_target": False, "max_distinct_inputs": 4},
        "expected_calls_per_forward": {"core_block": CORE_ROUNDS, "node_head": 1, "pointer_key": 1,
                                       "reach_option_head": "1 if the packet declares a reach slot else 0"},
        "hypotheses": [
            {"id": "H0_INJECTED", "kind": "INJECTED_FAULT_PLUMBING_CHECK",
             "statement": "suppressing every coordinate of every node row of graph.round_input at round 0 with gain 1.0 changes answer.scores; the apparatus must report APPLIED with changed_count == rows*width",
             "not_evidence_of": "any natural HELM fault"},
            {"id": "H1", "kind": "NATURAL_WITHIN_CHECKPOINT",
             "statement": "suppressing the frozen top-4 |activity| coordinates of the focus-argument node row at graph.round_input round 3 (gain 1.0) lowers the head.reach margin and changes the checked reach answer on confirmation inputs more than the matched control does",
             "configuration_source": "detect_top_k on DISCOVERY inputs, frozen before confirmation",
             "predicted_change": "reach margin falls; matched control within noise"},
        ],
        "conditions": [
            {"id": "C0", "action": "BASELINE_UNINSTRUMENTED", "role": "original prediction and scores"},
            {"id": "C1", "action": "OBSERVE_ONLY", "site": "graph.round_input", "coordinates": "all", "role": "passive neutrality: exact equality with C0 on prediction, scores, model/optimizer state, RNG; overhead charged"},
            {"id": "C2", "action": "NO_OP_CONTROL", "site": "graph.round_input", "round_index": 3, "role": "sham edit equals C0 bitwise"},
            {"id": "C3", "action": "SUPPRESS", "site": "graph.round_input", "round_index": 3, "gain": 1.0, "coordinates": "frozen top-4", "role": "H1 intervention"},
            {"id": "C4", "action": "MATCHED_CONTROL", "control_of": "C3", "control_seed": 2026, "role": "same count, rows, round, gain; disjoint coordinates"},
            {"id": "C5", "action": "SUPPRESS", "site": "graph.round_input", "round_index": 0, "gain": 1.0, "coordinates": "all", "label": "INJECTED", "role": "H0 plumbing check"},
        ],
        "outcome": {"metric": "answer.scores for the reach and node slots plus the checked answer through the unchanged evaluator",
                    "readout": "head.reach margin via readout_margin (readout level only)",
                    "gate": "require_applied on C3/C4/C5 receipts before any scoring; C1 must be OBSERVED; C2 must be NO_OP_VERIFIED"},
        "stopping": ["C1 not exactly neutral -> stop, report OBSERVED_INCOMPLETE or the diff; no intervention scored",
                     "C2 not NO_OP_VERIFIED -> stop", "C5 not APPLIED with full changed_count -> apparatus fault, stop",
                     "H1 refuted or inconclusive is a completed result; no second hypothesis chosen after seeing confirmation answers"],
        "resources": {"packet_forwards_max": 4 * 6, "packet_forwards_envelope": 768, "conditions": 6, "conditions_max": 8,
                      "hypotheses": 2, "hypotheses_max": 2, "candidate_configurations": 1, "candidate_configurations_max": 4,
                      "raw_capture_bytes_max": 536870912, "model_execution_jobs": 1, "job_wall_seconds_max": 3600,
                      "helm_optimizer_updates": 0, "launcher": "EXISTING_CODEX_RUNNER_ONLY", "claude_launches": 0},
        "claim_boundary": {"forward_path": "hooks on container modules; learner file unchanged",
                           "authority": AUTHORITY, "basis": BASIS, "actor": ACTOR,
                           "level_reachable": "TASK_CAUSAL_CONTRIBUTION_SUPPORTED at most; no repair, no promotion, no native attribution"},
    }


# ---------------------------------------------------------------------------------------------------------
# Evidence record and read-only RPA projection (HH16, HH17; research traces stay out of harvest ingestion)
# ---------------------------------------------------------------------------------------------------------

EVIDENCE_SCHEMA = "helm.harness.diagnostic-evidence/0.1"
RPA_PROJECTION_SCHEMA = "helm.harness.rpa-projection/0.1"
HARVEST_INGESTION = "DISABLED_NOT_ADMITTED"
OUTCOME_METRICS = ("PARTS_REACH_SCORES", "CHECKED_ANSWER", "NONE")


def evidence_record(*, declaration, receipt, configuration_id, split, baseline_prediction_id, changed_prediction_id,
                    checked_outcome, selected_by=ACTOR):
    """One branch = input + parent checkpoint + action + outcome, digest-sealed, never promotable from here."""
    if not isinstance(declaration, Declaration) or not isinstance(receipt, Receipt):
        _refuse("EVIDENCE_TYPES")
    if receipt.status is None or receipt.status not in STATUSES:
        _refuse("EVIDENCE_RECEIPT_UNFINALIZED")
    if receipt.declaration_digest != declaration_digest(declaration):
        _refuse("RECEIPT_DECLARATION_MISMATCH")
    if receipt.model_binding != "CALLER_VERIFIED":
        _refuse("MODEL_BINDING_UNVERIFIED", "evidence needs a caller-bound module")
    if split not in ("DISCOVERY", "CONFIRMATION", "SYNTHETIC_FIXTURE"):
        _refuse("EVIDENCE_SPLIT", repr(split))
    if type(checked_outcome) is not dict or checked_outcome.get("metric") not in OUTCOME_METRICS:
        _refuse("EVIDENCE_OUTCOME", "metric must be one of %r" % (OUTCOME_METRICS,))
    if checked_outcome["metric"] != "NONE" and checked_outcome.get("evaluator") != "UNCHANGED_INDEPENDENT_EVALUATOR":
        _refuse("EVIDENCE_OUTCOME", "task outcomes come from the unchanged independent evaluator only")
    if receipt.status in ("APPLIED", "APPLIED_NO_CHANGE") and changed_prediction_id is None:
        _refuse("EVIDENCE_PREDICTION", "an applied intervention needs its changed raw prediction id")
    for name, value in (("baseline_prediction_id", baseline_prediction_id), ("changed_prediction_id", changed_prediction_id)):
        if value is not None and (type(value) is not str or not value):
            _refuse("EVIDENCE_PREDICTION", name)
    if type(configuration_id) is not str or not configuration_id.startswith("helm-configuration-"):
        _refuse("EVIDENCE_CONFIGURATION", repr(configuration_id))
    body = {"schema": EVIDENCE_SCHEMA, "checkpoint_sha256": declaration.checkpoint_sha256,
            "input_sha256": declaration.input_sha256, "source_sha256": declaration.source_sha256,
            "configuration_id": configuration_id, "declaration_digest": receipt.declaration_digest,
            "receipt_digest": digest(asdict(receipt)), "action": declaration.action, "operation": declaration.operation,
            "site": declaration.site, "round_index": declaration.round_index, "receipt_status": receipt.status,
            "applied": receipt.applied, "split": split, "baseline_prediction_id": baseline_prediction_id,
            "changed_prediction_id": changed_prediction_id, "checked_outcome": dict(checked_outcome),
            "selected_by": selected_by, "native_decision": False, "claim_ceiling": declaration.claim_ceiling,
            "model_binding": receipt.model_binding, "restored_by": receipt.restored_by,
            "harvest_ingestion": HARVEST_INGESTION, "training_visibility": "NONE",
            "authority": AUTHORITY, "basis": BASIS, "promotion": "NOT_POSSIBLE_FROM_THIS_RECORD"}
    body["evidence_digest"] = digest(body)
    return body


def verify_evidence(evidence, *, retained_evidence_sha256=None):
    """The carried digest proves transport integrity only (an editor can recompute it, DeepSeek F4);
    the externally retained digest, when given, must match. The result names which level was checked."""
    body = dict(evidence)
    expected = body.pop("evidence_digest", None)
    if expected != digest(body) or body.get("schema") != EVIDENCE_SCHEMA:
        _refuse("EVIDENCE_TAMPERED")
    if body.get("harvest_ingestion") != HARVEST_INGESTION or body.get("promotion") != "NOT_POSSIBLE_FROM_THIS_RECORD":
        _refuse("EVIDENCE_AUTHORITY")
    if retained_evidence_sha256 is not None and retained_evidence_sha256 != expected:
        _refuse("EVIDENCE_ANCHOR_MISMATCH", "externally retained digest differs")
    body["anchor"] = "EXTERNAL_ANCHOR_VERIFIED" if retained_evidence_sha256 is not None else "SELF_CONSISTENT_ONLY"
    return body


def rpa_projection(evidence, *, retained_evidence_sha256):
    """What the atlas may show: a branch bound to input, parent checkpoint, action and outcome. View only.
    The view is built only from evidence anchored by a digest held OUTSIDE the artifact."""
    if retained_evidence_sha256 is None:
        _refuse("EXTERNAL_ANCHOR_REQUIRED", "the atlas shows only externally anchored evidence")
    body = verify_evidence(evidence, retained_evidence_sha256=retained_evidence_sha256)
    branch = {"schema": RPA_PROJECTION_SCHEMA,
              "branch_id": "helm-branch-" + digest([body["checkpoint_sha256"], body["input_sha256"],
                                                    body["declaration_digest"], body["receipt_digest"]]),
              "parent_checkpoint_sha256": body["checkpoint_sha256"], "input_sha256": body["input_sha256"],
              "action": body["action"], "operation": body["operation"], "site": body["site"],
              "round_index": body["round_index"], "outcome": {"receipt_status": body["receipt_status"],
                                                             "applied": body["applied"],
                                                             "checked_outcome": body["checked_outcome"]},
              "lineage": {"configuration_id": body["configuration_id"], "declaration_digest": body["declaration_digest"],
                          "receipt_digest": body["receipt_digest"], "evidence_digest": evidence["evidence_digest"],
                          "baseline_prediction_id": body["baseline_prediction_id"],
                          "changed_prediction_id": body["changed_prediction_id"]},
              "selected_by": body["selected_by"], "native_decision": body["native_decision"],
              "claim_ceiling": body["claim_ceiling"], "anchor": body["anchor"],
              "view_authority": "READ_ONLY_NO_EXECUTION_NO_MUTATION",
              "executable": False, "mutation_authority": None}
    return branch
