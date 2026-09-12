"""The no-result rescue path must save evidence, not die on a nested key.

Why this file exists. CandidateProvider.collect has a fallback for a run that
produced no results/result.json: collect every results/ object that exists, so a
worker that died after doing its work does not take its evidence with it.

On 2026-09-12 that fallback saved NOTHING for job
cas-meta2-graph6read-20260912062331-b34e3d92, whose readout.json (2,610,908
bytes) was sitting safely in the bucket. The key results/artifacts/manifest.json
becomes the local name remote_artifacts/manifest.json - a NESTED path - and the
parent directory was never created. write_evidence raised FileNotFoundError from
OUTSIDE the download guard, so the first nested key aborted the whole rescue. The
receipt recorded only that FileNotFoundError, which is why the run's real cause
had to be read from the instance's serial console instead.

The payload had to be downloaded by hand. This test is so that never repeats.
"""
import pathlib

import pytest

from aws import graph_training_candidate_launch as candidate


class _S3:
    def __init__(self, objects):
        self.objects = objects

    def list_objects_v2(self, Bucket=None):
        return {"Contents": [{"Key": key} for key in sorted(self.objects)]}

    def get_object(self, Bucket=None, Key=None):
        if Key not in self.objects:
            raise KeyError(Key)
        body = self.objects[Key]
        if body is None:                      # a key that cannot be downloaded
            raise RuntimeError("SimulatedDownloadFailure")
        return {"Body": _Body(body)}


class _Body:
    def __init__(self, raw):
        self._raw = raw

    def read(self, *args):
        raw, self._raw = self._raw, b""
        return raw


def _provider(tmp_path, objects):
    provider = candidate.CandidateProvider.__new__(candidate.CandidateProvider)
    provider.job = "cas-meta2-graph6read-00000000000000-deadbeef"
    provider.calls = []
    provider._result_raw = None
    provider._instance_id = "i-0000000000000000f"
    provider._evidence = tmp_path / "receipt"
    provider._evidence.mkdir()
    provider._resources = {"bucket": "a-bucket"}
    provider.clients = {"s3": _S3(objects)}
    return provider


OBJECTS = {
    # the nested keys that broke it, exactly as the real bucket held them
    "results/artifacts/manifest.json": b'{"artifacts": []}',
    "results/artifacts/readout.json": b'{"rows": 216}',
    "results/artifacts/measurements.json": b'{"summary": true}',
    "results/evidence/phase_worker_started.json": b'{"phase": "worker_started"}',
    "input/source.zip": b"NOT RESULTS - must be ignored",
}


def test_every_nested_results_object_is_rescued(tmp_path):
    provider = _provider(tmp_path, OBJECTS)
    collected = provider.collect(provider.job)
    saved = {entry["key"] for entry in collected["artifacts_collected"]}
    assert saved == {key for key in OBJECTS if key.startswith("results/")}, saved
    assert collected.get("uncollected") is None, collected.get("uncollected")
    # the big one is the whole point
    payload = tmp_path / "receipt" / "remote_artifacts" / "readout.json"
    assert payload.is_file()
    assert payload.read_bytes() == OBJECTS["results/artifacts/readout.json"]


def test_the_rescue_reports_its_reason_and_ignores_non_results_keys(tmp_path):
    provider = _provider(tmp_path, OBJECTS)
    collected = provider.collect(provider.job)
    assert collected["reason"] == "NO_RESULT_OBJECT_COLLECTED_WHAT_EXISTS"
    assert collected["artifacts_available"] is False
    assert not (tmp_path / "receipt" / "remote_source.zip").exists()


def test_one_unreadable_object_does_not_abort_the_rescue(tmp_path):
    """A single bad key must cost one file, not the whole payload."""
    objects = dict(OBJECTS)
    objects["results/artifacts/broken.json"] = None      # get_object will raise
    provider = _provider(tmp_path, objects)
    collected = provider.collect(provider.job)
    saved = {entry["key"] for entry in collected["artifacts_collected"]}
    assert "results/artifacts/readout.json" in saved
    assert [entry["key"] for entry in collected["uncollected"]] == \
        ["results/artifacts/broken.json"]
