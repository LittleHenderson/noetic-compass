"""Survival level (b): the accepted state outlives the machine, via a dedicated remote location.

Three fresh operating-system processes. Process 1 teaches and saves, mirroring
every sealed document to the remote. Its local directory is then destroyed —
the machine is gone. Process 2 has no local state, rebuilds the stream from the
remote alone, answers from the record, retracts a support and watches the
dependents fall. Its local state is destroyed too. Process 3 rebuilds again
and confirms the retraction held.

Two remotes run this proof. `DirectoryStore` is a second directory standing in
for the remote, so the proof runs everywhere, offline, in CI; it establishes
the *mechanism* — nothing of the stream is read from the destroyed machine —
but a directory on the same host is not level (b) storage and the test's name
says so. `S3Prefix` is the owner's dedicated AWS location; that test runs only
when `HELM_S3_BUCKET` is set and the environment's credentials are accepted,
and is skipped with the reason otherwise. On 2026-10-06 the sandbox's key was
rejected by the service (`InvalidAccessKeyId`); the live run awaits a valid key.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))
sys.path.insert(0, str(REPO / "scripts" / "cas_memory"))

from events import ask, fact, retract  # noqa: E402
from history import CURRENT, MemoryError_, Stream  # noqa: E402
from s3store import Credentials, DirectoryStore, S3Prefix, StoreError, authorization  # noqa: E402

K = "A|leads_to|D"
CHILD = r"""
import json, sys, shutil
sys.path.insert(0, {cas!r}); sys.path.insert(0, {ccb!r}); sys.path.insert(0, {mem!r})
from history import Stream
from events import Event, EventKind
from s3store import DirectoryStore, S3Prefix
store = {store_expr}
stream = Stream.restore_from(store, {stream_id!r}, {local!r})
out = []
for kind, s, o in {actions!r}:
    r = stream.commit(Event(EventKind(kind), s, o))
    out.append({{"verdict": r.verdict, "withdrawn": list(r.withdrawn), "route": r.route}})
report = {{"out": out, "rows": len(stream.rows), "standing": sorted(stream.organism.standing),
          "faults": list(stream.organism.faults), "mirror": stream.mirror.describe()}}
shutil.rmtree({local!r})     # this machine is gone too
print(json.dumps(report))
"""


def child(store_expr: str, stream_id: str, local: Path, actions) -> dict:
    script = CHILD.format(cas=str(REPO / "scripts" / "cas_rpu"), ccb=str(REPO / "scripts" / "ccb_r1"), mem=str(REPO / "scripts" / "cas_memory"),
                          store_expr=store_expr, stream_id=stream_id, local=str(local), actions=actions)
    proc = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=180, env=os.environ.copy())
    if proc.returncode != 0:
        raise AssertionError(f"child failed:\n{proc.stderr}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def replacement_proof(test: unittest.TestCase, store, store_expr: str) -> None:
    base = Path(tempfile.mkdtemp())
    machine1 = base / "machine1"
    s = Stream.genesis(machine1, organism_id="org", context_id="ctx", mirror=store)
    s.run([fact("A", "B"), fact("B", "C"), fact("C", "D")])
    test.assertEqual(s.commit(ask("A", "D")).verdict, "YES")
    stream_id = s.identity.stream_id
    test.assertTrue(store.exists(f"{stream_id}/{CURRENT}"))
    shutil.rmtree(machine1)                                        # machine 1 is gone
    test.assertFalse(machine1.exists())

    two = child(store_expr, stream_id, base / "machine2", [("ask", "A", "D"), ("retract", "B", "C"), ("ask", "A", "D")])
    test.assertEqual([o["verdict"] for o in two["out"]], ["YES", None, "UNKNOWN"])
    test.assertEqual(two["out"][1]["withdrawn"], [K], "the dependent fell on the replacement machine")
    test.assertEqual(two["faults"], [])
    test.assertFalse((base / "machine2").exists())

    three = child(store_expr, stream_id, base / "machine3", [("ask", "A", "D"), ("fact", "B", "C"), ("ask", "A", "D")])
    test.assertEqual([o["verdict"] for o in three["out"] if o["verdict"]], ["UNKNOWN", "YES"], "the retraction survived; re-teaching restores")
    test.assertEqual(three["rows"], 10)


class ReplacementViaSecondDirectoryTests(unittest.TestCase):
    """Mechanism proof, offline: nothing is read from the destroyed machine. Not level (b) storage."""

    def test_three_fresh_processes_each_restore_from_the_second_location_after_the_previous_machine_is_destroyed(self):
        remote = Path(tempfile.mkdtemp()) / "remote"
        replacement_proof(self, DirectoryStore(remote), f"DirectoryStore({str(remote)!r})")

    def test_a_remote_refusal_leaves_the_local_document_standing_and_the_next_save_heals_it(self):
        class Flaky(DirectoryStore):
            fail = True
            def put(self, name, data):
                if Flaky.fail:
                    raise StoreError("E-S3-HTTP-503", "simulated outage")
                return super().put(name, data)
        remote = Flaky(Path(tempfile.mkdtemp()) / "remote")
        local = Path(tempfile.mkdtemp()) / "local"
        with self.assertRaises(MemoryError_) as ctx:
            Stream.genesis(local, organism_id="o", context_id="c", mirror=remote)
        self.assertEqual(ctx.exception.code, "E-MEM-052")
        self.assertTrue((local / CURRENT).exists(), "the local document stands")
        Flaky.fail = False
        s = Stream.restore(local, mirror=remote)
        s.commit(fact("A", "B"))
        self.assertTrue(remote.exists(f"{s.identity.stream_id}/{CURRENT}"), "healed by the next successful save")

    def test_restoring_from_an_empty_remote_is_refused(self):
        remote = DirectoryStore(Path(tempfile.mkdtemp()) / "remote")
        with self.assertRaises(MemoryError_) as ctx:
            Stream.restore_from(remote, "noetic-compass.o.c.trunk", Path(tempfile.mkdtemp()) / "m")
        self.assertEqual(ctx.exception.code, "E-MEM-053")

    def test_a_tampered_remote_current_falls_back_to_the_retained_remote_copy(self):
        remote = DirectoryStore(Path(tempfile.mkdtemp()) / "remote")
        local = Path(tempfile.mkdtemp()) / "local"
        s = Stream.genesis(local, organism_id="o", context_id="c", mirror=remote)
        s.run([fact("A", "B"), fact("B", "C"), ask("A", "C")])
        name = f"{s.identity.stream_id}/{CURRENT}"
        remote.put(name, remote.get(name).replace(b'"verdict":"YES"', b'"verdict":"NO!"'))
        shutil.rmtree(local)
        r = Stream.restore_from(remote, s.identity.stream_id, Path(tempfile.mkdtemp()) / "m2", expected=s.identity)
        self.assertEqual(r.last_committed_seq, 2)
        self.assertEqual(r.commit(ask("A", "C")).verdict, "YES")


class SeparationTests(unittest.TestCase):
    def test_the_storage_peripheral_lives_outside_the_reasoning_package(self):
        """The sever law: nothing in scripts/cas_rpu may reach the network. The
        S3 client therefore lives in scripts/cas_memory and is injected into a
        Stream as `mirror`; history.py never imports it."""
        import s3store
        self.assertEqual(Path(s3store.__file__).parent.name, "cas_memory")
        history_src = (REPO / "scripts" / "cas_rpu" / "history.py").read_text()
        self.assertNotIn("s3store", history_src)
        self.assertNotIn("urllib", history_src)


class SignerTests(unittest.TestCase):
    def test_signature_matches_the_published_aws_example(self):
        """GET /test.txt with a Range header, 2013-05-24, us-east-1 (AWS docs)."""
        creds = Credentials("AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        empty = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        headers = {"host": "examplebucket.s3.amazonaws.com", "range": "bytes=0-9", "x-amz-content-sha256": empty, "x-amz-date": "20130524T000000Z"}
        auth = authorization("GET", "/test.txt", "", headers, empty, "20130524T000000Z", "us-east-1", creds)
        self.assertTrue(auth.endswith("Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"))
        self.assertIn("SignedHeaders=host;range;x-amz-content-sha256;x-amz-date", auth)

    def test_the_store_never_deletes_and_never_leaves_its_prefix(self):
        self.assertFalse(hasattr(S3Prefix, "delete"))
        with self.assertRaises(StoreError):
            S3Prefix("b", "p", "us-west-2", Credentials("k", "s"))._full("../escape")


class ReplacementViaDedicatedS3LocationTests(unittest.TestCase):
    """Level (b) proper. Runs only against the owner's dedicated location with a valid key."""

    def setUp(self):
        bucket = os.environ.get("HELM_S3_BUCKET")
        if not bucket:
            self.skipTest("HELM_S3_BUCKET not set: the dedicated AWS location is not configured in this environment")
        region = os.environ.get("HELM_S3_REGION", "us-west-2")
        prefix = os.environ.get("HELM_S3_PREFIX", "helm-memory")
        try:
            self.store = S3Prefix(bucket, prefix, region)
            self.store.list()
        except StoreError as exc:
            self.skipTest(f"the dedicated location is not reachable with this environment's credentials: {exc}")
        self.store_expr = f"S3Prefix({bucket!r}, {prefix!r}, {region!r})"

    def test_three_fresh_processes_each_restore_from_the_dedicated_s3_location_after_the_previous_machine_is_destroyed(self):
        replacement_proof(self, self.store, self.store_expr)


if __name__ == "__main__":
    unittest.main()
