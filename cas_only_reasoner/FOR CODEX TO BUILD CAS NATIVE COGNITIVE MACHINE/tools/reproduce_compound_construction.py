"""Actual-source acceptance for bounded compound construction and replay.

All examples are authored engineering fixtures. Arithmetic outputs remain
conditional on their original parameters and admitted source statements.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FORBIDDEN = frozenset({"torch", "transformers", "boto3", "botocore", "requests", "httpx", "openai"})


class DenyModelsAndProviders:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise AssertionError("forbidden model/provider import: " + fullname)


sys.meta_path.insert(0, DenyModelsAndProviders())
from cncm.canonical import canonical_json, digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_model import CompoundProblem, create_problem
from cncm.compound_profile import load_compound_profile
from cncm.compound_recovery import recover_compound_journal, _decode_proposal_batch
from cncm.model import TerminalStatus
from cncm.native_model import NativeBudget
from cncm.semantic_model import MemoryRef, SourceStatement
from cncm.semantic_profile import load_semantic_profile

SEMANTIC_PROFILE = "6a27f94656b45a4c4732d1a185844517f382390d6e3d1ce4259b63861badcecf"
ACQUISITION_FUNCTIONS = ("construct_program", "qualify_program", "select_finite_candidate", "qualify_procedure")
ACQUISITION_INTENTS = ("CONSTRUCT_COMPOUND", "INSTALL_COMPOUND", "SELECT_PRIMITIVE", "INSTALL_PRIMITIVE")


def write(path, value):
    raw = value if type(value) is bytes else (canonical_json(value) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)


def read(path):
    return json.loads(path.read_bytes())


def statement(value="5", previous=None):
    return SourceStatement("project", "offset", "fixture", value, "TEST_FIXTURE", "ASSERT", previous,
                           "engineering-fixture:compound-construction-001")


def task(*, updates=(), parameters=None, name="compound-baseline", **options):
    if parameters is None:
        parameters = {"a":"2", "b":"3", "c":MemoryRef("project", "offset"), "d":"7", "e":"35"}
    return create_problem(parameters, updates=updates, problem_id=name, **options)


def literal_task(**options):
    return task(parameters={"a":"2", "b":"3", "c":"5", "d":"7", "e":"35"}, **options)


def restore(journal, genesis, ingress, anchor, extensions=()):
    return recover_compound_journal(journal, trusted_genesis=genesis, trusted_ingress=ingress,
        expected_journal_digest=anchor, trusted_ingress_extensions=extensions)


def save_machine(output, stem, machine):
    journal = machine.journal()
    write(output / (stem + "_journal.json"), journal)
    write(output / (stem + "_anchor.json"), {"journal_digest":journal["journal_digest"]})
    return journal


def no_acquisition(result):
    counts = result.evidence["authorized_compound_transitions"]
    assert all(counts[kind] == 0 for kind in ACQUISITION_INTENTS)


def child(output):
    genesis = CompoundProblem.from_dict(read(output / "genesis.json"))
    custody = read(output / "external_ingress.json")
    ingress = tuple(custody["initial_statement_digests"])
    extensions = tuple(tuple(row) for row in custody["extensions"])
    complete = read(output / "correction_journal.json")
    anchor = read(output / "correction_anchor.json")["journal_digest"]
    original = restore(complete, genesis, ingress, anchor, extensions)
    profile = original.profile
    replay = CompoundMachine(profile, trusted_ingress=ingress)
    cuts = []
    for episode_index, episode in enumerate(complete["episodes"]):
        replay.start(CompoundProblem.from_dict(episode["problem"]),
            additional_trusted_ingress=() if episode_index == 0 else extensions[episode_index - 1])
        body = {key:value for key,value in complete.items() if key not in {"episodes", "journal_digest"}}
        body["episodes"] = complete["episodes"][:episode_index + 1]
        body["ingress_digest"] = episode["ingress_digest"]
        expected = {**body, "journal_digest":digest(body)}
        for index in range(len(episode["trace"]) + 1):
            if index:
                event = episode["trace"][index - 1]
                outcome = replay.coordinator.execute(enabled_components=event["enabled_components"],
                    scheduled_components=event["scheduled_components"],
                    intents=_decode_proposal_batch(episode["proposal_batches"][index - 1]))
                assert outcome.trace_event.to_dict() == event
            prefix = replay.journal()
            recovered = restore(prefix, genesis, ingress, prefix["journal_digest"], extensions[:episode_index])
            assert recovered.journal() == prefix
            result = recovered.run()
            assert result.terminal_status is TerminalStatus.CONCLUDED and recovered.journal() == expected
            cuts.append({"episode":episode_index, "cut":index, "prefix_digest":prefix["journal_digest"],
                "completed_digest":expected["journal_digest"], "conditional_output":result.output,
                "depth":len(replay.state.rpm_stack), "frame_kinds":[f.kind for f in replay.state.rpm_stack],
                "state_hash":replay.state.state_hash, "remaining_policy_budget":replay.state.native_budget.to_dict()})
    assert max(row["depth"] for row in cuts) == 2
    assert {kind for row in cuts for kind in row["frame_kinds"]} == {"ACQUIRE_COMPOUND", "ACQUIRE_PRIMITIVE"}
    write(output / "all_cut_replay.json", {"cuts":cuts, "all_cuts_exact":True, "pid":os.getpid()})
    failure_cuts = []
    for name, case in read(output / "failure_inputs.json").items():
        packet = CompoundProblem.from_dict(case["problem"])
        saved = read(output / (name + "_journal.json"))
        failed_anchor = read(output / (name + "_anchor.json"))["journal_digest"]
        verified = restore(saved, packet, (), failed_anchor)
        assert verified.state.compound_call.failure == case["failure"]
        failed_replay = CompoundMachine(profile, trusted_ingress=())
        failed_replay.start(packet)
        episode = saved["episodes"][0]
        for index in range(len(episode["trace"]) + 1):
            if index:
                event = episode["trace"][index - 1]
                outcome = failed_replay.coordinator.execute(enabled_components=event["enabled_components"],
                    scheduled_components=event["scheduled_components"],
                    intents=_decode_proposal_batch(episode["proposal_batches"][index - 1]))
                assert outcome.trace_event.to_dict() == event
            prefix = failed_replay.journal()
            recovered = restore(prefix, packet, (), prefix["journal_digest"])
            assert recovered.journal() == prefix
            result = recovered.run(allow_acquisition=case["allow_acquisition"])
            assert recovered.journal() == saved and result.output is None
            assert recovered.state.native_budget == verified.state.native_budget
            failure_cuts.append({"case":name, "cut":index, "prefix_digest":prefix["journal_digest"],
                "completed_digest":failed_anchor, "failure":recovered.state.compound_call.failure,
                "remaining_policy_budget":recovered.state.native_budget.to_dict()})
    write(output / "failure_cut_replay.json", {"cuts":failure_cuts, "all_cuts_exact":True, "pid":os.getpid()})
    # Reconstruct both independent rollback branches before disabling the actual
    # acquisition aliases. No historical reconstruction runs under these patches.
    rollback_branches = {kind:restore(complete, genesis, ingress, anchor, extensions)
                         for kind in ("compound", "primitive")}
    import cncm.compound_kernel as kernel
    attempted = []
    def forbidden(name):
        def reject(*args, **kwargs):
            attempted.append(name)
            raise AssertionError("new task attempted disabled acquisition: " + name)
        return reject
    for name in ACQUISITION_FUNCTIONS:
        setattr(kernel, name, forbidden(name))
    pinned = original.state.compound_head
    programs, primitives = original.state.compound_artifacts, original.state.procedural_artifacts
    cases = (
        ("literal_reuse", task(name="new-literal-parameters", parameters={"a":"-2", "b":"5", "c":"7", "d":"3", "e":"-23"}), "6/5"),
        ("fractional_reuse", task(name="new-fractional-parameters", parameters={
            "a":"1/2", "b":"-3/2", "c":"2/3", "d":"-1/4", "e":"7/8"}), "-19/18"),
        ("memory_reuse", task(name="later-omitted-source-value", parameters={
            "a":"2", "b":"3", "c":MemoryRef("project", "offset"), "d":"7", "e":"41"}), "3"),
    )
    reuse = {}
    for name, packet, expected_output in cases:
        if name == "memory_reuse":
            assert packet.updates == () and type(packet.parameters_dict()["c"]) is MemoryRef
        result = original.run(packet, allow_acquisition=False)
        assert result.output == expected_output and result.terminal_status is TerminalStatus.CONCLUDED
        no_acquisition(result)
        assert original.state.compound_head == pinned and original.state.compound_artifacts == programs
        assert original.state.procedural_artifacts == primitives
        work = result.evidence["conservative_policy_work_reserved"]
        assert work == ({"instructions":52, "checker_calls":3} if name == "memory_reuse" else
                        {"instructions":40, "checker_calls":2})
        write(output / (name + "_problem.json"), packet.to_dict())
        write(output / (name + "_result.json"), result.to_dict())
        reuse[name] = {"conditional_output":result.output, "terminal_status":result.terminal_status.value,
                      "policy_work":work, "compound_head":pinned}
    final = save_machine(output, "reuse", original)
    rollbacks = {}
    for capability, machine in rollback_branches.items():
        before = machine.state
        machine.start(task(name="rollback-" + capability))
        while machine.state.memory_resolution_digest is None:
            machine.advance()
        machine.rollback(capability=capability)
        assert machine.state.compound_artifacts == before.compound_artifacts
        assert machine.state.procedural_artifacts == before.procedural_artifacts
        assert machine.state.memory_statements == before.memory_statements
        if capability == "compound":
            assert machine.state.compound_head is None and machine.state.procedure_heads == before.procedure_heads
        else:
            assert machine.state.compound_head == before.compound_head and not machine.state.procedure_heads
        result = machine.run(allow_acquisition=False)
        assert result.output is None and result.terminal_status is TerminalStatus.NEEDS_CAPABILITY
        assert not machine.state.rpm_stack
        assert result.evidence["authorized_compound_transitions"]["APPLY_COMPOUND"] == 0
        no_acquisition(result)
        saved = save_machine(output, "rollback_" + capability, machine)
        write(output / ("rollback_" + capability + "_result.json"), result.to_dict())
        rollbacks[capability] = {"journal_digest":saved["journal_digest"],
            "terminal_status":result.terminal_status.value, "conditional_output":result.output,
            "failure":machine.state.compound_call.failure, "policy_work":result.evidence["conservative_policy_work_reserved"]}
    assert attempted == []
    assert load_compound_profile().profile_digest == profile.profile_digest
    receipt = {"pid":os.getpid(), "source_profile_digest":profile.profile_digest,
        "all_cuts_exact":True, "cut_count":len(cuts) + len(failure_cuts),
        "primary_cut_count":len(cuts), "failure_cut_count":len(failure_cuts), "maximum_depth":2,
        "reuse":reuse, "rollbacks":rollbacks, "reuse_journal_digest":final["journal_digest"],
        "disabled_functions":list(ACQUISITION_FUNCTIONS), "disabled_function_attempts":attempted,
        "acquisition_disabled_after_replay":True, "actual_call_checking_remained_enabled":True,
        "model_or_provider_work":False, "factual_status":"NOT_INDEPENDENTLY_VERIFIED", "source_status":"TEST_FIXTURE"}
    write(output / "fresh_process_receipt.json", receipt)
    print(canonical_json({"pid":os.getpid(), "cuts":len(cuts) + len(failure_cuts), "status":"FRESH_PROCESS_REPLAY_AND_REUSE_PASSED"}))


def reproduce(output):
    output.mkdir(parents=True, exist_ok=False)
    profile = load_compound_profile()
    assert load_semantic_profile().profile_digest == SEMANTIC_PROFILE
    old = statement()
    correction = statement("8", old.statement_digest)
    ingress, extensions = (old.statement_digest,), ((correction.statement_digest,),)
    genesis = task(updates=(old,))
    write(output / "genesis.json", genesis.to_dict())
    write(output / "external_ingress.json", {"initial_statement_digests":list(ingress),
        "extensions":[list(row) for row in extensions],
        "custody":"Authored engineering-fixture anchors supplied outside journals; not real user authorization."})
    write(output / "source_profile.json", profile.to_dict())
    machine = CompoundMachine(profile, trusted_ingress=ingress)
    baseline = machine.run(genesis)
    assert baseline.output == "3" and baseline.terminal_status is TerminalStatus.CONCLUDED
    assert baseline.evidence["conservative_policy_work_reserved"] == {"instructions":40876, "checker_calls":1730}
    baseline_journal = save_machine(output, "baseline", machine)
    write(output / "baseline_result.json", baseline.to_dict())
    program = machine.state.compound_artifacts[0]
    assert [(step.a_ref, step.b_ref, step.c_ref) for step in program.steps] == [("a","d","e"), ("b","c","r0")]
    assert program.primitive_sha256 == machine.state.procedural_artifacts[0].artifact_sha256
    construction = next(row.body_dict()["report"] for row in machine.state.compound_records if row.kind == "CONSTRUCTION")
    assert construction["candidate_count"] == 420 and len(construction["survivor_digests"]) == 1
    write(output / "constructed_program.json", program.to_dict())
    write(output / "construction_report.json", construction)
    assert correction.statement_digest not in machine.trusted_ingress
    corrected = machine.run(task(updates=(correction,), name="new-authorized-correction"),
        additional_trusted_ingress=extensions[0], allow_acquisition=False)
    assert corrected.output == "2" and corrected.terminal_status is TerminalStatus.CONCLUDED
    no_acquisition(corrected)
    correction_journal = save_machine(output, "correction", machine)
    write(output / "correction_result.json", corrected.to_dict())
    control = restore(baseline_journal, genesis, ingress, baseline_journal["journal_digest"])
    control_packet = task(name="uncorrected-source-control", parameters={
        "a":"2", "b":"3", "c":MemoryRef("project", "offset"), "d":"7", "e":"41"})
    control_result = control.run(control_packet, allow_acquisition=False)
    assert control_result.output == "4" and control_result.terminal_status is TerminalStatus.CONCLUDED
    no_acquisition(control_result)
    write(output / "uncorrected_control_result.json", control_result.to_dict())
    save_machine(output, "uncorrected_control", control)
    failures = {}
    cases = {
        "budget":(literal_task(name="budget-refusal", budget=NativeBudget(300,100)), True, "BUDGET_EXHAUSTED"),
        "depth":(literal_task(name="depth-refusal", rpm_depth_limit=1), True, "DEPTH_EXHAUSTED"),
        "prefix":(literal_task(name="prefix-refusal", construction_limit=1), True, "SEARCH_EXHAUSTED"),
        "domain":(task(name="domain-refusal", parameters={"a":"0","b":"3","c":"5","d":"7","e":"35"}), True, "DOMAIN_REJECTED"),
        "disabled":(literal_task(name="disabled-refusal"), False, "ACQUISITION_DISABLED"),
    }
    failure_inputs = {}
    for name, (packet, allow, expected_failure) in cases.items():
        failed = CompoundMachine(profile, trusted_ingress=())
        result = failed.run(packet, allow_acquisition=allow)
        assert result.output is None and result.terminal_status is not TerminalStatus.CONCLUDED
        assert failed.state.compound_call.failure == expected_failure
        assert not failed.state.rpm_stack and failed.state.compound_head is None
        assert not failed.state.branch_map()["branch-main"].proof_steps
        saved = save_machine(output, name, failed)
        restored = restore(saved, packet, (), saved["journal_digest"])
        assert restored.journal() == saved and restored.state.native_budget == failed.state.native_budget
        write(output / (name + "_result.json"), result.to_dict())
        failure_inputs[name] = {"problem":packet.to_dict(), "allow_acquisition":allow, "failure":expected_failure}
        failures[name] = {"status":result.terminal_status.value, "failure":expected_failure,
            "journal_digest":saved["journal_digest"], "policy_work":result.evidence["conservative_policy_work_reserved"]}
    write(output / "failure_inputs.json", failure_inputs)
    worker = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--child", str(output)],
        cwd=ROOT, capture_output=True, text=True, timeout=360)
    write(output / "subprocess_exit.json", {"exit_code":worker.returncode, "stdout":worker.stdout, "stderr":worker.stderr})
    if worker.returncode:
        raise RuntimeError("fresh-process compound acceptance failed; see subprocess_exit.json")
    receipt = read(output / "fresh_process_receipt.json")
    assert receipt["pid"] != os.getpid()
    assert receipt["source_profile_digest"] == profile.profile_digest
    later_problem = CompoundProblem.from_dict(read(output / "memory_reuse_problem.json"))
    assert later_problem.parameters == control_packet.parameters and later_problem.updates == ()
    assert control_result.evidence["conservative_policy_work_reserved"] == receipt["reuse"]["memory_reuse"]["policy_work"]
    for stem in ("reuse", "rollback_compound", "rollback_primitive"):
        anchor = read(output / (stem + "_anchor.json"))["journal_digest"]
        restored = restore((output / (stem + "_journal.json")).read_bytes(), genesis, ingress, anchor, extensions)
        assert restored.journal()["journal_digest"] == anchor
        assert restored.state.halt_status is (TerminalStatus.CONCLUDED if stem == "reuse" else TerminalStatus.NEEDS_CAPABILITY)
    assert load_compound_profile().profile_digest == profile.profile_digest, "source changed during acceptance"
    assert load_semantic_profile().profile_digest == SEMANTIC_PROFILE
    assert not any(name.split(".")[0] in FORBIDDEN for name in sys.modules)
    files = [{"path":path.name,"bytes":path.stat().st_size,"sha256":sha256(path.read_bytes()).hexdigest()}
             for path in sorted(output.iterdir()) if path.is_file()]
    result = {"schema_version":"cncm.compound-acceptance/0.5",
        "status":"BOUNDED_COMPOUND_CONSTRUCTION_ACCEPTANCE_PASSED",
        "source_profile_digest":profile.profile_digest, "prior_semantic_profile_digest":SEMANTIC_PROFILE,
        "producer_pid":os.getpid(), "fresh_process_pid":receipt["pid"],
        "fresh_process_cuts":receipt["cut_count"],
        "primary_cut_count":receipt["primary_cut_count"], "failure_cut_count":receipt["failure_cut_count"],
        "maximum_acquisition_depth":receipt["maximum_depth"],
        "candidate_count":construction["candidate_count"], "unique_survivors":len(construction["survivor_digests"]),
        "constructed_program_digest":program.program_digest, "pinned_primitive_sha256":program.primitive_sha256,
        "baseline_policy_work":baseline.evidence["conservative_policy_work_reserved"],
        "uncorrected_later_control_output":control_result.output, "corrected_later_output":receipt["reuse"]["memory_reuse"]["conditional_output"],
        "later_source_scalar_omitted":True, "correction_authorized_after_initial_episode":True,
        "reuse":receipt["reuse"], "rollbacks":receipt["rollbacks"], "typed_failure_examples":failures,
        "baseline_journal_digest":baseline_journal["journal_digest"],
        "correction_journal_digest":correction_journal["journal_digest"],
        "reuse_journal_digest":receipt["reuse_journal_digest"],
        "reproducer_sha256":sha256(Path(__file__).read_bytes()).hexdigest(), "files":files,
        "scope":"Bounded public-engineering-panel construction and conditional fixture reuse; not general learning, independently verified world truth or complete CNCM.",
        "model_or_provider_work":False, "full_goal_complete":False}
    write(output / "receipt.json", result)
    print(canonical_json({key:result[key] for key in ("status","source_profile_digest","fresh_process_cuts","constructed_program_digest")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--output",type=Path)
    modes.add_argument("--child",type=Path)
    args = parser.parse_args()
    target = (args.output or args.child).resolve()
    if not target.is_relative_to(ROOT / "records/compound_procedure_001"):
        raise SystemExit("acceptance output must remain in compound_procedure_001 records")
    try:
        child(target) if args.child else reproduce(target)
    except BaseException as error:
        if target.is_dir():
            failure_path = target / ("child_failure.json" if args.child else "producer_failure.json")
            if not failure_path.exists():
                write(failure_path, {"pid":os.getpid(),"type":type(error).__name__,"error":str(error),
                                    "traceback":traceback.format_exc()})
        raise
