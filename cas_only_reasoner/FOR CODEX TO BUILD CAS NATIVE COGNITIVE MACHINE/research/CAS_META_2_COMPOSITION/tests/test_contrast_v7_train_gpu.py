"""Actual AWS-only saved-fixture assembly/training smoke; no local neural work."""
import os
import sys
import pytest

pytestmark = pytest.mark.gpu
if (sys.platform != 'linux'
        or os.environ.get('CAS_META2_RUN_PROTOTYPE_TRAINING') != '1'
        or os.environ.get('CAS_META2_RUN_GPU_TESTS') != '1'):
    pytest.skip('Explicit Linux AWS prototype GPU smoke job required', allow_module_level=True)

from cas_meta2.contrast_v7 import gpu_preflight as q

JOB = os.environ.get('CAS_META2_AWS_JOB_ID', '')
q.require_request(JOB)


def test_saved_fixture_exact_append_and_matched_cuda_training_exit(tmp_path, request):
    assert getattr(request.config, '_cas_v4_alias_owner', False) is True
    assert request.config.pluginmanager.hasplugin('cas_meta2.pytest_no_aliases_v4')
    q.run_path(tmp_path)
    result = q.run_smoke(tmp_path/'v7_smoke', job=JOB, max_seconds=900,
                         include_native=q.NATIVE_GATE_READY)
    assert result['completed'] is True and result['splits'] == q.EXPECTED_SPLITS
    assert result['optimizer_steps'] == {'cas':22, 'generic':22}
    assert result['prepare_exit_before_training'] is True
    assert result['training_gate']['private_test_labels_opened'] is False
    assert result['fixture']['source_pins_sha256'] == q.PINS_SHA256
    assert result['fixture']['public_loader_sha256'] == q.LOADER_SHA256
    assert all(row['changed_count'] > 0 and row['all_loaded_on_cuda'] is True
               for row in result['changed_weights'].values())
    assert result['learning_accepted'] is False and result['task_generation'] is False
    if q.NATIVE_GATE_READY:
        native = q.check_native_smoke(result['native_receipt'])
        assert result['native_evaluation_completed'] is True
        assert native['cases'] == native['reference_cases'] == 9
        assert native['arm_verdicts'] == 45
        assert native['results']['rule']['task_correct'] == 9
        assert native['groups']['depth_3']['rule']['total'] == 6
        assert native['groups']['depth_4']['rule']['total'] == 3
    else:
        assert result['native_evaluation_completed'] is False
        assert result['native_receipt'] is None
        assert result['native_integration_status'] == 'PENDING_VALIDATED_V7_NATIVE_EVALUATOR'
