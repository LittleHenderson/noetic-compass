"""Native graph behavior, independent exact references and retained-version gates."""
from dataclasses import replace
from fractions import Fraction
import random

import pytest

from cncm.canonical import digest
from cncm.model import ContractError, TerminalStatus
from cncm.native_model import NativeBudget
from cncm.native_profile import load_native_profile
from cncm.nested_engine import NestedMachine
from cncm.nested_model import Equation, NestedIntentType, create_problem
from cncm.nested_profile import load_nested_profile

@pytest.fixture(scope="module")
def profile():
    return load_nested_profile()

def run(profile,equations,query,**kwargs):
    machine=NestedMachine(profile)
    result=machine.run(create_problem(equations,query,**kwargs))
    return machine,result

def admitted(machine,kind):
    return [event for event in machine.coordinator.trace.events
        if any(intent.intent_type is kind and intent.intent_id in event.authorized_intent_ids
            for intent in event.proposed_intents)]

def test_accepted_v02_source_profile_is_unchanged():
    assert load_native_profile().profile_digest=="c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607"

def test_real_nested_acquisition_and_same_caller_return(profile):
    problem=create_problem((Equation("y","2","1","0",(("x","1"),)),Equation("x","3","5","26")),"y")
    machine=NestedMachine(profile);machine.start(problem)
    first_run=machine.state.run_id
    suspended=[]
    while machine.state.halt_status is TerminalStatus.RUNNING:
        before=machine.state
        machine.advance()
        after=machine.state
        assert after.run_id==first_run
        assert after.native_budget.instructions_remaining<=before.native_budget.instructions_remaining
        assert after.native_budget.checker_calls_remaining<=before.native_budget.checker_calls_remaining
        if len(after.rpm_stack)==2:
            suspended.append(after)
            assert not after.branch_map()["branch-main"].proof_steps
            assert not after.branch_map()["branch-main"].propositions
            assert after.native_calls[0].variable=="y"
            assert after.native_calls[0].status=="WAITING_DEPENDENCY"
    assert suspended
    assert machine.result().output=="3"
    assert machine.state.halt_status is TerminalStatus.CONCLUDED
    assert len(admitted(machine,NestedIntentType.INSTALL_PROCEDURE))==1
    assert len(admitted(machine,NestedIntentType.APPLY_EQUATION))==2
    assert machine.state.native_budget==NativeBudget(512-264,128-38)
    calls={c.variable:c for c in machine.state.native_calls}
    assert calls["y"].dependency_records==(("x",calls["x"].execution_digest),)
    assert not machine.state.rpm_stack
    assert len(machine.state.branch_map()["branch-main"].proof_steps)==1

def test_shuffled_diamond_reuses_prerequisite_and_ignores_unreachable_failure(profile):
    equations=(
        Equation("z","2","1","0",(("x","1"),("y","1"))),
        Equation("unused","0","0","0",(("unused","1"),)),
        Equation("y","2","1","0",(("a","1"),)),
        Equation("a","3","5","26"),
        Equation("x","1","-1","0",(("a","1"),)),
    )
    machine,result=run(profile,equations,"z")
    assert result.terminal_status is TerminalStatus.CONCLUDED and result.output=="5"
    assert {c.variable:c.output for c in machine.state.native_calls}=={"z":"5","x":"8","a":"7","y":"3"}
    assert len(admitted(machine,NestedIntentType.APPLY_EQUATION))==4
    assert len(admitted(machine,NestedIntentType.INSTALL_PROCEDURE))==1
    assert len(admitted(machine,NestedIntentType.PUSH_DEPENDENCY))==3
    reordered=create_problem(tuple(reversed(equations)),"z")
    assert reordered.to_dict()==result.problem.to_dict()
    other=NestedMachine(profile);other.run(reordered)
    assert other.journal()==machine.journal()

@pytest.mark.parametrize("seed",range(12))
def test_generated_dependency_graphs_match_independent_fraction_reference(profile,seed):
    rng=random.Random(73100+seed)
    count=3+seed%5
    equations=[]
    reference={}
    for index in range(count):
        variable=f"v{index}"
        a=rng.choice((-5,-3,-1,1,2,4))
        b=rng.randint(-7,7)
        constant=rng.randint(-9,9)
        chosen=sorted(rng.sample(range(index),min(index,1+index%3))) if index else []
        # Force the previous layer on alternate tasks so structural depths vary.
        if index and seed%2==0 and index-1 not in chosen:
            chosen=sorted((chosen+[index-1])[-3:])
        terms=tuple((f"v{j}",str(rng.choice((-3,-1,1,2)))) for j in chosen)
        equation=Equation(variable,str(a),str(b),str(constant),terms)
        equations.append(equation)
        rhs=Fraction(constant)+sum((Fraction(c)*reference[v] for v,c in terms),Fraction())
        reference[variable]=(rhs-b)/a
    rng.shuffle(equations)
    query=f"v{count-1}"
    machine,result=run(profile,tuple(equations),query,budget=NativeBudget(2048,256),rpm_depth_limit=8,max_ticks=192)
    assert result.terminal_status is TerminalStatus.CONCLUDED
    assert Fraction(result.output)==reference[query]
    graph={e.variable:e for e in equations}
    reachable=set()
    def visit(v):
        if v not in reachable:
            reachable.add(v)
            for dep,_ in graph[v].rhs_terms:visit(dep)
    visit(query)
    assert {call.variable for call in machine.state.native_calls}==reachable
    for call in machine.state.native_calls:
        assert Fraction(call.output)==reference[call.variable]
    assert len(admitted(machine,NestedIntentType.APPLY_EQUATION))==len(reachable)
    assert len(admitted(machine,NestedIntentType.INSTALL_PROCEDURE))==1

@pytest.mark.parametrize("equations,query,status,reason",[
    ((Equation("a","1","0","0",(("missing","1"),)),),"a",TerminalStatus.NEEDS_INFORMATION,"MISSING_INFORMATION"),
    ((Equation("a","1","0","0",(("a","1"),)),),"a",TerminalStatus.LOOP_LIMIT_REACHED,"CYCLIC_DEPENDENCY"),
    ((Equation("a","1","0","0",(("b","1"),)),Equation("b","1","0","0",(("a","1"),))),
        "a",TerminalStatus.LOOP_LIMIT_REACHED,"CYCLIC_DEPENDENCY"),
    ((Equation("a","0","1","1"),),"a",TerminalStatus.NEEDS_CAPABILITY,"TRANSITION_REJECTED"),
])
def test_typed_failure_propagates_without_answer(profile,equations,query,status,reason):
    machine,result=run(profile,equations,query)
    assert result.terminal_status is status and result.output is None
    assert not machine.state.rpm_stack
    assert not machine.state.branch_map()["branch-main"].proof_steps
    assert reason in {r.body_dict()["reason"] for r in machine.state.native_records if r.kind=="FAILURE"}

def test_live_depth_refusal_and_native_budget_refusal(profile):
    equations=(Equation("a","1","0","0",(("b","1"),)),Equation("b","1","0","7"))
    machine,result=run(profile,equations,"a",rpm_depth_limit=1)
    assert result.terminal_status is TerminalStatus.NEEDS_CAPABILITY
    assert any(r.kind=="FAILURE" and r.body_dict()["reason"]=="DEPTH_EXHAUSTED" for r in machine.state.native_records)
    assert not machine.state.procedure_heads and not machine.state.rpm_stack
    machine,result=run(profile,(Equation("a","1","0","7"),),"a",budget=NativeBudget(20,2))
    assert result.terminal_status is TerminalStatus.BUDGET_EXHAUSTED
    assert machine.state.native_budget==NativeBudget(8,2)
    assert not machine.state.procedure_heads

def test_tick_exhaustion_preserves_unfinished_frames_without_new_budget(profile):
    p=create_problem((Equation("a","1","0","0",(("b","1"),)),Equation("b","1","0","7")),"a",max_ticks=7)
    machine=NestedMachine(profile);result=machine.run(p)
    assert result.terminal_status is TerminalStatus.BUDGET_EXHAUSTED
    assert machine.state.rpm_stack
    with pytest.raises(ContractError):machine.start(p)

def test_next_input_cannot_silently_widen_from_128_to_512_bits(profile):
    denominator=str(2**127-1)
    numerator=str(2**127-2)
    equations=(Equation("a","1/"+denominator,"0",numerator),
        Equation("b","1","0","0",(("a","1"),)))
    machine,result=run(profile,equations,"b")
    calls={c.variable:c for c in machine.state.native_calls}
    assert calls["a"].status=="COMPLETE" and Fraction(calls["a"].output).numerator.bit_length()>128
    assert calls["b"].status=="FAILED" and result.output is None
    assert result.terminal_status is TerminalStatus.NEEDS_CAPABILITY
    assert len(admitted(machine,NestedIntentType.APPLY_EQUATION))==1
    charges=[r.body_dict() for r in machine.state.native_records if r.kind=="WORK_RESERVATION"]
    assert charges[-1]["operation"]=="BIND_EQUATION" and charges[-1]["failure"]
    assert charges[-1]["instructions_allocated"]==12

def test_new_episode_reuses_registry_and_rollback_removes_dispatch(profile,monkeypatch):
    import cncm.nested_kernel as kernel
    machine,result=run(profile,(Equation("a","3","5","26"),),"a")
    assert result.output=="7"
    def forbidden(*a,**kw):raise AssertionError("reacquisition called")
    monkeypatch.setattr(kernel,"select_finite_candidate",forbidden)
    monkeypatch.setattr(kernel,"qualify_procedure",forbidden)
    next_problem=create_problem((Equation("x","-4","7","13"),Equation("y","2","0","0",(("x","1"),))),"y",problem_id="reuse")
    result=machine.run(next_problem,allow_acquisition=False)
    assert result.output=="-3/4" and result.terminal_status is TerminalStatus.CONCLUDED
    artifacts=machine.state.procedural_artifacts
    history=machine.state.native_records
    machine.start(create_problem((Equation("z","2","0","8"),),"z",problem_id="rollback"))
    machine.rollback()
    result=machine.run(allow_acquisition=False)
    assert result.terminal_status is TerminalStatus.NEEDS_CAPABILITY and result.output is None
    assert machine.state.procedural_artifacts==artifacts and not machine.state.procedure_heads
    assert machine.state.native_records[:len(history)]==history
