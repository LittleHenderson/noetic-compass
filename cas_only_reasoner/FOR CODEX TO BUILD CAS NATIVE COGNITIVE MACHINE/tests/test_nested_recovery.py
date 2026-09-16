"""Semantic recovery of real nested transitions; no tensors or providers.

Most tests use explicitly simulated source identities to isolate the algorithm.
The subprocess test binds actual local source bytes and restores every cut in a
separate process from the process that created the original transitions.
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
from cncm.model import ContractError, Intent, TerminalStatus
from cncm.native_model import NativeBudget
from cncm.nested_engine import NestedMachine
from cncm.nested_model import Equation, NestedIntentType, NestedProblem, create_problem
from cncm.nested_profile import NestedProfile, SOURCE_FILES, authority_policy, load_nested_profile
from cncm.nested_recovery import (_check_json_tree, _decode_intent, _decode_proposal_batch,
    decode_journal, recover_nested_journal, save_nested_journal, verify_nested_journal)

ROOT = Path(__file__).resolve().parents[1]


def simulated_profile():
    return NestedProfile(tuple((name, 1, digest({"simulated_source": name})) for name in SOURCE_FILES),
                         digest(authority_policy()))


def graph_problem(*, leaf_constant="26", name="recovery-graph", max_ticks=128, budget=None):
    # root -> (mid, side), mid -> leaf, side -> the same checked leaf.
    # Unreachable zero-leading equation must never be evaluated.
    return create_problem((Equation("unused", "0", "0", "1"),
        Equation("side", "1", "0", "0", (("leaf", "1"),)),
        Equation("root", "2", "1", "0", (("mid", "1"), ("side", "1"))),
        Equation("leaf", "3", "5", leaf_constant),
        Equation("mid", "1", "0", "1", (("leaf", "2"),))), "root",
        problem_id=name, max_ticks=max_ticks, budget=NativeBudget() if budget is None else budget)


def execute(machine, intent):
    return machine.coordinator.execute(enabled_components=(intent.issuer_subsystem,),
        scheduled_components=(intent.issuer_subsystem,), intents=(intent,))


def recover(journal, problem, profile, anchor=None):
    return recover_nested_journal(journal, trusted_genesis=problem, profile=profile,
        expected_journal_digest=journal["journal_digest"] if anchor is None else anchor)


def reseal(journal):
    journal["journal_digest"] = digest({key: value for key, value in journal.items() if key != "journal_digest"})
    return journal


def prefix_journals(problem, profile, complete):
    machine = NestedMachine(profile)
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
    problem, profile = graph_problem(), simulated_profile()
    machine = NestedMachine(profile)
    result = machine.run(problem)
    assert result.terminal_status is TerminalStatus.CONCLUDED
    assert result.output == "21/2"
    assert {call.variable for call in result.final_state.native_calls} == {"root", "mid", "side", "leaf"}
    assert result.evidence["authorized_nested_transitions"]["INSTALL_PROCEDURE"] == 1
    journal = machine.journal()
    return problem, profile, journal, prefix_journals(problem, profile, journal)


def test_every_graph_and_ordinary_cut_replays_and_finishes_exactly(completed):
    problem, profile, complete, prefixes = completed
    assert max(len(row["episodes"][0]["final_state"]["rpm_stack"]) for row in prefixes) >= 3
    for index, partial in enumerate(prefixes):
        restored = recover(deepcopy(partial), problem, profile)
        assert restored.journal() == partial, index
        coordinator = restored.coordinator
        result = restored.run()
        assert restored.coordinator is coordinator
        assert result.output == "21/2" and result.terminal_status is TerminalStatus.CONCLUDED
        assert restored.journal() == complete, index


def test_reuse_is_new_input_dependent_and_rollback_revokes_only_dispatch(completed):
    problem, profile, journal, _ = completed
    machine = recover(journal, problem, profile)
    original = machine.state
    second = graph_problem(leaf_constant="29", name="new-input-reuse")
    result = machine.run(second, allow_acquisition=False)
    assert result.output == "12" and result.terminal_status is TerminalStatus.CONCLUDED
    assert result.final_state.prior_episode_state_hash == original.state_hash
    assert result.evidence["authorized_nested_transitions"]["SELECT_PROCEDURE"] == 0
    assert result.evidence["authorized_nested_transitions"]["INSTALL_PROCEDURE"] == 0
    assert result.evidence["conservative_policy_work_reserved"] == {"instructions": 120, "checker_calls": 8}
    retained = machine.state.procedural_artifacts
    machine.start(graph_problem(name="rollback-maintenance"))
    machine.rollback()
    assert machine.state.procedure_heads == ()
    assert machine.state.procedural_artifacts == retained
    refused = machine.run(allow_acquisition=False)
    assert refused.output is None and refused.terminal_status is not TerminalStatus.CONCLUDED
    assert not machine.state.rpm_stack
    assert recover(machine.journal(), problem, profile).journal() == machine.journal()


@pytest.mark.parametrize("case", ["zero_leading", "missing", "cycle", "budget"])
def test_partial_failure_recovery_preserves_charges_and_exact_unwind(case):
    if case == "zero_leading":
        packet = create_problem((Equation("x", "0", "1", "2"),), "x")
    elif case == "missing":
        packet = create_problem((Equation("x", "1", "0", "0", (("missing", "1"),)),), "x")
    elif case == "cycle":
        packet = create_problem((Equation("x", "1", "0", "0", (("y", "1"),)),
            Equation("y", "1", "0", "0", (("x", "1"),))), "x")
    else:
        packet = graph_problem(budget=NativeBudget(143, 24))
    profile, machine = simulated_profile(), None
    machine = NestedMachine(profile)
    machine.start(packet)
    while machine.state.halt_status is TerminalStatus.RUNNING:
        machine.advance()
        snapshot = machine.journal()
        restored = recover(snapshot, packet, profile)
        assert restored.journal() == snapshot
        assert restored.state.native_budget == machine.state.native_budget
    assert machine.result().output is None
    assert machine.state.halt_status is not TerminalStatus.CONCLUDED
    assert not machine.state.rpm_stack


@pytest.mark.parametrize("case", ["duplicate", "malformed", "mixed"])
def test_rejected_occurrences_remain_lossless_and_do_not_retry_work(case):
    packet, profile = graph_problem(), simulated_profile()
    machine = NestedMachine(profile)
    machine.start(packet)
    machine.advance()
    intent = machine.coordinator.next_intent()
    if case == "duplicate":
        proposals = (intent, intent)
    elif case == "malformed":
        proposals = (replace(intent, intent_id="invalid-id"),)
    else:
        proposals = (intent, intent, replace(intent, intent_id="invalid-id"), {"not": "intent"})
    outcome = machine.coordinator.execute(enabled_components=(intent.issuer_subsystem,),
        scheduled_components=(intent.issuer_subsystem,), intents=proposals)
    assert outcome.rejected_intents
    journal = machine.journal()
    assert len(journal["episodes"][0]["proposal_batches"][-1]) == len(proposals)
    restored = recover(journal, packet, profile)
    assert restored.journal() == journal
    restored.run(); machine.run()
    assert restored.journal() == machine.journal()
    assert restored.result().output is None


def test_tick_exhaustion_retains_unresolved_stack_and_forbids_budget_restart():
    packet, profile = graph_problem(max_ticks=4), simulated_profile()
    machine = NestedMachine(profile)
    result = machine.run(packet)
    assert result.terminal_status is TerminalStatus.BUDGET_EXHAUSTED
    assert result.final_state.rpm_stack
    journal = machine.journal()
    restored = recover(journal, packet, profile)
    with pytest.raises(ContractError, match="unresolved"):
        restored.start(graph_problem(name="forbidden-budget-reset"))
    assert restored.journal() == journal


@pytest.mark.parametrize("field", ["output", "budget", "frame", "source", "occurrence", "schema", "extra"])
def test_resealed_false_history_is_not_imported(completed, field):
    packet, profile, complete, prefixes = completed
    source = next(row for row in prefixes if len(row["episodes"][0]["final_state"]["rpm_stack"]) >= 2) if field == "frame" else complete
    journal = deepcopy(source)
    state = journal["episodes"][0]["final_state"]
    if field == "output":
        next(call for call in state["native_calls"] if call["variable"] == "root")["output"] = "999"
    elif field == "budget":
        state["native_budget"]["instructions_remaining"] += 1
    elif field == "frame":
        state["rpm_stack"][-1]["frame_id"] = "foreign-frame"
    elif field == "source":
        journal["source_profile"]["source_files"][0]["sha256"] = "f" * 64
    elif field == "occurrence":
        journal["episodes"][0]["proposal_batches"][0][0]["malformed"] = True
    elif field == "schema":
        journal["schema_version"] = "cncm.native-journal/0.2"
    else:
        journal["imported_registry"] = []
    state["state_hash"] = digest({key: value for key, value in state.items() if key not in {"state_hash", "trace_head"}})
    reseal(journal)
    with pytest.raises(ContractError):
        recover(journal, packet, profile)


def test_trusted_complete_anchor_rejects_valid_truncation_and_wrong_genesis(completed):
    packet, profile, complete, prefixes = completed
    with pytest.raises(ContractError):
        recover(prefixes[3], packet, profile, anchor=complete["journal_digest"])
    with pytest.raises(ContractError):
        recover(complete, graph_problem(leaf_constant="29"), profile)
    receipt = verify_nested_journal(complete, trusted_genesis=packet,
        expected_journal_digest=complete["journal_digest"], profile=profile)
    assert receipt["final_state_hash"] == complete["episodes"][-1]["final_state"]["state_hash"]


@pytest.mark.parametrize("anchor", [None, "", "f" * 63, "G" * 64, 3])
def test_external_anchor_is_required(completed, anchor):
    packet, profile, complete, _ = completed
    with pytest.raises(ContractError):
        recover_nested_journal(complete, trusted_genesis=packet, expected_journal_digest=anchor, profile=profile)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff', b'{'])
def test_wire_decoder_refuses_duplicate_keys_nonfinite_and_invalid_json(raw):
    with pytest.raises(ContractError):
        decode_journal(raw)


@pytest.mark.parametrize("value", [3.0, ("tuple",), 1 << 512, {1: "non-string key"}, "\ud800"])
def test_non_json_or_unbounded_python_values_refuse_before_hashing(value):
    with pytest.raises(ContractError):
        _check_json_tree(value)


def test_large_receipt_integers_have_bounded_decode_without_widening_typed_counters(completed):
    for value in ((1 << 511), -(1 << 511), (1 << 512) - 1):
        raw = ('{"receipt_integer":' + str(value) + '}').encode()
        assert decode_journal(raw) == {"receipt_integer": value}
        _check_json_tree(decode_journal(raw))
    for number in (str(1 << 512), "9" * 156, "-" + "9" * 156):
        with pytest.raises(ContractError):
            decode_journal(('{"receipt_integer":' + number + '}').encode())
    packet, profile, complete, _ = completed
    invalid = deepcopy(complete)
    invalid["episodes"][0]["problem"]["reasoning"]["seed"] = 1 << 64
    reseal(invalid)
    with pytest.raises(ContractError):
        recover(invalid, packet, profile)


def test_large_checked_child_output_replays_before_128_bit_composition_refusal():
    denominator, numerator = str(2**127 - 1), str(2**127 - 2)
    packet = create_problem((Equation("child", "1/" + denominator, "0", numerator),
        Equation("parent", "1", "0", "0", (("child", "1"),))), "parent")
    profile, machine = simulated_profile(), None
    machine = NestedMachine(profile)
    machine.start(packet)
    while machine.state.halt_status is TerminalStatus.RUNNING:
        machine.advance()
        journal = machine.journal()
        # Exercise the bytes decoder as well as typed record reconstruction.
        restored = recover(canonical_json(journal).encode(), packet, profile,
                           anchor=journal["journal_digest"])
        assert restored.journal() == journal
    calls = {call.variable: call for call in machine.state.native_calls}
    assert calls["child"].status == "COMPLETE"
    assert int(calls["child"].output).bit_length() == 254
    assert calls["parent"].status == "FAILED" and machine.result().output is None
    reservations = [row.body_dict() for row in machine.state.native_records if row.kind == "WORK_RESERVATION"]
    assert reservations[-1]["operation"] == "BIND_EQUATION"
    assert reservations[-1]["failure"] and reservations[-1]["instructions_allocated"] == 12
    assert not machine.state.rpm_stack


def test_wrong_return_refuses_but_completed_child_can_return_correctly_after_recovery(completed):
    from cncm.nested_kernel import nested_intent
    packet, profile, _, prefixes = completed
    for partial in prefixes:
        machine = recover(partial, packet, profile)
        next_intent = machine.coordinator.next_intent() if machine.state.halt_status is TerminalStatus.RUNNING else None
        if next_intent is not None and next_intent.intent_type is NestedIntentType.RETURN_DEPENDENCY:
            break
    else:
        raise AssertionError("shared-dependency example did not expose a return boundary")
    before = machine.state
    child = next(call for call in before.native_calls if call.call_id == next_intent.mutation_dict()["child_call_id"])
    assert child.status == "COMPLETE"
    wrong = next_intent.mutation_dict()
    wrong["child_call_id"] = "foreign-child"
    rejected = execute(machine, nested_intent(machine.coordinator, NestedIntentType.RETURN_DEPENDENCY, wrong))
    assert rejected.rejected_intents and not rejected.authorized_intents
    assert machine.state.logical_tick == before.logical_tick + 1
    assert machine.state.native_budget == before.native_budget
    assert next(call for call in machine.state.native_calls if call.call_id == child.call_id) == child
    restored = recover(machine.journal(), packet, profile)
    expected = restored.coordinator.next_intent()
    assert expected.intent_type is NestedIntentType.RETURN_DEPENDENCY
    assert expected.mutation_dict()["child_call_id"] == child.call_id
    # A completed checked child remains immutable after a rejected foreign
    # return proposal. The canonical return is deliberately still available.
    assert restored.run().output == "21/2"
    assert machine.run().output == "21/2"
    assert restored.journal() == machine.journal()


def test_recursive_python_input_is_bounded_and_snapshot_copies_are_independent(completed):
    cycle = []; cycle.append(cycle)
    with pytest.raises(ContractError):
        _check_json_tree(cycle)
    packet, profile, complete, _ = completed
    machine = recover(complete, packet, profile)
    exported = machine.journal()
    exported["episodes"][0]["final_state"]["procedure_heads"].clear()
    assert machine.journal() == complete
    assert machine.result().output == "21/2"


def test_no_rollback_mid_call_and_no_acquisition_flag_coercion():
    machine = NestedMachine(simulated_profile())
    machine.start(graph_problem())
    with pytest.raises(ContractError):
        machine.advance(allow_acquisition=1)
    machine.advance()
    before = machine.journal()
    with pytest.raises(ContractError):
        machine.rollback()
    assert machine.journal() == before


def test_actual_source_fresh_process_restores_every_cut_then_reuses_without_acquisition():
    packet, profile = graph_problem(), load_nested_profile()
    machine = NestedMachine(profile)
    machine.run(packet)
    complete = machine.journal()
    prefixes = prefix_journals(packet, profile, complete)
    second = graph_problem(leaf_constant="29", name="fresh-reuse")
    expected_reuse = machine.run(second, allow_acquisition=False).summary()
    expected_reuse_digest = machine.journal()["journal_digest"]
    scratch = ROOT / "records/nested_planning_001/_scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="recovery-", dir=scratch) as directory:
        path = Path(directory) / "journal.json"
        receipt = save_nested_journal(recover(complete, packet, profile), path)
        assert receipt["bytes"] == path.stat().st_size
        assert not list(Path(directory).glob(".nested-journal-*"))
        script = r'''
import importlib.abc,json,os,pathlib,sys
class DenyNeuralAndProviders(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','transformers','boto3','botocore','requests','httpx','openai'}:
            raise AssertionError('forbidden model/provider import: '+fullname)
sys.meta_path.insert(0,DenyNeuralAndProviders())
from cncm.nested_model import NestedProblem
from cncm.nested_recovery import recover_nested_journal
payload=json.loads(sys.stdin.read())
genesis=NestedProblem.from_dict(payload['genesis'])
completed=[]
for prefix in payload['prefixes']:
    machine=recover_nested_journal(prefix,trusted_genesis=genesis,expected_journal_digest=prefix['journal_digest'])
    assert machine.journal()==prefix
    machine.run()
    completed.append(machine.journal()['journal_digest'])
machine=recover_nested_journal(pathlib.Path(payload['journal_path']).read_bytes(),trusted_genesis=genesis,expected_journal_digest=payload['anchor'])
reuse=machine.run(NestedProblem.from_dict(payload['second']),allow_acquisition=False)
print(json.dumps({'pid':os.getpid(),'cuts':completed,'reuse':reuse.summary(),'reuse_digest':machine.journal()['journal_digest']}))
'''
        child = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT, text=True,
            input=json.dumps({"genesis": packet.to_dict(), "prefixes": prefixes,
                "journal_path": str(path), "anchor": complete["journal_digest"], "second": second.to_dict()}),
            capture_output=True, timeout=120, check=False)
        assert child.returncode == 0, child.stderr
        result = json.loads(child.stdout)
        assert result["pid"] != os.getpid()
        assert result["cuts"] == [complete["journal_digest"]] * len(prefixes)
        assert result["reuse"] == expected_reuse
        assert result["reuse_digest"] == expected_reuse_digest
