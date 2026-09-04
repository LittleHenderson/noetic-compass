from __future__ import annotations

import unittest

from cncm.model import IntentType, RejectionReason, TerminalStatus
from cncm.semantics import decompose_query

from tests._support import coordinator_for, execute, make_intent


class ReservedTerminalStatusContractTests(unittest.TestCase):
    def coordinator_with_sealed_trace(self):
        packet, store, _, coordinator = coordinator_for("deduction")
        branch = store.snapshot().branch_map()["branch-main"]
        decomposition = make_intent(
            coordinator,
            intent_type=IntentType.RECORD_DECOMPOSITION,
            issuer="reasoning_engine",
            capability="decompose",
            scope="branch:branch-main",
            branch_id="branch-main",
            mutation={
                "decomposition": decompose_query(
                    branch,
                    packet.query,
                    packet.rules,
                ).to_dict()
            },
        )
        prepared = execute(coordinator, decomposition)
        self.assertEqual(prepared.rejected_intents, ())
        self.assertNotEqual(prepared.state.trace_head, "")
        return coordinator

    def test_components_cannot_request_reserved_or_kernel_only_halts(self) -> None:
        reserved_statuses = (
            TerminalStatus.NEEDS_CAPABILITY,
            TerminalStatus.LOOP_LIMIT_REACHED,
            TerminalStatus.DEADLOCK,
            TerminalStatus.FAULT,
        )

        for status in reserved_statuses:
            with self.subTest(status=status.value):
                coordinator = self.coordinator_with_sealed_trace()
                halt = make_intent(
                    coordinator,
                    intent_type=IntentType.HALT,
                    issuer="halting_controller",
                    capability="request_typed_halt",
                    scope="halt_status",
                    branch_id=None,
                    mutation={
                        "status": status.value,
                        "lacunae": [],
                        "diagnostics": [],
                    },
                )

                result = execute(coordinator, halt)

                self.assertEqual(result.authorized_intents, ())
                self.assertEqual(len(result.rejected_intents), 1)
                self.assertIs(
                    result.rejected_intents[0].reason,
                    RejectionReason.INVALID_TERMINAL_STATUS,
                )
                self.assertIs(result.state.halt_status, TerminalStatus.RUNNING)


if __name__ == "__main__":
    unittest.main()
