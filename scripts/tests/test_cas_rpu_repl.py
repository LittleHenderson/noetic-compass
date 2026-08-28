"""The interactive console — parsing, commands, and exit status.

The parser is the part worth testing: it is the surface a person actually
types at, and a misparse turns a relation into part of a node name silently,
which then looks like the reasoner failing rather than the console mishearing.
"""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from repl import (  # noqa: E402
    ASSOC_RELATION,
    DEFAULT_RELATION,
    EXIT_CONCLUDED,
    EXIT_INADMISSIBLE,
    EXIT_WITHHELD,
    SCENARIOS,
    Session,
    main,
    run_command,
)


class ParserTests(unittest.TestCase):
    def test_a_bare_arrow_uses_the_default_relation(self):
        self.assertEqual(
            Session.parse_edge("VS -> IU"), ("VS", DEFAULT_RELATION, "IU")
        )

    def test_a_named_relation_is_not_swallowed_into_the_subject(self):
        """`A -rel-> B`. Partitioning on `->` eats the second dash, so the
        left side arrives as `A -rel` and a naive split leaves the subject as
        'A -rel'. That misparse reads as the reasoner failing."""
        self.assertEqual(
            Session.parse_edge("alice -reports_to-> bob"),
            ("alice", "reports_to", "bob"),
        )

    def test_a_node_name_containing_a_dash_survives(self):
        self.assertEqual(
            Session.parse_edge("node-a -> node-b"),
            ("node-a", DEFAULT_RELATION, "node-b"),
        )

    def test_a_dashed_node_name_with_a_named_relation_survives(self):
        self.assertEqual(
            Session.parse_edge("node-a -knows-> node-b"),
            ("node-a", "knows", "node-b"),
        )

    def test_the_squiggle_arrow_is_the_associative_relation(self):
        self.assertEqual(
            Session.parse_edge("VS ~> DE"), ("VS", ASSOC_RELATION, "DE")
        )

    def test_whitespace_is_tolerated(self):
        for text in ("VS->IU", "  VS  ->  IU  ", "VS ->IU"):
            self.assertEqual(
                Session.parse_edge(text), ("VS", DEFAULT_RELATION, "IU")
            )

    def test_a_non_edge_is_rejected_rather_than_guessed(self):
        for text in ("hello", "VS", "-> IU", "VS ->", ""):
            self.assertIsNone(Session.parse_edge(text))


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.session = Session()

    def feed(self, *lines):
        out = []
        for line in lines:
            text, _, status = run_command(self.session, line)
            out.append((text or "", status))
        return out

    def test_an_edge_typed_bare_is_added_as_a_premise(self):
        self.feed("VS -> QS")
        self.assertEqual(self.session.premises, [("VS", DEFAULT_RELATION, "QS")])

    def test_not_adds_a_negated_premise(self):
        self.feed("not VS -> QS")
        self.assertEqual(self.session.negated, [("VS", DEFAULT_RELATION, "QS")])
        self.assertEqual(self.session.premises, [])

    def test_asking_returns_a_report_and_a_status(self):
        self.feed("VS -> QS", "QS -> IU")
        report, status = self.feed("? VS -> IU")[0]
        self.assertEqual(status, EXIT_CONCLUDED)
        self.assertIn("CONCLUDED", report)
        self.assertIn("rests on", report)

    def test_an_open_world_gap_withholds(self):
        self.feed("VS -> QS")
        report, status = self.feed("? VS -> IU")[0]
        self.assertEqual(status, EXIT_WITHHELD)
        self.assertIn("UNKNOWN", report)

    def test_closing_the_world_turns_the_same_gap_into_a_no(self):
        self.feed("VS -> QS", "world closed")
        report, status = self.feed("? VS -> IU")[0]
        self.assertEqual(status, EXIT_CONCLUDED)
        self.assertIn("NO", report)

    def test_a_contradiction_is_inadmissible(self):
        self.feed("VS -> QS", "not VS -> QS")
        _, status = self.feed("? VS -> QS")[0]
        self.assertEqual(status, EXIT_INADMISSIBLE)

    def test_world_rejects_anything_but_open_or_closed(self):
        text, status = self.feed("world sideways")[0]
        self.assertEqual(status, 1)
        self.assertIn("open", text)

    def test_every_scenario_loads_and_is_answerable(self):
        for name in SCENARIOS:
            session = Session()
            run_command(session, f"scenario {name}")
            self.assertTrue(session.premises or session.negated, name)

    def test_why_before_asking_says_so_rather_than_crashing(self):
        self.assertIn("nothing asked", self.session.show_why())
        self.assertIn("nothing asked", self.session.show_trace())

    def test_why_after_an_abstention_explains_there_is_no_conclusion(self):
        self.feed("VS -> QS", "? VS -> IU")
        self.assertIn("no conclusion", self.session.show_why())

    def test_why_renders_the_support_tree_down_to_premises(self):
        self.feed("VS -> QS", "QS -> IU", "? VS -> IU")
        tree = self.session.show_why()
        self.assertIn("[derived ^9]", tree)
        self.assertEqual(tree.count("[fact]"), 2)

    def test_ambition_changes_the_profile_and_reports_the_dominant_channel(self):
        text, _ = self.feed("ambition F5|A 1.0")[0]
        self.assertIn("F5|A", text)
        self.assertEqual(self.session.profile.dominant(), "F5|A")

    def test_a_bad_ambition_reference_is_reported_not_raised(self):
        text, _ = self.feed("ambition TF5b")[0]
        self.assertIn("?", text)

    def test_reset_clears_premises_but_keeps_ambition(self):
        self.feed("ambition F5|A 1.0", "VS -> QS", "reset")
        self.assertEqual(self.session.premises, [])
        self.assertEqual(self.session.profile.dominant(), "F5|A")

    def test_an_unknown_command_is_reported_rather_than_silently_ignored(self):
        text, status = self.feed("frobnicate")[0]
        self.assertEqual(status, 1)
        self.assertIn("unknown command", text)

    def test_quit_stops_the_loop(self):
        _, quit_now, _ = run_command(self.session, "quit")
        self.assertTrue(quit_now)

    def test_blank_lines_and_comments_do_nothing(self):
        for line in ("", "   ", "# a note"):
            text, quit_now, status = run_command(self.session, line)
            self.assertIsNone(text)
            self.assertFalse(quit_now)
            self.assertEqual(status, 0)


class OneShotTests(unittest.TestCase):
    """`--quiet` prints one word, and the exit status carries the verdict."""

    def one_shot(self, argv):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            status = main(argv)
        return buffer.getvalue().strip(), status

    def test_a_concluded_chain_prints_yes_and_exits_zero(self):
        out, status = self.one_shot(
            ["-p", "VS->QS, QS->IU", "-a", "VS->IU", "--quiet"]
        )
        self.assertEqual(out, "YES")
        self.assertEqual(status, EXIT_CONCLUDED)

    def test_an_open_world_gap_prints_unknown_and_exits_two(self):
        out, status = self.one_shot(["-p", "VS->QS", "-a", "VS->IU", "--quiet"])
        self.assertEqual(out, "UNKNOWN")
        self.assertEqual(status, EXIT_WITHHELD)

    def test_the_closed_world_flag_turns_that_into_no(self):
        out, status = self.one_shot(
            ["-p", "VS->QS", "-a", "VS->IU", "--closed", "--quiet"]
        )
        self.assertEqual(out, "NO")
        self.assertEqual(status, EXIT_CONCLUDED)

    def test_a_scenario_can_be_run_without_typing_premises(self):
        out, status = self.one_shot(
            ["--scenario", "ladder", "-a", "VS->NX", "--quiet"]
        )
        self.assertEqual(out, "YES")
        self.assertEqual(status, EXIT_CONCLUDED)

    def test_an_associative_only_route_does_not_conclude(self):
        out, status = self.one_shot(
            ["--scenario", "assoc", "-a", "VS->NX", "--quiet"]
        )
        self.assertNotEqual(out, "YES")
        self.assertEqual(status, EXIT_WITHHELD)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
