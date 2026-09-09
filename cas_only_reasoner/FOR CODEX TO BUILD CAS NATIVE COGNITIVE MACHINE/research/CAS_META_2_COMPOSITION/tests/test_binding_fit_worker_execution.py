"""Error-preservation demonstration through the actual exported worker.

These tests execute the REAL rendered worker script (``launch.render_worker()``
output — the exact text exported into the source package), driven in-process
with a fake subprocess boundary and a fake boto3 boundary. The "inner runner"
step spawns a REAL, deliberately failing, NON-NEURAL child process
(``sys.executable -c`` raising a marked RuntimeError) — never the neural mode.

Scenarios:
1. child fails -> worker failure report preserves the original child error;
2. a SECOND reporting failure (boto3 client raises after the report is
   written) -> the original child error still survives on disk;
3. the launcher collection path (wait/collect) consumes the worker-produced
   report and the original child error survives into ``training_result.json``.
"""
import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from aws import binding_fit_launch as launch

JOB = "cas-meta2-teaching-binding-20260908170000-abcdef12"

CHILD_MARKER = "DELIBERATE_NON_NEURAL_CHILD_FAILURE_9c41"
REPORTING_MARKER = "SIMULATED_SECOND_REPORTING_FAILURE"

FAILING_CHILD = (
    "import sys\n"
    "def boom():\n"
    "    raise RuntimeError(%r)\n"
    "boom()\n" % CHILD_MARKER
)


class FakeClientError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


def fake_clients(sg_groups=()):
    def raiser(code):
        def _raise(**kwargs):
            raise FakeClientError(code)
        return _raise

    ec2 = SimpleNamespace(
        describe_instances=raiser("InvalidInstanceID.NotFound"),
        describe_security_groups=lambda **k: {"SecurityGroups": list(sg_groups), "NextToken": None},
        delete_security_group=lambda GroupId: None)
    scheduler = SimpleNamespace(get_schedule=raiser("ResourceNotFoundException"))
    iam = SimpleNamespace(get_role=raiser("NoSuchEntity"),
                          get_instance_profile=raiser("NoSuchEntity"),
                          remove_role_from_instance_profile=raiser("NoSuchEntity"),
                          delete_role_policy=raiser("NoSuchEntity"))
    s3 = SimpleNamespace(list_objects_v2=raiser("NoSuchBucket"))
    clients = {"ec2": ec2, "s3": s3, "iam": iam, "scheduler": scheduler}
    return clients, []


def make_provider(ledger_path, clients):
    return launch.BindingFitProvider(job=JOB, source_sha="a" * 40, archive_sha256="b" * 64,
                                     manifest_sha256="c" * 64, ledger_path=ledger_path,
                                     clients=clients, client_error=FakeClientError)


class RecordingS3:
    def __init__(self, raise_on_client=False):
        self.raise_on_client = raise_on_client
        self.puts = []

    def client(self, *args, **kwargs):
        if self.raise_on_client:
            raise RuntimeError(REPORTING_MARKER)
        return SimpleNamespace(put_object=self._put_object)

    def _put_object(self, **kwargs):
        self.puts.append(kwargs)


def run_worker(tmp_path, *, raise_on_client=False):
    """Execute the actual exported worker text; return (results_bytes, sidecar,
    raised_error_or_None)."""
    root = tmp_path / "package"
    (root / "venv" / "bin").mkdir(parents=True)
    (root / "venv" / "bin" / "python").write_text("")  # exists() probe only
    config = {"schema": "cas-teaching-binding-fit-worker-config/1",
              "job": JOB, "bucket": "job-bucket", "region": "us-west-2"}
    (root / "config.json").write_text(json.dumps(config))
    worker_path = root / launch.WORKER_NAME
    worker_path.write_text(launch.render_worker())

    fake_boto3 = RecordingS3(raise_on_client=raise_on_client)

    def fake_run(argv, **kwargs):
        if "_inner_runner.py" in str(argv):
            return subprocess.run([sys.executable, "-c", FAILING_CHILD],
                                  capture_output=True, text=True)
        if "-m" in argv and "pip" in argv:
            return SimpleNamespace(returncode=0)
        raise AssertionError("unexpected child invocation: %r" % (argv,))

    namespace = {"__name__": "__main__", "__file__": str(worker_path)}
    saved = {}
    for name in ("subprocess", "boto3"):
        saved[name] = sys.modules.get(name)
    sys.modules["subprocess"] = SimpleNamespace(run=fake_run)
    sys.modules["boto3"] = fake_boto3
    raised = None
    try:
        exec(compile(worker_path.read_text(), str(worker_path), "exec"), namespace)
    except BaseException as error:
        raised = error
    finally:
        for name, module in saved.items():
            sys.modules[name] = module
    results = root / "results" / "result.json"
    sidecar = root / "results" / "result.json.sha256"
    assert results.is_file() and sidecar.is_file()
    raw = results.read_bytes()
    assert json.loads(raw)["schema"] == "cas-teaching-binding-fit-training/1"
    return raw, sidecar.read_bytes().strip(), raised, fake_boto3, root


def test_exported_worker_preserves_original_child_error(tmp_path):
    """The actual exported worker keeps the failing child's original error."""
    raw, sidecar, raised, fake_boto3, root = run_worker(tmp_path)
    assert raised is None  # reporting succeeded; worker completed
    report = json.loads(raw)
    assert report["status"] == "REMOTE_WORKER_FAILED"
    message = report["failure"]["message"]
    assert "INNER_RUNNER_EXIT_1" in message
    assert CHILD_MARKER in message  # original child error survives verbatim
    assert launch.digest(raw) == sidecar.decode("utf-8")
    assert (root / "_inner_runner.py").is_file()  # real inner text was materialized
    assert fake_boto3.puts  # upload of the failure report happened


def test_exported_worker_survives_second_reporting_failure(tmp_path):
    """With a second, reporting-stage failure, the original child error still
    survives in results/result.json (never overwritten or lost)."""
    raw, sidecar, raised, _boto3, _root = run_worker(tmp_path, raise_on_client=True)
    assert raised is not None and REPORTING_MARKER in str(raised)
    report = json.loads(raw)
    assert report["status"] == "REMOTE_WORKER_FAILED"
    assert CHILD_MARKER in report["failure"]["message"]
    assert launch.digest(raw) == sidecar.decode("utf-8")


def test_collection_path_preserves_child_error_through_wait_and_collect(tmp_path):
    """The launcher wait/collect path consumes the worker's report and the
    original child error survives into training_result.json."""
    raw, sidecar, _raised, _boto3, _root = run_worker(tmp_path)
    clients, _ = fake_clients()

    def get_object(**kwargs):
        key = kwargs["Key"]
        if key == "results/result.json":
            return {"Body": io.BytesIO(raw)}
        if key == "results/result.json.sha256":
            return {"Body": io.BytesIO(sidecar)}
        raise AssertionError("unexpected key: %r" % (key,))

    clients["s3"] = SimpleNamespace(get_object=get_object)
    provider = make_provider(tmp_path / "ledger.json", clients)
    provider._resources["bucket"] = "job-bucket"
    provider._instance_id = "i-0123456789abcdef0"
    (tmp_path / "evidence").mkdir()
    provider.configure_evidence(tmp_path / "evidence")

    outcome = provider.wait(JOB, timeout=60)
    assert outcome["worker_status"] == "REMOTE_FAILED"
    collected = provider.collect(JOB)
    training_result = (tmp_path / "evidence" / "training_result.json").read_bytes()
    assert CHILD_MARKER in training_result.decode("utf-8")
    assert collected["result_sha256"] == launch.digest(raw)
