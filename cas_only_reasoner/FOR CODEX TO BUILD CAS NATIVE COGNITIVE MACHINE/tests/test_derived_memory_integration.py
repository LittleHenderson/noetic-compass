"""End-to-end contracts for native checked-result reuse.

These tests are engineering cases; source assertions remain conditional.
"""
import pytest

from cncm.canonical import canonical_json
from cncm.derived_engine import DerivedMachine
from cncm.derived_model import DerivedDefinition, DerivedResultRef, DerivedIntentType, create_problem
from cncm.model import ContractError, TerminalStatus
from cncm.semantic_model import MemoryRef, SourceStatement


def source(value="11", previous=None, key="rhs", source_id="fixture", scope="integration"):
    return SourceStatement(scope,key,source_id,value,"TEST_FIXTURE","ASSERT",previous,
                           "engineering-fixture:derived-integration")


def reference(key="remembered-y", scope="integration"):
    return DerivedResultRef(scope=scope,key=key)


def definition(ref=None, rhs=None, revision=1, supersedes=None):
    ref = reference() if ref is None else ref
    parameters = dict(a="1",b="2",c="1",d="0",
                      e=MemoryRef("integration","rhs") if rhs is None else rhs)
    return DerivedDefinition(scope=ref.scope,key=ref.key,revision=revision,
                             supersedes=supersedes,variable="y",
                             parameters=tuple(sorted(parameters.items())))


def parent(ref=None, updates=(), definitions=(), target="35", name="derived-parent", **options):
    return create_problem(dict(a="2",b="3",c=reference() if ref is None else ref,d="7",e=target),
                          variable="x",updates=updates,definitions=definitions,
                          problem_id=name,**options)


def test_missing_formal_value_resumes_parent_and_later_changes_a_new_derivation():
    original=source()
    equation=definition()
    machine=DerivedMachine(trusted_ingress=(original.statement_digest,equation.definition_digest))
    result=machine.run(parent(updates=(original,),definitions=(equation,)))
    assert result.terminal_status is TerminalStatus.CONCLUDED and result.output=="3"
    before=canonical_json(machine.journal()["episodes"][0])
    result=machine.run(parent(target="41",name="later-derived-parent"),
                       allow_generation=False,allow_acquisition=False)
    assert result.terminal_status is TerminalStatus.CONCLUDED and result.output=="4"
    assert canonical_json(machine.journal()["episodes"][0])==before
    assert not machine.state.rpm_stack
    assert machine.state.commitment_state.decision_status=="COMMITTED"


def test_source_correction_refuses_stale_reuse_then_allows_checked_refresh():
    original=source()
    equation=definition()
    machine=DerivedMachine(trusted_ingress=(original.statement_digest,equation.definition_digest))
    assert machine.run(parent(updates=(original,),definitions=(equation,))).output=="3"
    correction=source("17",original.statement_digest)
    refused=machine.run(parent(updates=(correction,),name="stale-parent"),
                        additional_trusted_ingress=(correction.statement_digest,),
                        allow_generation=False,allow_acquisition=False)
    assert refused.output is None and refused.terminal_status is not TerminalStatus.CONCLUDED
    assert machine.state.commitment_state.decision_status!="COMMITTED"
    renewed=machine.run(parent(name="renewed-parent"),allow_acquisition=False)
    assert renewed.output=="2" and renewed.terminal_status is TerminalStatus.CONCLUDED
    reused=machine.run(parent(target="41",name="renewed-later"),allow_generation=False,
                       allow_acquisition=False)
    assert reused.output=="3" and not machine.state.rpm_stack


def test_committed_producer_is_reused_as_input_not_copied_as_consumer_answer():
    offset=source("5",key="offset")
    remembered=reference("producer-x")
    saved_consumer=reference("consumer-y")
    producer_inputs=dict(a="2",b="3",c=MemoryRef("integration","offset"),d="7",e="35")
    consumer_inputs=dict(a=remembered,b="2",c="1",d="4",e="28")
    producer_definition=DerivedDefinition(remembered.scope,remembered.key,1,None,"x",
                                         tuple(sorted(producer_inputs.items())))
    consumer_definition=DerivedDefinition(saved_consumer.scope,saved_consumer.key,1,None,"y",
                                         tuple(sorted(consumer_inputs.items())))
    machine=DerivedMachine(trusted_ingress=(offset.statement_digest,
        producer_definition.definition_digest,consumer_definition.definition_digest))
    producer=create_problem(producer_inputs, updates=(offset,),
                            definitions=(producer_definition,consumer_definition),
                            store_result=remembered,problem_id="producer")
    result=machine.run(producer)
    assert result.output=="3" and result.terminal_status is TerminalStatus.CONCLUDED
    consumer=create_problem(consumer_inputs,variable="y",
                            store_result=saved_consumer,problem_id="consumer")
    result=machine.run(consumer,allow_generation=False,allow_acquisition=False)
    assert result.output=="7/2" and result.terminal_status is TerminalStatus.CONCLUDED
    correction=source("8",offset.statement_digest,key="offset")
    dependent=create_problem(dict(a=saved_consumer,b="1",c="0",d="0",e="7"),
                             updates=(correction,),variable="z",problem_id="transitive-stale")
    refusal=machine.run(dependent,additional_trusted_ingress=(correction.statement_digest,),
                        allow_generation=False,allow_acquisition=False)
    assert refusal.output is None and refusal.terminal_status is not TerminalStatus.CONCLUDED
    assert machine.state.commitment_state.decision_status!="COMMITTED"
    refresh=create_problem(dict(a="2",b="3",c=MemoryRef("integration","offset"),d="7",e="35"),
                           store_result=remembered,problem_id="producer-refresh")
    assert machine.run(refresh,allow_generation=False,allow_acquisition=False).output=="2"
    # The caller still gives no remembered scalar. Exact source/record lineage
    # must decide which checked producer is current.
    final=create_problem(dict(a=remembered,b="2",c="1",d="4",e="28"),variable="y",
                         problem_id="consumer-refresh")
    assert machine.run(final,allow_generation=False,allow_acquisition=False).output=="11/2"


def test_pending_derived_child_cannot_start_a_fresh_budget_episode():
    original=source()
    equation=definition()
    machine=DerivedMachine(trusted_ingress=(original.statement_digest,equation.definition_digest))
    machine.start(parent(updates=(original,),definitions=(equation,)))
    for _ in range(32):
        if machine.state.rpm_stack:
            break
        machine.advance()
    assert machine.state.rpm_stack
    before=machine.state.to_dict()
    with pytest.raises(ContractError):
        machine.start(parent(name="illegal-new-episode"))
    assert machine.state.to_dict()==before


def test_generation_disabled_after_pause_prevents_a_new_child_candidate():
    original=source()
    equation=definition()
    machine=DerivedMachine(trusted_ingress=(original.statement_digest,equation.definition_digest))
    machine.start(parent(updates=(original,),definitions=(equation,)))
    for _ in range(32):
        proposal=machine.coordinator.next_intent()
        if proposal is not None and proposal.intent_type is DerivedIntentType.GENERATE_DERIVED:
            break
        machine.advance()
    assert proposal.intent_type is DerivedIntentType.GENERATE_DERIVED
    assert machine.state.rpm_stack
    result=machine.run(allow_generation=False,allow_acquisition=False)
    assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
    assert not machine.state.rpm_stack
    assert not any(row.kind=="CANDIDATE" for row in machine.state.derived_records)
