"""Exact compound replay, caller-held source trust and protected dependency reuse.

Most tests use explicitly simulated source identities. The subprocess case
requires frozen actual source files and restores acquisition in a new process.
"""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from cncm.canonical import canonical_json, digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_model import CompoundIntentType, CompoundProblem, create_problem
from cncm.compound_profile import CompoundProfile, SOURCE_FILES, authority_policy, load_compound_profile
from cncm.compound_recovery import (_check_json_tree, _decode_intent, _decode_proposal_batch,
    decode_journal, recover_compound_journal, save_compound_journal, verify_compound_journal)
from cncm.model import ContractError, TerminalStatus
from cncm.native_model import NativeBudget
from cncm.semantic_model import MemoryRef, SourceStatement

ROOT = Path(__file__).resolve().parents[1]


def simulated_profile():
    return CompoundProfile(tuple((name, 1, digest({"simulated_source": name})) for name in SOURCE_FILES),
                           digest(authority_policy()))


def source(value="4", previous=None):
    return SourceStatement("example", "offset", "fixture", value, "TEST_FIXTURE", "ASSERT", previous,
                           "local:compound-engineering-fixture")


def problem(*, updates=(), name="compound-source-example", max_ticks=128, budget=None, **options):
    return create_problem({"a":"2", "b":"3", "c":MemoryRef("example", "offset"), "d":"5", "e":"31"},
        updates=updates, problem_id=name, max_ticks=max_ticks,
        budget=NativeBudget(100000,10000) if budget is None else budget, **options)


def recover(journal, genesis, profile, ingress, *, extensions=(), anchor=None):
    return recover_compound_journal(journal, trusted_genesis=genesis, trusted_ingress=ingress, profile=profile,
        trusted_ingress_extensions=extensions,
        expected_journal_digest=journal["journal_digest"] if anchor is None else anchor)


def prefixes(genesis, profile, ingress, complete):
    machine = CompoundMachine(profile, trusted_ingress=ingress)
    machine.start(genesis)
    result = [machine.journal()]
    episode = complete["episodes"][0]
    for event, batch in zip(episode["trace"], episode["proposal_batches"], strict=True):
        outcome = machine.coordinator.execute(enabled_components=event["enabled_components"],
            scheduled_components=event["scheduled_components"], intents=_decode_proposal_batch(batch))
        assert outcome.trace_event.to_dict() == event
        result.append(machine.journal())
    return result


def reseal(journal):
    journal["journal_digest"] = digest({key:value for key,value in journal.items() if key != "journal_digest"})
    return journal


@pytest.fixture(scope="module")
def completed():
    statement, profile = source(), simulated_profile()
    ingress, packet = (statement.statement_digest,), problem(updates=(statement,))
    machine = CompoundMachine(profile, trusted_ingress=ingress)
    result = machine.run(packet)
    assert result.terminal_status is TerminalStatus.CONCLUDED and result.output == "3"
    assert not machine.state.native_calls
    journal = machine.journal()
    return packet, profile, ingress, journal, prefixes(packet, profile, ingress, journal)


def test_every_memory_acquisition_return_and_ordinary_cut_replays_exactly(completed):
    packet, profile, ingress, complete, cuts = completed
    states = [cut["episodes"][0]["final_state"] for cut in cuts]
    assert max(len(state["rpm_stack"]) for state in states) == 2
    assert {frame["kind"] for state in states for frame in state["rpm_stack"]} == {"ACQUIRE_COMPOUND", "ACQUIRE_PRIMITIVE"}
    for index, partial in enumerate(cuts):
        restored = recover(deepcopy(partial), packet, profile, ingress)
        assert restored.journal() == partial, index
        result = restored.run()
        assert result.output == "3" and result.terminal_status is TerminalStatus.CONCLUDED
        assert restored.journal() == complete, index


def test_evidence_binds_constructed_program_primitive_sources_and_conditional_output(completed):
    packet, profile, ingress, complete, _ = completed
    result = recover(complete, packet, profile, ingress).result()
    summary, evidence = result.summary(), result.evidence
    assert summary["conditional_output"] == "3"
    assert summary["unconditional_world_truth"] is evidence["unconditional_world_truth"] is False
    assert summary["claim_status"] == "CONDITIONAL_ON_RECORDED_SOURCE_BINDINGS"
    assert summary["source_binding_statuses"][0]["statuses"] == ["TEST_FIXTURE"]
    assert evidence["compound_head"] == result.final_state.compound_head
    assert evidence["compound_artifacts"] == [row.to_dict() for row in result.final_state.compound_artifacts]
    assert evidence["compound_records"] == [row.to_dict() for row in result.final_state.compound_records]
    assert evidence["primitive_artifact_digests"] == [row.artifact_sha256 for row in result.final_state.procedural_artifacts]
    assert evidence["compound_call"]["output"] == "3" and not evidence["remaining_frames"]
    assert evidence["scope"]["external_fact_verification"] is False
    assert evidence["evidence_digest"] == digest({k:v for k,v in evidence.items() if k != "evidence_digest"})


def test_new_source_correction_and_changed_coefficients_reuse_exact_program(completed):
    packet, profile, ingress, complete, _ = completed
    machine = recover(complete, packet, profile, ingress)
    original = machine.state
    correction = source("7", source().statement_digest)
    additions = (correction.statement_digest,)
    second = problem(updates=(correction,), name="new-correction")
    machine.start(second, additional_trusted_ingress=additions)
    assert machine.state.memory_statements == original.memory_statements
    assert not machine.state.memory_bindings and machine.state.compound_call is None
    partial = machine.journal()
    result = machine.run(allow_acquisition=False)
    assert result.output == "2" and result.terminal_status is TerminalStatus.CONCLUDED
    assert machine.state.compound_artifacts == original.compound_artifacts
    assert machine.state.compound_head == original.compound_head
    assert machine.state.procedural_artifacts == original.procedural_artifacts
    restored = recover(partial, packet, profile, ingress, extensions=(additions,))
    assert restored.run(allow_acquisition=False).output == "2"
    assert restored.journal() == machine.journal()
    later = create_problem({"a":"-2", "b":"5", "c":MemoryRef("example", "offset"), "d":"3", "e":"-23"},
                           problem_id="changed-coefficients")
    result = machine.run(later, allow_acquisition=False)
    assert result.output == "6/5" and result.terminal_status is TerminalStatus.CONCLUDED
    assert machine.state.compound_head == original.compound_head
    assert recover(machine.journal(), packet, profile, ingress, extensions=(additions,)).journal() == machine.journal()
    for external_initial, schedule in ((ingress, ()), (ingress + additions, ()), (ingress, ((), additions))):
        with pytest.raises(ContractError):
            recover(machine.journal(), packet, profile, external_initial, extensions=schedule)


@pytest.mark.parametrize("capability", ["compound", "primitive"])
def test_rollback_preserves_evidence_but_removes_protected_dispatch(completed, capability):
    packet, profile, ingress, complete, _ = completed
    machine = recover(complete, packet, profile, ingress)
    old = machine.state
    machine.start(problem(name="rollback-" + capability))
    before = machine.journal()
    with pytest.raises(ContractError, match="resolution"):
        machine.rollback(capability=capability)
    assert machine.journal() == before
    while machine.state.memory_resolution_digest is None:
        machine.advance()
    machine.rollback(capability=capability)
    assert machine.state.compound_artifacts == old.compound_artifacts
    assert machine.state.procedural_artifacts == old.procedural_artifacts
    assert machine.state.memory_statements == old.memory_statements
    if capability == "compound":
        assert machine.state.compound_head is None
        assert machine.state.procedure_heads == old.procedure_heads
    else:
        assert machine.state.compound_head == old.compound_head
        assert not machine.state.procedure_heads
    result = machine.run(allow_acquisition=False)
    assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
    assert not machine.state.rpm_stack
    assert recover(machine.journal(), packet, profile, ingress).journal() == machine.journal()


@pytest.mark.parametrize("case", ["missing", "untrusted", "budget", "no-acquisition", "search-exhaustion", "zero-leading"])
def test_failures_replay_exact_refusal_costs_and_unwind(case):
    statement, profile = source(), simulated_profile()
    ingress = (statement.statement_digest,)
    packet = problem(updates=(statement,))
    if case == "missing":
        packet, ingress = problem(), ()
    elif case == "untrusted":
        ingress = ()
    elif case == "budget":
        packet = problem(updates=(statement,), budget=NativeBudget(11,1))
    elif case == "search-exhaustion":
        packet = problem(updates=(statement,), construction_limit=1)
    elif case == "zero-leading":
        packet = create_problem({"a":"0", "b":"3", "c":"4", "d":"5", "e":"31"})
    machine = CompoundMachine(profile, trusted_ingress=ingress)
    result = machine.run(packet, allow_acquisition=case != "no-acquisition")
    assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
    assert not machine.state.rpm_stack
    complete = machine.journal()
    for cut in prefixes(packet, profile, ingress, complete):
        restored = recover(cut, packet, profile, ingress)
        restored.run(allow_acquisition=case != "no-acquisition")
        assert restored.journal() == complete
        assert restored.state.native_budget == machine.state.native_budget


@pytest.mark.parametrize("case", ["duplicate", "malformed", "mixed"])
def test_original_rejected_compound_occurrences_remain_lossless(completed, case):
    packet, profile, ingress, _, cuts = completed
    for cut in cuts:
        machine = recover(cut, packet, profile, ingress)
        if machine.state.halt_status is not TerminalStatus.RUNNING:
            continue
        intent = machine.coordinator.next_intent()
        if intent is not None and type(intent.intent_type) is CompoundIntentType:
            break
    else:
        raise AssertionError("fixture never reached compound proposal")
    proposals = {"duplicate":(intent,intent), "malformed":(replace(intent,intent_id="bad"),),
                "mixed":(intent,intent,replace(intent,intent_id="bad"),{"not":"intent"})}[case]
    outcome = machine.coordinator.execute(enabled_components=(intent.issuer_subsystem,),
        scheduled_components=(intent.issuer_subsystem,), intents=proposals)
    assert outcome.rejected_intents
    journal = machine.journal()
    assert len(journal["episodes"][0]["proposal_batches"][-1]) == len(proposals)
    restored = recover(journal, packet, profile, ingress)
    assert restored.journal() == journal
    restored.run(); machine.run()
    assert restored.journal() == machine.journal()


@pytest.mark.parametrize("field", ["output", "head", "budget", "primitive", "ingress", "occurrence", "schema", "extra"])
def test_resealed_state_and_authority_are_not_imported(completed, field):
    packet, profile, ingress, complete, _ = completed
    journal = deepcopy(complete)
    state = journal["episodes"][0]["final_state"]
    if field == "output":
        state["compound_call"]["output"] = "999"
    elif field == "head":
        state["compound_head"] = "f" * 64
    elif field == "budget":
        state["native_budget"]["instructions_remaining"] += 1
    elif field == "primitive":
        state["procedure_heads"] = []
    elif field == "ingress":
        journal["ingress_digest"] = "f" * 64
    elif field == "occurrence":
        journal["episodes"][0]["proposal_batches"][0][0]["malformed"] = True
    elif field == "schema":
        journal["schema_version"] = "cncm.semantic-journal/0.4"
    else:
        journal["trusted_ingress"] = list(ingress)
    state["state_hash"] = digest({key:value for key,value in state.items() if key not in {"state_hash","trace_head"}})
    reseal(journal)
    with pytest.raises(ContractError):
        recover(journal, packet, profile, ingress)


def test_recovery_requires_external_anchor_genesis_ingress_and_rejects_old_nested_intents(completed):
    packet, profile, ingress, complete, cuts = completed
    with pytest.raises(TypeError):
        recover_compound_journal(complete, trusted_genesis=packet, expected_journal_digest=complete["journal_digest"])
    for external in ((), ingress + ("e" * 64,), list(ingress), ingress + ingress):
        with pytest.raises(ContractError):
            recover(complete, packet, profile, external)
    with pytest.raises(ContractError):
        recover(cuts[2], packet, profile, ingress, anchor=complete["journal_digest"])
    with pytest.raises(ContractError):
        recover(complete, problem(name="wrong-genesis"), profile, ingress)
    wire = deepcopy(complete["episodes"][0]["proposal_batches"][0][0]["intent"])
    wire["intent_type"] = "REQUEST_EQUATION"
    with pytest.raises(ContractError, match="unknown recovered intent"):
        _decode_intent(wire)
    receipt = verify_compound_journal(complete, trusted_genesis=packet, trusted_ingress=ingress,
        expected_journal_digest=complete["journal_digest"], profile=profile)
    assert receipt["final_state_hash"] == complete["episodes"][-1]["final_state"]["state_hash"]


def test_strict_json_limits_are_preserved():
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff', ('{"x":' + '9' * 156 + '}').encode()):
        with pytest.raises(ContractError):
            decode_journal(raw)
    for value in (3.0,("tuple",),1 << 512,{1:"key"},"\ud800"):
        with pytest.raises(ContractError):
            _check_json_tree(value)
    maximum=(1 << 512)-1
    assert decode_journal(('{"receipt":' + str(maximum) + '}').encode()) == {"receipt":maximum}


def test_actual_source_fresh_process_recovers_each_cut_then_reuses_program():
    statement, profile = source(), load_compound_profile()
    ingress, packet = (statement.statement_digest,), problem(updates=(statement,))
    machine = CompoundMachine(profile, trusted_ingress=ingress)
    machine.run(packet)
    complete = machine.journal()
    cuts = prefixes(packet, profile, ingress, complete)
    correction = source("7", statement.statement_digest)
    additions = (correction.statement_digest,)
    second = problem(updates=(correction,), name="fresh-compound-correction")
    expected = machine.run(second, additional_trusted_ingress=additions, allow_acquisition=False).summary()
    expected_digest = machine.journal()["journal_digest"]
    scratch = ROOT / "records/compound_procedure_001/_scratch"
    scratch.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="replay-",dir=scratch) as directory:
        path=Path(directory)/"journal.json"
        receipt=save_compound_journal(recover(complete,packet,profile,ingress),path)
        assert receipt["bytes"] == path.stat().st_size
        assert not list(Path(directory).glob(".compound-journal-*"))
        script=r'''
import importlib.abc,json,os,pathlib,sys
class DenyModelsAndProviders(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','transformers','boto3','botocore','requests','httpx','openai'}:
            raise AssertionError('forbidden model/provider import: '+fullname)
sys.meta_path.insert(0,DenyModelsAndProviders())
from cncm.compound_model import CompoundProblem
from cncm.compound_recovery import recover_compound_journal
payload=json.loads(sys.stdin.read())
genesis=CompoundProblem.from_dict(payload['genesis'])
ingress=tuple(payload['external_ingress'])
finished=[]
for cut in payload['cuts']:
    machine=recover_compound_journal(cut,trusted_genesis=genesis,trusted_ingress=ingress,expected_journal_digest=cut['journal_digest'])
    assert machine.journal()==cut
    machine.run()
    finished.append(machine.journal()['journal_digest'])
machine=recover_compound_journal(pathlib.Path(payload['journal_path']).read_bytes(),trusted_genesis=genesis,trusted_ingress=ingress,expected_journal_digest=payload['anchor'])
result=machine.run(CompoundProblem.from_dict(payload['second']),allow_acquisition=False,additional_trusted_ingress=tuple(payload['new_external_authority']))
print(json.dumps({'pid':os.getpid(),'cuts':finished,'summary':result.summary(),'journal_digest':machine.journal()['journal_digest']}))
'''
        child=subprocess.run([sys.executable,"-B","-c",script],cwd=ROOT,text=True,
            input=json.dumps({"genesis":packet.to_dict(),"cuts":cuts,"external_ingress":ingress,
                "journal_path":str(path),"anchor":complete["journal_digest"],"second":second.to_dict(),
                "new_external_authority":additions}),capture_output=True,timeout=240,check=False)
        assert child.returncode==0, child.stderr
        actual=json.loads(child.stdout)
        assert actual["pid"] != os.getpid()
        assert actual["cuts"] == [complete["journal_digest"]] * len(cuts)
        assert actual["summary"] == expected and actual["journal_digest"] == expected_digest
