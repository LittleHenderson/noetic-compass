"""Native journal tests: real transitions, explicitly simulated profiles except
the fresh-process test, which pins the actual local source bytes. No neural work.
"""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from cncm.canonical import canonical_json, digest
from cncm.model import ContractError, Intent, TerminalStatus
from cncm.native_engine import NativeMachine
from cncm.native_kernel import expected_acquisition_frame, native_intent
from cncm.native_model import CAPABILITY, NativeBudget, NativeIntentType, NativeState
from cncm.native_profile import load_native_profile
from cncm.native_recovery import (
    _decode_intent, decode_journal, replay_native_journal, save_native_journal,
)
from cncm.procedural_substrate import make_candidate
from tests.test_native_kernel import native_problem, simulated_profile


ROOT = Path(__file__).resolve().parents[1]


def changed_problem(packet, *, c="29", name="second"):
    return replace(packet, reasoning=replace(packet.reasoning, problem_id=name),
                   call=replace(packet.call, inputs=(("a", "3"), ("b", "5"), ("c", c))))


def reseal_journal(journal):
    journal["journal_digest"] = digest({key: value for key, value in journal.items()
                                         if key != "journal_digest"})
    return journal


def reseal_state(state):
    state["state_hash"] = digest({key: value for key, value in state.items()
                                    if key not in {"state_hash", "trace_head"}})


def replay(journal, problem, profile, *, anchor=None):
    return replay_native_journal(journal, trusted_genesis=problem, profile=profile,
        expected_journal_digest=journal["journal_digest"] if anchor is None else anchor)


def execute(machine, intent):
    return machine.coordinator.execute(enabled_components=(intent.issuer_subsystem,),
        scheduled_components=(intent.issuer_subsystem,), intents=(intent,))


@pytest.fixture(scope="module")
def completed():
    packet, profile = native_problem(), simulated_profile()
    machine = NativeMachine(profile)
    result = machine.run(packet)
    assert result.terminal_status is TerminalStatus.CONCLUDED
    assert result.output == "7"
    assert len(result.trace) == 14
    return packet, profile, machine.journal()


@pytest.fixture(scope="module")
def prefixes(completed):
    packet, profile, journal = completed
    machine = NativeMachine(profile)
    machine.start(packet)
    result = [machine.journal()]
    for wire in journal["episodes"][0]["trace"]:
        outcome = execute(machine, _decode_intent(wire["proposed_intents"][0]))
        assert outcome.trace_event.to_dict() == wire
        result.append(machine.journal())
    return result


@pytest.mark.parametrize("boundary", range(15))
def test_replay_every_native_and_ordinary_boundary_preserves_exact_completion(completed, prefixes, boundary):
    packet, profile, expected = completed
    partial = prefixes[boundary]
    machine = replay(deepcopy(partial), packet, profile)
    assert machine.journal() == partial
    coordinator = machine.coordinator
    result = machine.run()
    assert machine.coordinator is coordinator
    assert result.terminal_status is TerminalStatus.CONCLUDED
    assert result.output == "7"
    assert machine.journal() == expected


def test_linked_episode_reuses_input_dependent_procedure_with_acquisition_disabled(completed):
    packet, profile, journal = completed
    machine = replay(journal, packet, profile)
    first_state, first_coordinator = machine.state, machine.coordinator
    second = changed_problem(packet)
    machine.start(second)
    assert machine.coordinator is not first_coordinator
    assert machine.state.prior_episode_state_hash == first_state.state_hash
    assert machine.state.native_budget == second.budget
    assert machine.state.procedure_heads == first_state.procedure_heads
    assert not machine.state.native_calls
    assert not machine.state.episodic_memory
    result = machine.run(allow_acquisition=False)
    assert result.terminal_status is TerminalStatus.CONCLUDED
    assert result.output == "8"
    assert result.evidence["conservative_policy_work_reserved"] == {"instructions": 6, "checker_calls": 1}
    assert result.evidence["authorized_native_transitions"]["PUSH_ACQUISITION"] == 0
    assert result.evidence["authorized_native_transitions"]["SELECT_PROCEDURE"] == 0
    assert result.evidence["authorized_native_transitions"]["INSTALL_PROCEDURE"] == 0
    assert not any(intent.intent_type.value in {"WRITE_EPISODE", "RECALL"}
                   for event in result.trace for intent in event.proposed_intents)
    assert machine._episodes[0].coordinator is first_coordinator
    restored = replay(machine.journal(), packet, profile)
    assert restored.journal() == machine.journal()
    assert restored.result().to_dict() == result.to_dict()


def test_rollback_revokes_head_then_new_dispatch_refuses_without_acquisition(completed):
    packet, profile, journal = completed
    machine = replay(journal, packet, profile)
    installed = machine.state.procedure_heads
    machine.start(changed_problem(packet, name="rollback-maintenance"))
    same_coordinator = machine.coordinator
    machine.rollback(CAPABILITY)
    assert machine.coordinator is same_coordinator
    assert installed and machine.state.procedure_heads == ()
    assert machine.state.procedural_artifacts  # Retained history is not dispatch authority.
    assert machine.state.native_records[-1].kind == "ROLLBACK"
    assert machine.state.native_calls == ()
    result = machine.run(allow_acquisition=False)
    assert result.terminal_status is TerminalStatus.NEEDS_CAPABILITY
    assert result.output is None
    assert result.evidence["conservative_policy_work_reserved"] == {"instructions": 0, "checker_calls": 0}
    restored = replay(machine.journal(), packet, profile)
    assert restored.journal() == machine.journal()
    # A newly authorized episode can acquire again; rollback never erases history.
    last_state = restored.state
    result = restored.run(changed_problem(packet, c="32", name="reacquire"))
    assert result.terminal_status is TerminalStatus.CONCLUDED and result.output == "9"
    assert result.final_state.prior_episode_state_hash == last_state.state_hash
    assert result.evidence["authorized_native_transitions"]["INSTALL_PROCEDURE"] == 1


def test_rollback_cannot_interrupt_an_existing_call(completed):
    packet, profile, journal = completed
    machine = replay(journal, packet, profile)
    machine.start(changed_problem(packet))
    machine.advance(allow_acquisition=False)
    before = machine.journal()
    with pytest.raises(ContractError, match="before any procedure request"):
        machine.rollback(CAPABILITY)
    assert machine.journal() == before


def test_rejected_install_recovery_returns_failure_without_retry_or_refund():
    packet, profile = native_problem(), simulated_profile()
    machine = NativeMachine(profile)
    machine.start(packet)
    machine.advance()
    machine.advance()
    intent = native_intent(machine.coordinator, NativeIntentType.INSTALL_PROCEDURE, {
        "call_id": packet.call.call_id, "artifact": make_candidate(combine="ADD_EXACT").to_dict(),
        "qualification_digest": None,
    })
    outcome = execute(machine, intent)
    assert outcome.rejected_intents and not outcome.authorized_intents
    spent = machine.state.native_budget
    assert spent == NativeBudget(452, 118)
    journal = machine.journal()
    restored = replay(journal, packet, profile)
    result = restored.run()
    assert result.terminal_status is TerminalStatus.NEEDS_CAPABILITY
    assert result.output is None and not result.final_state.rpm_stack
    assert result.final_state.native_calls[0].status == "FAILED"
    assert result.final_state.native_budget == spent
    kinds = [intent.intent_type.value for event in result.trace for intent in event.proposed_intents]
    assert kinds.count("INSTALL_PROCEDURE") == 1
    assert kinds[-2:] == ["RETURN_ACQUISITION", "HALT"]
    assert "SELECT_PROCEDURE" not in kinds
    assert replay(restored.journal(), packet, profile).journal() == restored.journal()


def test_budget_rejection_recovery_stops_without_selection_work():
    packet = native_problem(budget=NativeBudget(143, 24))
    profile = simulated_profile()
    machine = NativeMachine(profile)
    machine.start(packet)
    machine.advance()
    machine.advance()
    result = execute(machine, native_intent(machine.coordinator, NativeIntentType.SELECT_PROCEDURE,
                                            {"call_id": packet.call.call_id}))
    assert result.rejected_intents
    recovered = replay(machine.journal(), packet, profile)
    outcome = recovered.run()
    assert outcome.terminal_status is TerminalStatus.BUDGET_EXHAUSTED
    assert outcome.final_state.native_budget == packet.budget
    assert not outcome.final_state.rpm_stack
    assert not outcome.final_state.procedural_artifacts


@pytest.mark.parametrize("field", ["output", "budget", "artifact", "proof"])
def test_resealed_forged_final_snapshot_never_installs_or_replaces_replayed_state(completed, field):
    packet, profile, source = completed
    journal = deepcopy(source)
    state = journal["episodes"][0]["final_state"]
    if field == "output":
        state["native_calls"][0]["output"] = "999"
    elif field == "budget":
        state["native_budget"]["instructions_remaining"] += 1
    elif field == "artifact":
        artifact = make_candidate(combine="ADD_EXACT").to_dict()
        state["procedural_artifacts"] = [artifact]
        state["procedure_heads"][0][1] = artifact["artifact_sha256"]
        state["native_calls"][0]["artifact_sha256"] = artifact["artifact_sha256"]
    else:
        proof = state["branch_table"][0]["proof_steps"][0]
        assert proof["operation"] == "CHECKED_PROCEDURE"
        proof["execution_digest"] = "a" * 64
        proof["step_id"] = "native-proof-" + digest({key: value for key, value in proof.items()
                                                      if key != "step_id"})
    reseal_state(state)
    # These are structurally admissible data with recomputed content hashes.
    assert NativeState.from_dict(state).to_dict() == state
    reseal_journal(journal)
    with pytest.raises(ContractError, match="final state does not reconstruct"):
        replay(journal, packet, profile)


def test_rehashed_intent_cannot_substitute_an_uninstalled_artifact(completed):
    packet, profile, source = completed
    journal = deepcopy(source)
    event = journal["episodes"][0]["trace"][5]
    previous = _decode_intent(event["proposed_intents"][0])
    mutation = previous.mutation_dict()
    mutation["artifact_sha256"] = "f" * 64
    changed = Intent.create(intent_type=previous.intent_type, issuer_subsystem=previous.issuer_subsystem,
        required_capability=previous.required_capability, target_scope=previous.target_scope,
        branch_id=previous.branch_id, goal_id=previous.goal_id, precondition=previous.precondition_dict(),
        proposed_mutation=mutation, created_at_tick=previous.created_at_tick, provenance=previous.provenance)
    event["proposed_intents"] = [changed.to_dict()]
    journal["episodes"][0]["proposal_batches"][5][0]["intent"] = changed.to_dict()
    event["authorized_intent_ids"] = [changed.intent_id]
    event["event_hash"] = digest({key: value for key, value in event.items() if key != "event_hash"})
    reseal_journal(journal)
    with pytest.raises(ContractError, match="transition does not reproduce"):
        replay(journal, packet, profile)


@pytest.mark.parametrize("mutation", ["wrong_hash", "trace", "source", "schema", "extra_field", "episode_extra"])
def test_journal_identity_and_exact_schema_refuse_tampering(completed, mutation):
    packet, profile, source = completed
    journal = deepcopy(source)
    if mutation == "wrong_hash":
        journal["journal_digest"] = "0" * 64
    elif mutation == "trace":
        journal["episodes"][0]["trace"][0]["post_state_hash"] = "f" * 64
    elif mutation == "source":
        journal["source_profile"]["source_files"][0]["sha256"] = "f" * 64
        reseal_journal(journal)
    elif mutation == "schema":
        journal["schema_version"] = "cncm.native-journal/0.1"
        reseal_journal(journal)
    elif mutation == "extra_field":
        journal["imported_registry"] = []
        reseal_journal(journal)
    else:
        journal["episodes"][0]["trusted"] = True
        reseal_journal(journal)
    with pytest.raises(ContractError):
        replay(journal, packet, profile)


def test_trusted_anchor_rejects_a_valid_but_truncated_prefix(completed, prefixes):
    packet, profile, complete = completed
    assert prefixes[6]["journal_digest"] != complete["journal_digest"]
    with pytest.raises(ContractError, match="complete native journal digest mismatch"):
        replay(prefixes[6], packet, profile, anchor=complete["journal_digest"])


@pytest.mark.parametrize("anchor", [None, "", "a" * 63, "G" * 64, 3])
def test_external_complete_anchor_is_required(completed, anchor):
    packet, profile, journal = completed
    with pytest.raises(ContractError, match="expected complete journal digest required"):
        replay_native_journal(journal, trusted_genesis=packet, expected_journal_digest=anchor, profile=profile)


def test_wrong_genesis_is_rejected_even_with_valid_journal_hash(completed):
    packet, profile, journal = completed
    with pytest.raises(ContractError, match="genesis differs"):
        replay(journal, changed_problem(packet), profile)


def test_episode_prior_state_link_cannot_be_resealed_away(completed):
    packet, profile, journal = completed
    machine = replay(journal, packet, profile)
    machine.run(changed_problem(packet), allow_acquisition=False)
    forged = machine.journal()
    forged["episodes"][1]["prior_episode_state_hash"] = "f" * 64
    reseal_journal(forged)
    with pytest.raises(ContractError, match="genesis/handoff mismatch"):
        replay(forged, packet, profile)


@pytest.mark.parametrize("raw", [b'{"same":1,"same":2}', b'{"number":NaN}', b'{"number":Infinity}', b'\xff', b'{'])
def test_wire_decoder_rejects_duplicates_nonfinite_and_invalid_json(raw):
    with pytest.raises(ContractError):
        decode_journal(raw)


def test_journal_is_independent_data_not_a_live_mutation_path(completed):
    packet, profile, journal = completed
    machine = replay(journal, packet, profile)
    exported = machine.journal()
    exported["episodes"][0]["final_state"]["procedure_heads"].clear()
    exported["episodes"][0]["problem"]["call"]["inputs"]["a"] = "0"
    assert machine.journal() == journal
    assert machine.result().output == "7"


@pytest.mark.parametrize("case", ["duplicate_native", "malformed_native", "malformed_halt", "mixed"])
def test_rejected_proposal_occurrences_replay_before_failure_continuation(case):
    packet, profile = native_problem(), simulated_profile()
    machine = NativeMachine(profile)
    machine.start(packet)
    machine.advance()
    push = native_intent(machine.coordinator, NativeIntentType.PUSH_ACQUISITION, {
        "call_id": packet.call.call_id,
        "frame": expected_acquisition_frame(machine.state, packet.call).to_dict(),
    })
    halt = machine.coordinator.native_failure_halt("ACQUISITION_DISABLED")
    if case == "duplicate_native":
        proposals = (push, push)
    elif case == "malformed_native":
        proposals = (replace(push, intent_id="invalid-id"),)
    elif case == "malformed_halt":
        proposals = (replace(halt, intent_id="invalid-id"),)
    else:
        proposals = (push, push, replace(halt, intent_id="invalid-id"), {"not": "an intent"})
    outcome = machine.coordinator.execute(enabled_components=("rpm_controller", "halting_controller"),
        scheduled_components=("rpm_controller", "halting_controller"), intents=proposals)
    assert outcome.rejected_intents and not outcome.authorized_intents
    journal = machine.journal()
    batch = journal["episodes"][0]["proposal_batches"][-1]
    assert len(batch) == len(proposals)
    assert any(row["malformed"] for row in batch) is (case != "duplicate_native")
    restored = replay(journal, packet, profile)
    assert restored.journal() == journal
    restored.run()
    machine.run()
    assert restored.journal() == machine.journal()
    assert restored.state.halt_status is TerminalStatus.NEEDS_CAPABILITY
    assert restored.state.native_budget == packet.budget


def test_malformed_final_tick_halt_replays_same_fault():
    packet = native_problem()
    packet = replace(packet, reasoning=replace(packet.reasoning,
        budgets=replace(packet.reasoning.budgets, max_ticks=2)))
    profile = simulated_profile()
    machine = NativeMachine(profile)
    machine.start(packet)
    machine.advance()
    malformed = replace(machine.coordinator.native_failure_halt("ACQUISITION_DISABLED"),
                        intent_id="invalid-id")
    outcome = execute(machine, malformed)
    assert outcome.rejected_intents
    assert machine.state.halt_status is TerminalStatus.FAULT
    restored = replay(machine.journal(), packet, profile)
    assert restored.journal() == machine.journal()
    assert restored.run().terminal_status is TerminalStatus.FAULT


@pytest.mark.parametrize("case", ["missing_batch", "forged_malformed_flag", "extra_occurrence"])
def test_resealed_proposal_occurrence_tampering_is_rejected(completed, case):
    packet, profile, source = completed
    journal = deepcopy(source)
    batches = journal["episodes"][0]["proposal_batches"]
    if case == "missing_batch":
        batches.pop()
    elif case == "forged_malformed_flag":
        batches[0][0]["malformed"] = True
    else:
        batches[0].append(deepcopy(batches[0][0]))
    reseal_journal(journal)
    with pytest.raises(ContractError):
        replay(journal, packet, profile)


@pytest.mark.parametrize("case", ["float", "tuple", "integer", "cycle", "nonstring_key"])
def test_non_json_python_journal_values_are_rejected_before_hashing(completed, case):
    packet, profile, source = completed
    journal = deepcopy(source)
    if case == "float":
        journal["episodes"][0]["problem"]["reasoning"]["seed"] = 20260916.0
    elif case == "tuple":
        journal["episodes"] = tuple(journal["episodes"])
    elif case == "integer":
        journal["episodes"][0]["problem"]["reasoning"]["seed"] = 1 << 64
    elif case == "cycle":
        journal["cycle"] = journal
    else:
        journal[1] = "coercible key"
    with pytest.raises(ContractError):
        replay(journal, packet, profile)


def test_actual_source_fresh_process_replay_reuse_and_rollback(tmp_path):
    packet, profile = native_problem(), load_native_profile()
    machine = NativeMachine(profile)
    machine.run(packet)
    path = tmp_path / "native-journal.json"
    receipt = save_native_journal(machine, path)
    assert receipt["bytes"] == path.stat().st_size
    assert receipt["journal_digest"] == machine.journal()["journal_digest"]
    assert not list(tmp_path.glob(".native-journal-*"))
    second = changed_problem(packet)
    third = changed_problem(packet, c="32", name="fresh-rollback")
    expected_second = machine.run(second, allow_acquisition=False)
    expected_reuse_digest = machine.journal()["journal_digest"]
    machine.start(third)
    machine.rollback(CAPABILITY)
    expected_third = machine.run(allow_acquisition=False)
    expected_rollback_digest = machine.journal()["journal_digest"]
    script = r'''
import importlib.abc, json, os, pathlib, sys
class DenyNeuralAndProviderImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'transformers', 'boto3', 'botocore', 'requests', 'httpx', 'openai'}:
            raise AssertionError('forbidden model/provider import: ' + fullname)
sys.meta_path.insert(0, DenyNeuralAndProviderImports())
from cncm.native_model import NativeProblem, CAPABILITY
from cncm.native_recovery import replay_native_journal
payload=json.loads(sys.stdin.read())
machine=replay_native_journal(pathlib.Path(payload['journal_path']).read_bytes(),
    trusted_genesis=NativeProblem.from_dict(payload['genesis']),
    expected_journal_digest=payload['anchor'])
second=machine.run(NativeProblem.from_dict(payload['second']),allow_acquisition=False)
reuse_digest=machine.journal()['journal_digest']
machine.start(NativeProblem.from_dict(payload['third']))
machine.rollback(CAPABILITY)
third=machine.run(allow_acquisition=False)
print(json.dumps({'pid':os.getpid(),'second':second.summary(),'reuse_digest':reuse_digest,
    'third':third.summary(),'rollback_digest':machine.journal()['journal_digest']}))
'''
    child = subprocess.run([sys.executable, "-c", script], cwd=ROOT, text=True,
        input=json.dumps({"journal_path": str(path), "genesis": packet.to_dict(),
            "anchor": receipt["journal_digest"], "second": second.to_dict(), "third": third.to_dict()}),
        capture_output=True, timeout=45, check=False)
    assert child.returncode == 0, child.stderr
    result = json.loads(child.stdout)
    assert result["pid"] != os.getpid()
    assert result["second"] == expected_second.summary()
    assert result["reuse_digest"] == expected_reuse_digest
    assert result["third"] == expected_third.summary()
    assert result["rollback_digest"] == expected_rollback_digest
