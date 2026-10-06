"""CAS-RPU → CNCM interchange: a lesson told to the organism is used by the independent kernel.

HELM ability 7, roadmap step 6. The CNCM kernel is the frozen Codex reference
implementation at `eb99855`, mounted read-only and pinned by content. These
tests skip when it is not mounted, unless `CAS_RPA_REQUIRED=1` (CI mounts the
commit), in which case a skip is a failure. The fixtures follow
`docs/working/helm_interchange_and_fixtures_draft_2026_10_06.md` §2; F06 is
asserted as the divergence it is, never mapped away.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))
sys.path.insert(0, str(REPO / "scripts" / "cas_memory"))

import cncm_interchange as ix  # noqa: E402
from events import ask, associate, fact, hypothesis, lesson, negation, retract, unlesson  # noqa: E402
from history import Stream  # noqa: E402
from revision import replay  # noqa: E402

import tempfile  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))  # the hand-built §13 stream of test_cas_rpu_lessons

E = "rel_a"


class _NeedsCncm(unittest.TestCase):
    def setUp(self):
        try:
            self.cncm = ix.load_cncm()
        except ix.CncmUnavailable as exc:
            if os.environ.get("CAS_RPA_REQUIRED") == "1":
                raise AssertionError(f"CAS_RPA_REQUIRED=1 but the CNCM path cannot run: {exc}")
            self.skipTest(str(exc))

    def state_after(self, events, stream_id="s"):
        """Fold the organism's accepted rows for `events` into a CNCM state."""
        with tempfile.TemporaryDirectory() as d:
            s = Stream.genesis(d, organism_id="o", context_id=stream_id)
            s.run(events)
            envs, rejected = ix.export_rows(s.rows, s.identity.stream_id)
        st = ix.CncmState()
        for e in envs:
            st.fold(e)
        return st, rejected

    def verdict(self, events, pair, **kw):
        st, _ = self.state_after(events)
        return ix.ask_cncm(self.cncm, st, pair, **kw)


class VersionAndExportTests(_NeedsCncm):
    def test_the_loaded_kernel_is_the_pinned_one(self):
        v = ix.loaded_version()
        self.assertTrue(v["matches_pin"], v)
        self.assertEqual(v["combined"], ix.CNCM_MODULES_SHA256)

    def test_export_carries_explicit_polarity_and_rejects_guesses_and_associations(self):
        with tempfile.TemporaryDirectory() as d:
            s = Stream.genesis(d, organism_id="o", context_id="c")
            s.run([fact("A", "B"), negation("A", "C"), hypothesis("B", "C"), associate("C", "D"), lesson(E), fact("P", "Q", relation=E), retract("A", "B"), ask("A", "B")])
            envs, rejected = ix.export_rows(s.rows, s.identity.stream_id)
        kinds = [(e["event_type"], e.get("proposition", {}).get("polarity"), e.get("proposition", {}).get("predicate") or e.get("rule", {}).get("rule_id")) for e in envs]
        self.assertEqual(kinds, [("FACT", True, "leads_to"), ("FACT", False, "leads_to"), ("LESSON", None, "lesson_rel_a"), ("FACT", True, "rel_a"), ("RETRACT", True, "leads_to")])
        self.assertEqual(sorted(r["code"] for r in rejected), ["E-IX-PROPOSED", "E-IX-RELATION"])
        self.assertTrue(all(e["schema_version"] == ix.ENVELOPE_SCHEMA and e["source"]["engine"] == "cas_rpu" for e in envs))

    def test_import_refuses_a_defaulted_polarity_and_a_negative_retract(self):
        st = ix.CncmState()
        with self.assertRaises(ix.InterchangeError) as ctx:
            st.fold({"schema_version": ix.ENVELOPE_SCHEMA, "event_id": "x", "event_type": "FACT", "proposition": {"predicate": "leads_to", "arguments": ["A", "B"]}})
        self.assertEqual(ctx.exception.code, "E-IX-POLARITY")
        with self.assertRaises(ix.InterchangeError) as ctx:
            st.fold({"schema_version": ix.ENVELOPE_SCHEMA, "event_id": "y", "event_type": "RETRACT", "proposition": {"predicate": "leads_to", "arguments": ["A", "B"], "polarity": False}})
        self.assertEqual(ctx.exception.code, "E-IX-NEG-RETRACT")


class FixtureTests(_NeedsCncm):
    def test_f01_assertion_and_transitive_chain(self):
        self.assertEqual(self.verdict([fact("A", "B")], ("A", "B")).verdict, "YES")
        self.assertEqual(self.verdict([fact("A", "B"), fact("B", "C"), fact("C", "D")], ("A", "D")).verdict, "YES")

    def test_f02_explicit_denial_without_a_route_is_no_by_the_negative_query(self):
        a = self.verdict([fact("A", "B"), negation("A", "C")], ("A", "C"))
        self.assertEqual((a.verdict, a.positive_status, a.negative_status), ("NO", "NEEDS_INFORMATION", "CONCLUDED"))

    def test_f03_absence_is_unknown(self):
        a = self.verdict([fact("A", "B")], ("A", "C"))
        self.assertEqual((a.verdict, a.positive_status, a.negative_status), ("UNKNOWN", "NEEDS_INFORMATION", "NEEDS_INFORMATION"))

    def test_f05_conflict_on_the_route_and_a_denied_sound_chain_are_inadmissible(self):
        self.assertEqual(self.verdict([fact("A", "B"), fact("B", "C"), negation("B", "C")], ("A", "C")).verdict, "INADMISSIBLE")
        self.assertEqual(self.verdict([fact("A", "B"), fact("B", "C"), negation("A", "C")], ("A", "C")).verdict, "INADMISSIBLE")

    def test_f06_conflict_off_the_route_is_a_measured_divergence_never_mapped_away(self):
        """The oracle answers YES (the dispute is not on any route); CNCM refuses
        every question while a contradiction exists in the packet. The adapter
        reports INADMISSIBLE with `conflict_elsewhere=True`; it does not coerce."""
        events = [fact("A", "B"), fact("B", "C"), fact("X", "B"), negation("X", "B")]
        self.assertEqual(replay(events + [ask("A", "C")], False).expectations[0].verdict.value, "YES")
        a = self.verdict(events, ("A", "C"))
        self.assertEqual((a.verdict, a.conflict_elsewhere), ("INADMISSIBLE", True))

    def test_f07_f08_a_retracted_given_takes_its_dependents_with_it(self):
        self.assertEqual(self.verdict([fact("A", "B"), fact("B", "C"), retract("B", "C")], ("A", "C")).verdict, "UNKNOWN")
        self.assertEqual(self.verdict([fact("A", "B"), fact("B", "C"), retract("B", "C"), fact("B", "C")], ("A", "C")).verdict, "YES")

    def test_f09_f10_the_lesson_crosses_and_is_used_and_its_retraction_crosses_too(self):
        chain = [fact("A", "B", relation=E), fact("B", "C")]
        self.assertEqual(self.verdict(chain, ("A", "C")).verdict, "UNKNOWN", "CNCM alone: the foreign edge is not chained")
        self.assertEqual(self.verdict(chain + [lesson(E)], ("A", "C")).verdict, "YES", "with the imported lesson")
        self.assertEqual(self.verdict(chain + [lesson(E), fact("P", "Q", relation=E), fact("Q", "R")], ("P", "R")).verdict, "YES", "a new instance")
        self.assertEqual(self.verdict(chain + [lesson(E), unlesson(E)], ("A", "C")).verdict, "UNKNOWN", "retracted lesson")
        self.assertEqual(self.verdict(chain + [lesson("rel_b")], ("A", "C")).verdict, "UNKNOWN", "a lesson for another relation")
        self.assertEqual(self.verdict(chain + [lesson(E), hypothesis("C", "D")], ("A", "D")).verdict, "UNKNOWN", "a guess never crosses as a fact")

    def test_scoping_whole_stream_exposes_the_global_conflict_and_component_scoping_does_not(self):
        events = [fact("A", "B"), fact("B", "C"), fact("X", "Y"), negation("X", "Y")]   # the dispute is in another component
        whole = self.verdict(events, ("A", "C"), scope="whole")
        comp = self.verdict(events, ("A", "C"), scope="component")
        self.assertEqual((whole.verdict, whole.conflict_elsewhere), ("INADMISSIBLE", True))
        self.assertEqual((comp.verdict, comp.conflict_elsewhere), ("YES", False))


class StreamAgreementTests(_NeedsCncm):
    def test_the_hand_built_lesson_stream_agrees_except_where_no_divergence_is_predicted(self):
        """The §13 end-to-end stream of test_cas_rpu_lessons: every probe agrees
        with the oracle through CNCM, including the refused retract of a derived
        twin (nothing to export) and the denial of an entailed pair."""
        from test_cas_rpu_lessons import STREAM
        truth = replay(STREAM, False)
        cmp = ix.compare_stream(self.cncm, STREAM, truth.expectations, stream_id="hand")
        self.assertEqual(cmp.summary()["disagree"], 0, cmp.disagree)
        self.assertEqual(cmp.summary()["probes"], 13)


if __name__ == "__main__":
    unittest.main()
