"""The multi-session harness: one fresh process per session, the oracle fixed before any process runs.

Evaluation plan sections 3.2, 4.9 and 6. These tests use a small hand-built
`SeedStream` (three sessions, three episodes) so the harness is tested
independently of the generator, and run the real child processes: every
claim here was produced by separate interpreters sharing only a directory.
The RPA path runs when the pinned checkout is mounted and is reported as
not run otherwise.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))
sys.path.insert(0, str(REPO / "scripts" / "cas_memory"))

import session_harness as H  # noqa: E402
from events import ask, fact, hypothesis, negation, retract  # noqa: E402
from history import CURRENT, Identity, MemoryError_, Stream  # noqa: E402
from revision import StreamDifficulty, replay  # noqa: E402
from session_types import EpisodeSpan, SeedStream, SessionSet  # noqa: E402


def build(seed: int = 0, closed: bool = False, twin: bool = False) -> SeedStream:
    """Three sessions. Session 1 teaches A→B→C→D (held) and P→Q→R (held) and tells a
    guess; session 2 re-asks A→D across the boundary, retracts B→C, denies P→Q;
    session 3 revives B→C and re-asks everything. The twin replaces the teaching
    chain's FACTs with the same number of non-connecting FACTs over the same tokens."""
    gap = "NO" if closed else "UNKNOWN"
    s0 = [fact("A", "B"), fact("B", "C"), fact("U", "V"), fact("C", "D"), ask("A", "D"),
          fact("P", "Q"), fact("Q", "R"), ask("P", "R"), hypothesis("M", "N")]
    if twin:
        s0 = [fact("A", "B"), fact("V", "U"), fact("U", "V"), fact("D", "C"), ask("A", "D"),
              fact("P", "Q"), fact("Q", "R"), ask("P", "R"), hypothesis("M", "N")]
    s1 = [ask("A", "D"), ask("D", "A"), retract("B", "C"), ask("A", "D"), negation("P", "Q"), ask("P", "R")]
    s2 = [fact("B", "C"), ask("A", "D"), ask("P", "R"), ask("R", "P")]
    events = tuple(s0 + s1 + s2)
    n0, n1 = len(s0), len(s0) + len(s1)
    truth = replay(events, closed)
    episodes = (
        EpisodeSpan("X-hold", "X", "control", 0, n0 + 2, n0, gap if twin else "YES", True),
        EpisodeSpan("X-revive", "X", "diagnostic", n0 + 2, n1 + 2, n1 + 1, gap if twin else "YES", True),
        EpisodeSpan("T-exact", "T", "control", 5, n1 + 4, n1 + 2, "INADMISSIBLE", True),
    )
    return SeedStream(seed, f"ctx{seed}", closed, events, (n0, n1), episodes,
                      truth.expectations, truth.withdrawn, truth.refused, twin_of=seed if twin else None)


def session_set(closed: bool = False, seeds=(0,)) -> SessionSet:
    return SessionSet("fixture", "fixture", 0, StreamDifficulty(), 3, closed,
                      tuple(build(s, closed) for s in seeds), tuple(build(s, closed, twin=True) for s in seeds))


class _Root(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="helm-harness-"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)


class CleanRunTests(_Root):
    def test_every_path_agrees_with_the_whole_stream_oracle_in_both_worlds_and_the_record_path_hits_across_the_restart(self):
        for closed in (False, True):
            sset = session_set(closed)
            results = H.evaluate(sset, self.root / ("closed" if closed else "open"), paths=H.PATHS, faults=False)
            for path in ("recompute", "walk", "record_dep"):
                r = results[path]
                self.assertIsNone(r.skipped)
                self.assertTrue(r.matrix.perfect(path), (closed, path, [p.detail or (p.expected, p.got) for p in r.matrix.failures[path]]))
                self.assertEqual(r.unanswered, 0)
                self.assertEqual(r.retention["stale_hits"], 0)
                self.assertEqual(r.unseen_hits, 0)
                self.assertEqual(r.twin_designed, {"total": 3, "ok": 3}, "untaught twins answer GAP on every designed probe")
                self.assertEqual(r.heartbeat_faults, 0)
            walk, dep = results["walk"], results["record_dep"]
            self.assertEqual(walk.routes, {"disabled": 18})
            self.assertEqual(dep.routes.get("hit"), 1, "the cross-boundary re-ask of the held conclusion was served from the record")
            self.assertEqual(dep.retention, {"total": 2, "ok": 2, "hits": 1, "stale_hits": 0})
            self.assertEqual(len(dep.runs[0].sessions), 3, "three processes, one per session")
            self.assertTrue(all(s.label == "session" for s in dep.runs[0].sessions))
            self.assertEqual(len(dep.restore_ns), 4, "two restores per stream, primary and twin")
            self.assertIn("level (a)", dep.survival)
            rpa = results["record_rpa"]
            if rpa.skipped:
                self.assertIn("RPA", rpa.skipped)
            else:
                self.assertTrue(rpa.matrix.perfect("record_rpa"))
                self.assertEqual(rpa.routes, dep.routes, "the atlas changed no route: the pre-registered zero")

    def test_restore_validation_precedes_the_first_answer_in_every_later_session(self):
        run = H.run_seed(build(0), "record_dep", self.root)
        for rec in run.sessions[1:]:
            self.assertTrue(rec.done["restore_before_first_answer"])
            self.assertIsNotNone(rec.done["restore_ns"])
            self.assertEqual(rec.done["recovered_from"], CURRENT, "served from the current document, no fallback")
            self.assertEqual(rec.done["recovery_failures"], [])
        self.assertFalse(any(c["ok"] is False for c in run.fault_checks))

    def test_the_report_and_json_render(self):
        sset = session_set()
        results = H.evaluate(sset, self.root, paths=("recompute", "walk"), faults=False)
        text = H.render(results, sset)
        self.assertIn("retention probes", text)
        self.assertIn("STALE HITS 0", text)
        blob = H.to_json(results, sset)
        json.dumps(blob)
        self.assertEqual(blob["paths"]["walk"]["retention"]["stale_hits"], 0)

    def test_separate_contexts_never_share_a_store(self):
        """Two seeds are two contexts. A store written for one refuses to answer
        for the other (E-MEM-001), so no assumption crosses between situations."""
        a, b = build(0), build(1)
        H.run_seed(a, "record_dep", self.root)
        H.run_seed(b, "record_dep", self.root)
        dir_a = self.root / "open" / "record_dep" / "seed0-open"
        dir_b = self.root / "open" / "record_dep" / "seed1-open"
        ident_b = Stream.restore(dir_b).identity
        with self.assertRaises(MemoryError_) as ctx:
            Stream.restore(dir_a, expected=ident_b)
        self.assertEqual(ctx.exception.code, "E-MEM-001")


class FaultScheduleTests(_Root):
    """Each fault kind on the fixture, at a boundary, on the record path. The
    pass condition of plan section 4.9 is checked by the harness and asserted
    here; verdicts after recovery must still agree with the oracle."""

    def _run(self, kind: str, boundary: int = 1, path: str = "record_dep"):
        run = H.run_seed(build(0), path, self.root / kind, fault={"kind": kind, "boundary": boundary})
        score, unanswered = H.score_run(build(0), run)
        return run, score, unanswered

    def _passed(self, run, kind: str):
        checks = [c for c in run.fault_checks if c["kind"] == kind]
        self.assertTrue(checks, f"no {kind} check recorded: {run.fault_checks}")
        self.assertTrue(all(c["ok"] for c in checks), checks)
        return checks

    def test_kill_before_the_commit_boundary_loses_only_the_unacknowledged_event(self):
        run, score, unanswered = self._run("kill-before-write")
        self.assertEqual([s.label for s in run.sessions], ["session", "recovery", "session", "session"])
        self.assertEqual(run.sessions[0].returncode, 137)
        rec = self._passed(run, "recovery")[0]
        self.assertEqual(rec["restored_seq"], rec["acknowledged_seq"], "exactly the acknowledged prefix")
        self.assertTrue(all(p.verdict_ok for p in score.probes) and not unanswered)
        self.assertTrue(all(c["ok"] for c in run.fault_checks if c["kind"] == "recovery-probe"))

    def test_kill_during_the_document_write_leaves_the_previous_document_standing(self):
        run, score, _ = self._run("kill-before-replace", boundary=2)
        self._passed(run, "recovery")
        self.assertTrue(all(p.verdict_ok for p in score.probes))

    def test_kill_after_publication_before_acknowledgment_recovers_the_newer_document(self):
        """The host never saw the ack, so its prefix is one short of the document's.
        The restore reports a document AHEAD of the acknowledged prefix: that is not
        a loss (nothing acknowledged is missing), and the retried event is detected as
        already recorded (same id) and acknowledged once."""
        for kind in ("kill-after-replace", "kill-after-save"):
            run, score, unanswered = self._run(kind, boundary=1)
            rec = [c for c in run.fault_checks if c["kind"] == "recovery"][0]
            self.assertEqual(rec["restored_seq"], rec["acknowledged_seq"] + 1, kind)
            self.assertTrue(all(p.verdict_ok for p in score.probes) and not unanswered, kind)

    def test_kill_during_restore_then_restore_again(self):
        run, score, _ = self._run("kill-during-restore", boundary=1)
        self.assertEqual(run.sessions[1].returncode, 137)
        self.assertEqual(run.sessions[2].returncode, 0)
        self.assertTrue(all(p.verdict_ok for p in score.probes))

    def test_redelivery_in_process_and_after_restart_is_exactly_once(self):
        run, _, _ = self._run("redeliver")
        self.assertEqual(self._passed(run, "redeliver")[0]["rows_unchanged"], True)
        run, _, _ = self._run("redeliver-restart")
        c = self._passed(run, "redeliver-restart")[0]
        self.assertEqual((c["accepted"], c["rows_added"]), (True, 0), "recognised as a retry: acknowledged again, applied once")

    def test_out_of_order_delivery_is_refused_and_the_in_order_retry_lands(self):
        run, score, _ = self._run("swap", boundary=1)
        self.assertEqual(self._passed(run, "swap")[0]["code"], "E-MEM-002")
        self.assertTrue(all(p.verdict_ok for p in score.probes))

    def test_a_torn_or_corrupt_current_document_falls_back_to_the_retained_copy_with_nothing_lost(self):
        for kind in ("torn-current", "corrupt-current"):
            run, score, unanswered = self._run(kind)
            rec = [s for s in run.sessions if s.session == 1][0]
            self.assertNotEqual(rec.done["recovered_from"], CURRENT, kind)
            self.assertTrue(rec.done["recovery_failures"], "the damage was detected and named")
            self.assertEqual(rec.done["last_seq"] - len(rec.acks), run.sessions[0].acks[-1]["ack"], "nothing acknowledged was lost")
            self.assertTrue(all(p.verdict_ok for p in score.probes) and not unanswered, kind)

    def test_history_lost_beyond_retention_stops_serving_and_names_the_boundary(self):
        run, score, unanswered = self._run("corrupt-both")
        self.assertIsNotNone(run.stopped)
        self.assertIn("E-MEM-046", run.stopped)
        self.assertIn("lost", run.stopped)
        self.assertTrue(unanswered, "the later probes were never answered — reported, not invented")
        self.assertTrue(all(p.verdict_ok for p in score.probes), "what was answered before the loss was right")

    def test_an_incompatible_schema_is_refused_with_the_untouched_history_still_readable(self):
        run, _, _ = self._run("schema-bump")
        self.assertIn("E-MEM-010", run.stopped or "")

    def test_a_retention_limit_stops_the_stream_safely_and_the_next_session_continues(self):
        run, score, unanswered = self._run("quota", boundary=1)
        q = self._passed(run, "quota")[0]
        self.assertEqual(q["refused"], "E-MEM-050")
        self.assertEqual([s.label for s in run.sessions], ["session", "recovery", "session", "session"])
        self.assertTrue(all(p.verdict_ok for p in score.probes) and not unanswered)

    def test_missing_index_is_reported_not_applicable(self):
        run, _, _ = self._run("missing-index")
        c = [c for c in run.fault_checks if c["kind"] == "missing-index"][0]
        self.assertFalse(c["applicable"])
        self.assertIn("rebuilt", c["reason"])


class ReplacementMechanismTests(_Root):
    def test_every_session_restores_from_the_second_location_after_the_local_store_is_destroyed(self):
        mirror = self.root / "remote"
        run = H.run_seed(build(0), "record_dep", self.root / "local", mirror=str(mirror), replacement=True)
        self.assertEqual(len(run.sessions), 3)
        self.assertTrue(all(s.returncode == 0 for s in run.sessions))
        score, unanswered = H.score_run(build(0), run)
        self.assertTrue(all(p.verdict_ok for p in score.probes) and not unanswered)
        self.assertIn("mirrored to", run.sessions[-1].done["survival"])
        self.assertTrue(any(mirror.rglob(CURRENT)))


if __name__ == "__main__":
    unittest.main()
