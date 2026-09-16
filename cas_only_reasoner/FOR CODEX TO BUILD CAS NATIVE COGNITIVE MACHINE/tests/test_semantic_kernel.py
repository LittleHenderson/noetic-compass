"""Actual memory-dependent behavior and authority failures of native0.4."""
from dataclasses import replace
from fractions import Fraction
import random

import pytest

from cncm.canonical import digest
from cncm.model import ContractError, Intent, IntentType, TerminalStatus
from cncm.native_model import NativeBudget
from cncm.nested_kernel import nested_intent
from cncm.nested_model import NestedIntentType
from cncm.nested_profile import load_nested_profile
from cncm.semantic_engine import SemanticMachine
from cncm.semantic_kernel import semantic_intent
from cncm.semantic_model import (SourceStatement, MemoryRef, SemanticEquation,
                                 SemanticIntentType, create_problem)
from cncm.semantic_profile import load_semantic_profile


def source(value="5", *, scope="project", key="fee", source_id="source-a", previous=None,
           action="ASSERT", status="TEST_FIXTURE"):
    return SourceStatement(scope, key, source_id, value, status, action, previous,
                           "engineering-fixture:fee-example")


def task(constant="26", *, updates=(), scope="project", requirement="ATTESTED", **kwargs):
    return create_problem((SemanticEquation("x", "3", MemoryRef(scope,"fee",requirement), constant),),
                          "x", updates=updates, **kwargs)


@pytest.fixture(scope="module")
def profile():
    return load_semantic_profile()


def machine(profile, *statements):
    return SemanticMachine(profile, trusted_ingress=tuple(sorted(s.statement_digest for s in statements)))


def execute(m, i):
    return m.coordinator.execute(enabled_components=(i.issuer_subsystem,),
        scheduled_components=(i.issuer_subsystem,), intents=(i,))


def test_old_nested_source_profile_unchanged():
    assert load_nested_profile().profile_digest == "49f6c321472c6223b42a39ea21e402d2018ce5bd747acfd9266dc638aaf5be38"


def test_correction_changes_later_task_without_resupplying_value(profile, monkeypatch):
    old = source(); corrected = source("8", previous=old.statement_digest)
    unrelated = source("11", scope="neighbor")
    baseline = machine(profile,old)
    assert baseline.run(task("35",updates=(old,))).output == "10"
    m = machine(profile,old,unrelated)
    first = m.run(task(updates=(old,unrelated)))
    assert first.output == "7" and first.terminal_status is TerminalStatus.CONCLUDED
    original_records = m.state.memory_statements
    import cncm.nested_kernel as nk
    monkeypatch.setattr(nk,"select_finite_candidate",lambda:pytest.fail("reused procedure selected again"))
    monkeypatch.setattr(nk,"qualify_procedure",lambda *a:pytest.fail("reused procedure requalified"))
    assert corrected.statement_digest not in m.trusted_ingress
    correction = m.run(task("26",updates=(corrected,),problem_id="correction"),allow_acquisition=False,
                       additional_trusted_ingress=(corrected.statement_digest,))
    assert correction.output == "6"
    later = task("35",problem_id="later")
    assert later.updates == () and isinstance(later.equations[0].b,MemoryRef)
    result = m.run(later,allow_acquisition=False)
    assert result.output == "9" and result.terminal_status is TerminalStatus.CONCLUDED
    assert m.state.memory_statements[:len(original_records)] == original_records
    assert m.state.memory_bindings[0].statement_digests == (corrected.statement_digest,)
    assert m.state.memory_bindings[0].statuses == ("TEST_FIXTURE",)
    assert m.state.native_budget == NativeBudget(512-58,128-4)
    assert "semantic_resolution" in {p.source_type for p in m.state.branch_table[0].proof_steps[0].provenance}
    assert m.run(task("35",scope="neighbor",problem_id="neighbor"),allow_acquisition=False).output == "8"


@pytest.mark.parametrize("mode",["missing","unanchored","stale","revoked","conflict","verification"])
def test_refusal_before_any_arithmetic(profile,mode):
    old=source(); updates=(old,); anchors=(old,); requirement="ATTESTED"
    if mode=="missing":updates=();anchors=()
    if mode=="unanchored":anchors=()
    if mode=="stale":
        bad=source("8",previous="a"*64);updates=(old,bad);anchors=updates
    if mode=="revoked":
        revoked=source(None,action="RETRACT",previous=old.statement_digest);updates=(old,revoked);anchors=updates
    if mode=="conflict":
        rival=source("8",source_id="source-b");updates=(old,rival);anchors=updates
    if mode=="verification":requirement="INDEPENDENTLY_VERIFIED"
    m=machine(profile,*anchors); result=m.run(task(updates=updates,requirement=requirement))
    assert result.terminal_status is TerminalStatus.NEEDS_INFORMATION and result.output is None
    assert m.state.memory_failure and not m.state.native_calls and not m.state.procedure_heads
    assert m.state.native_budget.instructions_remaining < 512
    assert m.state.native_budget.checker_calls_remaining < 128


def test_insufficient_budget_refuses_before_checker(profile,monkeypatch):
    old=source();m=machine(profile,old)
    import cncm.semantic_kernel as sk
    monkeypatch.setattr(sk,"validate_source_update",lambda *a,**k:pytest.fail("unfunded check"))
    r=m.run(task(updates=(old,),budget=NativeBudget(11,128)))
    assert r.terminal_status is TerminalStatus.BUDGET_EXHAUSTED and r.output is None
    assert m.state.native_budget == NativeBudget(11,128)


def test_unresolved_memory_cannot_be_bypassed_by_direct_nested_request(profile):
    old=source();m=machine(profile,old);m.start(task(updates=(old,)))
    i=nested_intent(m.coordinator,NestedIntentType.REQUEST_EQUATION,{"variable":"x"})
    outcome=execute(m,i)
    assert outcome.rejected_intents and not m.state.native_calls
    assert m.state.native_budget == NativeBudget()
    assert m.run().output == "7"


def test_wrong_issuer_stale_and_duplicate_memory_proposals_do_not_write(profile):
    old=source();m=machine(profile,old);m.start(task(updates=(old,)))
    i=m.coordinator.next_intent()
    wrong=replace(i,issuer_subsystem="equation_controller")
    assert execute(m,wrong).rejected_intents
    assert not m.state.memory_statements and m.state.native_budget == NativeBudget()
    assert execute(m,i).rejected_intents  # old pre-state
    fresh=m.coordinator.next_intent()
    duplicate=m.coordinator.execute(enabled_components=(fresh.issuer_subsystem,),
        scheduled_components=(fresh.issuer_subsystem,),intents=(fresh,fresh))
    assert duplicate.rejected_intents and not m.state.memory_statements
    assert len(m.coordinator.proposal_batches[-1])==2
    assert m.run().output=="7"


def test_correction_cannot_change_suspended_inputs(profile):
    old=source();corrected=source("8",previous=old.statement_digest)
    m=machine(profile,old,corrected);m.start(task(updates=(old,)))
    while not m.state.rpm_stack:m.advance()
    before=m.state
    i=semantic_intent(m.coordinator,SemanticIntentType.STORE_SOURCE,
        {"index":1,"statement":corrected.to_dict()})
    assert execute(m,i).rejected_intents
    assert m.state.memory_statements==before.memory_statements
    assert m.state.memory_bindings==before.memory_bindings
    assert m.state.native_budget==before.native_budget


@pytest.mark.parametrize("seed",range(8))
def test_later_structural_variants_use_current_memory_and_fraction_oracle(profile,seed):
    rng=random.Random(81000+seed)
    old=source();value=Fraction(rng.randint(-9,12),rng.randint(1,4))
    corrected=source(str(value),previous=old.statement_digest)
    m=machine(profile,old,corrected);assert m.run(task(updates=(old,))).output=="7"
    assert m.run(task(updates=(corrected,),problem_id="correct"),allow_acquisition=False).output is not None
    a=rng.choice((-5,-2,1,3));c=rng.randint(-20,25)
    p=create_problem((SemanticEquation("root","2","1","0",(("x","3"),)),
        SemanticEquation("x",str(a),MemoryRef("project","fee"),str(c)),
        SemanticEquation("unused","0",MemoryRef("absent","secret"),"1")),
        "root",problem_id="variant")
    r=m.run(p,allow_acquisition=False)
    expected=(3*((Fraction(c)-value)/a)-1)/2
    assert r.terminal_status is TerminalStatus.CONCLUDED and Fraction(r.output)==expected
    assert len(m.state.memory_bindings)==1
    assert {call.variable for call in m.state.native_calls}=={"root","x"}
    assert {e.variable for e in m.coordinator.nested_problem.equations}=={"root","x"}
