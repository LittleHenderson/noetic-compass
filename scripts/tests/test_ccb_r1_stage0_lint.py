"""Stage 0 conformance linter must reject the audited board and accept its rebuild.

Guards the defect class recorded in
docs/working/cas_pcba_reasoning_audit_2026_08_27.md so a regressed netlist cannot
land quietly.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from stage0_lint import lint, parse_board  # noqa: E402

FIXTURES = REPO / "scripts" / "ccb_r1" / "fixtures"


def _lint(name: str):
    board = parse_board((FIXTURES / name).read_text(encoding="utf8"))
    return board, lint(board)


class Stage0LintTest(unittest.TestCase):
    def test_original_section11_board_is_rejected(self) -> None:
        _, findings = _lint("ccb_r1_section11_original.board")
        codes = {f.code for f in findings}
        # Each of these is a hand-found audit finding the lint must reproduce.
        self.assertIn("L-DOMAIN", codes, "must catch the E->C ascent (Inversion Axis W)")
        self.assertIn("L-FIREWALL", codes, "must catch goal_bias on the inference stage")
        self.assertIn("L-ORPHAN", codes, "must catch `action` having no writer")
        self.assertIn("L-FEEDBACK", codes, "must catch the O->C feedback path")
        self.assertIn("L-BETA", codes, "must catch `...` placeholder gains")
        self.assertTrue(any(f.severity == "critical" for f in findings))

    def test_firewall_does_not_fire_on_a_principled_charter(self) -> None:
        """F7 Purpose in the Principled domain is a charter, not ambition.

        Regression for a false positive: the firewall separates ambition from
        principle, and the domain coordinate is what distinguishes them.
        """
        _, findings = _lint("ccb_r1_section11_original.board")
        firewall = [f for f in findings if f.code == "L-FIREWALL"]
        self.assertTrue(firewall)
        for f in firewall:
            self.assertNotEqual(
                f.subject, "analyze", "charter_bias (^5^P_{F7}|T) is a legitimate governor"
            )

    def test_corrected_board_passes_clean(self) -> None:
        """The rules must be satisfiable -- a lint nothing can pass is useless."""
        _, findings = _lint("ccb_r1_section11_corrected.board")
        self.assertEqual(findings, [], f"expected clean, got: {[str(f) for f in findings]}")

    def test_placeholder_gain_is_not_mistaken_for_a_number(self) -> None:
        """`...` must not satisfy a numeric gain check (regex character-class trap)."""
        from stage0_lint import _NUMERIC

        self.assertIsNone(_NUMERIC.fullmatch("..."))
        self.assertIsNotNone(_NUMERIC.fullmatch("0.005"))
        self.assertIsNotNone(_NUMERIC.fullmatch("1.0"))


if __name__ == "__main__":
    unittest.main()
