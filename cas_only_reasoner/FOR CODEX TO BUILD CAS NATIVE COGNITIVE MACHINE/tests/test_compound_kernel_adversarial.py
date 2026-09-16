"""Independent qualification-stage and checked-receipt authority regressions.

Profiles explicitly simulate source identities. Fault injection tests the
coordinator's receipt receiver; it does not assert an external code-injection
path. Ordinary retained-state recovery remains a separately tested boundary.
"""
from copy import deepcopy

import pytest

from cncm.canonical import digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_kernel import compound_intent
from cncm.compound_model import CompoundIntentType as C, create_problem
from cncm.compound_profile import CompoundProfile, SOURCE_FILES, authority_policy
from cncm.compound_program import CallProgram, CallStep
from cncm.model import TerminalStatus
from cncm.native_model import NativeBudget
from cncm.procedural_substrate import make_candidate


def profile():
    return CompoundProfile(tuple((name,1,digest({'adversarial_simulated_source':name})) for name in SOURCE_FILES),
                           digest(authority_policy()))


def task(name='compound-authority-review'):
    return create_problem(dict(a='2',b='3',c='5',d='7',e='35'),problem_id=name)


def advance_until(machine,kind):
    for _ in range(30):
        proposal=machine.coordinator.next_intent()
        if proposal is not None and proposal.intent_type is kind:return proposal
        assert machine.state.halt_status is TerminalStatus.RUNNING
        machine.advance()
    pytest.fail('requested compound stage not reached')


def execute(machine,proposal):
    return machine.coordinator.execute(enabled_components=(proposal.issuer_subsystem,),
        scheduled_components=(proposal.issuer_subsystem,),intents=(proposal,))


@pytest.mark.parametrize('stage,install,prior_kind,cost',[
    (C.SELECT_PRIMITIVE,C.INSTALL_PRIMITIVE,'PRIMITIVE_SELECTION',(60,10)),
    (C.CONSTRUCT_COMPOUND,C.INSTALL_COMPOUND,'CONSTRUCTION',(288,12)),
])
def test_qualified_authored_candidate_cannot_bypass_current_run_selection_or_construction(stage,install,prior_kind,cost):
    machine=CompoundMachine(profile(),trusted_ingress=())
    machine.start(task())
    advance_until(machine,stage)
    before=machine.state
    artifact=make_candidate() if install is C.INSTALL_PRIMITIVE else CallProgram(
        before.procedural_artifacts[0].artifact_sha256,(CallStep('a','d','e'),CallStep('b','c','r0')))
    assert not any(row.kind==prior_kind for row in before.compound_records)
    proposal=compound_intent(machine.coordinator,install,dict(call_id=before.compound_call.call_id,
        artifact=artifact.to_dict(),qualification_digest=None))
    outcome=execute(machine,proposal)
    assert outcome.rejected_intents, 'a passing qualification does not replace required native construction'
    after=machine.state
    assert after.native_budget==NativeBudget(before.native_budget.instructions_remaining-cost[0],
                                             before.native_budget.checker_calls_remaining-cost[1])
    assert after.procedure_heads==before.procedure_heads
    assert after.compound_head==before.compound_head
    assert after.compound_artifacts==before.compound_artifacts
    assert not any(row.kind==prior_kind for row in after.compound_records)
    result=machine.run()
    assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
    assert not machine.state.rpm_stack


@pytest.fixture
def reusable():
    machine=CompoundMachine(profile(),trusted_ingress=())
    assert machine.run(task('initial-construction')).output=='3'
    return machine


@pytest.mark.parametrize('fault',['foreign_inputs','foreign_call','foreign_program','foreign_primitive','bad_digest','rejected_original_check'])
def test_receiver_rejects_foreign_or_corrupted_checked_receipts_and_preserves_charge(reusable,monkeypatch,fault):
    import cncm.compound_kernel as kernel
    machine=reusable
    machine.start(task('receipt-'+fault))
    proposal=advance_until(machine,C.APPLY_COMPOUND)
    before=machine.state
    real=kernel.check_program_call

    def faulty(program,primitive,inputs,**bindings):
        if fault=='foreign_inputs':
            return real(program,primitive,dict(inputs,e='41'),**bindings)
        if fault=='foreign_call':
            return real(program,primitive,inputs,**(bindings|{'call_id':'other-call'}))
        result=deepcopy(real(program,primitive,inputs,**bindings))
        if fault=='foreign_program':result['program_digest']='f'*64
        elif fault=='foreign_primitive':result['primitive_sha256']='f'*64
        elif fault=='bad_digest':
            result['report_digest']='0'*64
            return result
        elif fault=='rejected_original_check':
            check=result['original_check']
            check['status']='REJECTED'
            check['report_digest']=digest({k:v for k,v in check.items() if k!='report_digest'})
        result['report_digest']=digest({k:v for k,v in result.items() if k!='report_digest'})
        return result

    monkeypatch.setattr(kernel,'check_program_call',faulty)
    outcome=execute(machine,proposal)
    assert outcome.rejected_intents, 'current-call binding and checked subreceipts must be validated before applying output'
    assert machine.state.native_budget==NativeBudget(before.native_budget.instructions_remaining-24,
                                                     before.native_budget.checker_calls_remaining-1)
    assert machine.state.compound_call.output is None
    assert machine.state.compound_call.execution_digest is None
    assert not machine.state.branch_map()['branch-main'].proof_steps
    result=machine.run()
    assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
    assert machine.state.commitment_state.decision_status!='COMMITTED'


def test_memory_receipt_cannot_substitute_another_source_profile(monkeypatch):
    import cncm.compound_kernel as kernel
    machine=CompoundMachine(profile(),trusted_ingress=())
    machine.start(task('foreign-memory-profile'))
    real=kernel.verify_input_resolution

    def faulty(*args,**kwargs):
        receipt=real(*args,**kwargs)
        receipt['source_profile_digest']='f'*64
        receipt['receipt_digest']=digest({k:v for k,v in receipt.items() if k!='receipt_digest'})
        return receipt

    monkeypatch.setattr(kernel,'verify_input_resolution',faulty)
    before=machine.state.native_budget
    proposal=machine.coordinator.next_intent()
    assert execute(machine,proposal).rejected_intents
    assert machine.state.native_budget==NativeBudget(before.instructions_remaining-16,before.checker_calls_remaining-1)
    assert machine.state.memory_resolution_digest is None and machine.state.compound_call is None
    assert machine.run().output is None


def test_constructor_receipt_cannot_claim_a_different_search_prefix(monkeypatch):
    import cncm.compound_kernel as kernel
    machine=CompoundMachine(profile(),trusted_ingress=())
    machine.start(task('foreign-construction-count'))
    proposal=advance_until(machine,C.CONSTRUCT_COMPOUND)
    real=kernel.construct_program

    def faulty(*args,**kwargs):
        artifact,report=real(*args,**kwargs)
        report['candidate_count']=419
        report['report_digest']=digest({k:v for k,v in report.items() if k!='report_digest'})
        return artifact,report

    monkeypatch.setattr(kernel,'construct_program',faulty)
    before=machine.state.native_budget
    assert execute(machine,proposal).rejected_intents
    assert machine.state.native_budget==NativeBudget(before.instructions_remaining-40320,before.checker_calls_remaining-1680)
    assert machine.state.compound_head is None and not machine.state.compound_artifacts
    assert not any(row.kind=='CONSTRUCTION' for row in machine.state.compound_records)
    assert machine.run().output is None and not machine.state.rpm_stack
