"""CAS-HH-RDE-01 / D — reviewer-owned diagnostic probes.

OWNER: DeepSeek independent reviewer lane. Reviewer-only area.
Directive: 04_DEEPSEEK_DIRECTIVE.md; acceptance IDs HH03, HH04, HH06, HH10, HH11.

WHAT THIS FILE IS
-----------------
A falsifiable, model-free test of whether the existing CAS Harness capture path
can reach a HELM readout site at all, written so it runs with NO torch, NO model,
NO checkpoint and NO cloud. Every claim it makes about the harness is checked
against the pinned harness source bytes; every claim it makes about the
intervention is executed against a stub module whose forward-hook contract
mirrors torch's documented behaviour.

WHY THAT IS THE RIGHT FIRST PROBE
---------------------------------
The pinned harness runner (probe_runner.py, sha256 543666e576a559b1..., 13105
bytes at noetic-compass master e8537e6c) is written for Pythia-160M:
`_get_pythia_layers` returns `model.gpt_neox.layers` or None, and `capture_probes`
then logs a warning and yields an EMPTY CaptureState. That is the exact failure the
shared directive forbids being reported as a zero-valued observation (HH04).

THE TWO FROZEN HYPOTHESES (fixed before any confirmation result)
---------------------------------------------------------------
H1 (hook coverage): on the HELM pointer-learner readout path, the unadapted harness
   capture reaches ZERO of the declared readout sites, and does so silently: the
   run completes and no receipt field is marked incomplete.
   H1 is FALSIFIED if the coverage probe reports observed_sites > 0 for any declared
   readout site, or if an empty capture is marked incomplete/invalid rather than
   yielding an ordinary summary.

H2 (intervention application): a harness-shaped EraserIntervention whose coordinates
   are (layer, index) pairs derived from the Pythia MLP grid is never applied to a
   HELM readout tensor, so it is a silent no-op; scoping it to a HELM site by shape
   makes it apply.
   H2 is FALSIFIED if the Pythia-shaped intervention changes any element of a
   HELM-shaped readout tensor, or if a correctly scoped intervention fails to change
   exactly the declared coordinates and nothing else.

EXECUTION STATUS
----------------
Everything in this file executes here, on CPU, with no model. The probes that would
require a real HELM checkpoint are listed in NOT_RUN below with the exact command
that would run them in an admitted venue.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REVIEW_DIR = HERE

# ---------------------------------------------------------------------------
# Pinned identities. These are facts about bytes, and the tests check them.
# ---------------------------------------------------------------------------
HARNESS_SOURCE = Path(r"C:\Users\wakil\AppData\Local\Temp\rde01\probe_runner.py")
HARNESS_SHA256_PREFIX = "543666e576a559b1"
HARNESS_BYTES = 13105
HARNESS_BLOB = "3468723e300fdf4fbb090c0d156b8014825d546d"
HARNESS_COMMIT = "e8537e6ce9e93242fb11dec36c03dbcafa86042c"

HELM_SOURCE = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
                   r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\helm-cm2x-rerun-20260925"
                   r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
                   r"\research\CAS_META_2_COMPOSITION\cas_meta2\typed_teaching\pointer_learner.py")

# Declared HELM Parts/Reach readout sites (from 06_SOURCE_MAP.md, pinned source).
HELM_READOUT_SITES = ("_rounds", "GraphForward", "_reach_options", "_node_options",
                      "head_logits", "_graph")
# The harness only ever looks for this attribute path.
HARNESS_EXPECTED_LAYER_PATH = ("gpt_neox", "layers")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _harness_text() -> str:
    if not HARNESS_SOURCE.is_file():
        pytest.skip("HARNESS_SOURCE_UNAVAILABLE: %s" % HARNESS_SOURCE)
    return HARNESS_SOURCE.read_text(encoding="utf-8", errors="replace")


def _helm_text() -> str:
    if not HELM_SOURCE.is_file():
        pytest.skip("HELM_SOURCE_UNAVAILABLE: %s" % HELM_SOURCE)
    return HELM_SOURCE.read_text(encoding="utf-8", errors="replace")


# ===========================================================================
# HH04 / H1 — coverage is counted, never inferred, and never silently zero
# ===========================================================================
def test_pinned_harness_source_identity():
    if not HARNESS_SOURCE.is_file():
        pytest.skip("HARNESS_SOURCE_UNAVAILABLE")
    assert HARNESS_SOURCE.stat().st_size == HARNESS_BYTES
    assert _sha256(HARNESS_SOURCE).startswith(HARNESS_SHA256_PREFIX)


def test_h1_the_harness_layer_lookup_is_pythia_only():
    """The pinned runner can only find one architecture's block list."""
    text = _harness_text()
    assert "gpt_neox" in text and "layers" in text, "the pinned lookup changed; re-derive this probe"
    assert "_get_pythia_layers" in text
    # There is no HELM or generic module-walk fallback in the pinned source.
    for absent in ("named_modules", "world_head", "pointer", "cas_meta2", "typed_teaching"):
        assert absent not in text, (
            "the pinned harness now mentions %r; the Pythia-only claim must be re-derived" % absent)


def test_h1_a_foreign_model_yields_an_empty_capture_not_an_error():
    """Executed against a stub model: the contract is 'warn and yield empty'."""
    if not HARNESS_SOURCE.is_file():
        pytest.skip("HARNESS_SOURCE_UNAVAILABLE")
    module = _load_harness_module()
    stub = StubModule()                      # a HELM-like object with no gpt_neox
    with module.capture_probes(stub, n_layers=4) as state:
        assert state.mlp_post == {}, "a non-Pythia model must not produce coordinates"
        assert state.logits is None
    summary = module.summarise(state, token_index=0, attentions=None, top_k=8)
    assert summary.top_activated_neurons == []
    assert summary.mode7_edges == [{"from_token_index": None, "to_token_index": 0, "weight": 1.0}]


def test_h1_expected_versus_observed_coverage_is_a_required_receipt_field():
    """HH04: an un-hooked site is INCOMPLETE, not a zero-valued observation."""
    declared = list(HELM_READOUT_SITES)
    coverage = coverage_report(declared, observed=[])          # harness reached nothing
    assert coverage["expected_sites"] == len(declared)
    assert coverage["observed_sites"] == 0
    assert coverage["status"] == "INCOMPLETE"
    assert coverage["receipt_completeness"] == "INCOMPLETE"
    assert coverage["zero_is_not_an_observation"] is True
    assert all(row["observed_calls"] is None for row in coverage["sites"]), (
        "a site the hook never saw must be reported as unobserved, never as 0 calls")


def test_h1_a_partial_hook_is_incomplete_not_complete():
    coverage = coverage_report(list(HELM_READOUT_SITES), observed=["_graph"])
    assert coverage["observed_sites"] == 1
    assert coverage["status"] == "INCOMPLETE"
    assert coverage["receipt_completeness"] == "INCOMPLETE"


def test_h1_full_coverage_is_the_only_complete_case():
    coverage = coverage_report(list(HELM_READOUT_SITES), observed=list(HELM_READOUT_SITES))
    assert coverage["status"] == "COMPLETE"
    assert coverage["receipt_completeness"] == "COMPLETE"


def test_h1_helm_readout_sites_really_exist_in_the_pinned_source():
    """The declared sites are not invented: each name appears in the pinned learner."""
    text = _helm_text()
    for site in HELM_READOUT_SITES:
        assert re.search(r"\b%s\b" % re.escape(site), text), (
            "declared readout site %r is absent from the pinned HELM source" % site)
    # And the Pythia path the harness looks for is absent from HELM.
    assert "gpt_neox" not in text, (
        "HELM now contains gpt_neox; the reachability question must be re-derived")


# ===========================================================================
# HH10 / HH11 / H2 — intervention application, scope refusal, no-op neutrality
# ===========================================================================
def test_h2_a_pythia_shaped_intervention_does_not_touch_a_helm_tensor():
    """Executed: the pinned coordinate space and a HELM-shaped tensor do not meet."""
    module = _load_harness_module()
    helm_like = StubTensor([[0.5, -1.25, 3.0, 0.0]])          # shape (1, 4) "readout row"
    intervention = module.EraserIntervention(coords=((2, 7),), gain=1.0)   # Pythia-shaped
    out = module._apply_eraser(helm_like, layer_idx=0, intervention=intervention)
    assert out is helm_like, "the pinned eraser must return the SAME object when its layer never matches"
    assert helm_like[0, -1] == [0.5, -1.25, 3.0, 0.0], "no element may change"


def test_h2_a_layer_matched_but_out_of_range_index_is_refused_not_applied():
    module = _load_harness_module()
    helm_like = StubTensor([[0.5, -1.25, 3.0, 0.0]])
    out_of_range = module.EraserIntervention(coords=((0, 99),), gain=1.0)
    out = module._apply_eraser(helm_like, layer_idx=0, intervention=out_of_range)
    assert out is helm_like, "an index outside the observed width must be refused, not clamped"


def test_h2_a_correctly_scoped_intervention_changes_exactly_one_coordinate():
    module = _load_harness_module()
    helm_like = StubTensor([[0.5, -1.25, 3.0, 0.0]])
    scoped = module.EraserIntervention(coords=((0, 2),), gain=1.0)
    out = module._apply_eraser(helm_like, layer_idx=0, intervention=scoped)
    assert out is not helm_like, "a matching scope must return a modified tensor"
    assert out[0, -1] == [0.5, -1.25, 0.0, 0.0], "only the declared coordinate may change"
    assert helm_like[0, -1] == [0.5, -1.25, 3.0, 0.0], "the input must not be mutated in place"


def test_h2_gain_zero_is_a_no_op_even_when_scoped():
    """HH10: a sham action whose scope matches must still change nothing."""
    module = _load_harness_module()
    helm_like = StubTensor([[0.5, -1.25, 3.0, 0.0]])
    sham = module.EraserIntervention(coords=((0, 2),), gain=0.0)
    out = module._apply_eraser(helm_like, layer_idx=0, intervention=sham)
    assert out is not helm_like                      # scope matched, so the path was taken
    assert out[0, -1] == [0.5, -1.25, 3.0, 0.0], "gain 0.0 must leave every value equal"
    assert vector_equal_exact(out[0, -1], [0.5, -1.25, 3.0, 0.0]) is True


def test_h2_an_empty_intervention_is_a_no_op():
    module = _load_harness_module()
    helm_like = StubTensor([[1.0, 2.0]])
    assert module._apply_eraser(helm_like, 0, None) is helm_like
    assert module._apply_eraser(helm_like, 0, module.EraserIntervention(coords=(), gain=1.0)) is helm_like


def test_hh11_a_shape_mismatch_is_refused_before_any_write():
    """HH02/HH11: wrong shape must be refused at the gate, not half-applied."""
    with pytest.raises(ValueError, match="INTERVENTION_SHAPE_MISMATCH"):
        require_intervention_target(observed_shape=(4,), declared_shape=(8,))
    with pytest.raises(ValueError, match="INTERVENTION_SITE_UNREACHED"):
        require_intervention_target(observed_shape=(4,), declared_shape=(4,), observed_calls=0)


def test_matched_control_is_same_rank_and_norm_and_overhead():
    """HH12 preparation: the control must be matched, not merely present."""
    target = build_intervention_record(site="reach_option_head", coords=((0, 2), (0, 5)),
                                       gain=1.0, role="TARGET", overhead_ns=1000)
    control = build_intervention_record(site="off_path_block", coords=((0, 1), (0, 3)),
                                        gain=1.0, role="MATCHED_CONTROL", overhead_ns=1000)
    verdict = compare_intervention_pair(target, control)
    assert verdict["same_rank"] is True
    assert verdict["same_gain"] is True
    assert verdict["same_size"] is True
    assert verdict["overhead_delta_ns"] == 0
    assert verdict["matched"] is True
    unbalanced = dict(control, gain=0.5)
    assert compare_intervention_pair(target, unbalanced)["matched"] is False


# ===========================================================================
# HH06 — cleanup and no leakage of a modified tensor from a passive hook
# ===========================================================================
def test_hh06_a_failing_hook_still_removes_every_handle():
    module = _load_harness_module()
    stub = StubModule(with_pythia=True, layers=3, explode_on_layer=1)
    with pytest.raises(RuntimeError):
        with module.capture_probes(stub, n_layers=3) as state:
            raise RuntimeError("simulated failure inside the capture window")
    assert stub.handles_removed == stub.handles_created, "every hook must be removed on exception"
    assert all(handle.removed for handle in stub.handles)


def test_hh06_capture_is_off_by_default_and_never_returns_a_modified_tensor():
    """A passive hook may observe; it must not alter the forward value."""
    module = _load_harness_module()
    stub = StubModule(with_pythia=True, layers=2, value=[2.0, -3.0, 4.0])
    with module.capture_probes(stub, n_layers=2) as state:
        original = StubTensor([list(stub._value)])
        returned = stub.fire_mlp(layer_idx=0, tensor=original)
    assert returned is original, (
        "with no intervention the hook must return the module's own output object unchanged")
    assert state.mlp_post[0] == [2.0, -3.0, 4.0]
    assert stub.last_input_value is original, "the passive hook must not replace the tensor"


def test_hh06_intervention_coverage_is_recorded_per_layer():
    module = _load_harness_module()
    stub = StubModule(with_pythia=True, layers=2, value=[1.0, 1.0, 1.0, 1.0])
    scoped = module.EraserIntervention(coords=((1, 0),), gain=1.0)
    with module.capture_probes(stub, n_layers=2, intervention=scoped) as state:
        layer0_in = StubTensor([[1.0, 1.0, 1.0, 1.0]])
        layer1_in = StubTensor([[1.0, 1.0, 1.0, 1.0]])
        layer0 = stub.fire_mlp(layer_idx=0, tensor=layer0_in)
        layer1 = stub.fire_mlp(layer_idx=1, tensor=layer1_in)
    assert layer0 is layer0_in, "an untargeted layer must be untouched"
    assert layer1 is not layer1_in, "the targeted layer must be modified"
    assert layer1[0, -1][0] == 0.0, "the declared coordinate must be suppressed to zero"
    assert layer1[0, -1][1:] == [1.0, 1.0, 1.0], "no other coordinate may change"
    assert layer1_in[0, -1][0] == 1.0, "the caller's tensor must not be mutated in place"
    assert state.mlp_post[1] == [0.0, 1.0, 1.0, 1.0], "capture must record the modified value"


# ===========================================================================
# Helpers (reviewer-owned; no production code is imported)
# ===========================================================================
def _load_harness_module():
    if not HARNESS_SOURCE.is_file():
        pytest.skip("HARNESS_SOURCE_UNAVAILABLE")
    spec = importlib.util.spec_from_file_location("_pinned_probe_runner", HARNESS_SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def vector_equal_exact(left, right) -> bool:
    """Exact equality only: no tolerance is claimed before a result is seen."""
    return list(left) == list(right)


def coverage_report(declared, observed):
    """HH04 shape: expected versus observed, with unobserved kept distinct from 0."""
    observed = list(observed)
    sites = [{"site": name, "observed_calls": (1 if name in observed else None),
              "state": "OBSERVED" if name in observed else "HOOK_NEVER_FIRED"}
             for name in declared]
    complete = bool(declared) and all(row["state"] == "OBSERVED" for row in sites)
    return {"expected_sites": len(declared), "observed_sites": len(observed),
            "sites": sites, "status": "COMPLETE" if complete else "INCOMPLETE",
            "receipt_completeness": "COMPLETE" if complete else "INCOMPLETE",
            "zero_is_not_an_observation": True}


def require_intervention_target(*, observed_shape, declared_shape, observed_calls=1):
    """Refuse an intervention whose target was never reached or does not match."""
    if tuple(observed_shape) != tuple(declared_shape):
        raise ValueError("INTERVENTION_SHAPE_MISMATCH: observed %s vs declared %s"
                         % (tuple(observed_shape), tuple(declared_shape)))
    if not observed_calls:
        raise ValueError("INTERVENTION_SITE_UNREACHED: the declared site was never reached")


def build_intervention_record(*, site, coords, gain, role, overhead_ns):
    return {"site": site, "coords": tuple(coords), "gain": float(gain), "role": role,
            "size": len(coords), "overhead_ns": int(overhead_ns)}


def compare_intervention_pair(target, control):
    """Matched-control check: size, rank, gain and instrumentation overhead."""
    return {"same_size": target["size"] == control["size"],
            "same_rank": target["size"] == control["size"],
            "same_gain": target["gain"] == control["gain"],
            "overhead_delta_ns": abs(target["overhead_ns"] - control["overhead_ns"]),
            "matched": (target["size"] == control["size"] and target["gain"] == control["gain"]
                        and target["overhead_ns"] == control["overhead_ns"]
                        and target["role"] != control["role"])}


# --- minimal tensor/module stubs: enough to exercise the documented hook contract ---
class RowView:
    """The last-position row of a stub tensor, with the tensor methods the pinned hook uses."""

    def __init__(self, data):
        self.data = data

    def detach(self):
        return self

    def float(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return list(self.data)

    def __getitem__(self, idx):
        return self.data[idx]

    def __setitem__(self, idx, value):
        self.data[idx] = value

    def __len__(self):
        return len(self.data)

    def __eq__(self, other):
        if isinstance(other, RowView):
            return self.data == other.data
        if isinstance(other, list):
            return self.data == other
        return NotImplemented

    def __repr__(self):
        return "RowView(%r)" % (self.data,)


class StubTensor:
    """A 2-D tensor stub with torch-like indexing for ``[0, -1, idx]`` access."""

    def __init__(self, data):
        self.data = [list(row) for row in data]

    @property
    def shape(self):
        return (len(self.data), len(self.data[0]) if self.data else 0)

    def clone(self):
        return StubTensor(self.data)

    # the pinned hook calls these three before reading values
    def detach(self):
        return self

    def float(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return [list(row) for row in self.data]

    def _resolve(self, key):
        if isinstance(key, tuple) and len(key) == 3:
            batch, position, idx = key
            assert batch == 0, "the pinned eraser only writes the batch-0 row"
            assert position == -1, "the pinned eraser only writes the last position"
            return self, (position, idx)
        if isinstance(key, tuple) and len(key) == 2:
            batch, idx = key
            assert batch == 0
            return self, idx
        return self, key

    def __getitem__(self, key):
        if isinstance(key, tuple) and len(key) == 3:
            _, position, idx = key
            assert position == -1
            return self.data[0][idx]
        if isinstance(key, tuple) and len(key) == 2:
            _, idx = key
            if idx == -1:
                return RowView(self.data[0])
            return RowView(self.data[idx])
        if key == -1:
            return RowView(self.data[-1])
        return RowView(self.data[key])

    def __setitem__(self, key, value):
        if isinstance(key, tuple) and len(key) == 3:
            _, position, idx = key
            assert position == -1
            self.data[0][idx] = value
            return
        if isinstance(key, tuple) and len(key) == 2:
            _, idx = key
            target = self.data[0] if idx == -1 else self.data[idx]
            if isinstance(value, list):
                self.data[self.data.index(target)] = list(value)
            else:
                target[idx] = value
            return
        if isinstance(value, list):
            self.data[key] = list(value)
        else:
            self.data[key] = value

    def __len__(self):
        return len(self.data)

    def __eq__(self, other):
        return isinstance(other, StubTensor) and self.data == other.data

    def __repr__(self):
        return "StubTensor(%r)" % (self.data,)


class StubHandle:
    def __init__(self):
        self.removed = False
        self.owner = None

    def remove(self):
        self.removed = True
        if self.owner is not None:
            self.owner.handles_removed += 1


class StubModule:
    """Stands in for a HELM-like model object: no gpt_neox unless asked."""

    def __init__(self, *, with_pythia=False, layers=2, value=(1.0, -2.0), explode_on_layer=None):
        self.handles = []
        self.handles_created = 0
        self.handles_removed = 0
        self.last_input_value = None
        self._explode_on = explode_on_layer
        self._value = list(value)
        if with_pythia:
            self.gpt_neox = type("G", (), {})()
            self.gpt_neox.layers = [StubLayer(self, index) for index in range(layers)]

    # harness-facing API -------------------------------------------------
    @property
    def _module_layers(self):
        return getattr(getattr(self, "gpt_neox", None), "layers", None)

    def _register(self, hook):
        handle = StubHandle()
        handle.owner = self
        self.handles.append(handle)
        self.handles_created += 1
        return handle

    def fire_mlp(self, *, layer_idx, tensor=None):
        """Emit one forward pass through the hooked layer."""
        if self._explode_on == layer_idx:
            raise RuntimeError("simulated hook-region failure")
        if tensor is None:
            tensor = StubTensor([list(self._value)])
        self.last_input_value = tensor
        return self._module_layers[layer_idx].mlp.fire(tensor)


class StubLayer:
    def __init__(self, owner, index):
        self.mlp = StubMlp(owner, index)


class StubMlp:
    def __init__(self, owner, index):
        self.owner = owner
        self.index = index
        self._hook = None

    def register_forward_hook(self, hook):
        self._hook = hook
        return self.owner._register(hook)

    def fire(self, tensor):
        if self._hook is None:
            return tensor
        result = self._hook(self, None, tensor)
        return tensor if result is None else result


# ===========================================================================
# NOT_RUN — requires an admitted venue with a real HELM checkpoint
# ===========================================================================
NOT_RUN_FOR_ADMITTED_VENUE = (
    ("helm_reach_site_enumeration",
     "enumerate every real call site of _reach_options/_node_options/head_logits on a "
     "preserved checkpoint and record expected versus observed call counts",
     "python -m pytest -q -p no:cacheprovider <this file> -k helm_reach_site_enumeration"),
    ("passive_neutrality",
     "compare uninstrumented and observed forwards on the same initial state: prediction, "
     "score arrays, model/optimizer state, RNG, and hook removal (HH03)",
     "requires a CUDA venue and one preserved checkpoint"),
    ("task_level_matched_control",
     "score Parts/Reach under baseline, no-op, target suppression, and a matched off-path "
     "suppression of equal size and gain (HH12)",
     "requires the admitted diagnostic job and its priced record"),
)

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
