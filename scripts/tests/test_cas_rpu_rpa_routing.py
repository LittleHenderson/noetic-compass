"""Record-first with RPA: the atlas may only remove candidates, and here it removes none.

The fourth path of the directive's comparison. The atlas is the RPA model from
the mounted checkout at `eb99855`, imported (never copied) and fed a projection
of one organism's workspace. These tests skip, with the reason, when the
checkout is not mounted; the experiment then reports the path as not run.

Pre-registered expectation: zero difference from the dependency-mode
record-first path. A measured zero is reported as zero.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))
sys.path.insert(0, str(REPO / "scripts" / "cas_memory"))

import rpa_adapter  # noqa: E402
from events import ask, fact, hypothesis, negation, retract  # noqa: E402
from organism import Organism, OrganismError  # noqa: E402
from revision import generate_revision_set  # noqa: E402

CHAIN = [fact("A", "B"), fact("B", "C"), fact("C", "D")]


class _NeedsRpa(unittest.TestCase):
    def setUp(self):
        try:
            self.rpa = rpa_adapter.load_rpa()
        except rpa_adapter.RpaUnavailable as exc:
            self.skipTest(str(exc))


class AtlasProjectionTests(_NeedsRpa):
    def test_the_projection_validates_under_the_atlas_model_and_maps_every_status(self):
        org = Organism(record_first=True, record_invalidation="dependency")
        org.run_stream(CHAIN + [hypothesis("X", "Y"), ask("A", "D")])
        atlas = rpa_adapter.organism_atlas(org, "s", self.rpa)
        nodes = atlas.node_map()
        self.assertEqual(atlas.current_state_id, "present")
        self.assertEqual(nodes["rec-A.leads_to.D"].status, self.rpa.NodeStatus.VERIFIED)
        self.assertEqual(nodes["rec-A.leads_to.B"].status, self.rpa.NodeStatus.OBSERVED)
        self.assertEqual(nodes["rec-X.leads_to.Y"].status, self.rpa.NodeStatus.HYPOTHETICAL)
        self.assertEqual(atlas.hypothesis_branch_id, "rec-X.leads_to.Y")
        self.assertEqual(set(nodes["rec-A.leads_to.D"].evidence_refs), {"rec-A.leads_to.B", "rec-B.leads_to.C", "rec-C.leads_to.D"})
        org.consume(negation("B", "C"))
        atlas2 = rpa_adapter.organism_atlas(org, "s", self.rpa)
        self.assertEqual(atlas2.node_map()["rec-B.leads_to.C"].status, self.rpa.NodeStatus.UNKNOWN, "contradicted")
        self.assertEqual(atlas2.node_map()["rec-A.leads_to.D"].status, self.rpa.NodeStatus.REJECTED, "cascaded")

    def test_importing_the_atlas_loads_no_model_library(self):
        self.assertNotIn("torch", sys.modules)

    def test_the_organism_never_imports_an_atlas(self):
        """The narrower is injected; no import line in the reasoning package names the atlas."""
        for path in (REPO / "scripts" / "cas_rpu").glob("*.py"):
            for line in path.read_text().splitlines():
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")):
                    for word in ("rpa", "atlas", "cncm"):
                        self.assertNotIn(word, stripped.lower(), f"{path.name}: {stripped}")


class NarrowingTests(_NeedsRpa):
    def test_narrowing_keeps_a_verified_record_and_drops_nothing_valid(self):
        org = Organism(record_first=True, record_invalidation="dependency")
        n = rpa_adapter.RpaNarrower(org, "s", self.rpa)
        org.record_narrow = n
        org.run_stream(CHAIN + [ask("A", "D")])
        self.assertEqual(org.consume(ask("A", "D")).route, "hit")
        self.assertEqual(n.stats["removed"], 0)
        org.consume(retract("B", "C"))
        self.assertEqual(org.consume(ask("A", "D")).route, "miss", "standing was withdrawn before the atlas was consulted")

    def test_a_narrower_that_adds_a_candidate_is_refused(self):
        org = Organism(record_first=True, record_narrow=lambda key, cands: cands + ("Z|leads_to|Q",))
        org.run_stream(CHAIN + [ask("A", "D")])
        with self.assertRaises(OrganismError) as ctx:
            org.consume(ask("A", "D"))
        self.assertEqual(ctx.exception.code, "E-ORG-007")

    def test_a_narrower_that_removes_everything_forces_the_walk(self):
        org = Organism(record_first=True, record_narrow=lambda key, cands: ())
        org.run_stream(CHAIN + [ask("A", "D")])
        r = org.consume(ask("A", "D"))
        self.assertEqual((r.verdict, r.route), ("YES", "rejected:narrowed-out"))


class ZeroDifferenceTests(_NeedsRpa):
    def test_rpa_routing_equals_dependency_mode_on_every_probe_and_every_route(self):
        """The pre-registered expectation. If this ever fails, the atlas did something
        the dependency check did not, and that is the finding to report."""
        for closed in (False, True):
            sset = generate_revision_set(24, seed=20261006, closed_world=closed)
            removed = 0
            for item in sset.items:
                dep = Organism(closed_world=closed, record_first=True, record_invalidation="dependency")
                rpa = Organism(closed_world=closed, record_first=True, record_invalidation="dependency")
                narrower = rpa_adapter.RpaNarrower(rpa, item.item_id, self.rpa)
                rpa.record_narrow = narrower
                a = dep.run_stream(item.events)
                b = rpa.run_stream(item.events)
                self.assertEqual(
                    [(r.verdict, r.lacunae, r.contested, r.route) for r in a if r.verdict],
                    [(r.verdict, r.lacunae, r.contested, r.route) for r in b if r.verdict],
                    item.item_id,
                )
                removed += narrower.stats["removed"]
            self.assertEqual(removed, 0, "the atlas removed a candidate the dependency check kept")


if __name__ == "__main__":
    unittest.main()
