"""Each ablation removes exactly one rule, and the base workspace has that rule.

Every test below runs the same micro-stream twice: once on `Workspace`, once
on the ablated subclass. The base must exhibit the rule; the ablation must
lack it; and the ablation must still exhibit every *other* rule the tests
touch. That pairing is what entitles the experiment to attribute a failing
cell to the one rule the ablation removed.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

import ablations  # noqa: E402
from ablations import (  # noqa: E402
    ABLATIONS,
    AmnesicAsk,
    FixedWorld,
    LastWriterAdd,
    NoCascade,
    NoFirewall,
    NonTransitiveRetract,
    NoSweep,
    ablation,
)
from workspace import ASSERTIVE, Status, Workspace  # noqa: E402

R = "leads_to"
AB, BC, AC = "A|leads_to|B", "B|leads_to|C", "A|leads_to|C"


def chain(ws: Workspace) -> Workspace:
    """A -> B -> C given, A -> C derived from both links."""
    ws.fact("A", R, "B")
    ws.fact("B", R, "C")
    ws.derive("A", R, "C", (AB, BC))
    return ws


class RegistryTests(unittest.TestCase):
    def test_every_ablation_is_a_workspace_with_one_named_removed_rule(self):
        names = [a.name for a in ABLATIONS]
        self.assertEqual(len(names), len(set(names)))
        for a in ABLATIONS:
            self.assertTrue(a.name.startswith("abl_"), a.name)
            self.assertTrue(issubclass(a.workspace, Workspace), a.name)
            self.assertIsNot(a.workspace, Workspace, a.name)
            self.assertTrue(a.removed.startswith("Workspace."), a.removed)
            self.assertEqual(a.removed, a.workspace.removed)

    def test_every_ablation_overrides_only_what_it_declares(self):
        """The surface each ablation touches is declared, and nothing else moves."""
        ignored = {
            "__doc__", "__module__", "__qualname__", "__annotations__", "__firstlineno__",
            "__static_attributes__", "__dict__", "__weakref__", "__dataclass_params__",
            "__dataclass_fields__", "__match_args__", "__init__", "__repr__", "__eq__",
            "__hash__", "removed", "overrides",
        }
        for a in ABLATIONS:
            touched = {k for k in vars(a.workspace) if k not in ignored}
            self.assertEqual(
                touched, set(a.workspace.overrides),
                f"{a.name} overrides {sorted(touched)}; declared {a.workspace.overrides}",
            )
            for name in a.workspace.overrides:
                if name != "__post_init__":
                    self.assertTrue(hasattr(Workspace, name), f"{a.name}: {name} is not a Workspace method")

    def test_lookup_by_name(self):
        self.assertIs(ablation("abl_no_cascade").workspace, NoCascade)
        with self.assertRaises(KeyError):
            ablation("abl_nonexistent")

    def test_the_module_imports_only_the_workspace_and_stdlib(self):
        source = Path(ablations.__file__).read_text()
        for line in source.splitlines():
            line = line.strip()
            if line.startswith("from ") and " import " in line:
                module = line.split()[1].split(".")[0]
                self.assertIn(module, {"__future__", "dataclasses", "workspace"}, line)
            self.assertFalse(line.startswith("import "), line)


class NonTransitiveRetractTests(unittest.TestCase):
    def test_base_retraction_cascades_to_the_derivation(self):
        ws = chain(Workspace())
        ws.retract(AB)
        self.assertIs(ws.props[AC].status, Status.RETRACTED)

    def test_ablated_retraction_leaves_the_derivation_standing(self):
        ws = chain(NonTransitiveRetract())
        ws.retract(AB)
        self.assertIs(ws.props[AB].status, Status.RETRACTED)
        self.assertIs(ws.props[AC].status, Status.DERIVED)
        self.assertTrue(ws.holds("A", R, "C"), "a conclusion with no remaining reason is still held")

    def test_ablated_retraction_still_cascades_a_contradiction(self):
        """The other cascade -- from a dispute -- is a different rule and stays."""
        ws = chain(NonTransitiveRetract())
        ws.fact("A", R, "B", negated=True)
        self.assertIs(ws.props[AB].status, Status.CONTRADICTED)
        self.assertIs(ws.props[AC].status, Status.RETRACTED)

    def test_ablated_retraction_still_refuses_an_absent_pid_and_reinstates(self):
        ws = NonTransitiveRetract()
        with self.assertRaises(Exception):
            ws.retract("Q|leads_to|Z")
        ws.fact("A", R, "B")
        ws.fact("A", R, "B", negated=True)
        ws.retract(AB)
        self.assertIs(ws.props["~" + AB].status, Status.FACT, "the denial is reinstated")


class NoFirewallTests(unittest.TestCase):
    def test_base_files_a_told_guess_as_a_hypothesis_that_cannot_carry_an_inference(self):
        ws = Workspace()
        ws.fact("A", R, "B")
        ws.hypothesize("B", R, "C", stage="stream")
        self.assertIs(ws.props[BC].status, Status.HYPOTHESIS)
        with self.assertRaises(Exception):
            ws.derive("A", R, "C", (AB, BC))

    def test_ablated_files_a_told_guess_as_a_given(self):
        ws = NoFirewall()
        ws.fact("A", R, "B")
        ws.hypothesize("B", R, "C", stage="stream")
        self.assertIs(ws.props[BC].status, Status.FACT)
        ws.derive("A", R, "C", (AB, BC))
        self.assertTrue(ws.holds("A", R, "C"))

    def test_ablated_turns_a_refutation_into_a_dispute(self):
        base, abl = Workspace(), NoFirewall()
        for ws in (base, abl):
            ws.hypothesize("B", R, "C", stage="stream")
            ws.fact("B", R, "C", negated=True)
        self.assertIs(base.props[BC].status, Status.RETRACTED, "base: the guess is refuted")
        self.assertFalse(base.contested("B", R, "C"))
        self.assertTrue(abl.contested("B", R, "C"), "ablated: a guess fights a denial as an equal")

    def test_ablated_leaves_route_bookkeeping_alone(self):
        ws = NoFirewall()
        ws.hypothesize("A", R, "C")  # stage "^8" by default
        self.assertIs(ws.props[AC].status, Status.HYPOTHESIS)


class LastWriterAddTests(unittest.TestCase):
    def test_base_marks_both_sides_contradicted(self):
        ws = Workspace()
        ws.fact("A", R, "B")
        ws.fact("A", R, "B", negated=True)
        self.assertTrue(ws.contested("A", R, "B"))

    def test_ablated_lets_the_last_statement_win_silently(self):
        ws = LastWriterAdd()
        ws.fact("A", R, "B")
        ws.fact("A", R, "B", negated=True)
        self.assertFalse(ws.contested("A", R, "B"))
        self.assertIs(ws.props[AB].status, Status.RETRACTED)
        self.assertIs(ws.props["~" + AB].status, Status.FACT)
        self.assertEqual(ws.ask("A", R, "B"), "NO")
        ws.fact("A", R, "B")
        self.assertEqual(ws.ask("A", R, "B"), "YES", "and flips straight back")
        self.assertEqual(ws.contradictions(), ())

    def test_ablated_overwriting_still_cascades_through_the_loser(self):
        ws = chain(LastWriterAdd())
        ws.fact("A", R, "B", negated=True)
        self.assertIs(ws.props[AC].status, Status.RETRACTED)

    def test_ablated_still_refutes_a_hypothesis_the_normal_way(self):
        ws = LastWriterAdd()
        ws.hypothesize("A", R, "B", stage="stream")
        ws.fact("A", R, "B", negated=True)
        self.assertIs(ws.props[AB].status, Status.RETRACTED)
        self.assertIs(ws.props["~" + AB].status, Status.FACT)


class NoCascadeTests(unittest.TestCase):
    def test_base_dispute_cascades_to_the_derivation(self):
        ws = chain(Workspace())
        ws.fact("A", R, "B", negated=True)
        self.assertIs(ws.props[AC].status, Status.RETRACTED)

    def test_ablated_dispute_leaves_the_derivation_standing_on_a_dead_root(self):
        ws = chain(NoCascade())
        ws.fact("A", R, "B", negated=True)
        self.assertTrue(ws.contested("A", R, "B"), "the dispute itself is still recorded")
        self.assertIs(ws.props[AC].status, Status.DERIVED)
        roots = ws.roots(AC)
        self.assertIn(AB, roots)
        self.assertNotIn(ws.props[AB].status, ASSERTIVE, "a standing conclusion with a dead root")

    def test_ablated_explicit_retraction_still_cascades(self):
        ws = chain(NoCascade())
        ws.retract(BC)
        self.assertIs(ws.props[AC].status, Status.RETRACTED)


class AmnesicAskTests(unittest.TestCase):
    def test_base_records_what_it_could_not_answer(self):
        ws = Workspace()
        self.assertEqual(ws.ask("A", R, "B"), "UNKNOWN")
        self.assertEqual(ws.lacunae(), (AB,))

    def test_ablated_answers_identically_but_remembers_nothing(self):
        for closed in (False, True):
            base, abl = Workspace(closed_world=closed), AmnesicAsk(closed_world=closed)
            for ws in (base, abl):
                ws.fact("A", R, "B")
                ws.fact("B", R, "C", negated=True)
            for q in (("A", "B"), ("B", "C"), ("A", "C")):
                self.assertEqual(base.ask(q[0], R, q[1]), abl.ask(q[0], R, q[1]), (closed, q))
            self.assertEqual(base.lacunae(), (AC,) if not closed else (AC,))
            self.assertEqual(abl.lacunae(), ())


class FixedWorldTests(unittest.TestCase):
    def test_base_honours_the_flag(self):
        self.assertEqual(Workspace(closed_world=True).ask("A", R, "B"), "NO")
        self.assertEqual(Workspace(closed_world=False).ask("A", R, "B"), "UNKNOWN")

    def test_ablated_ignores_the_flag_and_says_so_through_the_attribute(self):
        ws = FixedWorld(closed_world=True)
        self.assertFalse(ws.closed_world, "the organism reads this attribute, so it is lied to as well")
        self.assertEqual(ws.ask("A", R, "B"), "UNKNOWN")
        self.assertEqual(FixedWorld().ask("A", R, "B"), "UNKNOWN")


class NoSweepTests(unittest.TestCase):
    def test_base_marks_route_guesses_and_the_sweep_clears_exactly_those(self):
        ws = Workspace()
        ws.hypothesize("A", R, "C")
        ws.hypothesize("B", R, "C", stage="stream")
        self.assertEqual(ws.props[AC].stage, "^8")
        self.assertEqual(ws.sweep("^8"), (AC,))
        self.assertIs(ws.props[AC].status, Status.RETRACTED)
        self.assertIs(ws.props[BC].status, Status.HYPOTHESIS)

    def test_ablated_guesses_are_unmarked_so_nothing_is_swept(self):
        ws = NoSweep()
        ws.hypothesize("A", R, "C")
        ws.hypothesize("B", R, "C", stage="stream")
        self.assertEqual(ws.props[AC].stage, "")
        self.assertEqual(ws.props[BC].stage, "stream")
        self.assertEqual(ws.sweep("^8"), ())
        self.assertIs(ws.props[AC].status, Status.HYPOTHESIS)

    def test_disabling_the_sweep_alone_would_change_nothing_because_the_walk_skips_the_mark(self):
        """The reason the ablation removes the mark rather than the sweep."""
        from banks import HypothesisBank
        ws = Workspace()
        ws.fact("A", R, "B")
        ws.hypothesize("B", R, "C")              # a lingering, still-marked guess
        found, _ = HypothesisBank().surface(ws, "A", "C", R)
        self.assertEqual(found, [], "a marked guess is not walked")
        ws2 = NoSweep()
        ws2.fact("A", R, "B")
        ws2.hypothesize("B", R, "C")             # unmarked
        found2, _ = HypothesisBank().surface(ws2, "A", "C", R)
        self.assertEqual([c.nodes for c in found2], [("A", "B", "C")], "an unmarked guess is walked")

    def test_through_the_organism_a_lingering_guess_is_named_as_a_gap(self):
        """The failure the mark prevents: a later question is answered along an
        earlier question's guess, and ^6 names that guess as something missing.
        The key is neither a given guess nor an association nor the query pair,
        so the lacuna report loses precision. Verdicts are unchanged."""
        from events import ask, associate, fact
        from organism import Organism
        stream = [fact("C0", "C1"), fact("C2", "C3"), associate("C1", "C2"), ask("C1", "C3"), ask("C0", "C3")]
        base = Organism().run_stream(stream)
        abl = Organism(workspace_factory=NoSweep).run_stream(stream)
        self.assertEqual([r.verdict for r in base[3:]], ["UNKNOWN", "UNKNOWN"])
        self.assertEqual([r.verdict for r in abl[3:]], ["UNKNOWN", "UNKNOWN"])
        self.assertEqual(base[4].lacunae, ("C1|leads_to|C2",))
        self.assertIn("C1|leads_to|C3", abl[4].lacunae, "the first question's guess, named as a gap")
        self.assertIn("C1|leads_to|C2", abl[4].lacunae)


class OneRuleAtATimeTests(unittest.TestCase):
    """Rules an ablation does NOT remove must survive in it. One probe per rule,
    run on every ablation that is not the one removing it."""

    def test_transitive_retraction_survives_in_every_other_ablation(self):
        for a in ABLATIONS:
            if a.workspace is NonTransitiveRetract:
                continue
            ws = chain(a.workspace())
            ws.retract(AB)
            self.assertIs(ws.props[AC].status, Status.RETRACTED, a.name)

    def test_the_hypothesis_firewall_survives_in_every_other_ablation(self):
        for a in ABLATIONS:
            if a.workspace is NoFirewall:
                continue
            ws = a.workspace()
            ws.fact("A", R, "B")
            ws.hypothesize("B", R, "C", stage="stream")
            with self.assertRaises(Exception, msg=a.name):
                ws.derive("A", R, "C", (AB, BC))

    def test_contradiction_detection_survives_in_every_other_ablation(self):
        for a in ABLATIONS:
            if a.workspace is LastWriterAdd:
                continue
            ws = a.workspace()
            ws.fact("A", R, "B")
            ws.fact("A", R, "B", negated=True)
            self.assertTrue(ws.contested("A", R, "B"), a.name)

    def test_the_dispute_cascade_survives_in_every_other_ablation(self):
        for a in ABLATIONS:
            if a.workspace in (NoCascade, LastWriterAdd):
                continue  # LastWriterAdd has no disputes to cascade from
            ws = chain(a.workspace())
            ws.fact("A", R, "B", negated=True)
            self.assertIs(ws.props[AC].status, Status.RETRACTED, a.name)

    def test_lacuna_recording_survives_in_every_other_ablation(self):
        for a in ABLATIONS:
            if a.workspace is AmnesicAsk:
                continue
            ws = a.workspace()
            ws.ask("A", R, "B")
            self.assertEqual(ws.lacunae(), (AB,), a.name)

    def test_the_world_assumption_survives_in_every_other_ablation(self):
        for a in ABLATIONS:
            if a.workspace is FixedWorld:
                continue
            self.assertEqual(a.workspace(closed_world=True).ask("A", R, "B"), "NO", a.name)

    def test_the_sweep_survives_in_every_other_ablation(self):
        for a in ABLATIONS:
            if a.workspace is NoSweep:
                continue
            ws = a.workspace()
            ws.hypothesize("A", R, "C")
            self.assertEqual(ws.sweep("^8"), (AC,), a.name)


if __name__ == "__main__":
    unittest.main()
