"""The rendered workers must run as ``__main__`` without a NameError.

Why this file exists. On 2026-09-12 the readout job reached AWS, launched a GPU
instance, and died 20 seconds into the run with::

    File ".../graph6_face_readout_worker.py", line 84, in main
        beacon(root, 'worker_started')
    NameError: name 'beacon' is not defined

The instance bootstrap was correct. The shared transport was appended to the END
of the worker source, which placed ``def beacon`` AFTER
``if __name__ == '__main__': main()``. Python binds a name when it executes the
``def``, so the guard ran ``main()`` first and the name did not exist yet.

Nothing already in the suite could see it:

* a compile check passes - the file is syntactically perfect;
* importing the worker as a module passes - an import executes the whole file,
  including the trailing defs, and never enters the guard;
* the existing rehearsal execs individual function bodies, which skips the
  module body altogether.

The bug only appears when the module is executed AS ``__main__``. So that is what
this file does, in a subprocess, with a fake boto3 and with the environment step
forced to fail immediately - no venv, no pip, no torch, no network, no AWS, no
reservation.

A $7.00 reservation and a launched g7.2xlarge were spent discovering this.
"""
import json
import subprocess
import sys

import pytest

from aws import graph6_face_readout_launch as readout
from aws import graph_training_curriculum_launch as curriculum
from aws import run_evidence


WORKERS = (("readout", readout.WORKER_NAME, readout.render_worker),
           ("curriculum", curriculum.WORKER_NAME, curriculum.render_worker))


DRIVER = r"""
import json, runpy, shutil, sys, types
from pathlib import Path

root = Path(sys.argv[1])


class _S3:
    def __init__(self):
        self.puts = []

    def put_object(self, **kwargs):
        self.puts.append(kwargs.get('Key'))
        return {}

    def head_object(self, **kwargs):
        raise RuntimeError('absent')


fake = types.ModuleType('boto3')
fake.client = lambda *a, **k: _S3()
sys.modules['boto3'] = fake

# No interpreter is 'found', so the worker raises SystemExit in its own first
# environment step and takes its failure path. Nothing is installed.
shutil.which = lambda *a, **k: None

try:
    runpy.run_path(str(root / sys.argv[2]), run_name='__main__')
    status = 'RETURNED'
except SystemExit as error:
    status = 'SYSTEMEXIT:' + str(error.code)
except BaseException as error:
    status = type(error).__name__ + ':' + str(error)
print('DRIVER_STATUS ' + status)
"""


def _stage(tmp_path, name, render):
    source = run_evidence.unified_worker_source(render())
    (tmp_path / name).write_text(source, encoding='utf-8')
    (tmp_path / 'config.json').write_text(json.dumps(
        {'job': 'entrypoint-order-check', 'bucket': 'no-such-bucket',
         'region': 'us-west-2'}), encoding='utf-8')
    driver = tmp_path / '_driver.py'
    driver.write_text(DRIVER, encoding='utf-8')
    return subprocess.run([sys.executable, '-B', str(driver), str(tmp_path), name],
                          capture_output=True, text=True, timeout=300)


@pytest.mark.parametrize('label,name,render', WORKERS,
                         ids=[entry[0] for entry in WORKERS])
def test_the_worker_runs_as_main_without_an_unbound_name(label, name, render,
                                                         tmp_path):
    """The exact failure mode of job cas-meta2-graph6read-20260912044325."""
    result = _stage(tmp_path, name, render)
    combined = result.stdout + result.stderr
    assert 'NameError' not in combined, combined[-3000:]
    assert 'DRIVER_STATUS' in combined, combined[-3000:]
    status = [line for line in combined.splitlines()
              if line.startswith('DRIVER_STATUS')][-1]
    # Both designed endings are accepted, because the two workers differ on
    # purpose: the readout raises SystemExit(1) on failure, the curriculum worker
    # returns and lets its uploaded result.json carry the status. Anything else
    # is an exception escaping main(), which is the class of defect this file is
    # here to catch - the shipped readout also died on
    # ``KeyError: 'result'`` in its final print, after the transport replaced the
    # uploader and changed the shape of its return value.
    assert status in ('DRIVER_STATUS SYSTEMEXIT:1', 'DRIVER_STATUS RETURNED'),         combined[-3000:]


@pytest.mark.parametrize('label,name,render', WORKERS,
                         ids=[entry[0] for entry in WORKERS])
def test_the_failed_worker_still_writes_its_result_and_its_beacons(
        label, name, render, tmp_path):
    """A worker that fails must leave a readable failure, not silence."""
    _stage(tmp_path, name, render)
    results = tmp_path / 'results'
    report = json.loads((results / 'result.json').read_bytes())
    # the two workers use different status words for the same state
    assert report['status'] in ('WORKER_FAILED', 'REMOTE_WORKER_FAILED')
    assert report['failure']['type'] == 'SystemExit'
    assert report['failure']['message'] == 'SUPPORTED_PYTHON_REQUIRED'
    assert 'SUPPORTED_PYTHON_REQUIRED' in         (results / 'failure.json').read_text(encoding='utf-8')
    # the beacons written before the failure say how far the worker got
    marks = {path.name for path in (results / 'evidence').glob('phase_*.json')}
    assert 'phase_worker_started.json' in marks, sorted(marks)
    assert 'phase_publisher_started.json' in marks, sorted(marks)


@pytest.mark.parametrize('label,name,render', WORKERS,
                         ids=[entry[0] for entry in WORKERS])
def test_every_definition_precedes_the_entrypoint(label, name, render):
    """The blunt structural law, stated once and checked on both workers."""
    source = run_evidence.unified_worker_source(render())
    bound = run_evidence.require_definitions_precede_entrypoint(source)
    for expected in ('beacon', 'publisher', 'publish_once', 'upload_results',
                     'PUBLISH_SECONDS', 'main'):
        assert expected in bound, (expected, bound)


def test_a_worker_with_a_trailing_definition_is_refused():
    """The check must actually fail on the shape that was shipped."""
    broken = ("def main():\n"
              "    beacon()\n"
              "\n"
              "\n"
              "if __name__ == '__main__':\n"
              "    main()\n"
              "def beacon():\n"
              "    return None\n")
    with pytest.raises(Exception) as caught:
        run_evidence.require_definitions_precede_entrypoint(broken)
    assert 'DEFINITION_AFTER_ENTRYPOINT:beacon' in str(caught.value)


def test_unified_transport_refuses_to_emit_a_trailing_definition():
    """The builder cannot produce the broken shape even if a renderer changes."""
    source = run_evidence.unified_worker_source(readout.render_worker())
    run_evidence.require_definitions_precede_entrypoint(source)
    lines = source.splitlines()
    guard = run_evidence.entrypoint_index(lines)
    assert guard is not None
    assert 'def beacon(' in source[:len('\n'.join(lines[:guard]))]
