"""Required real GPU gates for evaluation-only recovery; never enabled locally."""
import os
from pathlib import Path
import sys

import pytest

from cas_meta2.contrast_recovery_v6 import binding as b
from cas_meta2.contrast_recovery_v6.core import FAILURE, evaluate_case
from cas_meta2.contrast_recovery_v6.runtime import FrozenOperations

pytestmark = [pytest.mark.gpu, pytest.mark.skipif(
    sys.platform != 'linux' or os.environ.get('CAS_META2_RUN_CONTRAST_RECOVERY') != '1'
    or os.environ.get('CAS_META2_RUN_GPU_TESTS') != '1', reason='Explicit AWS-only recovery GPU gate')]


def _run_saved(index, tmp_path):
    job = os.environ.get('CAS_META2_AWS_JOB_ID')
    b.require_request(job, True)
    assert Path(tmp_path).resolve().is_relative_to(b.ROOT)
    context = b.load_inputs(admission_path=os.environ['CAS_META2_RECOVERY_ADMISSION'],
        admission_sha256=os.environ['CAS_META2_RECOVERY_ADMISSION_SHA256'],
        recovery_manifest_path=os.environ['CAS_META2_RECOVERY_MANIFEST'],
        recovery_manifest_sha256=os.environ['CAS_META2_RECOVERY_MANIFEST_SHA256'],
        inputs=os.environ['CAS_META2_RECOVERY_INPUTS'], packet=os.environ['CAS_META2_RECOVERY_PACKET'])
    ops = FrozenOperations(context,job=job,enabled=True)
    before = b.source_identity(context['admission'],context['recovery_manifest'])
    result = evaluate_case(index,context['tasks'][index],context['predictions'][index]['actions'],
                           tmp_path/f'case_{index:04d}',ops)
    ops.assert_identity()
    assert b.source_identity(context['admission'],context['recovery_manifest']) == before
    assert result['reference_verification']['task_correct'] is True
    assert set(result['arms']) == set(b.ARMS)
    return result


def test_saved_case_zero_uses_frozen_reference_and_verifier(tmp_path):
    result = _run_saved(0,tmp_path)
    assert result['arms']['rule']['execution_status'] == 'EXECUTED'
    assert result['arms']['rule']['verification']['task_correct'] is True
    assert all(result['arms'][arm]['execution_status'] == 'REJECTED' for arm in b.ARMS if arm != 'rule')


def test_saved_case_nine_contains_only_known_post_start_failure(tmp_path):
    result = _run_saved(9,tmp_path)
    failed = result['arms']['cas_trained']
    assert failed['execution_status'] == FAILURE
    assert failed['model_rejection'] is False
    assert failed['verification']['task_correct'] is False
    assert failed['partial_work']['committed_native_runs'] == 7
    assert failed['partial_work']['committed_reserved_policy_units'] == 504
    assert failed['partial_work']['compute_complete'] is False
    assert failed['partial_work']['failed_tick_compute'] is None
    assert result['arms']['rule']['execution_status'] == 'EXECUTED'
    assert result['arms']['rule']['verification']['task_correct'] is True
