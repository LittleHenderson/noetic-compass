"""CPU-only effect tests, initialized weights, zero optimizer steps."""
import ast
import copy
import hashlib
import pathlib
import sys
import types

import pytest
import torch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"research/CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import pointer_learner as P

torch.set_num_threads(2)

def container(seed=730, *, enabled=True):
    torch.manual_seed(seed)
    state = {name: torch.randn(P.PARAMETER_SHAPES[name])*0.03 for name in P.PARAMETERS}
    framework = types.SimpleNamespace(module=types.SimpleNamespace(state_dict=lambda: state))
    return P._build_container(torch, framework, torch.device("cpu"), analogy_focus_comparison=enabled)

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

@pytest.mark.parametrize("seed",[730,731,732])
def test_changing_only_focus_structure_changes_relative_analogy_scores(seed, legacy_scores):
    model=container(seed)
    before,after=forward(model),forward(model,shape="star")
    assert torch.equal(before.worlds[1:],after.worlds[1:])  # alternatives are held fixed
    assert torch.equal(before.declaration_embed,after.declaration_embed)
    old_before=legacy_scores(before,"world_id",["W1","W2"])
    old_after=legacy_scores(after,"world_id",["W1","W2"])
    assert torch.equal(old_before,old_after)  # reproduces missing path using original source method
    scores1=before._world_scores("world_id",["W1","W2"])
    scores2=after._world_scores("world_id",["W1","W2"])
    # This checks a path, not a minimum useful margin. Random initialization can
    # have a very small effect; gradient coverage below separately tests coupling.
    assert not torch.equal(scores1[0]-scores1[1],scores2[0]-scores2[1])
    print({"seed":seed,"legacy_max_difference":float((old_before-old_after).abs().max().detach()),
           "repaired_margin_before":float((scores1[0]-scores1[1]).detach()),
           "repaired_margin_after":float((scores2[0]-scores2[1]).detach())})

def test_focus_domain_also_reaches_relative_scores():
    model=container()
    before,after=forward(model),forward(model,focus_domain=2)
    assert torch.equal(before.worlds,after.worlds)
    assert torch.equal(before.declaration_embed[1:],after.declaration_embed[1:])
    a=before._world_scores("world_id",["W1","W2"])
    b=after._world_scores("world_id",["W1","W2"])
    assert not torch.isclose(a[0]-a[1],b[0]-b[1],atol=1e-6,rtol=0)

def test_gradient_reaches_focus_structure_domain_and_comparison_head():
    model=container()
    f=forward(model)
    f.worlds.retain_grad()
    f.declaration_embed.retain_grad()
    scores=f._world_scores("world_id",["W1","W2"])
    (scores[0]-scores[1]).backward()
    for grad in (f.worlds.grad[0],f.declaration_embed.grad[0, f.declaration_names.index("domain")],
                 model.analogy_head[0].weight.grad):
        assert torch.isfinite(grad).all() and grad.abs().sum()>0
    assert model.world_head[0].weight.grad is None
    assert model.node_encode.weight.grad.abs().sum()>0

@pytest.mark.parametrize("kind,field",[("definition","kind_ref"),("context","setting_ref")])
def test_other_world_choice_paths_remain_exactly_legacy(kind,field,legacy_scores):
    f=forward(container(),kind=kind)
    assert torch.equal(f._world_scores(field,["W0","W1","W2","NO_MATCH"]),
                       legacy_scores(f,field,["W0","W1","W2","NO_MATCH"]))

def test_public_head_dispatch_uses_the_new_comparison():
    f=forward(container())
    plan={"slots":[{"slot_id":"diagnostic-analogy","field":"world_id","symbols":["W1","W2"],"coordinates":[]}]}
    output=f.head_logits(plan,indicators=[0]*P.CLAUSE_COUNT)
    assert torch.equal(output["diagnostic-analogy"],f._world_scores("world_id",["W1","W2"]))

def test_historical_layout_is_rejected_and_new_layout_roundtrips():
    model=container()
    old={k:v for k,v in model.state_dict().items() if not k.startswith("analogy_head.")}
    with pytest.raises(RuntimeError,match="analogy_head"):
        container().load_state_dict(old,strict=True)
    container(enabled=False).load_state_dict(old,strict=True)
    assert P.CHECKPOINT_SCHEMA=="cncm.typed-pointer-checkpoint/0.2"
    restored=container(999)
    restored.load_state_dict(model.state_dict(),strict=True)
    assert torch.equal(forward(model)._world_scores("world_id",["W1","W2"]),
                       forward(restored)._world_scores("world_id",["W1","W2"]))

def test_switch_off_reproduces_legacy_scores_and_shared_initialization(legacy_scores):
    enabled=container()
    enabled_rng=torch.get_rng_state().clone()
    disabled=container(enabled=False)
    assert torch.equal(enabled_rng,torch.get_rng_state())
    for name,value in disabled.state_dict().items():
        assert torch.equal(value,enabled.state_dict()[name])
    for shape in ("chain","star"):
        f=forward(disabled,shape=shape)
        assert torch.equal(f._world_scores("world_id",["W1","W2"]),legacy_scores(f,"world_id",["W1","W2"]))

def test_complete_assignment_decoder_retains_historical_bytes():
    before=ROOT/"records/helm_failure_research_20260922/agents/A2/source_copies/helm2/slots.py"
    current=ROOT/"research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/slots.py"
    assert hashlib.sha256(before.read_bytes().replace(b"\r\n",b"\n")).digest()==hashlib.sha256(current.read_bytes().replace(b"\r\n",b"\n")).digest()
