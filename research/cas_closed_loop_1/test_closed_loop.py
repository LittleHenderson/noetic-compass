"""Public engineering controls; no model, protected fixtures or AWS calls."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from cncm.canonical import digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_kernel import compound_intent
from cncm.compound_model import CompoundIntentType as C, create_problem
from cncm.compound_profile import load_compound_profile
from cncm.compound_program import CallProgram, CallStep
from cncm.model import TerminalStatus
from cncm.native_model import NativeBudget
from research.cas_closed_loop_1.control import Design, BOARDS, checked_board, controlled_step, predicted_flow
from research.cas_closed_loop_1.native_step_adapter import primitive_work_for_events, verify_receipt
from research.cas_closed_loop_1.run_closed_loop import public_problem, run_episode, effect_check, demo, replay


def fresh(**options):
    machine = CompoundMachine(load_compound_profile(), trusted_ingress=())
    machine.start(public_problem(**options))
    return machine


def to_stage(machine, kind):
    for _ in range(32):
        proposed = machine.coordinator.next_intent()
        if proposed is not None and proposed.intent_type is kind:
            return proposed
        controlled_step(machine)
    raise AssertionError("stage not reached")


@pytest.mark.parametrize("drive,constraint,expected", [("12", "4", 3), ("12", "6", 2)])
def test_exact_pinned_ohm_calculation(drive, constraint, expected):
    assert predicted_flow(Design(drive, constraint)).value == expected


@pytest.mark.parametrize("drive,constraint", [("1", "0"), ("NaN", "1"), ("Infinity", "1"), ("-1", "1")])
def test_invalid_ohm_inputs_refused(drive, constraint):
    with pytest.raises(ValueError):
        predicted_flow(Design(drive, constraint))


def test_permission_mask_precedes_invalid_ratio_and_preserves_state():
    machine = fresh()
    before = machine.state
    row = controlled_step(machine, design=Design("NaN", "0"), permitted=False)
    assert row["I_predicted"] is None and row["I_allocated"] == row["I_executed"] == 0
    assert machine.state == before


@pytest.mark.parametrize("module_name", ["compiler_ohm", "pcba_check"])
def test_foreign_loaded_control_dependency_is_not_admitted(module_name, monkeypatch):
    from research.cas_closed_loop_1.native_step_adapter import GrantRefused
    machine = fresh()
    module = sys.modules[module_name]
    monkeypatch.setattr(module, "__file__", "foreign/" + module_name + ".py")
    with pytest.raises(GrantRefused, match="UNADMITTED_DEPENDENCY_LOCATION"):
        controlled_step(machine)


def test_disabled_actuator_keeps_prediction_and_grant_but_executes_nothing():
    machine = fresh()
    row = controlled_step(machine, actuator_enabled=False)
    assert row["I_predicted"] is not None
    assert row["I_allocated"] == 1 and row["I_executed"] == 0
    assert not effect_check(machine) and verify_receipt(row)


@pytest.mark.parametrize("name", list(BOARDS))
def test_supported_boards_static_check_and_operation_mask(name):
    from research.cas_closed_loop_1.control import OPERATIONS
    operation = sorted(OPERATIONS[name])[0]
    assert checked_board(name, operation)["static_status"] == "PASS"
    with pytest.raises(ValueError, match="UNSUPPORTED_BOARD_EXECUTION_PROFILE"):
        checked_board(name, "ARBITRARY_PASSIVE_TRANSFER")
    with pytest.raises(ValueError):
        checked_board(name, operation, BOARDS[name].replace("cjt step:", "resistor step:"))


@pytest.mark.parametrize("options", [{"allow_acquisition": False}, {"budget": NativeBudget(300, 100)},
                                    {"rpm_depth_limit": 1}, {"max_ticks": 2}])
def test_bounded_negative_controls_cannot_commit(options):
    options = dict(options)
    allowed = options.pop("allow_acquisition", True)
    machine = fresh(**options)
    rows = run_episode(machine, allow_acquisition=allowed)
    assert machine.state.halt_status in {TerminalStatus.NEEDS_CAPABILITY, TerminalStatus.BUDGET_EXHAUSTED}
    assert not effect_check(machine) and machine.result().output is None
    assert machine.state.compound_head is None
    assert all(row["charged_native_policy_units"]["instructions"] >= 0 for row in rows)


def test_wrong_method_is_rejected_and_failed_work_remains_charged():
    machine = fresh()
    to_stage(machine, C.CONSTRUCT_COMPOUND)
    primitive = machine.state.procedural_artifacts[0]
    wrong = CallProgram(primitive.artifact_sha256, (CallStep("a", "b", "c"),))
    intent = compound_intent(machine.coordinator, C.INSTALL_COMPOUND,
        {"call_id": machine.state.compound_call.call_id, "artifact": wrong.to_dict(), "qualification_digest": None})
    before = machine.state.native_budget
    outcome = machine.coordinator.execute(enabled_components=(intent.issuer_subsystem,),
        scheduled_components=(intent.issuer_subsystem,), intents=(intent,))
    assert outcome.rejected_intents and machine.state.compound_head is None
    assert machine.state.native_budget.instructions_remaining < before.instructions_remaining
    work = primitive_work_for_events(machine, [outcome.trace_event])
    assert work["measured_totals"]["primitive_instructions"] > 0
    run_episode(machine)
    assert not effect_check(machine)


@pytest.fixture(scope="module")
def completed(tmp_path_factory):
    destination = tmp_path_factory.mktemp("closed_loop") / "demo"
    result = demo(destination)
    return destination, result


def test_real_repair_exact_return_checked_bias_effect_and_event_bound_work(completed):
    directory, result = completed
    assert result["engineering_demo"] == "CHECKED" and result["output"] == "3"
    assert result["measured_native_work"]["primitive_instructions"] > 0
    assert result["complete_compute"] is None and result["cas_specific_advantage"] == "UNMEASURED"
    rows = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    journal = json.loads((directory / "journal.json").read_text())
    actions = [intent["intent_type"] for event in journal["episodes"][0]["trace"]
               for intent in event["proposed_intents"] if intent["intent_id"] in event["authorized_intent_ids"]]
    required = ["PUSH_COMPOUND_ACQUISITION", "PUSH_PRIMITIVE_ACQUISITION", "INSTALL_PRIMITIVE",
                "RETURN_PRIMITIVE", "CONSTRUCT_COMPOUND", "INSTALL_COMPOUND", "RETURN_COMPOUND", "APPLY_COMPOUND"]
    assert [actions.index(action) for action in required] == sorted(actions.index(action) for action in required)
    root_ids = {r["after"]["root_call"]["call_id"] for r in rows
                if r["after"]["root_call"] is not None}
    assert len(root_ids) == 1
    atlas = json.loads((directory / "atlas.json").read_text())
    assert [r["event"]["event_hash"] for r in atlas["timeline"]] == [r["event_hash"] for r in journal["episodes"][0]["trace"]]


def test_fresh_process_replays_retained_journal(completed):
    directory, result = completed
    command = [sys.executable, str(Path(__file__).with_name("run_closed_loop.py")), "replay",
               "--directory", str(directory), "--expected-bundle-digest", result["bundle_digest"]]
    process = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert process.returncode == 0, process.stdout + process.stderr
    replayed = json.loads(process.stdout)
    assert replayed["final_state_hash"] == result["replay"]["final_state_hash"]


def test_truncated_observation_refused_before_native_replay(completed, tmp_path):
    directory, result = completed
    for name in ("bundle.json", "journal.json", "events.jsonl"):
        (tmp_path / name).write_bytes((directory / name).read_bytes())
    rows = (tmp_path / "events.jsonl").read_text().splitlines()
    (tmp_path / "events.jsonl").write_text("\n".join(rows[:-1]) + "\n")
    with pytest.raises(ValueError, match="STEP_RECEIPTS_ALTERED_OR_TRUNCATED"):
        replay(tmp_path, result["bundle_digest"])


def test_recovered_reuse_changed_inputs_wrong_effect_and_invalidation(completed, monkeypatch):
    from cncm.compound_recovery import recover_compound_journal
    from cncm.compound_model import CompoundProblem
    import cncm.compound_kernel as kernel
    directory, result = completed
    journal = json.loads((directory / "journal.json").read_text())
    bundle = json.loads((directory / "bundle.json").read_text())
    machine = recover_compound_journal(journal, trusted_genesis=CompoundProblem.from_dict(bundle["trusted_genesis"]),
        trusted_ingress=(), expected_journal_digest=bundle["journal_digest"], profile=load_compound_profile())
    original_head = machine.state.compound_head
    # The independent check uses the original caller's inputs, not a runtime replacement.
    original_parameters = machine.problem.parameters
    object.__setattr__(machine.problem, "parameters", tuple((k, "999" if k == "e" else v) for k, v in original_parameters))
    assert not effect_check(machine)
    object.__setattr__(machine.problem, "parameters", original_parameters)
    changed = create_problem({"a": "2", "b": "3", "c": "5", "d": "7", "e": "41"}, problem_id="new-input")
    machine.start(changed)
    rows = run_episode(machine, allow_acquisition=False)
    assert effect_check(machine) and machine.result().output == "4"
    assert machine.state.compound_head == original_head
    assert all(row["board_binding"]["operation"] != "CONSTRUCT_COMPOUND" for row in rows)

    machine.start(public_problem(problem_id="invalid-effect"))
    to_stage(machine, C.APPLY_COMPOUND)
    original = kernel.check_program_call
    def wrong_effect(*args, **kwargs):
        report = original(*args, **kwargs)
        report["output"] = "999"
        report["report_digest"] = digest({k: v for k, v in report.items() if k != "report_digest"})
        return report
    with monkeypatch.context() as scoped:
        scoped.setattr(kernel, "check_program_call", wrong_effect)
        row = controlled_step(machine)
    assert row["I_predicted"] is not None and row["I_executed"] == 1
    assert machine.state.compound_call.output is None
    run_episode(machine, allow_acquisition=False)
    assert not effect_check(machine)

    machine.start(public_problem(problem_id="invalidate"))
    while machine.state.memory_resolution_digest is None:
        controlled_step(machine)
    spent = machine.state.native_budget
    machine.rollback(capability="primitive")
    assert machine.state.compound_head == original_head and machine.state.native_budget == spent
    observation = controlled_step(machine, allow_acquisition=False)
    assert observation["parent_readiness_before"] == "BLOCKED"
    assert "NO_ACTIVE_PRIMITIVE_HEAD" in observation["prerequisite_dispatch"]["blockers"]
    run_episode(machine, allow_acquisition=False)
    assert not effect_check(machine) and machine.state.halt_status is TerminalStatus.NEEDS_CAPABILITY
