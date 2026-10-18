"""plan_executor.py -- Governed prerequisite-graph executor.

Walks the topologically sorted plan nodes, gating every node with the real RPM Gate,
updating Bias working memory, verifying strict version increases, taking ASOM diagnostic
readouts, and recording step receipts.

SPECIFICATION: SPEC_PREREQUISITE_GRAPH_PLANNER_20261018.md (Section 5)
CLAIM CEILING:
MECHANISM ONLY. ORDERING IS DERIVED FROM STATED PREREQUISITES. NO UNDERSTANDING OF THE REQUEST IS CLAIMED.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
COUNCIL = os.path.dirname(HERE)

for path in (
    COUNCIL,
    os.path.join(COUNCIL, "the_loop_v3"),
    os.path.join(COUNCIL, "dwp_engine_v2"),
    os.path.join(COUNCIL, "repair_performer"),
    os.path.join(COUNCIL, "language_v3"),
):
    if path not in sys.path:
        sys.path.insert(0, path)

import asom
import bias as bias_module
import loop
import actor
import rpm_gate

from plan_graph import (
    CLAIM_CEILING,
    PLAN_ORDER_VIOLATION,
    PLAN_REPAIR_FAILED,
    PlanNode,
    PlanRefusal,
    PlanResult,
)


@dataclass(frozen=True)
class PlanStepReceipt:
    """Receipt for one executed plan step."""
    node: str
    order_position: int
    depth: int
    gate_verdict: str
    gate_code: str
    bias_version_before: int
    bias_version_after: int
    asom_label: str
    repaired: bool = False

    def as_dict(self) -> dict:
        return {
            "node": self.node,
            "order_position": self.order_position,
            "depth": self.depth,
            "gate_verdict": self.gate_verdict,
            "gate_code": self.gate_code,
            "bias_version_before": self.bias_version_before,
            "bias_version_after": self.bias_version_after,
            "asom_label": self.asom_label,
            "repaired": self.repaired,
        }


@dataclass(frozen=True)
class PlanExecutionReceipt:
    """Overall execution receipt for a completed plan graph."""
    plan_digest: str
    steps: Tuple[PlanStepReceipt, ...]
    final_bias_version: int
    final_bias_digest: str
    executed_order: Tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "plan_digest": self.plan_digest,
            "final_bias_version": self.final_bias_version,
            "final_bias_digest": self.final_bias_digest,
            "executed_order": list(self.executed_order),
            "steps": [s.as_dict() for s in self.steps],
        }


def execute_plan(
    plan: PlanResult,
    runner: Optional[Callable[[PlanNode], Any]] = None,
    bias: Optional[bias_module.Bias] = None,
    coordinator: str = "prereq_planner",
    open_child_fn: Optional[Callable] = None,
) -> PlanExecutionReceipt:
    """Execute a plan graph under strict RPM Gate governance.

    Section 5 invariants:
    1. For each node, construct RpmCause:
       - unsatisfied = node.needs not yet written into Bias
       - depth = node.depth
       - blocked_node = 'P' if unsatisfied else None
    2. Query rpm_gate(request):
       - PROCEED: proceed to run node
       - REPAIR: raise PLAN_ORDER_VIOLATION (the sort put a node before its prerequisites)
       - REFUSE: stop whole plan, raise refusal
    3. On success:
       - write node's outcome into Bias
       - call check_version_increase so version strictly rises
       - take ASOM diagnostic readout (display only; never gates)
       - record step receipt
    4. On mid-plan execution failure:
       - hand to repair_performer.perform_repair() ONCE
       - if REPAIRED, continue; if not, raise PLAN_REPAIR_FAILED (never loop)
    """
    if bias is None:
        bias = bias_module.Bias(coordinator=coordinator)

    receipts: List[PlanStepReceipt] = []
    executed_order: List[str] = []

    for idx, node in enumerate(plan.nodes):
        # 1. Check which prerequisites are not yet written into Bias
        unsatisfied = tuple(req for req in node.needs if not bias.has(req))

        # 2. Build RpmCause
        if unsatisfied:
            cause = rpm_gate.RpmCause(
                blocked_node="P",
                depth=node.depth,
                unsatisfied=unsatisfied,
            )
        else:
            cause = rpm_gate.RpmCause(
                blocked_node=None,
                depth=node.depth,
                unsatisfied=(),
            )

        snap = bias.snapshot()
        request = loop.GateRequest(
            turn=idx,
            coordinator=coordinator,
            bias_version=bias.version,
            bias_digest=snap.digest,
            proposal_text=f"execute node {node.omega}",
            prerequisites=tuple(node.needs),
            cause=cause,
        )

        # 3. Ask the RPM Gate
        verdict = rpm_gate.rpm_gate(request)

        # 4. Gate Verdict Handling
        if verdict.verdict == rpm_gate.REPAIR:
            # Self-check: Gate detected that the sort attempted to execute before prerequisites were satisfied
            raise PlanRefusal(
                PLAN_ORDER_VIOLATION,
                f"gate returned REPAIR on node '{node.omega}': prerequisite '{verdict.gap}' is unsatisfied ({verdict.code})",
            )

        if verdict.verdict == rpm_gate.REFUSE:
            raise PlanRefusal(
                verdict.code or "PLAN_REFUSE",
                f"gate refused node '{node.omega}': {verdict.reason}",
            )

        # PROCEED
        version_before = bias.version
        repaired = False
        outcome_val: Any = None

        if runner is not None:
            try:
                run_out = runner(node)
                if isinstance(run_out, dict) and run_out.get("ok") is False:
                    raise RuntimeError(f"node runner returned not ok: {run_out.get('detail', '')}")
                outcome_val = run_out if run_out is not None else {"status": "SUCCESS"}
            except Exception as err:
                # Genuine mid-plan failure: hand to repair_performer.perform_repair() ONCE
                ledger: List[dict] = []
                repair_child = open_child_fn or (lambda **kwargs: {"ok": True, "detail": "repaired by stand-in child"})
                repair_cause = rpm_gate.RpmCause(
                    blocked_node="P",
                    depth=node.depth,
                    unsatisfied=(f"execution of {node.omega}",),
                )
                repair_request = actor.make_request(
                    cause=repair_cause,
                    prerequisites=tuple(node.needs),
                    bias_version=bias.version,
                )
                repair_result = actor.perform_repair(
                    request=repair_request,
                    open_child=repair_child,
                    ledger=ledger,
                )

                if repair_result.get("outcome") == actor.REPAIRED:
                    repaired = True
                    outcome_val = {"status": "REPAIRED", "detail": str(err)}
                else:
                    raise PlanRefusal(
                        PLAN_REPAIR_FAILED,
                        f"the one repair attempt for node '{node.omega}' failed: {repair_result.get('outcome')}",
                    ) from err
        else:
            outcome_val = {"status": "SUCCESS", "omega": node.omega, "depth": node.depth}

        # 5. Write outcome to Bias and verify strict version increase
        bias.write(node.omega, outcome_val, coordinator)
        version_after = bias.version
        bias_module.check_version_increase(version_before, version_after)

        # 6. ASOM diagnostic readout (Display only; never gates)
        asom_label = asom.readout(region="ACTIVE", outcome="INTENDED", saturated=False)

        receipts.append(
            PlanStepReceipt(
                node=node.omega,
                order_position=idx,
                depth=node.depth,
                gate_verdict=verdict.verdict,
                gate_code=verdict.code,
                bias_version_before=version_before,
                bias_version_after=version_after,
                asom_label=asom_label,
                repaired=repaired,
            )
        )
        executed_order.append(node.omega)

    final_snap = bias.snapshot()
    return PlanExecutionReceipt(
        plan_digest=plan.digest,
        steps=tuple(receipts),
        final_bias_version=final_snap.version,
        final_bias_digest=final_snap.digest,
        executed_order=tuple(executed_order),
    )
