"""The sever-the-umbilical-cord test.

The decisive question is not whether CAS can wrap a language model. It is
whether, with no model attached at all, the architecture still produces the
conclusion. So: disconnect everything, hand the processor problems already
encoded in CAS, and check the ten capabilities that separate a reasoner from a
classifier.

    1  generate intermediate states not supplied in the input
    2  retrieve relevant memories
    3  produce multiple hypotheses
    4  decompose premises
    5  derive conclusions
    6  detect contradictions
    7  recurse into missing prerequisites
    8  backtrack from failed paths
    9  select a justified answer
    10 preserve a complete trace of how it arrived there

Each has a test below. `NoModelInTheLoopTests` establishes the "severed" part
structurally: nothing in the package can reach a model, so no capability
demonstrated here can be borrowed from one.

What this does NOT establish is in the module doc of `docs/working/
cas_rpu_reasoning_processor_2026_08_28.md`, and should be read with it. In
particular: a trivial graph solver also answers these items, so passing this
suite shows the architecture *reasons natively*, not that CAS structure is
necessary or superior for the task.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "scripts" / "cas_rpu"
sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from cmb import CognitiveMemoryBoard, Tier  # noqa: E402
from rpm import Terminal  # noqa: E402

from foundations import focused_profile  # noqa: E402
from runtime import EXPERIENCE_CELL, Phase, Problem, ReasoningProcessor  # noqa: E402
from workspace import Status  # noqa: E402


def processor(memory=None):
    return ReasoningProcessor(focused_profile("F2|A", 0.9), memory)


#: A four-hop chain with two associative decoys. The decoys are reachable by
#: `co_occurs`, so `^8` surfaces them and `^6` must throw them out.
LADDER = Problem(
    name="ladder",
    relation="leads_to",
    premises=(
        ("VS", "leads_to", "QS"),
        ("QS", "leads_to", "IU"),
        ("IU", "leads_to", "TR"),
        ("TR", "leads_to", "NX"),
        ("VS", "co_occurs", "DE"),   # decoy: wrong relation on the first link
        ("DE", "leads_to", "NX"),
        ("VS", "leads_to", "KP"),
        ("KP", "co_occurs", "NX"),   # decoy: wrong relation on the second link
    ),
    query=("VS", "NX"),
    target_channel="F2|A",
)


class NoModelInTheLoopTests(unittest.TestCase):
    """The umbilical cord is not merely unused -- it is absent."""

    FORBIDDEN = (
        "openai", "anthropic", "ollama", "transformers", "torch", "requests",
        "httpx", "urllib", "socket", "http.client", "runners", "wrap",
    )

    def test_no_module_in_the_package_can_reach_a_model_or_the_network(self):
        for path in sorted(PACKAGE.glob("*.py")):
            source = path.read_text()
            for banned in self.FORBIDDEN:
                self.assertNotIn(
                    f"import {banned}",
                    source,
                    f"{path.name} imports {banned}: the cord is still attached",
                )

    def test_the_package_imports_only_stdlib_and_cas_organs(self):
        allowed = {
            "__future__", "dataclasses", "enum", "math", "sys", "pathlib",
            "itertools", "typing", "collections", "re", "random", "hashlib",
            "json", "string", "argparse", "statistics",
            # CAS organs, themselves model-free
            "cjt_sim", "cmb", "cdab", "rpm",
            # this package
            "banks", "foundations", "workspace", "runtime", "events", "encoder",
            "organism", "revision", "controls", "ablations", "scoring", "history",
            "session_types", "sessions",
        }
        for path in sorted(PACKAGE.glob("*.py")):
            for line in path.read_text().splitlines():
                line = line.strip()
                if line.startswith("from ") and " import " in line:
                    module = line.split()[1].split(".")[0]
                    self.assertIn(module, allowed, f"{path.name}: {line}")


class TenCapabilityTests(unittest.TestCase):
    """One test per capability on the list."""

    def test_1_generates_intermediate_states_not_supplied_in_the_input(self):
        """`VS -> NX` appears nowhere in the premises. The processor makes it."""
        episode = processor().run(LADDER)
        self.assertIs(episode.terminal, Terminal.CONCLUDED)
        self.assertNotIn(
            ("VS", "leads_to", "NX"), LADDER.premises
        )
        self.assertIsNotNone(episode.conclusion)
        self.assertIs(episode.conclusion.status, Status.DERIVED)
        self.assertEqual(str(episode.conclusion), "VS ->[leads_to] NX")

    def test_2_retrieves_relevant_memories(self):
        memory = CognitiveMemoryBoard()
        memory.write(EXPERIENCE_CELL, 0.8, Tier.CONSTITUTIONAL)
        episode = processor(memory).run(LADDER)
        fetch = next(s for s in episode.trace if s.phase is Phase.FETCH)
        self.assertFalse(fetch.data["lacuna"])
        self.assertIn("charge", fetch.note)

    def test_2b_an_empty_cell_is_reported_as_a_lacuna_not_a_weak_memory(self):
        episode = processor(CognitiveMemoryBoard()).run(LADDER)
        fetch = next(s for s in episode.trace if s.phase is Phase.FETCH)
        self.assertTrue(fetch.data["lacuna"])

    def test_3_produces_multiple_hypotheses(self):
        episode = processor().run(LADDER)
        self.assertGreaterEqual(len(episode.candidates), 2)
        associate = next(s for s in episode.trace if s.phase is Phase.ASSOCIATE)
        self.assertGreaterEqual(len(associate.data["candidates"]), 2)

    def test_4_decomposes_premises_into_named_constituents(self):
        episode = processor().run(LADDER)
        self.assertTrue(episode.decompositions)
        for decomposition in episode.decompositions:
            self.assertEqual(
                len(decomposition.required), decomposition.candidate.hops
            )
            self.assertTrue(
                all("|leads_to|" in link for link in decomposition.required)
            )

    def test_5_derives_a_conclusion_from_support_it_names(self):
        episode = processor().run(LADDER)
        self.assertEqual(
            episode.conclusion.support,
            ("VS|leads_to|QS", "QS|leads_to|IU", "IU|leads_to|TR", "TR|leads_to|NX"),
        )

    def test_6_detects_contradictions(self):
        problem = Problem(
            "contra",
            "leads_to",
            (("VS", "leads_to", "QS"), ("QS", "leads_to", "IU")),
            ("VS", "IU"),
            negated_premises=(("QS", "leads_to", "IU"),),
        )
        episode = processor().run(problem)
        self.assertIs(episode.terminal, Terminal.INADMISSIBLE)
        self.assertIn("QS|leads_to|IU", episode.workspace.contradictions())

    def test_7_recurses_into_a_missing_prerequisite(self):
        """The block becomes a sub-desire and the planner descends into it."""
        problem = Problem(
            "gap",
            "leads_to",
            (("VS", "leads_to", "QS"), ("AA", "leads_to", "IU")),
            ("VS", "IU"),
        )
        episode = processor().run(problem)
        self.assertIs(episode.terminal, Terminal.NEEDS_INFORMATION)
        depths = [record.depth for record in episode.rpm_trace]
        self.assertIn(1, depths, "the planner named the block but never descended")
        descended = [r.goal for r in episode.rpm_trace if r.depth == 1]
        self.assertTrue(any("acquire" in name for name in descended))

    def test_7b_the_abstention_names_the_gap_it_would_need_closed(self):
        problem = Problem(
            "gap",
            "leads_to",
            (("VS", "leads_to", "QS"), ("AA", "leads_to", "IU")),
            ("VS", "IU"),
        )
        episode = processor().run(problem)
        self.assertIn("VS|leads_to|IU", episode.workspace.lacunae())
        decompose = next(s for s in episode.trace if s.phase is Phase.DECOMPOSE)
        self.assertEqual(decompose.data["forward"], ["QS"])
        self.assertEqual(decompose.data["backward"], ["AA"])

    def test_8_backtracks_from_a_failed_path(self):
        """Both decoys are surfaced by association and thrown out by `^6`."""
        episode = processor().run(LADDER)
        self.assertGreaterEqual(len(episode.backtracks), 1)
        self.assertTrue(
            any("missing" in note for note in episode.backtracks),
            episode.backtracks,
        )

    def test_9_selects_a_justified_answer(self):
        episode = processor().run(LADDER)
        self.assertEqual(episode.answer, "YES")
        tree = episode.justification
        self.assertEqual(tree["status"], "derived")
        self.assertEqual(len(tree["support"]), 4)
        for leaf in tree["support"]:
            self.assertEqual(leaf["support"], [])  # bottoms out in premises

    def test_10_preserves_a_complete_trace(self):
        episode = processor().run(LADDER)
        phases = [step.phase for step in episode.trace]
        for phase in Phase:
            self.assertIn(phase, phases, f"{phase.value} missing from the trace")
        ticks = [step.tick for step in episode.trace]
        self.assertEqual(ticks, sorted(ticks))
        self.assertEqual(len(set(ticks)), len(ticks))


class HonestyTests(unittest.TestCase):
    """The capabilities the processor must NOT claim."""

    def test_it_does_not_answer_a_question_the_premises_cannot_settle(self):
        problem = Problem(
            "unsettleable",
            "leads_to",
            (("VS", "leads_to", "QS"),),
            ("VS", "ZZ"),
        )
        episode = processor().run(problem)
        self.assertNotEqual(episode.answer, "YES")
        self.assertIsNone(episode.conclusion)

    def test_an_associative_route_alone_never_becomes_a_conclusion(self):
        """Every link of the only route is `co_occurs`. Association is present,
        deduction is not, and the processor must not confuse the two."""
        problem = Problem(
            "assoc_only",
            "leads_to",
            (("VS", "co_occurs", "DE"), ("DE", "co_occurs", "NX")),
            ("VS", "NX"),
        )
        episode = processor().run(problem)
        self.assertNotEqual(episode.answer, "YES")
        self.assertGreaterEqual(len(episode.candidates), 1)
        self.assertTrue(episode.backtracks)

    def test_the_conclusion_never_rests_on_a_hypothesis(self):
        episode = processor().run(LADDER)
        for pid in episode.conclusion.support:
            self.assertIn(
                episode.workspace.props[pid].status,
                (Status.FACT, Status.ASSUMPTION, Status.DERIVED),
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
