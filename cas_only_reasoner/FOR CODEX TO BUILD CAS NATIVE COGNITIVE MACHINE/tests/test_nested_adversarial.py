"""Independent attacks on the nested kernel; fixture profiles are not releases."""

import pytest

from cncm.canonical import digest
from cncm.kernel import COMMITMENT_GATES
from cncm.model import ContractError, Intent, IntentType, TerminalStatus
from cncm.native_model import NativeBudget
from cncm.nested_engine import NestedMachine
from cncm.nested_model import Equation, NestedIntentType as Kind, create_problem
from cncm.nested_profile import (NestedProfile, SOURCE_FILES, NESTED_AUTHORITIES,
                                 authority_policy)
from cncm.procedural_substrate import make_candidate


@pytest.fixture
def profile():
    # Stable source identities for unit tests only, not actual-source evidence.
    return NestedProfile(tuple((name, 1, "0" * 64) for name in SOURCE_FILES), digest(authority_policy()))


def leaf(problem_id="leaf", **options):
    return create_problem((Equation("x", "2", "1", "7"),), "x", problem_id=problem_id, **options)


def chain(problem_id="chain", **options):
    return create_problem((Equation("x", "2", "1", rhs_terms=(("y", "1"),)),
                           Equation("y", "2", "1", "15")), "x", problem_id=problem_id, **options)


def start(profile, problem=None):
    machine = NestedMachine(profile)
    machine.start(problem or leaf())
    return machine


def call(machine, variable):
    return next(row for row in machine.state.native_calls if row.variable == variable)


def drive(machine, condition):
    for _ in range(120):
        if condition(machine):
            return machine
        assert machine.state.halt_status is TerminalStatus.RUNNING
        machine.advance()
    pytest.fail("test could not reach its explicit state condition")


def acquisition(machine):
    return drive(machine, lambda m: bool(m.state.rpm_stack)
                 and m.state.rpm_stack[-1].kind == "PROCEDURE_ACQUISITION")


def intent(machine, kind, mutation, **changes):
    # Construct attack payloads directly, independently of _expected/next_intent.
    issuer, capability = NESTED_AUTHORITIES[kind.value]
    scope = ("rpm_stack" if kind in {Kind.PUSH_DEPENDENCY, Kind.RETURN_DEPENDENCY,
                                     Kind.PUSH_PROCEDURE, Kind.RETURN_PROCEDURE}
             else "procedural_memory" if kind in {Kind.SELECT_PROCEDURE, Kind.INSTALL_PROCEDURE,
                                                  Kind.ROLLBACK_PROCEDURE} else "nested_calls")
    arguments = dict(intent_type=kind, issuer_subsystem=issuer, required_capability=capability,
                     target_scope=scope, branch_id=None if kind is Kind.ROLLBACK_PROCEDURE else "branch-main",
                     goal_id=machine.state.active_goal_id, precondition={"state_hash": machine.state.state_hash},
                     proposed_mutation=mutation, created_at_tick=machine.state.logical_tick, provenance=())
    arguments.update(changes)
    return Intent.create(**arguments)


def ordinary(machine, kind, issuer, capability, scope, mutation, branch_id=None):
    return Intent.create(intent_type=kind, issuer_subsystem=issuer, required_capability=capability,
                         target_scope=scope, branch_id=branch_id, goal_id=machine.state.active_goal_id,
                         precondition={"state_hash": machine.state.state_hash}, proposed_mutation=mutation,
                         created_at_tick=machine.state.logical_tick, provenance=())


def execute(machine, proposal, occurrences=1):
    return machine.coordinator.execute(enabled_components=(proposal.issuer_subsystem,),
                                       scheduled_components=(proposal.issuer_subsystem,),
                                       intents=(proposal,) * occurrences)


def rejected(machine, proposal, *, charged=(0, 0), occurrences=1):
    before = machine.state
    outcome = execute(machine, proposal, occurrences)
    assert outcome.trace_event.rejected_intents
    assert not outcome.trace_event.authorized_intent_ids
    assert machine.state.native_budget.instructions_remaining == before.native_budget.instructions_remaining - charged[0]
    assert machine.state.native_budget.checker_calls_remaining == before.native_budget.checker_calls_remaining - charged[1]
    assert machine.state.procedure_heads == before.procedure_heads
    assert machine.state.native_calls == before.native_calls
    assert machine.state.rpm_stack == before.rpm_stack
    assert machine.state.branch_table == before.branch_table
    assert machine.state.commitment_state == before.commitment_state
    assert machine.state.halt_status is TerminalStatus.RUNNING
    return outcome


@pytest.mark.parametrize("changes", [
    {"issuer_subsystem": "untrusted_generator"},
    {"required_capability": "request_equation"},
    {"target_scope": "nested_calls"},
    {"branch_id": "branch-other"},
    {"goal_id": "goal-other"},
])
def test_validly_hashed_wrong_install_authority_never_runs_checker(profile, monkeypatch, changes):
    machine = acquisition(start(profile))
    checked = []
    monkeypatch.setattr("cncm.nested_kernel.qualify_procedure", lambda *_: checked.append(True))
    proposal = intent(machine, Kind.INSTALL_PROCEDURE,
                      {"call_id": call(machine, "x").call_id, "artifact": make_candidate().to_dict(),
                       "qualification_digest": None}, **changes)
    rejected(machine, proposal)
    assert checked == []


@pytest.mark.parametrize("attack", ["wrong_formula", "forged_qualification"])
def test_direct_install_bad_candidate_or_qualification_is_checked_charged_and_not_installed(profile, attack):
    machine = acquisition(start(profile))
    artifact = make_candidate(combine="ADD_EXACT") if attack == "wrong_formula" else make_candidate()
    proposal = intent(machine, Kind.INSTALL_PROCEDURE,
                      {"call_id": call(machine, "x").call_id, "artifact": artifact.to_dict(),
                       "qualification_digest": "f" * 64 if attack == "forged_qualification" else None})
    rejected(machine, proposal, charged=(60, 10))
    reservation = machine.state.native_records[-1]
    assert reservation.kind == "WORK_RESERVATION"
    assert reservation.body_dict()["failure"]
    assert reservation.body_dict()["failed_report"] is not None
    assert not machine.state.procedural_artifacts
    result = machine.run()
    assert result.terminal_status is TerminalStatus.NEEDS_CAPABILITY
    assert result.output is None and not result.final_state.rpm_stack
    assert not any(row.kind == "INSTALLATION" for row in result.final_state.native_records)


def test_good_direct_artifact_can_only_install_after_independent_qualification(profile):
    machine = acquisition(start(profile))
    proposal = intent(machine, Kind.INSTALL_PROCEDURE,
                      {"call_id": call(machine, "x").call_id, "artifact": make_candidate().to_dict(),
                       "qualification_digest": None})
    outcome = execute(machine, proposal)
    assert outcome.trace_event.authorized_intent_ids == (proposal.intent_id,)
    assert any(row.kind == "QUALIFICATION" for row in machine.state.native_records)
    assert machine.run().output == "3"


@pytest.mark.parametrize("occurrences", [2, 3])
def test_duplicate_work_proposals_do_not_run_or_charge_checker(profile, monkeypatch, occurrences):
    machine = acquisition(start(profile))
    checked = []
    monkeypatch.setattr("cncm.nested_kernel.select_finite_candidate", lambda: checked.append(True))
    proposal = intent(machine, Kind.SELECT_PROCEDURE, {"call_id": call(machine, "x").call_id})
    rejected(machine, proposal, occurrences=occurrences)
    assert checked == []


def test_stale_work_envelope_does_not_execute_checker(profile, monkeypatch):
    machine = acquisition(start(profile))
    proposal = intent(machine, Kind.INSTALL_PROCEDURE,
                      {"call_id": call(machine, "x").call_id, "artifact": make_candidate().to_dict(),
                       "qualification_digest": None})
    machine.advance()  # Real selection changes state and tick.
    checked = []
    monkeypatch.setattr("cncm.nested_kernel.qualify_procedure", lambda *_: checked.append(True))
    rejected(machine, proposal)
    assert checked == []


@pytest.mark.parametrize("change", ["artifact", "inputs", "call"])
def test_apply_must_match_pinned_current_call(profile, monkeypatch, change):
    machine = drive(start(profile), lambda m: bool(m.state.native_calls) and call(m, "x").status == "READY")
    current = call(machine, "x")
    mutation = {"call_id": current.call_id, "artifact_sha256": current.artifact_sha256,
                "inputs_digest": current.inputs_digest}
    mutation[{"artifact": "artifact_sha256", "inputs": "inputs_digest", "call": "call_id"}[change]] = (
        "other-call" if change == "call" else "f" * 64)
    checked = []
    monkeypatch.setattr("cncm.nested_kernel.check_procedure_call", lambda *_args, **_kwargs: checked.append(True))
    rejected(machine, intent(machine, Kind.APPLY_EQUATION, mutation))
    assert checked == []


def test_previous_episode_child_execution_cannot_ground_current_parent(profile):
    machine = start(profile, chain("before"))
    assert machine.run().output == "3"
    previous = call(machine, "y").execution_digest
    machine.start(chain("after"))
    drive(machine, lambda m: len(m.state.native_calls) == 2 and call(m, "x").status == "OPEN"
          and call(m, "y").status == "COMPLETE" and not m.state.rpm_stack)
    assert previous != call(machine, "y").execution_digest
    proposal = intent(machine, Kind.BIND_EQUATION,
                      {"call_id": call(machine, "x").call_id, "dependency_records": [["y", previous]],
                       "expected_head": dict(machine.state.procedure_heads)["cncm.solve-linear/0.1"]})
    rejected(machine, proposal)


@pytest.mark.parametrize("attack", ["omitted", "wrong_digest", "wrong_variable", "duplicate"])
def test_dependency_bind_cannot_omit_replace_or_duplicate_checked_reference(profile, attack):
    machine = drive(start(profile, chain()), lambda m: len(m.state.native_calls) == 2
                    and call(m, "x").status == "OPEN" and call(m, "y").status == "COMPLETE"
                    and not m.state.rpm_stack)
    key = call(machine, "y").execution_digest
    records = {"omitted": [], "wrong_digest": [["y", "f" * 64]],
               "wrong_variable": [["z", key]], "duplicate": [["y", key], ["y", key]]}[attack]
    rejected(machine, intent(machine, Kind.BIND_EQUATION,
                             {"call_id": call(machine, "x").call_id, "dependency_records": records,
                              "expected_head": dict(machine.state.procedure_heads)["cncm.solve-linear/0.1"]}))


@pytest.mark.parametrize("attack", ["parent", "child", "frame", "execution", "success"])
def test_child_return_cannot_change_saved_parent_or_result(profile, attack):
    machine = drive(start(profile, chain()), lambda m: len(m.state.native_calls) == 2
                    and call(m, "y").status == "COMPLETE" and bool(m.state.rpm_stack))
    frame = machine.state.rpm_stack[-1]
    current = call(machine, "y")
    mutation = {"call_id": call(machine, "x").call_id, "frame_id": frame.frame_id,
                "child_call_id": current.call_id, "execution_digest": current.execution_digest,
                "success": True, "failure": None}
    key = {"parent": "call_id", "child": "child_call_id", "frame": "frame_id",
           "execution": "execution_digest", "success": "success"}[attack]
    mutation[key] = False if attack == "success" else "f" * 64 if attack == "execution" else "forged-reference"
    rejected(machine, intent(machine, Kind.RETURN_DEPENDENCY, mutation))


def test_parent_goal_cannot_issue_child_acquisition_work(profile, monkeypatch):
    machine = acquisition(start(profile, chain()))
    assert machine.state.active_goal_id != machine.problem.reasoning.goal_id
    checked = []
    monkeypatch.setattr("cncm.nested_kernel.select_finite_candidate", lambda: checked.append(True))
    rejected(machine, intent(machine, Kind.SELECT_PROCEDURE,
                             {"call_id": call(machine, "y").call_id},
                             goal_id=machine.problem.reasoning.goal_id))
    assert checked == []


@pytest.mark.parametrize("stage", ["boot", "child", "root_complete"])
def test_conclusion_halt_cannot_skip_commitment(profile, stage):
    machine = start(profile, chain())
    if stage == "child":
        acquisition(machine)
    elif stage == "root_complete":
        drive(machine, lambda m: bool(m.state.native_calls) and call(m, "x").status == "COMPLETE")
    proposal = ordinary(machine, IntentType.HALT, "halting_controller", "request_typed_halt", "halt_status",
                        {"status": "CONCLUDED", "lacunae": [], "diagnostics": []})
    rejected(machine, proposal)


def test_forged_failure_halt_requires_real_failed_root_and_unwound_stack(profile):
    machine = acquisition(start(profile, chain()))
    proposal = ordinary(machine, IntentType.HALT, "halting_controller", "request_typed_halt", "halt_status",
                        {"status": "NEEDS_CAPABILITY", "lacunae": ["x"],
                         "diagnostics": ["nested_planning_failure", "TRANSITION_REJECTED"]})
    rejected(machine, proposal)


@pytest.mark.parametrize("stage", ["child", "root_complete"])
def test_true_gate_flags_do_not_create_commitment_authority(profile, stage):
    machine = start(profile, chain())
    if stage == "child":
        acquisition(machine)
    else:
        drive(machine, lambda m: bool(m.state.native_calls) and call(m, "x").status == "COMPLETE")
    proposal = ordinary(machine, IntentType.DECISION_COMMIT, "commitment_latch", "request_decision_commit",
                        "commitment_state", {"conclusion": machine.problem.reasoning.query.to_dict(),
                                             "gate_results": {name: True for name in COMMITMENT_GATES}}, "branch-main")
    rejected(machine, proposal)


def test_active_call_cannot_roll_back_its_pinned_procedure(profile):
    machine = start(profile)
    machine.run()
    machine.start(leaf("second"))
    proposal = machine.coordinator.rollback_intent()
    machine.advance()
    # Rebuild with current envelope; the forbidden condition is an active call,
    # not merely the stale state hash of the first rollback proposal.
    rejected(machine, intent(machine, Kind.ROLLBACK_PROCEDURE, proposal.mutation_dict()))


def test_shared_dependency_executes_once_and_all_parents_bind_same_record(profile):
    problem = create_problem((Equation("x", "1", "0", rhs_terms=(("a", "1"), ("b", "1"))),
                              Equation("a", "1", "0", rhs_terms=(("c", "2"),)),
                              Equation("b", "1", "0", rhs_terms=(("c", "3"),)),
                              Equation("c", "2", "1", "7")), "x")
    machine = start(profile, problem)
    result = machine.run()
    assert result.terminal_status is TerminalStatus.CONCLUDED and result.output == "15"
    executions = [row.body_dict() for row in machine.state.native_records if row.kind == "EXECUTION"]
    assert len(executions) == 4
    assert [row["variable"] for row in executions].count("c") == 1
    key = call(machine, "c").execution_digest
    assert call(machine, "a").dependency_records == (("c", key),)
    assert call(machine, "b").dependency_records == (("c", key),)
    assert machine.state.native_budget == NativeBudget(512 - 204 - 4 * 30, 128 - 34 - 4 * 2)


@pytest.mark.parametrize("two_nodes", [False, True])
def test_cycle_failure_unwinds_without_a_checked_answer(profile, two_nodes):
    equations = (Equation("x", "1", "0", rhs_terms=(("y", "1"),)),
                  Equation("y", "1", "0", rhs_terms=(("x", "1"),))) if two_nodes else (
                     Equation("x", "1", "0", rhs_terms=(("x", "1"),)),)
    machine = start(profile, create_problem(equations, "x"))
    result = machine.run()
    assert result.terminal_status is TerminalStatus.LOOP_LIMIT_REACHED
    assert result.output is None and not machine.state.rpm_stack
    assert not any(row.kind == "EXECUTION" for row in machine.state.native_records)
    assert machine.state.commitment_state.decision_status == "UNCOMMITTED"


def test_depth_counts_dependency_and_procedure_frames(profile):
    machine = start(profile, chain(rpm_depth_limit=1))
    result = machine.run()
    assert result.terminal_status is TerminalStatus.NEEDS_CAPABILITY
    assert result.output is None and not machine.state.rpm_stack
    assert not machine.state.procedural_artifacts
    failures = [row.body_dict()["reason"] for row in machine.state.native_records if row.kind == "FAILURE"]
    assert "DEPTH_EXHAUSTED" in failures


def test_overlarge_child_output_cannot_become_a_composition_input(profile):
    largest = (1 << 128) - 1
    problem = create_problem((Equation("x", "1", "0", rhs_terms=(("y", "1"),)),
                              Equation("y", f"1/{largest}", "0", "2")), "x")
    machine = start(profile, problem)
    result = machine.run()
    assert call(machine, "y").status == "COMPLETE"
    assert call(machine, "y").output == str(2 * largest)
    assert result.output is None and result.terminal_status is TerminalStatus.NEEDS_CAPABILITY
    failed = [row.body_dict() for row in machine.state.native_records if row.kind == "WORK_RESERVATION"
              and row.body_dict()["failure"]]
    assert len(failed) == 1 and failed[0]["operation"] == "BIND_EQUATION"
    assert failed[0]["instructions_allocated"] == 12
    assert not any(row.kind == "EXECUTION" and row.body_dict()["variable"] == "x"
                   for row in machine.state.native_records)


def test_exhausted_work_budget_is_refused_before_qualification(profile, monkeypatch):
    machine = acquisition(start(profile, leaf(budget=NativeBudget(50, 128))))
    checked = []
    monkeypatch.setattr("cncm.nested_kernel.qualify_procedure", lambda *_: checked.append(True))
    rejected(machine, intent(machine, Kind.INSTALL_PROCEDURE,
                             {"call_id": call(machine, "x").call_id, "artifact": make_candidate().to_dict(),
                              "qualification_digest": None}))
    assert checked == []
    result = machine.run()
    assert result.terminal_status is TerminalStatus.BUDGET_EXHAUSTED
    assert not machine.state.rpm_stack and result.output is None


def test_suspended_parent_branch_cannot_receive_ordinary_decomposition(profile):
    machine = acquisition(start(profile, chain()))
    branch = machine.state.branch_map()["branch-main"]
    decomposition = machine.coordinator._decompose_query(machine.state, branch)
    proposal = ordinary(machine, IntentType.RECORD_DECOMPOSITION, "reasoning_engine", "decompose",
                        "branch:branch-main", {"decomposition": decomposition.to_dict()}, "branch-main")
    rejected(machine, proposal)


def test_parent_cannot_apply_while_child_is_active(profile):
    machine = acquisition(start(profile, chain()))
    rejected(machine, intent(machine, Kind.APPLY_EQUATION,
                             {"call_id": call(machine, "x").call_id,
                              "artifact_sha256": make_candidate().artifact_sha256,
                              "inputs_digest": "f" * 64}))


def test_post_selection_artifact_substitution_is_rejected_before_qualification(profile, monkeypatch):
    machine = acquisition(start(profile))
    machine.advance()  # A selected proposal is now pinned by a SELECTION record.
    checked = []
    monkeypatch.setattr("cncm.nested_kernel.qualify_procedure", lambda *_: checked.append(True))
    rejected(machine, intent(machine, Kind.INSTALL_PROCEDURE,
                             {"call_id": call(machine, "x").call_id,
                              "artifact": make_candidate(combine="ADD_EXACT").to_dict(),
                              "qualification_digest": None}))
    assert checked == []


def test_fault_injected_wrong_grounding_is_caught_by_independent_equation_check(profile, monkeypatch):
    # Explicit internal fault injection, not a claim that callers may replace
    # the trusted module. Atomic math can validate a wrongly grounded equation;
    # the independent context check must still reject its output.
    machine = drive(start(profile), lambda m: bool(m.state.native_calls) and call(m, "x").status == "OPEN")
    with monkeypatch.context() as patch:
        patch.setattr("cncm.nested_kernel.grounding_inputs", lambda *_: {"a": "2", "b": "1", "c": "9"})
        machine.advance()
    drive(machine, lambda m: call(m, "x").status == "READY")
    current = call(machine, "x")
    rejected(machine, intent(machine, Kind.APPLY_EQUATION,
                             {"call_id": current.call_id, "artifact_sha256": current.artifact_sha256,
                              "inputs_digest": current.inputs_digest}), charged=(18, 2))
    failed = machine.state.native_records[-1].body_dict()
    assert failed["failed_report"]["status"] == "CHECKED"
    assert failed["failed_equation_report"]["status"] == "REJECTED"
    assert failed["failed_equation_report"]["reason"] == "GROUNDED_INPUT_MISMATCH"
    assert machine.run().output is None


def test_fault_injected_false_atomic_answer_is_caught_by_equation_check(profile, monkeypatch):
    machine = drive(start(profile), lambda m: bool(m.state.native_calls) and call(m, "x").status == "READY")
    from cncm.procedural_qualification import check_procedure_call

    def falsely_accept(*args, **kwargs):
        report = check_procedure_call(*args, **kwargs)
        report["execution"]["outputs"]["x"] = "999"
        report["report_sha256"] = digest({key: value for key, value in report.items() if key != "report_sha256"})
        return report

    monkeypatch.setattr("cncm.nested_kernel.check_procedure_call", falsely_accept)
    current = call(machine, "x")
    rejected(machine, intent(machine, Kind.APPLY_EQUATION,
                             {"call_id": current.call_id, "artifact_sha256": current.artifact_sha256,
                              "inputs_digest": current.inputs_digest}), charged=(18, 2))
    failure = machine.state.native_records[-1].body_dict()["failed_equation_report"]
    assert failure["reason"] == "EQUATION_SUBSTITUTION_MISMATCH"
    assert not any(row.kind == "EXECUTION" for row in machine.state.native_records)
