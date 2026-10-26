"""Exact declared Ohm calculation and narrow PCBA-to-native stage admission."""
from dataclasses import dataclass
from pathlib import Path
import sys

from cncm.canonical import digest
from cncm.model import TerminalStatus
from cncm.rpa_compound_adapter import _dispatch
from .native_step_adapter import admission_for, execute_grant, grant_for

RUNTIME = Path(__file__).resolve().parent / "_runtime"
sys.path.insert(0, str(RUNTIME / "pcba"))
from compiler_ohm import attention_flow, make_quantity, make_scale
from pcba_check import check_pcba_document

PROFILE = "cas.closed-loop.pcba-native-operations/0.1"
OPERATIONS = {
    "parent_transform": frozenset({"REQUEST_COMPOUND", "APPLY_COMPOUND"}),
    "prerequisite_acquisition": frozenset({"PUSH_COMPOUND_ACQUISITION", "PUSH_PRIMITIVE_ACQUISITION",
        "SELECT_PRIMITIVE", "INSTALL_PRIMITIVE", "RETURN_PRIMITIVE", "CONSTRUCT_COMPOUND",
        "INSTALL_COMPOUND", "RETURN_COMPOUND", "FAIL_COMPOUND"}),
    "verification_commit": frozenset({"CHECK_MEMORY_RESOLUTION", "ORDINARY_REASONING_AND_COMMITMENT", "HALT"}),
}
BOARDS = {name: f"board {name} {{ cjt step: CJT< ^8^C|T | ^5^C|T => ^9^C|T >; }}"
          for name in OPERATIONS}


def checked_board(name, operation, source=None):
    source = BOARDS[name] if source is None else source
    checked = check_pcba_document(source)
    if not checked["valid"]:
        raise ValueError("PCBA_STATIC_CHECK_FAILED")
    if source != BOARDS[name] or operation not in OPERATIONS[name]:
        raise ValueError("UNSUPPORTED_BOARD_EXECUTION_PROFILE")
    return {"profile": PROFILE, "board": name, "operation": operation,
            "source_sha256": checked["document"]["source_sha256"],
            "static_status": "PASS", "native_mapping": "CompoundMachine.advance",
            "scope": "Only the named native operation is supported; no passive, feedback, timing or neural execution."}


@dataclass(frozen=True)
class Design:
    drive: str = "1"
    constraint: str = "1"
    drive_source: str = "declared_host_dispatch_demand"
    constraint_source: str = "declared_one_window_host_dispatch_constraint"


def predicted_flow(design):
    if type(design) is not Design:
        raise ValueError("TYPED_DESIGN_REQUIRED")
    scale = make_scale("closed-loop-host-window/0.1", "declared_dispatch_drive", "native_host_step_invocation")
    drive = make_quantity("drive", design.drive, scale, "design", design.drive_source)
    constraint = make_quantity("constraint", design.constraint, scale, "design", design.constraint_source)
    return attention_flow(drive, constraint)


def controlled_step(machine, *, design=Design(), allow_acquisition=True, actuator_enabled=True,
                    permitted=True, board_source=None):
    # Hard mask precedes any ratio evaluation; no fallback route is selected.
    if type(permitted) is not bool:
        raise ValueError("PERMISSION_MASK_MUST_BE_BOOLEAN")
    admission_for(machine)
    if machine.state.halt_status is not TerminalStatus.RUNNING:
        raise ValueError("EPISODE_NOT_RUNNING")
    state = machine.state
    if (state.commitment_state.decision_status == "COMMITTED"
            or (state.trace_head and state.budget.ticks_remaining <= 1)):
        operation = "HALT"
    else:
        proposal = machine.coordinator.next_intent(allow_acquisition=allow_acquisition)
        operation = proposal.intent_type.value if proposal else (
            "HALT" if state.memory_failure or (state.compound_call and state.compound_call.status == "FAILED")
            else "ORDINARY_REASONING_AND_COMMITMENT")
    board = next((name for name, actions in OPERATIONS.items() if operation in actions), None)
    if board is None:
        raise ValueError("UNSUPPORTED_NATIVE_OPERATION:" + operation)
    binding = checked_board(board, operation, board_source)
    flow = predicted_flow(design) if permitted else None
    # Floor exact rational request, capped at this profile's one-call allowance.
    calls = min(1, flow.value.numerator // flow.value.denominator) if flow else 0
    dispatch = _dispatch(state)
    readiness = "READY" if dispatch["eligible"] else "BLOCKED"
    receipt = execute_grant(machine, grant_for(machine, calls=calls,
        allow_acquisition=allow_acquisition, actuator_enabled=actuator_enabled))
    receipt.pop("receipt_digest")
    receipt.update({"I_predicted": flow.to_dict() if flow else None,
        "prediction_window": {"run_id": state.run_id, "state_hash": state.state_hash,
                              "logical_tick": state.logical_tick, "unit": receipt["unit"]},
        "allocation_policy": "FLOOR_EXACT_PREDICTION_CAP_ONE_AFTER_PERMISSION_MASK",
        "permitted": permitted, "board_binding": binding, "parent_readiness_before": readiness,
        "first_unmet_prerequisite": dispatch["blockers"][0] if dispatch["blockers"] else None,
        "prerequisite_dispatch": dispatch,
        "region_state": "UNASSESSED", "residual": None,
        "residual_status": "UNAVAILABLE_UNCALIBRATED_DESIGN_NOT_EMPIRICAL_PREDICTION"})
    receipt["receipt_digest"] = digest(receipt)
    return receipt
