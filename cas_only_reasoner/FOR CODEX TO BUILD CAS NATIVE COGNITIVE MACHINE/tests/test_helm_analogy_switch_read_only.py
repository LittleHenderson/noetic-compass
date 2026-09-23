"""Read-only analogy switch on the pointer container. Initialized weights, zero optimizer steps.

Public contract (preregistration): "A repaired container must expose a read-only boolean attribute, written
`model.<switch>`. The probe records it and asserts it equals the requested state." The OFF layout, RNG use and
old scoring path must be unchanged. Fixtures and examples are those of `test_helm_analogy_focus_comparison.py`.
Every case runs on CPU except the last, which needs CUDA and is skipped where CUDA is unavailable.
"""
import ast
import json
import pathlib
import sys
import types

import pytest
import torch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"research/CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import pointer_learner as P

torch.set_num_threads(2)

SWITCH = "analogy_focus_comparison"
SEED = "analogy_seed"
NAMES = (SWITCH, SEED)
INVENTORY = ROOT/"records/helm_integrated_repairs_20260923/analogy_tensor_inventory.json"
ANALOGY_KEYS = ("analogy_head.0.weight", "analogy_head.2.weight", "analogy_head.2.bias",
                "analogy_head.3.weight", "analogy_head.3.bias")
ANALOGY_SHAPES = ([64, 452], [64], [64], [1, 64], [1])
OFF_PARAMETERS, ON_PARAMETERS = 174303, 203424
SYMBOLS = ["W1", "W2"]
EXAMPLES = (("chain", 1), ("star", 1), ("chain", 2))  # (focus shape, focus domain), as in the existing test


def framework(seed):
    torch.manual_seed(seed)
    state = {name: torch.randn(P.PARAMETER_SHAPES[name])*0.03 for name in P.PARAMETERS}
    return types.SimpleNamespace(module=types.SimpleNamespace(state_dict=lambda: state))


def container(seed=730, *, device="cpu", **switch):
    """The existing test's container; the switch keyword is passed through exactly as given, or not at all."""
    return P._build_container(torch, framework(seed), torch.device(device), **switch)


def reading(shape="chain", focus_domain=1, kind="analogy"):
    shapes = {"chain":[[0,1],[1,2],[2,3]], "star":[[0,1],[0,2],[0,3]]}
    worlds = {}
    for index,world in enumerate(("a","b","c")):
        worlds[world] = {"node_count":4, "nodes":[{"rank":i, "is_declared_whole":int(i==0)} for i in range(4)],
                         "contains":shapes[shape if index==0 else ("chain" if index==1 else "star")],
                         "is_focus":int(index==0),"is_target":0,
                         "declaration_ids":{field:[(focus_domain if index==0 else index)] for field in P.DECLARATION_FIELDS}}
    return {"focus_world_id":"a","worlds":worlds,
            "query":{"kind":P.pointer_inputs.KIND_IDS.index(kind),"kind_name":kind,"rule":0,
                     "whole":None,"part":None,"world_count":3,"target_world_id":None}}


def forward(model, **kwargs):
    return P.GraphForward(torch,model,reading(**kwargs),torch.device("cpu"))


@pytest.fixture(scope="module")
def legacy_scores():
    path = ROOT/"records/helm_failure_research_20260922/agents/A2/source_copies/helm2/pointer_learner.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    method = next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=="_world_scores")
    namespace = dict(vars(P))
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),"exec"),namespace)
    return namespace["_world_scores"]


class HeadCalls:
    """Forward hooks recording which world-choice head actually ran, and what it returned."""

    def __init__(self, model):
        self.calls, self.outputs, self.handles = {}, {}, []
        for name in ("analogy_head", "world_head"):
            if hasattr(model, name):
                self.handles.append(getattr(model, name).register_forward_hook(self._hook(name)))

    def _hook(self, name):
        def hook(module, inputs, output):
            self.calls[name] = self.calls.get(name, 0) + 1
            self.outputs[name] = output.detach().clone()
        return hook

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        for handle in self.handles:
            handle.remove()
        return False


def picked(f, flat, symbols=SYMBOLS):
    """The entries of one head output that `_world_scores` returns for `symbols`."""
    flat = flat.reshape(-1)
    return torch.stack([flat[f.world_position[P._world_alias_table_for(f.reading, symbol)]] for symbol in symbols])


def attempt_changes(model):
    """Try every write path a caller has on both names; return how many were refused with AttributeError."""
    enabled = model.analogy_focus_comparison
    replacements = {SWITCH: not enabled, SEED: None if enabled else P.ANALOGY_INIT_SEED}
    refused = 0
    for name, value in replacements.items():
        for write in (setattr, object.__setattr__):
            try:
                write(model, name, value)
            except AttributeError:
                refused += 1
        for remove in (delattr, object.__delattr__):
            try:
                remove(model, name)
            except AttributeError:
                refused += 1
        model.__dict__[name] = value
    return refused


def layout(model):
    return [(key, list(value.shape)) for key, value in model.state_dict().items()]


# ---- (1) the value is a real bool equal to the construction argument; the seed follows it ----

@pytest.mark.parametrize("switch,expected", [
    pytest.param({}, True, id="default"),
    pytest.param({SWITCH: True}, True, id="true"),
    pytest.param({SWITCH: False}, False, id="false"),
    pytest.param(json.loads('{"analogy_focus_comparison": false}'), False, id="json-false"),
    pytest.param(json.loads('{"analogy_focus_comparison": true}'), True, id="json-true"),
])
def test_switch_reads_back_as_the_requested_bool(switch, expected):
    model = container(**switch)
    value = getattr(model, SWITCH)
    assert type(value) is bool and value is expected
    seed = getattr(model, SEED)
    if expected:
        assert type(seed) is int and seed == 20260923 == P.ANALOGY_INIT_SEED
    else:
        assert seed is None


@pytest.mark.parametrize("value", [0, 1, None, "false", 0.0])
def test_non_bool_switch_is_refused_at_construction(value):
    with pytest.raises(ValueError, match="POINTER_ANALOGY_SWITCH"):
        container(**{SWITCH: value})


# ---- (2) assignment and deletion raise AttributeError in both states; the value is unchanged ----

def test_switch_is_served_by_getter_only_class_properties():
    for enabled in (True, False):
        model = container(**{SWITCH: enabled})
        for name in NAMES:
            prop = type(model).__dict__[name]
            assert isinstance(prop, property) and prop.fset is None and prop.fdel is None
            assert name not in vars(model)
            assert name not in model._parameters and name not in model._buffers and name not in model._modules
        assert type(model).get_extra_state is torch.nn.Module.get_extra_state
        # The guard is narrow: every other attribute still goes through torch's own `Module.__setattr__`.
        model.train(False)
        assert model.training is False
        model.train(True)
        model.unrelated_probe_note = "kept"
        assert model.unrelated_probe_note == "kept"
        del model.unrelated_probe_note


@pytest.mark.parametrize("enabled", [True, False], ids=["on", "off"])
@pytest.mark.parametrize("name", NAMES)
def test_assignment_and_deletion_raise_and_leave_the_value_unchanged(name, enabled):
    model = container(**{SWITCH: enabled})
    before = getattr(model, name)
    keys = layout(model)
    values = [not enabled, enabled, None, 0, 1, P.ANALOGY_INIT_SEED + 1, "false", torch.tensor(1.0),
              torch.nn.Parameter(torch.zeros(1)), torch.nn.Buffer(torch.zeros(1)), torch.nn.Linear(1, 1)]
    for value in values:
        with pytest.raises(AttributeError):
            setattr(model, name, value)
        after = getattr(model, name)
        assert type(after) is type(before) and after == before
    with pytest.raises(AttributeError):
        delattr(model, name)
    with pytest.raises(AttributeError):
        object.__setattr__(model, name, not enabled)
    with pytest.raises(AttributeError):
        object.__delattr__(model, name)
    if name == SWITCH:
        with pytest.raises(AttributeError):
            model.analogy_focus_comparison = not enabled
        with pytest.raises(AttributeError):
            del model.analogy_focus_comparison
    after = getattr(model, name)
    assert type(after) is type(before) and after == before
    assert layout(model) == keys
    assert name not in vars(model)
    assert name not in model._parameters and name not in model._buffers and name not in model._modules


# ---- (3) an instance-dict write changes neither the value nor the scoring branch ----

@pytest.mark.parametrize("enabled", [True, False], ids=["on", "off"])
def test_instance_dict_writes_change_neither_value_nor_scoring_branch(enabled, legacy_scores):
    model = container(**{SWITCH: enabled})
    expected = forward(model)._world_scores("world_id", SYMBOLS).detach().clone()
    model.__dict__[SWITCH] = not enabled
    model.__dict__[SEED] = None if enabled else P.ANALOGY_INIT_SEED
    assert getattr(model, SWITCH) is enabled
    assert getattr(model, SEED) == (P.ANALOGY_INIT_SEED if enabled else None)
    f = forward(model)
    with HeadCalls(model) as heads:
        scores = f._world_scores("world_id", SYMBOLS)
    assert torch.equal(scores, expected)
    if enabled:
        assert heads.calls == {"analogy_head": 1}
        assert torch.equal(scores, picked(f, heads.outputs["analogy_head"]))
    else:
        assert heads.calls == {"world_head": 1}
        assert torch.equal(scores, legacy_scores(f, "world_id", SYMBOLS))


# ---- (4) head presence, key order, the five ON shapes, parameter counts, no switch-named key ----

def test_layout_head_presence_and_parameter_counts():
    on, off = container(**{SWITCH: True}), container(**{SWITCH: False})
    assert hasattr(on, "analogy_head") is True and hasattr(off, "analogy_head") is False
    on_state, off_state = on.state_dict(), off.state_dict()
    on_keys, off_keys = list(on_state), list(off_state)
    assert [key for key in on_keys if key.startswith("analogy_head.")] == list(ANALOGY_KEYS)
    assert off_keys == [key for key in on_keys if key not in ANALOGY_KEYS]
    assert [list(on_state[key].shape) for key in ANALOGY_KEYS] == list(ANALOGY_SHAPES)
    for key in off_keys:
        assert off_state[key].shape == on_state[key].shape
    assert sum(p.numel() for p in off.parameters()) == OFF_PARAMETERS
    assert sum(p.numel() for p in on.parameters()) == ON_PARAMETERS
    assert len(list(off.parameters())) == len(off_keys) and len(list(on.parameters())) == len(on_keys)
    assert list(off.buffers()) == [] and list(on.buffers()) == []
    for key in on_keys + off_keys:
        assert "_extra_state" not in key and SWITCH not in key and SEED not in key


# ---- (5) the OFF (and ON) key/shape list equals the committed inventory's rows ----

def test_layout_matches_the_committed_tensor_inventory():
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    rows = inventory["rows"]
    assert {row["status"] for row in rows} == {"CARRIED_UNCHANGED_LAYOUT", "FRESH"}
    on, off = container(**{SWITCH: True}), container(**{SWITCH: False})
    assert layout(off) == [(row["name"], list(row["shape"])) for row in rows
                           if row["status"] == "CARRIED_UNCHANGED_LAYOUT"]
    assert layout(on) == [(row["name"], list(row["shape"])) for row in rows]
    fresh = [(row["name"], list(row["shape"])) for row in rows if row["status"] == "FRESH"]
    assert fresh == [(row["name"], list(row["shape"])) for row in inventory["new_tensors"]]
    assert fresh == [(key, shape) for key, shape in zip(ANALOGY_KEYS, ANALOGY_SHAPES)]
    on_state = on.state_dict()
    assert all(on_state[row["name"]].numel() == row["elements"] for row in rows)
    assert sum(p.numel() for p in off.parameters()) == inventory["legacy_parameters"] == OFF_PARAMETERS
    assert sum(p.numel() for p in on.parameters()) == inventory["experimental_parameters"] == ON_PARAMETERS
    assert on.analogy_seed == inventory["analogy_seed"] and off.analogy_seed is None


# ---- (6) after attempted changes: ON scores come from analogy_head, OFF scores equal legacy ----

@pytest.mark.parametrize("seed", [730, 731, 732])
def test_scoring_branch_survives_attempted_changes(seed, legacy_scores):
    on, off = container(seed, **{SWITCH: True}), container(seed, **{SWITCH: False})
    assert attempt_changes(on) == 8 and attempt_changes(off) == 8
    assert on.analogy_focus_comparison is True and off.analogy_focus_comparison is False
    for shape, focus_domain in EXAMPLES:
        f = forward(on, shape=shape, focus_domain=focus_domain)
        with HeadCalls(on) as heads:
            scores = f._world_scores("world_id", SYMBOLS)
        assert heads.calls == {"analogy_head": 1}
        assert torch.equal(scores, picked(f, heads.outputs["analogy_head"]))
        g = forward(off, shape=shape, focus_domain=focus_domain)
        with HeadCalls(off) as heads:
            scores = g._world_scores("world_id", SYMBOLS)
        assert heads.calls == {"world_head": 1}
        assert torch.equal(scores, legacy_scores(g, "world_id", SYMBOLS))
    for model in (on, off):
        for kind, field in (("definition", "kind_ref"), ("context", "setting_ref")):
            f = forward(model, kind=kind)
            symbols = ["W0", "W1", "W2", "NO_MATCH"]
            assert torch.equal(f._world_scores(field, symbols), legacy_scores(f, field, symbols))
    f = forward(on)
    plan = {"slots": [{"slot_id": "diagnostic-analogy", "field": "world_id", "symbols": SYMBOLS, "coordinates": []}]}
    output = f.head_logits(plan, indicators=[0]*P.CLAUSE_COUNT)
    assert torch.equal(output["diagnostic-analogy"], f._world_scores("world_id", SYMBOLS))


# ---- (7) CPU RNG state is equal after ON vs OFF construction ----

@pytest.mark.parametrize("first", [True, False], ids=["on-first", "off-first"])
def test_cpu_rng_state_and_shared_tensors_equal_after_on_and_off_construction(first):
    a = container(730, **{SWITCH: first})
    state_a = torch.get_rng_state().clone()
    b = container(730, **{SWITCH: not first})
    state_b = torch.get_rng_state().clone()
    assert torch.equal(state_a, state_b)
    on, off = (a, b) if first else (b, a)
    on_state = on.state_dict()
    for key, value in off.state_dict().items():
        assert torch.equal(value, on_state[key])
    # Reading the switch, and every refused write, draws nothing either.
    before = torch.get_rng_state().clone()
    assert attempt_changes(on) == 8 and attempt_changes(off) == 8
    assert (on.analogy_focus_comparison, on.analogy_seed, off.analogy_focus_comparison, off.analogy_seed) == \
        (True, P.ANALOGY_INIT_SEED, False, None)
    assert torch.equal(before, torch.get_rng_state())
    # The ON head's initial values depend on the analogy seed alone, not on the shared generator.
    other = container(731, **{SWITCH: True})
    for key in ANALOGY_KEYS:
        assert torch.equal(on_state[key], other.state_dict()[key])


# ---- (8) CUDA: RNG state of every device and all shared tensors are equal after ON vs OFF ----

@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is not available")
def test_cuda_rng_state_and_shared_tensors_equal_after_on_and_off_construction():
    def build(enabled):
        model = container(730, device="cuda", **{SWITCH: enabled})  # torch.manual_seed also seeds every CUDA device
        torch.cuda.synchronize()
        return model, torch.get_rng_state().clone(), [state.clone() for state in torch.cuda.get_rng_state_all()]
    on, cpu_on, cuda_on = build(True)
    off, cpu_off, cuda_off = build(False)
    assert torch.equal(cpu_on, cpu_off)
    assert len(cuda_on) == len(cuda_off) == torch.cuda.device_count()
    assert all(torch.equal(x, y) for x, y in zip(cuda_on, cuda_off))
    assert on.analogy_focus_comparison is True and off.analogy_focus_comparison is False
    on_state, off_state = on.state_dict(), off.state_dict()
    assert list(off_state) == [key for key in on_state if key not in ANALOGY_KEYS]
    for key, value in off_state.items():
        assert value.device.type == "cuda" and torch.equal(value, on_state[key])
    assert all(on_state[key].device.type == "cuda" for key in ANALOGY_KEYS)
    assert attempt_changes(on) == 8 and attempt_changes(off) == 8
    assert on.analogy_focus_comparison is True and off.analogy_focus_comparison is False
