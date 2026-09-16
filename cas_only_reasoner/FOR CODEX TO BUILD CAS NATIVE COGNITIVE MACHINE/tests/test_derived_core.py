"""Focused 0.6 authority, work-charge and protected-checker regression cases."""
from unittest.mock import patch
import pytest

from cncm.canonical import canonical_json, digest
from cncm.derived_engine import DerivedMachine
from cncm.derived_model import DerivedDefinition, DerivedResultRef, DerivedIntentType, create_problem
from cncm.derived_profile import DERIVED_WORK_COSTS
from cncm.derived_recovery import recover_derived_journal
from cncm.model import ContractError, TerminalStatus
from cncm.native_model import NativeBudget


def episode(*, budget=NativeBudget(100000,10000)):
    ref = DerivedResultRef('core','y')
    definition = DerivedDefinition('core','y',1,None,'y',tuple(sorted(dict(a='1',b='2',c='1',d='0',e='11').items())))
    problem = create_problem(dict(a='2',b='3',c=ref,d='7',e='35'),definitions=(definition,),budget=budget)
    return definition,problem


def until(machine, kind):
    for _ in range(64):
        proposal = machine.coordinator.next_intent()
        if proposal is not None and proposal.intent_type is kind: return
        machine.advance()
    raise AssertionError('stage not reached')


def test_invalid_generated_candidate_charges_failed_check_and_unwinds():
    definition,problem = episode()
    machine = DerivedMachine(trusted_ingress=(definition.definition_digest,))
    machine.start(problem)
    until(machine,DerivedIntentType.GENERATE_DERIVED)
    with patch('cncm.derived_kernel.generate_candidate',return_value='6'):
        machine.advance()
    before = machine.state.native_budget
    machine.advance()
    cost = DERIVED_WORK_COSTS['CHECK_DERIVED']
    assert machine.state.native_budget.instructions_remaining == before.instructions_remaining-cost[0]
    assert machine.state.native_budget.checker_calls_remaining == before.checker_calls_remaining-cost[1]
    assert machine.state.derived_failure == 'INVALID_FORMAL_PROOF'
    assert not any(r.kind == 'MEMORY' for r in machine.state.derived_records)
    result = machine.run()
    assert result.terminal_status is TerminalStatus.NEEDS_INFORMATION and not machine.state.rpm_stack
    assert result.output is None


def test_insufficient_work_allocation_does_not_invoke_candidate():
    definition,problem = episode(budget=NativeBudget(4111,129))
    machine = DerivedMachine(trusted_ingress=(definition.definition_digest,))
    with patch('cncm.derived_kernel.generate_candidate',side_effect=AssertionError('candidate must not run')):
        result = machine.run(problem)
    assert result.terminal_status is TerminalStatus.BUDGET_EXHAUSTED
    reservations = [r.body_dict() for r in machine.state.derived_records if r.kind == 'WORK_RESERVATION']
    refused = reservations[-1]
    assert refused['failure'] == 'BUDGET_EXHAUSTED'
    assert refused['instructions_allocated'] == refused['checker_calls_allocated'] == 0
    assert refused['before'] == refused['after']


def test_paused_child_recovery_replays_external_genesis_and_continues():
    definition,problem = episode()
    ingress = (definition.definition_digest,)
    machine = DerivedMachine(trusted_ingress=ingress)
    machine.start(problem)
    until(machine,DerivedIntentType.CHECK_DERIVED)
    journal = machine.journal()
    recovered = recover_derived_journal(journal,trusted_genesis=problem,trusted_ingress=ingress,
                                        expected_journal_digest=journal['journal_digest'])
    assert canonical_json(recovered.journal()) == canonical_json(journal)
    # The candidate already exists at this cut. Checking/resume need no new generation.
    with patch('cncm.derived_kernel.generate_candidate',side_effect=AssertionError('new candidate forbidden')):
        result = recovered.run(allow_generation=False)
    assert result.output == '3' and result.terminal_status is TerminalStatus.CONCLUDED
    assert result.evidence['unconditional_world_truth'] is False
    assert result.summary()['derived_failure'] is None
    with pytest.raises(ContractError):
        recover_derived_journal(journal,trusted_genesis=problem,trusted_ingress=(),
                                expected_journal_digest=journal['journal_digest'])


def test_resealed_saved_state_is_not_import_authority():
    definition,problem = episode()
    ingress = (definition.definition_digest,)
    machine = DerivedMachine(trusted_ingress=ingress)
    machine.start(problem)
    machine.advance()
    journal = machine.journal()
    journal['episodes'][0]['final_state']['derived_stored'] = True
    journal['journal_digest'] = digest({k:v for k,v in journal.items() if k != 'journal_digest'})
    with pytest.raises(ContractError):
        recover_derived_journal(journal,trusted_genesis=problem,trusted_ingress=ingress,
                                expected_journal_digest=journal['journal_digest'])


def test_mutable_source_update_input_is_refused():
    with pytest.raises(ContractError):
        create_problem(dict(a='2',b='3',c='5',d='7',e='35'),updates=[])
