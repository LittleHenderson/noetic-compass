"""Lasting memory, survival level (a): a clean process exit and a restart on the same machine.

The first result the lasting-memory directive asks for, on development data:
teach a fact, show it changes a later answer, save the accepted state,
terminate the process, show the same behaviour after restart without
teaching it again; then correct or retract it and show every dependent answer
changes, before and after restart. The independent reference is the recompute
control over the same rows.

What these tests do NOT show (contract M0.1): survival of machine termination
or replacement (level b), retention beyond the restarts performed here, or
anything about a frozen held-out set. They are preparation and a development
demonstration, labelled so in the CHANGELOG.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

import history  # noqa: E402
from ablations import NoCascade  # noqa: E402
from controls import ctl_recompute  # noqa: E402
from events import ask, associate, fact, hypothesis, negation, retract  # noqa: E402
from history import (  # noqa: E402
    CURRENT,
    Identity,
    MemoryError_,
    Stream,
    canonical_json,
    digest,
    reference_digest,
)

K = lambda s, o: f"{s}|leads_to|{o}"  # noqa: E731
CHAIN = [fact("A", "B"), fact("B", "C"), fact("C", "D")]

#: Run in a fresh operating-system process: restore, act, print a JSON report.
CHILD = r"""
import json, sys
sys.path.insert(0, {cas!r}); sys.path.insert(0, {ccb!r})
for banned in ("torch", "openai", "anthropic", "requests"):
    assert banned not in sys.modules
from history import Stream
from controls import ctl_recompute
from events import Event, EventKind
stream = Stream.restore({path!r}, reference=ctl_recompute)
out = []
for kind, s, o in {actions!r}:
    r = stream.commit(Event(EventKind(kind), s, o))
    out.append({{"verdict": r.verdict, "withdrawn": list(r.withdrawn), "accepted": r.accepted, "code": r.code}})
print(json.dumps({{"out": out, "rows": len(stream.rows), "standing": sorted(stream.organism.standing),
                   "faults": list(stream.organism.faults)}}))
"""


def fresh_process(path: Path, actions: list[tuple[str, str, str]]) -> dict:
    script = CHILD.format(cas=str(REPO / "scripts" / "cas_rpu"), ccb=str(REPO / "scripts" / "ccb_r1"), path=str(path), actions=actions)
    proc = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise AssertionError(f"child failed:\n{proc.stderr}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


class _Tmp(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.dir = Path(self._dir.name) / "stream"

    def tearDown(self):
        self._dir.cleanup()

    def genesis(self, **kw) -> Stream:
        kw.setdefault("organism_id", "org1")
        kw.setdefault("context_id", "ctx1")
        return Stream.genesis(self.dir, **kw)


class RetentionAcrossProcessesTests(_Tmp):
    """The directive's first result, at survival level (a)."""

    def test_a_taught_fact_changes_a_later_answer_after_a_fresh_process_restart(self):
        s = self.genesis()
        self.assertEqual(s.commit(ask("A", "D")).verdict, "UNKNOWN", "before teaching")
        s.run(CHAIN)
        self.assertEqual(s.commit(ask("A", "D")).verdict, "YES", "the teaching changed the answer")
        rows_before = len(s.rows)
        # -- process boundary: nothing is retaught in the child --
        child = fresh_process(self.dir, [("ask", "A", "D")])
        self.assertEqual(child["out"][0]["verdict"], "YES")
        self.assertEqual(child["standing"], [K("A", "D")], "the conclusion is held, not re-derived from a reteach")
        self.assertEqual(child["faults"], [])
        self.assertEqual(child["rows"], rows_before + 1, "the child's ask was committed to the same stream")

    def test_a_retraction_withdraws_dependents_before_and_after_restart(self):
        s = self.genesis()
        s.run(CHAIN + [ask("A", "D"), ask("B", "D")])
        # -- boundary 1: retract in a fresh process --
        child = fresh_process(self.dir, [("retract", "B", "C"), ("ask", "A", "D"), ("ask", "B", "D")])
        self.assertTrue(child["out"][0]["accepted"])
        self.assertEqual(sorted(child["out"][0]["withdrawn"]), [K("A", "D"), K("B", "D")], "every dependent fell")
        self.assertEqual([o["verdict"] for o in child["out"][1:]], ["UNKNOWN", "UNKNOWN"])
        # -- boundary 2: the retraction itself survived --
        child2 = fresh_process(self.dir, [("ask", "A", "D"), ("fact", "B", "C"), ("ask", "A", "D")])
        self.assertEqual([o["verdict"] for o in child2["out"] if o["verdict"]], ["UNKNOWN", "YES"])
        self.assertEqual(child2["standing"], [K("A", "D")])

    def test_a_denial_survives_restart_and_the_old_yes_never_escapes(self):
        s = self.genesis()
        s.run(CHAIN + [ask("A", "D")])
        child = fresh_process(self.dir, [("negation", "B", "C"), ("ask", "A", "D")])
        self.assertEqual(child["out"][0]["withdrawn"], [K("A", "D")])
        self.assertEqual(child["out"][1]["verdict"], "INADMISSIBLE")
        child2 = fresh_process(self.dir, [("ask", "A", "D")])
        self.assertEqual(child2["out"][0]["verdict"], "INADMISSIBLE", "no stale YES through any path after restart")

    def test_the_restored_stream_agrees_with_recompute_on_every_recorded_ask(self):
        s = self.genesis()
        s.run(CHAIN + [ask("A", "D"), associate("D", "E"), ask("A", "E"), retract("C", "D"), ask("A", "D"), fact("C", "D"), ask("A", "D")])
        restored = Stream.restore(self.dir, expected=s.identity, reference=ctl_recompute)
        events = [history._event_from_canonical(r["payload"]) for r in restored.rows]
        run = ctl_recompute(events, False)
        recorded = [r["outcome"]["verdict"] for r in restored.rows if r["type"] == "ASK"]
        self.assertEqual(recorded, [a.verdict for a in run.answers])
        self.assertEqual(reference_digest(restored.organism), reference_digest(s.organism))


class DocumentTests(_Tmp):
    def test_every_commit_leaves_a_sealed_document_that_reads_back(self):
        s = self.genesis()
        s.run(CHAIN)
        doc = json.loads((self.dir / CURRENT).read_bytes())
        body = {k: v for k, v in doc.items() if k != "document_digest"}
        self.assertEqual(digest(body), doc["document_digest"])
        self.assertEqual(doc["header"]["last_committed_seq"], 2)
        self.assertEqual([r["seq"] for r in doc["rows"]], [0, 1, 2])
        self.assertEqual(doc["reference_digest"], reference_digest(s.organism))
        self.assertTrue((self.dir / "history.00000003.json").exists(), "the previous document is retained, numbered by rows")

    def test_canonical_json_refuses_non_finite_numbers(self):
        with self.assertRaises(ValueError):
            canonical_json({"x": float("nan")})

    def test_a_tampered_current_document_falls_back_to_the_newest_verified_copy(self):
        s = self.genesis()
        s.run(CHAIN + [ask("A", "D")])
        current = self.dir / CURRENT
        data = bytearray(current.read_bytes())
        i = data.index(b'"verdict":"YES"')
        data[i:i + len(b'"verdict":"YES"')] = b'"verdict":"NO!"'
        current.write_bytes(bytes(data))
        restored = Stream.restore(self.dir, expected=s.identity)
        self.assertEqual(restored.last_committed_seq, 3, "the retained copy of the same state verified")
        self.assertEqual(restored.commit(ask("A", "D")).verdict, "YES")

    def test_when_nothing_verifies_the_stream_refuses_to_serve(self):
        s = self.genesis()
        s.run(CHAIN)
        for p in self.dir.glob("history.*.json"):
            p.write_bytes(b"{garbage")
        with self.assertRaises(MemoryError_) as ctx:
            Stream.restore(self.dir)
        self.assertEqual(ctx.exception.code, "E-MEM-045")

    def test_a_row_out_of_sequence_is_quarantined_and_restore_stops(self):
        s = self.genesis()
        s.run(CHAIN)
        doc = s.document()
        doc["rows"][1], doc["rows"][2] = doc["rows"][2], doc["rows"][1]
        body = {k: v for k, v in doc.items() if k != "document_digest"}
        doc["document_digest"] = digest(body)
        for p in self.dir.glob("history.*.json"):
            p.unlink()
        (self.dir / CURRENT).write_bytes(canonical_json(doc))
        with self.assertRaises(MemoryError_) as ctx:
            Stream.restore(self.dir)
        self.assertEqual(ctx.exception.code, "E-MEM-041")

    def test_a_recorded_outcome_that_does_not_replay_stops_restore(self):
        s = self.genesis()
        s.run(CHAIN + [ask("A", "D")])
        doc = s.document()
        doc["rows"][3]["outcome"]["verdict"] = "NO"
        body = {k: v for k, v in doc.items() if k != "document_digest"}
        doc["document_digest"] = digest(body)
        for p in self.dir.glob("history.*.json"):
            p.unlink()
        (self.dir / CURRENT).write_bytes(canonical_json(doc))
        with self.assertRaises(MemoryError_) as ctx:
            Stream.restore(self.dir)
        self.assertEqual(ctx.exception.code, "E-MEM-042")


class IdentityTests(_Tmp):
    def test_a_record_from_one_context_never_answers_for_another(self):
        s = self.genesis()
        s.run(CHAIN)
        other = Identity(organism_id="org1", context_id="ctx2", world_mode="open", constructor_args=s.identity.constructor_args)
        with self.assertRaises(MemoryError_) as ctx:
            Stream.restore(self.dir, expected=other)
        self.assertEqual(ctx.exception.code, "E-MEM-001")
        self.assertIn("context_id", str(ctx.exception))

    def test_world_mode_is_identity(self):
        s = self.genesis(closed_world=True)
        s.run([fact("A", "B"), ask("A", "C")])
        self.assertEqual(s.rows[-1]["outcome"]["verdict"], "NO")
        open_world = Identity(organism_id="org1", context_id="ctx1", world_mode="open", constructor_args=s.identity.constructor_args)
        with self.assertRaises(MemoryError_):
            Stream.restore(self.dir, expected=open_world)
        restored = Stream.restore(self.dir, expected=s.identity)
        self.assertTrue(restored.organism.ws.closed_world)

    def test_identifier_segments_are_checked(self):
        with self.assertRaises(MemoryError_):
            Identity(organism_id="org|1", context_id="c", world_mode="open", constructor_args={})
        with self.assertRaises(MemoryError_):
            Identity(organism_id="org", context_id="c", world_mode="sideways", constructor_args={})

    def test_constructor_arguments_are_part_of_identity_and_are_restored(self):
        s = self.genesis(motivation_kwargs={"beta": 0.2, "relax": 0.0})
        s.run(CHAIN + [ask("A", "D")])
        restored = Stream.restore(self.dir, expected=s.identity)
        self.assertEqual(restored.organism.motivation.beta, 0.2)
        self.assertEqual(restored.organism.motivation.relax_rate, 0.0)


class SingleWriterTests(_Tmp):
    def test_a_lost_acknowledgment_retry_applies_exactly_once(self):
        s = self.genesis()
        s.run(CHAIN)
        first = s.commit(ask("A", "D"))
        seq_after = s.last_committed_seq
        # A retry of the same logical update carries the same (stream, seq, payload)
        # and so the same event id -- but the clock has moved; emulate the lost-ack
        # case by replaying the stored row's id through the retry path.
        row = s.rows[-1]
        again = s._responses[row["event_id"]]
        self.assertIs(again, first)
        self.assertEqual(s.last_committed_seq, seq_after)

    def test_a_stale_expected_version_rejects_a_mutation_but_serialises_an_ask(self):
        s = self.genesis()
        s.run(CHAIN)
        with self.assertRaises(MemoryError_) as ctx:
            s.commit(fact("X", "Y"), expected_version=0)
        self.assertEqual(ctx.exception.code, "E-MEM-002")
        self.assertEqual(len(s.rows), 3, "nothing was applied")
        self.assertEqual(s.commit(ask("A", "D"), expected_version=0).verdict, "YES")

    def test_a_retry_of_an_event_recorded_before_its_acknowledgment_was_lost_is_acknowledged_once_more_and_applied_once(self):
        """A crash between the save and the ack: the host retries with the event's
        original version. The row at the intended seq holds that very event, so the
        stream answers with the recorded response and adds nothing."""
        s = self.genesis()
        s.run(CHAIN)
        first = s.commit(fact("X", "Y"), expected_version=2)
        rows = len(s.rows)
        again = s.commit(fact("X", "Y"), expected_version=2)          # the retry, after the clock moved
        self.assertIs(again, first)
        self.assertEqual(len(s.rows), rows)
        with self.assertRaises(MemoryError_) as ctx:
            s.commit(fact("X", "Z"), expected_version=2)             # a different event at a taken seq is stale
        self.assertEqual(ctx.exception.code, "E-MEM-002")
        restored = Stream.restore(s.directory, expected=s.identity)
        self.assertEqual(restored.commit(fact("X", "Y"), expected_version=2).verdict, None)
        self.assertEqual(len(restored.rows), rows, "recognised across the restart too")

    def test_history_lost_behind_the_acknowledged_prefix_is_refused_and_the_boundary_named(self):
        """E-MEM-046: when the newest document that verifies ends before what the host
        acknowledged, serving stops and the refusal names the lost rows. Without the
        host's acknowledged seq the fallback is silent, so the host must pass it."""
        s = self.genesis()
        s.run(CHAIN + [ask("A", "D")])
        acked = s.last_committed_seq
        current = s.directory / CURRENT
        current.write_bytes(b"{torn")
        newest_retained = sorted(p for p in s.directory.glob("history.*.json") if p.name != CURRENT)[-1]
        newest_retained.write_bytes(b"\xde\xad")
        with self.assertRaises(MemoryError_) as ctx:
            Stream.restore(s.directory, acknowledged_seq=acked)
        self.assertEqual(ctx.exception.code, "E-MEM-046")
        self.assertIn(f"rows {acked}..{acked} are lost", str(ctx.exception))
        fallback = Stream.restore(s.directory)                          # no acknowledged seq: the older copy serves
        self.assertEqual(fallback.last_committed_seq, acked - 1)
        self.assertNotEqual(fallback.recovered_from, CURRENT)
        self.assertEqual(len(fallback.recovery_failures), 2, "both damaged documents are named")

    def test_the_fault_hook_fires_at_the_named_points_of_a_save_and_is_off_by_default(self):
        s = self.genesis()
        self.assertIsNone(s.fault_hook)
        seen = []
        s.fault_hook = seen.append
        s.commit(fact("A", "B"))
        self.assertEqual(seen, ["before-write", "before-replace", "after-replace", "after-save"])

    def test_refused_events_are_recorded_as_refused_and_replay_identically(self):
        s = self.genesis()
        s.run(CHAIN + [ask("A", "D"), retract("A", "D"), retract("Q", "Z")])
        self.assertEqual([r["commit_status"] for r in s.rows[-2:]], ["REFUSED", "REFUSED"])
        self.assertEqual([r["refusal_code"] for r in s.rows[-2:]], ["E-ORG-001", "E-ORG-002"])
        restored = Stream.restore(self.dir, expected=s.identity)
        self.assertEqual(len(restored.rows), 6)


class LimitTests(_Tmp):
    def test_reaching_the_event_limit_stops_safely_and_discards_nothing(self):
        s = self.genesis(max_events=4)
        s.run(CHAIN + [ask("A", "D")])
        before = reference_digest(s.organism)
        with self.assertRaises(MemoryError_) as ctx:
            s.commit(fact("D", "E"))
        self.assertEqual(ctx.exception.code, "E-MEM-050")
        self.assertEqual(reference_digest(s.organism), before, "the organism was not touched")
        self.assertEqual(len(s.rows), 4)
        self.assertIsNotNone(s.stopped)
        # A restore under the same limit is readable and refuses the next commit the same way;
        # a restore under a raised limit continues from the identical state.
        restored = Stream.restore(self.dir, expected=s.identity, max_events=4)
        with self.assertRaises(MemoryError_) as ctx2:
            restored.commit(ask("A", "D"))
        self.assertEqual(ctx2.exception.code, "E-MEM-050")
        raised = Stream.restore(self.dir, expected=s.identity, max_events=8)
        self.assertEqual(raised.commit(ask("A", "D")).verdict, "YES")

    def test_the_byte_limit_stops_before_consuming(self):
        s = self.genesis(max_bytes=4096)
        with self.assertRaises(MemoryError_) as ctx:
            s.run(CHAIN)
        self.assertEqual(ctx.exception.code, "E-MEM-050")
        self.assertTrue((self.dir / CURRENT).exists(), "the last good document stands")

    def test_retained_copies_beyond_the_bound_are_archived_never_deleted(self):
        s = self.genesis(max_retained=3)
        s.run(CHAIN + [ask("A", "D"), ask("B", "D")])
        retained = sorted(p.name for p in self.dir.glob("history.*.json") if p.name != CURRENT)
        archived = sorted(p.name for p in (self.dir / "archive").glob("history.*.json"))
        self.assertEqual(len(retained), 3)
        self.assertEqual(len(retained) + len(archived), 6, "genesis + five commits, all still on disk")


class RestoreValidatesBeforeAnswering(_Tmp):
    def test_a_broken_cascade_is_caught_at_restore_not_at_the_next_beat(self):
        """With the no-cascade ablation a disputed premise leaves a standing conclusion
        on a dead root. The live organism faulted at its beat; the restored one must
        refuse to serve at all."""
        s = self.genesis(workspace_factory=NoCascade)
        s.run(CHAIN + [ask("A", "D"), negation("B", "C")])
        self.assertTrue(s.organism.faults, "the live organism's heartbeat caught it")
        with self.assertRaises(MemoryError_) as ctx:
            Stream.restore(self.dir, expected=s.identity)
        self.assertEqual(ctx.exception.code, "E-MEM-044")

    def test_a_document_from_different_engine_code_is_refused(self):
        s = self.genesis()
        s.run(CHAIN)
        doc = s.document()
        doc["header"]["engine_version"] = "0" * 64
        body = {k: v for k, v in doc.items() if k != "document_digest"}
        doc["document_digest"] = digest(body)
        for p in self.dir.glob("history.*.json"):
            p.unlink()
        (self.dir / CURRENT).write_bytes(canonical_json(doc))
        with self.assertRaises(MemoryError_) as ctx:
            Stream.restore(self.dir)
        self.assertEqual(ctx.exception.code, "E-MEM-010")


class PurityTests(unittest.TestCase):
    def test_history_imports_only_stdlib_and_this_package(self):
        source = Path(history.__file__).read_text()
        allowed = {"__future__", "dataclasses", "pathlib", "ablations", "events", "foundations", "organism", "workspace"}
        for line in source.splitlines():
            line = line.strip()
            if line.startswith("from ") and " import " in line:
                self.assertIn(line.split()[1].split(".")[0], allowed, line)
            elif line.startswith("import "):
                self.assertIn(line.split()[1].split(".")[0], {"hashlib", "json", "os", "shutil", "sys", "ablations"}, line)

    def test_the_claim_is_level_a_only(self):
        self.assertIn("level (a) only", Stream.genesis(tempfile.mkdtemp(), organism_id="o", context_id="c").report())


if __name__ == "__main__":
    unittest.main()
