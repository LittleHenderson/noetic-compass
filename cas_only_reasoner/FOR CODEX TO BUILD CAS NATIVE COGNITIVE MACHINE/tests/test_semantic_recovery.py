"""Lossless semantic replay with caller-held source trust; no world-fact claim.

The main fixtures use explicit simulated source identities. The final subprocess
case binds actual local source bytes and never imports model/provider libraries.
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
from cncm.model import ContractError, TerminalStatus
from cncm.native_model import NativeBudget
from cncm.semantic_engine import SemanticMachine
from cncm.semantic_model import (MemoryRef, SemanticEquation, SemanticIntentType,
    SemanticProblem, SourceStatement, create_problem)
from cncm.semantic_profile import SemanticProfile, SOURCE_FILES, authority_policy, load_semantic_profile
from cncm.semantic_recovery import (_check_json_tree, _decode_proposal_batch,
    decode_journal, recover_semantic_journal, save_semantic_journal, verify_semantic_journal)

ROOT = Path(__file__).resolve().parents[1]


def simulated_profile():
    return SemanticProfile(tuple((name, 1, digest({"simulated_source": name})) for name in SOURCE_FILES),
                           digest(authority_policy()))


def statements():
    rate = SourceStatement("example", "rate", "person", "3", "USER_ATTESTED", "ASSERT", None, "local:authored-example")
    offset = SourceStatement("example", "offset", "fixture", "1", "TEST_FIXTURE", "ASSERT", None, "local:engineering-fixture")
    correction = replace(rate, value="6", previous_digest=rate.statement_digest)
    retraction = replace(correction, value=None, action="RETRACT", previous_digest=correction.statement_digest)
    return rate, offset, correction, retraction


def graph_problem(*, updates=(), name="source-bound-graph", max_ticks=128, budget=None):
    return create_problem((
        SemanticEquation("root", "1", "0", "0", (("leaf", "2"),)),
        SemanticEquation("leaf", MemoryRef("example", "rate"), MemoryRef("example", "offset"), "10"),
        SemanticEquation("unused", MemoryRef("irrelevant", "not-known"), "0", "0")),
        "root", updates=updates, problem_id=name, max_ticks=max_ticks,
        budget=NativeBudget() if budget is None else budget)


def recover(journal, problem, profile, ingress, anchor=None, extensions=()):
    return recover_semantic_journal(journal, trusted_genesis=problem, trusted_ingress=ingress, profile=profile,
        trusted_ingress_extensions=extensions,
        expected_journal_digest=journal["journal_digest"] if anchor is None else anchor)


def reseal(journal):
    journal["journal_digest"] = digest({key: value for key, value in journal.items() if key != "journal_digest"})
    return journal


def prefix_journals(problem, profile, ingress, complete):
    machine = SemanticMachine(profile, trusted_ingress=ingress)
    machine.start(problem)
    prefixes = [machine.journal()]
    episode = complete["episodes"][0]
    for event, batch in zip(episode["trace"], episode["proposal_batches"], strict=True):
        result = machine.coordinator.execute(enabled_components=event["enabled_components"],
            scheduled_components=event["scheduled_components"], intents=_decode_proposal_batch(batch))
        assert result.trace_event.to_dict() == event
        prefixes.append(machine.journal())
    return prefixes


@pytest.fixture(scope="module")
def completed():
    source_rows = statements()
    ingress = tuple(row.statement_digest for row in source_rows[:2])
    packet, profile = graph_problem(updates=source_rows[:2]), simulated_profile()
    machine = SemanticMachine(profile, trusted_ingress=ingress)
    result = machine.run(packet)
    assert result.terminal_status is TerminalStatus.CONCLUDED and result.output == "6"
    assert {call.variable for call in result.final_state.native_calls} == {"root", "leaf"}
    complete = machine.journal()
    return packet, profile, ingress, complete, prefix_journals(packet, profile, ingress, complete)


def test_every_memory_nested_and_ordinary_cut_replays_and_finishes_exactly(completed):
    packet, profile, ingress, complete, prefixes = completed
    assert any(row["episodes"][0]["final_state"]["memory_bindings"] for row in prefixes)
    assert any(row["episodes"][0]["final_state"]["rpm_stack"] for row in prefixes)
    for index, partial in enumerate(prefixes):
        restored = recover(deepcopy(partial), packet, profile, ingress)
        assert restored.journal() == partial, index
        assert restored.run().output == "6"
        assert restored.journal() == complete, index


def test_conditional_result_preserves_real_source_status_and_provenance(completed):
    packet, profile, ingress, complete, _ = completed
    result = recover(complete, packet, profile, ingress).result()
    summary, evidence = result.summary(), result.evidence
    assert summary["conditional_output"] == "6"
    assert "procedure_output" not in summary and "conclusion" not in summary
    assert summary["claim_status"] == evidence["claim_status"] == "CONDITIONAL_ON_RECORDED_SOURCE_BINDINGS"
    assert summary["unconditional_world_truth"] is evidence["unconditional_world_truth"] is False
    assert {status for row in summary["source_binding_statuses"] for status in row["statuses"]} == {"USER_ATTESTED", "TEST_FIXTURE"}
    assert summary["ingress_digest"] == result.final_state.ingress_digest
    provenance = summary["conditional_conclusion"]["provenance"]
    assert any(row["source_type"] == "semantic_resolution" and row["source_id"] == result.final_state.memory_resolution_digest for row in provenance)
    assert evidence["authorized_semantic_transitions"] == {"STORE_SOURCE": 2, "RECALL_MEMORY": 2, "CHECK_MEMORY_RESOLUTION": 1}
    assert evidence["scope"]["external_fact_verification"] is False
    assert evidence["evidence_digest"] == digest({k:v for k,v in evidence.items() if k != "evidence_digest"})


def test_correction_reuse_and_retraction_preserve_history_and_reset_bindings(completed):
    packet, profile, ingress, complete, _ = completed
    machine = recover(complete, packet, profile, ingress)
    before = machine.state
    correction = graph_problem(updates=(statements()[2],), name="corrected-source-example")
    # This digest was not authorized when the first episode ran. Admission
    # happens only through the caller's explicit new external authority.
    addition = (statements()[2].statement_digest,)
    machine.start(correction, additional_trusted_ingress=addition)
    assert machine.state.memory_statements == before.memory_statements
    assert not machine.state.memory_bindings and machine.state.memory_resolution_digest is None
    assert machine.state.prior_episode_state_hash == before.state_hash
    assert machine.state.procedural_artifacts == before.procedural_artifacts
    prefixes = [machine.journal()]
    while machine.state.halt_status is TerminalStatus.RUNNING:
        machine.advance(allow_acquisition=False)
        if not machine.state.native_calls:
            prefixes.append(machine.journal())
    corrected = machine.journal()
    assert machine.result().output == "3"
    assert machine.evidence["authorized_nested_transitions"]["INSTALL_PROCEDURE"] == 0
    assert machine.evidence["authorized_nested_transitions"]["SELECT_PROCEDURE"] == 0
    assert machine.state.memory_statements == before.memory_statements + (statements()[2],)
    for partial in prefixes:
        restored = recover(partial, packet, profile, ingress, extensions=(addition,))
        assert restored.run(allow_acquisition=False).output == "3"
        assert restored.journal() == corrected
    retraction_addition = (statements()[3].statement_digest,)
    machine.run(graph_problem(updates=(statements()[3],), name="retracted-source-example"),
                allow_acquisition=False, additional_trusted_ingress=retraction_addition)
    assert machine.state.memory_failure == "REVOKED" and machine.result().output is None
    assert machine.state.halt_status is TerminalStatus.NEEDS_INFORMATION
    assert not machine.state.native_calls
    assert machine.state.memory_statements[-1] == statements()[3]
    assert recover(machine.journal(), packet, profile, ingress,
        extensions=(addition, retraction_addition)).journal() == machine.journal()


@pytest.mark.parametrize("case", ["missing", "untrusted", "conflict", "insufficient", "stale", "budget"])
def test_memory_failure_replays_with_exact_charges_and_no_nested_execution(case):
    source = statements()[0]
    ref, updates, ingress = MemoryRef("example", "rate"), (source,), (source.statement_digest,)
    budget = NativeBudget()
    if case == "missing":
        updates, ingress = (), ()
    elif case == "untrusted":
        ingress = ()
    elif case == "conflict":
        competing = replace(source, source_id="other-person", value="4")
        updates, ingress = (source, competing), (source.statement_digest, competing.statement_digest)
    elif case == "insufficient":
        ref = replace(ref, evidence_requirement="INDEPENDENTLY_VERIFIED")
    elif case == "stale":
        stale = replace(source, value="4")
        updates, ingress = (source, stale), (source.statement_digest, stale.statement_digest)
    elif case == "budget":
        budget = NativeBudget(11, 1)
    packet = create_problem((SemanticEquation("x", ref, "0", "12"),), "x", updates=updates, budget=budget)
    profile = simulated_profile()
    machine = SemanticMachine(profile, trusted_ingress=ingress)
    result = machine.run(packet)
    assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
    assert not machine.state.native_calls and not machine.state.rpm_stack
    expected = {"missing":"MISSING", "untrusted":"UNTRUSTED_INGRESS", "conflict":"CONFLICT",
                "insufficient":"INSUFFICIENT_EVIDENCE", "stale":"STALE_SOURCE_HEAD", "budget":"BUDGET_EXHAUSTED"}[case]
    assert machine.state.memory_failure == expected
    reservations = [row.body_dict() for row in machine.state.semantic_records if row.kind == "WORK_RESERVATION"]
    assert reservations[-1]["failure"] == expected
    assert reservations[-1]["instructions_allocated"] == (0 if case == "budget" else 12)
    complete = machine.journal()
    for partial in prefix_journals(packet, profile, ingress, complete):
        restored = recover(partial, packet, profile, ingress)
        restored.run()
        assert restored.journal() == complete
        assert restored.state.native_budget == machine.state.native_budget


@pytest.mark.parametrize("case", ["duplicate", "malformed", "mixed", "forged-id"])
def test_original_rejected_memory_occurrences_survive_replay(case):
    packet, profile = graph_problem(updates=statements()[:2]), simulated_profile()
    ingress = tuple(row.statement_digest for row in statements())
    machine = SemanticMachine(profile, trusted_ingress=ingress)
    machine.start(packet)
    intent = machine.coordinator.next_intent()
    assert intent.intent_type is SemanticIntentType.STORE_SOURCE
    proposals = {"duplicate": (intent, intent), "malformed": (replace(intent, intent_id="bad"),),
                "mixed": (intent, intent, replace(intent, intent_id="bad"), {"not":"intent"}),
                "forged-id": (replace(intent, intent_id="intent-" + "f" * 16),)}[case]
    result = machine.coordinator.execute(enabled_components=(intent.issuer_subsystem,),
        scheduled_components=(intent.issuer_subsystem,), intents=proposals)
    assert result.rejected_intents
    journal = machine.journal()
    assert len(journal["episodes"][0]["proposal_batches"][-1]) == len(proposals)
    restored = recover(journal, packet, profile, ingress)
    assert restored.journal() == journal
    restored.run(); machine.run()
    assert restored.journal() == machine.journal()


@pytest.mark.parametrize("case", ["missing", "extra", "replaced", "claimed-in-journal"])
def test_journal_and_statements_cannot_grant_ingress_authority(completed, case):
    packet, profile, ingress, complete, _ = completed
    journal = deepcopy(complete)
    supplied = ingress
    if case == "missing":
        supplied = ingress[1:]
    elif case == "extra":
        supplied = ingress + ("e" * 64,)
    elif case == "replaced":
        supplied = ingress[1:] + ("e" * 64,)
        journal["ingress_digest"] = digest(sorted(supplied))
        reseal(journal)
    else:
        journal["trusted_ingress"] = list(ingress)
        reseal(journal)
    with pytest.raises(ContractError):
        recover(journal, packet, profile, supplied)
    # Order alone is not a new authority set; canonical sorting is deliberate.
    assert recover(complete, packet, profile, tuple(reversed(ingress))).journal() == complete


def test_external_ingress_and_anchor_are_required(completed):
    packet, profile, ingress, complete, prefixes = completed
    with pytest.raises(TypeError):
        recover_semantic_journal(complete, trusted_genesis=packet, expected_journal_digest=complete["journal_digest"], profile=profile)
    with pytest.raises(TypeError):
        SemanticMachine(profile)
    for supplied in (None, list(ingress), ingress + (ingress[0],), ("not-digest",)):
        with pytest.raises(ContractError):
            recover(complete, packet, profile, supplied)
    for anchor in (None, "", "f" * 63, "G" * 64, 1):
        with pytest.raises(ContractError):
            recover_semantic_journal(complete, trusted_genesis=packet, trusted_ingress=ingress, expected_journal_digest=anchor, profile=profile)
    with pytest.raises(ContractError):
        recover(prefixes[2], packet, profile, ingress, anchor=complete["journal_digest"])
    with pytest.raises(ContractError):
        recover(complete, graph_problem(name="different-genesis"), profile, ingress)
    receipt = verify_semantic_journal(complete, trusted_genesis=packet, trusted_ingress=ingress,
        expected_journal_digest=complete["journal_digest"], profile=profile)
    assert receipt["ingress_digest"] == complete["ingress_digest"]
    assert receipt["final_state_hash"] == complete["episodes"][-1]["final_state"]["state_hash"]


def test_new_correction_trust_requires_external_episode_schedule_and_exact_chronology(completed):
    packet, profile, ingress, complete, _ = completed
    machine = recover(complete, packet, profile, ingress)
    addition = (statements()[2].statement_digest,)
    corrected = graph_problem(updates=(statements()[2],), name="newly-authorized-correction")
    assert machine.run(corrected, additional_trusted_ingress=addition, allow_acquisition=False).output == "3"
    # A later task changes no source authority. Its empty schedule suffix can
    # be omitted, without permitting an earlier or later source authorization.
    machine.run(graph_problem(name="same-authority-next-task"), allow_acquisition=False)
    journal = machine.journal()
    assert recover(journal, packet, profile, ingress, extensions=(addition,)).journal() == journal
    assert recover(journal, packet, profile, ingress, extensions=(addition, ())).journal() == journal
    for initial, schedule in ((ingress, ()), (ingress + addition, ()),
            (ingress, ((), addition)), (ingress, (addition, addition)),
            (ingress, (addition, (), ())), (ingress, [addition]),
            (ingress, (list(addition),))):
        with pytest.raises(ContractError):
            recover(journal, packet, profile, initial, extensions=schedule)


def test_ingress_extension_is_append_only_between_terminal_quiescent_episodes(completed):
    packet, profile, ingress, complete, _ = completed
    addition = (statements()[2].statement_digest,)
    machine = SemanticMachine(profile, trusted_ingress=ingress)
    with pytest.raises(ContractError, match="genesis"):
        machine.start(packet, additional_trusted_ingress=addition)
    machine.start(packet)
    before, authority = machine.journal(), machine.trusted_ingress
    with pytest.raises(ContractError, match="finish"):
        machine.start(graph_problem(), additional_trusted_ingress=addition)
    with pytest.raises(ContractError, match="new semantic problem"):
        machine.run(additional_trusted_ingress=addition)
    assert machine.journal() == before and machine.trusted_ingress == authority
    machine = recover(complete, packet, profile, ingress)
    before = machine.journal()
    with pytest.raises(ContractError, match="overlaps"):
        machine.start(graph_problem(), additional_trusted_ingress=(ingress[0],))
    assert machine.journal() == before
    # A valid external statement absent from original authority is still
    # rejected when the caller supplies no extension.
    refused = machine.run(graph_problem(updates=(statements()[2],), name="ungranted-correction"))
    assert refused.output is None and machine.state.memory_failure == "UNTRUSTED_INGRESS"
    assert machine.trusted_ingress == tuple(sorted(ingress))


@pytest.mark.parametrize("field", ["binding", "statement", "resolution", "budget", "failure", "source", "occurrence", "schema", "extra"])
def test_resealed_false_memory_or_trace_is_not_imported(completed, field):
    packet, profile, ingress, complete, _ = completed
    journal = deepcopy(complete)
    state = journal["episodes"][0]["final_state"]
    if field == "binding":
        state["memory_bindings"][0]["value"] = "999"
    elif field == "statement":
        state["memory_statements"][0]["value"] = "999"
    elif field == "resolution":
        state["memory_resolution_digest"] = "f" * 64
    elif field == "budget":
        state["native_budget"]["instructions_remaining"] += 1
    elif field == "failure":
        state["memory_failure"] = "MISSING"
    elif field == "source":
        journal["source_profile"]["source_files"][0]["sha256"] = "f" * 64
    elif field == "occurrence":
        journal["episodes"][0]["proposal_batches"][0][0]["malformed"] = True
    elif field == "schema":
        journal["schema_version"] = "cncm.nested-journal/0.3"
    else:
        journal["imported_memory"] = []
    state["state_hash"] = digest({k:v for k,v in state.items() if k not in {"state_hash", "trace_head"}})
    reseal(journal)
    with pytest.raises(ContractError):
        recover(journal, packet, profile, ingress)


def test_host_rollback_waits_for_resolution_and_preserves_memory(completed):
    packet, profile, ingress, complete, _ = completed
    machine = recover(complete, packet, profile, ingress)
    machine.start(graph_problem(name="rollback-maintenance"))
    before = machine.journal()
    with pytest.raises(ContractError, match="resolution"):
        machine.rollback()
    assert machine.journal() == before
    while machine.state.memory_resolution_digest is None:
        machine.advance()
    sources, bindings = machine.state.memory_statements, machine.state.memory_bindings
    machine.rollback()
    assert not machine.state.procedure_heads
    assert machine.state.memory_statements == sources and machine.state.memory_bindings == bindings
    assert machine.run(allow_acquisition=False).output is None
    assert recover(machine.journal(), packet, profile, ingress).journal() == machine.journal()


def test_memory_tick_budget_and_unresolved_nested_stack_cannot_be_reset():
    profile, ingress = simulated_profile(), tuple(row.statement_digest for row in statements())
    packet = graph_problem(updates=statements()[:2], max_ticks=3)
    machine = SemanticMachine(profile, trusted_ingress=ingress)
    assert machine.run(packet).terminal_status is TerminalStatus.BUDGET_EXHAUSTED
    assert not machine.state.native_calls
    assert recover(machine.journal(), packet, profile, ingress).journal() == machine.journal()
    packet = graph_problem(updates=statements()[:2], max_ticks=9)
    machine = SemanticMachine(profile, trusted_ingress=ingress)
    machine.run(packet)
    assert machine.state.rpm_stack
    restored = recover(machine.journal(), packet, profile, ingress)
    with pytest.raises(ContractError, match="unresolved"):
        restored.start(graph_problem())


def test_strict_raw_decode_bounded_integers_and_no_python_object_coercion():
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff', b'{',
                ('{"x":' + str(1 << 512) + '}').encode(), ('{"x":' + '9' * 156 + '}').encode()):
        with pytest.raises(ContractError):
            decode_journal(raw)
    for value in (3.0, ("tuple",), 1 << 512, {1:"key"}, "\ud800"):
        with pytest.raises(ContractError):
            _check_json_tree(value)
    cycle = []; cycle.append(cycle)
    with pytest.raises(ContractError):
        _check_json_tree(cycle)
    raw = ('{"receipt":' + str((1 << 512) - 1) + '}').encode()
    assert decode_journal(raw) == {"receipt": (1 << 512) - 1}


def test_large_nested_receipt_survives_semantic_replay_then_typed_binding_refusal():
    denominator, numerator = str(2**127 - 1), str(2**127 - 2)
    packet = create_problem((SemanticEquation("child", "1/" + denominator, "0", numerator),
        SemanticEquation("parent", "1", "0", "0", (("child", "1"),))), "parent")
    profile = simulated_profile()
    machine = SemanticMachine(profile, trusted_ingress=())
    machine.start(packet)
    while machine.state.halt_status is TerminalStatus.RUNNING:
        machine.advance()
        journal = machine.journal()
        restored = recover(canonical_json(journal).encode(), packet, profile, (), anchor=journal["journal_digest"])
        assert restored.journal() == journal
    child = next(call for call in machine.state.native_calls if call.variable == "child")
    assert child.status == "COMPLETE" and int(child.output).bit_length() == 254
    assert machine.result().output is None and machine.state.memory_failure is None
    assert not machine.state.rpm_stack


def test_actual_source_fresh_process_restores_all_cuts_then_applies_correction():
    ingress = tuple(row.statement_digest for row in statements()[:2])
    packet, profile = graph_problem(updates=statements()[:2]), load_semantic_profile()
    machine = SemanticMachine(profile, trusted_ingress=ingress)
    machine.run(packet)
    complete = machine.journal()
    prefixes = prefix_journals(packet, profile, ingress, complete)
    correction = graph_problem(updates=(statements()[2],), name="fresh-correction")
    addition = (statements()[2].statement_digest,)
    expected = machine.run(correction, allow_acquisition=False, additional_trusted_ingress=addition).summary()
    expected_digest = machine.journal()["journal_digest"]
    scratch = ROOT / "records/semantic_memory_001/_scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="recovery-", dir=scratch) as directory:
        path = Path(directory) / "journal.json"
        receipt = save_semantic_journal(recover(complete, packet, profile, ingress), path)
        assert receipt["bytes"] == path.stat().st_size
        assert not list(Path(directory).glob(".semantic-journal-*"))
        script = r'''
import importlib.abc,json,os,pathlib,sys
class DenyModelsAndProviders(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','transformers','boto3','botocore','requests','httpx','openai'}:
            raise AssertionError('forbidden model/provider import: '+fullname)
sys.meta_path.insert(0,DenyModelsAndProviders())
from cncm.semantic_model import SemanticProblem
from cncm.semantic_recovery import recover_semantic_journal
payload=json.loads(sys.stdin.read())
genesis=SemanticProblem.from_dict(payload['genesis'])
ingress=tuple(payload['external_ingress'])
completed=[]
for prefix in payload['prefixes']:
    machine=recover_semantic_journal(prefix,trusted_genesis=genesis,trusted_ingress=ingress,expected_journal_digest=prefix['journal_digest'])
    assert machine.journal()==prefix
    machine.run()
    completed.append(machine.journal()['journal_digest'])
machine=recover_semantic_journal(pathlib.Path(payload['journal_path']).read_bytes(),trusted_genesis=genesis,trusted_ingress=ingress,expected_journal_digest=payload['anchor'])
result=machine.run(SemanticProblem.from_dict(payload['correction']),allow_acquisition=False,
    additional_trusted_ingress=tuple(payload['new_external_authority']))
print(json.dumps({'pid':os.getpid(),'cuts':completed,'summary':result.summary(),'journal_digest':machine.journal()['journal_digest']}))
'''
        child = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT, text=True,
            input=json.dumps({"genesis":packet.to_dict(), "prefixes":prefixes, "external_ingress":ingress,
                "journal_path":str(path), "anchor":complete["journal_digest"], "correction":correction.to_dict(),
                "new_external_authority":addition}),
            capture_output=True, timeout=120, check=False)
        assert child.returncode == 0, child.stderr
        result = json.loads(child.stdout)
        assert result["pid"] != os.getpid()
        assert result["cuts"] == [complete["journal_digest"]] * len(prefixes)
        assert result["summary"] == expected
        assert result["journal_digest"] == expected_digest
