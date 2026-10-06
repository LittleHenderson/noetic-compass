"""CNCM → CAS-RPU interchange, the reverse direction: a fact held by the Codex
kernel, carried into the organism, changes its later answer; a CNCM-side
withdrawal takes the dependents with it, before and after a fresh process.

HELM ability 7, roadmap step 6; plan and gate answer in
`docs/working/helm_cooperation_reverse_direction_plan_2026_10_06.md`
(worked example A of the fixtures draft, fixtures F01, F07, F08, F11, F12,
F13). The CNCM kernel is the frozen Codex reference implementation at
`eb99855`, mounted read-only and pinned by content; these tests skip when it
is not mounted, unless `CAS_RPA_REQUIRED=1` (CI mounts the commit), in which
case a skip is a failure. Every expected answer below was written before the
first run.
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
sys.path.insert(0, str(REPO / "scripts" / "cas_memory"))

import cncm_interchange as ix  # noqa: E402
from controls import ctl_recompute  # noqa: E402
from events import ask, fact, hypothesis, negation, retract  # noqa: E402
from history import Stream  # noqa: E402

CTX = "ctx_helm_a"

#: Restore in a fresh operating-system process, import one envelope, ask, report.
CHILD = r"""
import json, sys
sys.path.insert(0, {cas!r}); sys.path.insert(0, {ccb!r}); sys.path.insert(0, {mem!r})
for banned in ("torch", "openai", "anthropic", "requests"):
    assert banned not in sys.modules
from history import Stream
from controls import ctl_recompute
from events import Event, EventKind
import cncm_interchange as ix
stream = Stream.restore({path!r}, reference=ctl_recompute)
rx = ix.Receiver.open(stream)
out = {{"known_before": sorted(rx.results), "imports": [], "asks": []}}
for env in json.load(open({envs!r})):
    r = rx.import_envelope(env)
    out["imports"].append({{"accepted": r.accepted, "code": r.code, "withdrawn": list(r.withdrawn)}})
for kind, s, o in {asks!r}:
    r = stream.commit(Event(EventKind(kind), s, o))
    out["asks"].append({{"verdict": r.verdict, "route": r.route, "provenance": rx.provenance_of(r)}})
out["rows"] = len(stream.rows)
print(json.dumps(out))
"""


def fresh_process(path: Path, envelopes: list[dict], asks: list[tuple[str, str, str]]) -> dict:
    envs_path = path / "child_envelopes.json"
    envs_path.write_text(json.dumps(envelopes), encoding="utf-8")
    script = CHILD.format(cas=str(REPO / "scripts" / "cas_rpu"), ccb=str(REPO / "scripts" / "ccb_r1"),
                          mem=str(REPO / "scripts" / "cas_memory"), path=str(path), envs=str(envs_path), asks=asks)
    proc = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise AssertionError(f"child failed:\n{proc.stderr}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


class _NeedsCncm(unittest.TestCase):
    def setUp(self):
        try:
            self.cncm = ix.load_cncm()
        except ix.CncmUnavailable as exc:
            if os.environ.get("CAS_RPA_REQUIRED") == "1":
                raise AssertionError(f"CAS_RPA_REQUIRED=1 but the CNCM path cannot run: {exc}")
            self.skipTest(str(exc))
        self._dir = tempfile.TemporaryDirectory()
        self.dir = Path(self._dir.name) / "stream"
        self.stream = Stream.genesis(self.dir, organism_id="rx", context_id=CTX)
        self.rx = ix.Receiver(self.stream)
        self.src = ix.CncmSource(self.cncm, context_id=CTX)

    def tearDown(self):
        self._dir.cleanup()

    def env(self, event) -> dict:
        envs = self.src.tell(event)
        self.assertEqual(len(envs), 1)
        return envs[0]

    def verdict(self, s, o) -> str:
        return self.stream.commit(ask(s, o)).verdict


class WorkedExampleATests(_NeedsCncm):
    def test_f01_a_fact_committed_by_cncm_changes_the_organisms_later_answer_and_is_traceable_to_the_run(self):
        self.stream.commit(fact("AA", "BB"))
        self.assertEqual(self.verdict("AA", "CC"), "UNKNOWN", "before: nothing joins BB to CC")
        env = self.env(fact("BB", "CC"))
        self.assertEqual(env["source"]["engine"], "cncm")
        self.assertEqual(env["source_representation"]["terminal_status"], "CONCLUDED", "CNCM committed the fact by a run")
        run_id = env["provenance"]["origin"]["hops"][0]["event_id"]
        self.assertTrue(run_id.startswith("run-"))
        r = self.rx.import_envelope(env)
        self.assertTrue(r.accepted and r.round_trip, r)
        self.assertEqual(self.stream.rows[-1]["source"], f"cncm:{env['event_id']}", "the history row names the envelope")
        a = self.stream.commit(ask("AA", "CC"))
        self.assertEqual(a.verdict, "YES", "after: the imported fact completes the chain")
        prov = self.rx.provenance_of(a)
        self.assertEqual(prov["roots"], ["AA|leads_to|BB", "BB|leads_to|CC"])
        self.assertEqual(prov["envelopes"], {"BB|leads_to|CC": env["event_id"]})
        self.assertEqual(prov["runs"], {"BB|leads_to|CC": run_id}, "the answer rests on the CNCM run by id")

    def test_the_untaught_twin_stays_unknown(self):
        self.stream.commit(fact("AA", "BB"))
        self.rx.import_envelope(self.env(fact("PP", "QQ")))      # an unrelated CNCM fact instead of the lesson
        self.assertEqual(self.verdict("AA", "CC"), "UNKNOWN")

    def test_a_denial_crosses_with_explicit_negative_polarity(self):
        env = self.env(negation("AA", "CC"))
        self.assertIs(env["proposition"]["polarity"], False)
        self.assertTrue(self.rx.import_envelope(env).accepted)
        self.stream.commit(fact("AA", "BB")); self.stream.commit(fact("BB", "CC"))
        self.assertEqual(self.verdict("AA", "CC"), "INADMISSIBLE", "a sound chain against an imported denial is disputed")


class WithdrawalTests(_NeedsCncm):
    def test_f08_a_cncm_side_withdrawal_takes_the_dependent_conclusion_with_it(self):
        self.stream.commit(fact("AA", "BB"))
        self.rx.import_envelope(self.env(fact("BB", "CC")))
        self.assertEqual(self.verdict("AA", "CC"), "YES")
        env = self.env(retract("BB", "CC"))
        self.assertEqual(env["source_representation"]["terminal_status"], "NEEDS_INFORMATION", "the later CNCM run no longer carries the given")
        r = self.rx.import_envelope(env)
        self.assertEqual((r.accepted, r.withdrawn), (True, ("AA|leads_to|CC",)))
        self.assertEqual(self.verdict("AA", "CC"), "UNKNOWN", "nothing escapes through a faster path")

    def test_f08_a_withdrawal_of_something_this_stream_never_held_is_refused_not_half_applied(self):
        r = self.rx.import_envelope(self.env(retract("BB", "CC")))
        self.assertEqual((r.accepted, r.code), (False, "E-IX-RETRACT-REFUSED"))
        self.assertEqual(len(self.stream.rows), 0, "nothing was committed")

    def test_a_withdrawal_of_a_conclusion_the_receiver_derived_is_refused(self):
        self.rx.import_envelope(self.env(fact("AA", "BB")))
        self.rx.import_envelope(self.env(fact("BB", "CC")))
        self.assertEqual(self.verdict("AA", "CC"), "YES")
        r = self.rx.import_envelope(self.env(retract("AA", "CC")))
        self.assertEqual((r.accepted, r.code), (False, "E-IX-RETRACT-REFUSED"), "derived, not given (E-ORG-001)")

    def test_f07_a_correction_is_atomic(self):
        self.stream.commit(fact("AA", "BB"))
        self.rx.import_envelope(self.env(fact("BB", "CC")))
        self.assertEqual(self.verdict("AA", "CC"), "YES")
        env = self.src.correction(("BB", "CC"), ("BB", "DD"))
        self.assertEqual(env["event_type"], "CORRECTION")
        r = self.rx.import_envelope(env)
        self.assertEqual((r.accepted, len(r.own_event_ids), r.withdrawn), (True, 2, ("AA|leads_to|CC",)))
        self.assertEqual(self.verdict("AA", "CC"), "UNKNOWN")
        self.assertEqual(self.verdict("AA", "DD"), "YES")
        bad = self.src.correction(("XX", "YY"), ("XX", "ZZ"))   # XX→YY was never given here
        r = self.rx.import_envelope(bad)
        self.assertEqual((r.accepted, r.code), (False, "E-IX-CORRECTION-REFUSED"))
        self.assertEqual(self.verdict("XX", "ZZ"), "UNKNOWN", "the assert half was not applied alone")


class RefusalTests(_NeedsCncm):
    def _env(self, **over) -> dict:
        env = self.env(fact("BB", "CC"))
        env.update(over)
        return env

    def test_f12_another_context_never_answers_for_this_one(self):
        other = ix.CncmSource(self.cncm, context_id="ctx_helm_b")
        r = self.rx.import_envelope(other.tell(fact("BB", "CC"))[0])
        self.assertEqual((r.accepted, r.code), (False, "E-IX-CONTEXT"))

    def test_f13_value_negative_retract_association_proposal_and_derived_are_refused_never_coerced(self):
        env = self._env(); env["proposition"]["value"] = "11"
        self.assertEqual(self.rx.import_envelope(env).code, "E-IX-VALUE")
        env = self._env(event_type="RETRACT"); env["proposition"]["polarity"] = False
        self.assertEqual(self.rx.import_envelope(env).code, "E-IX-NEG-RETRACT")
        env = self._env(); env["proposition"]["predicate"] = "co_occurs"
        self.assertEqual(self.rx.import_envelope(env).code, "E-IX-RELATION")
        env = self._env(event_type="PROPOSED")
        self.assertEqual(self.rx.import_envelope(env).code, "E-IX-PROPOSED")
        with self.assertRaises(ix.InterchangeError) as ctx:
            self.src.tell(hypothesis("BB", "CC"))
        self.assertEqual(ctx.exception.code, "E-IX-PROPOSED", "CNCM holds no guess")
        self.rx.import_envelope(self.env(fact("AA", "BB")))
        derived = self.src.conclusion(("AA", "CC"))
        self.assertIsNotNone(derived, "CNCM concludes AA→CC from its own givens")
        self.assertEqual(derived["event_type"], "DERIVED")
        self.assertEqual(self.rx.import_envelope(derived).code, "E-IX-DERIVED")
        self.assertEqual(len(self.stream.rows), 1, "only the one given was committed; every refused envelope changed nothing")
        self.assertEqual(self.verdict("AA", "CC"), "UNKNOWN", "CNCM's conclusion did not cross; the receiver lacks BB->CC")
        self.assertTrue(self.rx.import_envelope(self.env(fact("BB", "CC"))).accepted)
        self.assertEqual(self.verdict("AA", "CC"), "YES", "given both givens, the receiver derives it itself")

    def test_a_defaulted_polarity_a_missing_hop_a_cycle_and_a_stale_version_are_refused(self):
        env = self._env(); del env["proposition"]["polarity"]
        self.assertEqual(self.rx.import_envelope(env).code, "E-IX-POLARITY")
        env = self._env(); env["provenance"]["origin"]["hops"] = []
        self.assertEqual(self.rx.import_envelope(env).code, "E-IX-PROVENANCE")
        env = self._env(); env["provenance"]["origin"]["hops"].append({"engine": "cas_rpu", "stream_id": self.rx.stream_id, "event_id": "x"})
        self.assertEqual(self.rx.import_envelope(env).code, "E-IX-CYCLE")
        env = self._env(); env["sequence"]["expected_version"] = 7
        self.assertEqual(self.rx.import_envelope(env).code, "E-IX-VERSION")
        env = self._env(); env["sequence"]["expected_version"] = self.stream.last_committed_seq
        self.assertTrue(self.rx.import_envelope(env).accepted)
        self.assertEqual(len(self.stream.rows), 1)

    def test_the_same_envelope_twice_is_applied_once(self):
        env = self.env(fact("BB", "CC"))
        first = self.rx.import_envelope(env)
        again = self.rx.import_envelope(env)
        self.assertIs(again, first)
        self.assertEqual(len(self.stream.rows), 1)


class RestartTests(_NeedsCncm):
    def test_f11_an_imported_fact_survives_a_fresh_process_and_a_later_imported_withdrawal_still_cascades(self):
        self.stream.commit(fact("AA", "BB"))
        env_fact = self.env(fact("BB", "CC"))
        self.assertTrue(self.rx.import_envelope(env_fact).accepted)
        env_retract = self.env(retract("BB", "CC"))        # committed on the CNCM side now; sent after the restart
        # Process 2: the imported fact answers without being imported again; the duplicate is recognised from the ledger.
        out = fresh_process(self.dir, [env_fact], [("ask", "AA", "CC")])
        self.assertEqual(out["known_before"], [env_fact["event_id"]], "the ledger was read back")
        self.assertEqual(out["imports"][0]["accepted"], True)
        self.assertEqual(out["asks"][0]["verdict"], "YES")
        self.assertEqual(out["asks"][0]["provenance"]["envelopes"], {"BB|leads_to|CC": env_fact["event_id"]})
        self.assertEqual(out["rows"], 3, "process 2 added only its ask; the duplicate import changed nothing")
        # Process 3: the CNCM-side withdrawal arrives; the dependent falls; process 4 still says so.
        out = fresh_process(self.dir, [env_retract], [("ask", "AA", "CC")])
        self.assertEqual((out["imports"][0]["accepted"], out["imports"][0]["withdrawn"]), (True, ["AA|leads_to|CC"]))
        self.assertEqual(out["asks"][0]["verdict"], "UNKNOWN")
        out = fresh_process(self.dir, [], [("ask", "AA", "CC")])
        self.assertEqual(out["asks"][0]["verdict"], "UNKNOWN", "nothing stale escapes after a further restart")
        restored = Stream.restore(self.dir, reference=ctl_recompute)   # every recorded ask re-checked against the control
        self.assertEqual(restored.recovery_failures, ())


class StreamAgreementTests(_NeedsCncm):
    def test_a_generated_stream_held_by_cncm_and_received_through_the_envelope_agrees_with_the_oracle_across_restarts(self):
        """Seed 0, primary and untaught twin, open world, in-process restarts at
        every session boundary (each restore replays against the recompute
        control). Every given reaches CAS-RPU only through the envelope."""
        from sessions import generate_session_set
        sset = generate_session_set([0], closed_world=False)
        with tempfile.TemporaryDirectory() as root:
            for stream in (sset.streams[0], sset.twins[0]):
                cmp = ix.compare_import_stream(self.cncm, stream, root, restart="in-process")
                sm = cmp.summary()
                self.assertEqual(sm["disagree"], 0, cmp.disagree)
                self.assertEqual(sm["designed_agree"], sm["designed_probes"])
                self.assertGreater(sm["designed_probes"], 0)
                self.assertEqual(sm["restarts"], stream.sessions - 1)
                self.assertEqual(sm["round_trip_failures"], 0)
                self.assertEqual(sm["imports_accepted"] + sum(sm["rejected"].values()), sm["imports"])
                self.assertEqual(sm["rejected"].get("E-IX-RETRACT-REFUSED", 0), sm["refused_expected"], "the only refusals are the retracts the stream designs as refused")
                self.assertEqual(sm["refused_matched"], sm["refused_expected"])


if __name__ == "__main__":
    unittest.main()
