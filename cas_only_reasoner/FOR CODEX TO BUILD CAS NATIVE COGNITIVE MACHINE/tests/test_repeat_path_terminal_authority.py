from __future__ import annotations

import unittest

from cncm.engine import CognitiveMachine
from cncm.model import BranchStatus, IntentType, ProblemPacket, TerminalStatus
from cncm.verification import verify_bundle

from tests._support import fixture_document


class _RepeatStablePassMachine(CognitiveMachine):
    """Exercise the repeat guard by scheduling the same stable pass twice."""

    def __init__(self) -> None:
        super().__init__()
        self.repeat_guard_observed = False

    def _derive_until_stable(
        self,
        packet,
        branch_id,
        coordinator,
        repeat_counts,
    ) -> bool:
        repeat_limit_reached = super()._derive_until_stable(
            packet,
            branch_id,
            coordinator,
            repeat_counts,
        )
        if (
            repeat_limit_reached
            or coordinator.store.snapshot().halt_status is not TerminalStatus.RUNNING
        ):
            return repeat_limit_reached

        repeat_limit_reached = super()._derive_until_stable(
            packet,
            branch_id,
            coordinator,
            repeat_counts,
        )
        self.repeat_guard_observed = repeat_limit_reached
        return repeat_limit_reached


class RepeatPathTerminalAuthorityRegressionTests(unittest.TestCase):
    def test_repeat_guard_defers_to_admitted_state_derived_halt(self) -> None:
        document = fixture_document("missing_information")
        document["problem_id"] = "repeat_path_terminal_authority"
        document["budgets"]["max_repeat_states"] = 1
        machine = _RepeatStablePassMachine()

        result = machine.run(ProblemPacket.from_dict(document))

        self.assertTrue(machine.repeat_guard_observed)
        self.assertIs(result.terminal_status, TerminalStatus.NEEDS_INFORMATION)
        self.assertIs(
            result.final_state.branch_map()["branch-main"].status,
            BranchStatus.BLOCKED,
        )
        self.assertEqual(
            result.final_state.global_workspace.lacunae,
            ("holds(P)@global",),
        )
        self.assertEqual(
            result.final_state.global_workspace.diagnostics,
            ("no branch established every required premise",),
        )
        self.assertEqual(result.final_state.logical_tick, 5)
        self.assertEqual(result.final_state.trace_head, result.trace[-1].event_hash)
        self.assertEqual(result.final_state.state_hash, result.trace[-1].post_state_hash)
        self.assertTrue(all(event.sealed for event in result.trace))
        self.assertTrue(all(not event.rejected_intents for event in result.trace))
        self.assertTrue(
            all(
                event.terminal_status is TerminalStatus.RUNNING
                for event in result.trace[:-1]
            )
        )
        self.assertIs(
            result.trace[-1].terminal_status,
            TerminalStatus.NEEDS_INFORMATION,
        )

        halt_intents = [
            intent
            for event in result.trace
            for intent in event.proposed_intents
            if intent.intent_type is IntentType.HALT
        ]
        self.assertEqual(len(halt_intents), 1)
        self.assertEqual(
            halt_intents[0].mutation_dict()["status"],
            TerminalStatus.NEEDS_INFORMATION.value,
        )
        self.assertIn(
            halt_intents[0].intent_id,
            result.trace[-1].authorized_intent_ids,
        )
        verification = verify_bundle(result.to_dict())
        self.assertTrue(verification.valid, verification.errors)


if __name__ == "__main__":
    unittest.main()
