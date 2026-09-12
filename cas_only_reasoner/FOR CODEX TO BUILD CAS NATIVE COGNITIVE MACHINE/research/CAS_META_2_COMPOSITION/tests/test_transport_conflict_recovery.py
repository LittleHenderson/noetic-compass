"""A create-only conflict must never destroy a delivery that already happened.

Why this file exists. Job cas-meta2-graph6read-20260912062331-b34e3d92 ran the
readout to completion on a GPU instance, uploaded readout.json (2,610,908 bytes)
and measurements.json, and then died before writing results/result.json:

    File ".../graph6_face_readout_worker.py", line 260, in upload_results
        upload = publish_once(s3, bucket, root, published, 'result.json', ...)
    File ".../graph6_face_readout_worker.py", line 232, in publish_once
        existing = s3.get_object(Bucket=bucket, Key=key)
    botocore.errorfactory.AccessDenied: ... not authorized to perform:
        s3:GetObject on ".../results/evidence/phase_pip_requirements_starting.json"

Three faults in one line of failure:

1. ``upload_results`` was called WITHOUT the publisher's map of what it had
   already uploaded, so the final pass started from an empty map and re-put every
   file the publisher had already sent. Every one of those create-only puts
   conflicted.
2. The conflict handler read the object back to compare digests, but the job role
   granted s3:GetObject on input/* only - so the read was denied.
3. The denial was raised, killing a worker whose science was finished and whose
   payload was already safely in the bucket.

The fixes are tested here in that order. The science survived only because the
incremental publisher had already sent the payload; that is the part of the
design that worked, and these tests exist so the rest of it stops undoing it.

No AWS, no network, no reservation.
"""
import json
import pathlib

import pytest

from aws import graph6_face_readout_launch as readout
from aws import graph_training_curriculum_launch as curriculum
from aws import run_evidence


def _transport(render):
    """Every definition in the rendered worker, without running main()."""
    namespace = {"__name__": "packaged_worker_not_main"}
    exec(run_evidence.unified_worker_source(render()), namespace)  # noqa: S102
    return namespace


class _CreateOnlyS3:
    """A bucket with real create-only semantics and a read permission switch."""

    def __init__(self, *, readable=True, existing=None):
        self.objects = dict(existing or {})
        self.readable = readable
        self.puts = []

    def put_object(self, Bucket=None, Key=None, Body=None, IfNoneMatch=None):
        self.puts.append(Key)
        if IfNoneMatch == "*" and Key in self.objects:
            raise _ClientError("PreconditionFailed", "PutObject")
        self.objects[Key] = Body
        return {}

    def get_object(self, Bucket=None, Key=None):
        if not self.readable:
            raise _ClientError("AccessDenied", "GetObject")
        if Key not in self.objects:
            raise _ClientError("NoSuchKey", "GetObject")
        return {"Body": _Body(self.objects[Key])}


class _ClientError(Exception):
    def __init__(self, code, operation):
        super().__init__("%s on %s" % (code, operation))
        self.response = {"Error": {"Code": code}}


class _Body:
    def __init__(self, raw):
        self._raw = raw

    def read(self, *args):
        return self._raw


def _populate(root):
    results = root / "results"
    (results / "artifacts").mkdir(parents=True)
    (results / "evidence").mkdir(parents=True)
    (results / "artifacts" / "readout.json").write_text('{"rows": 216}')
    (results / "evidence" / "phase_worker_started.json").write_text('{"phase": "a"}')
    body = json.dumps({"status": "FINISHED"}).encode("utf-8")
    (results / "result.json").write_bytes(body)
    (results / "result.json.sha256").write_text("deadbeef")
    return results


@pytest.mark.parametrize("render", [readout.render_worker, curriculum.render_worker],
                         ids=["readout", "curriculum"])
def test_the_final_upload_is_handed_the_publishers_map(render):
    """Fault 1, checked on the rendered source itself."""
    source = run_evidence.unified_worker_source(render())
    calls = [line.strip() for line in source.splitlines()
             if "upload_results(s3, bucket," in line and "def " not in line]
    assert calls, source[-2000:]
    for call in calls:
        assert call.endswith("_published)"), call


def test_a_conflict_whose_readback_is_denied_does_not_kill_the_run(tmp_path):
    """Faults 2 and 3: the exact production failure, reproduced and survived."""
    namespace = _transport(readout.render_worker)
    results = _populate(tmp_path)
    already = {"results/evidence/phase_worker_started.json": b"{}",
               "results/artifacts/readout.json": b"{}"}
    s3 = _CreateOnlyS3(readable=False, existing=already)
    # published={} is the old behaviour: it re-puts what is already there
    upload = namespace["upload_results"](s3, "bucket", tmp_path, {})
    assert [entry["key"] for entry in upload["unverified_existing"]] == sorted(already)
    # the marker still went up, which is the whole point
    assert upload["marker"] is True
    assert "results/result.json" in s3.objects
    assert upload["result"] is True


def test_a_genuine_digest_conflict_is_still_fatal(tmp_path):
    """The safety the recovery must not quietly remove."""
    namespace = _transport(readout.render_worker)
    _populate(tmp_path)
    s3 = _CreateOnlyS3(readable=True, existing={
        "results/artifacts/readout.json": b'{"rows": 999}'})
    with pytest.raises(SystemExit) as caught:
        namespace["upload_results"](s3, "bucket", tmp_path, {})
    assert "EVIDENCE_DIGEST_CONFLICT:results/artifacts/readout.json" in str(caught.value)


def test_the_publishers_map_prevents_the_conflict_arising_at_all(tmp_path):
    """Fault 1 again, behaviourally: with the map, nothing is re-put."""
    namespace = _transport(readout.render_worker)
    _populate(tmp_path)
    s3 = _CreateOnlyS3(readable=False)
    published = {}
    namespace["publish_once"](s3, "bucket", tmp_path, published,
                             "result.json", "result.json.sha256")
    first = list(s3.puts)
    assert first, "the publisher uploaded nothing"
    upload = namespace["upload_results"](s3, "bucket", tmp_path, published)
    # nothing from the first pass is sent again, so no conflict can occur
    assert upload["unverified_existing"] == []
    assert upload["marker"] is True


def test_the_worker_role_can_read_back_what_it_wrote():
    """Fault 2 at its root: the policy document the launcher actually builds.

    Built by running the launcher's own policy expression rather than by reading
    the file as text, so a reformat cannot make this pass or fail by accident.
    """
    bucket = "cas-meta2-graph6read-example-807562639912"
    policy = _role_policy(bucket)
    statements = {tuple(row["Action"]): row["Resource"] for row in policy["Statement"]}
    get = statements[("s3:GetObject",)]
    put = statements[("s3:PutObject",)]
    assert "arn:aws:s3:::" + bucket + "/input/*" in get
    # the create-only transport must be able to read back what it wrote
    assert "arn:aws:s3:::" + bucket + "/results/*" in get
    # writes stay confined to results/*: reading more did not widen writing
    assert put == ["arn:aws:s3:::" + bucket + "/results/*"]
    for resource in get + put:
        assert resource.startswith("arn:aws:s3:::" + bucket + "/"), resource


def _role_policy(bucket):
    """The policy from the launcher's source, evaluated - not pattern-matched."""
    import ast
    import textwrap

    text = pathlib.Path(curriculum.__file__).read_text(encoding="utf-8")
    # anchor on the job-only policy, not on the role's trust document, which
    # also ends in PolicyDocument=json.dumps(
    marker = 'PolicyDocument=json.dumps('
    start = text.index(marker, text.index('PolicyName="job-only"')) + len(marker)
    depth, index = 1, start
    while depth:
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
        index += 1
    expression = textwrap.dedent(text[start:index - 1])
    return eval(compile(ast.Expression(ast.parse(expression, mode="eval").body),
                        "<policy>", "eval"), {"bucket": bucket})
