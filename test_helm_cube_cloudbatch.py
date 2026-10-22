"""test_helm_cube_cloudbatch.py -- the cloud search fetches all fold records in ONE call (A-TEACH2-12), FIX FIRST.

Written BEFORE the code. Owner's word (2026-10-22): "Yes, make it faster" (read the cloud's fold records in one go
instead of one call each). In plain words, these tests check that:
  - a question that needs the cloud makes at most 3 cloud calls: one batched read of the fold records, then the found
    capsule's record and original -- and no fold record is read one by one;
  - old lines are still found EXACT (30 of 30 on the pinned chat), never a wrong line;
  - a changed record in the batch is still held;
  - offline is unchanged;
  - the bucket adapter makes ONE `aws s3 cp --recursive` call filtered to fold records, and leaves no temporary folder.
Run:  python -m pytest test_helm_cube_cloudbatch.py -q
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_cold_cloud as hcc  # noqa: E402
import helm_memory_compact as hmc  # noqa: E402
import test_helm_cube_cloudsearch as C  # noqa: E402
from test_helm_cube_tiers import long_line, plot  # noqa: E402


class BatchCountingCloud(C.CountingCloud):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.batches = []

    def get_many(self, prefix, suffix):
        self.batches.append((prefix, suffix))
        return super().get_many(prefix, suffix)


def _run(tmp_path, n=600):
    cloud = BatchCountingCloud()
    orig = C.CountingCloud
    C.CountingCloud = lambda **kw: cloud
    try:
        mem, osc, _ = C._run(tmp_path, n)
    finally:
        C.CountingCloud = orig
    return mem, osc, cloud


def test_a_cloud_question_makes_at_most_three_calls(tmp_path):
    mem, osc, cloud = _run(tmp_path)
    comp = mem.compactor
    for i in C.SAMPLE:
        cloud.gets.clear()
        cloud.batches.clear()
        out = comp.recall(f"the beds in {plot(i)}")
        assert out["label"] == "EXACT" and long_line(i) in out["texts"]
        assert not any(k.endswith(".fold.json") for k in cloud.gets)          # no fold record read one by one
        assert len(cloud.batches) <= 1 and len(cloud.gets) + len(cloud.batches) <= 3


def test_a_changed_record_in_the_batch_is_held(tmp_path):
    mem, osc, cloud = _run(tmp_path)
    comp = mem.compactor
    for key in comp.moved_folds.values():
        cloud.objects[key] = cloud.objects[key].replace(b"planted", b"plantex", 1)
    for i in C.SAMPLE:
        out = comp.recall(f"the beds in {plot(i)}")
        assert out["label"] != "EXACT" or long_line(i) in out["texts"]
    assert "LEAN_REBUILD_MISMATCH" in [f["kind"] for f in comp.eye_report()]


def test_offline_is_unchanged(tmp_path):
    mem, osc, cloud = _run(tmp_path)
    cloud.online = False
    outs = [mem.compactor.recall(f"the beds in {plot(i)}") for i in C.SAMPLE]
    assert all(o["label"] != "EXACT" for o in outs if not o["texts"])
    assert any("stored away" in o["reason"] for o in outs)


def test_nothing_from_the_batch_stays_in_working_memory(tmp_path):
    mem, osc, cloud = _run(tmp_path)
    before = hmc._canon(mem.compactor.capsules.stored())
    for i in C.SAMPLE:
        mem.compactor.recall(f"the beds in {plot(i)}")
    assert hmc._canon(mem.compactor.capsules.stored()) == before


def test_the_fake_cloud_batch_returns_only_matching_keys():
    cloud = hcc.FakeCloud()
    cloud.put("teach/s/a.fold.json", b"1")
    cloud.put("teach/s/b.lean.json", b"2")
    cloud.put("teach/other/c.fold.json", b"3")
    assert cloud.get_many("teach/s/", ".fold.json") == {"teach/s/a.fold.json": b"1"}
    cloud.online = False
    try:
        cloud.get_many("teach/s/", ".fold.json")
        assert False, "offline must raise"
    except hcc.CloudUnavailable:
        pass


def test_the_bucket_adapter_makes_one_recursive_copy_and_cleans_up():
    calls = []
    made = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        dest = cmd[cmd.index("--recursive") - 1]
        made.append(dest)
        os.makedirs(os.path.join(dest, "sub"), exist_ok=True)
        with open(os.path.join(dest, "fold-1-0001.fold.json"), "wb") as fh:
            fh.write(b"A")
        with open(os.path.join(dest, "sub", "fold-2-0001.fold.json"), "wb") as fh:
            fh.write(b"B")

        class R:
            returncode = 0
            stdout = b""
            stderr = b""
        return R()

    s3 = hcc.S3Cloud(bucket="helm-cold-memory-807562639912-usw2", prefix="teach/t/", region="us-west-2",
                     runner=fake_run)
    got = s3.get_many("teach/t/", ".fold.json")
    assert got == {"teach/t/fold-1-0001.fold.json": b"A", "teach/t/sub/fold-2-0001.fold.json": b"B"}
    assert len(calls) == 1
    cmd = calls[0]
    assert cmd[:3] == ["aws", "s3", "cp"] and "s3://helm-cold-memory-807562639912-usw2/teach/t/" in cmd
    assert cmd[cmd.index("--exclude") + 1] == "*" and cmd[cmd.index("--include") + 1] == "*.fold.json"
    assert "--region" in cmd and "us-west-2" in cmd
    assert not os.path.exists(made[0])                                    # the temporary folder is removed
    assert tempfile.gettempdir()
